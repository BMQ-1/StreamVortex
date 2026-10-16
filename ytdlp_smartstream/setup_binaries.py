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
        req = urllib.request.Request(url, headers={"User-Agent": "StreamVortex/1.2.0"})
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
    Verifies global yt-dlp, FFmpeg, Playwright, and plugins on the device.
    Prioritizes existing global installations and avoids downloading
    redundant binaries into bin/ when global tools are present.
    """
    from .engine import find_ytdlp, find_ffmpeg, find_ffprobe, find_ytdlp_conf
    bin_dir = get_bin_dir()
    results = {}

    def report(msg: str, pct: float = 0.0):
        if progress_callback:
            progress_callback(msg, pct)
        else:
            print(f"[StreamVortex Setup] {msg}")

    # 1. yt-dlp check (Global first)
    ytdlp_cmd = find_ytdlp()
    ytdlp_ready = False
    try:
        res = subprocess.run(ytdlp_cmd + ["--version"], capture_output=True, text=True, timeout=5)
        if res.returncode == 0:
            ver = res.stdout.strip()
            binary_path = ytdlp_cmd[0]
            report(f"Global yt-dlp verified: {binary_path} (v{ver}) - using global installation", 25.0)
            results["yt-dlp"] = {"status": "OK", "version": ver, "path": binary_path}
            ytdlp_ready = True
    except Exception:
        pass

    if not ytdlp_ready and force_download:
        ytdlp_bin = bin_dir / "yt-dlp.exe"
        report("No global yt-dlp detected. Downloading official yt-dlp.exe...", 5.0)
        def on_ytdlp_prog(dl, tot, pct):
            report(f"Downloading yt-dlp.exe: {dl / 1024 / 1024:.1f} MB / {tot / 1024 / 1024:.1f} MB ({pct:.1f}%)", 5.0 + (pct * 0.2))
        download_file_with_progress(YTDLP_RELEASE_URL, ytdlp_bin, progress_callback=on_ytdlp_prog)
        try:
            res = subprocess.run([str(ytdlp_bin), "--version"], capture_output=True, text=True, timeout=5)
            results["yt-dlp"] = {"status": "OK", "version": res.stdout.strip(), "path": str(ytdlp_bin)}
        except Exception as e:
            results["yt-dlp"] = {"status": "ERROR", "error": str(e), "path": str(ytdlp_bin)}

    # 2. FFmpeg & FFprobe check (Global first)
    ffmpeg_path = find_ffmpeg()
    ffprobe_path = find_ffprobe()
    ffmpeg_ready = False
    if ffmpeg_path:
        try:
            res = subprocess.run([ffmpeg_path, "-version"], capture_output=True, text=True, timeout=5)
            if res.returncode == 0:
                ver = res.stdout.splitlines()[0] if res.stdout else "Available"
                report(f"Global FFmpeg verified: {ffmpeg_path} - using global installation", 50.0)
                results["ffmpeg"] = {"status": "OK", "version": ver, "path": ffmpeg_path}
                ffmpeg_ready = True
        except Exception:
            pass

    if ffprobe_path:
        report(f"Global FFprobe verified: {ffprobe_path}", 60.0)
        results["ffprobe"] = {"status": "OK", "path": ffprobe_path}

    if not ffmpeg_ready and force_download:
        ffmpeg_bin = bin_dir / "ffmpeg.exe"
        ffprobe_bin = bin_dir / "ffprobe.exe"
        report("No global FFmpeg detected. Downloading official release...", 30.0)
        zip_dest = bin_dir / "ffmpeg_temp.zip"
        def on_ffmpeg_prog(dl, tot, pct):
            report(f"Downloading FFmpeg: {dl / 1024 / 1024:.1f} MB / {tot / 1024 / 1024:.1f} MB ({pct:.1f}%)", 30.0 + (pct * 0.3))
        if download_file_with_progress(FFMPEG_RELEASE_URL, zip_dest, progress_callback=on_ffmpeg_prog):
            report("Extracting ffmpeg.exe and ffprobe.exe...", 55.0)
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
                results["ffmpeg"] = {"status": "OK", "path": str(ffmpeg_bin)}
            except Exception as e:
                report(f"Extraction error: {e}", 55.0)

    # 3. Active yt-dlp config verification
    conf_file = find_ytdlp_conf()
    if conf_file and conf_file.exists():
        report(f"Active yt-dlp config verified: {conf_file}", 68.0)
        results["config"] = {"status": "OK", "path": str(conf_file)}
    else:
        results["config"] = {"status": "INFO", "path": "Default settings"}

    # 3b. aria2c download accelerator verification
    from .engine import find_aria2c
    aria_bin = find_aria2c()
    if aria_bin:
        report(f"aria2c download accelerator verified: {aria_bin}", 75.0)
        results["aria2c"] = {"status": "OK", "path": str(aria_bin)}
    else:
        report("aria2c accelerator not found (using native multi-threaded downloader)", 75.0)
        results["aria2c"] = {"status": "INFO", "detail": "Optional accelerator"}

    # 4. Playwright Chromium
    report("Checking Playwright Chromium driver...", 80.0)
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            b = p.chromium.launch(headless=True)
            b.close()
        results["playwright"] = {"status": "OK", "detail": "Chromium headless ready"}
        report("Playwright Chromium headless ready", 90.0)
    except Exception:
        report("Installing Playwright Chromium headless driver...", 82.0)
        try:
            subprocess.run([sys.executable, "-m", "playwright", "install", "chromium"], capture_output=True, check=True)
            results["playwright"] = {"status": "OK", "detail": "Installed successfully"}
        except Exception as e:
            results["playwright"] = {"status": "WARN", "detail": f"Could not auto-install: {e}"}

    # 5. Link native yt-dlp plugin
    report("Registering native yt-dlp plugin...", 95.0)
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

    report("Setup verification complete! System is using global environment.", 100.0)
    return results


if __name__ == "__main__":
    setup_all_binaries()
