import json
import logging
import os
import shutil
import subprocess
import threading
from typing import Callable, List, Optional

from ..cleaner.safety_guard import is_path_safe_to_clean
from ..models import AppType, InstalledApp, ResidualItem

logger = logging.getLogger(__name__)

WORKER_SCRIPT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "privileged_worker.py")
)


class UninstallerEngine:
    """
    Gerenciador e orquestrador do processo completo de remoção de aplicativos
    e limpeza profunda de diretórios residuais.
    """

    def __init__(self) -> None:
        self._is_running = False

    def uninstall_async(
        self,
        app: InstalledApp,
        residuals: List[ResidualItem],
        on_status: Callable[[float, str], None],
        on_log: Callable[[str], None],
        on_finished: Callable[[bool, Optional[str]], None],
    ) -> None:
        """Executa a desinstalação e limpeza em uma thread separada para não travar a UI."""
        thread = threading.Thread(
            target=self._run_uninstall,
            args=(app, residuals, on_status, on_log, on_finished),
            daemon=True,
        )
        thread.start()

    def _run_uninstall(
        self,
        app: InstalledApp,
        residuals: List[ResidualItem],
        on_status: Callable[[float, str], None],
        on_log: Callable[[str], None],
        on_finished: Callable[[bool, Optional[str]], None],
    ) -> None:
        self._is_running = True
        try:
            on_status(0.05, f"Preparando desinstalação de '{app.name}'...")
            on_log(f"=== Iniciando remoção de {app.name} ({app.id}) ===")
            on_log(f"Tipo: {app.app_type.label} | Versão: {app.version or 'N/A'}")

            # Separa resíduos do usuário e do sistema
            user_residuals = [r for r in residuals if r.selected and not r.requires_root]
            system_residuals = [r for r in residuals if r.selected and r.requires_root]

            # 1. Limpeza de resíduos de usuário (executados com privilégios do usuário)
            if user_residuals:
                on_status(0.15, "Limpando configurações e dados do usuário...")
                for r in user_residuals:
                    if not is_path_safe_to_clean(r.path):
                        on_log(f"⚠️ Ignorado por salvaguarda: {r.path}")
                        continue
                    if not os.path.exists(r.path):
                        continue

                    on_log(f"Removendo dados do usuário: {r.path}")
                    try:
                        if os.path.islink(r.path) or os.path.isfile(r.path):
                            os.remove(r.path)
                        elif os.path.isdir(r.path):
                            shutil.rmtree(r.path)
                    except Exception as err:
                        on_log(f"Erro ao remover {r.path}: {err}")

            # 2. Desinstalação do Pacote Principal
            success = True
            error_msg: Optional[str] = None

            if app.app_type == AppType.FLATPAK:
                on_status(0.40, f"Desinstalando Flatpak '{app.id}'...")
                scope_arg = "--user" if app.flatpak_scope == "user" else "--system"
                cmd = ["flatpak", "uninstall", scope_arg, "--delete-data", "-y", app.id]
                on_log(f"Executando: {' '.join(cmd)}")
                proc = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                )
                if proc.stdout:
                    for line in proc.stdout:
                        on_log(line.rstrip())
                ret = proc.wait()
                if ret != 0:
                    on_log(f"Aviso: flatpak uninstall retornou código {ret}")

            elif app.app_type in (AppType.APT, AppType.STANDALONE, AppType.SNAP):
                # Necessita de privilégios de administrador via pkexec
                action_name = "apt_purge" if app.app_type == AppType.APT else (
                    "snap_remove" if app.app_type == AppType.SNAP else "clean_standalone"
                )
                payload = {
                    "action": action_name,
                    "package": app.package_name if app.app_type != AppType.STANDALONE else "",
                    "system_paths": [r.path for r in system_residuals],
                }

                on_status(0.35, "Solicitando autorização de administrador...")
                cmd = ["pkexec", "/usr/bin/python3", WORKER_SCRIPT, json.dumps(payload)]
                on_log("Aguardando confirmação de autenticação do sistema (pkexec)...")

                proc = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                )

                if proc.stdout:
                    for line in proc.stdout:
                        clean_line = line.strip()
                        if clean_line.startswith("@@STATUS|"):
                            parts = clean_line.split("|", 2)
                            if len(parts) >= 3:
                                try:
                                    frac = float(parts[1])
                                    msg = parts[2]
                                    on_status(frac, msg)
                                except ValueError:
                                    pass
                        elif clean_line.startswith("@@LOG|"):
                            on_log(clean_line[6:])
                        elif clean_line.startswith("@@DONE|"):
                            pass
                        else:
                            on_log(clean_line)

                ret = proc.wait()
                if ret != 0:
                    success = False
                    error_msg = f"Processo cancelado ou falhou com código {ret}"
                    on_log(f"Erro: {error_msg}")

            # 3. Limpeza de atalhos e bancos de dados locais
            on_status(0.90, "Atualizando atalhos do ambiente gráfico...")
            user_apps = os.path.expanduser("~/.local/share/applications")
            if os.path.exists(user_apps):
                subprocess.run(["update-desktop-database", user_apps], capture_output=True)

            user_icons = os.path.expanduser("~/.local/share/icons/hicolor")
            if os.path.exists(user_icons):
                subprocess.run(["gtk-update-icon-cache", "-f", "-t", user_icons], capture_output=True)

            if success:
                on_status(1.0, f"'{app.name}' foi removido completamente do sistema!")
                on_log(f"✔ Concluído: {app.name} e todos os seus dados foram limpos.")
                on_finished(True, None)
            else:
                on_status(1.0, "Operação finalizada com avisos/erros.")
                on_finished(False, error_msg)

        except Exception as e:
            logger.exception("Falha durante desinstalação")
            on_log(f"ERRO CRÍTICO: {e}")
            on_status(1.0, f"Erro: {e}")
            on_finished(False, str(e))
        finally:
            self._is_running = False
