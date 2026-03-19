# app/repository/customer_repository.py
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.models.customer import Customer
from app.repository.base_repository import BaseRepository


class CustomerRepository(BaseRepository[Customer]):

    def __init__(self, session: Session):
        super().__init__(session, Customer)

    def get_active(self) -> list[Customer]:
        stmt = select(Customer).where(Customer.is_active == True).order_by(Customer.full_name)  # noqa: E712
        return list(self.session.scalars(stmt).all())

    def search(self, query: str, limit: int = 20) -> list[Customer]:
        """Busqueda por nombre, CUIT/DNI o email."""
        like = f"%{query}%"
        stmt = (
            select(Customer)
            .where(
                Customer.is_active == True,  # noqa: E712
                or_(
                    Customer.full_name.ilike(like),
                    Customer.tax_id.ilike(like),
                    Customer.email.ilike(like),
                    Customer.phone.ilike(like),
                ),
            )
            .limit(limit)
        )
        return list(self.session.scalars(stmt).all())

    def get_by_tax_id(self, tax_id: str) -> Customer | None:
        stmt = select(Customer).where(Customer.tax_id == tax_id)
        return self.session.scalars(stmt).first()
