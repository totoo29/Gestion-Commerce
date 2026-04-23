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
    ("⚙", "Configuración",   "settings",  True),  # <-- Novedad
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

        self.lbl_logo = ctk.CTkLabel(
            header,
            text="DevMont",
            font=("Segoe UI", 18, "bold"),
            text_color=COLORS["accent"],
        )
        self.lbl_logo.pack(pady=(10, 0))

        self.lbl_subtitle = ctk.CTkLabel(
            header,
            text="Commerce",
            font=FONTS["small"],
            text_color=COLORS["text_secondary"],
        )
        self.lbl_subtitle.pack()

        # ── Separador ─────────────────────────────────────────────────────────
        ctk.CTkFrame(self, fg_color=COLORS["border"], height=1).pack(fill="x")

        # ── Usuario logueado ──────────────────────────────────────────────────
        user_frame = ctk.CTkFrame(self, fg_color="transparent")
        user_frame.pack(fill="x", padx=SIZES["padding_sm"], pady=SIZES["padding_sm"])

        self.lbl_user = ctk.CTkLabel(
            user_frame,
            text="👤  " + AppSession.display_name,
            font=FONTS["small"],
            text_color=COLORS["text_secondary"],
            anchor="w",
        )
        self.lbl_user.pack(fill="x", padx=6)

        role = "Administrador" if AppSession.is_admin else "Operador"
        self.lbl_role = ctk.CTkLabel(
            user_frame,
            text=role,
            font=("Segoe UI", 10),
            text_color=COLORS["text_disabled"],
            anchor="w",
        )
        self.lbl_role.pack(fill="x", padx=6)

        # ── Separador ─────────────────────────────────────────────────────────
        ctk.CTkFrame(self, fg_color=COLORS["border"], height=1).pack(fill="x")

        # ── Items de navegacion ───────────────────────────────────────────────
        nav_container = ctk.CTkScrollableFrame(
            self, 
            fg_color="transparent",
            scrollbar_button_color=COLORS["bg_panel"],
            scrollbar_button_hover_color=COLORS["border"]
        )
        nav_container.pack(fill="both", expand=True, pady=SIZES["padding_sm"])
        self.nav_buttons = []

        for icon, label, view_name, admin_only in NAV_ITEMS:
            if admin_only and not AppSession.is_admin:
                continue
            btn = self._make_nav_button(nav_container, icon, label, view_name)
            self.nav_buttons.append((btn, icon, label))

        # ── Boton cerrar sesion (al fondo) ────────────────────────────────────
        ctk.CTkFrame(self, fg_color=COLORS["border"], height=1).pack(fill="x")

        ctk.CTkFrame(self, fg_color=COLORS["border"], height=1).pack(fill="x")

        self.btn_logout = ctk.CTkButton(
            self,
            text="⏻  Cerrar sesión",
            font=FONTS["small"],
            height=40,
            fg_color="transparent",
            hover_color=COLORS["btn_danger"],
            text_color=COLORS["text_secondary"],
            anchor="w",
            command=self._logout,
        )
        self.btn_logout.pack(fill="x", padx=4, pady=8)

    def _make_nav_button(
        self,
        parent: ctk.CTkFrame,
        icon: str,
        label: str,
        view_name: str,
    ) -> ctk.CTkButton:
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
        return btn

    def toggle_collapsed(self, is_collapsed: bool) -> None:
        if is_collapsed:
            self.configure(width=SIZES["sidebar_w_collapsed"])
            self.lbl_logo.configure(text="DM")
            self.lbl_subtitle.pack_forget()
            
            self.lbl_user.configure(text=" 👤", anchor="center")
            self.lbl_user.pack(fill="x", padx=0)
            self.lbl_role.pack_forget()
            
            for btn, icon, label in self.nav_buttons:
                btn.configure(text=f" {icon} ", anchor="center")
            
            self.btn_logout.configure(text="⏻", anchor="center")
        else:
            self.configure(width=SIZES["sidebar_w"])
            self.lbl_logo.configure(text="DevMont")
            self.lbl_subtitle.pack()
            
            self.lbl_user.configure(text="👤  " + AppSession.display_name, anchor="w")
            self.lbl_user.pack(fill="x", padx=6)
            self.lbl_role.pack(fill="x", padx=6)
            
            for btn, icon, label in self.nav_buttons:
                btn.configure(text=f"  {icon}  {label}", anchor="w")
                
            self.btn_logout.configure(text="⏻  Cerrar sesión", anchor="w")

    def _logout(self) -> None:
        AppSession.logout()
        self.navigate("login")
