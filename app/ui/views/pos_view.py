# app/ui/views/pos_view.py
from decimal import Decimal, InvalidOperation
from typing import Callable

import customtkinter as ctk

from app.core.exceptions import (
    ProductoNoEncontradoError,
    StockInsuficienteError,
)
from app.core.logging import get_logger
from app.database import SessionLocal
from app.services.sale_service import SaleInput, SaleItemInput
from app.services.product_service import ProductService
from app.services.sale_service import SaleService
from app.ui.components.modal import AlertModal, ConfirmModal
from app.ui.components.search_bar import SearchBar
from app.ui.components import AppShell, ShellConfig
from app.ui.session import AppSession
from app.ui.theme import COLORS, FONTS, SIZES

logger = get_logger(__name__)


# ── Fila del carrito ──────────────────────────────────────────────────────────

class CartRow(ctk.CTkFrame):
    """
    Una fila en el carrito de compras.
    Muestra nombre, cantidad editable, precio unitario y subtotal.
    El boton X elimina el item del carrito.
    """

    def __init__(
        self,
        master,
        item: "CartItem",
        on_remove: Callable,
        on_qty_change: Callable,
        index: int,
        **kwargs,
    ):
        bg = COLORS["bg_input"] if index % 2 == 0 else COLORS["bg_panel"]
        super().__init__(master, fg_color=bg, corner_radius=0, height=40, **kwargs)
        self.pack_propagate(False)
        self.item = item
        self.on_remove = on_remove
        self.on_qty_change = on_qty_change
        self._build(index)

    def _build(self, index: int) -> None:
        # Nombre del producto (expandible)
        ctk.CTkLabel(
            self,
            text=self.item.name,
            font=FONTS["body"],
            text_color=COLORS["text_primary"],
            anchor="w",
        ).pack(side="left", fill="x", expand=True, padx=(SIZES["padding_sm"], 0))

        # Precio unitario
        ctk.CTkLabel(
            self,
            text=f"${self.item.unit_price:,.2f}",
            font=FONTS["mono"],
            text_color=COLORS["text_secondary"],
            width=100,
        ).pack(side="left", padx=4)

        # Campo de cantidad
        self.qty_var = ctk.StringVar(value=str(self.item.quantity))
        qty_entry = ctk.CTkEntry(
            self,
            textvariable=self.qty_var,
            width=56,
            height=28,
            font=FONTS["body"],
            fg_color=COLORS["bg_input"],
            border_color=COLORS["border"],
            text_color=COLORS["text_primary"],
            justify="center",
        )
        qty_entry.pack(side="left", padx=4)
        qty_entry.bind("<Return>", lambda e: self._apply_qty())
        qty_entry.bind("<FocusOut>", lambda e: self._apply_qty())

        # Subtotal
        self.lbl_subtotal = ctk.CTkLabel(
            self,
            text=f"${self.item.subtotal:,.2f}",
            font=FONTS["mono"],
            text_color=COLORS["text_primary"],
            width=110,
            anchor="e",
        )
        self.lbl_subtotal.pack(side="left", padx=4)

        # Boton eliminar
        ctk.CTkButton(
            self,
            text="✕",
            width=28,
            height=28,
            fg_color=COLORS["btn_danger"],
            hover_color=COLORS["btn_danger_hover"],
            font=FONTS["small"],
            command=lambda: self.on_remove(self.item.product_id),
        ).pack(side="left", padx=(4, SIZES["padding_sm"]))

    def _apply_qty(self) -> None:
        try:
            qty = int(self.qty_var.get())
            if qty < 1:
                raise ValueError
            if qty != self.item.quantity:
                self.on_qty_change(self.item.product_id, qty)
        except ValueError:
            self.qty_var.set(str(self.item.quantity))


# ── Modelo del carrito ────────────────────────────────────────────────────────

class CartItem:
    def __init__(self, product_id: int, name: str, unit_price: Decimal, quantity: int = 1):
        self.product_id = product_id
        self.name = name
        self.unit_price = unit_price
        self.quantity = quantity

    @property
    def subtotal(self) -> Decimal:
        return self.unit_price * self.quantity


