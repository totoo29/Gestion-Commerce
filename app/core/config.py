# app/core/config.py
from pathlib import Path

from pydantic_settings import BaseSettings

# Directorio base: C:\Users\<usuario>\DevMontCommerce\
BASE_DIR = Path.home() / "DevMontCommerce"


class Settings(BaseSettings):
    # ── Base de datos ──────────────────────────────────────────────────────────
    DB_PATH: Path = BASE_DIR / "data" / "devmont.db"

    # ── Backups automaticos ────────────────────────────────────────────────────
    BACKUP_DIR: Path = BASE_DIR / "backups"
    BACKUP_KEEP_DAYS: int = 30

    # ── Reportes y PDFs generados ─────────────────────────────────────────────
    REPORTS_DIR: Path = BASE_DIR / "reportes"

    # ── Logs de la aplicacion ─────────────────────────────────────────────────
    LOG_DIR: Path = BASE_DIR / "logs"

    # ── Interfaz ──────────────────────────────────────────────────────────────
    THEME: str = "dark"       # "dark" o "light"
    FONT_SIZE: int = 13

    # ── Datos del negocio (para tickets y facturas) ────────────────────────────
    # Estos valores pueden sobreescribirse en el archivo .env
    BUSINESS_NAME: str    = "Mi Comercio"
    BUSINESS_ADDRESS: str = "Dirección del local"
    BUSINESS_PHONE: str   = ""
    BUSINESS_EMAIL: str   = ""
    BUSINESS_TAX_ID: str  = ""      # CUIT del negocio
    BUSINESS_SLOGAN: str  = ""      # Frase opcional en el ticket

    # ── Desarrollo ────────────────────────────────────────────────────────────
    DEBUG: bool = False       # True => muestra SQL en consola

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()

# Crear todos los directorios al importar el modulo (idempotente)
for _dir in [
    settings.DB_PATH.parent,
    settings.BACKUP_DIR,
    settings.REPORTS_DIR,
    settings.LOG_DIR,
]:
    _dir.mkdir(parents=True, exist_ok=True)
