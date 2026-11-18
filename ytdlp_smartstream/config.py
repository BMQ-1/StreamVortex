"""
StreamVortex Configuration & State Manager.
Persists user settings, watchlist, and download history in a user-friendly JSON file.
"""

import json
import time
from pathlib import Path
from typing import Dict, Any, List, Optional

CONFIG_DIR = Path.home() / ".streamvortex"
CONFIG_FILE = CONFIG_DIR / "config.json"
HISTORY_FILE = CONFIG_DIR / "history.json"
DEFAULT_DOWNLOAD_DIR = Path.home() / "Downloads"

DEFAULT_CONFIG: Dict[str, Any] = {
    "download_dir": str(DEFAULT_DOWNLOAD_DIR),
    "default_quality": "best",
    "default_container": "mp4",
    "notifications": True,
    "preferred_player": "mpv",
    "watchlist": [],
    "watchlist_items": [],
    "max_concurrent_downloads": 2,
    "cookies_from_browser": "none",
    "rate_limit": "",
    "proxy": "",
    "clipboard_watch": False,
    "auto_remux": True,
    "sponsorblock": False,
    "subtitles": True,
    "embed_metadata": True,
    "embed_thumbnail": True,
    "watchdog_enabled": False,
    "watchdog_interval": 60,
    "watchdog_auto_record": False,
}


def _sync_watchlist_structures(data: Dict[str, Any]) -> Dict[str, Any]:
    """Keeps legacy `watchlist` (List[str]) and rich `watchlist_items` synchronized."""
    legacy = list(data.get("watchlist", []) or [])
    items = list(data.get("watchlist_items", []) or [])

    existing_handles = {str(it.get("handle", "")).strip().lstrip("@").lower() for it in items if isinstance(it, dict)}
    for handle in legacy:
        clean = str(handle).strip().lstrip("@").lower()
        if clean and clean not in existing_handles:
            items.append({
                "handle": clean,
                "platform": "tiktok",
                "url": f"https://www.tiktok.com/@{clean}/live",
                "auto_record": False,
            })
            existing_handles.add(clean)

    # Ensure legacy list reflects all handles
    synced_legacy = []
    for it in items:
        if isinstance(it, dict) and it.get("handle"):
            h = str(it["handle"]).strip().lstrip("@").lower()
            if h and h not in synced_legacy:
                synced_legacy.append(h)

    data["watchlist"] = synced_legacy
    data["watchlist_items"] = items
    return data


def get_config() -> Dict[str, Any]:
    """Retrieves user settings with sensible defaults."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    defaults = dict(DEFAULT_CONFIG)
    defaults["watchlist"] = []
    defaults["watchlist_items"] = []

    if not CONFIG_FILE.exists():
        save_config(defaults)
        return defaults

    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            if not isinstance(data, dict):
                return defaults
            for k, v in defaults.items():
                data.setdefault(k, v)
            return _sync_watchlist_structures(data)
    except Exception:
        return defaults


def save_config(config_data: Dict[str, Any]):
    """Saves settings to config file."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    synced = _sync_watchlist_structures(dict(config_data))
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(synced, f, indent=2)


def get_download_dir() -> Path:
    """Returns the configured download directory, creating it if needed."""
    cfg = get_config()
    d_dir = Path(cfg.get("download_dir", DEFAULT_DOWNLOAD_DIR))
    d_dir.mkdir(parents=True, exist_ok=True)
    return d_dir


def get_history() -> List[Dict[str, Any]]:
    """Loads recording and download history."""
    if not HISTORY_FILE.exists():
        return []
    try:
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            if not isinstance(data, list):
                return []
            # Normalize entries so both `type` and `media_type` exist
            for item in data:
                if isinstance(item, dict):
                    mt = item.get("media_type") or item.get("type") or "video"
                    item["type"] = mt
                    item["media_type"] = mt
                    if not item.get("date_str") and isinstance(item.get("timestamp"), (int, float)):
                        item["date_str"] = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(item["timestamp"]))
            return data
    except Exception:
        return []


def add_history_entry(
    title: str,
    filename: str,
    stream_url: str,
    media_type: str = "video",
    platform: Optional[str] = None,
    size_bytes: Optional[int] = None,
    thumbnail: Optional[str] = None,
):
    """Records a completed download to history."""
    history = get_history()
    if size_bytes is None and filename:
        try:
            p = Path(filename)
            if p.exists() and p.is_file():
                size_bytes = p.stat().st_size
        except Exception:
            size_bytes = None

    entry = {
        "title": title,
        "filename": filename,
        "stream_url": stream_url,
        "type": media_type,
        "media_type": media_type,
        "platform": platform or "",
        "size_bytes": size_bytes,
        "thumbnail": thumbnail or "",
        "timestamp": time.time(),
        "date_str": time.strftime("%Y-%m-%d %H:%M:%S"),
    }
    # Prepend new entry
    history.insert(0, entry)
    # Keep last 250 entries
    history = history[:250]
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    try:
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(history, f, indent=2)
    except Exception:
        pass


