#!/usr/bin/env python3
"""
Worker privilegiado executado via pkexec em uma única sessão autenticada.
Realiza desinstalação profunda via apt-get purge, remoção de pacotes e limpeza
de diretórios do sistema (/etc, /opt, /var), transmitindo logs em tempo real.
"""

import json
import os
import pty
import select
import shutil
import subprocess
import sys
from typing import Dict, List

# Adiciona o diretório raiz do projeto ao path para importar as salvaguardas
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from src.cleaner.safety_guard import is_package_critical, is_path_safe_to_clean


def emit(text: str) -> None:
    sys.stdout.write(text)
    if not text.endswith("\n"):
        sys.stdout.write("\n")
    sys.stdout.flush()


def emit_status(fraction: float, message: str) -> None:
    clean_msg = message.replace("\n", " ").strip()
    sys.stdout.write(f"@@STATUS|{fraction:.4f}|{clean_msg}\n")
    sys.stdout.flush()


def emit_log(text: str) -> None:
    sys.stdout.write(f"@@LOG|{text}\n")
    sys.stdout.flush()


def run_pty_command(cmd: List[str]) -> int:
    """Executa um comando dentro de um pseudo-terminal (PTY) para capturar saída em tempo real."""
    env = os.environ.copy()
    env["DEBIAN_FRONTEND"] = "noninteractive"
    env["TERM"] = "dumb"
    env["LC_ALL"] = "C.UTF-8"

    master_fd, slave_fd = pty.openpty()
    proc = subprocess.Popen(
        cmd,
        stdin=slave_fd,
        stdout=slave_fd,
        stderr=slave_fd,
        env=env,
        close_fds=True,
    )
    os.close(slave_fd)

    buf = ""
    try:
        while True:
            rlist, _, _ = select.select([master_fd], [], [], 0.2)
            if master_fd in rlist:
                try:
                    data = os.read(master_fd, 1024)
                except OSError:
                    break
                if not data:
                    break
                chunk = data.decode("utf-8", errors="replace")
                for ch in chunk:
                    if ch in ("\r", "\n"):
                        line = buf.strip()
                        if line:
                            emit_log(line)
                        buf = ""
                    else:
                        buf += ch
            elif proc.poll() is not None:
                break
        if buf.strip():
            emit_log(buf.strip())
    finally:
        try:
            os.close(master_fd)
        except OSError:
            pass

    return proc.wait()


def main() -> int:
    if len(sys.argv) < 2:
        emit("Erro: Nenhum payload JSON fornecido.")
        return 1

    try:
        payload = json.loads(sys.argv[1])
    except Exception as e:
        emit(f"Erro ao decodificar JSON: {e}")
        return 1

    action = payload.get("action", "")
    pkg_name = payload.get("package", "")
    system_paths: List[str] = payload.get("system_paths", [])

    emit_status(0.05, "Iniciando operação privilegiada...")

    # 1. Validação de segurança do pacote
    if pkg_name:
        crit = is_package_critical(pkg_name)
        if crit:
            emit_log(f"ERRO DE SEGURANÇA: O pacote '{pkg_name}' é protegido: {crit}")
            emit_status(1.0, "Operação abortada por segurança.")
            return 2

    # 2. Executa a remoção do pacote
    if action == "apt_purge" and pkg_name:
        emit_status(0.20, f"Removendo e purgando pacote '{pkg_name}' via APT...")
        emit_log(f"Executando: apt-get purge --autoremove -y {pkg_name}")
        cmd = ["apt-get", "purge", "--autoremove", "-y", pkg_name]
        ret = run_pty_command(cmd)
        if ret != 0:
            emit_log(f"Aviso: apt-get purge retornou código {ret}")

    elif action == "flatpak_uninstall" and pkg_name:
        emit_status(0.20, f"Desinstalando Flatpak do sistema '{pkg_name}'...")
        emit_log(f"Executando: flatpak uninstall --delete-data -y {pkg_name}")
        cmd = ["flatpak", "uninstall", "--delete-data", "-y", pkg_name]
        ret = run_pty_command(cmd)
        if ret != 0:
            emit_log(f"Aviso: flatpak uninstall retornou código {ret}")

    elif action == "snap_remove" and pkg_name:
        emit_status(0.20, f"Removendo Snap '{pkg_name}'...")
        emit_log(f"Executando: snap remove --purge {pkg_name}")
        cmd = ["snap", "remove", "--purge", pkg_name]
        ret = run_pty_command(cmd)
        if ret != 0:
            emit_log(f"Aviso: snap remove retornou código {ret}")

    # 3. Limpeza de caminhos residuais do sistema (/etc, /opt, /var)
    if system_paths:
        emit_status(0.70, "Limpando diretórios residuais de sistema...")
        for p in system_paths:
            if not is_path_safe_to_clean(p):
                emit_log(f"Ignorado por segurança: {p}")
                continue
            if not os.path.exists(p):
                continue

            emit_log(f"Removendo diretório de sistema: {p}")
            try:
                if os.path.islink(p) or os.path.isfile(p):
                    os.remove(p)
                elif os.path.isdir(p):
                    shutil.rmtree(p)
            except Exception as e:
                emit_log(f"Falha ao remover {p}: {e}")

    emit_status(0.95, "Atualizando banco de dados de atalhos do sistema...")
    subprocess.run(["update-desktop-database"], capture_output=True)

    emit_status(1.0, "Operação concluída com sucesso!")
    emit("@@DONE|SUCCESS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
