# tests/unit/test_purchase_service.py
from decimal import Decimal

import pytest
from sqlalchemy.orm import Session

from app.core.exceptions import OperacionInvalidaError
from app.services.purchase_service import PurchaseInput, PurchaseItemInput, PurchaseService


def make_item(product_id: int, qty: str, cost: str) -> PurchaseItemInput:
    return PurchaseItemInput(
        product_id=product_id,
        quantity=Decimal(qty),
        unit_cost=Decimal(cost),
    )


class TestPurchaseService:

    def test_create_purchase_pending(self, session: Session, sample_product):
        """Una orden de compra nueva queda en estado 'pending'."""
        service = PurchaseService(session)
        data = PurchaseInput(items=[make_item(sample_product.id, "50", "30.00")])
        purchase = service.create_purchase(data)

        assert purchase.id is not None
        assert purchase.status == "pending"
        assert purchase.total == Decimal("1500.00")

    def test_create_purchase_does_not_modify_stock(self, session: Session, sample_product):
        """Crear una orden de compra NO modifica el stock aun."""
        service = PurchaseService(session)
        data = PurchaseInput(items=[make_item(sample_product.id, "50", "30.00")])
        service.create_purchase(data)

        from app.repository.stock_repository import StockRepository
        stock = StockRepository(session).get_by_product_id(sample_product.id)
        assert stock.quantity == Decimal("100")  # Sin cambios

    def test_receive_purchase_increments_stock(self, session: Session, sample_product):
        """Recibir una compra incrementa el stock de cada producto."""
        service = PurchaseService(session)
        data = PurchaseInput(items=[make_item(sample_product.id, "50", "30.00")])
        purchase = service.create_purchase(data)

        service.receive_purchase(purchase.id)

        from app.repository.stock_repository import StockRepository
        stock = StockRepository(session).get_by_product_id(sample_product.id)
        assert stock.quantity == Decimal("150")  # 100 iniciales + 50 recibidos

    def test_receive_purchase_changes_status(self, session: Session, sample_product):
        """Recibir una compra cambia su estado a 'received'."""
        service = PurchaseService(session)
        data = PurchaseInput(items=[make_item(sample_product.id, "10", "20.00")])
        purchase = service.create_purchase(data)

        service.receive_purchase(purchase.id)
        assert purchase.status == "received"

    def test_receive_purchase_registers_movement(self, session: Session, sample_product):
        """Recibir una compra registra movimiento de tipo 'purchase'."""
        service = PurchaseService(session)
        data = PurchaseInput(items=[make_item(sample_product.id, "25", "20.00")])
        purchase = service.create_purchase(data)
        service.receive_purchase(purchase.id)

        from app.services.stock_service import StockService
        movements = StockService(session).get_stock_movements(sample_product.id)
        assert any(m.movement_type == "purchase" for m in movements)

    def test_receive_already_received_raises(self, session: Session, sample_product):
        """Intentar recibir una compra ya recibida lanza OperacionInvalidaError."""
        service = PurchaseService(session)
        data = PurchaseInput(items=[make_item(sample_product.id, "5", "10.00")])
        purchase = service.create_purchase(data)
        service.receive_purchase(purchase.id)

        with pytest.raises(OperacionInvalidaError):
            service.receive_purchase(purchase.id)

    def test_cancel_pending_purchase(self, session: Session, sample_product):
        """Cancelar una orden pendiente la marca como 'cancelled'."""
        service = PurchaseService(session)
        data = PurchaseInput(items=[make_item(sample_product.id, "10", "50.00")])
        purchase = service.create_purchase(data)

        service.cancel_purchase(purchase.id)
        assert purchase.status == "cancelled"

    def test_cancel_received_purchase_raises(self, session: Session, sample_product):
        """No se puede cancelar una compra ya recibida."""
        service = PurchaseService(session)
        data = PurchaseInput(items=[make_item(sample_product.id, "5", "10.00")])
        purchase = service.create_purchase(data)
        service.receive_purchase(purchase.id)

        with pytest.raises(OperacionInvalidaError):
            service.cancel_purchase(purchase.id)
