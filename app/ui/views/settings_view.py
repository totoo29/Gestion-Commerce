from __future__ import annotations

from typing import Callable

import customtkinter as ctk

from app.core.config import settings
from app.ui.components.modal import AlertModal
from app.ui.components import AppShell, ShellConfig
from app.ui.theme import COLORS, FONTS, SIZES


class SettingsView(ctk.CTkFrame):
    """Configuración (tema + datos del negocio)."""

    def __init__(self, master: ctk.CTk, navigate: Callable, **kwargs):
        super().__init__(master, fg_color=COLORS["bg_main"], **kwargs)
        self.navigate = navigate
        self._build_ui()

    def _build_ui(self) -> None:
        shell = AppShell(
            self,
            navigate=self.navigate,
            config=ShellConfig(title="Configuración", active_view="settings"),
        )
        shell.pack(fill="both", expand=True)

        page = ctk.CTkFrame(shell.content, fg_color="transparent")
        page.grid(row=0, column=0, sticky="nsew")
        page.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            page,
            text="Configuración",
            font=FONTS["title"],
            text_color=COLORS["text_primary"],
        ).grid(row=0, column=0, sticky="w", pady=(0, SIZES["padding"]))

        grid = ctk.CTkFrame(page, fg_color="transparent")
        grid.grid(row=1, column=0, sticky="ew")
        grid.grid_columnconfigure((0, 1), weight=1, uniform="cols")

        # Card: Datos del negocio
        card_biz = ctk.CTkFrame(
            grid,
            fg_color=COLORS["bg_panel"],
            corner_radius=SIZES["radius_lg"],
            border_width=1,
            border_color=COLORS["border"],
        )
        card_biz.grid(row=0, column=0, sticky="nsew", pady=(0, SIZES["padding"]))

        ctk.CTkLabel(
            card_biz,
            text="Datos del negocio",
            font=FONTS["heading"],
            text_color=COLORS["text_primary"],
        ).pack(anchor="w", padx=SIZES["padding"], pady=(SIZES["padding"], 0))

        ctk.CTkLabel(
            card_biz,
            text="Se usan en tickets, facturas y reportes.",
            font=FONTS["small"],
            text_color=COLORS["text_secondary"],
        ).pack(anchor="w", padx=SIZES["padding"], pady=(4, SIZES["padding_sm"]))

        form = ctk.CTkFrame(card_biz, fg_color="transparent")
        form.pack(fill="x", padx=SIZES["padding"], pady=(0, SIZES["padding"]))

        self.var_name = ctk.StringVar(value=settings.BUSINESS_NAME)
        self.var_address = ctk.StringVar(value=settings.BUSINESS_ADDRESS)
        self.var_phone = ctk.StringVar(value=settings.BUSINESS_PHONE)
        self.var_email = ctk.StringVar(value=settings.BUSINESS_EMAIL)

        for label, var in [
            ("Nombre", self.var_name),
            ("Dirección", self.var_address),
            ("Teléfono", self.var_phone),
            ("Email", self.var_email),
        ]:
            ctk.CTkLabel(
                form,
                text=label,
                font=FONTS["small"],
                text_color=COLORS["text_secondary"],
                anchor="w",
            ).pack(fill="x", pady=(8, 0))
            ctk.CTkEntry(
                form,
                textvariable=var,
                height=SIZES["input_height"],
                font=FONTS["body"],
                fg_color=COLORS["bg_input"],
                border_color=COLORS["border"],
                text_color=COLORS["text_primary"],
            ).pack(fill="x", pady=(2, 0))

        ctk.CTkButton(
            card_biz,
            text="Guardar",
            height=36,
            font=FONTS["body_bold"],
            fg_color=COLORS["btn_success"],
            hover_color=COLORS["btn_success_hover"],
            command=self._save_business_settings,
        ).pack(fill="x", padx=SIZES["padding"], pady=(0, SIZES["padding"]))

    def _save_business_settings(self) -> None:
        """
        Persiste datos del negocio en .env (mismo formato que ReportsView).
        """
        try:
            from pathlib import Path

            env_path = Path(".env")
            existing = env_path.read_text(encoding="utf-8").splitlines() if env_path.exists() else []

            new_values = {
                "BUSINESS_NAME": self.var_name.get().strip(),
                "BUSINESS_ADDRESS": self.var_address.get().strip(),
                "BUSINESS_PHONE": self.var_phone.get().strip(),
                "BUSINESS_EMAIL": self.var_email.get().strip(),
            }

            updated = set()
            out: list[str] = []
            for line in existing:
                stripped = line.strip()
                if stripped.startswith("#") or "=" not in stripped:
                    out.append(line)
                    continue
                key = stripped.split("=", 1)[0].strip()
                if key in new_values:
                    out.append(f'{key}="{new_values[key]}"')
                    updated.add(key)
                else:
                    out.append(line)

            for key, value in new_values.items():
                if key not in updated:
                    out.append(f'{key}="{value}"')

            env_path.write_text("\n".join(out) + "\n", encoding="utf-8")

            for key, value in new_values.items():
                if hasattr(settings, key):
                    setattr(settings, key, value)

            AlertModal(self, "Guardado", "Configuración actualizada.", kind="success")
        except Exception as e:
            AlertModal(self, "Error", str(e), kind="error")

