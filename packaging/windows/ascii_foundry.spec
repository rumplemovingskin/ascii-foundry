# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path

from PyInstaller.utils.hooks import collect_all

block_cipher = None

root = Path(SPECPATH).resolve().parents[1]
src = root / "src"
icon = root / "build" / "assets" / "ascii-foundry.ico"

datas = []
binaries = []
hiddenimports = []

yt_dlp_datas, yt_dlp_binaries, yt_dlp_hiddenimports = collect_all("yt_dlp")
datas += yt_dlp_datas
binaries += yt_dlp_binaries
hiddenimports += yt_dlp_hiddenimports

for binary_name in ("ffmpeg.exe", "ffprobe.exe"):
    binary_path = root / "vendor" / "ffmpeg" / "bin" / binary_name
    if binary_path.exists():
        binaries.append((str(binary_path), "bin"))

a = Analysis(
    [str(root / "src" / "ascii_foundry" / "__main__.py")],
    pathex=[str(src)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
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
    name="ASCII Foundry",
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
    icon=str(icon) if icon.exists() else None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="ASCII Foundry",
)
