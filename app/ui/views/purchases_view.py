# app/ui/views/purchases_view.py
from decimal import Decimal, InvalidOperation
from typing import Callable

import customtkinter as ctk

from app.core.logging import get_logger
from app.database import SessionLocal
from app.repository.supplier_repository import SupplierRepository
from app.services.product_service import ProductService
from app.services.purchase_service import PurchaseInput, PurchaseItemInput, PurchaseService
from app.ui.components.data_table import DataTable
from app.ui.components.modal import AlertModal, ConfirmModal
from app.ui.components.search_bar import SearchBar
from app.ui.session import AppSession
from app.ui.components import AppShell, ShellConfig
from app.ui.theme import COLORS, FONTS, SIZES

logger = get_logger(__name__)

STATUS_LABELS = {
    "pending":   "⏳ Pendiente",
    "received":  "✔ Recibida",
    "cancelled": "✖ Cancelada",
}

STATUS_COLORS = {
    "pending":   COLORS["warning"],
    "received":  COLORS["success"],
    "cancelled": COLORS["text_disabled"],
}


class PurchasesView(ctk.CTkFrame):
    """
    Vista de Compras.

    Tabs:
        1. Órdenes de compra  — listado con estado, proveedor, total
        2. Nueva orden        — formulario para crear orden con items
        3. Recibir mercadería — recepcionar una orden pendiente

    Flujo:
        1. Se crea una orden (estado: Pendiente) con los productos y costos
        2. Cuando llega la mercadería se recepciona → el stock se incrementa
        3. La orden queda en estado Recibida (inmutable)
    """

    def __init__(self, master: ctk.CTk, navigate: Callable, **kwargs):
        super().__init__(master, fg_color=COLORS["bg_main"], **kwargs)
        self.navigate = navigate
        self._selected_purchase_id: int | None = None
        self._selected_purchase_status: str = ""
        self._suppliers: list = []
        self._cart_items: list[dict] = []   # [{product_id, name, qty, cost}]
        self._build_ui()
        self._load_suppliers()
        self._load_purchases()

    # ── Construccion ──────────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        shell = AppShell(
            self,
            navigate=self.navigate,
            config=ShellConfig(title="Compras", active_view="purchases"),
        )
        shell.pack(fill="both", expand=True)

        main = ctk.CTkFrame(shell.content, fg_color="transparent")
        main.pack(side="left", fill="both", expand=True)

        # Cabecera
        header = ctk.CTkFrame(main, fg_color="transparent")
        header.pack(fill="x", pady=(0, SIZES["padding"]))
        ctk.CTkLabel(header, text="Compras", font=FONTS["subtitle"],
                     text_color=COLORS["text_primary"]).pack(side="left")

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

        self.tabview.add("📋  Órdenes")
        self.tabview.add("➕  Nueva orden")
        self.tabview.add("📦  Recibir mercadería")

        self._build_tab_orders(self.tabview.tab("📋  Órdenes"))
        self._build_tab_new(self.tabview.tab("➕  Nueva orden"))
        self._build_tab_receive(self.tabview.tab("📦  Recibir mercadería"))

    # ── Tab 1: Listado de órdenes ─────────────────────────────────────────────

    def _build_tab_orders(self, parent: ctk.CTkFrame) -> None:
        pad = SIZES["padding_sm"]

        top = ctk.CTkFrame(parent, fg_color="transparent")
        top.pack(fill="x", padx=pad, pady=pad)

        ctk.CTkButton(
            top, text="↺  Actualizar", height=30, width=110,
            font=FONTS["small"],
            fg_color=COLORS["btn_neutral"], hover_color=COLORS["btn_neutral_hover"],
            command=self._load_purchases,
        ).pack(side="right")

        ctk.CTkButton(
            top, text="⚠  Solo pendientes", height=30, width=150,
            font=FONTS["small"],
            fg_color=COLORS["warning"], hover_color="#c87f00",
            text_color="#000000",
            command=self._load_pending_only,
        ).pack(side="right", padx=(0, 8))

        self.table_orders = DataTable(
            parent,
            columns=["#", "Fecha", "Proveedor", "Referencia", "Total", "Estado"],
            col_widths=[50, 130, 200, 140, 110, 120],
            on_select=self._on_order_select,
        )
        self.table_orders.pack(fill="both", expand=True, padx=pad, pady=(0, pad))

        # Acciones sobre la orden seleccionada
        actions = ctk.CTkFrame(parent, fg_color="transparent")
        actions.pack(fill="x", padx=pad, pady=(0, pad))

        self.btn_receive_order = ctk.CTkButton(
            actions,
            text="📦  Recibir esta orden",
            height=36, font=FONTS["body_bold"],
            fg_color=COLORS["btn_success"], hover_color=COLORS["btn_success_hover"],
            state="disabled",
            command=self._go_to_receive,
        )
        self.btn_receive_order.pack(side="left", padx=(0, 8))

        self.btn_cancel_order = ctk.CTkButton(
            actions,
            text="✖  Cancelar orden",
            height=36, font=FONTS["body"],
            fg_color=COLORS["btn_neutral"], hover_color=COLORS["btn_danger"],
            state="disabled",
            command=self._confirm_cancel,
        )
        self.btn_cancel_order.pack(side="left")

    # ── Tab 2: Nueva orden ────────────────────────────────────────────────────

    def _build_tab_new(self, parent: ctk.CTkFrame) -> None:
        pad = SIZES["padding"]

        # Panel superior: datos de la orden
        top = ctk.CTkFrame(parent, fg_color=COLORS["bg_card"], corner_radius=8)
        top.pack(fill="x", padx=pad, pady=pad)

        # Proveedor
        col1 = ctk.CTkFrame(top, fg_color="transparent")
        col1.pack(side="left", fill="x", expand=True, padx=pad, pady=pad)
        ctk.CTkLabel(col1, text="Proveedor (opcional):", font=FONTS["small"],
                     text_color=COLORS["text_secondary"], anchor="w").pack(fill="x")
        self.var_supplier = ctk.StringVar(value="Sin proveedor")
        self.opt_supplier = ctk.CTkOptionMenu(
            col1, variable=self.var_supplier,
            values=["Sin proveedor"],
            height=SIZES["input_height"],
            font=FONTS["body"],
            fg_color=COLORS["bg_input"],
            button_color=COLORS["bg_card"],
            button_hover_color=COLORS["accent"],
            text_color=COLORS["text_primary"],
        )
        self.opt_supplier.pack(fill="x", pady=(2, 0))

        # Referencia del proveedor
        col2 = ctk.CTkFrame(top, fg_color="transparent")
        col2.pack(side="left", fill="x", expand=True, padx=pad, pady=pad)
        ctk.CTkLabel(col2, text="Referencia / Remito:", font=FONTS["small"],
                     text_color=COLORS["text_secondary"], anchor="w").pack(fill="x")
        self.var_reference = ctk.StringVar()
        ctk.CTkEntry(
            col2, textvariable=self.var_reference,
            placeholder_text="Nro. de remito o factura del proveedor",
            height=SIZES["input_height"],
            font=FONTS["body"],
            fg_color=COLORS["bg_input"], border_color=COLORS["border"],
            text_color=COLORS["text_primary"],
        ).pack(fill="x", pady=(2, 0))

        # Notas
        col3 = ctk.CTkFrame(top, fg_color="transparent")
        col3.pack(side="left", fill="x", expand=True, padx=pad, pady=pad)
        ctk.CTkLabel(col3, text="Notas:", font=FONTS["small"],
                     text_color=COLORS["text_secondary"], anchor="w").pack(fill="x")
        self.var_purchase_notes = ctk.StringVar()
        ctk.CTkEntry(
            col3, textvariable=self.var_purchase_notes,
            height=SIZES["input_height"],
            font=FONTS["body"],
            fg_color=COLORS["bg_input"], border_color=COLORS["border"],
            text_color=COLORS["text_primary"],
        ).pack(fill="x", pady=(2, 0))

        # Buscador de productos
        ctk.CTkLabel(parent, text="Agregar producto a la orden:",
                     font=FONTS["small"], text_color=COLORS["text_secondary"],
                     anchor="w").pack(fill="x", padx=pad)

        search_row = ctk.CTkFrame(parent, fg_color="transparent")
        search_row.pack(fill="x", padx=pad, pady=(2, SIZES["padding_sm"]))
        search_row.columnconfigure(0, weight=1)

        self.search_product = SearchBar(
            search_row,
            placeholder="Buscar producto por nombre o SKU...",
            on_search=self._search_product_for_order,
        )
        self.search_product.grid(row=0, column=0, sticky="ew", padx=(0, 8))

        # Resultado de busqueda (dropdown)
        self.search_results_new = ctk.CTkScrollableFrame(
            parent, fg_color=COLORS["bg_input"], height=0,
        )
        self.search_results_new.pack(fill="x", padx=pad)

        # Tabla de items de la orden
        ctk.CTkLabel(parent, text="Items de la orden:", font=FONTS["small"],
                     text_color=COLORS["text_secondary"], anchor="w").pack(
            fill="x", padx=pad, pady=(SIZES["padding_sm"], 0))

        self.table_new_items = DataTable(
            parent,
            columns=["Producto", "Cantidad", "Costo unit.", "Subtotal"],
            col_widths=[300, 90, 120, 120],
            page_size=10,
        )
        self.table_new_items.pack(fill="both", expand=True, padx=pad)

        # Pie: total + botones
        footer = ctk.CTkFrame(parent, fg_color="transparent")
        footer.pack(fill="x", padx=pad, pady=pad)

        self.lbl_order_total = ctk.CTkLabel(
            footer, text="Total: $0,00",
            font=("Consolas", 16, "bold"), text_color=COLORS["accent"],
        )
        self.lbl_order_total.pack(side="left")

        ctk.CTkButton(
            footer, text="🗑  Limpiar",
            height=36, width=100,
            font=FONTS["small"],
            fg_color=COLORS["btn_neutral"], hover_color=COLORS["btn_neutral_hover"],
            command=self._clear_new_order,
        ).pack(side="right", padx=(8, 0))

        ctk.CTkButton(
            footer, text="💾  Crear orden",
            height=36,
            font=FONTS["body_bold"],
            fg_color=COLORS["btn_success"], hover_color=COLORS["btn_success_hover"],
            command=self._create_order,
        ).pack(side="right")

    # ── Tab 3: Recibir mercadería ─────────────────────────────────────────────

    def _build_tab_receive(self, parent: ctk.CTkFrame) -> None:
        pad = SIZES["padding"]

        # Info de la orden a recepcionar
        self.lbl_receive_title = ctk.CTkLabel(
            parent,
            text="Seleccione una orden pendiente en la pestaña Órdenes\n"
                 "y presione 'Recibir esta orden'.",
            font=FONTS["body"], text_color=COLORS["text_disabled"], justify="center",
        )
        self.lbl_receive_title.pack(pady=pad)

        info = ctk.CTkFrame(parent, fg_color=COLORS["bg_card"], corner_radius=8)
        info.pack(fill="x", padx=pad)

        self.lbl_receive_info = ctk.CTkLabel(
            info, text="",
            font=FONTS["body"], text_color=COLORS["text_secondary"],
            justify="left", anchor="w",
        )
        self.lbl_receive_info.pack(fill="x", padx=pad, pady=pad)

        ctk.CTkLabel(parent, text="Items que se incorporarán al stock:",
                     font=FONTS["small"], text_color=COLORS["text_secondary"],
                     anchor="w").pack(fill="x", padx=pad, pady=(pad, 0))

        self.table_receive_items = DataTable(
            parent,
            columns=["Producto", "Cantidad a recibir", "Costo unit.", "Subtotal"],
            col_widths=[320, 140, 120, 120],
            page_size=15,
        )
        self.table_receive_items.pack(fill="both", expand=True, padx=pad, pady=SIZES["padding_sm"])

        self.btn_confirm_receive = ctk.CTkButton(
            parent,
            text="✔  Confirmar recepción — incrementar stock",
            height=48,
            font=("Segoe UI", 14, "bold"),
            fg_color=COLORS["btn_success"], hover_color=COLORS["btn_success_hover"],
            state="disabled",
            command=self._confirm_receive,
        )
        self.btn_confirm_receive.pack(fill="x", padx=pad, pady=(0, pad))

    # ── Carga de datos ────────────────────────────────────────────────────────

    def _load_suppliers(self) -> None:
        try:
            with SessionLocal() as session:
                self._suppliers = SupplierRepository(session).get_active()
            names = ["Sin proveedor"] + [s.name for s in self._suppliers]
            self.opt_supplier.configure(values=names)
        except Exception as e:
            logger.error(f"Error cargando proveedores: {e}")

    def _load_purchases(self) -> None:
        try:
            with SessionLocal() as session:
                purchases = PurchaseService(session).get_recent_purchases(limit=100)
            self._purchases_cache = purchases
            self.table_orders.load(self._purchases_to_rows(purchases))
            self._reset_order_actions()
        except Exception as e:
            logger.error(f"Error cargando compras: {e}")

    def _load_pending_only(self) -> None:
        try:
            with SessionLocal() as session:
                purchases = PurchaseService(session).get_pending_purchases()
            self._purchases_cache = purchases
            self.table_orders.load(self._purchases_to_rows(purchases))
            self._reset_order_actions()
        except Exception as e:
            logger.error(f"Error cargando pendientes: {e}")

    # ── Seleccion de orden ────────────────────────────────────────────────────

    def _on_order_select(self, row_data: list) -> None:
        index = self.table_orders._selected_index
        if index is None or not hasattr(self, "_purchases_cache"):
            return

        page_start = self.table_orders._current_page * self.table_orders.page_size
        abs_index  = page_start + index
        if abs_index >= len(self._purchases_cache):
            return

        purchase = self._purchases_cache[abs_index]
        self._selected_purchase_id     = purchase.id
        self._selected_purchase_status = purchase.status

        is_pending = purchase.status == "pending"
        self.btn_receive_order.configure(state="normal" if is_pending else "disabled")
        self.btn_cancel_order.configure(state="normal"  if is_pending else "disabled")

    def _reset_order_actions(self) -> None:
        self._selected_purchase_id     = None
        self._selected_purchase_status = ""
        self.btn_receive_order.configure(state="disabled")
        self.btn_cancel_order.configure(state="disabled")

    # ── Cancelar orden ────────────────────────────────────────────────────────

    def _confirm_cancel(self) -> None:
        if not self._selected_purchase_id:
            return
        ConfirmModal(
            self,
            title="Cancelar orden",
            message="¿Cancelar esta orden de compra?\nEsta acción no se puede deshacer.",
            on_confirm=self._do_cancel,
            confirm_text="Cancelar orden",
            danger=True,
        )

    def _do_cancel(self) -> None:
        try:
            with SessionLocal() as session:
                PurchaseService(session).cancel_purchase(self._selected_purchase_id)
            AlertModal(self, "Orden cancelada", "La orden fue cancelada.", kind="success")
            self._load_purchases()
        except Exception as e:
            AlertModal(self, "Error", str(e), kind="error")

    # ── Nueva orden ───────────────────────────────────────────────────────────

    def _search_product_for_order(self, query: str) -> None:
        try:
            with SessionLocal() as session:
                products = ProductService(session).search_products(query)

            for w in self.search_results_new.winfo_children():
                w.destroy()

            if not products:
                self.search_results_new.configure(height=0)
                return

            self.search_results_new.configure(height=min(len(products) * 38, 190))

            for product in products:
                row = ctk.CTkFrame(
                    self.search_results_new,
                    fg_color=COLORS["bg_input"],
                    cursor="hand2", height=34,
                )
                row.pack(fill="x", pady=1)
                row.pack_propagate(False)

                ctk.CTkLabel(
                    row, text=f"{product.sku} — {product.name}",
                    font=FONTS["body"], text_color=COLORS["text_primary"], anchor="w",
                ).pack(side="left", padx=SIZES["padding_sm"], fill="x", expand=True)

                row.bind("<Button-1>", lambda e, p=product: self._open_add_item_dialog(p))
                for child in row.winfo_children():
                    child.bind("<Button-1>", lambda e, p=product: self._open_add_item_dialog(p))

        except Exception as e:
            logger.error(f"Error buscando producto: {e}")

    def _open_add_item_dialog(self, product) -> None:
        """Dialogo inline para ingresar cantidad y costo del item."""
        for w in self.search_results_new.winfo_children():
            w.destroy()
        self.search_results_new.configure(height=0)
        self.search_product.clear()

        dialog = ctk.CTkToplevel(self)
        dialog.title(f"Agregar: {product.name}")
        dialog.resizable(False, False)
        dialog.configure(fg_color=COLORS["bg_panel"])
        dialog.grab_set()

        # Centrar
        dialog.update_idletasks()
        px, py = self.winfo_rootx(), self.winfo_rooty()
        pw, ph = self.winfo_width(), self.winfo_height()
        dialog.geometry(f"360x260+{px + (pw - 360)//2}+{py + (ph - 260)//2}")

        ctk.CTkLabel(dialog, text=product.name, font=FONTS["heading"],
                     text_color=COLORS["text_primary"]).pack(padx=24, pady=(20, 4))
        ctk.CTkLabel(dialog, text=f"SKU: {product.sku}", font=FONTS["small"],
                     text_color=COLORS["text_secondary"]).pack(padx=24)

        ctk.CTkFrame(dialog, fg_color=COLORS["border"], height=1).pack(fill="x", pady=12)

        row_qty = ctk.CTkFrame(dialog, fg_color="transparent")
        row_qty.pack(fill="x", padx=24)
        ctk.CTkLabel(row_qty, text="Cantidad:", font=FONTS["body"],
                     text_color=COLORS["text_secondary"], width=100).pack(side="left")
        var_qty = ctk.StringVar(value="1")
        ctk.CTkEntry(row_qty, textvariable=var_qty, width=100,
                     height=32, font=FONTS["body"],
                     fg_color=COLORS["bg_input"], border_color=COLORS["border"],
                     text_color=COLORS["text_primary"]).pack(side="left")

        row_cost = ctk.CTkFrame(dialog, fg_color="transparent")
        row_cost.pack(fill="x", padx=24, pady=8)
        ctk.CTkLabel(row_cost, text="Costo unit.:", font=FONTS["body"],
                     text_color=COLORS["text_secondary"], width=100).pack(side="left")
        var_cost = ctk.StringVar(value="0.00")
        ctk.CTkEntry(row_cost, textvariable=var_cost, width=100,
                     height=32, font=FONTS["mono"],
                     fg_color=COLORS["bg_input"], border_color=COLORS["border"],
                     text_color=COLORS["text_primary"]).pack(side="left")

        def _add():
            try:
                qty  = Decimal(var_qty.get().replace(",", "."))
                cost = Decimal(var_cost.get().replace(",", "."))
                if qty <= 0:
                    raise ValueError
            except (InvalidOperation, ValueError):
                return

            # Si ya existe el producto en el carrito, sumar cantidad
            for item in self._cart_items:
                if item["product_id"] == product.id:
                    item["qty"]  += qty
                    item["cost"]  = cost
                    break
            else:
                self._cart_items.append({
                    "product_id": product.id,
                    "name":       product.name,
                    "qty":        qty,
                    "cost":       cost,
                })

            dialog.destroy()
            self._refresh_new_order_table()

        ctk.CTkButton(dialog, text="Agregar al pedido", height=36,
                      font=FONTS["body_bold"],
                      fg_color=COLORS["btn_success"],
                      hover_color=COLORS["btn_success_hover"],
                      command=_add).pack(fill="x", padx=24, pady=(4, 0))
        ctk.CTkButton(dialog, text="Cancelar", height=32,
                      font=FONTS["small"],
                      fg_color=COLORS["btn_neutral"],
                      hover_color=COLORS["btn_neutral_hover"],
                      command=dialog.destroy).pack(fill="x", padx=24, pady=(6, 20))

        dialog.bind("<Return>", lambda e: _add())
        dialog.bind("<Escape>", lambda e: dialog.destroy())

    def _refresh_new_order_table(self) -> None:
        rows = []
        total = Decimal("0")
        for item in self._cart_items:
            subtotal = item["qty"] * item["cost"]
            total   += subtotal
            rows.append([
                item["name"],
                str(int(item["qty"])),
                f"${item['cost']:,.2f}",
                f"${subtotal:,.2f}",
            ])
        self.table_new_items.load(rows)
        self.lbl_order_total.configure(
            text=f"Total: ${total:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        )

    def _clear_new_order(self) -> None:
        self._cart_items.clear()
        self.var_supplier.set("Sin proveedor")
        self.var_reference.set("")
        self.var_purchase_notes.set("")
        self._refresh_new_order_table()

    def _create_order(self) -> None:
        if not self._cart_items:
            AlertModal(self, "Sin productos",
                       "Agregue al menos un producto a la orden.", kind="warning")
            return

        supplier_name = self.var_supplier.get()
        supplier_id   = None
        for s in self._suppliers:
            if s.name == supplier_name:
                supplier_id = s.id
                break

        items = [
            PurchaseItemInput(
                product_id=i["product_id"],
                quantity=i["qty"],
                unit_cost=i["cost"],
            )
            for i in self._cart_items
        ]
        data = PurchaseInput(
            items=items,
            supplier_id=supplier_id,
            supplier_reference=self.var_reference.get().strip() or None,
            notes=self.var_purchase_notes.get().strip() or None,
        )

        try:
            with SessionLocal() as session:
                purchase = PurchaseService(session).create_purchase(
                    data, user_id=AppSession.user_id
                )
            AlertModal(
                self, "Orden creada",
                f"Orden #{purchase.id} creada con estado Pendiente.\n"
                "Cuando llegue la mercadería, recepciónela desde la pestaña Órdenes.",
                kind="success",
            )
            self._clear_new_order()
            self._load_purchases()
            self.tabview.set("📋  Órdenes")
        except Exception as e:
            logger.error(f"Error creando orden: {e}")
            AlertModal(self, "Error", str(e), kind="error")

    # ── Recepcionar orden ─────────────────────────────────────────────────────

    def _go_to_receive(self) -> None:
        if not self._selected_purchase_id:
            return

        try:
            with SessionLocal() as session:
                from app.repository.purchase_repository import PurchaseRepository
                purchase = PurchaseRepository(session).get_with_details(self._selected_purchase_id)

            if not purchase:
                AlertModal(self, "Error", "No se encontró la orden.", kind="error")
                return

            supplier_name = purchase.supplier.name if purchase.supplier else "Sin proveedor"
            self.lbl_receive_title.configure(
                text=f"Orden #{purchase.id}  —  {supplier_name}",
                text_color=COLORS["text_primary"],
            )
            self.lbl_receive_info.configure(
                text=(
                    f"Referencia: {purchase.supplier_reference or '—'}    "
                    f"Total: ${purchase.total:,.2f}    "
                    f"Notas: {purchase.notes or '—'}"
                )
            )

            rows = []
            for d in purchase.details:
                rows.append([
                    d.product.name if d.product else str(d.product_id),
                    str(int(d.quantity)),
                    f"${d.unit_cost:,.2f}",
                    f"${d.subtotal:,.2f}",
                ])
            self.table_receive_items.load(rows)
            self.btn_confirm_receive.configure(state="normal")
            self.tabview.set("📦  Recibir mercadería")

        except Exception as e:
            logger.error(f"Error preparando recepcion: {e}")
            AlertModal(self, "Error", str(e), kind="error")

    def _confirm_receive(self) -> None:
        purchase_id = self._selected_purchase_id
        ConfirmModal(
            self,
            title="Confirmar recepción",
            message=(
                f"¿Confirmar la recepción de la orden #{purchase_id}?\n\n"
                "Esta acción incrementará el stock de todos los\n"
                "productos de la orden y no se puede deshacer."
            ),
            on_confirm=lambda: self._do_receive(purchase_id),
            confirm_text="Confirmar recepción",
        )

    def _do_receive(self, purchase_id: int) -> None:
        try:
            with SessionLocal() as session:
                PurchaseService(session).receive_purchase(
                    purchase_id, user_id=AppSession.user_id
                )
            AlertModal(
                self, "Mercadería recibida",
                f"Orden #{purchase_id} recepcionada.\nEl stock fue incrementado.",
                kind="success",
            )
            self.btn_confirm_receive.configure(state="disabled")
            self.lbl_receive_title.configure(
                text="Seleccione una orden pendiente en la pestaña Órdenes\n"
                     "y presione 'Recibir esta orden'.",
                text_color=COLORS["text_disabled"],
            )
            self.table_receive_items.clear()
            self._load_purchases()
            self.tabview.set("📋  Órdenes")
        except Exception as e:
            logger.error(f"Error recepcionando: {e}")
            AlertModal(self, "Error", str(e), kind="error")

    # ── Helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def _purchases_to_rows(purchases: list) -> list[list]:
        rows = []
        for p in purchases:
            supplier = p.supplier.name if p.supplier else "—"
            fecha    = p.created_at.strftime("%d/%m/%Y %H:%M") if p.created_at else "—"
            total    = f"${p.total:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
            estado   = STATUS_LABELS.get(p.status, p.status)
            rows.append([str(p.id), fecha, supplier,
                         p.supplier_reference or "—", total, estado])
        return rows
