# app/models/purchase.py
from decimal import Decimal

from sqlalchemy import ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class Purchase(Base, TimestampMixin):
    """
    Orden de compra a un proveedor.
    Al recibir la mercaderia, el stock se incrementa automaticamente.
    """
    __tablename__ = "purchases"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    supplier_id: Mapped[int | None] = mapped_column(
        ForeignKey("suppliers.id", ondelete="SET NULL"), nullable=True
    )
    created_by: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    # Referencia del proveedor (numero de remito, factura de compra, etc.)
    supplier_reference: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Totales
    subtotal: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    tax: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0, nullable=False)
    total: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)

    # Estado: pending | received | cancelled
    status: Mapped[str] = mapped_column(String(20), default="pending", nullable=False, index=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relaciones
    supplier: Mapped["Supplier | None"] = relationship(back_populates="purchases")  # type: ignore[name-defined]
    details: Mapped[list["PurchaseDetail"]] = relationship(
        back_populates="purchase", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Purchase id={self.id} status={self.status} total={self.total}>"


class PurchaseDetail(Base):
    """Linea de detalle de una orden de compra."""
    __tablename__ = "purchase_details"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    purchase_id: Mapped[int] = mapped_column(
        ForeignKey("purchases.id", ondelete="CASCADE"), nullable=False
    )
    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id", ondelete="RESTRICT"), nullable=False
    )
    quantity: Mapped[Decimal] = mapped_column(Numeric(12, 3), nullable=False)
    unit_cost: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)  # Costo de compra
    subtotal: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)

    # Relaciones
    purchase: Mapped[Purchase] = relationship(back_populates="details")
    product: Mapped["Product"] = relationship(back_populates="purchase_details")  # type: ignore[name-defined]

    def __repr__(self) -> str:
        return f"<PurchaseDetail purchase={self.purchase_id} product={self.product_id} qty={self.quantity}>"
