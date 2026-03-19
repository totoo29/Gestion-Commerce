# app/services/stock_service.py
from decimal import Decimal

from sqlalchemy.orm import Session

from app.core.constants import MovementType
from app.core.exceptions import ProductoNoEncontradoError
from app.core.logging import get_logger
from app.models.stock import Stock, StockMovement
from app.repository.product_repository import ProductRepository
from app.repository.stock_repository import StockRepository

logger = get_logger(__name__)


class StockService:

    def __init__(self, session: Session):
        self.session = session
        self.stock_repo = StockRepository(session)
        self.product_repo = ProductRepository(session)

    def adjust_stock(
        self,
        product_id: int,
        new_quantity: Decimal,
        notes: str | None = None,
        user_id: int | None = None,
    ) -> Stock:
        """
        Ajuste manual de stock (inventario fisico).
        Registra el movimiento con tipo 'adjustment'.
        """
        stock = self.stock_repo.get_with_lock(product_id)
        if stock is None:
            raise ProductoNoEncontradoError(product_id)

        stock_before = stock.quantity
        stock.quantity = new_quantity

        self.stock_repo.create_movement(
            stock_id=stock.id,
            movement_type=MovementType.ADJUSTMENT,
            quantity=new_quantity - stock_before,
            stock_before=stock_before,
            stock_after=new_quantity,
            created_by=user_id,
            notes=notes or "Ajuste manual de inventario",
        )

        self.session.commit()
        logger.info(
            f"Ajuste de stock: producto={product_id}, "
            f"antes={stock_before}, despues={new_quantity}"
        )
        return stock

    def update_min_stock(
        self,
        product_id: int,
        min_quantity: Decimal,
    ) -> Stock:
        """Actualiza el umbral de stock minimo para alertas."""
        stock = self.stock_repo.get_by_product_id(product_id)
        if stock is None:
            raise ProductoNoEncontradoError(product_id)

        stock.min_quantity = min_quantity
        self.session.commit()
        logger.info(f"Stock minimo actualizado: producto={product_id}, minimo={min_quantity}")
        return stock

    def get_critical_items(self) -> list[Stock]:
        """
        Retorna todos los productos con stock en o por debajo del minimo.
        Usado por el dashboard y el badge de alertas en la UI.
        """
        return self.stock_repo.get_critical_stock_items()

    def get_stock_movements(
        self,
        product_id: int,
        limit: int = 50,
    ) -> list[StockMovement]:
        """Historial de movimientos de un producto."""
        return self.stock_repo.get_movements_by_product(product_id, limit=limit)

    def get_stock(self, product_id: int) -> Stock | None:
        return self.stock_repo.get_by_product_id(product_id)
