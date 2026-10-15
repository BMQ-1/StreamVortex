"""
StreamVortex CLI Interface.
Modern, feature-rich command-line interface with cyberpunk styling, Rich tables, and live watchdog.
"""

import sys
import os

if sys.platform == "win32":
    try:
        if sys.stdout.encoding.lower() != "utf-8":
            sys.stdout.reconfigure(encoding="utf-8")
        if sys.stderr.encoding.lower() != "utf-8":
            sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

import re
import argparse
import json
import shutil
import subprocess
from typing import Optional

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text

from .sniffer import smart_sniff
from .tiktok_resolver import resolve_tiktok_live, resolve_tiktok_video, TikTokMediaResult
from .recorder import copy_to_clipboard, send_notification, record_stream, wait_for_live
from .web_ui import launch_web_ui

console = Console()

BANNER = """
   _____ _                              _    _            _            
  / ____| |                            | |  | |          | |           
 | (___ | |_ _ __ ___  __ _ _ __ ___   | |  | | ___  _ __| |_ _____  __
  \___ \| __| '__/ _ \/ _` | '_ ` _ \  | |  | |/ _ \| '__| __/ _ \ \/ /
  ____) | |_| | |  __/ (_| | | | | | | \ \_/ / (_) | |  | ||  __/>  < 
 |_____/ \__|_|  \___|\__,_|_| |_| |_|  \___/ \___/|_|   \__\___/_/\_\ 
"""


def print_banner():
    panel = Panel(
        Text(BANNER, style="bold cyan"),
        subtitle="[bold white]v1.0.0[/bold white] [dim]| Powered by [bold cyan]yt-dlp[/bold cyan] // Resilient Stream Intelligence Engine[/dim]",
        border_style="bright_blue",
        padding=(0, 2)
    )
    console.print(panel)


def display_formats_table(media: TikTokMediaResult):
    table = Table(
        title=f"Available Formats for [bold cyan]{media.uploader}[/bold cyan]",
        border_style="bright_blue",
        header_style="bold magenta",
        show_lines=True
    )
    table.add_column("Format ID", style="bold green")
    table.add_column("Protocol", style="cyan")
    table.add_column("Resolution", style="yellow")
    table.add_column("Bitrate (kbps)", justify="right")
    table.add_column("Codec", style="dim")
    table.add_column("Note", style="italic")

    for f in media.formats:
        res = f"{f.width}x{f.height}" if f.width and f.height else "Unknown"
        tbr = str(f.tbr) if f.tbr else "Auto"
        codec = f.vcodec or "h264"
        table.add_row(
            f.quality_id,
            f.protocol,
            res,
            tbr,
            codec,
            f.format_note or ""
        )

    console.print(table)


