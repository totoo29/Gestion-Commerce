from __future__ import annotations

from typing import Callable

import customtkinter as ctk

from app.ui.components import AppShell, ShellConfig, DataTable, SearchBar
from app.ui.theme import COLORS, FONTS, SIZES


class CustomersView(ctk.CTkFrame):
    """Clientes (UI estilo SaaS, tabla + búsqueda)."""

    def __init__(self, master: ctk.CTk, navigate: Callable, **kwargs):
        super().__init__(master, fg_color=COLORS["bg_main"], **kwargs)
        self.navigate = navigate
        self._build_ui()

    def _build_ui(self) -> None:
        shell = AppShell(
            self,
            navigate=self.navigate,
            config=ShellConfig(title="Clientes", active_view="customers"),
        )
        shell.pack(fill="both", expand=True)

        page = ctk.CTkFrame(shell.content, fg_color="transparent")
        page.grid(row=0, column=0, sticky="nsew")
        page.grid_columnconfigure(0, weight=1)
        page.grid_rowconfigure(2, weight=1)

        header = ctk.CTkFrame(page, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", pady=(0, SIZES["padding_sm"]))
        header.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            header,
            text="Clientes",
            font=FONTS["title"],
            text_color=COLORS["text_primary"],
        ).grid(row=0, column=0, sticky="w")

        ctk.CTkButton(
            header,
            text="+ Crear cliente",
            height=36,
            font=FONTS["body_bold"],
            fg_color=COLORS["accent"],
            hover_color=COLORS["accent_hover"],
            command=lambda: None,
        ).grid(row=0, column=1, sticky="e")

        self.search = SearchBar(
            page,
            placeholder="Buscar cliente por nombre, teléfono o email…",
            on_search=lambda q: None,
            on_clear=lambda: None,
            auto_search=True,
            min_chars=2,
        )
        self.search.grid(row=1, column=0, sticky="ew", pady=(0, SIZES["padding_sm"]))

        self.table = DataTable(
            page,
            columns=["Nombre", "Teléfono", "Email", "Total comprado", "Última compra"],
            col_widths=[220, 140, 240, 140, 160],
            page_size=20,
        )
        self.table.grid(row=2, column=0, sticky="nsew")

        self.table.load(
            [
                ["Consumidor Final", "—", "—", "$0,00", "—"],
                ["Cliente Demo", "+54 11 3333-3333", "cliente@demo.com", "$0,00", "—"],
            ]
        )