# ── Vista principal POS ───────────────────────────────────────────────────────

class POSView(ctk.CTkFrame):
    """
    Punto de Venta.

    Layout:
        [Navbar lateral] | [Panel izquierdo: busqueda + carrito] | [Panel derecho: totales + cobro]

    Flujo:
        1. Cajero escanea o busca producto → se agrega al carrito
        2. Puede editar cantidades o eliminar items
        3. Ingresa monto recibido → sistema calcula vuelto
        4. Confirma → SaleService procesa la venta atomicamente
        5. Se imprime ticket (PDF) y el carrito se limpia
    """

    def __init__(self, master: ctk.CTk, navigate: Callable, **kwargs):
        super().__init__(master, fg_color=COLORS["bg_main"], **kwargs)
        self.navigate = navigate
        self._cart: dict[int, CartItem] = {}  # product_id -> CartItem
        # El valor del descuento se obtiene de ``self.disc_var`` mediante el
        # metodo ``_discount``. No guardamos un atributo separado porque eso
        # chocaba con el nombre del metodo y provocaba un TypeError al intentar
        # llamarlo.
        self._build_ui()
        # Mostrar algunos productos por defecto (limitado) para que el
        # cajero pueda navegar sin tener que tipear nada.
        self.after(200, lambda: self._search_product(""))
        # Foco en busqueda al abrir
        self.after(250, lambda: self.search_bar.focus())

    # ── Construccion de la UI ─────────────────────────────────────────────────

    def _build_ui(self) -> None:
        shell = AppShell(
            self,
            navigate=self.navigate,
            config=ShellConfig(title="Punto de Venta", active_view="pos"),
        )
        shell.pack(fill="both", expand=True)

        root = ctk.CTkFrame(shell.content, fg_color="transparent")
        root.grid(row=0, column=0, sticky="nsew")
        root.grid_rowconfigure(0, weight=1)
        root.grid_columnconfigure(0, weight=1)
        root.grid_columnconfigure(1, weight=0)

        # Panel central/izquierdo: búsqueda + carrito
        left = ctk.CTkFrame(root, fg_color="transparent")
        left.grid(row=0, column=0, sticky="nsew", padx=(0, SIZES["padding"]))
        left.grid_rowconfigure(3, weight=1)

        self._build_left_panel(left)

        # Panel derecho: totales + cobro (sticky visual)
        right = ctk.CTkFrame(
            root,
            fg_color=COLORS["bg_panel"],
            width=340,
            corner_radius=SIZES["radius_lg"],
            border_width=1,
            border_color=COLORS["border"],
        )
        right.grid(row=0, column=1, sticky="ns")
        right.grid_propagate(False)

        self._build_right_panel(right)

    def _build_left_panel(self, parent: ctk.CTkFrame) -> None:
        parent.grid_columnconfigure(0, weight=1)
        parent.grid_rowconfigure(1, weight=1)
        # Buscador (sticky-like)
        search_card = ctk.CTkFrame(
            parent,
            fg_color=COLORS["bg_panel"],
            corner_radius=SIZES["radius_lg"],
            border_width=1,
            border_color=COLORS["border"],
        )
        search_card.grid(row=0, column=0, sticky="ew", pady=(0, SIZES["padding"]))
        search_card.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            search_card,
            text="Buscar producto",
            font=FONTS["heading"],
            text_color=COLORS["text_primary"],
        ).grid(row=0, column=0, sticky="w", padx=SIZES["padding"], pady=(SIZES["padding"], 0))

        # cuando el campo esta vacio queremos mostrar un puñado de
        # productos (ej. los recientes o los mas comunes). para ello
        # aprovechamos que el servicio admite query vacio y simplemente
        # hacemos la busqueda con limite. el callback on_clear se activa cuando
        # el usuario presiona la "✕" de la barra y reseteará la lista.
        self.search_bar = SearchBar(
            search_card,
            placeholder="Nombre / SKU / código de barras… (Enter para agregar)",
            on_search=self._search_product,
            on_clear=lambda: self._search_product(""),
            # buscamos mientras se escribe para responsividad
            auto_search=True,
            min_chars=1,
        )
        self.search_bar.grid(row=1, column=0, sticky="ew", padx=SIZES["padding"], pady=(SIZES["padding_sm"], SIZES["padding_sm"]))

        self.search_results_frame = ctk.CTkScrollableFrame(
            search_card,
            fg_color=COLORS["bg_input"],
            height=0,
        )
        self.search_results_frame.grid(row=2, column=0, sticky="ew", padx=SIZES["padding"], pady=(0, SIZES["padding"]))

        # Encabezados del carrito
        cart_header = ctk.CTkFrame(
            parent,
            fg_color=COLORS["bg_panel"],
            corner_radius=SIZES["radius_lg"],
            border_width=1,
            border_color=COLORS["border"],
        )
        cart_header.grid(row=1, column=0, sticky="nsew", pady=(0, 0))
        cart_header.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            cart_header,
            text="Carrito",
            font=FONTS["heading"],
            text_color=COLORS["text_primary"],
        ).grid(row=0, column=0, sticky="w", padx=SIZES["padding"], pady=(SIZES["padding"], 0))

        cols = ctk.CTkFrame(cart_header, fg_color=COLORS["bg_input"], corner_radius=SIZES["radius_md"], height=32)
        cols.grid(row=1, column=0, sticky="ew", padx=SIZES["padding"], pady=(SIZES["padding_sm"], SIZES["padding_sm"]))
        cols.grid_propagate(False)

        for text, width in [("Producto", 0), ("P. Unit.", 100), ("Cant.", 56), ("Subtotal", 110), ("", 44)]:
            ctk.CTkLabel(
                cols,
                text=text,
                font=FONTS["small"],
                text_color=COLORS["text_secondary"],
                width=width if width else 0,
                anchor="w" if not width else "center",
            ).pack(side="left", padx=(SIZES["padding_sm"], 0))

        # Carrito (scrollable)
        self.cart_frame = ctk.CTkScrollableFrame(
            cart_header,
            fg_color="transparent",
            scrollbar_button_color=COLORS["border"],
        )
        self.cart_frame.grid(row=2, column=0, sticky="nsew", padx=SIZES["padding"], pady=(0, SIZES["padding"]))
        cart_header.grid_rowconfigure(2, weight=1)

        # Placeholder carrito vacio
        self.lbl_empty_cart = ctk.CTkLabel(
            self.cart_frame,
            text="El carrito está vacío.\nEscanee o busque un producto para comenzar.",
            font=FONTS["body"],
            text_color=COLORS["text_disabled"],
            justify="center",
        )
        self.lbl_empty_cart.pack(pady=40)

    def _build_right_panel(self, parent: ctk.CTkFrame) -> None:
        pad = SIZES["padding"]

        ctk.CTkLabel(
            parent,
            text="Resumen",
            font=FONTS["heading"],
            text_color=COLORS["text_secondary"],
        ).pack(padx=pad, pady=(pad, 0), anchor="w")

        ctk.CTkFrame(parent, fg_color=COLORS["border"], height=1).pack(fill="x", pady=8)

        # Subtotal
        row_sub = ctk.CTkFrame(parent, fg_color="transparent")
        row_sub.pack(fill="x", padx=pad)
        ctk.CTkLabel(row_sub, text="Subtotal:", font=FONTS["body"],
                     text_color=COLORS["text_secondary"]).pack(side="left")
        self.lbl_subtotal = ctk.CTkLabel(row_sub, text="$0,00", font=FONTS["mono"],
                                          text_color=COLORS["text_primary"])
        self.lbl_subtotal.pack(side="right")

        # Descuento
        row_disc = ctk.CTkFrame(parent, fg_color="transparent")
        row_disc.pack(fill="x", padx=pad, pady=4)
        ctk.CTkLabel(row_disc, text="Descuento:", font=FONTS["body"],
                     text_color=COLORS["text_secondary"]).pack(side="left")

        self.disc_var = ctk.StringVar(value="0")
        ctk.CTkEntry(
            row_disc,
            textvariable=self.disc_var,
            width=70,
            height=28,
            font=FONTS["mono"],
            fg_color=COLORS["bg_input"],
            border_color=COLORS["border"],
            text_color=COLORS["text_primary"],
            justify="right",
        ).pack(side="right")
        ctk.CTkLabel(row_disc, text="$", font=FONTS["body"],
                     text_color=COLORS["text_secondary"]).pack(side="right", padx=(0, 4))
        self.disc_var.trace_add("write", lambda *_: self._update_totals())

        ctk.CTkFrame(parent, fg_color=COLORS["border"], height=1).pack(fill="x", padx=pad, pady=8)

        # TOTAL
        row_total = ctk.CTkFrame(parent, fg_color="transparent")
        row_total.pack(fill="x", padx=pad)
        ctk.CTkLabel(row_total, text="TOTAL:", font=FONTS["heading"],
                     text_color=COLORS["text_primary"]).pack(side="left")
        self.lbl_total = ctk.CTkLabel(
            row_total,
            text="$0,00",
            font=("Consolas", 22, "bold"),
            text_color=COLORS["accent"],
        )
        self.lbl_total.pack(side="right")

        ctk.CTkFrame(parent, fg_color=COLORS["border"], height=1).pack(fill="x", padx=pad, pady=8)

        # Monto recibido (frame contenedor para poder ocultarlo)
        self.frame_paid = ctk.CTkFrame(parent, fg_color="transparent")
        self.frame_paid.pack(fill="x", padx=0)
        ctk.CTkLabel(self.frame_paid, text="Monto recibido:", font=FONTS["body"],
                     text_color=COLORS["text_secondary"]).pack(padx=pad, anchor="w")

        self.paid_var = ctk.StringVar(value="")
        self.entry_paid = ctk.CTkEntry(
            self.frame_paid,
            textvariable=self.paid_var,
            placeholder_text="0,00",
            height=SIZES["input_height"] + 4,
            font=("Consolas", 18, "bold"),
            fg_color=COLORS["bg_input"],
            border_color=COLORS["border_focus"],
            text_color=COLORS["text_primary"],
            justify="right",
        )
        self.entry_paid.pack(fill="x", padx=pad, pady=(4, 8))
        self.paid_var.trace_add("write", lambda *_: self._update_change())
        self.entry_paid.bind("<Return>", lambda e: self._confirm_sale())

        # Vuelto (frame contenedor para poder ocultarlo)
        self.frame_change = ctk.CTkFrame(parent, fg_color="transparent")
        self.frame_change.pack(fill="x", padx=0, pady=(0, 8))
        row_change = ctk.CTkFrame(self.frame_change, fg_color="transparent")
        row_change.pack(fill="x", padx=pad)
        ctk.CTkLabel(row_change, text="Vuelto:", font=FONTS["body"],
                     text_color=COLORS["text_secondary"]).pack(side="left")
        self.lbl_change = ctk.CTkLabel(
            row_change,
            text="$0,00",
            font=("Consolas", 18, "bold"),
            text_color=COLORS["success"],
        )
        self.lbl_change.pack(side="right")

        # Metodo de pago
        ctk.CTkLabel(parent, text="Método de pago:", font=FONTS["small"],
                     text_color=COLORS["text_secondary"]).pack(padx=pad, anchor="w")
        self.payment_method = ctk.StringVar(value="efectivo")
        self.payment_method.trace_add("write", lambda *_: self._on_payment_method_change())
        methods = ctk.CTkFrame(parent, fg_color="transparent")
        methods.pack(fill="x", padx=pad, pady=(4, 16))
        for method, label in [("efectivo", "Efectivo"), ("tarjeta", "Tarjeta"), ("transferencia", "Transfer.")]:
            ctk.CTkRadioButton(
                methods,
                text=label,
                variable=self.payment_method,
                value=method,
                font=FONTS["small"],
                text_color=COLORS["text_primary"],
                fg_color=COLORS["accent"],
            ).pack(side="left", padx=(0, 8))

        # Botones de accion
        self.btn_cobrar = ctk.CTkButton(
            parent,
            text="✔  COBRAR",
            height=52,
            font=("Segoe UI", 15, "bold"),
            fg_color=COLORS["btn_success"],
            hover_color=COLORS["btn_success_hover"],
            command=self._confirm_sale,
        )
        self.btn_cobrar.pack(fill="x", padx=pad, pady=(0, 8))

        # Botón Presupuesto
        ctk.CTkButton(
            parent,
            text="📃  Generar Presupuesto",
            height=36,
            font=FONTS["small"],
            fg_color=COLORS["accent"],
            hover_color=COLORS["accent_hover"],
            command=self._generate_estimate,
        ).pack(fill="x", padx=pad, pady=(0, 8))

        ctk.CTkButton(
            parent,
            text="🗑  Limpiar carrito",
            height=36,
            font=FONTS["small"],
            fg_color=COLORS["btn_neutral"],
            hover_color=COLORS["btn_neutral_hover"],
            command=self._clear_cart,
        ).pack(fill="x", padx=pad)

    # ── Busqueda de productos ─────────────────────────────────────────────────

    def _search_product(self, query: str) -> None:
        """Busca productos por nombre, sku o codigo de barras.

        Si ``query`` es cadena vacia se retornan los primeros productos
        (limite 8). El componente ``SearchBar`` maneja la invocacion cuando el
        campo se limpia o el usuario presiona Enter, y tambien dispararemos la
        busqueda al iniciar la vista para poblar el listado inicial.
        """
        try:
            with SessionLocal() as session:
                service = ProductService(session)
                results = service.search(query or "", limit=8)

            self._show_search_results(results)
        except Exception as e:
            logger.error(f"Error buscando producto: {e}")

    def _show_search_results(self, products: list) -> None:
        """Muestra los resultados debajo de la barra de busqueda."""
        for w in self.search_results_frame.winfo_children():
            w.destroy()

        if not products:
            self.search_results_frame.configure(height=0)
            return

        self.search_results_frame.configure(height=min(len(products) * 40, 200))

        for product in products:
            # Obtener precio del producto. el modelo Price almacena la cantidad en
            # ``amount``; antes se intentaba leer ``price`` y eso arrojaba una
            # AttributeError que terminaba abortando el renderizado de la lista.
            price = Decimal("0")
            if product.prices:
                price = product.prices[0].amount

            row = ctk.CTkFrame(
                self.search_results_frame,
                fg_color=COLORS["bg_input"],
                cursor="hand2",
                height=36,
            )
            row.pack(fill="x", pady=1)
            row.pack_propagate(False)

            ctk.CTkLabel(
                row,
                text=product.name,
                font=FONTS["body"],
                text_color=COLORS["text_primary"],
                anchor="w",
            ).pack(side="left", padx=SIZES["padding_sm"], fill="x", expand=True)

            ctk.CTkLabel(
                row,
                text=f"${price:,.2f}",
                font=FONTS["mono"],
                text_color=COLORS["accent"],
                width=90,
            ).pack(side="right", padx=SIZES["padding_sm"])

            # Click o Enter agrega al carrito
            row.bind("<Button-1>", lambda e, p=product, pr=price: self._add_to_cart(p, pr))
            for child in row.winfo_children():
                child.bind("<Button-1>", lambda e, p=product, pr=price: self._add_to_cart(p, pr))

    # ── Carrito ───────────────────────────────────────────────────────────────

    def _add_to_cart(self, product, price: Decimal) -> None:
        """Agrega un producto al carrito o incrementa su cantidad si ya existe."""
        if product.id in self._cart:
            self._cart[product.id].quantity += 1
        else:
            self._cart[product.id] = CartItem(
                product_id=product.id,
                name=product.name,
                unit_price=price,
                quantity=1,
            )

        self.search_bar.clear()
        self._search_product("")

        self._render_cart()
        self._update_totals()
        self.entry_paid.focus_set()

    def _remove_from_cart(self, product_id: int) -> None:
        self._cart.pop(product_id, None)
        self._render_cart()
        self._update_totals()

    def _change_qty(self, product_id: int, qty: int) -> None:
        if product_id in self._cart:
            self._cart[product_id].quantity = qty
        self._render_cart()
        self._update_totals()

    def _render_cart(self) -> None:
        for w in self.cart_frame.winfo_children():
            w.destroy()

        if not self._cart:
            self.lbl_empty_cart = ctk.CTkLabel(
                self.cart_frame,
                text="El carrito está vacío.\nEscanee o busque un producto para comenzar.",
                font=FONTS["body"],
                text_color=COLORS["text_disabled"],
                justify="center",
            )
            self.lbl_empty_cart.pack(pady=40)
            return

        for i, item in enumerate(self._cart.values()):
            CartRow(
                self.cart_frame,
                item=item,
                on_remove=self._remove_from_cart,
                on_qty_change=self._change_qty,
                index=i,
            ).pack(fill="x")

    def _clear_cart(self) -> None:
        if not self._cart:
            return
        ConfirmModal(
            self,
            title="Limpiar carrito",
            message="¿Desea vaciar el carrito y comenzar de nuevo?",
            on_confirm=self._do_clear_cart,
            confirm_text="Vaciar",
            danger=True,
        )

    def _do_clear_cart(self) -> None:
        self._cart.clear()
        self.paid_var.set("")
        self.disc_var.set("0")
        self._render_cart()
        self._update_totals()
        self.search_bar.focus()

    # ── Totales ───────────────────────────────────────────────────────────────

    def _subtotal(self) -> Decimal:
        return sum((item.subtotal for item in self._cart.values()), Decimal("0"))

    def _discount(self) -> Decimal:
        try:
            return Decimal(self.disc_var.get() or "0")
        except InvalidOperation:
            return Decimal("0")

    def _total(self) -> Decimal:
        return max(Decimal("0"), self._subtotal() - self._discount())

    def _update_totals(self) -> None:
        sub = self._subtotal()
        total = self._total()
        self.lbl_subtotal.configure(text=self._fmt(sub))
        self.lbl_total.configure(text=self._fmt(total))
        self._update_change()

    def _update_change(self) -> None:
        try:
            paid = Decimal(self.paid_var.get().replace(",", ".") or "0")
        except InvalidOperation:
            paid = Decimal("0")

        total = self._total()
        change = paid - total

        self.lbl_change.configure(
            text=self._fmt(change) if change >= 0 else f"-{self._fmt(-change)}",
            text_color=COLORS["success"] if change >= 0 else COLORS["error"],
        )

    @staticmethod
    def _fmt(amount: Decimal) -> str:
        """Formatea un decimal como moneda con separador de miles."""
        return f"${amount:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

    # ── Proceso de venta ──────────────────────────────────────────────────────

    def _on_payment_method_change(self) -> None:
        """Oculta el campo de monto recibido y vuelto para tarjeta/transferencia."""
        method = self.payment_method.get()
        if method == "efectivo":
            self.frame_paid.pack(fill="x", padx=0)
            self.frame_change.pack(fill="x", padx=0, pady=(0, 8))
        else:
            self.frame_paid.pack_forget()
            self.frame_change.pack_forget()
            self.paid_var.set("")

    def _confirm_sale(self) -> None:
        if not self._cart:
            AlertModal(self, "Carrito vacío", "Agregue productos antes de cobrar.", kind="warning")
            return

        total = self._total()
        method = self.payment_method.get()

        # Tarjeta y transferencia no requieren monto recibido: se usa el total
        if method in ("tarjeta", "transferencia"):
            self._process_sale(total)
            return

        try:
            paid_str = self.paid_var.get().replace(",", ".")
            paid = Decimal(paid_str)
        except InvalidOperation:
            AlertModal(self, "Monto inválido", "Ingrese un monto recibido válido.", kind="error")
            self.entry_paid.focus_set()
            return

        if paid < total:
            AlertModal(
                self,
                "Monto insuficiente",
                f"El monto recibido (${paid:,.2f}) es menor al total ({self._fmt(total)}).",
                kind="error",
            )
            self.entry_paid.focus_set()
            return

        self._process_sale(paid)

    def _process_sale(self, amount_paid: Decimal) -> None:
        """Delega al SaleService. La vista NO contiene logica de negocio."""
        self.btn_cobrar.configure(state="disabled", text="Procesando...")
        self.update_idletasks()

        try:
            items = [
                SaleItemInput(
                    product_id=item.product_id,
                    quantity=item.quantity,
                    unit_price=item.unit_price,
                )
                for item in self._cart.values()
            ]

            sale_data = SaleInput(
                items=items,
                discount=self._discount(),
                amount_paid=amount_paid,
                payment_method=self.payment_method.get(),
            )

            with SessionLocal() as session:
                service = SaleService(session)
                sale = service.process_sale(sale_data, seller_id=AppSession.user_id)

            logger.info(f"Venta #{sale.id} procesada. Total: {sale.total}")

            change = amount_paid - self._total()
            self._show_success(sale.id, self._total(), amount_paid, change)
            self._do_clear_cart()

        except StockInsuficienteError as e:
            AlertModal(
                self,
                "Stock insuficiente",
                f"No hay suficiente stock del producto.\n"
                f"Disponible: {e.disponible} | Requerido: {e.requerido}",
                kind="error",
            )
        except ProductoNoEncontradoError:
            AlertModal(self, "Producto no encontrado",
                       "Uno de los productos ya no existe en el sistema.", kind="error")
        except Exception as e:
            logger.error(f"Error procesando venta: {e}")
            AlertModal(self, "Error del sistema",
                       f"No se pudo procesar la venta:\n{e}", kind="error")
        finally:
            self.btn_cobrar.configure(state="normal", text="✔  COBRAR")

    def _show_success(
        self,
        sale_id: int,
        total: Decimal,
        paid: Decimal,
        change: Decimal,
    ) -> None:
        method = self.payment_method.get()
        msg = f"Venta #{sale_id} registrada exitosamente.\n\nTotal:    {self._fmt(total)}\n"
        if method == "efectivo":
            msg += f"Recibido: {self._fmt(paid)}\nVuelto:   {self._fmt(change)}"
        else:
            label = "Tarjeta" if method == "tarjeta" else "Transferencia"
        msg += "\n\n¿Desea generar e imprimir el ticket?"
        ConfirmModal(
            self,
            title="¡Venta completada!",
            message=msg,
            on_confirm=lambda: self._print_ticket(sale_id),
            confirm_text="Imprimir",
            cancel_text="No Imprimir",
        )
        self.search_bar.focus()

    def _print_ticket(self, sale_id: int) -> None:
        """Genera e imprime el ticket PDF. Falla silenciosamente si hay error."""
        try:
            from reports.pdf_service import print_ticket
            print_ticket(sale_id, auto_open=True)
        except Exception as e:
            logger.warning(f"No se pudo generar el ticket PDF: {e}")

    def _generate_estimate(self) -> None:
        """Imprime la vista del carrito actual en formato de Presupuesto PDF (A4 o Termica)"""
        if not self._cart:
            AlertModal(self, "Carrito vacío", "Agregue productos antes de imprimir el presupuesto.", kind="warning")
            return
            
        from reports.pdf_service import print_estimate
        
        try:
            print_estimate(
                cart_items=list(self._cart.values()),
                subtotal=self._subtotal(),
                discount=self._discount(),
                total=self._total(),
                seller_name="Vendedor (Presupuesto)",
                auto_open=True
            )
        except Exception as e:
            logger.error(f"Error generando presupuesto: {e}")
            AlertModal(self, "Error", f"No se pudo armar el presupuesto: {e}", kind="error")