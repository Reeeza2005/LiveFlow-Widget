# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path

PROJECT_DIR = Path(SPECPATH)
ICON_FILE = PROJECT_DIR / "AppDir" / "liveflow-widget.png"

a = Analysis(
    ['app/widget.py'],
    pathex=['.'],
    binaries=[],
    datas=[
        ('config', 'config'),
        ('VERSION', '.'),
        ('AppDir/liveflow-widget.png', '.'),
    ],
    hiddenimports=[
        'urllib',
        'urllib.request',
        'urllib.error',
        'pynput',
        'pynput.keyboard',
        'pynput.keyboard._xorg',
        'pynput.mouse',
        'pynput.mouse._xorg',
        'pynput._util.xorg',
    ],
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
    name='widget',
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
    icon=str(ICON_FILE),
)