def main():
    parser = argparse.ArgumentParser(
        prog="streamvortex",
        description="StreamVortex // Powered by yt-dlp - Resilient Stream Extraction & Watchdog Engine"
    )
    parser.add_argument("url", nargs="?", default="", help="Target live or video URL")
    parser.add_argument("--download", "-d", action="store_true", help="Download stream using yt-dlp")
    parser.add_argument("--record", "-r", action="store_true", help="Record live stream with FFmpeg auto-reconnect")
    parser.add_argument("--play", "-p", action="store_true", help="Play stream in MPV or VLC player")
    parser.add_argument("--copy", "-c", action="store_true", help="Copy extracted stream URL directly to clipboard")
    parser.add_argument("--wait", "-w", action="store_true", help="Watchdog mode: wait until channel goes live, then alert/record")
    parser.add_argument("--web", action="store_true", help="Launch the local Dark-Mode Web UI with embedded HLS player")
    parser.add_argument("--audio", "-a", action="store_true", help="Extract audio only (MP3) from stream or video")
    parser.add_argument("--doctor", action="store_true", help="Run system diagnostics and dependency check")
    parser.add_argument("--wizard", action="store_true", help="Launch beginner-friendly interactive menu")
    parser.add_argument("--m3u8-only", "-m", action="store_true", help="Print only raw stream URL (for piping)")
    parser.add_argument("--json", "-j", action="store_true", help="Output stream metadata in structured JSON")
    parser.add_argument("--timeout", "-t", type=int, default=15, help="Timeout in seconds for stream discovery")
    parser.add_argument("--output", "-o", default=None, help="Output filename for recordings")

    args = parser.parse_args()

    # Doctor check
    if args.doctor:
        from .doctor import run_doctor
        run_doctor()
        return

    # Launch Web UI
    if args.web:
        launch_web_ui()
        return

    # Wizard mode (explicit or when no URL and no other flags passed)
    if args.wizard or (not args.url.strip() and not args.m3u8_only and not args.json):
        from .wizard import run_wizard
        run_wizard()
        return

    url = args.url.strip()

    # Check for TikTok Live
    is_tiktok_live = "tiktok.com" in url and "/live" in url
    is_tiktok_video = "tiktok.com" in url and "/video/" in url

    if not args.m3u8_only and not args.json:
        print_banner()

    # Watchdog wait mode
    if args.wait and is_tiktok_live:
        m = re.search(r'@([\w.-]+)/live', url)
        uploader = m.group(1) if m else url
        def on_live(res):
            hls = next((f for f in res.formats if f.protocol == "m3u8_native"), res.formats[0])
            if args.copy:
                copy_to_clipboard(hls.url)
            if args.record:
                out_name = args.output or f"{uploader}_live_{int(sys.time.time())}.mp4"
                record_stream(hls.url, out_name, headers=res.http_headers)
            elif args.play:
                _play(hls.url)
        wait_for_live(uploader, poll_interval=10, on_live_start=on_live)
        return

    # TikTok Live Resolution
    if is_tiktok_live:
        m = re.search(r'@([\w.-]+)/live', url)
        uploader = m.group(1) if m else None
        if not uploader:
            console.print("[red]Could not parse TikTok username from URL[/red]", file=sys.stderr)
            sys.exit(1)

        with console.status(f"[bold cyan]Resolving TikTok Live for @{uploader}...[/bold cyan]"):
            result = resolve_tiktok_live(uploader, timeout=args.timeout)

        if not result or not result.formats:
            console.print(f"[red][-] Channel @{uploader} is offline or stream could not be resolved.[/red]", file=sys.stderr)
            sys.exit(1)

        hls_formats = [f for f in result.formats if f.protocol == "m3u8_native"]
        best_format = hls_formats[0] if hls_formats else result.formats[0]

        if args.m3u8_only:
            print(best_format.url)
            return

        if args.json:
            print(json.dumps({
                "id": result.media_id,
                "uploader": result.uploader,
                "title": result.title,
                "is_live": result.is_live,
                "formats": [
                    {"id": f.quality_id, "url": f.url, "protocol": f.protocol, "ext": f.ext, "width": f.width, "height": f.height, "tbr": f.tbr}
                    for f in result.formats
                ]
            }, indent=2))
            return

        console.print(f"\n[bold green][+] LIVE DETECTED:[/bold green] [bold white]{result.title}[/bold white]")
        console.print(f"[dim]Uploader:[/dim] @{result.uploader} | [dim]Room ID:[/dim] {result.media_id}\n")

        display_formats_table(result)

        if args.copy:
            copy_to_clipboard(best_format.url)
            send_notification("StreamVortex", f"Copied @{uploader} live stream URL to clipboard!")
            console.print(f"\n[bold green][+] Copied .m3u8 URL to clipboard![/bold green]")

        if args.record:
            out_file = args.output or f"{result.uploader}_live.mp4"
            record_stream(best_format.url, out_file, headers=result.http_headers)
            return

        if args.download or args.audio:
            _download(
                best_format.url,
                args.output or f"{result.uploader}_live.mp4",
                referer=f"https://www.tiktok.com/@{result.uploader}/live",
                audio_only=args.audio,
                is_live=True
            )
            return

        if args.play:
            _play(best_format.url)
            return

        console.print(f"\n[bold cyan]Stream URL:[/bold cyan]\n[underline]{best_format.url}[/underline]\n")
        console.print("[dim]Tip: Add -c to copy to clipboard, -r to record, -a for MP3, or -p to play directly.[/dim]")
        return

    # TikTok Video Resolution
    if is_tiktok_video:
        with console.status("[bold cyan]Resolving TikTok Video without watermarks...[/bold cyan]"):
            result = resolve_tiktok_video(url, timeout=args.timeout)

        if not result or not result.formats:
            console.print("[red][-] Could not extract video stream.[/red]", file=sys.stderr)
            sys.exit(1)

        best_format = result.formats[0]
        if args.m3u8_only:
            print(best_format.url)
            return
        if args.json:
            print(json.dumps({"id": result.media_id, "title": result.title, "url": best_format.url}, indent=2))
            return

        console.print(f"[bold green][+] Video Found:[/bold green] {result.title}")
        display_formats_table(result)

        if args.copy:
            copy_to_clipboard(best_format.url)
            console.print("[bold green][+] Video URL copied to clipboard![/bold green]")
        if args.download or args.audio:
            _download(
                best_format.url,
                args.output or f"tiktok_{result.media_id}.mp4",
                referer=url,
                audio_only=args.audio
            )
        elif args.play:
            _play(best_format.url)
        return

    # Universal Sniffer
    with console.status(f"[bold cyan]Sniffing media wire for {url}...[/bold cyan]"):
        sniffed = smart_sniff(url, timeout=args.timeout)

    if not sniffed:
        console.print("[red][-] No active HLS/FLV/DASH stream detected on page.[/red]", file=sys.stderr)
        sys.exit(1)

    if args.m3u8_only:
        print(sniffed.url)
        return

    if args.json:
        print(json.dumps({
            "url": sniffed.url,
            "stream_type": sniffed.stream_type,
            "title": sniffed.page_title,
            "headers": sniffed.headers,
            "all_streams": sniffed.all_streams
        }, indent=2))
        return

    console.print(f"\n[bold green][+] DISCOVERED {sniffed.stream_type.upper()} STREAM[/bold green]")
    console.print(f"[dim]Title:[/dim] {sniffed.page_title or 'Web Stream'}")
    console.print(f"[bold cyan]URL:[/bold cyan] {sniffed.url}\n")

    if args.copy:
        copy_to_clipboard(sniffed.url)
        console.print("[bold green][+] Stream URL copied to clipboard![/bold green]")

    if args.record:
        record_stream(sniffed.url, args.output or "live_stream.mp4", headers=sniffed.headers)
        return

    if args.download or args.audio:
        _download(
            sniffed.url,
            args.output or "download.mp4",
            referer=url,
            audio_only=args.audio,
            is_live=sniffed.stream_type in ("hls", "flv")
        )
        return

    if args.play:
        _play(sniffed.url, sniffed.headers.get("User-Agent"))
        return


def _play(stream_url: str, user_agent: Optional[str] = None):
    player = shutil.which("mpv") or shutil.which("vlc")
    if not player:
        console.print("[yellow]Neither MPV nor VLC found on system PATH to play directly.[/yellow]")
        console.print(f"URL: {stream_url}")
        return

    cmd = [player, stream_url]
    if user_agent and "mpv" in player.lower():
        cmd.extend([f"--user-agent={user_agent}"])
    console.print(f"[bold cyan]Launching {Path(player).name}...[/bold cyan]")
    subprocess.run(cmd)


from .engine import run_ytdlp_download


def _download(
    stream_url: str,
    output_name: str,
    referer: Optional[str] = None,
    audio_only: bool = False,
    is_live: bool = False
):
    console.print(f"[bold cyan]Running download via yt-dlp ({'MP3 Audio' if audio_only else 'Video'})...[/bold cyan]")
    run_ytdlp_download(
        stream_url=stream_url,
        output_filename=output_name,
        referer=referer,
        audio_only=audio_only,
        is_live=is_live
    )


if __name__ == "__main__":
    main()
