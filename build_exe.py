"""
StreamVortex Executable Compiler (PyInstaller).
Builds a standalone, trustworthy Windows executable: StreamVortex.exe
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
        "--hidden-import", "ttkbootstrap",
        "--hidden-import", "rich",
        "--hidden-import", "yt_dlp",
        "--hidden-import", "playwright",
        "--hidden-import", "winotify",
        "--hidden-import", "pyperclip",
        "--collect-all", "ttkbootstrap",
        "--collect-all", "yt_dlp_plugins",
        "--collect-all", "ytdlp_smartstream",
        str(main_file)
    ]

    print("[Build] Executing PyInstaller compilation...")
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
