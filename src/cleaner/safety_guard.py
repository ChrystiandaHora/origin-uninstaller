import os
import re
from typing import Optional, Set

# Lista de pacotes essenciais para o funcionamento do Debian / Linux.
# Esses pacotes NUNCA devem ter permissão de desinstalação pela interface.
CRITICAL_PACKAGES: Set[str] = {
    # Inicialização e init system
    "systemd",
    "systemd-sysv",
    "systemd-timesyncd",
    "init",
    "sysvinit-utils",
    # Shell básico e utilitários Unix fundamentais
    "coreutils",
    "bash",
    "dash",
    "sed",
    "grep",
    "gawk",
    "findutils",
    "tar",
    "gzip",
    "bzip2",
    "xz-utils",
    "procps",
    "util-linux",
    "bsdutils",
    "mount",
    # Autenticação e segurança de contas
    "sudo",
    "login",
    "passwd",
    "shadow",
    "base-files",
    "base-passwd",
    "debianutils",
    "libc6",
    "libc-bin",
    "libpam0g",
    "libpam-modules",
    "libpam-runtime",
    "policykit-1",
    "polkitd",
    # Gerenciamento de pacotes e subsistemas
    "apt",
    "apt-get",
    "dpkg",
    "debconf",
    "flatpak",
    "snapd",
    # Kernel e bootloader
    "linux-base",
    # Desktop Environment Shell & Display Server
    "gnome-shell",
    "mutter",
    "gdm3",
    "xorg",
    "wayland",
    "dbus",
    "pipewire",
    # Origens dos apps da suíte Origin
    "origin-updater",
    "origin-uninstaller",
}

# Prefixos e regex de pacotes protegidos
CRITICAL_PATTERNS = [
    re.compile(r"^linux-image-"),
    re.compile(r"^linux-headers-"),
    re.compile(r"^grub-"),
    re.compile(r"^systemd-"),
]

# Diretórios que JAMAIS podem ser marcados como resíduo (salvaguarda de caminho)
PROTECTED_PATHS: Set[str] = {
    "/",
    "/bin",
    "/boot",
    "/dev",
    "/etc",
    "/home",
    "/lib",
    "/lib64",
    "/media",
    "/mnt",
    "/opt",
    "/proc",
    "/root",
    "/run",
    "/sbin",
    "/sys",
    "/tmp",
    "/usr",
    "/var",
    "/usr/bin",
    "/usr/share",
    "/usr/local",
    "/var/lib",
    "/var/lib/dpkg",
    "/var/lib/apt",
    "/var/lib/flatpak",
    "/var/lib/snapd",
    os.path.expanduser("~"),
    os.path.expanduser("~/.config"),
    os.path.expanduser("~/.cache"),
    os.path.expanduser("~/.local"),
    os.path.expanduser("~/.local/share"),
    os.path.expanduser("~/.local/bin"),
    os.path.expanduser("~/.local/state"),
    os.path.expanduser("~/.var"),
    os.path.expanduser("~/.var/app"),
    os.path.expanduser("~/snap"),
    os.path.expanduser("~/Downloads"),
    os.path.expanduser("~/Documents"),
    os.path.expanduser("~/Desktop"),
}


def is_package_critical(pkg_name: str) -> Optional[str]:
    """
    Verifica se um pacote é essencial para a estabilidade do sistema.
    Retorna a razão da proteção ou None se for seguro desinstalar.
    """
    clean_name = pkg_name.strip().lower()

    if clean_name in CRITICAL_PACKAGES:
        return "Pacote essencial para a operação e inicialização do sistema Debian/Linux."

    for pat in CRITICAL_PATTERNS:
        if pat.match(clean_name):
            return "Componente de Kernel/Bootloader vital para a inicialização da máquina."

    return None


def is_path_safe_to_clean(path: str) -> bool:
    """
    Verifica se um caminho de resíduo é seguro para exclusão,
    impedindo a deleção acidental de diretórios-raiz ou pastas inteiras do usuário.
    """
    try:
        norm = os.path.realpath(os.path.expanduser(path.strip()))
    except Exception:
        return False

    if norm in PROTECTED_PATHS:
        return False

    # Evita exclusão de qualquer caminho excessivamente curto
    parts = [p for p in norm.split(os.sep) if p]
    if len(parts) < 3:
        return False

    # Se for dentro da home do usuário, deve ser uma subpasta específica
    home = os.path.realpath(os.path.expanduser("~"))
    if norm.startswith(home):
        rel = os.path.relpath(norm, home)
        rel_parts = [p for p in rel.split(os.sep) if p]
        # Não pode ser a home nem um diretório raiz da home direto sem ser uma subpasta de app
        if len(rel_parts) < 1:
            return False
        # Se for na raiz da home, só permitimos se for um dotfile específico (ex: ~/.dbeaver4, ~/.zoom)
        if len(rel_parts) == 1 and not rel_parts[0].startswith("."):
            return False

    return True
