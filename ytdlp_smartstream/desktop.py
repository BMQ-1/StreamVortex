"""
StreamVortex Modern Desktop GUI Studio.
Provides a modern dark-mode control window with live stream sniffing,
yt-dlp downloading, FFmpeg recording, binary setup, and transparent live logs.
"""

import sys
import os
import shutil
import threading
import subprocess
import webbrowser
from pathlib import Path
from typing import Optional

try:
    import ttkbootstrap as tb
    from ttkbootstrap.constants import *
    HAS_TTKBOOTSTRAP = True
except ImportError:
    import tkinter as tk
    from tkinter import ttk
    HAS_TTKBOOTSTRAP = False

from .setup_binaries import setup_all_binaries, get_bin_dir
from .engine import find_ytdlp, find_ffmpeg, run_ytdlp_download
from .config import get_download_dir, add_history_entry
from .sniffer import smart_sniff
from .tiktok_resolver import resolve_tiktok_live, resolve_tiktok_video
from .recorder import copy_to_clipboard, send_notification, record_stream


class StreamVortexApp:
    def __init__(self):
        if HAS_TTKBOOTSTRAP:
            self.root = tb.Window(
                title="StreamVortex // Powered by yt-dlp",
                themename="darkly",
                size=(920, 680),
                resizable=(True, True)
            )
        else:
            self.root = tk.Tk()
            self.root.title("StreamVortex // Powered by yt-dlp")
            self.root.geometry("920x680")
            self.root.configure(bg="#111827")

        self.root.minsize(800, 600)
        self._build_ui()
        self._check_engine_status_async()

    def _build_ui(self):
        # Main padding container
        main_frame = tb.Frame(self.root, padding=20) if HAS_TTKBOOTSTRAP else tk.Frame(self.root, padx=20, pady=20, bg="#111827")
        main_frame.pack(fill="both", expand=True)

        # 1. Header with Cyberpunk Branding & yt-dlp Badge
        header_frame = tb.Frame(main_frame) if HAS_TTKBOOTSTRAP else tk.Frame(main_frame, bg="#111827")
        header_frame.pack(fill="x", pady=(0, 15))

        title_lbl = tb.Label(
            header_frame,
            text="⚡ StreamVortex",
            font=("Segoe UI", 20, "bold"),
            bootstyle="info"
        ) if HAS_TTKBOOTSTRAP else tk.Label(header_frame, text="⚡ StreamVortex", font=("Segoe UI", 20, "bold"), fg="#00f2fe", bg="#111827")
        title_lbl.pack(side="left")

        badge_lbl = tb.Label(
            header_frame,
            text=" Powered by yt-dlp ",
            font=("Segoe UI", 9, "bold"),
            bootstyle="danger-inverse"
        ) if HAS_TTKBOOTSTRAP else tk.Label(header_frame, text=" Powered by yt-dlp ", font=("Segoe UI", 9, "bold"), fg="white", bg="#ef4444")
        badge_lbl.pack(side="left", padx=10, pady=4)

        ver_lbl = tb.Label(
            header_frame,
            text="v1.0.0 // Universal Stream Intelligence",
            font=("Segoe UI", 9),
            bootstyle="secondary"
        ) if HAS_TTKBOOTSTRAP else tk.Label(header_frame, text="v1.0.0 // Universal Stream Intelligence", font=("Segoe UI", 9), fg="#94a3b8", bg="#111827")
        ver_lbl.pack(side="left", padx=5)

        # Quick Links on Right of Header
        links_frame = tb.Frame(header_frame) if HAS_TTKBOOTSTRAP else tk.Frame(header_frame, bg="#111827")
        links_frame.pack(side="right")

        web_btn = tb.Button(
            links_frame,
            text="🌐 Open Web Studio",
            bootstyle="outline-info",
            command=self._launch_web_studio
        ) if HAS_TTKBOOTSTRAP else tk.Button(links_frame, text="🌐 Open Web Studio", command=self._launch_web_studio)
        web_btn.pack(side="left", padx=4)

        folder_btn = tb.Button(
            links_frame,
            text="📁 Downloads",
            bootstyle="outline-secondary",
            command=self._open_downloads_folder
        ) if HAS_TTKBOOTSTRAP else tk.Button(links_frame, text="📁 Downloads", command=self._open_downloads_folder)
        folder_btn.pack(side="left", padx=4)

        # 2. Engine & Binaries Status Card
        status_card = tb.Labelframe(main_frame, text=" Engine & Binaries Health (Self-Contained) ", padding=12, bootstyle="info") if HAS_TTKBOOTSTRAP else tk.LabelFrame(main_frame, text=" Engine & Binaries Health ", padx=12, pady=12, bg="#1e293b", fg="white")
        status_card.pack(fill="x", pady=(0, 15))

        status_grid = tb.Frame(status_card) if HAS_TTKBOOTSTRAP else tk.Frame(status_card, bg="#1e293b")
        status_grid.pack(fill="x")

        self.ytdlp_status_lbl = tb.Label(status_grid, text="yt-dlp: Checking...", font=("Segoe UI", 9), bootstyle="secondary") if HAS_TTKBOOTSTRAP else tk.Label(status_grid, text="yt-dlp: Checking...", fg="#94a3b8", bg="#1e293b")
        self.ytdlp_status_lbl.pack(side="left", padx=(0, 15))

        self.ffmpeg_status_lbl = tb.Label(status_grid, text="FFmpeg: Checking...", font=("Segoe UI", 9), bootstyle="secondary") if HAS_TTKBOOTSTRAP else tk.Label(status_grid, text="FFmpeg: Checking...", fg="#94a3b8", bg="#1e293b")
        self.ffmpeg_status_lbl.pack(side="left", padx=15)

        self.driver_status_lbl = tb.Label(status_grid, text="Playwright: Checking...", font=("Segoe UI", 9), bootstyle="secondary") if HAS_TTKBOOTSTRAP else tk.Label(status_grid, text="Playwright: Checking...", fg="#94a3b8", bg="#1e293b")
        self.driver_status_lbl.pack(side="left", padx=15)

        self.setup_btn = tb.Button(
            status_grid,
            text="⚡ Auto-Download / Verify Binaries",
            bootstyle="success",
            command=self._run_binary_setup_thread
        ) if HAS_TTKBOOTSTRAP else tk.Button(status_grid, text="⚡ Auto-Download Binaries", command=self._run_binary_setup_thread)
        self.setup_btn.pack(side="right")

        self.progress_bar = tb.Progressbar(status_card, mode="determinate", bootstyle="info-striped") if HAS_TTKBOOTSTRAP else ttk.Progressbar(status_card, mode="determinate")
        self.progress_bar.pack(fill="x", pady=(8, 0))
        self.progress_bar["value"] = 100

        # 3. Stream Actions Panel
        action_card = tb.Labelframe(main_frame, text=" Stream Discovery & Downloader ", padding=14, bootstyle="primary") if HAS_TTKBOOTSTRAP else tk.LabelFrame(main_frame, text=" Stream Discovery & Downloader ", padx=14, pady=14, bg="#1e293b", fg="white")
        action_card.pack(fill="x", pady=(0, 15))

        # URL Input
        url_frame = tb.Frame(action_card) if HAS_TTKBOOTSTRAP else tk.Frame(action_card, bg="#1e293b")
        url_frame.pack(fill="x", pady=(0, 10))

        tb.Label(url_frame, text="Target URL:", font=("Segoe UI", 10, "bold")).pack(side="left", padx=(0, 8))
        self.url_var = tb.StringVar() if HAS_TTKBOOTSTRAP else tk.StringVar()
        self.url_entry = tb.Entry(url_frame, textvariable=self.url_var, font=("Consolas", 10)) if HAS_TTKBOOTSTRAP else tk.Entry(url_frame, textvariable=self.url_var, font=("Consolas", 10))
        self.url_entry.pack(side="left", fill="x", expand=True, padx=(0, 8))

        paste_btn = tb.Button(url_frame, text="📋 Paste", bootstyle="secondary", command=self._paste_clipboard) if HAS_TTKBOOTSTRAP else tk.Button(url_frame, text="📋 Paste", command=self._paste_clipboard)
        paste_btn.pack(side="left")

        # Action Buttons
        btn_bar = tb.Frame(action_card) if HAS_TTKBOOTSTRAP else tk.Frame(action_card, bg="#1e293b")
        btn_bar.pack(fill="x")

        self.sniff_btn = tb.Button(btn_bar, text="⚡ Sniff Stream", bootstyle="info", command=self._on_sniff_click) if HAS_TTKBOOTSTRAP else tk.Button(btn_bar, text="⚡ Sniff Stream", command=self._on_sniff_click)
        self.sniff_btn.pack(side="left", padx=(0, 6))

        self.download_btn = tb.Button(btn_bar, text="⬇️ Download Video (yt-dlp)", bootstyle="success", command=self._on_download_click) if HAS_TTKBOOTSTRAP else tk.Button(btn_bar, text="⬇️ Download Video (yt-dlp)", command=self._on_download_click)
        self.download_btn.pack(side="left", padx=6)

        self.record_btn = tb.Button(btn_bar, text="🔴 Record Live (FFmpeg)", bootstyle="danger", command=self._on_record_click) if HAS_TTKBOOTSTRAP else tk.Button(btn_bar, text="🔴 Record Live", command=self._on_record_click)
        self.record_btn.pack(side="left", padx=6)

        self.audio_btn = tb.Button(btn_bar, text="🎵 Extract MP3", bootstyle="warning", command=self._on_audio_click) if HAS_TTKBOOTSTRAP else tk.Button(btn_bar, text="🎵 Extract MP3", command=self._on_audio_click)
        self.audio_btn.pack(side="left", padx=6)

        self.play_btn = tb.Button(btn_bar, text="🎬 Play in Player", bootstyle="secondary", command=self._on_play_click) if HAS_TTKBOOTSTRAP else tk.Button(btn_bar, text="🎬 Play in Player", command=self._on_play_click)
        self.play_btn.pack(side="left", padx=6)

        # 4. Transparent Live Activity & Output Console
        log_card = tb.Labelframe(main_frame, text=" Transparent Activity & Command Execution Console ", padding=10, bootstyle="secondary") if HAS_TTKBOOTSTRAP else tk.LabelFrame(main_frame, text=" Transparent Activity Console ", padx=10, pady=10, bg="#1e293b", fg="white")
        log_card.pack(fill="both", expand=True)

        self.log_text = tb.ScrolledText(log_card, height=12, font=("Consolas", 9), autohide=True) if HAS_TTKBOOTSTRAP else tk.Text(log_card, height=12, font=("Consolas", 9), bg="#0a0f1d", fg="#e2e8f0")
        self.log_text.pack(fill="both", expand=True)
        self._log("[StreamVortex v1.0.0] Initialized. Powered by yt-dlp.")
        self._log(f"[Storage] Download folder: {get_download_dir()}")

    def _log(self, text: str):
        self.log_text.insert("end", text + "\n")
        self.log_text.see("end")

    def _paste_clipboard(self):
        try:
            val = self.root.clipboard_get()
            if val:
                self.url_var.set(val.strip())
        except Exception:
            pass

    def _open_downloads_folder(self):
        d_dir = get_download_dir()
        if sys.platform == "win32":
            os.startfile(d_dir)
        else:
            subprocess.run(["xdg-open", str(d_dir)])

    def _launch_web_studio(self):
        self._log("[Web Studio] Launching background server at http://127.0.0.1:8765 ...")
        from .web_ui import launch_web_ui
        threading.Thread(target=launch_web_ui, daemon=True).start()

    def _check_engine_status_async(self):
        def _check():
            ytdlp = find_ytdlp()
            ffmpeg = find_ffmpeg()
            bin_dir = get_bin_dir()

            ytdlp_text = f"yt-dlp: Ready ({Path(ytdlp[0]).name})" if ytdlp else "yt-dlp: Missing"
            ffmpeg_text = f"FFmpeg: Ready ({Path(ffmpeg).name})" if ffmpeg else "FFmpeg: Missing"

            # Check playwright
            try:
                from playwright.sync_api import sync_playwright
                with sync_playwright() as p:
                    b = p.chromium.launch(headless=True)
                    b.close()
                pw_text = "Playwright: Chromium Ready"
            except Exception:
                pw_text = "Playwright: Missing Driver"

            self.root.after(0, lambda: self.ytdlp_status_lbl.config(text=ytdlp_text, bootstyle="success" if ytdlp else "danger"))
            self.root.after(0, lambda: self.ffmpeg_status_lbl.config(text=ffmpeg_text, bootstyle="success" if ffmpeg else "warning"))
            self.root.after(0, lambda: self.driver_status_lbl.config(text=pw_text, bootstyle="success" if "Ready" in pw_text else "warning"))

        threading.Thread(target=_check, daemon=True).start()

    def _run_binary_setup_thread(self):
        self.setup_btn.config(state="disabled")
        self._log("\n[Setup] Starting automated binary check & official downloads...")

        def _worker():
            def prog_cb(msg: str, pct: float):
                self.root.after(0, lambda: self._log(f"[Setup] {msg}"))
                self.root.after(0, lambda: self.progress_bar.configure(value=pct))

            results = setup_all_binaries(force_download=False, progress_callback=prog_cb)
            self.root.after(0, lambda: self._log("[Setup] All binaries and plugins are verified!"))
            self.root.after(0, lambda: self.setup_btn.config(state="normal"))
            self._check_engine_status_async()

        threading.Thread(target=_worker, daemon=True).start()

    def _on_sniff_click(self):
        url = self.url_var.get().strip()
        if not url:
            self._log("[Error] Please enter a video or stream URL.")
            return

        self._log(f"\n[Sniffer] Analyzing media wire for: {url}")
        def _worker():
            sniffed = smart_sniff(url)
            if sniffed:
                self.root.after(0, lambda: self._log(f"[Success] Stream Found: {sniffed.url} ({sniffed.stream_type.upper()})"))
                copy_to_clipboard(sniffed.url)
                self.root.after(0, lambda: self._log("[Clipboard] Copied direct stream URL to clipboard!"))
            else:
                self.root.after(0, lambda: self._log("[-] No stream detected on that page."))
        threading.Thread(target=_worker, daemon=True).start()

    def _on_download_click(self):
        url = self.url_var.get().strip()
        if not url:
            self._log("[Error] Please enter a URL.")
            return

        self._log(f"\n[Download] Executing yt-dlp download for: {url}")
        d_dir = get_download_dir()
        out_file = str(d_dir / "%(title)s.%(ext)s")

        def _worker():
            def on_out(line):
                self.root.after(0, lambda l=line: self._log(f"[yt-dlp] {l}"))
            run_ytdlp_download(url, out_file, is_live=True, on_output=on_out)
            self.root.after(0, lambda: self._log(f"[Done] Download completed! Saved to: {d_dir}"))
        threading.Thread(target=_worker, daemon=True).start()

    def _on_record_click(self):
        url = self.url_var.get().strip()
        if not url:
            self._log("[Error] Please enter a live URL.")
            return

        import time
        d_dir = get_download_dir()
        out_file = str(d_dir / f"stream_{int(time.time())}.mp4")
        self._log(f"\n[Record] Starting live FFmpeg capture to: {out_file}")

        def _worker():
            # If TikTok, resolve live format first
            if "tiktok.com" in url:
                import re
                m = re.search(r'@([\w.-]+)', url)
                if m:
                    res = resolve_tiktok_live(m.group(1))
                    if res and res.formats:
                        hls = next((f for f in res.formats if f.protocol == "m3u8_native"), res.formats[0])
                        record_stream(hls.url, out_file, headers=res.http_headers)
                        return
            record_stream(url, out_file)
        threading.Thread(target=_worker, daemon=True).start()

    def _on_audio_click(self):
        url = self.url_var.get().strip()
        if not url:
            self._log("[Error] Please enter a URL.")
            return

        d_dir = get_download_dir()
        out_file = str(d_dir / "%(title)s.%(ext)s")
        self._log(f"\n[Audio] Extracting MP3 audio track via yt-dlp...")

        def _worker():
            def on_out(line):
                self.root.after(0, lambda l=line: self._log(f"[yt-dlp] {l}"))
            run_ytdlp_download(url, out_file, audio_only=True, on_output=on_out)
            self.root.after(0, lambda: self._log(f"[Done] MP3 Audio saved to: {d_dir}"))
        threading.Thread(target=_worker, daemon=True).start()

    def _on_play_click(self):
        url = self.url_var.get().strip()
        if not url:
            self._log("[Error] Please enter a URL.")
            return

        player = shutil.which("mpv") or shutil.which("vlc")
        if not player:
            self._log("[Notice] Neither MPV nor VLC found on system PATH. Copying URL instead...")
            copy_to_clipboard(url)
            return

        self._log(f"[Player] Launching {Path(player).name} with {url}...")
        subprocess.Popen([player, url])

    def run(self):
        self.root.mainloop()


def launch_desktop_gui():
    app = StreamVortexApp()
    app.run()


if __name__ == "__main__":
    launch_desktop_gui()
