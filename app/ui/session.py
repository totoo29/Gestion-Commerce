# app/ui/session.py
"""
Singleton global que mantiene el estado del usuario autenticado.
Se inicializa al hacer login y se limpia al cerrar sesion.

Uso:
    from app.ui.session import AppSession
    AppSession.login(user)
    AppSession.user_id       # int
    AppSession.username      # str
    AppSession.is_admin      # bool
    AppSession.logout()
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.models.user import User


@dataclass
class _AppSession:
    """Estado de la sesion activa. No instanciar directamente: usar AppSession."""
    user_id:   int | None = field(default=None)
    username:  str        = field(default="")
    full_name: str        = field(default="")
    roles:     list[str]  = field(default_factory=list)
    _logged_in: bool      = field(default=False)

    def login(self, user: "User") -> None:
        """Registra el usuario autenticado en la sesion global."""
        self.user_id   = user.id
        self.username  = user.username
        self.full_name = user.full_name
        self.roles     = [r.name for r in user.roles]
        self._logged_in = True

    def logout(self) -> None:
        """Limpia todos los datos de sesion."""
        self.user_id   = None
        self.username  = ""
        self.full_name = ""
        self.roles     = []
        self._logged_in = False

    @property
    def is_logged_in(self) -> bool:
        return self._logged_in

    @property
    def is_admin(self) -> bool:
        return "admin" in self.roles

    @property
    def display_name(self) -> str:
        """Nombre para mostrar en la UI."""
        return self.full_name or self.username


# Instancia global unica
AppSession = _AppSession()
