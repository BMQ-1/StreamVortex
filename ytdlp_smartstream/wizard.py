"""
StreamVortex Interactive Beginner-Friendly Wizard.
Guided, menu-driven experience for users who prefer interactive prompts over terminal arguments.
"""

import sys
import os
import subprocess
from pathlib import Path

if sys.platform == "win32":
    try:
        if sys.stdout.encoding.lower() != "utf-8":
            sys.stdout.reconfigure(encoding="utf-8")
        if sys.stderr.encoding.lower() != "utf-8":
            sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

import questionary
from rich.console import Console
from rich.panel import Panel

from .config import get_download_dir, get_config, save_config, add_history_entry
from .tiktok_resolver import resolve_tiktok_live, resolve_tiktok_video
from .sniffer import smart_sniff
from .recorder import copy_to_clipboard, send_notification, record_stream, wait_for_live
from .web_ui import launch_web_ui
from .doctor import run_doctor

console = Console()


def run_wizard():
    """Runs the main interactive wizard loop."""
    from .engine import is_environment_ready
    if not is_environment_ready():
        console.print("\n[bold yellow][!] First-Time Setup Detected:[/bold yellow] [dim]Essential media engines (yt-dlp / FFmpeg) are not found.[/dim]")
        do_setup = questionary.confirm("Would you like to run the automated 1-click setup wizard now?", default=True).ask()
        if do_setup:
            from .onboarding import run_cli_onboarding
            run_cli_onboarding()

    while True:
        from .engine import find_ytdlp_conf, get_conf_download_dir
        active_conf = find_ytdlp_conf()
        conf_dl = get_conf_download_dir()
        conf_str = f"\n[dim]Config: [bold yellow]{active_conf.name}[/bold yellow] ({active_conf.parent})[/dim]" if active_conf else ""
        dl_str = f"\n[dim]Downloads Destination: [bold green]{conf_dl}[/bold green][/dim]"
        console.clear()
        console.print(
            Panel.fit(
                f"[bold cyan]⚡ StreamVortex Control Center[/bold cyan] [bold white](Powered by yt-dlp)[/bold white]\n"
                f"[dim]Universal Stream Sniffer, Live Watchdog & Recording Studio for yt-dlp[/dim]{conf_str}{dl_str}",
                border_style="bright_blue"
            )
        )

        choice = questionary.select(
            "What would you like to do? (Use ↑/↓ arrow keys to navigate, Enter to select)",
            choices=[
                "🖥️ Open Modern Desktop GUI Studio (Full Window)",
                "⚡ Quick Stream Sniffer & Downloader (Paste any URL)",
                "🔴 TikTok Live Downloader / Watchdog (yt-dlp Engine)",
                "📑 Batch URL Sequential Downloader (Multiple links)",
                "📥 Change Download Destination (Drag & Drop Any Folder)",
                "🌐 Open Web Studio (Recommended for beginners)",
                "🎵 Extract Audio Only MP3 (via yt-dlp)",
                "🛠️ Repair & Fix Video Containers (Fix MPEG-TS & FLV)",
                "📁 Open Downloads Folder",
                "🩺 System Diagnostics & yt-dlp Health Check",
                "🔌 Sync & Install Native yt-dlp Roaming Plugin",
                "📦 Build Standalone Executable (StreamVortex.exe)",
                "🚀 Zero-Setup Onboarding (Install yt-dlp, FFmpeg, Python, VLC)",
                "🚪 Exit"
            ],
            style=questionary.Style([
                ('qmark', 'fg:#00f2fe bold'),
                ('question', 'bold'),
                ('answer', 'fg:#00f2fe bold'),
                ('pointer', 'fg:#4facfe bold'),
                ('highlighted', 'fg:#00f2fe bold'),
                ('selected', 'fg:#00f2fe'),
            ])
        ).ask()

        if not choice or "Exit" in choice:
            console.print("\n[dim]Goodbye! Happy streaming.[/dim]\n")
            break

        if "Desktop GUI" in choice:
            from .desktop import launch_desktop_gui
            console.print("\n[bold cyan]Launching Modern Desktop GUI Studio...[/bold cyan]")
            launch_desktop_gui()
            continue

        if "Web Dashboard" in choice or "Web Studio" in choice:
            console.print("\n[bold cyan]Starting local Web Dashboard at http://127.0.0.1:8765 ...[/bold cyan]")
            launch_web_ui()
            break

        if "Batch URL" in choice:
            _handle_batch_download()
            questionary.press_any_key_to_continue().ask()
            continue

        if "Change Download Destination" in choice:
            _handle_change_download_dir()
            questionary.press_any_key_to_continue().ask()
            continue

        if "Repair & Fix Video Containers" in choice:
            _handle_repair_fixup()
            questionary.press_any_key_to_continue().ask()
            continue

        if "Open Downloads Folder" in choice:
            from .engine import get_conf_download_dir
            d_dir = get_conf_download_dir()
            console.print(f"\n[cyan]Opening {d_dir}...[/cyan]")
            if sys.platform == "win32":
                os.startfile(d_dir)
            else:
                subprocess.run(["xdg-open", str(d_dir)])
            questionary.press_any_key_to_continue().ask()
            continue

        if "System Diagnostics" in choice:
            run_doctor()
            questionary.press_any_key_to_continue().ask()
            continue

        if "Sync & Install Native yt-dlp" in choice:
            console.print("\n[bold cyan]Syncing native StreamVortex extractors into yt-dlp roaming plugin directory...[/bold cyan]")
            try:
                from ..install_plugin import install as run_plugin_install
            except (ImportError, ValueError):
                try:
                    import install_plugin
                    run_plugin_install = install_plugin.install
                except Exception:
                    run_plugin_install = None
            if run_plugin_install:
                run_plugin_install()
            else:
                console.print("[yellow][!] Running setup installer fallback...[/yellow]")
                from .setup_binaries import check_and_install_dependencies
                check_and_install_dependencies()
            questionary.press_any_key_to_continue().ask()
            continue

        if "Build Standalone Executable" in choice:
            console.print("\n[bold cyan]Compiling standalone StreamVortex.exe with PyInstaller...[/bold cyan]")
            try:
                root_dir = Path(__file__).resolve().parent.parent
                build_script = root_dir / "build_exe.py"
                if build_script.exists():
                    subprocess.run([sys.executable, str(build_script)], check=True)
                else:
                    console.print("[yellow][!] build_exe.py script not found.[/yellow]")
            except Exception as e:
                console.print(f"[bold red][!] Compilation error: {e}[/bold red]")
            questionary.press_any_key_to_continue().ask()
            continue

        if "Zero-Setup Onboarding" in choice:
            from .onboarding import run_cli_onboarding
            run_cli_onboarding()
            questionary.press_any_key_to_continue().ask()
            continue

        if "Quick Stream Sniffer" in choice:
            _handle_quick_sniff()
            questionary.press_any_key_to_continue().ask()
            continue

        if "TikTok Live" in choice:
            _handle_tiktok_live()
            questionary.press_any_key_to_continue().ask()
            continue

        if "Extract Audio Only" in choice:
            _handle_audio_extract()
            questionary.press_any_key_to_continue().ask()
            continue


