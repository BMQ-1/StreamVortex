# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all

datas = [('C:\\AntiGravity\\PC Tool\\yt-dlp extracting Library\\assets', 'assets')]
binaries = []
hiddenimports = ['customtkinter', 'ttkbootstrap', 'rich', 'yt_dlp', 'playwright', 'winotify', 'pyperclip', 'PIL', 'webview', 'pywebview', 'clr', 'pythonnet', 'questionary', 'prompt_toolkit', 'yt_dlp_plugins', 'yt_dlp_plugins.extractor', 'yt_dlp_plugins.postprocessor', 'yt_dlp_plugins.extractor.smartstream_common', 'yt_dlp_plugins.extractor.smartstream_fixup', 'yt_dlp_plugins.extractor.tiktok_resolver', 'yt_dlp_plugins.extractor.tiktok_smart', 'yt_dlp_plugins.extractor.universal_smart', 'yt_dlp_plugins.postprocessor.smartstream_fixup']
tmp_ret = collect_all('webview')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('questionary')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('prompt_toolkit')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('customtkinter')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('ttkbootstrap')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('yt_dlp_plugins')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('ytdlp_smartstream')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('PIL')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]


a = Analysis(
    ['C:\\AntiGravity\\PC Tool\\yt-dlp extracting Library\\main_entry.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
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
    name='StreamVortex',
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
    version='C:\\AntiGravity\\PC Tool\\yt-dlp extracting Library\\version_info.txt',
    icon=['C:\\AntiGravity\\PC Tool\\yt-dlp extracting Library\\StreamVortex.ico'],
)
