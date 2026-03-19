# tests/conftest.py
"""
Fixtures compartidos para todos los tests.
Usa SQLite en memoria (:memory:) para aislar cada test
sin tocar la base de datos real.
"""
from decimal import Decimal

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker

from app.models import Base
from app.models.product import Category, PriceList, Product
from app.models.stock import Stock
from app.models.user import Role, User
from app.core.security import hash_password


# ── Engine en memoria ─────────────────────────────────────────────────────────

@pytest.fixture(scope="session")
def engine():
    """
    Engine SQLite en memoria compartido por la sesion de tests.
    Se crea una vez y se reutiliza en todos los tests.
    """
    _engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
    )

    # Aplicar los mismos PRAGMAs que en produccion
    @event.listens_for(_engine, "connect")
    def set_pragmas(dbapi_conn, _):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    # Crear todas las tablas
    Base.metadata.create_all(_engine)
    yield _engine
    Base.metadata.drop_all(_engine)


@pytest.fixture(scope="function")
def session(engine):
    """
    Sesion de base de datos con rollback automatico al finalizar cada test.
    Usa SAVEPOINT para que los rollbacks internos de los services no
    invaliden la conexion del test.
    """
    connection = engine.connect()
    transaction = connection.begin()
    _session = Session(bind=connection)

    # Crear un savepoint anidado para aislar rollbacks internos
    nested = connection.begin_nested()

    from sqlalchemy import event as sa_event

    @sa_event.listens_for(_session, "after_transaction_end")
    def restart_savepoint(session, transaction):
        nonlocal nested
        if not nested.is_active:
            nested = connection.begin_nested()

    yield _session

    _session.close()
    transaction.rollback()
    connection.close()


# ── Datos de prueba reutilizables ─────────────────────────────────────────────

@pytest.fixture
def admin_user(session: Session) -> User:
    """Usuario administrador para tests de autenticacion y ventas."""
    role = Role(name="admin", description="Administrador")
    session.add(role)
    session.flush()

    user = User(
        username="admin_test",
        full_name="Admin Test",
        hashed_password=hash_password("test1234"),
        is_active=True,
        roles=[role],
    )
    session.add(user)
    session.flush()
    return user


@pytest.fixture
def default_price_list(session: Session) -> PriceList:
    """Lista de precios minorista por defecto."""
    price_list = PriceList(name="Minorista", is_default=True)
    session.add(price_list)
    session.flush()
    return price_list


@pytest.fixture
def category(session: Session) -> Category:
    """Categoria generica para productos de prueba."""
    cat = Category(name="General")
    session.add(cat)
    session.flush()
    return cat


@pytest.fixture
def sample_product(session: Session, category: Category) -> Product:
    """
    Producto con stock inicial de 100 unidades.
    Fixture central usado por la mayoria de los tests de venta y stock.
    """
    product = Product(
        sku="TEST-001",
        name="Producto de prueba",
        unit="unidad",
        category_id=category.id,
    )
    session.add(product)
    session.flush()

    stock = Stock(
        product_id=product.id,
        quantity=Decimal("100"),
        min_quantity=Decimal("5"),
    )
    session.add(stock)
    session.flush()
    return product


@pytest.fixture
def low_stock_product(session: Session) -> Product:
    """Producto con stock critico (por debajo del minimo)."""
    product = Product(sku="LOW-001", name="Producto stock bajo", unit="unidad")
    session.add(product)
    session.flush()

    stock = Stock(
        product_id=product.id,
        quantity=Decimal("2"),
        min_quantity=Decimal("10"),
    )
    session.add(stock)
    session.flush()
    return product
