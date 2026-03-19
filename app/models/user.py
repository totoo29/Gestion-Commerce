# app/models/user.py
from sqlalchemy import Boolean, ForeignKey, String, Table, Column
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

# Tabla de asociacion Many-to-Many entre User y Role
user_roles = Table(
    "user_roles",
    Base.metadata,
    Column("user_id", ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
    Column("role_id", ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True),
)


class Role(Base):
    """Rol del sistema: admin, cajero, etc."""
    __tablename__ = "roles"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(String(200), nullable=True)

    # Relacion inversa
    users: Mapped[list["User"]] = relationship(
        secondary=user_roles, back_populates="roles"
    )

    def __repr__(self) -> str:
        return f"<Role {self.name}>"


class User(Base, TimestampMixin):
    """Usuario del sistema (cajero, administrador)."""
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    full_name: Mapped[str] = mapped_column(String(150), nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relaciones
    roles: Mapped[list[Role]] = relationship(
        secondary=user_roles, back_populates="users"
    )
    sales: Mapped[list["Sale"]] = relationship(back_populates="seller")  # type: ignore[name-defined]

    def has_role(self, role_name: str) -> bool:
        return any(r.name == role_name for r in self.roles)

    def __repr__(self) -> str:
        return f"<User {self.username}>"
