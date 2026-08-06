# -*- mode: python ; coding: utf-8 -*-
#
# Linux build. Kept separate from HOI4ModMaker.spec rather than branching
# inside it, so the validated Windows build is never at risk from a change
# made for Linux. Two differences from the Windows spec:
#   * no icon - PyInstaller only embeds an icon into a Windows PE or a macOS
#     bundle, and the .ico path there uses a backslash that isn't a
#     separator on Linux anyway;
#   * upx off - upx is rarely installed on Linux build machines and its
#     absence is a hard error rather than a warning.

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[('assets', 'assets')],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['matplotlib', 'scipy', 'pandas', 'sv_ttk'],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='HOI4ModMaker',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='HOI4ModMaker',
)
