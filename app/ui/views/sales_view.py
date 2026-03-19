# app/ui/views/sales_view.py
from datetime import date, timedelta, datetime
from typing import Callable
from decimal import Decimal

import customtkinter as ctk

from app.core.logging import get_logger
from app.database import SessionLocal
from app.repository.sale_repository import SaleRepository
from app.ui.components.data_table import DataTable
from app.ui.components.modal import AlertModal
from app.ui.components import AppShell, ShellConfig
from app.ui.theme import COLORS, FONTS, SIZES

logger = get_logger(__name__)


class SalesView(ctk.CTkFrame):
    def __init__(self, master: ctk.CTk, navigate: Callable, **kwargs):
        super().__init__(master, fg_color=COLORS["bg_main"], **kwargs)
        self.navigate = navigate
        self._build_ui()
        self._load_sales(date.today(), date.today())

    def _build_ui(self) -> None:
        shell = AppShell(
            self,
            navigate=self.navigate,
            config=ShellConfig(title="Ventas por día", active_view="sales"),
        )
        shell.pack(fill="both", expand=True)

        main = ctk.CTkFrame(shell.content, fg_color="transparent")
        main.pack(fill="both", expand=True)

        # Header
        header = ctk.CTkFrame(main, fg_color="transparent")
        header.pack(fill="x", pady=(0, SIZES["padding"]))
        ctk.CTkLabel(header, text="Historial de Ventas", font=FONTS["subtitle"],
                     text_color=COLORS["text_primary"]).pack(side="left")

        # Filtros
        filters = ctk.CTkFrame(main, fg_color=COLORS["bg_panel"], corner_radius=8)
        filters.pack(fill="x", pady=(0, SIZES["padding"]))

        pad = SIZES["padding_sm"]

        ctk.CTkLabel(filters, text="Filtrar por fecha:", font=FONTS["body_bold"], text_color=COLORS["text_primary"]).pack(side="left", padx=pad, pady=pad)

        self.btn_today = ctk.CTkButton(filters, text="Hoy", width=80, height=30, command=lambda: self._set_filter("today"))
        self.btn_today.pack(side="left", padx=(8, 0), pady=pad)

        self.btn_week = ctk.CTkButton(filters, text="Últimos 7 días", width=120, height=30, fg_color=COLORS["btn_neutral"], hover_color=COLORS["btn_neutral_hover"], command=lambda: self._set_filter("week"))
        self.btn_week.pack(side="left", padx=(8, 0), pady=pad)
        
        # Fecha personalizada
        ctk.CTkLabel(filters, text="  O buscar un día (dd/mm/aaaa):", font=FONTS["small"], text_color=COLORS["text_secondary"]).pack(side="left", padx=(16, 4))
        self.var_date = ctk.StringVar(value=date.today().strftime("%d/%m/%Y"))
        
        self.entry_date = ctk.CTkEntry(filters, textvariable=self.var_date, width=100, height=30, font=FONTS["body"])
        self.entry_date.pack(side="left", padx=4)
        
        self.btn_search = ctk.CTkButton(filters, text="Buscar", width=80, height=30, fg_color=COLORS["accent"], hover_color=COLORS["accent_hover"], command=self._search_custom_date)
        self.btn_search.pack(side="left", padx=4)

        # Totales
        self.lbl_totals = ctk.CTkLabel(filters, text="Total filtrado: $0.00", font=FONTS["body_bold"], text_color=COLORS["success"])
        self.lbl_totals.pack(side="right", padx=pad)

        # Tabla de ventas
        self.table = DataTable(
            main,
            columns=["# Venta", "Fecha y Hora", "Cliente", "Total", "Método", "Estado"],
            col_widths=[80, 160, 200, 120, 120, 100],
        )
        self.table.pack(fill="both", expand=True)

    def _set_filter(self, mode: str):
        if mode == "today":
            self.btn_today.configure(fg_color=COLORS["primary"], hover_color=COLORS["primary_hover"])
            self.btn_week.configure(fg_color=COLORS["btn_neutral"], hover_color=COLORS["btn_neutral_hover"])
            d = date.today()
            self.var_date.set(d.strftime("%d/%m/%Y"))
            self._load_sales(d, d)
        elif mode == "week":
            self.btn_week.configure(fg_color=COLORS["primary"], hover_color=COLORS["primary_hover"])
            self.btn_today.configure(fg_color=COLORS["btn_neutral"], hover_color=COLORS["btn_neutral_hover"])
            d_to = date.today()
            d_from = d_to - timedelta(days=7)
            self._load_sales(d_from, d_to)

    def _search_custom_date(self):
        self.btn_today.configure(fg_color=COLORS["btn_neutral"], hover_color=COLORS["btn_neutral_hover"])
        self.btn_week.configure(fg_color=COLORS["btn_neutral"], hover_color=COLORS["btn_neutral_hover"])
        
        date_str = self.var_date.get()
        try:
            d = datetime.strptime(date_str, "%d/%m/%Y").date()
            self._load_sales(d, d)
        except ValueError:
            AlertModal(self, "Fecha inválida", "Por favor ingrese la fecha en formato dd/mm/aaaa.", kind="warning")

    def _load_sales(self, d_from: date, d_to: date):
        try:
            with SessionLocal() as session:
                repo = SaleRepository(session)
                sales = repo.get_by_date_range(d_from, d_to, limit=1000)
                
            rows = []
            total_sum = Decimal("0")
            for sale in sales:
                fecha = sale.created_at.strftime("%d/%m/%Y %H:%M") if sale.created_at else "—"
                cliente = sale.customer.name if sale.customer else "Consumidor Final"
                total_fmt = f"${sale.total:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
                metodo = sale.payment_method.capitalize()
                estado = "✔ Completada" if sale.status == "completed" else sale.status
                rows.append([str(sale.id), fecha, cliente, total_fmt, metodo, estado])
                
                total_sum += sale.total
                
            self.table.load(rows)
            total_fmt_str = f"${total_sum:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
            self.lbl_totals.configure(text=f"Total: {total_fmt_str}")
        except Exception as e:
            logger.error(f"Error cargando ventas: {e}")
            AlertModal(self, "Error", f"Ocurrió un error al cargar las ventas:\n{e}", kind="error")
