# app/models/customer.py
from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class Customer(Base, TimestampMixin):
    """Cliente del comercio. Opcional en ventas (puede ser consumidor final)."""
    __tablename__ = "customers"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    full_name: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    tax_id: Mapped[str | None] = mapped_column(String(20), unique=True, nullable=True)  # CUIT/DNI
    email: Mapped[str | None] = mapped_column(String(200), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(30), nullable=True)
    address: Mapped[str | None] = mapped_column(String(300), nullable=True)
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)

    # Relacion inversa
    sales: Mapped[list["Sale"]] = relationship(back_populates="customer")  # type: ignore[name-defined]
    invoices: Mapped[list["Invoice"]] = relationship(back_populates="customer")  # type: ignore[name-defined]

    def __repr__(self) -> str:
        return f"<Customer {self.full_name}>"
