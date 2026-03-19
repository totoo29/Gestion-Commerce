# build.py
"""
Script de empaquetado para generar Ferreteria.exe con PyInstaller.

Uso:
    python build.py

Resultado:
    dist/DevMontCommerce.exe  (~60-100 MB, sin necesidad de Python instalado)

Requisitos:
    pip install pyinstaller>=6.0.0
"""
import sys
import subprocess
from pathlib import Path

APP_NAME    = "DevMontCommerce"
ENTRY_POINT = "main.py"
ICON_PATH   = "assets/icon.ico"


def build() -> None:
    icon = Path(ICON_PATH)

    args = [
        sys.executable, "-m", "PyInstaller",

        # Entrada
        ENTRY_POINT,

        # Nombre del ejecutable
        f"--name={APP_NAME}",

        # Sin ventana de consola (app de escritorio)
        "--windowed",

        # Un solo .exe (no carpeta)
        "--onefile",

        # Icono (si existe)
        f"--icon={ICON_PATH}" if icon.exists() else "--icon=NONE",

        # Incluir archivos que PyInstaller no detecta automaticamente
        "--add-data=alembic;alembic",
        "--add-data=alembic.ini;.",

        # Incluir assets si existe la carpeta
        "--add-data=assets;assets" if Path("assets").exists() else "",

        # Imports dinamicos que PyInstaller no rastrea
        "--hidden-import=sqlalchemy.dialects.sqlite",
        "--hidden-import=sqlalchemy.orm",
        "--hidden-import=alembic",
        "--hidden-import=alembic.config",
        "--hidden-import=alembic.command",
        "--hidden-import=alembic.runtime.migration",
        "--hidden-import=alembic.operations",
        "--hidden-import=customtkinter",
        "--hidden-import=PIL._tkinter_finder",
        "--hidden-import=reportlab.graphics.renderPDF",
        "--hidden-import=reportlab.platypus",
        "--hidden-import=pydantic_settings",
        "--hidden-import=bcrypt",
        "--hidden-import=app.models",
        "--hidden-import=app.models.user",
        "--hidden-import=app.models.product",
        "--hidden-import=app.models.stock",
        "--hidden-import=app.models.sale",
        "--hidden-import=app.models.purchase",
        "--hidden-import=app.models.supplier",
        "--hidden-import=app.models.customer",
        "--hidden-import=app.models.invoice",

        # Limpiar build anterior
        "--clean",

        # Directorio de trabajo temporal
        "--workpath=build_tmp",

        # Directorio de salida
        "--distpath=dist",
    ]

    # Filtrar args vacios (el de assets si no existe)
    args = [a for a in args if a]

    print(f"\n{'='*60}")
    print(f"  Empaquetando {APP_NAME}...")
    print(f"{'='*60}\n")

    result = subprocess.run(args)

    if result.returncode == 0:
        exe_path = Path("dist") / f"{APP_NAME}.exe"
        size_mb  = exe_path.stat().st_size / 1024 / 1024 if exe_path.exists() else 0
        print(f"\n{'='*60}")
        print(f"  ✅ Build exitoso!")
        print(f"  Ejecutable: dist/{APP_NAME}.exe  ({size_mb:.1f} MB)")
        print(f"{'='*60}\n")
    else:
        print(f"\n{'='*60}")
        print(f"  ❌ Build fallido. Revisar errores arriba.")
        print(f"{'='*60}\n")
        sys.exit(1)


if __name__ == "__main__":
    build()
