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
        "--collect-all", "customtkinter",
        "--collect-all", "ttkbootstrap",
        "--collect-all", "yt_dlp_plugins",
        "--collect-all", "ytdlp_smartstream",
        "--collect-all", "PIL",
    ]

    # Add official icon
    ico_file = root / "StreamVortex.ico"
    if ico_file.exists():
        cmd.extend(["--icon", str(ico_file)])

    # Add Windows version info resource
    version_file = root / "version_info.txt"
    if version_file.exists():
        cmd.extend(["--version-file", str(version_file)])

    # Add assets directory
    assets_dir = root / "assets"
    if assets_dir.exists():
        cmd.extend(["--add-data", f"{assets_dir};assets"])

    # Optional local conf
    conf_file = root / "yt-dlp.conf"
    if conf_file.exists():
        cmd.extend(["--add-data", f"{conf_file};."])

    cmd.append(str(main_file))

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
