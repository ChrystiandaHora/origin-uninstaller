import glob
import logging
import os
import re
import shutil
import subprocess
from typing import List, Optional

from ..models import AppType, InstalledApp

logger = logging.getLogger(__name__)


def parse_flatpak_size(size_str: str) -> int:
    """Converte strings como '131,7 MB', '797,2 kB' em bytes inteiros."""
    if not size_str:
        return 0
    clean = size_str.replace("\xa0", " ").replace(",", ".").strip()
    match = re.search(r"([\d\.]+)\s*([a-zA-Z]+)", clean)
    if not match:
        return 0
    try:
        val = float(match.group(1))
        unit = match.group(2).lower()
        if "k" in unit:
            mult = 1024
        elif "m" in unit:
            mult = 1024 * 1024
        elif "g" in unit:
            mult = 1024 * 1024 * 1024
        elif "t" in unit:
            mult = 1024 * 1024 * 1024 * 1024
        else:
            mult = 1
        return int(val * mult)
    except (ValueError, IndexError):
        return 0


class FlatpakScanner:
    """Varre e lista aplicativos Flatpak instalados (escopo sistema e usuário)."""

    def __init__(self) -> None:
        self.flatpak_bin = shutil.which("flatpak")

    def is_available(self) -> bool:
        return self.flatpak_bin is not None

    def scan(self) -> List[InstalledApp]:
        if not self.is_available():
            return []

        apps: List[InstalledApp] = []
        cmd = [
            self.flatpak_bin,
            "list",
            "--app",
            "--columns=application,name,version,origin,installation,size,description",
        ]

        try:
            out = subprocess.check_output(cmd, text=True, errors="replace")
            for line in out.strip().split("\n"):
                if not line or "\t" not in line:
                    continue
                parts = line.split("\t")
                if len(parts) < 2:
                    continue

                app_id = parts[0].strip()
                name = parts[1].strip() or app_id
                version = parts[2].strip() if len(parts) > 2 else ""
                origin = parts[3].strip() if len(parts) > 3 else "flathub"
                scope = parts[4].strip() if len(parts) > 4 else "system"
                size_str = parts[5].strip() if len(parts) > 5 else ""
                description = parts[6].strip() if len(parts) > 6 else ""

                size_bytes = parse_flatpak_size(size_str)
                icon_path = self._find_flatpak_icon(app_id, scope)

                app = InstalledApp(
                    id=app_id,
                    name=name,
                    version=version,
                    summary=description or f"Aplicativo Flatpak ({origin})",
                    app_type=AppType.FLATPAK,
                    package_name=app_id,
                    icon_name=app_id,
                    icon_path=icon_path,
                    installed_size_bytes=size_bytes,
                    is_system_critical=False,
                    flatpak_scope=scope,
                )
                apps.append(app)
        except Exception as e:
            logger.error(f"Erro ao listar flatpaks: {e}")

        apps.sort(key=lambda a: a.name.lower())
        return apps

    def _find_flatpak_icon(self, app_id: str, scope: str) -> Optional[str]:
        """Procura o ícone exportado do Flatpak em disco."""
        search_dirs = [
            f"/var/lib/flatpak/exports/share/icons/hicolor/scalable/apps/{app_id}.svg",
            f"/var/lib/flatpak/exports/share/icons/hicolor/128x128/apps/{app_id}.png",
            f"/var/lib/flatpak/exports/share/icons/hicolor/64x64/apps/{app_id}.png",
            os.path.expanduser(
                f"~/.local/share/flatpak/exports/share/icons/hicolor/scalable/apps/{app_id}.svg"
            ),
            os.path.expanduser(
                f"~/.local/share/flatpak/exports/share/icons/hicolor/128x128/apps/{app_id}.png"
            ),
        ]
        for p in search_dirs:
            if os.path.exists(p):
                return p
        return None
