#!/usr/bin/env python3
"""
Origin Uninstaller - Ponto de entrada da aplicação Desktop GTK4 / Libadwaita.
Desinstalador de aplicativos com limpeza profunda e remoção de dados residuais para Linux.
"""

import os
import sys

# Garante que o diretório do projeto esteja no sys.path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gio, Gtk

from src.ui.window import UninstallerWindow


class UninstallerApplication(Adw.Application):
    """Aplicação Desktop Nativa GTK4 / Libadwaita para remoção profunda de aplicativos."""

    def __init__(self) -> None:
        super().__init__(
            application_id="br.com.chrystian.OriginUninstaller",
            flags=Gio.ApplicationFlags.FLAGS_NONE,
        )
        Gtk.Window.set_default_icon_name("origin-uninstaller")

        # Configura preferência por esquema de cores escuro/moderno Libadwaita
        style_mgr = Adw.StyleManager.get_default()
        style_mgr.set_color_scheme(Adw.ColorScheme.PREFER_DARK)

    def do_activate(self) -> None:
        win = self.props.active_window
        if not win:
            win = UninstallerWindow(self)
        win.present()


def main() -> int:
    # Se chamado com argumento CLI simples para listagem rápida
    if len(sys.argv) > 1 and sys.argv[1] in ("--list", "-l"):
        from src.scanners import SystemScanner

        scanner = SystemScanner()
        print("Varrendo aplicativos instalados...")
        apps = scanner.scan_all()
        print(f"\nEncontrados {len(apps)} aplicativos:")
        for app in apps:
            crit = " [🔒 Protegido]" if app.is_system_critical else ""
            print(f" • [{app.app_type.label}] {app.name} ({app.package_name}) - {app.formatted_installed_size}{crit}")
        return 0

    app = UninstallerApplication()
    return app.run(sys.argv)


if __name__ == "__main__":
    sys.exit(main())
