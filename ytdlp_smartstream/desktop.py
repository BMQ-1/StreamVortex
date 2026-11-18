"""
StreamVortex Modern Desktop Studio (PyWebView Native Engine).
Universal yt-dlp & Live Stream Suite with:
- Multi-threaded embedded HTTP server (ThreadingHTTPServer) for zero-stall HLS & local media streaming
- Embedded HLS.js & local Range-streaming video monitor with Mark-In/Mark-Out clipper
- Native PyWebView bridge with two-way JS <-> Python API
- Concurrent batch download executor (1-4 workers) with 1-click job retry
- Real-time background Creator Watchdog daemon (TikTok, Twitch, Kick, YouTube, generic URLs)
- Deep ffprobe container inspection, batch folder scan, lossless remux, and audio extraction
- Live engine console logs & real-time throughput telemetry
- Built-in yt-dlp.conf editor, inline diagnostics, browser cookie auth, and 1-click yt-dlp updater
"""

import sys
import os
import re
import time
import json
import shutil
import socket
import mimetypes
import urllib.parse
import urllib.request
import threading
import subprocess
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from typing import Optional, Dict, Any, List

# Windows-specific process AppUserModelID and DPI awareness
if sys.platform == "win32":
    try:
        import ctypes
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass
    try:
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("streamvortex.studio.app.v2.0")
    except Exception:
        pass

try:
    import webview
    HAS_WEBVIEW = True
except ImportError:
    HAS_WEBVIEW = False

from .config import (
    get_download_dir, get_config, save_config,
    get_history, add_history_entry, remove_history_entry, clear_history,
    get_watchlist, get_watchlist_items, add_to_watchlist,
    update_watchlist_item, remove_from_watchlist,
)
from .engine import (
    find_ytdlp, find_ffmpeg, find_ffprobe, find_player, find_ytdlp_conf,
    find_global_python, get_conf_download_dir, update_ytdlp_conf_destinations,
    deploy_embedded_ytdlp_conf, build_format_args,
    resolve_stream_metadata, resolve_playlist_entries, run_ytdlp_download,
    check_free_disk_space, detect_platform, play_media_target, clean_target_url,
    sniff_container, probe_media_details, scan_folder_for_repairs,
    fixup_recorded_file, extract_audio_from_file, DOWNLOAD_MANAGER,
    DEFAULT_YTDLP_CONF_TEMPLATE,
)
from .sniffer import smart_sniff, DEFAULT_USER_AGENT
from .tiktok_resolver import resolve_tiktok_live_fast, resolve_tiktok_live, resolve_tiktok_video
from .onboarding import check_environment_status, launch_onboarding_gui
from .doctor import run_doctor
from .recorder import send_notification


def get_asset_path(filename: str) -> Optional[Path]:
    """Finds an asset file across workspace and frozen bundles."""
    meipass = getattr(sys, "_MEIPASS", None)
    candidates = [
        Path(meipass) / "assets" / filename if meipass else None,
        Path(meipass) / filename if meipass else None,
        Path(__file__).resolve().parent.parent / "assets" / filename,
        Path(__file__).resolve().parent / "assets" / filename,
        Path(sys.executable).parent / "assets" / filename if getattr(sys, "frozen", False) else None,
        Path(__file__).resolve().parent.parent / filename,
        Path(sys.executable).parent / filename if getattr(sys, "frozen", False) else None,
    ]
    for c in candidates:
        if c and c.exists():
            return c
    return None


def find_free_port(start_port: int = 8765) -> int:
    """Finds an available local port for the embedded studio server."""
    for port in range(start_port, start_port + 50):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(('127.0.0.1', port))
                return port
        except OSError:
            continue
    return start_port


class ReusableThreadingHTTPServer(ThreadingHTTPServer):
    allow_reuse_address = True
    daemon_threads = True


# =============================================================================
# BACKGROUND CREATOR WATCHDOG DAEMON
# =============================================================================

