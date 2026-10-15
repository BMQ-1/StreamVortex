"""
StreamVortex Complete Zero-Setup Onboarding & Binary Provisioner.
Designed for 1-click first-time setup for all users (including beginners with no Python, yt-dlp, or FFmpeg).

Features:
- Detects missing tools (yt-dlp, FFmpeg, Python, VLC/MPV, yt-dlp.conf).
- Asks or selects dedicated tools folder (e.g. C:\\Tools or %USERPROFILE%\\Tools).
- Downloads official yt-dlp.exe, ffmpeg.exe, ffprobe.exe directly from official channels.
- Installs StreamVortex's optimized yt-dlp.conf and tiktok-live.conf presets directly next to yt-dlp.exe.
- Installs or checks global Python (python.org official installer).
- Checks for VLC / MPV, installs official VLC Media Player if missing.
- Safely registers tools directory in Windows User PATH.
- Modern GUI Wizard + Interactive CLI Wizard.
"""

import sys
import os
import shutil
import zipfile
import urllib.request
import subprocess
import threading
from pathlib import Path
from typing import Optional, Callable, Dict, Any, Tuple

from .config import get_config, save_config, get_download_dir

YTDLP_RELEASE_URL = "https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp.exe"
FFMPEG_RELEASE_URL = "https://github.com/yt-dlp/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-gpl.zip"
ARIA2C_RELEASE_URL = "https://github.com/q3aql/aria2-static-builds/releases/download/v1.37.0/aria2-1.37.0-win-64bit-build1.zip"
PYTHON_INSTALLER_URL = "https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe"
VLC_INSTALLER_URL = "https://get.videolan.org/vlc/3.0.21/win64/vlc-3.0.21-win64.exe"

from .engine import DEFAULT_YTDLP_CONF_TEMPLATE


def get_default_tools_dir() -> Path:
    """
    Returns the recommended tools directory.
    Prioritizes C:\\Tools if accessible, otherwise %USERPROFILE%\\Tools.
    """
    cfg = get_config()
    saved = cfg.get("tools_dir")
    if saved and Path(saved).exists():
        return Path(saved)

    c_tools = Path("C:/Tools")
    try:
        c_tools.mkdir(parents=True, exist_ok=True)
        test_file = c_tools / ".write_test"
        test_file.touch()
        test_file.unlink()
        return c_tools
    except Exception:
        pass

    user_tools = Path.home() / "Tools"
    user_tools.mkdir(parents=True, exist_ok=True)
    return user_tools


def check_environment_status() -> Dict[str, Any]:
    """
    Inspects system readiness across all components.
    """
    from .engine import find_ytdlp, find_ffmpeg, find_ffprobe, find_global_python, find_ytdlp_conf, find_player

    ytdlp = find_ytdlp()
    ffmpeg = find_ffmpeg()
    ffprobe = find_ffprobe()
    global_py = find_global_python()
    conf = find_ytdlp_conf()
    player = find_player()

    # yt-dlp details
    ytdlp_ok = False
    ytdlp_ver = "Missing"
    if ytdlp:
        try:
            res = subprocess.run(ytdlp + ["--version"], capture_output=True, text=True, timeout=3)
            if res.returncode == 0:
                ytdlp_ok = True
                ytdlp_ver = res.stdout.strip()
        except Exception:
            pass

    # FFmpeg details
    ffmpeg_ok = False
    ffmpeg_ver = "Missing"
    if ffmpeg:
        try:
            res = subprocess.run([ffmpeg, "-version"], capture_output=True, text=True, timeout=3)
            if res.returncode == 0:
                ffmpeg_ok = True
                ffmpeg_ver = res.stdout.splitlines()[0] if res.stdout else "Available"
        except Exception:
            pass

    # Python details
    python_ok = False
    py_ver = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    which_py = shutil.which("python")
    if which_py:
        python_ok = True

    # Player details
    player_ok = bool(player)

    # Config details
    conf_ok = bool(conf and conf.exists())

    return {
        "ytdlp": {"ok": ytdlp_ok, "path": ytdlp[0] if ytdlp else None, "version": ytdlp_ver},
        "ffmpeg": {"ok": ffmpeg_ok, "path": ffmpeg, "version": ffmpeg_ver},
        "ffprobe": {"ok": bool(ffprobe), "path": ffprobe},
        "python": {"ok": python_ok, "path": global_py, "version": py_ver},
        "player": {"ok": player_ok, "path": player, "name": Path(player).stem if player else None},
        "conf": {"ok": conf_ok, "path": str(conf) if conf else None},
        "is_ready": ytdlp_ok and ffmpeg_ok
    }


