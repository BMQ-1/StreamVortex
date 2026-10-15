# ⚡ StreamVortex

<p align="center">
  <img src="https://img.shields.io/badge/StreamVortex-v1.0.0-00f2fe?style=for-the-badge&logo=fastapi&logoColor=black" alt="Version" />
  <img src="https://img.shields.io/badge/yt--dlp-Plugin_Ready-red?style=for-the-badge&logo=youtube" alt="yt-dlp" />
  <img src="https://img.shields.io/badge/Python-3.9%20%7C%203.10%20%7C%203.11%20%7C%203.12-blue?style=for-the-badge&logo=python" alt="Python" />
  <img src="https://img.shields.io/badge/License-MIT-green?style=for-the-badge" alt="License" />
  <img src="https://img.shields.io/badge/Platform-Windows%20%7C%20Linux%20%7C%20macOS-purple?style=for-the-badge" alt="Platform" />
</p>

> **Universal Stream Intelligence Studio, Live Watchdog, & Native yt-dlp Plugin Engine**

```text
   _____ _                              _    _            _            
  / ____| |                            | |  | |          | |           
 | (___ | |_ _ __ ___  __ _ _ __ ___   | |  | | ___  _ __| |_ _____  __
  \___ \| __| '__/ _ \/ _` | '_ ` _ \  | |  | |/ _ \| '__| __/ _ \ \/ /
  ____) | |_| | |  __/ (_| | | | | | | \ \_/ / (_) | |  | ||  __/>  < 
 |_____/ \__|_|  \___|\__,_|_| |_| |_|  \___/ \___/|_|   \__\___/_/\_\ 
```

**StreamVortex** bridges the gap when `yt-dlp` fails on live broadcasts, VODs, or protected HLS streams due to Akamai WAF challenges, dynamic Webcast parameters, or obfuscated player tokens. It functions both as an autonomous cyberpunk CLI/Web studio and as a native, transparent plugin for `yt-dlp`.

---

## 🌟 Key Features

* **Beginner-Friendly Interactive Wizard:** Run `streamvortex` or double-click `Launch StreamVortex.bat` to access a guided, menu-driven experience with zero command-line complexity.
* **Modern Web Studio Dashboard (`streamvortex --web`):**
  * Embedded **HLS.js Live Player** with low-latency playback.
  * 1-Click **Best Video Download** & **MP3 Audio Extraction**.
  * **Live Watchdog Tab**: Monitor multiple creators and track their streaming status.
  * **Downloads History & Explorer Tab**: View saved files and open their folders directly.
* **Native `yt-dlp` Terminal Integration:**
  * Uses standard `yt-dlp <URL>` seamlessly in your command line.
  * Overrides broken built-in extractors with resilient multi-tier scrapers.
* **Live Watchdog & Auto-Record (`--wait` / `-w`):**
  * Monitors offline creators and starts lossless FFmpeg recording the second they go live.
* **One-Click Clipboard & Windows Notifications (`--copy` / `-c`):**
  * Copies direct `.m3u8` URLs to the Windows clipboard with desktop toast notifications.
* **System Health Doctor (`streamvortex --doctor`):**
  * Verifies and diagnoses Python, FFmpeg, Playwright/Chromium, media players, and plugin status with 1 command.

---

## 🚀 Quick Start for Beginners

### Option A: The One-Click Launcher (No Terminal Required)
Double-click `Launch StreamVortex.bat` in the project folder. This opens the interactive menu where you can simply pick an option using your arrow keys.

### Option B: The Interactive Terminal Wizard
In your terminal, simply run:
```bash
streamvortex
```

### Option C: The Modern Web Dashboard
Launch the browser-based studio:
```bash
streamvortex --web
```
Or open `http://127.0.0.1:8765` in your browser.

---

## 💻 Power-User & Terminal CLI Commands

### 1. Normal `yt-dlp` Command (Seamless Plugin)
```bash
# Standard yt-dlp commands work out of the box:
yt-dlp "https://www.tiktok.com/@username/live"

# Universal Sniffer for any arbitrary website:
yt-dlp "smart:https://some-stream-site.com/live/channel"
```

### 2. StreamVortex Cyberpunk CLI
```bash
# Inspect stream and view multi-bitrate table
streamvortex "https://www.tiktok.com/@username/live"

# Copy direct .m3u8 URL to clipboard (with Windows toast notification)
streamvortex -c "https://www.tiktok.com/@username/live"

# Extract audio only as high-quality MP3
streamvortex -a "https://www.tiktok.com/@username/live"

# Play stream directly in MPV or VLC
streamvortex -p "https://www.tiktok.com/@username/live"

# Record live broadcast with automatic reconnect
streamvortex -r "https://www.tiktok.com/@username/live"

# Watchdog mode: wait until creator goes live, then auto-record
streamvortex -w -r "https://www.tiktok.com/@username/live"

# Run system health diagnostics
streamvortex --doctor
```

---

## 📂 Project Architecture

* [Launch StreamVortex.bat](file:///c:/AntiGravity/PC%20Tool/yt-dlp%20extracting%20Library/Launch%20StreamVortex.bat): Double-click launcher for beginners.
* [ytdlp_smartstream/wizard.py](file:///c:/AntiGravity/PC%20Tool/yt-dlp%20extracting%20Library/ytdlp_smartstream/wizard.py): Interactive menu-driven wizard.
* [ytdlp_smartstream/web_ui.py](file:///c:/AntiGravity/PC%20Tool/yt-dlp%20extracting%20Library/ytdlp_smartstream/web_ui.py): Glassmorphism Web Studio dashboard with HLS player, watchdog, and downloads history.
* [ytdlp_smartstream/doctor.py](file:///c:/AntiGravity/PC%20Tool/yt-dlp%20extracting%20Library/ytdlp_smartstream/doctor.py): Complete system health and dependency diagnostics.
* [ytdlp_smartstream/config.py](file:///c:/AntiGravity/PC%20Tool/yt-dlp%20extracting%20Library/ytdlp_smartstream/config.py): Persistent settings, download history, and creator watchlist.
* [ytdlp_smartstream/cli.py](file:///c:/AntiGravity/PC%20Tool/yt-dlp%20extracting%20Library/ytdlp_smartstream/cli.py): Rich cyberpunk CLI.
* [ytdlp_smartstream/recorder.py](file:///c:/AntiGravity/PC%20Tool/yt-dlp%20extracting%20Library/ytdlp_smartstream/recorder.py): Resilient live recording and notification engine.
* [ytdlp_smartstream/tiktok_resolver.py](file:///c:/AntiGravity/PC%20Tool/yt-dlp%20extracting%20Library/ytdlp_smartstream/tiktok_resolver.py): Multi-tier TikTok Live & VOD resolver.
* [ytdlp_smartstream/sniffer.py](file:///c:/AntiGravity/PC%20Tool/yt-dlp%20extracting%20Library/ytdlp_smartstream/sniffer.py): Universal static & Playwright CDP network interceptor.
* [yt_dlp_plugins/extractor/](file:///c:/AntiGravity/PC%20Tool/yt-dlp%20extracting%20Library/yt_dlp_plugins/extractor): Native `yt-dlp` plugin extractors.
