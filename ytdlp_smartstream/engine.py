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
import threading
import urllib.parse
from pathlib import Path
from typing import Optional, List, Dict, Any, Callable, Tuple

from .config import get_download_dir, get_config, add_history_entry


def find_global_python() -> str:
    """
    Locates the global Python executable on the device.
    Prioritizes the system PATH Python, then standard global installation directories.
    """
    which_py = shutil.which("python") or shutil.which("python3")
    if which_py:
        return which_py

    user_home = Path.home()
    candidates = [
        user_home / "AppData/Local/Programs/Python/Python311/python.exe",
        user_home / "AppData/Local/Programs/Python/Python312/python.exe",
        user_home / "AppData/Local/Programs/Python/Python310/python.exe",
        user_home / "AppData/Local/Programs/Python/Python39/python.exe",
        Path("C:/Python311/python.exe"),
        Path("C:/Python312/python.exe"),
        Path("C:/Python310/python.exe"),
        Path("C:/Program Files/Python311/python.exe"),
        Path("C:/Program Files/Python312/python.exe"),
    ]
    for cand in candidates:
        if cand.exists():
            return str(cand)

    return sys.executable


def find_ytdlp() -> List[str]:
    """
    Locates the global yt-dlp executable on the device.
    Prioritizes:
    1. System PATH (e.g. C:\\Tools\\yt-dlp.exe)
    2. C:\\Tools\\yt-dlp.exe
    3. Global WinGet / AppData / ProgramFiles installations
    4. Global Python module (python -m yt_dlp)
    5. Local project fallback (only if no global yt-dlp is available)
    """
    # 1. Check system PATH (Global)
    which_bin = shutil.which("yt-dlp")
    if which_bin:
        return [which_bin]

    # 2. Check configured tools_dir
    try:
        saved_tools = get_config().get("tools_dir")
        if saved_tools:
            p = Path(saved_tools) / "yt-dlp.exe"
            if p.exists():
                return [str(p)]
    except Exception:
        pass

    # 3. Check C:\Tools\yt-dlp.exe (Global)
    c_tools = Path("C:/Tools/yt-dlp.exe")
    if c_tools.exists():
        return [str(c_tools)]

    # 4. Check standard global package locations
    user_home = Path.home()
    candidates = [
        user_home / "AppData/Local/Microsoft/WinGet/Links/yt-dlp.exe",
        user_home / "AppData/Local/yt-dlp/yt-dlp.exe",
        Path("C:/Program Files/yt-dlp/yt-dlp.exe"),
        Path("C:/ProgramData/chocolatey/bin/yt-dlp.exe"),
    ]
    for cand in candidates:
        if cand.exists():
            return [str(cand)]

    # 5. Check global Python environment for yt_dlp module
    global_py = find_global_python()
    try:
        res = subprocess.run([global_py, "-m", "yt_dlp", "--version"], capture_output=True, text=True, timeout=2)
        if res.returncode == 0:
            return [global_py, "-m", "yt_dlp"]
    except Exception:
        pass

    # 6. Fallback to local project bin/yt-dlp.exe only if no global tool exists
    if getattr(sys, "frozen", False):
        local_bin = Path(sys.executable).parent / "bin" / "yt-dlp.exe"
    else:
        local_bin = Path(__file__).resolve().parent.parent / "bin" / "yt-dlp.exe"
    if local_bin.exists():
        return [str(local_bin)]

    return [sys.executable, "-m", "yt_dlp"]


def find_ffmpeg() -> Optional[str]:
    """
    Locates the global FFmpeg executable on the device.
    Prioritizes:
    1. System PATH (e.g. C:\\ffmpeg_folder\\... or C:\\Tools\\ffmpeg.exe)
    2. Configured tools_dir from onboarding
    3. C:\\ffmpeg_folder\\ffmpeg-essentials_build\\bin\\ffmpeg.exe
    4. C:\\Tools\\ffmpeg.exe
    5. Other standard global paths
    6. Local fallback (only if no global FFmpeg is available)
    """
    # 1. Check system PATH (Global)
    which_bin = shutil.which("ffmpeg")
    if which_bin:
        return which_bin

    # 2. Check configured tools_dir
    try:
        saved_tools = get_config().get("tools_dir")
        if saved_tools:
            p = Path(saved_tools) / "ffmpeg.exe"
            if p.exists():
                return str(p)
    except Exception:
        pass

    # 3. Known global paths
    candidates = [
        Path("C:/ffmpeg_folder/ffmpeg-essentials_build/bin/ffmpeg.exe"),
        Path("C:/ffmpeg_folder/bin/ffmpeg.exe"),
        Path("C:/Tools/ffmpeg.exe"),
        Path("C:/ffmpeg/bin/ffmpeg.exe"),
        Path("C:/Program Files/ffmpeg/bin/ffmpeg.exe"),
        Path.home() / "AppData/Local/Microsoft/WinGet/Links/ffmpeg.exe",
        Path("C:/ProgramData/chocolatey/bin/ffmpeg.exe"),
    ]
    for cand in candidates:
        if cand.exists():
            return str(cand)

    # 4. Fallback: Local project bin/ffmpeg.exe (only if no global exists)
    if getattr(sys, "frozen", False):
        local_bin = Path(sys.executable).parent / "bin" / "ffmpeg.exe"
    else:
        local_bin = Path(__file__).resolve().parent.parent / "bin" / "ffmpeg.exe"
    if local_bin.exists():
        return str(local_bin)

    return None


