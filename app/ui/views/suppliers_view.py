from __future__ import annotations

from typing import Callable
import customtkinter as ctk

from app.database import SessionLocal
from app.models.supplier import Supplier
from app.repository.supplier_repository import SupplierRepository
from app.ui.components import AppShell, ShellConfig, DataTable, SearchBar
from app.ui.components.modal import AlertModal, ConfirmModal
from app.ui.theme import COLORS, FONTS, SIZES


class SuppliersView(ctk.CTkFrame):
    """
    ABM de Proveedores.

    Layout:
        [Navbar lateral] | [Lista de proveedores + buscador] | [Panel detalle / formulario]
    """

    def __init__(self, master: ctk.CTk, navigate: Callable, **kwargs):
        super().__init__(master, fg_color=COLORS["bg_main"], **kwargs)
        self.navigate = navigate
        self._selected_supplier_id: int | None = None
        self._build_ui()
        self._load_data()

    # ── Construccion ──────────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        shell = AppShell(
            self,
            navigate=self.navigate,
            config=ShellConfig(title="Proveedores", active_view="suppliers"),
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
        right.grid_propagate(False)
        self._build_detail_panel(right)

    def _build_list_panel(self, parent: ctk.CTkFrame) -> None:
        header = ctk.CTkFrame(parent, fg_color="transparent")
        header.pack(fill="x", pady=(0, SIZES["padding_sm"]))

        ctk.CTkLabel(
            header,
            text="Proveedores",
            font=FONTS["title"],
            text_color=COLORS["text_primary"],
        ).pack(side="left")

        ctk.CTkButton(
            header,
            text="+ Agregar proveedor",
            height=36,
            font=FONTS["body_bold"],
            fg_color=COLORS["accent"],
            hover_color=COLORS["accent_hover"],
            command=self._new_supplier,
        ).pack(side="right")

        self.search = SearchBar(
            parent,
            placeholder="Buscar proveedor por nombre, CUIT o contacto...",
            on_search=self._search_data,
            on_clear=self._load_data,
            auto_search=True,
            min_chars=2,
        )
        self.search.pack(fill="x", pady=(0, SIZES["padding_sm"]))

        self.table = DataTable(
            parent,
            columns=["Nombre", "CUIT", "Teléfono", "Email", "Condición", "Estado"],
            col_widths=[240, 100, 120, 200, 120, 80],
            page_size=20,
            on_select=self._on_row_select,
        )
        self.table.pack(fill="both", expand=True)

    def _build_detail_panel(self, parent: ctk.CTkFrame) -> None:
        pad = SIZES["padding"]

        self.lbl_detail_title = ctk.CTkLabel(
            parent, text="Seleccione un proveedor",
            font=FONTS["heading"], text_color=COLORS["text_primary"],
        )
        self.lbl_detail_title.pack(padx=pad, pady=(pad, 0), anchor="w")

        ctk.CTkFrame(parent, fg_color=COLORS["border"], height=1).pack(fill="x", pady=8)

        self.form_scroll = ctk.CTkScrollableFrame(parent, fg_color="transparent")
        self.form_scroll.pack(fill="both", expand=True, padx=pad)

        self.var_name = ctk.StringVar()
        self.var_tax_id = ctk.StringVar()
        self.var_phone = ctk.StringVar()
        self.var_email = ctk.StringVar()
        self.var_condition = ctk.StringVar(value="Contado")

        fields = [
            ("Razón Social *", self.var_name),
            ("CUIT / DNI", self.var_tax_id),
            ("Teléfono", self.var_phone),
            ("Email", self.var_email),
            ("Condición de pago", self.var_condition),
        ]

        for label, var in fields:
            ctk.CTkLabel(
                self.form_scroll, text=label, font=FONTS["small"], text_color=COLORS["text_secondary"], anchor="w"
            ).pack(fill="x", pady=(8, 0))
            
            ctk.CTkEntry(
                self.form_scroll, textvariable=var, height=SIZES["input_height"],
                font=FONTS["body"], fg_color=COLORS["bg_input"], border_color=COLORS["border"],
                text_color=COLORS["text_primary"],
            ).pack(fill="x", pady=(2, 0))

        btn_frame = ctk.CTkFrame(parent, fg_color="transparent")
        btn_frame.pack(fill="x", padx=pad, pady=pad)

        self.btn_save = ctk.CTkButton(
            btn_frame, text="💾  Guardar",
            height=SIZES["btn_height"], font=FONTS["body_bold"],
            fg_color=COLORS["btn_success"], hover_color=COLORS["btn_success_hover"],
            command=self._save_supplier,
        )
        self.btn_save.pack(fill="x", pady=(0, 6))

        self.btn_deactivate = ctk.CTkButton(
            btn_frame, text="🗑  Desactivar proveedor",
            height=SIZES["btn_height"], font=FONTS["body"],
            fg_color=COLORS["btn_neutral"], hover_color=COLORS["btn_danger"],
            command=self._deactivate_supplier,
            state="disabled",
        )
        self.btn_deactivate.pack(fill="x")

    # ── Interaccion ──────────────────────────────────────────────────────────

    def _on_row_select(self, row_data: list) -> None:
        index = self.table._selected_index
        if index is None or not hasattr(self, "_suppliers_cache"):
            return

        page_start = self.table._current_page * self.table.page_size
        abs_index = page_start + index
        if abs_index >= len(self._suppliers_cache):
            return

        supplier = self._suppliers_cache[abs_index]
        self._selected_supplier_id = supplier.id
        self._fill_form(supplier)

    def _fill_form(self, supplier: Supplier) -> None:
        self.lbl_detail_title.configure(text=f"Editando: {supplier.name}")
        self.var_name.set(supplier.name)
        self.var_tax_id.set(supplier.tax_id or "")
        self.var_phone.set(supplier.phone or "")
        self.var_email.set(supplier.email or "")
        self.var_condition.set(supplier.notes or "")

        self.btn_deactivate.configure(
            state="normal" if supplier.is_active else "disabled",
            text="🗑  Desactivar" if supplier.is_active else "✖ Inactivo",
        )

    def _new_supplier(self) -> None:
        self._selected_supplier_id = None
        self.lbl_detail_title.configure(text="Nuevo proveedor")
        self.var_name.set("")
        self.var_tax_id.set("")
        self.var_phone.set("")
        self.var_email.set("")
        self.var_condition.set("Contado")
        self.btn_deactivate.configure(state="disabled")

    # ── Datos ────────────────────────────────────────────────────────────────

    def _save_supplier(self) -> None:
        name = self.var_name.get().strip()
        if not name:
            AlertModal(self, "Campo requerido", "La razón social es obligatoria.", kind="warning")
            return

        try:
            with SessionLocal() as session:
                repo = SupplierRepository(session)
                
                if self._selected_supplier_id is None:
                    # Crear
                    supplier = Supplier(
                        name=name,
                        tax_id=self.var_tax_id.get().strip() or None,
                        phone=self.var_phone.get().strip() or None,
                        email=self.var_email.get().strip() or None,
                        notes=self.var_condition.get().strip() or None,
                    )
                    repo.create(supplier)
                    msg = f"Proveedor '{name}' creado exitosamente."
                else:
                    # Editar
                    supplier = repo.get_by_id(self._selected_supplier_id)
                    if supplier:
                        supplier.name = name
                        supplier.tax_id = self.var_tax_id.get().strip() or None
                        supplier.phone = self.var_phone.get().strip() or None
                        supplier.email = self.var_email.get().strip() or None
                        supplier.notes = self.var_condition.get().strip() or None
                    msg = f"Proveedor '{name}' actualizado correctamente."
                
                session.commit()
            
            AlertModal(self, "Éxito", msg, kind="success")
            self._load_data()
        except Exception as e:
            AlertModal(self, "Error al guardar", str(e), kind="error")

    def _deactivate_supplier(self) -> None:
        if not self._selected_supplier_id:
            return
        name = self.var_name.get()
        ConfirmModal(
            self,
            title="Desactivar proveedor",
            message=f"¿Desactivar '{name}'?",
            on_confirm=self._do_deactivate,
            confirm_text="Desactivar",
            danger=True,
        )

    def _do_deactivate(self) -> None:
        try:
            with SessionLocal() as session:
                supplier = session.get(Supplier, self._selected_supplier_id)
                if supplier:
                    supplier.is_active = False
                    session.commit()
            AlertModal(self, "Éxito", "Proveedor desactivado.", kind="success")
            self._new_supplier()
            self._load_data()
        except Exception as e:
            AlertModal(self, "Error", str(e), kind="error")

    def _load_data(self) -> None:
        try:
            with SessionLocal() as session:
                repo = SupplierRepository(session)
                suppliers = repo.get_active()
            self._update_table(suppliers)
        except Exception as e:
            AlertModal(self, "Error", f"Error cargando: {e}", kind="error")

    def _search_data(self, query: str) -> None:
        try:
            with SessionLocal() as session:
                repo = SupplierRepository(session)
                suppliers = repo.search(query)
            self._update_table(suppliers)
        except Exception:
            pass
            
    def _update_table(self, suppliers: list[Supplier]) -> None:
        self._suppliers_cache = suppliers
        rows = []
        for s in suppliers:
            rows.append([
                s.name,
                s.tax_id or "—",
                s.phone or "—",
                s.email or "—",
                s.notes or "—",
                "✔ Activo" if s.is_active else "✖ Inactivo",
            ])
        self.table.load(rows)
