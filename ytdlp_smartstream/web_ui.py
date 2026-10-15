"""
StreamVortex Modern Dark-Mode Web Dashboard.
Features:
- Live HLS stream player with embedded HLS.js
- Multi-platform stream resolver (TikTok Live, Videos, and Universal Web Sniffer)
- One-click Video & MP3 Audio downloader
- Live Watchdog multi-channel monitor
- Downloads History & Explorer integration
- Settings management
"""

import json
import os
import sys
import shutil
import subprocess
import threading
import webbrowser
from http.server import HTTPServer, BaseHTTPRequestHandler
import urllib.parse
from pathlib import Path
from typing import Dict, Any

from .tiktok_resolver import resolve_tiktok_live, resolve_tiktok_video
from .sniffer import smart_sniff
from .engine import find_ytdlp_conf, resolve_stream_metadata, run_ytdlp_download
from .config import (
    get_config, save_config, get_download_dir,
    get_history, add_history_entry,
    get_watchlist, add_to_watchlist, remove_from_watchlist
)
from .recorder import record_stream

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>StreamVortex Studio // Universal Stream Intelligence</title>
  <script src="https://cdn.jsdelivr.net/npm/hls.js@latest"></script>
  <script src="https://cdn.tailwindcss.com"></script>
  <link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600;700&family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap" rel="stylesheet">
  <style>
    body {
      background: #07090e;
      background-image: 
        radial-gradient(circle at 10% 10%, rgba(0, 242, 254, 0.08) 0%, transparent 45%),
        radial-gradient(circle at 90% 90%, rgba(79, 172, 254, 0.06) 0%, transparent 45%);
      color: #f1f5f9;
      font-family: 'Plus Jakarta Sans', sans-serif;
    }
    .mono { font-family: 'JetBrains Mono', monospace; }
    .glass {
      background: rgba(15, 23, 42, 0.65);
      backdrop-filter: blur(20px);
      border: 1px solid rgba(255, 255, 255, 0.08);
    }
    .glass-input {
      background: rgba(8, 12, 22, 0.8);
      border: 1px solid rgba(255, 255, 255, 0.1);
    }
    .glass-input:focus {
      border-color: #00f2fe;
      box-shadow: 0 0 0 3px rgba(0, 242, 254, 0.2);
    }
    .btn-gradient {
      background: linear-gradient(135deg, #00f2fe 0%, #4facfe 100%);
      color: #030712;
      font-weight: 700;
      transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
    }
    .btn-gradient:hover {
      transform: translateY(-2px);
      box-shadow: 0 8px 25px -4px rgba(0, 242, 254, 0.4);
    }
    .live-pulse::before {
      content: '';
      display: inline-block;
      width: 8px;
      height: 8px;
      border-radius: 50%;
      background: #ff2a5f;
      margin-right: 6px;
      box-shadow: 0 0 10px #ff2a5f;
      animation: pulse 1.5s infinite;
    }
    @keyframes pulse {
      0% { opacity: 1; transform: scale(1); }
      50% { opacity: 0.4; transform: scale(0.85); }
      100% { opacity: 1; transform: scale(1); }
    }
  </style>
</head>
<body class="min-h-screen flex flex-col">

  <!-- Top Navigation Bar -->
  <header class="glass sticky top-0 z-50 px-6 py-4 border-b border-white/5 flex items-center justify-between">
    <div class="flex items-center gap-3">
      <div class="w-10 h-10 rounded-xl bg-gradient-to-tr from-cyan-400 to-blue-500 flex items-center justify-center text-slate-950 font-black text-xl shadow-lg shadow-cyan-500/20">
        ⚡
      </div>
      <div>
        <div class="flex items-center gap-2">
          <h1 class="text-xl font-extrabold tracking-tight bg-gradient-to-r from-cyan-400 to-blue-400 bg-clip-text text-transparent">
            StreamVortex
          </h1>
          <span class="text-[10px] uppercase font-bold tracking-wider px-2 py-0.5 rounded-full bg-red-500/10 text-red-400 border border-red-500/20 mono">
            Powered by yt-dlp
          </span>
          <span class="text-[10px] uppercase font-bold tracking-wider px-2 py-0.5 rounded-full bg-cyan-500/10 text-cyan-400 border border-cyan-500/20 mono">
            Config: __ACTIVE_CONF__
          </span>
        </div>
        <p class="text-xs text-slate-400 mono">v1.0.0 // Intelligent Stream &amp; Live Studio</p>
      </div>
    </div>

    <div class="flex items-center gap-2 bg-slate-900/60 p-1 rounded-xl border border-white/5">
      <button onclick="switchTab('studio')" id="tabBtn-studio" class="tab-btn px-4 py-2 rounded-lg text-sm font-semibold transition-all bg-cyan-400 text-slate-950">
        ⚡ Studio
      </button>
      <button onclick="switchTab('watchdog')" id="tabBtn-watchdog" class="tab-btn px-4 py-2 rounded-lg text-sm font-semibold transition-all text-slate-300 hover:text-white">
        🔴 Watchdog
      </button>
      <button onclick="switchTab('history')" id="tabBtn-history" class="tab-btn px-4 py-2 rounded-lg text-sm font-semibold transition-all text-slate-300 hover:text-white">
        📁 Downloads
      </button>
    </div>

    <div class="flex items-center gap-3">
      <button onclick="openFolder()" class="px-3 py-2 rounded-lg glass text-xs font-semibold text-slate-300 hover:text-white hover:border-cyan-400/50 flex items-center gap-1.5 transition-all">
        📂 Open Folder
      </button>
    </div>
  </header>

  <!-- Main Content Container -->
  <main class="flex-1 max-w-6xl w-full mx-auto p-6 flex flex-col gap-6">

    <!-- TAB 1: STUDIO -->
    <div id="tab-studio" class="tab-content flex flex-col gap-6">
      
      <!-- Input Card -->
      <div class="glass rounded-2xl p-6 shadow-2xl flex flex-col gap-4">
        <label class="text-xs font-bold uppercase tracking-wider text-slate-400 flex items-center justify-between">
          <span>Target Stream or Video URL</span>
          <span class="text-cyan-400 lowercase font-normal mono">tiktok live • tiktok vod • web m3u8</span>
        </label>
        <div class="flex flex-col sm:flex-row gap-3">
          <input 
            type="text" 
            id="streamUrlInput" 
            placeholder="Paste URL (e.g. https://www.tiktok.com/@weathernewslive/live)..." 
            class="flex-1 glass-input rounded-xl px-4 py-3.5 text-sm mono text-white outline-none"
            onkeydown="if(event.key === 'Enter') resolveStream()"
          />
          <button onclick="resolveStream()" id="resolveBtn" class="btn-gradient px-7 py-3.5 rounded-xl text-sm flex items-center justify-center gap-2 cursor-pointer">
            <span>⚡ Resolve</span>
          </button>
        </div>

        <div id="loader" class="hidden py-4 text-center mono text-sm text-cyan-400 animate-pulse flex items-center justify-center gap-2">
          <svg class="animate-spin h-5 w-5 text-cyan-400" viewBox="0 0 24 24" fill="none"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z"></path></svg>
          <span>Interception wire active: resolving manifests & solving challenges...</span>
        </div>
      </div>

      <!-- Live Player & Formats Section -->
      <div id="playerSection" class="hidden flex flex-col gap-6">
        
        <div class="glass rounded-2xl p-6 shadow-2xl flex flex-col gap-4">
          <!-- Stream Header -->
          <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-white/5">
            <div>
              <div class="flex items-center gap-2.5 mb-1.5">
                <span id="liveStatusBadge" class="live-pulse bg-red-500/15 border border-red-500/30 text-red-400 text-xs px-2.5 py-0.5 rounded-full font-bold mono">
                  LIVE STREAM
                </span>
                <span id="uploaderBadge" class="text-xs font-semibold text-cyan-400 mono">@creator</span>
              </div>
              <h2 id="streamTitle" class="text-xl font-bold tracking-tight text-white">Stream Title</h2>
            </div>
            
            <div class="flex items-center gap-2 flex-wrap">
              <button onclick="downloadCurrent('video')" class="btn-gradient px-4 py-2.5 rounded-xl text-xs flex items-center gap-1.5">
                ⬇️ Download Best
              </button>
              <button onclick="downloadCurrent('audio')" class="glass hover:border-cyan-400 px-4 py-2.5 rounded-xl text-xs font-bold text-white flex items-center gap-1.5 transition-all">
                🎵 Audio Only (MP3)
              </button>
              <button onclick="copyCurrentUrl()" class="glass hover:border-cyan-400 px-4 py-2.5 rounded-xl text-xs font-bold text-slate-300 hover:text-white flex items-center gap-1.5 transition-all">
                📋 Copy M3U8
              </button>
            </div>
          </div>

          <!-- Video Player Container -->
          <div class="relative w-full aspect-video rounded-xl overflow-hidden bg-black border border-white/10 shadow-2xl">
            <video id="hlsVideo" controls autoplay muted class="w-full h-full object-contain"></video>
          </div>

          <!-- Formats Grid -->
          <div class="mt-2">
            <h3 class="text-sm font-bold text-slate-300 mb-3 flex items-center justify-between">
              <span>Available Multi-Bitrate Formats</span>
              <span class="text-xs text-slate-500 font-normal">Click any format to preview or copy</span>
            </h3>
            <div id="formatsList" class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3"></div>
          </div>
        </div>

      </div>

    </div>

    <!-- TAB 2: WATCHDOG -->
    <div id="tab-watchdog" class="tab-content hidden flex flex-col gap-6">
      <div class="glass rounded-2xl p-6 shadow-2xl flex flex-col gap-4">
        <h2 class="text-lg font-bold text-white">🔴 Live Creator Watchdog</h2>
        <p class="text-xs text-slate-400">
          Add TikTok creators to monitor. StreamVortex will alert you the moment they go live and can automatically start recording.
        </p>

        <div class="flex gap-3">
          <input 
            type="text" 
            id="watchdogInput" 
            placeholder="Creator username (e.g. weathernewslive)..." 
            class="flex-1 glass-input rounded-xl px-4 py-3 text-sm mono text-white outline-none"
          />
          <button onclick="addToWatchlist()" class="btn-gradient px-6 py-3 rounded-xl text-sm font-bold">
            + Add to Watchlist
          </button>
        </div>

        <div class="mt-4">
          <h3 class="text-xs font-bold uppercase tracking-wider text-slate-400 mb-3">Monitored Creators</h3>
          <div id="watchlistContainer" class="flex flex-col gap-2"></div>
        </div>
      </div>
    </div>

    <!-- TAB 3: DOWNLOADS HISTORY -->
    <div id="tab-history" class="tab-content hidden flex flex-col gap-6">
      <div class="glass rounded-2xl p-6 shadow-2xl flex flex-col gap-4">
        <div class="flex items-center justify-between pb-3 border-b border-white/5">
          <div>
            <h2 class="text-lg font-bold text-white">📁 Download & Recording History</h2>
            <p class="text-xs text-slate-400">Recorded streams and downloaded media files.</p>
          </div>
          <button onclick="openFolder()" class="btn-gradient px-4 py-2 rounded-xl text-xs">
            Open Downloads Folder
          </button>
        </div>

        <div id="historyContainer" class="flex flex-col gap-2.5 mt-2"></div>
      </div>
    </div>

  </main>

  <!-- Toast Notification Pill -->
  <div id="toast" class="fixed bottom-6 right-6 z-50 glass bg-slate-900/95 border-cyan-400/50 text-white px-5 py-3 rounded-xl text-sm shadow-2xl shadow-cyan-500/20 hidden transition-all duration-300">
    Notification
  </div>

  <script>
    let currentStream = null;
    let hls = null;

    function showToast(msg) {
      const toast = document.getElementById('toast');
      toast.innerText = msg;
      toast.classList.remove('hidden');
      setTimeout(() => { toast.classList.add('hidden'); }, 3000);
    }

    function switchTab(tabId) {
      document.querySelectorAll('.tab-content').forEach(el => el.classList.add('hidden'));
      document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.classList.remove('bg-cyan-400', 'text-slate-950');
        btn.classList.add('text-slate-300');
      });

      document.getElementById('tab-' + tabId).classList.remove('hidden');
      const activeBtn = document.getElementById('tabBtn-' + tabId);
      activeBtn.classList.add('bg-cyan-400', 'text-slate-950');
      activeBtn.classList.remove('text-slate-300');

      if (tabId === 'history') loadHistory();
      if (tabId === 'watchdog') loadWatchlist();
    }

    async function resolveStream() {
      const url = document.getElementById('streamUrlInput').value.trim();
      if (!url) return;

      const loader = document.getElementById('loader');
      const playerSection = document.getElementById('playerSection');
      loader.classList.remove('hidden');
      playerSection.classList.add('hidden');

      try {
        const resp = await fetch('/api/resolve?url=' + encodeURIComponent(url));
        const data = await resp.json();
        loader.classList.add('hidden');

        if (data.error) {
          alert('Resolution Error: ' + data.error);
          return;
        }

        currentStream = data;
        document.getElementById('streamTitle').innerText = data.title || 'Untitled Stream';
        document.getElementById('uploaderBadge').innerText = data.uploader ? '@' + data.uploader : '';
        document.getElementById('liveStatusBadge').innerText = data.is_live ? 'LIVE STREAM' : 'VOD VIDEO';

        renderFormats(data.formats || []);

        const hlsFmt = data.formats.find(f => f.protocol === 'm3u8_native' || f.url.includes('.m3u8')) || data.formats[0];
        if (hlsFmt) {
          playStream(hlsFmt.url);
        }

        playerSection.classList.remove('hidden');
      } catch (e) {
        loader.classList.add('hidden');
        alert('Server connection failed: ' + e);
      }
    }

    function renderFormats(formats) {
      const container = document.getElementById('formatsList');
      container.innerHTML = '';

      formats.forEach(f => {
        const card = document.createElement('div');
        card.className = 'glass hover:border-cyan-400/60 p-3 rounded-xl flex items-center justify-between cursor-pointer transition-all';
        card.onclick = () => playStream(f.url);
        card.innerHTML = `
          <div>
            <div class="text-xs font-bold text-white mono">${f.id || f.quality_id}</div>
            <div class="text-[11px] text-slate-400 mono">${f.protocol} • ${f.width ? f.width + 'p' : f.ext}</div>
          </div>
          <div class="flex gap-1.5">
            <button onclick="event.stopPropagation(); navigator.clipboard.writeText('${f.url}'); showToast('URL Copied!');" class="glass hover:bg-white/10 px-2.5 py-1.5 rounded-lg text-xs mono text-cyan-400">
              Copy
            </button>
            <button onclick="event.stopPropagation(); triggerDownload('${f.url}', currentStream ? currentStream.title : '${f.id}', false, currentStream ? currentStream.uploader : '', currentStream ? currentStream.is_live : false);" class="btn-gradient px-2.5 py-1.5 rounded-lg text-xs font-bold" title="Download Format">
              ⬇️
            </button>
          </div>
        `;
        container.appendChild(card);
      });
    }

    function playStream(url) {
      const video = document.getElementById('hlsVideo');
      if (Hls.isSupported() && (url.includes('.m3u8') || url.includes('pull-hls'))) {
        if (hls) hls.destroy();
        hls = new Hls({ enableWorker: true });
        hls.loadSource(url);
        hls.attachMedia(video);
        hls.on(Hls.Events.MANIFEST_PARSED, () => video.play().catch(() => {}));
      } else {
        video.src = url;
        video.play().catch(() => {});
      }
      showToast('Loaded format into live player');
    }

    function copyCurrentUrl() {
      if (!currentStream || !currentStream.formats || !currentStream.formats[0]) return;
      navigator.clipboard.writeText(currentStream.formats[0].url);
      showToast('Stream URL copied to clipboard!');
    }

    async function downloadCurrent(type) {
      if (!currentStream || !currentStream.formats || !currentStream.formats[0]) return;
      const url = currentStream.formats[0].url;
      const title = currentStream.title || 'stream';
      const uploader = currentStream.uploader || '';
      const isLive = currentStream.is_live !== undefined ? currentStream.is_live : true;
      await triggerDownload(url, title, type === 'audio', uploader, isLive);
    }

    async function triggerDownload(url, title, isAudio, uploader, isLive) {
      showToast(`Started download (${isAudio ? 'MP3 Audio' : 'Video'})...`);
      try {
        const resp = await fetch('/api/download', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({
            url: url,
            title: title || (currentStream ? currentStream.title : ''),
            uploader: uploader || (currentStream ? currentStream.uploader : ''),
            is_live: isLive !== undefined ? isLive : (currentStream ? currentStream.is_live : false),
            audio_only: isAudio,
            referer: document.getElementById('streamUrlInput').value
          })
        });
        const res = await resp.json();
        if (res.status === 'started') {
          showToast('Downloading in background! Check Downloads tab.');
        }
      } catch (e) {
        showToast('Download request failed');
      }
    }

    async function loadHistory() {
      const resp = await fetch('/api/history');
      const data = await resp.json();
      const container = document.getElementById('historyContainer');
      container.innerHTML = '';
      if (!data || data.length === 0) {
        container.innerHTML = '<div class="text-sm text-slate-500 py-6 text-center mono">No downloads recorded yet.</div>';
        return;
      }
      data.forEach(item => {
        const row = document.createElement('div');
        row.className = 'glass p-3.5 rounded-xl flex items-center justify-between text-sm';
        row.innerHTML = `
          <div>
            <div class="font-bold text-white">${item.title}</div>
            <div class="text-xs text-slate-400 mono">${item.date_str} • ${item.type.toUpperCase()}</div>
          </div>
          <button onclick="openFolder()" class="glass hover:border-cyan-400 px-3 py-1.5 rounded-lg text-xs mono text-cyan-400">
            Open File
          </button>
        `;
        container.appendChild(row);
      });
    }

    async function loadWatchlist() {
      const resp = await fetch('/api/watchlist');
      const list = await resp.json();
      const container = document.getElementById('watchlistContainer');
      container.innerHTML = '';
      if (!list || list.length === 0) {
        container.innerHTML = '<div class="text-sm text-slate-500 py-4 text-center mono">No creators on watchlist yet.</div>';
        return;
      }
      list.forEach(c => {
        const row = document.createElement('div');
        row.className = 'glass p-3.5 rounded-xl flex items-center justify-between';
        row.innerHTML = `
          <div class="flex items-center gap-3">
            <span class="w-2.5 h-2.5 rounded-full bg-slate-500"></span>
            <span class="mono font-bold text-white">@${c}</span>
          </div>
          <div class="flex gap-2">
            <button onclick="checkCreatorLive('${c}')" class="btn-gradient px-3 py-1.5 rounded-lg text-xs font-bold">Check Now</button>
            <button onclick="removeFromWatchlist('${c}')" class="glass hover:bg-red-500/20 text-red-400 px-3 py-1.5 rounded-lg text-xs mono">Remove</button>
          </div>
        `;
        container.appendChild(row);
      });
    }

    async function addToWatchlist() {
      const input = document.getElementById('watchdogInput');
      const val = input.value.trim();
      if (!val) return;
      await fetch('/api/watchlist/add?creator=' + encodeURIComponent(val));
      input.value = '';
      loadWatchlist();
      showToast(`Added @${val} to Watchlist!`);
    }

    async function removeFromWatchlist(creator) {
      await fetch('/api/watchlist/remove?creator=' + encodeURIComponent(creator));
      loadWatchlist();
      showToast(`Removed @${creator}`);
    }

    function checkCreatorLive(creator) {
      document.getElementById('streamUrlInput').value = `https://www.tiktok.com/@${creator}/live`;
      switchTab('studio');
      resolveStream();
    }

    async function openFolder() {
      await fetch('/api/open_folder');
      showToast('Opened downloads folder in Explorer');
    }
  </script>
