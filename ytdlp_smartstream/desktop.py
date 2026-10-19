"""
StreamVortex Modern Desktop Studio (PyWebView Native Engine).
Universal yt-dlp & Live Stream Suite with:
- Embedded HLS.js live video player for real-time stream preview
- Native PyWebView bridge with two-way JS <-> Python API
- Left sidebar navigation (Studio & Player, Library/History, Batch Downloader, Watchdog, Container Repair, Settings)
- Native Windows Folder and File Dialog integration
- Real-time download queue with live progress, speed, ETA, and cancellation
- Live Creator Watchdog with auto-record support
- Lossless container repair and MPEG-TS / FLV / .part recovery
- yt-dlp.conf bidirectional synchronization
"""

import sys
import os
import re
import time
import json
import shutil
import socket
import urllib.parse
import urllib.request
import threading
import subprocess
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler
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
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("streamvortex.studio.app.v1.3")
    except Exception:
        pass

try:
    import webview
    HAS_WEBVIEW = True
except ImportError:
    HAS_WEBVIEW = False

from .config import (
    get_download_dir, get_config, save_config,
    get_history, add_history_entry,
    get_watchlist, add_to_watchlist, remove_from_watchlist
)
from .engine import (
    find_ytdlp, find_ffmpeg, find_ffprobe, find_player, find_ytdlp_conf,
    get_conf_download_dir, update_ytdlp_conf_destinations, build_format_args,
    resolve_stream_metadata, run_ytdlp_download, check_free_disk_space,
    detect_platform, play_media_target, clean_target_url,
    sniff_container, fixup_recorded_file, DOWNLOAD_MANAGER
)
from .sniffer import smart_sniff, DEFAULT_USER_AGENT
from .tiktok_resolver import resolve_tiktok_live_fast, resolve_tiktok_live, resolve_tiktok_video
from .onboarding import check_environment_status, launch_onboarding_gui
from .doctor import run_doctor


