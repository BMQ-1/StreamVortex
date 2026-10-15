"""
StreamVortex Unified Execution & Tool Orchestration Engine.
Intelligently locates, configures, and executes yt-dlp, FFmpeg, and aria2c.
Automatically finds user .conf files across system locations and ensures
they are correctly loaded, while dynamically resolving and applying the actual
titles of videos and live streams.
"""

import sys
import os
import re
import json
import shutil
import subprocess
from pathlib import Path
from typing import Optional, List, Dict, Any, Callable

from .config import get_download_dir, get_config, add_history_entry


def find_ytdlp() -> List[str]:
    """
    Finds the most reliable yt-dlp executable or Python module runner.
    Prioritizes local bin/yt-dlp.exe, then C:\\Tools, then PATH.
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
    Locates FFmpeg executable across local bin/, C:\\Tools, and system PATH.
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


def find_ytdlp_conf(is_tiktok_live: bool = False, custom_conf: Optional[str] = None) -> Optional[Path]:
    """
    Intelligently locates the user's yt-dlp configuration file (.conf).
    Prioritizes:
    1. Explicit custom path or configured in ~/.streamvortex/config.json
    2. C:\\Tools\\tiktok-live.conf.txt (if is_tiktok_live is True)
    3. C:\\Tools\\yt-dlp.conf (user primary config)
    4. Project root yt-dlp.conf or bin/yt-dlp.conf
    5. %APPDATA%\\yt-dlp\\config or %APPDATA%\\yt-dlp.conf
    6. %USERPROFILE%\\yt-dlp.conf or ~/.config/yt-dlp/config
    7. Current working directory yt-dlp.conf
    """
    if custom_conf and Path(custom_conf).exists():
        return Path(custom_conf)

    # 1. Config in ~/.streamvortex/config.json
    try:
        cfg = get_config()
        saved_conf = cfg.get("ytdlp_conf_path")
        if saved_conf and Path(saved_conf).exists():
            return Path(saved_conf)
    except Exception:
        pass

    # 2. Specialized TikTok live config
    if is_tiktok_live:
        tiktok_conf = Path("C:/Tools/tiktok-live.conf.txt")
        if tiktok_conf.exists():
            return tiktok_conf

    # 3. User preferred C:\Tools\yt-dlp.conf
    c_tools_conf = Path("C:/Tools/yt-dlp.conf")
    if c_tools_conf.exists():
        return c_tools_conf

    # 4. Project root or bin/
    try:
        project_root = Path(__file__).resolve().parent.parent
        for p in [project_root / "yt-dlp.conf", project_root / "bin" / "yt-dlp.conf"]:
            if p.exists():
                return p
    except Exception:
        pass

    # 5. Standard yt-dlp config directories
    try:
        from yt_dlp.utils import get_user_config_dirs
        for d in get_user_config_dirs("yt-dlp"):
            for name in ["config", "config.txt", "yt-dlp.conf"]:
                cand = Path(d) / name
                if cand.exists():
                    return cand
    except Exception:
        pass

    # 6. User profile
    user_home = Path.home()
    for cand in [user_home / "yt-dlp.conf", user_home / ".config" / "yt-dlp" / "config"]:
        if cand.exists():
            return cand

    # 7. Current directory
    cwd_conf = Path.cwd() / "yt-dlp.conf"
    if cwd_conf.exists():
        return cwd_conf

    return None


def conf_has_output_template(conf_path: Path) -> bool:
    """Checks whether the configuration file defines an output template (-o / --output)."""
    if not conf_path.exists():
        return False
    try:
        with open(conf_path, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                line = line.strip()
                if line.startswith("#"):
                    continue
                if line.startswith("-o ") or line.startswith("-o\t") or line == "-o" or line.startswith("--output"):
                    return True
    except Exception:
        pass
    return False


def sanitize_filename(name: str, max_length: int = 150) -> str:
    """Sanitizes a string to be a safe, clean Windows/Unix filename."""
    if not name:
        return "media"
    # Replace invalid Windows filename characters: \ / : * ? " < > |
    invalid_chars = r'\/:*?"<>|'
    cleaned = "".join(c if c not in invalid_chars else (" - " if c in ":/" else " ") for c in name)
    cleaned = "".join(c for c in cleaned if c.isprintable())
    cleaned = " ".join(cleaned.split())
    cleaned = cleaned.strip(". ")
    if not cleaned:
        cleaned = "media"
    return cleaned[:max_length].rstrip(". ")


def sanitize_title_for_filename(
    title: str,
    uploader: Optional[str] = None,
    ext: str = "mp4",
    max_len: int = 150
) -> str:
    """
    Constructs a clean, safe, descriptive filename using the actual title and creator name.
    """
    if not title or title.strip() in ("", "download", "stream", "video", "media"):
        raw_name = f"{uploader}_live" if uploader else "stream_video"
    else:
        title = title.strip()
        # If uploader is provided and not already in title, prefix it
        if uploader and uploader.lower() not in title.lower():
            raw_name = f"{uploader} - {title}"
        else:
            raw_name = title

    base = sanitize_filename(raw_name, max_length=max_len)
    return f"{base}.{ext}"


def resolve_stream_metadata(url: str, timeout: int = 8) -> Dict[str, Any]:
    """
    Universal metadata resolver for any stream or video in the world.
    Extracts actual title, creator, thumbnail, and stream properties.
    """
    url = url.strip()

    # 1. TikTok Live
    if "tiktok.com" in url and "/live" in url:
        m = re.search(r'@([\w.-]+)/live', url)
        uploader = m.group(1) if m else "creator"
        try:
            from .tiktok_resolver import resolve_tiktok_live
            res = resolve_tiktok_live(uploader, timeout=timeout)
            if res and res.formats:
                return {
                    "title": res.title,
                    "uploader": res.uploader,
                    "is_live": True,
                    "id": res.media_id,
                    "formats": [
                        {"id": f.quality_id, "url": f.url, "protocol": f.protocol, "ext": f.ext, "width": f.width, "height": f.height}
                        for f in res.formats
                    ],
                    "suggested_filename": sanitize_title_for_filename(res.title, uploader=res.uploader, ext="mp4")
                }
        except Exception:
            pass

    # 2. TikTok Video (VOD)
    if "tiktok.com" in url and "/video/" in url:
        try:
            from .tiktok_resolver import resolve_tiktok_video
            res = resolve_tiktok_video(url, timeout=timeout)
            if res and res.formats:
                return {
                    "title": res.title,
                    "uploader": res.uploader,
                    "is_live": False,
                    "id": res.media_id,
                    "formats": [
                        {"id": f.quality_id, "url": f.url, "protocol": f.protocol, "ext": f.ext}
                        for f in res.formats
                    ],
                    "suggested_filename": sanitize_title_for_filename(res.title, uploader=res.uploader, ext="mp4")
                }
        except Exception:
            pass

    # 3. Global yt-dlp probe (YouTube, Twitch, Kick, Vimeo, etc.)
    ytdlp_cmd = find_ytdlp()
    try:
        probe_cmd = list(ytdlp_cmd) + ["--dump-json", "--skip-download", "--no-warnings", url]
        conf = find_ytdlp_conf()
        if conf:
            probe_cmd.extend(["--config-locations", str(conf)])

        res = subprocess.run(probe_cmd, capture_output=True, text=True, timeout=timeout, encoding="utf-8", errors="replace")
        if res.returncode == 0 and res.stdout.strip():
            data = json.loads(res.stdout.splitlines()[0])
            title = data.get("title") or "video"
            uploader = data.get("uploader") or data.get("channel") or ""
            is_live = bool(data.get("is_live"))
            return {
                "title": title,
                "uploader": uploader,
                "is_live": is_live,
                "id": data.get("id"),
                "thumbnail": data.get("thumbnail"),
                "duration": data.get("duration"),
                "suggested_filename": sanitize_title_for_filename(title, uploader=uploader, ext="mp4")
            }
    except Exception:
        pass

    # 4. Universal Web Sniffer fallback
    try:
        from .sniffer import smart_sniff
        sniffed = smart_sniff(url, timeout=timeout)
        if sniffed:
            title = sniffed.page_title or "Web Stream"
            return {
                "title": title,
                "uploader": "",
                "is_live": sniffed.stream_type in ("hls", "flv"),
                "id": url,
                "formats": [{"id": f"{sniffed.stream_type}-main", "url": sniffed.url, "protocol": "m3u8_native" if sniffed.stream_type == "hls" else "https"}],
                "suggested_filename": sanitize_title_for_filename(title, ext="mp4")
            }
    except Exception:
        pass

    return {
        "title": "stream_media",
        "uploader": "",
        "is_live": False,
        "id": "unknown",
        "suggested_filename": "stream_media.mp4"
    }


def run_ytdlp_download(
    stream_url: str,
    output_filename: Optional[str] = None,
    referer: Optional[str] = None,
    audio_only: bool = False,
    is_live: bool = False,
    quality_preference: Optional[str] = None,
    on_output: Optional[Callable[[str], None]] = None,
    conf_path: Optional[str] = None,
    title: Optional[str] = None,
    uploader: Optional[str] = None,
    respect_conf_output: bool = True
) -> int:
    """
    Executes a yt-dlp download with intelligent configuration management & title resolution:
    - Automatically discovers and injects the user's .conf file (e.g. C:\\Tools\\yt-dlp.conf).
    - If is_live=True: overrides incompatible external downloaders (like aria2c)
      by using native HLS/m3u8 streaming, ensuring lives download smoothly.
    - If audio_only=True: extracts audio and transcodes to high-quality MP3.
    - Always names the resulting file using the actual title of the video or live.
    - If the user's .conf defines an output template (-o) and output_filename is None,
      respects and uses the user's configured output template!
    """
    ytdlp_cmd = find_ytdlp()
    d_dir = get_download_dir()

    cmd = list(ytdlp_cmd)

    # 1. Config Discovery & Injection
    is_tiktok_live = "tiktok.com" in stream_url and "/live" in stream_url
    conf = Path(conf_path) if conf_path else find_ytdlp_conf(is_tiktok_live=is_tiktok_live)

    if conf and conf.exists():
        cmd.extend(["--config-locations", str(conf)])
        msg = f"[StreamVortex] Using yt-dlp configuration: {conf}"
        if on_output:
            on_output(msg)
        else:
            print(msg)

    cmd.append(stream_url)

    # 2. Output Filename & Template Handling
    has_conf_output = conf_has_output_template(conf) if conf else False
    out_path_label = ""

    if output_filename:
        out_path = Path(output_filename)
        if not out_path.is_absolute():
            out_path = d_dir / out_path
        cmd.extend(["-o", str(out_path)])
        out_path_label = str(out_path)
    elif title:
        # Caller provided actual title: format safe name
        safe_name = sanitize_title_for_filename(title, uploader=uploader, ext="mp3" if audio_only else "mp4")
        out_path = d_dir / safe_name
        cmd.extend(["-o", str(out_path)])
        out_path_label = str(out_path)
    elif has_conf_output and respect_conf_output:
        # Config file defines its own output template (e.g. C:\Tools\Videos\%(title)s.%(ext)s)
        # Do not override -o on CLI; yt-dlp will naturally apply the .conf template!
        out_path_label = "Configured in yt-dlp.conf"
    else:
        # Default to actual title template in download directory
        ext = "mp3" if audio_only else "%(ext)s"
        out_path = d_dir / f"%(title).90B [%(id)s].{ext}"
        cmd.extend(["-o", str(out_path)])
        out_path_label = str(out_path)

    # 3. Handle Audio Extraction
    if audio_only:
        cmd.extend([
            "-x",
            "--audio-format", "mp3",
            "--audio-quality", "0",
        ])

    # 4. Handle Live Streams: Override aria2c conflicts from yt-dlp.conf
    if is_live:
        # Use native m3u8 downloader and fallback format so live streams don't crash
        cmd.extend([
            "--downloader", "m3u8:native",
            "--no-part",
            "-f", "best/b",
        ])
    elif quality_preference and quality_preference != "best":
        if "720" in quality_preference:
            cmd.extend(["-f", "best[height<=720]/best"])
        elif "1080" in quality_preference:
            cmd.extend(["-f", "best[height<=1080]/best"])
        elif "480" in quality_preference:
            cmd.extend(["-f", "best[height<=480]/best"])

    # 5. Headers & Flags
    if referer:
        cmd.extend(["--referer", referer])

    cmd.extend(["--no-mtime", "--progress"])

    # 6. Run process with live output streaming
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
        entry_title = title or (Path(out_path_label).stem if out_path_label != "Configured in yt-dlp.conf" else "Downloaded Media")
        add_history_entry(
            title=entry_title,
            filename=out_path_label,
            stream_url=stream_url,
            media_type="audio" if audio_only else ("live" if is_live else "video")
        )

    return retcode


def run_ffmpeg_record(
    stream_url: str,
    output_filename: Optional[str] = None,
    headers: Optional[Dict[str, str]] = None,
    max_duration_seconds: Optional[int] = None,
    title: Optional[str] = None,
    uploader: Optional[str] = None
) -> int:
    """
    Direct, lossless stream recording via FFmpeg.
    Automatically generates descriptive filenames using the actual title and uploader.
    """
    ffmpeg_bin = find_ffmpeg()
    if not ffmpeg_bin:
        return run_ytdlp_download(stream_url, output_filename=output_filename, title=title, uploader=uploader, is_live=True)

    d_dir = get_download_dir()

    if output_filename:
        out_path = Path(output_filename)
        if not out_path.is_absolute():
            out_path = d_dir / out_path
    elif title:
        safe_name = sanitize_title_for_filename(title, uploader=uploader, ext="mp4")
        out_path = d_dir / safe_name
    else:
        import time
        out_path = d_dir / f"live_stream_{int(time.time())}.mp4"

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
            title=title or out_path.stem,
            filename=str(out_path),
            stream_url=stream_url,
            media_type="live_record"
        )
    return proc.returncode
