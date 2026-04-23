import os
from typing import Callable
from tkinter import filedialog
import customtkinter as ctk

from app.core.app_settings import ApplicationSettings
from app.ui.components import AppShell, ShellConfig
from app.ui.components.modal import AlertModal
from app.ui.theme import COLORS, FONTS, SIZES

class SettingsView(ctk.CTkFrame):
    """
    Vista de configuración de la facturación y sistema.
    """
    
    def __init__(self, master: ctk.CTk, navigate: Callable, **kwargs):
        super().__init__(master, fg_color=COLORS["bg_main"], **kwargs)
        self.navigate = navigate
        self._build_ui()
        self._load_data()

    def _build_ui(self) -> None:
        shell = AppShell(
            self,
            navigate=self.navigate,
            config=ShellConfig(title="Configuración General", active_view="settings"),
        )
        shell.pack(fill="both", expand=True)

        main = ctk.CTkFrame(shell.content, fg_color="transparent")
        main.pack(fill="both", expand=True)

        card = ctk.CTkFrame(
            main, 
            fg_color=COLORS["bg_panel"],
            corner_radius=SIZES["radius_lg"],
            border_width=1,
            border_color=COLORS["border"],
        )
        card.pack(fill="x", padx=SIZES["padding_lg"], pady=SIZES["padding_lg"])

        ctk.CTkLabel(
            card,
            text="Datos Formales e Impresión (Tickets y Facturas)",
            font=FONTS["subtitle"],
            text_color=COLORS["text_primary"]
        ).pack(anchor="w", padx=SIZES["padding_lg"], pady=(SIZES["padding_lg"], SIZES["padding"]))

        self.var_company_name = ctk.StringVar()
        self.var_company_id = ctk.StringVar()
        self.var_address = ctk.StringVar()
        self.var_phone = ctk.StringVar()
        self.var_footer = ctk.StringVar()
        self.var_logo = ctk.StringVar()
        self.var_format = ctk.StringVar()

        self._make_input(card, "Nombre Comercial:", self.var_company_name)
        self._make_input(card, "CUIT / RUT / Documento:", self.var_company_id)
        self._make_input(card, "Dirección Comercial:", self.var_address)
        self._make_input(card, "Teléfono de Contacto:", self.var_phone)
        self._make_input(card, "Agradecimiento pie (Ticket):", self.var_footer)

        # Selector de Logo
        row_logo = ctk.CTkFrame(card, fg_color="transparent")
        row_logo.pack(fill="x", padx=SIZES["padding_lg"], pady=(0, SIZES["padding"]))
        ctk.CTkLabel(row_logo, text="Logo Empresa:", width=180, anchor="e", font=FONTS["body"], text_color=COLORS["text_secondary"]).pack(side="left", padx=(0, 16))
        
        self.entry_logo = ctk.CTkEntry(row_logo, textvariable=self.var_logo, height=36, fg_color=COLORS["bg_input"], text_color=COLORS["text_primary"])
        self.entry_logo.pack(side="left", fill="x", expand=True)
        self.entry_logo.configure(state="disabled")

        ctk.CTkButton(row_logo, text="Examinar...", width=100, height=36, command=self._browse_logo, fg_color=COLORS["btn_neutral"], hover_color=COLORS["btn_neutral_hover"], font=FONTS["small"]).pack(side="left", padx=(8, 0))

        # Selector de formato
        row_fmt = ctk.CTkFrame(card, fg_color="transparent")
        row_fmt.pack(fill="x", padx=SIZES["padding_lg"], pady=(0, SIZES["padding"]))
        ctk.CTkLabel(row_fmt, text="Formato de Impresión:", width=180, anchor="e", font=FONTS["body"], text_color=COLORS["text_secondary"]).pack(side="left", padx=(0, 16))
        ctk.CTkRadioButton(row_fmt, text="Ticket Térmico (80mm)", variable=self.var_format, value="80mm", text_color=COLORS["text_primary"]).pack(side="left", padx=(0, 16))
        ctk.CTkRadioButton(row_fmt, text="Factura Tradicional (A4)", variable=self.var_format, value="A4", text_color=COLORS["text_primary"]).pack(side="left")

        # Botón Guardar
        ctk.CTkButton(
            card,
            text="✔ Guardar Diseño",
            font=FONTS["body_bold"],
            height=40,
            fg_color=COLORS["btn_success"],
            hover_color=COLORS["btn_success_hover"],
            command=self._save_data
        ).pack(anchor="e", padx=SIZES["padding_lg"], pady=SIZES["padding_lg"])

    def _make_input(self, parent, label_text, str_var) -> None:
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", padx=SIZES["padding_lg"], pady=(0, SIZES["padding"]))
        ctk.CTkLabel(
            row, text=label_text, width=180, anchor="e", 
            font=FONTS["body"], text_color=COLORS["text_secondary"]
        ).pack(side="left", padx=(0, 16))
        ctk.CTkEntry(
            row, textvariable=str_var, height=36, 
            font=FONTS["body"], fg_color=COLORS["bg_input"], text_color=COLORS["text_primary"]
        ).pack(side="left", fill="x", expand=True)

    def _browse_logo(self) -> None:
        path = filedialog.askopenfilename(
            title="Seleccionar Logo",
            filetypes=[("Imágenes", "*.png;*.jpg;*.jpeg")]
        )
        if path:
            self.entry_logo.configure(state="normal")
            self.var_logo.set(path)
            self.entry_logo.configure(state="disabled")

    def _load_data(self) -> None:
        settings = ApplicationSettings.get_settings()
        self.var_company_name.set(settings.get("company_name", ""))
        self.var_company_id.set(settings.get("company_id", ""))
        self.var_address.set(settings.get("address", ""))
        self.var_phone.set(settings.get("phone", ""))
        self.var_footer.set(settings.get("footer_text", ""))
        self.var_format.set(settings.get("print_format", "80mm"))
        
        self.entry_logo.configure(state="normal")
        self.var_logo.set(settings.get("logo_path", ""))
        self.entry_logo.configure(state="disabled")

    def _save_data(self) -> None:
        ApplicationSettings.save_settings(
            company_name=self.var_company_name.get(),
            company_id=self.var_company_id.get(),
            address=self.var_address.get(),
            phone=self.var_phone.get(),
            footer_text=self.var_footer.get(),
            logo_path=self.var_logo.get(),
            print_format=self.var_format.get()
        )
        AlertModal(self, "Configuración guardada", "Los datos del diseño de facturación se han actualizado correctamente. Esto se aplicará a todos los próximos tickets y remitos.", kind="success")
