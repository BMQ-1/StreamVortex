# ⚡ StreamVortex: Intelligent Stream Sniffer & Downloader Engine for yt-dlp

<p align="center">
  <img src="https://img.shields.io/badge/StreamVortex-v1.0.0-00f2fe?style=for-the-badge&logo=fastapi&logoColor=black" alt="Version" />
  <img src="https://img.shields.io/badge/Powered_By-yt--dlp-ff0000?style=for-the-badge&logo=youtube" alt="yt-dlp" />
  <img src="https://img.shields.io/badge/Python-3.9%20%7C%203.10%20%7C%203.11%20%7C%203.12-blue?style=for-the-badge&logo=python" alt="Python" />
  <img src="https://img.shields.io/badge/License-MIT-green?style=for-the-badge" alt="License" />
  <img src="https://img.shields.io/badge/Platform-Windows%20%7C%20Linux%20%7C%20macOS-purple?style=for-the-badge" alt="Platform" />
</p>

> **Universal Stream Intelligence Studio, Live Watchdog, Modern Desktop GUI & Native yt-dlp Plugin Engine**

```text
   _____ _                              _    _            _            
  / ____| |                            | |  | |          | |           
 | (___ | |_ _ __ ___  __ _ _ __ ___   | |  | | ___  _ __| |_ _____  __
  \___ \| __| '__/ _ \/ _` | '_ ` _ \  | |  | |/ _ \| '__| __/ _ \ \/ /
  ____) | |_| | |  __/ (_| | | | | | | \ \_/ / (_) | |  | ||  __/>  < 
 |_____/ \__|_|  \___|\__,_|_| |_| |_|  \___/ \___/|_|   \__\___/_/\_\ 
```

**StreamVortex** bridges the gap when media downloaders fail on live broadcasts, VODs, or protected HLS/DASH streams due to Akamai WAF challenges, dynamic Webcast parameters, obfuscated player tokens, or strict anti-bot firewalls.

It operates seamlessly in **4 distinct modes**:
1. 🖥️ **Modern Desktop GUI Studio** — Sleek dark-mode interface with clipboard auto-sniffing, batch downloading, and visual live logs.
2. 🌐 **Glassmorphism Web Studio** — Embedded low-latency HLS.js live player, creator watchdog, and file explorer.
3. ⚡ **Cyberpunk CLI & Wizard** — Interactive guided menu and high-speed command-line tooling for power users.
4. 🔌 **Transparent `yt-dlp` Plugin** — Drop-in multi-tier extractors that enhance your standard `yt-dlp` command automatically.

---

## 🌟 Key Features

* **📦 Standalone Executable (`StreamVortex.exe`):**
  * **Zero technical knowledge required!** Users without Python or command-line experience can download `StreamVortex.exe` from GitHub Releases and run it right away.
* **🚀 1-Click Zero-Setup Media Engine (`streamvortex --onboard`):**
  * Automatically detects system prerequisites and downloads official `yt-dlp.exe`, `ffmpeg.exe`, and `ffprobe.exe`.
  * Deploys StreamVortex's optimized `yt-dlp.conf` and `tiktok-live.conf.txt` presets directly adjacent to your binaries.
  * Detects or installs official **Python 3.11** runtime and **VLC Media Player**.
  * Safely registers tools in Windows User PATH without requiring Administrator privileges.
* **🖥️ Modern Desktop GUI Studio (`streamvortex --gui`):**
  * **Auto-Clipboard Monitor**: Automatically detects copied video/live stream URLs and queues them.
  * **Live Stream Sniffer**: Intercepts obfuscated `.m3u8` streams using Playwright CDP.
  * **Batch Queue & Downloads History**: Queue multiple URLs, track real-time progress, and open target folders in 1 click.
  * **Preset Selector**: Instantly toggle between Best Quality (1080p60/Source), Fast 720p, or Audio-Only (MP3/M4A).
* **🌐 Web Studio Dashboard (`streamvortex --web`):**
  * Embedded **HLS.js Live Player** with low-latency real-time preview.
  * **Live Watchdog Tab**: Monitor multiple creators and track online/offline status automatically.
  * **Downloads Explorer Tab**: View saved media, check file sizes, and open them in your default player.
* **🔌 Native `yt-dlp` Terminal Integration:**
  * Uses standard `yt-dlp <URL>` seamlessly in your terminal.
  * Overrides broken built-in extractors with resilient multi-tier scrapers.
  * Universal sniffer protocol support: `yt-dlp "smart:<URL>"`.
* **📡 Live Watchdog & Lossless Auto-Record (`--wait` / `-w`):**
  * Monitors offline creators and starts lossless recording the exact second they go live.
* **📋 One-Click Clipboard & Toast Notifications (`--copy` / `-c`):**
  * Copies direct `.m3u8` master playlist URLs to the Windows clipboard with native desktop toast notifications.
* **🩺 System Health Doctor (`streamvortex --doctor`):**
  * Verifies and diagnoses Python, FFmpeg, Playwright/Chromium, media players, and plugin status in 1 command.

---

## 🚀 Quick Start

### Option 1: Standalone Windows Executable (No Python Required)
1. Download **`StreamVortex.exe`** from the **[Releases](https://github.com/basel-shweikani/StreamVortex/releases)** tab.
2. Double-click `StreamVortex.exe`.
3. If it is your first time, the **Zero-Setup Wizard** will offer to auto-configure `yt-dlp` and `ffmpeg` into `C:\Tools` in under 60 seconds.

---

### Option 2: Run via One-Click Launcher
Double-click `Launch StreamVortex.bat` in the project folder to open the guided menu:
```text
  [1] Launch Desktop GUI Studio (Recommended - Visual Window)
  [2] Launch Web Studio in Browser (http://127.0.0.1:8765)
  [3] 1-Click Zero-Setup Wizard (Install yt-dlp, FFmpeg, Python, VLC)
  [4] Launch Interactive Control Center (Terminal Wizard)
  [5] Run System Diagnostics (Doctor Health Check)
  [6] Build Standalone StreamVortex.exe
```

---

### Option 3: Python Pip Installation (Cross-Platform)

```bash
# Clone the repository
git clone https://github.com/basel-shweikani/StreamVortex.git
cd StreamVortex

# Install StreamVortex in editable mode with dependencies
pip install -e .

# Launch Desktop GUI Studio
streamvortex --gui

# Or launch Web Studio
streamvortex --web

# Or run interactive terminal wizard
streamvortex
```

---

## 💻 CLI Usage & Commands

### 1. Seamless Native `yt-dlp` Plugin
Standard `yt-dlp` commands work out of the box with StreamVortex's extractor enhancements:
```bash
# Download or record TikTok Live broadcasts
yt-dlp "https://www.tiktok.com/@username/live"

# Universal Sniffer for any arbitrary streaming website:
yt-dlp "smart:https://some-stream-site.com/live/channel"
```

### 2. StreamVortex Cyberpunk CLI
```bash
# Inspect stream and view multi-bitrate resolution table
streamvortex "https://www.tiktok.com/@username/live"

# Copy direct .m3u8 URL to clipboard (with Windows toast notification)
streamvortex -c "https://www.tiktok.com/@username/live"

# Extract audio only as high-quality MP3
streamvortex -a "https://www.tiktok.com/@username/live"

# Play stream directly in MPV or VLC without downloading
streamvortex -p "https://www.tiktok.com/@username/live"

# Record live broadcast with automatic reconnect
streamvortex -r "https://www.tiktok.com/@username/live"

# Watchdog mode: wait until creator goes live, then auto-record
streamvortex -w -r "https://www.tiktok.com/@username/live"

# Launch Modern Desktop GUI Studio
streamvortex --gui

# Launch Modern Web Studio Dashboard
streamvortex --web

# Run system health diagnostics
streamvortex --doctor

# 1-Click Zero-Setup media environment installer
streamvortex --onboard
```

---

## 📂 Project Structure

```text
StreamVortex/
├── Launch StreamVortex.bat       # 1-Click beginner launcher
├── StreamVortex.spec             # PyInstaller standalone build configuration
├── build_exe.py                  # Automated binary packaging script
├── pyproject.toml                # Standard Python package configuration
├── setup.py                      # Setuptools configuration
│
├── ytdlp_smartstream/            # Core Application Package
│   ├── desktop.py                # Modern Desktop GUI Studio (ttkbootstrap)
│   ├── web_ui.py                 # Glassmorphism Web Studio & HLS.js live player
│   ├── onboarding.py             # 1-Click zero-setup binary installer GUI
│   ├── setup_binaries.py         # Automated yt-dlp & FFmpeg downloader
│   ├── engine.py                 # Core media detection and execution engine
│   ├── cli.py                    # Cyberpunk rich terminal interface
│   ├── wizard.py                 # Interactive terminal wizard
│   ├── doctor.py                 # System health and diagnostic auditor
│   ├── config.py                 # Configuration, history, and creator watchlist
│   ├── sniffer.py                # Universal Playwright CDP network interceptor
│   ├── tiktok_resolver.py        # Multi-tier resilient TikTok Live/VOD resolver
│   └── recorder.py               # Lossless live recording & notifications
│
└── yt_dlp_plugins/               # Native yt-dlp Plugin Package
    └── extractor/
        ├── tiktok_smart.py       # Enhanced TikTok Live & VOD extractor
        └── universal_smart.py    # Universal 'smart:' stream sniffer extractor
```

---

## 🛠️ Architecture & How It Works

1. **Multi-Tier Resolution**: When given a live URL, StreamVortex tries lightweight static room metadata first. If challenges (Akamai/WAF/Bot-detection) are encountered, it automatically escalates to a Playwright headless Chromium browser session to sniff real `.m3u8` master playlists directly from CDP network traffic.
2. **Lossless Capture**: StreamVortex pipes validated master playlists directly to `yt-dlp` or `ffmpeg -c copy`, ensuring byte-for-byte stream capture without quality loss or re-encoding overhead.
3. **Smart Watchdog**: Periodically polls creator status with jittered backoff to avoid rate limits, instantly triggering recording the second an offline creator goes live.
4. **Zero-Setup Environment**: If `yt-dlp` or `ffmpeg` are missing from your PATH, StreamVortex downloads the official portable builds into a local directory and configures everything automatically.

---

## 🤝 Contributing

Contributions, bug reports, and feature requests are welcome!
1. Fork the Project
2. Create your Feature Branch (`git checkout -b feature/AmazingFeature`)
3. Commit your Changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the Branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

---

## 📄 License

Distributed under the **MIT License**. See [LICENSE](LICENSE) for more details.

---

<p align="center">
  <b>StreamVortex</b> — Built with ❤️ for the media preservation and open-source community.
</p>
