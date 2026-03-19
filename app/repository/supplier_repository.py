# app/repository/supplier_repository.py
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.models.supplier import Supplier
from app.repository.base_repository import BaseRepository


class SupplierRepository(BaseRepository[Supplier]):

    def __init__(self, session: Session):
        super().__init__(session, Supplier)

    def get_active(self) -> list[Supplier]:
        stmt = select(Supplier).where(Supplier.is_active == True).order_by(Supplier.name)  # noqa: E712
        return list(self.session.scalars(stmt).all())

    def search(self, query: str, limit: int = 20) -> list[Supplier]:
        """Busqueda por nombre, CUIT o nombre de contacto."""
        like = f"%{query}%"
        stmt = (
            select(Supplier)
            .where(
                Supplier.is_active == True,  # noqa: E712
                or_(
                    Supplier.name.ilike(like),
                    Supplier.tax_id.ilike(like),
                    Supplier.contact_name.ilike(like),
                ),
            )
            .limit(limit)
        )
        return list(self.session.scalars(stmt).all())

    def get_by_tax_id(self, tax_id: str) -> Supplier | None:
        stmt = select(Supplier).where(Supplier.tax_id == tax_id)
        return self.session.scalars(stmt).first()
