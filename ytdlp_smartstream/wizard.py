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
    while True:
        console.clear()
        console.print(
            Panel.fit(
                "[bold cyan]⚡ StreamVortex Control Center[/bold cyan] [bold white](Powered by yt-dlp)[/bold white]\n"
                "[dim]Universal Stream Sniffer, Live Watchdog & Recording Studio for yt-dlp[/dim]",
                border_style="bright_blue"
            )
        )

        choice = questionary.select(
            "What would you like to do?",
            choices=[
                "⚡ Quick Stream Sniffer & Downloader (Paste any URL)",
                "🔴 TikTok Live Downloader / Watchdog (yt-dlp Engine)",
                "🌐 Open Web Studio (Recommended for beginners)",
                "🎵 Extract Audio Only MP3 (via yt-dlp)",
                "📁 Open Downloads Folder",
                "🩺 System Diagnostics & yt-dlp Health Check",
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

        if "Web Dashboard" in choice:
            console.print("\n[bold cyan]Starting local Web Dashboard at http://127.0.0.1:8765 ...[/bold cyan]")
            launch_web_ui()
            break

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
        d_dir = get_download_dir()
        out_file = str(d_dir / "downloaded_stream.mp4")
        subprocess.run(["yt-dlp", sniffed.url, "-o", out_file, "--referer", url])
        add_history_entry(sniffed.page_title or "Stream", out_file, sniffed.url)
    elif "Record Live" in action:
        d_dir = get_download_dir()
        import time
        out_file = str(d_dir / f"live_record_{int(time.time())}.mp4")
        record_stream(sniffed.url, out_file, headers=sniffed.headers)
        add_history_entry(sniffed.page_title or "Live Stream", out_file, sniffed.url)
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
            d_dir = get_download_dir()
            out = str(d_dir / f"{creator_clean}_live.mp4")
            from .engine import run_ytdlp_download
            run_ytdlp_download(best.url, out, referer=f"https://www.tiktok.com/@{creator_clean}/live", is_live=True)
        elif "Record Stream" in act:
            d_dir = get_download_dir()
            out = str(d_dir / f"{creator_clean}_live.mp4")
            record_stream(best.url, out, headers=result.http_headers)
            add_history_entry(result.title, out, best.url)
        elif "Copy M3U8" in act:
            copy_to_clipboard(best.url)
            console.print("[green][+] Copied .m3u8 URL to clipboard![/green]")

    elif "Watchdog" in mode:
        _start_watchdog(creator_clean)


def _start_watchdog(creator_clean: str):
    d_dir = get_download_dir()
    import time
    def on_live(res):
        out = str(d_dir / f"{creator_clean}_live_{int(time.time())}.mp4")
        hls = next((f for f in res.formats if f.protocol == "m3u8_native"), res.formats[0])
        record_stream(hls.url, out, headers=res.http_headers)
        add_history_entry(res.title, out, hls.url)
    wait_for_live(creator_clean, poll_interval=10, on_live_start=on_live)


def _handle_audio_extract():
    url = questionary.text("Enter stream or video URL to extract MP3 from:").ask()
    if not url or not url.strip():
        return
    url = url.strip()

    d_dir = get_download_dir()
    out_file = str(d_dir / "%(title)s.%(ext)s")
    console.print("\n[bold cyan]Extracting audio track as MP3...[/bold cyan]")
    from .engine import run_ytdlp_download
    run_ytdlp_download(url, out_file, audio_only=True)
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


if __name__ == "__main__":
    run_wizard()

