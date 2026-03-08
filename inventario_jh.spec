# -*- mode: python ; coding: utf-8 -*-

from PyInstaller.utils.hooks import collect_data_files, collect_submodules
import os

block_cipher = None

venv_site = r'.venv\Lib\site-packages'

a = Analysis(
    ['app\\main.py'],
    pathex=['.'],
    binaries=[],
    datas=[
        ('assets', 'assets'),
        ('app', 'app'),
        (os.path.join(venv_site, 'reportlab'), 'reportlab'),
        (os.path.join(venv_site, 'openpyxl'), 'openpyxl'),
    ],
    hiddenimports=[
        'sqlalchemy',
        'sqlalchemy.dialects.sqlite',
        'sqlalchemy.dialects.sqlite.pysqlite',
        'sqlalchemy.orm',
        'sqlalchemy.ext.declarative',
        *collect_submodules('reportlab'),
        *collect_submodules('openpyxl'),
        *collect_submodules('PIL'),
        'PIL',
        'PIL.Image',
        'PIL.ImageDraw',
        'PIL.ImageFont',
        'PySide6.QtCore',
        'PySide6.QtWidgets',
        'PySide6.QtGui',
        'PySide6.QtSvg',
        'PySide6.QtXml',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=['hook_reportlab.py'],
    excludes=[
        'tkinter', 'matplotlib', 'numpy', 'pandas',
        'scipy', 'cv2', 'PyQt5', 'PyQt6',
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
    console=False,
    icon='assets\\icon.ico',
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
