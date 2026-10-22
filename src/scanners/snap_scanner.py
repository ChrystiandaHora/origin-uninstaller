import logging
import shutil
import subprocess
from typing import List

from ..models import AppType, InstalledApp

logger = logging.getLogger(__name__)


class SnapScanner:
    """Varre e lista pacotes Snap instalados caso o snapd esteja disponível."""

    def __init__(self) -> None:
        self.snap_bin = shutil.which("snap")

    def is_available(self) -> bool:
        return self.snap_bin is not None

    def scan(self) -> List[InstalledApp]:
        if not self.is_available():
            return []

        apps: List[InstalledApp] = []
        try:
            out = subprocess.check_output(
                [self.snap_bin, "list"], text=True, errors="replace"
            )
            lines = out.strip().split("\n")
            if len(lines) <= 1:
                return []

            # Cabeçalho típico: Name Version Rev Tracking Publisher Notes
            for line in lines[1:]:
                parts = line.split()
                if not parts:
                    continue
                name = parts[0]
                version = parts[1] if len(parts) > 1 else ""
                publisher = parts[4] if len(parts) > 4 else ""

                # Ignora bases de sistema e runtimes como bare, core, core20, snapd
                if name in {"bare", "core", "core18", "core20", "core22", "core24", "snapd"}:
                    continue

                app = InstalledApp(
                    id=f"snap:{name}",
                    name=name.capitalize(),
                    version=version,
                    summary=f"Pacote Snap ({publisher})",
                    app_type=AppType.SNAP,
                    package_name=name,
                    icon_name="application-x-executable",
                    installed_size_bytes=0,
                    is_system_critical=False,
                )
                apps.append(app)
        except Exception as e:
            logger.debug(f"Snap não disponível ou erro ao executar: {e}")

        return apps