def find_ffprobe() -> Optional[str]:
    """
    Locates the global FFprobe executable on the device.
    """
    # 1. Check system PATH (Global)
    which_bin = shutil.which("ffprobe")
    if which_bin:
        return which_bin

    # 2. Adjacent to detected ffmpeg
    ff_bin = find_ffmpeg()
    if ff_bin:
        adjacent = Path(ff_bin).parent / "ffprobe.exe"
        if adjacent.exists():
            return str(adjacent)

    # 3. Check configured tools_dir
    try:
        saved_tools = get_config().get("tools_dir")
        if saved_tools:
            p = Path(saved_tools) / "ffprobe.exe"
            if p.exists():
                return str(p)
    except Exception:
        pass

    # 4. Known global paths
    candidates = [
        Path("C:/ffmpeg_folder/ffmpeg-essentials_build/bin/ffprobe.exe"),
        Path("C:/ffmpeg_folder/bin/ffprobe.exe"),
        Path("C:/Tools/ffprobe.exe"),
        Path("C:/ffmpeg/bin/ffprobe.exe"),
        Path("C:/Program Files/ffmpeg/bin/ffprobe.exe"),
    ]
    for cand in candidates:
        if cand.exists():
            return str(cand)

    # 5. Fallback: Local project bin/ffprobe.exe
    if getattr(sys, "frozen", False):
        local_bin = Path(sys.executable).parent / "bin" / "ffprobe.exe"
    else:
        local_bin = Path(__file__).resolve().parent.parent / "bin" / "ffprobe.exe"
    if local_bin.exists():
        return str(local_bin)

    return None


def find_player() -> Optional[str]:
    """
    Locates the best available media player on the device (MPV or VLC).
    Checks system PATH, configured tools directory, and standard Windows install paths.
    """
    # 1. MPV on PATH
    mpv = shutil.which("mpv")
    if mpv:
        return mpv

    # 2. VLC on PATH
    vlc = shutil.which("vlc")
    if vlc:
        return vlc

    # 3. Check in configured tools_dir
    try:
        tools_dir = get_config().get("tools_dir")
        if tools_dir:
            for name in ["mpv.exe", "vlc.exe"]:
                p = Path(tools_dir) / name
                if p.exists():
                    return str(p)
    except Exception:
        pass

    # 4. Standard VLC install locations
    for cand in [
        Path(os.environ.get("PROGRAMFILES", "C:/Program Files")) / "VideoLAN" / "VLC" / "vlc.exe",
        Path(os.environ.get("PROGRAMFILES(X86)", "C:/Program Files (x86)")) / "VideoLAN" / "VLC" / "vlc.exe",
        Path("C:/Program Files/VideoLAN/VLC/vlc.exe"),
        Path("C:/Program Files (x86)/VideoLAN/VLC/vlc.exe"),
    ]:
        if cand.exists():
            return str(cand)

    return None


def is_environment_ready() -> bool:
    """Returns True if essential extraction tools (yt-dlp and FFmpeg) are ready."""
    ytdlp = find_ytdlp()
    ffmpeg = find_ffmpeg()
    return bool(ytdlp and ffmpeg)


def find_aria2c() -> Optional[str]:
    """
    Locates the aria2c multi-connection download accelerator executable.
    Checks system PATH, C:\\Tools, adjacent to yt-dlp.exe, and project bin folder.
    """
    which_bin = shutil.which("aria2c")
    if which_bin:
        return which_bin

    # Adjacent to detected yt-dlp
    ytdlp_cmd = find_ytdlp()
    if ytdlp_cmd and not ytdlp_cmd[0].endswith(".py") and "-m" not in ytdlp_cmd:
        p = Path(ytdlp_cmd[0]).parent / "aria2c.exe"
        if p.exists():
            return str(p)

    # Standard C:\Tools
    for cand in [Path("C:/Tools/aria2c.exe"), Path("C:/Tools/aria2/aria2c.exe")]:
        if cand.exists():
            return str(cand)

    # Local bin
    if getattr(sys, "frozen", False):
        local_bin = Path(sys.executable).parent / "bin" / "aria2c.exe"
    else:
        local_bin = Path(__file__).resolve().parent.parent / "bin" / "aria2c.exe"
    if local_bin.exists():
        return str(local_bin)

    return None


DEFAULT_YTDLP_CONF_TEMPLATE = """# ========================================================
# StreamVortex Optimized yt-dlp Configuration
# Auto-generated by StreamVortex Engine
# ========================================================

# ===== OUTPUT =====
-o "{dest_dir}\\%(playlist|)s\\%(title).70B_%(epoch)s.%(ext)s"
-o "subtitle:{dest_dir}\\Subs\\%(title).70B_%(epoch)s.%(ext)s"
-o "thumbnail:{dest_dir}\\Thumbnails\\%(title).70B_%(epoch)s.%(ext)s"

# ===== FORMAT PRIORITY =====
# 🥈 Start at 2K → 1080p fallback (skip 4K entirely)
-f "(bestvideo[vcodec~='^av01'][height>=1440]+bestaudio[acodec=opus]/bestvideo[vcodec~='^vp9'][height>=1440]+bestaudio[acodec=opus]/bestvideo[height>=1440]+bestaudio[acodec=opus]/bestvideo[vcodec~='^av01'][height>=1080]+bestaudio[acodec=opus]/bestvideo[vcodec~='^vp9'][height>=1080]+bestaudio[acodec=opus]/bestvideo[height>=1080]+bestaudio[acodec=opus]/bestvideo+bestaudio/best)"
-S "hdr,res,fps,vcodec:av01,acodec:opus"
--merge-output-format mkv

# ===== EXTERNAL DOWNLOADER (aria2c) =====
--downloader aria2c
--downloader-args "aria2c:-x 16 -s 16 -k 1M"

# ===== THUMBNAIL =====
--write-thumbnail
--embed-thumbnail
--convert-thumbnail jpg

# ===== NETWORK =====
--force-ipv4
--retries 10
--fragment-retries 20
--sleep-interval 1
--max-sleep-interval 3
--js-runtimes node
-N 6

# ===== SUBTITLES =====
--write-subs
--sub-langs "en"
--sub-format "vtt/srt/best"
--convert-subs srt

# ===== SPONSORBLOCK =====
--sponsorblock-mark all

# ===== DOWNLOAD QUALITY OF LIFE =====
--continue
--no-mtime

# ===== OUTPUT CONSOLE =====
--console-title
--progress
"""