def _handle_change_download_dir():
    """Interactive drag and drop download destination folder selector."""
    from .engine import get_conf_download_dir, update_ytdlp_conf_destinations, find_ytdlp_conf
    current = get_conf_download_dir()
    conf = find_ytdlp_conf()
    conf_name = conf.name if conf else "yt-dlp.conf"

    console.print("\n[bold cyan]📥 Interactive Download Destination Setup[/bold cyan]")
    console.print(f"[dim]Current destination from {conf_name}: [bold white]{current}[/bold white][/dim]\n")
    console.print("[dim]💡 Tip: Simply [bold white]drag & drop ANY folder[/bold white] from Windows Explorer into this window![/dim]")
    console.print("[dim]   (Or type a directory path, or press Enter to keep current)[/dim]\n")

    raw = questionary.text(
        "Enter or Drag & Drop folder path:",
        default=str(current)
    ).ask()

    if not raw or not raw.strip():
        return

    cleaned = raw.strip().strip("'\"")
    new_dir = Path(cleaned).expanduser().resolve()
    new_dir.mkdir(parents=True, exist_ok=True)

    ok, msg = update_ytdlp_conf_destinations(new_dir)
    if ok:
        console.print(f"\n[bold green][+] SUCCESS:[/bold green] Download folder set to: [bold white]{new_dir}[/bold white]")
        console.print(f"[green][+] Updated all destinations in {conf_name}:[/green]")
        console.print(f"    [dim]• Video: {new_dir}\\%(playlist|)s\\%(title).70B_%(epoch)s.%(ext)s[/dim]")
        console.print(f"    [dim]• Subtitles: {new_dir}\\Subs\\%(title).70B_%(epoch)s.%(ext)s[/dim]")
        console.print(f"    [dim]• Thumbnails: {new_dir}\\Thumbnails\\%(title).70B_%(epoch)s.%(ext)s[/dim]\n")
    else:
        console.print(f"[red][-] Failed to update config: {msg}[/red]")


