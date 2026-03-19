# app/services/product_service.py
from decimal import Decimal

from sqlalchemy.orm import Session

from app.core.constants import DEFAULT_MIN_STOCK
from app.core.exceptions import ProductoNoEncontradoError
from app.core.logging import get_logger
from app.models.product import Barcode, Category, Price, PriceList, Product
from app.models.stock import Stock
from app.repository.product_repository import ProductRepository
from app.repository.stock_repository import StockRepository

logger = get_logger(__name__)


class ProductService:

    def __init__(self, session: Session):
        self.session = session
        self.product_repo = ProductRepository(session)
        self.stock_repo = StockRepository(session)

    # ── Productos ─────────────────────────────────────────────────────────────

    def create_product(
        self,
        sku: str,
        name: str,
        description: str | None = None,
        unit: str = "unidad",
        category_id: int | None = None,
        barcodes: list[str] | None = None,
        initial_stock: Decimal = Decimal("0"),
        min_stock: Decimal = Decimal(str(DEFAULT_MIN_STOCK)),
        prices: dict[int, Decimal] | None = None,  # {price_list_id: amount}
    ) -> Product:
        """
        Crea un producto completo con su stock inicial,
        codigos de barras y precios en una sola transaccion.
        """
        product = Product(
            sku=sku,
            name=name,
            description=description,
            unit=unit,
            category_id=category_id,
        )
        self.product_repo.create(product)

        # Crear registro de stock asociado
        stock = Stock(
            product_id=product.id,
            quantity=initial_stock,
            min_quantity=min_stock,
        )
        self.session.add(stock)

        # Agregar codigos de barras
        for code in (barcodes or []):
            if not self.product_repo.barcode_exists(code):
                self.session.add(Barcode(code=code, product_id=product.id))

        # Agregar precios
        for price_list_id, amount in (prices or {}).items():
            self.session.add(Price(
                product_id=product.id,
                price_list_id=price_list_id,
                amount=amount,
            ))

        self.session.commit()
        logger.info(f"Producto creado: SKU={sku}, nombre='{name}'")
        return product

    def update_product(
        self,
        product_id: int,
        name: str | None = None,
        description: str | None = None,
        unit: str | None = None,
        category_id: int | None = None,
        is_active: bool | None = None,
    ) -> Product:
        """Actualiza los campos basicos de un producto."""
        product = self.product_repo.get_by_id(product_id)
        if product is None:
            raise ProductoNoEncontradoError(product_id)

        if name is not None:
            product.name = name
        if description is not None:
            product.description = description
        if unit is not None:
            product.unit = unit
        if category_id is not None:
            product.category_id = category_id
        if is_active is not None:
            product.is_active = is_active

        self.session.commit()
        logger.info(f"Producto actualizado: id={product_id}")
        return product

    def deactivate_product(self, product_id: int) -> None:
        """Baja logica: marca el producto como inactivo sin eliminarlo."""
        product = self.product_repo.get_by_id(product_id)
        if product is None:
            raise ProductoNoEncontradoError(product_id)
        product.is_active = False
        self.session.commit()
        logger.info(f"Producto desactivado: id={product_id}")

    def search(self, query: str, limit: int = 20) -> list[Product]:
        """Busca productos utilizando el repositorio.

        El parametro *limit* se pasa directamente al repositorio y permite limitar
        la cantidad de resultados retornados (especialmente util para la barra de
        busqueda del punto de venta).
        """
        return self.product_repo.search(query, limit=limit)

    # Se mantiene el metodo anterior por compatibilidad con otras partes del
    # codigo que ya lo invocaban.
    def search_products(self, query: str) -> list[Product]:
        """Busqueda por texto: nombre, SKU o codigo de barras.

        Internamente delega en :meth:`search`.
        """
        return self.search(query)

    def get_product(self, product_id: int) -> Product:
        product = self.product_repo.get_with_full_detail(product_id)
        if product is None:
            raise ProductoNoEncontradoError(product_id)
        return product

    def get_all_products(self, limit: int = 200, offset: int = 0) -> list[Product]:
        return self.product_repo.get_active_products(limit=limit, offset=offset)

    # ── Precios ───────────────────────────────────────────────────────────────

    def set_price(
        self,
        product_id: int,
        price_list_id: int,
        amount: Decimal,
    ) -> Price:
        """Crea o actualiza el precio de un producto en una lista de precios."""
        price = self.product_repo.get_price(product_id, price_list_id)
        if price is None:
            price = Price(
                product_id=product_id,
                price_list_id=price_list_id,
                amount=amount,
            )
            self.session.add(price)
        else:
            price.amount = amount

        self.session.commit()
        logger.info(f"Precio actualizado: producto={product_id}, lista={price_list_id}, monto={amount}")
        return price

    # ── Categorias ────────────────────────────────────────────────────────────

    def create_category(self, name: str, description: str | None = None) -> Category:
        category = Category(name=name, description=description)
        self.session.add(category)
        self.session.commit()
        return category

    def get_all_categories(self) -> list[Category]:
        return self.product_repo.get_all_categories()

    # ── Listas de precio ──────────────────────────────────────────────────────

    def create_price_list(
        self,
        name: str,
        description: str | None = None,
        is_default: bool = False,
    ) -> PriceList:
        price_list = PriceList(name=name, description=description, is_default=is_default)
        self.session.add(price_list)
        self.session.commit()
        return price_list

    def get_all_price_lists(self) -> list[PriceList]:
        return self.product_repo.get_all_price_lists()

    def get_default_price_list(self) -> PriceList | None:
        return self.product_repo.get_default_price_list()

    # ── Barcodes ──────────────────────────────────────────────────────────────

    def add_barcode(self, product_id: int, code: str) -> Barcode:
        if self.product_repo.barcode_exists(code):
            raise ValueError(f"El codigo de barras '{code}' ya esta en uso.")
        barcode = Barcode(product_id=product_id, code=code)
        self.session.add(barcode)
        self.session.commit()
        return barcode

    def remove_barcode(self, barcode_id: int) -> None:
        from sqlalchemy import select
        from app.models.product import Barcode as BarcodeModel
        stmt = select(BarcodeModel).where(BarcodeModel.id == barcode_id)
        barcode = self.session.scalars(stmt).first()
        if barcode:
            self.session.delete(barcode)
            self.session.commit()
