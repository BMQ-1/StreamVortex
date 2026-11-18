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
import time
import shutil
import subprocess
import threading
import urllib.parse
from pathlib import Path
from typing import Optional, List, Dict, Any, Callable, Tuple, Union

from .config import get_download_dir, get_config, save_config, add_history_entry


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
        user_home / "AppData/Local/Programs/Python/Python313/python.exe",
        user_home / "AppData/Local/Programs/Python/Python312/python.exe",
        user_home / "AppData/Local/Programs/Python/Python311/python.exe",
        user_home / "AppData/Local/Programs/Python/Python310/python.exe",
        user_home / "AppData/Local/Programs/Python/Python39/python.exe",
        Path("C:/Python313/python.exe"),
        Path("C:/Python312/python.exe"),
        Path("C:/Python311/python.exe"),
        Path("C:/Python310/python.exe"),
        Path("C:/Program Files/Python313/python.exe"),
        Path("C:/Program Files/Python312/python.exe"),
        Path("C:/Program Files/Python311/python.exe"),
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
    1. System PATH (e.g. C:\\Tools\\ffmpeg.exe)
    2. Configured tools_dir from onboarding
    3. Standard global Windows install locations (C:\\Tools, C:\\ffmpeg, Program Files, WinGet, Chocolatey)
    4. Local fallback (only if no global FFmpeg is available)
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

    # 3. Known standard global paths
    candidates = [
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

    # 4. Known standard global paths
    candidates = [
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
    Locates the best available media player on the device (MPV, VLC, or FFplay).
    Checks system PATH, configured tools directory, standard install paths, and FFmpeg directory.
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
            for name in ["mpv.exe", "vlc.exe", "ffplay.exe"]:
                p = Path(tools_dir) / name
                if p.exists():
                    return str(p)
    except Exception:
        pass

    # 4. Standard VLC & MPV install locations
    for cand in [
        Path(os.environ.get("PROGRAMFILES", "C:/Program Files")) / "VideoLAN" / "VLC" / "vlc.exe",
        Path(os.environ.get("PROGRAMFILES(X86)", "C:/Program Files (x86)")) / "VideoLAN" / "VLC" / "vlc.exe",
        Path("C:/Program Files/VideoLAN/VLC/vlc.exe"),
        Path("C:/Program Files (x86)/VideoLAN/VLC/vlc.exe"),
        Path("C:/Tools/vlc/vlc.exe"),
        Path("C:/Tools/mpv/mpv.exe"),
    ]:
        if cand.exists():
            return str(cand)

    # 5. FFplay adjacent to FFmpeg or on PATH
    ffplay = shutil.which("ffplay")
    if ffplay:
        return ffplay
    ffmpeg = find_ffmpeg()
    if ffmpeg:
        adjacent_ffplay = Path(ffmpeg).parent / ("ffplay.exe" if sys.platform == "win32" else "ffplay")
        if adjacent_ffplay.exists():
            return str(adjacent_ffplay)

    return None


def play_media_target(
    target_url_or_file: str,
    title: Optional[str] = None,
    user_agent: Optional[str] = None
) -> Tuple[bool, str]:
    """
    Universal media player launcher with multi-tier fallbacks:
    Tier 1: Dedicated media player (MPV / VLC / FFplay).
    Tier 2: Native OS default player / browser (os.startfile / xdg-open / open).
    Tier 3: Clipboard copy fallback.
    Returns (success, description_of_action).
    """
    target = target_url_or_file.strip()
    if not target:
        return False, "Empty target"

    player = find_player()
    if player:
        cmd = [player, target]
        p_name = Path(player).stem.lower()
        if "mpv" in p_name and user_agent:
            cmd.extend([f"--user-agent={user_agent}"])
        elif "vlc" in p_name and user_agent:
            cmd.extend([f"--http-user-agent={user_agent}"])
        elif "ffplay" in p_name:
            cmd = [player, "-autoexit", "-window_title", title or "StreamVortex Player", target]
            if user_agent:
                cmd.extend(["-user_agent", user_agent])
        try:
            subprocess.Popen(cmd)
            return True, f"Launched in {Path(player).name}"
        except Exception:
            pass

    # Tier 2: System OS default player / browser
    try:
        if sys.platform == "win32":
            os.startfile(target)
            return True, "Launched in system default media player"
        elif sys.platform == "darwin":
            subprocess.Popen(["open", target])
            return True, "Launched in default media player"
        else:
            subprocess.Popen(["xdg-open", target])
            return True, "Launched in default media player"
    except Exception:
        pass

    # Tier 3: Clipboard fallback
    try:
        import pyperclip
        pyperclip.copy(target)
        return True, "Copied URL to clipboard (no desktop player available)"
    except Exception:
        pass

    return False, f"Could not launch player for {target}"


def is_environment_ready() -> bool:
    """Returns True if essential extraction tools (yt-dlp and FFmpeg) are ready."""
    ytdlp = find_ytdlp()
    ffmpeg = find_ffmpeg()
    return bool(ytdlp and ffmpeg)


def find_aria2c() -> Optional[str]:
    """
    Decommissioned: aria2c is disabled due to known security vulnerabilities (CVEs)
    and severe live stream fragmentation crashes. yt-dlp native multi-threading (-N 6)
    is used instead. Returns None.
    """
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

# ===== EXTERNAL DOWNLOADER (aria2c - DISABLED) =====
# Disabled due to security vulnerabilities and lack of streaming protocol support.
# yt-dlp native multi-threaded downloader (-N 6) is used instead.
# --downloader aria2c
# --downloader-args "aria2c:-x 16 -s 16 -k 1M"

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

# ===== SMARTSTREAM CONTAINER FIXUP =====
# Automatically remuxes MPEG-TS/FLV container mismatches in live recordings.
# Works when the SmartStream plugin is loaded (yt-dlp run from project dir or --plugin-dirs).
--use-postprocessor "SmartStreamFixup:when=after_move;force=true"
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
            return ["-f", "best[height<=720]/bestvideo[height<=720]+bestaudio/best",
                    "--merge-output-format", "mp4"], f"Live stream capped at 720p{conf_label}"
        elif "480" in q_clean:
            return ["-f", "best[height<=480]/bestvideo[height<=480]+bestaudio/best",
                    "--merge-output-format", "mp4"], f"Live stream capped at 480p{conf_label}"
        else:
            return ["-f", "best/bestvideo+bestaudio/b",
                    "--merge-output-format", "mp4"], f"Live stream source quality (unified manifest){conf_label}"

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
    r"""
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
    url = url.strip().strip("'\"<>")
    # Prevent option injection if URL starts with dashes
    while url.startswith("-"):
        url = url.lstrip("-").strip()

    if not url:
        return ""

    known_schemes = ("http://", "https://", "smart:", "sniff:", "rtmp://", "rtmps://", "mms://", "rtsp://", "hls://")
    if not url.startswith(known_schemes):
        first_segment = url.split("/")[0].split("?")[0].split("#")[0]
        if "." in first_segment or first_segment.startswith("www."):
            url = "https://" + url
    try:
        parsed = urllib.parse.urlsplit(url)
        if parsed.query:
            qs = urllib.parse.parse_qs(parsed.query, keep_blank_values=True)
            tracking_params = {
                "si", "fbclid", "igsh", "igshid", "ref_src", "tt_from", "checksum",
                "gclid", "msclkid", "mc_eid", "yclid", "zanpid", "spm", "_hsenc", "_hsmi"
            }
            filtered_qs = {k: v for k, v in qs.items() if not k.lower().startswith("utm_") and k.lower() not in tracking_params}
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
    elif "rumble.com" in u:
        return {
            "id": "rumble",
            "name": "Rumble Video",
            "badge_color": "#85c742",
            "icon": "🥊",
            "type": "vod"
        }
    elif "vimeo.com" in u:
        return {
            "id": "vimeo",
            "name": "Vimeo Video",
            "badge_color": "#1ab7ea",
            "icon": "▶️",
            "type": "vod"
        }
    elif "bilibili.com" in u:
        return {
            "id": "bilibili",
            "name": "Bilibili",
            "badge_color": "#00a1d6",
            "icon": "📺",
            "type": "vod"
        }
    elif "dailymotion.com" in u:
        return {
            "id": "dailymotion",
            "name": "Dailymotion",
            "badge_color": "#0066dc",
            "icon": "🎞️",
            "type": "vod"
        }
    elif ".m3u8" in u:
        return {
            "id": "hls",
            "name": "HLS Live Stream (m3u8)",
            "badge_color": "#00f2fe",
            "icon": "⚡",
            "type": "live"
        }
    elif ".mpd" in u:
        return {
            "id": "dash",
            "name": "DASH Live Stream (mpd)",
            "badge_color": "#38bdf8",
            "icon": "⚡",
            "type": "live"
        }
    elif any(u.endswith(ext) or f"{ext}?" in u for ext in [".flv", ".ts"]):
        return {
            "id": "livefeed",
            "name": "Direct Stream Feed",
            "badge_color": "#f59e0b",
            "icon": "⚡",
            "type": "live"
        }
    elif any(u.endswith(ext) or f"{ext}?" in u for ext in [".mp4", ".mkv", ".webm", ".avi", ".mov"]):
        return {
            "id": "directmedia",
            "name": "Direct Media File",
            "badge_color": "#10b981",
            "icon": "🎬",
            "type": "vod"
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


def parse_hls_manifest_variants(m3u8_url: str, timeout: int = 4) -> List[Dict[str, Any]]:
    """Inspects an HLS master playlist to extract multi-bitrate quality streams."""
    formats = []
    try:
        from .sniffer import DEFAULT_USER_AGENT
        req = urllib.request.Request(m3u8_url, headers={"User-Agent": DEFAULT_USER_AGENT, "Referer": m3u8_url})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            text = resp.read().decode("utf-8", errors="ignore")
            if "#EXT-X-STREAM-INF" in text:
                lines = text.splitlines()
                for idx, line in enumerate(lines):
                    if line.startswith("#EXT-X-STREAM-INF:"):
                        bw_m = re.search(r'BANDWIDTH=(\d+)', line)
                        res_m = re.search(r'RESOLUTION=(\d+)x(\d+)', line)
                        w = int(res_m.group(1)) if res_m else None
                        h = int(res_m.group(2)) if res_m else None
                        bw = int(bw_m.group(1)) // 1000 if bw_m else None
                        for nxt in lines[idx + 1:idx + 4]:
                            nxt = nxt.strip()
                            if nxt and not nxt.startswith("#"):
                                var_url = urllib.parse.urljoin(m3u8_url, nxt)
                                formats.append({
                                    "id": f"hls-{h}p" if h else f"hls-variant-{len(formats)+1}",
                                    "url": var_url,
                                    "protocol": "m3u8_native",
                                    "ext": "mp4",
                                    "width": w,
                                    "height": h,
                                    "tbr": bw,
                                    "format_note": f"HLS {h}p" if h else "HLS Variant"
                                })
                                break
    except Exception:
        pass
    return formats


def resolve_playlist_entries(url: str, timeout: int = 18, max_items: int = 100) -> Optional[Dict[str, Any]]:
    """
    Fast flat-playlist inspector using yt-dlp --flat-playlist --dump-single-json.
    Returns playlist metadata and selectable entries without resolving every individual stream.
    """
    ytdlp_cmd = find_ytdlp()
    platform_info = detect_platform(url)
    try:
        cmd = list(ytdlp_cmd) + [
            "--flat-playlist",
            "--dump-single-json",
            "--no-warnings",
            "--playlist-end", str(max_items),
            url,
        ]
        cfg = get_config()
        cookies_browser = (cfg.get("cookies_from_browser") or "").strip().lower()
        if cookies_browser and cookies_browser != "none":
            cmd.extend(["--cookies-from-browser", cookies_browser])

        res = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, encoding="utf-8", errors="replace")
        if res.returncode == 0 and res.stdout.strip():
            data = json.loads(res.stdout)
            entries_raw = data.get("entries") or []
            if not entries_raw:
                return None
            entries = []
            for idx, e in enumerate(entries_raw, 1):
                if not isinstance(e, dict):
                    continue
                entry_url = e.get("url") or e.get("webpage_url") or ""
                if entry_url and not entry_url.startswith("http"):
                    if platform_info.get("id") == "youtube" and e.get("id"):
                        entry_url = f"https://www.youtube.com/watch?v={e['id']}"
                if not entry_url:
                    continue
                entries.append({
                    "index": idx,
                    "id": e.get("id") or str(idx),
                    "title": e.get("title") or f"Item #{idx}",
                    "url": entry_url,
                    "duration": e.get("duration"),
                    "uploader": e.get("uploader") or e.get("channel") or data.get("uploader") or "",
                })
            if not entries:
                return None
            title = data.get("title") or "Playlist"
            uploader = data.get("uploader") or data.get("channel") or ""
            return {
                "title": title,
                "uploader": uploader,
                "is_live": False,
                "is_playlist": True,
                "id": data.get("id") or "playlist",
                "platform": platform_info,
                "original_url": url,
                "direct_url": None,
                "http_headers": {},
                "thumbnail": data.get("thumbnail"),
                "playlist_count": len(entries),
                "playlist_entries": entries,
                "formats": [],
                "suggested_filename": sanitize_title_for_filename(title, uploader=uploader, ext="mp4"),
            }
    except Exception:
        pass
    return None


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
            if res and res.is_live and res.formats:
                best_fmt = res.formats[0]
                return {
                    "title": res.title,
                    "uploader": res.uploader,
                    "is_live": True,
                    "id": res.media_id,
                    "platform": platform_info,
                    "original_url": url,
                    "direct_url": getattr(res, "direct_url", None) or (best_fmt.url if best_fmt else None),
                    "http_headers": res.http_headers,
                    "formats": [
                        {"id": f.quality_id, "url": f.url, "protocol": f.protocol, "ext": f.ext, "width": f.width, "height": f.height}
                        for f in res.formats
                    ],
                    "suggested_filename": sanitize_title_for_filename(res.title, uploader=res.uploader, ext="mp4")
                }
            else:
                return {
                    "title": f"TikTok Live by @{uploader} (Offline)",
                    "uploader": uploader,
                    "is_live": False,
                    "id": uploader,
                    "platform": platform_info,
                    "original_url": url,
                    "direct_url": None,
                    "http_headers": {"Referer": url},
                    "formats": [],
                    "suggested_filename": sanitize_title_for_filename(f"TikTok Live by @{uploader}", uploader=uploader, ext="mp4")
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
                    "original_url": url,
                    "direct_url": getattr(res, "direct_url", None) or (res.formats[0].url if res.formats else None),
                    "http_headers": res.http_headers,
                    "formats": [
                        {"id": f.quality_id, "url": f.url, "protocol": f.protocol, "ext": f.ext}
                        for f in res.formats
                    ],
                    "suggested_filename": sanitize_title_for_filename(res.title, uploader=res.uploader, ext="mp4")
                }
        except Exception:
            pass

    # 2.5 Direct HLS Manifest Multi-Bitrate Inspection
    if ".m3u8" in url.lower():
        try:
            stem = Path(urllib.parse.urlsplit(url).path).stem or "HLS Stream"
            variants = parse_hls_manifest_variants(url, timeout=min(timeout, 5))
            if not variants:
                variants = [{"id": "hls-origin", "url": url, "protocol": "m3u8_native", "ext": "mp4"}]
            return {
                "title": stem,
                "uploader": platform_info.get("name", "HLS Stream"),
                "is_live": True,
                "id": stem,
                "platform": platform_info,
                "original_url": url,
                "direct_url": url,
                "http_headers": {"Referer": url},
                "formats": variants,
                "suggested_filename": sanitize_title_for_filename(stem, ext="mp4")
            }
        except Exception:
            pass

    # 3. Global yt-dlp probe (YouTube, Twitch, Kick, Vimeo, Playlists, etc.)
    ytdlp_cmd = find_ytdlp()
    try:
        is_pl_url = ("list=" in url and "watch?v=" not in url) or "/playlist?" in url or "/sets/" in url
        if is_pl_url:
            pl_meta = resolve_playlist_entries(url, timeout=max(timeout, 15))
            if pl_meta and pl_meta.get("playlist_entries"):
                return pl_meta

        probe_cmd = list(ytdlp_cmd) + ["--dump-json", "--skip-download", "--no-warnings", "--no-playlist", url]
        conf = find_ytdlp_conf()
        if conf:
            probe_cmd.extend(["--config-locations", str(conf)])
        cfg = get_config()
        cookies_browser = (cfg.get("cookies_from_browser") or "").strip().lower()
        if cookies_browser and cookies_browser != "none":
            probe_cmd.extend(["--cookies-from-browser", cookies_browser])
        proxy_url = (cfg.get("proxy") or "").strip()
        if proxy_url:
            probe_cmd.extend(["--proxy", proxy_url])

        res = subprocess.run(probe_cmd, capture_output=True, text=True, timeout=timeout, encoding="utf-8", errors="replace")
        if res.returncode == 0 and res.stdout.strip():
            data = json.loads(res.stdout.splitlines()[0])
            title = data.get("title") or "video"
            uploader = data.get("uploader") or data.get("channel") or data.get("creator") or ""
            is_live = bool(data.get("is_live")) or (data.get("live_status") == "is_live")
            raw_fmts = data.get("formats", [])
            extracted_fmts = []
            for f in raw_fmts:
                if f.get("url"):
                    vcodec = f.get("vcodec") or "none"
                    acodec = f.get("acodec") or "none"
                    extracted_fmts.append({
                        "id": f.get("format_id", "fmt"),
                        "url": f.get("url"),
                        "protocol": f.get("protocol", "https"),
                        "ext": f.get("ext", "mp4"),
                        "width": f.get("width"),
                        "height": f.get("height"),
                        "fps": f.get("fps"),
                        "tbr": round(f["tbr"]) if isinstance(f.get("tbr"), (int, float)) else f.get("tbr"),
                        "vcodec": vcodec if vcodec != "none" else "",
                        "acodec": acodec if acodec != "none" else "",
                        "filesize": f.get("filesize") or f.get("filesize_approx"),
                        "format_note": f.get("format_note", "")
                    })
            extracted_fmts.sort(key=lambda x: ((x.get("height") or 0), (x.get("tbr") or 0)), reverse=True)
            best_direct = data.get("url")
            if not best_direct and extracted_fmts:
                combined = next((f for f in extracted_fmts if f.get("vcodec") and f.get("acodec")), None)
                best_direct = (combined or extracted_fmts[0]).get("url")
            return {
                "title": title,
                "uploader": uploader,
                "is_live": is_live,
                "is_playlist": False,
                "id": data.get("id"),
                "platform": platform_info,
                "original_url": url,
                "direct_url": best_direct,
                "http_headers": data.get("http_headers", {}),
                "thumbnail": data.get("thumbnail"),
                "duration": data.get("duration"),
                "view_count": data.get("view_count"),
                "formats": extracted_fmts[:18] if extracted_fmts else [],
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
            is_live = sniffed.stream_type in ("hls", "flv")
            return {
                "title": title,
                "uploader": "",
                "is_live": is_live,
                "id": url,
                "platform": platform_info,
                "original_url": url,
                "direct_url": sniffed.url,
                "http_headers": sniffed.headers or {},
                "formats": [{"id": f"{sniffed.stream_type}-main", "url": sniffed.url, "protocol": "m3u8_native" if sniffed.stream_type == "hls" else "https"}],
                "suggested_filename": sanitize_title_for_filename(title, ext="mp4")
            }
    except Exception:
        pass

    # 5. Direct Stream or Media URL Smart Recognition Fallback
    try:
        parsed_p = urllib.parse.urlsplit(url).path.lower()
        if any(parsed_p.endswith(ext) or f"{ext}?" in url.lower() for ext in [".m3u8", ".mpd", ".flv", ".ts", ".mp4", ".mkv", ".webm", ".avi", ".mov"]):
            stem = Path(urllib.parse.urlsplit(url).path).stem or "direct_stream"
            is_live_stream = any(ext in url.lower() for ext in [".m3u8", ".mpd", ".flv", ".ts"])
            if ".m3u8" in parsed_p or ".mpd" in parsed_p or ".ts" in parsed_p:
                ext_type = "mp4"
            elif ".flv" in parsed_p:
                ext_type = "flv"
            elif any(parsed_p.endswith(f".{e}") for e in ["mp4", "mkv", "webm", "avi", "mov"]):
                ext_type = Path(parsed_p).suffix.lstrip(".") or "mp4"
            else:
                ext_type = "mp4"
            return {
                "title": stem,
                "uploader": platform_info.get("name", "Direct Stream"),
                "is_live": is_live_stream,
                "id": stem,
                "platform": platform_info,
                "original_url": url,
                "direct_url": url,
                "http_headers": {},
                "formats": [
                    {"id": "direct-stream", "url": url, "protocol": "m3u8_native" if ".m3u8" in url.lower() else "https", "ext": ext_type}
                ],
                "suggested_filename": sanitize_title_for_filename(stem, ext=ext_type)
            }
    except Exception:
        pass

    return {
        "title": "stream_media",
        "uploader": "",
        "is_live": False,
        "id": "unknown",
        "platform": platform_info,
        "original_url": url,
        "direct_url": None,
        "http_headers": {},
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


# Enhanced and resilient regex patterns for live & VOD download progress
PROGRESS_VOD_REGEX = re.compile(
    r'\[download\]\s+([\d\.]+)%\s+of\s+~?([^\s]+)(?:\s+at\s+([^\s]+))?(?:\s+ETA\s+([^\s]+))?',
    re.IGNORECASE
)
PROGRESS_REGEX = PROGRESS_VOD_REGEX  # Backwards compatibility alias
PROGRESS_SIMPLE_REGEX = re.compile(r'\[download\]\s+([\d\.]+)%')
PROGRESS_LIVE_REGEX = re.compile(
    r'\[download\]\s+([\d\.]+[A-Za-z]+)\s+at\s+([^\s]+)(?:\s+\(([\d:]+)\))?',
    re.IGNORECASE
)
FFMPEG_PROGRESS_REGEX = re.compile(
    r'(?:frame=\s*\d+.*?)?size=\s*([^\s]+)\s+time=\s*([\d:.]+)\s+bitrate=\s*([^\s]+)\s+speed=\s*([^\s]+)',
    re.IGNORECASE
)
ARIA2_PROGRESS_REGEX = re.compile(
    r'\[#\w+\s+([^\/]+)\/([^\(]+)\(([\d\.]+)%\)\s+CN:\d+\s+DL:([^\s]+)(?:\s+ETA:([^\s\]]+))?',
    re.IGNORECASE
)
DESTINATION_REGEX = re.compile(
    r'(?:\[download\] Destination: |\[Merger\] Merging formats into "|\[ExtractAudio\] Destination: |\[Fixup[A-Za-z0-9]+\] Fixing .+ in ")([^"\r\n]+)',
    re.IGNORECASE
)
PROGRESS_FRAG_REGEX = re.compile(
    r'\[download\]\s+(?:([\d\.]+[A-Za-z]+)\s+at\s+([^\s]+))?.*\(frag\s+(\d+)(?:/(\d+|\w+))?\)',
    re.IGNORECASE
)

# Container fixup constants & routines for live streams (fixing MPEG-TS saved as .mp4)
EXT_TO_CONTAINER = {
    'mp4': 'mp4', 'm4v': 'mp4', 'mov': 'mp4', 'm4a': 'mp4',
    'mkv': 'matroska', 'flv': 'flv', 'ts': 'mpegts'
}
CONTAINER_TO_EXT = {'mpegts': 'ts', 'flv': 'flv', 'mp4': 'mp4', 'matroska': 'mkv'}
_MP4_BOXES = (b'ftyp', b'moov', b'mdat', b'free', b'skip', b'wide')


def sniff_container(path: Union[str, Path]) -> Optional[str]:
    """Return 'mpegts' | 'flv' | 'mp4' | 'matroska' | None from magic bytes."""
    try:
        with open(path, 'rb') as f:
            head = f.read(188 * 16)
    except OSError:
        return None
    if not head:
        return None
    if head[:4] == b'FLV\x01' or head[:3] == b'FLV':
        return 'flv'
    if head[4:8] in _MP4_BOXES or (len(head) >= 12 and head[8:12] in _MP4_BOXES):
        return 'mp4'
    if head[:4] == b'\x1a\x45\xdf\xa3':
        return 'matroska'
    if len(head) >= 188 * 2:
        for stride in (188, 192, 204):
            for off in range(min(stride, len(head) - stride)):
                if off + stride * 3 <= len(head):
                    if all(head[off + i * stride] == 0x47 for i in range(4 if off + stride * 4 <= len(head) else 3)):
                        return 'mpegts'
        if head[0] == 0x47 and len(head) >= 376 and head[188] == 0x47:
            return 'mpegts'
    return None


def find_recent_output_file(label: str) -> Optional[str]:
    """Finds the most recently modified media file in the output directory if label was configured in yt-dlp.conf."""
    try:
        m = re.search(r'\((.+)\)', label)
        d = Path(m.group(1)) if m else Path.cwd()
        if not d.is_dir():
            d = Path.cwd()
        candidates = []
        for ext in ('*.mp4', '*.mp4.part', '*.mkv', '*.mkv.part', '*.ts', '*.flv'):
            for f in d.glob(ext):
                try:
                    if f.is_file() and f.stat().st_size > 0 and (time.time() - f.stat().st_mtime) < 1800:
                        candidates.append((f.stat().st_mtime, f))
                except Exception:
                    pass
        if candidates:
            candidates.sort(key=lambda x: x[0], reverse=True)
            chosen = candidates[0][1]
            if chosen.suffix == '.part':
                clean_target = chosen.with_suffix('')
                try:
                    chosen.rename(clean_target)
                    return str(clean_target)
                except Exception:
                    return str(chosen)
            return str(chosen)
    except Exception:
        pass
    return None


def parse_speed_to_bps(speed_str: Optional[str]) -> float:
    """Converts speed strings like '14.20MiB/s', '2.5 MB/s', or '1.01x (2422kbits/s)' into bytes/sec."""
    if not speed_str or speed_str == "--":
        return 0.0
    s = str(speed_str)
    # Check bytes/sec formats first (MiB/s, MB/s, KiB/s, KB/s, B/s, GiB/s)
    m = re.search(r'([\d\.]+)\s*(GiB|GB|MiB|MB|KiB|KB|B)/s', s, re.IGNORECASE)
    if m:
        val = float(m.group(1))
        unit = m.group(2).lower()
        mult = {
            "b": 1.0,
            "kb": 1000.0, "kib": 1024.0,
            "mb": 1000.0 ** 2, "mib": 1024.0 ** 2,
            "gb": 1000.0 ** 3, "gib": 1024.0 ** 3,
        }.get(unit, 1.0)
        return val * mult
    # Check ffmpeg bitrate formats like 2422.1kbits/s
    m_bit = re.search(r'([\d\.]+)\s*(k|m|g)?bits/s', s, re.IGNORECASE)
    if m_bit:
        val = float(m_bit.group(1))
        prefix = (m_bit.group(2) or "").lower()
        mult = {"": 1.0, "k": 1000.0, "m": 1000.0 ** 2, "g": 1000.0 ** 3}.get(prefix, 1.0)
        return (val * mult) / 8.0
    return 0.0


def probe_media_details(file_path: Union[str, Path]) -> Dict[str, Any]:
    """
    Deep technical media inspection powered by ffprobe + magic-byte container sniffer.
    Returns codecs, resolution, fps, bitrate, duration, audio specs, and container health.
    """
    p = Path(file_path)
    details: Dict[str, Any] = {
        "ffprobe_available": False,
        "video_codec": None,
        "audio_codec": None,
        "resolution": None,
        "fps": None,
        "duration_sec": None,
        "duration_formatted": None,
        "bitrate_kbps": None,
        "sample_rate": None,
        "audio_channels": None,
        "format_name": None,
        "streams_count": 0,
    }
    ffprobe_bin = find_ffprobe()
    if not ffprobe_bin or not p.exists():
        return details

    details["ffprobe_available"] = True
    try:
        cmd = [
            ffprobe_bin, "-v", "quiet",
            "-print_format", "json",
            "-show_format", "-show_streams",
            str(p)
        ]
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=8, encoding="utf-8", errors="replace")
        if res.returncode != 0 or not res.stdout.strip():
            return details
        payload = json.loads(res.stdout)
        fmt = payload.get("format") or {}
        streams = payload.get("streams") or []
        details["streams_count"] = len(streams)
        details["format_name"] = fmt.get("format_name")

        if fmt.get("duration"):
            try:
                dur = float(fmt["duration"])
                details["duration_sec"] = round(dur, 1)
                hrs = int(dur // 3600)
                mins = int((dur % 3600) // 60)
                secs = int(dur % 60)
                details["duration_formatted"] = f"{hrs:02d}:{mins:02d}:{secs:02d}" if hrs else f"{mins:02d}:{secs:02d}"
            except Exception:
                pass
        if fmt.get("bit_rate"):
            try:
                details["bitrate_kbps"] = round(int(fmt["bit_rate"]) / 1000)
            except Exception:
                pass

        for st in streams:
            ctype = st.get("codec_type")
            if ctype == "video" and not details["video_codec"]:
                details["video_codec"] = (st.get("codec_name") or "").upper()
                w, h = st.get("width"), st.get("height")
                if w and h:
                    details["resolution"] = f"{w}x{h}"
                fr = st.get("avg_frame_rate") or st.get("r_frame_rate")
                if fr and "/" in str(fr):
                    try:
                        num, den = str(fr).split("/", 1)
                        if float(den) > 0:
                            fps_val = float(num) / float(den)
                            if 0 < fps_val < 300:
                                details["fps"] = round(fps_val, 2)
                    except Exception:
                        pass
            elif ctype == "audio" and not details["audio_codec"]:
                details["audio_codec"] = (st.get("codec_name") or "").upper()
                if st.get("sample_rate"):
                    details["sample_rate"] = f"{int(st['sample_rate']) / 1000:.1f} kHz"
                if st.get("channels"):
                    details["audio_channels"] = f"{st['channels']}ch"
    except Exception:
        pass
    return details


def scan_folder_for_repairs(folder_path: Union[str, Path]) -> List[Dict[str, Any]]:
    """Scans a directory for media files that have container mismatches, legacy FLV, or incomplete .part extensions."""
    root = Path(folder_path)
    if not root.exists() or not root.is_dir():
        return []
    found: List[Dict[str, Any]] = []
    exts = ("*.mp4", "*.ts", "*.flv", "*.mkv", "*.part", "*.m4v", "*.mov")
    seen = set()
    for pat in exts:
        for p in root.glob(pat):
            if p in seen or not p.is_file():
                continue
            seen.add(p)
            try:
                size = p.stat().st_size
                if size == 0:
                    continue
                have = sniff_container(p)
                ext = p.suffix.lstrip(".").lower()
                is_flv = (have == "flv" or ext == "flv")
                is_part = (ext == "part")
                is_ts_mismatch = (have == "mpegts" and ext != "ts")
                is_mismatched = is_flv or is_part or is_ts_mismatch or (
                    have and ext not in (have, "part") and not (ext == "mp4" and have == "mp4")
                )
                found.append({
                    "path": str(p),
                    "filename": p.name,
                    "extension": ext,
                    "detected_container": have or "unknown",
                    "size_mb": round(size / (1024 * 1024), 2),
                    "is_mismatched": bool(is_mismatched),
                    "reason": "Legacy FLV" if is_flv else ("Incomplete .part" if is_part else ("MPEG-TS inside ." + ext if is_ts_mismatch else ("Container mismatch" if is_mismatched else "Clean"))),
                })
            except Exception:
                continue
    # Show mismatched files first
    found.sort(key=lambda x: (not x["is_mismatched"], x["filename"].lower()))
    return found


def fixup_recorded_file(
    file_path: Union[str, Path],
    on_output: Optional[Callable[[str], None]] = None,
    preferred_container: str = "mp4"
) -> Path:
    """
    Checks if recorded file container matches its file extension or is a legacy container (e.g. .flv).
    - If input is FLV (or container is flv), normalizes/remuxes it into a modern, fully playable .mp4
      (with .mkv fallback if legacy codecs require Matroska, or high-speed transcode if stream copy fails).
    - If container is MPEG-TS inside .mp4, remuxes to clean MP4 with faststart.
    - If .part file, removes .part and repairs the underlying container.
    Returns the final, fully playable Path.
    """
    p = Path(file_path)
    if not p.exists() or not p.is_file() or p.stat().st_size == 0:
        return p

    target_p = p
    if p.suffix.lower() == '.part':
        target_p = p.with_suffix('')
        ext = target_p.suffix.lstrip('.').lower()
    else:
        ext = p.suffix.lstrip('.').lower()

    have = sniff_container(p)
    if not have:
        return p

    is_flv = (have == 'flv' or ext == 'flv')

    if is_flv:
        # Target format for FLV is modern MP4 (or MKV if requested)
        want = 'mp4' if preferred_container.lower() != 'mkv' else 'matroska'
        final_ext = 'mp4' if want == 'mp4' else 'mkv'
        target_p = target_p.with_suffix(f'.{final_ext}')
    else:
        want = EXT_TO_CONTAINER.get(ext, 'mp4')
        if want == have and p == target_p:
            return p  # Already matching and not .part

    dest_desc = "MP4 / MKV" if is_flv else want
    msg = f"[StreamVortex Fixup] Container '{have}' -> '{dest_desc}'. Normalizing to fully playable media..."
    if on_output:
        on_output(msg)

    ffmpeg_bin = find_ffmpeg()
    if ffmpeg_bin:
        in_size = p.stat().st_size
        in_opts = ['-y', '-fflags', '+genpts+discardcorrupt', '-err_detect', 'ignore_err', '-i', str(p)]
        base_copy = ['-map', '0:v?', '-map', '0:a?', '-sn', '-dn', '-c', 'copy',
                     '-avoid_negative_ts', 'make_zero', '-max_muxing_queue_size', '4096']

        # Construct prioritized attempts for MP4 and MKV: (target_extension, [ffmpeg args])
        attempts: List[Tuple[str, List[str]]] = []

        if is_flv:
            # 1. Lossless MP4 with AAC bitstream filter
            attempts.append(('mp4', base_copy + ['-bsf:a', 'aac_adtstoasc', '-f', 'mp4', '-movflags', '+faststart']))
            # 2. Lossless MP4 direct copy
            attempts.append(('mp4', base_copy + ['-f', 'mp4', '-movflags', '+faststart']))
            # 3. Lossless MKV (Matroska natively accepts VP6, FLV1, Nellymoser, Speex without re-encoding)
            attempts.append(('mkv', base_copy + ['-f', 'matroska']))
            # 4. Universal high-speed transcode to MP4 (guarantees 100% playable file on any media player)
            attempts.append(('mp4', [
                '-map', '0:v?', '-map', '0:a?',
                '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '18', '-pix_fmt', 'yuv420p',
                '-c:a', 'aac', '-b:a', '192k',
                '-avoid_negative_ts', 'make_zero', '-max_muxing_queue_size', '4096',
                '-f', 'mp4', '-movflags', '+faststart'
            ]))
        else:
            if want == 'mp4':
                attempts.append(('mp4', base_copy + ['-bsf:a', 'aac_adtstoasc', '-f', 'mp4', '-movflags', '+faststart']))
                attempts.append(('mp4', base_copy + ['-f', 'mp4', '-movflags', '+faststart']))
                attempts.append(('mkv', base_copy + ['-f', 'matroska']))
            elif want == 'matroska':
                attempts.append(('mkv', base_copy + ['-f', 'matroska']))
            else:
                attempts.append((ext, base_copy + ['-f', want]))

        for out_ext, out_args in attempts:
            candidate_dst = target_p.with_suffix(f'.{out_ext}')
            tmp_dst = target_p.with_name(f"{target_p.stem}.fix.{out_ext}")
            cmd = [ffmpeg_bin] + in_opts + out_args + [str(tmp_dst)]
            try:
                res = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, timeout=120)
                out_size = tmp_dst.stat().st_size if tmp_dst.exists() else 0
                if res.returncode == 0 and out_size > 0 and out_size >= in_size * 0.3:
                    try:
                        shutil.copystat(p, tmp_dst)
                    except Exception:
                        pass

                    # Windows-safe atomic move/replace
                    for retry in range(4):
                        try:
                            if candidate_dst.exists() and candidate_dst.resolve() != tmp_dst.resolve():
                                candidate_dst.unlink(missing_ok=True)
                            tmp_dst.rename(candidate_dst)
                            break
                        except PermissionError:
                            time.sleep(0.15)
                    else:
                        candidate_dst.unlink(missing_ok=True)
                        tmp_dst.rename(candidate_dst)

                    # Remove source file if distinct (e.g. .flv or .part)
                    if p.exists() and p.resolve() != candidate_dst.resolve():
                        try:
                            p.unlink(missing_ok=True)
                        except Exception:
                            pass

                    done_msg = f"[StreamVortex Fixup] Successfully fixed and converted {have} into fully playable .{out_ext}: {candidate_dst.name}"
                    if on_output:
                        on_output(done_msg)
                    return candidate_dst
            except Exception:
                pass
            finally:
                if tmp_dst.exists():
                    try:
                        tmp_dst.unlink(missing_ok=True)
                    except Exception:
                        pass

    # Fallback: rename to honest extension so media players open without container error
    new_ext = CONTAINER_TO_EXT.get(have)
    if new_ext:
        honest_path = target_p.with_suffix(f".{new_ext}")
        cand = honest_path
        n = 0
        while cand.exists():
            n += 1
            cand = target_p.with_name(f"{target_p.stem}_{n}.{new_ext}")
        try:
            if p != cand and p.exists():
                p.rename(cand)
            warn_msg = f"[StreamVortex Fixup] Remux unavailable; safely renamed to '{cand.name}' (valid {have})."
            if on_output:
                on_output(warn_msg)
            return cand
        except Exception:
            pass

    return p


def extract_audio_from_file(
    file_path: Union[str, Path],
    audio_format: str = "mp3",
    on_output: Optional[Callable[[str], None]] = None
) -> Optional[Path]:
    """Extracts high-quality MP3 (320k) or lossless AAC M4A audio from any media file via FFmpeg."""
    p = Path(file_path)
    if not p.exists() or not p.is_file():
        return None
    ffmpeg_bin = find_ffmpeg()
    if not ffmpeg_bin:
        return None
    fmt = "m4a" if audio_format.lower() == "m4a" else "mp3"
    out_p = p.with_suffix(f".{fmt}")
    if out_p.resolve() == p.resolve():
        out_p = p.with_name(f"{p.stem}_audio.{fmt}")
    if fmt == "mp3":
        cmd = [ffmpeg_bin, "-y", "-i", str(p), "-vn", "-c:a", "libmp3lame", "-b:a", "320k", str(out_p)]
    else:
        cmd = [ffmpeg_bin, "-y", "-i", str(p), "-vn", "-c:a", "aac", "-b:a", "256k", "-movflags", "+faststart", str(out_p)]
    try:
        res = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, timeout=180)
        if res.returncode == 0 and out_p.exists() and out_p.stat().st_size > 0:
            if on_output:
                on_output(f"[StreamVortex Audio] Extracted {fmt.upper()}: {out_p.name}")
            return out_p
    except Exception:
        pass
    return None


class DownloadManager:
    """Thread-safe active download tracker with process management, telemetry history, and live console logs."""
    def __init__(self):
        self._lock = threading.Lock()
        self._jobs: Dict[str, Dict[str, Any]] = {}
        self._console_logs: List[Dict[str, Any]] = []
        self._telemetry_points: List[Dict[str, Any]] = []

    def append_log(self, job_id: Optional[str], line: str, level: str = "info"):
        if not line:
            return
        low = line.lower()
        if level == "info":
            if "error" in low or "failed" in low or "aborted" in low:
                level = "error"
            elif "warning" in low or "warn" in low or "retrying" in low:
                level = "warn"
            elif "successfully" in low or "100%" in low or "merging" in low or "finished" in low:
                level = "success"
        entry = {
            "ts": time.strftime("%H:%M:%S"),
            "job_id": job_id or "system",
            "level": level,
            "line": line[:500],
        }
        with self._lock:
            self._console_logs.append(entry)
            if len(self._console_logs) > 350:
                self._console_logs = self._console_logs[-350:]
            if job_id and job_id in self._jobs:
                job_logs = self._jobs[job_id].setdefault("logs", [])
                job_logs.append(entry)
                if len(job_logs) > 120:
                    self._jobs[job_id]["logs"] = job_logs[-120:]

    def get_console_logs(self, limit: int = 200) -> List[Dict[str, Any]]:
        with self._lock:
            return list(self._console_logs[-limit:])

    def clear_console_logs(self):
        with self._lock:
            self._console_logs.clear()

    def start_job(
        self,
        job_id: str,
        title: str,
        url: str,
        is_live: bool = False,
        options: Optional[Dict[str, Any]] = None,
        platform: Optional[str] = None,
        container: Optional[str] = None,
    ) -> Dict[str, Any]:
        with self._lock:
            job = {
                "id": job_id,
                "title": title or "Media Download",
                "url": url,
                "is_live": is_live,
                "status": "starting",
                "progress": 0.0,
                "percent": 0.0,
                "speed": "--",
                "speed_bps": 0.0,
                "eta": "--",
                "size": "--",
                "completed": False,
                "success": False,
                "error": None,
                "process": None,
                "target_path": None,
                "saved_path": None,
                "stop_requested": False,
                "start_time": time.time(),
                "end_time": None,
                "platform": platform or "",
                "container": container or "mp4",
                "options": dict(options) if isinstance(options, dict) else {},
                "logs": [],
            }
            self._jobs[job_id] = job
            return job

    def register_process(self, job_id: str, proc: subprocess.Popen, target_path: Optional[str] = None):
        with self._lock:
            if job_id in self._jobs:
                self._jobs[job_id]["process"] = proc
                if target_path:
                    self._jobs[job_id]["target_path"] = target_path

    def update_job(
        self,
        job_id: str,
        progress: Optional[float] = None,
        speed: str = "--",
        eta: str = "--",
        size: str = "--",
        status: Optional[str] = None,
        saved_path: Optional[str] = None
    ):
        with self._lock:
            if job_id in self._jobs:
                u: Dict[str, Any] = {}
                if progress is not None:
                    u["progress"] = progress
                    u["percent"] = progress
                if speed != "--":
                    u["speed"] = speed
                    bps = parse_speed_to_bps(speed)
                    u["speed_bps"] = bps
                    if bps > 0:
                        self._record_telemetry_locked()
                if eta != "--":
                    u["eta"] = eta
                if size != "--":
                    u["size"] = size
                if status is not None:
                    u["status"] = status
                if saved_path:
                    u["saved_path"] = saved_path
                self._jobs[job_id].update(u)

    def _record_telemetry_locked(self):
        now = time.time()
        total_bps = sum(
            float(j.get("speed_bps") or 0.0)
            for j in self._jobs.values()
            if not j.get("completed")
        )
        if self._telemetry_points and (now - self._telemetry_points[-1]["t"]) < 0.7:
            self._telemetry_points[-1]["bps"] = total_bps
        else:
            self._telemetry_points.append({"t": now, "bps": total_bps})
            if len(self._telemetry_points) > 48:
                self._telemetry_points = self._telemetry_points[-48:]

    def get_telemetry_snapshot(self) -> Dict[str, Any]:
        with self._lock:
            active_jobs = [j for j in self._jobs.values() if not j.get("completed")]
            completed_jobs = [j for j in self._jobs.values() if j.get("completed")]
            total_bps = sum(float(j.get("speed_bps") or 0.0) for j in active_jobs)
            now = time.time()
            # Keep chart ticking smoothly even when idle/steady
            if not self._telemetry_points or (now - self._telemetry_points[-1]["t"]) >= 1.0:
                self._telemetry_points.append({"t": now, "bps": total_bps})
                if len(self._telemetry_points) > 48:
                    self._telemetry_points = self._telemetry_points[-48:]
            peak_bps = max((p["bps"] for p in self._telemetry_points), default=0.0)
            return {
                "active_count": len(active_jobs),
                "completed_count": len(completed_jobs),
                "current_bps": total_bps,
                "current_mbps": round(total_bps / (1024 * 1024), 2),
                "peak_mbps": round(peak_bps / (1024 * 1024), 2),
                "series": [round(p["bps"] / (1024 * 1024), 2) for p in self._telemetry_points[-36:]],
            }

    def stop_job(self, job_id: str) -> bool:
        """
        Gracefully stops a live recording or active download.
        Preserves whatever content was recorded, avoids file corruption, and marks job stopped.
        """
        proc = None
        target_path = None
        with self._lock:
            if job_id not in self._jobs:
                return False
            job = self._jobs[job_id]
            job["stop_requested"] = True
            job["status"] = "stopped"
            proc = job.get("process")
            target_path = job.get("saved_path") or job.get("target_path")

        if proc and proc.poll() is None:
            # 1. Try sending 'q' to stdin (standard FFmpeg quit command)
            try:
                if proc.stdin and not proc.stdin.closed:
                    proc.stdin.write("q\n")
                    proc.stdin.flush()
            except Exception:
                pass

            # 2. Terminate gracefully
            try:
                proc.terminate()
            except Exception:
                pass

            # 3. Wait up to 2.5 seconds for container finalization
            try:
                proc.wait(timeout=2.5)
            except Exception:
                pass

            # 4. If still running, enforce tree-kill to eliminate orphaned child processes (ffmpeg.exe, yt-dlp.exe)
            if proc.poll() is None:
                if sys.platform == "win32":
                    try:
                        subprocess.run(
                            ["taskkill", "/F", "/T", "/PID", str(proc.pid)],
                            stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL,
                            timeout=3
                        )
                    except Exception:
                        pass
                try:
                    proc.kill()
                    proc.wait(timeout=1.0)
                except Exception:
                    pass

        # 4. Check if a partial or downloaded file exists and promote .part if needed
        found_target = None
        if target_path and not str(target_path).startswith("Configured in"):
            p = Path(target_path)
            part_p = Path(f"{target_path}.part")
            if part_p.exists() and part_p.stat().st_size > 0:
                try:
                    if not p.exists():
                        part_p.rename(p)
                        found_target = p
                    else:
                        found_target = p
                except Exception:
                    found_target = part_p
            elif p.exists() and p.stat().st_size > 0:
                found_target = p

        if not found_target:
            cand = find_recent_output_file(str(target_path or ""))
            if cand:
                found_target = Path(cand)

        # 5. Fix container mismatch on the promoted file (e.g. MPEG-TS inside .mp4, FLV, etc.)
        if found_target and found_target.exists() and found_target.stat().st_size > 0:
            try:
                fixed_p = fixup_recorded_file(found_target)
                with self._lock:
                    if job_id in self._jobs:
                        self._jobs[job_id]["saved_path"] = str(fixed_p)
            except Exception:
                pass

        with self._lock:
            if job_id in self._jobs:
                self._jobs[job_id]["completed"] = True
                self._jobs[job_id]["status"] = "stopped"

        return True

    def is_stop_requested(self, job_id: Optional[str]) -> bool:
        if not job_id:
            return False
        with self._lock:
            job = self._jobs.get(job_id)
            return bool(job and job.get("stop_requested"))

    def get_saved_path(self, job_id: Optional[str]) -> Optional[str]:
        if not job_id:
            return None
        with self._lock:
            job = self._jobs.get(job_id)
            return job.get("saved_path") if job else None

    def finish_job(self, job_id: str, success: bool = True, error: Optional[str] = None):
        with self._lock:
            if job_id in self._jobs:
                stopped = bool(self._jobs[job_id].get("stop_requested"))
                final_progress = self._jobs[job_id]["progress"] if stopped else (100.0 if success else self._jobs[job_id]["progress"])
                self._jobs[job_id].update({
                    "completed": True,
                    "success": bool(success or stopped),
                    "status": "stopped" if stopped else ("completed" if success else "failed"),
                    "progress": final_progress,
                    "percent": final_progress,
                    "speed_bps": 0.0,
                    "end_time": time.time(),
                    "error": error
                })

    @staticmethod
    def _serialize_job(job: Dict[str, Any]) -> Dict[str, Any]:
        out = {k: v for k, v in job.items() if k not in ("process", "logs")}
        start_t = float(job.get("start_time") or time.time())
        end_t = float(job.get("end_time") or time.time())
        out["elapsed"] = max(0, int((end_t if job.get("completed") else time.time()) - start_t))
        out["percent"] = out.get("progress", 0.0)
        out["logs_tail"] = (job.get("logs") or [])[-8:]
        return out

    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            return self._jobs.get(job_id)

    def get_serializable_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            job = self._jobs.get(job_id)
            return self._serialize_job(job) if job else None

    def get_active_jobs(self) -> List[Dict[str, Any]]:
        with self._lock:
            return list(self._jobs.values())

    def get_serializable_jobs(self) -> List[Dict[str, Any]]:
        with self._lock:
            return [self._serialize_job(j) for j in self._jobs.values()]

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
    progress_callback: Optional[Callable[..., None]] = None,
    conf_path: Optional[str] = None,
    title: Optional[str] = None,
    uploader: Optional[str] = None,
    respect_conf_output: bool = True,
    job_id: Optional[str] = None,
    container: Optional[str] = None,
    subtitles: Optional[bool] = None,
    embed_metadata: Optional[bool] = None,
    embed_thumbnail: Optional[bool] = None,
    sponsorblock: Optional[bool] = None,
    clip_start: Optional[str] = None,
    clip_end: Optional[str] = None,
    cookies_from_browser: Optional[str] = None,
    rate_limit: Optional[str] = None,
    format_id: Optional[str] = None,
    proxy: Optional[str] = None,
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
    clean_container = (container or "").strip().lower()
    ext_target = "m4a" if quality_preference == "audio_m4a" else ("mp3" if is_audio else (clean_container or "mp4"))

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
    if format_id and not is_audio:
        cmd.extend(["-f", f"{format_id}+bestaudio/{format_id}/best"])
        fmt_reason = f"Explicit format selected: {format_id}"
    else:
        fmt_args, fmt_reason = build_format_args(
            quality_preference=quality_preference,
            is_live=is_live,
            audio_only=audio_only,
            conf_path=conf
        )
        if fmt_args:
            cmd.extend(fmt_args)

    # Explicit output container override (MP4, MKV, WebM, TS, FLV)
    if clean_container and not is_audio and clean_container in ("mp4", "mkv", "webm", "flv", "ts"):
        if clean_container in ("mp4", "mkv", "webm"):
            cmd.extend(["--merge-output-format", clean_container])
            if not is_live:
                cmd.extend(["--remux-video", clean_container])

    # Subtitles, Metadata, Thumbnail, SponsorBlock toggles
    if subtitles is True and not is_live:
        cmd.extend(["--write-subs", "--write-auto-subs", "--sub-langs", "en.*", "--embed-subs"])
    elif subtitles is False:
        cmd.extend(["--no-write-subs", "--no-write-auto-subs"])

    if embed_metadata is True:
        cmd.append("--embed-metadata")
    elif embed_metadata is False:
        cmd.append("--no-embed-metadata")

    if embed_thumbnail is True and not is_live:
        cmd.append("--embed-thumbnail")
    elif embed_thumbnail is False:
        cmd.append("--no-embed-thumbnail")

    if sponsorblock is True and not is_live:
        cmd.extend(["--sponsorblock-remove", "sponsor,selfpromo"])

    # Interactive Clipper / Time-Range Trimmer
    c_start = (clip_start or "").strip()
    c_end = (clip_end or "").strip()
    if (c_start or c_end) and not is_live:
        s_tok = c_start if c_start else "00:00:00"
        e_tok = c_end if c_end else "inf"
        cmd.extend(["--download-sections", f"*{s_tok}-{e_tok}", "--force-keyframes-at-cuts"])

    # Browser Cookies & Proxy & Rate Limit (from call or saved studio config)
    cfg = get_config()
    eff_cookies = (cookies_from_browser if cookies_from_browser is not None else cfg.get("cookies_from_browser", "none")) or "none"
    eff_cookies = eff_cookies.strip().lower()
    if eff_cookies and eff_cookies != "none":
        cmd.extend(["--cookies-from-browser", eff_cookies])

    eff_rate = (rate_limit if rate_limit is not None else cfg.get("rate_limit", "")) or ""
    eff_rate = eff_rate.strip()
    if eff_rate and eff_rate.lower() != "unlimited":
        cmd.extend(["-r", eff_rate])

    eff_proxy = (proxy if proxy is not None else cfg.get("proxy", "")) or ""
    eff_proxy = eff_proxy.strip()
    if eff_proxy:
        cmd.extend(["--proxy", eff_proxy])

    if fmt_reason:
        msg = f"[StreamVortex Quality] {fmt_reason}"
        if job_id:
            DOWNLOAD_MANAGER.append_log(job_id, msg)
        if on_output:
            on_output(msg)
        else:
            print(msg)

    # 5. Live Streams Engine Overrides
    if is_live:
        cmd.extend([
            "--downloader", "native",
            "--no-live-from-start",
            "--no-part",
        ])
        # --hls-use-mpegts is valid only for HLS/m3u8 streams.
        # Raw FLV/RTMP feeds must NOT receive this flag — it would cause
        # yt-dlp to write MPEG-TS data into a .flv file, breaking playback.
        _su = stream_url.lower()
        _is_raw_flv = (
            _su.endswith('.flv') or
            _su.startswith('rtmp') or
            (_su.startswith('rtmpe')) or
            ('/flv' in _su and '.m3u8' not in _su)
        )
        if not _is_raw_flv:
            cmd.append("--hls-use-mpegts")

    # 5. Headers & Flags
    if referer:
        cmd.extend(["--referer", referer])

    extra_flags = [
        "--retries", "10",
        "--fragment-retries", "15",
        "--file-access-retries", "5",
        "--retry-sleep", "2",
        "--no-mtime",
        "--progress"
    ]
    if on_output or progress_callback or job_id:
        extra_flags.append("--newline")
    cmd.extend(extra_flags)

    # Option injection safety: append target stream URL at the very end
    cmd.extend(["--", stream_url])

    # Execution environment (aria2c disabled; yt-dlp native multi-threading -N 6 active)
    env = os.environ.copy()

    # 6. Run process with live output streaming, progress parsing & fault isolation
    target_clean_stem = Path(out_path_label).stem if (out_path_label and not out_path_label.startswith("Configured in")) else (title or "media")

    def dispatch_progress(pct: Optional[float], speed: str, eta: str, size: str = "--", status_desc: str = "Downloading"):
        if job_id:
            DOWNLOAD_MANAGER.update_job(job_id, progress=pct, speed=speed, eta=eta, size=size, status=status_desc)
        if not progress_callback:
            return
        try:
            progress_callback(pct, speed, eta, size, status_desc)
        except TypeError:
            try:
                progress_callback(pct, speed, eta)
            except Exception:
                pass

    if job_id or on_output or progress_callback:
        proc = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            env=env
        )
        last_dest_file: Optional[str] = None
        if job_id:
            DOWNLOAD_MANAGER.register_process(job_id, proc, target_path=out_path_label)

        try:
            if job_id:
                DOWNLOAD_MANAGER.append_log(job_id, f"$ {' '.join(cmd[:8])} ... {stream_url}")
            for line in proc.stdout:
                clean_line = line.strip()
                if job_id and clean_line:
                    DOWNLOAD_MANAGER.append_log(job_id, clean_line)
                if on_output:
                    on_output(clean_line)

                # Track destination file path
                m_dest = DESTINATION_REGEX.search(clean_line)
                if m_dest:
                    dest_file = m_dest.group(1).strip()
                    last_dest_file = dest_file
                    if job_id:
                        DOWNLOAD_MANAGER.update_job(job_id, saved_path=dest_file)

                if clean_line:
                    # 1. Standard VOD download progress
                    m_vod = PROGRESS_VOD_REGEX.search(clean_line)
                    if m_vod:
                        try:
                            pct = float(m_vod.group(1))
                            tot_size = m_vod.group(2)
                            spd = m_vod.group(3) or "--"
                            eta_val = m_vod.group(4) or "--"
                            dispatch_progress(pct, spd, eta_val, size=f"~{tot_size}", status_desc="Downloading")
                        except Exception:
                            pass
                        continue

                    # 2. FFMPEG muxing/live progress
                    m_ff = FFMPEG_PROGRESS_REGEX.search(clean_line)
                    if m_ff:
                        try:
                            sz = m_ff.group(1)
                            t_str = m_ff.group(2).split('.')[0]
                            bitrate = m_ff.group(3)
                            spd = m_ff.group(4)
                            if "KiB" in sz:
                                try:
                                    sz_num = float(sz.replace("KiB", "")) / 1024.0
                                    sz = f"{sz_num:.1f} MB"
                                except Exception:
                                    pass
                            dispatch_progress(None, f"{spd} ({bitrate})", f"REC {t_str}", size=sz, status_desc="Recording Live")
                        except Exception:
                            pass
                        continue

                    # 3. Live stream fragment & count progress
                    m_frag = PROGRESS_FRAG_REGEX.search(clean_line)
                    if m_frag:
                        try:
                            sz = m_frag.group(1) or "--"
                            spd = m_frag.group(2) or "--"
                            f_curr = m_frag.group(3)
                            f_tot = m_frag.group(4)
                            frag_info = f"Frag #{f_curr}" + (f"/{f_tot}" if f_tot and str(f_tot).lower() != 'unknown' else "")
                            dispatch_progress(None, spd, frag_info, size=sz, status_desc=f"Recording Live ({frag_info})")
                        except Exception:
                            pass
                        continue

                    # 3b. Native Live stream progress
                    m_live = PROGRESS_LIVE_REGEX.search(clean_line)
                    if m_live:
                        try:
                            bytes_down = m_live.group(1)
                            spd = m_live.group(2)
                            elapsed = m_live.group(3) or "--"
                            dispatch_progress(None, spd, f"REC {elapsed}", size=bytes_down, status_desc="Recording Live")
                        except Exception:
                            pass
                        continue

                    # 4. Aria2c progress line
                    m_aria = ARIA2_PROGRESS_REGEX.search(clean_line)
                    if m_aria:
                        try:
                            d_str = m_aria.group(1)
                            t_str = m_aria.group(2)
                            pct = float(m_aria.group(3))
                            spd = m_aria.group(4)
                            eta_val = m_aria.group(5) or "--"
                            dispatch_progress(pct, spd, eta_val, size=f"{d_str}/{t_str}", status_desc="Downloading")
                        except Exception:
                            pass
                        continue

                    # 5. Simple percentage progress
                    m_simple = PROGRESS_SIMPLE_REGEX.search(clean_line)
                    if m_simple:
                        try:
                            pct = float(m_simple.group(1))
                            dispatch_progress(pct, "--", "--", "--", "Downloading")
                        except Exception:
                            pass
                        continue

            proc.wait()
            retcode = proc.returncode
        except (KeyboardInterrupt, Exception):
            if proc.poll() is None:
                try:
                    proc.terminate()
                    proc.wait(timeout=2.0)
                except Exception:
                    pass
                if proc.poll() is None:
                    if sys.platform == "win32":
                        try:
                            subprocess.run(
                                ["taskkill", "/F", "/T", "/PID", str(proc.pid)],
                                stdout=subprocess.DEVNULL,
                                stderr=subprocess.DEVNULL,
                                timeout=3
                            )
                        except Exception:
                            pass
                    try:
                        proc.kill()
                        proc.wait(timeout=1.0)
                    except Exception:
                        pass
            retcode = 0 if is_live else 1
    else:
        try:
            retcode = subprocess.run(cmd, env=env).returncode
        except KeyboardInterrupt:
            if on_output:
                on_output("[StreamVortex] Interrupted by user. Finalizing and repairing container...")
            else:
                print("\n[StreamVortex] Interrupted by user. Finalizing and repairing container...")
            retcode = 0 if is_live else 1

    was_stopped = DOWNLOAD_MANAGER.is_stop_requested(job_id)
    actual_file = DOWNLOAD_MANAGER.get_saved_path(job_id) or last_dest_file or out_path_label

    if actual_file and str(actual_file).startswith("Configured in"):
        if last_dest_file:
            actual_file = last_dest_file
        else:
            cand = find_recent_output_file(out_path_label)
            if cand:
                actual_file = cand

    # Check whether valid output content was saved on disk
    file_exists = False
    if actual_file and not str(actual_file).startswith("Configured in"):
        p = Path(actual_file)
        if p.exists() and p.stat().st_size > 0:
            file_exists = True
        else:
            part_p = Path(f"{actual_file}.part")
            if part_p.exists() and part_p.stat().st_size > 0:
                try:
                    part_p.rename(p)
                    file_exists = True
                except Exception:
                    file_exists = True
                    actual_file = str(part_p)

    if not file_exists:
        cand = find_recent_output_file(out_path_label or str(target_dir))
        if cand:
            actual_file = cand
            file_exists = True

    # Normalize container if recorded live stream is MPEG-TS inside .mp4
    if file_exists:
        try:
            fixed_p = fixup_recorded_file(actual_file, on_output=on_output)
            actual_file = str(fixed_p)
            if job_id:
                DOWNLOAD_MANAGER.update_job(job_id, saved_path=actual_file)
        except Exception:
            pass

    if retcode == 0 or (file_exists and (was_stopped or is_live)):
        final_path = actual_file if file_exists else out_path_label
        entry_title = title or (Path(final_path).stem if final_path and not final_path.startswith("Configured in") else "Downloaded Media")
        add_history_entry(
            title=entry_title,
            filename=final_path,
            stream_url=stream_url,
            media_type="audio" if (audio_only or quality_preference in ("audio_mp3", "audio_m4a")) else ("live" if is_live else "video")
        )
        if job_id:
            DOWNLOAD_MANAGER.finish_job(job_id, success=True)
        return 0
    else:
        # Smart Fallback: if live stream capture fails via yt-dlp, seamlessly engage direct FFmpeg recorder
        if is_live and not was_stopped and find_ffmpeg():
            fallback_msg = f"[StreamVortex Fallback] yt-dlp live stream capture failed (code {retcode}). Seamlessly engaging FFmpeg direct stream recorder..."
            if on_output:
                on_output(fallback_msg)
            elif progress_callback:
                try:
                    progress_callback(None, "--", "--", "--", "Switching to FFmpeg...")
                except Exception:
                    pass
            ff_ret = run_ffmpeg_record(
                stream_url=stream_url,
                output_filename=output_filename,
                headers={"Referer": referer} if referer else None,
                title=title,
                uploader=uploader,
                on_output=on_output,
                progress_callback=progress_callback,
                job_id=job_id
            )
            if ff_ret == 0:
                return 0

        if job_id:
            DOWNLOAD_MANAGER.finish_job(job_id, success=False, error=f"Exit code {retcode}")
        # Automatic cleanup on true failures (preserve recorded data if stopped by user)
        if not (was_stopped and file_exists):
            cleanup_empty_or_broken_files(target_dir, target_stem=target_clean_stem)
        return retcode if retcode != 0 else 1


def run_ffmpeg_record(
    stream_url: str,
    output_filename: Optional[str] = None,
    headers: Optional[Dict[str, str]] = None,
    max_duration_seconds: Optional[int] = None,
    title: Optional[str] = None,
    uploader: Optional[str] = None,
    on_output: Optional[Callable[[str], None]] = None,
    progress_callback: Optional[Callable[..., None]] = None,
    job_id: Optional[str] = None
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
            progress_callback=progress_callback,
            job_id=job_id
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

    def dispatch_progress(pct: Optional[float], speed: str, eta: str, size: str = "--", status_desc: str = "Recording Live"):
        if job_id:
            DOWNLOAD_MANAGER.update_job(job_id, progress=pct, speed=speed, eta=eta, size=size, status=status_desc)
        if not progress_callback:
            return
        try:
            progress_callback(pct, speed, eta, size, status_desc)
        except TypeError:
            try:
                progress_callback(pct, speed, eta)
            except Exception:
                pass

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
        if job_id:
            DOWNLOAD_MANAGER.register_process(job_id, proc, target_path=str(out_path))

        for line in proc.stderr:
            clean_line = line.strip()
            if job_id and clean_line:
                DOWNLOAD_MANAGER.append_log(job_id, clean_line)
            if on_output:
                on_output(clean_line)
            if clean_line:
                m = FFMPEG_PROGRESS_REGEX.search(clean_line)
                if m:
                    sz = m.group(1)
                    t_str = m.group(2).split('.')[0]
                    bitrate = m.group(3)
                    speed = m.group(4)
                    if "KiB" in sz:
                        try:
                            sz_num = float(sz.replace("KiB", "")) / 1024.0
                            sz = f"{sz_num:.1f} MB"
                        except Exception:
                            pass
                    dispatch_progress(None, f"{speed} ({bitrate})", f"REC {t_str}", size=sz, status_desc="Recording Live")

        proc.wait()
        retcode = proc.returncode
    except KeyboardInterrupt:
        if proc.poll() is None:
            try:
                proc.stdin.write("q\n")
                proc.stdin.flush()
                proc.wait(timeout=3)
            except Exception:
                pass
            if proc.poll() is None:
                if sys.platform == "win32":
                    try:
                        subprocess.run(
                            ["taskkill", "/F", "/T", "/PID", str(proc.pid)],
                            stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL,
                            timeout=3
                        )
                    except Exception:
                        pass
                try:
                    proc.kill()
                except Exception:
                    pass
        retcode = 0
    except Exception as e:
        if on_output:
            on_output(f"[FFmpeg Error] {e}")
        retcode = 1

    was_stopped = DOWNLOAD_MANAGER.is_stop_requested(job_id)
    file_exists = out_path.exists() and out_path.stat().st_size > 0

    # Normalize container if recorded stream has container mismatch
    if file_exists:
        try:
            fixed_p = fixup_recorded_file(out_path, on_output=on_output)
            out_path = fixed_p
            if job_id:
                DOWNLOAD_MANAGER.update_job(job_id, saved_path=str(out_path))
        except Exception:
            pass

    if retcode == 0 or (was_stopped and file_exists):
        add_history_entry(
            title=title or out_path.stem,
            filename=str(out_path),
            stream_url=stream_url,
            media_type="live_record"
        )
        if job_id:
            DOWNLOAD_MANAGER.finish_job(job_id, success=True)
        return 0
    else:
        if job_id:
            DOWNLOAD_MANAGER.finish_job(job_id, success=False, error=f"FFmpeg exit {retcode}")
        if not (was_stopped and file_exists):
            cleanup_empty_or_broken_files(d_dir, out_path.stem)
        return retcode if retcode != 0 else 1