def _handle_quick_sniff():
    url = questionary.text("Enter or paste the video/live URL:").ask()
    if not url or not url.strip():
        return

    url = url.strip()
    with console.status("[bold cyan]Sniffing media wire for live streams...[/bold cyan]"):
        sniffed = smart_sniff(url)

    if not sniffed:
        console.print("[red][-] No active stream detected on that page.[/red]")
        return

    console.print(f"\n[bold green][+] Stream Discovered![/bold green]")
    console.print(f"[dim]Type:[/dim] {sniffed.stream_type.upper()} | [dim]Title:[/dim] {sniffed.page_title or 'Stream'}")
    console.print(f"[cyan]URL:[/cyan] {sniffed.url}\n")

    action = questionary.select(
        "What would you like to do?",
        choices=[
            "🎬 Play Now in Media Player (MPV)",
            "⬇️ Download Video (yt-dlp)",
            "🔴 Record Live Stream (FFmpeg copy)",
            "📋 Copy URL to Clipboard",
            "🔙 Back"
        ]
    ).ask()

    if "Play Now" in action:
        _play_url(sniffed.url, sniffed.headers.get("User-Agent"))
    elif "Download Video" in action:
        from .engine import run_ytdlp_download
        run_ytdlp_download(sniffed.url, referer=url, title=sniffed.page_title)
    elif "Record Live" in action:
        from .engine import run_ffmpeg_record
        run_ffmpeg_record(sniffed.url, headers=sniffed.headers, title=sniffed.page_title)
    elif "Copy URL" in action:
        copy_to_clipboard(sniffed.url)
        console.print("[green][+] Copied to clipboard![/green]")


def _handle_tiktok_live():
    creator = questionary.text("Enter TikTok username (e.g. @weathernewslive):").ask()
    if not creator or not creator.strip():
        return

    creator_clean = creator.strip().lstrip("@")
    mode = questionary.select(
        f"Select action for @{creator_clean}:",
        choices=[
            "⚡ Check & Download Current Live Stream",
            "👀 Watchdog: Wait & Auto-Record when creator goes LIVE",
            "🔙 Back"
        ]
    ).ask()

    if "Check & Download" in mode:
        with console.status(f"[bold cyan]Resolving live stream for @{creator_clean}...[/bold cyan]"):
            result = resolve_tiktok_live(creator_clean)

        if not result or not result.formats:
            console.print(f"[yellow][-] @{creator_clean} is currently offline.[/yellow]")
            want_watchdog = questionary.confirm("Would you like to start Watchdog mode to wait for them?").ask()
            if want_watchdog:
                _start_watchdog(creator_clean)
            return

        hls_formats = [f for f in result.formats if f.protocol == "m3u8_native"]
        best = hls_formats[0] if hls_formats else result.formats[0]

        console.print(f"\n[bold green][+] @{creator_clean} IS LIVE![/bold green] - {result.title}\n")
        act = questionary.select(
            "Choose action:",
            choices=[
                "🎬 Play Stream Now (MPV)",
                "⬇️ Download Live Stream",
                "🔴 Record Stream via FFmpeg",
                "📋 Copy M3U8 URL",
                "🔙 Back"
            ]
        ).ask()

        if "Play Stream" in act:
            _play_url(best.url)
        elif "Download Live" in act:
            from .engine import run_ytdlp_download
            run_ytdlp_download(
                best.url,
                referer=f"https://www.tiktok.com/@{creator_clean}/live",
                is_live=True,
                title=result.title,
                uploader=result.uploader
            )
        elif "Record Stream" in act:
            from .engine import run_ffmpeg_record
            run_ffmpeg_record(
                best.url,
                headers=result.http_headers,
                title=result.title,
                uploader=result.uploader
            )
        elif "Copy M3U8" in act:
            copy_to_clipboard(best.url)
            console.print("[green][+] Copied .m3u8 URL to clipboard![/green]")

    elif "Watchdog" in mode:
        _start_watchdog(creator_clean)


