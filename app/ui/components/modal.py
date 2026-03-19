# app/ui/components/modal.py
from typing import Callable

import customtkinter as ctk

from app.ui.theme import COLORS, FONTS, SIZES


class ConfirmModal(ctk.CTkToplevel):
    """
    Modal de confirmacion con dos botones: Confirmar y Cancelar.

    Uso:
        modal = ConfirmModal(
            parent,
            title="Eliminar producto",
            message="¿Está seguro que desea eliminar este producto?",
            on_confirm=lambda: service.delete(product_id),
        )
    """

    def __init__(
        self,
        parent,
        title: str,
        message: str,
        on_confirm: Callable,
        confirm_text: str = "Confirmar",
        cancel_text: str = "Cancelar",
        danger: bool = False,
    ):
        super().__init__(parent)
        self.on_confirm = on_confirm

        self.title(title)
        self.resizable(False, False)
        self.configure(fg_color=COLORS["bg_panel"])
        self.grab_set()  # Modal: bloquea interaccion con la ventana padre

        self._build_ui(title, message, confirm_text, cancel_text, danger)
        self._center_on_parent(parent)
        self.after(100, self.focus_set)

    def _build_ui(self, title, message, confirm_text, cancel_text, danger):
        # Icono + titulo
        ctk.CTkLabel(
            self,
            text=title,
            font=FONTS["heading"],
            text_color=COLORS["text_primary"],
        ).pack(padx=32, pady=(28, 8))

        # Mensaje
        ctk.CTkLabel(
            self,
            text=message,
            font=FONTS["body"],
            text_color=COLORS["text_secondary"],
            wraplength=340,
            justify="center",
        ).pack(padx=32, pady=(0, 24))

        # Botones
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(padx=32, pady=(0, 28), fill="x")

        confirm_color = COLORS["btn_danger"] if danger else COLORS["accent"]
        confirm_hover = COLORS["btn_danger_hover"] if danger else COLORS["accent_hover"]

        ctk.CTkButton(
            btn_frame,
            text=cancel_text,
            font=FONTS["body"],
            height=SIZES["btn_height"],
            fg_color=COLORS["btn_neutral"],
            hover_color=COLORS["btn_neutral_hover"],
            command=self.destroy,
        ).pack(side="left", fill="x", expand=True, padx=(0, 8))

        ctk.CTkButton(
            btn_frame,
            text=confirm_text,
            font=FONTS["body_bold"],
            height=SIZES["btn_height"],
            fg_color=confirm_color,
            hover_color=confirm_hover,
            command=self._confirm,
        ).pack(side="left", fill="x", expand=True)

        # Escape cierra el modal
        self.bind("<Escape>", lambda e: self.destroy())

    def _confirm(self):
        self.destroy()
        self.on_confirm()

    def _center_on_parent(self, parent):
        self.update_idletasks()
        pw = parent.winfo_width()
        ph = parent.winfo_height()
        px = parent.winfo_rootx()
        py = parent.winfo_rooty()
        mw = 400
        mh = 200
        x = px + (pw - mw) // 2
        y = py + (ph - mh) // 2
        self.geometry(f"{mw}x{mh}+{x}+{y}")


class AlertModal(ctk.CTkToplevel):
    """
    Modal de alerta de un solo boton: informacion, exito o error.

    Uso:
        AlertModal(parent, title="Error", message="Stock insuficiente.", kind="error")
        AlertModal(parent, title="Listo", message="Venta registrada.", kind="success")
    """

    ICONS = {
        "error":   "✖",
        "success": "✔",
        "warning": "⚠",
        "info":    "ℹ",
    }

    ICON_COLORS = {
        "error":   COLORS["error"],
        "success": COLORS["success"],
        "warning": COLORS["warning"],
        "info":    COLORS["info"],
    }

    def __init__(
        self,
        parent,
        title: str,
        message: str,
        kind: str = "info",
        btn_text: str = "Aceptar",
    ):
        super().__init__(parent)
        self.title(title)
        self.resizable(False, False)
        self.configure(fg_color=COLORS["bg_panel"])
        self.grab_set()

        self._build_ui(title, message, kind, btn_text)
        self._center_on_parent(parent)
        self.after(100, self.focus_set)

    def _build_ui(self, title, message, kind, btn_text):
        icon_color = self.ICON_COLORS.get(kind, COLORS["info"])
        icon = self.ICONS.get(kind, "ℹ")

        # Icono
        ctk.CTkLabel(
            self,
            text=icon,
            font=("Segoe UI", 36),
            text_color=icon_color,
        ).pack(pady=(28, 4))

        # Titulo
        ctk.CTkLabel(
            self,
            text=title,
            font=FONTS["heading"],
            text_color=COLORS["text_primary"],
        ).pack(padx=32)

        # Mensaje
        ctk.CTkLabel(
            self,
            text=message,
            font=FONTS["body"],
            text_color=COLORS["text_secondary"],
            wraplength=340,
            justify="center",
        ).pack(padx=32, pady=(8, 24))

        ctk.CTkButton(
            self,
            text=btn_text,
            font=FONTS["body_bold"],
            height=SIZES["btn_height"],
            fg_color=icon_color,
            hover_color=COLORS["accent_hover"] if kind == "error" else COLORS["btn_success_hover"],
            command=self.destroy,
        ).pack(padx=48, pady=(0, 28), fill="x")

        self.bind("<Return>", lambda e: self.destroy())
        self.bind("<Escape>", lambda e: self.destroy())

    def _center_on_parent(self, parent):
        self.update_idletasks()
        pw = parent.winfo_width()
        ph = parent.winfo_height()
        px = parent.winfo_rootx()
        py = parent.winfo_rooty()
        mw = 400
        mh = 260
        x = px + (pw - mw) // 2
        y = py + (ph - mh) // 2
        self.geometry(f"{mw}x{mh}+{x}+{y}")
