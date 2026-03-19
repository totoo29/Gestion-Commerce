# app/ui/views/stock_view.py
from decimal import Decimal, InvalidOperation
from typing import Callable

import customtkinter as ctk

from app.core.logging import get_logger
from app.database import SessionLocal
from app.services.product_service import ProductService
from app.services.stock_service import StockService
from app.ui.components.data_table import DataTable
from app.ui.components.modal import AlertModal, ConfirmModal
from app.ui.components.search_bar import SearchBar
from app.ui.components.stock_badge import StockBadge
from app.ui.session import AppSession
from app.ui.components import AppShell, ShellConfig
from app.ui.theme import COLORS, FONTS, SIZES

logger = get_logger(__name__)

# Etiquetas legibles para cada tipo de movimiento
MOVEMENT_LABELS = {
    "sale":       "Venta",
    "purchase":   "Compra",
    "adjustment": "Ajuste manual",
    "return":     "Devolución",
    "loss":       "Merma",
    "initial":    "Stock inicial",
}


class StockView(ctk.CTkFrame):
    """
    Vista de Stock.

    Tabs:
        1. Inventario actual  — tabla con stock de todos los productos, alertas visuales
        2. Ajuste manual      — formulario para corregir stock por inventario físico
        3. Movimientos        — historial de movimientos de un producto

    Operaciones:
        - Ver stock actual con badge CRÍTICO / BAJO / OK
        - Filtrar por productos con stock crítico
        - Ajustar stock manualmente (con nota obligatoria)
        - Cambiar stock mínimo de un producto
        - Ver historial completo de movimientos de cualquier producto
    """

    def __init__(self, master: ctk.CTk, navigate: Callable, **kwargs):
        super().__init__(master, fg_color=COLORS["bg_main"], **kwargs)
        self.navigate = navigate
        self._selected_product_id: int | None = None
        self._products_cache: list = []
        self._build_ui()
        self._load_inventory()

    # ── Construccion ──────────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        shell = AppShell(
            self,
            navigate=self.navigate,
            config=ShellConfig(title="Inventario", active_view="stock"),
        )
        shell.pack(fill="both", expand=True)

        main = ctk.CTkFrame(shell.content, fg_color="transparent")
        main.pack(side="left", fill="both", expand=True)

        # Cabecera
        header = ctk.CTkFrame(main, fg_color="transparent")
        header.pack(fill="x", pady=(0, SIZES["padding"]))

        ctk.CTkLabel(header, text="Stock e Inventario", font=FONTS["subtitle"],
                     text_color=COLORS["text_primary"]).pack(side="left")

        self.btn_only_critical = ctk.CTkButton(
            header,
            text="⚠  Solo críticos",
            height=32, width=140,
            font=FONTS["small"],
            fg_color=COLORS["warning"],
            hover_color="#c87f00",
            text_color="#000000",
            command=self._load_critical_only,
        )
        self.btn_only_critical.pack(side="right", padx=(8, 0))

        ctk.CTkButton(
            header,
            text="↺  Actualizar",
            height=32, width=110,
            font=FONTS["small"],
            fg_color=COLORS["btn_neutral"],
            hover_color=COLORS["btn_neutral_hover"],
            command=self._load_inventory,
        ).pack(side="right")

        # Tabs
        self.tabview = ctk.CTkTabview(
            main,
            fg_color=COLORS["bg_panel"],
            segmented_button_fg_color=COLORS["bg_card"],
            segmented_button_selected_color=COLORS["accent"],
            segmented_button_selected_hover_color=COLORS["accent_hover"],
            segmented_button_unselected_color=COLORS["bg_card"],
            segmented_button_unselected_hover_color=COLORS["btn_neutral_hover"],
            text_color=COLORS["text_primary"],
        )
        self.tabview.pack(fill="both", expand=True)

        self.tabview.add("📦  Inventario")
        self.tabview.add("✏  Ajuste manual")
        self.tabview.add("📋  Movimientos")

        self._build_tab_inventory(self.tabview.tab("📦  Inventario"))
        self._build_tab_adjust(self.tabview.tab("✏  Ajuste manual"))
        self._build_tab_movements(self.tabview.tab("📋  Movimientos"))

    # ── Tab 1: Inventario ─────────────────────────────────────────────────────

    def _build_tab_inventory(self, parent: ctk.CTkFrame) -> None:
        pad = SIZES["padding_sm"]

        self.search_inventory = SearchBar(
            parent,
            placeholder="Buscar producto...",
            on_search=self._search_inventory,
            on_clear=self._load_inventory,
            auto_search=True,
            min_chars=2,
        )
        self.search_inventory.pack(fill="x", padx=pad, pady=pad)

        self.table_inventory = DataTable(
            parent,
            columns=["SKU", "Nombre", "Stock actual", "Stock mínimo", "Estado"],
            col_widths=[90, 300, 110, 110, 90],
            on_select=self._on_inventory_select,
        )
        self.table_inventory.pack(fill="both", expand=True, padx=pad, pady=(0, pad))

    # ── Tab 2: Ajuste manual ──────────────────────────────────────────────────

    def _build_tab_adjust(self, parent: ctk.CTkFrame) -> None:
        pad = SIZES["padding"]

        form = ctk.CTkFrame(parent, fg_color="transparent", width=480)
        form.pack(anchor="center", padx=pad, pady=pad)

        ctk.CTkLabel(
            form,
            text="Ajuste manual de inventario",
            font=FONTS["heading"],
            text_color=COLORS["text_primary"],
        ).pack(anchor="w", pady=(0, 4))

        ctk.CTkLabel(
            form,
            text="Seleccione un producto en la tabla de Inventario\n"
                 "para cargar sus datos en este formulario.",
            font=FONTS["small"],
            text_color=COLORS["text_secondary"],
            justify="left",
        ).pack(anchor="w", pady=(0, SIZES["padding"]))

        # Producto seleccionado
        ctk.CTkLabel(form, text="Producto seleccionado:", font=FONTS["small"],
                     text_color=COLORS["text_secondary"], anchor="w").pack(fill="x")
        self.lbl_adjust_product = ctk.CTkLabel(
            form, text="— Ninguno —",
            font=FONTS["body_bold"], text_color=COLORS["accent"],
        )
        self.lbl_adjust_product.pack(anchor="w", pady=(2, SIZES["padding"]))

        # Stock actual (solo lectura)
        row_current = ctk.CTkFrame(form, fg_color="transparent")
        row_current.pack(fill="x", pady=(0, SIZES["padding_sm"]))
        ctk.CTkLabel(row_current, text="Stock actual:", font=FONTS["body"],
                     text_color=COLORS["text_secondary"]).pack(side="left")
        self.lbl_current_stock = ctk.CTkLabel(
            row_current, text="—",
            font=FONTS["mono"], text_color=COLORS["text_primary"],
        )
        self.lbl_current_stock.pack(side="right")

        # Nuevo stock
        ctk.CTkLabel(form, text="Nuevo stock (cantidad real contada):", font=FONTS["small"],
                     text_color=COLORS["text_secondary"], anchor="w").pack(fill="x")
        self.var_new_qty = ctk.StringVar()
        self.entry_new_qty = ctk.CTkEntry(
            form, textvariable=self.var_new_qty,
            placeholder_text="Ej: 150",
            height=SIZES["input_height"] + 4,
            font=("Consolas", 18, "bold"),
            fg_color=COLORS["bg_input"],
            border_color=COLORS["border_focus"],
            text_color=COLORS["text_primary"],
        )
        self.entry_new_qty.pack(fill="x", pady=(2, SIZES["padding_sm"]))

        # Stock mínimo
        ctk.CTkLabel(form, text="Stock mínimo (alerta):", font=FONTS["small"],
                     text_color=COLORS["text_secondary"], anchor="w").pack(fill="x")
        self.var_min_qty = ctk.StringVar()
        ctk.CTkEntry(
            form, textvariable=self.var_min_qty,
            height=SIZES["input_height"],
            font=FONTS["body"],
            fg_color=COLORS["bg_input"],
            border_color=COLORS["border"],
            text_color=COLORS["text_primary"],
        ).pack(fill="x", pady=(2, SIZES["padding_sm"]))

        # Nota
        ctk.CTkLabel(form, text="Motivo del ajuste *:", font=FONTS["small"],
                     text_color=COLORS["text_secondary"], anchor="w").pack(fill="x")
        self.var_notes = ctk.StringVar()
        ctk.CTkEntry(
            form, textvariable=self.var_notes,
            placeholder_text="Ej: Inventario físico mensual, corrección de diferencia...",
            height=SIZES["input_height"],
            font=FONTS["body"],
            fg_color=COLORS["bg_input"],
            border_color=COLORS["border"],
            text_color=COLORS["text_primary"],
        ).pack(fill="x", pady=(2, SIZES["padding"]))

        self.btn_adjust = ctk.CTkButton(
            form,
            text="✔  Aplicar ajuste",
            height=SIZES["btn_height"] + 4,
            font=FONTS["body_bold"],
            fg_color=COLORS["btn_success"],
            hover_color=COLORS["btn_success_hover"],
            state="disabled",
            command=self._confirm_adjust,
        )
        self.btn_adjust.pack(fill="x")

    # ── Tab 3: Movimientos ────────────────────────────────────────────────────

    def _build_tab_movements(self, parent: ctk.CTkFrame) -> None:
        pad = SIZES["padding_sm"]

        top = ctk.CTkFrame(parent, fg_color="transparent")
        top.pack(fill="x", padx=pad, pady=pad)

        ctk.CTkLabel(top, text="Producto:", font=FONTS["body"],
                     text_color=COLORS["text_secondary"]).pack(side="left")
        self.lbl_movements_product = ctk.CTkLabel(
            top, text="Seleccione un producto en la tabla de Inventario",
            font=FONTS["body"], text_color=COLORS["text_disabled"],
        )
        self.lbl_movements_product.pack(side="left", padx=8)

        ctk.CTkButton(
            top, text="↺  Recargar",
            height=28, width=100, font=FONTS["small"],
            fg_color=COLORS["btn_neutral"],
            hover_color=COLORS["btn_neutral_hover"],
            command=self._load_movements,
        ).pack(side="right")

        self.table_movements = DataTable(
            parent,
            columns=["Fecha", "Tipo", "Cantidad", "Antes", "Después", "Nota"],
            col_widths=[140, 110, 90, 90, 90, 260],
            page_size=30,
        )
        self.table_movements.pack(fill="both", expand=True, padx=pad, pady=(0, pad))

    # ── Carga de datos ────────────────────────────────────────────────────────

    def _load_inventory(self, query: str = "") -> None:
        try:
            with SessionLocal() as session:
                products = ProductService(session).get_all_products(limit=500)

            self._products_cache = products
            rows = self._products_to_rows(products)
            self.table_inventory.load(rows)
        except Exception as e:
            logger.error(f"Error cargando inventario: {e}")
            AlertModal(self, "Error", str(e), kind="error")

    def _load_critical_only(self) -> None:
        try:
            with SessionLocal() as session:
                critical = StockService(session).get_critical_items()

            # Filtrar el cache por los ids criticos
            critical_ids = {s.product_id for s in critical}
            filtered = [p for p in self._products_cache if p.id in critical_ids]
            self.table_inventory.load(self._products_to_rows(filtered))
        except Exception as e:
            logger.error(f"Error cargando criticos: {e}")

    def _search_inventory(self, query: str) -> None:
        try:
            with SessionLocal() as session:
                products = ProductService(session).search_products(query)
            self._products_cache = products
            self.table_inventory.load(self._products_to_rows(products))
        except Exception as e:
            logger.error(f"Error buscando: {e}")

    def _load_movements(self) -> None:
        if not self._selected_product_id:
            return
        try:
            with SessionLocal() as session:
                movements = StockService(session).get_stock_movements(
                    self._selected_product_id, limit=100
                )

            rows = []
            for m in movements:
                tipo = MOVEMENT_LABELS.get(m.movement_type, m.movement_type)
                qty_str = f"+{m.quantity}" if m.quantity >= 0 else str(m.quantity)
                rows.append([
                    m.created_at.strftime("%d/%m/%Y %H:%M") if m.created_at else "—",
                    tipo,
                    qty_str,
                    str(int(m.stock_before)),
                    str(int(m.stock_after)),
                    m.notes or "—",
                ])
            self.table_movements.load(rows)
        except Exception as e:
            logger.error(f"Error cargando movimientos: {e}")

    # ── Seleccion de producto ─────────────────────────────────────────────────

    def _on_inventory_select(self, row_data: list) -> None:
        index = self.table_inventory._selected_index
        if index is None or not self._products_cache:
            return

        page_start = self.table_inventory._current_page * self.table_inventory.page_size
        abs_index = page_start + index
        if abs_index >= len(self._products_cache):
            return

        product = self._products_cache[abs_index]
        self._selected_product_id = product.id
        stock = product.stock

        # Actualizar tab Ajuste
        self.lbl_adjust_product.configure(text=f"{product.sku} — {product.name}")
        current = stock.quantity if stock else Decimal("0")
        self.lbl_current_stock.configure(text=f"{current:,.0f} {product.unit}")
        self.var_new_qty.set(str(int(current)))
        self.var_min_qty.set(str(int(stock.min_quantity)) if stock else "5")
        self.var_notes.set("")
        self.btn_adjust.configure(state="normal")

        # Actualizar tab Movimientos
        self.lbl_movements_product.configure(
            text=f"{product.sku} — {product.name}",
            text_color=COLORS["text_primary"],
        )
        self._load_movements()

    # ── Ajuste de stock ───────────────────────────────────────────────────────

    def _confirm_adjust(self) -> None:
        if not self._selected_product_id:
            return

        new_qty_str = self.var_new_qty.get().strip().replace(",", ".")
        notes = self.var_notes.get().strip()

        if not new_qty_str:
            AlertModal(self, "Campo requerido", "Ingrese la nueva cantidad.", kind="warning")
            self.entry_new_qty.focus_set()
            return

        try:
            new_qty = Decimal(new_qty_str)
            if new_qty < 0:
                raise ValueError
        except (InvalidOperation, ValueError):
            AlertModal(self, "Cantidad inválida",
                       "La cantidad debe ser un número mayor o igual a 0.", kind="error")
            return

        if not notes:
            AlertModal(self, "Motivo requerido",
                       "Describa el motivo del ajuste (inventario físico, corrección, etc.).",
                       kind="warning")
            return

        # Calcular diferencia para mostrar en confirmacion
        current_text = self.lbl_current_stock.cget("text").split()[0].replace(",", "")
        try:
            current = Decimal(current_text)
            diff = new_qty - current
            diff_str = f"+{diff:,.0f}" if diff >= 0 else f"{diff:,.0f}"
            diff_color = "verde" if diff >= 0 else "rojo"
        except Exception:
            diff_str = "desconocida"

        product_name = self.lbl_adjust_product.cget("text")

        ConfirmModal(
            self,
            title="Confirmar ajuste de stock",
            message=(
                f"Producto: {product_name}\n"
                f"Nuevo stock: {new_qty:,.0f}\n"
                f"Diferencia: {diff_str}\n"
                f"Motivo: {notes}"
            ),
            on_confirm=lambda: self._do_adjust(new_qty, notes),
            confirm_text="Aplicar ajuste",
        )

    def _do_adjust(self, new_qty: Decimal, notes: str) -> None:
        try:
            min_qty_str = self.var_min_qty.get().strip()
            min_qty = Decimal(min_qty_str) if min_qty_str else None
        except InvalidOperation:
            min_qty = None

        try:
            with SessionLocal() as session:
                svc = StockService(session)
                svc.adjust_stock(
                    self._selected_product_id,
                    new_quantity=new_qty,
                    notes=notes,
                    user_id=AppSession.user_id,
                )
                if min_qty is not None:
                    svc.update_min_stock(self._selected_product_id, min_qty)

            AlertModal(self, "Ajuste aplicado",
                       f"Stock actualizado a {new_qty:,.0f} unidades.", kind="success")
            self.var_notes.set("")
            self._load_inventory()
            self._load_movements()

        except Exception as e:
            logger.error(f"Error aplicando ajuste: {e}")
            AlertModal(self, "Error", str(e), kind="error")

    # ── Helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def _products_to_rows(products: list) -> list[list]:
        rows = []
        for p in products:
            stock = p.stock
            qty     = stock.quantity     if stock else Decimal("0")
            min_qty = stock.min_quantity if stock else Decimal("0")

            if min_qty > 0 and qty <= min_qty:
                estado = "⛔ CRÍTICO"
            elif min_qty > 0 and qty <= min_qty * Decimal("1.5"):
                estado = "⚠ BAJO"
            else:
                estado = "✔ OK"

            rows.append([
                p.sku,
                p.name,
                f"{qty:,.0f} {p.unit}",
                f"{min_qty:,.0f}",
                estado,
            ])
        return rows
