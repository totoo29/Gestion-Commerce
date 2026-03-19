# app/repository/sale_repository.py
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session, joinedload

from app.models.sale import Sale, SaleDetail
from app.repository.base_repository import BaseRepository


class SaleRepository(BaseRepository[Sale]):

    def __init__(self, session: Session):
        super().__init__(session, Sale)

    def get_with_details(self, sale_id: int) -> Sale | None:
        """Carga la venta con todos sus items y relaciones."""
        stmt = (
            select(Sale)
            .where(Sale.id == sale_id)
            .options(
                joinedload(Sale.details).joinedload(SaleDetail.product),
                joinedload(Sale.seller),
                joinedload(Sale.customer),
                joinedload(Sale.invoice),
            )
        )
        return self.session.scalars(stmt).first()

    def get_by_date_range(
        self,
        date_from: date,
        date_to: date,
        limit: int = 200,
        offset: int = 0,
    ) -> list[Sale]:
        """Ventas en un rango de fechas, del mas reciente al mas antiguo."""
        stmt = (
            select(Sale)
            .where(
                and_(
                    func.date(Sale.created_at) >= date_from,
                    func.date(Sale.created_at) <= date_to,
                    Sale.status == "completed",
                )
            )
            .order_by(Sale.created_at.desc())
            .limit(limit)
            .offset(offset)
            .options(joinedload(Sale.seller), joinedload(Sale.customer))
        )
        return list(self.session.scalars(stmt).all())

    def get_today_sales(self) -> list[Sale]:
        """Ventas completadas del dia de hoy."""
        today = date.today()
        return self.get_by_date_range(today, today, limit=500)

    def get_daily_total(self, for_date: date) -> Decimal:
        """Total facturado en un dia especifico."""
        stmt = select(func.coalesce(func.sum(Sale.total), 0)).where(
            and_(
                func.date(Sale.created_at) == for_date,
                Sale.status == "completed",
            )
        )
        return self.session.scalar(stmt) or Decimal("0")

    def get_today_total(self) -> Decimal:
        return self.get_daily_total(date.today())

    def count_today(self) -> int:
        """Cantidad de ventas completadas hoy."""
        stmt = select(func.count()).select_from(Sale).where(
            and_(
                func.date(Sale.created_at) == date.today(),
                Sale.status == "completed",
            )
        )
        return self.session.scalar(stmt) or 0
