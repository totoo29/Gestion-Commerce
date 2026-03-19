# app/repository/purchase_repository.py
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.models.purchase import Purchase, PurchaseDetail
from app.repository.base_repository import BaseRepository


class PurchaseRepository(BaseRepository[Purchase]):

    def __init__(self, session: Session):
        super().__init__(session, Purchase)

    def get_with_details(self, purchase_id: int) -> Purchase | None:
        """Carga la compra con todos sus items y relaciones."""
        stmt = (
            select(Purchase)
            .where(Purchase.id == purchase_id)
            .options(
                joinedload(Purchase.details).joinedload(PurchaseDetail.product),
                joinedload(Purchase.supplier),
            )
        )
        return self.session.scalars(stmt).first()

    def get_pending(self) -> list[Purchase]:
        """Ordenes de compra pendientes de recepcion."""
        stmt = (
            select(Purchase)
            .where(Purchase.status == "pending")
            .order_by(Purchase.created_at.desc())
            .options(joinedload(Purchase.supplier))
        )
        return list(self.session.scalars(stmt).all())

    def get_recent(self, limit: int = 50) -> list[Purchase]:
        """Compras recientes ordenadas por fecha descendente."""
        stmt = (
            select(Purchase)
            .order_by(Purchase.created_at.desc())
            .limit(limit)
            .options(joinedload(Purchase.supplier))
        )
        return list(self.session.scalars(stmt).all())
