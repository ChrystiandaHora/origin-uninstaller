from dataclasses import dataclass, field
from enum import Enum
import os
from typing import List, Optional


class AppType(str, Enum):
    APT = "apt"
    FLATPAK = "flatpak"
    SNAP = "snap"
    STANDALONE = "standalone"

    @property
    def label(self) -> str:
        if self == AppType.APT:
            return "APT / DEB"
        elif self == AppType.FLATPAK:
            return "Flatpak"
        elif self == AppType.SNAP:
            return "Snap"
        elif self == AppType.STANDALONE:
            return "Manual / Opt"
        return self.value.upper()

    @property
    def badge_css(self) -> str:
        if self == AppType.APT:
            return "badge-apt"
        elif self == AppType.FLATPAK:
            return "badge-flatpak"
        elif self == AppType.SNAP:
            return "badge-snap"
        return "badge-standalone"


def format_size(size_bytes: float) -> str:
    """Formata bytes em unidades legíveis para humanos (B, KB, MB, GB)."""
    if size_bytes <= 0:
        return "0 B"
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if size_bytes < 1024.0 or unit == "TB":
            return f"{size_bytes:.1f} {unit}" if unit != "B" else f"{int(size_bytes)} B"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} GB"


@dataclass
class ResidualItem:
    """Representa um diretório ou arquivo residual a ser limpo."""

    path: str
    size_bytes: int = 0
    category: str = "Dados Locais"
    selected: bool = True
    requires_root: bool = False
    is_directory: bool = True
    exists: bool = True

    @property
    def formatted_size(self) -> str:
        return format_size(self.size_bytes)


@dataclass
class InstalledApp:
    """Representa um aplicativo instalado detectado no sistema operacional."""

    id: str
    name: str
    version: str = ""
    summary: str = ""
    app_type: AppType = AppType.APT
    package_name: str = ""
    icon_name: str = "application-x-executable"
    icon_path: Optional[str] = None
    installed_size_bytes: int = 0
    is_system_critical: bool = False
    critical_reason: Optional[str] = None
    desktop_file: Optional[str] = None
    exec_cmd: Optional[str] = None
    flatpak_scope: Optional[str] = None  # "system" ou "user"
    residuals: List[ResidualItem] = field(default_factory=list)

    @property
    def total_reclaimable_bytes(self) -> int:
        residuals_size = sum(r.size_bytes for r in self.residuals if r.selected)
        return self.installed_size_bytes + residuals_size

    @property
    def formatted_installed_size(self) -> str:
        return format_size(self.installed_size_bytes)

    @property
    def formatted_total_size(self) -> str:
        return format_size(self.total_reclaimable_bytes)
