# app/models/sale.py
from decimal import Decimal

from sqlalchemy import ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class Sale(Base, TimestampMixin):
    """
    Cabecera de una venta.
    Una venta puede tener uno o mas items (SaleDetail).
    """
    __tablename__ = "sales"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    # FK opcionales
    seller_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    customer_id: Mapped[int | None] = mapped_column(
        ForeignKey("customers.id", ondelete="SET NULL"), nullable=True
    )

    # Totales
    subtotal: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    discount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0, nullable=False)
    tax: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0, nullable=False)
    total: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)

    # Pago
    payment_method: Mapped[str] = mapped_column(String(50), default="efectivo", nullable=False)
    amount_paid: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    change_given: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0, nullable=False)

    # Estado: pending | completed | cancelled
    status: Mapped[str] = mapped_column(String(20), default="completed", nullable=False, index=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relaciones
    seller: Mapped["User"] = relationship(back_populates="sales")  # type: ignore[name-defined]
    customer: Mapped["Customer | None"] = relationship(back_populates="sales")  # type: ignore[name-defined]
    details: Mapped[list["SaleDetail"]] = relationship(
        back_populates="sale", cascade="all, delete-orphan"
    )
    invoice: Mapped["Invoice | None"] = relationship(back_populates="sale", uselist=False)  # type: ignore[name-defined]

    def __repr__(self) -> str:
        return f"<Sale id={self.id} total={self.total} status={self.status}>"


class SaleDetail(Base):
    """Linea de detalle de una venta: producto, cantidad y precio al momento de la venta."""
    __tablename__ = "sale_details"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    sale_id: Mapped[int] = mapped_column(
        ForeignKey("sales.id", ondelete="CASCADE"), nullable=False
    )
    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id", ondelete="RESTRICT"), nullable=False
    )
    quantity: Mapped[Decimal] = mapped_column(Numeric(12, 3), nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)  # Precio al momento de la venta
    discount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0, nullable=False)
    subtotal: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)

    # Relaciones
    sale: Mapped[Sale] = relationship(back_populates="details")
    product: Mapped["Product"] = relationship(back_populates="sale_details")  # type: ignore[name-defined]

    def __repr__(self) -> str:
        return f"<SaleDetail sale={self.sale_id} product={self.product_id} qty={self.quantity}>"
