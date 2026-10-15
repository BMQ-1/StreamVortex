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
        from .engine import find_ytdlp_conf
        active_conf = find_ytdlp_conf()
        conf_str = f"\n[dim]Config: [bold yellow]{active_conf.name}[/bold yellow] ({active_conf.parent})[/dim]" if active_conf else ""
        console.clear()
        console.print(
            Panel.fit(
                f"[bold cyan]⚡ StreamVortex Control Center[/bold cyan] [bold white](Powered by yt-dlp)[/bold white]\n"
                f"[dim]Universal Stream Sniffer, Live Watchdog & Recording Studio for yt-dlp[/dim]{conf_str}",
                border_style="bright_blue"
            )
        )

        choice = questionary.select(
            "What would you like to do?",
            choices=[
                "⚡ Quick Stream Sniffer & Downloader (Paste any URL)",
                "🔴 TikTok Live Downloader / Watchdog (yt-dlp Engine)",
                "📑 Batch URL Sequential Downloader (Multiple links)",
                "🌐 Open Web Studio (Recommended for beginners)",
                "🎵 Extract Audio Only MP3 (via yt-dlp)",
                "📁 Open Downloads Folder",
                "🩺 System Diagnostics & yt-dlp Health Check",
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

        if "Web Dashboard" in choice or "Web Studio" in choice:
            console.print("\n[bold cyan]Starting local Web Dashboard at http://127.0.0.1:8765 ...[/bold cyan]")
            launch_web_ui()
            break

        if "Batch URL" in choice:
            _handle_batch_download()
            questionary.press_any_key_to_continue().ask()
            continue

        if "Open Downloads Folder" in choice:
            d_dir = get_download_dir()
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
        "Studio Audio MP3"
    ]).ask()
    q_map = {"Maximum Quality (4K/2K/1080p)": "max", "Standard MP4 (1080p)": "1080p", "Fast MP4 (720p)": "720p", "Studio Audio MP3": "audio_mp3"}
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


if __name__ == "__main__":
    run_wizard()

