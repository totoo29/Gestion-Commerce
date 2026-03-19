# app/repository/user_repository.py
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.models.user import Role, User
from app.repository.base_repository import BaseRepository


class UserRepository(BaseRepository[User]):

    def __init__(self, session: Session):
        super().__init__(session, User)

    def get_by_username(self, username: str) -> User | None:
        """Busca un usuario por nombre de usuario (case-sensitive)."""
        stmt = (
            select(User)
            .where(User.username == username)
            .options(joinedload(User.roles))
        )
        return self.session.scalars(stmt).first()

    def get_by_id_with_roles(self, user_id: int) -> User | None:
        """Carga el usuario junto con sus roles en una sola query."""
        stmt = (
            select(User)
            .where(User.id == user_id)
            .options(joinedload(User.roles))
        )
        return self.session.scalars(stmt).first()

    def get_active_users(self) -> list[User]:
        """Retorna todos los usuarios activos."""
        stmt = select(User).where(User.is_active == True)  # noqa: E712
        return list(self.session.scalars(stmt).all())

    def get_role_by_name(self, name: str) -> Role | None:
        stmt = select(Role).where(Role.name == name)
        return self.session.scalars(stmt).first()

    def create_role(self, name: str, description: str | None = None) -> Role:
        role = Role(name=name, description=description)
        self.session.add(role)
        self.session.flush()
        return role
