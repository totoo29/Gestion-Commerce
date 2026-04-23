# app/ui/views/products_view.py
from decimal import Decimal, InvalidOperation
from typing import Callable

import customtkinter as ctk

from app.core.exceptions import ProductoNoEncontradoError
from app.core.logging import get_logger
from app.database import SessionLocal
from app.services.product_service import ProductService
from app.ui.components.modal import AlertModal, ConfirmModal
from app.ui.components.search_bar import SearchBar
from app.ui.components.data_table import DataTable
from app.ui.components import AppShell, ShellConfig
from app.ui.theme import COLORS, FONTS, SIZES

logger = get_logger(__name__)


class ProductsView(ctk.CTkFrame):
    """
    ABM de Productos.

    Layout:
        [Navbar lateral] | [Lista de productos + buscador] | [Panel detalle / formulario]

    Operaciones:
        - Listar todos los productos activos con stock y precio
        - Buscar por nombre, SKU o barcode
        - Crear nuevo producto (nombre, SKU, unidad, categoria, precio, stock inicial)
        - Editar producto existente
        - Desactivar producto (baja logica)
        - Agregar / quitar barcodes
        - Cambiar precio
    """

    def __init__(self, master: ctk.CTk, navigate: Callable, **kwargs):
        super().__init__(master, fg_color=COLORS["bg_main"], **kwargs)
        self.navigate = navigate
        self._selected_product_id: int | None = None
        self._categories: list = []
        self._price_lists: list = []
        self._build_ui()
        self._load_catalogs()
        self._load_products()

    # ── Construccion ──────────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        shell = AppShell(
            self,
            navigate=self.navigate,
            config=ShellConfig(title="Productos", active_view="products"),
        )
        shell.pack(fill="both", expand=True)

        root = ctk.CTkFrame(shell.content, fg_color="transparent")
        root.grid(row=0, column=0, sticky="nsew")
        root.grid_rowconfigure(0, weight=1)
        root.grid_columnconfigure(0, weight=1)
        root.grid_columnconfigure(1, weight=0)

        # Panel izquierdo: lista
        left = ctk.CTkFrame(root, fg_color="transparent")
        left.grid(row=0, column=0, sticky="nsew", padx=(0, SIZES["padding"]))
        self._build_list_panel(left)

        # Panel derecho: detalle / formulario
        right = ctk.CTkFrame(
            root,
            fg_color=COLORS["bg_panel"],
            width=420,
            corner_radius=SIZES["radius_lg"],
            border_width=1,
            border_color=COLORS["border"],
        )
        right.grid(row=0, column=1, sticky="ns")
        right.pack_propagate(False)  # Fijar el tamaño para que no baile al cambiar productos
        self._build_detail_panel(right)

    def _build_list_panel(self, parent: ctk.CTkFrame) -> None:
        # Cabecera
        header = ctk.CTkFrame(parent, fg_color="transparent")
        header.pack(fill="x", pady=(0, SIZES["padding_sm"]))

        ctk.CTkLabel(header, text="Productos", font=FONTS["subtitle"],
                     text_color=COLORS["text_primary"]).pack(side="left")

        ctk.CTkButton(
            header,
            text="＋  Nuevo producto",
            height=36,
            font=FONTS["body_bold"],
            fg_color=COLORS["accent"],
            hover_color=COLORS["accent_hover"],
            command=self._new_product,
        ).pack(side="right")

        # Barra de busqueda
        self.search_bar = SearchBar(
            parent,
            placeholder="Buscar por nombre, SKU o código de barras...",
            on_search=self._search,
            on_clear=self._load_products,
            auto_search=True,
            min_chars=2,
        )
        self.search_bar.pack(fill="x", pady=(0, SIZES["padding_sm"]))

        # Tabla
        self.table = DataTable(
            parent,
            columns=["SKU", "Nombre", "Unidad", "Precio", "Stock", "Estado"],
            col_widths=[90, 0, 80, 100, 70, 70],
            col_weights=[0, 1, 0, 0, 0, 0],
            col_aligns=["w", "w", "center", "e", "center", "center"],
            on_select=self._on_row_select,
        )
        self.table.pack(fill="both", expand=True)

    def _build_detail_panel(self, parent: ctk.CTkFrame) -> None:
        pad = SIZES["padding"]

        self.lbl_detail_title = ctk.CTkLabel(
            parent, text="Seleccione un producto",
            font=FONTS["heading"], text_color=COLORS["text_primary"],
        )
        self.lbl_detail_title.pack(padx=pad, pady=(pad, 0), anchor="w")

        ctk.CTkFrame(parent, fg_color=COLORS["border"], height=1).pack(fill="x", pady=8)

        # Scroll para el formulario
        self.form_scroll = ctk.CTkScrollableFrame(parent, fg_color="transparent")
        self.form_scroll.pack(fill="both", expand=True, padx=pad)

        # ── Campos del formulario ─────────────────────────────────────────────
        self.var_name        = ctk.StringVar()
        self.var_sku         = ctk.StringVar()
        self.var_unit        = ctk.StringVar(value="unidad")
        self.var_description = ctk.StringVar()
        self.var_price       = ctk.StringVar()
        self.var_min_stock   = ctk.StringVar(value="5")
        self.var_init_stock  = ctk.StringVar(value="0")
        self.var_barcode     = ctk.StringVar()
        self.var_category    = ctk.StringVar(value="Sin categoría")

        fields = [
            ("Nombre *",          self.var_name,        False),
            ("SKU / Código *",    self.var_sku,         False),
            ("Unidad",            self.var_unit,        False),
            ("Descripción",       self.var_description, False),
            ("Precio de venta *", self.var_price,       False),
            ("Stock mínimo",      self.var_min_stock,   False),
        ]

        for label, var, disabled in fields:
            ctk.CTkLabel(self.form_scroll, text=label, font=FONTS["small"],
                         text_color=COLORS["text_secondary"], anchor="w").pack(fill="x", pady=(8, 0))
            entry = ctk.CTkEntry(
                self.form_scroll, textvariable=var,
                height=SIZES["input_height"],
                font=FONTS["body"],
                fg_color=COLORS["bg_input"],
                border_color=COLORS["border"],
                text_color=COLORS["text_primary"],
            )
            entry.pack(fill="x", pady=(2, 0))
            if disabled:
                entry.configure(state="disabled")

        # Categoria (dropdown)
        ctk.CTkLabel(self.form_scroll, text="Categoría", font=FONTS["small"],
                     text_color=COLORS["text_secondary"], anchor="w").pack(fill="x", pady=(8, 0))
        self.opt_category = ctk.CTkOptionMenu(
            self.form_scroll,
            variable=self.var_category,
            values=["Sin categoría"],
            height=SIZES["input_height"],
            font=FONTS["body"],
            fg_color=COLORS["bg_input"],
            button_color=COLORS["bg_card"],
            button_hover_color=COLORS["accent"],
            text_color=COLORS["text_primary"],
        )
        self.opt_category.pack(fill="x", pady=(2, 0))

        # Stock inicial (solo al crear)
        self.frm_init_stock = ctk.CTkFrame(self.form_scroll, fg_color="transparent")
        self.frm_init_stock.pack(fill="x")
        ctk.CTkLabel(self.frm_init_stock, text="Stock inicial", font=FONTS["small"],
                     text_color=COLORS["text_secondary"], anchor="w").pack(fill="x", pady=(8, 0))
        ctk.CTkEntry(
            self.frm_init_stock, textvariable=self.var_init_stock,
            height=SIZES["input_height"], font=FONTS["body"],
            fg_color=COLORS["bg_input"], border_color=COLORS["border"],
            text_color=COLORS["text_primary"],
        ).pack(fill="x", pady=(2, 0))

        ctk.CTkFrame(self.form_scroll, fg_color=COLORS["border"], height=1).pack(
            fill="x", pady=SIZES["padding"])

        # Seccion barcodes
        self.frm_barcodes = ctk.CTkFrame(self.form_scroll, fg_color="transparent")
        self.frm_barcodes.pack(fill="x")

        ctk.CTkLabel(self.frm_barcodes, text="Códigos de barras", font=FONTS["small"],
                     text_color=COLORS["text_secondary"], anchor="w").pack(fill="x")

        barcode_row = ctk.CTkFrame(self.frm_barcodes, fg_color="transparent")
        barcode_row.pack(fill="x", pady=(2, 0))
        ctk.CTkEntry(
            barcode_row, textvariable=self.var_barcode,
            placeholder_text="Escanear o escribir...",
            height=32, font=FONTS["body"],
            fg_color=COLORS["bg_input"], border_color=COLORS["border"],
            text_color=COLORS["text_primary"],
        ).pack(side="left", fill="x", expand=True, padx=(0, 4))
        ctk.CTkButton(
            barcode_row, text="Agregar", width=80, height=32,
            font=FONTS["small"],
            fg_color=COLORS["bg_card"], hover_color=COLORS["accent"],
            command=self._add_barcode,
        ).pack(side="left")

        # Frame scrollable para mostrar barcodes como botones eliminables
        self.frm_barcode_list = ctk.CTkScrollableFrame(
            self.frm_barcodes,
            fg_color=COLORS["bg_input"],
            height=80,
        )
        self.frm_barcode_list.pack(fill="both", expand=True, pady=(4, 0))
        self.frm_barcode_list.grid_columnconfigure(0, weight=1)

        # Placeholder cuando no hay barcodes
        self.lbl_no_barcodes = ctk.CTkLabel(
            self.frm_barcode_list, text="Sin códigos registrados",
            font=FONTS["small"], text_color=COLORS["text_disabled"],
        )
        self.lbl_no_barcodes.pack(pady=8)

        # Se usará para guardar referencias a barcodes durante edicion
        self._barcode_widgets: dict[int, ctk.CTkFrame] = {}

        # ── Botones de accion ─────────────────────────────────────────────────
        btn_frame = ctk.CTkFrame(parent, fg_color="transparent")
        btn_frame.pack(fill="x", padx=pad, pady=pad)

        self.btn_save = ctk.CTkButton(
            btn_frame, text="💾  Guardar",
            height=SIZES["btn_height"],
            font=FONTS["body_bold"],
            fg_color=COLORS["btn_success"],
            hover_color=COLORS["btn_success_hover"],
            command=self._save_product,
        )
        self.btn_save.pack(fill="x", pady=(0, 6))

        self.btn_deactivate = ctk.CTkButton(
            btn_frame, text="🗑  Desactivar producto",
            height=SIZES["btn_height"],
            font=FONTS["body"],
            fg_color=COLORS["btn_neutral"],
            hover_color=COLORS["btn_danger"],
            command=self._deactivate_product,
            state="disabled",
        )
        self.btn_deactivate.pack(fill="x")

    # ── Carga de datos ────────────────────────────────────────────────────────

    def _load_catalogs(self) -> None:
        """Carga categorias y listas de precio una sola vez."""
        try:
            with SessionLocal() as session:
                svc = ProductService(session)
                self._categories  = svc.get_all_categories()
                self._price_lists = svc.get_all_price_lists()

            cat_names = ["Sin categoría"] + [c.name for c in self._categories]
            self.opt_category.configure(values=cat_names)
        except Exception as e:
            logger.error(f"Error cargando catalogos: {e}")

    def _load_products(self, query: str = "") -> None:
        """Carga todos los productos activos en la tabla."""
        try:
            with SessionLocal() as session:
                svc = ProductService(session)
                products = svc.get_all_products(limit=100)

            rows = []
            for p in products:
                price = self._get_default_price(p)
                stock_qty = p.stock.quantity if p.stock else 0
                rows.append([
                    p.sku,
                    p.name,
                    p.unit,
                    f"${price:,.2f}" if price else "-",
                    str(int(stock_qty)),
                    "✔ Activo" if p.is_active else "✖ Inactivo",
                ])

            self.table.load(rows)
            # Guardar referencia a los objetos para acceder por indice
            self._products_cache = products
        except Exception as e:
            logger.error(f"Error cargando productos: {e}")
            AlertModal(self, "Error", f"No se pudieron cargar los productos:\n{e}", kind="error")

    def _search(self, query: str) -> None:
        try:
            with SessionLocal() as session:
                svc = ProductService(session)
                products = svc.search_products(query)

            rows = []
            for p in products:
                price = self._get_default_price(p)
                stock_qty = p.stock.quantity if p.stock else 0
                rows.append([
                    p.sku,
                    p.name,
                    p.unit,
                    f"${price:,.2f}" if price else "-",
                    str(int(stock_qty)),
                    "✔ Activo" if p.is_active else "✖ Inactivo",
                ])
            self.table.load(rows)
            self._products_cache = products
        except Exception as e:
            logger.error(f"Error buscando: {e}")

    # ── Interaccion con la tabla ──────────────────────────────────────────────

    def _on_row_select(self, row_data: list) -> None:
        """Al seleccionar una fila, carga el producto en el formulario."""
        index = self.table._selected_index
        if index is None or not hasattr(self, "_products_cache"):
            return

        page_start = self.table._current_page * self.table.page_size
        abs_index = page_start + index
        if abs_index >= len(self._products_cache):
            return

        product = self._products_cache[abs_index]
        self._selected_product_id = product.id
        self._fill_form(product)

    def _fill_form(self, product) -> None:
        """Rellena el formulario con los datos del producto seleccionado."""
        self.lbl_detail_title.configure(text=f"Editando: {product.name}")

        self.var_name.set(product.name)
        self.var_sku.set(product.sku)
        self.var_unit.set(product.unit or "unidad")
        self.var_description.set(product.description or "")

        price = self._get_default_price(product)
        self.var_price.set(f"{price:.2f}" if price else "")

        stock = product.stock
        self.var_min_stock.set(str(int(stock.min_quantity)) if stock else "5")

        # Ocultar campo stock inicial (solo para nuevos)
        self.frm_init_stock.pack_forget()

        # Barcodes: mostrar como botones interactivos
        self._render_barcodes(product.barcodes if product.barcodes else [], product.id)

        self.btn_deactivate.configure(
            state="normal" if product.is_active else "disabled",
            text="🗑  Desactivar" if product.is_active else "✖ Inactivo",
        )

    def _new_product(self) -> None:
        """Limpia el formulario para crear un nuevo producto."""
        self._selected_product_id = None
        self.lbl_detail_title.configure(text="Nuevo producto")

        self.var_name.set("")
        self.var_sku.set("")
        self.var_unit.set("unidad")
        self.var_description.set("")
        self.var_price.set("")
        self.var_min_stock.set("5")
        self.var_init_stock.set("0")
        self.var_barcode.set("")
        self.var_category.set("Sin categoría")
        self._render_barcodes([], None)  # Limpiar barcodes
        self.btn_deactivate.configure(state="disabled")
        self.frm_init_stock.pack(fill="x")

    # ── Guardar ───────────────────────────────────────────────────────────────

    def _save_product(self) -> None:
        name  = self.var_name.get().strip()
        sku   = self.var_sku.get().strip()
        unit  = self.var_unit.get().strip() or "unidad"
        desc  = self.var_description.get().strip()
        price_str = self.var_price.get().strip().replace(",", ".")

        if not name:
            AlertModal(self, "Campo requerido", "El nombre del producto es obligatorio.", kind="warning")
            return
        if not sku:
            AlertModal(self, "Campo requerido", "El SKU es obligatorio.", kind="warning")
            return

        try:
            price = Decimal(price_str) if price_str else None
        except InvalidOperation:
            AlertModal(self, "Precio inválido", "Ingrese un precio numérico válido.", kind="error")
            return

        try:
            min_stock = Decimal(self.var_min_stock.get() or "5")
        except InvalidOperation:
            min_stock = Decimal("5")

        # Categoria
        cat_name = self.var_category.get()
        category_id = None
        for cat in self._categories:
            if cat.name == cat_name:
                category_id = cat.id
                break

        try:
            with SessionLocal() as session:
                svc = ProductService(session)

                if self._selected_product_id is None:
                    # ── CREAR ─────────────────────────────────────────────────
                    try:
                        init_stock = Decimal(self.var_init_stock.get() or "0")
                    except InvalidOperation:
                        init_stock = Decimal("0")

                    # Obtener lista de precios por defecto
                    pl = svc.get_default_price_list()
                    prices = {}
                    if pl and price is not None:
                        prices = {pl.id: price}

                    # Barcodes iniciales (del campo temporal)
                    initial_barcodes = getattr(self, "_temp_barcodes", [])

                    product = svc.create_product(
                        sku=sku,
                        name=name,
                        description=desc or None,
                        unit=unit,
                        category_id=category_id,
                        initial_stock=init_stock,
                        min_stock=min_stock,
                        prices=prices,
                        barcodes=initial_barcodes,
                    )
                    self._temp_barcodes = []  # Limpiar temporales tras guardar
                    AlertModal(self, "Producto creado",
                               f"'{name}' fue creado exitosamente.", kind="success")
                else:
                    # ── EDITAR ────────────────────────────────────────────────
                    svc.update_product(
                        self._selected_product_id,
                        name=name,
                        description=desc or None,
                        unit=unit,
                        category_id=category_id,
                    )
                    if price is not None:
                        pl = svc.get_default_price_list()
                        if pl:
                            svc.set_price(self._selected_product_id, pl.id, price)

                    AlertModal(self, "Producto actualizado",
                               f"'{name}' fue actualizado correctamente.", kind="success")

            self._load_products()

        except Exception as e:
            logger.error(f"Error guardando producto: {e}")
            AlertModal(self, "Error al guardar", str(e), kind="error")

    # ── Desactivar ────────────────────────────────────────────────────────────

    def _deactivate_product(self) -> None:
        if not self._selected_product_id:
            return
        name = self.var_name.get()
        ConfirmModal(
            self,
            title="Desactivar producto",
            message=f"¿Desactivar '{name}'?\nNo aparecerá en búsquedas ni en el POS.",
            on_confirm=self._do_deactivate,
            confirm_text="Desactivar",
            danger=True,
        )

    def _do_deactivate(self) -> None:
        try:
            with SessionLocal() as session:
                ProductService(session).deactivate_product(self._selected_product_id)
            AlertModal(self, "Producto desactivado",
                       "El producto fue desactivado correctamente.", kind="success")
            self._new_product()
            self._load_products()
        except Exception as e:
            AlertModal(self, "Error", str(e), kind="error")

    # ── Barcodes ──────────────────────────────────────────────────────────────

    def _add_barcode(self) -> None:
        code = self.var_barcode.get().strip()
        if not code:
            return
        
        if self._selected_product_id:
            # Agregar a base de datos (producto ya guardado)
            try:
                with SessionLocal() as session:
                    svc = ProductService(session)
                    svc.add_barcode(self._selected_product_id, code)
                    product = svc.get_product(self._selected_product_id)
                self.var_barcode.set("")
                self._fill_form(product)
            except Exception as e:
                AlertModal(self, "Error", str(e), kind="error")
        else:
            # Agregar temporalmente a la lista en memoria (producto nuevo)
            if not hasattr(self, "_temp_barcodes"):
                self._temp_barcodes = []
            
            # Validar que no esté duplicado
            if code not in self._temp_barcodes:
                self._temp_barcodes.append(code)
                self._render_barcodes(self._temp_barcodes, None)
                self.var_barcode.set("")
            else:
                AlertModal(self, "Duplicado", "Este código ya fue agregado.", kind="warning")

    def _render_barcodes(self, barcodes: list, product_id: int | None) -> None:
        """Renderiza los códigos de barras como botones editables/eliminables."""
        # Limpiar widgets previos
        for w in self.frm_barcode_list.winfo_children():
            w.destroy()
        self._barcode_widgets.clear()

        if not barcodes:
            self.lbl_no_barcodes = ctk.CTkLabel(
                self.frm_barcode_list, text="Sin códigos registrados",
                font=FONTS["small"], text_color=COLORS["text_disabled"],
            )
            self.lbl_no_barcodes.pack(pady=8)
            return

        for barcode_obj in barcodes:
            # barcode_obj puede ser un objeto Barcode o una string (temp)
            if isinstance(barcode_obj, str):
                code = barcode_obj
                barcode_id = None
            else:
                code = barcode_obj.code
                barcode_id = barcode_obj.id

            row = ctk.CTkFrame(self.frm_barcode_list, fg_color=COLORS["bg_card"], height=32, corner_radius=6)
            row.pack(fill="x", padx=4, pady=2)
            row.pack_propagate(False)

            ctk.CTkLabel(
                row, text=code, font=FONTS["mono"],
                text_color=COLORS["text_primary"],
            ).pack(side="left", padx=8, fill="x", expand=True)

            ctk.CTkButton(
                row, text="✗", width=28, height=28,
                font=FONTS["small"], fg_color=COLORS["btn_danger"],
                hover_color=COLORS["btn_danger_hover"],
                command=lambda bc_id=barcode_id, bc_code=code, p_id=product_id:
                    self._delete_barcode(bc_id, bc_code, p_id),
            ).pack(side="right", padx=4)

    def _delete_barcode(self, barcode_id: int | None, code: str, product_id: int | None) -> None:
        """Elimina un código de barras."""
        if barcode_id is not None and product_id is not None:
            # Eliminar del servidor
            try:
                with SessionLocal() as session:
                    svc = ProductService(session)
                    svc.remove_barcode(barcode_id)
                    product = svc.get_product(product_id)
                self._fill_form(product)
            except Exception as e:
                AlertModal(self, "Error", f"No se pudo eliminar: {e}", kind="error")
        else:
            # Eliminar de la lista temporal
            if hasattr(self, "_temp_barcodes") and code in self._temp_barcodes:
                self._temp_barcodes.remove(code)
                self._render_barcodes(self._temp_barcodes, None)

    # ── Helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def _get_default_price(product) -> Decimal | None:
        if not product.prices:
            return None
        # El modelo Price expone el campo 'amount' como valor numerico
        return product.prices[0].amount
