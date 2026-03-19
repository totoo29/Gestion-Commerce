# app/repository/product_repository.py
from sqlalchemy import or_, select
from sqlalchemy.orm import Session, joinedload

from app.models.product import Barcode, Category, Price, PriceList, Product
from app.repository.base_repository import BaseRepository


class ProductRepository(BaseRepository[Product]):

    def __init__(self, session: Session):
        super().__init__(session, Product)

    def get_by_sku(self, sku: str) -> Product | None:
        stmt = select(Product).where(Product.sku == sku)
        return self.session.scalars(stmt).first()

    def get_by_barcode(self, code: str) -> Product | None:
        """Busca un producto por cualquiera de sus codigos de barras."""
        stmt = (
            select(Product)
            .join(Product.barcodes)
            .where(Barcode.code == code)
            .options(joinedload(Product.barcodes), joinedload(Product.prices))
        )
        return self.session.scalars(stmt).unique().first()

    def search(self, query: str, limit: int = 20) -> list[Product]:
        """
        Busqueda por texto libre: coincide contra nombre, SKU y codigos de barras.
        Util para la barra de busqueda del punto de venta.
        """
        like = f"%{query}%"
        stmt = (
            select(Product)
            .outerjoin(Product.barcodes)
            .where(
                Product.is_active == True,  # noqa: E712
                or_(
                    Product.name.ilike(like),
                    Product.sku.ilike(like),
                    Barcode.code.ilike(like),
                ),
            )
            .distinct()
            .limit(limit)
            .options(
                joinedload(Product.barcodes),
                joinedload(Product.stock),
                joinedload(Product.prices).joinedload(Price.price_list),
            )
        )
        return list(self.session.scalars(stmt).unique().all())

    def get_active_products(self, limit: int = 200, offset: int = 0) -> list[Product]:
        stmt = (
            select(Product)
            .where(Product.is_active == True)  # noqa: E712
            .order_by(Product.name)
            .limit(limit)
            .offset(offset)
            .options(
                joinedload(Product.category),
                joinedload(Product.barcodes),
                joinedload(Product.stock),
                joinedload(Product.prices).joinedload(Price.price_list),
            )
        )
        return list(self.session.scalars(stmt).unique().all())

    def get_with_full_detail(self, product_id: int) -> Product | None:
        """Carga el producto con todas sus relaciones (para pantalla de edicion)."""
        stmt = (
            select(Product)
            .where(Product.id == product_id)
            .options(
                joinedload(Product.category),
                joinedload(Product.barcodes),
                joinedload(Product.prices).joinedload(Price.price_list),
                joinedload(Product.stock),
            )
        )
        return self.session.scalars(stmt).unique().first()

    # ── Categorias ────────────────────────────────────────────────────────────

    def get_all_categories(self) -> list[Category]:
        stmt = select(Category).order_by(Category.name)
        return list(self.session.scalars(stmt).all())

    def get_category_by_name(self, name: str) -> Category | None:
        stmt = select(Category).where(Category.name == name)
        return self.session.scalars(stmt).first()

    # ── Listas de precio ──────────────────────────────────────────────────────

    def get_default_price_list(self) -> PriceList | None:
        stmt = select(PriceList).where(PriceList.is_default == True)  # noqa: E712
        return self.session.scalars(stmt).first()

    def get_all_price_lists(self) -> list[PriceList]:
        stmt = select(PriceList).order_by(PriceList.name)
        return list(self.session.scalars(stmt).all())

    def get_price(self, product_id: int, price_list_id: int) -> Price | None:
        stmt = select(Price).where(
            Price.product_id == product_id,
            Price.price_list_id == price_list_id,
        )
        return self.session.scalars(stmt).first()

    # ── Barcodes ──────────────────────────────────────────────────────────────

    def barcode_exists(self, code: str) -> bool:
        stmt = select(Barcode).where(Barcode.code == code)
        return self.session.scalars(stmt).first() is not None