def _start_watchdog(creator_clean: str):
    from .engine import run_ffmpeg_record
    def on_live(res):
        hls = next((f for f in res.formats if f.protocol == "m3u8_native"), res.formats[0])
        run_ffmpeg_record(hls.url, headers=res.http_headers, title=res.title, uploader=creator_clean)
    wait_for_live(creator_clean, poll_interval=10, on_live_start=on_live)


def _handle_audio_extract():
    url = questionary.text("Enter stream or video URL to extract MP3 from:").ask()
    if not url or not url.strip():
        return
    url = url.strip()

    console.print("\n[bold cyan]Extracting audio track as MP3...[/bold cyan]")
    from .engine import run_ytdlp_download
    run_ytdlp_download(url, audio_only=True)
    d_dir = get_download_dir()
    console.print(f"\n[bold green][+] Audio saved to: {d_dir}[/bold green]")


def _play_url(url: str, user_agent: str = None):
    import shutil
    player = shutil.which("mpv") or shutil.which("vlc")
    if not player:
        console.print("[yellow]Neither MPV nor VLC found on PATH. Stream URL:[/yellow]")
        console.print(url)
        return
    cmd = [player, url]
    if user_agent and "mpv" in player.lower():
        cmd.extend([f"--user-agent={user_agent}"])
    subprocess.run(cmd)


def _handle_batch_download():
    console.print("\n[bold cyan]📑 Batch URL Sequential Downloader[/bold cyan]")
    path_str = questionary.text("Enter path to text file containing URLs (or leave blank to paste interactively):").ask()
    if path_str and path_str.strip():
        p = Path(path_str.strip())
        if not p.exists():
            console.print(f"[red][!] File not found: {p}[/red]")
            return
        urls = [line.strip() for line in p.read_text(encoding="utf-8").splitlines() if line.strip() and line.strip().startswith("http")]
    else:
        raw = questionary.text("Enter URLs separated by spaces or commas:").ask()
        if not raw:
            return
        urls = [u.strip() for u in raw.replace(",", " ").split() if u.strip().startswith("http")]

    if not urls:
        console.print("[yellow][!] No valid URLs provided.[/yellow]")
        return

    q = questionary.select("Select quality profile:", choices=[
        "Maximum Quality (4K/2K/1080p)",
        "Standard MP4 (1080p)",
        "Fast MP4 (720p)",
        "Respect yt-dlp.conf Setting",
        "Studio Audio MP3"
    ]).ask()
    q_map = {
        "Maximum Quality (4K/2K/1080p)": "max",
        "Standard MP4 (1080p)": "1080p",
        "Fast MP4 (720p)": "720p",
        "Respect yt-dlp.conf Setting": "conf",
        "Studio Audio MP3": "audio_mp3"
    }
    q_code = q_map.get(q, "max")

    from .engine import resolve_stream_metadata, run_ytdlp_download
    console.print(f"\n[cyan]Starting download for {len(urls)} items...[/cyan]")
    for idx, u in enumerate(urls, 1):
        console.print(f"\n[bold yellow]--- [{idx}/{len(urls)}] {u} ---[/bold yellow]")
        meta = resolve_stream_metadata(u)
        run_ytdlp_download(
            stream_url=u,
            title=meta.get("title"),
            uploader=meta.get("uploader"),
            is_live=meta.get("is_live", False),
            audio_only=q_code.startswith("audio_"),
            quality_preference=q_code,
            on_output=lambda line: console.print(f"[dim]{line}[/dim]"),
            respect_conf_output=True
        )
    console.print("\n[bold green][+] All batch downloads complete![/bold green]\n")


