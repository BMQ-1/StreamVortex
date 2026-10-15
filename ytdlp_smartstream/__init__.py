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


def __getattr__(name: str):
    if name == "run_wizard":
        from .wizard import run_wizard
        return run_wizard
    if name == "launch_web_ui":
        from .web_ui import launch_web_ui
        return launch_web_ui
    if name == "launch_desktop_gui":
        from .desktop import launch_desktop_gui
        return launch_desktop_gui
    if name == "setup_all_binaries":
        from .setup_binaries import setup_all_binaries
        return setup_all_binaries
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

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

__version__ = "1.0"
