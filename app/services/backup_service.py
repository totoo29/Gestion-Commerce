# app/services/backup_service.py
import shutil
from datetime import datetime
from pathlib import Path

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class BackupService:

    def create_backup(self) -> Path:
        """
        Copia el archivo .db con timestamp al directorio de backups.
        Formato: devmont_20240315_143022.db
        Retorna la ruta del backup creado.
        """
        if not settings.DB_PATH.exists():
            logger.warning("No se puede hacer backup: el archivo de base de datos no existe aun.")
            raise FileNotFoundError(f"Base de datos no encontrada: {settings.DB_PATH}")

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = settings.BACKUP_DIR / f"devmont_{timestamp}.db"

        shutil.copy2(settings.DB_PATH, backup_path)
        logger.info(f"Backup creado: {backup_path}")

        self._cleanup_old_backups()
        return backup_path

    def _cleanup_old_backups(self) -> None:
        """Elimina backups con mas de BACKUP_KEEP_DAYS dias."""
        cutoff = datetime.now().timestamp() - (settings.BACKUP_KEEP_DAYS * 86400)
        removed = 0

        for backup in settings.BACKUP_DIR.glob("devmont_*.db"):
            if backup.stat().st_mtime < cutoff:
                backup.unlink()
                removed += 1

        if removed:
            logger.info(f"Backups eliminados por antiguedad: {removed}")

    def restore_from_backup(self, backup_path: Path) -> None:
        """
        Reemplaza la base de datos actual con un backup.
        USAR CON PRECAUCION: esta operacion es irreversible.
        La app debe reiniciarse despues de restaurar.
        """
        if not backup_path.exists():
            raise FileNotFoundError(f"Backup no encontrado: {backup_path}")

        shutil.copy2(backup_path, settings.DB_PATH)
        logger.warning(f"Base de datos restaurada desde: {backup_path}")

    def list_backups(self) -> list[Path]:
        """Lista todos los backups disponibles, del mas reciente al mas antiguo."""
        backups = sorted(
            settings.BACKUP_DIR.glob("devmont_*.db"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        return backups

    def get_backup_dir(self) -> Path:
        return settings.BACKUP_DIR