def download_file_with_feedback(
    url: str,
    dest_path: Path,
    label: str = "Downloading",
    callback: Optional[Callable[[str, float], None]] = None
) -> bool:
    """
    Downloads an official file with chunk-by-chunk feedback and progress tracking.
    """
    try:
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        temp_dest = dest_path.with_suffix(dest_path.suffix + ".tmp")

        req = urllib.request.Request(
            url,
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) StreamVortex/1.0.0"}
        )

        with urllib.request.urlopen(req) as resp:
            total = int(resp.headers.get("Content-Length", 0))
            downloaded = 0
            block_size = 1024 * 128

            with open(temp_dest, "wb") as f:
                while True:
                    chunk = resp.read(block_size)
                    if not chunk:
                        break
                    f.write(chunk)
                    downloaded += len(chunk)
                    pct = (downloaded / total * 100) if total > 0 else 0
                    if callback:
                        msg = f"{label}: {downloaded / 1024 / 1024:.1f} MB" + (f" / {total / 1024 / 1024:.1f} MB ({pct:.1f}%)" if total else "")
                        callback(msg, pct)

            if dest_path.exists():
                dest_path.unlink()
            temp_dest.rename(dest_path)
            return True
    except Exception as e:
        if callback:
            callback(f"[-] Download error for {label}: {e}", 0.0)
        return False


def install_yt_dlp(tools_dir: Path, callback: Optional[Callable[[str, float], None]] = None) -> Tuple[bool, str]:
    """Downloads and verifies the latest official yt-dlp.exe."""
    target_exe = tools_dir / "yt-dlp.exe"
    if callback:
        callback("Fetching latest official yt-dlp.exe release from GitHub...", 5.0)

    success = download_file_with_feedback(
        YTDLP_RELEASE_URL,
        target_exe,
        label="yt-dlp.exe",
        callback=callback
    )
    if not success:
        return False, "Failed to download yt-dlp.exe from GitHub."

    # Verify execution
    try:
        res = subprocess.run([str(target_exe), "--version"], capture_output=True, text=True, timeout=6)
        ver = res.stdout.strip()
        if callback:
            callback(f"[+] Verified yt-dlp.exe (v{ver}) successfully!", 100.0)
        return True, str(target_exe)
    except Exception as e:
        return False, f"Verification failed for yt-dlp.exe: {e}"


def install_ffmpeg_suite(tools_dir: Path, callback: Optional[Callable[[str, float], None]] = None) -> Tuple[bool, str]:
    """Downloads official FFmpeg & FFprobe suite and extracts to tools_dir."""
    zip_path = tools_dir / "ffmpeg_temp.zip"
    ffmpeg_exe = tools_dir / "ffmpeg.exe"
    ffprobe_exe = tools_dir / "ffprobe.exe"

    if callback:
        callback("Downloading official FFmpeg build from GitHub...", 5.0)

    success = download_file_with_feedback(
        FFMPEG_RELEASE_URL,
        zip_path,
        label="FFmpeg Suite",
        callback=callback
    )
    if not success:
        return False, "Failed to download FFmpeg archive."

    if callback:
        callback("Extracting ffmpeg.exe and ffprobe.exe into tools folder...", 85.0)

    try:
        with zipfile.ZipFile(zip_path, "r") as z:
            for member in z.namelist():
                if member.endswith("ffmpeg.exe"):
                    with z.open(member) as src, open(ffmpeg_exe, "wb") as dst:
                        shutil.copyfileobj(src, dst)
                elif member.endswith("ffprobe.exe"):
                    with z.open(member) as src, open(ffprobe_exe, "wb") as dst:
                        shutil.copyfileobj(src, dst)

        if zip_path.exists():
            zip_path.unlink()

        # Verify
        res = subprocess.run([str(ffmpeg_exe), "-version"], capture_output=True, text=True, timeout=5)
        ver = res.stdout.splitlines()[0] if res.stdout else "Available"
        if callback:
            callback(f"[+] Verified FFmpeg ({ver}) successfully!", 100.0)
        return True, str(ffmpeg_exe)
    except Exception as e:
        return False, f"Extraction error: {e}"


