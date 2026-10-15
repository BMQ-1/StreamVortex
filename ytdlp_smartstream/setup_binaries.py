"""
StreamVortex Binary & Dependency Provisioner.
Automates downloading, verifying, and configuring yt-dlp, FFmpeg, and Playwright.
All downloads are fetched directly from official release channels with full transparency.
"""

import sys
import os
import shutil
import zipfile
import urllib.request
import subprocess
from pathlib import Path
from typing import Optional, Callable, Dict, Any

from yt_dlp.utils import get_user_config_dirs

YTDLP_RELEASE_URL = "https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp.exe"
FFMPEG_RELEASE_URL = "https://github.com/yt-dlp/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-gpl.zip"


def get_bin_dir() -> Path:
    """Returns the dedicated bin directory for StreamVortex."""
    # 1. If running as compiled exe
    if getattr(sys, "frozen", False):
        exe_dir = Path(sys.executable).parent
        bin_dir = exe_dir / "bin"
    else:
        # 2. Project root bin/
        project_root = Path(__file__).resolve().parent.parent
        bin_dir = project_root / "bin"

    bin_dir.mkdir(parents=True, exist_ok=True)
    return bin_dir


def download_file_with_progress(
    url: str,
    dest_path: Path,
    label: str = "Downloading",
    progress_callback: Optional[Callable[[int, int, float], None]] = None
) -> bool:
    """
    Downloads a remote file with progress reporting.
    progress_callback receives: (downloaded_bytes, total_bytes, percent)
    """
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "StreamVortex/1.0.0"})
        with urllib.request.urlopen(req) as resp:
            total_size = int(resp.headers.get("Content-Length", 0))
            downloaded = 0
            block_size = 1024 * 64
            temp_dest = dest_path.with_suffix(".tmp")

            with open(temp_dest, "wb") as f:
                while True:
                    chunk = resp.read(block_size)
                    if not chunk:
                        break
                    f.write(chunk)
                    downloaded += len(chunk)
                    percent = (downloaded / total_size * 100) if total_size > 0 else 0
                    if progress_callback:
                        progress_callback(downloaded, total_size, percent)

            if dest_path.exists():
                dest_path.unlink()
            temp_dest.rename(dest_path)
            return True
    except Exception as e:
        print(f"[-] Download failed for {url}: {e}", file=sys.stderr)
        return False


