# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[('img', 'img')],
    hiddenimports=[],
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
    name='SmartImageShrink_TAGVERSION',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch='OS_ARCHITECTURE',
    codesign_identity='SECRET_DEVELOPER_ID',
    entitlements_file=None,
    icon=['img/icon.png'],
)
app = BUNDLE(
    exe,
    name='SmartImageShrink_TAGVERSION.app',
    icon='img/icon.png',
    bundle_identifier='com.presa.SmartImageShrink',
)