def deploy_embedded_ytdlp_conf(target_dir: Optional[Path] = None, downloads_dir: Optional[Path] = None) -> Optional[Path]:
    """
    Automatically deploys the embedded, optimized yt-dlp.conf directly next to yt-dlp.exe.
    Called when the executable is run or on first media download if no conf exists.
    Ensures users get the .conf next to yt-dlp.exe without needing it cloned in the repo.
    """
    dest_download = (downloads_dir or get_download_dir()).expanduser().resolve()
    dest_download.mkdir(parents=True, exist_ok=True)

    dest_tools = target_dir
    if not dest_tools:
        ytdlp_cmd = find_ytdlp()
        if ytdlp_cmd and not ytdlp_cmd[0].endswith(".py") and "-m" not in ytdlp_cmd:
            exe_p = Path(ytdlp_cmd[0])
            if exe_p.exists():
                dest_tools = exe_p.parent

    if not dest_tools:
        c_tools = Path("C:/Tools")
        try:
            c_tools.mkdir(parents=True, exist_ok=True)
            dest_tools = c_tools
        except Exception:
            dest_tools = Path.home() / "Tools"

    dest_tools.mkdir(parents=True, exist_ok=True)
    conf_target = dest_tools / "yt-dlp.conf"

    if not conf_target.exists():
        conf_str = DEFAULT_YTDLP_CONF_TEMPLATE.replace("{dest_dir}", str(dest_download).replace("/", "\\"))
        try:
            conf_target.write_text(conf_str, encoding="utf-8")
        except Exception:
            pass

    return conf_target if conf_target.exists() else None


