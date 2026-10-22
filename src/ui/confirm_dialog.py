import os
from typing import Callable, List

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gtk, Pango

from ..cleaner.residual_finder import ResidualFinder
from ..models import AppType, InstalledApp, ResidualItem, format_size


class ConfirmRemovalDialog(Adw.Window):
    """
    Janela modal detalhada que exibe o resumo da desinstalação e lista todas
    as pastas e arquivos residuais encontrados com checkboxes para escolha do usuário,
    seguida por uma confirmação final de segurança antes da execução.
    """

    def __init__(
        self,
        parent_window: Gtk.Window,
        app: InstalledApp,
        on_confirmed: Callable[[InstalledApp, List[ResidualItem]], None],
    ) -> None:
        super().__init__(transient_for=parent_window, modal=True)
        self.app = app
        self.on_confirmed = on_confirmed

        self.set_title("Confirmar Desinstalação")
        self.set_default_size(560, 620)

        # Busca os resíduos do aplicativo
        finder = ResidualFinder()
        self.residuals: List[ResidualItem] = finder.find_residuals(app)

        self._build_ui()

    def _build_ui(self) -> None:
        toolbar_view = Adw.ToolbarView()
        self.set_content(toolbar_view)

        # Header Bar
        header = Adw.HeaderBar()
        header.set_show_end_title_buttons(True)
        toolbar_view.add_top_bar(header)

        # Conteúdo com Scroll
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_vexpand(True)
        scrolled.set_hexpand(True)
        toolbar_view.set_content(scrolled)

        clamp = Adw.Clamp()
        clamp.set_maximum_size(560)
        scrolled.set_child(clamp)

        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        main_box.set_margin_top(20)
        main_box.set_margin_bottom(20)
        main_box.set_margin_start(20)
        main_box.set_margin_end(20)
        clamp.set_child(main_box)

        # --- Cabeçalho do App ---
        app_header_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=14)
        app_header_box.add_css_class("card")
        app_header_box.set_margin_bottom(6)
        app_header_box.set_size_request(-1, 80)

        # Ícone
        icon_widget = self._create_app_icon()
        icon_widget.set_margin_start(16)
        app_header_box.append(icon_widget)

        # Informações de texto
        text_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        text_box.set_valign(Gtk.Align.CENTER)
        text_box.set_hexpand(True)

        title_lbl = Gtk.Label(label=self.app.name)
        title_lbl.set_halign(Gtk.Align.START)
        title_lbl.add_css_class("title-2")
        text_box.append(title_lbl)

        sub_lbl = Gtk.Label(
            label=f"{self.app.package_name} • {self.app.app_type.label}"
            + (f" • v{self.app.version}" if self.app.version else "")
        )
        sub_lbl.set_halign(Gtk.Align.START)
        sub_lbl.add_css_class("dim-label")
        text_box.append(sub_lbl)

        app_header_box.append(text_box)
        main_box.append(app_header_box)

        # --- Card de Espaço Liberado Total ---
        self.summary_card = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        self.summary_card.add_css_class("summary-banner")
        self.summary_card.set_margin_bottom(4)

        summary_icon = Gtk.Image.new_from_icon_name("drive-harddisk-symbolic")
        summary_icon.set_pixel_size(24)
        self.summary_card.append(summary_icon)

        self.summary_lbl = Gtk.Label()
        self.summary_lbl.set_halign(Gtk.Align.START)
        self.summary_lbl.set_hexpand(True)
        self.summary_card.append(self.summary_lbl)
        main_box.append(self.summary_card)

        # --- Grupo 1: Pacote Principal ---
        group_pkg = Adw.PreferencesGroup()
        group_pkg.set_title("1. Pacote do Aplicativo")
        group_pkg.set_description("Será removido e purgado do sistema operacional:")

        row_pkg = Adw.ActionRow()
        row_pkg.set_title(self.app.name)

        if self.app.app_type == AppType.APT:
            row_pkg.set_subtitle(f"Comando: apt-get purge --autoremove -y {self.app.package_name}")
        elif self.app.app_type == AppType.FLATPAK:
            row_pkg.set_subtitle(f"Comando: flatpak uninstall --delete-data -y {self.app.id}")
        else:
            row_pkg.set_subtitle(f"Pacote: {self.app.package_name}")

        if self.app.installed_size_bytes > 0:
            sz_badge = Gtk.Label(label=self.app.formatted_installed_size)
            sz_badge.add_css_class("badge")
            sz_badge.add_css_class("badge-size")
            row_pkg.add_suffix(sz_badge)

        group_pkg.add(row_pkg)
        main_box.append(group_pkg)

        # --- Grupo 2: Pastas e Resíduos Encontrados ---
        group_res = Adw.PreferencesGroup()
        group_res.set_title(f"2. Pastas e Arquivos Residuais ({len(self.residuals)} encontrados)")
        group_res.set_description(
            "Selecione quais diretórios de configurações, caches e dados locais devem ser excluídos definitivamente:"
        )

        if not self.residuals:
            row_empty = Adw.ActionRow()
            row_empty.set_title("Nenhum dado residual adicional encontrado")
            row_empty.set_subtitle("As configurações padrão já foram limpas ou não foram criadas.")
            row_empty.set_icon_name("object-select-symbolic")
            group_res.add(row_empty)
        else:
            self.checkboxes: List[Gtk.CheckButton] = []
            for r in self.residuals:
                row_r = Adw.ActionRow()
                row_r.set_title(r.category)
                row_r.set_subtitle(r.path)
                row_r.set_subtitle_lines(2)

                # Checkbox
                chk = Gtk.CheckButton()
                chk.set_active(r.selected)
                chk.set_valign(Gtk.Align.CENTER)
                chk.connect("toggled", self._on_checkbox_toggled, r)
                self.checkboxes.append(chk)
                row_r.add_prefix(chk)

                # Suffix de tamanho
                if r.size_bytes > 0:
                    badge = Gtk.Label(label=r.formatted_size)
                    badge.add_css_class("badge")
                    badge.add_css_class("badge-residual")
                    row_r.add_suffix(badge)

                if r.requires_root:
                    root_icon = Gtk.Image.new_from_icon_name("dialog-password-symbolic")
                    root_icon.set_tooltip_text("Diretório de sistema (requer permissão de root)")
                    row_r.add_suffix(root_icon)

                group_res.add(row_r)

        main_box.append(group_res)

        # --- Barra Inferior de Ações ---
        bottom_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        bottom_box.set_halign(Gtk.Align.END)
        bottom_box.set_margin_top(10)

        btn_cancel = Gtk.Button(label="Cancelar")
        btn_cancel.connect("clicked", lambda _: self.close())
        bottom_box.append(btn_cancel)

        btn_proceed = Gtk.Button(label="Prosseguir para Confirmação Final →")
        btn_proceed.add_css_class("destructive-action")
        btn_proceed.connect("clicked", self._on_proceed_clicked)
        bottom_box.append(btn_proceed)

        main_box.append(bottom_box)
        self._update_summary_label()

    def _create_app_icon(self) -> Gtk.Widget:
        if self.app.icon_path and os.path.exists(self.app.icon_path):
            img = Gtk.Image.new_from_file(self.app.icon_path)
            img.set_pixel_size(48)
            return img

        icon_name = self.app.icon_name or "application-x-executable"
        img = Gtk.Image.new_from_icon_name(icon_name)
        img.set_pixel_size(48)
        return img

    def _on_checkbox_toggled(self, chk: Gtk.CheckButton, residual: ResidualItem) -> None:
        residual.selected = chk.get_active()
        self._update_summary_label()

    def _update_summary_label(self) -> None:
        selected_res = [r for r in self.residuals if r.selected]
        res_bytes = sum(r.size_bytes for r in selected_res)
        total_bytes = self.app.installed_size_bytes + res_bytes

        text = (
            f"<b>Espaço total a ser liberado: {format_size(total_bytes)}</b> "
            f"({self.app.formatted_installed_size} pacote + {format_size(res_bytes)} resíduos)"
        )
        self.summary_lbl.set_markup(text)

    def _on_proceed_clicked(self, _btn: Gtk.Button) -> None:
        """Exibe a segunda confirmação reforçada de segurança antes de remover."""
        selected_res = [r for r in self.residuals if r.selected]
        res_count = len(selected_res)
        res_bytes = sum(r.size_bytes for r in selected_res)
        total_bytes = self.app.installed_size_bytes + res_bytes

        alert = Adw.AlertDialog(
            heading="⚠️ Confirmar Remoção Definitiva?",
            body=(
                f"Você está prestes a desinstalar completamente o aplicativo '{self.app.name}'.\n\n"
                f"• Pacote: {self.app.package_name}\n"
                f"• Pastas de dados selecionadas: {res_count} diretórios ({format_size(res_bytes)})\n"
                f"• Espaço total a liberar: {format_size(total_bytes)}\n\n"
                f"Esta ação é permanente e não poderá ser desfeita. Todos os arquivos marcados "
                f"serão excluídos do seu computador. Deseja realmente continuar?"
            ),
        )
        alert.add_response("cancel", "Cancelar")
        alert.add_response("confirm", "Sim, Desinstalar e Limpar Tudo")
        alert.set_response_appearance("confirm", Adw.ResponseAppearance.DESTRUCTIVE)
        alert.set_default_response("cancel")

        alert.connect("response", self._on_alert_response, selected_res)
        alert.present(self)

    def _on_alert_response(
        self,
        alert: Adw.AlertDialog,
        response: str,
        selected_res: List[ResidualItem],
    ) -> None:
        if response == "confirm":
            self.close()
            self.on_confirmed(self.app, selected_res)
