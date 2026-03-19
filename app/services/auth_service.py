# app/services/auth_service.py
from sqlalchemy.orm import Session

from app.core.exceptions import CredencialesInvalidasError, UsuarioNoEncontradoError
from app.core.logging import get_logger
from app.core.security import hash_password, verify_password
from app.models.user import User
from app.repository.user_repository import UserRepository

logger = get_logger(__name__)


class AuthService:

    def __init__(self, session: Session):
        self.session = session
        self.user_repo = UserRepository(session)

    def login(self, username: str, password: str) -> User:
        """
        Valida credenciales y retorna el usuario autenticado.
        Lanza excepcion si el usuario no existe, esta inactivo
        o la contrasena es incorrecta.
        """
        user = self.user_repo.get_by_username(username)

        if user is None:
            logger.warning(f"Intento de login con usuario inexistente: '{username}'")
            raise UsuarioNoEncontradoError(username)

        if not user.is_active:
            logger.warning(f"Intento de login con usuario inactivo: '{username}'")
            raise CredencialesInvalidasError(f"Usuario '{username}' esta desactivado.")

        if not verify_password(password, user.hashed_password):
            logger.warning(f"Contrasena incorrecta para usuario: '{username}'")
            raise CredencialesInvalidasError("Contrasena incorrecta.")

        logger.info(f"Login exitoso: '{username}'")
        return user

    def create_user(
        self,
        username: str,
        full_name: str,
        password: str,
        role_names: list[str],
    ) -> User:
        """
        Crea un nuevo usuario con los roles indicados.
        Si un rol no existe, lo crea automaticamente.
        """
        user = User(
            username=username,
            full_name=full_name,
            hashed_password=hash_password(password),
        )

        for role_name in role_names:
            role = self.user_repo.get_role_by_name(role_name)
            if role is None:
                role = self.user_repo.create_role(role_name)
            user.roles.append(role)

        self.user_repo.create(user)
        self.session.commit()

        logger.info(f"Usuario creado: '{username}' con roles {role_names}")
        return user

    def change_password(self, user_id: int, new_password: str) -> None:
        """Cambia la contrasena de un usuario existente."""
        user = self.user_repo.get_by_id(user_id)
        if user is None:
            raise UsuarioNoEncontradoError(str(user_id))

        user.hashed_password = hash_password(new_password)
        self.session.commit()
        logger.info(f"Contrasena cambiada para usuario id={user_id}")

    def ensure_admin_exists(self) -> None:
        """
        Verifica que exista al menos un usuario admin.
        Si no hay ninguno, crea el usuario por defecto.
        Llamar al iniciar la app por primera vez.
        """
        admin = self.user_repo.get_by_username("admin")
        if admin is None:
            self.create_user(
                username="admin",
                full_name="Administrador",
                password="admin1234",
                role_names=["admin"],
            )
            logger.info("Usuario admin por defecto creado (contrasena: admin1234)")