class WatchdogService:
    """Background live channel monitor with auto-record and desktop notifications."""

    def __init__(self, api_ref: "StreamVortexApi"):
        self._api = api_ref
        self._lock = threading.Lock()
        self._status_map: Dict[str, Dict[str, Any]] = {}
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._last_cycle_at: Optional[float] = None
        self._active_auto_records: Dict[str, str] = {}  # key -> job_id

    def start(self):
        with self._lock:
            if self._running:
                return
            self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self):
        with self._lock:
            self._running = False

    def _item_key(self, handle: str, platform: str = "tiktok") -> str:
        return f"{(platform or 'tiktok').lower()}:{handle.strip().lstrip('@').lower()}"

    def get_cached_status(self, handle: str, platform: str = "tiktok") -> Dict[str, Any]:
        with self._lock:
            return dict(self._status_map.get(self._item_key(handle, platform), {}))

    def set_cached_status(self, handle: str, platform: str, status: Dict[str, Any]):
        with self._lock:
            self._status_map[self._item_key(handle, platform)] = {
                **status,
                "checked_at": time.strftime("%H:%M:%S"),
            }

    def get_snapshot(self) -> Dict[str, Any]:
        cfg = get_config()
        items = get_watchlist_items()
        enriched = []
        with self._lock:
            for it in items:
                key = self._item_key(it.get("handle", ""), it.get("platform", "tiktok"))
                st = self._status_map.get(key, {})
                rec_job_id = self._active_auto_records.get(key)
                is_rec = False
                if rec_job_id:
                    job = DOWNLOAD_MANAGER.get_job(rec_job_id)
                    if job and not job.get("completed"):
                        is_rec = True
                    else:
                        self._active_auto_records.pop(key, None)
                enriched.append({
                    "handle": it.get("handle", ""),
                    "platform": it.get("platform", "tiktok"),
                    "url": it.get("url", ""),
                    "auto_record": bool(it.get("auto_record", False)),
                    "is_live": bool(st.get("is_live", False)),
                    "title": st.get("title", ""),
                    "stream_url": st.get("stream_url", ""),
                    "checked_at": st.get("checked_at", "Never"),
                    "is_recording": is_rec,
                    "recording_job_id": rec_job_id if is_rec else None,
                })
            last_str = time.strftime("%H:%M:%S", time.localtime(self._last_cycle_at)) if self._last_cycle_at else "Idle"
        return {
            "enabled": bool(cfg.get("watchdog_enabled", False)),
            "interval": int(cfg.get("watchdog_interval", 60)),
            "global_auto_record": bool(cfg.get("watchdog_auto_record", False)),
            "last_cycle": last_str,
            "items": enriched,
        }

    def check_item(self, handle: str, platform: str = "tiktok", url: Optional[str] = None, trigger_auto: bool = False) -> Dict[str, Any]:
        clean = handle.strip().lstrip("@")
        plat = (platform or "tiktok").lower()
        target_url = url or (
            f"https://www.tiktok.com/@{clean}/live" if plat == "tiktok"
            else f"https://www.twitch.tv/{clean}" if plat == "twitch"
            else f"https://kick.com/{clean}" if plat == "kick"
            else f"https://www.youtube.com/@{clean}/live" if plat == "youtube"
            else clean
        )
        result: Dict[str, Any] = {
            "is_live": False,
            "uploader": clean,
            "platform": plat,
            "url": target_url,
            "title": "",
            "stream_url": "",
        }
        try:
            if plat == "tiktok":
                res = resolve_tiktok_live_fast(clean) or resolve_tiktok_live(clean, timeout=6)
                if res and res.is_live and res.formats:
                    result.update({
                        "is_live": True,
                        "title": res.title or f"@{clean} Live",
                        "stream_url": res.formats[0].url,
                        "uploader": res.uploader or clean,
                    })
            else:
                meta = resolve_stream_metadata(target_url, timeout=10)
                if meta and (meta.get("is_live") or meta.get("direct_url")) and meta.get("formats"):
                    result.update({
                        "is_live": True,
                        "title": meta.get("title") or f"{clean} Live",
                        "stream_url": meta.get("direct_url") or meta["formats"][0].get("url") or target_url,
                        "uploader": meta.get("uploader") or clean,
                    })
        except Exception:
            pass

        prev = self.get_cached_status(clean, plat)
        was_live = bool(prev.get("is_live", False))
        self.set_cached_status(clean, plat, result)

        if result["is_live"] and not was_live:
            cfg = get_config()
            if cfg.get("notifications", True):
                send_notification("StreamVortex Watchdog", f"{clean} ({plat}) is live: {result['title'][:60]}")
            DOWNLOAD_MANAGER.append_log("watchdog", f"[Watchdog] LIVE detected: {clean} ({plat}) — {result['title']}", level="success")

        if result["is_live"] and trigger_auto:
            key = self._item_key(clean, plat)
            with self._lock:
                existing_jid = self._active_auto_records.get(key)
                already_rec = False
                if existing_jid:
                    j = DOWNLOAD_MANAGER.get_job(existing_jid)
                    already_rec = bool(j and not j.get("completed"))
            if not already_rec:
                start_res = self._api.start_download({
                    "url": result["stream_url"] or target_url,
                    "title": result["title"] or f"{clean}_live",
                    "uploader": clean,
                    "is_live": True,
                    "quality": "max",
                    "container": "mp4",
                })
                if start_res and start_res.get("job_id"):
                    with self._lock:
                        self._active_auto_records[key] = start_res["job_id"]
                    DOWNLOAD_MANAGER.append_log("watchdog", f"[Watchdog] Auto-recording started for {clean} ({start_res['job_id']})", level="success")

        return result

    def _loop(self):
        while True:
            with self._lock:
                if not self._running:
                    break
            cfg = get_config()
            enabled = bool(cfg.get("watchdog_enabled", False))
            interval = max(20, int(cfg.get("watchdog_interval", 60)))
            global_auto = bool(cfg.get("watchdog_auto_record", False))

            if enabled:
                items = get_watchlist_items()
                for it in items:
                    with self._lock:
                        if not self._running:
                            return
                    if not get_config().get("watchdog_enabled", False):
                        break
                    should_auto = global_auto or bool(it.get("auto_record", False))
                    self.check_item(
                        it.get("handle", ""),
                        platform=it.get("platform", "tiktok"),
                        url=it.get("url"),
                        trigger_auto=should_auto,
                    )
                    time.sleep(1.5)
                with self._lock:
                    self._last_cycle_at = time.time()

            # Sleep in 2s slices so toggle/shutdown responds quickly
            slept = 0
            while slept < interval:
                with self._lock:
                    if not self._running:
                        return
                time.sleep(2)
                slept += 2
                if not enabled and get_config().get("watchdog_enabled", False):
                    break


# =============================================================================
# EMBEDDED MULTI-THREADED HTTP SERVER (UI, HLS PROXY, LOCAL MEDIA STREAMING)
# =============================================================================

