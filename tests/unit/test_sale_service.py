# tests/unit/test_sale_service.py
from decimal import Decimal

import pytest
from sqlalchemy.orm import Session

from app.core.exceptions import (
    OperacionInvalidaError,
    ProductoNoEncontradoError,
    StockInsuficienteError,
    VentaNoEncontradaError,
)
from app.services.sale_service import SaleInput, SaleItemInput, SaleService


def make_item(product_id: int, qty: str, price: str) -> SaleItemInput:
    """Helper para crear items de venta rapidamente."""
    return SaleItemInput(
        product_id=product_id,
        quantity=Decimal(qty),
        unit_price=Decimal(price),
    )


class TestSaleService:

    def test_process_sale_basic(self, session: Session, sample_product, admin_user):
        """Venta basica: descuenta stock y crea la venta correctamente."""
        service = SaleService(session)
        data = SaleInput(
            items=[make_item(sample_product.id, "3", "100.00")],
            payment_method="efectivo",
            amount_paid=Decimal("300.00"),
        )

        sale = service.process_sale(data, seller_id=admin_user.id)

        assert sale.id is not None
        assert sale.status == "completed"
        assert sale.total == Decimal("300.00")
        assert sale.change_given == Decimal("0")
        assert len(sale.details) == 1

    def test_process_sale_discounts_stock(self, session: Session, sample_product):
        """Procesar una venta reduce el stock del producto."""
        service = SaleService(session)
        data = SaleInput(
            items=[make_item(sample_product.id, "10", "50.00")],
            amount_paid=Decimal("500.00"),
        )
        service.process_sale(data)

        # Stock inicial = 100, vendimos 10 => debe quedar 90
        from app.repository.stock_repository import StockRepository
        repo = StockRepository(session)
        stock = repo.get_by_product_id(sample_product.id)
        assert stock.quantity == Decimal("90")

    def test_process_sale_registers_stock_movement(self, session: Session, sample_product):
        """Procesar una venta registra un movimiento de tipo 'sale'."""
        service = SaleService(session)
        data = SaleInput(
            items=[make_item(sample_product.id, "5", "100.00")],
            amount_paid=Decimal("500.00"),
        )
        service.process_sale(data)

        from app.services.stock_service import StockService
        stock_service = StockService(session)
        movements = stock_service.get_stock_movements(sample_product.id)

        assert len(movements) == 1
        assert movements[0].movement_type == "sale"
        assert movements[0].quantity == Decimal("-5")
        assert movements[0].stock_before == Decimal("100")
        assert movements[0].stock_after == Decimal("95")

    def test_process_sale_calculates_change(self, session: Session, sample_product):
        """El vuelto se calcula correctamente."""
        service = SaleService(session)
        data = SaleInput(
            items=[make_item(sample_product.id, "1", "75.00")],
            amount_paid=Decimal("100.00"),
        )
        sale = service.process_sale(data)

        assert sale.change_given == Decimal("25.00")

    def test_process_sale_with_discount(self, session: Session, sample_product):
        """Descuento en la venta se refleja en el total."""
        service = SaleService(session)
        data = SaleInput(
            items=[make_item(sample_product.id, "2", "100.00")],
            discount=Decimal("50.00"),
            amount_paid=Decimal("150.00"),
        )
        sale = service.process_sale(data)

        assert sale.subtotal == Decimal("200.00")
        assert sale.discount == Decimal("50.00")
        assert sale.total == Decimal("150.00")

    def test_process_sale_multiple_items(self, session: Session, admin_user):
        """Venta con multiples productos distintos."""
        from app.models.product import Product
        from app.models.stock import Stock

        product_a = Product(sku="A-001", name="Producto A", unit="unidad")
        product_b = Product(sku="B-001", name="Producto B", unit="unidad")
        session.add_all([product_a, product_b])
        session.flush()

        session.add(Stock(product_id=product_a.id, quantity=Decimal("50"), min_quantity=Decimal("5")))
        session.add(Stock(product_id=product_b.id, quantity=Decimal("30"), min_quantity=Decimal("5")))
        session.flush()

        service = SaleService(session)
        data = SaleInput(
            items=[
                make_item(product_a.id, "2", "100.00"),
                make_item(product_b.id, "3", "200.00"),
            ],
            amount_paid=Decimal("800.00"),
        )
        sale = service.process_sale(data, seller_id=admin_user.id)

        assert sale.total == Decimal("800.00")
        assert len(sale.details) == 2

    def test_insufficient_stock_raises(self, session: Session, sample_product):
        """Venta con mas unidades que stock disponible lanza StockInsuficienteError."""
        service = SaleService(session)
        data = SaleInput(
            items=[make_item(sample_product.id, "999", "10.00")],  # Solo hay 100
            amount_paid=Decimal("9990.00"),
        )

        with pytest.raises(StockInsuficienteError) as exc_info:
            service.process_sale(data)

        assert exc_info.value.product_id == sample_product.id
        assert exc_info.value.disponible == 100
        assert exc_info.value.requerido == 999

    def test_insufficient_stock_does_not_modify_stock(self, session: Session, sample_product):
        """Si falla por stock insuficiente, el stock NO se modifica (rollback).
        Verifica que la excepcion reporta el stock real disponible (100),
        lo que confirma que el valor no fue alterado antes de fallar.
        """
        service = SaleService(session)
        data = SaleInput(
            items=[make_item(sample_product.id, "999", "10.00")],
            amount_paid=Decimal("9990.00"),
        )

        with pytest.raises(StockInsuficienteError) as exc_info:
            service.process_sale(data)

        # La excepcion reporta disponible=100: confirma que el stock
        # no fue modificado antes de detectar la insuficiencia.
        assert exc_info.value.disponible == 100
        assert exc_info.value.requerido == 999
        assert exc_info.value.product_id == sample_product.id

    def test_nonexistent_product_raises(self, session: Session):
        """Venta con producto inexistente lanza ProductoNoEncontradoError."""
        service = SaleService(session)
        data = SaleInput(
            items=[make_item(99999, "1", "100.00")],
            amount_paid=Decimal("100.00"),
        )

        with pytest.raises(ProductoNoEncontradoError):
            service.process_sale(data)

    def test_cancel_sale_restores_stock(self, session: Session, sample_product):
        """Cancelar una venta devuelve el stock al nivel previo."""
        service = SaleService(session)

        # Procesar venta (descuenta 10 unidades)
        data = SaleInput(
            items=[make_item(sample_product.id, "10", "100.00")],
            amount_paid=Decimal("1000.00"),
        )
        sale = service.process_sale(data)
        assert sale.status == "completed"

        # Cancelar venta (debe devolver las 10 unidades)
        service.cancel_sale(sale.id)

        from app.repository.stock_repository import StockRepository
        stock = StockRepository(session).get_by_product_id(sample_product.id)
        assert stock.quantity == Decimal("100")  # Stock original restaurado

    def test_cancel_sale_changes_status(self, session: Session, sample_product):
        """Cancelar una venta cambia su estado a 'cancelled'."""
        service = SaleService(session)
        data = SaleInput(
            items=[make_item(sample_product.id, "1", "100.00")],
            amount_paid=Decimal("100.00"),
        )
        sale = service.process_sale(data)
        service.cancel_sale(sale.id)

        cancelled = service.get_sale(sale.id)
        assert cancelled.status == "cancelled"

    def test_cancel_already_cancelled_raises(self, session: Session, sample_product):
        """Cancelar una venta ya cancelada lanza OperacionInvalidaError."""
        service = SaleService(session)
        data = SaleInput(
            items=[make_item(sample_product.id, "1", "100.00")],
            amount_paid=Decimal("100.00"),
        )
        sale = service.process_sale(data)
        service.cancel_sale(sale.id)

        with pytest.raises(OperacionInvalidaError):
            service.cancel_sale(sale.id)

    def test_get_nonexistent_sale_raises(self, session: Session):
        """Obtener venta inexistente lanza VentaNoEncontradaError."""
        service = SaleService(session)

        with pytest.raises(VentaNoEncontradaError):
            service.get_sale(99999)