def get_asset_path(filename: str) -> Optional[Path]:
    """Finds an asset file across workspace and frozen bundles."""
    candidates = [
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


# =============================================================================
# EMBEDDED LOCAL SERVER FOR ASSETS, HLS PROXY & STREAM PREVIEW
# =============================================================================

class StreamVortexHttpHandler(BaseHTTPRequestHandler):
    """
    Local lightweight HTTP server for serving UI, static assets, and proxying HLS streams
    to bypass cross-origin / header restrictions in the embedded video player.
    """
    server_version = "StreamVortexStudio/1.3"
    api = None

    def log_message(self, format, *args):
        # Suppress routine HTTP log spam in console
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
                if api and hasattr(api, method):
                    func = getattr(api, method)
                    result = func(*args)
                    resp_bytes = json.dumps(result).encode("utf-8")
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
                self.send_error(500, str(e))
                return
        self.send_error(404, "Not Found")

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

        # 2. HLS Manifest Proxy (Rewrites URLs and injects CORS headers for seamless live playback)
        if parsed.path == "/api/proxy_hls":
            query = urllib.parse.parse_qs(parsed.query)
            target_url = query.get("url", [None])[0]
            if not target_url:
                self.send_error(400, "Missing url parameter")
                return

            try:
                headers = {
                    "User-Agent": DEFAULT_USER_AGENT,
                    "Referer": target_url,
                    "Origin": f"{urllib.parse.urlsplit(target_url).scheme}://{urllib.parse.urlsplit(target_url).netloc}"
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

                # Rewrite child variant and chunk links through our local proxy
                rewritten_lines = []
                for line in raw_content.splitlines():
                    sline = line.strip()
                    if sline and not sline.startswith('#'):
                        abs_url = urllib.parse.urljoin(target_url, sline)
                        if '.m3u8' in abs_url or 'pull-hls' in abs_url:
                            rewritten_lines.append(f"/api/proxy_hls?url={urllib.parse.quote(abs_url)}")
                        else:
                            rewritten_lines.append(f"/api/proxy_chunk?url={urllib.parse.quote(abs_url)}")
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

        # 3. Media Chunk Proxy (Streams video chunks with CORS headers)
        if parsed.path == "/api/proxy_chunk":
            query = urllib.parse.parse_qs(parsed.query)
            target_url = query.get("url", [None])[0]
            if not target_url:
                self.send_error(400, "Missing url parameter")
                return

            try:
                req = urllib.request.Request(target_url, headers={"User-Agent": DEFAULT_USER_AGENT, "Referer": target_url})
                with urllib.request.urlopen(req, timeout=15) as resp:
                    c_type = resp.headers.get("Content-Type", "video/MP2T")
                    self.send_response(200)
                    self.send_header("Content-Type", c_type)
                    self.send_header("Access-Control-Allow-Origin", "*")
                    self.end_headers()
                    shutil.copyfileobj(resp, self.wfile)
            except Exception as e:
                self.send_error(502, f"Chunk Proxy Error: {e}")
            return

        # 4. Main Application HTML
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
    Exposed directly to window.pywebview.api in JavaScript.
    Handles all interactions: URL resolution, file dialogs, downloads, batch queues,
    container repairs, history, watchlist, and settings.
    """
    def __init__(self, port: int):
        self.port = port
        self._window = None

    def set_window(self, window):
        self._window = window

    def get_initial_state(self) -> Dict[str, Any]:
        """Provides all configuration and system info on app initialization."""
        conf = find_ytdlp_conf()
        conf_name = conf.name if conf else "Default"
        dl_dir = str(get_conf_download_dir(conf))
        ytdlp_cmd = find_ytdlp()
        ytdlp_str = " ".join(ytdlp_cmd) if isinstance(ytdlp_cmd, list) else str(ytdlp_cmd)
        ffmpeg_bin = find_ffmpeg()
        has_space, free_gb = check_free_disk_space()

        return {
            "config": get_config(),
            "download_dir": dl_dir,
            "active_conf": conf_name,
            "ytdlp_path": ytdlp_str,
            "ffmpeg_path": ffmpeg_bin or "Missing",
            "ffmpeg_ready": bool(ffmpeg_bin),
            "free_disk_gb": round(free_gb, 1),
            "has_disk_space": has_space,
            "history": get_history(),
            "watchlist": get_watchlist(),
            "active_jobs": DOWNLOAD_MANAGER.get_active_jobs(),
            "server_port": self.port
        }

    def resolve_url(self, url: str) -> Dict[str, Any]:
        """
        Analyzes a URL using multi-tier resolvers.
        Discovers titles, platform metadata, and multi-bitrate formats.
        """
        clean_url = clean_target_url(url.strip())
        if not clean_url:
            return {"error": "Please enter a valid URL."}

        try:
            # 1. Resolve with universal engine
            meta = resolve_stream_metadata(clean_url, timeout=12)
            if meta and meta.get("formats"):
                direct_url = meta.get("direct_url") or meta["formats"][0].get("url")
                # Attach CORS proxy URL for live HLS streams so player never fails
                if direct_url and (".m3u8" in direct_url or "pull-hls" in direct_url):
                    meta["preview_url"] = f"http://127.0.0.1:{self.port}/api/proxy_hls?url={urllib.parse.quote(direct_url)}"
                else:
                    meta["preview_url"] = direct_url
                return meta

            # 2. Fallback to smart sniffer
            sniffed = smart_sniff(clean_url, timeout=12)
            if sniffed and sniffed.url:
                is_hls = sniffed.stream_type == "hls"
                preview_url = f"http://127.0.0.1:{self.port}/api/proxy_hls?url={urllib.parse.quote(sniffed.url)}" if is_hls else sniffed.url
                return {
                    "id": clean_url,
                    "title": sniffed.page_title or "Discovered Web Stream",
                    "uploader": "",
                    "is_live": sniffed.stream_type in ("hls", "flv"),
                    "platform": detect_platform(clean_url),
                    "direct_url": sniffed.url,
                    "preview_url": preview_url,
                    "formats": [
                        {
                            "id": f"{sniffed.stream_type}-main",
                            "url": sniffed.url,
                            "protocol": "m3u8_native" if is_hls else "https",
                            "ext": "mp4" if is_hls else sniffed.stream_type
                        }
                    ]
                }

            return {"error": "No media stream detected on page or channel is offline."}
        except Exception as e:
            return {"error": str(e)}

    def start_download(self, options: Dict[str, Any]) -> Dict[str, Any]:
        """Starts a download job in the background and tracks it in DOWNLOAD_MANAGER."""
        url = options.get("url", "").strip()
        if not url:
            return {"error": "No URL provided"}

        title = options.get("title") or "stream"
        uploader = options.get("uploader") or ""
        is_live = bool(options.get("is_live", False))
        quality = options.get("quality", "max")
        audio_only = bool(options.get("audio_only", False)) or quality.startswith("audio_")
        container = options.get("container", "mp4")
        custom_folder = options.get("folder")

        job_id = f"job-{int(time.time() * 1000)}"
        DOWNLOAD_MANAGER.start_job(job_id, title, url, is_live=is_live)

        def _worker():
            try:
                run_ytdlp_download(
                    stream_url=url,
                    audio_only=audio_only,
                    is_live=is_live,
                    quality_preference=quality,
                    title=title,
                    uploader=uploader,
                    job_id=job_id,
                    respect_conf_output=True if not custom_folder else False,
                    output_filename=None if not custom_folder else str(Path(custom_folder) / f"{title}.{container}")
                )
            except Exception as e:
                DOWNLOAD_MANAGER.finish_job(job_id, success=False, error=str(e))

        t = threading.Thread(target=_worker, daemon=True)
        t.start()
        return {"status": "started", "job_id": job_id}

    def batch_download(self, options: Dict[str, Any]) -> Dict[str, Any]:
        """Queues multiple URLs for sequential download."""
        urls = options.get("urls", [])
        quality = options.get("quality", "max")
        audio_only = bool(options.get("audio_only", False)) or quality.startswith("audio_")

        valid_urls = [u.strip() for u in urls if u.strip().startswith("http")]
        if not valid_urls:
            return {"error": "No valid URLs provided"}

        def _batch_worker():
            for u in valid_urls:
                try:
                    meta = resolve_stream_metadata(u, timeout=8)
                    title = meta.get("title") if meta else None
                    uploader = meta.get("uploader") if meta else None
                    is_live = meta.get("is_live", False) if meta else False
                    job_id = f"batch-{int(time.time() * 1000)}"
                    DOWNLOAD_MANAGER.start_job(job_id, title or u, u, is_live=is_live)
                    run_ytdlp_download(
                        stream_url=u,
                        audio_only=audio_only,
                        is_live=is_live,
                        quality_preference=quality,
                        title=title,
                        uploader=uploader,
                        job_id=job_id
                    )
                except Exception:
                    pass

        threading.Thread(target=_batch_worker, daemon=True).start()
        return {"status": "queued", "count": len(valid_urls)}

    def get_active_jobs(self) -> List[Dict[str, Any]]:
        """Returns the list of running and recent download tasks."""
        return DOWNLOAD_MANAGER.get_active_jobs()

    def clear_completed_jobs(self) -> Dict[str, Any]:
        """Clears completed or failed jobs from the active queue."""
        DOWNLOAD_MANAGER.clear_completed()
        return {"status": "cleared", "active_jobs": DOWNLOAD_MANAGER.get_active_jobs()}

    def stop_job(self, job_id: str) -> Dict[str, Any]:
        """Gracefully stops a live recording and finalizes its container."""
        success = DOWNLOAD_MANAGER.stop_job(job_id)
        job = DOWNLOAD_MANAGER.get_job(job_id)
        return {
            "status": "stopped" if success else "not_found",
            "saved_path": job.get("saved_path") if job else None,
            "title": job.get("title") if job else None
        }

    def get_job_status(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Returns live details for a specific job."""
        return DOWNLOAD_MANAGER.get_job(job_id)

    def select_folder(self) -> Dict[str, Any]:
        """Opens native Windows folder picker dialog and updates yt-dlp.conf."""
        if self._window:
            result = self._window.create_file_dialog(webview.FOLDER_DIALOG)
            if result and len(result) > 0:
                picked = result[0]
                # Sync with yt-dlp.conf
                conf = find_ytdlp_conf()
                if conf:
                    update_ytdlp_conf_destinations(Path(picked), conf_path=conf)
                return {"folder": picked}
        return {"cancelled": True}

    def select_file(self, file_types: Optional[List[str]] = None) -> Dict[str, Any]:
        """Opens native Windows file picker dialog."""
        if self._window:
            types = tuple(file_types) if file_types else ('Video Files (*.mp4;*.ts;*.flv;*.mkv;*.part)', 'All Files (*.*)')
            result = self._window.create_file_dialog(webview.OPEN_DIALOG, file_types=types)
            if result and len(result) > 0:
                return {"file": result[0]}
        return {"cancelled": True}

    def open_folder(self, folder_path: Optional[str] = None) -> Dict[str, Any]:
        """Opens target folder in Windows Explorer."""
        target = Path(folder_path) if folder_path else get_conf_download_dir()
        if target.exists():
            if sys.platform == "win32":
                os.startfile(str(target))
            else:
                subprocess.run(["xdg-open", str(target)])
            return {"status": "opened", "path": str(target)}
        return {"error": "Folder does not exist"}

    def open_file(self, file_path: str) -> Dict[str, Any]:
        """Opens media file in default system player or highlights it in Explorer."""
        p = Path(file_path)
        if p.exists():
            if sys.platform == "win32":
                os.startfile(str(p))
            else:
                subprocess.run(["xdg-open", str(p)])
            return {"status": "opened"}
        return {"error": "File does not exist"}

    def play_in_external_player(self, target_url: str) -> Dict[str, Any]:
        """Plays stream or media file in MPV or VLC."""
        ok, desc = play_media_target(target_url)
        return {"success": ok, "message": desc}

    def get_history(self) -> List[Dict[str, Any]]:
        """Returns downloaded media history."""
        return get_history()

    def clear_history(self) -> Dict[str, Any]:
        """Clears media history."""
        save_config("history", [])
        return {"status": "cleared"}

    def get_watchlist(self) -> List[str]:
        """Returns monitored creator watchlist."""
        return get_watchlist()

    def add_to_watchlist(self, creator: str) -> Dict[str, Any]:
        """Adds a creator to the live watchdog."""
        c = creator.strip().lstrip("@")
        if c:
            add_to_watchlist(c)
        return {"watchlist": get_watchlist()}

    def remove_from_watchlist(self, creator: str) -> Dict[str, Any]:
        """Removes a creator from the watchlist."""
        c = creator.strip().lstrip("@")
        if c:
            remove_from_watchlist(c)
        return {"watchlist": get_watchlist()}

    def check_creator_live(self, creator: str) -> Dict[str, Any]:
        """Checks if a creator is currently live."""
        c = creator.strip().lstrip("@")
        res = resolve_tiktok_live_fast(c) or resolve_tiktok_live(c, timeout=6)
        if res and res.is_live and res.formats:
            return {
                "is_live": True,
                "title": res.title,
                "stream_url": res.formats[0].url,
                "uploader": res.uploader
            }
        return {"is_live": False, "uploader": c}

    def inspect_container(self, file_path: str) -> Dict[str, Any]:
        """Inspects magic bytes of a media file to detect actual container."""
        p = Path(file_path.strip().strip('"\''))
        if not p.exists():
            return {"error": "File does not exist"}
        have = sniff_container(p)
        ext = p.suffix.lstrip(".").lower()
        size_mb = round(p.stat().st_size / (1024 * 1024), 2)
        is_flv = (have == "flv" or ext == "flv")
        is_part = (ext == "part")
        is_ts_mismatch = (have == "mpegts" and ext != "ts")
        is_mismatched = is_flv or is_part or is_ts_mismatch or (have and ext not in (have, "part") and not (ext == "mp4" and have == "mp4"))

        detected_str = have or "Unknown"
        if is_flv:
            detected_str = f"{have or 'flv'} (FLV Video)"

        return {
            "path": str(p),
            "filename": p.name,
            "size_mb": size_mb,
            "extension": ext,
            "detected_container": detected_str,
            "is_mismatched": bool(is_mismatched),
            "status_label": "LEGACY FLV (REPAIR TO PLAYABLE MP4/MKV)" if is_flv else ("CONTAINER MISMATCH (REPAIR NEEDED)" if is_mismatched else "CONTAINER CLEAN")
        }

    def repair_container(self, file_path: str) -> Dict[str, Any]:
        """Losslessly remuxes broken/mismatched video into clean MP4 with faststart."""
        p = Path(file_path.strip().strip('"\''))
        if not p.exists():
            return {"error": "File does not exist"}
        fixed = fixup_recorded_file(p)
        return {
            "status": "repaired",
            "original_path": str(p),
            "repaired_path": str(fixed),
            "repaired_name": fixed.name
        }

    def get_system_health(self) -> Dict[str, Any]:
        """Runs diagnostics check for yt-dlp, FFmpeg, Python, and storage."""
        health = check_environment_status()
        has_space, free_gb = check_free_disk_space()
        health["disk_free_gb"] = round(free_gb, 1)
        health["has_disk_space"] = has_space
        return health

    def check_all_watchdog(self) -> List[Dict[str, Any]]:
        """Checks live status for all creators in the watchlist."""
        results = []
        for creator in get_watchlist():
            try:
                res = self.check_creator_live(creator)
                results.append(res)
            except Exception:
                results.append({"is_live": False, "uploader": creator})
        return results

    def open_conf_folder(self) -> Dict[str, Any]:
        """Opens directory containing yt-dlp.conf."""
        conf = find_ytdlp_conf()
        if conf and conf.exists():
            return self.open_folder(str(conf.parent))
        return self.open_folder(str(Path.home()))

    def run_1click_setup(self) -> Dict[str, Any]:
        """Launches automated tool installation wizard."""
        threading.Thread(target=launch_onboarding_gui, daemon=True).start()
        return {"status": "launched"}

    def run_doctor(self) -> Dict[str, Any]:
        """Runs system doctor."""
        threading.Thread(target=run_doctor, daemon=True).start()
        return {"status": "launched"}

    def copy_to_clipboard(self, text: str) -> Dict[str, Any]:
        """Copies string to clipboard."""
        from .recorder import copy_to_clipboard
        copy_to_clipboard(text)
        return {"status": "copied"}

    def get_clipboard_text(self) -> Dict[str, Any]:
        """Reads current clipboard text."""
        try:
            import pyperclip
            return {"text": pyperclip.paste()}
        except Exception:
            return {"text": ""}


# =============================================================================
# MODERN MULTI-PANEL 3-WINDOW HTML / CSS / JS APPLICATION TEMPLATE (2026 PRO)
# =============================================================================

from .studio_ui import generate_studio_html


# =============================================================================
# MAIN DESKTOP GUI LAUNCHER (PyWebView Engine)
# =============================================================================

def launch_desktop_gui():
    """
    Main entry point for StreamVortex Desktop Studio.
    Launches PyWebView with Edge WebView2 on Windows, backed by local server.
    """
    port = find_free_port(8765)
    server = HTTPServer(('127.0.0.1', port), StreamVortexHttpHandler)
    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()

    api = StreamVortexApi(port=port)
    StreamVortexHttpHandler.api = api

    # Icon candidate resolution
    ico_path = get_asset_path("StreamVortex.ico") or get_asset_path("icon.ico")
    icon_str = str(ico_path) if ico_path else None

    if HAS_WEBVIEW:
        window = webview.create_window(
            title="StreamVortex Studio — Universal yt-dlp & Live Suite v1.3",
            url=f"http://127.0.0.1:{port}/",
            js_api=api,
            width=1240,
            height=820,
            min_size=(980, 640),
            background_color="#080b11",
            text_select=True
        )
        api.set_window(window)

        # Launch PyWebView desktop application
        webview.start(icon=icon_str, debug=False)
    else:
        # Fallback to browser UI if webview module is absent
        import webbrowser
        webbrowser.open(f"http://127.0.0.1:{port}/")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            pass


if __name__ == "__main__":
    launch_desktop_gui()
