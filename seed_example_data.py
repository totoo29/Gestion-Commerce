from decimal import Decimal

from sqlalchemy import select

from app.core.logging import get_logger, setup_logging
from app.database import SessionLocal
from app.models.customer import Customer
from app.models.supplier import Supplier
from app.services.product_service import ProductService
from main import ensure_admin, run_migrations


logger = get_logger(__name__)


def seed_example_data() -> None:
    """
    Crea datos de ejemplo en la base de datos:
      - Usuario admin (si no existe)
      - Categorias
      - Lista de precios por defecto
      - Productos con stock inicial y precios
      - Algunos clientes y proveedores
    Es seguro ejecutarla varias veces: si ya hay datos basicos, no duplica.
    """
    setup_logging()
    logger.info("Iniciando seed de datos de ejemplo...")

    # Asegurar esquema y usuario admin
    run_migrations()
    ensure_admin()

    with SessionLocal() as session:
        product_service = ProductService(session)

        # ── Listas de precio ─────────────────────────────────────────────────
        default_price_list = product_service.get_default_price_list()
        if default_price_list is None:
            logger.info("Creando lista de precios 'Minorista' por defecto...")
            default_price_list = product_service.create_price_list(
                name="Minorista",
                description="Lista de precios minorista por defecto",
                is_default=True,
            )

        # ── Categorias ───────────────────────────────────────────────────────
        categories = product_service.get_all_categories()
        if not categories:
            logger.info("Creando categorias de ejemplo...")
            bebidas = product_service.create_category(
                name="Bebidas",
                description="Bebidas y refrescos",
            )
            snacks = product_service.create_category(
                name="Snacks",
                description="Snacks y golosinas",
            )
            limpieza = product_service.create_category(
                name="Limpieza",
                description="Productos de limpieza del hogar",
            )
            categories = [bebidas, snacks, limpieza]
        else:
            bebidas = categories[0]

        # ── Productos ────────────────────────────────────────────────────────
        existing_products = product_service.get_all_products(limit=1)
        if not existing_products:
            logger.info("Creando productos de ejemplo...")

            product_service.create_product(
                sku="BEB-001",
                name="Gaseosa Cola 1.5L",
                description="Botella de gaseosa sabor cola 1.5L",
                unit="unidad",
                category_id=bebidas.id,
                barcodes=["7790000000011"],
                initial_stock=Decimal("30"),
                prices={default_price_list.id: Decimal("1500.00")},
            )

            product_service.create_product(
                sku="BEB-002",
                name="Agua Mineral 500ml",
                description="Agua mineral sin gas 500ml",
                unit="unidad",
                category_id=bebidas.id,
                barcodes=["7790000000028"],
                initial_stock=Decimal("50"),
                prices={default_price_list.id: Decimal("800.00")},
            )

        # ── Clientes ─────────────────────────────────────────────────────────
        if not session.scalars(select(Customer).limit(1)).first():
            logger.info("Creando clientes de ejemplo...")
            customers = [
                Customer(
                    full_name="Consumidor Final",
                    tax_id=None,
                    email=None,
                    phone=None,
                    address="",
                    is_active=True,
                ),
                Customer(
                    full_name="Cliente Empresa S.A.",
                    tax_id="30-12345678-9",
                    email="contacto@clienteempresa.com",
                    phone="+54 11 5555-0000",
                    address="Av. Siempre Viva 123, CABA",
                    is_active=True,
                ),
            ]
            session.add_all(customers)
            session.commit()

        # ── Proveedores ──────────────────────────────────────────────────────
        if not session.scalars(select(Supplier).limit(1)).first():
            logger.info("Creando proveedores de ejemplo...")
            suppliers = [
                Supplier(
                    name="Bebidas Argentinas S.R.L.",
                    tax_id="30-87654321-0",
                    contact_name="Juan Pérez",
                    email="ventas@bebidasargen.com",
                    phone="+54 11 4444-1111",
                    address="Ruta 8 km 45, Buenos Aires",
                    notes="Entrega semanal",
                    is_active=True,
                ),
            ]
            session.add_all(suppliers)
            session.commit()

    logger.info("Seed de datos de ejemplo completado.")


if __name__ == "__main__":
    seed_example_data()

