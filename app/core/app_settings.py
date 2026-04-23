import json
from pathlib import Path
from typing import TypedDict
from app.core.logging import get_logger

logger = get_logger(__name__)

# Ubicacion del archivo de configuraciones
SETTINGS_PATH = Path("data/settings.json")

class InvoiceSettingsDict(TypedDict):
    company_name: str
    company_id: str
    address: str
    phone: str
    footer_text: str
    logo_path: str
    print_format: str

class ApplicationSettings:
    """Gestor de configuraciones generales de la app, persistidas en JSON."""
    _instance = None
    _settings: InvoiceSettingsDict = {
        "company_name": "DevMont Commerce",
        "company_id": "CUIT: 00-00000000-0",
        "address": "Dirección comercial 123",
        "phone": "+54 11 1234-5678",
        "footer_text": "¡Gracias por su confiar en nosotros!",
        "logo_path": "",
        "print_format": "80mm",
    }

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ApplicationSettings, cls).__new__(cls)
            cls._instance._load()
        return cls._instance

    def _load(self):
        try:
            if SETTINGS_PATH.exists():
                with open(SETTINGS_PATH, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self._settings.update(data)
        except Exception as e:
            logger.error(f"No se pudo cargar settings.json: {e}")

    def save(self):
        try:
            SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
            with open(SETTINGS_PATH, "w", encoding="utf-8") as f:
                json.dump(self._settings, f, indent=4, ensure_ascii=False)
            logger.info("Configuraciones guardadas exitosamente.")
        except Exception as e:
            logger.error(f"No se pudo guardar settings.json: {e}")

    @classmethod
    def get_settings(cls) -> InvoiceSettingsDict:
        return cls()._settings

    @classmethod
    def save_settings(cls, **kwargs):
        inst = cls()
        inst._settings.update(kwargs)
        inst.save()
