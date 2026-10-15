"""
StreamVortex Configuration & State Manager.
Persists user settings, watchlist, and download history in a user-friendly JSON file.
"""

import json
from pathlib import Path
from typing import Dict, Any, List

CONFIG_DIR = Path.home() / ".streamvortex"
CONFIG_FILE = CONFIG_DIR / "config.json"
HISTORY_FILE = CONFIG_DIR / "history.json"
DEFAULT_DOWNLOAD_DIR = Path.home() / "Downloads"


def get_config() -> Dict[str, Any]:
    """Retrieves user settings with sensible defaults."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    defaults = {
        "download_dir": str(DEFAULT_DOWNLOAD_DIR),
        "default_quality": "best",
        "notifications": True,
        "preferred_player": "mpv",
        "watchlist": []
    }
    if not CONFIG_FILE.exists():
        save_config(defaults)
        return defaults

    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            # Ensure all default keys exist
            for k, v in defaults.items():
                data.setdefault(k, v)
            return data
    except Exception:
        return defaults


def save_config(config_data: Dict[str, Any]):
    """Saves settings to config file."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config_data, f, indent=2)


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
            return json.load(f)
    except Exception:
        return []


def add_history_entry(title: str, filename: str, stream_url: str, media_type: str = "video"):
    """Records a completed download to history."""
    history = get_history()
    import time
    entry = {
        "title": title,
        "filename": filename,
        "stream_url": stream_url,
        "type": media_type,
        "timestamp": time.time(),
        "date_str": time.strftime("%Y-%m-%d %H:%M:%S")
    }
    # Prepend new entry
    history.insert(0, entry)
    # Keep last 100 entries
    history = history[:100]
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    try:
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(history, f, indent=2)
    except Exception:
        pass


def get_watchlist() -> List[str]:
    """Returns list of tracked creators."""
    return get_config().get("watchlist", [])


def add_to_watchlist(creator: str) -> bool:
    """Adds a creator to the live watchlist."""
    cfg = get_config()
    wl = cfg.get("watchlist", [])
    creator_clean = creator.strip().lstrip("@").lower()
    if creator_clean and creator_clean not in wl:
        wl.append(creator_clean)
        cfg["watchlist"] = wl
        save_config(cfg)
        return True
    return False


def remove_from_watchlist(creator: str) -> bool:
    """Removes a creator from the live watchlist."""
    cfg = get_config()
    wl = cfg.get("watchlist", [])
    creator_clean = creator.strip().lstrip("@").lower()
    if creator_clean in wl:
        wl.remove(creator_clean)
        cfg["watchlist"] = wl
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
