# app/models/product.py
from decimal import Decimal

from sqlalchemy import ForeignKey, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class Category(Base, TimestampMixin):
    """Categoria de productos (ej: Herramientas, Electricidad, Limpieza)."""
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relacion inversa
    products: Mapped[list["Product"]] = relationship(back_populates="category")

    def __repr__(self) -> str:
        return f"<Category {self.name}>"


class Product(Base, TimestampMixin):
    """
    Producto comercializado por el negocio.
    Un producto puede tener multiples codigos de barras y multiples listas de precio.
    """
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    sku: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    unit: Mapped[str] = mapped_column(String(20), default="unidad", nullable=False)  # unidad, kg, m, etc.
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)

    # FK a categoria (opcional)
    category_id: Mapped[int | None] = mapped_column(
        ForeignKey("categories.id", ondelete="SET NULL"), nullable=True
    )

    # Relaciones
    category: Mapped[Category | None] = relationship(back_populates="products")
    barcodes: Mapped[list["Barcode"]] = relationship(back_populates="product", cascade="all, delete-orphan")
    prices: Mapped[list["Price"]] = relationship(back_populates="product", cascade="all, delete-orphan")
    stock: Mapped["Stock"] = relationship(back_populates="product", uselist=False, cascade="all, delete-orphan")  # type: ignore[name-defined]
    sale_details: Mapped[list["SaleDetail"]] = relationship(back_populates="product")  # type: ignore[name-defined]
    purchase_details: Mapped[list["PurchaseDetail"]] = relationship(back_populates="product")  # type: ignore[name-defined]

    def __repr__(self) -> str:
        return f"<Product {self.sku} - {self.name}>"


class Barcode(Base):
    """
    Codigo de barras asociado a un producto.
    Un producto puede tener multiples codigos (EAN-13, QR, codigo interno).
    """
    __tablename__ = "barcodes"
    __table_args__ = (UniqueConstraint("code", name="uq_barcode_code"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id", ondelete="CASCADE"), nullable=False
    )

    product: Mapped[Product] = relationship(back_populates="barcodes")

    def __repr__(self) -> str:
        return f"<Barcode {self.code}>"


class PriceList(Base, TimestampMixin):
    """
    Lista de precios (ej: Minorista, Mayorista, Empleados).
    Permite manejar distintos precios para distintos tipos de clientes.
    """
    __tablename__ = "price_lists"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(String(200), nullable=True)
    is_default: Mapped[bool] = mapped_column(default=False, nullable=False)

    prices: Mapped[list["Price"]] = relationship(back_populates="price_list")

    def __repr__(self) -> str:
        return f"<PriceList {self.name}>"


class Price(Base, TimestampMixin):
    """
    Precio de un producto en una lista de precios especifica.
    Permite historico: se registra cuando cambio el precio.
    """
    __tablename__ = "prices"
    __table_args__ = (
        UniqueConstraint("product_id", "price_list_id", name="uq_price_product_list"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id", ondelete="CASCADE"), nullable=False
    )
    price_list_id: Mapped[int] = mapped_column(
        ForeignKey("price_lists.id", ondelete="CASCADE"), nullable=False
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)

    product: Mapped[Product] = relationship(back_populates="prices")
    price_list: Mapped[PriceList] = relationship(back_populates="prices")

    def __repr__(self) -> str:
        return f"<Price product={self.product_id} list={self.price_list_id} amount={self.amount}>"
