# tests/unit/test_product_service.py
from decimal import Decimal

import pytest
from sqlalchemy.orm import Session

from app.core.exceptions import ProductoNoEncontradoError
from app.services.product_service import ProductService


class TestProductService:

    def test_create_product_minimal(self, session: Session, default_price_list):
        """Crear producto con datos minimos genera stock automaticamente."""
        service = ProductService(session)
        product = service.create_product(sku="P-001", name="Martillo")

        assert product.id is not None
        assert product.sku == "P-001"
        assert product.name == "Martillo"
        assert product.is_active is True
        assert product.stock is not None
        assert product.stock.quantity == Decimal("0")

    def test_create_product_with_initial_stock(self, session: Session):
        """Crear producto con stock inicial mayor a cero."""
        service = ProductService(session)
        product = service.create_product(
            sku="P-002",
            name="Tornillo",
            initial_stock=Decimal("500"),
            min_stock=Decimal("50"),
        )

        assert product.stock.quantity == Decimal("500")
        assert product.stock.min_quantity == Decimal("50")

    def test_create_product_with_barcode(self, session: Session):
        """Crear producto con codigo de barras lo asocia correctamente."""
        service = ProductService(session)
        product = service.create_product(
            sku="P-003",
            name="Destornillador",
            barcodes=["7791234567890"],
        )

        assert len(product.barcodes) == 1
        assert product.barcodes[0].code == "7791234567890"

    def test_create_product_with_price(self, session: Session, default_price_list):
        """Crear producto con precio en lista minorista."""
        service = ProductService(session)
        product = service.create_product(
            sku="P-004",
            name="Llave inglesa",
            prices={default_price_list.id: Decimal("1500.00")},
        )

        assert len(product.prices) == 1
        assert product.prices[0].amount == Decimal("1500.00")
        assert product.prices[0].price_list_id == default_price_list.id

    def test_update_product_name(self, session: Session, sample_product):
        """Actualizar nombre de un producto existente."""
        service = ProductService(session)
        updated = service.update_product(sample_product.id, name="Producto actualizado")

        assert updated.name == "Producto actualizado"
        assert updated.sku == sample_product.sku  # SKU no cambia

    def test_update_nonexistent_product_raises(self, session: Session):
        """Actualizar producto que no existe lanza ProductoNoEncontradoError."""
        service = ProductService(session)

        with pytest.raises(ProductoNoEncontradoError):
            service.update_product(99999, name="No existe")

    def test_deactivate_product(self, session: Session, sample_product):
        """Desactivar un producto lo marca como inactivo (baja logica)."""
        service = ProductService(session)
        service.deactivate_product(sample_product.id)

        product = service.get_product(sample_product.id)
        assert product.is_active is False

    def test_search_by_name(self, session: Session, sample_product):
        """Busqueda por nombre retorna el producto correcto.

        Este test utiliza el metodo historico ``search_products`` para asegurarnos
        de que el alias sigue funcionando tras los refactorings.
        """
        service = ProductService(session)
        results = service.search_products("prueba")

        assert len(results) >= 1
        assert any(p.id == sample_product.id for p in results)

    def test_search_with_limit_parameter(self, session: Session, sample_product):
        """El metodo ``search`` acepta un limite y lo aplica correctamente."""
        service = ProductService(session)

        # crear algunos productos extra que tambien coincidan con la busqueda
        for i in range(5):
            service.create_product(sku=f"LIM{i}", name="prueba extra")

        # si pedimos limit pequeño solo deberia devolver esa cantidad
        results = service.search("prueba", limit=2)
        assert len(results) == 2

        # y la llamada al alias deberia retornar los mismos productos sin limit
        results_alias = service.search_products("prueba")
        assert len(results_alias) >= 3

    def test_search_empty_query_returns_limit(self, session: Session):
        """Una busqueda con query vacio debe devolver algunos productos (hasta el
        limite) en lugar de un listado completamente vacio."""
        service = ProductService(session)
        # asegurarnos de tener por lo menos 3 productos en la base
        for i in range(3):
            service.create_product(sku=f"EQ{i}", name="producto {i}")

        results = service.search("", limit=2)
        assert len(results) == 2

    def test_search_by_barcode(self, session: Session):
        """Busqueda por codigo de barras retorna el producto correcto."""
        service = ProductService(session)
        product = service.create_product(
            sku="BC-001",
            name="Producto con barcode",
            barcodes=["1234567890123"],
        )

        results = service.search_products("1234567890123")
        assert any(p.id == product.id for p in results)

    def test_set_price_creates_new(self, session: Session, sample_product, default_price_list):
        """set_price crea precio si no existia."""
        service = ProductService(session)
        price = service.set_price(sample_product.id, default_price_list.id, Decimal("999.99"))

        assert price.amount == Decimal("999.99")

    def test_set_price_updates_existing(self, session: Session, sample_product, default_price_list):
        """set_price actualiza precio si ya existia."""
        service = ProductService(session)
        service.set_price(sample_product.id, default_price_list.id, Decimal("100.00"))
        service.set_price(sample_product.id, default_price_list.id, Decimal("200.00"))

        from app.repository.product_repository import ProductRepository
        repo = ProductRepository(session)
        price = repo.get_price(sample_product.id, default_price_list.id)
        assert price.amount == Decimal("200.00")

    def test_add_barcode_duplicate_raises(self, session: Session, sample_product):
        """Agregar un codigo de barras ya en uso lanza ValueError."""
        service = ProductService(session)
        service.add_barcode(sample_product.id, "9999999999999")

        with pytest.raises(ValueError, match="ya esta en uso"):
            service.add_barcode(sample_product.id, "9999999999999")

    def test_remove_barcode(self, session: Session, sample_product):
        """Remover un codigo de barras existente lo elimina de la base de datos."""
        service = ProductService(session)
        barcode = service.add_barcode(sample_product.id, "1111111111111")
        
        # Verificar que existe
        product = service.get_product(sample_product.id)
        assert len(product.barcodes) == 1
        assert product.barcodes[0].code == "1111111111111"
        
        # Remover
        service.remove_barcode(barcode.id)
        
        # Verificar que fue eliminado
        product = service.get_product(sample_product.id)
        assert len(product.barcodes) == 0

    def test_remove_nonexistent_barcode_silently_ignored(self, session: Session):
        """Intentar remover un barcode inexistente no lanza error (idempotente)."""
        service = ProductService(session)
        # No debería lanzar excepción
        service.remove_barcode(99999)

    def test_barcode_by_get_by_barcode_repository(self, session: Session):
        """El repositorio puede buscar un producto por codigo de barras."""
        from app.repository.product_repository import ProductRepository
        
        service = ProductService(session)
        product = service.create_product(
            sku="SEARCH-BC",
            name="Buscar por barcode",
            barcodes=["UNIQUE-BC-2024"],
        )
        
        repo = ProductRepository(session)
        found = repo.get_by_barcode("UNIQUE-BC-2024")
        assert found is not None
        assert found.id == product.id

    def test_create_category(self, session: Session):
        """Crear categoria nueva."""
        service = ProductService(session)
        cat = service.create_category("Herramientas", "Herramientas manuales y electricas")

        assert cat.id is not None
        assert cat.name == "Herramientas"