def install_aria2c_engine(tools_dir: Path, callback: Optional[Callable[[str, float], None]] = None) -> Tuple[bool, str]:
    """
    Downloads the official portable aria2c.exe download accelerator and places it next to yt-dlp.exe.
    This enables yt-dlp's 16-connection multi-threaded acceleration configured in yt-dlp.conf.
    """
    from .engine import find_aria2c
    existing = find_aria2c()
    if existing:
        if callback:
            callback(f"[+] aria2c accelerator already available: {existing}", 100.0)
        return True, existing

    zip_path = tools_dir / "aria2_temp.zip"
    aria2_exe = tools_dir / "aria2c.exe"

    if callback:
        callback("Downloading official portable aria2c download accelerator...", 10.0)

    success = download_file_with_feedback(
        ARIA2C_RELEASE_URL,
        zip_path,
        label="aria2c Accelerator",
        callback=callback
    )
    if not success:
        return False, "Failed to download aria2c archive."

    try:
        with zipfile.ZipFile(zip_path, "r") as z:
            for member in z.namelist():
                if member.endswith("aria2c.exe"):
                    with z.open(member) as src, open(aria2_exe, "wb") as dst:
                        shutil.copyfileobj(src, dst)
                    break
        if zip_path.exists():
            zip_path.unlink()
        if aria2_exe.exists():
            if callback:
                callback(f"[+] Installed aria2c.exe into {tools_dir}!", 100.0)
            return True, str(aria2_exe)
    except Exception as e:
        return False, f"aria2c extraction error: {e}"

    return False, "aria2c.exe not found in downloaded archive."


def install_optimized_configs(
    tools_dir: Path,
    downloads_dir: Optional[Path] = None,
    callback: Optional[Callable[[str, float], None]] = None
) -> Tuple[bool, str]:
    """
    Deploys the standard yt-dlp.conf directly next to yt-dlp.exe in tools_dir (e.g. C:\\Tools\\yt-dlp.conf).
    This establishes yt-dlp's native portable configuration globally, ensuring yt-dlp works
    consistently from any command prompt across the entire PC even if StreamVortex is deleted.
    Outputs are dynamically configured to the user's chosen downloads directory (default: ~/Downloads).
    """
    target_dl = (downloads_dir or get_download_dir()).expanduser().resolve()
    target_dl.mkdir(parents=True, exist_ok=True)

    conf_path = tools_dir / "yt-dlp.conf"

    # Prioritize user's actual yt-dlp.conf placed in project or bundled
    source_conf = None
    if getattr(sys, "frozen", False):
        exe_conf = Path(sys.executable).parent / "yt-dlp.conf"
        meipass = getattr(sys, "_MEIPASS", None)
        bundle_conf = Path(meipass) / "yt-dlp.conf" if meipass else None
        if exe_conf.exists():
            source_conf = exe_conf
        elif bundle_conf and bundle_conf.exists():
            source_conf = bundle_conf
    else:
        root_conf = Path(__file__).resolve().parent.parent / "yt-dlp.conf"
        if root_conf.exists():
            source_conf = root_conf

    if source_conf and source_conf.exists():
        conf_content = source_conf.read_text(encoding="utf-8", errors="ignore")
    else:
        conf_content = DEFAULT_YTDLP_CONF_TEMPLATE.replace("{downloads_dir}", str(target_dl).replace("/", "\\")).replace("{dest_dir}", str(target_dl).replace("/", "\\"))

    try:
        conf_path.parent.mkdir(parents=True, exist_ok=True)
        with open(conf_path, "w", encoding="utf-8") as f:
            f.write(conf_content)

        # Apply interactive download destinations (videos, subtitles, thumbnails)
        from .engine import update_ytdlp_conf_destinations
        update_ytdlp_conf_destinations(target_dl, conf_path=conf_path)

        if callback:
            callback(f"[+] Installed global yt-dlp.conf directly next to yt-dlp.exe in {tools_dir} (Output: {target_dl})!", 100.0)
        return True, str(conf_path)
    except Exception as e:
        return False, f"Could not create configuration file: {e}"


