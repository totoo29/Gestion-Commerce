# app/repository/invoice_repository.py
from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.models.invoice import Invoice
from app.repository.base_repository import BaseRepository


class InvoiceRepository(BaseRepository[Invoice]):

    def __init__(self, session: Session):
        super().__init__(session, Invoice)

    def get_by_sale_id(self, sale_id: int) -> Invoice | None:
        stmt = select(Invoice).where(Invoice.sale_id == sale_id)
        return self.session.scalars(stmt).first()

    def get_by_number(self, number: str) -> Invoice | None:
        stmt = select(Invoice).where(Invoice.number == number)
        return self.session.scalars(stmt).first()

    def get_next_number(self, invoice_type: str) -> str:
        """
        Genera el siguiente numero de comprobante correlativo por tipo.
        Formato: TIPO-00000001 (ej: TICKET-00000001, FACTURA_B-00000042)
        """
        stmt = select(func.count()).select_from(Invoice).where(
            Invoice.invoice_type == invoice_type
        )
        count = self.session.scalar(stmt) or 0
        return f"{invoice_type.upper()}-{(count + 1):08d}"

    def get_recent(self, limit: int = 50) -> list[Invoice]:
        stmt = (
            select(Invoice)
            .order_by(Invoice.created_at.desc())
            .limit(limit)
            .options(joinedload(Invoice.customer), joinedload(Invoice.sale))
        )
        return list(self.session.scalars(stmt).all())
