# app/services/purchase_service.py
from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy.orm import Session

from app.core.constants import MovementType
from app.core.exceptions import OperacionInvalidaError, ProductoNoEncontradoError
from app.core.logging import get_logger
from app.models.purchase import Purchase, PurchaseDetail
from app.repository.product_repository import ProductRepository
from app.repository.purchase_repository import PurchaseRepository
from app.repository.stock_repository import StockRepository

logger = get_logger(__name__)


@dataclass
class PurchaseItemInput:
    product_id: int
    quantity: Decimal
    unit_cost: Decimal


@dataclass
class PurchaseInput:
    items: list[PurchaseItemInput]
    supplier_id: int | None = None
    supplier_reference: str | None = None
    notes: str | None = None


class PurchaseService:

    def __init__(self, session: Session):
        self.session = session
        self.purchase_repo = PurchaseRepository(session)
        self.stock_repo = StockRepository(session)
        self.product_repo = ProductRepository(session)

    def create_purchase(
        self,
        data: PurchaseInput,
        user_id: int | None = None,
    ) -> Purchase:
        """
        Crea una orden de compra en estado 'pending'.
        El stock NO se modifica aun: se actualiza al recibir la mercaderia.
        """
        try:
            subtotal = Decimal("0")
            details = []

            for item in data.items:
                product = self.product_repo.get_by_id(item.product_id)
                if product is None:
                    raise ProductoNoEncontradoError(item.product_id)

                item_subtotal = item.unit_cost * item.quantity
                subtotal += item_subtotal

                details.append(PurchaseDetail(
                    product_id=item.product_id,
                    quantity=item.quantity,
                    unit_cost=item.unit_cost,
                    subtotal=item_subtotal,
                ))

            purchase = Purchase(
                supplier_id=data.supplier_id,
                supplier_reference=data.supplier_reference,
                created_by=user_id,
                subtotal=subtotal,
                tax=Decimal("0"),
                total=subtotal,
                status="pending",
                notes=data.notes,
            )
            self.session.add(purchase)
            self.session.flush()

            for detail in details:
                detail.purchase_id = purchase.id
                self.session.add(detail)

            self.session.commit()
            logger.info(f"Orden de compra creada: id={purchase.id}, total={subtotal}")
            return purchase

        except Exception:
            self.session.rollback()
            raise

    def receive_purchase(
        self,
        purchase_id: int,
        user_id: int | None = None,
    ) -> Purchase:
        """
        Recibe la mercaderia de una orden de compra:
          1. Verifica que la orden este en estado 'pending'
          2. Incrementa el stock de cada producto
          3. Registra los movimientos de stock
          4. Marca la orden como 'received'
        Todo en una sola transaccion atomica.
        """
        purchase = self.purchase_repo.get_with_details(purchase_id)
        if purchase is None:
            raise OperacionInvalidaError(f"Orden de compra {purchase_id} no encontrada.")

        if purchase.status != "pending":
            raise OperacionInvalidaError(
                f"La orden {purchase_id} ya fue procesada (estado: '{purchase.status}')."
            )

        try:
            for detail in purchase.details:
                stock = self.stock_repo.get_with_lock(detail.product_id)
                if stock is None:
                    raise ProductoNoEncontradoError(detail.product_id)

                stock_before = stock.quantity
                stock.quantity += detail.quantity

                self.stock_repo.create_movement(
                    stock_id=stock.id,
                    movement_type=MovementType.PURCHASE,
                    quantity=detail.quantity,
                    stock_before=stock_before,
                    stock_after=stock.quantity,
                    created_by=user_id,
                    reference_id=purchase_id,
                    reference_type="purchase",
                )

            purchase.status = "received"
            self.session.commit()

            logger.info(f"Compra recibida: id={purchase_id}, items={len(purchase.details)}")
            return purchase

        except Exception:
            self.session.rollback()
            raise

    def cancel_purchase(self, purchase_id: int) -> Purchase:
        """Cancela una orden de compra que todavia no fue recibida."""
        purchase = self.purchase_repo.get_by_id(purchase_id)
        if purchase is None:
            raise OperacionInvalidaError(f"Orden de compra {purchase_id} no encontrada.")

        if purchase.status != "pending":
            raise OperacionInvalidaError(
                f"No se puede cancelar una orden en estado '{purchase.status}'."
            )

        purchase.status = "cancelled"
        self.session.commit()
        logger.info(f"Orden de compra cancelada: id={purchase_id}")
        return purchase

    def get_pending_purchases(self) -> list[Purchase]:
        return self.purchase_repo.get_pending()

    def get_recent_purchases(self, limit: int = 50) -> list[Purchase]:
        return self.purchase_repo.get_recent(limit=limit)
