# inventario_jh.spec
# ─────────────────────────────────────────────────────────────
# Ejecutar con:  pyinstaller inventario_jh.spec
# ─────────────────────────────────────────────────────────────

from PyInstaller.utils.hooks import collect_data_files, collect_submodules
import sys, os

block_cipher = None

# Recopilar datos de PySide6
pyside6_datas = collect_data_files('PySide6')

a = Analysis(
    ['run.py'],
    pathex=['.'],
    binaries=[],
    datas=[
        ('assets', 'assets'),           # ícono .ico
        ('app', 'app'),                 # código fuente
    ] + pyside6_datas,
    hiddenimports=[
        'sqlalchemy',
        'sqlalchemy.dialects.sqlite',
        'sqlalchemy.orm',
        'reportlab',
        'reportlab.pdfgen',
        'reportlab.lib',
        'reportlab.platypus',
        'PySide6.QtCore',
        'PySide6.QtWidgets',
        'PySide6.QtGui',
        'PySide6.QtSvg',
        'PySide6.QtXml',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'tkinter', 'matplotlib', 'numpy', 'pandas',
        'scipy', 'PIL', 'cv2', 'PyQt5', 'PyQt6',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='InventarioJH',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,                      # Sin ventana de consola
    icon='assets/icon.ico',             # Ícono del .exe
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='InventarioJH',
)