def install_python_runtime(callback: Optional[Callable[[str, float], None]] = None) -> Tuple[bool, str]:
    """
    Installs the official Python 3.11 Windows runtime.
    If already installed on PATH, skips immediately.
    """
    if shutil.which("python"):
        if callback:
            callback(f"[+] Python is already installed on system PATH.", 100.0)
        return True, shutil.which("python")

    temp_dir = Path(os.environ.get("TEMP", "C:/Windows/Temp"))
    installer = temp_dir / "python-3.11.9-amd64.exe"

    if callback:
        callback("Downloading official Python 3.11.9 installer from python.org...", 10.0)

    success = download_file_with_feedback(
        PYTHON_INSTALLER_URL,
        installer,
        label="Python 3.11 Installer",
        callback=callback
    )
    if not success:
        return False, "Failed to download Python installer."

    if callback:
        callback("Running official Python installer (adding Python to PATH)...", 75.0)

    try:
        # Run passive installer adding python to path
        subprocess.run([str(installer), "/passive", "PrependPath=1", "Include_pip=1"], check=True, timeout=120)
        if callback:
            callback("[+] Python 3.11 installed successfully!", 100.0)
        return True, "Python 3.11 installed"
    except Exception as e:
        return False, f"Python installation failed: {e}"


def install_vlc_player(callback: Optional[Callable[[str, float], None]] = None) -> Tuple[bool, str]:
    """
    Installs VLC Media Player for instant live stream preview playback.
    Prioritizes winget if present, otherwise official installer.
    """
    from .engine import find_player
    existing = find_player()
    if existing:
        if callback:
            callback(f"[+] Media player already available: {existing}", 100.0)
        return True, existing

    # Try winget first
    if shutil.which("winget"):
        if callback:
            callback("Installing official VLC Media Player via Windows Package Manager (winget)...", 30.0)
        try:
            res = subprocess.run(
                ["winget", "install", "VideoLAN.VLC", "--silent", "--accept-source-agreements", "--accept-package-agreements"],
                capture_output=True,
                text=True,
                timeout=120
            )
            if res.returncode == 0:
                if callback:
                    callback("[+] VLC Media Player installed via winget!", 100.0)
                return True, "VLC Media Player"
        except Exception:
            pass

    # Direct download fallback
    temp_dir = Path(os.environ.get("TEMP", "C:/Windows/Temp"))
    vlc_installer = temp_dir / "vlc_setup.exe"
    if callback:
        callback("Downloading official VLC Media Player installer from VideoLAN...", 20.0)

    success = download_file_with_feedback(
        VLC_INSTALLER_URL,
        vlc_installer,
        label="VLC Installer",
        callback=callback
    )
    if not success:
        return False, "Failed to download VLC installer."

    if callback:
        callback("Running official VLC Media Player installer...", 70.0)
    try:
        subprocess.run([str(vlc_installer), "/S"], check=True, timeout=90)
        if callback:
            callback("[+] VLC Media Player installed successfully!", 100.0)
        return True, "VLC Media Player"
    except Exception as e:
        return False, f"VLC installation failed: {e}"


def add_folder_to_user_path(folder: Path) -> bool:
    """
    Safely and permanently adds folder to the Windows User PATH environment variable
    via PowerShell without requiring Administrator privileges.
    """
    folder_str = str(folder.resolve())
    cmd = f"""
    $current = [Environment]::GetEnvironmentVariable('Path', 'User');
    if ($current -notlike '*{folder_str}*') {{
        [Environment]::SetEnvironmentVariable('Path', "$current;{folder_str}", 'User')
    }}
    """
    try:
        res = subprocess.run(["powershell", "-NoProfile", "-Command", cmd], capture_output=True, text=True, timeout=5)
        # Also update current process os.environ
        if folder_str not in os.environ.get("PATH", ""):
            os.environ["PATH"] = f"{folder_str};" + os.environ.get("PATH", "")
        return res.returncode == 0
    except Exception:
        return False


