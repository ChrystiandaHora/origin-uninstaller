import os
from typing import Callable, Optional

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gtk, Pango

from ..models import AppType, InstalledApp


class AppRow(Adw.ActionRow):
    """Linha personalizada para exibição de um aplicativo instalado."""

    def __init__(
        self,
        app: InstalledApp,
        on_uninstall_clicked: Callable[[InstalledApp], None],
    ) -> None:
        super().__init__()
        self.app = app
        self.on_uninstall_clicked = on_uninstall_clicked

        self.set_title(app.name)
        self.set_title_lines(1)

        # Subtítulo com ID do pacote e versão
        sub_parts = [app.package_name]
        if app.version:
            sub_parts.append(f"v{app.version}")
        elif app.summary:
            sub_parts.append(app.summary[:50] + ("..." if len(app.summary) > 50 else ""))

        self.set_subtitle(" • ".join(sub_parts))
        self.set_subtitle_lines(1)
        self.add_css_class("app-row")

        # Ícone do aplicativo
        icon_widget = self._create_icon_widget()
        self.add_prefix(icon_widget)

        # Container de badges e botão de ação
        suffix_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        suffix_box.set_valign(Gtk.Align.CENTER)

        # 1. Badge do Tipo (APT, Flatpak, Snap, Manual)
        type_badge = Gtk.Label(label=app.app_type.label)
        type_badge.add_css_class("badge")
        type_badge.add_css_class(app.app_type.badge_css)
        suffix_box.append(type_badge)

        # 2. Badge de Tamanho Instalado
        if app.installed_size_bytes > 0:
            size_badge = Gtk.Label(label=app.formatted_installed_size)
            size_badge.add_css_class("badge")
            size_badge.add_css_class("badge-size")
            suffix_box.append(size_badge)

        # 3. Botão de Ação (Desinstalar ou Protegido)
        if app.is_system_critical:
            btn_lock = Gtk.Button()
            btn_lock.set_icon_name("object-locked-symbolic")
            btn_lock.set_tooltip_text(
                f"Bloqueado para proteção do sistema: {app.critical_reason or 'Pacote essencial'}"
            )
            btn_lock.set_sensitive(False)
            btn_lock.add_css_class("flat")
            suffix_box.append(btn_lock)
        else:
            btn_uninstall = Gtk.Button()
            btn_uninstall.set_icon_name("user-trash-symbolic")
            btn_uninstall.set_label("Desinstalar")
            btn_uninstall.set_tooltip_text(f"Desinstalar e limpar todos os dados de {app.name}")
            btn_uninstall.add_css_class("destructive-action")
            btn_uninstall.connect("clicked", self._on_btn_clicked)
            suffix_box.append(btn_uninstall)

        self.add_suffix(suffix_box)

    def _create_icon_widget(self) -> Gtk.Widget:
        if self.app.icon_path and os.path.exists(self.app.icon_path):
            img = Gtk.Image.new_from_file(self.app.icon_path)
            img.set_pixel_size(36)
            return img

        icon_name = self.app.icon_name or "application-x-executable"
        img = Gtk.Image.new_from_icon_name(icon_name)
        img.set_pixel_size(36)
        return img

    def _on_btn_clicked(self, _btn: Gtk.Button) -> None:
        self.on_uninstall_clicked(self.app)
