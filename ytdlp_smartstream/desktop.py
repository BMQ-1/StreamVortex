"""
StreamVortex Modern Desktop Studio GUI.
Faithfully recreates the modern dark-mode fluent mockup concept with:
- Left sidebar navigation (Downloads, Library/History, Batch Mode, Settings, About)
- Video / Playlist URL bar with Paste & Analyze
- Save Folder selector with drag-and-drop and yt-dlp.conf synchronization
- Format options (Quality, Output container, Subtitles, MP3 audio, Metadata, Thumbnails)
- Real-time Downloads Queue & Status tracker with thumbnails, progress bars, speed, and ETA
- Full integration with yt-dlp, FFmpeg, aria2c, and live streaming
"""

import sys
import os
import re
import time
import json
import shutil
import threading
import subprocess
from pathlib import Path
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
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("streamvortex.studio.app.v1.1")
    except Exception:
        pass

import customtkinter as ctk
from PIL import Image, ImageTk

from .config import get_download_dir, get_config, save_config, get_history, add_history_entry
from .engine import (
    find_ytdlp, find_ffmpeg, find_ytdlp_conf, get_conf_download_dir,
    update_ytdlp_conf_destinations, build_format_args, resolve_stream_metadata,
    run_ytdlp_download, run_ffmpeg_record, check_free_disk_space, detect_platform,
    DOWNLOAD_MANAGER
)
from .onboarding import launch_onboarding_gui, check_environment_status
from .web_ui import launch_web_ui
from .doctor import run_doctor

# Refined high-end dark fluent color palette
COLOR_BG_DARK = "#0d111a"          # Obsidian window background
COLOR_SIDEBAR = "#090c13"          # Sleek sidebar tone
COLOR_SIDEBAR_ACTIVE = "#162035"   # Active nav pill background
COLOR_SIDEBAR_HOVER = "#111726"    # Hover nav pill
COLOR_ACCENT = "#00d2ff"           # Vibrant electric cyan
COLOR_ACCENT_HOVER = "#00b4db"     # Cyan button hover
COLOR_CARD = "#141a27"             # Elevated panel cards
COLOR_CARD_BORDER = "#1f283d"      # Subtle 1px card border
COLOR_CARD_HOVER = "#182133"
COLOR_INPUT_BG = "#0f1420"         # Text input background
COLOR_INPUT_BORDER = "#25304a"     # Input border
COLOR_BTN_SECONDARY = "#1e2638"    # Secondary button
COLOR_BTN_SECONDARY_HOVER = "#2a364e"
COLOR_TEXT_PRIMARY = "#f8fafc"     # Crisp white
COLOR_TEXT_SECONDARY = "#8b9cb5"   # Muted slate subtext
COLOR_SUCCESS = "#10b981"          # Emerald green
COLOR_WARNING = "#f59e0b"          # Amber
COLOR_DANGER = "#ef4444"           # Red / Live badge


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


