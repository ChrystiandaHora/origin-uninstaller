import configparser
import glob
import os
from typing import Dict, List, Optional, Set, Tuple

# Mapeamento para pacotes populares cujo nome do pacote difere do .desktop ou merece tratamento especial
POPULAR_PACKAGES: Dict[str, Tuple[str, str]] = {
    "google-chrome-stable": ("Google Chrome", "google-chrome"),
    "google-chrome": ("Google Chrome", "google-chrome"),
    "code": ("Visual Studio Code", "vscode"),
    "firefox-esr": ("Firefox ESR", "firefox-esr"),
    "firefox": ("Mozilla Firefox", "firefox"),
    "spotify-client": ("Spotify", "spotify-client"),
    "anydesk": ("AnyDesk", "anydesk"),
    "discord": ("Discord", "discord"),
    "dbeaver-ce": ("DBeaver Community", "dbeaver"),
    "rustdesk": ("RustDesk", "rustdesk"),
    "docker-desktop": ("Docker Desktop", "docker"),
    "obs-studio": ("OBS Studio", "com.obsproject.Studio"),
    "vlc": ("VLC Media Player", "vlc"),
    "gimp": ("GIMP", "gimp"),
    "inkscape": ("Inkscape", "inkscape"),
    "blender": ("Blender", "blender"),
    "steam-installer": ("Steam", "steam"),
    "steam": ("Steam", "steam"),
    "telegram-desktop": ("Telegram Desktop", "telegram"),
    "origin-updater": ("Origin Updater", "origin-updater"),
    "origin-uninstaller": ("Origin Uninstaller", "origin-uninstaller"),
}

COMMON_RUNTIMES: Set[str] = {
    "flatpak",
    "snap",
    "python",
    "python3",
    "sh",
    "bash",
    "env",
    "flatpak-spawn",
    "xdg-open",
    "perl",
    "ruby",
    "sudo",
    "pkexec",
}


