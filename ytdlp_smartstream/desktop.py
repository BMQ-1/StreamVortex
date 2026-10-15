"""
StreamVortex Modern Desktop GUI Studio.
Provides a modern dark-mode control window with live stream sniffing,
yt-dlp downloading, FFmpeg recording, binary setup, batch downloads,
auto-clipboard monitoring, and transparent live logs.
"""

import sys
import os
import re
import shutil
import threading
import subprocess
import webbrowser
from pathlib import Path
from typing import Optional, List

try:
    import ttkbootstrap as tb
    from ttkbootstrap.constants import *
    HAS_TTKBOOTSTRAP = True
except ImportError:
    import tkinter as tk
    from tkinter import ttk
    HAS_TTKBOOTSTRAP = False

from .setup_binaries import setup_all_binaries, get_bin_dir
from .engine import (
    find_ytdlp, find_ffmpeg, run_ytdlp_download, run_ffmpeg_record,
    resolve_stream_metadata, find_ytdlp_conf, find_player, is_environment_ready,
    detect_platform, clean_target_url, check_free_disk_space
)
from .config import get_download_dir, add_history_entry, get_history
from .onboarding import get_default_tools_dir, launch_onboarding_gui
from .sniffer import smart_sniff
from .tiktok_resolver import resolve_tiktok_live, resolve_tiktok_video
from .recorder import copy_to_clipboard, send_notification, record_stream