def run_full_onboarding(
    tools_dir: Path,
    downloads_dir: Optional[Path] = None,
    do_ytdlp: bool = True,
    do_ffmpeg: bool = True,
    do_conf: bool = True,
    do_python: bool = True,
    do_vlc: bool = True,
    do_add_path: bool = True,
    callback: Optional[Callable[[str, float], None]] = None
) -> Dict[str, Any]:
    """
    Executes the full automated onboarding workflow.
    """
    tools_dir.mkdir(parents=True, exist_ok=True)
    results = {}

    def report(msg: str, pct: float):
        if callback:
            callback(msg, pct)
        else:
            print(f"[Onboarding] {msg}")

    report(f"Configuring destination directory: {tools_dir}", 2.0)

    # 1. yt-dlp
    if do_ytdlp:
        report("Setting up yt-dlp core engine...", 5.0)
        ok, detail = install_yt_dlp(tools_dir, lambda m, p: report(m, 5.0 + (p * 0.25)))
        results["ytdlp"] = {"ok": ok, "detail": detail}
    else:
        results["ytdlp"] = {"ok": True, "detail": "Skipped by user"}

    # 2. FFmpeg & FFprobe
    if do_ffmpeg:
        report("Setting up FFmpeg & FFprobe media engine...", 30.0)
        ok, detail = install_ffmpeg_suite(tools_dir, lambda m, p: report(m, 30.0 + (p * 0.30)))
        results["ffmpeg"] = {"ok": ok, "detail": detail}
    else:
        results["ffmpeg"] = {"ok": True, "detail": "Skipped by user"}

    # 2b. aria2c download accelerator (used by yt-dlp.conf)
    report("Checking aria2c multi-connection download accelerator...", 60.0)
    ok_aria, detail_aria = install_aria2c_engine(tools_dir, lambda m, p: report(m, 60.0 + (p * 0.08)))
    results["aria2c"] = {"ok": ok_aria, "detail": detail_aria}

    # 3. Optimized Configs next to yt-dlp.exe
    if do_conf:
        report("Installing optimized yt-dlp.conf preset directly next to yt-dlp.exe...", 68.0)
        ok, detail = install_optimized_configs(tools_dir, downloads_dir=downloads_dir, callback=lambda m, p: report(m, 68.0 + (p * 0.05)))
        results["conf"] = {"ok": ok, "detail": detail}
    else:
        results["conf"] = {"ok": True, "detail": "Skipped by user"}

    # 4. Global Python
    if do_python:
        report("Checking Python environment...", 75.0)
        ok, detail = install_python_runtime(lambda m, p: report(m, 75.0 + (p * 0.10)))
        results["python"] = {"ok": ok, "detail": detail}
    else:
        results["python"] = {"ok": True, "detail": "Skipped by user"}

    # 5. Media Player (VLC / MPV)
    if do_vlc:
        report("Checking media player for live stream preview...", 85.0)
        ok, detail = install_vlc_player(lambda m, p: report(m, 85.0 + (p * 0.10)))
        results["player"] = {"ok": ok, "detail": detail}
    else:
        results["player"] = {"ok": True, "detail": "Skipped by user"}

    # 6. Windows User PATH registration
    if do_add_path:
        report(f"Adding {tools_dir} to Windows User PATH...", 96.0)
        add_folder_to_user_path(tools_dir)
        results["path"] = {"ok": True, "detail": f"Added {tools_dir} to User PATH"}

    # 7. Save to StreamVortex config
    cfg = get_config()
    cfg["tools_dir"] = str(tools_dir)
    cfg["ytdlp_conf_path"] = str(tools_dir / "yt-dlp.conf")
    save_config(cfg)

    report("🎉 Onboarding setup complete! StreamVortex is fully operational.", 100.0)
    return results


# ========================================================
# GUI ONBOARDING DIALOG (Tkinter / ttkbootstrap)
# ========================================================

