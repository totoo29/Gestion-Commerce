# tests/unit/test_stock_service.py
from decimal import Decimal

import pytest
from sqlalchemy.orm import Session

from app.core.exceptions import ProductoNoEncontradoError
from app.services.stock_service import StockService


class TestStockService:

    def test_adjust_stock_up(self, session: Session, sample_product, admin_user):
        """Ajuste de stock a un valor mayor registra movimiento correctamente."""
        service = StockService(session)
        stock = service.adjust_stock(
            product_id=sample_product.id,
            new_quantity=Decimal("200"),
            notes="Conteo fisico",
            user_id=admin_user.id,
        )

        assert stock.quantity == Decimal("200")

    def test_adjust_stock_down(self, session: Session, sample_product):
        """Ajuste de stock a un valor menor."""
        service = StockService(session)
        stock = service.adjust_stock(
            product_id=sample_product.id,
            new_quantity=Decimal("50"),
        )

        assert stock.quantity == Decimal("50")

    def test_adjust_stock_registers_movement(self, session: Session, sample_product):
        """El ajuste de stock registra un movimiento de tipo 'adjustment'."""
        service = StockService(session)
        service.adjust_stock(sample_product.id, Decimal("75"))

        movements = service.get_stock_movements(sample_product.id)
        assert len(movements) == 1
        assert movements[0].movement_type == "adjustment"
        assert movements[0].stock_before == Decimal("100")
        assert movements[0].stock_after == Decimal("75")

    def test_adjust_nonexistent_product_raises(self, session: Session):
        """Ajustar stock de producto inexistente lanza ProductoNoEncontradoError."""
        service = StockService(session)

        with pytest.raises(ProductoNoEncontradoError):
            service.adjust_stock(99999, Decimal("10"))

    def test_update_min_stock(self, session: Session, sample_product):
        """Actualizar el stock minimo de alerta."""
        service = StockService(session)
        stock = service.update_min_stock(sample_product.id, Decimal("20"))

        assert stock.min_quantity == Decimal("20")

    def test_get_critical_items_returns_low_stock(
        self, session: Session, sample_product, low_stock_product
    ):
        """get_critical_items retorna solo productos con stock critico."""
        service = StockService(session)
        critical = service.get_critical_items()

        critical_ids = [s.product_id for s in critical]
        assert low_stock_product.id in critical_ids
        assert sample_product.id not in critical_ids

    def test_get_critical_items_empty_when_all_ok(self, session: Session, sample_product):
        """get_critical_items retorna lista vacia si todos los stocks estan bien."""
        service = StockService(session)
        # sample_product tiene 100 unidades con minimo 5 => no es critico
        critical = service.get_critical_items()

        critical_ids = [s.product_id for s in critical]
        assert sample_product.id not in critical_ids

    def test_stock_becomes_critical_after_adjustment(self, session: Session, sample_product):
        """Un producto pasa a critico si se ajusta su stock por debajo del minimo."""
        service = StockService(session)
        service.adjust_stock(sample_product.id, Decimal("3"))  # Minimo es 5

        critical = service.get_critical_items()
        assert any(s.product_id == sample_product.id for s in critical)

    def test_get_stock_movements_order(self, session: Session, sample_product):
        """Los movimientos se retornan del mas reciente al mas antiguo."""
        service = StockService(session)
        service.adjust_stock(sample_product.id, Decimal("80"))
        service.adjust_stock(sample_product.id, Decimal("60"))
        service.adjust_stock(sample_product.id, Decimal("40"))

        movements = service.get_stock_movements(sample_product.id)
        assert len(movements) == 3
        # El mas reciente tiene stock_after=40
        assert movements[0].stock_after == Decimal("40")
