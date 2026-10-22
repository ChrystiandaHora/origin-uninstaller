from typing import Callable, Optional

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, GLib, Gtk, Pango

from ..models import InstalledApp


class LogView(Gtk.Box):
    """
    Visualização dedicada do progresso e saída de terminal em tempo real
    durante a desinstalação de pacotes e limpeza de pastas.
    """

    def __init__(self, on_back_clicked: Callable[[], None]) -> None:
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=14)
        self.on_back_clicked = on_back_clicked
        self.set_margin_top(16)
        self.set_margin_bottom(16)
        self.set_margin_start(20)
        self.set_margin_end(20)

        self._build_ui()

    def _build_ui(self) -> None:
        # 1. Cabeçalho de Status
        self.header_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        self.header_box.add_css_class("card")
        self.header_box.set_size_request(-1, 64)

        self.spinner = Gtk.Spinner()
        self.spinner.set_spinning(True)
        self.spinner.set_pixel_size(24)
        self.spinner.set_margin_start(16)
        self.header_box.append(self.spinner)

        status_text_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        status_text_box.set_valign(Gtk.Align.CENTER)
        status_text_box.set_hexpand(True)

        self.status_title = Gtk.Label(label="Desinstalando aplicativo...")
        self.status_title.set_halign(Gtk.Align.START)
        self.status_title.add_css_class("title-3")
        status_text_box.append(self.status_title)

        self.status_desc = Gtk.Label(label="Aguarde enquanto os pacotes e arquivos são limpos.")
        self.status_desc.set_halign(Gtk.Align.START)
        self.status_desc.add_css_class("dim-label")
        status_text_box.append(self.status_desc)

        self.header_box.append(status_text_box)
        self.append(self.header_box)

        # 2. Barra de Progresso
        self.progress_bar = Gtk.ProgressBar()
        self.progress_bar.set_fraction(0.0)
        self.progress_bar.set_show_text(True)
        self.progress_bar.set_text("0%")
        self.append(self.progress_bar)

        # 3. Terminal de Log Monospaçado
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_vexpand(True)
        scrolled.set_hexpand(True)
        scrolled.add_css_class("terminal-scrolled")

        self.text_view = Gtk.TextView()
        self.text_view.set_editable(False)
        self.text_view.set_cursor_visible(False)
        self.text_view.set_monospace(True)
        self.text_view.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
        self.text_view.set_left_margin(12)
        self.text_view.set_right_margin(12)
        self.text_view.set_top_margin(10)
        self.text_view.set_bottom_margin(10)
        self.text_view.add_css_class("terminal-view")

        self.buffer = self.text_view.get_buffer()
        scrolled.set_child(self.text_view)
        self.append(scrolled)

        # 4. Rodapé com Botão de Retorno
        self.bottom_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        self.bottom_box.set_halign(Gtk.Align.END)
        self.bottom_box.set_margin_top(4)

        self.btn_back = Gtk.Button(label="Voltar para a Lista de Aplicativos")
        self.btn_back.set_icon_name("go-previous-symbolic")
        self.btn_back.add_css_class("suggested-action")
        self.btn_back.set_sensitive(False)
        self.btn_back.connect("clicked", lambda _: self.on_back_clicked())
        self.bottom_box.append(self.btn_back)

        self.append(self.bottom_box)

    def reset(self, app_name: str) -> None:
        """Reinicia o log para uma nova execução."""
        self.buffer.set_text("")
        self.progress_bar.set_fraction(0.0)
        self.progress_bar.set_text("0%")
        self.spinner.set_spinning(True)
        self.status_title.set_text(f"Removendo '{app_name}'...")
        self.status_desc.set_text("Executando desinstalação profunda e limpeza...")
        self.btn_back.set_sensitive(False)

    def set_status(self, fraction: float, message: str) -> None:
        GLib.idle_add(self._do_set_status, fraction, message)

    def _do_set_status(self, fraction: float, message: str) -> bool:
        self.progress_bar.set_fraction(max(0.0, min(1.0, fraction)))
        pct = int(fraction * 100)
        self.progress_bar.set_text(f"{pct}% - {message}")
        self.status_desc.set_text(message)
        return False

    def append_log(self, text: str) -> None:
        GLib.idle_add(self._do_append_log, text)

    def _do_append_log(self, text: str) -> bool:
        end_iter = self.buffer.get_end_iter()
        self.buffer.insert(end_iter, text + "\n")
        # Scroll para o fim
        mark = self.buffer.create_mark(None, self.buffer.get_end_iter(), False)
        self.text_view.scroll_to_mark(mark, 0.0, True, 0.0, 1.0)
        return False

    def set_finished(self, success: bool, error: Optional[str] = None) -> None:
        GLib.idle_add(self._do_set_finished, success, error)

    def _do_set_finished(self, success: bool, error: Optional[str]) -> bool:
        self.spinner.set_spinning(False)
        self.btn_back.set_sensitive(True)
        if success:
            self.status_title.set_text("✔ Desinstalação e Limpeza Concluídas!")
            self.status_desc.set_text("O aplicativo e todos os dados selecionados foram removidos.")
            self.progress_bar.set_fraction(1.0)
            self.progress_bar.set_text("100% - Concluído")
        else:
            self.status_title.set_text("⚠️ Concluído com Avisos ou Erros")
            self.status_desc.set_text(error or "Verifique o log de saída do terminal acima.")
        return False
