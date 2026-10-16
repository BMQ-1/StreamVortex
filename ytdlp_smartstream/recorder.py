"""
StreamVortex Live Recorder & Watchdog Engine.
Handles automatic live detection, resilient stream recording, and Windows desktop notifications.
"""

import sys
import time
import shutil
import subprocess
from pathlib import Path
from typing import Optional, Dict, Callable

from .tiktok_resolver import resolve_tiktok_live, TikTokMediaResult

try:
    from winotify import Notification, audio
    HAS_WINOTIFY = True
except ImportError:
    HAS_WINOTIFY = False

try:
    import pyperclip
    HAS_PYPERCLIP = True
except ImportError:
    HAS_PYPERCLIP = False


def send_notification(title: str, msg: str):
    """Sends a native Windows 10/11 desktop toast notification."""
    if HAS_WINOTIFY and sys.platform == "win32":
        try:
            toast = Notification(
                app_id="StreamVortex",
                title=title,
                msg=msg,
                duration="short"
            )
            toast.set_audio(audio.Default, loop=False)
            toast.show()
            return
        except Exception:
            pass
    print(f"[{title}] {msg}")


def copy_to_clipboard(text: str) -> bool:
    """Copies stream URL or text to the Windows system clipboard."""
    if HAS_PYPERCLIP:
        try:
            pyperclip.copy(text)
            return True
        except Exception:
            pass
    return False


def wait_for_live(
    uploader: str,
    poll_interval: int = 15,
    on_live_start: Optional[Callable[[TikTokMediaResult], None]] = None,
    max_checks: Optional[int] = None
) -> Optional[TikTokMediaResult]:
    """
    Watchdog mode:
    Polls a creator's live status until they go live, then triggers on_live_start.
    """
    check_count = 0
    print(f"\n[StreamVortex Watchdog] Monitoring @{uploader} for LIVE broadcast...")
    print(f"[i] Checking every {poll_interval}s. Press Ctrl+C to abort.\n")

    while True:
        check_count += 1
        timestamp = time.strftime("%H:%M:%S")
        try:
            result = resolve_tiktok_live(uploader, timeout=8)
            if result and result.is_live and result.formats:
                print(f"\n[+] [{timestamp}] 🔴 LIVE DETECTED! @{uploader} is now streaming!")
                print(f"[+] Title: {result.title}")
                send_notification(
                    "StreamVortex: Live Started!",
                    f"@{uploader} is now streaming live: {result.title[:50]}"
                )
                if on_live_start:
                    on_live_start(result)
                return result
            else:
                sys.stdout.write(f"\r[{timestamp}] (Check #{check_count}) @{uploader} is offline. Waiting...")
                sys.stdout.flush()
        except Exception as e:
            sys.stdout.write(f"\r[{timestamp}] (Check #{check_count}) Error checking: {e}. Retrying...")
            sys.stdout.flush()

        if max_checks and check_count >= max_checks:
            print("\n[-] Reached maximum check limit.")
            return None

        time.sleep(poll_interval)


from .engine import run_ffmpeg_record, run_ytdlp_download


def record_stream(
    stream_url: str,
    output_filename: str,
    headers: Optional[Dict[str, str]] = None,
    max_duration_seconds: Optional[int] = None,
    auto_reconnect: bool = True,
    title: Optional[str] = None,
    uploader: Optional[str] = None
) -> int:
    """
    Records a live HLS or FLV stream to disk with automatic reconnect & recovery.
    """
    print(f"\n[StreamVortex] Starting live stream recording -> {output_filename}")
    code = run_ffmpeg_record(
        stream_url=stream_url,
        output_filename=output_filename,
        headers=headers,
        max_duration_seconds=max_duration_seconds,
        title=title,
        uploader=uploader
    )
    if code == 0:
        send_notification("StreamVortex: Recording Finished", f"Saved to {Path(output_filename).name}")
    return code

