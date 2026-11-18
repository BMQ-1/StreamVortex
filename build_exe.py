"""
StreamVortex Executable Compiler (PyInstaller).
Builds a standalone, trustworthy Windows executable: StreamVortex.exe
Includes official app icon branding and full CustomTkinter bundling.
"""
import sys
import os
import shutil
import subprocess
from pathlib import Path


def build():
    root = Path(__file__).resolve().parent
    main_file = root / "main_entry.py"
    dist_dir = root / "dist"

    print("========================================================================")
    print("  Building StreamVortex.exe (Standalone Windows Executable)           ")
    print("========================================================================")

    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--noconfirm",
        "--name", "StreamVortex",
        "--onefile",
        "--clean",
        "--hidden-import", "customtkinter",
        "--hidden-import", "ttkbootstrap",
        "--hidden-import", "rich",
        "--hidden-import", "yt_dlp",
        "--hidden-import", "playwright",
        "--hidden-import", "winotify",
        "--hidden-import", "pyperclip",
        "--hidden-import", "PIL",
        "--hidden-import", "webview",
        "--hidden-import", "pywebview",
        "--hidden-import", "clr",
        "--hidden-import", "pythonnet",
        "--hidden-import", "questionary",
        "--hidden-import", "prompt_toolkit",
        "--hidden-import", "yt_dlp_plugins",
        "--hidden-import", "yt_dlp_plugins.extractor",
        "--hidden-import", "yt_dlp_plugins.postprocessor",
        "--hidden-import", "yt_dlp_plugins.extractor.smartstream_common",
        "--hidden-import", "yt_dlp_plugins.extractor.smartstream_fixup",
        "--hidden-import", "yt_dlp_plugins.extractor.tiktok_resolver",
        "--hidden-import", "yt_dlp_plugins.extractor.tiktok_smart",
        "--hidden-import", "yt_dlp_plugins.extractor.universal_smart",
        "--hidden-import", "yt_dlp_plugins.postprocessor.smartstream_fixup",
        "--collect-all", "webview",
        "--collect-all", "questionary",
        "--collect-all", "prompt_toolkit",
        "--collect-all", "customtkinter",
        "--collect-all", "ttkbootstrap",
        "--collect-all", "yt_dlp_plugins",
        "--collect-all", "ytdlp_smartstream",
        "--collect-all", "PIL",
    ]

    # Add official icon (relative path keeps generated StreamVortex.spec portable)
    if (root / "StreamVortex.ico").exists():
        cmd.extend(["--icon", "StreamVortex.ico"])

    # Add Windows version info resource
    if (root / "version_info.txt").exists():
        cmd.extend(["--version-file", "version_info.txt"])

    # Add assets directory
    if (root / "assets").exists():
        cmd.extend(["--add-data", "assets;assets"])

    # Optional local conf
    if (root / "yt-dlp.conf").exists():
        cmd.extend(["--add-data", "yt-dlp.conf;."])

    cmd.append("main_entry.py")

    print("[Build] Executing PyInstaller compilation with icon and assets...")
    res = subprocess.run(cmd, cwd=str(root))
    if res.returncode == 0:
        exe_path = dist_dir / "StreamVortex.exe"
        if exe_path.exists():
            target_exe = root / "StreamVortex.exe"
            shutil.copy2(exe_path, target_exe)
            print("\n========================================================================")
            print("[+] Build SUCCESSFUL!")
            print(f"[+] Standalone Executable created: {target_exe}")
            print(f"[+] Size: {target_exe.stat().st_size / 1024 / 1024:.2f} MB")
            print("========================================================================\n")
            return True

    print("[-] Build failed with return code:", res.returncode)
    return False


if __name__ == "__main__":
    build()
