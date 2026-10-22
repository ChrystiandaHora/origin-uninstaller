import glob
import logging
import os
import shutil
from typing import List, Set

from ..cleaner.residual_finder import get_path_size
from ..cleaner.safety_guard import is_path_safe_to_clean
from ..models import AppType, InstalledApp
from .desktop_resolver import DesktopResolver

logger = logging.getLogger(__name__)


class StandaloneScanner:
    """
    Varre aplicativos instalados manualmente em /opt, ~/.local/bin ou ~/Applications
    que possuem atalhos .desktop e não são gerenciados pelo APT nem pelo Flatpak.
    """

    def __init__(self, resolver: DesktopResolver) -> None:
        self.resolver = resolver

    def scan(self, claimed_package_names: Set[str]) -> List[InstalledApp]:
        apps: List[InstalledApp] = []
        user_apps_dir = os.path.expanduser("~/.local/share/applications")

        # Verifica atalhos locais de usuário em ~/.local/share/applications/*.desktop
        if os.path.isdir(user_apps_dir):
            for desk_path in glob.glob(os.path.join(user_apps_dir, "*.desktop")):
                base_name = os.path.splitext(os.path.basename(desk_path))[0].lower()
                if base_name in claimed_package_names:
                    continue

                dname, icon_name, icon_path, comment, _ = self.resolver.resolve(base_name)
                # Verifica se aponta para algum executável ou AppImage
                entry = self.resolver._entries_by_key.get(base_name, {})
                exec_cmd = entry.get("exec", "")

                app = InstalledApp(
                    id=f"standalone:{base_name}",
                    name=dname,
                    version="Manual",
                    summary=comment or "Aplicativo instalado manualmente",
                    app_type=AppType.STANDALONE,
                    package_name=base_name,
                    icon_name=icon_name,
                    icon_path=icon_path,
                    installed_size_bytes=0,
                    desktop_file=desk_path,
                    exec_cmd=exec_cmd,
                )
                apps.append(app)

        return apps