class StreamVortexApp:
    def __init__(self):
        if HAS_TTKBOOTSTRAP:
            self.root = tb.Window(
                title="StreamVortex // Powered by yt-dlp",
                themename="darkly",
                size=(960, 720),
                resizable=(True, True)
            )
        else:
            self.root = tk.Tk()
            self.root.title("StreamVortex // Powered by yt-dlp")
            self.root.geometry("960x720")
            self.root.configure(bg="#111827")

        self.root.minsize(860, 640)
        self._last_clip = ""
        self._build_ui()
        self._check_engine_status_async()
        self._start_clipboard_watcher()
        self.root.after(800, self._check_first_run_onboarding)

    def _build_ui(self):
        # Main padding container
        main_frame = tb.Frame(self.root, padding=18) if HAS_TTKBOOTSTRAP else tk.Frame(self.root, padx=18, pady=18, bg="#111827")
        main_frame.pack(fill="both", expand=True)

        # 1. Header with Cyberpunk Branding & yt-dlp Badge
        header_frame = tb.Frame(main_frame) if HAS_TTKBOOTSTRAP else tk.Frame(main_frame, bg="#111827")
        header_frame.pack(fill="x", pady=(0, 12))

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
            text="v1.0 // Universal Stream Studio",
            font=("Segoe UI", 9),
            bootstyle="secondary"
        ) if HAS_TTKBOOTSTRAP else tk.Label(header_frame, text="v1.0 // Universal Stream Studio", font=("Segoe UI", 9), fg="#94a3b8", bg="#111827")
        ver_lbl.pack(side="left", padx=5)

        # Quick Navigation Links on Right of Header
        links_frame = tb.Frame(header_frame) if HAS_TTKBOOTSTRAP else tk.Frame(header_frame, bg="#111827")
        links_frame.pack(side="right")

        web_btn = tb.Button(
            links_frame,
            text="🌐 Web Studio",
            bootstyle="outline-info",
            command=self._launch_web_studio
        ) if HAS_TTKBOOTSTRAP else tk.Button(links_frame, text="🌐 Web Studio", command=self._launch_web_studio)
        web_btn.pack(side="left", padx=3)

        doctor_btn = tb.Button(
            links_frame,
            text="🩺 Doctor",
            bootstyle="outline-warning",
            command=self._run_doctor_check
        ) if HAS_TTKBOOTSTRAP else tk.Button(links_frame, text="🩺 Doctor", command=self._run_doctor_check)
        doctor_btn.pack(side="left", padx=3)

        tools_btn = tb.Button(
            links_frame,
            text="🛠️ Tools Folder",
            bootstyle="outline-secondary",
            command=self._open_tools_folder
        ) if HAS_TTKBOOTSTRAP else tk.Button(links_frame, text="🛠️ Tools Folder", command=self._open_tools_folder)
        tools_btn.pack(side="left", padx=3)

        history_btn = tb.Button(
            links_frame,
            text="📜 History",
            bootstyle="outline-secondary",
            command=self._open_history_dialog
        ) if HAS_TTKBOOTSTRAP else tk.Button(links_frame, text="📜 History", command=self._open_history_dialog)
        history_btn.pack(side="left", padx=3)

        folder_btn = tb.Button(
            links_frame,
            text="📁 Downloads",
            bootstyle="outline-secondary",
            command=self._open_downloads_folder
        ) if HAS_TTKBOOTSTRAP else tk.Button(links_frame, text="📁 Downloads", command=self._open_downloads_folder)
        folder_btn.pack(side="left", padx=3)

        # 2. Engine & Binaries Status Card
        status_card = tb.Labelframe(main_frame, text=" System & Media Engines Status ", padding=10, bootstyle="info") if HAS_TTKBOOTSTRAP else tk.LabelFrame(main_frame, text=" System Status ", padx=10, pady=10, bg="#1e293b", fg="white")
        status_card.pack(fill="x", pady=(0, 12))

        status_grid = tb.Frame(status_card) if HAS_TTKBOOTSTRAP else tk.Frame(status_card, bg="#1e293b")
        status_grid.pack(fill="x")

        self.ytdlp_status_lbl = tb.Label(status_grid, text="yt-dlp: Checking...", font=("Segoe UI", 9), bootstyle="secondary") if HAS_TTKBOOTSTRAP else tk.Label(status_grid, text="yt-dlp: Checking...", fg="#94a3b8", bg="#1e293b")
        self.ytdlp_status_lbl.pack(side="left", padx=(0, 10))

        self.ffmpeg_status_lbl = tb.Label(status_grid, text="FFmpeg: Checking...", font=("Segoe UI", 9), bootstyle="secondary") if HAS_TTKBOOTSTRAP else tk.Label(status_grid, text="FFmpeg: Checking...", fg="#94a3b8", bg="#1e293b")
        self.ffmpeg_status_lbl.pack(side="left", padx=10)

        self.driver_status_lbl = tb.Label(status_grid, text="Playwright: Checking...", font=("Segoe UI", 9), bootstyle="secondary") if HAS_TTKBOOTSTRAP else tk.Label(status_grid, text="Playwright: Checking...", fg="#94a3b8", bg="#1e293b")
        self.driver_status_lbl.pack(side="left", padx=10)

        self.conf_status_lbl = tb.Label(status_grid, text="Config: Checking...", font=("Segoe UI", 9), bootstyle="secondary") if HAS_TTKBOOTSTRAP else tk.Label(status_grid, text="Config: Checking...", fg="#94a3b8", bg="#1e293b")
        self.conf_status_lbl.pack(side="left", padx=10)

        self.disk_space_lbl = tb.Label(status_grid, text="Storage: Checking...", font=("Segoe UI", 9), bootstyle="secondary") if HAS_TTKBOOTSTRAP else tk.Label(status_grid, text="Storage: Checking...", fg="#94a3b8", bg="#1e293b")
        self.disk_space_lbl.pack(side="left", padx=10)

        self.setup_btn = tb.Button(
            status_grid,
            text="⚡ 1-Click Setup Wizard",
            bootstyle="success",
            command=self._open_setup_wizard
        ) if HAS_TTKBOOTSTRAP else tk.Button(status_grid, text="⚡ Setup Wizard", command=self._open_setup_wizard)
        self.setup_btn.pack(side="right")

        # 2b. Interactive Download Destination & Drag-and-Drop Card
        from .engine import get_conf_download_dir
        dest_card = tb.Labelframe(main_frame, text=" 📥 Active Download Destination (yt-dlp.conf) ", padding=10, bootstyle="info") if HAS_TTKBOOTSTRAP else tk.LabelFrame(main_frame, text=" Download Destination ", padx=10, pady=10, bg="#1e293b", fg="white")
        dest_card.pack(fill="x", pady=(0, 12))

        dest_row = tb.Frame(dest_card) if HAS_TTKBOOTSTRAP else tk.Frame(dest_card, bg="#1e293b")
        dest_row.pack(fill="x")

        tb.Label(dest_row, text="Saving to:", font=("Segoe UI", 9, "bold")).pack(side="left", padx=(0, 8))
        self.download_dir_var = tb.StringVar(value=str(get_conf_download_dir())) if HAS_TTKBOOTSTRAP else tk.StringVar(value=str(get_conf_download_dir()))
        self.dest_entry = tb.Entry(dest_row, textvariable=self.download_dir_var, font=("Segoe UI", 9)) if HAS_TTKBOOTSTRAP else tk.Entry(dest_row, textvariable=self.download_dir_var, font=("Segoe UI", 9))
        self.dest_entry.pack(side="left", fill="x", expand=True, padx=(0, 8))

        self.dest_entry.bind("<Return>", lambda e: self._on_download_dir_apply())
        self.dest_entry.bind("<FocusOut>", lambda e: self._on_download_dir_apply())

        set_dest_btn = tb.Button(
            dest_row,
            text="📂 Browse / Drop Folder",
            bootstyle="outline-info",
            command=self._browse_and_set_download_dir
        ) if HAS_TTKBOOTSTRAP else tk.Button(dest_row, text="📂 Browse / Drop", command=self._browse_and_set_download_dir)
        set_dest_btn.pack(side="right")

        # 3. Stream Actions & Downloader Panel
        action_card = tb.Labelframe(main_frame, text=" Stream Discovery & Intelligent Downloader ", padding=14, bootstyle="primary") if HAS_TTKBOOTSTRAP else tk.LabelFrame(main_frame, text=" Stream Discovery & Downloader ", padx=14, pady=14, bg="#1e293b", fg="white")
        action_card.pack(fill="x", pady=(0, 12))

        # URL Input Row
        url_frame = tb.Frame(action_card) if HAS_TTKBOOTSTRAP else tk.Frame(action_card, bg="#1e293b")
        url_frame.pack(fill="x", pady=(0, 8))

        tb.Label(url_frame, text="Target URL:", font=("Segoe UI", 10, "bold")).pack(side="left", padx=(0, 8))
        self.url_var = tb.StringVar() if HAS_TTKBOOTSTRAP else tk.StringVar()
        self.url_var.trace_add("write", lambda *args: self._on_url_change())
        self.url_entry = tb.Entry(url_frame, textvariable=self.url_var, font=("Consolas", 10)) if HAS_TTKBOOTSTRAP else tk.Entry(url_frame, textvariable=self.url_var, font=("Consolas", 10))
        self.url_entry.pack(side="left", fill="x", expand=True, padx=(0, 8))

        paste_btn = tb.Button(url_frame, text="📋 Paste", bootstyle="secondary", command=self._paste_clipboard) if HAS_TTKBOOTSTRAP else tk.Button(url_frame, text="📋 Paste", command=self._paste_clipboard)
        paste_btn.pack(side="left", padx=(0, 4))

        batch_btn = tb.Button(url_frame, text="📑 Batch URLs", bootstyle="info", command=self._open_batch_dialog) if HAS_TTKBOOTSTRAP else tk.Button(url_frame, text="📑 Batch", command=self._open_batch_dialog)
        batch_btn.pack(side="left")

        # Platform Detection & Quick Platform Presets Row
        platform_row = tb.Frame(action_card) if HAS_TTKBOOTSTRAP else tk.Frame(action_card, bg="#1e293b")
        platform_row.pack(fill="x", pady=(0, 10))

        self.platform_badge_lbl = tb.Label(
            platform_row,
            text="🌐 Universal Mode",
            font=("Segoe UI", 8, "bold"),
            bootstyle="secondary-inverse"
        ) if HAS_TTKBOOTSTRAP else tk.Label(platform_row, text="🌐 Universal Mode", font=("Segoe UI", 8, "bold"), fg="#94a3b8", bg="#0f172a")
        self.platform_badge_lbl.pack(side="left", padx=(0, 10))

        tb.Label(platform_row, text="Presets:", font=("Segoe UI", 8), bootstyle="secondary").pack(side="left", padx=(0, 4))

        for name, example in [("TikTok Live", "https://www.tiktok.com/@weathernewslive/live"), ("YouTube", "https://www.youtube.com/watch?v=dQw4w9WgXcQ"), ("Twitch", "https://www.twitch.tv/"), ("Kick", "https://kick.com/")]:
            btn = tb.Button(
                platform_row,
                text=name,
                bootstyle="link",
                command=lambda ex=example: self.url_var.set(ex)
            ) if HAS_TTKBOOTSTRAP else tk.Button(platform_row, text=name, command=lambda ex=example: self.url_var.set(ex))
            btn.pack(side="left", padx=2)

        # Format & Smart Features Control Row
        opt_frame = tb.Frame(action_card) if HAS_TTKBOOTSTRAP else tk.Frame(action_card, bg="#1e293b")
        opt_frame.pack(fill="x", pady=(0, 10))

        tb.Label(opt_frame, text="Quality Profile:", font=("Segoe UI", 9)).pack(side="left", padx=(0, 6))
        self.quality_var = tb.StringVar(value="🎬 Maximum Quality (4K / 2K / 1080p)") if HAS_TTKBOOTSTRAP else tk.StringVar(value="🎬 Maximum Quality (4K / 2K / 1080p)")
        quality_options = [
            "🎬 Maximum Quality (4K / 2K / 1080p)",
            "📱 Universal MP4 (1080p)",
            "⚡ Fast / Low Bandwidth (720p)",
            "⚙️ Respect yt-dlp.conf Setting",
            "🎵 Studio MP3 Audio (320kbps)",
            "🎧 High-Fidelity Audio (M4A)"
        ]
        self.quality_combo = tb.Combobox(
            opt_frame,
            textvariable=self.quality_var,
            values=quality_options,
            state="readonly",
            width=32
        ) if HAS_TTKBOOTSTRAP else ttk.Combobox(opt_frame, textvariable=self.quality_var, values=quality_options, state="readonly", width=32)
        self.quality_combo.pack(side="left", padx=(0, 16))

        # Auto-sniff clipboard checkbox
        self.auto_sniff_var = tb.BooleanVar(value=True) if HAS_TTKBOOTSTRAP else tk.BooleanVar(value=True)
        self.auto_sniff_chk = tb.Checkbutton(
            opt_frame,
            text="⚡ Auto-Sniff Clipboard",
            variable=self.auto_sniff_var,
            bootstyle="round-toggle"
        ) if HAS_TTKBOOTSTRAP else tk.Checkbutton(opt_frame, text="⚡ Auto-Sniff Clipboard", variable=self.auto_sniff_var, bg="#1e293b", fg="white", selectcolor="#0f172a")
        self.auto_sniff_chk.pack(side="left")

        # Live Speed / Status indicator
        self.download_speed_lbl = tb.Label(
            opt_frame,
            text="Ready",
            font=("Consolas", 9),
            bootstyle="secondary"
        ) if HAS_TTKBOOTSTRAP else tk.Label(opt_frame, text="Ready", font=("Consolas", 9), fg="#94a3b8", bg="#1e293b")
        self.download_speed_lbl.pack(side="right")

        # Action Buttons Row
        btn_bar = tb.Frame(action_card) if HAS_TTKBOOTSTRAP else tk.Frame(action_card, bg="#1e293b")
        btn_bar.pack(fill="x", pady=(0, 8))

        self.sniff_btn = tb.Button(btn_bar, text="⚡ Sniff Stream", bootstyle="info", command=self._on_sniff_click) if HAS_TTKBOOTSTRAP else tk.Button(btn_bar, text="⚡ Sniff Stream", command=self._on_sniff_click)
        self.sniff_btn.pack(side="left", padx=(0, 6))

        self.download_btn = tb.Button(btn_bar, text="⬇️ Download Media", bootstyle="success", command=self._on_download_click) if HAS_TTKBOOTSTRAP else tk.Button(btn_bar, text="⬇️ Download Media", command=self._on_download_click)
        self.download_btn.pack(side="left", padx=6)

        self.record_btn = tb.Button(btn_bar, text="🔴 Record Live (FFmpeg)", bootstyle="danger", command=self._on_record_click) if HAS_TTKBOOTSTRAP else tk.Button(btn_bar, text="🔴 Record Live", command=self._on_record_click)
        self.record_btn.pack(side="left", padx=6)

        self.audio_btn = tb.Button(btn_bar, text="🎵 Extract Audio", bootstyle="warning", command=self._on_audio_click) if HAS_TTKBOOTSTRAP else tk.Button(btn_bar, text="🎵 Extract Audio", command=self._on_audio_click)
        self.audio_btn.pack(side="left", padx=6)

        self.play_btn = tb.Button(btn_bar, text="🎬 Play in Player", bootstyle="secondary", command=self._on_play_click) if HAS_TTKBOOTSTRAP else tk.Button(btn_bar, text="🎬 Play in Player", command=self._on_play_click)
        self.play_btn.pack(side="left", padx=6)

        # Real-time Download Progress Bar
        self.progress_bar = tb.Progressbar(action_card, mode="determinate", bootstyle="success-striped") if HAS_TTKBOOTSTRAP else ttk.Progressbar(action_card, mode="determinate")
        self.progress_bar.pack(fill="x")
        self.progress_bar["value"] = 100

        # 4. Transparent Live Activity & Output Console
        log_card = tb.Labelframe(main_frame, text=" Live Activity & Command Execution Console ", padding=10, bootstyle="secondary") if HAS_TTKBOOTSTRAP else tk.LabelFrame(main_frame, text=" Activity Console ", padx=10, pady=10, bg="#1e293b", fg="white")
        log_card.pack(fill="both", expand=True)

        log_top = tb.Frame(log_card) if HAS_TTKBOOTSTRAP else tk.Frame(log_card, bg="#1e293b")
        log_top.pack(fill="x", pady=(0, 4))
        clear_btn = tb.Button(log_top, text="🧹 Clear Log", bootstyle="outline-secondary", command=self._clear_log) if HAS_TTKBOOTSTRAP else tk.Button(log_top, text="Clear", command=self._clear_log)
        clear_btn.pack(side="right")

        self.log_text = tb.ScrolledText(log_card, height=12, font=("Consolas", 9), autohide=True) if HAS_TTKBOOTSTRAP else tk.Text(log_card, height=12, font=("Consolas", 9), bg="#0a0f1d", fg="#e2e8f0")
        self.log_text.pack(fill="both", expand=True)

        self._log("[StreamVortex v1.0] Universal Stream Studio Initialized.")
        self._log(f"[Storage] Primary download directory: {get_download_dir()}")

    def _log(self, text: str):
        self.log_text.insert("end", text + "\n")
        self.log_text.see("end")

    def _clear_log(self):
        self.log_text.delete("1.0", "end")

    def _paste_clipboard(self):
        try:
            val = self.root.clipboard_get()
            if val:
                self.url_var.set(val.strip())
        except Exception:
            pass

    def _start_clipboard_watcher(self):
        def _check():
            try:
                if self.auto_sniff_var.get():
                    clip = self.root.clipboard_get().strip()
                    if clip and clip != self._last_clip and (clip.startswith("http://") or clip.startswith("https://")):
                        low = clip.lower()
                        stream_sites = ["tiktok.com", "youtube.com", "youtu.be", "twitch.tv", "kick.com", "twitter.com", "x.com", "facebook.com", "instagram.com", ".m3u8", ".mpd", ".flv"]
                        if any(k in low for k in stream_sites):
                            self._last_clip = clip
                            self.url_var.set(clip)
                            self._log(f"[Auto-Sniffer] Detected stream URL from clipboard: {clip}")
                            short_disp = clip[:45] + "..." if len(clip) > 45 else clip
                            self.download_speed_lbl.config(text=f"Detected: {short_disp}", bootstyle="info")
            except Exception:
                pass
            self.root.after(1000, _check)
        self.root.after(1000, _check)

    def _open_downloads_folder(self):
        from .engine import get_conf_download_dir
        d_dir = get_conf_download_dir()
        if sys.platform == "win32":
            os.startfile(d_dir)
        else:
            subprocess.run(["xdg-open", str(d_dir)])

    def _browse_and_set_download_dir(self):
        from tkinter import filedialog
        current = self.download_dir_var.get().strip().strip("'\"")
        chosen = filedialog.askdirectory(initialdir=current, title="Select Download Destination Folder")
        if chosen:
            self.download_dir_var.set(chosen)
            self._on_download_dir_apply()

    def _on_download_dir_apply(self):
        from .engine import update_ytdlp_conf_destinations
        val = self.download_dir_var.get().strip().strip("'\"")
        if val:
            p = Path(val).expanduser().resolve()
            p.mkdir(parents=True, exist_ok=True)
            ok, msg = update_ytdlp_conf_destinations(p)
            self._log(f"[+] Download destination updated: {p}")
            self._log("[+] Synced destinations in yt-dlp.conf (Videos, Subs, Thumbnails)")
            self._check_engine_status_async()

    def _open_tools_folder(self):
        tdir = get_default_tools_dir()
        if tdir.exists():
            if sys.platform == "win32":
                os.startfile(tdir)
            else:
                subprocess.run(["xdg-open", str(tdir)])
            self._log(f"[Tools] Opened media tools directory: {tdir}")
        else:
            self._log(f"[Tools] Tools folder '{tdir}' does not exist yet. Run Setup Wizard.")

    def _launch_web_studio(self):
        self._log("[Web Studio] Starting local web server at http://127.0.0.1:8765 ...")
        from .web_ui import launch_web_ui
        threading.Thread(target=launch_web_ui, daemon=True).start()

    def _run_doctor_check(self):
        self._log("\n[Doctor] Running system diagnostic check...")
        def _worker():
            from .doctor import run_doctor
            run_doctor()
            self.root.after(0, lambda: self._log("[Doctor] Health check completed. See terminal/logs for full table."))
            self._check_engine_status_async()
        threading.Thread(target=_worker, daemon=True).start()

    def _check_engine_status_async(self):
        def _check():
            ytdlp = find_ytdlp()
            ffmpeg = find_ffmpeg()

            ytdlp_text = "yt-dlp: Ready" if ytdlp else "yt-dlp: Missing"
            ffmpeg_text = "FFmpeg: Ready" if ffmpeg else "FFmpeg: Missing"

            # Check playwright
            try:
                from playwright.sync_api import sync_playwright
                with sync_playwright() as p:
                    b = p.chromium.launch(headless=True)
                    b.close()
                pw_text = "Playwright: Ready"
            except Exception:
                pw_text = "Playwright: Missing"

            # Check yt-dlp config
            conf = find_ytdlp_conf()
            conf_text = "Config: Global (.conf)" if conf else "Config: Standard"

            # Check disk space
            has_space, free_gb = check_free_disk_space()
            disk_text = f"Disk: {free_gb:.1f} GB Free"

            self.root.after(0, lambda: self.ytdlp_status_lbl.config(text=ytdlp_text, bootstyle="success" if ytdlp else "danger"))
            self.root.after(0, lambda: self.ffmpeg_status_lbl.config(text=ffmpeg_text, bootstyle="success" if ffmpeg else "warning"))
            self.root.after(0, lambda: self.driver_status_lbl.config(text=pw_text, bootstyle="success" if "Ready" in pw_text else "secondary"))
            self.root.after(0, lambda: self.conf_status_lbl.config(text=conf_text, bootstyle="success" if conf else "secondary"))
            self.root.after(0, lambda: self.disk_space_lbl.config(text=disk_text, bootstyle="secondary" if has_space else "danger"))

        threading.Thread(target=_check, daemon=True).start()

    def _on_url_change(self):
        val = self.url_var.get().strip()
        if val:
            p = detect_platform(val)
            self.platform_badge_lbl.config(
                text=f"{p['icon']} {p['name']}",
                bootstyle="info-inverse" if p['id'] != 'generic' else 'secondary-inverse'
            )
        else:
            self.platform_badge_lbl.config(text="🌐 Universal Mode", bootstyle="secondary-inverse")

    def _open_history_dialog(self):
        win = tb.Toplevel(self.root) if HAS_TTKBOOTSTRAP else tk.Toplevel(self.root)
        win.title("Downloads & Recording History")
        win.geometry("750x480")
        if not HAS_TTKBOOTSTRAP:
            win.configure(bg="#1e293b")

        tb.Label(
            win,
            text="📜 Downloads History",
            font=("Segoe UI", 14, "bold"),
            bootstyle="info"
        ).pack(anchor="w", padx=18, pady=(16, 6))

        content_frame = tb.Frame(win, padding=18) if HAS_TTKBOOTSTRAP else tk.Frame(win, padx=18, pady=18, bg="#1e293b")
        content_frame.pack(fill="both", expand=True)

        history = get_history()
        if not history:
            tb.Label(content_frame, text="No downloads recorded yet.", font=("Segoe UI", 10), bootstyle="secondary").pack(pady=40)
        else:
            tree = ttk.Treeview(content_frame, columns=("Title", "Date", "Type"), show="headings", height=12)
            tree.heading("Title", text="Title")
            tree.heading("Date", text="Date")
            tree.heading("Type", text="Type")
            tree.column("Title", width=420)
            tree.column("Date", width=160)
            tree.column("Type", width=80)
            tree.pack(fill="both", expand=True)

            for item in reversed(history[-50:]):
                tree.insert("", "end", values=(item.get("title", "Media"), item.get("date_str", "--"), item.get("type", "video").upper()))

        btn_row = tb.Frame(win, padding=18) if HAS_TTKBOOTSTRAP else tk.Frame(win, padx=18, pady=18, bg="#1e293b")
        btn_row.pack(fill="x")
        tb.Button(btn_row, text="📂 Open Downloads Folder", bootstyle="info", command=self._open_downloads_folder).pack(side="left")
        tb.Button(btn_row, text="Close", bootstyle="secondary", command=win.destroy).pack(side="right")

    def _check_first_run_onboarding(self):
        if not is_environment_ready():
            self._log("[Welcome] Media engines not found. Launching Setup Wizard for 1-click installation...")
            self._open_setup_wizard()

    def _open_setup_wizard(self):
        launch_onboarding_gui(parent=self.root, on_complete=self._check_engine_status_async)

    def _get_quality_code(self) -> str:
        val = self.quality_var.get()
        if "Respect" in val or "yt-dlp.conf" in val or "conf" in val.lower():
            return "conf"
        elif "4K" in val or "Maximum" in val:
            return "max"
        elif "1080p" in val:
            return "1080p"
        elif "720p" in val:
            return "720p"
        elif "MP3" in val:
            return "audio_mp3"
        elif "M4A" in val:
            return "audio_m4a"
        return "best"

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
                self.root.after(0, lambda: self.download_speed_lbl.config(text="Stream sniffed & copied!", bootstyle="success"))
            else:
                self.root.after(0, lambda: self._log("[-] No stream detected on that page."))
                self.root.after(0, lambda: self.download_speed_lbl.config(text="No stream found", bootstyle="warning"))
        threading.Thread(target=_worker, daemon=True).start()

    def _on_download_click(self):
        url = self.url_var.get().strip()
        if not url:
            self._log("[Error] Please enter a URL.")
            return

        q_code = self._get_quality_code()
        is_audio = q_code in ("audio_mp3", "audio_m4a")

        self._log(f"\n[Download] Resolving media info for: {url}")
        self.download_speed_lbl.config(text="Resolving...", bootstyle="info")
        self.progress_bar.configure(value=0)

        def _worker():
            meta = resolve_stream_metadata(url)
            title = meta.get("title")
            uploader = meta.get("uploader")
            is_live = meta.get("is_live", False)
            self.root.after(0, lambda: self._log(f"[Metadata] Title: '{title}'" + (f" | Creator: @{uploader}" if uploader else "") + f" | Live: {is_live}"))
            self.root.after(0, lambda: self._log(f"[Download] Starting yt-dlp download (Profile: {q_code})..."))

            def on_out(line):
                self.root.after(0, lambda l=line: self._log(f"[yt-dlp] {l}"))

            def on_prog(pct, speed, eta):
                if pct is not None:
                    self.root.after(0, lambda p=pct: self.progress_bar.configure(value=p))
                    self.root.after(0, lambda p=pct, s=speed, e=eta: self.download_speed_lbl.config(
                        text=f"⚡ {p:.1f}% • {s} • ETA: {e}",
                        bootstyle="info"
                    ))
                else:
                    self.root.after(0, lambda: self.progress_bar.step(2))
                    self.root.after(0, lambda s=speed, e=eta: self.download_speed_lbl.config(
                        text=f"🔴 LIVE • {s} • {e}",
                        bootstyle="info"
                    ))

            ret = run_ytdlp_download(
                stream_url=url,
                title=title,
                uploader=uploader,
                is_live=is_live,
                audio_only=is_audio,
                quality_preference=q_code,
                on_output=on_out,
                progress_callback=on_prog,
                respect_conf_output=True
            )
            d_dir = get_download_dir()
            if ret == 0:
                self.root.after(0, lambda: self.progress_bar.configure(value=100))
                self.root.after(0, lambda: self.download_speed_lbl.config(text="✅ Download Complete!", bootstyle="success"))
                self.root.after(0, lambda: self._log(f"[Done] Download completed! Target directory: {d_dir}"))
            else:
                self.root.after(0, lambda: self.download_speed_lbl.config(text="❌ Download Failed", bootstyle="danger"))
                self.root.after(0, lambda: self._log("[-] Download process encountered an error."))

        threading.Thread(target=_worker, daemon=True).start()

    def _on_record_click(self):
        url = self.url_var.get().strip()
        if not url:
            self._log("[Error] Please enter a live URL.")
            return

        self._log(f"\n[Record] Resolving stream for live recording: {url}")
        self.download_speed_lbl.config(text="Recording...", bootstyle="danger")

        def _worker():
            meta = resolve_stream_metadata(url)
            title = meta.get("title")
            uploader = meta.get("uploader")
            stream_target = url
            headers = None

            if "tiktok.com" in url:
                m = re.search(r'@([\w.-]+)', url)
                if m:
                    res = resolve_tiktok_live(m.group(1))
                    if res and res.formats:
                        hls = next((f for f in res.formats if f.protocol == "m3u8_native"), res.formats[0])
                        stream_target = hls.url
                        headers = res.http_headers
                        title = res.title
                        uploader = res.uploader

            self.root.after(0, lambda: self._log(f"[Record] Capturing '{title}' by @{uploader or 'stream'} via FFmpeg..."))

            def on_out(line):
                self.root.after(0, lambda l=line: self._log(f"[FFmpeg] {l}"))

            def on_prog(pct, speed, eta):
                self.root.after(0, lambda: self.progress_bar.step(2))
                self.root.after(0, lambda s=speed, e=eta: self.download_speed_lbl.config(
                    text=f"🔴 REC • {s} • {e}",
                    bootstyle="danger"
                ))

            ret = run_ffmpeg_record(
                stream_target,
                headers=headers,
                title=title,
                uploader=uploader,
                on_output=on_out,
                progress_callback=on_prog
            )
            if ret == 0:
                self.root.after(0, lambda: self.download_speed_lbl.config(text="✅ Live Recording Saved!", bootstyle="success"))
                self.root.after(0, lambda: self._log("[Done] Live recording saved to downloads directory!"))
            else:
                self.root.after(0, lambda: self.download_speed_lbl.config(text="Live Recording Stopped", bootstyle="secondary"))

        threading.Thread(target=_worker, daemon=True).start()

    def _on_audio_click(self):
        url = self.url_var.get().strip()
        if not url:
            self._log("[Error] Please enter a URL.")
            return

        self._log(f"\n[Audio] Resolving media info for MP3 extraction: {url}")
        self.download_speed_lbl.config(text="Extracting Audio...", bootstyle="warning")
        self.progress_bar.configure(value=0)

        def _worker():
            meta = resolve_stream_metadata(url)
            title = meta.get("title")
            uploader = meta.get("uploader")
            self.root.after(0, lambda: self._log(f"[Metadata] Title: '{title}'" + (f" | Creator: @{uploader}" if uploader else "")))
            self.root.after(0, lambda: self._log("[Audio] Extracting high-bitrate MP3 audio track..."))

            def on_out(line):
                self.root.after(0, lambda l=line: self._log(f"[yt-dlp] {l}"))

            def on_prog(pct, speed, eta):
                if pct is not None:
                    self.root.after(0, lambda p=pct: self.progress_bar.configure(value=p))
                    self.root.after(0, lambda p=pct, s=speed, e=eta: self.download_speed_lbl.config(
                        text=f"🎵 {p:.1f}% • {s} • ETA: {e}",
                        bootstyle="warning"
                    ))
                else:
                    self.root.after(0, lambda: self.progress_bar.step(2))
                    self.root.after(0, lambda s=speed, e=eta: self.download_speed_lbl.config(
                        text=f"🎵 EXTRACTING • {s} • {e}",
                        bootstyle="warning"
                    ))

            ret = run_ytdlp_download(
                stream_url=url,
                title=title,
                uploader=uploader,
                audio_only=True,
                on_output=on_out,
                progress_callback=on_prog,
                respect_conf_output=True
            )
            d_dir = get_download_dir()
            if ret == 0:
                self.root.after(0, lambda: self.progress_bar.configure(value=100))
                self.root.after(0, lambda: self.download_speed_lbl.config(text="✅ MP3 Saved!", bootstyle="success"))
                self.root.after(0, lambda: self._log(f"[Done] MP3 Audio saved! Target directory: {d_dir}"))
            else:
                self.root.after(0, lambda: self.download_speed_lbl.config(text="❌ Audio Extraction Failed", bootstyle="danger"))

        threading.Thread(target=_worker, daemon=True).start()

    def _on_play_click(self):
        url = self.url_var.get().strip()
        if not url:
            self._log("[Error] Please enter a URL.")
            return

        player = find_player()
        if not player:
            self._log("[Notice] No media player (VLC / MPV) found. Opening setup wizard to install VLC...")
            copy_to_clipboard(url)
            self._open_setup_wizard()
            return

        self._log(f"[Player] Launching {Path(player).name} with {url}...")
        subprocess.Popen([player, url])

    def _open_batch_dialog(self):
        """Opens a modern dark-mode modal dialog to download multiple URLs at once."""
        win = tb.Toplevel(self.root) if HAS_TTKBOOTSTRAP else tk.Toplevel(self.root)
        win.title("Batch URL Downloader")
        win.geometry("640x480")
        if not HAS_TTKBOOTSTRAP:
            win.configure(bg="#1e293b")

        tb.Label(
            win,
            text="📑 Batch URL Downloader",
            font=("Segoe UI", 14, "bold"),
            bootstyle="info"
        ).pack(anchor="w", padx=18, pady=(16, 6))

        tb.Label(
            win,
            text="Paste video, live, or stream URLs below (one per line):",
            font=("Segoe UI", 9),
            bootstyle="secondary"
        ).pack(anchor="w", padx=18, pady=(0, 10))

        txt_frame = tb.Frame(win, padding=18) if HAS_TTKBOOTSTRAP else tk.Frame(win, padx=18, pady=18, bg="#1e293b")
        txt_frame.pack(fill="both", expand=True)

        batch_txt = tb.ScrolledText(txt_frame, height=12, font=("Consolas", 10)) if HAS_TTKBOOTSTRAP else tk.Text(txt_frame, height=12, font=("Consolas", 10), bg="#0f172a", fg="white")
        batch_txt.pack(fill="both", expand=True)

        btn_row = tb.Frame(win, padding=18) if HAS_TTKBOOTSTRAP else tk.Frame(win, padx=18, pady=18, bg="#1e293b")
        btn_row.pack(fill="x")

        def _start_batch():
            raw = batch_txt.get("1.0", "end").strip()
            urls = [u.strip() for u in raw.splitlines() if u.strip() and u.strip().startswith("http")]
            if not urls:
                self._log("[Batch] No valid URLs found in batch input.")
                win.destroy()
                return

            win.destroy()
            self._log(f"\n[Batch] Starting download queue for {len(urls)} URLs...")
            q_code = self._get_quality_code()

            def _batch_worker():
                for idx, u in enumerate(urls, 1):
                    self.root.after(0, lambda i=idx, tot=len(urls), target=u: self._log(f"\n--- [Batch {i}/{tot}] Downloading: {target} ---"))
                    self.root.after(0, lambda i=idx, tot=len(urls): self.download_speed_lbl.config(
                        text=f"Batch {i}/{tot}",
                        bootstyle="info"
                    ))
                    meta = resolve_stream_metadata(u)
                    run_ytdlp_download(
                        stream_url=u,
                        title=meta.get("title"),
                        uploader=meta.get("uploader"),
                        is_live=meta.get("is_live", False),
                        audio_only=q_code in ("audio_mp3", "audio_m4a"),
                        quality_preference=q_code,
                        on_output=lambda l: self.root.after(0, lambda line=l: self._log(f"[Batch] {line}")),
                        respect_conf_output=True
                    )
                self.root.after(0, lambda: self._log("\n[Batch] All queued downloads finished!"))
                self.root.after(0, lambda: self.download_speed_lbl.config(text="Batch Complete!", bootstyle="success"))

            threading.Thread(target=_batch_worker, daemon=True).start()

        start_btn = tb.Button(btn_row, text="🚀 Start Batch Download", bootstyle="success", command=_start_batch) if HAS_TTKBOOTSTRAP else tk.Button(btn_row, text="Start Batch", command=_start_batch)
        start_btn.pack(side="right", padx=(8, 0))

        cancel_btn = tb.Button(btn_row, text="Cancel", bootstyle="secondary", command=win.destroy) if HAS_TTKBOOTSTRAP else tk.Button(btn_row, text="Cancel", command=win.destroy)
        cancel_btn.pack(side="right")

    def run(self):
        self.root.mainloop()


def launch_desktop_gui():
    app = StreamVortexApp()
    app.run()


if __name__ == "__main__":
    launch_desktop_gui()