class DesktopResolver:
    """
    Analisa os arquivos .desktop do sistema e o índice dpkg para mapear
    pacotes instalados em nomes amigáveis, ícones reais e informações de exibição.
    """

    def __init__(self) -> None:
        self._entries_by_key: Dict[str, Dict[str, str]] = {}
        self._gui_packages: Set[str] = set()
        self._desktop_to_package: Dict[str, str] = {}
        self._package_to_desktops: Dict[str, List[str]] = {}

        self._load_dpkg_desktop_mapping()
        self._load_desktop_entries()

    def _load_dpkg_desktop_mapping(self) -> None:
        """Lê rapidamente o índice /var/lib/dpkg/info/*.list para associar .desktop ao pacote exato."""
        for path in glob.glob("/var/lib/dpkg/info/*.list"):
            pkg_raw = os.path.basename(path)[:-5]
            pkg = pkg_raw.split(":")[0] if ":" in pkg_raw else pkg_raw
            try:
                with open(path, "r", encoding="utf-8", errors="ignore") as f:
                    for line in f:
                        line = line.strip()
                        if line.startswith("/usr/share/applications/") and line.endswith(".desktop"):
                            desk_basename = os.path.basename(line).lower()
                            self._desktop_to_package[desk_basename] = pkg
                            if pkg not in self._package_to_desktops:
                                self._package_to_desktops[pkg] = []
                            self._package_to_desktops[pkg].append(line)
                            self._gui_packages.add(pkg.lower())
            except Exception:
                continue

    def _load_desktop_entries(self) -> None:
        search_dirs = [
            "/usr/share/applications",
            "/usr/local/share/applications",
            "/var/lib/flatpak/exports/share/applications",
            os.path.expanduser("~/.local/share/applications"),
            os.path.expanduser("~/.local/share/flatpak/exports/share/applications"),
        ]

        for folder in search_dirs:
            if not os.path.isdir(folder):
                continue
            for path in glob.glob(os.path.join(folder, "*.desktop")):
                try:
                    cp = configparser.ConfigParser(interpolation=None)
                    cp.read(path, encoding="utf-8")
                    if "Desktop Entry" not in cp:
                        continue
                    de = cp["Desktop Entry"]
                    if de.get("NoDisplay", "false").lower() == "true":
                        continue

                    name = (
                        de.get("Name[pt_BR]")
                        or de.get("Name[pt]")
                        or de.get("Name")
                        or ""
                    ).strip()
                    icon = (de.get("Icon") or "").strip()
                    comment = (
                        de.get("Comment[pt_BR]")
                        or de.get("Comment[pt]")
                        or de.get("Comment")
                        or ""
                    ).strip()
                    exec_cmd = (de.get("Exec") or "").strip()
                    categories = (de.get("Categories") or "").strip()

                    entry = {
                        "name": name,
                        "icon": icon,
                        "comment": comment,
                        "exec": exec_cmd,
                        "categories": categories,
                        "path": path,
                    }

                    desk_base = os.path.basename(path).lower()
                    base_id = os.path.splitext(desk_base)[0]
                    self._entries_by_key[base_id] = entry
                    self._entries_by_key[desk_base] = entry
                    self._gui_packages.add(base_id)

                    # Se o dpkg associou este desktop a um pacote específico, armazena
                    if desk_base in self._desktop_to_package:
                        pkg = self._desktop_to_package[desk_base].lower()
                        self._entries_by_key[pkg] = entry
                        self._gui_packages.add(pkg)

                    # Se tiver comando executável, mapeia o primeiro token (se não for runtime genérico)
                    if exec_cmd:
                        exe_base = os.path.basename(exec_cmd.split()[0]).lower()
                        if exe_base not in COMMON_RUNTIMES and exe_base not in self._entries_by_key:
                            self._entries_by_key[exe_base] = entry
                            self._gui_packages.add(exe_base)

                except Exception:
                    continue

    def is_gui_app(self, pkg_name: str) -> bool:
        key = pkg_name.lower()
        if key in COMMON_RUNTIMES:
            return False
        if key in POPULAR_PACKAGES or key in self._gui_packages:
            return True
        if key in self._package_to_desktops:
            return True
        if key.endswith("-stable") and key[:-7] in self._gui_packages:
            return True
        if key.endswith("-desktop") and key[:-8] in self._gui_packages:
            return True
        return False

    def resolve(
        self, pkg_name: str, fallback_name: Optional[str] = None
    ) -> Tuple[str, str, Optional[str], str, Optional[str]]:
        """
        Retorna: (display_name, icon_name, icon_path, comment, desktop_path)
        """
        key = pkg_name.lower()

        if key in POPULAR_PACKAGES:
            name, icon = POPULAR_PACKAGES[key]
            entry = self._entries_by_key.get(key, {})
            comment = entry.get("comment", "")
            desk_path = entry.get("path")
            icon_name, icon_path = self._parse_icon(icon)
            return name, icon_name, icon_path, comment, desk_path

        if key in self._entries_by_key:
            entry = self._entries_by_key[key]
            name = entry["name"] or fallback_name or pkg_name
            icon_name, icon_path = self._parse_icon(entry["icon"])
            return name, icon_name, icon_path, entry["comment"], entry["path"]

        # Tenta sem sufixos
        for suf in ["-stable", "-bin", "-ce"]:
            if key.endswith(suf) and key[:-len(suf)] in self._entries_by_key:
                entry = self._entries_by_key[key[:-len(suf)]]
                name = entry["name"] or fallback_name or pkg_name
                icon_name, icon_path = self._parse_icon(entry["icon"])
                return name, icon_name, icon_path, entry["comment"], entry["path"]

        # Fallback
        name = fallback_name or pkg_name
        return name, "application-x-executable", None, "", None

    def _parse_icon(self, icon: str) -> Tuple[str, Optional[str]]:
        if not icon:
            return "application-x-executable", None
        if os.path.isabs(icon) and os.path.exists(icon):
            return "image-x-generic", icon
        return icon, None
