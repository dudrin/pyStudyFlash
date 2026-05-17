# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path

from PyInstaller.utils.hooks import collect_submodules


project_dir = Path(SPECPATH).resolve()

datas = [
    (str(project_dir / "cursors"), "cursors"),
]

hiddenimports = [
    "win32timezone",
    "pyautogui",
    "pymsgbox",
    "pyscreeze",
    "pygetwindow",
    "mouseinfo",
    "pytweening",
]
hiddenimports += collect_submodules("pynput")


a = Analysis(
    ["pystudyflash.py"],
    pathex=[str(project_dir)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["tkinter", "matplotlib"],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="pyStudyFlash",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="pyStudyFlash",
)
