import logging
import os
import subprocess
from typing import List, Optional

from ..cleaner.safety_guard import is_package_critical
from ..models import AppType, InstalledApp
from .desktop_resolver import DesktopResolver

logger = logging.getLogger(__name__)


class AptScanner:
    """
    Varre pacotes instalados no sistema via APT/DPKG, priorizando
    aplicativos reais de usuário com interface gráfica (.desktop)
    e identificando pacotes críticos do sistema operacional.
    """

    def __init__(self, resolver: Optional[DesktopResolver] = None) -> None:
        self.resolver = resolver or DesktopResolver()

    def scan(self, gui_only: bool = True) -> List[InstalledApp]:
        """
        Retorna a lista de aplicativos instalados via APT.
        Se gui_only for True, lista aplicativos com interface gráfica (.desktop);
        caso contrário, lista todos os pacotes instalados.
        """
        apps: List[InstalledApp] = []

        try:
            import apt

            cache = apt.Cache()
            for pkg in cache:
                if not pkg.is_installed:
                    continue

                pkg_name = pkg.name
                is_gui = self.resolver.is_gui_app(pkg_name)

                if gui_only and not is_gui:
                    continue

                installed_ver = pkg.installed.version if pkg.installed else ""
                size_bytes = (
                    pkg.installed.installed_size
                    if (pkg.installed and pkg.installed.installed_size)
                    else 0
                )
                summary = pkg.installed.summary if pkg.installed else ""

                dname, icon_name, icon_path, desk_comment, desk_path = self.resolver.resolve(
                    pkg_name, fallback_name=summary or pkg_name
                )

                critical_reason = is_package_critical(pkg_name)
                is_critical = critical_reason is not None

                app = InstalledApp(
                    id=pkg_name,
                    name=dname,
                    version=installed_ver,
                    summary=desk_comment or summary,
                    app_type=AppType.APT,
                    package_name=pkg_name,
                    icon_name=icon_name,
                    icon_path=icon_path,
                    installed_size_bytes=size_bytes,
                    is_system_critical=is_critical,
                    critical_reason=critical_reason,
                    desktop_file=desk_path,
                )
                apps.append(app)

        except Exception as e:
            logger.warning(f"Falha ao usar python3-apt ({e}), tentando dpkg-query...")
            apps = self._scan_dpkg_query(gui_only)

        # Ordenação: aplicativos normais primeiro, depois protegidos; por ordem alfabética de nome
        apps.sort(key=lambda a: (a.is_system_critical, a.name.lower()))
        return apps

    def _scan_dpkg_query(self, gui_only: bool = True) -> List[InstalledApp]:
        """Fallback via comando dpkg-query caso python3-apt não esteja disponível."""
        apps: List[InstalledApp] = []
        cmd = [
            "dpkg-query",
            "-W",
            "-f=${Package}\t${Version}\t${Installed-Size}\t${binary:Summary}\n",
        ]
        try:
            out = subprocess.check_output(cmd, text=True, errors="replace")
            for line in out.strip().split("\n"):
                if not line or "\t" not in line:
                    continue
                parts = line.split("\t")
                pkg_name = parts[0]
                version = parts[1] if len(parts) > 1 else ""
                # Installed-Size no dpkg-query vem em KiB
                try:
                    size_kb = int(parts[2]) if len(parts) > 2 and parts[2] else 0
                    size_bytes = size_kb * 1024
                except ValueError:
                    size_bytes = 0
                summary = parts[3] if len(parts) > 3 else ""

                is_gui = self.resolver.is_gui_app(pkg_name)
                if gui_only and not is_gui:
                    continue

                dname, icon_name, icon_path, desk_comment, desk_path = self.resolver.resolve(
                    pkg_name, fallback_name=summary or pkg_name
                )
                critical_reason = is_package_critical(pkg_name)

                app = InstalledApp(
                    id=pkg_name,
                    name=dname,
                    version=version,
                    summary=desk_comment or summary,
                    app_type=AppType.APT,
                    package_name=pkg_name,
                    icon_name=icon_name,
                    icon_path=icon_path,
                    installed_size_bytes=size_bytes,
                    is_system_critical=critical_reason is not None,
                    critical_reason=critical_reason,
                    desktop_file=desk_path,
                )
                apps.append(app)
        except Exception as err:
            logger.error(f"Erro no dpkg-query: {err}")

        return apps
