# app/core/logging.py
import logging
import sys
from logging.handlers import RotatingFileHandler

from app.core.config import settings

_LOG_FILE = settings.LOG_DIR / "devmont.log"
_MAX_BYTES = 5 * 1024 * 1024   # 5 MB por archivo
_BACKUP_COUNT = 3               # Conservar hasta 3 archivos rotados

_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def setup_logging() -> None:
    """
    Configura el sistema de logs.
    - Siempre: escribe en archivo rotativo en LOG_DIR.
    - En modo DEBUG: muestra logs tambien en consola.
    Llamar una sola vez al iniciar la app (en main.py).
    """
    level = logging.DEBUG if settings.DEBUG else logging.INFO
    formatter = logging.Formatter(_FORMAT, datefmt=_DATE_FORMAT)

    file_handler = RotatingFileHandler(
        _LOG_FILE,
        maxBytes=_MAX_BYTES,
        backupCount=_BACKUP_COUNT,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)

    handlers: list[logging.Handler] = [file_handler]

    if settings.DEBUG:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        handlers.append(console_handler)

    logging.basicConfig(level=level, handlers=handlers, force=True)

    logging.getLogger("sqlalchemy.engine").setLevel(
        logging.DEBUG if settings.DEBUG else logging.WARNING
    )
    logging.getLogger("alembic").setLevel(logging.INFO)


def get_logger(name: str) -> logging.Logger:
    """Shortcut para obtener un logger con el nombre del modulo."""
    return logging.getLogger(name)
