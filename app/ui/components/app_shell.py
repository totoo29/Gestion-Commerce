from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

import customtkinter as ctk

from app.ui.session import AppSession
from app.ui.theme import COLORS, FONTS, SIZES


@dataclass(frozen=True)
class ShellConfig:
    title: str
    active_view: str


class AppShell(ctk.CTkFrame):
    """
    Layout base para todas las pantallas post-login:
    - Sidebar colapsable (navegación)
    - Topbar (título, búsqueda rápida, toggle tema)
    - Content container (slot)
    """

    def __init__(
        self,
        master,
        navigate: Callable[[str], None],
        config: ShellConfig,
        **kwargs,
    ):
        super().__init__(master, fg_color=COLORS["bg_main"], **kwargs)
        self.navigate = navigate
        self.config = config

        self.sidebar = None
        self.topbar = None
        self.content = None

        self._build()

    def _build(self) -> None:
        self.is_collapsed = False
        
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=0, minsize=SIZES["sidebar_w"])
        self.grid_columnconfigure(1, weight=1)

        from app.ui.components.navbar import Navbar  # import diferido

        self.sidebar = Navbar(
            self,
            navigate=self.navigate,
            active_view=self.config.active_view,
        )
        self.sidebar.grid(row=0, column=0, sticky="nsew")

        main = ctk.CTkFrame(self, fg_color="transparent")
        main.grid(row=0, column=1, sticky="nsew")
        main.grid_rowconfigure(1, weight=1)
        main.grid_columnconfigure(0, weight=1)

        # Topbar
        self.topbar = ctk.CTkFrame(
            main,
            fg_color=COLORS["bg_panel"],
            height=SIZES["header_h"],
            corner_radius=0,
        )
        self.topbar.grid(row=0, column=0, sticky="ew")
        self.topbar.grid_propagate(False)
        self.topbar.grid_columnconfigure(1, weight=1)

        # Título / breadcrumb
        left = ctk.CTkFrame(self.topbar, fg_color="transparent")
        left.grid(row=0, column=0, sticky="w", padx=SIZES["padding"], pady=10)

        # Burger button
        self.btn_toggle = ctk.CTkButton(
            left, text="☰", width=36, height=36, font=FONTS["heading"], 
            fg_color="transparent", hover_color=COLORS["border"],
            text_color=COLORS["text_primary"],
            command=self._on_sidebar_toggle
        )
        self.btn_toggle.pack(side="left", padx=(0, 12))

        ctk.CTkLabel(
            left,
            text=self.config.title,
            font=FONTS["heading"],
            text_color=COLORS["text_primary"],
        ).pack(side="left")

        # Búsqueda rápida (placeholder UX)
        center = ctk.CTkFrame(self.topbar, fg_color="transparent")
        center.grid(row=0, column=1, sticky="ew", padx=(0, SIZES["padding"]), pady=10)
        center.grid_columnconfigure(0, weight=1)

        self.quick_search = ctk.CTkEntry(
            center,
            placeholder_text="Buscar (Ctrl+K)…",
            height=34,
            font=FONTS["body"],
            fg_color=COLORS["bg_input"],
            border_color=COLORS["border"],
            text_color=COLORS["text_primary"],
            placeholder_text_color=COLORS["text_disabled"],
        )
        self.quick_search.grid(row=0, column=0, sticky="ew")

        # Acciones derecha: usuario
        right = ctk.CTkFrame(self.topbar, fg_color="transparent")
        right.grid(row=0, column=2, sticky="e", padx=SIZES["padding"], pady=10)

        ctk.CTkLabel(
            right,
            text=AppSession.display_name,
            font=FONTS["small"],
            text_color=COLORS["text_secondary"],
        ).pack(side="left")

        # Content slot
        self.content = ctk.CTkFrame(main, fg_color="transparent")
        self.content.grid(
            row=1,
            column=0,
            sticky="nsew",
            padx=SIZES["padding_lg"],
            pady=SIZES["padding_lg"],
        )
        self.content.grid_columnconfigure(0, weight=1)
        self.content.grid_rowconfigure(0, weight=1)

        toplevel = self.winfo_toplevel()
        if toplevel is not None:
            toplevel.bind("<Control-k>", lambda e: self.quick_search.focus_set())
            toplevel.bind("<Control-K>", lambda e: self.quick_search.focus_set())

    def _on_sidebar_toggle(self) -> None:
        self.is_collapsed = not getattr(self, "is_collapsed", False)
        
        # update container minsize
        new_w = SIZES["sidebar_w_collapsed"] if self.is_collapsed else SIZES["sidebar_w"]
        self.grid_columnconfigure(0, minsize=new_w)
        
        # call the method on sidebar to adapt its interior
        if hasattr(self.sidebar, "toggle_collapsed"):
            self.sidebar.toggle_collapsed(self.is_collapsed)
            
        self.update_idletasks()