class StreamVortexHttpHandler(BaseHTTPRequestHandler):
    """
    Multi-threaded local HTTP server for serving UI, static assets,
    proxying HLS streams (CORS bypass), and Range-streaming local media files.
    """
    server_version = "StreamVortexStudio/2.0"
    api = None

    def log_message(self, format, *args):
        pass

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Range, User-Agent, Referer")
        self.end_headers()

    def do_POST(self):
        parsed = urllib.parse.urlsplit(self.path)
        if parsed.path == "/api/call":
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length).decode("utf-8") if length > 0 else "{}"
            try:
                data = json.loads(body)
                method = data.get("method")
                args = data.get("args", [])
                api = getattr(StreamVortexHttpHandler, "api", None)
                if api and method and not method.startswith("_") and hasattr(api, method):
                    func = getattr(api, method)
                    result = func(*args)
                    resp_bytes = json.dumps(result, default=str).encode("utf-8")
                    self.send_response(200)
                    self.send_header("Content-Type", "application/json")
                    self.send_header("Access-Control-Allow-Origin", "*")
                    self.end_headers()
                    self.wfile.write(resp_bytes)
                    return
                else:
                    self.send_error(404, "Method not found")
                    return
            except Exception as e:
                err_bytes = json.dumps({"error": str(e)}).encode("utf-8")
                self.send_response(500)
                self.send_header("Content-Type", "application/json")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(err_bytes)
                return
        self.send_error(404, "Not Found")

    def _serve_local_media(self, raw_path: str):
        """Streams a local media file with HTTP 206 Range support for embedded player seeking."""
        try:
            p = Path(raw_path).resolve()
            if not p.exists() or not p.is_file():
                self.send_error(404, "Media file not found")
                return
            allowed_exts = {".mp4", ".m4v", ".mov", ".webm", ".mkv", ".mp3", ".m4a", ".aac", ".ogg", ".wav", ".flv", ".ts"}
            if p.suffix.lower() not in allowed_exts:
                self.send_error(403, "Unsupported media extension")
                return

            file_size = p.stat().st_size
            ctype, _ = mimetypes.guess_type(str(p))
            if not ctype:
                ctype = "video/mp4" if p.suffix.lower() in {".mp4", ".m4v", ".mov"} else "application/octet-stream"

            range_hdr = self.headers.get("Range")
            if range_hdr and range_hdr.startswith("bytes="):
                rng = range_hdr.replace("bytes=", "").split(",")[0].strip()
                start_s, end_s = rng.split("-", 1)
                start = int(start_s) if start_s else 0
                end = int(end_s) if end_s else file_size - 1
                end = min(end, file_size - 1)
                if start >= file_size or start > end:
                    self.send_response(416)
                    self.send_header("Content-Range", f"bytes */{file_size}")
                    self.end_headers()
                    return
                length = end - start + 1
                self.send_response(206)
                self.send_header("Content-Type", ctype)
                self.send_header("Content-Range", f"bytes {start}-{end}/{file_size}")
                self.send_header("Content-Length", str(length))
                self.send_header("Accept-Ranges", "bytes")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                with open(p, "rb") as f:
                    f.seek(start)
                    remaining = length
                    while remaining > 0:
                        chunk = f.read(min(1024 * 256, remaining))
                        if not chunk:
                            break
                        self.wfile.write(chunk)
                        remaining -= len(chunk)
            else:
                self.send_response(200)
                self.send_header("Content-Type", ctype)
                self.send_header("Content-Length", str(file_size))
                self.send_header("Accept-Ranges", "bytes")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                with open(p, "rb") as f:
                    shutil.copyfileobj(f, self.wfile, length=1024 * 256)
        except (BrokenPipeError, ConnectionResetError):
            pass
        except Exception as e:
            try:
                self.send_error(500, f"Media stream error: {e}")
            except Exception:
                pass

    def do_GET(self):
        parsed = urllib.parse.urlsplit(self.path)

        # 1. Favicon / Icon
        if parsed.path in ["/icon.png", "/favicon.ico"]:
            ico = get_asset_path("icon.png") or get_asset_path("icon_64.png")
            if ico and ico.exists():
                self.send_response(200)
                self.send_header("Content-Type", "image/png")
                self.send_header("Cache-Control", "public, max-age=86400")
                self.end_headers()
                self.wfile.write(ico.read_bytes())
                return

        # 2. Local Media Player Streaming (HTTP 206 Range Support)
        if parsed.path == "/api/media":
            query = urllib.parse.parse_qs(parsed.query)
            file_path = query.get("path", [None])[0]
            if not file_path:
                self.send_error(400, "Missing path parameter")
                return
            self._serve_local_media(file_path)
            return

        # 3. HLS Manifest Proxy (Rewrites URLs and injects CORS headers)
        if parsed.path == "/api/proxy_hls":
            query = urllib.parse.parse_qs(parsed.query)
            target_url = query.get("url", [None])[0]
            if not target_url:
                self.send_error(400, "Missing url parameter")
                return

            try:
                parsed_t = urllib.parse.urlsplit(target_url)
                headers = {
                    "User-Agent": DEFAULT_USER_AGENT,
                    "Referer": f"{parsed_t.scheme}://{parsed_t.netloc}/",
                    "Origin": f"{parsed_t.scheme}://{parsed_t.netloc}"
                }
                custom_hdr_raw = query.get("headers", [None])[0]
                if custom_hdr_raw:
                    try:
                        headers.update(json.loads(custom_hdr_raw))
                    except Exception:
                        pass

                req = urllib.request.Request(target_url, headers=headers)
                with urllib.request.urlopen(req, timeout=10) as resp:
                    raw_content = resp.read().decode('utf-8', errors='ignore')

                hdr_q = f"&headers={urllib.parse.quote(custom_hdr_raw)}" if custom_hdr_raw else ""
                rewritten_lines = []
                for line in raw_content.splitlines():
                    sline = line.strip()
                    if sline.startswith('#') and 'URI="' in sline:
                        def _rewrite_uri(match):
                            u = urllib.parse.urljoin(target_url, match.group(1))
                            ep = "/api/proxy_hls" if (".m3u8" in u or "pull-hls" in u) else "/api/proxy_chunk"
                            return f'URI="{ep}?url={urllib.parse.quote(u, safe="")}{hdr_q}"'
                        rewritten_lines.append(re.sub(r'URI="([^"]+)"', _rewrite_uri, line))
                    elif sline and not sline.startswith('#'):
                        abs_url = urllib.parse.urljoin(target_url, sline)
                        if '.m3u8' in abs_url or 'pull-hls' in abs_url:
                            rewritten_lines.append(f"/api/proxy_hls?url={urllib.parse.quote(abs_url, safe='')}{hdr_q}")
                        else:
                            rewritten_lines.append(f"/api/proxy_chunk?url={urllib.parse.quote(abs_url, safe='')}{hdr_q}")
                    else:
                        rewritten_lines.append(line)

                body = "\n".join(rewritten_lines).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "application/vnd.apple.mpegurl")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.send_header("Cache-Control", "no-cache, no-store")
                self.end_headers()
                self.wfile.write(body)
            except Exception as e:
                self.send_error(502, f"HLS Proxy Error: {e}")
            return

        # 4. Media Chunk / Direct Stream Proxy (Supports Range & CORS)
        if parsed.path == "/api/proxy_chunk":
            query = urllib.parse.parse_qs(parsed.query)
            target_url = query.get("url", [None])[0]
            if not target_url:
                self.send_error(400, "Missing url parameter")
                return

            try:
                parsed_t = urllib.parse.urlsplit(target_url)
                headers = {
                    "User-Agent": DEFAULT_USER_AGENT,
                    "Referer": f"{parsed_t.scheme}://{parsed_t.netloc}/",
                }
                custom_hdr_raw = query.get("headers", [None])[0]
                if custom_hdr_raw:
                    try:
                        headers.update(json.loads(custom_hdr_raw))
                    except Exception:
                        pass
                if self.headers.get("Range"):
                    headers["Range"] = self.headers["Range"]

                req = urllib.request.Request(target_url, headers=headers)
                with urllib.request.urlopen(req, timeout=15) as resp:
                    c_type = resp.headers.get("Content-Type", "video/MP2T")
                    status = getattr(resp, "status", 200)
                    self.send_response(status)
                    self.send_header("Content-Type", c_type)
                    if resp.headers.get("Content-Length"):
                        self.send_header("Content-Length", resp.headers["Content-Length"])
                    if resp.headers.get("Content-Range"):
                        self.send_header("Content-Range", resp.headers["Content-Range"])
                    self.send_header("Accept-Ranges", "bytes")
                    self.send_header("Access-Control-Allow-Origin", "*")
                    self.end_headers()
                    shutil.copyfileobj(resp, self.wfile)
            except (BrokenPipeError, ConnectionResetError):
                pass
            except Exception as e:
                try:
                    self.send_error(502, f"Chunk Proxy Error: {e}")
                except Exception:
                    pass
            return

        # 5. Main Application HTML
        if parsed.path in ["/", "/index.html"]:
            html_content = generate_studio_html()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Cache-Control", "no-cache")
            self.end_headers()
            self.wfile.write(html_content.encode("utf-8"))
            return

        self.send_error(404, "Not Found")


# =============================================================================
# NATIVE PYTHON <-> JAVASCRIPT BIDIRECTIONAL API BRIDGE
# =============================================================================

