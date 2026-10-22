import os
import threading
from typing import Dict, List, Optional

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gdk, GLib, Gtk, Pango

from ..execution.uninstaller_engine import UninstallerEngine
from ..models import AppType, InstalledApp, ResidualItem, format_size
from ..scanners import SystemScanner
from .app_row import AppRow
from .confirm_dialog import ConfirmRemovalDialog
from .log_view import LogView

ASSETS_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "assets")
)
APP_ICON_SVG = os.path.join(ASSETS_DIR, "origin-uninstaller.svg")

APP_CSS = """
.summary-card {
    background-color: alpha(@card_bg_color, 0.95);
    border: 1px solid alpha(@borders, 0.6);
    border-radius: 12px;
    padding: 12px 16px;
    transition: all 150ms ease;
}
.summary-card:hover {
    background-color: alpha(@accent_bg_color, 0.14);
    border-color: alpha(@accent_bg_color, 0.5);
}
.summary-card-active {
    background-color: alpha(@accent_bg_color, 0.22);
    border: 1.5px solid @accent_bg_color;
}
.summary-count {
    font-size: 20px;
    font-weight: 800;
}
.summary-title {
    font-size: 11px;
    opacity: 0.85;
    font-weight: 600;
}
.summary-banner {
    background-color: alpha(@accent_bg_color, 0.12);
    border: 1px solid alpha(@accent_bg_color, 0.35);
    border-radius: 10px;
    padding: 10px 14px;
}
.app-row {
    padding: 8px 12px;
    border-bottom: 1px solid alpha(@borders, 0.3);
}
.badge {
    border-radius: 6px;
    padding: 2px 7px;
    font-size: 11px;
    font-weight: 700;
}
.badge-apt {
    background-color: alpha(#dc2626, 0.18);
    color: #f87171;
    border: 1px solid alpha(#dc2626, 0.4);
}
.badge-flatpak {
    background-color: alpha(#2563eb, 0.18);
    color: #60a5fa;
    border: 1px solid alpha(#2563eb, 0.4);
}
.badge-snap {
    background-color: alpha(#ea580c, 0.18);
    color: #fb923c;
    border: 1px solid alpha(#ea580c, 0.4);
}
.badge-standalone {
    background-color: alpha(#7c3aed, 0.18);
    color: #a78bfa;
    border: 1px solid alpha(#7c3aed, 0.4);
}
.badge-size {
    background-color: alpha(@card_bg_color, 0.85);
    border: 1px solid alpha(@borders, 0.5);
    opacity: 0.9;
}
.badge-residual {
    background-color: alpha(#10b981, 0.15);
    color: #34d399;
    border: 1px solid alpha(#10b981, 0.35);
}
.terminal-scrolled {
    border-radius: 10px;
    border: 1px solid alpha(#45475a, 0.6);
}
.terminal-view {
    background-color: #11111b;
    color: #cdd6f4;
    font-family: monospace;
    font-size: 12px;
}
"""


