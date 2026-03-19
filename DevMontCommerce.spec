# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[('alembic', 'alembic'), ('alembic.ini', '.'), ('assets', 'assets')],
    hiddenimports=['sqlalchemy.dialects.sqlite', 'sqlalchemy.orm', 'alembic', 'alembic.config', 'alembic.command', 'alembic.runtime.migration', 'alembic.operations', 'customtkinter', 'PIL._tkinter_finder', 'reportlab.graphics.renderPDF', 'reportlab.platypus', 'pydantic_settings', 'bcrypt', 'app.models', 'app.models.user', 'app.models.product', 'app.models.stock', 'app.models.sale', 'app.models.purchase', 'app.models.supplier', 'app.models.customer', 'app.models.invoice'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='DevMontCommerce',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['assets\\icon.ico'],
)
