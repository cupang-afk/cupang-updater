# -*- mode: python ; coding: utf-8 -*-
import argparse

opt = argparse.ArgumentParser(add_help=False)
opt.add_argument("--extra-hidden-import", "--extrahiddenimport", dest="hidden_imports", default=[], action="append")
args, _ = opt.parse_known_args()

a = Analysis(
    ["..\\cli.py"],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=["pycurl"] + args.hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="cupang-updater-bin",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
