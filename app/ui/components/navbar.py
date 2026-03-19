# app/ui/components/navbar.py
from typing import Callable

import customtkinter as ctk

from app.ui.session import AppSession
from app.ui.theme import COLORS, FONTS, SIZES


# Definicion de items del menu: (icono, etiqueta, view_name, solo_admin)
NAV_ITEMS = [
    ("🛒", "Punto de Venta",  "pos",       False),
    ("📊", "Dashboard",       "dashboard", False),
    ("📦", "Productos",       "products",  False),
    ("🗃", "Stock",           "stock",     False),
    ("🛍", "Compras",         "purchases", False),
    ("🏭", "Proveedores",     "suppliers", False),
    ("👥", "Clientes",        "customers", False),
    ("📄", "Reportes",        "reports",   False),
    ("⬆", "Importar Excel", "import",    False),
]


class Navbar(ctk.CTkFrame):
    """
    Barra de navegacion lateral izquierda.
    Muestra el nombre del usuario logueado y botones de navegacion.
    Resalta visualmente la vista activa.

    Uso:
        navbar = Navbar(parent, navigate=self.navigate, active_view="pos")
        navbar.pack(side="left", fill="y")
    """

    def __init__(
        self,
        master,
        navigate: Callable[[str], None],
        active_view: str = "",
        **kwargs,
    ):
        super().__init__(
            master,
            fg_color=COLORS["bg_panel"],
            width=SIZES["sidebar_w"],
            corner_radius=0,
            **kwargs,
        )
        self.navigate = navigate
        self.active_view = active_view
        self.pack_propagate(False)
        self._build_ui()

    def _build_ui(self) -> None:
        # ── Logo / nombre de la app ───────────────────────────────────────────
        header = ctk.CTkFrame(self, fg_color=COLORS["bg_card"], height=64)
        header.pack(fill="x")
        header.pack_propagate(False)

        ctk.CTkLabel(
            header,
            text="DevMont",
            font=("Segoe UI", 18, "bold"),
            text_color=COLORS["accent"],
        ).pack(pady=(10, 0))

        ctk.CTkLabel(
            header,
            text="Commerce",
            font=FONTS["small"],
            text_color=COLORS["text_secondary"],
        ).pack()

        # ── Separador ─────────────────────────────────────────────────────────
        ctk.CTkFrame(self, fg_color=COLORS["border"], height=1).pack(fill="x")

        # ── Usuario logueado ──────────────────────────────────────────────────
        user_frame = ctk.CTkFrame(self, fg_color="transparent")
        user_frame.pack(fill="x", padx=SIZES["padding_sm"], pady=SIZES["padding_sm"])

        ctk.CTkLabel(
            user_frame,
            text="👤  " + AppSession.display_name,
            font=FONTS["small"],
            text_color=COLORS["text_secondary"],
            anchor="w",
        ).pack(fill="x")

        role = "Administrador" if AppSession.is_admin else "Operador"
        ctk.CTkLabel(
            user_frame,
            text=role,
            font=("Segoe UI", 10),
            text_color=COLORS["text_disabled"],
            anchor="w",
        ).pack(fill="x")

        # ── Separador ─────────────────────────────────────────────────────────
        ctk.CTkFrame(self, fg_color=COLORS["border"], height=1).pack(fill="x")

        # ── Items de navegacion ───────────────────────────────────────────────
        nav_container = ctk.CTkFrame(self, fg_color="transparent")
        nav_container.pack(fill="both", expand=True, pady=SIZES["padding_sm"])

        for icon, label, view_name, admin_only in NAV_ITEMS:
            if admin_only and not AppSession.is_admin:
                continue
            self._make_nav_button(nav_container, icon, label, view_name)

        # ── Boton cerrar sesion (al fondo) ────────────────────────────────────
        ctk.CTkFrame(self, fg_color=COLORS["border"], height=1).pack(fill="x")

        ctk.CTkButton(
            self,
            text="⏻  Cerrar sesión",
            font=FONTS["small"],
            height=40,
            fg_color="transparent",
            hover_color=COLORS["btn_danger"],
            text_color=COLORS["text_secondary"],
            anchor="w",
            command=self._logout,
        ).pack(fill="x", padx=4, pady=8)

    def _make_nav_button(
        self,
        parent: ctk.CTkFrame,
        icon: str,
        label: str,
        view_name: str,
    ) -> None:
        is_active = view_name == self.active_view

        btn = ctk.CTkButton(
            parent,
            text=f"  {icon}  {label}",
            font=FONTS["body_bold"] if is_active else FONTS["body"],
            height=44,
            anchor="w",
            fg_color=COLORS["accent"] if is_active else "transparent",
            hover_color=COLORS["accent_hover"] if is_active else COLORS["bg_card"],
            text_color=COLORS["text_primary"],
            corner_radius=6,
            command=lambda v=view_name: self.navigate(v),
        )
        btn.pack(fill="x", padx=6, pady=2)

    def _logout(self) -> None:
        AppSession.logout()
        self.navigate("login")