def find_ytdlp_conf(custom_conf: Optional[str] = None) -> Optional[Path]:
    """
    Locates or automatically deploys the user's global yt-dlp configuration file (.conf).
    Prioritizes yt-dlp's native portable location directly next to yt-dlp.exe:
    1. Explicit custom path or configured in ~/.streamvortex/config.json
    2. Directly adjacent to global yt-dlp.exe (e.g. C:\\Tools\\yt-dlp.conf)
    3. C:\\Tools\\yt-dlp.conf
    4. Standard user config directories (%APPDATA%\\yt-dlp\\config, %USERPROFILE%\\yt-dlp.conf)
    5. Automatic On-Demand Deployment: If no config exists, generates and deploys the
       embedded, optimized yt-dlp.conf directly next to yt-dlp.exe!
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

    # 2. Look DIRECTLY NEXT TO THE GLOBAL yt-dlp.exe! (yt-dlp's native portable configuration)
    ytdlp_cmd = find_ytdlp()
    ytdlp_dir = None
    if ytdlp_cmd and not ytdlp_cmd[0].endswith(".py") and "-m" not in ytdlp_cmd:
        ytdlp_exe_path = Path(ytdlp_cmd[0])
        if ytdlp_exe_path.exists():
            ytdlp_dir = ytdlp_exe_path.parent
            for name in ["yt-dlp.conf", "yt-dlp.conf.txt", "config.txt", "config"]:
                adjacent_conf = ytdlp_dir / name
                if adjacent_conf.exists():
                    return adjacent_conf

    # 3. Standard C:\Tools\yt-dlp.conf
    c_tools_conf = Path("C:/Tools/yt-dlp.conf")
    if c_tools_conf.exists():
        return c_tools_conf

    # 4. Standard yt-dlp config directories
    try:
        from yt_dlp.utils import get_user_config_dirs
        for d in get_user_config_dirs("yt-dlp"):
            for name in ["config", "config.txt", "yt-dlp.conf"]:
                cand = Path(d) / name
                if cand.exists():
                    return cand
    except Exception:
        pass

    # 5. User profile
    user_home = Path.home()
    for cand in [user_home / "yt-dlp.conf", user_home / ".config" / "yt-dlp" / "config"]:
        if cand.exists():
            return cand

    # 6. Automatic Deployment: Built right into the executable!
    # Deploys the optimized yt-dlp.conf directly next to yt-dlp.exe (or in C:\Tools)
    deployed = deploy_embedded_ytdlp_conf(ytdlp_dir)
    if deployed and deployed.exists():
        return deployed

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


def get_conf_download_dir(conf_path: Optional[Path] = None) -> Path:
    """
    Extracts the active download directory specified in yt-dlp.conf.
    If not specified or relative/placeholder, defaults cleanly to user's Downloads directory.
    """
    target_conf = conf_path or find_ytdlp_conf()
    if target_conf and target_conf.exists():
        try:
            content = target_conf.read_text(encoding="utf-8", errors="ignore")
            for line in content.splitlines():
                line = line.strip()
                if line.startswith("-o ") and not line.startswith("-o subtitle:") and not line.startswith("-o thumbnail:"):
                    val = line[3:].strip().strip('"').strip("'")
                    if val.startswith("~"):
                        val = str(Path.home()) + val[1:]
                    idx = val.find("%")
                    path_part = val[:idx] if idx != -1 else val
                    sep_idx = max(path_part.rfind("/"), path_part.rfind("\\"))
                    if sep_idx != -1:
                        extracted = Path(path_part[:sep_idx]).expanduser().resolve()
                        if extracted.exists() or extracted.parent.exists():
                            return extracted
        except Exception:
            pass

    return get_download_dir()


def update_ytdlp_conf_destinations(new_download_dir: Path, conf_path: Optional[Path] = None) -> Tuple[bool, str]:
    """
    Interactively updates all download destinations in yt-dlp.conf:
    - Videos: <dest_dir>\\%(playlist|)s\\%(title).70B_%(epoch)s.%(ext)s
    - Subtitles: subtitle:<dest_dir>\\Subs\\%(title).70B_%(epoch)s.%(ext)s
    - Thumbnails: thumbnail:<dest_dir>\\Thumbnails\\%(title).70B_%(epoch)s.%(ext)s

    Preserves all format selections, aria2c flags, network resilience, and user options.
    Also synchronizes StreamVortex config.json so CLI, GUI, and Web studio remain unified.
    """
    dest_dir = Path(new_download_dir).expanduser().resolve()
    dest_dir.mkdir(parents=True, exist_ok=True)

    target_conf = conf_path or find_ytdlp_conf()
    if not target_conf:
        saved_tools = get_config().get("tools_dir")
        if saved_tools:
            target_conf = Path(saved_tools) / "yt-dlp.conf"
        else:
            target_conf = Path("C:/Tools/yt-dlp.conf")

    target_conf.parent.mkdir(parents=True, exist_ok=True)

    dest_str = str(dest_dir).replace("/", "\\")
    new_video_line = f'-o "{dest_str}\\%(playlist|)s\\%(title).70B_%(epoch)s.%(ext)s"'
    new_sub_line = f'-o "subtitle:{dest_str}\\Subs\\%(title).70B_%(epoch)s.%(ext)s"'
    new_thumb_line = f'-o "thumbnail:{dest_str}\\Thumbnails\\%(title).70B_%(epoch)s.%(ext)s"'

    existing_lines = []
    if target_conf.exists():
        try:
            existing_lines = target_conf.read_text(encoding="utf-8", errors="ignore").splitlines()
        except Exception:
            existing_lines = []

    # Filter out existing -o lines
    filtered_lines = []
    for line in existing_lines:
        s = line.strip()
        if s.startswith("-o ") or s.startswith("--output "):
            continue
        filtered_lines.append(line)

    # Clean leading blank lines or existing output section headers
    while filtered_lines and (filtered_lines[0].strip() == "" or "OUTPUT" in filtered_lines[0]):
        filtered_lines.pop(0)

    output_block = [
        "# ===== OUTPUT =====",
        new_video_line,
        new_sub_line,
        new_thumb_line,
        ""
    ]

    final_content = "\n".join(output_block + filtered_lines).strip() + "\n"

    try:
        with open(target_conf, "w", encoding="utf-8") as f:
            f.write(final_content)

        try:
            root_conf = Path(__file__).resolve().parent.parent / "yt-dlp.conf"
            if root_conf.exists() and root_conf.resolve() != target_conf.resolve():
                with open(root_conf, "w", encoding="utf-8") as f:
                    f.write(final_content)
        except Exception:
            pass

        cfg = get_config()
        cfg["download_dir"] = str(dest_dir)
        cfg["ytdlp_conf_path"] = str(target_conf)
        save_config(cfg)

        return True, f"Updated yt-dlp.conf output destinations to: {dest_dir}"
    except Exception as e:
        return False, str(e)


def get_conf_format(conf_path: Optional[Path] = None) -> Optional[str]:
    """
    Extracts the active, uncommented format rule (-f or --format) specified in yt-dlp.conf.
    Returns None if no active format rule is present.
    """
    target_conf = conf_path or find_ytdlp_conf()
    if not target_conf or not target_conf.exists():
        return None
    try:
        content = target_conf.read_text(encoding="utf-8", errors="ignore")
        for line in content.splitlines():
            s = line.strip()
            if not s or s.startswith("#") or s.startswith(";"):
                continue
            if s.startswith("-f ") or s.startswith("-f\t"):
                return s[2:].strip().strip('"').strip("'")
            if s.startswith("--format ") or s.startswith("--format\t"):
                return s[8:].strip().strip('"').strip("'")
            if s.startswith("--format="):
                return s[9:].strip().strip('"').strip("'")
    except Exception:
        pass
    return None


def build_format_args(
    quality_preference: Optional[str] = "best",
    is_live: bool = False,
    audio_only: bool = False,
    conf_path: Optional[Path] = None
) -> Tuple[List[str], str]:
    """
    Determines the exact yt-dlp CLI arguments (-f, -S, --merge-output-format) needed to fulfill user intent.

    Precedence & Edge Case Resolution Hierarchy:
    1. Audio Extraction ('audio_mp3', 'audio_m4a', or audio_only=True):
       Forces '-f bestaudio/best' and '--no-keep-video'. This guarantees yt-dlp only downloads
       the lightweight audio stream, bypassing any heavy video format or video merge rules in yt-dlp.conf.
    2. Respect yt-dlp.conf ('conf', 'config', 'custom'):
       Passes NO format flags, allowing the user's custom yt-dlp.conf format rules to take full priority.
    3. Live Stream (is_live=True):
       Live feeds usually have unified streams. We pass live-compatible stream selectors ('best/bestvideo+bestaudio/b'),
       overriding split video+audio format rules in yt-dlp.conf that would otherwise fail on live manifests.
    4. Best / Maximum Quality ('best', 'bestquality', 'max', '4k_2k', '4k'):
       Passes '-f (bestvideo+bestaudio/best)' and '-S res,fps,hdr:12,codec:av01:vp9:h264'.
       yt-dlp parses CLI arguments after --config-locations, so this explicitly overrides any
       720p or 1080p cap defined in yt-dlp.conf, ensuring the user gets full 4K/2K resolution.
    5. Specific Resolution Caps ('1080p', '720p', '480p'):
       Explicitly enforces the chosen cap with matching format and sort flags, overriding any opposing rule in .conf.
    """
    conf_format = get_conf_format(conf_path)
    conf_label = f" (overriding '{conf_format}' in yt-dlp.conf)" if conf_format else ""

    q_clean = (quality_preference or "").lower().strip()

    # 1. Audio-only extraction edge case
    if audio_only or q_clean in ("audio_mp3", "audio_m4a", "audio"):
        fmt_label = "M4A" if q_clean == "audio_m4a" else "MP3"
        return [
            "-f", "bestaudio/best",
            "--no-keep-video"
        ], f"Audio-only profile ({fmt_label}): downloading pure audio stream{conf_label}"

    # 2. Explicit request to defer to yt-dlp.conf
    if q_clean in ("conf", "config", "custom", "native"):
        active_fmt = conf_format or "default yt-dlp fallback"
        return [], f"Respecting format rule directly from yt-dlp.conf: {active_fmt}"

    # 3. Live streams edge case
    if is_live:
        if "720" in q_clean:
            return ["-f", "best[height<=720]/bestvideo[height<=720]+bestaudio/best"], f"Live stream capped at 720p{conf_label}"
        elif "480" in q_clean:
            return ["-f", "best[height<=480]/bestvideo[height<=480]+bestaudio/best"], f"Live stream capped at 480p{conf_label}"
        else:
            return ["-f", "best/bestvideo+bestaudio/b"], f"Live stream source quality (unified manifest){conf_label}"

    # 4. Explicit resolution profiles
    if "1080" in q_clean:
        return [
            "-f", "(bestvideo[height<=1080]+bestaudio/best[height<=1080]/best)",
            "-S", "res:1080,fps,hdr:12",
            "--merge-output-format", "mp4"
        ], f"Enforcing 1080p Universal MP4 profile{conf_label}"

    if "720" in q_clean:
        return [
            "-f", "(bestvideo[height<=720]+bestaudio/best[height<=720]/best)",
            "-S", "res:720,fps"
        ], f"Enforcing 720p Fast profile{conf_label}"

    if "480" in q_clean:
        return [
            "-f", "(bestvideo[height<=480]+bestaudio/best[height<=480]/best)",
            "-S", "res:480"
        ], f"Enforcing 480p Data Saver profile{conf_label}"

    # 5. Best / Maximum quality (default when quality_preference is "best", "max", "bestquality", etc.)
    return [
        "-f", "(bestvideo+bestaudio/best)",
        "-S", "res,fps,hdr:12,codec:av01:vp9:h264"
    ], f"Enforcing Maximum/Best quality profile (unconstrained 4K/2K/1080p){conf_label}"


RESERVED_NAMES = {
    "CON", "PRN", "AUX", "NUL",
    "COM1", "COM2", "COM3", "COM4", "COM5", "COM6", "COM7", "COM8", "COM9",
    "LPT1", "LPT2", "LPT3", "LPT4", "LPT5", "LPT6", "LPT7", "LPT8", "LPT9"
}


def sanitize_filename(name: str, max_length: int = 150) -> str:
    """
    Sanitizes a string to be a safe, clean Windows/Unix filename.
    Guards against:
    - Windows invalid characters (\ / : * ? " < > |)
    - Control characters and unprintable symbols
    - Windows reserved names (CON, PRN, AUX, NUL, COM1-9, LPT1-9)
    - Trailing spaces and dots which trigger filesystem errors
    """
    if not name:
        return "media"
    invalid_chars = r'\/:*?"<>|'
    cleaned = "".join(c if c not in invalid_chars else (" - " if c in ":/" else " ") for c in name)
    cleaned = "".join(c for c in cleaned if c.isprintable() and ord(c) >= 32 and ord(c) != 127)
    cleaned = " ".join(cleaned.split())
    cleaned = cleaned.strip(". ")
    if not cleaned:
        cleaned = "media"
    cleaned = cleaned[:max_length].rstrip(". ")

    # Windows reserved device names protection
    stem_check = cleaned.split(".")[0].strip().upper()
    if stem_check in RESERVED_NAMES:
        cleaned = f"media_{cleaned}"

    return cleaned


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


def clean_target_url(url: str) -> str:
    """
    Cleans and sanitizes a stream URL, stripping tracking tokens, leading dashes (option injection guard),
    and formatting artifacts.
    """
    if not url:
        return ""
    url = url.strip().strip(''"<>')
    # Prevent option injection if URL starts with dashes
    while url.startswith("-"):
        url = url.lstrip("-").strip()
    try:
        parsed = urllib.parse.urlsplit(url)
        if parsed.query:
            qs = urllib.parse.parse_qs(parsed.query, keep_blank_values=True)
            filtered_qs = {k: v for k, v in qs.items() if not k.lower().startswith("utm_") and k.lower() not in ("si", "fbclid", "igsh", "ref_src")}
            new_query = urllib.parse.urlencode(filtered_qs, doseq=True) if filtered_qs else ""
            url = urllib.parse.urlunsplit((parsed.scheme, parsed.netloc, parsed.path, new_query, parsed.fragment))
    except Exception:
        pass
    return url


def detect_platform(url: str) -> Dict[str, str]:
    """Identifies the target streaming platform with styling cues and metadata."""
    u = url.lower()
    if "tiktok.com" in u:
        is_live = "/live" in u
        return {
            "id": "tiktok",
            "name": "TikTok Live" if is_live else "TikTok Video",
            "badge_color": "#ff2a5f",
            "icon": "🎵",
            "type": "live" if is_live else "vod"
        }
    elif "youtube.com" in u or "youtu.be" in u:
        is_live = "/live" in u or "live" in u
        is_short = "/shorts/" in u
        name = "YouTube Shorts" if is_short else ("YouTube Live" if is_live else "YouTube")
        return {
            "id": "youtube",
            "name": name,
            "badge_color": "#ff0000",
            "icon": "▶️",
            "type": "live" if is_live else "vod"
        }
    elif "twitch.tv" in u:
        is_clip = "/clip" in u or "clips.twitch.tv" in u
        return {
            "id": "twitch",
            "name": "Twitch Clip" if is_clip else "Twitch Stream",
            "badge_color": "#a970ff",
            "icon": "🟣",
            "type": "vod" if is_clip else "live"
        }
    elif "kick.com" in u:
        return {
            "id": "kick",
            "name": "Kick Stream",
            "badge_color": "#53fc18",
            "icon": "🟢",
            "type": "live"
        }
    elif "twitter.com" in u or "x.com" in u:
        return {
            "id": "twitter",
            "name": "X / Twitter",
            "badge_color": "#1d9bf0",
            "icon": "🐦",
            "type": "vod"
        }
    elif "instagram.com" in u:
        return {
            "id": "instagram",
            "name": "Instagram",
            "badge_color": "#e1306c",
            "icon": "📷",
            "type": "vod"
        }
    elif "facebook.com" in u or "fb.watch" in u:
        return {
            "id": "facebook",
            "name": "Facebook Video",
            "badge_color": "#1877f2",
            "icon": "📘",
            "type": "vod"
        }
    elif "reddit.com" in u or "v.redd.it" in u:
        return {
            "id": "reddit",
            "name": "Reddit Video",
            "badge_color": "#ff4500",
            "icon": "🤖",
            "type": "vod"
        }
    elif ".m3u8" in u:
        return {
            "id": "hls",
            "name": "HLS Stream (m3u8)",
            "badge_color": "#00f2fe",
            "icon": "⚡",
            "type": "live"
        }
    elif ".mpd" in u:
        return {
            "id": "dash",
            "name": "DASH Stream (mpd)",
            "badge_color": "#38bdf8",
            "icon": "⚡",
            "type": "live"
        }
    return {
        "id": "generic",
        "name": "Universal Web Stream",
        "badge_color": "#64748b",
        "icon": "🌐",
        "type": "unknown"
    }


def check_free_disk_space(target_dir: Optional[Path] = None, min_gb: float = 0.5) -> Tuple[bool, float]:
    """Checks whether the target drive has sufficient free disk space."""
    d = target_dir or get_download_dir()
    try:
        total, used, free = shutil.disk_usage(d)
        free_gb = free / (1024 ** 3)
        return free_gb >= min_gb, round(free_gb, 2)
    except Exception:
        return True, 999.0


def resolve_stream_metadata(url: str, timeout: int = 8) -> Dict[str, Any]:
    """
    Universal metadata resolver for any stream or video in the world.
    Extracts actual title, creator, thumbnail, platform, and stream properties.
    """
    url = clean_target_url(url)
    platform_info = detect_platform(url)

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
                    "platform": platform_info,
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
                    "platform": platform_info,
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
            uploader = data.get("uploader") or data.get("channel") or data.get("creator") or ""
            is_live = bool(data.get("is_live"))
            raw_fmts = data.get("formats", [])
            extracted_fmts = []
            for f in raw_fmts:
                if f.get("url"):
                    extracted_fmts.append({
                        "id": f.get("format_id", "fmt"),
                        "url": f.get("url"),
                        "protocol": f.get("protocol", "https"),
                        "ext": f.get("ext", "mp4"),
                        "height": f.get("height"),
                        "format_note": f.get("format_note", "")
                    })
            return {
                "title": title,
                "uploader": uploader,
                "is_live": is_live,
                "id": data.get("id"),
                "platform": platform_info,
                "thumbnail": data.get("thumbnail"),
                "duration": data.get("duration"),
                "formats": extracted_fmts[-10:] if extracted_fmts else [],
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
                "platform": platform_info,
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
        "platform": platform_info,
        "suggested_filename": "stream_media.mp4"
    }


def cleanup_empty_or_broken_files(target_dir: Path, target_stem: Optional[str] = None):
    """
    Cleans up 0-byte ghost files, leftover .part, and .ytdl temporary artifacts
    after an interrupted, failed, or cancelled download or recording.
    """
    if not target_dir or not target_dir.exists():
        return
    try:
        patterns = ["*.part", "*.ytdl", "*.part-Frag*"]
        if target_stem:
            clean_stem = sanitize_filename(target_stem)
            patterns.extend([f"{clean_stem}*.part", f"{clean_stem}*.ytdl", f"*{clean_stem}*.part"])

        for pat in patterns:
            for f in target_dir.glob(pat):
                try:
                    if f.is_file():
                        f.unlink(missing_ok=True)
                except Exception:
                    pass

        if target_stem:
            clean_stem = sanitize_filename(target_stem)
            for f in target_dir.glob(f"{clean_stem}.*"):
                try:
                    if f.is_file() and f.stat().st_size == 0:
                        f.unlink(missing_ok=True)
                except Exception:
                    pass
    except Exception:
        pass


PROGRESS_REGEX = re.compile(r'\[download\]\s+([\d\.]+)%\s+of\s+~?([^\s]+)\s+at\s+([^\s]+)\s+ETA\s+([^\s]+)')
PROGRESS_SIMPLE_REGEX = re.compile(r'\[download\]\s+([\d\.]+)%')
PROGRESS_LIVE_REGEX = re.compile(r'\[download\]\s+([\d\.]+[A-Za-z]+)\s+at\s+([^\s]+)(?:\s+\(([\d:]+)\))?')
FFMPEG_PROGRESS_REGEX = re.compile(r'size=\s*([^\s]+)\s+time=\s*([\d:.]+)\s+bitrate=\s*([^\s]+)\s+speed=\s*([^\s]+)')


class DownloadManager:
    """Thread-safe active download tracker for Desktop GUI and Web Studio."""
    def __init__(self):
        self._lock = threading.Lock()
        self._jobs: Dict[str, Dict[str, Any]] = {}

    def start_job(self, job_id: str, title: str, url: str) -> Dict[str, Any]:
        with self._lock:
            job = {
                "id": job_id,
                "title": title or "Media Download",
                "url": url,
                "status": "starting",
                "progress": 0.0,
                "speed": "--",
                "eta": "--",
                "completed": False,
                "error": None
            }
            self._jobs[job_id] = job
            return job

    def update_job(self, job_id: str, progress: float, speed: str = "--", eta: str = "--", status: str = "downloading"):
        with self._lock:
            if job_id in self._jobs:
                self._jobs[job_id].update({
                    "progress": progress,
                    "speed": speed,
                    "eta": eta,
                    "status": status
                })

    def finish_job(self, job_id: str, success: bool = True, error: Optional[str] = None):
        with self._lock:
            if job_id in self._jobs:
                self._jobs[job_id].update({
                    "completed": True,
                    "status": "completed" if success else "failed",
                    "progress": 100.0 if success else self._jobs[job_id]["progress"],
                    "error": error
                })

    def get_active_jobs(self) -> List[Dict[str, Any]]:
        with self._lock:
            return list(self._jobs.values())

    def clear_completed(self):
        with self._lock:
            self._jobs = {k: v for k, v in self._jobs.items() if not v["completed"]}


DOWNLOAD_MANAGER = DownloadManager()


def run_ytdlp_download(
    stream_url: str,
    output_filename: Optional[str] = None,
    referer: Optional[str] = None,
    audio_only: bool = False,
    is_live: bool = False,
    quality_preference: Optional[str] = None,
    on_output: Optional[Callable[[str], None]] = None,
    progress_callback: Optional[Callable[[float, str, str], None]] = None,
    conf_path: Optional[str] = None,
    title: Optional[str] = None,
    uploader: Optional[str] = None,
    respect_conf_output: bool = True
) -> int:
    """
    Executes a yt-dlp download with intelligent configuration management, progress streaming, & title resolution:
    - Automatically discovers and injects the user's .conf file (e.g. C:\\Tools\\yt-dlp.conf).
    - If is_live=True: overrides incompatible external downloaders (like aria2c)
      by using native HLS/m3u8 streaming, ensuring lives download smoothly.
    - If audio_only=True: extracts audio and transcodes to high-quality MP3/M4A.
    - Parses live percentage, speed, and ETA for real-time progress callbacks.
    - Always names the resulting file using the actual title of the video or live.
    - If the user's .conf defines an output template (-o) and output_filename is None,
      respects and uses the user's configured output template!
    """
    ytdlp_cmd = find_ytdlp()
    d_dir = get_download_dir()
    stream_url = clean_target_url(stream_url)

    # Disk space pre-check (safety guard)
    has_critical, free_gb = check_free_disk_space(d_dir, min_gb=0.1)
    if not has_critical:
        err_msg = f"[Storage Guard] Download aborted: Critically low disk space ({free_gb:.2f} GB free, minimum 0.1 GB required)."
        if on_output:
            on_output(err_msg)
        else:
            print(err_msg)
        return 1

    has_space, _ = check_free_disk_space(d_dir, min_gb=0.5)
    if not has_space:
        low_msg = f"[Storage Alert] Low disk space detected ({free_gb:.1f} GB free). Continuing with download..."
        if on_output:
            on_output(low_msg)

    cmd = list(ytdlp_cmd)

    # 1. Config Discovery & Injection
    conf = Path(conf_path) if conf_path else find_ytdlp_conf()

    if conf and conf.exists():
        cmd.extend(["--config-locations", str(conf)])
        msg = f"[StreamVortex] Using global yt-dlp configuration: {conf}"
        if on_output:
            on_output(msg)
        else:
            print(msg)

    # 2. Output Filename & Template Handling
    has_conf_output = conf_has_output_template(conf) if conf else False
    target_dir = get_conf_download_dir(conf)
    out_path_label = ""

    is_audio = audio_only or (quality_preference and quality_preference in ("audio_mp3", "audio_m4a"))
    ext_target = "m4a" if quality_preference == "audio_m4a" else ("mp3" if is_audio else "mp4")

    if output_filename:
        out_path = Path(output_filename)
        if not out_path.is_absolute():
            out_path = target_dir / out_path
        cmd.extend(["-o", str(out_path)])
        out_path_label = str(out_path)
    elif has_conf_output and respect_conf_output and not is_audio:
        out_path_label = f"Configured in {conf.name} ({target_dir})"
    elif title:
        safe_name = sanitize_title_for_filename(title, uploader=uploader, ext=ext_target)
        out_path = target_dir / safe_name
        cmd.extend(["-o", str(out_path)])
        out_path_label = str(out_path)
    else:
        out_ext = ext_target if is_audio else "%(ext)s"
        out_path = target_dir / f"%(title).90B [%(id)s].{out_ext}"
        cmd.extend(["-o", str(out_path)])
        out_path_label = str(out_path)

    # 3. Handle Audio Extraction
    if is_audio:
        fmt = "m4a" if quality_preference == "audio_m4a" else "mp3"
        cmd.extend([
            "-x",
            "--audio-format", fmt,
            "--audio-quality", "0",
        ])

    # 4. Handle Format Selection & Quality Profiles (resolves precedence with yt-dlp.conf)
    fmt_args, fmt_reason = build_format_args(
        quality_preference=quality_preference,
        is_live=is_live,
        audio_only=audio_only,
        conf_path=conf
    )
    if fmt_args:
        cmd.extend(fmt_args)

    if fmt_reason:
        msg = f"[StreamVortex Quality] {fmt_reason}"
        if on_output:
            on_output(msg)
        else:
            print(msg)

    # 5. Live Streams Engine Overrides
    if is_live:
        cmd.extend([
            "--downloader", "m3u8:native",
            "--no-part",
        ])

    # 5. Headers & Flags
    if referer:
        cmd.extend(["--referer", referer])

    cmd.extend([
        "--retries", "10",
        "--fragment-retries", "15",
        "--file-access-retries", "5",
        "--retry-sleep", "2",
        "--no-mtime",
        "--progress"
    ])

    # Option injection safety: append target stream URL at the very end
    cmd.extend(["--", stream_url])

    # Configure execution environment with aria2c in PATH if present
    env = os.environ.copy()
    aria_bin = find_aria2c()
    if aria_bin:
        aria_dir = str(Path(aria_bin).parent)
        env["PATH"] = aria_dir + os.pathsep + env.get("PATH", "")

    # 6. Run process with live output streaming, progress parsing & fault isolation
    target_clean_stem = Path(out_path_label).stem if (out_path_label and not out_path_label.startswith("Configured in")) else (title or "media")

    if on_output or progress_callback:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            env=env
        )
        try:
            for line in proc.stdout:
                clean_line = line.strip()
                if on_output:
                    on_output(clean_line)
                if progress_callback and clean_line:
                    m = PROGRESS_REGEX.search(clean_line)
                    if m:
                        try:
                            pct = float(m.group(1))
                            speed = m.group(3)
                            eta = m.group(4)
                            progress_callback(pct, speed, eta)
                        except Exception:
                            pass
                    else:
                        m_simple = PROGRESS_SIMPLE_REGEX.search(clean_line)
                        if m_simple:
                            try:
                                pct = float(m_simple.group(1))
                                progress_callback(pct, "--", "--")
                            except Exception:
                                pass
                        else:
                            m_live = PROGRESS_LIVE_REGEX.search(clean_line)
                            if m_live:
                                try:
                                    bytes_down = m_live.group(1)
                                    speed = m_live.group(2)
                                    elapsed = m_live.group(3) or "--"
                                    progress_callback(None, speed, f"{bytes_down} ({elapsed})")
                                except Exception:
                                    pass
            proc.wait()
            retcode = proc.returncode
        except (KeyboardInterrupt, Exception) as e:
            if proc.poll() is None:
                proc.kill()
                proc.wait()
            cleanup_empty_or_broken_files(target_dir, target_stem=target_clean_stem)
            return 1
    else:
        retcode = subprocess.run(cmd, env=env).returncode

    if retcode == 0:
        entry_title = title or (Path(out_path_label).stem if out_path_label != "Configured in yt-dlp.conf" else "Downloaded Media")
        add_history_entry(
            title=entry_title,
            filename=out_path_label,
            stream_url=stream_url,
            media_type="audio" if (audio_only or quality_preference in ("audio_mp3", "audio_m4a")) else ("live" if is_live else "video")
        )
    else:
        # Automatic cleanup on failed or aborted download
        cleanup_empty_or_broken_files(target_dir, target_stem=target_clean_stem)

    return retcode


def run_ffmpeg_record(
    stream_url: str,
    output_filename: Optional[str] = None,
    headers: Optional[Dict[str, str]] = None,
    max_duration_seconds: Optional[int] = None,
    title: Optional[str] = None,
    uploader: Optional[str] = None,
    on_output: Optional[Callable[[str], None]] = None,
    progress_callback: Optional[Callable[[Optional[float], str, str], None]] = None
) -> int:
    """
    Direct, lossless stream recording via FFmpeg.
    Automatically generates descriptive filenames using the actual title and uploader,
    streams real-time stderr progress, finalizes cleanly with +faststart, and
    cleans up empty or broken files on failure.
    """
    ffmpeg_bin = find_ffmpeg()
    if not ffmpeg_bin:
        return run_ytdlp_download(
            stream_url,
            output_filename=output_filename,
            title=title,
            uploader=uploader,
            is_live=True,
            on_output=on_output,
            progress_callback=progress_callback
        )

    d_dir = get_download_dir()

    # Disk space check
    has_critical, free_gb = check_free_disk_space(d_dir, min_gb=0.1)
    if not has_critical:
        err_msg = f"[Storage Guard] Live recording aborted: Critically low disk space ({free_gb:.2f} GB free)."
        if on_output:
            on_output(err_msg)
        return 1

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

    # Lossless stream copy with faststart for crash resistance & instant playback
    cmd.extend(["-c", "copy", "-movflags", "+faststart", str(out_path)])

    retcode = 1
    try:
        proc = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stderr=subprocess.PIPE,
            stdout=subprocess.DEVNULL,
            text=True,
            encoding="utf-8",
            errors="replace"
        )
        for line in proc.stderr:
            clean_line = line.strip()
            if on_output:
                on_output(clean_line)
            if progress_callback and clean_line:
                m = FFMPEG_PROGRESS_REGEX.search(clean_line)
                if m:
                    size = m.group(1)
                    t_str = m.group(2)
                    bitrate = m.group(3)
                    speed = m.group(4)
                    progress_callback(None, f"{speed} ({bitrate})", f"{t_str} ({size})")
        proc.wait()
        retcode = proc.returncode
    except KeyboardInterrupt:
        if proc.poll() is None:
            try:
                proc.stdin.write("q\n")
                proc.stdin.flush()
                proc.wait(timeout=5)
            except Exception:
                proc.kill()
        retcode = 0
    except Exception as e:
        if on_output:
            on_output(f"[FFmpeg Error] {e}")
        retcode = 1

    # Cleanup if aborted or 0-byte ghost file
    if retcode != 0 or (out_path.exists() and out_path.stat().st_size == 0):
        cleanup_empty_or_broken_files(d_dir, out_path.stem)
    elif out_path.exists() and out_path.stat().st_size > 0:
        add_history_entry(
            title=title or out_path.stem,
            filename=str(out_path),
            stream_url=stream_url,
            media_type="live_record"
        )

    return retcode
