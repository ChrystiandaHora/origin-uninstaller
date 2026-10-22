import logging
from typing import List, Set

from ..models import InstalledApp
from .apt_scanner import AptScanner
from .desktop_resolver import DesktopResolver
from .flatpak_scanner import FlatpakScanner
from .snap_scanner import SnapScanner
from .standalone_scanner import StandaloneScanner

logger = logging.getLogger(__name__)


class SystemScanner:
    """
    Coordena a varredura unificada de todas as fontes de aplicativos
    (APT/DEB, Flatpak, Snap e Standalone/Manual).
    """

    def __init__(self) -> None:
        self.resolver = DesktopResolver()
        self.apt_scanner = AptScanner(self.resolver)
        self.flatpak_scanner = FlatpakScanner()
        self.snap_scanner = SnapScanner()
        self.standalone_scanner = StandaloneScanner(self.resolver)

    def scan_all(self, gui_only: bool = True) -> List[InstalledApp]:
        all_apps: List[InstalledApp] = []
        claimed_keys: Set[str] = set()

        # 1. Varre Flatpaks
        try:
            flatpaks = self.flatpak_scanner.scan()
            all_apps.extend(flatpaks)
            for f in flatpaks:
                claimed_keys.add(f.id.lower())
                claimed_keys.add(f.name.lower())
        except Exception as e:
            logger.error(f"Erro ao varrer Flatpaks: {e}")

        # 2. Varre APT/DEB
        try:
            apt_apps = self.apt_scanner.scan(gui_only=gui_only)
            all_apps.extend(apt_apps)
            for a in apt_apps:
                claimed_keys.add(a.package_name.lower())
                claimed_keys.add(a.name.lower())
        except Exception as e:
            logger.error(f"Erro ao varrer APT: {e}")

        # 3. Varre Snaps
        try:
            snaps = self.snap_scanner.scan()
            all_apps.extend(snaps)
            for s in snaps:
                claimed_keys.add(s.package_name.lower())
        except Exception as e:
            logger.error(f"Erro ao varrer Snaps: {e}")

        # 4. Varre Standalones locais
        try:
            standalones = self.standalone_scanner.scan(claimed_keys)
            all_apps.extend(standalones)
        except Exception as e:
            logger.error(f"Erro ao varrer Standalones: {e}")

        # Ordena: não-críticos primeiro, depois por ordem alfabética do nome
        all_apps.sort(key=lambda a: (a.is_system_critical, a.name.lower()))
        return all_apps
