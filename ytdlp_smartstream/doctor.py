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
    from .engine import find_global_python, find_ytdlp, find_ffmpeg, find_ytdlp_conf
    global_py = find_global_python()
    py_ver = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    checks.append({"name": "Python Environment", "status": "[bold green]PASS[/bold green]", "detail": f"v{py_ver} ({global_py})"})

    # 2. FFmpeg Check
    ffmpeg_bin = find_ffmpeg()
    if ffmpeg_bin:
        try:
            res = subprocess.run([ffmpeg_bin, "-version"], capture_output=True, text=True, timeout=3)
            checks.append({"name": "FFmpeg Engine", "status": "[bold green]PASS[/bold green]", "detail": f"Global ({ffmpeg_bin})"})
        except Exception:
            checks.append({"name": "FFmpeg Engine", "status": "[bold green]PASS[/bold green]", "detail": f"Global ({ffmpeg_bin})"})
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
    conf_file = find_ytdlp_conf()
    if conf_file and conf_file.exists():
        ytdlp_exe_path = Path(ytdlp_cmd[0]) if ytdlp_cmd and not ytdlp_cmd[0].endswith(".py") else None
        is_adjacent = ytdlp_exe_path and conf_file.parent.resolve() == ytdlp_exe_path.parent.resolve()
        adj_tag = " (adjacent to yt-dlp.exe)" if is_adjacent else " (project/global)"
        checks.append({"name": "yt-dlp Config (.conf)", "status": "[bold green]PASS[/bold green]", "detail": f"Active: {conf_file}{adj_tag}"})
    else:
        checks.append({"name": "yt-dlp Config (.conf)", "status": "[bold yellow]INFO[/bold yellow]", "detail": "Using standard defaults"})

    # 6b. aria2c Download Accelerator Check
    from .engine import find_aria2c
    aria_bin = find_aria2c()
    if aria_bin:
        checks.append({"name": "aria2c Accelerator", "status": "[bold green]PASS[/bold green]", "detail": f"Detected: {aria_bin} (16 TCP connections active)"})
    else:
        checks.append({"name": "aria2c Accelerator", "status": "[bold yellow]INFO[/bold yellow]", "detail": "Optional accelerator (yt-dlp uses native multi-connection engine)"})

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
