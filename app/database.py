# app/database.py
from collections.abc import Generator

from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings

# ── Engine ────────────────────────────────────────────────────────────────────
engine = create_engine(
    f"sqlite:///{settings.DB_PATH}",
    connect_args={"check_same_thread": False},
    echo=settings.DEBUG,
)


# ── PRAGMAs aplicados en cada nueva conexion ──────────────────────────────────
@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_conn, connection_record):  # noqa: ANN001
    cursor = dbapi_conn.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")    # Lecturas concurrentes
    cursor.execute("PRAGMA foreign_keys=ON")     # Integridad referencial
    cursor.execute("PRAGMA synchronous=NORMAL")  # Balance velocidad/seguridad
    cursor.close()


# ── Session factory ───────────────────────────────────────────────────────────
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


def get_session() -> Generator[Session, None, None]:
    """
    Context manager para obtener una sesion de base de datos.

    Uso en services:
        with SessionLocal() as session:
            service = MiService(session)
    """
    session = SessionLocal()
    try:
        yield session
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