class UninstallerWindow(Adw.ApplicationWindow):
    """Janela principal do Origin Uninstaller."""

    def __init__(self, app: Adw.Application) -> None:
        super().__init__(application=app)
        self.set_title("Origin Uninstaller")
        self.set_default_size(920, 680)

        self._load_css()

        self.scanner = SystemScanner()
        self.engine = UninstallerEngine()
        self.all_apps: List[InstalledApp] = []
        self.current_filter_category = "all"
        self.search_query = ""

        self._build_ui()
        self._start_scan()

    def _load_css(self) -> None:
        provider = Gtk.CssProvider()
        provider.load_from_string(APP_CSS)
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(),
            provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
        )

    def _build_ui(self) -> None:
        # Layout principal com ToolbarView
        self.toolbar_view = Adw.ToolbarView()
        self.set_content(self.toolbar_view)

        # 1. HeaderBar moderno
        header = Adw.HeaderBar()
        self.toolbar_view.add_top_bar(header)

        # Botão Recarregar / Varredura
        btn_refresh = Gtk.Button()
        btn_refresh.set_icon_name("view-refresh-symbolic")
        btn_refresh.set_tooltip_text("Recarregar e varrer aplicativos instalados")
        btn_refresh.connect("clicked", lambda _: self._start_scan())
        header.pack_start(btn_refresh)

        # Barra de Pesquisa no topo
        self.search_entry = Gtk.SearchEntry()
        self.search_entry.set_placeholder_text("Pesquisar aplicativo ou pacote...")
        self.search_entry.set_size_request(320, -1)
        self.search_entry.connect("search-changed", self._on_search_changed)
        header.set_title_widget(self.search_entry)

        # Botão Sobre
        btn_about = Gtk.Button()
        btn_about.set_icon_name("help-about-symbolic")
        btn_about.set_tooltip_text("Sobre o Origin Uninstaller")
        btn_about.connect("clicked", self._show_about_dialog)
        header.pack_end(btn_about)

        # 2. Main Stack (Lista de Apps vs Log de Execução)
        self.main_stack = Gtk.Stack()
        self.main_stack.set_transition_type(Gtk.StackTransitionType.SLIDE_LEFT_RIGHT)
        self.toolbar_view.set_content(self.main_stack)

        # Página 1: Lista e Filtros
        self.list_container = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        self.list_container.set_margin_top(12)
        self.list_container.set_margin_bottom(12)
        self.list_container.set_margin_start(16)
        self.list_container.set_margin_end(16)

        # Cards de Resumo e Filtro Rápido
        self.cards_box = self._build_summary_cards()
        self.list_container.append(self.cards_box)

        # Stack interno da lista (Carregando vs Lista vs Vazio)
        self.list_stack = Gtk.Stack()
        self.list_stack.set_vexpand(True)
        self.list_stack.set_hexpand(True)

        # Estado 1: Carregando
        loading_page = Adw.StatusPage()
        loading_page.set_icon_name("system-search-symbolic")
        loading_page.set_title("Varrendo o sistema...")
        loading_page.set_description("Localizando aplicativos APT, Flatpak e pacotes instalados.")
        spinner = Gtk.Spinner()
        spinner.set_spinning(True)
        spinner.set_pixel_size(36)
        spinner.set_halign(Gtk.Align.CENTER)
        spinner.set_margin_top(12)
        loading_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        loading_box.append(loading_page)
        loading_box.append(spinner)
        self.list_stack.add_named(loading_box, "loading")

        # Estado 2: Lista Scrolled com ListBox
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_vexpand(True)
        scrolled.set_hexpand(True)

        self.list_box = Gtk.ListBox()
        self.list_box.set_selection_mode(Gtk.SelectionMode.NONE)
        self.list_box.add_css_class("boxed-list")
        self.list_box.set_filter_func(self._filter_app_row)
        scrolled.set_child(self.list_box)
        self.list_stack.add_named(scrolled, "list")

        # Estado 3: Vazio
        self.empty_page = Adw.StatusPage()
        self.empty_page.set_icon_name("edit-find-symbolic")
        self.empty_page.set_title("Nenhum aplicativo encontrado")
        self.empty_page.set_description("Tente ajustar os termos da sua pesquisa ou o filtro de categoria.")
        self.list_stack.add_named(self.empty_page, "empty")

        self.list_container.append(self.list_stack)
        self.main_stack.add_named(self.list_container, "list_view")

        # Página 2: Log em Tempo Real
        self.log_view = LogView(on_back_clicked=self._on_back_to_list)
        self.main_stack.add_named(self.log_view, "log_view")

    def _build_summary_cards(self) -> Gtk.Box:
        cards_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        cards_box.set_homogeneous(True)

        self.card_all = self._create_card("all", "Todos os Apps", "0 apps", "view-grid-symbolic")
        self.card_apt = self._create_card("apt", "APT / DEB", "0 apps", "package-x-generic-symbolic")
        self.card_flatpak = self._create_card("flatpak", "Flatpak", "0 apps", "system-software-install-symbolic")
        self.card_other = self._create_card("other", "Snap & Outros", "0 apps", "application-x-executable-symbolic")

        cards_box.append(self.card_all)
        cards_box.append(self.card_apt)
        cards_box.append(self.card_flatpak)
        cards_box.append(self.card_other)

        self._update_card_styles()
        return cards_box

    def _create_card(self, category_key: str, title: str, count_text: str, icon_name: str) -> Gtk.Button:
        btn = Gtk.Button()
        btn.add_css_class("flat")
        btn.add_css_class("summary-card")

        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        box.set_valign(Gtk.Align.CENTER)

        icon = Gtk.Image.new_from_icon_name(icon_name)
        icon.set_pixel_size(24)
        box.append(icon)

        text_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        count_lbl = Gtk.Label(label=count_text)
        count_lbl.set_halign(Gtk.Align.START)
        count_lbl.add_css_class("summary-count")
        text_box.append(count_lbl)

        title_lbl = Gtk.Label(label=title)
        title_lbl.set_halign(Gtk.Align.START)
        title_lbl.add_css_class("summary-title")
        text_box.append(title_lbl)

        box.append(text_box)
        btn.set_child(box)

        # Guarda referência para atualização dos rótulos
        setattr(self, f"count_lbl_{category_key}", count_lbl)

        btn.connect("clicked", lambda _: self._set_category_filter(category_key))
        return btn

    def _set_category_filter(self, category_key: str) -> None:
        self.current_filter_category = category_key
        self._update_card_styles()
        self.list_box.invalidate_filter()
        self._check_empty_state()

    def _update_card_styles(self) -> None:
        cards = {
            "all": self.card_all,
            "apt": self.card_apt,
            "flatpak": self.card_flatpak,
            "other": self.card_other,
        }
        for k, btn in cards.items():
            if k == self.current_filter_category:
                btn.add_css_class("summary-card-active")
            else:
                btn.remove_css_class("summary-card-active")

    def _start_scan(self) -> None:
        self.list_stack.set_visible_child_name("loading")
        thread = threading.Thread(target=self._scan_worker, daemon=True)
        thread.start()

    def _scan_worker(self) -> None:
        apps = self.scanner.scan_all()
        GLib.idle_add(self._on_scan_completed, apps)

    def _on_scan_completed(self, apps: List[InstalledApp]) -> bool:
        self.all_apps = apps

        # Limpa linhas antigas
        while True:
            child = self.list_box.get_first_child()
            if child is None:
                break
            self.list_box.remove(child)

        # Adiciona novas linhas
        for app in apps:
            row = AppRow(app, on_uninstall_clicked=self._on_uninstall_requested)
            self.list_box.append(row)

        # Atualiza métricas dos cards
        total_count = len(apps)
        apt_count = sum(1 for a in apps if a.app_type == AppType.APT)
        flatpak_count = sum(1 for a in apps if a.app_type == AppType.FLATPAK)
        other_count = sum(1 for a in apps if a.app_type in (AppType.SNAP, AppType.STANDALONE))

        self.count_lbl_all.set_text(f"{total_count} apps")
        self.count_lbl_apt.set_text(f"{apt_count} apps")
        self.count_lbl_flatpak.set_text(f"{flatpak_count} apps")
        self.count_lbl_other.set_text(f"{other_count} apps")

        self.list_box.invalidate_filter()
        self.list_stack.set_visible_child_name("list")
        self._check_empty_state()
        return False

    def _on_search_changed(self, entry: Gtk.SearchEntry) -> None:
        self.search_query = entry.get_text().strip().lower()
        self.list_box.invalidate_filter()
        self._check_empty_state()

    def _filter_app_row(self, row: Gtk.ListBoxRow) -> bool:
        if not isinstance(row, AppRow):
            return True
        app = row.app

        # Filtro de Categoria
        if self.current_filter_category == "apt" and app.app_type != AppType.APT:
            return False
        elif self.current_filter_category == "flatpak" and app.app_type != AppType.FLATPAK:
            return False
        elif self.current_filter_category == "other" and app.app_type not in (AppType.SNAP, AppType.STANDALONE):
            return False

        # Filtro de Busca por Texto
        if self.search_query:
            query = self.search_query
            match_name = query in app.name.lower()
            match_pkg = query in app.package_name.lower()
            match_id = query in app.id.lower()
            match_summary = query in app.summary.lower()
            if not (match_name or match_pkg or match_id or match_summary):
                return False

        return True

    def _check_empty_state(self) -> None:
        # Verifica se alguma linha passou pelo filtro
        has_visible = False
        child = self.list_box.get_first_child()
        while child:
            if child.get_child_visible():
                has_visible = True
                break
            child = child.get_next_sibling()

        if not has_visible and len(self.all_apps) > 0:
            self.list_stack.set_visible_child_name("empty")
        elif len(self.all_apps) > 0:
            self.list_stack.set_visible_child_name("list")

    def _on_uninstall_requested(self, app: InstalledApp) -> None:
        """Abre o diálogo de confirmação detalhada para o aplicativo."""
        dialog = ConfirmRemovalDialog(
            parent_window=self,
            app=app,
            on_confirmed=self._on_removal_confirmed,
        )
        dialog.present()

    def _on_removal_confirmed(self, app: InstalledApp, selected_residuals: List[ResidualItem]) -> None:
        """Executa a desinstalação após a confirmação do usuário."""
        self.log_view.reset(app.name)
        self.main_stack.set_visible_child_name("log_view")

        def on_status(frac: float, msg: str) -> None:
            self.log_view.set_status(frac, msg)

        def on_log(line: str) -> None:
            self.log_view.append_log(line)

        def on_finished(success: bool, err: Optional[str]) -> None:
            self.log_view.set_finished(success, err)
            if success:
                # Recarrega a lista em background
                GLib.timeout_add(1500, self._trigger_background_scan)

        self.engine.uninstall_async(app, selected_residuals, on_status, on_log, on_finished)

    def _trigger_background_scan(self) -> bool:
        self.scanner.scan_all()
        return False

    def _on_back_to_list(self) -> None:
        self.main_stack.set_visible_child_name("list_view")
        self._start_scan()

    def _show_about_dialog(self, _btn: Gtk.Button) -> None:
        dialog = Adw.AboutDialog()
        dialog.set_application_name("Origin Uninstaller")
        dialog.set_version("1.0.0")
        dialog.set_developer_name("Chrystian")
        dialog.set_comments(
            "Desinstalador nativo para Linux focado em remoção completa e limpeza profunda de arquivos residuais, configurações e dados."
        )
        dialog.set_license_type(Gtk.License.MIT_X11)
        dialog.set_issue_url("https://github.com/chrystian/origin-uninstaller")

        if os.path.exists(APP_ICON_SVG):
            dialog.set_application_icon("origin-uninstaller")

        dialog.present(self)
