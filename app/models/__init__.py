# app/models/__init__.py
# Importar Base primero, luego todos los modelos.
# Este orden es CRITICO: Alembic necesita que todos los modelos
# esten registrados en Base.metadata antes de generar migraciones.

from app.models.base import Base, TimestampMixin

# Importar en orden de dependencias (de menor a mayor FK)
from app.models.user import Role, User, user_roles
from app.models.customer import Customer
from app.models.supplier import Supplier
from app.models.product import Barcode, Category, Price, PriceList, Product
from app.models.stock import Stock, StockMovement
from app.models.sale import Sale, SaleDetail
from app.models.purchase import Purchase, PurchaseDetail
from app.models.invoice import Invoice

__all__ = [
    "Base",
    "TimestampMixin",
    # Usuarios
    "Role",
    "User",
    "user_roles",
    # Clientes y proveedores
    "Customer",
    "Supplier",
    # Productos
    "Category",
    "Product",
    "Barcode",
    "PriceList",
    "Price",
    # Stock
    "Stock",
    "StockMovement",
    # Ventas
    "Sale",
    "SaleDetail",
    # Compras
    "Purchase",
    "PurchaseDetail",
    # Facturacion
    "Invoice",
]