def _handle_repair_fixup():
    """
    Interactive Container Repair & Normalizer.
    Users can drag-and-drop a single file or a whole directory of videos.
    Safely inspects containers (detecting raw MPEG-TS or FLV disguised as .mp4, corrupted .part files, etc.)
    and losslessly remuxes them with timestamps rebuilt and +faststart applied.
    """
    from .engine import fixup_recorded_file, sniff_container, EXT_TO_CONTAINER

    console.print("\n[bold cyan]🛠️ Universal Video Container Repair & Normalizer[/bold cyan]")
    console.print("[dim]Fixes mismatched containers (e.g. MPEG-TS live feeds or FLV saved as .mp4, broken/interrupted .part files).[/dim]\n")
    console.print("[dim]💡 Tip: Simply [bold white]drag & drop a file OR a folder[/bold white] from Windows Explorer into this window![/dim]")

    raw = questionary.text("Enter or Drag & Drop file or folder path:").ask()
    if not raw or not raw.strip():
        return

    path_target = Path(raw.strip().strip("'\"")).expanduser().resolve()
    if not path_target.exists():
        console.print(f"[bold red][!] Path does not exist: {path_target}[/bold red]")
        return

    targets = []
    if path_target.is_file():
        targets.append(path_target)
    elif path_target.is_dir():
        # Search all common video extensions including .part files
        exts = ["*.mp4", "*.ts", "*.flv", "*.mkv", "*.part", "*.m4v", "*.mov"]
        for ext in exts:
            targets.extend([f for f in path_target.glob(ext) if f.is_file() and f.stat().st_size > 0])
        targets = sorted(list(set(targets)))
        console.print(f"\n[cyan]Found {len(targets)} potential video files in {path_target.name}/[/cyan]")

    if not targets:
        console.print("[yellow][!] No valid video files found at that location.[/yellow]")
        return

    fixed_count = 0
    clean_count = 0

    with console.status("[bold cyan]Scanning and repairing media files...[/bold cyan]"):
        for item in targets:
            ext = item.suffix.lower().lstrip(".")
            target_ext = item.with_suffix("").suffix.lower().lstrip(".") if ext == "part" else ext
            have = sniff_container(item)

            if not have:
                continue

            is_flv = (have == "flv" or ext == "flv")
            want = "mp4" if is_flv else EXT_TO_CONTAINER.get(target_ext, "mp4")
            needs_fix = is_flv or (have != want) or (ext == "part")

            if needs_fix:
                dest_desc = "mp4/mkv" if is_flv else want
                console.print(f"\n[bold yellow][Fixing][/bold yellow] {item.name}")
                console.print(f"  [dim]Detected container:[/dim] [bold red]{have}[/bold red] -> [bold green]{dest_desc}[/bold green]")
                res_path = fixup_recorded_file(
                    item,
                    on_output=lambda line: console.print(f"  [dim]{line}[/dim]")
                )
                fixed_count += 1
                console.print(f"  [bold green]✓ Fixed & Playable:[/bold green] {res_path.name}")
            else:
                clean_count += 1

    console.print(f"\n[bold green][+] Repair Complete![/bold green] Fixed: [bold white]{fixed_count}[/bold white] | Already Clean: [dim]{clean_count}[/dim]\n")


if __name__ == "__main__":
    run_wizard()

