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
from pathlib import Path
from typing import Optional

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text

from .sniffer import smart_sniff
from .tiktok_resolver import resolve_tiktok_live, resolve_tiktok_video, TikTokMediaResult
from .recorder import copy_to_clipboard, send_notification, record_stream, wait_for_live
from .web_ui import launch_web_ui
from .engine import find_ytdlp_conf, sanitize_title_for_filename, run_ytdlp_download, resolve_stream_metadata

console = Console()

BANNER = """
   _____ _                              _    _            _            
  / ____| |                            | |  | |          | |           
 | (___ | |_ _ __ ___  __ _ _ __ ___   | |  | | ___  _ __| |_ _____  __
  \___ \| __| '__/ _ \/ _` | '_ ` _ \  | |  | |/ _ \| '__| __/ _ \ \/ /
  ____) | |_| | |  __/ (_| | | | | | | \ \_/ / (_) | |  | ||  __/>  < 
 |_____/ \__|_|  \___|\__,_|_| |_| |_|  \___/ \___/|_|   \__\___/_/\_\ 
"""


def print_banner(conf_path: Optional[str] = None):
    conf = Path(conf_path) if conf_path else find_ytdlp_conf()
    conf_label = f" [bold yellow]| Config: {conf.name}[/bold yellow]" if conf else ""
    panel = Panel(
        Text(BANNER, style="bold cyan"),
        subtitle=f"[bold white]v1.2[/bold white] [dim]| Powered by [bold cyan]yt-dlp[/bold cyan] // Resilient Stream Intelligence Engine[/dim]{conf_label}",
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
    parser.add_argument("--gui", "-g", action="store_true", help="Launch modern dark-mode Desktop GUI window")
    parser.add_argument("--setup", action="store_true", help="Verify and configure media tools (yt-dlp, FFmpeg, Playwright)")
    parser.add_argument("--onboard", "--install-tools", action="store_true", help="Launch 1-click installer wizard for yt-dlp, FFmpeg, Python, VLC")
    parser.add_argument("--web", action="store_true", help="Launch the local Dark-Mode Web UI with embedded HLS player")
    parser.add_argument("--audio", "-a", action="store_true", help="Extract audio only (MP3) from stream or video")
    parser.add_argument("--doctor", action="store_true", help="Run system diagnostics and dependency check")
    parser.add_argument("--wizard", action="store_true", help="Launch beginner-friendly interactive menu")
    parser.add_argument("--cli", action="store_true", help="Launch interactive terminal wizard")
    parser.add_argument("--m3u8-only", "-m", action="store_true", help="Print only raw stream URL (for piping)")
    parser.add_argument("--json", "-j", action="store_true", help="Output stream metadata in structured JSON")
    parser.add_argument("--conf", "-C", default=None, help="Path to custom yt-dlp.conf configuration file")
    parser.add_argument("--timeout", "-t", type=int, default=15, help="Timeout in seconds for stream discovery")
    parser.add_argument("--output", "-o", default=None, help="Output filename for recordings")
    parser.add_argument("--batch", "-b", default=None, help="Path to text file containing URLs to download sequentially")
    parser.add_argument("--quality", "-q", default="max", choices=["max", "best", "bestquality", "1080p", "720p", "480p", "conf", "audio_mp3", "audio_m4a"], help="Quality profile (default: max | options: max, 1080p, 720p, 480p, conf, audio_mp3, audio_m4a)")
    parser.add_argument("--open-folder", action="store_true", help="Open the downloads directory in file explorer")
    parser.add_argument("--fix", "-F", default=None, help="Path to video file or folder to inspect and repair container (MPEG-TS/FLV/part)")

    args = parser.parse_args()

    # Open downloads directory
    if getattr(args, "open_folder", False):
        from .config import get_download_dir
        d = get_download_dir()
        if sys.platform == "win32":
            os.startfile(d)
        else:
            subprocess.run(["xdg-open", str(d)])
        return

    # Direct container repair tool
    if args.fix:
        from .wizard import _handle_repair_fixup
        from .engine import fixup_recorded_file, sniff_container, EXT_TO_CONTAINER
        target = Path(args.fix.strip().strip("'\"")).expanduser().resolve()
        if not target.exists():
            console.print(f"[bold red][!] File or folder does not exist: {target}[/bold red]")
            return

        targets = []
        if target.is_file():
            targets.append(target)
        elif target.is_dir():
            for ext in ["*.mp4", "*.ts", "*.flv", "*.mkv", "*.part", "*.m4v", "*.mov"]:
                targets.extend([f for f in target.glob(ext) if f.is_file() and f.stat().st_size > 0])
            targets = sorted(list(set(targets)))

        console.print(f"\n[bold cyan]🛠️ StreamVortex Container Repair:[/bold cyan] Scanning {len(targets)} item(s)...")
        for f in targets:
            ext = f.suffix.lower().lstrip(".")
            target_ext = f.with_suffix("").suffix.lower().lstrip(".") if ext == "part" else ext
            have = sniff_container(f)
            if not have:
                continue

            is_flv = (have == "flv" or ext == "flv")
            want = "mp4" if is_flv else EXT_TO_CONTAINER.get(target_ext, "mp4")
            needs_fix = is_flv or (have != want) or (ext == "part")

            if needs_fix:
                dest_desc = "mp4/mkv" if is_flv else want
                console.print(f"[yellow][Fixing][/yellow] {f.name} ({have} -> {dest_desc})")
                res = fixup_recorded_file(f, on_output=lambda line: console.print(f"  [dim]{line}[/dim]"))
                console.print(f"[green]✓ Saved:[/green] {res.name}")
            else:
                console.print(f"[dim]• Clean:[/dim] {f.name} ({have})")
        console.print("[bold green][+] Finished container inspection & repairs![/bold green]\n")
        return

    # Batch file downloader
    if args.batch:
        batch_path = Path(args.batch)
        if not batch_path.exists():
            console.print(f"[bold red][!] Batch file not found: {batch_path}[/bold red]")
            return
        urls = [line.strip() for line in batch_path.read_text(encoding="utf-8").splitlines() if line.strip() and line.strip().startswith("http")]
        console.print(f"[bold cyan][StreamVortex Batch] Queuing {len(urls)} URLs...[/bold cyan]")
        for idx, u in enumerate(urls, 1):
            console.print(f"\n[bold yellow][{idx}/{len(urls)}] Processing: {u}[/bold yellow]")
            meta = resolve_stream_metadata(u)
            run_ytdlp_download(
                stream_url=u,
                title=meta.get("title"),
                uploader=meta.get("uploader"),
                is_live=meta.get("is_live", False),
                audio_only=args.audio or args.quality.startswith("audio_"),
                quality_preference=args.quality,
                on_output=lambda line: console.print(f"[dim]{line}[/dim]"),
                respect_conf_output=True
            )
        console.print("\n[bold green][+] All batch downloads completed![/bold green]")
        return

    # Onboarding & Dependency Provisioner
    if args.onboard or args.setup:
        if args.gui or (not sys.stdin or not sys.stdin.isatty()):
            from .onboarding import launch_onboarding_gui
            launch_onboarding_gui()
        else:
            from .onboarding import run_cli_onboarding
            run_cli_onboarding()
        return

    # Modern Desktop GUI window
    if args.gui:
        from .desktop import launch_desktop_gui
        launch_desktop_gui()
        return

    # Doctor check
    if args.doctor:
        from .doctor import run_doctor
        run_doctor()
        return

    # Launch Web UI
    if args.web:
        launch_web_ui()
        return

    # Explicit wizard mode
    if args.wizard:
        from .wizard import run_wizard
        run_wizard()
        return

    # Default fallback when no URL or flags provided:
    # Starts directly in the interactive terminal wizard using Up/Down arrow keys.
    # Users can navigate with Up/Down buttons or choose option 1 to open the Desktop GUI Studio later!
    if not args.url.strip() and not args.m3u8_only and not args.json:
        from .wizard import run_wizard
        run_wizard()
        return

    url = args.url.strip()

    if not (url.startswith("http://") or url.startswith("https://") or url.startswith("smart:")):
        console.print(f"[red][!] Invalid URL format: '{url}'. Please enter a full URL (e.g. https://www.tiktok.com/@username/live)[/red]")
        return

    # Check for TikTok Live
    is_tiktok_live = "tiktok.com" in url and "/live" in url
    is_tiktok_video = "tiktok.com" in url and "/video/" in url

    if not args.m3u8_only and not args.json:
        print_banner(conf_path=args.conf)

    # Watchdog wait mode
    if args.wait and is_tiktok_live:
        m = re.search(r'@([\w.-]+)/live', url)
        uploader = m.group(1) if m else url
        def on_live(res):
            hls = next((f for f in res.formats if f.protocol == "m3u8_native"), res.formats[0])
            if args.copy:
                copy_to_clipboard(hls.url)
            if args.record:
                out_name = args.output or sanitize_title_for_filename(res.title, uploader=uploader, ext="mp4")
                record_stream(hls.url, out_name, headers=res.http_headers, title=res.title, uploader=uploader)
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
            out_file = args.output or sanitize_title_for_filename(result.title, uploader=result.uploader, ext="mp4")
            record_stream(best_format.url, out_file, headers=result.http_headers, title=result.title, uploader=result.uploader)
            return

        if args.download or args.audio:
            _download(
                best_format.url,
                output_name=args.output,
                referer=f"https://www.tiktok.com/@{result.uploader}/live",
                audio_only=args.audio,
                is_live=True,
                title=result.title,
                uploader=result.uploader,
                conf_path=args.conf
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
                output_name=args.output,
                referer=url,
                audio_only=args.audio,
                title=result.title,
                uploader=result.uploader,
                conf_path=args.conf
            )
        elif args.play:
            _play(best_format.url)
        return

    # Universal Sniffer & Multi-Platform Resolver
    with console.status(f"[bold cyan]Sniffing media wire for {url}...[/bold cyan]"):
        sniffed = smart_sniff(url, timeout=args.timeout)

    if not sniffed:
        meta = resolve_stream_metadata(url, timeout=args.timeout)
        if meta and meta.get("title") != "stream_media" and (args.download or args.audio or args.play):
            console.print(f"\n[bold green][+] RECOGNIZED MEDIA TARGET:[/bold green] [bold white]{meta['title']}[/bold white]")
            if meta.get("uploader"):
                console.print(f"[dim]Uploader:[/dim] @{meta['uploader']}")
            if args.download or args.audio:
                _download(
                    url,
                    output_name=args.output,
                    referer=url,
                    audio_only=args.audio,
                    is_live=meta.get("is_live", False),
                    title=meta.get("title"),
                    uploader=meta.get("uploader"),
                    conf_path=args.conf
                )
                return
            elif args.play:
                _play(url)
                return
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
        out_file = args.output or sanitize_title_for_filename(sniffed.page_title or "live_stream", ext="mp4")
        record_stream(sniffed.url, out_file, headers=sniffed.headers, title=sniffed.page_title)
        return

    if args.download or args.audio:
        _download(
            sniffed.url,
            output_name=args.output,
            referer=url,
            audio_only=args.audio,
            is_live=sniffed.stream_type in ("hls", "flv"),
            title=sniffed.page_title,
            conf_path=args.conf
        )
        return

    if args.play:
        _play(sniffed.url, sniffed.headers.get("User-Agent"))
        return


def _play(stream_url: str, user_agent: Optional[str] = None):
    from .engine import find_player
    player = find_player()
    if not player:
        console.print("[yellow]Neither MPV nor VLC found on system. Launching Onboarding to install VLC...[/yellow]")
        from .onboarding import run_cli_onboarding
        run_cli_onboarding()
        player = find_player()
        if not player:
            console.print(f"URL: {stream_url}")
            return

    cmd = [player, stream_url]
    if user_agent and "mpv" in player.lower():
        cmd.extend([f"--user-agent={user_agent}"])
    console.print(f"[bold cyan]Launching {Path(player).name}...[/bold cyan]")
    subprocess.run(cmd)


def _download(
    stream_url: str,
    output_name: Optional[str] = None,
    referer: Optional[str] = None,
    audio_only: bool = False,
    is_live: bool = False,
    title: Optional[str] = None,
    uploader: Optional[str] = None,
    conf_path: Optional[str] = None
):
    console.print(f"[bold cyan]Running download via yt-dlp ({'MP3 Audio' if audio_only else 'Video'})...[/bold cyan]")
    if title:
        console.print(f"[dim]Title:[/dim] [bold white]{title}[/bold white]")
    run_ytdlp_download(
        stream_url=stream_url,
        output_filename=output_name,
        referer=referer,
        audio_only=audio_only,
        is_live=is_live,
        title=title,
        uploader=uploader,
        conf_path=conf_path
    )


if __name__ == "__main__":
    main()
