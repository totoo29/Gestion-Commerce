# app/ui/views/login_view.py
import json
from pathlib import Path
from typing import Callable

import customtkinter as ctk

from app.core.config import settings, BASE_DIR
from app.core.exceptions import CredencialesInvalidasError, UsuarioNoEncontradoError
from app.core.logging import get_logger
from app.database import SessionLocal
from app.services.auth_service import AuthService
from app.ui.session import AppSession
from app.ui.theme import COLORS, FONTS, SIZES

logger = get_logger(__name__)


class LoginView(ctk.CTkFrame):
    """
    Pantalla de inicio de sesion.
    Se muestra al iniciar la app y al cerrar sesion.
    Al autenticar correctamente navega al dashboard.
    """

    def __init__(self, master: ctk.CTk, navigate: Callable, **kwargs):
        super().__init__(master, fg_color=COLORS["bg_main"], **kwargs)
        self.navigate = navigate
        
        self.remember_file = BASE_DIR / ".remembered_user.json"
        
        self._build_ui()
        
        self._load_remembered_user()
        
        # Foco automatico en el campo usuario al abrir (si no hay uno guardado)
        if not self.entry_username.get():
            self.after(100, lambda: self.entry_username.focus_set())
        else:
            self.after(100, lambda: self.entry_password.focus_set())

    # ── Construccion de la UI ─────────────────────────────────────────────────

    def _build_ui(self) -> None:
        # Centrar el formulario vertical y horizontalmente
        self.grid_rowconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(2, weight=1)

        # Card central
        card = ctk.CTkFrame(
            self,
            fg_color=COLORS["bg_panel"],
            corner_radius=16,
            width=420,
            border_width=1,
            border_color=COLORS["border"],
        )
        card.grid(row=1, column=1, padx=20, pady=20)
        card.grid_propagate(False)
        card.configure(width=420, height=520)

        # ── Logo / Titulo ─────────────────────────────────────────────────────
        ctk.CTkLabel(
            card,
            text="DevMont",
            font=("Segoe UI", 32, "bold"),
            text_color=COLORS["accent"],
        ).pack(pady=(48, 0))

        ctk.CTkLabel(
            card,
            text="Commerce",
            font=("Segoe UI", 18),
            text_color=COLORS["text_secondary"],
        ).pack(pady=(0, 4))

        ctk.CTkLabel(
            card,
            text="Sistema de Gestión Comercial",
            font=FONTS["small"],
            text_color=COLORS["text_disabled"],
        ).pack(pady=(0, 4))

        ctk.CTkLabel(
            card,
            text="Bienvenido, inicia sesión para continuar",
            font=FONTS["body"],
            text_color=COLORS["text_secondary"],
        ).pack(pady=(0, 28))

        # ── Campos ───────────────────────────────────────────────────────────
        ctk.CTkLabel(
            card,
            text="Usuario",
            font=FONTS["body_bold"],
            text_color=COLORS["text_secondary"],
            anchor="w",
        ).pack(fill="x", padx=40)

        self.entry_username = ctk.CTkEntry(
            card,
            placeholder_text="Ingrese su usuario",
            height=SIZES["input_height"],
            font=FONTS["body"],
            fg_color=COLORS["bg_input"],
            border_color=COLORS["border"],
            text_color=COLORS["text_primary"],
        )
        self.entry_username.pack(fill="x", padx=40, pady=(4, 2))

        ctk.CTkLabel(
            card,
            text="Usa tu nombre de usuario asignado por el sistema.",
            font=FONTS["small"],
            text_color=COLORS["text_disabled"],
            anchor="w",
        ).pack(fill="x", padx=40, pady=(0, 12))

        ctk.CTkLabel(
            card,
            text="Contraseña",
            font=FONTS["body_bold"],
            text_color=COLORS["text_secondary"],
            anchor="w",
        ).pack(fill="x", padx=40)

        password_frame = ctk.CTkFrame(
            card,
            fg_color="transparent",
        )
        password_frame.pack(fill="x", padx=40, pady=(4, 4))

        self.entry_password = ctk.CTkEntry(
            password_frame,
            placeholder_text="Ingrese su contraseña",
            show="●",
            height=SIZES["input_height"],
            font=FONTS["body"],
            fg_color=COLORS["bg_input"],
            border_color=COLORS["border"],
            text_color=COLORS["text_primary"],
        )
        self.entry_password.pack(side="left", fill="x", expand=True)

        self._password_visible = False
        self.btn_toggle_password = ctk.CTkButton(
            password_frame,
            width=36,
            text="👁",
            font=FONTS["body"],
            fg_color="transparent",
            text_color=COLORS["text_secondary"],
            hover_color=COLORS["bg_card"],
            command=self._toggle_password_visibility,
        )
        self.btn_toggle_password.pack(side="left", padx=(8, 0))

        options_frame = ctk.CTkFrame(
            card,
            fg_color="transparent",
        )
        options_frame.pack(fill="x", padx=40, pady=(0, 8))

        self.chk_remember = ctk.CTkCheckBox(
            options_frame,
            text="Recordarme en este equipo",
            font=FONTS["small"],
            text_color=COLORS["text_secondary"],
        )
        self.chk_remember.pack(side="left")

        self.btn_forgot = ctk.CTkButton(
            options_frame,
            text="¿Olvidaste tu contraseña?",
            fg_color="transparent",
            text_color=COLORS["accent_light"],
            hover_color=COLORS["bg_card"],
            font=FONTS["small"],
            width=0,
            command=self._on_forgot_password,
        )
        self.btn_forgot.pack(side="right")

        # ── Mensaje de error ──────────────────────────────────────────────────
        self.lbl_error = ctk.CTkLabel(
            card,
            text="",
            font=FONTS["small"],
            text_color=COLORS["error"],
            height=20,
        )
        self.lbl_error.pack(pady=(0, 8))

        # ── Boton ingresar ────────────────────────────────────────────────────
        self.btn_login = ctk.CTkButton(
            card,
            text="INGRESAR",
            height=SIZES["btn_height"] + 4,
            font=("Segoe UI", 14, "bold"),
            fg_color=COLORS["accent"],
            hover_color=COLORS["accent_hover"],
            command=self._do_login,
        )
        self.btn_login.pack(fill="x", padx=40, pady=(8, 0))

        ctk.CTkFrame(
            card,
            height=1,
            fg_color=COLORS["border"],
        ).pack(fill="x", padx=40, pady=(16, 8))

        # ── Version ───────────────────────────────────────────────────────────
        ctk.CTkLabel(
            card,
            text="v1.0.0",
            font=FONTS["small"],
            text_color=COLORS["text_disabled"],
        ).pack(side="bottom", pady=16)

        # Enter en cualquier campo dispara el login
        self.entry_username.bind("<Return>", lambda e: self.entry_password.focus_set())
        self.entry_password.bind("<Return>", lambda e: self._do_login())

    # ── Logica ────────────────────────────────────────────────────────────────

    def _do_login(self) -> None:
        username = self.entry_username.get().strip()
        password = self.entry_password.get()

        if not username:
            self._show_error("Ingrese su nombre de usuario.")
            self.entry_username.focus_set()
            return

        if not password:
            self._show_error("Ingrese su contraseña.")
            self.entry_password.focus_set()
            return

        # Deshabilitar boton mientras procesa
        self.btn_login.configure(state="disabled", text="Ingresando...")
        self.update_idletasks()

        try:
            with SessionLocal() as session:
                service = AuthService(session)
                user = service.login(username, password)

            # Guardar sesion global
            AppSession.login(user)
            logger.info(f"Login exitoso en UI: {username}")
            
            # Recordar usuario si el checkbox está marcado
            if self.chk_remember.get():
                try:
                    with open(self.remember_file, "w") as f:
                        json.dump({"username": username}, f)
                except Exception as e:
                    logger.error(f"Error guardando recordatorio de usuario: {e}")
            else:
                # Limpiar si no está marcado
                if self.remember_file.exists():
                    try:
                        self.remember_file.unlink()
                    except Exception as e:
                        logger.error(f"Error borrando recordatorio de usuario: {e}")

            # Navegar al dashboard
            self.navigate("dashboard")

        except (UsuarioNoEncontradoError, CredencialesInvalidasError):
            self._show_error("Usuario o contraseña incorrectos.")
            self.entry_password.delete(0, "end")
            self.entry_password.focus_set()

        except Exception as e:
            logger.error(f"Error inesperado en login: {e}")
            self._show_error("Error del sistema. Intente nuevamente.")

        finally:
            # Puede que la vista haya sido destruida al navegar al dashboard
            if self.winfo_exists() and getattr(self, "btn_login", None) and self.btn_login.winfo_exists():
                self.btn_login.configure(state="normal", text="INGRESAR")

    def _show_error(self, message: str) -> None:
        self.lbl_error.configure(text=message)

    def _toggle_password_visibility(self) -> None:
        self._password_visible = not self._password_visible
        if self._password_visible:
            self.entry_password.configure(show="")
            self.btn_toggle_password.configure(text="●")
        else:
            self.entry_password.configure(show="●")
            self.btn_toggle_password.configure(text="👁")

    def _on_forgot_password(self) -> None:
        self._show_error("Si olvidaste tu contraseña, contacta al administrador del sistema.")

    def _load_remembered_user(self) -> None:
        if self.remember_file.exists():
            try:
                with open(self.remember_file, "r") as f:
                    data = json.load(f)
                    if "username" in data:
                        self.entry_username.insert(0, data["username"])
                        self.chk_remember.select()
            except Exception as e:
                logger.error(f"Error cargando recordatorio de usuario: {e}")
