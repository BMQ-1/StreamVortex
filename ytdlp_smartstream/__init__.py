"""
StreamVortex: Universal stream sniffer & resilient live/video extractor engine for yt-dlp.
"""

from .sniffer import smart_sniff, sniff_dynamic, sniff_static, SniffedStream
from .tiktok_resolver import (
    resolve_tiktok_live,
    resolve_tiktok_video,
    TikTokMediaResult,
    TikTokLiveResult
)
from .recorder import (
    record_stream,
    wait_for_live,
    copy_to_clipboard,
    send_notification
)
from .engine import (
    find_ytdlp,
    find_ffmpeg,
    run_ytdlp_download,
    run_ffmpeg_record
)
from .config import (
    get_config,
    save_config,
    get_download_dir,
    get_history,
    add_history_entry,
    get_watchlist,
    add_to_watchlist,
    remove_from_watchlist
)
from .doctor import run_doctor
from .wizard import run_wizard
from .web_ui import launch_web_ui

__all__ = [
    "smart_sniff",
    "sniff_dynamic",
    "sniff_static",
    "SniffedStream",
    "resolve_tiktok_live",
    "resolve_tiktok_video",
    "TikTokMediaResult",
    "TikTokLiveResult",
    "record_stream",
    "wait_for_live",
    "copy_to_clipboard",
    "send_notification",
    "find_ytdlp",
    "find_ffmpeg",
    "run_ytdlp_download",
    "run_ffmpeg_record",
    "get_config",
    "save_config",
    "get_download_dir",
    "get_history",
    "add_history_entry",
    "get_watchlist",
    "add_to_watchlist",
    "remove_from_watchlist",
    "run_doctor",
    "run_wizard",
    "launch_web_ui",
]

__version__ = "1.0.0"
