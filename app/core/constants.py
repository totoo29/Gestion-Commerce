# app/core/constants.py
from enum import Enum


class UserRole(str, Enum):
    ADMIN = "admin"
    CAJERO = "cajero"


class MovementType(str, Enum):
    SALE = "sale"             # Descuento por venta
    PURCHASE = "purchase"     # Ingreso por compra
    ADJUSTMENT = "adjustment" # Ajuste manual de inventario
    RETURN = "return"         # Devolucion de cliente


class SaleStatus(str, Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class PurchaseStatus(str, Enum):
    PENDING = "pending"
    RECEIVED = "received"
    CANCELLED = "cancelled"


class InvoiceType(str, Enum):
    TICKET = "ticket"         # Ticket termico (sin datos fiscales)
    FACTURA_A = "factura_a"   # Factura A (responsable inscripto)
    FACTURA_B = "factura_b"   # Factura B (consumidor final)


# Nombre visible del sistema (usado en titulos, PDFs, logs)
APP_NAME = "DevMont Commerce"
APP_VERSION = "1.0.0"

# Stock minimo por defecto al crear un producto nuevo
DEFAULT_MIN_STOCK = 5

# Ancho de papel de impresora termica en mm
THERMAL_PAPER_WIDTH_MM = 80
