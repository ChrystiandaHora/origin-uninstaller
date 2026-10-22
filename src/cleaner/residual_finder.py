import glob
import os
import shutil
from typing import Dict, List, Set

from ..models import InstalledApp, ResidualItem
from .safety_guard import is_path_safe_to_clean


def get_path_size(path: str) -> int:
    """Calcula o tamanho total em bytes de um arquivo ou diretório de forma recursiva."""
    try:
        if os.path.islink(path):
            return 0
        if os.path.isfile(path):
            return os.path.getsize(path)
        total = 0
        for dirpath, _, filenames in os.walk(path, followlinks=False):
            for f in filenames:
                fp = os.path.join(dirpath, f)
                try:
                    if not os.path.islink(fp):
                        total += os.path.getsize(fp)
                except (OSError, FileNotFoundError):
                    pass
        return total
    except (OSError, FileNotFoundError):
        return 0


class ResidualFinder:
    """
    Localizador inteligente de arquivos, diretórios de configuração,
    cache, sandboxes e dados residuais deixados por aplicativos.
    """

    def __init__(self) -> None:
        self.home = os.path.expanduser("~")
        self.config_dir = os.path.join(self.home, ".config")
        self.cache_dir = os.path.join(self.home, ".cache")
        self.local_share = os.path.join(self.home, ".local", "share")
        self.local_state = os.path.join(self.home, ".local", "state")
        self.flatpak_var = os.path.join(self.home, ".var", "app")
        self.snap_dir = os.path.join(self.home, "snap")

    def _generate_slugs(self, app: InstalledApp) -> Set[str]:
        """Gera uma lista de identificadores/slugs possíveis para o aplicativo."""
        slugs: Set[str] = set()

        def add_clean(val: str | None) -> None:
            if not val:
                return
            clean = val.strip()
            if clean and len(clean) >= 2:
                slugs.add(clean.lower())
                slugs.add(clean)

        add_clean(app.package_name)
        add_clean(app.id)

        # Se package_name termina com '-stable', '-bin', '-ce', adiciona sem o sufixo
        for suffix in ["-stable", "-bin", "-ce", "-desktop", "-client"]:
            if app.package_name.lower().endswith(suffix):
                add_clean(app.package_name[:-len(suffix)])

        # Nome de exibição simplificado
        if app.name:
            simple_name = app.name.lower().replace(" ", "").replace("-", "")
            add_clean(simple_name)
            # Apenas a primeira palavra do nome se tiver mais de 3 chars
            first_word = app.name.split()[0].lower()
            if len(first_word) >= 3 and first_word not in {"the", "gnu"}:
                add_clean(first_word)

        # Comando executável
        if app.exec_cmd:
            exe = os.path.basename(app.exec_cmd.split()[0]).lower()
            if len(exe) >= 2 and exe not in {"python", "python3", "sh", "bash"}:
                add_clean(exe)

        # Mapeamentos específicos conhecidos
        known_aliases: Dict[str, List[str]] = {
            "code": ["Code", "vscode", "Visual Studio Code"],
            "google-chrome-stable": ["google-chrome", "chrome"],
            "google-chrome": ["chrome"],
            "discord": ["discord", "discordcanary"],
            "spotify-client": ["spotify", "Spotify"],
            "spotify": ["spotify", "Spotify"],
            "dbeaver-ce": ["dbeaver", "dbeaver4", ".dbeaver4", ".dbeaver-drivers"],
            "dbeaver": ["dbeaver4", ".dbeaver4"],
            "rustdesk": ["rustdesk", "RustDesk"],
            "anydesk": ["anydesk", ".anydesk"],
            "docker-desktop": ["docker", "docker-desktop", ".docker"],
            "obs-studio": ["obs-studio"],
        }

        for key, aliases in known_aliases.items():
            if key in app.package_name.lower() or key in app.id.lower():
                for a in aliases:
                    add_clean(a)

        return slugs

    def find_residuals(self, app: InstalledApp) -> List[ResidualItem]:
        """Varre o sistema procurando pastas e arquivos associados ao app."""
        slugs = self._generate_slugs(app)
        seen_paths: Set[str] = set()
        items: List[ResidualItem] = []

        def add_item(path: str, category: str, requires_root: bool = False) -> None:
            if not os.path.exists(path):
                return
            real = os.path.realpath(path)
            if real in seen_paths:
                return
            if not is_path_safe_to_clean(real):
                return

            size = get_path_size(real)
            seen_paths.add(real)
            items.append(
                ResidualItem(
                    path=real,
                    size_bytes=size,
                    category=category,
                    selected=True,
                    requires_root=requires_root,
                    is_directory=os.path.isdir(real),
                    exists=True,
                )
            )

        # 1. Sandbox Flatpak dedicada
        if app.app_type.value == "flatpak" or app.id.count(".") >= 2:
            flatpak_app_dir = os.path.join(self.flatpak_var, app.id)
            if os.path.isdir(flatpak_app_dir):
                add_item(flatpak_app_dir, "Sandbox e Dados do Flatpak")

        # 2. Varredura nas pastas do usuário (~/.config, ~/.cache, ~/.local/share, ~/.local/state)
        for slug in slugs:
            # ~/.config/<slug>
            cfg_path = os.path.join(self.config_dir, slug)
            add_item(cfg_path, "Configurações do Usuário (~/.config)")

            # ~/.cache/<slug>
            cache_path = os.path.join(self.cache_dir, slug)
            add_item(cache_path, "Cache e Temporários (~/.cache)")

            # ~/.local/share/<slug>
            data_path = os.path.join(self.local_share, slug)
            add_item(data_path, "Dados Locais (~/.local/share)")

            # ~/.local/state/<slug>
            state_path = os.path.join(self.local_state, slug)
            add_item(state_path, "Estado do Aplicativo (~/.local/state)")

            # Dotfiles na raiz da home (ex: ~/.dbeaver4, ~/.anydesk, ~/.zoom)
            dot_path = os.path.join(self.home, f".{slug}")
            # Verificação extra para não pegar dotfiles de sistema essenciais
            if os.path.exists(dot_path) and slug not in {"bashrc", "profile", "local", "config", "cache", "gnupg", "ssh"}:
                add_item(dot_path, "Dados e Diretório Legado (~/.)")

            # Sandbox Snap (~/snap/<slug>)
            snap_path = os.path.join(self.snap_dir, slug)
            add_item(snap_path, "Sandbox e Dados do Snap")

        # 3. Atalhos .desktop customizados na home do usuário
        user_apps_dir = os.path.join(self.local_share, "applications")
        if os.path.isdir(user_apps_dir):
            for slug in slugs:
                matches = glob.glob(os.path.join(user_apps_dir, f"*{slug}*.desktop"))
                for m in matches:
                    add_item(m, "Atalho de Menu do Usuário (.desktop)")

        # 4. Diretórios residuais de sistema (requerem permissão de root)
        # Apenas se o pacote for APT ou Standalone
        if app.app_type.value in ("apt", "standalone"):
            for slug in slugs:
                # /etc/<slug>
                etc_path = f"/etc/{slug}"
                if os.path.exists(etc_path):
                    add_item(etc_path, "Configurações Globais do Sistema (/etc)", requires_root=True)

                # /var/log/<slug>
                log_path = f"/var/log/{slug}"
                if os.path.exists(log_path):
                    add_item(log_path, "Arquivos de Log do Sistema (/var/log)", requires_root=True)

                # /var/lib/<slug>
                var_lib_path = f"/var/lib/{slug}"
                if os.path.exists(var_lib_path):
                    add_item(var_lib_path, "Banco de Dados/Dados do Sistema (/var/lib)", requires_root=True)

                # /opt/<slug>
                opt_path = f"/opt/{slug}"
                if os.path.exists(opt_path):
                    add_item(opt_path, "Diretório de Instalação (/opt)", requires_root=True)

        # Ordena resíduos por tamanho decrescente
        items.sort(key=lambda x: x.size_bytes, reverse=True)
        return items
