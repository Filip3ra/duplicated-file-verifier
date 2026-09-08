# -*- mode: python ; coding: utf-8 -*-
"""Windows onedir bundle: GUI (dupcheck.exe) + CLI (dupcheck-cli.exe)."""

from pathlib import Path

from PyInstaller.utils.hooks import collect_submodules

SPEC_DIR = Path(SPECPATH).resolve()
ROOT = SPEC_DIR.parent
SRC = ROOT / "src"
ICON = SRC / "duplicate_verifier" / "assets" / "dupcheck-icon-png.ico"

datas = [
    (
        str(SRC / "duplicate_verifier" / "assets"),
        "duplicate_verifier/assets",
    )
]
hiddenimports = [
    *collect_submodules("PIL"),
    "PIL._tkinter_finder",
    "imagehash",
    "numpy",
    "send2trash",
    "tkinter",
    "tkinter.filedialog",
    "tkinter.messagebox",
    "tkinter.ttk",
    "tqdm",
    "multiprocessing",
]
excludes = ["pytest", "scipy"]
icon_path = str(ICON) if ICON.is_file() else None

gui_a = Analysis(
    [str(SPEC_DIR / "gui_entry.py")],
    pathex=[str(SRC)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    noarchive=False,
)
gui_pyz = PYZ(gui_a.pure)
gui_exe = EXE(
    gui_pyz,
    gui_a.scripts,
    [],
    exclude_binaries=True,
    name="dupcheck",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    icon=icon_path,
)

cli_a = Analysis(
    [str(SPEC_DIR / "cli_entry.py")],
    pathex=[str(SRC)],
    binaries=[],
    datas=[],
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    noarchive=False,
)
cli_pyz = PYZ(cli_a.pure)
cli_exe = EXE(
    cli_pyz,
    cli_a.scripts,
    [],
    exclude_binaries=True,
    name="dupcheck-cli",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    icon=icon_path,
)

coll = COLLECT(
    gui_exe,
    cli_exe,
    gui_a.binaries,
    gui_a.zipfiles,
    gui_a.datas,
    cli_a.binaries,
    cli_a.zipfiles,
    cli_a.datas,
    name="dupcheck",
    strip=False,
    upx=False,
    upx_exclude=[],
)
