"""
StreamVortex Studio Modern Multi-Panel UI Template (2026 Executive Pro Suite).
Features:
- Razor-sharp native ClearType rendering (Segoe UI Variable & Cascadia Code with Inter / Jakarta Sans)
- Zero text shifting / jumping / blurring on hover or touch (eliminated subpixel transforms & weight shifting)
- High-contrast, large-format typography engineered for crystal clarity from afar and on high-DPI displays
- Stealth Luxury Obsidian & Executive Cobalt Sapphire Blue palette
- Silky 2026 opacity crossfades and fluid side panel slide/collapse mechanics
- Dynamic Zoom engine with Ctrl + Mouse Scroll, Ctrl +/-/0, and topbar zoom badge
- Bulletproof uncollapsible Hero URL command bar with integrated Paste & Clear
- Fully responsive 3-window layout with smart auto-docking and non-breaking headers
"""

from .engine import find_ytdlp_conf, get_conf_download_dir


def generate_studio_html() -> str:
    conf = find_ytdlp_conf()
    conf_name = conf.name if conf else "Default"
    conf_dir = str(get_conf_download_dir(conf))

    return f"""<!DOCTYPE html>
<html lang="en" class="dark">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>StreamVortex Studio — Universal yt-dlp &amp; Live Suite v1.3</title>
  <link rel="icon" type="image/png" href="/icon.png">
  <script src="https://cdn.jsdelivr.net/npm/hls.js@1.5.8/dist/hls.min.js"></script>
  <script src="https://cdn.tailwindcss.com"></script>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;600;700&family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap" rel="stylesheet">
  <style>
    :root {{
      --bg-base: #080a0f;
      --bg-panel: rgba(13, 17, 26, 0.96);
      --bg-card: rgba(20, 27, 40, 0.78);
      --bg-card-hover: rgba(28, 38, 56, 0.95);
      --bg-input: #0b0f16;
      --border-panel: rgba(255, 255, 255, 0.1);
      --border-subtle: rgba(255, 255, 255, 0.08);
      --border-hover: rgba(59, 130, 246, 0.5);
      --accent-blue: #2563eb;
      --accent-blue-hover: #1d4ed8;
      --accent-blue-glow: rgba(37, 99, 235, 0.35);
      --accent-sky: #38bdf8;
      --accent-danger: #ef4444;
      --accent-danger-hover: #dc2626;
      --accent-emerald: #10b981;
      --ease-apple: cubic-bezier(0.16, 1, 0.3, 1);
    }}
    * {{
      box-sizing: border-box;
      -webkit-font-smoothing: antialiased;
      -moz-osx-font-smoothing: grayscale;
      text-rendering: geometricPrecision;
    }}
    body {{
      background: var(--bg-base);
      background-image: 
        radial-gradient(ellipse 70% 45% at 50% 0%, rgba(37, 99, 235, 0.09), transparent 70%),
        radial-gradient(ellipse 45% 35% at 95% 100%, rgba(56, 189, 248, 0.04), transparent 60%);
      color: #ffffff;
      font-family: "Segoe UI Variable Text", "Segoe UI", -apple-system, BlinkMacSystemFont, system-ui, "Plus Jakarta Sans", "Inter", sans-serif;
      font-feature-settings: "cv02", "cv03", "cv04", "cv11", "ss01";
      overflow: hidden;
      user-select: none;
      height: 100vh;
      width: 100vw;
      font-size: 13px;
      line-height: 1.5;
      transition: zoom 0.12s ease-out;
    }}
    .mono {{ font-family: "Cascadia Code", "Consolas", "JetBrains Mono", monospace; }}

    /* Modern Glass Surfaces */
    .glass-topbar {{
      background: rgba(11, 15, 23, 0.96);
      backdrop-filter: blur(24px);
      -webkit-backdrop-filter: blur(24px);
      border-bottom: 1px solid var(--border-panel);
    }}
    .glass-panel {{
      background: var(--bg-panel);
      backdrop-filter: blur(24px);
      -webkit-backdrop-filter: blur(24px);
      border: 1px solid var(--border-panel);
    }}
    .glass-card {{
      background: var(--bg-card);
      border: 1px solid var(--border-subtle);
      transition: background-color 0.15s ease, border-color 0.15s ease, box-shadow 0.15s ease;
    }}
    .glass-card:hover {{
      border-color: var(--border-hover);
      background: var(--bg-card-hover);
      box-shadow: 0 10px 28px -6px rgba(0, 0, 0, 0.55), 0 0 16px -4px rgba(37, 99, 235, 0.22);
    }}
    .glass-input {{
      background: var(--bg-input);
      border: 1px solid rgba(255, 255, 255, 0.12);
      color: #ffffff;
      transition: border-color 0.15s ease, box-shadow 0.15s ease, background-color 0.15s ease;
    }}
    .glass-input:focus {{
      border-color: var(--accent-blue);
      box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.25);
      outline: none;
      background: #0f1420;
    }}

    /* Buttons with pure lighting micro-interactions (NO text-blurring subpixel transforms) */
    .btn-primary {{
      background: linear-gradient(180deg, #3b82f6 0%, #2563eb 100%);
      color: #ffffff;
      font-weight: 600;
      border: 1px solid rgba(255, 255, 255, 0.25);
      transition: filter 0.15s ease, box-shadow 0.15s ease;
      box-shadow: 0 4px 14px rgba(37, 99, 235, 0.4);
      cursor: pointer;
    }}
    .btn-primary:hover {{
      filter: brightness(1.12);
      box-shadow: 0 6px 20px rgba(37, 99, 235, 0.55);
    }}
    .btn-primary:active {{
      filter: brightness(0.92);
      box-shadow: 0 2px 8px rgba(37, 99, 235, 0.3);
    }}
    .btn-danger {{
      background: linear-gradient(180deg, #f87171 0%, #ef4444 100%);
      color: #ffffff;
      font-weight: 600;
      border: 1px solid rgba(255, 255, 255, 0.25);
      transition: filter 0.15s ease, box-shadow 0.15s ease;
      box-shadow: 0 4px 14px rgba(239, 68, 68, 0.4);
      cursor: pointer;
    }}
    .btn-danger:hover {{
      filter: brightness(1.12);
      box-shadow: 0 6px 20px rgba(239, 68, 68, 0.55);
    }}
    .btn-danger:active {{
      filter: brightness(0.92);
      box-shadow: 0 2px 8px rgba(239, 68, 68, 0.3);
    }}
    .btn-secondary {{
      background: rgba(255, 255, 255, 0.07);
      border: 1px solid rgba(255, 255, 255, 0.12);
      color: #e2e8f0;
      font-weight: 500;
      transition: background-color 0.15s ease, border-color 0.15s ease, color 0.15s ease;
      cursor: pointer;
    }}
    .btn-secondary:hover {{
      background: rgba(255, 255, 255, 0.14);
      border-color: rgba(255, 255, 255, 0.24);
      color: #ffffff;
    }}
    .btn-secondary:active {{
      background: rgba(255, 255, 255, 0.05);
    }}

    /* Sidebar Navigation Items: Consistent weight to prevent layout jump on hover */
    .nav-item {{
      transition: background-color 0.18s ease, color 0.18s ease, border-color 0.18s ease;
      color: #cbd5e1;
      font-weight: 500;
    }}
    .nav-item:hover {{
      color: #ffffff;
      background: rgba(255, 255, 255, 0.08);
    }}
    .nav-item.active {{
      background: linear-gradient(90deg, rgba(37, 99, 235, 0.22) 0%, rgba(37, 99, 235, 0.08) 100%);
      color: #ffffff;
      font-weight: 600;
      border-left: 3px solid #3b82f6;
    }}

    /* Right Side Dock Tabs */
    .dock-tab {{
      color: #94a3b8;
      border-bottom: 2px solid transparent;
      font-weight: 500;
      transition: color 0.18s ease, border-color 0.18s ease;
    }}
    .dock-tab:hover {{
      color: #ffffff;
    }}
    .dock-tab.active {{
      color: #ffffff;
      font-weight: 600;
      border-bottom-color: #3b82f6;
    }}

    /* Fluid Tab Crossfade Engine (Hardware accelerated & stationary) */
    .tab-content {{
      display: none;
      opacity: 0;
      transform: translateY(6px);
      transition: opacity 0.2s var(--ease-apple), transform 0.2s var(--ease-apple);
    }}
    .tab-content.active {{
      display: flex;
      opacity: 1;
      transform: translateY(0);
    }}
    .tab-view-animated {{
      animation: tabFadeIn 0.2s var(--ease-apple) forwards;
    }}
    @keyframes tabFadeIn {{
      0% {{
        opacity: 0;
        transform: translateY(6px);
      }}
      100% {{
        opacity: 1;
        transform: translateY(0);
      }}
    }}

    /* Smooth Collapsible Side Panels */
    #leftSidebar {{
      transition: width 0.28s var(--ease-apple), max-width 0.28s var(--ease-apple), min-width 0.28s var(--ease-apple), opacity 0.2s ease;
      will-change: width, max-width, opacity;
    }}
    #leftSidebar.sidebar-collapsed {{
      width: 0 !important;
      min-width: 0 !important;
      max-width: 0 !important;
      opacity: 0 !important;
      border-right-width: 0 !important;
      padding: 0 !important;
      overflow: hidden !important;
      pointer-events: none !important;
    }}
    #rightSidebar {{
      transition: width 0.28s var(--ease-apple), max-width 0.28s var(--ease-apple), min-width 0.28s var(--ease-apple), opacity 0.2s ease;
      will-change: width, max-width, opacity;
    }}
    #rightSidebar.dock-collapsed {{
      width: 0 !important;
      min-width: 0 !important;
      max-width: 0 !important;
      opacity: 0 !important;
      border-left-width: 0 !important;
      padding: 0 !important;
      overflow: hidden !important;
      pointer-events: none !important;
    }}

    /* Live Recording Pulse */
    .live-dot {{
      position: relative;
      display: inline-flex;
      align-items: center;
    }}
    .live-dot::before {{
      content: '';
      display: inline-block;
      width: 8px;
      height: 8px;
      border-radius: 50%;
      background: #ef4444;
      margin-right: 6px;
      box-shadow: 0 0 10px #ef4444;
      animation: pulse-ring 1.6s cubic-bezier(0.24, 0, 0.38, 1) infinite;
    }}
    @keyframes pulse-ring {{
      0% {{ transform: scale(0.95); box-shadow: 0 0 0 0 rgba(239, 68, 68, 0.7); }}
      70% {{ transform: scale(1.25); box-shadow: 0 0 0 6px rgba(239, 68, 68, 0); }}
      100% {{ transform: scale(0.95); box-shadow: 0 0 0 0 rgba(239, 68, 68, 0); }}
    }}

    /* Animated Shimmer Bar */
    .progress-shimmer {{
      background-image: linear-gradient(
        90deg,
        rgba(255, 255, 255, 0) 0%,
        rgba(255, 255, 255, 0.25) 50%,
        rgba(255, 255, 255, 0) 100%
      );
      background-size: 200% 100%;
      animation: shimmer 1.6s infinite ease-in-out;
    }}
    @keyframes shimmer {{
      0% {{ background-position: -200% 0; }}
      100% {{ background-position: 200% 0; }}
    }}

    /* Custom Fluid Scrollbars */
    ::-webkit-scrollbar {{ width: 6px; height: 6px; }}
    ::-webkit-scrollbar-track {{ background: rgba(0, 0, 0, 0.2); }}
    ::-webkit-scrollbar-thumb {{ background: rgba(255, 255, 255, 0.16); border-radius: 4px; transition: background 0.2s; }}
    ::-webkit-scrollbar-thumb:hover {{ background: rgba(255, 255, 255, 0.32); }}

    #dragOverlay.active {{
      display: flex;
    }}
  </style>
</head>
<body class="flex flex-col relative select-none">

  <!-- Drag & Drop Overlay -->
  <div id="dragOverlay" class="fixed inset-0 z-50 hidden bg-slate-950/85 backdrop-blur-md border-2 border-dashed border-blue-500 items-center justify-center p-8 pointer-events-none transition-all">
    <div class="glass-panel p-8 rounded-2xl flex flex-col items-center gap-3 text-center shadow-2xl">
      <img src="/icon.png" class="w-16 h-16 rounded-2xl shadow-xl object-contain" alt="StreamVortex" onerror="this.onerror=null; this.src='/icon.png';" />
      <h2 class="text-xl font-bold text-white">Drop Media File or Stream URL</h2>
      <p class="text-xs text-slate-300 mono">URLs will be analyzed in Studio • Video files will be inspected in Container Repair</p>
    </div>
  </div>

  <!-- Global Application Header / Topbar -->
  <header class="glass-topbar px-4 py-2.5 flex items-center justify-between gap-3 shrink-0 z-30 flex-nowrap">
    
    <!-- Left Module: Sidebar Toggle + Official Branded App Icon -->
    <div class="flex items-center gap-3 shrink-0">
      <button onclick="toggleSidebar()" class="p-1.5 rounded-xl text-slate-300 hover:text-white hover:bg-white/10 transition-all cursor-pointer" title="Toggle Navigation Sidebar">
        <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h16M4 18h7"></path></svg>
      </button>
      <div class="flex items-center gap-2.5">
        <div class="w-8 h-8 rounded-xl overflow-hidden shadow-md shadow-blue-900/30 border border-white/15 flex items-center justify-center bg-slate-900 shrink-0">
          <img src="/icon.png" class="w-full h-full object-contain" alt="StreamVortex" onerror="this.onerror=null; this.parentElement.innerHTML='⚡';" />
        </div>
        <div>
          <div class="flex items-center gap-2">
            <h1 class="text-sm font-bold tracking-tight text-white flex items-center gap-1.5">
              StreamVortex <span class="text-[10px] uppercase font-bold text-blue-400 bg-blue-500/15 px-1.5 py-0.5 rounded border border-blue-500/30">Studio</span>
            </h1>
            <span class="text-[10px] font-bold px-1.5 py-0.5 rounded bg-slate-800 text-slate-200 border border-slate-700 mono">v1.3</span>
          </div>
          <p class="text-[11px] text-slate-300 mono">Universal Live &amp; Video Suite // yt-dlp</p>
        </div>
      </div>
    </div>

    <!-- Center Module: Quick Status Ribbon (Responsive & Non-breaking) -->
    <div class="hidden lg:flex items-center gap-2 text-xs mono shrink-0">
      <span class="text-[11px] font-semibold px-2 py-0.5 rounded-md bg-slate-900 text-slate-200 border border-slate-800 whitespace-nowrap">
        Config: {conf_name}
      </span>
      <span id="hdrDiskBadge" class="text-[11px] font-semibold px-2 py-0.5 rounded-md bg-slate-900 text-slate-200 border border-slate-800 flex items-center gap-1 whitespace-nowrap">
        💾 <span id="hdrDiskText">Checking...</span>
      </span>
      <button onclick="pyCall('open_folder')" class="text-[11px] font-semibold px-2.5 py-0.5 rounded-md bg-slate-900 hover:bg-slate-800 text-slate-200 hover:text-white border border-slate-800 transition-all cursor-pointer flex items-center gap-1" title="Open download folder">
        📂 <span id="hdrDlDir" class="truncate max-w-[150px]">{conf_dir}</span>
      </button>
    </div>

    <!-- Right Module: Global Actions, Zoom Badge & Side Window Toggles -->
    <div class="flex items-center gap-2 shrink-0">
      <!-- Zoom Indicator Pill (Click to reset 100%) -->
      <button onclick="resetZoom()" id="hdrZoomBtn" class="text-xs font-semibold px-2 py-1 rounded-lg bg-slate-900 hover:bg-slate-800 text-slate-200 hover:text-white border border-slate-700 mono transition-all cursor-pointer flex items-center gap-1" title="Interface Zoom (Ctrl + Scroll to zoom, Click to reset)">
        🔍 <span id="zoomPercentText">100%</span>
      </button>

      <div id="queueIndicator" onclick="openRightPanelTab('queue')" class="hidden cursor-pointer px-2.5 py-1 rounded-lg text-xs font-semibold bg-rose-500/15 text-rose-400 border border-rose-500/30 flex items-center gap-1.5 whitespace-nowrap" title="Click to view running downloads">
        <span class="w-2 h-2 rounded-full bg-rose-500 animate-ping"></span>
        <span id="navQueueCount" class="mono">0</span> Running
      </div>
      <button onclick="pyCall('run_1click_setup')" class="btn-secondary px-3 py-1.5 rounded-lg text-xs font-semibold flex items-center gap-1.5 cursor-pointer whitespace-nowrap">
        <span>⚡</span> Wizard
      </button>
      <button onclick="pyCall('open_folder')" class="btn-secondary px-3 py-1.5 rounded-lg text-xs font-semibold flex items-center gap-1.5 cursor-pointer whitespace-nowrap">
        <span>📂</span> Explorer
      </button>
      <button onclick="toggleRightPanel()" id="rightPanelToggleBtn" class="p-1.5 rounded-xl text-blue-400 hover:text-white hover:bg-white/10 transition-all cursor-pointer border border-blue-500/30" title="Toggle Side Window (Telemetry &amp; Queue)">
        <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 17V7m0 10a2 2 0 01-2 2H5a2 2 0 01-2-2V7a2 2 0 012-2h2a2 2 0 012 2m0 10a2 2 0 002 2h2a2 2 0 002-2M9 7a2 2 0 012-2h2a2 2 0 012 2m0 10V7m0 10a2 2 0 002 2h2a2 2 0 002-2V7a2 2 0 00-2-2h-2a2 2 0 00-2 2"></path></svg>
      </button>
    </div>
  </header>

  <!-- ======================================================================= -->
  <!-- 3-WINDOW SPLIT WORKSPACE: LEFT NAV + CENTER STAGE + RIGHT INSPECTOR      -->
  <!-- ======================================================================= -->
  <div class="flex-1 flex overflow-hidden relative">

    <!-- 1. LEFT SIDEBAR WINDOW (Workspaces & Presets) -->
    <aside id="leftSidebar" class="w-56 border-r border-white/5 bg-[#0a0d15]/95 backdrop-blur-xl flex flex-col justify-between shrink-0 z-20">
      
      <!-- Top Part: Navigation Workspaces -->
      <div class="p-3 flex flex-col gap-4 overflow-y-auto min-w-0">
        <div>
          <div class="text-[11px] font-bold uppercase tracking-wider text-slate-400 px-3 py-1 mono">Workspace</div>
          <nav class="flex flex-col gap-1 mt-1">
            <button onclick="switchTab('studio')" id="tabBtn-studio" class="nav-item tab-btn active w-full text-left px-3 py-2 rounded-xl text-xs flex items-center gap-2.5 cursor-pointer">
              <span class="text-sm shrink-0">⚡</span> <span class="truncate">Studio &amp; Sniffer</span>
            </button>
            <button onclick="switchTab('batch')" id="tabBtn-batch" class="nav-item tab-btn w-full text-left px-3 py-2 rounded-xl text-xs flex items-center gap-2.5 cursor-pointer">
              <span class="text-sm shrink-0">📦</span> <span class="truncate">Batch Downloader</span>
            </button>
            <button onclick="switchTab('watchdog')" id="tabBtn-watchdog" class="nav-item tab-btn w-full text-left px-3 py-2 rounded-xl text-xs flex items-center justify-between cursor-pointer">
              <div class="flex items-center gap-2.5 min-w-0">
                <span class="text-sm shrink-0">🔴</span> <span class="truncate">Creator Watchdog</span>
              </div>
              <span id="navWatchCount" class="text-[11px] font-bold px-1.5 py-0.2 rounded-md bg-slate-800 text-slate-300 mono shrink-0">0</span>
            </button>
            <button onclick="switchTab('repair')" id="tabBtn-repair" class="nav-item tab-btn w-full text-left px-3 py-2 rounded-xl text-xs flex items-center gap-2.5 cursor-pointer">
              <span class="text-sm shrink-0">🛠️</span> <span class="truncate">Container Repair</span>
            </button>
            <button onclick="switchTab('library')" id="tabBtn-library" class="nav-item tab-btn w-full text-left px-3 py-2 rounded-xl text-xs flex items-center gap-2.5 cursor-pointer">
              <span class="text-sm shrink-0">📁</span> <span class="truncate">Media Library</span>
            </button>
            <button onclick="switchTab('settings')" id="tabBtn-settings" class="nav-item tab-btn w-full text-left px-3 py-2 rounded-xl text-xs flex items-center gap-2.5 cursor-pointer">
              <span class="text-sm shrink-0">⚙️</span> <span class="truncate">Engine &amp; Settings</span>
            </button>
          </nav>
        </div>

        <!-- Presets Section -->
        <div class="pt-2 border-t border-white/5">
          <div class="text-[11px] font-bold uppercase tracking-wider text-slate-400 px-3 py-1 mono">Quick Presets</div>
          <div class="flex flex-col gap-1 mt-1 text-xs">
            <button onclick="setPreset('https://www.tiktok.com/@weathernewslive/live')" class="w-full text-left px-3 py-1.5 rounded-lg text-slate-200 hover:text-white hover:bg-white/10 transition-all text-xs flex items-center gap-2 cursor-pointer font-medium">
              <span class="shrink-0">🎵</span> <span class="truncate">TikTok Live Demo</span>
            </button>
            <button onclick="setPreset('https://www.youtube.com/watch?v=dQw4w9WgXcQ')" class="w-full text-left px-3 py-1.5 rounded-lg text-slate-200 hover:text-white hover:bg-white/10 transition-all text-xs flex items-center gap-2 cursor-pointer font-medium">
              <span class="shrink-0">▶️</span> <span class="truncate">YouTube Demo</span>
            </button>
            <button onclick="setPreset('https://test-streams.mux.dev/x36xhzz/x36xhzz.m3u8')" class="w-full text-left px-3 py-1.5 rounded-lg text-slate-200 hover:text-white hover:bg-white/10 transition-all text-xs flex items-center gap-2 cursor-pointer font-medium">
              <span class="shrink-0">⚡</span> <span class="truncate">HLS M3U8 Stream</span>
            </button>
          </div>
        </div>
      </div>

      <!-- Bottom Part: Engine Status & Diagnostics Dock (Zero clipping) -->
      <div class="p-3.5 border-t border-white/5 bg-slate-950/70 flex flex-col gap-2 shrink-0">
        <div class="flex items-center justify-between text-xs mono">
          <span class="text-slate-300">yt-dlp Engine</span>
          <span id="sideYtStatus" class="text-emerald-400 font-bold">Ready</span>
        </div>
        <div class="flex items-center justify-between text-xs mono">
          <span class="text-slate-300">FFmpeg</span>
          <span id="sideFfStatus" class="text-emerald-400 font-bold">Ready</span>
        </div>
        <div class="pt-1 flex flex-col gap-1">
          <div class="flex items-center justify-between text-[11px] mono text-slate-300">
            <span>Disk Space</span>
            <span id="sideDiskText" class="text-blue-300 font-semibold">--</span>
          </div>
          <div class="w-full bg-slate-900 rounded-full h-1.5 overflow-hidden">
            <div id="sideDiskBar" class="h-full bg-blue-600 rounded-full" style="width: 65%;"></div>
          </div>
        </div>
        <button onclick="pyCall('run_doctor')" class="w-full mt-1 btn-secondary py-1.5 rounded-lg text-xs font-semibold flex items-center justify-center gap-1.5 cursor-pointer">
          <span>🩺</span> Diagnostics Doctor
        </button>
      </div>
    </aside>

    <!-- 2. CENTER STAGE CANVAS (Main Workspace) -->
    <main class="flex-1 flex flex-col min-w-0 overflow-y-auto bg-[#07090f] p-4 sm:p-6 lg:p-7 space-y-6">

      <!-- =============================================================== -->
      <!-- TAB 1: STUDIO & SNIFFER (Primary Workspace)                     -->
      <!-- =============================================================== -->
      <section id="tab-studio" class="tab-content active flex flex-col gap-5">
        
        <!-- Live Recording / Download Telemetry HUD (Inside Studio) -->
        <div id="studioLiveHud" class="hidden glass-panel rounded-2xl p-5 border border-blue-500/40 shadow-2xl flex flex-col gap-3.5">
          <div class="flex items-center justify-between flex-wrap gap-2 border-b border-white/5 pb-3">
            <div class="flex items-center gap-2.5 min-w-0">
              <span id="hudLiveDot" class="live-dot font-bold text-xs text-rose-400 shrink-0">RECORDING LIVE STREAM</span>
              <span id="hudStreamTitle" class="text-sm font-bold text-white truncate max-w-md">Stream Title</span>
            </div>
            <div class="flex items-center gap-2 shrink-0">
              <span id="hudStatusDesc" class="mono text-xs text-blue-400 font-semibold">Capturing HLS chunks</span>
              <button onclick="stopActiveStudioDownload()" id="hudStopBtn" class="btn-danger px-3.5 py-1 rounded-lg text-xs font-semibold flex items-center gap-1.5 cursor-pointer">
                ⏹️ Stop &amp; Finalize
              </button>
            </div>
          </div>

          <!-- 4 Telemetry Metrics Grid (Responsive, No Overflow) -->
          <div class="grid grid-cols-2 md:grid-cols-4 gap-3 text-xs mono">
            <div class="bg-slate-950/70 p-3 rounded-xl border border-white/5 flex flex-col gap-1 min-w-0">
              <span class="text-[11px] uppercase font-bold text-slate-300">Elapsed Time</span>
              <span id="hudElapsed" class="text-sm font-bold text-emerald-400">00:00:00</span>
            </div>
            <div class="bg-slate-950/70 p-3 rounded-xl border border-white/5 flex flex-col gap-1 min-w-0">
              <span class="text-[11px] uppercase font-bold text-slate-300">Captured Size</span>
              <span id="hudSize" class="text-sm font-bold text-white">0.0 MB</span>
            </div>
            <div class="bg-slate-950/70 p-3 rounded-xl border border-white/5 flex flex-col gap-1 min-w-0">
              <span class="text-[11px] uppercase font-bold text-slate-300">Speed / Bitrate</span>
              <span id="hudSpeed" class="text-sm font-bold text-blue-400">--</span>
            </div>
            <div class="bg-slate-950/70 p-3 rounded-xl border border-white/5 flex flex-col gap-1 min-w-0">
              <span class="text-[11px] uppercase font-bold text-slate-300">Save Destination</span>
              <span id="hudFile" class="text-xs text-slate-200 truncate font-semibold" title="Output file">Saving to disk...</span>
            </div>
          </div>

          <!-- Animated Progress Bar -->
          <div class="w-full bg-slate-950 rounded-full h-2 overflow-hidden border border-white/5">
            <div id="hudProgressBar" class="h-full bg-gradient-to-r from-blue-600 via-sky-400 to-blue-500 progress-shimmer w-full"></div>
          </div>

          <div class="flex items-center justify-between flex-wrap gap-2 text-xs text-slate-300 mono pt-1">
            <span>Format: <span id="hudFormatBadge" class="text-white font-medium">MP4 (MPEG-TS auto-remux enabled)</span></span>
            <div class="flex gap-3">
              <button onclick="pyCall('open_folder')" class="hover:text-white underline cursor-pointer">Open Folder</button>
              <button onclick="playInExternalPlayer()" class="hover:text-blue-400 underline cursor-pointer">Preview in VLC/MPV</button>
            </div>
          </div>
        </div>

        <!-- Hero URL Command Bar Dock (Bulletproof layout, never crushes) -->
        <div class="glass-panel rounded-2xl p-5 sm:p-6 shadow-2xl flex flex-col gap-4">
          <div class="flex items-center justify-between flex-wrap gap-2 pb-1">
            <div class="flex items-center gap-2">
              <span class="w-1.5 h-3.5 bg-blue-500 rounded-full inline-block"></span>
              <span class="text-xs font-bold uppercase tracking-wider text-slate-200">Target Stream, Video, or Playlist URL</span>
            </div>
            <span id="platformDetectBadge" class="px-2.5 py-1 rounded-md bg-slate-900 border border-slate-700/80 text-blue-400 text-xs mono font-semibold flex items-center gap-1.5 shadow-sm">
              ⚡ Universal Sniffer
            </span>
          </div>

          <!-- Input Bar with integrated actions (immune to squishing) -->
          <div class="flex flex-col gap-3">
            <div class="relative flex items-center w-full min-w-0">
              <span id="urlIconSlot" class="absolute left-3.5 text-slate-400 text-sm pointer-events-none select-none">⚡</span>
              <input 
                type="text" 
                id="streamUrlInput" 
                placeholder="Paste any stream or video URL (TikTok Live, YouTube 4K, Twitch, Kick, or .m3u8)..." 
                class="w-full glass-input rounded-xl pl-10 pr-24 py-3.5 text-xs sm:text-sm mono text-white outline-none"
                oninput="onUrlInputChanged(this.value)"
                onkeydown="if(event.key === 'Enter') onAnalyzeClick()"
              />
              <div class="absolute right-2 flex items-center gap-1">
                <button onclick="clearUrlInput()" id="clearUrlBtn" class="hidden text-slate-400 hover:text-white p-1 text-xs rounded hover:bg-white/10 transition-colors cursor-pointer" title="Clear input">✕</button>
                <button onclick="onPasteClick()" class="btn-secondary px-2.5 py-1.5 rounded-lg text-xs font-semibold flex items-center gap-1 cursor-pointer" title="Paste from clipboard">
                  <span>📋</span> <span>Paste</span>
                </button>
              </div>
            </div>

            <!-- Action Command Row -->
            <div class="flex items-center gap-2.5">
              <button onclick="onAnalyzeClick()" id="analyzeBtn" class="btn-primary flex-1 py-3 rounded-xl text-xs sm:text-sm font-bold flex items-center justify-center gap-2 cursor-pointer shadow-lg">
                <span>⚡ Analyze &amp; Sniff Stream</span>
              </button>
              <button onclick="onHeroDownloadBtnClick()" class="btn-secondary px-5 py-3 rounded-xl text-xs sm:text-sm font-semibold flex items-center justify-center gap-1.5 cursor-pointer whitespace-nowrap" title="Direct download with active presets">
                <span>⬇️</span> <span class="hidden sm:inline">Quick Download</span>
              </button>
            </div>
          </div>

          <!-- Keyboard Hints -->
          <div class="flex items-center justify-between flex-wrap gap-2 pt-2 border-t border-white/5 text-xs text-slate-300 mono">
            <span>Universal live sniffer with automatic token and format extraction</span>
            <span>Press <kbd class="px-1.5 py-0.5 rounded bg-slate-800 border border-slate-700 text-slate-200 font-semibold">/</kbd> to focus • <kbd class="px-1.5 py-0.5 rounded bg-slate-800 border border-slate-700 text-slate-200 font-semibold">Ctrl+Enter</kbd> to record • <kbd class="px-1.5 py-0.5 rounded bg-slate-800 border border-slate-700 text-slate-200 font-semibold">Ctrl + Scroll</kbd> to zoom</span>
          </div>

          <!-- Loading State -->
          <div id="loader" class="hidden py-6 rounded-xl glass-card flex flex-col items-center justify-center gap-2.5 border border-slate-700">
            <div class="w-8 h-8 border-2 border-blue-500 border-t-transparent rounded-full animate-spin"></div>
            <span class="text-xs font-semibold text-white tracking-wide">Resolving stream manifest &amp; bitrates...</span>
          </div>
        </div>

        <!-- Live Player & Stream Preview Section (Appears after analysis) -->
        <div id="playerSection" class="hidden flex flex-col gap-5">
          
          <div class="glass-panel rounded-2xl p-5 sm:p-6 shadow-2xl flex flex-col gap-4">
            <!-- Metadata Ribbon -->
            <div class="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-4 border-b border-white/5">
              <div class="flex flex-col gap-1.5 min-w-0">
                <div class="flex items-center gap-2 flex-wrap">
                  <span id="platformBadge" class="text-xs px-2.5 py-0.5 rounded-md font-bold mono bg-slate-900 text-blue-400 border border-slate-800 flex items-center gap-1">
                    ⚡ Universal
                  </span>
                  <span id="liveStatusBadge" class="live-dot bg-rose-500/10 border border-rose-500/25 text-rose-400 text-xs px-2.5 py-0.5 rounded-md font-bold mono">
                    LIVE STREAM
                  </span>
                  <span id="uploaderBadge" class="text-xs font-medium text-slate-200 mono bg-slate-800/80 px-2 py-0.5 rounded-md border border-slate-700">@creator</span>
                </div>
                <h2 id="streamTitle" class="text-base sm:text-lg font-bold text-white line-clamp-2">Stream Title</h2>
              </div>
              
              <!-- Quick Actions -->
              <div class="flex items-center gap-2 flex-wrap shrink-0">
                <button onclick="startDownloadCurrent('video')" id="theaterDownloadBtn" class="btn-primary px-4 py-2 rounded-xl text-xs font-bold flex items-center gap-1.5 cursor-pointer">
                  ⬇️ Download Best
                </button>
                <button onclick="startDownloadCurrent('audio')" class="btn-secondary px-3.5 py-2 rounded-xl text-xs font-semibold text-white flex items-center gap-1.5 cursor-pointer">
                  🎵 Audio (MP3)
                </button>
                <button onclick="copyStreamUrl()" class="btn-secondary px-3.5 py-2 rounded-xl text-xs font-semibold text-slate-200 hover:text-white flex items-center gap-1.5 cursor-pointer" title="Copy raw manifest URL">
                  📋 Copy URL
                </button>
                <button onclick="playInExternalPlayer()" class="btn-secondary px-3.5 py-2 rounded-xl text-xs font-semibold text-slate-200 hover:text-white flex items-center gap-1.5 cursor-pointer" title="Play directly in VLC or MPV">
                  ▶ VLC/MPV
                </button>
                <button onclick="onAnalyzeClick()" class="btn-secondary px-3 py-2 rounded-xl text-xs font-semibold text-slate-300 hover:text-white cursor-pointer" title="Refresh stream">
                  🔄
                </button>
              </div>
            </div>

            <!-- Embedded Video Player -->
            <div class="relative w-full aspect-video rounded-xl overflow-hidden bg-black border border-white/10 shadow-2xl">
              <video id="hlsVideo" controls autoplay muted playsinline class="w-full h-full object-contain"></video>
            </div>

            <!-- Discovered Formats Grid -->
            <div class="pt-1">
              <div class="flex items-center justify-between mb-2">
                <h3 class="text-xs font-bold uppercase tracking-wider text-slate-200 flex items-center gap-1.5">
                  <span>Discovered Streams &amp; Bitrates</span>
                  <span id="formatsCountBadge" class="text-xs px-2 py-0.5 rounded-md bg-slate-800 text-slate-200 mono font-semibold">0 formats</span>
                </h3>
                <span class="text-xs text-slate-300 mono">Click format to preview in player</span>
              </div>
              <div id="formatsList" class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2.5"></div>
            </div>
          </div>

        </div>

        <!-- Format Options & Destination Drawer -->
        <div class="glass-panel rounded-2xl p-5 sm:p-6 shadow-2xl flex flex-col gap-5">
          <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-1 pb-1 border-b border-white/5">
            <div class="flex items-center gap-2">
              <span class="w-1.5 h-3 bg-blue-500 rounded-full inline-block"></span>
              <span class="text-xs font-bold uppercase tracking-wider text-slate-200">Download Configuration &amp; Destination</span>
            </div>
            <span class="text-[11px] text-slate-400 mono">Synced with yt-dlp.conf</span>
          </div>

          <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
            <!-- Quality Profile -->
            <div class="flex flex-col gap-1.5">
              <label class="text-xs font-semibold text-slate-200">Quality Preset</label>
              <select id="qualitySelect" class="glass-input rounded-xl px-3.5 py-2.5 text-xs mono text-blue-300 outline-none cursor-pointer">
                <option value="max">🎬 Best Available (Unconstrained 4K/2K/1080p)</option>
                <option value="1080p">📱 1080p Full HD MP4</option>
                <option value="720p">⚡ 720p Fast HD MP4</option>
                <option value="480p">💾 480p Data Saver MP4</option>
                <option value="audio_mp3">🎵 Lossless MP3 (320k Audio Extraction)</option>
                <option value="audio_m4a">🎧 AAC M4A (Original Audio)</option>
                <option value="conf">⚙️ Respect yt-dlp.conf rules</option>
              </select>
            </div>

            <!-- Container Format -->
            <div class="flex flex-col gap-1.5">
              <label class="text-xs font-semibold text-slate-200">Output Container</label>
              <select id="containerSelect" class="glass-input rounded-xl px-3.5 py-2.5 text-xs mono text-blue-300 outline-none cursor-pointer">
                <option value="mp4">MP4 (Universal Compatibility)</option>
                <option value="mkv">MKV (Matroska Multi-Track)</option>
                <option value="webm">WebM (VP9/Opus)</option>
                <option value="flv">FLV (Flash Video)</option>
                <option value="ts">TS (Raw MPEG-TS Stream)</option>
              </select>
            </div>
          </div>

          <!-- 4 Modern Interactive Toggle Chips -->
          <div class="grid grid-cols-2 sm:grid-cols-4 gap-2.5">
            <label class="glass-card hover:border-slate-500 p-2.5 rounded-xl flex items-center gap-2 cursor-pointer text-xs font-medium text-slate-200">
              <input type="checkbox" id="chkSubtitles" checked class="w-4 h-4 rounded accent-blue-600 cursor-pointer">
              <span>Download Subtitles</span>
            </label>
            <label class="glass-card hover:border-slate-500 p-2.5 rounded-xl flex items-center gap-2 cursor-pointer text-xs font-medium text-slate-200">
              <input type="checkbox" id="chkAudioOnly" onchange="onAudioToggle()" class="w-4 h-4 rounded accent-blue-600 cursor-pointer">
              <span>Audio Only (MP3)</span>
            </label>
            <label class="glass-card hover:border-slate-500 p-2.5 rounded-xl flex items-center gap-2 cursor-pointer text-xs font-medium text-slate-200">
              <input type="checkbox" id="chkMetadata" checked class="w-4 h-4 rounded accent-blue-600 cursor-pointer">
              <span>Embed Metadata</span>
            </label>
            <label class="glass-card hover:border-slate-500 p-2.5 rounded-xl flex items-center gap-2 cursor-pointer text-xs font-medium text-slate-200">
              <input type="checkbox" id="chkThumbnail" checked class="w-4 h-4 rounded accent-blue-600 cursor-pointer">
              <span>Embed Thumbnail</span>
            </label>
          </div>

          <!-- Save Destination Folder -->
          <div class="flex flex-col gap-1.5 pt-2 border-t border-white/5">
            <label class="text-xs font-semibold text-slate-200 flex items-center justify-between">
              <span>Save Destination Directory</span>
              <span class="text-xs text-blue-400 mono">Synced with global config</span>
            </label>
            <div class="flex flex-col sm:flex-row gap-2 items-stretch sm:items-center">
              <input 
                type="text" 
                id="saveFolderInput" 
                value="{conf_dir}" 
                class="flex-1 min-w-0 glass-input rounded-xl px-4 py-2.5 text-xs mono text-slate-200 outline-none truncate" 
                readonly 
              />
              <div class="flex gap-2 shrink-0">
                <button onclick="onSelectFolderClick()" class="btn-secondary px-4 py-2.5 rounded-xl text-xs font-semibold flex items-center gap-1.5 cursor-pointer">
                  📁 Browse...
                </button>
                <button onclick="pyCall('open_folder')" class="btn-secondary px-3.5 py-2.5 rounded-xl text-xs font-semibold flex items-center gap-1.5 cursor-pointer" title="Open folder in Explorer">
                  ↗ Open
                </button>
              </div>
            </div>
          </div>

          <!-- Dynamic Hero Action Button -->
          <div class="pt-2 flex flex-col sm:flex-row items-center justify-between gap-3">
            <span id="heroStatusHint" class="text-xs text-slate-300 mono truncate max-w-sm">Auto-reconnect &amp; container repair active on all downloads.</span>
            <button onclick="onHeroDownloadBtnClick()" id="heroDownloadBtn" class="btn-primary w-full sm:w-auto px-10 py-3.5 rounded-xl text-sm font-bold flex items-center justify-center gap-2 cursor-pointer shadow-lg transition-all shrink-0">
              <span>⬇️</span> <span id="heroBtnLabel">START DOWNLOAD</span>
            </button>
          </div>
        </div>

      </section>

      <!-- =============================================================== -->
      <!-- TAB 2: BATCH URL DOWNLOADER                                     -->
      <!-- =============================================================== -->
      <section id="tab-batch" class="tab-content flex flex-col gap-5">
        <div class="glass-panel rounded-2xl p-6 shadow-2xl flex flex-col gap-4">
          <div class="flex items-center justify-between flex-wrap gap-2 border-b border-white/5 pb-3">
            <div>
              <h2 class="text-base font-bold text-white flex items-center gap-2">
                <span>📦</span> Batch URL Downloader
              </h2>
              <p class="text-xs text-slate-300">Queue multiple video or stream links below for sequential processing with full metadata tagging.</p>
            </div>
            <span id="batchCountBadge" class="mono text-xs px-3 py-1 rounded-md bg-slate-900 text-blue-400 border border-slate-800 font-semibold">
              0 valid URLs detected
            </span>
          </div>

          <textarea 
            id="batchUrlsInput" 
            rows="9" 
            placeholder="Paste links here (one URL per line)...&#10;https://www.tiktok.com/@creator/live&#10;https://www.youtube.com/watch?v=...&#10;https://twitch.tv/...&#10;https://kick.com/..." 
            class="glass-input rounded-xl p-4 text-xs mono text-white outline-none w-full"
            oninput="updateBatchUrlCount()"
          ></textarea>

          <div class="flex items-center justify-between flex-wrap gap-4 pt-1">
            <div class="flex items-center gap-3">
              <label class="text-xs font-semibold text-slate-200">Batch Quality:</label>
              <select id="batchQualitySelect" class="glass-input rounded-xl px-3 py-2 text-xs mono text-blue-300 outline-none">
                <option value="max">🎬 Best Available Quality</option>
                <option value="1080p">📱 1080p MP4</option>
                <option value="720p">⚡ 720p Fast MP4</option>
                <option value="audio_mp3">🎵 Audio Only (MP3 320k)</option>
              </select>
            </div>
            <button onclick="onSubmitBatchClick()" class="btn-primary px-6 py-2.5 rounded-xl text-xs font-bold cursor-pointer flex items-center gap-2">
              <span>🚀</span> Start Sequential Batch
            </button>
          </div>
        </div>
      </section>

      <!-- =============================================================== -->
      <!-- TAB 3: CREATOR LIVE WATCHDOG                                    -->
      <!-- =============================================================== -->
      <section id="tab-watchdog" class="tab-content flex flex-col gap-5">
        <div class="glass-panel rounded-2xl p-6 shadow-2xl flex flex-col gap-4">
          <div class="flex items-center justify-between flex-wrap gap-2 border-b border-white/5 pb-3">
            <div>
              <h2 class="text-base font-bold text-white flex items-center gap-2">
                <span>🔴</span> Creator Live Watchdog
              </h2>
              <p class="text-xs text-slate-300">Monitor your favorite creators across TikTok, Twitch, and Kick. Check live status or launch instant recording.</p>
            </div>
            <button onclick="checkAllWatchdogClick()" class="btn-secondary px-3.5 py-1.5 rounded-xl text-xs font-semibold text-blue-400 flex items-center gap-1.5 cursor-pointer">
              <span>🔄</span> Check All Creators
            </button>
          </div>

          <div class="flex flex-col sm:flex-row gap-2.5">
            <input 
              type="text" 
              id="watchdogInput" 
              placeholder="Enter creator handle or username (e.g. weathernewslive)..." 
              class="flex-1 glass-input rounded-xl px-4 py-2.5 text-xs mono text-white outline-none"
              onkeydown="if(event.key === 'Enter') onAddWatchlistClick()"
            />
            <button onclick="onAddWatchlistClick()" class="btn-primary px-5 py-2.5 rounded-xl text-xs font-bold cursor-pointer flex items-center justify-center gap-1.5 shrink-0">
              <span>+</span> Add Creator
            </button>
          </div>

          <div class="pt-2">
            <h3 class="text-xs font-bold uppercase tracking-wider text-slate-300 mb-3 flex items-center justify-between">
              <span>Monitored Watchlist</span>
              <span id="watchlistCount" class="text-xs mono text-slate-300 font-semibold">0 creators</span>
            </h3>
            <div id="watchlistContainer" class="grid grid-cols-1 sm:grid-cols-2 gap-3"></div>
          </div>
        </div>
      </section>

      <!-- =============================================================== -->
      <!-- TAB 4: CONTAINER REPAIR & FIXUP STUDIO                          -->
      <!-- =============================================================== -->
      <section id="tab-repair" class="tab-content flex flex-col gap-5">
        <div class="glass-panel rounded-2xl p-6 shadow-2xl flex flex-col gap-5">
          <div>
            <h2 class="text-base font-bold text-white flex items-center gap-2">
              <span>🛠️</span> Video Container Repair &amp; Interrupted Stream Fixup
            </h2>
            <p class="text-xs text-slate-300">
              Fixes unplayable videos caused by raw MPEG-TS streams saved inside .mp4 containers, legacy FLV videos, or incomplete .part recordings.
            </p>
          </div>

          <!-- Drag & Drop Zone -->
          <div id="repairDropZone" onclick="onSelectRepairFileClick()" class="glass-card hover:border-slate-500 p-8 rounded-xl border-2 border-dashed border-white/10 flex flex-col items-center justify-center gap-2 text-center cursor-pointer transition-all">
            <span class="text-2xl text-blue-400">📁</span>
            <span class="text-sm font-semibold text-white">Select Video File or Drop Here</span>
            <span class="text-xs text-slate-300 mono">Supports .mp4, .flv, .ts, .mkv, .part, .m4v</span>
          </div>

          <div class="flex flex-col sm:flex-row gap-2.5">
            <input 
              type="text" 
              id="repairPathInput" 
              placeholder="Selected video file or .part path..." 
              class="flex-1 min-w-0 glass-input rounded-xl px-4 py-2.5 text-xs mono text-white outline-none"
              onkeydown="if(event.key === 'Enter') onInspectRepairClick()"
            />
            <div class="flex gap-2 shrink-0">
              <button onclick="onSelectRepairFileClick()" class="btn-secondary px-4 py-2.5 rounded-xl text-xs font-semibold flex items-center gap-1.5 cursor-pointer">
                📁 Browse...
              </button>
              <button onclick="onInspectRepairClick()" class="btn-primary px-5 py-2.5 rounded-xl text-xs font-bold cursor-pointer flex items-center gap-1.5">
                🔍 Inspect
              </button>
            </div>
          </div>

          <!-- Inspection Result Card -->
          <div id="repairCard" class="hidden glass-card rounded-xl p-5 flex flex-col gap-4 border border-slate-700">
            <div class="flex items-center justify-between flex-wrap gap-2">
              <span id="repairFileName" class="text-sm font-bold text-white mono truncate max-w-md">video.mp4</span>
              <span id="repairStatusBadge" class="text-xs font-bold mono px-2.5 py-0.5 rounded-md bg-blue-500/15 text-blue-400 border border-blue-500/30">INSPECTED</span>
            </div>

            <div class="grid grid-cols-1 sm:grid-cols-3 gap-3 text-xs mono text-slate-200 bg-slate-950/80 p-3.5 rounded-xl border border-white/5">
              <div>Disk Extension: <span id="repairExt" class="text-white font-bold">mp4</span></div>
              <div>True Container: <span id="repairContainer" class="text-blue-400 font-bold">mpegts</span></div>
              <div>File Size: <span id="repairSize" class="text-slate-200 font-bold">45 MB</span></div>
            </div>

            <div id="repairNotice" class="text-xs text-amber-300 bg-amber-500/10 border border-amber-500/25 p-3 rounded-xl mono">
              Container discrepancy detected. StreamVortex will losslessly remux to a standards-compliant playable container with faststart headers.
            </div>

            <div class="flex justify-end gap-2.5 pt-1">
              <button onclick="onExecuteRepairClick()" class="btn-primary px-6 py-2.5 rounded-xl text-xs font-bold cursor-pointer flex items-center gap-2">
                <span>⚡</span> Lossless Remux &amp; Faststart Fix
              </button>
            </div>
          </div>
        </div>
      </section>

      <!-- =============================================================== -->
      <!-- TAB 5: MEDIA LIBRARY & HISTORY                                  -->
      <!-- =============================================================== -->
      <section id="tab-library" class="tab-content flex flex-col gap-5">
        <div class="glass-panel rounded-2xl p-6 shadow-2xl flex flex-col gap-4">
          <div class="flex items-center justify-between flex-wrap gap-2 border-b border-white/5 pb-3">
            <div>
              <h2 class="text-base font-bold text-white flex items-center gap-2">
                <span>📁</span> Downloaded Media Library &amp; History
              </h2>
              <p class="text-xs text-slate-300">Search, launch, and explore your downloaded live recordings and videos.</p>
            </div>
            <div class="flex gap-2">
              <button onclick="loadHistory()" class="btn-secondary px-3.5 py-1.5 rounded-xl text-xs font-semibold text-slate-200">
                🔄 Refresh
              </button>
              <button onclick="pyCall('open_folder')" class="btn-primary px-4 py-1.5 rounded-xl text-xs font-bold">
                📂 Open Folder
              </button>
            </div>
          </div>

          <div class="flex items-center gap-3">
            <input 
              type="text" 
              id="libSearchInput" 
              placeholder="🔍 Search downloads by title, creator, or path..." 
              class="glass-input rounded-xl px-4 py-2.5 text-xs mono text-white outline-none w-full"
              oninput="filterHistory()"
            />
          </div>

          <div id="historyStatsBar" class="flex items-center gap-2 text-xs mono text-slate-300">
            <span id="histTotalBadge" class="px-2.5 py-0.5 rounded-md bg-slate-900 border border-slate-700 text-blue-400 font-semibold">0 Items</span>
          </div>

          <div id="historyContainer" class="flex flex-col gap-2 max-h-[500px] overflow-y-auto pr-1"></div>
        </div>
      </section>

      <!-- =============================================================== -->
      <!-- TAB 6: SETTINGS & SYSTEM DIAGNOSTICS                            -->
      <!-- =============================================================== -->
      <section id="tab-settings" class="tab-content flex flex-col gap-5">
        <div class="glass-panel rounded-2xl p-6 shadow-2xl flex flex-col gap-5">
          <div class="border-b border-white/5 pb-3">
            <h2 class="text-base font-bold text-white flex items-center gap-2">
              <span>⚙️</span> Studio Settings &amp; System Health
            </h2>
            <p class="text-xs text-slate-300">Engine status, tool locations, storage availability, and yt-dlp.conf management.</p>
          </div>

          <!-- 4 Health Cards Grid -->
          <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
            <div class="glass-card p-4 rounded-xl flex flex-col gap-1 border border-white/5">
              <span class="text-xs uppercase font-bold text-slate-300 mono">yt-dlp Engine</span>
              <span id="healthYtdlp" class="text-xs font-bold text-emerald-400">Checking...</span>
              <span id="healthYtdlpPath" class="text-xs text-slate-300 mono truncate">--</span>
            </div>
            <div class="glass-card p-4 rounded-xl flex flex-col gap-1 border border-white/5">
              <span class="text-xs uppercase font-bold text-slate-300 mono">FFmpeg Transcoder</span>
              <span id="healthFfmpeg" class="text-xs font-bold text-emerald-400">Checking...</span>
              <span id="healthFfmpegPath" class="text-xs text-slate-300 mono truncate">--</span>
            </div>
            <div class="glass-card p-4 rounded-xl flex flex-col gap-1 border border-white/5">
              <span class="text-xs uppercase font-bold text-slate-300 mono">Free Storage Space</span>
              <span id="healthDisk" class="text-xs font-bold text-blue-400">Checking...</span>
              <span class="text-xs text-slate-300 mono">Active Download Drive</span>
            </div>
            <div class="glass-card p-4 rounded-xl flex flex-col gap-1 border border-white/5">
              <span class="text-xs uppercase font-bold text-slate-300 mono">Active Config</span>
              <span id="healthConf" class="text-xs font-bold text-amber-300 mono">{conf_name}</span>
              <span class="text-xs text-slate-300 mono">yt-dlp.conf</span>
            </div>
          </div>

          <!-- Destination Folder Editor -->
          <div class="flex flex-col gap-1.5 pt-2 border-t border-white/5">
            <label class="text-xs font-semibold text-slate-200">Global Downloads Directory (yt-dlp.conf)</label>
            <div class="flex flex-col sm:flex-row gap-2">
              <input type="text" id="settingsDlDir" value="{conf_dir}" class="flex-1 glass-input rounded-xl px-4 py-2.5 text-xs mono text-white outline-none truncate" readonly />
              <button onclick="onSelectFolderClick()" class="btn-secondary px-4 py-2.5 rounded-xl text-xs font-semibold shrink-0">Browse...</button>
            </div>
          </div>

          <!-- Action Tools -->
          <div class="flex items-center gap-3 flex-wrap pt-2 border-t border-white/5">
            <button onclick="pyCall('run_doctor')" class="btn-secondary px-4 py-2.5 rounded-xl text-xs font-semibold flex items-center gap-2 cursor-pointer">
              <span>🩺</span> Run Diagnostics
            </button>
            <button onclick="pyCall('run_1click_setup')" class="btn-secondary px-4 py-2.5 rounded-xl text-xs font-semibold flex items-center gap-2 cursor-pointer">
              <span>⚡</span> 1-Click Setup Wizard
            </button>
            <button onclick="pyCall('open_conf_folder')" class="btn-secondary px-4 py-2.5 rounded-xl text-xs font-semibold text-slate-200 hover:text-white flex items-center gap-2 cursor-pointer">
              <span>📂</span> Open Config Folder
            </button>
            <button onclick="loadHealth()" class="btn-secondary px-3 py-2.5 rounded-xl text-xs font-semibold text-slate-200 hover:text-white cursor-pointer" title="Refresh health">
              🔄 Refresh
            </button>
          </div>
        </div>
      </section>

    </main>

    <!-- 3. RIGHT SIDE WINDOW (Live Telemetry, Transfers & Stream Inspector) -->
    <aside id="rightSidebar" class="w-72 xl:w-80 border-l border-white/5 bg-[#0a0d15]/95 backdrop-blur-xl flex flex-col justify-between shrink-0 z-20">
      
      <!-- Dock Tabs Header -->
      <div class="p-3 border-b border-white/5 flex items-center justify-between">
        <div class="flex items-center gap-3 text-xs font-semibold">
          <button onclick="openRightPanelTab('hud')" id="rightTabBtn-hud" class="dock-tab active pb-1 cursor-pointer">
            ⚡ Live HUD
          </button>
          <button onclick="openRightPanelTab('queue')" id="rightTabBtn-queue" class="dock-tab pb-1 cursor-pointer">
            📋 Queue (<span id="rightQueueCount">0</span>)
          </button>
          <button onclick="openRightPanelTab('inspector')" id="rightTabBtn-inspector" class="dock-tab pb-1 cursor-pointer">
            🔍 Inspector
          </button>
        </div>
        <button onclick="toggleRightPanel()" class="text-slate-400 hover:text-white p-1 text-xs cursor-pointer rounded hover:bg-white/10" title="Hide Side Window">✕</button>
      </div>

      <!-- Dock Tab 1: Live HUD Active Telemetry Card -->
      <div id="rightTab-hud" class="flex-1 p-4 flex flex-col gap-3.5 overflow-y-auto">
        <div id="sideHudActiveCard" class="hidden glass-card p-4 rounded-xl border border-blue-500/30 flex flex-col gap-3">
          <div class="flex items-center justify-between text-xs">
            <span class="live-dot font-bold text-rose-400">RECORDING LIVE</span>
            <span id="sideLiveTime" class="mono text-emerald-400 font-bold">00:00:00</span>
          </div>
          <div class="font-bold text-white text-xs truncate" id="sideLiveTitle">Stream Title</div>
          <div class="flex justify-between text-xs mono text-slate-300">
            <span>Captured:</span> <span id="sideLiveSize" class="text-white font-bold">0.0 MB</span>
          </div>
          <button onclick="stopActiveStudioDownload()" class="btn-danger w-full py-2.5 rounded-lg text-xs font-bold cursor-pointer">
            ⏹️ Stop &amp; Remux
          </button>
        </div>

        <!-- Idle Status Card in Right Window -->
        <div id="sideHudIdleCard" class="glass-card p-5 rounded-xl border border-white/5 flex flex-col items-center justify-center text-center gap-2 py-8">
          <div class="w-12 h-12 rounded-2xl bg-blue-500/10 border border-blue-500/20 flex items-center justify-center text-blue-400 text-lg shadow-inner">
            <img src="/icon.png" class="w-8 h-8 rounded-xl object-contain" alt="StreamVortex" onerror="this.onerror=null; this.src='/icon.png';" />
          </div>
          <h4 class="text-xs font-bold text-white">StreamVortex Engine Ready</h4>
          <p class="text-xs text-slate-300">Paste any URL or drop a media file to start live sniffing, streaming, or downloading.</p>
        </div>

        <!-- Quick System Stats in Right Window -->
        <div class="glass-card p-3.5 rounded-xl flex flex-col gap-2 border border-white/5">
          <span class="text-[11px] font-bold uppercase tracking-wider text-slate-300 mono">Environment</span>
          <div class="flex items-center justify-between text-xs mono">
            <span class="text-slate-300">Stream Cache</span>
            <span class="text-slate-100 font-medium">Local /tmp</span>
          </div>
          <div class="flex items-center justify-between text-xs mono">
            <span class="text-slate-300">HLS Remuxer</span>
            <span class="text-emerald-400 font-semibold">Native FFmpeg</span>
          </div>
          <div class="flex items-center justify-between text-xs mono">
            <span class="text-slate-300">Lossless Fixup</span>
            <span class="text-blue-400 font-semibold">Active</span>
          </div>
        </div>
      </div>

      <!-- Dock Tab 2: Queue & Active Transfers -->
      <div id="rightTab-queue" class="hidden flex-1 p-4 flex flex-col gap-3 overflow-y-auto">
        <div id="activeDownloadsContainer" class="flex flex-col gap-3">
          <div class="flex items-center justify-between text-xs border-b border-white/5 pb-2">
            <span id="activeCount" class="mono text-blue-300 font-semibold">0 active</span>
            <button onclick="onClearCompletedClick()" class="text-xs text-slate-300 hover:text-white mono cursor-pointer">
              Clear Done
            </button>
          </div>
          <div id="activeJobsList" class="flex flex-col gap-2.5">
            <div class="text-xs text-slate-400 py-6 text-center mono">No active downloads running</div>
          </div>
        </div>
      </div>

      <!-- Dock Tab 3: Stream Technical Inspector -->
      <div id="rightTab-inspector" class="hidden flex-1 p-4 flex flex-col gap-3 overflow-y-auto text-xs mono">
        <div class="glass-card p-3.5 rounded-xl flex flex-col gap-2 border border-white/5">
          <span class="text-[11px] font-bold uppercase text-slate-300">Stream Technical Profile</span>
          <div class="flex flex-col gap-1.5 pt-1">
            <div class="flex justify-between"><span class="text-slate-300">Protocol:</span> <span id="inspProtocol" class="text-white font-medium">--</span></div>
            <div class="flex justify-between"><span class="text-slate-300">Container:</span> <span id="inspContainer" class="text-white font-medium">--</span></div>
            <div class="flex justify-between"><span class="text-slate-300">Platform:</span> <span id="inspPlatform" class="text-blue-400 font-medium">--</span></div>
            <div class="flex justify-between"><span class="text-slate-300">Total Formats:</span> <span id="inspFormats" class="text-white font-medium">0</span></div>
          </div>
        </div>
        <div class="glass-card p-3.5 rounded-xl flex flex-col gap-2 border border-white/5">
          <span class="text-[11px] font-bold uppercase text-slate-300">Direct Manifest / Source</span>
          <div id="inspUrlBox" class="p-2.5 rounded-lg bg-slate-950 text-xs break-all text-slate-200 max-h-32 overflow-y-auto border border-white/5">
            No stream analyzed yet.
          </div>
          <button onclick="copyStreamUrl()" class="btn-secondary w-full py-2 rounded-lg text-xs font-semibold cursor-pointer">
            📋 Copy Stream Link
          </button>
        </div>
      </div>

      <!-- Right Dock Bottom Utilities -->
      <div class="p-3 border-t border-white/5 bg-slate-950/70 flex items-center justify-between text-xs mono">
        <span class="text-slate-300">Auto-Remux: ON</span>
        <button onclick="pyCall('open_folder')" class="text-blue-400 hover:text-white cursor-pointer">📂 Downloads</button>
      </div>
    </aside>

  </div>

  <!-- Modern Toast Notification -->
  <div id="toast" class="fixed bottom-6 right-6 z-50 glass-panel bg-slate-900/95 border-slate-700 text-white px-4 py-3 rounded-xl text-xs shadow-2xl hidden transition-all duration-300 flex items-center gap-2.5">
    <span id="toastIcon">⚡</span>
    <span id="toastText">Notification</span>
  </div>

  <script>
    let currentStream = null;
    let hls = null;
    let rawHistory = [];
    let pollTimer = null;
    let activeStudioJobId = null;
    let activeStudioStartTime = null;
    let activeStudioTimerInterval = null;

    // =========================================================================
    // DYNAMIC ZOOM ENGINE (Ctrl + Mouse Scroll / Ctrl + +/-/0 / Topbar Badge)
    // =========================================================================
    let currentZoom = 1.0;
    const MIN_ZOOM = 0.65;
    const MAX_ZOOM = 1.75;
    const ZOOM_STEP = 0.05;

    function applyZoom(newZoom, notify = true) {{
      currentZoom = Math.max(MIN_ZOOM, Math.min(MAX_ZOOM, Math.round(newZoom * 100) / 100));
      document.body.style.zoom = currentZoom;
      const zoomText = Math.round(currentZoom * 100) + '%';
      const badge = document.getElementById('zoomPercentText');
      if (badge) badge.innerText = zoomText;
      if (notify) {{
        showToast(`Zoom: ${{zoomText}}`, '🔍');
      }}
      try {{
        localStorage.setItem('streamvortex_ui_zoom', currentZoom);
      }} catch (e) {{}}
    }}

    function resetZoom() {{
      applyZoom(1.0, true);
    }}

    // Ctrl + Mouse Wheel listener for smooth zoom
    window.addEventListener('wheel', (e) => {{
      if (e.ctrlKey) {{
        e.preventDefault();
        const delta = e.deltaY < 0 ? ZOOM_STEP : -ZOOM_STEP;
        applyZoom(currentZoom + delta);
      }}
    }}, {{ passive: false }});

    // Direct native Python bridge via PyWebView or HTTP fallback
    async function pyCall(method, ...args) {{
      if (window.pywebview && window.pywebview.api && window.pywebview.api[method]) {{
        try {{
          return await window.pywebview.api[method](...args);
        }} catch (e) {{
          console.error('pywebview api error:', e);
        }}
      }}
      try {{
        const res = await fetch('/api/call', {{
          method: 'POST',
          headers: {{ 'Content-Type': 'application/json' }},
          body: JSON.stringify({{ method: method, args: args }})
        }});
        if (res.ok) return await res.json();
      }} catch (e) {{
        console.error('HTTP API fallback error:', e);
      }}
      return null;
    }}

    function showToast(msg, icon = '⚡') {{
      const toast = document.getElementById('toast');
      document.getElementById('toastText').innerText = msg;
      document.getElementById('toastIcon').innerText = icon;
      toast.classList.remove('hidden');
      toast.classList.add('flex');
      if (window._toastTimer) clearTimeout(window._toastTimer);
      window._toastTimer = setTimeout(() => {{
        toast.classList.add('hidden');
        toast.classList.remove('flex');
      }}, 3200);
    }}

    // Smooth Side Window Collapse / Expand Controls
    function toggleSidebar() {{
      const sb = document.getElementById('leftSidebar');
      sb.classList.toggle('sidebar-collapsed');
    }}

    function toggleRightPanel() {{
      const rp = document.getElementById('rightSidebar');
      rp.classList.toggle('dock-collapsed');
    }}

    function openRightPanelTab(tabId) {{
      const rp = document.getElementById('rightSidebar');
      rp.classList.remove('dock-collapsed');

      document.querySelectorAll('.dock-tab').forEach(b => b.classList.remove('active'));
      const btn = document.getElementById('rightTabBtn-' + tabId);
      if (btn) btn.classList.add('active');

      ['hud', 'queue', 'inspector'].forEach(t => {{
        const pane = document.getElementById('rightTab-' + t);
        if (pane) {{
          pane.classList.add('hidden');
          pane.classList.remove('tab-view-animated');
        }}
      }});

      const target = document.getElementById('rightTab-' + tabId);
      if (target) {{
        target.classList.remove('hidden');
        target.classList.add('tab-view-animated');
      }}
    }}

    // Silky Smooth Tab Switcher Engine
    function switchTab(tabId) {{
      const allTabs = document.querySelectorAll('.tab-content');
      const allBtns = document.querySelectorAll('.tab-btn');
      
      allTabs.forEach(el => {{
        el.classList.remove('active');
        el.classList.remove('tab-view-animated');
      }});
      allBtns.forEach(btn => btn.classList.remove('active'));

      const target = document.getElementById('tab-' + tabId);
      if (target) {{
        target.classList.add('active');
        target.classList.add('tab-view-animated');
      }}
      const activeBtn = document.getElementById('tabBtn-' + tabId);
      if (activeBtn) activeBtn.classList.add('active');

      if (tabId === 'library') loadHistory();
      if (tabId === 'watchdog') loadWatchlist();
      if (tabId === 'settings') loadHealth();
    }}

    function scrollToQueue() {{
      openRightPanelTab('queue');
    }}

    function clearUrlInput() {{
      const inp = document.getElementById('streamUrlInput');
      inp.value = '';
      onUrlInputChanged('');
      inp.focus();
    }}

    function onUrlInputChanged(val) {{
      const clearBtn = document.getElementById('clearUrlBtn');
      const badge = document.getElementById('platformDetectBadge');
      const iconSlot = document.getElementById('urlIconSlot');
      const clean = val.toLowerCase().trim();

      if (clean.length > 0) {{
        clearBtn.classList.remove('hidden');
      }} else {{
        clearBtn.classList.add('hidden');
      }}

      if (clean.includes('tiktok.com')) {{
        badge.innerText = '🎵 TikTok Live / Video';
        iconSlot.innerText = '🎵';
      }} else if (clean.includes('youtube.com') || clean.includes('youtu.be')) {{
        badge.innerText = '▶️ YouTube Video / Live';
        iconSlot.innerText = '▶️';
      }} else if (clean.includes('twitch.tv')) {{
        badge.innerText = '🟣 Twitch Stream';
        iconSlot.innerText = '🟣';
      }} else if (clean.includes('kick.com')) {{
        badge.innerText = '🟢 Kick Live';
        iconSlot.innerText = '🟢';
      }} else if (clean.includes('.m3u8')) {{
        badge.innerText = '⚡ HLS Live Stream';
        iconSlot.innerText = '⚡';
      }} else {{
        badge.innerText = '⚡ Universal Sniffer';
        iconSlot.innerText = '⚡';
      }}
    }}

    async function onPasteClick() {{
      const res = await pyCall('get_clipboard_text');
      let text = (res && res.text) ? res.text.trim() : '';
      if (!text) {{
        try {{
          text = (await navigator.clipboard.readText() || '').trim();
        }} catch(e) {{}}
      }}
      if (text) {{
        const inp = document.getElementById('streamUrlInput');
        inp.value = text;
        onUrlInputChanged(text);
        showToast('Pasted URL from clipboard', '📋');
      }} else {{
        showToast('Clipboard is empty or inaccessible', '⚠️');
      }}
    }}

    function setPreset(url) {{
      const inp = document.getElementById('streamUrlInput');
      inp.value = url;
      onUrlInputChanged(url);
      switchTab('studio');
      onAnalyzeClick();
    }}

    async function onAnalyzeClick() {{
      const url = document.getElementById('streamUrlInput').value.trim();
      if (!url) {{
        showToast('Please enter or paste a stream URL first', '⚠️');
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
          alert('Resolution Error: ' + (data ? data.error : 'Stream is offline or manifest unavailable.'));
          return;
        }}

        currentStream = data;
        document.getElementById('streamTitle').innerText = data.title || 'Untitled Stream';
        document.getElementById('uploaderBadge').innerText = data.uploader ? '@' + data.uploader : '@live';
        document.getElementById('liveStatusBadge').innerText = data.is_live ? 'LIVE STREAM' : 'VOD VIDEO';

        if (data.platform) {{
          const pb = document.getElementById('platformBadge');
          pb.innerText = `${{data.platform.icon || '⚡'}} ${{data.platform.name || 'Universal'}}`;
          document.getElementById('inspPlatform').innerText = data.platform.name || 'Universal';
        }}

        // Populate side inspector window
        document.getElementById('inspProtocol').innerText = data.is_live ? 'HLS (m3u8)' : 'HTTPS';
        document.getElementById('inspContainer').innerText = (data.formats && data.formats[0]) ? (data.formats[0].ext || 'mp4') : 'mp4';
        document.getElementById('inspFormats').innerText = (data.formats || []).length;
        document.getElementById('inspUrlBox').innerText = data.direct_url || data.preview_url || url;

        renderFormats(data.formats || []);

        const previewTarget = data.preview_url || data.direct_url;
        if (previewTarget) {{
          playStream(previewTarget);
        }}

        playerSection.classList.remove('hidden');
        playerSection.classList.add('tab-view-animated');
        showToast('Stream resolved successfully!', '✓');
      }} catch (e) {{
        loader.classList.add('hidden');
        alert('Failed to resolve stream: ' + e);
      }}
    }}

    function renderFormats(formats) {{
      const container = document.getElementById('formatsList');
      const badge = document.getElementById('formatsCountBadge');
      container.innerHTML = '';
      badge.innerText = `${{formats.length}} formats`;

      if (!formats || formats.length === 0) {{
        container.innerHTML = '<div class="text-xs text-slate-300 py-3 mono col-span-full">No multi-bitrate format details available</div>';
        return;
      }}

      formats.forEach((f, idx) => {{
        const card = document.createElement('div');
        card.className = 'glass-card hover:border-slate-500 p-2.5 rounded-xl flex items-center justify-between cursor-pointer transition-all min-w-0';
        card.onclick = () => {{
          playStream(f.url);
          showToast(`Switched preview to ${{f.id || 'format'}}`);
        }};

        const resText = f.height ? `${{f.height}}p` : (f.ext || 'mp4');
        const brText = f.tbr ? `${{f.tbr}} kbps` : (f.protocol || 'hls');

        card.innerHTML = `
          <div class="overflow-hidden min-w-0">
            <div class="text-xs font-semibold text-white mono flex items-center gap-1.5 truncate">
              <span class="w-1.5 h-1.5 rounded-full bg-blue-500 shrink-0"></span>
              <span class="truncate">${{f.id || 'stream-' + (idx+1)}}</span>
            </div>
            <div class="text-xs text-slate-300 mono mt-0.5 truncate">${{resText}} • ${{brText}}</div>
          </div>
          <div class="flex gap-1.5 shrink-0 ml-2" onclick="event.stopPropagation()">
            <button onclick="pyCall('copy_to_clipboard', '${{f.url}}'); showToast('Format URL Copied!', '📋');" class="btn-secondary px-2.5 py-1 rounded-lg text-xs mono text-blue-400">
              Copy
            </button>
            <button onclick="triggerDownloadDirect('${{f.url}}', '${{f.id || 'fmt'}}');" class="btn-primary px-3 py-1 rounded-lg text-xs font-bold" title="Download Format">
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
        hls = new Hls({{ enableWorker: true, lowLatencyMode: true }});
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
      showToast('Cleared completed tasks from queue', '🧹');
    }}

    function copyStreamUrl() {{
      if (!currentStream) return;
      const u = currentStream.direct_url || (currentStream.formats && currentStream.formats[0] ? currentStream.formats[0].url : '');
      if (u) {{
        pyCall('copy_to_clipboard', u);
        showToast('Stream URL copied to clipboard!', '📋');
      }}
    }}

    function playInExternalPlayer() {{
      if (!currentStream) return;
      const u = currentStream.direct_url || (currentStream.formats && currentStream.formats[0] ? currentStream.formats[0].url : '');
      if (u) {{
        pyCall('play_in_external_player', u);
        showToast('Launching external media player...', '▶');
      }}
    }}

    async function onSelectFolderClick() {{
      const res = await pyCall('select_folder');
      if (res && res.folder) {{
        document.getElementById('saveFolderInput').value = res.folder;
        document.getElementById('settingsDlDir').value = res.folder;
        document.getElementById('hdrDlDir').innerText = res.folder;
        showToast('Download destination updated!', '📁');
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

    // =========================================================================
    // HERO BUTTON: START <-> STOP DOWNLOAD STATE CONTROLLER & TELEMETRY HUD
    // =========================================================================

    function formatSeconds(secs) {{
      const s = Math.floor(secs);
      const hrs = Math.floor(s / 3600);
      const mins = Math.floor((s % 3600) / 60);
      const remSecs = s % 60;
      if (hrs > 0) {{
        return `${{String(hrs).padStart(2, '0')}}:${{String(mins).padStart(2, '0')}}:${{String(remSecs).padStart(2, '0')}}`;
      }}
      return `${{String(mins).padStart(2, '0')}}:${{String(remSecs).padStart(2, '0')}}`;
    }}

    function setHeroButtonToRecording(jobId, isLive) {{
      activeStudioJobId = jobId;
      activeStudioStartTime = Date.now();

      const btn = document.getElementById('heroDownloadBtn');
      const label = document.getElementById('heroBtnLabel');
      const theaterBtn = document.getElementById('theaterDownloadBtn');
      const hud = document.getElementById('studioLiveHud');

      // Update right side window
      openRightPanelTab('hud');
      document.getElementById('sideHudActiveCard').classList.remove('hidden');
      document.getElementById('sideHudActiveCard').classList.add('tab-view-animated');
      document.getElementById('sideHudIdleCard').classList.add('hidden');
      document.getElementById('sideLiveTitle').innerText = (currentStream && currentStream.title) ? currentStream.title : 'Live Stream Capture';

      btn.className = 'btn-danger w-full sm:w-auto px-10 py-3.5 rounded-xl text-sm font-bold flex items-center justify-center gap-2 cursor-pointer shadow-lg animate-pulse shrink-0';
      label.innerText = isLive ? 'STOP RECORDING (00:00)' : 'STOP DOWNLOAD (00:00)';
      if (theaterBtn) {{
        theaterBtn.className = 'btn-danger px-4 py-2 rounded-xl text-xs font-bold flex items-center gap-1.5 cursor-pointer';
        theaterBtn.innerText = '⏹️ Stop';
      }}

      hud.classList.remove('hidden');
      hud.classList.add('tab-view-animated');
      document.getElementById('hudLiveDot').innerText = isLive ? 'RECORDING LIVE STREAM' : 'DOWNLOADING VIDEO';
      document.getElementById('hudStreamTitle').innerText = (currentStream && currentStream.title) ? currentStream.title : 'Live Stream Capture';

      if (activeStudioTimerInterval) clearInterval(activeStudioTimerInterval);
      activeStudioTimerInterval = setInterval(() => {{
        if (!activeStudioStartTime) return;
        const elapsed = (Date.now() - activeStudioStartTime) / 1000;
        const formatted = formatSeconds(elapsed);
        document.getElementById('hudElapsed').innerText = formatted;
        document.getElementById('sideLiveTime').innerText = formatted;
        if (activeStudioJobId) {{
          label.innerText = isLive ? `STOP RECORDING (${{formatted}})` : `STOP DOWNLOAD (${{formatted}})`;
        }}
      }}, 1000);
    }}

    function resetHeroButtonToIdle(completedPath = null) {{
      activeStudioJobId = null;
      if (activeStudioTimerInterval) {{
        clearInterval(activeStudioTimerInterval);
        activeStudioTimerInterval = null;
      }}

      const btn = document.getElementById('heroDownloadBtn');
      const label = document.getElementById('heroBtnLabel');
      const theaterBtn = document.getElementById('theaterDownloadBtn');
      const hud = document.getElementById('studioLiveHud');

      document.getElementById('sideHudActiveCard').classList.add('hidden');
      document.getElementById('sideHudIdleCard').classList.remove('hidden');

      btn.className = 'btn-primary w-full sm:w-auto px-10 py-3.5 rounded-xl text-sm font-bold flex items-center justify-center gap-2 cursor-pointer shadow-lg transition-all shrink-0';
      label.innerText = 'START DOWNLOAD';
      if (theaterBtn) {{
        theaterBtn.className = 'btn-primary px-4 py-2 rounded-xl text-xs font-bold flex items-center gap-1.5 cursor-pointer';
        theaterBtn.innerText = '⬇️ Download Best';
      }}

      if (completedPath) {{
        document.getElementById('hudStatusDesc').innerText = '✓ Finished & Container Verified';
        document.getElementById('hudFile').innerText = completedPath;
        document.getElementById('hudStopBtn').classList.add('hidden');
      }} else {{
        hud.classList.add('hidden');
      }}
    }}

    async function onHeroDownloadBtnClick() {{
      if (activeStudioJobId) {{
        await stopActiveStudioDownload();
      }} else {{
        await startDownloadCurrent('custom');
      }}
    }}

    async function stopActiveStudioDownload() {{
      if (!activeStudioJobId) return;
      const targetId = activeStudioJobId;
      const label = document.getElementById('heroBtnLabel');
      const hudStopBtn = document.getElementById('hudStopBtn');

      label.innerText = '⏳ Finalizing & Repairing Container...';
      hudStopBtn.innerText = '⏳ Finalizing...';
      hudStopBtn.disabled = true;
      showToast('Stopping stream and running FFmpeg faststart fixup...', '⏹️');

      const res = await pyCall('stop_job', targetId);
      const savedPath = (res && res.saved_path) ? res.saved_path : null;
      resetHeroButtonToIdle(savedPath);
      pollActiveDownloads();

      if (savedPath) {{
        showToast('Stream recording cleanly finalized and repaired!', '✓');
      }} else {{
        showToast('Download stopped.', '⏹️');
      }}
    }}

    async function startDownloadCurrent(type) {{
      if (activeStudioJobId) {{
        await stopActiveStudioDownload();
        return;
      }}

      const inputUrl = document.getElementById('streamUrlInput').value.trim();
      const targetUrl = (currentStream && currentStream.direct_url) ? currentStream.direct_url : inputUrl;
      if (!targetUrl) {{
        showToast('Please enter a stream URL first', '⚠️');
        return;
      }}

      const title = currentStream ? currentStream.title : '';
      const uploader = currentStream ? currentStream.uploader : '';
      const isLive = currentStream ? Boolean(currentStream.is_live) : false;
      const q = document.getElementById('qualitySelect').value;
      const isAudio = (type === 'audio') || document.getElementById('chkAudioOnly').checked || q.startsWith('audio_');
      const container = document.getElementById('containerSelect').value;
      const customFolder = document.getElementById('saveFolderInput').value;

      showToast(`Starting ${{isLive ? 'Live Recording' : 'Download'}} (${{isAudio ? 'Audio MP3' : 'Video'}})...`, '⬇️');
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
        setHeroButtonToRecording(res.job_id, isLive);
        pollActiveDownloads();
      }}
    }}

    async function triggerDownloadDirect(url, formatId) {{
      const title = currentStream ? currentStream.title : formatId;
      const uploader = currentStream ? currentStream.uploader : '';
      const isLive = currentStream ? Boolean(currentStream.is_live) : false;
      const res = await pyCall('start_download', {{
        url: url,
        title: title,
        uploader: uploader,
        is_live: isLive,
        quality: 'max'
      }});
      if (res && res.job_id) {{
        setHeroButtonToRecording(res.job_id, isLive);
        showToast('Started downloading format ' + formatId, '⬇️');
        pollActiveDownloads();
      }}
    }}

    async function pollActiveDownloads() {{
      try {{
        const jobs = await pyCall('get_active_jobs') || [];
        const container = document.getElementById('activeDownloadsContainer');
        const list = document.getElementById('activeJobsList');
        const countLbl = document.getElementById('activeCount');
        const navCount = document.getElementById('navQueueCount');
        const sideQueueCount = document.getElementById('rightQueueCount');
        const queueIndicator = document.getElementById('queueIndicator');

        const running = jobs.filter(j => !j.completed);
        navCount.innerText = running.length;
        if (sideQueueCount) sideQueueCount.innerText = running.length;

        if (running.length > 0) {{
          queueIndicator.classList.remove('hidden');
          queueIndicator.classList.add('flex');
        }} else {{
          queueIndicator.classList.add('hidden');
          queueIndicator.classList.remove('flex');
        }}

        // Sync active studio job telemetry in center and right windows
        if (activeStudioJobId) {{
          const currentJob = jobs.find(j => j.id === activeStudioJobId);
          if (currentJob) {{
            if (currentJob.completed) {{
              resetHeroButtonToIdle(currentJob.saved_path);
            }} else {{
              if (currentJob.size && currentJob.size !== '--') {{
                document.getElementById('hudSize').innerText = currentJob.size;
                document.getElementById('sideLiveSize').innerText = currentJob.size;
              }}
              if (currentJob.speed && currentJob.speed !== '--') {{
                document.getElementById('hudSpeed').innerText = currentJob.speed;
              }}
              if (currentJob.saved_path) {{
                document.getElementById('hudFile').innerText = currentJob.saved_path;
              }}
            }}
          }}
        }}

        // Render queue in right window
        countLbl.innerText = `${{running.length}} active`;
        list.innerHTML = '';
        if (jobs.length === 0) {{
          list.innerHTML = '<div class="text-xs text-slate-400 py-6 text-center mono">No active downloads running</div>';
          return;
        }}

        jobs.slice().reverse().forEach(j => {{
          const item = document.createElement('div');
          item.className = 'glass-card p-3 rounded-xl flex flex-col gap-2 min-w-0';
          
          let badgeText = j.status;
          let statusColor = 'text-blue-400';
          const isDone = j.completed && j.success;
          const isFail = j.completed && !j.success;

          if (isDone) {{ statusColor = 'text-emerald-400'; badgeText = '✓ FINISHED'; }}
          else if (isFail) {{ statusColor = 'text-rose-400'; badgeText = '✕ FAILED'; }}
          else if (j.is_live) {{ statusColor = 'text-rose-400'; badgeText = '● LIVE CAPTURE'; }}

          const barWidth = isDone ? '100%' : (j.percent > 0 ? j.percent + '%' : (j.is_live ? '100%' : '15%'));
          const barClass = isDone ? 'bg-emerald-500' : (j.is_live ? 'bg-rose-500 progress-shimmer' : 'bg-blue-600 progress-shimmer');

          item.innerHTML = `
            <div class="flex items-center justify-between text-xs">
              <span class="mono font-bold ${{statusColor}}">${{badgeText}}</span>
              <span class="mono text-slate-300">${{j.size || '--'}}</span>
            </div>
            <div class="font-semibold text-white text-xs truncate max-w-full" title="${{j.title || j.url}}">
              ${{j.title || j.url}}
            </div>
            <div class="w-full bg-slate-950 rounded-full h-1.5 overflow-hidden border border-white/5">
              <div class="${{barClass}}" style="width: ${{barWidth}}"></div>
            </div>
            <div class="flex items-center justify-between text-xs text-slate-300 mono">
              <span class="truncate">${{j.speed || '--'}}</span>
              <div class="flex gap-2 shrink-0">
                ${{!j.completed ? `<button onclick="pyCall('stop_job', '${{j.id}}'); pollActiveDownloads();" class="text-rose-400 hover:text-white cursor-pointer font-medium">Stop</button>` : ''}}
                ${{j.saved_path ? `<button onclick="pyCall('open_file', '${{j.saved_path.replace(/\\\\/g, '\\\\\\\\')}}')" class="text-blue-400 hover:text-white cursor-pointer font-medium">Play</button>` : ''}}
              </div>
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
      const badge = document.getElementById('histTotalBadge');
      container.innerHTML = '';
      badge.innerText = `${{items.length}} Items`;

      if (!items || items.length === 0) {{
        container.innerHTML = '<div class="text-xs text-slate-300 py-10 text-center mono">No media downloads recorded in library yet.</div>';
        return;
      }}

      items.slice().reverse().forEach(h => {{
        const row = document.createElement('div');
        row.className = 'glass-card p-3.5 rounded-xl flex items-center justify-between gap-3 border border-white/5 min-w-0';
        const isAudio = h.media_type === 'audio';
        const icon = isAudio ? '🎵' : (h.media_type === 'live' ? '🔴' : '🎬');
        row.innerHTML = `
          <div class="flex items-center gap-3 min-w-0">
            <span class="text-xl shrink-0">${{icon}}</span>
            <div class="min-w-0">
              <div class="font-bold text-white text-xs truncate max-w-lg">${{h.title || 'Downloaded Item'}}</div>
              <div class="text-xs text-slate-300 mono truncate mt-0.5">${{h.timestamp ? h.timestamp.slice(0, 16) : ''}} • ${{h.filename || ''}}</div>
            </div>
          </div>
          <div class="flex gap-2 shrink-0 ml-2">
            ${{h.filename ? `<button onclick="pyCall('open_file', '${{h.filename.replace(/\\\\/g, '\\\\\\\\')}}')" class="btn-primary px-3 py-1 rounded-lg text-xs font-semibold">▶ Play</button>` : ''}}
            ${{h.filename ? `<button onclick="pyCall('open_folder', '${{h.filename.replace(/\\\\/g, '\\\\\\\\')}}')" class="btn-secondary px-2.5 py-1 rounded-lg text-xs text-slate-200">📂 Reveal</button>` : ''}}
            ${{h.filename ? `<button onclick="pyCall('copy_to_clipboard', '${{h.filename.replace(/\\\\/g, '\\\\\\\\')}}'); showToast('Path copied!', '📋');" class="btn-secondary px-2.5 py-1 rounded-lg text-xs text-slate-300">📋</button>` : ''}}
          </div>
        `;
        container.appendChild(row);
      }});
    }}

    function updateBatchUrlCount() {{
      const txt = document.getElementById('batchUrlsInput').value.trim();
      const urls = txt.split('\\n').map(u => u.trim()).filter(u => u.startsWith('http'));
      document.getElementById('batchCountBadge').innerText = `${{urls.length}} valid URLs detected`;
    }}

    async function onSubmitBatchClick() {{
      const txt = document.getElementById('batchUrlsInput').value.trim();
      const urls = txt.split('\\n').map(u => u.trim()).filter(u => u.startsWith('http'));
      if (urls.length === 0) {{
        showToast('Please enter valid HTTP(S) URLs (one per line)', '⚠️');
        return;
      }}
      const q = document.getElementById('batchQualitySelect').value;
      const res = await pyCall('batch_download', {{ urls: urls, quality: q }});
      if (res && res.count) {{
        showToast(`Queued ${{res.count}} batch tasks!`, '🚀');
        document.getElementById('batchUrlsInput').value = '';
        updateBatchUrlCount();
        openRightPanelTab('queue');
        pollActiveDownloads();
      }}
    }}

    async function loadWatchlist() {{
      const list = await pyCall('get_watchlist') || [];
      const container = document.getElementById('watchlistContainer');
      const count = document.getElementById('watchlistCount');
      const navWatch = document.getElementById('navWatchCount');
      container.innerHTML = '';
      count.innerText = `${{list.length}} creators`;
      if (navWatch) navWatch.innerText = list.length;

      if (!list || list.length === 0) {{
        container.innerHTML = '<div class="text-xs text-slate-300 py-6 text-center mono col-span-full">No creators currently monitored. Add one above!</div>';
        return;
      }}

      list.forEach(c => {{
        const row = document.createElement('div');
        row.className = 'glass-card p-3.5 rounded-xl flex items-center justify-between text-xs border border-white/5 min-w-0';
        row.innerHTML = `
          <div class="flex items-center gap-3 min-w-0">
            <div class="w-8 h-8 rounded-full bg-slate-800 flex items-center justify-center font-bold text-blue-400 mono text-xs shrink-0">
              @
            </div>
            <div class="min-w-0">
              <div class="mono font-bold text-white text-xs truncate">${{c}}</div>
              <span id="watchStatus-${{c}}" class="text-xs text-slate-300 mono">Offline</span>
            </div>
          </div>
          <div class="flex gap-2 shrink-0 ml-2">
            <button onclick="onCheckCreatorClick('${{c}}')" class="btn-secondary px-3 py-1 rounded-lg text-xs font-semibold">Check</button>
            <button onclick="onRemoveWatchlistClick('${{c}}')" class="btn-secondary text-red-400 hover:text-white px-2.5 py-1 rounded-lg text-xs mono">✕</button>
          </div>
        `;
        container.appendChild(row);
      }});
    }}

    async function onAddWatchlistClick() {{
      const input = document.getElementById('watchdogInput');
      const val = input.value.trim().replace(/^@/, '');
      if (!val) return;
      await pyCall('add_to_watchlist', val);
      input.value = '';
      loadWatchlist();
      showToast(`Added @${{val}} to Watchlist!`, '✓');
    }}

    async function onRemoveWatchlistClick(creator) {{
      await pyCall('remove_from_watchlist', creator);
      loadWatchlist();
      showToast(`Removed @${{creator}}`, '✓');
    }}

    async function onCheckCreatorClick(creator) {{
      showToast(`Checking live status for @${{creator}}...`, '🔍');
      const res = await pyCall('check_creator_live', creator);
      const lbl = document.getElementById('watchStatus-' + creator);
      if (lbl) {{
        if (res && res.is_live) {{
          lbl.className = 'text-xs text-emerald-400 font-bold mono';
          lbl.innerText = '🔴 LIVE NOW!';
          if (res.stream_url) {{
            setPreset(res.stream_url);
          }}
        }} else {{
          lbl.className = 'text-xs text-slate-400 mono';
          lbl.innerText = 'Offline';
        }}
      }}
    }}

    async function checkAllWatchdogClick() {{
      const list = await pyCall('get_watchlist') || [];
      showToast(`Checking ${{list.length}} monitored creators...`, '🔄');
      for (const c of list) {{
        await onCheckCreatorClick(c);
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
      if (!path) {{
        showToast('Please select a video file first', '⚠️');
        return;
      }}
      showToast('Inspecting video container headers...', '🔍');
      const data = await pyCall('inspect_file_container', path);
      if (!data || data.error) {{
        alert('File Inspection Error: ' + (data ? data.error : 'File not accessible.'));
        return;
      }}

      document.getElementById('repairFileName').innerText = data.filename || path;
      document.getElementById('repairExt').innerText = data.extension || '--';
      document.getElementById('repairContainer').innerText = data.detected_container || 'unknown';
      document.getElementById('repairSize').innerText = data.size_formatted || '--';

      const badge = document.getElementById('repairStatusBadge');
      const notice = document.getElementById('repairNotice');
      if (data.is_mismatched) {{
        badge.className = 'text-xs font-bold mono px-2.5 py-0.5 rounded-md bg-amber-500/20 text-amber-300 border border-amber-500/40';
        badge.innerText = data.status_label || 'MISMATCH DETECTED';
        notice.innerText = 'Container discrepancy detected. StreamVortex will losslessly remux to a standards-compliant playable container with moov faststart headers.';
        notice.classList.remove('hidden');
      }} else {{
        badge.className = 'text-xs font-bold mono px-2.5 py-0.5 rounded-md bg-emerald-500/20 text-emerald-300 border border-emerald-500/30';
        badge.innerText = 'CONTAINER CLEAN';
        notice.innerText = 'Container header is consistent with file extension. You can still remux to faststart MP4 if web playback issues occur.';
      }}

      document.getElementById('repairCard').classList.remove('hidden');
    }}

    async function onExecuteRepairClick() {{
      const path = document.getElementById('repairPathInput').value.trim();
      if (!path) return;
      showToast('Remuxing and repairing container with FFmpeg...', '🛠️');
      const res = await pyCall('repair_container', path);
      if (res && res.repaired_path) {{
        alert('Repair Successful!\\n\\nSaved clean file:\\n' + res.repaired_path);
        onInspectRepairClick();
      }}
    }}

    async function loadHealth() {{
      const h = await pyCall('get_system_health');
      if (!h) return;
      const ytOk = h.ytdlp && (h.ytdlp.ok || h.ytdlp.found);
      const ffOk = h.ffmpeg && (h.ffmpeg.ok || h.ffmpeg.found);

      document.getElementById('healthYtdlp').innerText = ytOk ? '🟢 Ready (' + (h.ytdlp.version || 'Installed') + ')' : '🔴 Missing';
      document.getElementById('healthYtdlpPath').innerText = (h.ytdlp && h.ytdlp.path) || '--';

      document.getElementById('healthFfmpeg').innerText = ffOk ? '🟢 Ready (' + (h.ffmpeg.version ? h.ffmpeg.version.slice(0, 16) : 'Available') + ')' : '🔴 Missing';
      document.getElementById('healthFfmpegPath').innerText = (h.ffmpeg && h.ffmpeg.path) || '--';

      const diskGb = h.disk_free_gb ? `${{h.disk_free_gb.toFixed(1)}} GB` : '--';
      document.getElementById('healthDisk').innerText = diskGb;
      document.getElementById('hdrDiskText').innerText = diskGb;
      document.getElementById('sideDiskText').innerText = diskGb;
      document.getElementById('sideYtStatus').innerText = ytOk ? 'Ready' : 'Missing';
      document.getElementById('sideFfStatus').innerText = ffOk ? 'Ready' : 'Missing';
    }}

    window.addEventListener('DOMContentLoaded', () => {{
      // Smart Auto-Docking: on medium screens (<1200px), collapse right dock by default to give center workspace huge breathing room
      if (window.innerWidth < 1200) {{
        const rp = document.getElementById('rightSidebar');
        if (rp) rp.classList.add('dock-collapsed');
      }}

      // Global Keyboard Shortcuts
      window.addEventListener('keydown', (e) => {{
        if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {{
          e.preventDefault();
          onHeroDownloadBtnClick();
          return;
        }}
        // Zoom shortcuts: Ctrl + '=', Ctrl + '+', Ctrl + '-', Ctrl + '0'
        if (e.ctrlKey || e.metaKey) {{
          if (e.key === '=' || e.key === '+') {{
            e.preventDefault();
            applyZoom(currentZoom + ZOOM_STEP);
            return;
          }} else if (e.key === '-' || e.key === '_') {{
            e.preventDefault();
            applyZoom(currentZoom - ZOOM_STEP);
            return;
          }} else if (e.key === '0') {{
            e.preventDefault();
            resetZoom();
            return;
          }}
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
        if (e.key === 'Escape') {{
          document.getElementById('dragOverlay').classList.remove('active');
        }}
      }});

      // Global Drag & Drop Handler for URLs and media files
      let dragCounter = 0;
      window.addEventListener('dragenter', (e) => {{
        e.preventDefault();
        dragCounter++;
        document.getElementById('dragOverlay').classList.add('active');
      }});
      window.addEventListener('dragleave', (e) => {{
        e.preventDefault();
        dragCounter--;
        if (dragCounter <= 0) {{
          document.getElementById('dragOverlay').classList.remove('active');
          dragCounter = 0;
        }}
      }});
      window.addEventListener('dragover', (e) => {{
        e.preventDefault();
      }});
      window.addEventListener('drop', (e) => {{
        e.preventDefault();
        dragCounter = 0;
        document.getElementById('dragOverlay').classList.remove('active');

        let text = e.dataTransfer.getData('text/plain') || '';
        if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {{
          const file = e.dataTransfer.files[0];
          const filePath = file.path || file.name || '';
          if (filePath) text = filePath;
        }}
        text = text.trim().replace(/^["']|["']$/g, '');
        if (!text) return;

        if (text.startsWith('http://') || text.startsWith('https://')) {{
          document.getElementById('streamUrlInput').value = text;
          onUrlInputChanged(text);
          switchTab('studio');
          onAnalyzeClick();
          showToast('Dropped URL loaded for analysis', '✓');
        }} else if (text.match(/\\.(mp4|mkv|ts|flv|webm|m4a|aac|mp3|m3u8|part)$/i) || text.includes('\\\\') || text.includes('/')) {{
          document.getElementById('repairPathInput').value = text;
          switchTab('repair');
          onInspectRepairClick();
          showToast('Dropped media file loaded for container inspection', '✓');
        }}
      }});

      // Restore saved zoom from previous session
      try {{
        const savedZoom = parseFloat(localStorage.getItem('streamvortex_ui_zoom'));
        if (savedZoom && !isNaN(savedZoom)) {{
          applyZoom(savedZoom, false);
        }}
      }} catch (e) {{}}

      // Initialize state and start polling
      setTimeout(async () => {{
        const state = await pyCall('get_initial_state');
        if (state) {{
          if (state.download_dir) {{
            document.getElementById('saveFolderInput').value = state.download_dir;
            document.getElementById('hdrDlDir').innerText = state.download_dir;
            document.getElementById('settingsDlDir').value = state.download_dir;
          }}
          if (state.free_disk_gb) {{
            const diskText = `${{state.free_disk_gb}} GB`;
            document.getElementById('hdrDiskText').innerText = diskText;
            document.getElementById('sideDiskText').innerText = diskText;
          }}
          if (state.watchlist) {{
            document.getElementById('navWatchCount').innerText = state.watchlist.length;
          }}
        }}
        pollActiveDownloads();
      }}, 300);
    }});
  </script>
</body>
</html>
"""
