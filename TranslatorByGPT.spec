# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path

project = Path(SPECPATH)

analysis = Analysis(
    ['main.py'],
    pathex=[str(project)],
    binaries=[],
    datas=[('web', 'web'), ('assets/translator.ico', 'assets')],
    hiddenimports=['pystray._win32'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(analysis.pure)
exe = EXE(
    pyz,
    analysis.scripts,
    analysis.binaries,
    analysis.datas,
    [],
    name='TranslatorByGPT',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    icon=str(project / 'assets' / 'translator.ico'),
    version=str(project / 'assets' / 'version-info.txt'),
)
