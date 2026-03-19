# app/ui/views/reports_view.py
"""
Vista de Reportes y Administracion del sistema.

Tabs:
    1. Reportes PDF    — generar ticket retroactivo, factura, reporte de inventario
    2. Backups         — lista de backups, crear manual, restaurar
    3. Configuracion   — datos del negocio editables sin tocar el .env
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Callable

import customtkinter as ctk

from app.core.config import settings
from app.core.logging import get_logger
from app.services.backup_service import BackupService
from app.ui.components.modal import AlertModal, ConfirmModal
from app.ui.components import AppShell, ShellConfig
from app.ui.theme import COLORS, FONTS, SIZES

logger = get_logger(__name__)


class ReportsView(ctk.CTkFrame):

    def __init__(self, master: ctk.CTk, navigate: Callable, **kwargs):
        super().__init__(master, fg_color=COLORS["bg_main"], **kwargs)
        self.navigate = navigate
        self._backups: list[Path] = []
        self._build_ui()
        self._load_backups()

    # ── Construccion ──────────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        shell = AppShell(
            self,
            navigate=self.navigate,
            config=ShellConfig(title="Reportes", active_view="reports"),
        )
        shell.pack(fill="both", expand=True)

        main = ctk.CTkFrame(shell.content, fg_color="transparent")
        main.pack(side="left", fill="both", expand=True)

        ctk.CTkLabel(main, text="Reportes y Sistema", font=FONTS["subtitle"],
                     text_color=COLORS["text_primary"]).pack(anchor="w",
                                                              pady=(0, SIZES["padding"]))

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

        self.tabview.add("📄  Reportes PDF")
        self.tabview.add("💾  Backups")
        self.tabview.add("⚙  Configuración")

        self._build_tab_reports(self.tabview.tab("📄  Reportes PDF"))
        self._build_tab_backups(self.tabview.tab("💾  Backups"))
        self._build_tab_config(self.tabview.tab("⚙  Configuración"))

    # ── Tab 1: Reportes PDF ───────────────────────────────────────────────────

    def _build_tab_reports(self, parent: ctk.CTkFrame) -> None:
        pad = SIZES["padding"]

        scroll = ctk.CTkScrollableFrame(parent, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=pad, pady=pad)

        # ── Reporte de inventario ─────────────────────────────────────────────
        self._report_card(
            scroll,
            icon="📦",
            title="Reporte de Inventario",
            description=(
                "Genera un PDF A4 con el stock actual de todos los productos.\n"
                "Incluye estado CRÍTICO / BAJO / OK con badges de color."
            ),
            btn_text="Generar reporte",
            btn_command=self._gen_stock_report,
        )

        # ── Ticket por numero de venta ────────────────────────────────────────
        self._report_card(
            scroll,
            icon="🧾",
            title="Ticket de venta (por N° de venta)",
            description="Reimprime o genera el ticket térmico de una venta ya registrada.",
            btn_text="Generar ticket",
            btn_command=None,          # Se activa con el campo de ID
            extra_widget=self._build_sale_id_row(scroll, "ticket"),
        )

        # ── Factura por numero de venta ───────────────────────────────────────
        self._report_card(
            scroll,
            icon="📋",
            title="Factura A4 (por N° de venta)",
            description="Genera la factura A4 completa de una venta registrada.",
            btn_text="Generar factura",
            btn_command=None,
            extra_widget=self._build_sale_id_row(scroll, "factura"),
        )

    def _report_card(
        self,
        parent,
        icon: str,
        title: str,
        description: str,
        btn_text: str,
        btn_command: Callable | None,
        extra_widget=None,
    ) -> ctk.CTkFrame:
        card = ctk.CTkFrame(parent, fg_color=COLORS["bg_panel"], corner_radius=10)
        card.pack(fill="x", pady=(0, SIZES["padding"]))

        top = ctk.CTkFrame(card, fg_color="transparent")
        top.pack(fill="x", padx=SIZES["padding"], pady=(SIZES["padding"], 0))

        ctk.CTkLabel(top, text=f"{icon}  {title}", font=FONTS["heading"],
                     text_color=COLORS["text_primary"]).pack(side="left")

        if btn_command:
            ctk.CTkButton(
                top, text=btn_text, height=34, font=FONTS["body"],
                fg_color=COLORS["accent"], hover_color=COLORS["accent_hover"],
                command=btn_command,
            ).pack(side="right")

        ctk.CTkLabel(card, text=description, font=FONTS["small"],
                     text_color=COLORS["text_secondary"],
                     justify="left", anchor="w").pack(
            fill="x", padx=SIZES["padding"], pady=(4, SIZES["padding_sm"]))

        if extra_widget:
            extra_widget.pack(fill="x", padx=SIZES["padding"],
                              pady=(0, SIZES["padding"]))

        return card

    def _build_sale_id_row(self, parent, mode: str) -> ctk.CTkFrame:
        """Fila con campo ID de venta + botón generar."""
        row = ctk.CTkFrame(parent, fg_color="transparent")

        var = ctk.StringVar()
        ctk.CTkEntry(
            row, textvariable=var,
            placeholder_text="N° de venta (ej: 42)",
            width=180, height=32,
            font=FONTS["body"],
            fg_color=COLORS["bg_input"],
            border_color=COLORS["border"],
            text_color=COLORS["text_primary"],
        ).pack(side="left", padx=(0, 8))

        def _gen():
            sale_id_str = var.get().strip()
            if not sale_id_str.isdigit():
                AlertModal(self, "ID inválido",
                           "Ingrese un número de venta válido.", kind="warning")
                return
            sale_id = int(sale_id_str)
            if mode == "ticket":
                self._gen_ticket(sale_id)
            else:
                self._gen_invoice(sale_id)

        ctk.CTkButton(
            row, text=f"Generar {'ticket' if mode == 'ticket' else 'factura'}",
            height=32, font=FONTS["body"],
            fg_color=COLORS["accent"], hover_color=COLORS["accent_hover"],
            command=_gen,
        ).pack(side="left")

        return row

    # ── Tab 2: Backups ────────────────────────────────────────────────────────

    def _build_tab_backups(self, parent: ctk.CTkFrame) -> None:
        pad = SIZES["padding"]

        # Acciones
        actions = ctk.CTkFrame(parent, fg_color="transparent")
        actions.pack(fill="x", padx=pad, pady=pad)

        ctk.CTkButton(
            actions, text="💾  Crear backup ahora",
            height=36, font=FONTS["body_bold"],
            fg_color=COLORS["btn_success"], hover_color=COLORS["btn_success_hover"],
            command=self._create_backup_now,
        ).pack(side="left", padx=(0, 8))

        ctk.CTkButton(
            actions, text="📂  Abrir carpeta",
            height=36, font=FONTS["body"],
            fg_color=COLORS["btn_neutral"], hover_color=COLORS["btn_neutral_hover"],
            command=self._open_backup_folder,
        ).pack(side="left", padx=(0, 8))

        ctk.CTkButton(
            actions, text="↺  Actualizar lista",
            height=36, font=FONTS["body"],
            fg_color=COLORS["btn_neutral"], hover_color=COLORS["btn_neutral_hover"],
            command=self._load_backups,
        ).pack(side="left")

        # Info de config
        ctk.CTkLabel(
            parent,
            text=(f"Directorio: {settings.BACKUP_DIR}\n"
                  f"Retención: {settings.BACKUP_KEEP_DAYS} días  •  "
                  f"Backup automático: cada 24 horas al iniciar la app"),
            font=FONTS["small"],
            text_color=COLORS["text_secondary"],
            justify="left", anchor="w",
        ).pack(fill="x", padx=pad, pady=(0, SIZES["padding_sm"]))

        ctk.CTkFrame(parent, fg_color=COLORS["border"], height=1).pack(fill="x", padx=pad)

        # Lista de backups
        ctk.CTkLabel(parent, text="Backups disponibles:", font=FONTS["small"],
                     text_color=COLORS["text_secondary"], anchor="w").pack(
            fill="x", padx=pad, pady=(SIZES["padding_sm"], 4))

        self.backup_list_frame = ctk.CTkScrollableFrame(
            parent, fg_color="transparent",
            scrollbar_button_color=COLORS["border"],
        )
        self.backup_list_frame.pack(fill="both", expand=True, padx=pad, pady=(0, pad))

    # ── Tab 3: Configuracion ──────────────────────────────────────────────────

    def _build_tab_config(self, parent: ctk.CTkFrame) -> None:
        pad = SIZES["padding"]

        scroll = ctk.CTkScrollableFrame(parent, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=pad, pady=pad)

        ctk.CTkLabel(
            scroll,
            text=(
                "Estos valores se guardan en el archivo .env de la aplicación.\n"
                "Aparecen en los tickets y facturas generados."
            ),
            font=FONTS["small"],
            text_color=COLORS["text_secondary"],
            justify="left", anchor="w",
        ).pack(fill="x", pady=(0, SIZES["padding"]))

        # Campos de configuracion del negocio
        self._config_fields: dict[str, ctk.StringVar] = {}

        config_items = [
            ("BUSINESS_NAME",    "Nombre del negocio *",    settings.BUSINESS_NAME),
            ("BUSINESS_ADDRESS", "Dirección",                settings.BUSINESS_ADDRESS),
            ("BUSINESS_PHONE",   "Teléfono",                 settings.BUSINESS_PHONE),
            ("BUSINESS_EMAIL",   "Email",                    settings.BUSINESS_EMAIL),
            ("BUSINESS_TAX_ID",  "CUIT",                     settings.BUSINESS_TAX_ID),
            ("BUSINESS_SLOGAN",  "Slogan (pie del ticket)",  settings.BUSINESS_SLOGAN),
        ]

        for key, label, current in config_items:
            ctk.CTkLabel(scroll, text=label, font=FONTS["small"],
                         text_color=COLORS["text_secondary"], anchor="w").pack(fill="x", pady=(8, 0))
            var = ctk.StringVar(value=current)
            self._config_fields[key] = var
            ctk.CTkEntry(
                scroll, textvariable=var,
                height=SIZES["input_height"],
                font=FONTS["body"],
                fg_color=COLORS["bg_input"],
                border_color=COLORS["border"],
                text_color=COLORS["text_primary"],
            ).pack(fill="x", pady=(2, 0))

        ctk.CTkButton(
            scroll,
            text="💾  Guardar configuración",
            height=SIZES["btn_height"],
            font=FONTS["body_bold"],
            fg_color=COLORS["btn_success"],
            hover_color=COLORS["btn_success_hover"],
            command=self._save_config,
        ).pack(fill="x", pady=(SIZES["padding"], 0))

    # ── Acciones: PDFs ────────────────────────────────────────────────────────

    def _gen_stock_report(self) -> None:
        try:
            from reports.pdf_service import print_stock_report
            path = print_stock_report(auto_open=True)
            AlertModal(self, "Reporte generado",
                       f"Archivo guardado en:\n{path}", kind="success")
        except Exception as e:
            logger.error(f"Error generando reporte de stock: {e}")
            AlertModal(self, "Error", str(e), kind="error")

    def _gen_ticket(self, sale_id: int) -> None:
        try:
            from reports.pdf_service import print_ticket
            path = print_ticket(sale_id, auto_open=True)
            AlertModal(self, "Ticket generado",
                       f"Ticket #{sale_id} guardado en:\n{path}", kind="success")
        except Exception as e:
            logger.error(f"Error generando ticket: {e}")
            AlertModal(self, "Error", str(e), kind="error")

    def _gen_invoice(self, sale_id: int) -> None:
        try:
            from reports.pdf_service import print_invoice
            path = print_invoice(sale_id, auto_open=True)
            AlertModal(self, "Factura generada",
                       f"Factura #{sale_id} guardada en:\n{path}", kind="success")
        except Exception as e:
            logger.error(f"Error generando factura: {e}")
            AlertModal(self, "Error", str(e), kind="error")

    # ── Acciones: Backups ─────────────────────────────────────────────────────

    def _load_backups(self) -> None:
        try:
            self._backups = BackupService().list_backups()
        except Exception:
            self._backups = []

        for w in self.backup_list_frame.winfo_children():
            w.destroy()

        if not self._backups:
            ctk.CTkLabel(
                self.backup_list_frame,
                text="No hay backups disponibles.",
                font=FONTS["body"],
                text_color=COLORS["text_disabled"],
            ).pack(pady=20)
            return

        for i, backup_path in enumerate(self._backups):
            row = ctk.CTkFrame(
                self.backup_list_frame,
                fg_color=COLORS["bg_input"] if i % 2 == 0 else COLORS["bg_panel"],
                corner_radius=4, height=36,
            )
            row.pack(fill="x", pady=1)
            row.pack_propagate(False)

            # Nombre + fecha de modificacion
            mtime = datetime.fromtimestamp(backup_path.stat().st_mtime)
            size_kb = backup_path.stat().st_size // 1024

            ctk.CTkLabel(
                row,
                text=backup_path.name,
                font=FONTS["mono"],
                text_color=COLORS["text_primary"],
                anchor="w",
            ).pack(side="left", padx=SIZES["padding_sm"], fill="x", expand=True)

            ctk.CTkLabel(
                row,
                text=f"{mtime.strftime('%d/%m/%Y %H:%M')}  •  {size_kb} KB",
                font=FONTS["small"],
                text_color=COLORS["text_secondary"],
            ).pack(side="left", padx=SIZES["padding_sm"])

            ctk.CTkButton(
                row, text="Restaurar",
                width=80, height=26,
                font=FONTS["small"],
                fg_color=COLORS["btn_neutral"],
                hover_color=COLORS["btn_danger"],
                command=lambda p=backup_path: self._confirm_restore(p),
            ).pack(side="right", padx=SIZES["padding_sm"])

    def _create_backup_now(self) -> None:
        try:
            path = BackupService().create_backup()
            AlertModal(
                self, "Backup creado",
                f"Backup guardado exitosamente:\n{path.name}",
                kind="success",
            )
            self._load_backups()
        except FileNotFoundError:
            AlertModal(self, "Sin datos",
                       "La base de datos no existe aún. Cree al menos una venta primero.",
                       kind="warning")
        except Exception as e:
            AlertModal(self, "Error", str(e), kind="error")

    def _open_backup_folder(self) -> None:
        import subprocess, sys
        try:
            path = settings.BACKUP_DIR
            path.mkdir(parents=True, exist_ok=True)
            if sys.platform == "win32":
                import os
                os.startfile(str(path))
            elif sys.platform == "darwin":
                subprocess.Popen(["open", str(path)])
            else:
                subprocess.Popen(["xdg-open", str(path)])
        except Exception as e:
            AlertModal(self, "Error", str(e), kind="error")

    def _confirm_restore(self, backup_path: Path) -> None:
        ConfirmModal(
            self,
            title="Restaurar base de datos",
            message=(
                f"¿Restaurar la base de datos desde:\n{backup_path.name}?\n\n"
                "⚠ ATENCIÓN: Se reemplazará la base de datos actual.\n"
                "La aplicación se cerrará para completar la restauración."
            ),
            on_confirm=lambda: self._do_restore(backup_path),
            confirm_text="Restaurar",
            danger=True,
        )

    def _do_restore(self, backup_path: Path) -> None:
        try:
            BackupService().restore_from_backup(backup_path)
            AlertModal(
                self,
                "Restauración completada",
                "La base de datos fue restaurada.\nCierre y vuelva a abrir la aplicación.",
                kind="success",
            )
        except Exception as e:
            AlertModal(self, "Error al restaurar", str(e), kind="error")

    # ── Acciones: Config ──────────────────────────────────────────────────────

    def _save_config(self) -> None:
        """
        Escribe los cambios de configuracion al archivo .env.
        Si .env no existe, lo crea.
        """
        try:
            env_path = Path(".env")

            # Leer el .env existente (si hay)
            existing_lines: list[str] = []
            if env_path.exists():
                existing_lines = env_path.read_text(encoding="utf-8").splitlines()

            # Clave -> nuevo valor
            new_values = {
                key: var.get().strip()
                for key, var in self._config_fields.items()
            }

            # Actualizar o agregar cada clave
            updated_keys = set()
            result_lines: list[str] = []

            for line in existing_lines:
                stripped = line.strip()
                if stripped.startswith("#") or "=" not in stripped:
                    result_lines.append(line)
                    continue
                key = stripped.split("=", 1)[0].strip()
                if key in new_values:
                    result_lines.append(f'{key}="{new_values[key]}"')
                    updated_keys.add(key)
                else:
                    result_lines.append(line)

            # Agregar las claves que no estaban en el .env
            for key, value in new_values.items():
                if key not in updated_keys:
                    result_lines.append(f'{key}="{value}"')

            env_path.write_text("\n".join(result_lines) + "\n", encoding="utf-8")

            # Actualizar el objeto settings en memoria para efecto inmediato
            for key, value in new_values.items():
                if hasattr(settings, key):
                    setattr(settings, key, value)

            AlertModal(
                self, "Configuración guardada",
                "Los cambios se aplicarán en el próximo ticket o reporte generado.",
                kind="success",
            )
        except Exception as e:
            logger.error(f"Error guardando configuracion: {e}")
            AlertModal(self, "Error", str(e), kind="error")
