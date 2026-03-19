# app/services/backup_scheduler.py
"""
Scheduler de backup automatico.
Crea un backup al iniciar la app y luego cada 24 horas en segundo plano.
Usa threading.Timer para no bloquear la UI de Tkinter.

Uso en main.py (ya integrado):
    from app.services.backup_scheduler import BackupScheduler
    scheduler = BackupScheduler()
    scheduler.start()
    # Al cerrar la app:
    scheduler.stop()
"""
from __future__ import annotations

import threading
from pathlib import Path

from app.core.logging import get_logger
from app.services.backup_service import BackupService

logger = get_logger(__name__)

BACKUP_INTERVAL_HOURS = 24
BACKUP_INTERVAL_SECS  = BACKUP_INTERVAL_HOURS * 3600


class BackupScheduler:
    """
    Ejecuta backups periodicos en un hilo daemon.
    No bloquea la UI ni el hilo principal.
    """

    def __init__(self) -> None:
        self._timer: threading.Timer | None = None
        self._stopped = False

    def start(self) -> None:
        """
        Crea el backup inicial y programa el proximo en 24 horas.
        Llama a esto una vez al iniciar la aplicacion.
        """
        # Backup inmediato al arrancar (en hilo separado para no bloquear el splash)
        t = threading.Thread(target=self._run_backup, daemon=True)
        t.start()

        # Programar siguiente backup en 24 horas
        self._schedule_next()
        logger.info(f"BackupScheduler iniciado. Proximos backups cada {BACKUP_INTERVAL_HOURS}h.")

    def stop(self) -> None:
        """Cancela el timer pendiente. Llamar al cerrar la app."""
        self._stopped = True
        if self._timer is not None:
            self._timer.cancel()
            self._timer = None
        logger.info("BackupScheduler detenido.")

    # ── Internos ──────────────────────────────────────────────────────────────

    def _run_backup(self) -> None:
        """Ejecuta el backup y registra el resultado."""
        try:
            path = BackupService().create_backup()
            logger.info(f"Backup automatico exitoso: {path.name}")
        except FileNotFoundError:
            logger.info("Backup omitido: la base de datos aun no existe.")
        except Exception as e:
            logger.error(f"Error en backup automatico: {e}")

    def _schedule_next(self) -> None:
        """Programa la proxima ejecucion en BACKUP_INTERVAL_SECS segundos."""
        if self._stopped:
            return
        self._timer = threading.Timer(BACKUP_INTERVAL_SECS, self._tick)
        self._timer.daemon = True
        self._timer.start()

    def _tick(self) -> None:
        """Ejecuta el backup y reprograma el siguiente."""
        if self._stopped:
            return
        self._run_backup()
        self._schedule_next()
