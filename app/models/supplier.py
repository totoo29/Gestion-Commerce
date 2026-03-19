# app/models/supplier.py
from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class Supplier(Base, TimestampMixin):
    """Proveedor de mercaderia."""
    __tablename__ = "suppliers"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    tax_id: Mapped[str | None] = mapped_column(String(20), unique=True, nullable=True)  # CUIT
    contact_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    email: Mapped[str | None] = mapped_column(String(200), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(30), nullable=True)
    address: Mapped[str | None] = mapped_column(String(300), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)

    # Relacion inversa
    purchases: Mapped[list["Purchase"]] = relationship(back_populates="supplier")  # type: ignore[name-defined]

    def __repr__(self) -> str:
        return f"<Supplier {self.name}>"
