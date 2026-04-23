# app/ui/components/data_table.py
from typing import Callable, Any

import customtkinter as ctk

from app.ui.theme import COLORS, FONTS, SIZES


class DataTable(ctk.CTkFrame):
    """
    Tabla de datos reutilizable con:
    - Encabezados configurables
    - Paginacion integrada
    - Seleccion de fila con callback
    - Colores alternados por fila
    - Soporte de anchos de columna personalizados

    Uso:
        table = DataTable(
            parent,
            columns=["Codigo", "Nombre", "Precio", "Stock"],
            col_widths=[100, 300, 120, 80],
            on_select=lambda row_data: print(row_data),
        )
        table.load([
            ["001", "Tornillo 6mm", "$1.50", "200"],
            ["002", "Tuerca M8",    "$0.80", "150"],
        ])
    """

    PAGE_SIZE = 20  # Filas por pagina

    def __init__(
        self,
        master,
        columns: list[str],
        col_widths: list[int] | None = None,
        col_weights: list[int] | None = None,
        col_aligns: list[str] | None = None,
        on_select: Callable[[list], None] | None = None,
        page_size: int = PAGE_SIZE,
        **kwargs,
    ):
        super().__init__(master, fg_color=COLORS["bg_panel"], corner_radius=8, **kwargs)
        self.columns = columns
        self.col_widths = col_widths or self._default_widths(columns)
        self.col_weights = col_weights or [0] * len(columns)
        self.col_aligns = col_aligns or ["w"] * len(columns)
        self.on_select = on_select
        self.page_size = page_size

        self._all_rows: list[list] = []
        self._current_page: int = 0
        self._selected_index: int | None = None
        self._row_frames: list[ctk.CTkFrame] = []

        self._build_ui()

    # ── Construccion ──────────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        # Encabezados
        header = ctk.CTkFrame(self, fg_color=COLORS["bg_card"], corner_radius=0)
        header.pack(fill="x")

        for i, col in enumerate(self.columns):
            header.grid_columnconfigure(i, weight=self.col_weights[i])
            # Para títulos usamos la misma alineación o "w" si es center
            anchor_h = "center" if self.col_aligns[i] == "center" else self.col_aligns[i]
            sticky_h = "ew" if self.col_weights[i] > 0 else ("w" if anchor_h=="w" else ("e" if anchor_h=="e" else "ew"))
            
            ctk.CTkLabel(
                header,
                text=col,
                font=FONTS["body_bold"],
                text_color=COLORS["text_primary"],
                width=self.col_widths[i] if self.col_weights[i] == 0 else 0,
                anchor=anchor_h,
            ).grid(row=0, column=i, padx=(SIZES["padding_sm"], SIZES["padding_sm"]), pady=6, sticky=sticky_h)

        # Area de filas (scrollable)
        self.rows_frame = ctk.CTkScrollableFrame(
            self,
            fg_color="transparent",
            scrollbar_button_color=COLORS["border"],
            scrollbar_button_hover_color=COLORS["accent"],
        )
        self.rows_frame.pack(fill="both", expand=True)

        # Paginacion
        self.pagination = ctk.CTkFrame(self, fg_color=COLORS["bg_card"], height=40)
        self.pagination.pack(fill="x")
        self.pagination.pack_propagate(False)

        self.btn_prev = ctk.CTkButton(
            self.pagination,
            text="◀ Anterior",
            width=110,
            height=28,
            font=FONTS["small"],
            fg_color=COLORS["btn_neutral"],
            hover_color=COLORS["btn_neutral_hover"],
            command=self._prev_page,
        )
        self.btn_prev.pack(side="left", padx=SIZES["padding_sm"], pady=6)

        self.lbl_page = ctk.CTkLabel(
            self.pagination,
            text="Página 1 de 1",
            font=FONTS["small"],
            text_color=COLORS["text_secondary"],
        )
        self.lbl_page.pack(side="left", expand=True)

        self.lbl_total = ctk.CTkLabel(
            self.pagination,
            text="0 registros",
            font=FONTS["small"],
            text_color=COLORS["text_disabled"],
        )
        self.lbl_total.pack(side="left", padx=SIZES["padding"])

        self.btn_next = ctk.CTkButton(
            self.pagination,
            text="Siguiente ▶",
            width=110,
            height=28,
            font=FONTS["small"],
            fg_color=COLORS["btn_neutral"],
            hover_color=COLORS["btn_neutral_hover"],
            command=self._next_page,
        )
        self.btn_next.pack(side="right", padx=SIZES["padding_sm"], pady=6)

    # ── API publica ───────────────────────────────────────────────────────────

    def load(self, rows: list[list]) -> None:
        """Carga todos los datos y muestra la primera pagina."""
        self._all_rows = rows
        self._current_page = 0
        self._selected_index = None
        self._render_page()

    def clear(self) -> None:
        """Vacia la tabla."""
        self.load([])

    def get_selected(self) -> list | None:
        """Retorna los datos de la fila seleccionada o None."""
        if self._selected_index is None:
            return None
        page_start = self._current_page * self.page_size
        abs_index = page_start + self._selected_index
        if abs_index < len(self._all_rows):
            return self._all_rows[abs_index]
        return None

    def total_rows(self) -> int:
        return len(self._all_rows)

    # ── Renderizado ───────────────────────────────────────────────────────────

    def _render_page(self) -> None:
        # Limpiar filas anteriores
        for widget in self.rows_frame.winfo_children():
            widget.destroy()
        self._row_frames.clear()
        self._selected_index = None

        total = len(self._all_rows)
        total_pages = max(1, -(-total // self.page_size))  # ceil division
        page_start = self._current_page * self.page_size
        page_rows = self._all_rows[page_start: page_start + self.page_size]

        # Filas
        for i, row_data in enumerate(page_rows):
            bg = COLORS["bg_input"] if i % 2 == 0 else COLORS["bg_panel"]
            row_frame = ctk.CTkFrame(
                self.rows_frame,
                fg_color=bg,
                corner_radius=0,
                height=SIZES["row_height"],
                cursor="hand2",
            )
            row_frame.pack(fill="x")
            row_frame.pack_propagate(False)

            for j, cell in enumerate(row_data):
                row_frame.grid_columnconfigure(j, weight=self.col_weights[j])
                anchor_h = self.col_aligns[j]
                sticky_h = "ew" if self.col_weights[j] > 0 else ("w" if anchor_h=="w" else ("e" if anchor_h=="e" else "ew"))
                
                ctk.CTkLabel(
                    row_frame,
                    text=str(cell),
                    font=FONTS["body"],
                    text_color=COLORS["text_primary"],
                    width=self.col_widths[j] if self.col_weights[j] == 0 else 0,
                    anchor=anchor_h,
                ).grid(row=0, column=j, padx=(SIZES["padding_sm"], SIZES["padding_sm"]), pady=4, sticky=sticky_h)

            # Evento de seleccion
            row_frame.bind("<Button-1>", lambda e, idx=i: self._select_row(idx))
            for child in row_frame.winfo_children():
                child.bind("<Button-1>", lambda e, idx=i: self._select_row(idx))

            self._row_frames.append(row_frame)

        # Fila vacia si no hay datos
        if not page_rows:
            ctk.CTkLabel(
                self.rows_frame,
                text="Sin resultados.",
                font=FONTS["body"],
                text_color=COLORS["text_disabled"],
            ).pack(pady=24)

        # Paginacion
        self.lbl_page.configure(
            text=f"Página {self._current_page + 1} de {total_pages}"
        )
        self.lbl_total.configure(text=f"{total} registros")
        self.btn_prev.configure(state="normal" if self._current_page > 0 else "disabled")
        self.btn_next.configure(
            state="normal" if self._current_page < total_pages - 1 else "disabled"
        )

    def _select_row(self, index: int) -> None:
        # Deseleccionar anterior
        if self._selected_index is not None and self._selected_index < len(self._row_frames):
            i = self._selected_index
            bg = COLORS["bg_input"] if i % 2 == 0 else COLORS["bg_panel"]
            self._row_frames[i].configure(fg_color=bg)

        # Seleccionar nueva
        self._selected_index = index
        if index < len(self._row_frames):
            self._row_frames[index].configure(fg_color=COLORS["bg_card"])

        if self.on_select:
            data = self.get_selected()
            if data is not None:
                self.on_select(data)

    def _prev_page(self) -> None:
        if self._current_page > 0:
            self._current_page -= 1
            self._render_page()

    def _next_page(self) -> None:
        total = len(self._all_rows)
        total_pages = max(1, -(-total // self.page_size))
        if self._current_page < total_pages - 1:
            self._current_page += 1
            self._render_page()

    # ── Helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def _default_widths(columns: list[str]) -> list[int]:
        """Asigna anchos uniformes si no se especifican."""
        return [160] * len(columns)
