# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files, collect_submodules


PROJECT_ROOT = Path.cwd().resolve()
ICON_PATH = PROJECT_ROOT / "app" / "Source" / "Icons" / "logos" / "TuleVentaIcon.ico"

datas = []
datas += collect_data_files("plotly")
datas += collect_data_files("reportlab")
datas += [
    (str(PROJECT_ROOT / "app" / "Source"), "app/Source"),
    (str(PROJECT_ROOT / "datos"), "datos"),
    (str(PROJECT_ROOT / "licencia_publica.pem"), "."),
]

hiddenimports = collect_submodules("plotly") + [
    "PySide6.QtPdf",
    "PySide6.QtPrintSupport",
    "PySide6.QtWebEngineCore",
    "PySide6.QtWebEngineWidgets",
]


a = Analysis(
    [str(PROJECT_ROOT / "inicio.py")],
    pathex=[str(PROJECT_ROOT)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[str(PROJECT_ROOT / "pyinstaller_runtime_hooks" / "pyi_rth_safe_inspect_getsource.py")],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="TuleVenta",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(ICON_PATH),
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="TuleVenta",
)