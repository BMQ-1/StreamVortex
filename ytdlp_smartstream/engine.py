"""
StreamVortex Unified Execution & Tool Orchestration Engine.
Intelligently locates, configures, and executes yt-dlp, FFmpeg, and aria2c.
Ensures seamless compatibility between user global configs (e.g. C:\\Tools\\yt-dlp.conf)
and live stream requirements.
"""

import sys
import shutil
import subprocess
from pathlib import Path
from typing import Optional, List, Dict, Callable

from .config import get_download_dir, get_config, add_history_entry


def find_ytdlp() -> List[str]:
    """
    Finds the most reliable yt-dlp executable or Python module runner.
    Prioritizes local bin/yt-dlp.exe, then C:\Tools, then PATH.
    """
    # 0. Check local bin/yt-dlp.exe
    if getattr(sys, "frozen", False):
        local_bin = Path(sys.executable).parent / "bin" / "yt-dlp.exe"
    else:
        local_bin = Path(__file__).resolve().parent.parent / "bin" / "yt-dlp.exe"
    if local_bin.exists():
        return [str(local_bin)]

    # 1. Check C:\Tools\yt-dlp.exe
    tool_bin = Path("C:/Tools/yt-dlp.exe")
    if tool_bin.exists():
        return [str(tool_bin)]

    # 2. Check system PATH
    which_bin = shutil.which("yt-dlp")
    if which_bin:
        return [which_bin]

    # 3. Fallback to python module
    return [sys.executable, "-m", "yt_dlp"]


def find_ffmpeg() -> Optional[str]:
    """
    Locates FFmpeg executable across local bin/, C:\Tools, and system PATH.
    """
    # 0. Check local bin/ffmpeg.exe
    if getattr(sys, "frozen", False):
        local_bin = Path(sys.executable).parent / "bin" / "ffmpeg.exe"
    else:
        local_bin = Path(__file__).resolve().parent.parent / "bin" / "ffmpeg.exe"
    if local_bin.exists():
        return str(local_bin)

    # 1. Check C:\Tools\ffmpeg.exe
    tool_bin = Path("C:/Tools/ffmpeg.exe")
    if tool_bin.exists():
        return str(tool_bin)

    # 2. Check system PATH
    which_bin = shutil.which("ffmpeg")
    if which_bin:
        return which_bin

    return None


def run_ytdlp_download(
    stream_url: str,
    output_filename: Optional[str] = None,
    referer: Optional[str] = None,
    audio_only: bool = False,
    is_live: bool = False,
    quality_preference: Optional[str] = None,
    on_output: Optional[Callable[[str], None]] = None
) -> int:
    """
    Executes a yt-dlp download with foolproof parameters:
    - If is_live=True: overrides incompatible external downloaders (like aria2c)
      by using native HLS streaming downloader.
    - If audio_only=True: extracts audio and transcodes to high-quality MP3.
    - Saves output in user's configured download directory if relative path.
    """
    ytdlp_cmd = find_ytdlp()
    d_dir = get_download_dir()

    # Determine output path
    if output_filename:
        out_path = Path(output_filename)
        if not out_path.is_absolute():
            out_path = d_dir / out_path
    else:
        ext = "mp3" if audio_only else "%(ext)s"
        out_path = d_dir / f"%(title).80B_%(id)s.{ext}"

    cmd = list(ytdlp_cmd)
    cmd.append(stream_url)

    # Handle Audio Extraction
    if audio_only:
        cmd.extend([
            "-x",
            "--audio-format", "mp3",
            "--audio-quality", "0",
        ])

    # Handle Live Streams: Override aria2c conflicts from yt-dlp.conf
    if is_live:
        # Use native downloader for m3u8 fragments to prevent aria2c crash
        cmd.extend([
            "--downloader", "m3u8:native",
            "--no-part",
        ])

    # Quality selector override if requested
    if quality_preference and quality_preference != "best":
        if "720" in quality_preference:
            cmd.extend(["-f", "best[height<=720]/best"])
        elif "1080" in quality_preference:
            cmd.extend(["-f", "best[height<=1080]/best"])
        elif "480" in quality_preference:
            cmd.extend(["-f", "best[height<=480]/best"])
    else:
        # Default fallback so strict configs (e.g. av01/vp9 only) don't reject H264 lives
        if is_live:
            cmd.extend(["-f", "best/b"])

    # Output template
    cmd.extend(["-o", str(out_path)])

    # Headers
    if referer:
        cmd.extend(["--referer", referer])

    # Add console title & progress
    cmd.extend(["--no-mtime", "--progress"])

    # Run process
    if on_output:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace"
        )
        for line in proc.stdout:
            on_output(line.strip())
        proc.wait()
        retcode = proc.returncode
    else:
        retcode = subprocess.run(cmd).returncode

    if retcode == 0:
        add_history_entry(
            title=Path(out_path).stem,
            filename=str(out_path),
            stream_url=stream_url,
            media_type="audio" if audio_only else "video"
        )

    return retcode


def run_ffmpeg_record(
    stream_url: str,
    output_filename: str,
    headers: Optional[Dict[str, str]] = None,
    max_duration_seconds: Optional[int] = None
) -> int:
    """
    Direct, lossless stream recording via FFmpeg.
    Copies audio and video packets directly without re-encoding (0% CPU impact).
    """
    ffmpeg_bin = find_ffmpeg()
    if not ffmpeg_bin:
        # Fallback to yt-dlp
        return run_ytdlp_download(stream_url, output_filename, is_live=True)

    d_dir = get_download_dir()
    out_path = Path(output_filename)
    if not out_path.is_absolute():
        out_path = d_dir / out_path

    cmd = [
        ffmpeg_bin,
        "-y",
        "-reconnect", "1",
        "-reconnect_at_eof", "1",
        "-reconnect_streamed", "1",
        "-reconnect_delay_max", "5",
    ]

    if headers:
        header_lines = [f"{k}: {v}" for k, v in headers.items()]
        cmd.extend(["-headers", "\r\n".join(header_lines) + "\r\n"])

    cmd.extend(["-i", stream_url])

    if max_duration_seconds:
        cmd.extend(["-t", str(max_duration_seconds)])

    # Lossless stream copy
    cmd.extend(["-c", "copy", str(out_path)])

    proc = subprocess.run(cmd)
    if proc.returncode == 0:
        add_history_entry(
            title=out_path.stem,
            filename=str(out_path),
            stream_url=stream_url,
            media_type="live_record"
        )
    return proc.returncode
