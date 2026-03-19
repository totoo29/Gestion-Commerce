# app/models/stock.py
from decimal import Decimal

from sqlalchemy import ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class Stock(Base, TimestampMixin):
    """
    Stock actual de un producto.
    Relacion 1-a-1 con Product: cada producto tiene exactamente un registro de stock.
    """
    __tablename__ = "stock"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    quantity: Mapped[Decimal] = mapped_column(Numeric(12, 3), default=0, nullable=False)
    min_quantity: Mapped[Decimal] = mapped_column(Numeric(12, 3), default=5, nullable=False)

    # Relaciones
    product: Mapped["Product"] = relationship(back_populates="stock")  # type: ignore[name-defined]
    movements: Mapped[list["StockMovement"]] = relationship(
        back_populates="stock", cascade="all, delete-orphan"
    )

    @property
    def is_critical(self) -> bool:
        """True si el stock actual esta en o por debajo del minimo."""
        return self.quantity <= self.min_quantity

    def __repr__(self) -> str:
        return f"<Stock product={self.product_id} qty={self.quantity}>"


class StockMovement(Base, TimestampMixin):
    """
    Registro inmutable de cada movimiento de stock.
    Sirve como historial y para auditoría.
    Nunca se edita ni elimina: solo se insertan nuevos registros.
    """
    __tablename__ = "stock_movements"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    stock_id: Mapped[int] = mapped_column(
        ForeignKey("stock.id", ondelete="CASCADE"), nullable=False
    )
    # Tipo: sale | purchase | adjustment | return (ver constants.py)
    movement_type: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    # Cantidad del movimiento: negativa para salidas, positiva para entradas
    quantity: Mapped[Decimal] = mapped_column(Numeric(12, 3), nullable=False)
    # Snapshot del stock antes y despues del movimiento
    stock_before: Mapped[Decimal] = mapped_column(Numeric(12, 3), nullable=False)
    stock_after: Mapped[Decimal] = mapped_column(Numeric(12, 3), nullable=False)
    # Referencia opcional al documento que origino el movimiento
    reference_id: Mapped[int | None] = mapped_column(nullable=True)
    reference_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    stock: Mapped[Stock] = relationship(back_populates="movements")

    def __repr__(self) -> str:
        return f"<StockMovement type={self.movement_type} qty={self.quantity}>"
