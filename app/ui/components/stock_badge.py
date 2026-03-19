# app/ui/components/stock_badge.py
import customtkinter as ctk
from decimal import Decimal

from app.ui.theme import COLORS, FONTS


class StockBadge(ctk.CTkLabel):
    """
    Badge (etiqueta de color) que indica el nivel de stock de un producto.

    Niveles:
        - CRITICO  (rojo):    quantity <= min_quantity
        - BAJO     (naranja): quantity <= min_quantity * 1.5
        - NORMAL   (verde):   quantity > min_quantity * 1.5

    Uso:
        badge = StockBadge(parent, quantity=5, min_quantity=10)
        badge.pack()

        # Actualizar dinamicamente:
        badge.update_stock(quantity=15, min_quantity=10)
    """

    def __init__(
        self,
        master,
        quantity: int | float | Decimal = 0,
        min_quantity: int | float | Decimal = 0,
        show_number: bool = True,
        **kwargs,
    ):
        super().__init__(master, font=FONTS["badge"], corner_radius=6, **kwargs)
        self.show_number = show_number
        self.update_stock(quantity, min_quantity)

    def update_stock(
        self,
        quantity: int | float | Decimal,
        min_quantity: int | float | Decimal,
    ) -> None:
        qty = float(quantity)
        min_qty = float(min_quantity)

        if min_qty <= 0:
            # Sin stock minimo configurado: mostrar neutral
            text = f" {qty:.0f} " if self.show_number else " OK "
            self.configure(
                text=text,
                fg_color=COLORS["btn_neutral"],
                text_color=COLORS["text_secondary"],
            )
            return

        if qty <= min_qty:
            level = "CRÍTICO"
            fg = COLORS["error"]
            tc = "#ffffff"
        elif qty <= min_qty * 1.5:
            level = "BAJO"
            fg = COLORS["warning"]
            tc = "#000000"
        else:
            level = "OK"
            fg = COLORS["success"]
            tc = "#000000"

        if self.show_number:
            text = f" {qty:.0f} "
        else:
            text = f" {level} "

        self.configure(text=text, fg_color=fg, text_color=tc)


class StockBadgeDetailed(ctk.CTkFrame):
    """
    Version expandida del badge que muestra cantidad / minimo y etiqueta de nivel.
    Util para vistas de stock y alertas en dashboard.

    Uso:
        badge = StockBadgeDetailed(parent, quantity=5, min_quantity=10, product_name="Tornillo")
        badge.pack(fill="x")
    """

    def __init__(
        self,
        master,
        quantity: int | float | Decimal,
        min_quantity: int | float | Decimal,
        product_name: str = "",
        **kwargs,
    ):
        super().__init__(master, fg_color="transparent", **kwargs)
        self._build(quantity, min_quantity, product_name)

    def _build(self, quantity, min_quantity, product_name):
        qty = float(quantity)
        min_qty = float(min_quantity)

        if min_qty > 0 and qty <= min_qty:
            color = COLORS["error"]
            label = "CRÍTICO"
        elif min_qty > 0 and qty <= min_qty * 1.5:
            color = COLORS["warning"]
            label = "BAJO"
        else:
            color = COLORS["success"]
            label = "OK"

        if product_name:
            ctk.CTkLabel(
                self,
                text=product_name,
                font=FONTS["body"],
                text_color=COLORS["text_primary"],
                anchor="w",
            ).pack(side="left", fill="x", expand=True)

        ctk.CTkLabel(
            self,
            text=f"{qty:.0f} / {min_qty:.0f}",
            font=FONTS["mono"],
            text_color=COLORS["text_secondary"],
        ).pack(side="left", padx=8)

        ctk.CTkLabel(
            self,
            text=f" {label} ",
            font=FONTS["badge"],
            fg_color=color,
            text_color="#ffffff" if label == "CRÍTICO" else "#000000",
            corner_radius=4,
        ).pack(side="left")