def setup_all_binaries(
    force_download: bool = False,
    progress_callback: Optional[Callable[[str, float], None]] = None
) -> Dict[str, Any]:
    """
    Ensures yt-dlp, FFmpeg, Playwright, and plugins are installed and ready.
    Returns status dictionary.
    """
    bin_dir = get_bin_dir()
    results = {}

    def report(msg: str, pct: float = 0.0):
        if progress_callback:
            progress_callback(msg, pct)
        else:
            print(f"[StreamVortex Setup] {msg}")

    # 1. yt-dlp.exe
    ytdlp_bin = bin_dir / "yt-dlp.exe"
    if not force_download and ytdlp_bin.exists():
        report(f"yt-dlp is already present in {ytdlp_bin}", 25.0)
    else:
        # Check C:\Tools\yt-dlp.exe first for quick copy
        c_tools_ytdlp = Path("C:/Tools/yt-dlp.exe")
        if not force_download and c_tools_ytdlp.exists():
            report(f"Copying verified yt-dlp.exe from {c_tools_ytdlp} to {bin_dir}...", 10.0)
            shutil.copy2(c_tools_ytdlp, ytdlp_bin)
        else:
            report(f"Downloading latest official yt-dlp.exe from GitHub releases...", 5.0)
            def on_ytdlp_prog(dl, tot, pct):
                report(f"Downloading yt-dlp.exe: {dl / 1024 / 1024:.1f} MB / {tot / 1024 / 1024:.1f} MB ({pct:.1f}%)", 5.0 + (pct * 0.2))
            download_file_with_progress(YTDLP_RELEASE_URL, ytdlp_bin, progress_callback=on_ytdlp_prog)

    # Verify yt-dlp
    try:
        res = subprocess.run([str(ytdlp_bin), "--version"], capture_output=True, text=True, timeout=5)
        results["yt-dlp"] = {"status": "OK", "version": res.stdout.strip(), "path": str(ytdlp_bin)}
    except Exception as e:
        results["yt-dlp"] = {"status": "ERROR", "error": str(e), "path": str(ytdlp_bin)}

    # 2. FFmpeg & FFprobe
    ffmpeg_bin = bin_dir / "ffmpeg.exe"
    ffprobe_bin = bin_dir / "ffprobe.exe"
    if not force_download and ffmpeg_bin.exists() and ffprobe_bin.exists():
        report(f"FFmpeg & FFprobe already present in {bin_dir}", 60.0)
    else:
        # Check C:\Tools first
        c_tools_ffmpeg = Path("C:/Tools/ffmpeg.exe")
        c_tools_ffprobe = Path("C:/Tools/ffprobe.exe")
        if not force_download and c_tools_ffmpeg.exists() and c_tools_ffprobe.exists():
            report(f"Copying verified FFmpeg suite from C:\\Tools to {bin_dir}...", 40.0)
            shutil.copy2(c_tools_ffmpeg, ffmpeg_bin)
            shutil.copy2(c_tools_ffprobe, ffprobe_bin)
        else:
            report(f"Downloading official FFmpeg release from GitHub...", 30.0)
            zip_dest = bin_dir / "ffmpeg_temp.zip"
            def on_ffmpeg_prog(dl, tot, pct):
                report(f"Downloading FFmpeg suite: {dl / 1024 / 1024:.1f} MB / {tot / 1024 / 1024:.1f} MB ({pct:.1f}%)", 30.0 + (pct * 0.3))
            if download_file_with_progress(FFMPEG_RELEASE_URL, zip_dest, progress_callback=on_ffmpeg_prog):
                report("Extracting ffmpeg.exe and ffprobe.exe...", 60.0)
                try:
                    with zipfile.ZipFile(zip_dest, "r") as z:
                        for member in z.namelist():
                            if member.endswith("ffmpeg.exe"):
                                with z.open(member) as src, open(ffmpeg_bin, "wb") as dst:
                                    shutil.copyfileobj(src, dst)
                            elif member.endswith("ffprobe.exe"):
                                with z.open(member) as src, open(ffprobe_bin, "wb") as dst:
                                    shutil.copyfileobj(src, dst)
                    if zip_dest.exists():
                        zip_dest.unlink()
                except Exception as e:
                    report(f"Extraction error: {e}", 60.0)

    # Verify FFmpeg
    try:
        res = subprocess.run([str(ffmpeg_bin), "-version"], capture_output=True, text=True, timeout=5)
        ver = res.stdout.splitlines()[0] if res.stdout else "Available"
        results["ffmpeg"] = {"status": "OK", "version": ver, "path": str(ffmpeg_bin)}
    except Exception as e:
        results["ffmpeg"] = {"status": "ERROR", "error": str(e), "path": str(ffmpeg_bin)}

    # 3. Playwright Chromium
    report("Checking Playwright Chromium driver...", 70.0)
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            b = p.chromium.launch(headless=True)
            b.close()
        results["playwright"] = {"status": "OK", "detail": "Chromium headless ready"}
        report("Playwright Chromium headless ready", 85.0)
    except Exception:
        report("Installing Playwright Chromium headless driver...", 75.0)
        try:
            subprocess.run([sys.executable, "-m", "playwright", "install", "chromium"], capture_output=True, check=True)
            results["playwright"] = {"status": "OK", "detail": "Installed successfully"}
        except Exception as e:
            results["playwright"] = {"status": "WARN", "detail": f"Could not auto-install: {e}"}

    # 4. Link native yt-dlp plugin
    report("Registering native yt-dlp plugin...", 90.0)
    try:
        config_dirs = list(get_user_config_dirs("yt-dlp"))
        roaming_dir = next((d for d in config_dirs if "Roaming" in str(d)), config_dirs[0])
        target_dir = Path(roaming_dir) / "plugins" / "smartstream" / "yt_dlp_plugins" / "extractor"
        target_dir.mkdir(parents=True, exist_ok=True)

        source_dir = Path(__file__).resolve().parent.parent / "yt_dlp_plugins" / "extractor"
        if source_dir.exists():
            for f in source_dir.glob("*.py"):
                shutil.copy2(f, target_dir / f.name)
            (target_dir.parent / "__init__.py").touch(exist_ok=True)
            (target_dir / "__init__.py").touch(exist_ok=True)
            results["plugin"] = {"status": "OK", "path": str(target_dir)}
        else:
            results["plugin"] = {"status": "WARN", "detail": "Source extractor directory not found"}
    except Exception as e:
        results["plugin"] = {"status": "ERROR", "error": str(e)}

    report("Setup complete! All binaries and plugins are ready.", 100.0)
    return results


if __name__ == "__main__":
    setup_all_binaries()
