# app/models/invoice.py
from decimal import Decimal

from sqlalchemy import ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class Invoice(Base, TimestampMixin):
    """
    Comprobante fiscal asociado a una venta.
    Actualmente soporta tickets y facturas locales.
    Preparado para integracion con AFIP (WSFE) en el futuro:
    los campos cae, cae_expiry y afip_number se populan cuando
    se obtenga autorizacion electronica.
    """
    __tablename__ = "invoices"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    sale_id: Mapped[int] = mapped_column(
        ForeignKey("sales.id", ondelete="RESTRICT"),
        unique=True,
        nullable=False,
    )
    customer_id: Mapped[int | None] = mapped_column(
        ForeignKey("customers.id", ondelete="SET NULL"), nullable=True
    )

    # Tipo de comprobante: ticket | factura_a | factura_b
    invoice_type: Mapped[str] = mapped_column(String(20), nullable=False)

    # Numeracion local (hasta integrar AFIP)
    number: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)

    # Totales (se copian de la venta en el momento de facturar)
    subtotal: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    tax: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0, nullable=False)
    total: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)

    # ── Campos AFIP (futuros) ──────────────────────────────────────────────────
    # Se dejan nullable para no bloquear el uso sin AFIP
    cae: Mapped[str | None] = mapped_column(String(20), nullable=True)
    cae_expiry: Mapped[str | None] = mapped_column(String(10), nullable=True)  # Formato YYYYMMDD
    afip_number: Mapped[int | None] = mapped_column(nullable=True)

    # Ruta al PDF generado (relativa a REPORTS_DIR)
    pdf_path: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Relaciones
    sale: Mapped["Sale"] = relationship(back_populates="invoice")  # type: ignore[name-defined]
    customer: Mapped["Customer | None"] = relationship(back_populates="invoices")  # type: ignore[name-defined]

    def __repr__(self) -> str:
        return f"<Invoice {self.number} type={self.invoice_type} total={self.total}>"