class StreamVortexApi:
    """
    Exposed directly to window.pywebview.api in JavaScript (and /api/call HTTP fallback).
    """

    def __init__(self, port: Optional[int]):
        self.port = port
        self._window = None
        self._last_clipboard_url: str = ""
        self.watchdog = WatchdogService(self)

    def set_window(self, window):
        self._window = window

    def get_initial_state(self) -> Dict[str, Any]:
        """Provides all configuration, health, jobs, watchlist, and telemetry on initialization."""
        conf = find_ytdlp_conf()
        conf_name = conf.name if conf else "Default"
        dl_dir = str(get_conf_download_dir(conf))
        ytdlp_cmd = find_ytdlp()
        ytdlp_str = " ".join(ytdlp_cmd) if isinstance(ytdlp_cmd, list) else str(ytdlp_cmd)
        ffmpeg_bin = find_ffmpeg()
        ffprobe_bin = find_ffprobe()
        has_space, free_gb = check_free_disk_space()

        return {
            "config": get_config(),
            "download_dir": dl_dir,
            "active_conf": conf_name,
            "conf_path": str(conf) if conf else "",
            "ytdlp_path": ytdlp_str,
            "ytdlp_ready": bool(ytdlp_cmd),
            "ffmpeg_path": ffmpeg_bin or "Missing",
            "ffmpeg_ready": bool(ffmpeg_bin),
            "ffprobe_ready": bool(ffprobe_bin),
            "free_disk_gb": round(free_gb, 1),
            "has_disk_space": has_space,
            "history": get_history(),
            "watchlist": get_watchlist(),
            "watchdog": self.watchdog.get_snapshot(),
            "active_jobs": DOWNLOAD_MANAGER.get_serializable_jobs(),
            "telemetry": DOWNLOAD_MANAGER.get_telemetry_snapshot(),
            "console_logs": DOWNLOAD_MANAGER.get_console_logs(120),
            "server_port": self.port,
        }

    def resolve_url(self, url: str) -> Dict[str, Any]:
        """
        Analyzes a URL using multi-tier resolvers.
        Discovers playlists, titles, thumbnails, platform metadata, and multi-bitrate formats.
        """
        clean_url = clean_target_url(url.strip())
        if not clean_url:
            return {"error": "Please enter a valid URL."}

        DOWNLOAD_MANAGER.append_log("sniffer", f"[Sniffer] Analyzing target: {clean_url}")
        try:
            # 1. Universal resolver (TikTok, HLS, yt-dlp, playlists)
            meta = resolve_stream_metadata(clean_url, timeout=14)
            if meta and meta.get("is_playlist") and meta.get("playlist_entries"):
                DOWNLOAD_MANAGER.append_log("sniffer", f"[Sniffer] Playlist detected: {meta.get('title')} ({meta.get('playlist_count')} items)", level="success")
                return meta

            if meta and meta.get("formats"):
                direct_url = meta.get("direct_url") or meta["formats"][0].get("url")
                hdrs = meta.get("http_headers") or {}
                hdr_q = f"&headers={urllib.parse.quote(json.dumps(hdrs))}" if hdrs else ""
                if direct_url and (".m3u8" in direct_url or "pull-hls" in direct_url):
                    meta["preview_url"] = f"/api/proxy_hls?url={urllib.parse.quote(direct_url, safe='')}{hdr_q}"
                elif direct_url and self.port:
                    meta["preview_url"] = direct_url
                else:
                    meta["preview_url"] = direct_url
                DOWNLOAD_MANAGER.append_log("sniffer", f"[Sniffer] Resolved: {meta.get('title')} ({len(meta.get('formats', []))} formats)", level="success")
                return meta

            # 2. Fallback to universal smart sniffer
            sniffed = smart_sniff(clean_url, timeout=12)
            if sniffed and sniffed.url:
                is_hls = sniffed.stream_type == "hls"
                hdr_q = f"&headers={urllib.parse.quote(json.dumps(sniffed.headers))}" if sniffed.headers else ""
                preview_url = f"/api/proxy_hls?url={urllib.parse.quote(sniffed.url, safe='')}{hdr_q}" if is_hls else sniffed.url
                DOWNLOAD_MANAGER.append_log("sniffer", f"[Sniffer] Intercepted {sniffed.stream_type.upper()} stream", level="success")
                return {
                    "id": clean_url,
                    "title": sniffed.page_title or "Discovered Web Stream",
                    "uploader": "",
                    "is_live": sniffed.stream_type in ("hls", "flv"),
                    "is_playlist": False,
                    "platform": detect_platform(clean_url),
                    "original_url": clean_url,
                    "direct_url": sniffed.url,
                    "http_headers": sniffed.headers or {},
                    "preview_url": preview_url,
                    "formats": [
                        {
                            "id": f"{sniffed.stream_type}-main",
                            "url": sniffed.url,
                            "protocol": "m3u8_native" if is_hls else "https",
                            "ext": "mp4" if is_hls else sniffed.stream_type,
                        }
                    ],
                }

            DOWNLOAD_MANAGER.append_log("sniffer", f"[Sniffer] No active stream found for {clean_url}", level="warn")
            return {"error": "No media stream detected on page or channel is currently offline."}
        except Exception as e:
            DOWNLOAD_MANAGER.append_log("sniffer", f"[Sniffer Error] {e}", level="error")
            return {"error": str(e)}

    def start_download(self, options: Dict[str, Any]) -> Dict[str, Any]:
        """Starts a download job in the background with full studio options and tracks it in DOWNLOAD_MANAGER."""
        url = (options.get("url") or "").strip()
        if not url:
            return {"error": "No URL provided"}

        title = options.get("title") or ""
        uploader = options.get("uploader") or ""
        is_live = bool(options.get("is_live", False))
        quality = options.get("quality", "max")
        audio_only = bool(options.get("audio_only", False)) or str(quality).startswith("audio_")
        container = (options.get("container") or "mp4").strip().lower()
        custom_folder = (options.get("folder") or "").strip()
        subtitles = options.get("subtitles")
        embed_metadata = options.get("embed_metadata")
        embed_thumbnail = options.get("embed_thumbnail")
        sponsorblock = options.get("sponsorblock")
        clip_start = (options.get("clip_start") or "").strip() or None
        clip_end = (options.get("clip_end") or "").strip() or None
        cookies_from_browser = options.get("cookies_from_browser")
        rate_limit = options.get("rate_limit")
        format_id = options.get("format_id")
        proxy = options.get("proxy")
        platform_name = (options.get("platform") or detect_platform(url).get("name", "Stream"))

        job_id = f"job-{int(time.time() * 1000)}"
        DOWNLOAD_MANAGER.start_job(
            job_id,
            title or url,
            url,
            is_live=is_live,
            options=dict(options),
            platform=platform_name,
            container=container,
        )
        DOWNLOAD_MANAGER.append_log(job_id, f"[Queue] Starting job {job_id}: {title or url}")

        # Determine whether custom_folder differs from conf download dir
        conf = find_ytdlp_conf()
        conf_dir = str(get_conf_download_dir(conf))
        use_custom_out = bool(custom_folder and Path(custom_folder).resolve() != Path(conf_dir).resolve())
        out_file = None
        if use_custom_out:
            ext_final = "m4a" if quality == "audio_m4a" else ("mp3" if audio_only else "%(ext)s")
            if title:
                from .engine import sanitize_title_for_filename
                out_file = str(Path(custom_folder) / sanitize_title_for_filename(title, uploader=uploader, ext=container if not audio_only else ext_final))
            else:
                out_file = str(Path(custom_folder) / f"%(title).90B [%(id)s].{ext_final}")

        def _worker():
            try:
                run_ytdlp_download(
                    stream_url=url,
                    audio_only=audio_only,
                    is_live=is_live,
                    quality_preference=quality,
                    title=title or None,
                    uploader=uploader or None,
                    job_id=job_id,
                    respect_conf_output=not use_custom_out,
                    output_filename=out_file,
                    container=container,
                    subtitles=subtitles,
                    embed_metadata=embed_metadata,
                    embed_thumbnail=embed_thumbnail,
                    sponsorblock=sponsorblock,
                    clip_start=clip_start,
                    clip_end=clip_end,
                    cookies_from_browser=cookies_from_browser,
                    rate_limit=rate_limit,
                    format_id=format_id,
                    proxy=proxy,
                )
            except Exception as e:
                DOWNLOAD_MANAGER.append_log(job_id, f"[Worker Error] {e}", level="error")
                DOWNLOAD_MANAGER.finish_job(job_id, success=False, error=str(e))

        threading.Thread(target=_worker, daemon=True).start()
        return {"status": "started", "job_id": job_id}

    def retry_job(self, job_id: str) -> Dict[str, Any]:
        """Retries a completed/failed/stopped job using its original options."""
        job = DOWNLOAD_MANAGER.get_job(job_id)
        if not job:
            return {"error": "Job not found"}
        opts = dict(job.get("options") or {})
        if not opts.get("url"):
            opts["url"] = job.get("url", "")
            opts["title"] = job.get("title", "")
            opts["is_live"] = bool(job.get("is_live", False))
        return self.start_download(opts)

    def batch_download(self, options: Dict[str, Any]) -> Dict[str, Any]:
        """Queues multiple URLs with configurable parallel concurrency (1-4 workers)."""
        raw_urls = options.get("urls", [])
        quality = options.get("quality", "max")
        container = options.get("container", "mp4")
        audio_only = bool(options.get("audio_only", False)) or str(quality).startswith("audio_")
        subtitles = options.get("subtitles")
        embed_metadata = options.get("embed_metadata")
        embed_thumbnail = options.get("embed_thumbnail")
        cfg = get_config()
        concurrency = max(1, min(4, int(options.get("concurrency") or cfg.get("max_concurrent_downloads", 2))))

        valid_urls = [clean_target_url(u) for u in raw_urls if isinstance(u, str) and u.strip()]
        valid_urls = [u for u in valid_urls if u.startswith(("http://", "https://"))]
        if not valid_urls:
            return {"error": "No valid HTTP(S) URLs provided"}

        DOWNLOAD_MANAGER.append_log("batch", f"[Batch] Queuing {len(valid_urls)} URL(s) with {concurrency} parallel worker(s)")

        def _process_one(idx: int, u: str):
            try:
                meta = resolve_stream_metadata(u, timeout=10)
                title = meta.get("title") if meta and meta.get("title") != "stream_media" else None
                uploader = meta.get("uploader") if meta else None
                is_live = bool(meta.get("is_live", False)) if meta else False
                plat = (meta.get("platform") or {}).get("name", "Batch") if meta else "Batch"
                job_id = f"batch-{int(time.time() * 1000)}-{idx}"
                job_opts = {
                    "url": u,
                    "title": title or u,
                    "uploader": uploader or "",
                    "is_live": is_live,
                    "quality": quality,
                    "audio_only": audio_only,
                    "container": container,
                    "subtitles": subtitles,
                    "embed_metadata": embed_metadata,
                    "embed_thumbnail": embed_thumbnail,
                }
                DOWNLOAD_MANAGER.start_job(job_id, title or u, u, is_live=is_live, options=job_opts, platform=plat, container=container)
                run_ytdlp_download(
                    stream_url=u,
                    audio_only=audio_only,
                    is_live=is_live,
                    quality_preference=quality,
                    title=title,
                    uploader=uploader,
                    job_id=job_id,
                    container=container,
                    subtitles=subtitles,
                    embed_metadata=embed_metadata,
                    embed_thumbnail=embed_thumbnail,
                )
            except Exception as e:
                DOWNLOAD_MANAGER.append_log("batch", f"[Batch Error] {u}: {e}", level="error")

        def _batch_coordinator():
            with ThreadPoolExecutor(max_workers=concurrency) as pool:
                for idx, u in enumerate(valid_urls):
                    pool.submit(_process_one, idx, u)

        threading.Thread(target=_batch_coordinator, daemon=True).start()
        return {"status": "queued", "count": len(valid_urls), "concurrency": concurrency}

    def get_active_jobs(self) -> List[Dict[str, Any]]:
        """Returns JSON-safe list of running and recent download tasks."""
        return DOWNLOAD_MANAGER.get_serializable_jobs()

    def get_telemetry(self) -> Dict[str, Any]:
        """Returns live throughput oscilloscope points and aggregate stats."""
        return DOWNLOAD_MANAGER.get_telemetry_snapshot()

    def get_console_logs(self, limit: int = 200) -> List[Dict[str, Any]]:
        """Returns live engine console log entries."""
        return DOWNLOAD_MANAGER.get_console_logs(limit=limit)

    def clear_console_logs(self) -> Dict[str, Any]:
        DOWNLOAD_MANAGER.clear_console_logs()
        return {"status": "cleared"}

    def clear_completed_jobs(self) -> Dict[str, Any]:
        """Clears completed or failed jobs from the active queue."""
        DOWNLOAD_MANAGER.clear_completed()
        return {"status": "cleared", "active_jobs": DOWNLOAD_MANAGER.get_serializable_jobs()}

    def stop_job(self, job_id: str) -> Dict[str, Any]:
        """Gracefully stops a live recording and finalizes its container."""
        DOWNLOAD_MANAGER.append_log(job_id, f"[Queue] Stopping and finalizing {job_id}...", level="warn")
        success = DOWNLOAD_MANAGER.stop_job(job_id)
        job = DOWNLOAD_MANAGER.get_serializable_job(job_id)
        return {
            "status": "stopped" if success else "not_found",
            "saved_path": job.get("saved_path") if job else None,
            "title": job.get("title") if job else None,
        }

    def get_job_status(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Returns JSON-safe live details for a specific job."""
        return DOWNLOAD_MANAGER.get_serializable_job(job_id)

    def select_folder(self) -> Dict[str, Any]:
        """Opens native Windows folder picker dialog and updates yt-dlp.conf."""
        if self._window:
            result = self._window.create_file_dialog(webview.FOLDER_DIALOG)
            if result and len(result) > 0:
                picked = result[0]
                conf = find_ytdlp_conf()
                if conf:
                    update_ytdlp_conf_destinations(Path(picked), conf_path=conf)
                else:
                    cfg = get_config()
                    cfg["download_dir"] = picked
                    save_config(cfg)
                return {"folder": picked}
        return {"cancelled": True}

    def pick_any_folder(self) -> Dict[str, Any]:
        """Opens native folder dialog without modifying global download destination (for folder repair scan)."""
        if self._window:
            result = self._window.create_file_dialog(webview.FOLDER_DIALOG)
            if result and len(result) > 0:
                return {"folder": result[0]}
        return {"cancelled": True}

    def select_file(self, file_types: Optional[List[str]] = None) -> Dict[str, Any]:
        """Opens native Windows file picker dialog."""
        if self._window:
            types = tuple(file_types) if file_types else ('Video & Media Files (*.mp4;*.ts;*.flv;*.mkv;*.webm;*.part;*.m4v;*.mov)', 'All Files (*.*)')
            result = self._window.create_file_dialog(webview.OPEN_DIALOG, file_types=types)
            if result and len(result) > 0:
                return {"file": result[0]}
        return {"cancelled": True}

    def select_batch_file(self) -> Dict[str, Any]:
        """Opens native file dialog to load a .txt batch URL list."""
        if self._window:
            result = self._window.create_file_dialog(webview.OPEN_DIALOG, file_types=('Text Files (*.txt;*.list)', 'All Files (*.*)'))
            if result and len(result) > 0:
                try:
                    content = Path(result[0]).read_text(encoding="utf-8", errors="ignore")
                    return {"file": result[0], "content": content}
                except Exception as e:
                    return {"error": str(e)}
        return {"cancelled": True}

    def open_folder(self, folder_path: Optional[str] = None) -> Dict[str, Any]:
        """Opens target folder (or reveals target file) in Windows Explorer."""
        target = Path(folder_path) if folder_path else get_conf_download_dir()
        if target.exists():
            if target.is_file():
                return self.reveal_in_explorer(str(target))
            if sys.platform == "win32":
                os.startfile(str(target))
            else:
                subprocess.run(["xdg-open", str(target)])
            return {"status": "opened", "path": str(target)}
        return {"error": "Folder does not exist"}

    def reveal_in_explorer(self, file_path: str) -> Dict[str, Any]:
        """Highlights a specific file in Windows Explorer (or opens parent directory on Unix)."""
        p = Path(file_path)
        if not p.exists():
            if p.parent.exists():
                return self.open_folder(str(p.parent))
            return {"error": "File does not exist"}
        if sys.platform == "win32":
            subprocess.Popen(["explorer", f"/select,{str(p.resolve())}"])
        elif sys.platform == "darwin":
            subprocess.Popen(["open", "-R", str(p.resolve())])
        else:
            subprocess.Popen(["xdg-open", str(p.parent.resolve())])
        return {"status": "revealed", "path": str(p)}

    def open_file(self, file_path: str) -> Dict[str, Any]:
        """Opens media file in default system player."""
        p = Path(file_path)
        if p.exists():
            if sys.platform == "win32":
                os.startfile(str(p))
            else:
                subprocess.run(["xdg-open", str(p)])
            return {"status": "opened"}
        return {"error": "File does not exist"}

    def delete_media_file(self, file_path: str, timestamp: Optional[float] = None) -> Dict[str, Any]:
        """Deletes a media file from disk (if present) and removes it from history."""
        deleted_disk = False
        if file_path:
            p = Path(file_path)
            if p.exists() and p.is_file():
                try:
                    p.unlink()
                    deleted_disk = True
                except Exception as e:
                    return {"error": f"Could not delete file: {e}"}
        remove_history_entry(filename=file_path, timestamp=timestamp)
        return {"status": "deleted", "deleted_disk": deleted_disk}

    def play_in_external_player(self, target_url: str) -> Dict[str, Any]:
        """Plays stream or media file in MPV or VLC."""
        ok, desc = play_media_target(target_url)
        return {"success": ok, "message": desc}

    def get_history(self) -> List[Dict[str, Any]]:
        """Returns enriched media history with live file existence and size."""
        items = get_history()
        enriched = []
        for h in items:
            row = dict(h)
            fn = row.get("filename") or ""
            exists = False
            size_mb = None
            ext = ""
            if fn and not fn.startswith("Configured in"):
                p = Path(fn)
                if p.exists() and p.is_file():
                    exists = True
                    size_mb = round(p.stat().st_size / (1024 * 1024), 2)
                    ext = p.suffix.lstrip(".").upper()
                elif row.get("size_bytes"):
                    size_mb = round(float(row["size_bytes"]) / (1024 * 1024), 2)
            row["exists"] = exists
            row["size_mb"] = size_mb
            row["ext"] = ext
            row["media_url"] = f"/api/media?path={urllib.parse.quote(fn, safe='')}" if exists else ""
            enriched.append(row)
        return enriched

    def scan_downloads_folder(self) -> List[Dict[str, Any]]:
        """Scans the active download directory for local media files."""
        dl_dir = get_conf_download_dir()
        if not dl_dir.exists():
            return []
        media_exts = {".mp4", ".mkv", ".webm", ".mov", ".m4v", ".ts", ".flv", ".mp3", ".m4a", ".aac", ".wav"}
        audio_exts = {".mp3", ".m4a", ".aac", ".wav"}
        files = []
        try:
            for p in dl_dir.rglob("*"):
                if p.is_file() and p.suffix.lower() in media_exts:
                    try:
                        st = p.stat()
                        if st.st_size == 0:
                            continue
                        mt = "audio" if p.suffix.lower() in audio_exts else "video"
                        files.append({
                            "title": p.stem,
                            "filename": str(p),
                            "ext": p.suffix.lstrip(".").upper(),
                            "type": mt,
                            "media_type": mt,
                            "size_mb": round(st.st_size / (1024 * 1024), 2),
                            "timestamp": st.st_mtime,
                            "date_str": time.strftime("%Y-%m-%d %H:%M", time.localtime(st.st_mtime)),
                            "exists": True,
                            "media_url": f"/api/media?path={urllib.parse.quote(str(p), safe='')}",
                        })
                    except Exception:
                        continue
        except Exception:
            pass
        files.sort(key=lambda x: x["timestamp"], reverse=True)
        return files[:200]

    def clear_history(self) -> Dict[str, Any]:
        clear_history()
        return {"status": "cleared"}

    # ---- Watchdog API ----

    def get_watchlist(self) -> List[str]:
        return get_watchlist()

    def get_watchdog_state(self) -> Dict[str, Any]:
        return self.watchdog.get_snapshot()

    def set_watchdog_config(self, enabled: bool, interval: int = 60, global_auto_record: bool = False) -> Dict[str, Any]:
        cfg = get_config()
        cfg["watchdog_enabled"] = bool(enabled)
        cfg["watchdog_interval"] = max(20, min(600, int(interval)))
        cfg["watchdog_auto_record"] = bool(global_auto_record)
        save_config(cfg)
        if enabled:
            self.watchdog.start()
        return self.watchdog.get_snapshot()

    def add_to_watchlist(self, creator: str, platform: Optional[str] = None, auto_record: bool = False) -> Dict[str, Any]:
        if creator and creator.strip():
            add_to_watchlist(creator.strip(), platform=platform, auto_record=auto_record)
        return {"watchlist": get_watchlist(), "watchdog": self.watchdog.get_snapshot()}

    def toggle_watchdog_auto_record(self, creator: str, enabled: bool, platform: Optional[str] = None) -> Dict[str, Any]:
        update_watchlist_item(creator, auto_record=enabled, platform=platform)
        return self.watchdog.get_snapshot()

    def remove_from_watchlist(self, creator: str, platform: Optional[str] = None) -> Dict[str, Any]:
        if creator and creator.strip():
            remove_from_watchlist(creator.strip(), platform=platform)
        return {"watchlist": get_watchlist(), "watchdog": self.watchdog.get_snapshot()}

    def check_creator_live(self, creator: str, platform: str = "tiktok", url: Optional[str] = None) -> Dict[str, Any]:
        return self.watchdog.check_item(creator, platform=platform, url=url, trigger_auto=False)

    def check_all_watchdog(self) -> Dict[str, Any]:
        items = get_watchlist_items()
        results = []
        for it in items:
            results.append(self.watchdog.check_item(it.get("handle", ""), platform=it.get("platform", "tiktok"), url=it.get("url"), trigger_auto=False))
        return {"results": results, "watchdog": self.watchdog.get_snapshot()}

    # ---- Container Repair & Deep Inspection API ----

    def inspect_container(self, file_path: str) -> Dict[str, Any]:
        """Inspects magic bytes AND ffprobe stream metadata of a media file."""
        p = Path(file_path.strip().strip('"\''))
        if not p.exists():
            return {"error": "File does not exist"}
        have = sniff_container(p)
        ext = p.suffix.lstrip(".").lower()
        size_mb = round(p.stat().st_size / (1024 * 1024), 2)
        is_flv = (have == "flv" or ext == "flv")
        is_part = (ext == "part")
        is_ts_mismatch = (have == "mpegts" and ext != "ts")
        is_mismatched = is_flv or is_part or is_ts_mismatch or (
            have and ext not in (have, "part") and not (ext == "mp4" and have == "mp4")
        )

        detected_str = have or "Unknown"
        if is_flv:
            detected_str = f"{have or 'flv'} (FLV Video)"

        probe = probe_media_details(p)

        return {
            "path": str(p),
            "filename": p.name,
            "size_mb": size_mb,
            "size_formatted": f"{size_mb} MB",
            "extension": ext,
            "detected_container": detected_str,
            "is_mismatched": bool(is_mismatched),
            "status_label": (
                "LEGACY FLV (REPAIR TO PLAYABLE MP4/MKV)" if is_flv
                else ("CONTAINER MISMATCH (REPAIR NEEDED)" if is_mismatched else "CONTAINER CLEAN")
            ),
            "media_url": f"/api/media?path={urllib.parse.quote(str(p), safe='')}",
            "probe": probe,
        }

    inspect_file_container = inspect_container

    def scan_repair_folder(self, folder_path: Optional[str] = None) -> Dict[str, Any]:
        target = Path(folder_path) if folder_path else get_conf_download_dir()
        if not target.exists():
            return {"error": "Folder does not exist"}
        items = scan_folder_for_repairs(target)
        return {
            "folder": str(target),
            "total": len(items),
            "mismatched_count": sum(1 for i in items if i["is_mismatched"]),
            "items": items,
        }

    def repair_container(self, file_path: str, target_format: str = "mp4") -> Dict[str, Any]:
        """Losslessly remuxes broken/mismatched video into clean MP4/MKV or extracts audio MP3/M4A."""
        try:
            p = Path(file_path.strip().strip('"\''))
            if not p.exists():
                return {"error": f"File does not exist: {file_path}"}
            fmt = (target_format or "mp4").lower().strip()
            DOWNLOAD_MANAGER.append_log("repair", f"[Repair] Processing {p.name} -> {fmt.upper()}")
            if fmt in ("mp3", "m4a"):
                fixed = extract_audio_from_file(p, audio_format=fmt, on_output=lambda l: DOWNLOAD_MANAGER.append_log("repair", l))
            else:
                fixed = fixup_recorded_file(p, on_output=lambda l: DOWNLOAD_MANAGER.append_log("repair", l), preferred_container=fmt)
            if not fixed or not fixed.exists():
                return {"error": "Remuxing failed (FFmpeg returned an error or target file could not be created)"}
            DOWNLOAD_MANAGER.append_log("repair", f"[Repair] Complete: {fixed.name}", level="success")
            return {
                "status": "repaired",
                "original_path": str(p),
                "repaired_path": str(fixed),
                "repaired_name": fixed.name,
            }
        except Exception as e:
            DOWNLOAD_MANAGER.append_log("repair", f"[Repair Error] {e}", level="error")
            return {"error": f"Container repair failed: {str(e)}"}

    # ---- Settings, Config Editor & Inline Diagnostics ----

    def get_system_health(self) -> Dict[str, Any]:
        """Runs diagnostics check for yt-dlp, FFmpeg, FFprobe, Python, player, and storage."""
        health = check_environment_status()
        has_space, free_gb = check_free_disk_space()
        health["disk_free_gb"] = round(free_gb, 1)
        health["has_disk_space"] = has_space
        return health

    def run_inline_diagnostics(self) -> Dict[str, Any]:
        """Returns structured diagnostic rows for inline display inside Settings."""
        health = self.get_system_health()
        rows = [
            {
                "component": "Python Runtime",
                "status": "pass" if health["python"]["ok"] else "warn",
                "detail": f"v{health['python']['version']} ({health['python']['path']})",
            },
            {
                "component": "yt-dlp Engine",
                "status": "pass" if health["ytdlp"]["ok"] else "fail",
                "detail": f"v{health['ytdlp']['version']} ({health['ytdlp']['path'] or 'Not found'})",
            },
            {
                "component": "FFmpeg Muxer",
                "status": "pass" if health["ffmpeg"]["ok"] else "warn",
                "detail": (health["ffmpeg"]["version"][:64] if health["ffmpeg"]["ok"] else "Not found — install via Setup Wizard"),
            },
            {
                "component": "FFprobe Inspector",
                "status": "pass" if health["ffprobe"]["ok"] else "warn",
                "detail": health["ffprobe"]["path"] or "Not found (needed for codec inspection)",
            },
            {
                "component": "yt-dlp Config",
                "status": "pass" if health["conf"]["ok"] else "warn",
                "detail": health["conf"]["path"] or "Using built-in defaults",
            },
            {
                "component": "External Player",
                "status": "pass" if health["player"]["ok"] else "info",
                "detail": f"{health['player']['name']} ({health['player']['path']})" if health["player"]["ok"] else "Optional (MPV / VLC not found)",
            },
            {
                "component": "Storage Headroom",
                "status": "pass" if health["has_disk_space"] else "warn",
                "detail": f"{health['disk_free_gb']} GB available on target drive",
            },
        ]
        # Playwright check (fast filesystem check)
        appdata_local = os.environ.get("LOCALAPPDATA", "")
        ms_pw = Path(appdata_local) / "ms-playwright" if appdata_local else None
        pw_ready = bool(ms_pw and ms_pw.exists() and any(ms_pw.glob("chromium*")))
        rows.append({
            "component": "Playwright Chromium",
            "status": "pass" if pw_ready else "info",
            "detail": "Headless browser sniffer ready" if pw_ready else "Optional (for dynamic WAF/JS stream sniffing)",
        })
        return {"rows": rows, "health": health}

    def get_ytdlp_conf(self) -> Dict[str, Any]:
        conf = find_ytdlp_conf()
        if conf and conf.exists():
            try:
                return {"path": str(conf), "content": conf.read_text(encoding="utf-8", errors="ignore")}
            except Exception as e:
                return {"error": str(e)}
        return {"path": "", "content": DEFAULT_YTDLP_CONF_TEMPLATE}

    def save_ytdlp_conf(self, content: str) -> Dict[str, Any]:
        conf = find_ytdlp_conf()
        if not conf:
            conf = deploy_embedded_ytdlp_conf()
        if not conf:
            return {"error": "Could not locate or create yt-dlp.conf"}
        try:
            conf.write_text(content, encoding="utf-8")
            DOWNLOAD_MANAGER.append_log("system", f"[Config] Saved yt-dlp.conf ({conf})", level="success")
            return {"status": "saved", "path": str(conf), "download_dir": str(get_conf_download_dir(conf))}
        except Exception as e:
            return {"error": str(e)}

    def save_studio_settings(self, settings: Dict[str, Any]) -> Dict[str, Any]:
        cfg = get_config()
        allowed_keys = {
            "max_concurrent_downloads",
            "cookies_from_browser",
            "rate_limit",
            "proxy",
            "clipboard_watch",
            "auto_remux",
            "sponsorblock",
            "subtitles",
            "embed_metadata",
            "embed_thumbnail",
            "notifications",
            "default_quality",
            "default_container",
            "watchdog_enabled",
            "watchdog_interval",
            "watchdog_auto_record",
        }
        for k, v in settings.items():
            if k in allowed_keys:
                cfg[k] = v
        save_config(cfg)
        if cfg.get("watchdog_enabled"):
            self.watchdog.start()
        return {"status": "saved", "config": get_config()}

    def update_ytdlp_binary(self) -> Dict[str, Any]:
        """Updates yt-dlp via `-U` (or pip if running as python module)."""
        ytdlp_cmd = find_ytdlp()
        DOWNLOAD_MANAGER.append_log("system", "[Update] Checking for yt-dlp updates...")
        try:
            if "-m" in ytdlp_cmd:
                cmd = [ytdlp_cmd[0], "-m", "pip", "install", "-U", "yt-dlp"]
            else:
                cmd = list(ytdlp_cmd) + ["-U"]
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=60, encoding="utf-8", errors="replace")
            out = (res.stdout + "\n" + res.stderr).strip()
            for line in out.splitlines()[-6:]:
                DOWNLOAD_MANAGER.append_log("system", f"[Update] {line}")
            return {"ok": res.returncode == 0, "output": out[-500:]}
        except Exception as e:
            return {"ok": False, "output": str(e)}

    def open_conf_folder(self) -> Dict[str, Any]:
        conf = find_ytdlp_conf()
        if conf and conf.exists():
            return self.reveal_in_explorer(str(conf))
        return self.open_folder(str(Path.home()))

    def run_1click_setup(self) -> Dict[str, Any]:
        threading.Thread(target=launch_onboarding_gui, daemon=True).start()
        return {"status": "launched"}

    def run_doctor(self) -> Dict[str, Any]:
        threading.Thread(target=run_doctor, daemon=True).start()
        return {"status": "launched"}

    def copy_to_clipboard(self, text: str) -> Dict[str, Any]:
        from .recorder import copy_to_clipboard
        copy_to_clipboard(text)
        return {"status": "copied"}

    def get_clipboard_text(self) -> Dict[str, Any]:
        try:
            import pyperclip
            return {"text": pyperclip.paste()}
        except Exception:
            return {"text": ""}

    def check_clipboard_url(self) -> Dict[str, Any]:
        """Checks clipboard for a newly copied supported stream/video URL."""
        try:
            import pyperclip
            raw = (pyperclip.paste() or "").strip()
            if not raw or "\n" in raw or len(raw) > 800:
                return {"found": False}
            if not raw.startswith(("http://", "https://")):
                return {"found": False}
            if raw == self._last_clipboard_url:
                return {"found": False}
            plat = detect_platform(raw)
            supported_ids = {
                "tiktok", "youtube", "twitch", "kick", "twitter", "instagram",
                "facebook", "reddit", "rumble", "vimeo", "bilibili", "dailymotion",
                "hls", "dash", "livefeed", "directmedia"
            }
            if plat.get("id") in supported_ids:
                self._last_clipboard_url = raw
                return {"found": True, "url": clean_target_url(raw), "platform": plat}
        except Exception:
            pass
        return {"found": False}


# =============================================================================
# STUDIO HTML TEMPLATE IMPORT
# =============================================================================

from .studio_ui import generate_studio_html


# =============================================================================
# MAIN DESKTOP GUI LAUNCHER (PyWebView Engine)
# =============================================================================

def launch_desktop_gui():
    """
    Main entry point for StreamVortex Desktop Studio.
    Launches PyWebView with Edge WebView2 on Windows, backed by a multi-threaded local server.
    """
    port = find_free_port(8765)
    server = ReusableThreadingHTTPServer(('127.0.0.1', port), StreamVortexHttpHandler)
    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()

    api = StreamVortexApi(port=port)
    StreamVortexHttpHandler.api = api
    if get_config().get("watchdog_enabled", False):
        api.watchdog.start()

    ico_path = get_asset_path("StreamVortex.ico") or get_asset_path("icon.ico")
    icon_str = str(ico_path) if ico_path else None

    if HAS_WEBVIEW:
        window = webview.create_window(
            title="StreamVortex Studio",
            url=f"http://127.0.0.1:{port}/",
            js_api=api,
            width=1360,
            height=860,
            min_size=(1024, 680),
            background_color="#0d0e11",
            text_select=True
        )
        api.set_window(window)
        webview.start(icon=icon_str, debug=False)
    else:
        import webbrowser
        webbrowser.open(f"http://127.0.0.1:{port}/")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            pass


if __name__ == "__main__":
    launch_desktop_gui()
