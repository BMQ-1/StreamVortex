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
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("streamvortex.studio.app.v1.2")
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
    server_version = "StreamVortexStudio/1.2"

    def log_message(self, format, *args):
        # Suppress routine HTTP log spam in console
        pass

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Range, User-Agent, Referer")
        self.end_headers()

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
        return {"status": "stopped" if success else "not_found"}

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
        return check_environment_status()

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
# MODERN OBSIDIAN HTML / CSS / JS APPLICATION TEMPLATE
# =============================================================================

def generate_studio_html() -> str:
    conf = find_ytdlp_conf()
    conf_name = conf.name if conf else "Default"
    conf_dir = str(get_conf_download_dir(conf))

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>StreamVortex Studio — Universal yt-dlp &amp; Live Suite v1.2</title>
  <link rel="icon" type="image/png" href="/icon.png">
  <script src="https://cdn.jsdelivr.net/npm/hls.js@1.5.8/dist/hls.min.js"></script>
  <script src="https://cdn.tailwindcss.com"></script>
  <link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600;700&family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap" rel="stylesheet">
  <style>
    body {{
      background: #080b11;
      background-image: 
        radial-gradient(circle at 10% 10%, rgba(0, 242, 254, 0.07) 0%, transparent 45%),
        radial-gradient(circle at 90% 90%, rgba(79, 172, 254, 0.05) 0%, transparent 45%);
      color: #f1f5f9;
      font-family: 'Plus Jakarta Sans', sans-serif;
      overflow-x: hidden;
      user-select: none;
    }}
    .mono {{ font-family: 'JetBrains Mono', monospace; }}
    .glass {{
      background: rgba(15, 21, 35, 0.7);
      backdrop-filter: blur(20px);
      border: 1px solid rgba(255, 255, 255, 0.07);
    }}
    .glass-input {{
      background: rgba(10, 14, 24, 0.85);
      border: 1px solid rgba(255, 255, 255, 0.1);
    }}
    .glass-input:focus {{
      border-color: #00f2fe;
      box-shadow: 0 0 0 3px rgba(0, 242, 254, 0.2);
    }}
    .btn-gradient {{
      background: linear-gradient(135deg, #00f2fe 0%, #4facfe 100%);
      color: #040813;
      font-weight: 700;
      transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
    }}
    .btn-gradient:hover {{
      transform: translateY(-1px);
      box-shadow: 0 8px 25px -4px rgba(0, 242, 254, 0.4);
    }}
    .live-dot::before {{
      content: '';
      display: inline-block;
      width: 8px;
      height: 8px;
      border-radius: 50%;
      background: #ff2a5f;
      margin-right: 6px;
      box-shadow: 0 0 10px #ff2a5f;
      animation: pulse 1.5s infinite;
    }}
    @keyframes pulse {{
      0% {{ opacity: 1; transform: scale(1); }}
      50% {{ opacity: 0.35; transform: scale(0.8); }}
      100% {{ opacity: 1; transform: scale(1); }}
    }}
    ::-webkit-scrollbar {{ width: 6px; height: 6px; }}
    ::-webkit-scrollbar-track {{ background: rgba(0, 0, 0, 0.2); }}
    ::-webkit-scrollbar-thumb {{ background: rgba(255, 255, 255, 0.15); border-radius: 3px; }}
    ::-webkit-scrollbar-thumb:hover {{ background: rgba(0, 242, 254, 0.4); }}
  </style>
</head>
<body class="min-h-screen flex flex-col">

  <!-- Header -->
  <header class="glass sticky top-0 z-50 px-6 py-3.5 border-b border-white/5 flex items-center justify-between">
    <div class="flex items-center gap-3">
      <div class="w-10 h-10 rounded-xl bg-gradient-to-tr from-cyan-400 to-blue-500 flex items-center justify-center text-slate-950 font-black text-xl shadow-lg shadow-cyan-500/20">
        ⚡
      </div>
      <div>
        <div class="flex items-center gap-2">
          <h1 class="text-xl font-extrabold tracking-tight bg-gradient-to-r from-cyan-400 via-sky-300 to-blue-400 bg-clip-text text-transparent">
            StreamVortex
          </h1>
          <span class="text-[9px] uppercase font-bold tracking-wider px-2 py-0.5 rounded-full bg-cyan-500/10 text-cyan-400 border border-cyan-500/20 mono">
            STUDIO v1.2
          </span>
          <span class="text-[9px] uppercase font-bold tracking-wider px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 mono">
            Config: {conf_name}
          </span>
          <button onclick="pyCall('open_folder')" class="text-[9px] font-bold tracking-wider px-2.5 py-0.5 rounded-full bg-slate-800/80 text-slate-300 hover:text-white border border-white/10 mono cursor-pointer flex items-center gap-1" title="Click to open active downloads folder">
            📂 <span id="hdrDlDir" class="truncate max-w-[200px]">{conf_dir}</span>
          </button>
        </div>
        <p class="text-[11px] text-slate-400 mono">Universal Live &amp; VOD Stream Intelligence // Powered by yt-dlp</p>
      </div>
    </div>

    <!-- Center Navigation Tabs -->
    <div class="flex items-center gap-1 bg-slate-900/80 p-1 rounded-xl border border-white/5">
      <button onclick="switchTab('studio')" id="tabBtn-studio" class="tab-btn px-3.5 py-1.5 rounded-lg text-xs font-semibold transition-all bg-cyan-400 text-slate-950">
        ⚡ Studio &amp; Player
      </button>
      <button onclick="switchTab('library')" id="tabBtn-library" class="tab-btn px-3.5 py-1.5 rounded-lg text-xs font-semibold transition-all text-slate-300 hover:text-white">
        📁 Library
      </button>
      <button onclick="switchTab('batch')" id="tabBtn-batch" class="tab-btn px-3.5 py-1.5 rounded-lg text-xs font-semibold transition-all text-slate-300 hover:text-white">
        📦 Batch
      </button>
      <button onclick="switchTab('watchdog')" id="tabBtn-watchdog" class="tab-btn px-3.5 py-1.5 rounded-lg text-xs font-semibold transition-all text-slate-300 hover:text-white">
        🔴 Watchdog
      </button>
      <button onclick="switchTab('repair')" id="tabBtn-repair" class="tab-btn px-3.5 py-1.5 rounded-lg text-xs font-semibold transition-all text-slate-300 hover:text-white">
        🛠️ Fix Containers
      </button>
      <button onclick="switchTab('settings')" id="tabBtn-settings" class="tab-btn px-3.5 py-1.5 rounded-lg text-xs font-semibold transition-all text-slate-300 hover:text-white">
        ⚙️ Settings
      </button>
    </div>

    <!-- Header Actions -->
    <div class="flex items-center gap-2">
      <button onclick="pyCall('run_1click_setup')" class="px-3 py-1.5 rounded-lg glass text-xs font-semibold text-amber-300 hover:text-white hover:border-amber-400/50 flex items-center gap-1 transition-all cursor-pointer">
        ⚡ Setup Wizard
      </button>
      <button onclick="pyCall('open_folder')" class="px-3 py-1.5 rounded-lg glass text-xs font-semibold text-slate-300 hover:text-white hover:border-cyan-400/50 flex items-center gap-1 transition-all cursor-pointer">
        📂 Explorer
      </button>
    </div>
  </header>

  <!-- Main Viewport -->
  <main class="flex-1 max-w-6xl w-full mx-auto p-6 flex flex-col gap-6">

    <!-- Active Downloads Live Monitoring Strip (Always visible when downloads active) -->
    <div id="activeDownloadsContainer" class="hidden flex flex-col gap-3 glass rounded-2xl p-5 border border-cyan-500/30 shadow-2xl">
      <div class="flex items-center justify-between text-xs font-bold uppercase tracking-wider text-cyan-400">
        <span class="flex items-center gap-2">
          <span class="w-2.5 h-2.5 rounded-full bg-cyan-400 animate-pulse"></span>
          Active Downloads Queue &amp; Recordings
        </span>
        <div class="flex items-center gap-2">
          <span id="activeCount" class="mono text-slate-400 text-[11px]">0 active</span>
          <button onclick="onClearCompletedClick()" class="glass hover:bg-white/10 text-slate-300 hover:text-white px-2.5 py-0.5 rounded text-[10px] mono cursor-pointer">
            🧹 Clear Completed
          </button>
        </div>
      </div>
      <div id="activeJobsList" class="flex flex-col gap-2.5"></div>
    </div>

    <!-- ================================================================= -->
    <!-- TAB 1: STUDIO & LIVE PLAYER (Primary Downloader)                  -->
    <!-- ================================================================= -->
    <div id="tab-studio" class="tab-content flex flex-col gap-5">
      
      <!-- URL Bar Card -->
      <div class="glass rounded-2xl p-5 shadow-2xl flex flex-col gap-3.5">
        <div class="flex items-center justify-between">
          <label class="text-xs font-bold uppercase tracking-wider text-slate-300 flex items-center gap-2">
            <span>Video, Stream, or Playlist URL</span>
          </label>
          <span class="text-xs text-cyan-400 mono">tiktok live • youtube • twitch • kick • hls (.m3u8)</span>
        </div>

        <div class="flex flex-col sm:flex-row gap-2.5">
          <div class="relative flex-1">
            <input 
              type="text" 
              id="streamUrlInput" 
              placeholder="Paste any stream or video URL (e.g. TikTok Live, YouTube, Twitch, Kick, or .m3u8)..." 
              class="w-full glass-input rounded-xl px-4 py-3 text-sm mono text-white outline-none pr-10"
              onkeydown="if(event.key === 'Enter') onAnalyzeClick()"
            />
          </div>
          <button onclick="onPasteClick()" class="glass hover:border-cyan-400 px-4 py-3 rounded-xl text-xs font-bold text-slate-300 hover:text-white flex items-center justify-center gap-1.5 transition-all cursor-pointer">
            📋 Paste
          </button>
          <button onclick="onAnalyzeClick()" id="analyzeBtn" class="btn-gradient px-6 py-3 rounded-xl text-sm font-bold flex items-center justify-center gap-2 cursor-pointer whitespace-nowrap">
            <span>⚡ Analyze</span>
          </button>
        </div>

        <!-- Quick Platform Preset Pills -->
        <div class="flex items-center gap-1.5 flex-wrap pt-0.5 text-xs">
          <span class="text-slate-400 mono text-[11px]">Presets:</span>
          <button onclick="setPreset('https://www.tiktok.com/@weathernewslive/live')" class="px-2.5 py-1 rounded-lg glass text-slate-300 hover:text-white hover:border-pink-500/50 transition-all cursor-pointer">🎵 TikTok Live</button>
          <button onclick="setPreset('https://www.youtube.com/watch?v=dQw4w9WgXcQ')" class="px-2.5 py-1 rounded-lg glass text-slate-300 hover:text-white hover:border-red-500/50 transition-all cursor-pointer">▶️ YouTube</button>
          <button onclick="setPreset('https://www.twitch.tv/')" class="px-2.5 py-1 rounded-lg glass text-slate-300 hover:text-white hover:border-purple-500/50 transition-all cursor-pointer">🟣 Twitch</button>
          <button onclick="setPreset('https://kick.com/')" class="px-2.5 py-1 rounded-lg glass text-slate-300 hover:text-white hover:border-green-500/50 transition-all cursor-pointer">🟢 Kick</button>
          <button onclick="setPreset('https://test-streams.mux.dev/x36xhzz/x36xhzz.m3u8')" class="px-2.5 py-1 rounded-lg glass text-slate-300 hover:text-white hover:border-cyan-500/50 transition-all cursor-pointer">⚡ Demo M3U8</button>
        </div>

        <div id="loader" class="hidden py-3 text-center mono text-xs text-cyan-400 animate-pulse flex items-center justify-center gap-2">
          <svg class="animate-spin h-4 w-4 text-cyan-400" viewBox="0 0 24 24" fill="none"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z"></path></svg>
          <span>Resolving multi-bitrate streams &amp; inspecting manifests...</span>
        </div>
      </div>

      <!-- Live Player & Stream Preview Section (Appears when analyzed) -->
      <div id="playerSection" class="hidden flex flex-col gap-5">
        
        <div class="glass rounded-2xl p-5 shadow-2xl flex flex-col gap-4 border border-cyan-500/20">
          <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-white/5">
            <div>
              <div class="flex items-center gap-2 mb-1 flex-wrap">
                <span id="platformBadge" class="text-[11px] px-2.5 py-0.5 rounded-full font-bold mono bg-cyan-500/15 text-cyan-300 border border-cyan-500/30">
                  ⚡ Universal
                </span>
                <span id="liveStatusBadge" class="live-dot bg-red-500/15 border border-red-500/30 text-red-400 text-[11px] px-2.5 py-0.5 rounded-full font-bold mono">
                  LIVE STREAM
                </span>
                <span id="uploaderBadge" class="text-xs font-semibold text-cyan-400 mono">@creator</span>
              </div>
              <h2 id="streamTitle" class="text-lg font-bold tracking-tight text-white">Stream Title</h2>
            </div>
            
            <div class="flex items-center gap-2 flex-wrap">
              <button onclick="startDownloadCurrent('video')" class="btn-gradient px-4 py-2 rounded-xl text-xs font-bold flex items-center gap-1.5 cursor-pointer">
                ⬇️ Download Best
              </button>
              <button onclick="startDownloadCurrent('audio')" class="glass hover:border-cyan-400 px-3.5 py-2 rounded-xl text-xs font-bold text-white flex items-center gap-1.5 transition-all cursor-pointer">
                🎵 Audio (MP3)
              </button>
              <button onclick="copyStreamUrl()" class="glass hover:border-cyan-400 px-3 py-2 rounded-xl text-xs font-bold text-slate-300 hover:text-white flex items-center gap-1.5 transition-all cursor-pointer">
                📋 Copy M3U8
              </button>
              <button onclick="playInExternalPlayer()" class="glass hover:border-cyan-400 px-3 py-2 rounded-xl text-xs font-bold text-cyan-300 hover:text-white flex items-center gap-1.5 transition-all cursor-pointer">
                ▶ VLC/MPV
              </button>
            </div>
          </div>

          <!-- Embedded Live Player -->
          <div class="relative w-full aspect-video rounded-xl overflow-hidden bg-black border border-white/10 shadow-2xl">
            <video id="hlsVideo" controls autoplay muted class="w-full h-full object-contain"></video>
          </div>

          <!-- Multi-Bitrate Formats Grid -->
          <div>
            <h3 class="text-xs font-bold uppercase tracking-wider text-slate-400 mb-2 flex items-center justify-between">
              <span>Discovered Multi-Bitrate Formats</span>
              <span class="text-[11px] text-slate-500 font-normal">Click any format to preview in player</span>
            </h3>
            <div id="formatsList" class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2.5"></div>
          </div>
        </div>

      </div>

      <!-- Format Options & Destination Panel -->
      <div class="glass rounded-2xl p-5 shadow-2xl flex flex-col gap-4">
        <h3 class="text-xs font-bold uppercase tracking-wider text-slate-300">Format &amp; Output Configuration</h3>

        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
          <!-- Quality Profile -->
          <div class="flex flex-col gap-1.5">
            <label class="text-xs text-slate-400">Quality Preset</label>
            <select id="qualitySelect" class="glass-input rounded-xl px-3 py-2.5 text-xs mono text-cyan-300 outline-none cursor-pointer">
              <option value="max">🎬 Best Quality (Video + Audio)</option>
              <option value="1080p">📱 1080p MP4 (High Definition)</option>
              <option value="720p">⚡ 720p Fast (Standard HD)</option>
              <option value="480p">💾 480p Data Saver</option>
              <option value="conf">⚙️ Respect yt-dlp.conf</option>
              <option value="audio_mp3">🎵 MP3 (320k Lossless Audio)</option>
              <option value="audio_m4a">🎧 M4A (AAC Audio)</option>
            </select>
          </div>

          <!-- Container Format -->
          <div class="flex flex-col gap-1.5">
            <label class="text-xs text-slate-400">Output Container</label>
            <select id="containerSelect" class="glass-input rounded-xl px-3 py-2.5 text-xs mono text-cyan-300 outline-none cursor-pointer">
              <option value="mp4">MP4 (Universal Compatibility)</option>
              <option value="mkv">MKV (Matroska Multi-Track)</option>
              <option value="webm">WebM (VP9/Opus)</option>
              <option value="flv">FLV (Flash Video)</option>
              <option value="ts">TS (Raw MPEG-TS Stream)</option>
            </select>
          </div>
        </div>

        <!-- Options Checkboxes -->
        <div class="grid grid-cols-2 sm:grid-cols-4 gap-3 pt-1">
          <label class="flex items-center gap-2 text-xs text-slate-300 cursor-pointer">
            <input type="checkbox" id="chkSubtitles" checked class="rounded accent-cyan-400">
            <span>Download Subtitles</span>
          </label>
          <label class="flex items-center gap-2 text-xs text-slate-300 cursor-pointer">
            <input type="checkbox" id="chkAudioOnly" onchange="onAudioToggle()" class="rounded accent-cyan-400">
            <span>Audio Only (MP3)</span>
          </label>
          <label class="flex items-center gap-2 text-xs text-slate-300 cursor-pointer">
            <input type="checkbox" id="chkMetadata" checked class="rounded accent-cyan-400">
            <span>Embed Metadata</span>
          </label>
          <label class="flex items-center gap-2 text-xs text-slate-300 cursor-pointer">
            <input type="checkbox" id="chkThumbnail" checked class="rounded accent-cyan-400">
            <span>Embed Thumbnail</span>
          </label>
        </div>

        <!-- Save Destination Folder -->
        <div class="flex flex-col gap-1.5 pt-2 border-t border-white/5">
          <label class="text-xs text-slate-400 flex items-center justify-between">
            <span>Save Destination Folder</span>
            <span class="text-[11px] text-cyan-400">Synchronized with yt-dlp.conf</span>
          </label>
          <div class="flex gap-2">
            <input 
              type="text" 
              id="saveFolderInput" 
              value="{conf_dir}" 
              class="flex-1 glass-input rounded-xl px-3.5 py-2.5 text-xs mono text-slate-200 outline-none" 
              readonly 
            />
            <button onclick="onSelectFolderClick()" class="glass hover:border-cyan-400 px-4 py-2.5 rounded-xl text-xs font-semibold text-slate-200 hover:text-white transition-all cursor-pointer whitespace-nowrap">
              📁 Browse...
            </button>
            <button onclick="pyCall('open_folder')" class="glass hover:border-cyan-400 px-3.5 py-2.5 rounded-xl text-xs font-semibold text-slate-200 hover:text-white transition-all cursor-pointer">
              ↗ Open
            </button>
          </div>
        </div>

        <!-- Big Action Download Button -->
        <div class="pt-2 flex justify-end">
          <button onclick="startDownloadCurrent('custom')" class="btn-gradient w-full sm:w-auto px-10 py-3.5 rounded-xl text-sm font-extrabold flex items-center justify-center gap-2 cursor-pointer shadow-xl">
            <span>⬇️ START DOWNLOAD</span>
          </button>
        </div>
      </div>

    </div>

    <!-- ================================================================= -->
    <!-- TAB 2: LIBRARY & HISTORY                                          -->
    <!-- ================================================================= -->
    <div id="tab-library" class="tab-content hidden flex flex-col gap-4">
      <div class="glass rounded-2xl p-5 shadow-2xl flex flex-col gap-4">
        <div class="flex items-center justify-between pb-3 border-b border-white/5">
          <div>
            <h2 class="text-base font-bold text-white flex items-center gap-2">
              <span>📁</span> Downloaded Media Library &amp; History
            </h2>
            <p class="text-xs text-slate-400">Browse recorded live streams and downloaded video archives.</p>
          </div>
          <div class="flex gap-2">
            <button onclick="loadHistory()" class="glass hover:border-cyan-400 px-3 py-1.5 rounded-xl text-xs font-semibold text-slate-300">
              🔄 Refresh
            </button>
            <button onclick="pyCall('open_folder')" class="btn-gradient px-4 py-1.5 rounded-xl text-xs font-bold">
              📂 Open Folder
            </button>
          </div>
        </div>

        <input 
          type="text" 
          id="libSearchInput" 
          placeholder="🔍 Search library by title, creator, or URL..." 
          class="glass-input rounded-xl px-4 py-2.5 text-xs mono text-white outline-none w-full"
          oninput="filterHistory()"
        />

        <div id="historyContainer" class="flex flex-col gap-2 max-h-[500px] overflow-y-auto pr-1"></div>
      </div>
    </div>

    <!-- ================================================================= -->
    <!-- TAB 3: BATCH DOWNLOADER                                           -->
    <!-- ================================================================= -->
    <div id="tab-batch" class="tab-content hidden flex flex-col gap-4">
      <div class="glass rounded-2xl p-5 shadow-2xl flex flex-col gap-4">
        <h2 class="text-base font-bold text-white flex items-center gap-2">
          <span>📦</span> Batch URL Downloader
        </h2>
        <p class="text-xs text-slate-400">
          Paste multiple stream, video, or playlist links below (one per line). StreamVortex will queue and download them sequentially.
        </p>

        <textarea 
          id="batchUrlsInput" 
          rows="8" 
          placeholder="https://www.tiktok.com/@creator/live&#10;https://www.youtube.com/watch?v=...&#10;https://twitch.tv/..." 
          class="glass-input rounded-xl p-3.5 text-xs mono text-white outline-none w-full"
        ></textarea>

        <div class="flex items-center justify-between gap-4">
          <div class="flex items-center gap-2">
            <label class="text-xs text-slate-400">Batch Quality:</label>
            <select id="batchQualitySelect" class="glass-input rounded-xl px-3 py-1.5 text-xs mono text-cyan-300 outline-none">
              <option value="max">Best Quality</option>
              <option value="1080p">1080p MP4</option>
              <option value="720p">720p Fast</option>
              <option value="audio_mp3">Audio Only (MP3)</option>
            </select>
          </div>
          <button onclick="onSubmitBatchClick()" class="btn-gradient px-6 py-2.5 rounded-xl text-xs font-bold cursor-pointer">
            🚀 Start Batch Download
          </button>
        </div>
      </div>
    </div>

    <!-- ================================================================= -->
    <!-- TAB 4: LIVE WATCHDOG                                              -->
    <!-- ================================================================= -->
    <div id="tab-watchdog" class="tab-content hidden flex flex-col gap-4">
      <div class="glass rounded-2xl p-5 shadow-2xl flex flex-col gap-4">
        <h2 class="text-base font-bold text-white flex items-center gap-2">
          <span>🔴</span> Creator Live Watchdog
        </h2>
        <p class="text-xs text-slate-400">
          Monitor your favorite TikTok or Twitch creators. StreamVortex will check their status and can immediately launch recording.
        </p>

        <div class="flex gap-2">
          <input 
            type="text" 
            id="watchdogInput" 
            placeholder="Creator username (e.g. weathernewslive)..." 
            class="flex-1 glass-input rounded-xl px-4 py-2.5 text-xs mono text-white outline-none"
            onkeydown="if(event.key === 'Enter') onAddWatchlistClick()"
          />
          <button onclick="onAddWatchlistClick()" class="btn-gradient px-5 py-2.5 rounded-xl text-xs font-bold cursor-pointer">
            + Add to Watchlist
          </button>
        </div>

        <div class="pt-2">
          <h3 class="text-xs font-bold uppercase tracking-wider text-slate-400 mb-2.5">Monitored Creators</h3>
          <div id="watchlistContainer" class="flex flex-col gap-2"></div>
        </div>
      </div>
    </div>

    <!-- ================================================================= -->
    <!-- TAB 5: CONTAINER REPAIR & FIXUP STUDIO                            -->
    <!-- ================================================================= -->
    <div id="tab-repair" class="tab-content hidden flex flex-col gap-4">
      <div class="glass rounded-2xl p-5 shadow-2xl flex flex-col gap-4">
        <h2 class="text-base font-bold text-white flex items-center gap-2">
          <span>🛠️</span> Video Container Repair &amp; Interrupted Stream Fixup
        </h2>
        <p class="text-xs text-slate-400">
          Fixes videos that won't play due to MPEG-TS inside .mp4, broken FLV headers, or incomplete .part recordings from interrupted live sessions.
        </p>

        <div class="flex gap-2">
          <input 
            type="text" 
            id="repairPathInput" 
            placeholder="Select video file or .part file (or paste path)..." 
            class="flex-1 glass-input rounded-xl px-4 py-2.5 text-xs mono text-white outline-none"
          />
          <button onclick="onSelectRepairFileClick()" class="glass hover:border-cyan-400 px-4 py-2.5 rounded-xl text-xs font-semibold text-slate-200 hover:text-white cursor-pointer">
            📁 Browse File...
          </button>
          <button onclick="onInspectRepairClick()" class="btn-gradient px-5 py-2.5 rounded-xl text-xs font-bold cursor-pointer">
            🔍 Inspect
          </button>
        </div>

        <!-- Inspection Result Card -->
        <div id="repairCard" class="hidden glass rounded-xl p-4 flex flex-col gap-3 border border-white/10">
          <div class="flex items-center justify-between">
            <span id="repairFileName" class="text-xs font-bold text-white mono truncate max-w-md">video.mp4</span>
            <span id="repairStatusBadge" class="text-[10px] font-bold mono px-2 py-0.5 rounded-full bg-cyan-500/15 text-cyan-300">INSPECTED</span>
          </div>
          <div class="grid grid-cols-3 gap-2 text-xs mono text-slate-300 bg-slate-900/60 p-3 rounded-lg border border-white/5">
            <div>Extension: <span id="repairExt" class="text-white font-bold">mp4</span></div>
            <div>True Container: <span id="repairContainer" class="text-cyan-400 font-bold">mpegts</span></div>
            <div>Size: <span id="repairSize" class="text-slate-400">45 MB</span></div>
          </div>
          <div class="flex justify-end gap-2 pt-1">
            <button onclick="onExecuteRepairClick()" class="btn-gradient px-6 py-2 rounded-xl text-xs font-bold cursor-pointer">
              ⚡ Lossless Remux &amp; Faststart Fix
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- ================================================================= -->
    <!-- TAB 6: SETTINGS & DIAGNOSTICS                                     -->
    <!-- ================================================================= -->
    <div id="tab-settings" class="tab-content hidden flex flex-col gap-4">
      <div class="glass rounded-2xl p-5 shadow-2xl flex flex-col gap-4">
        <h2 class="text-base font-bold text-white flex items-center gap-2">
          <span>⚙️</span> Studio Settings &amp; System Health
        </h2>

        <!-- Health Cards Grid -->
        <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
          <div class="glass p-3.5 rounded-xl flex flex-col gap-1">
            <span class="text-[10px] uppercase font-bold text-slate-400 mono">yt-dlp Engine</span>
            <span id="healthYtdlp" class="text-xs font-bold text-emerald-400">Checking...</span>
          </div>
          <div class="glass p-3.5 rounded-xl flex flex-col gap-1">
            <span class="text-[10px] uppercase font-bold text-slate-400 mono">FFmpeg Transcoder</span>
            <span id="healthFfmpeg" class="text-xs font-bold text-emerald-400">Checking...</span>
          </div>
          <div class="glass p-3.5 rounded-xl flex flex-col gap-1">
            <span class="text-[10px] uppercase font-bold text-slate-400 mono">Free Disk Space</span>
            <span id="healthDisk" class="text-xs font-bold text-cyan-400">Checking...</span>
          </div>
          <div class="glass p-3.5 rounded-xl flex flex-col gap-1">
            <span class="text-[10px] uppercase font-bold text-slate-400 mono">Active Config</span>
            <span id="healthConf" class="text-xs font-bold text-amber-300 mono">{conf_name}</span>
          </div>
        </div>

        <!-- Settings Options -->
        <div class="flex flex-col gap-3 pt-2 border-t border-white/5">
          <div class="flex flex-col gap-1">
            <label class="text-xs text-slate-400">Global Download Directory (yt-dlp.conf)</label>
            <div class="flex gap-2">
              <input type="text" id="settingsDlDir" value="{conf_dir}" class="flex-1 glass-input rounded-xl px-3.5 py-2 text-xs mono text-white outline-none" readonly />
              <button onclick="onSelectFolderClick()" class="glass hover:border-cyan-400 px-4 py-2 rounded-xl text-xs font-semibold text-slate-200">Browse...</button>
            </div>
          </div>

          <div class="flex gap-3 pt-2">
            <button onclick="pyCall('run_doctor')" class="glass hover:border-cyan-400 px-4 py-2 rounded-xl text-xs font-bold text-cyan-300">
              🩺 Run System Doctor Diagnostics
            </button>
            <button onclick="pyCall('run_1click_setup')" class="glass hover:border-amber-400 px-4 py-2 rounded-xl text-xs font-bold text-amber-300">
              ⚡ Launch 1-Click Setup Wizard
            </button>
          </div>
        </div>
      </div>
    </div>

  </main>

  <!-- Toast Notification Pill -->
  <div id="toast" class="fixed bottom-6 right-6 z-50 glass bg-slate-900/95 border-cyan-400/50 text-white px-5 py-3 rounded-xl text-xs shadow-2xl hidden transition-all duration-300">
    Notification
  </div>

  <script>
    let currentStream = null;
    let hls = null;
    let rawHistory = [];

    // Helper to call native Python API via pywebview bridge or HTTP fallback
    async function pyCall(method, ...args) {{
      if (window.pywebview && window.pywebview.api && window.pywebview.api[method]) {{
        return await window.pywebview.api[method](...args);
      }}
      return null;
    }}

    function showToast(msg) {{
      const toast = document.getElementById('toast');
      toast.innerText = msg;
      toast.classList.remove('hidden');
      setTimeout(() => {{ toast.classList.add('hidden'); }}, 3200);
    }}

    function switchTab(tabId) {{
      document.querySelectorAll('.tab-content').forEach(el => el.classList.add('hidden'));
      document.querySelectorAll('.tab-btn').forEach(btn => {{
        btn.classList.remove('bg-cyan-400', 'text-slate-950');
        btn.classList.add('text-slate-300');
      }});

      const target = document.getElementById('tab-' + tabId);
      if (target) target.classList.remove('hidden');
      const activeBtn = document.getElementById('tabBtn-' + tabId);
      if (activeBtn) {{
        activeBtn.classList.add('bg-cyan-400', 'text-slate-950');
        activeBtn.classList.remove('text-slate-300');
      }}

      if (tabId === 'library') loadHistory();
      if (tabId === 'watchdog') loadWatchlist();
      if (tabId === 'settings') loadHealth();
    }}

    async function onPasteClick() {{
      const res = await pyCall('get_clipboard_text');
      if (res && res.text) {{
        document.getElementById('streamUrlInput').value = res.text.trim();
        showToast('Pasted URL from clipboard');
      }} else {{
        try {{
          const txt = await navigator.clipboard.readText();
          if (txt) {{
            document.getElementById('streamUrlInput').value = txt.trim();
            showToast('Pasted URL from clipboard');
          }}
        }} catch(e) {{}}
      }}
    }}

    function setPreset(url) {{
      document.getElementById('streamUrlInput').value = url;
      onAnalyzeClick();
    }}

    async function onAnalyzeClick() {{
      const url = document.getElementById('streamUrlInput').value.trim();
      if (!url) {{
        showToast('Please enter or paste a stream URL');
        return;
      }}

      const loader = document.getElementById('loader');
      const playerSection = document.getElementById('playerSection');
      loader.classList.remove('hidden');
      playerSection.classList.add('hidden');

      try {{
        const data = await pyCall('resolve_url', url);
        loader.classList.add('hidden');

        if (!data || data.error) {{
          alert('Resolution Error: ' + (data ? data.error : 'Unknown'));
          return;
        }}

        currentStream = data;
        document.getElementById('streamTitle').innerText = data.title || 'Untitled Stream';
        document.getElementById('uploaderBadge').innerText = data.uploader ? '@' + data.uploader : '';
        document.getElementById('liveStatusBadge').innerText = data.is_live ? 'LIVE STREAM' : 'VOD VIDEO';

        if (data.platform) {{
          const pb = document.getElementById('platformBadge');
          pb.innerText = `${{data.platform.icon || '⚡'}} ${{data.platform.name || 'Universal'}}`;
          if (data.platform.badge_color) {{
            pb.style.borderColor = data.platform.badge_color + '55';
            pb.style.color = data.platform.badge_color;
          }}
        }}

        renderFormats(data.formats || []);

        const previewTarget = data.preview_url || data.direct_url;
        if (previewTarget) {{
          playStream(previewTarget);
        }}

        playerSection.classList.remove('hidden');
        showToast('Stream resolved successfully!');
      }} catch (e) {{
        loader.classList.add('hidden');
        alert('Failed to resolve stream: ' + e);
      }}
    }}

    function renderFormats(formats) {{
      const container = document.getElementById('formatsList');
      container.innerHTML = '';

      if (!formats || formats.length === 0) {{
        container.innerHTML = '<div class="text-xs text-slate-500 py-2 mono">No format details available</div>';
        return;
      }}

      formats.forEach(f => {{
        const card = document.createElement('div');
        card.className = 'glass hover:border-cyan-400/60 p-2.5 rounded-xl flex items-center justify-between cursor-pointer transition-all';
        card.onclick = () => playStream(f.url);
        card.innerHTML = `
          <div>
            <div class="text-xs font-bold text-white mono">${{f.id || 'stream'}}</div>
            <div class="text-[11px] text-slate-400 mono">${{f.protocol}} • ${{f.height ? f.height + 'p' : (f.ext || 'mp4')}}</div>
          </div>
          <div class="flex gap-1">
            <button onclick="event.stopPropagation(); pyCall('copy_to_clipboard', '${{f.url}}'); showToast('URL Copied!');" class="glass hover:bg-white/10 px-2.5 py-1 rounded-lg text-xs mono text-cyan-400">
              Copy
            </button>
            <button onclick="event.stopPropagation(); triggerDownloadDirect('${{f.url}}', '${{f.id}}');" class="btn-gradient px-2.5 py-1 rounded-lg text-xs font-bold" title="Download Format">
              ⬇️
            </button>
          </div>
        `;
        container.appendChild(card);
      }});
    }}

    function playStream(url) {{
      const video = document.getElementById('hlsVideo');
      if (Hls.isSupported() && (url.includes('.m3u8') || url.includes('proxy_hls') || url.includes('pull-hls'))) {{
        if (hls) hls.destroy();
        hls = new Hls({{ enableWorker: true }});
        hls.loadSource(url);
        hls.attachMedia(video);
        hls.on(Hls.Events.MANIFEST_PARSED, () => video.play().catch(() => {{}}));
        hls.on(Hls.Events.ERROR, function(event, data) {{
          if (data && data.fatal) {{
            if (data.type === Hls.ErrorTypes.NETWORK_ERROR && !url.includes('proxy_hls') && currentStream && currentStream.direct_url) {{
              const proxyUrl = '/api/proxy_hls?url=' + encodeURIComponent(currentStream.direct_url);
              hls.loadSource(proxyUrl);
            }} else if (data.type === Hls.ErrorTypes.MEDIA_ERROR) {{
              hls.recoverMediaError();
            }}
          }}
        }});
      }} else {{
        video.src = url;
        video.play().catch(() => {{}});
      }}
    }}

    async function onClearCompletedClick() {{
      await pyCall('clear_completed_jobs');
      pollActiveDownloads();
      showToast('Cleared completed tasks from queue');
    }}

    function copyStreamUrl() {{
      if (!currentStream || !currentStream.formats || !currentStream.formats[0]) return;
      pyCall('copy_to_clipboard', currentStream.formats[0].url);
      showToast('Stream URL copied to clipboard!');
    }}

    function playInExternalPlayer() {{
      if (!currentStream) return;
      const u = currentStream.direct_url || (currentStream.formats && currentStream.formats[0] ? currentStream.formats[0].url : '');
      if (u) pyCall('play_in_external_player', u);
    }}

    async function onSelectFolderClick() {{
      const res = await pyCall('select_folder');
      if (res && res.folder) {{
        document.getElementById('saveFolderInput').value = res.folder;
        document.getElementById('hdrDlDir').innerText = res.folder;
        showToast('Download folder updated!');
      }}
    }}

    function onAudioToggle() {{
      const isAudio = document.getElementById('chkAudioOnly').checked;
      const qSelect = document.getElementById('qualitySelect');
      if (isAudio) {{
        qSelect.value = 'audio_mp3';
      }} else if (qSelect.value.startsWith('audio_')) {{
        qSelect.value = 'max';
      }}
    }}

    async function startDownloadCurrent(type) {{
      const inputUrl = document.getElementById('streamUrlInput').value.trim();
      const targetUrl = (currentStream && currentStream.direct_url) ? currentStream.direct_url : inputUrl;
      if (!targetUrl) {{
        showToast('Please enter a stream URL first');
        return;
      }}

      const title = currentStream ? currentStream.title : '';
      const uploader = currentStream ? currentStream.uploader : '';
      const isLive = currentStream ? Boolean(currentStream.is_live) : false;
      const q = document.getElementById('qualitySelect').value;
      const isAudio = (type === 'audio') || document.getElementById('chkAudioOnly').checked || q.startsWith('audio_');
      const container = document.getElementById('containerSelect').value;
      const customFolder = document.getElementById('saveFolderInput').value;

      showToast(`Starting download (${{isAudio ? 'Audio' : 'Video'}})...`);
      const res = await pyCall('start_download', {{
        url: targetUrl,
        title: title,
        uploader: uploader,
        is_live: isLive,
        quality: q,
        audio_only: isAudio,
        container: container,
        folder: customFolder
      }});

      if (res && res.job_id) {{
        showToast('Download queued in active status tracker');
        pollActiveDownloads();
      }}
    }}

    async function triggerDownloadDirect(url, formatId) {{
      const title = currentStream ? currentStream.title : formatId;
      const uploader = currentStream ? currentStream.uploader : '';
      const isLive = currentStream ? Boolean(currentStream.is_live) : false;
      await pyCall('start_download', {{
        url: url,
        title: title,
        uploader: uploader,
        is_live: isLive,
        quality: 'max'
      }});
      showToast('Downloading format ' + formatId);
      pollActiveDownloads();
    }}

    let pollTimer = null;
    async function pollActiveDownloads() {{
      try {{
        const jobs = await pyCall('get_active_jobs') || [];
        const container = document.getElementById('activeDownloadsContainer');
        const list = document.getElementById('activeJobsList');
        const countLbl = document.getElementById('activeCount');

        const running = jobs.filter(j => !j.completed);
        if (running.length === 0 && jobs.length === 0) {{
          container.classList.add('hidden');
          return;
        }}

        container.classList.remove('hidden');
        countLbl.innerText = `${{running.length}} running • ${{jobs.length}} total`;
        list.innerHTML = '';

        jobs.slice(-5).reverse().forEach(j => {{
          const item = document.createElement('div');
          item.className = 'glass p-3 rounded-xl flex flex-col gap-1.5 text-xs';
          const pct = Math.min(100, Math.max(0, j.progress || 0));
          const isDone = j.status === 'completed';
          const isFail = j.status === 'failed';
          const isStopped = j.status === 'stopped';
          const isCapturing = j.status === 'capturing' || (j.is_live && pct === 0 && !isDone && !isFail && !isStopped);
          
          let statusColor = 'text-cyan-400';
          let badgeText = pct.toFixed(1) + '%';
          if (isDone) {{ statusColor = 'text-emerald-400'; badgeText = 'COMPLETED'; }}
          else if (isFail) {{ statusColor = 'text-red-400'; badgeText = 'FAILED'; }}
          else if (isStopped) {{ statusColor = 'text-amber-400'; badgeText = 'STOPPED'; }}
          else if (isCapturing) {{ statusColor = 'text-rose-400 animate-pulse'; badgeText = '🔴 RECORDING'; }}

          const barWidth = isCapturing ? '100%' : `${{pct}}%`;
          const barClass = isCapturing ? 'h-full bg-gradient-to-r from-rose-500 via-pink-500 to-amber-500 rounded-full animate-pulse' : 'h-full bg-gradient-to-r from-cyan-400 to-blue-500 rounded-full transition-all duration-300';

          item.innerHTML = `
            <div class="flex items-center justify-between">
              <span class="font-bold text-white truncate max-w-md">${{j.title}}</span>
              <div class="flex items-center gap-2">
                <span class="mono ${{statusColor}} font-bold">${{badgeText}}</span>
                ${{!j.completed ? `<button onclick="pyCall('stop_job', '${{j.id}}'); showToast('Stopping recording and finalizing file...');" class="glass hover:bg-red-500/20 text-red-400 px-2 py-0.5 rounded text-[10px] mono">⏹️ Stop</button>` : ''}}
                ${{j.saved_path ? `<button onclick="pyCall('open_file', '${{j.saved_path.replace(/\\\\/g, '\\\\\\\\')}}')" class="glass hover:bg-cyan-500/20 text-cyan-400 px-2 py-0.5 rounded text-[10px] mono">▶ Play</button>` : ''}}
              </div>
            </div>
            <div class="w-full bg-slate-800/80 rounded-full h-2 overflow-hidden border border-white/5">
              <div class="${{barClass}}" style="width: ${{barWidth}}"></div>
            </div>
            <div class="flex items-center justify-between text-[11px] text-slate-400 mono">
              <span>${{j.status.toUpperCase()}}</span>
              <span>${{j.speed || '--'}} • ETA: ${{j.eta || '--'}}</span>
            </div>
          `;
          list.appendChild(item);
        }});

        if (running.length > 0) {{
          if (pollTimer) clearTimeout(pollTimer);
          pollTimer = setTimeout(pollActiveDownloads, 1200);
        }}
      }} catch (e) {{}}
    }}

    async function loadHistory() {{
      rawHistory = await pyCall('get_history') || [];
      renderHistoryList(rawHistory);
    }}

    function filterHistory() {{
      const q = document.getElementById('libSearchInput').value.toLowerCase().trim();
      if (!q) {{
        renderHistoryList(rawHistory);
        return;
      }}
      const filtered = rawHistory.filter(h => 
        (h.title && h.title.toLowerCase().includes(q)) || 
        (h.filename && h.filename.toLowerCase().includes(q)) ||
        (h.stream_url && h.stream_url.toLowerCase().includes(q))
      );
      renderHistoryList(filtered);
    }}

    function renderHistoryList(items) {{
      const container = document.getElementById('historyContainer');
      container.innerHTML = '';
      if (!items || items.length === 0) {{
        container.innerHTML = '<div class="text-xs text-slate-500 py-8 text-center mono">No downloaded files in library history.</div>';
        return;
      }}

      items.slice().reverse().forEach(h => {{
        const row = document.createElement('div');
        row.className = 'glass p-3 rounded-xl flex items-center justify-between gap-3';
        const isAudio = h.media_type === 'audio';
        const icon = isAudio ? '🎵' : (h.media_type === 'live' ? '🔴' : '🎬');
        row.innerHTML = `
          <div class="flex items-center gap-3 overflow-hidden">
            <span class="text-xl">${{icon}}</span>
            <div class="overflow-hidden">
              <div class="font-bold text-white text-xs truncate max-w-lg">${{h.title || 'Downloaded Item'}}</div>
              <div class="text-[10px] text-slate-400 mono truncate">${{h.timestamp ? h.timestamp.slice(0, 16) : ''}} • ${{h.filename || ''}}</div>
            </div>
          </div>
          <div class="flex gap-1.5 shrink-0">
            ${{h.filename ? `<button onclick="pyCall('open_file', '${{h.filename.replace(/\\\\/g, '\\\\\\\\')}}')" class="btn-gradient px-3 py-1 rounded-lg text-xs font-bold">▶ Play</button>` : ''}}
            ${{h.filename ? `<button onclick="pyCall('open_folder', '${{h.filename.replace(/\\\\/g, '\\\\\\\\')}}')" class="glass hover:border-cyan-400 px-2.5 py-1 rounded-lg text-xs text-slate-300">📂 Open</button>` : ''}}
          </div>
        `;
        container.appendChild(row);
      }});
    }}

    async function onSubmitBatchClick() {{
      const txt = document.getElementById('batchUrlsInput').value.trim();
      const urls = txt.split('\\n').map(u => u.trim()).filter(u => u.startsWith('http'));
      if (urls.length === 0) {{
        showToast('Please enter valid URLs (one per line)');
        return;
      }}
      const q = document.getElementById('batchQualitySelect').value;
      const res = await pyCall('batch_download', {{ urls: urls, quality: q }});
      if (res && res.count) {{
        showToast(`Queued ${{res.count}} batch items!`);
        document.getElementById('batchUrlsInput').value = '';
        pollActiveDownloads();
      }}
    }}

    async function loadWatchlist() {{
      const list = await pyCall('get_watchlist') || [];
      const container = document.getElementById('watchlistContainer');
      container.innerHTML = '';
      if (!list || list.length === 0) {{
        container.innerHTML = '<div class="text-xs text-slate-500 py-4 text-center mono">No creators on watchlist. Add one above!</div>';
        return;
      }}

      list.forEach(c => {{
        const row = document.createElement('div');
        row.className = 'glass p-3 rounded-xl flex items-center justify-between text-xs';
        row.innerHTML = `
          <div class="flex items-center gap-2.5">
            <span class="w-2 h-2 rounded-full bg-slate-500"></span>
            <span class="mono font-bold text-white">@${{c}}</span>
          </div>
          <div class="flex gap-1.5">
            <button onclick="onCheckCreatorClick('${{c}}')" class="btn-gradient px-3 py-1 rounded-lg text-xs font-bold">Check Live</button>
            <button onclick="onRemoveWatchlistClick('${{c}}')" class="glass hover:bg-red-500/20 text-red-400 px-2.5 py-1 rounded-lg text-xs mono">Remove</button>
          </div>
        `;
        container.appendChild(row);
      }});
    }}

    async function onAddWatchlistClick() {{
      const input = document.getElementById('watchdogInput');
      const val = input.value.trim();
      if (!val) return;
      await pyCall('add_to_watchlist', val);
      input.value = '';
      loadWatchlist();
      showToast(`Added @${{val}} to Watchlist!`);
    }}

    async function onRemoveWatchlistClick(creator) {{
      await pyCall('remove_from_watchlist', creator);
      loadWatchlist();
      showToast(`Removed @${{creator}}`);
    }}

    async function onCheckCreatorClick(creator) {{
      showToast(`Checking live status for @${{creator}}...`);
      const res = await pyCall('check_creator_live', creator);
      if (res && res.is_live) {{
        alert(`🎉 @${{creator}} is currently LIVE!\\n\\n"${{res.title}}"`);
        document.getElementById('streamUrlInput').value = `https://www.tiktok.com/@${{creator}}/live`;
        switchTab('studio');
        onAnalyzeClick();
      }} else {{
        showToast(`@${{creator}} is currently offline.`);
      }}
    }}

    async function onSelectRepairFileClick() {{
      const res = await pyCall('select_file');
      if (res && res.file) {{
        document.getElementById('repairPathInput').value = res.file;
        onInspectRepairClick();
      }}
    }}

    async function onInspectRepairClick() {{
      const path = document.getElementById('repairPathInput').value.trim();
      if (!path) return;
      const data = await pyCall('inspect_container', path);
      if (!data || data.error) {{
        alert('Inspection error: ' + (data ? data.error : 'File not found'));
        return;
      }}

      document.getElementById('repairFileName').innerText = data.filename;
      document.getElementById('repairExt').innerText = '.' + data.extension;
      document.getElementById('repairContainer').innerText = data.detected_container;
      document.getElementById('repairSize').innerText = data.size_mb + ' MB';

      const badge = document.getElementById('repairStatusBadge');
      if (data.is_mismatched) {{
        badge.className = 'text-[10px] font-bold mono px-2 py-0.5 rounded-full bg-amber-500/20 text-amber-300 border border-amber-500/40';
        badge.innerText = data.status_label || 'CONTAINER MISMATCH (REPAIR NEEDED)';
      }} else {{
        badge.className = 'text-[10px] font-bold mono px-2 py-0.5 rounded-full bg-emerald-500/20 text-emerald-300';
        badge.innerText = 'CONTAINER CLEAN';
      }}

      document.getElementById('repairCard').classList.remove('hidden');
    }}

    async function onExecuteRepairClick() {{
      const path = document.getElementById('repairPathInput').value.trim();
      if (!path) return;
      showToast('Repairing and remuxing container with FFmpeg...');
      const res = await pyCall('repair_container', path);
      if (res && res.repaired_path) {{
        alert('Repair Successful!\\n\\nSaved clean file:\\n' + res.repaired_path);
        onInspectRepairClick();
      }}
    }}

    async function loadHealth() {{
      const h = await pyCall('get_system_health');
      if (!h) return;
      document.getElementById('healthYtdlp').innerText = h.ytdlp && h.ytdlp.found ? '🟢 Installed (' + (h.ytdlp.version || 'Ready') + ')' : '🔴 Missing';
      document.getElementById('healthFfmpeg').innerText = h.ffmpeg && h.ffmpeg.found ? '🟢 Installed (' + (h.ffmpeg.version || 'Ready') + ')' : '🔴 Missing';
      document.getElementById('healthDisk').innerText = h.disk_free_gb ? `${{h.disk_free_gb.toFixed(1)}} GB Free` : '--';
    }}

    window.addEventListener('DOMContentLoaded', () => {{
      // Global Keyboard Shortcuts
      window.addEventListener('keydown', (e) => {{
        if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {{
          e.preventDefault();
          onAnalyzeClick();
          return;
        }}
        if (e.key === '/' && !['INPUT', 'TEXTAREA'].includes(document.activeElement.tagName)) {{
          e.preventDefault();
          const input = document.getElementById('streamUrlInput');
          if (input) {{
            switchTab('studio');
            input.focus();
            input.select();
          }}
        }}
      }});

      // Global Drag & Drop Handler for URLs and media files
      window.addEventListener('dragover', (e) => {{
        e.preventDefault();
        e.stopPropagation();
      }});

      window.addEventListener('drop', (e) => {{
        e.preventDefault();
        e.stopPropagation();
        let text = e.dataTransfer.getData('text/plain') || '';
        if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {{
          const file = e.dataTransfer.files[0];
          const filePath = file.path || file.name || '';
          if (filePath) {{
            text = filePath;
          }}
        }}
        text = text.trim().replace(/^["']|["']$/g, '');
        if (!text) return;

        if (text.startsWith('http://') || text.startsWith('https://')) {{
          document.getElementById('streamUrlInput').value = text;
          switchTab('studio');
          onAnalyzeClick();
          showToast('Dropped URL loaded for analysis');
        }} else if (text.match(/\\.(mp4|mkv|ts|flv|webm|m4a|aac|mp3|m3u8)$/i) || text.includes('\\\\') || text.includes('/')) {{
          document.getElementById('repairPathInput').value = text;
          switchTab('repair');
          onInspectRepairClick();
          showToast('Dropped media file loaded for container inspection');
        }}
      }});

      setTimeout(async () => {{
        const state = await pyCall('get_initial_state');
        if (state) {{
          if (state.download_dir) {{
            document.getElementById('saveFolderInput').value = state.download_dir;
            document.getElementById('hdrDlDir').innerText = state.download_dir;
            document.getElementById('settingsDlDir').value = state.download_dir;
          }}
        }}
        pollActiveDownloads();
      }}, 300);
    }});
  </script>
</body>
</html>
"""


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

    # Icon candidate resolution
    ico_path = get_asset_path("StreamVortex.ico") or get_asset_path("icon.ico")
    icon_str = str(ico_path) if ico_path else None

    if HAS_WEBVIEW:
        window = webview.create_window(
            title="StreamVortex Studio — Universal yt-dlp & Live Suite v1.2",
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