</body>
</html>
"""


class StreamVortexWebHandler(BaseHTTPRequestHandler):

    def do_GET(self):
        parsed = urllib.parse.urlsplit(self.path)

        if parsed.path in ["/", "/index.html"]:
            conf = find_ytdlp_conf()
            conf_name = conf.name if conf else "Default"
            html = HTML_TEMPLATE.replace("__ACTIVE_CONF__", conf_name)
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(html.encode("utf-8"))
            return

        if parsed.path == "/api/resolve":
            query = urllib.parse.parse_qs(parsed.query)
            target_url = query.get("url", [None])[0]
            if not target_url:
                self._send_json({"error": "Missing url parameter"}, status=400)
                return

            try:
                # 1. Resolve using universal metadata resolver (TikTok Live/Video, YouTube, Twitch, etc.)
                meta = resolve_stream_metadata(target_url)
                if meta and meta.get("formats"):
                    self._send_json(meta)
                    return

                # 2. Universal Sniffer fallback
                sniffed = smart_sniff(target_url)
                if sniffed:
                    self._send_json({
                        "id": target_url,
                        "title": sniffed.page_title or "Discovered Stream",
                        "uploader": "",
                        "is_live": sniffed.stream_type in ("hls", "flv"),
                        "formats": [
                            {"id": f"{sniffed.stream_type}-main", "url": sniffed.url, "protocol": "m3u8_native" if sniffed.stream_type == "hls" else "https", "ext": "mp4"}
                        ]
                    })
                    return

                self._send_json({"error": "No media stream detected on page or channel is offline."}, status=404)
            except Exception as e:
                self._send_json({"error": str(e)}, status=500)
            return

        if parsed.path == "/api/history":
            self._send_json(get_history())
            return

        if parsed.path == "/api/watchlist":
            self._send_json(get_watchlist())
            return

        if parsed.path == "/api/watchlist/add":
            query = urllib.parse.parse_qs(parsed.query)
            creator = query.get("creator", [""])[0]
            success = add_to_watchlist(creator)
            self._send_json({"success": success})
            return

        if parsed.path == "/api/watchlist/remove":
            query = urllib.parse.parse_qs(parsed.query)
            creator = query.get("creator", [""])[0]
            success = remove_from_watchlist(creator)
            self._send_json({"success": success})
            return

        if parsed.path == "/api/open_folder":
            d_dir = get_download_dir()
            if sys.platform == "win32":
                os.startfile(d_dir)
            else:
                subprocess.run(["xdg-open", str(d_dir)])
            self._send_json({"success": True})
            return

        self.send_response(404)
        self.end_headers()

    def do_POST(self):
        parsed = urllib.parse.urlsplit(self.path)

        if parsed.path == "/api/download":
            length = int(self.headers.get("content-length", 0))
            body = self.rfile.read(length).decode("utf-8")
            data = json.loads(body)

            stream_url = data.get("url")
            title = data.get("title")
            uploader = data.get("uploader")
            audio_only = data.get("audio_only", False)
            referer = data.get("referer")
            is_live = data.get("is_live", False)

            # Run download asynchronously in worker thread
            def _worker():
                target_title = title
                target_uploader = uploader
                target_is_live = is_live

                # If title is missing or generic placeholder, resolve metadata first
                if not target_title or target_title in ("download", "media", "stream", "Discovered Stream"):
                    meta = resolve_stream_metadata(stream_url)
                    target_title = meta.get("title")
                    target_uploader = meta.get("uploader") or target_uploader
                    target_is_live = meta.get("is_live", target_is_live)

                run_ytdlp_download(
                    stream_url=stream_url,
                    title=target_title,
                    uploader=target_uploader,
                    referer=referer,
                    audio_only=audio_only,
                    is_live=target_is_live,
                    respect_conf_output=True
                )

            threading.Thread(target=_worker, daemon=True).start()
            self._send_json({"status": "started"})
            return

        self.send_response(404)
        self.end_headers()

    def _send_json(self, data, status=200):
        body = json.dumps(data).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):
        pass


def launch_web_ui(port: int = 8765, open_browser: bool = True):
    server = HTTPServer(("127.0.0.1", port), StreamVortexWebHandler)
    url = f"http://127.0.0.1:{port}"
    print(f"\n[StreamVortex Web Studio] Serving at {url}")
    print("[i] Press Ctrl+C in terminal to stop web server.\n")

    if open_browser:
        threading.Thread(target=lambda: webbrowser.open(url)).start()

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[StreamVortex] Web server stopped.")
        server.server_close()
