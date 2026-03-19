# main.py
import os

import alembic.config
import customtkinter as ctk
from alembic import command

from app.core.config import settings
from app.core.constants import APP_NAME, APP_VERSION
from app.core.logging import get_logger, setup_logging

logger = get_logger(__name__)


def run_migrations() -> None:
    """Aplica todas las migraciones pendientes al iniciar la app."""
    logger.info("Verificando migraciones de base de datos...")
    
    # 1. Obtenemos la ruta absoluta de la carpeta donde está main.py
    base_dir = os.path.dirname(os.path.abspath(__file__))
    
    # 2. Armamos la ruta absoluta hacia alembic.ini
    alembic_ini_path = os.path.join(base_dir, "alembic.ini")
    
    # 3. Cargamos la configuración con esa ruta exacta
    alembic_cfg = alembic.config.Config(alembic_ini_path)
    
    # 4. Forzamos la ruta absoluta de la carpeta de scripts para evitar problemas similares
    alembic_cfg.set_main_option("script_location", os.path.join(base_dir, "alembic"))
    
    command.upgrade(alembic_cfg, "head")
    logger.info("Base de datos actualizada.")

def ensure_admin() -> None:
    """Crea el usuario admin por defecto si la DB esta vacia."""
    from app.database import SessionLocal
    from app.services.auth_service import AuthService
    with SessionLocal() as session:
        AuthService(session).ensure_admin_exists()


def main() -> None:
    # 1. Configurar logs (debe ser lo primero)
    setup_logging()
    logger.info(f"Iniciando {APP_NAME} v{APP_VERSION}")

    # 2. Aplicar migraciones pendientes
    run_migrations()

    # 3. Garantizar que exista al menos un usuario admin
    ensure_admin()

    # 4. Iniciar scheduler de backup automatico (hilo daemon, no bloquea)
    from app.services.backup_scheduler import BackupScheduler
    scheduler = BackupScheduler()
    scheduler.start()

    # 5. Lanzar la app (tema fijo definido en app.ui.theme)
    from app.ui.app import DevMontApp
    app = DevMontApp()

    # Detener scheduler al cerrar la ventana
    original_close = app._on_close
    def _on_close_with_scheduler():
        scheduler.stop()
        original_close()
    app._on_close = _on_close_with_scheduler
    app.protocol("WM_DELETE_WINDOW", _on_close_with_scheduler)

    logger.info("Ventana principal iniciada.")
    app.mainloop()
    logger.info(f"{APP_NAME} cerrado correctamente.")


if __name__ == "__main__":
    main()
