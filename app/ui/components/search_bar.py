# app/ui/components/search_bar.py
from typing import Callable

import customtkinter as ctk

from app.ui.theme import COLORS, FONTS, SIZES


class SearchBar(ctk.CTkFrame):
    """
    Barra de busqueda con campo de texto y boton de limpiar.
    Compatible con lectores de codigo de barras USB (simulan teclado + Enter).

    Parametros:
        placeholder: Texto de ayuda en el campo vacio.
        on_search:   Callback(query: str) llamado al presionar Enter o el boton buscar.
        on_clear:    Callback() opcional llamado al limpiar el campo.
        auto_search: Si True, dispara on_search en cada caracter (para busqueda en vivo).
        min_chars:   Minimo de caracteres para disparar auto_search.

    Uso con lector de barras:
        El lector envia los caracteres y luego simula Enter.
        SearchBar captura el evento <Return> y llama on_search automaticamente.
    """

    def __init__(
        self,
        master,
        placeholder: str = "Buscar...",
        on_search: Callable[[str], None] | None = None,
        on_clear: Callable[[], None] | None = None,
        auto_search: bool = False,
        min_chars: int = 2,
        **kwargs,
    ):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.on_search = on_search
        self.on_clear = on_clear
        self.auto_search = auto_search
        self.min_chars = min_chars

        self._build_ui(placeholder)

    def _build_ui(self, placeholder: str) -> None:
        self.columnconfigure(0, weight=1)

        self.var = ctk.StringVar()

        self.entry = ctk.CTkEntry(
            self,
            textvariable=self.var,
            placeholder_text=placeholder,
            height=SIZES["input_height"],
            font=FONTS["body"],
            fg_color=COLORS["bg_input"],
            border_color=COLORS["border"],
            text_color=COLORS["text_primary"],
            placeholder_text_color=COLORS["text_disabled"],
        )
        self.entry.grid(row=0, column=0, sticky="ew", padx=(0, 4))

        self.btn_clear = ctk.CTkButton(
            self,
            text="✕",
            width=SIZES["input_height"],
            height=SIZES["input_height"],
            fg_color=COLORS["btn_neutral"],
            hover_color=COLORS["btn_neutral_hover"],
            font=FONTS["body"],
            command=self.clear,
        )
        self.btn_clear.grid(row=0, column=1)

        # Enter => buscar (cubre lectores de barcode)
        self.entry.bind("<Return>", lambda e: self._trigger_search())

        # Auto-search mientras escribe
        if self.auto_search:
            self.var.trace_add("write", lambda *_: self._auto_trigger())

    def _trigger_search(self) -> None:
        query = self.var.get().strip()
        if self.on_search and query:
            self.on_search(query)

    def _auto_trigger(self) -> None:
        query = self.var.get().strip()
        if self.on_search and len(query) >= self.min_chars:
            self.on_search(query)

    def clear(self) -> None:
        self.var.set("")
        self.entry.focus_set()
        if self.on_clear:
            self.on_clear()

    def get(self) -> str:
        return self.var.get().strip()

    def set(self, value: str) -> None:
        self.var.set(value)

    def focus(self) -> None:
        self.entry.focus_set()
