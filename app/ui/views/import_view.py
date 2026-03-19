# app/ui/views/import_view.py
"""
Vista de importacion de productos desde Excel.

Flujo:
    1. Usuario selecciona el archivo con el selector de archivos
    2. Se muestra una tabla de preview con las primeras 10 filas
    3. Se muestra el mapeo de columnas detectado
    4. Usuario confirma → se ejecuta la importacion
    5. Se muestra el resultado fila a fila (creados / actualizados / errores)
"""
from __future__ import annotations

import threading
from pathlib import Path
from typing import Callable

import customtkinter as ctk
from tkinter import filedialog

from app.core.logging import get_logger
from app.database import SessionLocal
from app.ui.components.modal import AlertModal
from app.ui.components.navbar import Navbar
from app.ui.theme import COLORS, FONTS, SIZES

logger = get_logger(__name__)

ACCEPTED_EXTENSIONS = [
    ("Archivos Excel / CSV", "*.xlsx *.xls *.xlsm *.csv"),
    ("Excel",                "*.xlsx *.xls *.xlsm"),
    ("CSV",                  "*.csv"),
    ("Todos",                "*.*"),
]


class ImportView(ctk.CTkFrame):

    def __init__(self, master: ctk.CTk, navigate: Callable, **kwargs):
        super().__init__(master, fg_color=COLORS["bg_main"], **kwargs)
        self.navigate = navigate
        self._file_path: Path | None = None
        self._col_mapping_vars: list[tuple[str, ctk.StringVar]] = []
        self._current_mapping: dict[str, str] = {}
        self._build_ui()

    # ── Construccion ──────────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        Navbar(self, navigate=self.navigate, active_view="import").pack(side="left", fill="y")
        ctk.CTkFrame(self, fg_color=COLORS["border"], width=1).pack(side="left", fill="y")

        main = ctk.CTkFrame(self, fg_color=COLORS["bg_main"])
        main.pack(side="left", fill="both", expand=True,
                  padx=SIZES["padding"], pady=SIZES["padding"])

        # Titulo
        ctk.CTkLabel(main, text="Importar productos desde Excel",
                     font=FONTS["subtitle"],
                     text_color=COLORS["text_primary"]).pack(anchor="w",
                                                              pady=(0, SIZES["padding"]))

        # ── Paso 1: seleccion de archivo ──────────────────────────────────────
        step1 = ctk.CTkFrame(main, fg_color=COLORS["bg_panel"], corner_radius=10)
        step1.pack(fill="x", pady=(0, SIZES["padding"]))

        ctk.CTkLabel(step1, text="1. Seleccionar archivo",
                     font=FONTS["heading"],
                     text_color=COLORS["text_primary"]).pack(
            anchor="w", padx=SIZES["padding"], pady=(SIZES["padding"], SIZES["padding_sm"]))

        file_row = ctk.CTkFrame(step1, fg_color="transparent")
        file_row.pack(fill="x", padx=SIZES["padding"], pady=(0, SIZES["padding"]))

        self.file_label = ctk.CTkLabel(
            file_row,
            text="Ningún archivo seleccionado",
            font=FONTS["body"],
            text_color=COLORS["text_secondary"],
            anchor="w",
        )
        self.file_label.pack(side="left", fill="x", expand=True)

        ctk.CTkButton(
            file_row, text="📂  Examinar...",
            height=36, font=FONTS["body"],
            fg_color=COLORS["btn_neutral"],
            hover_color=COLORS["btn_neutral_hover"],
            command=self._pick_file,
        ).pack(side="right")

        # Tip de formato
        ctk.CTkLabel(
            step1,
            text=(
                "Columnas reconocidas: SKU/Codigo, Nombre, Descripcion, Unidad, Precio, "
                "Stock, Stock_Minimo, Categoria, Barcode\n"
                "El encabezado debe estar en la primera fila. "
                "Formatos: .xlsx  .xls  .csv"
            ),
            font=FONTS["small"],
            text_color=COLORS["text_disabled"],
            justify="left", anchor="w",
            wraplength=700,
        ).pack(anchor="w", padx=SIZES["padding"], pady=(0, SIZES["padding"]))

        # ── Paso 2: preview ───────────────────────────────────────────────────
        step2 = ctk.CTkFrame(main, fg_color=COLORS["bg_panel"], corner_radius=10)
        step2.pack(fill="x", pady=(0, SIZES["padding"]))

        ctk.CTkLabel(step2, text="2. Vista previa",
                     font=FONTS["heading"],
                     text_color=COLORS["text_primary"]).pack(
            anchor="w", padx=SIZES["padding"], pady=(SIZES["padding"], SIZES["padding_sm"]))

        self.preview_frame = ctk.CTkScrollableFrame(
            step2, fg_color="transparent", height=160,
            scrollbar_button_color=COLORS["border"],
        )
        self.preview_frame.pack(fill="x", padx=SIZES["padding"],
                                pady=(0, SIZES["padding"]))

        self.preview_status = ctk.CTkLabel(
            step2, text="Seleccioná un archivo para ver la vista previa.",
            font=FONTS["small"], text_color=COLORS["text_disabled"],
        )
        self.preview_status.pack(pady=(0, SIZES["padding"]))

        # ── Paso 3: confirmar ─────────────────────────────────────────────────
        step3 = ctk.CTkFrame(main, fg_color=COLORS["bg_panel"], corner_radius=10)
        step3.pack(fill="x", pady=(0, SIZES["padding"]))

        ctk.CTkLabel(step3, text="3. Importar",
                     font=FONTS["heading"],
                     text_color=COLORS["text_primary"]).pack(
            anchor="w", padx=SIZES["padding"], pady=(SIZES["padding"], SIZES["padding_sm"]))

        btn_row = ctk.CTkFrame(step3, fg_color="transparent")
        btn_row.pack(fill="x", padx=SIZES["padding"], pady=(0, SIZES["padding"]))

        self.import_btn = ctk.CTkButton(
            btn_row, text="⬆  Importar productos",
            height=40, font=FONTS["body_bold"],
            fg_color=COLORS["accent"], hover_color=COLORS["accent_hover"],
            state="disabled",
            command=self._start_import,
        )
        self.import_btn.pack(side="left", padx=(0, 8))

        self.progress_bar = ctk.CTkProgressBar(
            btn_row, width=200, height=10,
            fg_color=COLORS["bg_input"],
            progress_color=COLORS["accent"],
        )
        self.progress_bar.set(0)
        self.progress_bar.pack(side="left", padx=(0, 8))
        self.progress_bar.pack_forget()   # ocultar hasta importar

        self.status_label = ctk.CTkLabel(
            btn_row, text="",
            font=FONTS["small"],
            text_color=COLORS["text_secondary"],
        )
        self.status_label.pack(side="left")

        # ── Resultados ────────────────────────────────────────────────────────
        ctk.CTkLabel(main, text="Resultados",
                     font=FONTS["heading"],
                     text_color=COLORS["text_primary"]).pack(
            anchor="w", pady=(0, 4))

        self.results_frame = ctk.CTkScrollableFrame(
            main, fg_color=COLORS["bg_panel"],
            scrollbar_button_color=COLORS["border"],
        )
        self.results_frame.pack(fill="both", expand=True)

        ctk.CTkLabel(
            self.results_frame,
            text="Los resultados de la importación aparecerán aquí.",
            font=FONTS["small"], text_color=COLORS["text_disabled"],
        ).pack(pady=20)

    # ── Seleccion de archivo ──────────────────────────────────────────────────

    def _pick_file(self) -> None:
        path = filedialog.askopenfilename(
            title="Seleccionar archivo de productos",
            filetypes=ACCEPTED_EXTENSIONS,
        )
        if not path:
            return

        self._file_path = Path(path)
        self.file_label.configure(
            text=self._file_path.name,
            text_color=COLORS["text_primary"],
        )
        self._load_preview()

    # ── Preview ───────────────────────────────────────────────────────────────

    def _load_preview(self) -> None:
        """Lee las primeras filas y las muestra en la tabla de preview."""
        for w in self.preview_frame.winfo_children():
            w.destroy()
        self.preview_status.configure(text="Cargando preview...")

        try:
            import pandas as pd
            ext = self._file_path.suffix.lower()

            if ext in (".xlsx", ".xls", ".xlsm"):
                df = pd.read_excel(self._file_path, dtype=str, nrows=8)
            else:
                try:
                    df = pd.read_csv(self._file_path, dtype=str, nrows=8, encoding="utf-8")
                except UnicodeDecodeError:
                    df = pd.read_csv(self._file_path, dtype=str, nrows=8, encoding="latin-1")

            df = df.fillna("")

            if df.empty:
                self.preview_status.configure(text="⚠  El archivo está vacío.")
                return

            # Encabezado de columnas y Mapeo
            cols = list(df.columns)
            col_w = max(100, min(150, 700 // len(cols)))

            header_labels = ctk.CTkFrame(self.preview_frame, fg_color=COLORS["bg_card"])
            header_labels.pack(fill="x", pady=0)
            
            header_combos = ctk.CTkFrame(self.preview_frame, fg_color=COLORS["bg_card"])
            header_combos.pack(fill="x", pady=(0, 2))

            FIELD_OPTIONS = ["(Ignorar)", "sku", "name", "description", "unit", "price", "stock", "min_stock", "category", "barcode"]
            from app.services.import_service import COLUMN_ALIASES

            self._col_mapping_vars = []

            for col in cols:
                # Nombre original de la columna
                ctk.CTkLabel(
                    header_labels, text=str(col)[:18],
                    width=col_w, font=FONTS["small_bold"],
                    text_color=COLORS["text_secondary"], anchor="w",
                ).pack(side="left", padx=2)
                
                # Combobox para mapear al campo de la BD
                var = ctk.StringVar()
                norm_col = str(col).strip().lower().replace("  ", " ")
                canonical = COLUMN_ALIASES.get(norm_col)
                var.set(canonical if canonical else "(Ignorar)")
                
                combo = ctk.CTkOptionMenu(
                    header_combos, values=FIELD_OPTIONS, variable=var,
                    width=col_w, height=28, font=FONTS["small"],
                    fg_color=COLORS["bg_input"], button_color=COLORS["border"],
                    button_hover_color=COLORS["border_focus"],
                )
                combo.pack(side="left", padx=2, pady=4)
                
                self._col_mapping_vars.append((col, var))

            # Filas de datos
            for i, (_, row) in enumerate(df.iterrows()):
                bg = COLORS["bg_input"] if i % 2 == 0 else COLORS["bg_panel"]
                fr = ctk.CTkFrame(self.preview_frame, fg_color=bg)
                fr.pack(fill="x", pady=0)
                for col in cols:
                    ctk.CTkLabel(
                        fr, text=str(row[col])[:20],
                        width=col_w, font=FONTS["small"],
                        text_color=COLORS["text_secondary"], anchor="w",
                    ).pack(side="left", padx=2)

            total_rows = len(pd.read_excel(self._file_path, dtype=str)) \
                if ext in (".xlsx", ".xls", ".xlsm") else \
                sum(1 for _ in open(self._file_path, encoding="utf-8", errors="ignore")) - 1

            self.preview_status.configure(
                text=f"✅  {total_rows} filas detectadas  •  {len(cols)} columnas: {', '.join(cols[:8])}",
                text_color=COLORS["text_primary"],
            )
            self.import_btn.configure(state="normal")

        except Exception as e:
            self.preview_status.configure(
                text=f"❌  Error leyendo el archivo: {e}",
                text_color=COLORS["btn_danger"],
            )
            logger.error(f"Error en preview: {e}")

    # ── Importacion ───────────────────────────────────────────────────────────

    def _start_import(self) -> None:
        if not self._file_path:
            return

        self.import_btn.configure(state="disabled")
        self.progress_bar.pack(side="left", padx=(0, 8))
        self.progress_bar.configure(mode="indeterminate")
        self.progress_bar.start()
        self.status_label.configure(text="Importando...", text_color=COLORS["text_secondary"])

        for w in self.results_frame.winfo_children():
            w.destroy()

        # Construir el mapeo seleccionado
        self._current_mapping = {}
        for col_name, var in self._col_mapping_vars:
            val = var.get()
            if val != "(Ignorar)":
                self._current_mapping[col_name] = val

        # Ejecutar en hilo separado para no bloquear la UI
        thread = threading.Thread(target=self._run_import, daemon=True)
        thread.start()

    def _run_import(self) -> None:
        try:
            from app.services.import_service import ImportService
            with SessionLocal() as session:
                svc    = ImportService(session)
                result = svc.import_from_file(self._file_path, self._current_mapping)
            # Volver al hilo de Tkinter para actualizar la UI
            self.after(0, lambda r=result: self._show_results(r))
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Error en importacion: {error_msg}")
            self.after(0, lambda m=error_msg: self._show_import_error(m))

    def _show_results(self, result) -> None:
        """Muestra la tabla de resultados después de la importacion."""
        self.progress_bar.stop()
        self.progress_bar.pack_forget()
        self.import_btn.configure(state="normal")

        # Resumen en el status label
        color = COLORS["btn_success"] if result.success else COLORS["btn_danger"]
        self.status_label.configure(text=result.summary(), text_color=color)

        # Limpiar resultados anteriores
        for w in self.results_frame.winfo_children():
            w.destroy()

        # Tarjeta de resumen
        summary_card = ctk.CTkFrame(self.results_frame,
                                    fg_color=COLORS["bg_card"], corner_radius=8)
        summary_card.pack(fill="x", padx=SIZES["padding_sm"],
                          pady=(SIZES["padding_sm"], SIZES["padding"]))

        for label, value, color_key in [
            ("Total procesados",  str(result.total),   "text_primary"),
            ("✅ Nuevos",          str(result.created), "btn_success"),
            ("🔄 Actualizados",   str(result.updated), "accent"),
            ("❌ Errores",        str(result.errors),  "btn_danger" if result.errors else "text_disabled"),
        ]:
            row = ctk.CTkFrame(summary_card, fg_color="transparent")
            row.pack(fill="x", padx=SIZES["padding"], pady=2)
            ctk.CTkLabel(row, text=label, font=FONTS["small"],
                         text_color=COLORS["text_secondary"]).pack(side="left")
            ctk.CTkLabel(row, text=value, font=FONTS["body_bold"],
                         text_color=COLORS[color_key]).pack(side="right")

        # Tabla de detalle fila por fila
        if result.rows:
            ctk.CTkLabel(
                self.results_frame,
                text="Detalle por fila:",
                font=FONTS["small"],
                text_color=COLORS["text_secondary"],
                anchor="w",
            ).pack(fill="x", padx=SIZES["padding_sm"], pady=(0, 4))

            ACTION_CONFIG = {
                "created": ("✅ Nuevo",       COLORS["btn_success"]),
                "updated": ("🔄 Actualizado", COLORS["accent"]),
                "skipped": ("— Omitido",      COLORS["text_disabled"]),
                "error":   ("❌ Error",        COLORS["btn_danger"]),
            }

            MAX_SHOW = 100
            for i, row in enumerate(result.rows):
                if i >= MAX_SHOW:
                    ctk.CTkLabel(self.results_frame, text=f"... y {len(result.rows) - MAX_SHOW} filas más ocultas por rendimiento.",
                                 font=FONTS["small_bold"], text_color=COLORS["text_secondary"]).pack(pady=8)
                    break

                bg = COLORS["bg_input"] if i % 2 == 0 else COLORS["bg_panel"]
                fr = ctk.CTkFrame(self.results_frame, fg_color=bg, height=28)
                fr.pack(fill="x", padx=SIZES["padding_sm"], pady=0)
                fr.pack_propagate(False)

                action_txt, action_color = ACTION_CONFIG.get(
                    row.action, (row.action, COLORS["text_secondary"])
                )

                ctk.CTkLabel(fr, text=f"F{row.row_number}", width=35,
                             font=FONTS["mono"], text_color=COLORS["text_disabled"],
                             anchor="w").pack(side="left", padx=(4, 0))

                ctk.CTkLabel(fr, text=row.sku[:14], width=110,
                             font=FONTS["mono"], text_color=COLORS["text_secondary"],
                             anchor="w").pack(side="left", padx=2)

                ctk.CTkLabel(fr, text=row.name[:32], font=FONTS["small"],
                             text_color=COLORS["text_primary"], anchor="w").pack(
                    side="left", fill="x", expand=True, padx=2)

                ctk.CTkLabel(fr, text=action_txt, width=110,
                             font=FONTS["small_bold"], text_color=action_color,
                             anchor="e").pack(side="right", padx=4)

                if row.error:
                    ctk.CTkLabel(fr, text=f"⚠ {row.error[:50]}",
                                 font=FONTS["small"], text_color=COLORS["btn_danger"],
                                 anchor="w").pack(side="right", padx=4)

    def _show_import_error(self, msg: str) -> None:
        self.progress_bar.stop()
        self.progress_bar.pack_forget()
        self.import_btn.configure(state="normal")
        self.status_label.configure(text="Error en la importación",
                                    text_color=COLORS["btn_danger"])
        AlertModal(self, "Error al importar", msg, kind="error")