class StreamVortexApp:
    def __init__(self):
        ctk.set_appearance_mode("Dark")
        ctk.set_default_color_theme("blue")

        self.root = ctk.CTk()
        self.root.title("StreamVortex Studio - Universal yt-dlp & Live Stream Suite v1.1")
        self.root.geometry("1160x760")
        self.root.minsize(1020, 680)
        self.root.configure(fg_color=COLOR_BG_DARK)

        # Set Window and Taskbar Icons
        self._apply_window_icons()

        # Application State
        self.active_tab = "downloads"
        self.analyzed_metadata: Optional[Dict[str, Any]] = None
        self.active_jobs: List[Dict[str, Any]] = []
        self._clip_last = ""
        self.yt_version_str = "Checking..."

        self._load_app_icons()
        self._build_main_layout()
        self._check_system_status_async()
        self._start_clipboard_monitor()

    def _apply_window_icons(self):
        """Sets native Win32 window icons, taskbar identity, and Tk iconphoto."""
        ico_path = get_asset_path("StreamVortex.ico") or get_asset_path("icon.ico")
        if ico_path and sys.platform == "win32":
            try:
                self.root.iconbitmap(default=str(ico_path))
            except Exception:
                try:
                    self.root.iconbitmap(str(ico_path))
                except Exception:
                    pass
            # Native Win32 WM_SETICON for direct HWND taskbar binding
            try:
                import ctypes
                self.root.update_idletasks()
                hwnd = self.root.winfo_id()
                parent_hwnd = ctypes.windll.user32.GetParent(hwnd)
                target_hwnd = parent_hwnd if parent_hwnd else hwnd
                IMAGE_ICON = 1
                LR_LOADFROMFILE = 0x00000010
                h_sm = ctypes.windll.user32.LoadImageW(0, str(ico_path), IMAGE_ICON, 16, 16, LR_LOADFROMFILE)
                h_lg = ctypes.windll.user32.LoadImageW(0, str(ico_path), IMAGE_ICON, 32, 32, LR_LOADFROMFILE)
                WM_SETICON = 0x0080
                if h_sm:
                    ctypes.windll.user32.SendMessageW(target_hwnd, WM_SETICON, 0, h_sm)
                if h_lg:
                    ctypes.windll.user32.SendMessageW(target_hwnd, WM_SETICON, 1, h_lg)
            except Exception:
                pass

        png_path = get_asset_path("icon.png") or get_asset_path("icon_64.png")
        if png_path:
            try:
                raw_img = Image.open(png_path)
                self._photo_icon = ImageTk.PhotoImage(raw_img)
                self.root.iconphoto(True, self._photo_icon)
            except Exception:
                pass

    def _load_app_icons(self):
        """Loads and prepares application graphics and icons."""
        self.img_app_logo = None
        self.img_app_logo_large = None
        icon_path = get_asset_path("icon.png") or get_asset_path("icon_64.png")
        if icon_path:
            try:
                raw_img = Image.open(icon_path)
                self.img_app_logo = ctk.CTkImage(light_image=raw_img, dark_image=raw_img, size=(42, 42))
                self.img_app_logo_large = ctk.CTkImage(light_image=raw_img, dark_image=raw_img, size=(96, 96))
            except Exception:
                pass

    def _build_main_layout(self):
        """Builds the 2-column layout: Left Sidebar + Main Viewport."""
        self.root.grid_rowconfigure(0, weight=1)
        self.root.grid_columnconfigure(1, weight=1)

        # =====================================================================
        # 1. LEFT SIDEBAR
        # =====================================================================
        self.sidebar_frame = ctk.CTkFrame(self.root, width=235, corner_radius=0, fg_color=COLOR_SIDEBAR)
        self.sidebar_frame.grid(row=0, column=0, sticky="nsew")
        self.sidebar_frame.grid_rowconfigure(7, weight=1)

        # Sidebar Header / Brand Logo & Title
        header_frame = ctk.CTkFrame(self.sidebar_frame, fg_color="transparent")
        header_frame.pack(fill="x", padx=16, pady=(20, 22))

        if self.img_app_logo:
            logo_lbl = ctk.CTkLabel(header_frame, image=self.img_app_logo, text="")
            logo_lbl.pack(side="left", padx=(0, 12))

        title_box = ctk.CTkFrame(header_frame, fg_color="transparent")
        title_box.pack(side="left", fill="x", expand=True)

        title_lbl = ctk.CTkLabel(
            title_box,
            text="StreamVortex",
            font=ctk.CTkFont(family="Segoe UI", size=18, weight="bold"),
            text_color=COLOR_TEXT_PRIMARY
        )
        title_lbl.pack(anchor="w")

        sub_badge = ctk.CTkLabel(
            title_box,
            text="STUDIO v1.1",
            font=ctk.CTkFont(family="Segoe UI", size=9, weight="bold"),
            text_color=COLOR_ACCENT
        )
        sub_badge.pack(anchor="w")

        # Sidebar Navigation Buttons
        self.nav_buttons: Dict[str, ctk.CTkButton] = {}
        nav_items = [
            ("downloads", "⬇   Downloads"),
            ("library", "📁   Library (History)"),
            ("batch", "📦   Batch Mode"),
            ("settings", "⚙   Settings & Tools"),
            ("about", "💬   About Studio"),
        ]

        for tab_id, text in nav_items:
            btn = ctk.CTkButton(
                self.sidebar_frame,
                text=text,
                font=ctk.CTkFont(family="Segoe UI", size=13, weight="normal"),
                anchor="w",
                height=42,
                corner_radius=8,
                fg_color="transparent",
                text_color=COLOR_TEXT_SECONDARY,
                hover_color=COLOR_SIDEBAR_HOVER,
                command=lambda t=tab_id: self._switch_tab(t)
            )
            btn.pack(fill="x", padx=12, pady=3)
            self.nav_buttons[tab_id] = btn

        # Quick Switch Section
        quick_sep = ctk.CTkFrame(self.sidebar_frame, height=1, fg_color=COLOR_CARD_BORDER)
        quick_sep.pack(fill="x", padx=16, pady=(16, 12))

        quick_label = ctk.CTkLabel(
            self.sidebar_frame,
            text="QUICK SWITCH",
            font=ctk.CTkFont(family="Segoe UI", size=9, weight="bold"),
            text_color="#53647c",
            anchor="w"
        )
        quick_label.pack(fill="x", padx=16, pady=(0, 6))

        web_studio_btn = ctk.CTkButton(
            self.sidebar_frame,
            text="🌐  Web Studio (Browser)",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            anchor="w",
            height=32,
            corner_radius=6,
            fg_color="transparent",
            hover_color=COLOR_SIDEBAR_HOVER,
            text_color=COLOR_TEXT_SECONDARY,
            command=self._on_open_web_studio
        )
        web_studio_btn.pack(fill="x", padx=12, pady=2)

        doctor_btn = ctk.CTkButton(
            self.sidebar_frame,
            text="🩺  System Diagnostics",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            anchor="w",
            height=32,
            corner_radius=6,
            fg_color="transparent",
            hover_color=COLOR_SIDEBAR_HOVER,
            text_color=COLOR_TEXT_SECONDARY,
            command=self._on_run_doctor
        )
        doctor_btn.pack(fill="x", padx=12, pady=2)

        # Sidebar Footer: Engine version & Health card
        self.sidebar_footer = ctk.CTkFrame(self.sidebar_frame, fg_color=COLOR_CARD, corner_radius=8, border_width=1, border_color=COLOR_CARD_BORDER)
        self.sidebar_footer.pack(side="bottom", fill="x", padx=12, pady=16)

        self.footer_status_pill = ctk.CTkLabel(
            self.sidebar_footer,
            text="🟢  yt-dlp Engine Ready",
            font=ctk.CTkFont(family="Segoe UI", size=10, weight="bold"),
            text_color=COLOR_SUCCESS,
            anchor="w"
        )
        self.footer_status_pill.pack(fill="x", padx=10, pady=(8, 2))

        self.footer_disk_lbl = ctk.CTkLabel(
            self.sidebar_footer,
            text="💾  Disk Free: Checking...",
            font=ctk.CTkFont(family="Segoe UI", size=9),
            text_color=COLOR_TEXT_SECONDARY,
            anchor="w"
        )
        self.footer_disk_lbl.pack(fill="x", padx=10, pady=(0, 8))

        # =====================================================================
        # 2. MAIN CONTENT VIEWPORT
        # =====================================================================
        self.content_container = ctk.CTkFrame(self.root, corner_radius=0, fg_color=COLOR_BG_DARK)
        self.content_container.grid(row=0, column=1, sticky="nsew", padx=22, pady=18)
        self.content_container.grid_rowconfigure(0, weight=1)
        self.content_container.grid_columnconfigure(0, weight=1)

        # Build View Tabs
        self.tabs: Dict[str, ctk.CTkFrame] = {
            "downloads": self._build_downloads_tab(),
            "library": self._build_library_tab(),
            "batch": self._build_batch_tab(),
            "settings": self._build_settings_tab(),
            "about": self._build_about_tab(),
        }

        self._switch_tab("downloads")

    def _switch_tab(self, tab_id: str):
        """Switches the active view in the content container with styling."""
        self.active_tab = tab_id
        for t_id, frame in self.tabs.items():
            if t_id == tab_id:
                frame.grid(row=0, column=0, sticky="nsew")
            else:
                frame.grid_forget()

        # Update sidebar button highlight
        for t_id, btn in self.nav_buttons.items():
            if t_id == tab_id:
                btn.configure(
                    fg_color=COLOR_SIDEBAR_ACTIVE,
                    text_color=COLOR_ACCENT,
                    font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold")
                )
            else:
                btn.configure(
                    fg_color="transparent",
                    text_color=COLOR_TEXT_SECONDARY,
                    font=ctk.CTkFont(family="Segoe UI", size=13, weight="normal")
                )

        if tab_id == "library":
            self._refresh_library_list()

    # =========================================================================
    # TAB 1: DOWNLOADS VIEW (Matching mockup_concept.jpg)
    # =========================================================================
    def _build_downloads_tab(self) -> ctk.CTkFrame:
        parent = ctk.CTkFrame(self.content_container, fg_color="transparent")
        parent.grid_rowconfigure(5, weight=1)
        parent.grid_columnconfigure(0, weight=1)

        # --- SECTION 1: Video / Playlist URL ---
        url_label = ctk.CTkLabel(
            parent,
            text="Video / Playlist URL",
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            text_color=COLOR_TEXT_PRIMARY
        )
        url_label.grid(row=0, column=0, sticky="w", pady=(0, 6))

        url_row = ctk.CTkFrame(parent, fg_color="transparent")
        url_row.grid(row=1, column=0, sticky="ew", pady=(0, 10))
        url_row.grid_columnconfigure(0, weight=1)

        self.url_entry = ctk.CTkEntry(
            url_row,
            placeholder_text="Paste any video or live link (YouTube, TikTok Live, Twitch, Kick, Twitter, Instagram...)",
            font=ctk.CTkFont(family="Segoe UI", size=12),
            height=40,
            corner_radius=8,
            fg_color=COLOR_INPUT_BG,
            border_color=COLOR_INPUT_BORDER,
            text_color=COLOR_TEXT_PRIMARY
        )
        self.url_entry.grid(row=0, column=0, sticky="ew", padx=(0, 10))
        self.url_entry.bind("<Return>", lambda e: self._on_analyze_click())

        self.paste_btn = ctk.CTkButton(
            url_row,
            text="📋  Paste",
            width=85,
            height=40,
            corner_radius=8,
            fg_color=COLOR_BTN_SECONDARY,
            hover_color=COLOR_BTN_SECONDARY_HOVER,
            font=ctk.CTkFont(family="Segoe UI", size=12),
            command=self._on_paste_click
        )
        self.paste_btn.grid(row=0, column=1, padx=(0, 8))

        self.analyze_btn = ctk.CTkButton(
            url_row,
            text="⚡  Analyze",
            width=100,
            height=40,
            corner_radius=8,
            fg_color=COLOR_ACCENT,
            hover_color=COLOR_ACCENT_HOVER,
            text_color="#000000",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            command=self._on_analyze_click
        )
        self.analyze_btn.grid(row=0, column=2)

        # Dynamic Video / Stream Preview Card (Appears when analyzed)
        self.preview_card = ctk.CTkFrame(parent, fg_color=COLOR_CARD, corner_radius=8, border_width=1, border_color=COLOR_CARD_BORDER)
        self.preview_card.grid(row=2, column=0, sticky="ew", pady=(0, 10))
        self.preview_card.grid_columnconfigure(1, weight=1)
        self.preview_card.grid_remove()  # Hidden until analyzed

        self.prev_icon_lbl = ctk.CTkLabel(self.preview_card, text="🎬", font=ctk.CTkFont(size=24), width=44)
        self.prev_icon_lbl.grid(row=0, column=0, rowspan=2, padx=12, pady=10)

        self.prev_title_lbl = ctk.CTkLabel(
            self.preview_card,
            text="Stream Title",
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            text_color=COLOR_TEXT_PRIMARY,
            anchor="w"
        )
        self.prev_title_lbl.grid(row=0, column=1, sticky="w", pady=(8, 2))

        self.prev_meta_lbl = ctk.CTkLabel(
            self.preview_card,
            text="Author • Resolution • Format",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            text_color=COLOR_TEXT_SECONDARY,
            anchor="w"
        )
        self.prev_meta_lbl.grid(row=1, column=1, sticky="w", pady=(0, 8))

        self.prev_badge_lbl = ctk.CTkLabel(
            self.preview_card,
            text="READY",
            font=ctk.CTkFont(family="Segoe UI", size=10, weight="bold"),
            text_color=COLOR_SUCCESS,
            width=70
        )
        self.prev_badge_lbl.grid(row=0, column=2, rowspan=2, padx=14)

        # --- SECTION 2: Save Folder ---
        save_label = ctk.CTkLabel(
            parent,
            text="Save Folder",
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            text_color=COLOR_TEXT_PRIMARY
        )
        save_label.grid(row=3, column=0, sticky="w", pady=(0, 6))

        save_row = ctk.CTkFrame(parent, fg_color="transparent")
        save_row.grid(row=4, column=0, sticky="ew", pady=(0, 14))
        save_row.grid_columnconfigure(0, weight=1)

        initial_folder = str(get_conf_download_dir())
        self.folder_entry = ctk.CTkEntry(
            save_row,
            font=ctk.CTkFont(family="Segoe UI", size=12),
            height=38,
            corner_radius=8,
            fg_color=COLOR_INPUT_BG,
            border_color=COLOR_INPUT_BORDER,
            text_color=COLOR_TEXT_PRIMARY
        )
        self.folder_entry.insert(0, initial_folder)
        self.folder_entry.grid(row=0, column=0, sticky="ew", padx=(0, 10))
        self.folder_entry.bind("<FocusOut>", lambda e: self._on_folder_change())
        self.folder_entry.bind("<Return>", lambda e: self._on_folder_change())

        self.browse_btn = ctk.CTkButton(
            save_row,
            text="Browse...",
            width=85,
            height=38,
            corner_radius=8,
            fg_color=COLOR_BTN_SECONDARY,
            hover_color=COLOR_BTN_SECONDARY_HOVER,
            font=ctk.CTkFont(family="Segoe UI", size=12),
            command=self._on_browse_folder_click
        )
        self.browse_btn.grid(row=0, column=1, padx=(0, 8))

        self.open_cur_folder_btn = ctk.CTkButton(
            save_row,
            text="↗  Open",
            width=75,
            height=38,
            corner_radius=8,
            fg_color=COLOR_BTN_SECONDARY,
            hover_color=COLOR_BTN_SECONDARY_HOVER,
            font=ctk.CTkFont(family="Segoe UI", size=12),
            command=self._on_open_downloads_folder
        )
        self.open_cur_folder_btn.grid(row=0, column=2)

        # --- SECTION 3: Format Options Panel ---
        fmt_card = ctk.CTkFrame(parent, fg_color=COLOR_CARD, corner_radius=10, border_width=1, border_color=COLOR_CARD_BORDER)
        fmt_card.grid(row=5, column=0, sticky="ew", pady=(0, 14), padx=0)
        fmt_card.grid_columnconfigure(0, weight=1)
        fmt_card.grid_columnconfigure(1, weight=1)

        fmt_label = ctk.CTkLabel(
            fmt_card,
            text="Format Options",
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            text_color=COLOR_TEXT_PRIMARY
        )
        fmt_label.grid(row=0, column=0, columnspan=2, sticky="w", padx=14, pady=(10, 8))

        # Dropdowns (Left Column)
        left_opts = ctk.CTkFrame(fmt_card, fg_color="transparent")
        left_opts.grid(row=1, column=0, sticky="nsew", padx=14, pady=(0, 10))
        left_opts.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(left_opts, text="Video Quality", font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"), text_color=COLOR_TEXT_SECONDARY).grid(row=0, column=0, sticky="w", padx=(0, 10), pady=6)
        self.quality_menu = ctk.CTkOptionMenu(
            left_opts,
            values=[
                "Best Quality (Video + Audio)",
                "Universal MP4 (1080p)",
                "Fast (720p)",
                "Data Saver (480p)",
                "Respect yt-dlp.conf",
            ],
            fg_color=COLOR_BTN_SECONDARY,
            button_color=COLOR_BTN_SECONDARY_HOVER,
            button_hover_color=COLOR_ACCENT,
            dropdown_fg_color=COLOR_CARD,
            font=ctk.CTkFont(family="Segoe UI", size=11),
            height=32
        )
        self.quality_menu.set("Best Quality (Video + Audio)")
        self.quality_menu.grid(row=0, column=1, sticky="ew", pady=6)

        ctk.CTkLabel(left_opts, text="Output Format", font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"), text_color=COLOR_TEXT_SECONDARY).grid(row=1, column=0, sticky="w", padx=(0, 10), pady=6)
        self.container_menu = ctk.CTkOptionMenu(
            left_opts,
            values=["MP4", "MKV", "WebM", "Auto"],
            fg_color=COLOR_BTN_SECONDARY,
            button_color=COLOR_BTN_SECONDARY_HOVER,
            button_hover_color=COLOR_ACCENT,
            dropdown_fg_color=COLOR_CARD,
            font=ctk.CTkFont(family="Segoe UI", size=11),
            height=32
        )
        self.container_menu.set("MP4")
        self.container_menu.grid(row=1, column=1, sticky="ew", pady=6)

        # Checkboxes (Right Column)
        right_opts = ctk.CTkFrame(fmt_card, fg_color="transparent")
        right_opts.grid(row=1, column=1, sticky="nsew", padx=14, pady=(0, 10))

        self.chk_subtitles = ctk.CTkCheckBox(right_opts, text="Download Subtitles", font=ctk.CTkFont(family="Segoe UI", size=11), fg_color=COLOR_ACCENT, hover_color=COLOR_ACCENT_HOVER, checkmark_color="#000")
        self.chk_subtitles.select()
        self.chk_subtitles.grid(row=0, column=0, sticky="w", pady=6)

        self.chk_audio_only = ctk.CTkCheckBox(right_opts, text="Convert to Audio (MP3)", font=ctk.CTkFont(family="Segoe UI", size=11), fg_color=COLOR_ACCENT, hover_color=COLOR_ACCENT_HOVER, checkmark_color="#000", command=self._on_mp3_toggle)
        self.chk_audio_only.grid(row=0, column=1, sticky="w", padx=14, pady=6)

        self.chk_metadata = ctk.CTkCheckBox(right_opts, text="Embed Metadata", font=ctk.CTkFont(family="Segoe UI", size=11), fg_color=COLOR_ACCENT, hover_color=COLOR_ACCENT_HOVER, checkmark_color="#000")
        self.chk_metadata.select()
        self.chk_metadata.grid(row=1, column=0, sticky="w", pady=6)

        self.chk_thumbnail = ctk.CTkCheckBox(right_opts, text="Download Thumbnail", font=ctk.CTkFont(family="Segoe UI", size=11), fg_color=COLOR_ACCENT, hover_color=COLOR_ACCENT_HOVER, checkmark_color="#000")
        self.chk_thumbnail.select()
        self.chk_thumbnail.grid(row=1, column=1, sticky="w", padx=14, pady=6)

        # --- SECTION 4: Downloads Queue / Status Table ---
        queue_header_row = ctk.CTkFrame(parent, fg_color="transparent")
        queue_header_row.grid(row=6, column=0, sticky="ew", pady=(0, 4))
        queue_header_row.grid_columnconfigure(0, weight=1)

        queue_title = ctk.CTkLabel(
            queue_header_row,
            text="Downloads Queue / Status",
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            text_color=COLOR_TEXT_PRIMARY
        )
        queue_title.grid(row=0, column=0, sticky="w")

        # Table Column Headers
        col_headers = ctk.CTkFrame(parent, fg_color="#0a0d14", height=28, corner_radius=6)
        col_headers.grid(row=7, column=0, sticky="ew", pady=(0, 6))
        col_headers.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(col_headers, text="  Status", font=ctk.CTkFont(family="Segoe UI", size=10, weight="bold"), text_color=COLOR_TEXT_SECONDARY, width=65).grid(row=0, column=0, padx=6)
        ctk.CTkLabel(col_headers, text="Title & Channel", font=ctk.CTkFont(family="Segoe UI", size=10, weight="bold"), text_color=COLOR_TEXT_SECONDARY, anchor="w").grid(row=0, column=1, padx=6, sticky="w")
        ctk.CTkLabel(col_headers, text="Progress", font=ctk.CTkFont(family="Segoe UI", size=10, weight="bold"), text_color=COLOR_TEXT_SECONDARY, width=140).grid(row=0, column=2, padx=6)
        ctk.CTkLabel(col_headers, text="File Size", font=ctk.CTkFont(family="Segoe UI", size=10, weight="bold"), text_color=COLOR_TEXT_SECONDARY, width=110).grid(row=0, column=3, padx=6)
        ctk.CTkLabel(col_headers, text="Speed", font=ctk.CTkFont(family="Segoe UI", size=10, weight="bold"), text_color=COLOR_TEXT_SECONDARY, width=90).grid(row=0, column=4, padx=6)
        ctk.CTkLabel(col_headers, text="ETA", font=ctk.CTkFont(family="Segoe UI", size=10, weight="bold"), text_color=COLOR_TEXT_SECONDARY, width=80).grid(row=0, column=5, padx=6)
        ctk.CTkLabel(col_headers, text="Actions", font=ctk.CTkFont(family="Segoe UI", size=10, weight="bold"), text_color=COLOR_TEXT_SECONDARY, width=100).grid(row=0, column=6, padx=6)

        # Scrollable Queue List
        self.queue_scroll = ctk.CTkScrollableFrame(
            parent,
            fg_color=COLOR_CARD,
            corner_radius=8,
            border_width=1,
            border_color=COLOR_CARD_BORDER
        )
        self.queue_scroll.grid(row=8, column=0, sticky="nsew", pady=(0, 10))
        self.queue_scroll.grid_columnconfigure(1, weight=1)

        # Empty state placeholder
        self.queue_empty_lbl = ctk.CTkLabel(
            self.queue_scroll,
            text="No active downloads. Paste a video or stream URL above and click 'START DOWNLOAD'.",
            font=ctk.CTkFont(family="Segoe UI", size=12),
            text_color=COLOR_TEXT_SECONDARY
        )
        self.queue_empty_lbl.pack(pady=32)

        # --- SECTION 5: Bottom Action Bar & Status Footer ---
        bottom_bar = ctk.CTkFrame(parent, fg_color="transparent")
        bottom_bar.grid(row=9, column=0, sticky="ew", pady=(0, 2))
        bottom_bar.grid_columnconfigure(0, weight=1)

        self.status_msg_lbl = ctk.CTkLabel(
            bottom_bar,
            text="Ready • Standalone Engine loaded",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            text_color=COLOR_TEXT_SECONDARY,
            anchor="w"
        )
        self.status_msg_lbl.grid(row=0, column=0, sticky="w")

        self.start_download_btn = ctk.CTkButton(
            bottom_bar,
            text="⬇   START DOWNLOAD",
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            height=44,
            width=220,
            corner_radius=8,
            fg_color=COLOR_ACCENT,
            hover_color=COLOR_ACCENT_HOVER,
            text_color="#000000",
            command=self._on_start_download_click
        )
        self.start_download_btn.grid(row=0, column=1, sticky="e")

        # Bottom Overall Throughput Footer
        footer_strip = ctk.CTkFrame(parent, fg_color="transparent")
        footer_strip.grid(row=10, column=0, sticky="ew", pady=(2, 0))
        footer_strip.grid_columnconfigure(0, weight=1)

        self.overall_speed_lbl = ctk.CTkLabel(
            footer_strip,
            text="Active Speed: -- • Remaining ETA: --",
            font=ctk.CTkFont(family="Consolas", size=10),
            text_color=COLOR_TEXT_SECONDARY,
            anchor="e"
        )
        self.overall_speed_lbl.grid(row=0, column=1, sticky="e")

        return parent

    # =========================================================================
    # TAB 2: LIBRARY / HISTORY
    # =========================================================================
    def _build_library_tab(self) -> ctk.CTkFrame:
        parent = ctk.CTkFrame(self.content_container, fg_color="transparent")
        parent.grid_rowconfigure(2, weight=1)
        parent.grid_columnconfigure(0, weight=1)

        # Top Bar
        top_bar = ctk.CTkFrame(parent, fg_color="transparent")
        top_bar.grid(row=0, column=0, sticky="ew", pady=(0, 12))
        top_bar.grid_columnconfigure(1, weight=1)

        title = ctk.CTkLabel(
            top_bar,
            text="📁 Downloaded Library & Recordings",
            font=ctk.CTkFont(family="Segoe UI", size=16, weight="bold"),
            text_color=COLOR_TEXT_PRIMARY
        )
        title.grid(row=0, column=0, sticky="w", padx=(0, 16))

        open_folder_btn = ctk.CTkButton(
            top_bar,
            text="📂 Open Downloads Folder",
            height=34,
            corner_radius=6,
            fg_color=COLOR_BTN_SECONDARY,
            hover_color=COLOR_BTN_SECONDARY_HOVER,
            command=self._on_open_downloads_folder
        )
        open_folder_btn.grid(row=0, column=2, sticky="e")

        # Search Bar
        self.lib_search_entry = ctk.CTkEntry(
            parent,
            placeholder_text="🔍 Search library by title or link...",
            height=36,
            corner_radius=8,
            fg_color=COLOR_INPUT_BG,
            border_color=COLOR_INPUT_BORDER
        )
        self.lib_search_entry.grid(row=1, column=0, sticky="ew", pady=(0, 12))
        self.lib_search_entry.bind("<KeyRelease>", lambda e: self._refresh_library_list())

        # History Scroll Area
        self.library_scroll = ctk.CTkScrollableFrame(
            parent,
            fg_color=COLOR_CARD,
            corner_radius=8,
            border_width=1,
            border_color=COLOR_CARD_BORDER
        )
        self.library_scroll.grid(row=2, column=0, sticky="nsew")
        self.library_scroll.grid_columnconfigure(1, weight=1)

        return parent

    def _refresh_library_list(self):
        """Populates the history list with interactive cards."""
        for w in self.library_scroll.winfo_children():
            w.destroy()

        history = get_history()
        query = self.lib_search_entry.get().strip().lower() if hasattr(self, "lib_search_entry") else ""
        filtered = [h for h in history if not query or query in h.get("title", "").lower() or query in h.get("stream_url", "").lower()]

        if not filtered:
            empty = ctk.CTkLabel(
                self.library_scroll,
                text="No downloaded items found." if not query else f"No items matching '{query}'.",
                font=ctk.CTkFont(family="Segoe UI", size=12),
                text_color=COLOR_TEXT_SECONDARY
            )
            empty.pack(pady=40)
            return

        for idx, item in enumerate(reversed(filtered)):
            card = ctk.CTkFrame(self.library_scroll, fg_color=COLOR_INPUT_BG, corner_radius=6)
            card.pack(fill="x", padx=6, pady=4)
            card.grid_columnconfigure(1, weight=1)

            # Icon
            is_audio = item.get("media_type") == "audio"
            icon_text = "🎵" if is_audio else ("🔴" if "live" in item.get("media_type", "") else "🎬")
            ctk.CTkLabel(card, text=icon_text, font=ctk.CTkFont(size=18), width=36).grid(row=0, column=0, rowspan=2, padx=10, pady=8)

            # Title & Meta
            title_txt = item.get("title") or "Downloaded Media"
            ctk.CTkLabel(
                card,
                text=title_txt,
                font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
                text_color=COLOR_TEXT_PRIMARY,
                anchor="w"
            ).grid(row=0, column=1, sticky="w", pady=(8, 2))

            meta_txt = f"{item.get('media_type', 'video').upper()} • {item.get('timestamp', '')[:16]} • {item.get('filename', '')}"
            ctk.CTkLabel(
                card,
                text=meta_txt,
                font=ctk.CTkFont(family="Segoe UI", size=10),
                text_color=COLOR_TEXT_SECONDARY,
                anchor="w"
            ).grid(row=1, column=1, sticky="w", pady=(0, 8))

            # Action Buttons
            btn_box = ctk.CTkFrame(card, fg_color="transparent")
            btn_box.grid(row=0, column=2, rowspan=2, padx=10)

            fpath = item.get("filename")
            if fpath and Path(fpath).exists():
                play_btn = ctk.CTkButton(
                    btn_box,
                    text="▶ Play",
                    width=60,
                    height=28,
                    corner_radius=6,
                    fg_color=COLOR_ACCENT,
                    hover_color=COLOR_ACCENT_HOVER,
                    text_color="#000",
                    font=ctk.CTkFont(size=11, weight="bold"),
                    command=lambda p=fpath: self._play_file(p)
                )
                play_btn.pack(side="left", padx=4)

            open_btn = ctk.CTkButton(
                btn_box,
                text="📁 Open",
                width=60,
                height=28,
                corner_radius=6,
                fg_color=COLOR_BTN_SECONDARY,
                hover_color=COLOR_BTN_SECONDARY_HOVER,
                font=ctk.CTkFont(size=11),
                command=lambda p=fpath: self._open_file_in_folder(p)
            )
            open_btn.pack(side="left", padx=4)

    # =========================================================================
    # TAB 3: BATCH MODE
    # =========================================================================
    def _build_batch_tab(self) -> ctk.CTkFrame:
        parent = ctk.CTkFrame(self.content_container, fg_color="transparent")
        parent.grid_rowconfigure(2, weight=1)
        parent.grid_columnconfigure(0, weight=1)

        title = ctk.CTkLabel(
            parent,
            text="📦 Batch URL Downloader",
            font=ctk.CTkFont(family="Segoe UI", size=16, weight="bold"),
            text_color=COLOR_TEXT_PRIMARY
        )
        title.grid(row=0, column=0, sticky="w", pady=(0, 6))

        desc = ctk.CTkLabel(
            parent,
            text="Paste multiple video, stream, or audio URLs (one URL per line) to queue and download them sequentially.",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            text_color=COLOR_TEXT_SECONDARY
        )
        desc.grid(row=1, column=0, sticky="w", pady=(0, 10))

        self.batch_textbox = ctk.CTkTextbox(
            parent,
            font=ctk.CTkFont(family="Consolas", size=11),
            fg_color=COLOR_CARD,
            border_width=1,
            border_color=COLOR_CARD_BORDER
        )
        self.batch_textbox.grid(row=2, column=0, sticky="nsew", pady=(0, 14))

        # Bottom Batch Actions
        b_bar = ctk.CTkFrame(parent, fg_color="transparent")
        b_bar.grid(row=3, column=0, sticky="ew")
        b_bar.grid_columnconfigure(0, weight=1)

        self.batch_status_lbl = ctk.CTkLabel(
            b_bar,
            text="Ready to queue links.",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            text_color=COLOR_TEXT_SECONDARY
        )
        self.batch_status_lbl.grid(row=0, column=0, sticky="w")

        add_batch_btn = ctk.CTkButton(
            b_bar,
            text="⬇   Add All to Downloads Queue",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            height=40,
            width=230,
            corner_radius=8,
            fg_color=COLOR_ACCENT,
            hover_color=COLOR_ACCENT_HOVER,
            text_color="#000",
            command=self._on_queue_batch_click
        )
        add_batch_btn.grid(row=0, column=1, sticky="e")

        return parent

    # =========================================================================
    # TAB 4: SETTINGS & TOOLS
    # =========================================================================
    def _build_settings_tab(self) -> ctk.CTkFrame:
        parent = ctk.CTkFrame(self.content_container, fg_color="transparent")
        parent.grid_columnconfigure(0, weight=1)

        title = ctk.CTkLabel(
            parent,
            text="⚙ Settings & Toolchain Orchestration",
            font=ctk.CTkFont(family="Segoe UI", size=16, weight="bold"),
            text_color=COLOR_TEXT_PRIMARY
        )
        title.pack(anchor="w", pady=(0, 16))

        # Card 1: 1-Click Automated Setup Wizard
        card_setup = ctk.CTkFrame(parent, fg_color=COLOR_CARD, corner_radius=10, border_width=1, border_color=COLOR_CARD_BORDER)
        card_setup.pack(fill="x", pady=(0, 14))
        card_setup.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            card_setup,
            text="⚡ 1-Click Automated Tools Setup",
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            text_color=COLOR_TEXT_PRIMARY
        ).grid(row=0, column=0, sticky="w", padx=14, pady=(12, 4))

        ctk.CTkLabel(
            card_setup,
            text="Installs and configures official yt-dlp, FFmpeg, and optimized configuration into C:\\Tools automatically.",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            text_color=COLOR_TEXT_SECONDARY
        ).grid(row=1, column=0, sticky="w", padx=14, pady=(0, 12))

        setup_btn = ctk.CTkButton(
            card_setup,
            text="Run 1-Click Setup Wizard",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            height=34,
            corner_radius=6,
            fg_color=COLOR_SUCCESS,
            hover_color="#059669",
            command=self._on_launch_setup_wizard
        )
        setup_btn.grid(row=0, column=1, rowspan=2, padx=14, pady=12, sticky="e")

        # Card 2: yt-dlp.conf Configuration
        card_conf = ctk.CTkFrame(parent, fg_color=COLOR_CARD, corner_radius=10, border_width=1, border_color=COLOR_CARD_BORDER)
        card_conf.pack(fill="x", pady=(0, 14))
        card_conf.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            card_conf,
            text="📄 Global Configuration (yt-dlp.conf)",
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            text_color=COLOR_TEXT_PRIMARY
        ).grid(row=0, column=0, sticky="w", padx=14, pady=(12, 4))

        active_conf = find_ytdlp_conf()
        conf_str = str(active_conf) if active_conf else "No custom .conf found (Using StreamVortex Embedded Engine)"
        self.conf_path_lbl = ctk.CTkLabel(
            card_conf,
            text=f"Active Path: {conf_str}",
            font=ctk.CTkFont(family="Consolas", size=10),
            text_color=COLOR_TEXT_SECONDARY
        )
        self.conf_path_lbl.grid(row=1, column=0, sticky="w", padx=14, pady=(0, 12))

        open_conf_btn = ctk.CTkButton(
            card_conf,
            text="Open in Notepad",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            height=34,
            corner_radius=6,
            fg_color=COLOR_BTN_SECONDARY,
            hover_color=COLOR_BTN_SECONDARY_HOVER,
            command=self._on_open_conf_file
        )
        open_conf_btn.grid(row=0, column=1, rowspan=2, padx=14, pady=12, sticky="e")

        # Card 3: System Diagnostics & Web Studio
        card_diag = ctk.CTkFrame(parent, fg_color=COLOR_CARD, corner_radius=10, border_width=1, border_color=COLOR_CARD_BORDER)
        card_diag.pack(fill="x", pady=(0, 14))
        card_diag.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            card_diag,
            text="🩺 Diagnostics & Alternative Studios",
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            text_color=COLOR_TEXT_PRIMARY
        ).grid(row=0, column=0, sticky="w", padx=14, pady=(12, 4))

        ctk.CTkLabel(
            card_diag,
            text="Run comprehensive diagnostic health check or launch the Browser-based Web Studio.",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            text_color=COLOR_TEXT_SECONDARY
        ).grid(row=1, column=0, sticky="w", padx=14, pady=(0, 12))

        btn_group = ctk.CTkFrame(card_diag, fg_color="transparent")
        btn_group.grid(row=0, column=1, rowspan=2, padx=14, pady=12, sticky="e")

        doc_btn = ctk.CTkButton(
            btn_group,
            text="Run Doctor Check",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            height=34,
            corner_radius=6,
            fg_color=COLOR_BTN_SECONDARY,
            hover_color=COLOR_BTN_SECONDARY_HOVER,
            command=self._on_run_doctor
        )
        doc_btn.pack(side="left", padx=4)

        web_btn = ctk.CTkButton(
            btn_group,
            text="🌐 Open Web Studio",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            height=34,
            corner_radius=6,
            fg_color=COLOR_BTN_SECONDARY,
            hover_color=COLOR_BTN_SECONDARY_HOVER,
            command=self._on_open_web_studio
        )
        web_btn.pack(side="left", padx=4)

        return parent

    # =========================================================================
    # TAB 5: ABOUT VIEW
    # =========================================================================
    def _build_about_tab(self) -> ctk.CTkFrame:
        parent = ctk.CTkFrame(self.content_container, fg_color="transparent")
        parent.pack_propagate(False)

        card = ctk.CTkFrame(parent, fg_color=COLOR_CARD, corner_radius=12, border_width=1, border_color=COLOR_CARD_BORDER)
        card.pack(fill="both", expand=True, padx=20, pady=20)

        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.place(relx=0.5, rely=0.5, anchor="center")

        if hasattr(self, "img_app_logo_large") and self.img_app_logo_large:
            logo_l = ctk.CTkLabel(inner, image=self.img_app_logo_large, text="")
            logo_l.pack(pady=(0, 14))

        app_title = ctk.CTkLabel(
            inner,
            text="StreamVortex",
            font=ctk.CTkFont(family="Segoe UI", size=24, weight="bold"),
            text_color=COLOR_TEXT_PRIMARY
        )
        app_title.pack()

        app_sub = ctk.CTkLabel(
            inner,
            text="v1.1 // Standalone Desktop Studio Edition",
            font=ctk.CTkFont(family="Segoe UI", size=12),
            text_color=COLOR_ACCENT
        )
        app_sub.pack(pady=(2, 12))

        app_desc = ctk.CTkLabel(
            inner,
            text=(
                "Resilient HLS/DASH/VOD stream intelligence & live watchdog engine powered by yt-dlp.\n"
                "Features smart quality overrides (unconstrained 4K/2K), zero-setup auto-deployed .conf,\n"
                "fault-tolerant live recording with FFmpeg +faststart, and broken file auto-cleaning."
            ),
            font=ctk.CTkFont(family="Segoe UI", size=11),
            text_color=COLOR_TEXT_SECONDARY,
            justify="center"
        )
        app_desc.pack(pady=(0, 18))

        github_btn = ctk.CTkButton(
            inner,
            text="⭐ GitHub: BMQ-1 / StreamVortex",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            height=36,
            corner_radius=8,
            fg_color=COLOR_BTN_SECONDARY,
            hover_color=COLOR_BTN_SECONDARY_HOVER,
            command=lambda: os.system("start https://github.com/BMQ-1/StreamVortex") if sys.platform == "win32" else None
        )
        github_btn.pack()

        return parent

    # =========================================================================
    # CORE USER ACTIONS & INTERACTIONS
    # =========================================================================
    def _on_paste_click(self):
        """Pastes URL from clipboard and triggers auto-analysis."""
        try:
            txt = self.root.clipboard_get().strip()
            if txt:
                self.url_entry.delete(0, "end")
                self.url_entry.insert(0, txt)
                self._on_analyze_click()
        except Exception:
            pass

    def _on_browse_folder_click(self):
        """Opens folder dialog and persists selection to yt-dlp.conf."""
        from tkinter import filedialog
        cur_dir = self.folder_entry.get().strip()
        chosen = filedialog.askdirectory(initialdir=cur_dir, title="Select Download Destination Folder")
        if chosen:
            self.folder_entry.delete(0, "end")
            self.folder_entry.insert(0, chosen)
            self._on_folder_change()

    def _on_folder_change(self):
        """Saves folder change to yt-dlp.conf and config.json."""
        target = self.folder_entry.get().strip()
        if target:
            p = Path(target)
            if p.exists():
                ok, msg = update_ytdlp_conf_destinations(p)
                if ok:
                    self.status_msg_lbl.configure(text=f"✓ Destination saved: {p}", text_color=COLOR_SUCCESS)
                    self._update_disk_space_display(p)
                else:
                    self.status_msg_lbl.configure(text=f"Error saving conf: {msg}", text_color=COLOR_DANGER)

    def _on_open_downloads_folder(self):
        """Opens current download directory in Explorer."""
        target = self.folder_entry.get().strip() or str(get_conf_download_dir())
        p = Path(target)
        if p.exists():
            if sys.platform == "win32":
                os.startfile(str(p))
            else:
                subprocess.run(["xdg-open", str(p)])

    def _on_mp3_toggle(self):
        """When MP3 toggle is checked, adjusts format selection."""
        if self.chk_audio_only.get():
            self.container_menu.set("MP3")
        else:
            self.container_menu.set("MP4")

    def _on_analyze_click(self):
        """Analyzes entered URL in background and prepares preview card."""
        url = self.url_entry.get().strip()
        if not url:
            self.status_msg_lbl.configure(text="Please enter a stream or video URL.", text_color=COLOR_WARNING)
            return

        self.status_msg_lbl.configure(text="🔍 Analyzing stream metadata with yt-dlp...", text_color=COLOR_ACCENT)
        self.analyze_btn.configure(state="disabled", text="Analyzing...")

        def _worker():
            meta = resolve_stream_metadata(url)
            self.analyzed_metadata = meta
            title = meta.get("title") or "Media Stream"
            uploader = meta.get("uploader") or "Unknown Creator"
            is_live = meta.get("is_live", False)
            duration_sec = meta.get("duration", 0)

            dur_str = f"{int(duration_sec // 60)}:{int(duration_sec % 60):02d}" if duration_sec else "Live / Stream"

            def _update_ui():
                self.analyze_btn.configure(state="normal", text="⚡  Analyze")
                self.preview_card.grid()  # Show card
                self.prev_icon_lbl.configure(text="🔴" if is_live else "🎬")
                self.prev_title_lbl.configure(text=title if len(title) <= 65 else f"{title[:62]}...")
                self.prev_meta_lbl.configure(text=f"@{uploader} • Duration: {dur_str} • Auto-Detected Best Format")
                self.prev_badge_lbl.configure(
                    text="LIVE NOW" if is_live else "READY",
                    text_color=COLOR_DANGER if is_live else COLOR_SUCCESS
                )
                self.status_msg_lbl.configure(
                    text=f"✓ Ready: '{title}' by @{uploader}",
                    text_color=COLOR_SUCCESS
                )

            self.root.after(0, _update_ui)

        threading.Thread(target=_worker, daemon=True).start()

    def _on_start_download_click(self):
        """Starts downloading the analyzed or entered URL."""
        url = self.url_entry.get().strip()
        if not url:
            self.status_msg_lbl.configure(text="Please enter a valid URL.", text_color=COLOR_WARNING)
            return

        job_id = f"job-{int(time.time() * 1000)}"
        meta = self.analyzed_metadata or resolve_stream_metadata(url)
        title = meta.get("title") or "Media Download"
        uploader = meta.get("uploader") or ""
        is_live = meta.get("is_live", False)
        is_audio = bool(self.chk_audio_only.get())

        # Quality preference mapping
        q_choice = self.quality_menu.get()
        if "Best" in q_choice:
            q_code = "max"
        elif "1080p" in q_choice:
            q_code = "1080p"
        elif "720p" in q_choice:
            q_code = "720p"
        elif "480p" in q_choice:
            q_code = "480p"
        else:
            q_code = "conf"

        if is_audio:
            q_code = "audio_mp3"

        row = self._add_or_update_queue_row(
            job_id=job_id,
            title=title,
            uploader=uploader,
            url=url,
            is_live=is_live,
            status="Starting...",
            progress_pct=0.0
        )

        self.status_msg_lbl.configure(text=f"⬇ Downloading '{title}'...", text_color=COLOR_ACCENT)

        def _worker():
            def on_prog(pct, speed, eta):
                def _ui():
                    status_text = "🔴 RECORDING" if (is_live and pct is None) else "Downloading"
                    prog_val = 0.5 if pct is None else (pct / 100.0)
                    row["progress_bar"].set(prog_val)
                    pct_str = "--" if pct is None else f"{pct:.1f}%"
                    row["progress_lbl"].configure(text=pct_str)
                    row["speed_lbl"].configure(text=speed or "--")
                    row["eta_lbl"].configure(text=f"{eta}" if eta else "--")
                    self.overall_speed_lbl.configure(text=f"Active Speed: {speed or '--'} • Remaining ETA: {eta or '--'}")
                self.root.after(0, _ui)

            ret = run_ytdlp_download(
                stream_url=url,
                title=title,
                uploader=uploader,
                is_live=is_live,
                audio_only=is_audio,
                quality_preference=q_code,
                progress_callback=on_prog,
                respect_conf_output=True
            )

            def _finish():
                if ret == 0:
                    row["progress_bar"].set(1.0)
                    row["progress_lbl"].configure(text="100%", text_color=COLOR_SUCCESS)
                    row["status_badge"].configure(text="DONE", text_color=COLOR_SUCCESS)
                    row["speed_lbl"].configure(text="Complete")
                    row["eta_lbl"].configure(text="--")
                    if "play_btn" in row:
                        row["play_btn"].configure(state="normal")
                    if "open_btn" in row:
                        row["open_btn"].configure(state="normal")
                    self.status_msg_lbl.configure(text=f"✅ Finished: '{title}' saved to {get_conf_download_dir()}", text_color=COLOR_SUCCESS)
                else:
                    row["status_badge"].configure(text="FAILED", text_color=COLOR_DANGER)
                    self.status_msg_lbl.configure(text=f"❌ Download failed for '{title}'.", text_color=COLOR_DANGER)
                self.overall_speed_lbl.configure(text="Active Speed: -- • Remaining ETA: --")

            self.root.after(0, _finish)

        threading.Thread(target=_worker, daemon=True).start()

    def _on_queue_batch_click(self):
        """Processes all URLs in the Batch text box."""
        raw = self.batch_textbox.get("1.0", "end").strip()
        urls = [u.strip() for u in raw.splitlines() if u.strip() and u.strip().startswith("http")]
        if not urls:
            self.batch_status_lbl.configure(text="No valid URLs found in input.", text_color=COLOR_WARNING)
            return

        self.batch_status_lbl.configure(text=f"Queuing {len(urls)} items into Downloads...", text_color=COLOR_ACCENT)
        self._switch_tab("downloads")

        for u in urls:
            self.url_entry.delete(0, "end")
            self.url_entry.insert(0, u)
            self._on_start_download_click()
            time.sleep(0.3)

    # =========================================================================
    # QUEUE ROW BUILDER
    # =========================================================================
    def _add_or_update_queue_row(
        self,
        job_id: str,
        title: str,
        uploader: str,
        url: str,
        is_live: bool,
        status: str,
        progress_pct: float
    ) -> Dict[str, Any]:
        """Creates or updates a clean card in the Downloads Queue list."""
        if hasattr(self, "queue_empty_lbl") and self.queue_empty_lbl.winfo_exists():
            self.queue_empty_lbl.destroy()

        card = ctk.CTkFrame(self.queue_scroll, fg_color=COLOR_INPUT_BG, corner_radius=6, height=52)
        card.pack(fill="x", padx=4, pady=3)
        card.grid_columnconfigure(1, weight=1)

        # Status badge / indicator
        badge_color = COLOR_DANGER if is_live else COLOR_ACCENT
        status_badge = ctk.CTkLabel(
            card,
            text="🔴 LIVE" if is_live else "QUEUED",
            font=ctk.CTkFont(family="Segoe UI", size=9, weight="bold"),
            text_color=badge_color,
            width=65
        )
        status_badge.grid(row=0, column=0, padx=6, pady=8)

        # Title & Uploader
        display_title = title if len(title) <= 50 else f"{title[:47]}..."
        creator_tag = f" • @{uploader}" if uploader else ""
        title_box = ctk.CTkFrame(card, fg_color="transparent")
        title_box.grid(row=0, column=1, sticky="w", padx=6)

        t_lbl = ctk.CTkLabel(
            title_box,
            text=f"{display_title}{creator_tag}",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            text_color=COLOR_TEXT_PRIMARY,
            anchor="w"
        )
        t_lbl.pack(anchor="w")

        # Progress bar + Label
        prog_frame = ctk.CTkFrame(card, fg_color="transparent", width=140)
        prog_frame.grid(row=0, column=2, padx=6)

        prog_bar = ctk.CTkProgressBar(
            prog_frame,
            width=90,
            height=8,
            corner_radius=4,
            progress_color=COLOR_ACCENT,
            fg_color="#1d263b"
        )
        prog_bar.set(progress_pct / 100.0)
        prog_bar.pack(side="left", padx=(0, 6))

        prog_lbl = ctk.CTkLabel(
            prog_frame,
            text=f"{progress_pct:.0f}%",
            font=ctk.CTkFont(family="Consolas", size=10),
            text_color=COLOR_TEXT_SECONDARY,
            width=36
        )
        prog_lbl.pack(side="left")

        # Size
        size_lbl = ctk.CTkLabel(
            card,
            text="--",
            font=ctk.CTkFont(family="Consolas", size=10),
            text_color=COLOR_TEXT_SECONDARY,
            width=110
        )
        size_lbl.grid(row=0, column=3, padx=6)

        # Speed
        speed_lbl = ctk.CTkLabel(
            card,
            text="--",
            font=ctk.CTkFont(family="Consolas", size=10),
            text_color=COLOR_TEXT_SECONDARY,
            width=90
        )
        speed_lbl.grid(row=0, column=4, padx=6)

        # ETA
        eta_lbl = ctk.CTkLabel(
            card,
            text="--",
            font=ctk.CTkFont(family="Consolas", size=10),
            text_color=COLOR_TEXT_SECONDARY,
            width=80
        )
        eta_lbl.grid(row=0, column=5, padx=6)

        # Row Action Buttons (Open Folder / Play)
        act_box = ctk.CTkFrame(card, fg_color="transparent", width=100)
        act_box.grid(row=0, column=6, padx=6)

        open_btn = ctk.CTkButton(
            act_box,
            text="📁",
            width=30,
            height=26,
            corner_radius=4,
            fg_color=COLOR_BTN_SECONDARY,
            hover_color=COLOR_BTN_SECONDARY_HOVER,
            command=self._on_open_downloads_folder
        )
        open_btn.pack(side="left", padx=2)

        row_data = {
            "job_id": job_id,
            "card": card,
            "status_badge": status_badge,
            "title_lbl": t_lbl,
            "progress_bar": prog_bar,
            "progress_lbl": prog_lbl,
            "size_lbl": size_lbl,
            "speed_lbl": speed_lbl,
            "eta_lbl": eta_lbl,
            "open_btn": open_btn,
        }
        self.active_jobs.append(row_data)
        return row_data

    # =========================================================================
    # ACTIONS & UTILITIES
    # =========================================================================
    def _play_file(self, filepath: str):
        """Launches downloaded media file in default system player."""
        if filepath and Path(filepath).exists():
            if sys.platform == "win32":
                os.startfile(filepath)
            else:
                subprocess.run(["xdg-open", filepath])

    def _open_file_in_folder(self, filepath: str):
        """Reveals file in Windows Explorer or file manager."""
        if filepath:
            p = Path(filepath)
            if sys.platform == "win32" and p.exists():
                subprocess.run(["explorer", f"/select,{p}"])
            elif p.parent.exists():
                if sys.platform == "win32":
                    os.startfile(str(p.parent))
                else:
                    subprocess.run(["xdg-open", str(p.parent)])

    def _on_launch_setup_wizard(self):
        """Launches the 1-Click Onboarding provisioner."""
        launch_onboarding_gui()
        self._check_system_status_async()

    def _on_open_conf_file(self):
        """Opens yt-dlp.conf in Notepad."""
        conf = find_ytdlp_conf()
        if conf and conf.exists():
            if sys.platform == "win32":
                os.system(f"notepad.exe \"{conf}\"")
            else:
                subprocess.run(["xdg-open", str(conf)])

    def _on_run_doctor(self):
        """Runs the doctor diagnostics check in a separate window or terminal."""
        run_doctor()

    def _on_open_web_studio(self):
        """Launches the local Web UI at http://127.0.0.1:8765."""
        threading.Thread(target=launch_web_ui, daemon=True).start()
        import webbrowser
        webbrowser.open("http://127.0.0.1:8765")

    def _update_disk_space_display(self, path: Path):
        """Updates disk space label in sidebar footer."""
        try:
            free_gb, total_gb = check_free_disk_space(str(path))
            drive = path.anchor or path.drive or "Disk"
            self.footer_disk_lbl.configure(text=f"💾  {drive} Free: {free_gb:.1f} GB")
        except Exception:
            pass

    def _check_system_status_async(self):
        """Checks yt-dlp & FFmpeg status in the background."""
        def _chk():
            y = find_ytdlp()
            f = find_ffmpeg()
            status_text = "🟢  yt-dlp Engine Ready" if (y and f) else "🟡  Setup Recommended"
            status_color = COLOR_SUCCESS if (y and f) else COLOR_WARNING
            dl_dir = get_conf_download_dir()

            def _update():
                self.footer_status_pill.configure(text=status_text, text_color=status_color)
                self._update_disk_space_display(dl_dir)
            self.root.after(0, _update)

        threading.Thread(target=_chk, daemon=True).start()

    def _start_clipboard_monitor(self):
        """Monitors clipboard for valid video links to offer instant pasting."""
        def _poll():
            while True:
                time.sleep(1.2)
                try:
                    txt = self.root.clipboard_get().strip()
                    if txt and txt != self._clip_last:
                        self._clip_last = txt
                        if any(domain in txt for domain in ["youtube.com", "youtu.be", "tiktok.com", "twitch.tv", "kick.com"]):
                            def _notify():
                                if not self.url_entry.get().strip():
                                    self.url_entry.delete(0, "end")
                                    self.url_entry.insert(0, txt)
                                    self.status_msg_lbl.configure(
                                        text=f"📋 Link detected from clipboard! Click 'Analyze' or 'START DOWNLOAD'.",
                                        text_color=COLOR_ACCENT
                                    )
                            self.root.after(0, _notify)
                except Exception:
                    pass

        threading.Thread(target=_poll, daemon=True).start()


def launch_desktop_gui():
    """Entry point to launch the modern Desktop GUI Studio."""
    app = StreamVortexApp()
    app.root.mainloop()


if __name__ == "__main__":
    launch_desktop_gui()