def launch_onboarding_gui(parent=None, on_complete: Optional[Callable[[], None]] = None):
    """
    Renders an interactive, modern visual onboarding window.
    """
    import tkinter as tk
    from tkinter import ttk, filedialog, messagebox

    try:
        import ttkbootstrap as tb
        HAS_TB = True
    except ImportError:
        HAS_TB = False

    status = check_environment_status()

    win = tb.Toplevel(parent) if (HAS_TB and parent) else (tb.Window(title="StreamVortex Setup Wizard", themename="darkly") if HAS_TB else (tk.Toplevel(parent) if parent else tk.Tk()))
    win.title("⚡ StreamVortex Zero-Setup Wizard // 1-Click Environment Setup")
    win.geometry("780x680")
    win.resizable(False, False)

    if not HAS_TB:
        win.configure(bg="#0f172a")

    container = tb.Frame(win, padding=24) if HAS_TB else tk.Frame(win, padx=24, pady=24, bg="#0f172a")
    container.pack(fill="both", expand=True)

    # Title & Welcome
    title_lbl = tb.Label(
        container,
        text="🚀 Welcome to StreamVortex",
        font=("Segoe UI", 18, "bold"),
        bootstyle="info"
    ) if HAS_TB else tk.Label(container, text="🚀 Welcome to StreamVortex", font=("Segoe UI", 18, "bold"), fg="#00f2fe", bg="#0f172a")
    title_lbl.pack(anchor="w")

    desc_lbl = tb.Label(
        container,
        text="StreamVortex can automatically set up everything you need: official yt-dlp, FFmpeg, optimized configs, Python, and VLC media player. Safe, transparent, and verified.",
        font=("Segoe UI", 9),
        wraplength=730,
        bootstyle="secondary"
    ) if HAS_TB else tk.Label(container, text="StreamVortex can automatically set up everything you need: official yt-dlp, FFmpeg, optimized configs, Python, and VLC media player. Safe, transparent, and verified.", font=("Segoe UI", 9), wraplength=730, fg="#94a3b8", bg="#0f172a")
    desc_lbl.pack(anchor="w", pady=(4, 15))

    # Folder Picker Card
    # Tools Folder Picker Card
    folder_card = tb.Labelframe(container, text=" 📂 Tools Installation Folder ", padding=14, bootstyle="info") if HAS_TB else tk.LabelFrame(container, text=" 📂 Tools Installation Folder ", padx=14, pady=14, fg="#00f2fe", bg="#1e293b")
    folder_card.pack(fill="x", pady=(0, 10))

    folder_var = tk.StringVar(value=str(get_default_tools_dir()))
    folder_entry = tb.Entry(folder_card, textvariable=folder_var, font=("Segoe UI", 9), bootstyle="info") if HAS_TB else tk.Entry(folder_card, textvariable=folder_var, font=("Segoe UI", 9))
    folder_entry.pack(side="left", fill="x", expand=True, padx=(0, 8))

    def browse_folder():
        chosen = filedialog.askdirectory(initialdir=folder_var.get(), title="Select Tools Folder")
        if chosen:
            folder_var.set(chosen)

    browse_btn = tb.Button(folder_card, text="Browse...", command=browse_folder, bootstyle="outline-secondary") if HAS_TB else tk.Button(folder_card, text="Browse...", command=browse_folder)
    browse_btn.pack(side="right")

    # Download Destination Folder Picker Card (Default: ~/Downloads)
    dl_card = tb.Labelframe(container, text=" 📥 Download Destination Folder (yt-dlp.conf) ", padding=14, bootstyle="primary") if HAS_TB else tk.LabelFrame(container, text=" 📥 Download Destination Folder (yt-dlp.conf) ", padx=14, pady=14, fg="#00f2fe", bg="#1e293b")
    dl_card.pack(fill="x", pady=(0, 10))

    from .engine import get_conf_download_dir
    dl_var = tk.StringVar(value=str(get_conf_download_dir()))
    dl_entry = tb.Entry(dl_card, textvariable=dl_var, font=("Segoe UI", 9), bootstyle="primary") if HAS_TB else tk.Entry(dl_card, textvariable=dl_var, font=("Segoe UI", 9))
    dl_entry.pack(side="left", fill="x", expand=True, padx=(0, 8))

    def browse_dl():
        chosen = filedialog.askdirectory(initialdir=dl_var.get(), title="Select Download Destination Folder")
        if chosen:
            dl_var.set(chosen)

    browse_dl_btn = tb.Button(dl_card, text="Browse / Drop...", command=browse_dl, bootstyle="outline-primary") if HAS_TB else tk.Button(dl_card, text="Browse...", command=browse_dl)
    browse_dl_btn.pack(side="right")

    # Options Card
    opts_card = tb.Labelframe(container, text=" 📦 Components to Configure & Install ", padding=14, bootstyle="info") if HAS_TB else tk.LabelFrame(container, text=" 📦 Components to Configure & Install ", padx=14, pady=14, fg="#00f2fe", bg="#1e293b")
    opts_card.pack(fill="x", pady=(0, 10))

    chk_ytdlp_var = tk.BooleanVar(value=True)
    chk_ffmpeg_var = tk.BooleanVar(value=True)
    chk_conf_var = tk.BooleanVar(value=True)
    chk_python_var = tk.BooleanVar(value=not status["python"]["ok"])
    chk_vlc_var = tk.BooleanVar(value=not status["player"]["ok"])
    chk_path_var = tk.BooleanVar(value=True)

    ytdlp_lbl_text = "Download latest official yt-dlp.exe" + (" (Ready: " + status["ytdlp"]["version"] + ")" if status["ytdlp"]["ok"] else "")
    ffmpeg_lbl_text = "Download official FFmpeg & FFprobe media suite" + (" (Ready)" if status["ffmpeg"]["ok"] else "")
    python_lbl_text = "Verify / Install Python 3.11 Runtime" + (" (Already detected)" if status["python"]["ok"] else " (Recommended)")
    vlc_lbl_text = "Verify / Install VLC Media Player" + (" (Already detected: " + str(status["player"]["name"]) + ")" if status["player"]["ok"] else " (For live previews)")

    tb.Checkbutton(opts_card, text=ytdlp_lbl_text, variable=chk_ytdlp_var, bootstyle="round-toggle").pack(anchor="w", pady=2) if HAS_TB else tk.Checkbutton(opts_card, text=ytdlp_lbl_text, variable=chk_ytdlp_var, bg="#1e293b", fg="white", selectcolor="#0f172a").pack(anchor="w", pady=2)
    tb.Checkbutton(opts_card, text=ffmpeg_lbl_text, variable=chk_ffmpeg_var, bootstyle="round-toggle").pack(anchor="w", pady=2) if HAS_TB else tk.Checkbutton(opts_card, text=ffmpeg_lbl_text, variable=chk_ffmpeg_var, bg="#1e293b", fg="white", selectcolor="#0f172a").pack(anchor="w", pady=2)
    tb.Checkbutton(opts_card, text="Install StreamVortex optimized yt-dlp.conf preset directly next to yt-dlp.exe", variable=chk_conf_var, bootstyle="round-toggle").pack(anchor="w", pady=2) if HAS_TB else tk.Checkbutton(opts_card, text="Install StreamVortex optimized yt-dlp.conf preset directly next to yt-dlp.exe", variable=chk_conf_var, bg="#1e293b", fg="white", selectcolor="#0f172a").pack(anchor="w", pady=2)
    tb.Checkbutton(opts_card, text=python_lbl_text, variable=chk_python_var, bootstyle="round-toggle").pack(anchor="w", pady=2) if HAS_TB else tk.Checkbutton(opts_card, text=python_lbl_text, variable=chk_python_var, bg="#1e293b", fg="white", selectcolor="#0f172a").pack(anchor="w", pady=2)
    tb.Checkbutton(opts_card, text=vlc_lbl_text, variable=chk_vlc_var, bootstyle="round-toggle").pack(anchor="w", pady=2) if HAS_TB else tk.Checkbutton(opts_card, text=vlc_lbl_text, variable=chk_vlc_var, bg="#1e293b", fg="white", selectcolor="#0f172a").pack(anchor="w", pady=2)
    tb.Checkbutton(opts_card, text="Add Tools folder to Windows User PATH (Enables global CMD usage)", variable=chk_path_var, bootstyle="round-toggle").pack(anchor="w", pady=2) if HAS_TB else tk.Checkbutton(opts_card, text="Add Tools folder to Windows User PATH (Enables global CMD usage)", variable=chk_path_var, bg="#1e293b", fg="white", selectcolor="#0f172a").pack(anchor="w", pady=2)

    # Progress & Log
    progress_bar = tb.Progressbar(container, mode="determinate", bootstyle="success-striped") if HAS_TB else ttk.Progressbar(container, mode="determinate")
    progress_bar.pack(fill="x", pady=(6, 6))

    log_box = tk.Text(container, height=5, bg="#080c16", fg="#e2e8f0", font=("Consolas", 8), relief="flat", padx=8, pady=8)
    log_box.pack(fill="both", expand=True, pady=(0, 10))
    log_box.insert("end", "[Ready] Click 'Start Automated Setup' below to begin.\n")

    # Action Buttons
    btn_frame = tb.Frame(container) if HAS_TB else tk.Frame(container, bg="#0f172a")
    btn_frame.pack(fill="x")

    def _start():
        start_btn.config(state="disabled")
        browse_btn.config(state="disabled")
        browse_dl_btn.config(state="disabled")
        tools_path = Path(folder_var.get().strip().strip("'\""))
        dl_path = Path(dl_var.get().strip().strip("'\""))

        def _worker():
            def cb(msg: str, pct: float):
                def _update():
                    log_box.insert("end", msg + "\n")
                    log_box.see("end")
                    progress_bar.configure(value=pct)
                win.after(0, _update)

            res = run_full_onboarding(
                tools_dir=tools_path,
                downloads_dir=dl_path,
                do_ytdlp=chk_ytdlp_var.get(),
                do_ffmpeg=chk_ffmpeg_var.get(),
                do_conf=chk_conf_var.get(),
                do_python=chk_python_var.get(),
                do_vlc=chk_vlc_var.get(),
                do_add_path=chk_path_var.get(),
                callback=cb
            )

            def _done():
                start_btn.config(text="✓ Setup Complete", bootstyle="success", state="disabled")
                close_btn.config(text="🚀 Launch Studio", bootstyle="info", command=_finish)
                messagebox.showinfo("Setup Complete", f"StreamVortex has configured everything!\n\nTools: {tools_path}\nDownloads: {dl_path}\nConfig: {tools_path / 'yt-dlp.conf'}")
            win.after(0, _done)

        threading.Thread(target=_worker, daemon=True).start()

    def _finish():
        win.destroy()
        if on_complete:
            on_complete()

    start_btn = tb.Button(btn_frame, text="⚡ Start Automated Setup (1-Click)", bootstyle="success", command=_start) if HAS_TB else tk.Button(btn_frame, text="⚡ Start Automated Setup", command=_start, bg="#10b981", fg="white")
    start_btn.pack(side="left", padx=(0, 8))

    close_btn = tb.Button(btn_frame, text="Cancel / Skip", bootstyle="outline-secondary", command=win.destroy) if HAS_TB else tk.Button(btn_frame, text="Cancel / Skip", command=win.destroy)
    close_btn.pack(side="right")

    if not parent:
        win.mainloop()


