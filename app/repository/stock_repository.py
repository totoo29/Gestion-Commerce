# app/repository/stock_repository.py
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.stock import Stock, StockMovement
from app.repository.base_repository import BaseRepository


class StockRepository(BaseRepository[Stock]):

    def __init__(self, session: Session):
        super().__init__(session, Stock)

    def get_by_product_id(self, product_id: int) -> Stock | None:
        stmt = select(Stock).where(Stock.product_id == product_id)
        return self.session.scalars(stmt).first()

    def get_with_lock(self, product_id: int) -> Stock | None:
        """
        Obtiene el stock con bloqueo de escritura (SELECT FOR UPDATE).
        En SQLite el bloqueo es a nivel de base de datos (WAL mode),
        por lo que esta query garantiza consistencia en la transaccion actual.
        Usar siempre dentro de una transaccion antes de modificar el stock.
        """
        stmt = (
            select(Stock)
            .where(Stock.product_id == product_id)
            .with_for_update()
        )
        return self.session.scalars(stmt).first()

    def get_critical_stock_items(self) -> list[Stock]:
        """
        Retorna todos los registros de stock donde la cantidad
        es menor o igual al minimo configurado.
        """
        from sqlalchemy.orm import joinedload
        stmt = (
            select(Stock)
            .options(joinedload(Stock.product))
            .where(Stock.quantity <= Stock.min_quantity)
        )
        return list(self.session.scalars(stmt).all())

    def create_movement(
        self,
        stock_id: int,
        movement_type: str,
        quantity: Decimal,
        stock_before: Decimal,
        stock_after: Decimal,
        created_by: int | None = None,
        reference_id: int | None = None,
        reference_type: str | None = None,
        notes: str | None = None,
    ) -> StockMovement:
        """
        Registra un movimiento de stock.
        Nunca modifica el stock directamente: eso lo hace el service.
        """
        movement = StockMovement(
            stock_id=stock_id,
            movement_type=movement_type,
            quantity=quantity,
            stock_before=stock_before,
            stock_after=stock_after,
            created_by=created_by,
            reference_id=reference_id,
            reference_type=reference_type,
            notes=notes,
        )
        self.session.add(movement)
        self.session.flush()
        return movement

    def get_movements_by_product(
        self,
        product_id: int,
        limit: int = 50,
    ) -> list[StockMovement]:
        """Historial de movimientos de un producto, del mas reciente al mas antiguo."""
        stmt = (
            select(StockMovement)
            .join(StockMovement.stock)
            .where(Stock.product_id == product_id)
            .order_by(StockMovement.id.desc())
            .limit(limit)
        )
        return list(self.session.scalars(stmt).all())