def remove_history_entry(filename: Optional[str] = None, timestamp: Optional[float] = None) -> bool:
    """Removes a specific entry from history by filename or timestamp."""
    history = get_history()
    new_history = []
    removed = False
    for h in history:
        match_ts = timestamp is not None and abs(float(h.get("timestamp", 0)) - float(timestamp)) < 0.01
        match_fn = filename and h.get("filename") == filename
        if not removed and (match_ts or match_fn):
            removed = True
            continue
        new_history.append(h)

    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    try:
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(new_history, f, indent=2)
        return removed
    except Exception:
        return False


def clear_history() -> bool:
    """Clears recording and download history."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    try:
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump([], f, indent=2)
        return True
    except Exception:
        return False


def get_watchlist() -> List[str]:
    """Returns list of tracked creator handles."""
    return get_config().get("watchlist", [])


def get_watchlist_items() -> List[Dict[str, Any]]:
    """Returns structured list of tracked creators with platform, URL, and auto-record flags."""
    return get_config().get("watchlist_items", [])


def _infer_watchdog_item(creator_or_url: str, platform: Optional[str] = None, auto_record: bool = False) -> Optional[Dict[str, Any]]:
    raw = creator_or_url.strip()
    if not raw:
        return None
    lower = raw.lower()
    inferred_platform = (platform or "").lower().strip()
    handle = raw.lstrip("@").strip()
    url = raw

    if lower.startswith(("http://", "https://")):
        if "tiktok.com" in lower:
            inferred_platform = "tiktok"
            import re
            m = re.search(r"@([\w.-]+)", raw)
            handle = m.group(1) if m else raw
            url = f"https://www.tiktok.com/@{handle}/live"
        elif "twitch.tv" in lower:
            inferred_platform = "twitch"
            part = raw.rstrip("/").split("/")[-1]
            handle = part.split("?")[0]
            url = f"https://www.twitch.tv/{handle}"
        elif "kick.com" in lower:
            inferred_platform = "kick"
            part = raw.rstrip("/").split("/")[-1]
            handle = part.split("?")[0]
            url = f"https://kick.com/{handle}"
        elif "youtube.com" in lower or "youtu.be" in lower:
            inferred_platform = "youtube"
            import re
            m = re.search(r"@([\w.-]+)", raw)
            handle = m.group(1) if m else raw.rstrip("/").split("/")[-1]
            url = raw if "/live" in lower else f"https://www.youtube.com/@{handle}/live"
        else:
            inferred_platform = inferred_platform or "generic"
            handle = raw.split("//", 1)[-1][:48]
            url = raw
    else:
        inferred_platform = inferred_platform or "tiktok"
        handle = raw.lstrip("@").strip().lower()
        if inferred_platform == "twitch":
            url = f"https://www.twitch.tv/{handle}"
        elif inferred_platform == "kick":
            url = f"https://kick.com/{handle}"
        elif inferred_platform == "youtube":
            url = f"https://www.youtube.com/@{handle}/live"
        else:
            inferred_platform = "tiktok"
            url = f"https://www.tiktok.com/@{handle}/live"

    return {
        "handle": handle.lower(),
        "platform": inferred_platform,
        "url": url,
        "auto_record": bool(auto_record),
    }


def add_to_watchlist(creator: str, platform: Optional[str] = None, auto_record: bool = False) -> bool:
    """Adds a creator or live channel URL to the live watchlist."""
    cfg = get_config()
    items = cfg.get("watchlist_items", [])
    item = _infer_watchdog_item(creator, platform=platform, auto_record=auto_record)
    if not item:
        return False

    key = (item["handle"], item["platform"])
    for existing in items:
        if (existing.get("handle", "").lower(), existing.get("platform", "tiktok").lower()) == key:
            return False

    items.append(item)
    cfg["watchlist_items"] = items
    wl = cfg.get("watchlist", [])
    if item["handle"] not in wl:
        wl.append(item["handle"])
    cfg["watchlist"] = wl
    save_config(cfg)
    return True


def update_watchlist_item(handle: str, auto_record: Optional[bool] = None, platform: Optional[str] = None) -> bool:
    """Updates flags on an existing watchlist item."""
    cfg = get_config()
    items = cfg.get("watchlist_items", [])
    clean = handle.strip().lstrip("@").lower()
    changed = False
    for it in items:
        if it.get("handle", "").lower() == clean and (not platform or it.get("platform") == platform):
            if auto_record is not None:
                it["auto_record"] = bool(auto_record)
            changed = True
    if changed:
        cfg["watchlist_items"] = items
        save_config(cfg)
    return changed


def remove_from_watchlist(creator: str, platform: Optional[str] = None) -> bool:
    """Removes a creator from the live watchlist."""
    cfg = get_config()
    wl = cfg.get("watchlist", [])
    items = cfg.get("watchlist_items", [])
    creator_clean = creator.strip().lstrip("@").lower()

    new_items = [
        it for it in items
        if not (it.get("handle", "").lower() == creator_clean and (not platform or it.get("platform") == platform))
    ]
    removed = len(new_items) != len(items) or creator_clean in wl
    if removed:
        cfg["watchlist_items"] = new_items
        cfg["watchlist"] = [w for w in wl if w.lower() != creator_clean]
        save_config(cfg)
        return True
    return False


if __name__ == "__main__":
    import os
    import sys
    import subprocess
    d = get_download_dir()
    if sys.platform == "win32":
        os.startfile(d)
    else:
        subprocess.run(["xdg-open", str(d)])
