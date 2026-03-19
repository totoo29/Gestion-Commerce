# tests/unit/test_auth_service.py
import pytest
from sqlalchemy.orm import Session

from app.core.exceptions import CredencialesInvalidasError, UsuarioNoEncontradoError
from app.services.auth_service import AuthService


class TestAuthService:

    def test_create_user_success(self, session: Session):
        """Crear un usuario nuevo con rol asignado."""
        service = AuthService(session)
        user = service.create_user(
            username="cajero1",
            full_name="Juan Perez",
            password="segura123",
            role_names=["cajero"],
        )

        assert user.id is not None
        assert user.username == "cajero1"
        assert user.full_name == "Juan Perez"
        assert user.is_active is True
        assert len(user.roles) == 1
        assert user.roles[0].name == "cajero"

    def test_login_success(self, session: Session, admin_user):
        """Login exitoso con credenciales correctas."""
        service = AuthService(session)
        user = service.login("admin_test", "test1234")

        assert user.username == "admin_test"

    def test_login_wrong_password(self, session: Session, admin_user):
        """Login con contrasena incorrecta lanza CredencialesInvalidasError."""
        service = AuthService(session)

        with pytest.raises(CredencialesInvalidasError):
            service.login("admin_test", "contrasena_incorrecta")

    def test_login_nonexistent_user(self, session: Session):
        """Login con usuario que no existe lanza UsuarioNoEncontradoError."""
        service = AuthService(session)

        with pytest.raises(UsuarioNoEncontradoError):
            service.login("usuario_fantasma", "cualquier_cosa")

    def test_login_inactive_user(self, session: Session, admin_user):
        """Login con usuario inactivo lanza CredencialesInvalidasError."""
        admin_user.is_active = False
        session.flush()

        service = AuthService(session)
        with pytest.raises(CredencialesInvalidasError):
            service.login("admin_test", "test1234")

    def test_ensure_admin_creates_default(self, session: Session):
        """ensure_admin_exists crea el usuario admin si no existe."""
        service = AuthService(session)
        service.ensure_admin_exists()

        # Debe poder loguear con credenciales por defecto
        user = service.login("admin", "admin1234")
        assert user.username == "admin"
        assert user.has_role("admin")

    def test_ensure_admin_idempotent(self, session: Session):
        """Llamar ensure_admin_exists dos veces no duplica el usuario."""
        service = AuthService(session)
        service.ensure_admin_exists()
        service.ensure_admin_exists()  # Segunda llamada no debe fallar

        from sqlalchemy import select
        from app.models.user import User
        stmt = select(User).where(User.username == "admin")
        admins = list(session.scalars(stmt).all())
        assert len(admins) == 1

    def test_change_password(self, session: Session, admin_user):
        """Cambio de contrasena permite login con la nueva contrasena."""
        service = AuthService(session)
        service.change_password(admin_user.id, "nueva_contrasena_456")

        # Login con contrasena nueva funciona
        user = service.login("admin_test", "nueva_contrasena_456")
        assert user.id == admin_user.id

        # Login con contrasena vieja falla
        with pytest.raises(CredencialesInvalidasError):
            service.login("admin_test", "test1234")

    def test_create_user_reuses_existing_role(self, session: Session):
        """Si el rol ya existe, no se crea uno nuevo."""
        service = AuthService(session)
        service.create_user("user1", "User 1", "pass1", ["cajero"])
        service.create_user("user2", "User 2", "pass2", ["cajero"])

        from sqlalchemy import select
        from app.models.user import Role
        stmt = select(Role).where(Role.name == "cajero")
        roles = list(session.scalars(stmt).all())
        assert len(roles) == 1  # Solo un rol "cajero"