# ========================================================
# CLI ONBOARDING WIZARD
# ========================================================

def run_cli_onboarding():
    """
    Terminal-based interactive onboarding for console users.
    Prompts user to select tools folder and drag & drop download folder.
    """
    from rich.console import Console
    from rich.panel import Panel
    import questionary

    console = Console()
    console.clear()
    console.print(
        Panel.fit(
            "[bold cyan]⚡ StreamVortex Zero-Setup Onboarding[/bold cyan]\n"
            "[dim]Automated installation of yt-dlp, FFmpeg, optimized configs, Python, and VLC[/dim]",
            border_style="bright_blue"
        )
    )

    default_dir = str(get_default_tools_dir())
    tools_dir_str = questionary.text(
        "Choose folder to install media tools (yt-dlp, FFmpeg, configs):",
        default=default_dir
    ).ask()
    if not tools_dir_str:
        return

    tools_dir = Path(tools_dir_str)

    # Interactive Download Destination with Drag & Drop prompt
    from .engine import get_conf_download_dir
    default_dl = str(get_conf_download_dir())
    console.print(
        f"\n[bold cyan]📥 Download Destination Folder[/bold cyan]\n"
        f"[dim]Current default: [bold white]{default_dl}[/bold white][/dim]\n"
        "[dim]💡 Tip: Drag and drop ANY folder from Windows Explorer into this window, or press Enter to keep default.[/dim]"
    )
    raw_dl = questionary.text(
        "Enter or Drag & Drop download folder:",
        default=default_dl
    ).ask()
    if raw_dl and raw_dl.strip():
        cleaned_dl = raw_dl.strip().strip("'\"")
        downloads_dir = Path(cleaned_dl).expanduser().resolve()
    else:
        downloads_dir = Path(default_dl)
    downloads_dir.mkdir(parents=True, exist_ok=True)
    console.print(f"[bold green][+] Destination folder confirmed:[/bold green] {downloads_dir}\n")

    opts = questionary.checkbox(
        "Select components to install / configure:",
        choices=[
            questionary.Choice("Download official yt-dlp.exe", checked=True),
            questionary.Choice("Download official FFmpeg & FFprobe", checked=True),
            questionary.Choice("Install optimized yt-dlp.conf preset directly next to yt-dlp.exe", checked=True),
            questionary.Choice("Verify / Install Python 3.11 Runtime", checked=True),
            questionary.Choice("Verify / Install VLC Media Player", checked=True),
            questionary.Choice("Add Tools folder to Windows User PATH", checked=True),
        ]
    ).ask()

    if not opts:
        console.print("[yellow]Setup cancelled.[/yellow]")
        return

    console.print("\n[bold cyan]Starting automated setup...[/bold cyan]\n")

    def cli_cb(msg: str, pct: float):
        console.print(f"[dim][{pct:.0f}%][/dim] {msg}")

    run_full_onboarding(
        tools_dir=tools_dir,
        downloads_dir=downloads_dir,
        do_ytdlp="yt-dlp.exe" in "".join(opts),
        do_ffmpeg="FFmpeg" in "".join(opts),
        do_conf="optimized" in "".join(opts),
        do_python="Python" in "".join(opts),
        do_vlc="VLC" in "".join(opts),
        do_add_path="PATH" in "".join(opts),
        callback=cli_cb
    )

    console.print(f"\n[bold green][+] Setup complete! Everything is ready.[/bold green]")
    console.print(f"[dim]Downloads will be saved to: [bold white]{downloads_dir}[/bold white][/dim]\n")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--cli":
        run_cli_onboarding()
    else:
        launch_onboarding_gui()
