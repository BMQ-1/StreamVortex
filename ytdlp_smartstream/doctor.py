"""
StreamVortex System Doctor & Diagnostic Engine.
Verifies dependencies, media runtimes, browser drivers, and yt-dlp plugin status.
"""

import sys
import os
import shutil
import subprocess
from pathlib import Path
from typing import Dict, Any, List

if sys.platform == "win32":
    try:
        if sys.stdout.encoding.lower() != "utf-8":
            sys.stdout.reconfigure(encoding="utf-8")
        if sys.stderr.encoding.lower() != "utf-8":
            sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from yt_dlp.utils import get_user_config_dirs

console = Console()


def run_doctor() -> bool:
    """Runs a complete system health check and prints a structured diagnostics report."""
    console.print("\n[bold cyan][StreamVortex Doctor] Running System Diagnostic Check...[/bold cyan]\n")

    checks: List[Dict[str, Any]] = []
    all_ok = True

    # 1. Python Check
    py_ver = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    if sys.version_info >= (3, 9):
        checks.append({"name": "Python Environment", "status": "[bold green]PASS[/bold green]", "detail": f"Python {py_ver}"})
    else:
        checks.append({"name": "Python Environment", "status": "[bold red]FAIL[/bold red]", "detail": f"Python {py_ver} (Requires 3.9+)"})
        all_ok = False

    # 2. FFmpeg Check
    from .engine import find_ytdlp, find_ffmpeg
    ffmpeg_bin = find_ffmpeg()
    if ffmpeg_bin:
        try:
            res = subprocess.run([ffmpeg_bin, "-version"], capture_output=True, text=True, timeout=3)
            first_line = res.stdout.splitlines()[0] if res.stdout else "Available"
            checks.append({"name": "FFmpeg Engine", "status": "[bold green]PASS[/bold green]", "detail": first_line[:50]})
        except Exception:
            checks.append({"name": "FFmpeg Engine", "status": "[bold green]PASS[/bold green]", "detail": ffmpeg_bin})
    else:
        checks.append({"name": "FFmpeg Engine", "status": "[bold yellow]WARN[/bold yellow]", "detail": "Not found on PATH or C:\\Tools (Recording falls back to yt-dlp)"})

    # 3. yt-dlp Check
    ytdlp_cmd = find_ytdlp()
    try:
        res = subprocess.run(ytdlp_cmd + ["--version"], capture_output=True, text=True, timeout=3)
        ver = res.stdout.strip()
        binary_label = ytdlp_cmd[0]
        checks.append({"name": "yt-dlp Core Engine", "status": "[bold green]PASS[/bold green]", "detail": f"v{ver} ({binary_label})"})
    except Exception:
        checks.append({"name": "yt-dlp Core Engine", "status": "[bold red]FAIL[/bold red]", "detail": "yt-dlp not found on PATH, C:\\Tools, or python module"})
        all_ok = False

    # 4. Playwright Chromium Check
    if "PLAYWRIGHT_BROWSERS_PATH" not in os.environ:
        appdata_local = os.environ.get("LOCALAPPDATA", "")
        if appdata_local:
            os.environ["PLAYWRIGHT_BROWSERS_PATH"] = str(Path(appdata_local) / "ms-playwright")

    pw_ok = False
    pw_detail = ""
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            b = p.chromium.launch(headless=True)
            b.close()
        pw_ok = True
        pw_detail = "Chromium headless driver ready"
    except Exception:
        appdata_local = os.environ.get("LOCALAPPDATA", "")
        ms_pw = Path(appdata_local) / "ms-playwright"
        if ms_pw.exists() and any(ms_pw.glob("chromium*")):
            pw_ok = True
            pw_detail = "Chromium driver verified in LocalAppData"
        else:
            pw_detail = "Chromium driver missing. Run: playwright install chromium"

    if pw_ok:
        checks.append({"name": "Playwright / Chromium", "status": "[bold green]PASS[/bold green]", "detail": pw_detail})
    else:
        checks.append({"name": "Playwright / Chromium", "status": "[bold yellow]WARN[/bold yellow]", "detail": pw_detail})

    # 5. Native yt-dlp Plugin Registration Check
    config_dirs = list(get_user_config_dirs("yt-dlp"))
    roaming_dir = next((d for d in config_dirs if "Roaming" in str(d)), config_dirs[0])
    target_plugin_dir = Path(roaming_dir) / "plugins" / "smartstream" / "yt_dlp_plugins" / "extractor"
    if (target_plugin_dir / "tiktok_smart.py").exists() and (target_plugin_dir / "universal_smart.py").exists():
        checks.append({"name": "yt-dlp Native Plugin", "status": "[bold green]PASS[/bold green]", "detail": "Linked in %APPDATA%/yt-dlp/plugins"})
    else:
        checks.append({"name": "yt-dlp Native Plugin", "status": "[bold yellow]WARN[/bold yellow]", "detail": "Plugin not linked. Run: python install_plugin.py"})

    # 6. yt-dlp Configuration (.conf) Check
    from .engine import find_ytdlp_conf
    conf_file = find_ytdlp_conf()
    if conf_file and conf_file.exists():
        checks.append({"name": "yt-dlp Config (.conf)", "status": "[bold green]PASS[/bold green]", "detail": f"Active: {conf_file}"})
    else:
        checks.append({"name": "yt-dlp Config (.conf)", "status": "[bold yellow]INFO[/bold yellow]", "detail": "Using standard defaults"})

    # 7. Media Player Check
    mpv_path = shutil.which("mpv")
    vlc_path = shutil.which("vlc")
    player_detail = []
    if mpv_path: player_detail.append("MPV")
    if vlc_path: player_detail.append("VLC")
    if player_detail:
        checks.append({"name": "Media Player (VLC/MPV)", "status": "[bold green]PASS[/bold green]", "detail": ", ".join(player_detail)})
    else:
        checks.append({"name": "Media Player (VLC/MPV)", "status": "[dim]OPTIONAL[/dim]", "detail": "Neither MPV nor VLC found for direct desktop playback"})

    # Render diagnostics table
    table = Table(border_style="bright_blue", header_style="bold magenta", show_lines=True)
    table.add_column("Component", style="bold white", width=24)
    table.add_column("Status", justify="center", width=12)
    table.add_column("Details", style="dim")

    for c in checks:
        table.add_row(c["name"], c["status"], c["detail"])

    console.print(table)

    if all_ok:
        console.print("\n[bold green][+] System is fully optimized for stream extraction and recording![/bold green]\n")
    else:
        console.print("\n[yellow]! Some recommended components need attention. Follow the details above to optimize your setup.[/yellow]\n")

    return all_ok


if __name__ == "__main__":
    run_doctor()
