# app/ui/views/dashboard_view.py
from typing import Callable
from datetime import date

import customtkinter as ctk

from app.core.logging import get_logger
from app.database import SessionLocal
from app.services.sale_service import SaleService
from app.services.stock_service import StockService
from app.ui.session import AppSession
from app.ui.components import AppShell, ShellConfig
from app.ui.theme import COLORS, FONTS, SIZES

logger = get_logger(__name__)


class DashboardView(ctk.CTkFrame):
    """
    Vista principal post-login.
    Muestra resumen del dia: ventas, total y alertas de stock critico.
    Sirve como hub de navegacion hacia el resto de modulos.
    """

    def __init__(self, master: ctk.CTk, navigate: Callable, **kwargs):
        super().__init__(master, fg_color=COLORS["bg_main"], **kwargs)
        self.navigate = navigate
        self._build_ui()
        self._load_data()

    # ── Construccion de la UI ─────────────────────────────────────────────────

    def _build_ui(self) -> None:
        shell = AppShell(
            self,
            navigate=self.navigate,
            config=ShellConfig(title="Dashboard", active_view="dashboard"),
        )
        shell.pack(fill="both", expand=True)

        content = ctk.CTkFrame(shell.content, fg_color="transparent")
        content.grid(row=0, column=0, sticky="nsew")
        content.grid_columnconfigure(0, weight=1)
        content.grid_rowconfigure(3, weight=1)

        # Titulo + subtitulo
        title_row = ctk.CTkFrame(content, fg_color="transparent")
        title_row.grid(row=0, column=0, sticky="ew", pady=(0, SIZES["padding"]))
        title_row.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            title_row,
            text=f"Hola, {AppSession.display_name}",
            font=FONTS["title"],
            text_color=COLORS["text_primary"],
        ).grid(row=0, column=0, sticky="w")

        ctk.CTkLabel(
            title_row,
            text=f"Resumen • {date.today().strftime('%d/%m/%Y')}",
            font=FONTS["small"],
            text_color=COLORS["text_secondary"],
        ).grid(row=1, column=0, sticky="w", pady=(2, 0))

        # ── Tarjetas de métricas ─────────────────────────────────────────────
        cards_frame = ctk.CTkFrame(content, fg_color="transparent")
        cards_frame.grid(row=1, column=0, sticky="ew", pady=(0, SIZES["padding_lg"]))
        cards_frame.grid_columnconfigure((0, 1, 2, 3), weight=1, uniform="metrics")

        self.card_ventas = self._make_metric_card(cards_frame, "Tickets (hoy)", "0", COLORS["info"], icon="🧾")
        self.card_total = self._make_metric_card(cards_frame, "Ventas (hoy)", "$0,00", COLORS["success"], icon="💳")
        self.card_mes = self._make_metric_card(cards_frame, "Ventas (mes)", "$0,00", COLORS["accent"], icon="📈")
        self.card_alertas = self._make_metric_card(cards_frame, "Stock bajo", "0", COLORS["warning"], icon="⚠")

        self.card_ventas.grid(row=0, column=0, sticky="nsew", padx=(0, SIZES["padding_sm"]))
        self.card_total.grid(row=0, column=1, sticky="nsew", padx=(SIZES["padding_sm"], SIZES["padding_sm"]))
        self.card_mes.grid(row=0, column=2, sticky="nsew", padx=(SIZES["padding_sm"], SIZES["padding_sm"]))
        self.card_alertas.grid(row=0, column=3, sticky="nsew", padx=(SIZES["padding_sm"], 0))

        # ── Accesos rápidos + gráficos (placeholders) ─────────────────────────
        mid = ctk.CTkFrame(content, fg_color="transparent")
        mid.grid(row=2, column=0, sticky="nsew", pady=(0, SIZES["padding_lg"]))
        mid.grid_columnconfigure((0, 1), weight=1, uniform="mid")
        mid.grid_rowconfigure(1, weight=1)

        shortcuts_card = ctk.CTkFrame(
            mid,
            fg_color=COLORS["bg_panel"],
            corner_radius=SIZES["radius_lg"],
            border_width=1,
            border_color=COLORS["border"],
        )
        shortcuts_card.grid(row=0, column=0, rowspan=2, sticky="nsew", padx=(0, SIZES["padding"]))
        shortcuts_card.grid_columnconfigure(0, weight=1)

        top_row = ctk.CTkFrame(shortcuts_card, fg_color="transparent")
        top_row.grid(row=0, column=0, sticky="ew", padx=SIZES["padding"], pady=(SIZES["padding"], 0))
        top_row.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            top_row,
            text="Accesos rápidos",
            font=FONTS["heading"],
            text_color=COLORS["text_primary"],
        ).grid(row=0, column=0, sticky="w")

        ctk.CTkButton(
            top_row,
            text="↻ Actualizar",
            font=FONTS["small"],
            width=120,
            height=30,
            fg_color=COLORS["btn_neutral"],
            hover_color=COLORS["btn_neutral_hover"],
            command=self._load_data,
        ).grid(row=0, column=1, sticky="e")

        shortcuts = ctk.CTkFrame(shortcuts_card, fg_color="transparent")
        shortcuts.grid(row=1, column=0, sticky="ew", padx=SIZES["padding"], pady=(SIZES["padding_sm"], SIZES["padding"]))
        shortcuts.grid_columnconfigure((0, 1), weight=1, uniform="shortcuts")

        accesos = [
            ("🛒  Punto de Venta", "pos", COLORS["btn_success"], COLORS["btn_success_hover"], 0, 0, True),
            ("📦  Productos", "products", COLORS["btn_neutral"], COLORS["btn_neutral_hover"], 0, 1, False),
            ("🗃  Inventario", "stock", COLORS["btn_neutral"], COLORS["btn_neutral_hover"], 1, 0, False),
            ("🛍  Compras", "purchases", COLORS["btn_neutral"], COLORS["btn_neutral_hover"], 1, 1, False),
        ]

        for label, view, color, hover, r, c, is_primary in accesos:
            ctk.CTkButton(
                shortcuts,
                text=label,
                font=FONTS["body_bold"],
                height=56,
                fg_color=color,
                hover_color=hover,
                border_width=1 if not is_primary else 0,
                border_color=COLORS["border"],
                command=lambda v=view: self.navigate(v),
            ).grid(row=r, column=c, sticky="ew", padx=(0, SIZES["padding_sm"]) if c == 0 else (SIZES["padding_sm"], 0), pady=(0, SIZES["padding_sm"]) if r == 0 else (SIZES["padding_sm"], 0))

        charts_card = ctk.CTkFrame(
            mid,
            fg_color=COLORS["bg_panel"],
            corner_radius=SIZES["radius_lg"],
            border_width=1,
            border_color=COLORS["border"],
        )
        charts_card.grid(row=0, column=1, sticky="nsew")
        charts_card.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            charts_card,
            text="Ventas por día (próximamente)",
            font=FONTS["heading"],
            text_color=COLORS["text_primary"],
        ).pack(anchor="w", padx=SIZES["padding"], pady=(SIZES["padding"], 0))

        ctk.CTkLabel(
            charts_card,
            text="Aquí irá un gráfico tipo línea/área.",
            font=FONTS["small"],
            text_color=COLORS["text_secondary"],
        ).pack(anchor="w", padx=SIZES["padding"], pady=(4, SIZES["padding"]))

        charts2_card = ctk.CTkFrame(
            mid,
            fg_color=COLORS["bg_panel"],
            corner_radius=SIZES["radius_lg"],
            border_width=1,
            border_color=COLORS["border"],
        )
        charts2_card.grid(row=1, column=1, sticky="nsew", pady=(SIZES["padding"], 0))
        charts2_card.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            charts2_card,
            text="Ventas por categoría (próximamente)",
            font=FONTS["heading"],
            text_color=COLORS["text_primary"],
        ).pack(anchor="w", padx=SIZES["padding"], pady=(SIZES["padding"], 0))

        ctk.CTkLabel(
            charts2_card,
            text="Aquí irá un gráfico tipo barras/donut.",
            font=FONTS["small"],
            text_color=COLORS["text_secondary"],
        ).pack(anchor="w", padx=SIZES["padding"], pady=(4, SIZES["padding"]))

        # ── Panel de alertas de stock ─────────────────────────────────────────
        alerts_card = ctk.CTkFrame(
            content,
            fg_color=COLORS["bg_panel"],
            corner_radius=SIZES["radius_lg"],
            border_width=1,
            border_color=COLORS["border"],
        )
        alerts_card.grid(row=3, column=0, sticky="nsew")
        alerts_card.grid_columnconfigure(0, weight=1)
        alerts_card.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(
            alerts_card,
            text="Productos con stock crítico",
            font=FONTS["heading"],
            text_color=COLORS["text_primary"],
        ).grid(row=0, column=0, sticky="w", padx=SIZES["padding"], pady=(SIZES["padding"], SIZES["padding_sm"]))

        self.alerts_frame = ctk.CTkScrollableFrame(
            alerts_card,
            fg_color="transparent",
            height=220,
        )
        self.alerts_frame.grid(row=1, column=0, sticky="nsew", padx=SIZES["padding"], pady=(0, SIZES["padding"]))

    def _make_metric_card(
        self,
        parent,
        title: str,
        value: str,
        color: str,
        icon: str = "",
    ) -> ctk.CTkFrame:
        """Crea una tarjeta de metrica con titulo y valor grande."""
        card = ctk.CTkFrame(
            parent,
            fg_color=COLORS["bg_panel"],
            corner_radius=16,
            height=120,
            border_width=1,
            border_color=COLORS["border"],
        )
        card.grid_propagate(False)
        card.grid_columnconfigure(0, weight=1)

        top = ctk.CTkFrame(card, fg_color="transparent")
        top.grid(row=0, column=0, sticky="ew", padx=SIZES["padding"], pady=(SIZES["padding"], 0))
        top.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            top,
            text=title,
            font=FONTS["small"],
            text_color=COLORS["text_secondary"],
        ).grid(row=0, column=0, sticky="w")

        if icon:
            ctk.CTkLabel(
                top,
                text=icon,
                font=FONTS["body"],
                text_color=COLORS["text_secondary"],
            ).grid(row=0, column=1, sticky="e")

        lbl = ctk.CTkLabel(
            card,
            text=value,
            font=("Segoe UI", 30, "bold"),
            text_color=color,
        )
        lbl.grid(row=1, column=0, sticky="w", padx=SIZES["padding"], pady=(6, SIZES["padding"]))

        # Guardar referencia al label de valor para actualizarlo
        card._value_label = lbl
        return card

    # ── Carga de datos ────────────────────────────────────────────────────────

    def _load_data(self) -> None:
        """Carga las metricas del dia y las alertas de stock."""
        try:
            with SessionLocal() as session:
                sale_service  = SaleService(session)
                stock_service = StockService(session)

                count = sale_service.get_today_count()
                total = sale_service.get_today_total()
                try:
                    total_month = sale_service.get_month_total()
                except Exception:
                    total_month = 0
                alertas = stock_service.get_critical_items()

            # Actualizar tarjetas
            self.card_ventas._value_label.configure(text=str(count))
            self.card_total._value_label.configure(
                text=f"${total:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
            )
            self.card_mes._value_label.configure(
                text=f"${total_month:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
            )
            self.card_alertas._value_label.configure(
                text=str(len(alertas)),
                text_color=COLORS["warning"] if alertas else COLORS["success"],
            )

            # Listar productos con stock critico
            for widget in self.alerts_frame.winfo_children():
                widget.destroy()

            if not alertas:
                ctk.CTkLabel(
                    self.alerts_frame,
                    text="✓  Todos los productos tienen stock suficiente.",
                    font=FONTS["body"],
                    text_color=COLORS["success"],
                ).pack(anchor="w", pady=8)
            else:
                for stock in alertas:
                    row = ctk.CTkFrame(self.alerts_frame, fg_color="transparent")
                    row.pack(fill="x", pady=2)
                    ctk.CTkLabel(
                        row,
                        text=f"⚠  {stock.product.name}",
                        font=FONTS["body"],
                        text_color=COLORS["warning"],
                    ).pack(side="left")
                    ctk.CTkLabel(
                        row,
                        text=f"Stock: {stock.quantity} / Mínimo: {stock.min_quantity}",
                        font=FONTS["small"],
                        text_color=COLORS["text_secondary"],
                    ).pack(side="right")

        except Exception as e:
            logger.error(f"Error cargando dashboard: {e}")

    # ── Acciones ──────────────────────────────────────────────────────────────

    def _logout(self) -> None:
        AppSession.logout()
        self.navigate("login")
