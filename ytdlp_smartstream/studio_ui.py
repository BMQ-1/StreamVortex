"""
StreamVortex Studio — Broadcast Control-Room Desktop UI.
Self-contained matte graphite workstation interface with zero external CSS dependency,
uniform 16px vector icons, real-time throughput oscilloscope, broadcast HLS/local monitor
with Mark-In/Mark-Out clipper, playlist selector, multi-platform creator watchdog,
ffprobe container inspector, live engine console, yt-dlp.conf editor, and Ctrl+K palette.
"""

import html
from .engine import find_ytdlp_conf, get_conf_download_dir


_STUDIO_HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>StreamVortex Studio</title>
  <link rel="icon" type="image/png" href="/icon.png">
  <script src="https://cdn.jsdelivr.net/npm/hls.js@1.5.8/dist/hls.min.js" defer></script>
  <style>
    :root {
      --bg-rail: #0b0c0f;
      --bg-canvas: #0f1115;
      --bg-surface: #15181e;
      --bg-raised: #1c2028;
      --bg-hover: #232833;
      --bg-input: #0c0e12;

      --hairline: rgba(237, 240, 247, 0.08);
      --hairline-strong: rgba(237, 240, 247, 0.14);
      --hairline-focus: rgba(79, 143, 247, 0.55);

      --text-1: #edf0f5;
      --text-2: #9ba2b0;
      --text-3: #6c7382;

      --primary-bg: #edf0f5;
      --primary-fg: #0b0c0f;
      --primary-hover: #ffffff;

      --tally: #e5484d;
      --tally-soft: rgba(229, 72, 77, 0.12);
      --tally-border: rgba(229, 72, 77, 0.30);

      --signal: #4f8ff7;
      --signal-soft: rgba(79, 143, 247, 0.12);
      --signal-border: rgba(79, 143, 247, 0.30);

      --ok: #3fb97a;
      --ok-soft: rgba(63, 185, 122, 0.12);
      --ok-border: rgba(63, 185, 122, 0.28);

      --warn: #e09f3e;
      --warn-soft: rgba(224, 159, 62, 0.12);
      --warn-border: rgba(224, 159, 62, 0.30);

      --ease: cubic-bezier(0.22, 1, 0.36, 1);
      --font-ui: "Segoe UI Variable Text", "Inter", -apple-system, BlinkMacSystemFont, "Segoe UI", system-ui, sans-serif;
      --font-mono: "Cascadia Code", "JetBrains Mono", Consolas, monospace;

      --r-sm: 5px;
      --r-md: 8px;
      --r-lg: 10px;
      --r-xl: 12px;
    }

    *, *::before, *::after {
      box-sizing: border-box;
      margin: 0;
      padding: 0;
    }

    html, body {
      height: 100%;
      width: 100%;
      overflow: hidden;
      background: var(--bg-canvas);
      color: var(--text-1);
      font-family: var(--font-ui);
      font-size: 13px;
      line-height: 1.45;
      -webkit-font-smoothing: antialiased;
      user-select: none;
    }

    input, textarea, select, pre, code {
      font-family: inherit;
      user-select: text;
    }

    .mono {
      font-family: var(--font-mono);
      font-variant-numeric: tabular-nums;
    }

    .tabular {
      font-variant-numeric: tabular-nums;
    }

    .hidden { display: none !important; }
    .truncate { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
    .min-w-0 { min-width: 0; }
    .flex-1 { flex: 1 1 0%; }
    .shrink-0 { flex-shrink: 0; }

    /* Scrollbars */
    ::-webkit-scrollbar { width: 6px; height: 6px; }
    ::-webkit-scrollbar-track { background: transparent; }
    ::-webkit-scrollbar-thumb { background: rgba(237, 240, 247, 0.12); border-radius: 3px; }
    ::-webkit-scrollbar-thumb:hover { background: rgba(237, 240, 247, 0.24); }

    /* Icons */
    .ic {
      width: 16px;
      height: 16px;
      stroke: currentColor;
      fill: none;
      stroke-width: 1.5;
      stroke-linecap: round;
      stroke-linejoin: round;
      flex-shrink: 0;
    }
    .ic-sm { width: 14px; height: 14px; }

    /* Shell Layout */
    .app-shell {
      display: flex;
      flex-direction: column;
      height: 100vh;
      width: 100vw;
    }

    /* Topbar */
    .topbar {
      height: 48px;
      background: var(--bg-rail);
      border-bottom: 1px solid var(--hairline);
      padding: 0 12px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
      flex-shrink: 0;
      z-index: 30;
    }
    .topbar-group {
      display: flex;
      align-items: center;
      gap: 8px;
      min-width: 0;
    }
    .brand {
      display: flex;
      align-items: center;
      gap: 10px;
      padding: 0 4px;
    }
    .brand-mark {
      width: 24px;
      height: 24px;
      border-radius: 6px;
      overflow: hidden;
      background: #141923;
      border: 1px solid var(--hairline-strong);
      display: flex;
      align-items: center;
      justify-content: center;
      flex-shrink: 0;
    }
    .brand-mark img { width: 100%; height: 100%; object-fit: cover; }
    .brand-name {
      font-size: 14px;
      font-weight: 600;
      color: var(--text-1);
      letter-spacing: -0.01em;
    }
    .brand-tag {
      font-size: 11px;
      color: var(--text-3);
      font-family: var(--font-mono);
      margin-left: 2px;
    }

    /* Command Palette Trigger */
    .cmd-trigger {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 24px;
      height: 30px;
      padding: 0 10px;
      background: var(--bg-surface);
      border: 1px solid var(--hairline);
      border-radius: var(--r-md);
      color: var(--text-3);
      font-size: 12px;
      cursor: pointer;
      transition: background-color 140ms var(--ease), border-color 140ms var(--ease), color 140ms var(--ease);
    }
    .cmd-trigger:hover {
      background: var(--bg-raised);
      border-color: var(--hairline-strong);
      color: var(--text-2);
    }
    .kbd {
      display: inline-flex;
      align-items: center;
      padding: 1px 5px;
      border-radius: var(--r-sm);
      background: var(--bg-raised);
      border: 1px solid var(--hairline-strong);
      color: var(--text-2);
      font-family: var(--font-mono);
      font-size: 11px;
      line-height: 1.3;
    }

    /* Buttons */
    .btn {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      gap: 7px;
      height: 32px;
      padding: 0 12px;
      border-radius: var(--r-md);
      font-size: 12.5px;
      font-weight: 500;
      border: 1px solid transparent;
      cursor: pointer;
      white-space: nowrap;
      transition: background-color 140ms var(--ease), border-color 140ms var(--ease), color 140ms var(--ease), transform 100ms var(--ease);
    }
    .btn:active:not(:disabled) { transform: scale(0.98); }
    .btn:disabled { opacity: 0.45; cursor: not-allowed; }
    .btn-lg { height: 38px; padding: 0 16px; font-size: 13px; }
    .btn-sm { height: 28px; padding: 0 9px; font-size: 12px; gap: 5px; }
    .btn-icon { width: 32px; height: 32px; padding: 0; }
    .btn-icon-sm { width: 28px; height: 28px; padding: 0; }

    .btn-primary {
      background: var(--primary-bg);
      color: var(--primary-fg);
      font-weight: 600;
    }
    .btn-primary:hover:not(:disabled) { background: var(--primary-hover); }

    .btn-secondary {
      background: var(--bg-raised);
      border-color: var(--hairline);
      color: var(--text-1);
      box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.05);
    }
    .btn-secondary:hover:not(:disabled) {
      background: var(--bg-hover);
      border-color: var(--hairline-strong);
    }

    .btn-ghost {
      background: transparent;
      color: var(--text-2);
    }
    .btn-ghost:hover:not(:disabled) {
      background: var(--bg-raised);
      color: var(--text-1);
    }

    .btn-tally {
      background: var(--tally);
      color: #ffffff;
      font-weight: 600;
    }
    .btn-tally:hover:not(:disabled) { background: #d43c41; }

    .btn-tally-soft {
      background: var(--tally-soft);
      border-color: var(--tally-border);
      color: #f37d81;
    }
    .btn-tally-soft:hover:not(:disabled) {
      background: rgba(229, 72, 77, 0.20);
      color: #ffffff;
    }

    .btn-signal-soft {
      background: var(--signal-soft);
      border-color: var(--signal-border);
      color: #8cb7fa;
    }
    .btn-signal-soft:hover:not(:disabled) {
      background: rgba(79, 143, 247, 0.20);
      color: #ffffff;
    }

    /* Status Pill & Tally Dot */
    .tally-dot {
      width: 6px;
      height: 6px;
      border-radius: 50%;
      background: var(--tally);
      display: inline-block;
      flex-shrink: 0;
    }
    .tally-dot.live {
      animation: tally-blink 1.6s ease-in-out infinite;
    }
    @keyframes tally-blink {
      0%, 100% { opacity: 1; }
      50% { opacity: 0.35; }
    }
    .status-dot {
      width: 6px;
      height: 6px;
      border-radius: 50%;
      display: inline-block;
      flex-shrink: 0;
    }
    .dot-ok { background: var(--ok); }
    .dot-warn { background: var(--warn); }
    .dot-err { background: var(--tally); }
    .dot-muted { background: var(--text-3); }

    .chip {
      display: inline-flex;
      align-items: center;
      gap: 6px;
      height: 24px;
      padding: 0 8px;
      border-radius: var(--r-sm);
      background: var(--bg-raised);
      border: 1px solid var(--hairline);
      font-size: 11.5px;
      color: var(--text-2);
      white-space: nowrap;
    }
    .chip-live {
      background: var(--tally-soft);
      border-color: var(--tally-border);
      color: #f3888b;
    }
    .chip-ok {
      background: var(--ok-soft);
      border-color: var(--ok-border);
      color: #69d49d;
    }
    .chip-warn {
      background: var(--warn-soft);
      border-color: var(--warn-border);
      color: #ebba6d;
    }
    .chip-signal {
      background: var(--signal-soft);
      border-color: var(--signal-border);
      color: #8cb7fa;
    }

    /* Workspace Body (3 Columns) */
    .workspace {
      flex: 1;
      display: flex;
      min-height: 0;
      overflow: hidden;
    }

    /* Left Rail */
    .left-rail {
      width: 232px;
      background: var(--bg-rail);
      border-right: 1px solid var(--hairline);
      display: flex;
      flex-direction: column;
      justify-content: space-between;
      flex-shrink: 0;
      overflow: hidden;
    }
    .left-rail.collapsed { display: none; }
    .rail-scroll {
      flex: 1;
      overflow-y: auto;
      padding: 12px;
      display: flex;
      flex-direction: column;
      gap: 20px;
    }
    .rail-section-label {
      font-size: 11.5px;
      font-weight: 500;
      color: var(--text-3);
      padding: 0 8px 6px 8px;
    }
    .nav-list {
      display: flex;
      flex-direction: column;
      gap: 2px;
    }
    .nav-btn {
      height: 34px;
      padding: 0 10px;
      border-radius: var(--r-md);
      background: transparent;
      border: 1px solid transparent;
      color: var(--text-2);
      font-size: 13px;
      font-weight: 400;
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 8px;
      cursor: pointer;
      width: 100%;
      text-align: left;
      transition: background-color 140ms var(--ease), color 140ms var(--ease);
    }
    .nav-btn-left {
      display: flex;
      align-items: center;
      gap: 10px;
      min-width: 0;
    }
    .nav-btn:hover {
      background: var(--bg-surface);
      color: var(--text-1);
    }
    .nav-btn.active {
      background: var(--bg-raised);
      border-color: var(--hairline);
      color: var(--text-1);
      font-weight: 500;
      box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.06);
    }
    .nav-btn .ic { color: var(--text-3); }
    .nav-btn.active .ic { color: var(--text-1); }
    .nav-count {
      font-family: var(--font-mono);
      font-size: 11px;
      color: var(--text-3);
    }

    .rail-footer {
      padding: 12px 14px;
      border-top: 1px solid var(--hairline);
      display: flex;
      flex-direction: column;
      gap: 8px;
    }
    .rail-stat-row {
      display: flex;
      align-items: center;
      justify-content: space-between;
      font-size: 12px;
      color: var(--text-2);
    }
    .rail-stat-val {
      display: inline-flex;
      align-items: center;
      gap: 6px;
      font-family: var(--font-mono);
      font-size: 11.5px;
      color: var(--text-1);
    }

    /* Center Stage */
    .center-stage {
      flex: 1;
      min-width: 0;
      overflow-y: auto;
      padding: 20px 24px 32px 24px;
      display: flex;
      flex-direction: column;
      gap: 16px;
    }
    .stage-inner {
      width: 100%;
      max-width: 1120px;
      margin: 0 auto;
      display: flex;
      flex-direction: column;
      gap: 16px;
    }

    /* Tab Panels */
    .tab-content {
      display: none;
      flex-direction: column;
      gap: 16px;
    }
    .tab-content.active {
      display: flex;
      animation: fadeRise 180ms var(--ease);
    }
    @keyframes fadeRise {
      from { opacity: 0; transform: translateY(4px); }
      to { opacity: 1; transform: translateY(0); }
    }

    /* Cards & Panels */
    .panel {
      background: var(--bg-surface);
      border: 1px solid var(--hairline);
      border-radius: var(--r-xl);
      padding: 18px 20px;
      display: flex;
      flex-direction: column;
      gap: 14px;
    }
    .panel-header {
      display: flex;
      align-items: flex-start;
      justify-content: space-between;
      gap: 12px;
      flex-wrap: wrap;
    }
    .panel-header > div:first-child {
      min-width: 0;
      flex: 1 1 260px;
    }
    .panel-title {
      font-size: 14.5px;
      font-weight: 500;
      color: var(--text-1);
      letter-spacing: -0.005em;
    }
    .panel-sub {
      font-size: 12.5px;
      color: var(--text-2);
      margin-top: 2px;
    }
    .divider {
      height: 1px;
      background: var(--hairline);
      width: 100%;
    }

    /* Inputs & Selects */
    .input, .select, .textarea {
      width: 100%;
      background: var(--bg-input);
      border: 1px solid var(--hairline-strong);
      border-radius: var(--r-md);
      color: var(--text-1);
      font-size: 13px;
      outline: none;
      transition: border-color 140ms var(--ease), background-color 140ms var(--ease);
    }
    .input, .select { height: 36px; padding: 0 12px; }
    .textarea { padding: 12px; resize: vertical; line-height: 1.5; }
    .input:focus, .select:focus, .textarea:focus {
      border-color: var(--hairline-focus);
      background: #0e1117;
    }
    .select { cursor: pointer; font-family: var(--font-ui) !important; font-size: 12.5px; }
    .select option { background: #15181e; color: var(--text-1); }

    .field {
      display: flex;
      flex-direction: column;
      gap: 6px;
      min-width: 0;
    }
    .field-label {
      font-size: 12px;
      color: var(--text-2);
      font-weight: 500;
      display: flex;
      align-items: center;
      justify-content: space-between;
    }

    /* Grid Helpers */
    .grid-2 { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 12px; }
    .grid-3 { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 12px; }
    .grid-4 { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 10px; }
    @media (max-width: 900px) {
      .grid-4 { grid-template-columns: repeat(2, minmax(0, 1fr)); }
      .grid-3 { grid-template-columns: repeat(2, minmax(0, 1fr)); }
    }
    @media (max-width: 680px) {
      .grid-2, .grid-3 { grid-template-columns: 1fr; }
    }

    /* Toggle Chips */
    .toggle-chip {
      display: flex;
      align-items: center;
      gap: 8px;
      padding: 8px 10px;
      background: var(--bg-raised);
      border: 1px solid var(--hairline);
      border-radius: var(--r-md);
      cursor: pointer;
      font-size: 12.5px;
      color: var(--text-2);
      transition: border-color 140ms var(--ease), color 140ms var(--ease);
    }
    .toggle-chip:hover { border-color: var(--hairline-strong); color: var(--text-1); }
    .toggle-chip input[type="checkbox"] {
      width: 14px;
      height: 14px;
      accent-color: var(--signal);
      cursor: pointer;
    }

    /* Clipboard Banner */
    .clip-banner {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
      padding: 10px 14px;
      background: var(--bg-surface);
      border: 1px solid var(--signal-border);
      border-radius: var(--r-lg);
    }

    /* Inline Error Banner */
    .alert-bar {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
      padding: 10px 14px;
      border-radius: var(--r-md);
      font-size: 12.5px;
      border: 1px solid var(--tally-border);
      background: var(--tally-soft);
      color: #f39ea1;
    }

    /* URL Command Bar */
    .url-bar-wrap {
      position: relative;
      display: flex;
      align-items: center;
      width: 100%;
    }
    .url-bar-input {
      height: 42px;
      padding-left: 36px;
      padding-right: 112px;
      font-family: var(--font-mono);
      font-size: 12.5px;
    }
    .url-bar-icon {
      position: absolute;
      left: 11px;
      color: var(--text-3);
      pointer-events: none;
      display: flex;
    }
    .url-bar-actions {
      position: absolute;
      right: 6px;
      display: flex;
      align-items: center;
      gap: 4px;
    }

    /* Broadcast Monitor (Visual Moment 1) */
    .monitor-frame {
      background: #07080a;
      border: 1px solid var(--hairline-strong);
      border-radius: var(--r-lg);
      overflow: hidden;
      display: flex;
      flex-direction: column;
    }
    .monitor-viewport {
      position: relative;
      width: 100%;
      aspect-ratio: 16 / 9;
      max-height: 400px;
      background: #040507;
      display: flex;
      align-items: center;
      justify-content: center;
    }
    .monitor-viewport video {
      width: 100%;
      height: 100%;
      object-fit: contain;
      background: #000000;
    }
    .monitor-hud-strip {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
      padding: 8px 12px;
      background: #0d0f14;
      border-top: 1px solid var(--hairline);
      font-size: 12px;
      flex-wrap: wrap;
    }

    /* Format Matrix Cards */
    .format-grid {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
      gap: 8px;
    }
    .format-card {
      background: var(--bg-raised);
      border: 1px solid var(--hairline);
      border-radius: var(--r-md);
      padding: 10px 12px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 8px;
      cursor: pointer;
      transition: border-color 140ms var(--ease), background-color 140ms var(--ease);
    }
    .format-card:hover {
      background: var(--bg-hover);
      border-color: var(--hairline-strong);
    }
    .format-card.selected {
      border-color: var(--signal-border);
      background: rgba(79, 143, 247, 0.08);
    }

    /* Live Capture HUD */
    .capture-hud {
      background: var(--bg-surface);
      border: 1px solid var(--tally-border);
      border-radius: var(--r-xl);
      padding: 16px 20px;
      display: flex;
      flex-direction: column;
      gap: 12px;
    }
    .stat-tile {
      background: var(--bg-input);
      border: 1px solid var(--hairline);
      border-radius: var(--r-md);
      padding: 10px 12px;
      display: flex;
      flex-direction: column;
      gap: 3px;
      min-width: 0;
    }
    .stat-label { font-size: 11.5px; color: var(--text-3); }
    .stat-val { font-size: 15px; font-weight: 500; color: var(--text-1); font-family: var(--font-mono); font-variant-numeric: tabular-nums; }

    /* Progress Bar */
    .progress-track {
      width: 100%;
      height: 5px;
      background: var(--bg-input);
      border-radius: 3px;
      overflow: hidden;
      border: 1px solid var(--hairline);
    }
    .progress-fill {
      height: 100%;
      background: var(--signal);
      border-radius: 3px;
      transition: width 220ms var(--ease);
    }
    .progress-fill.live { background: var(--tally); }
    .progress-fill.done { background: var(--ok); }
    .progress-fill.err { background: var(--tally); }

    /* Right Telemetry & Console Dock */
    .right-dock {
      width: 328px;
      background: var(--bg-rail);
      border-left: 1px solid var(--hairline);
      display: flex;
      flex-direction: column;
      flex-shrink: 0;
      overflow: hidden;
    }
    .right-dock.collapsed { display: none; }
    .dock-header {
      height: 42px;
      padding: 0 10px;
      border-bottom: 1px solid var(--hairline);
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 4px;
      flex-shrink: 0;
    }
    .dock-tabs {
      display: flex;
      align-items: center;
      gap: 2px;
    }
    .dock-tab {
      height: 28px;
      padding: 0 9px;
      border-radius: var(--r-sm);
      background: transparent;
      border: none;
      color: var(--text-3);
      font-size: 12px;
      font-weight: 500;
      cursor: pointer;
      transition: background-color 140ms var(--ease), color 140ms var(--ease);
    }
    .dock-tab:hover { color: var(--text-1); background: var(--bg-surface); }
    .dock-tab.active { color: var(--text-1); background: var(--bg-raised); }
    .dock-body {
      flex: 1;
      overflow-y: auto;
      padding: 14px;
      display: flex;
      flex-direction: column;
      gap: 12px;
    }
    .dock-footer {
      height: 36px;
      padding: 0 14px;
      border-top: 1px solid var(--hairline);
      display: flex;
      align-items: center;
      justify-content: space-between;
      font-size: 11.5px;
      color: var(--text-3);
      flex-shrink: 0;
    }

    /* Oscilloscope Chart (Visual Moment 2) */
    .scope-card {
      background: var(--bg-surface);
      border: 1px solid var(--hairline);
      border-radius: var(--r-lg);
      padding: 12px;
      display: flex;
      flex-direction: column;
      gap: 10px;
    }
    .scope-svg {
      width: 100%;
      height: 108px;
      display: block;
      background: var(--bg-input);
      border-radius: var(--r-sm);
      border: 1px solid var(--hairline);
    }

    /* Queue & List Rows */
    .list-stack {
      display: flex;
      flex-direction: column;
      gap: 8px;
    }
    .row-card {
      background: var(--bg-surface);
      border: 1px solid var(--hairline);
      border-radius: var(--r-lg);
      padding: 11px 12px;
      display: flex;
      flex-direction: column;
      gap: 8px;
    }
    .lib-row {
      background: var(--bg-raised);
      border: 1px solid var(--hairline);
      border-radius: var(--r-md);
      padding: 10px 12px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
    }
    .lib-row:hover { border-color: var(--hairline-strong); }

    /* Console Log Viewer */
    .console-box {
      flex: 1;
      min-height: 260px;
      background: var(--bg-input);
      border: 1px solid var(--hairline);
      border-radius: var(--r-md);
      padding: 10px;
      overflow-y: auto;
      font-family: var(--font-mono);
      font-size: 11.5px;
      line-height: 1.5;
      display: flex;
      flex-direction: column;
      gap: 3px;
      user-select: text;
    }
    .log-line { word-break: break-word; color: var(--text-2); }
    .log-line.error { color: #f3888b; }
    .log-line.warn { color: #ebba6d; }
    .log-line.success { color: #69d49d; }
    .log-ts { color: var(--text-3); margin-right: 6px; }

    /* Diagnostics Table */
    .diag-table {
      width: 100%;
      border-collapse: collapse;
      font-size: 12.5px;
    }
    .diag-table th, .diag-table td {
      text-align: left;
      padding: 9px 10px;
      border-bottom: 1px solid var(--hairline);
    }
    .diag-table th { color: var(--text-3); font-weight: 500; font-size: 12px; }
    .diag-table td { color: var(--text-1); }

    /* Drag Overlay */
    .drag-overlay {
      position: fixed;
      inset: 0;
      z-index: 60;
      background: rgba(11, 12, 15, 0.88);
      display: none;
      align-items: center;
      justify-content: center;
      padding: 32px;
      pointer-events: none;
    }
    .drag-overlay.active { display: flex; }
    .drag-box {
      background: var(--bg-surface);
      border: 1px dashed var(--signal);
      border-radius: var(--r-xl);
      padding: 32px 44px;
      text-align: center;
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: 8px;
    }

    /* Command Palette Modal */
    .modal-backdrop {
      position: fixed;
      inset: 0;
      z-index: 70;
      background: rgba(7, 8, 10, 0.72);
      display: none;
      align-items: flex-start;
      justify-content: center;
      padding-top: 12vh;
    }
    .modal-backdrop.open { display: flex; }
    .cmd-modal {
      width: 100%;
      max-width: 520px;
      background: var(--bg-surface);
      border: 1px solid var(--hairline-strong);
      border-radius: var(--r-xl);
      overflow: hidden;
      box-shadow: 0 20px 48px rgba(0, 0, 0, 0.55);
    }
    .cmd-input {
      width: 100%;
      height: 46px;
      padding: 0 16px;
      background: var(--bg-surface);
      border: none;
      border-bottom: 1px solid var(--hairline);
      color: var(--text-1);
      font-size: 14px;
      outline: none;
    }
    .cmd-list {
      max-height: 320px;
      overflow-y: auto;
      padding: 6px;
      display: flex;
      flex-direction: column;
      gap: 2px;
    }
    .cmd-item {
      height: 36px;
      padding: 0 12px;
      border-radius: var(--r-md);
      background: transparent;
      border: none;
      color: var(--text-2);
      font-size: 13px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      cursor: pointer;
      width: 100%;
      text-align: left;
    }
    .cmd-item:hover, .cmd-item.active {
      background: var(--bg-raised);
      color: var(--text-1);
    }

    /* Toast */
    .toast {
      position: fixed;
      bottom: 20px;
      right: 20px;
      z-index: 80;
      background: var(--bg-raised);
      border: 1px solid var(--hairline-strong);
      border-radius: var(--r-md);
      padding: 10px 14px;
      font-size: 12.5px;
      color: var(--text-1);
      display: none;
      align-items: center;
      gap: 8px;
      box-shadow: 0 12px 28px rgba(0, 0, 0, 0.45);
    }
    .toast.show { display: flex; animation: fadeRise 160ms var(--ease); }

    /* Dropzone */
    .dropzone {
      border: 1px dashed var(--hairline-strong);
      border-radius: var(--r-lg);
      background: var(--bg-input);
      padding: 24px 16px;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      gap: 6px;
      cursor: pointer;
      text-align: center;
      transition: border-color 140ms var(--ease), background-color 140ms var(--ease);
    }
    .dropzone:hover {
      border-color: var(--signal-border);
      background: var(--bg-raised);
    }

    /* Spinner */
    .spin {
      width: 16px;
      height: 16px;
      border: 2px solid var(--hairline-strong);
      border-top-color: var(--text-1);
      border-radius: 50%;
      animation: rot 0.75s linear infinite;
    }
    @keyframes rot { to { transform: rotate(360deg); } }

    /* Switch */
    .switch {
      position: relative;
      display: inline-flex;
      align-items: center;
      cursor: pointer;
      gap: 8px;
      font-size: 12.5px;
      color: var(--text-2);
    }
    .switch input { display: none; }
    .switch-track {
      width: 32px;
      height: 18px;
      border-radius: 9px;
      background: var(--bg-hover);
      border: 1px solid var(--hairline-strong);
      position: relative;
      transition: background-color 140ms var(--ease), border-color 140ms var(--ease);
    }
    .switch-track::after {
      content: "";
      position: absolute;
      top: 2px;
      left: 2px;
      width: 12px;
      height: 12px;
      border-radius: 50%;
      background: var(--text-2);
      transition: transform 140ms var(--ease), background-color 140ms var(--ease);
    }
    .switch input:checked + .switch-track {
      background: var(--signal-soft);
      border-color: var(--signal);
    }
    .switch input:checked + .switch-track::after {
      transform: translateX(14px);
      background: var(--signal);
    }
    .switch.tally input:checked + .switch-track {
      background: var(--tally-soft);
      border-color: var(--tally);
    }
    .switch.tally input:checked + .switch-track::after {
      background: var(--tally);
    }

    /* Subtabs */
    .seg-group {
      display: inline-flex;
      background: var(--bg-input);
      border: 1px solid var(--hairline);
      border-radius: var(--r-md);
      padding: 2px;
      gap: 2px;
    }
    .seg-btn {
      height: 26px;
      padding: 0 10px;
      border-radius: 6px;
      background: transparent;
      border: none;
      color: var(--text-3);
      font-size: 12px;
      font-weight: 500;
      cursor: pointer;
    }
    .seg-btn:hover { color: var(--text-1); }
    .seg-btn.active { background: var(--bg-raised); color: var(--text-1); }
  </style>
</head>
<body>

  <!-- Drag & Drop Overlay -->
  <div id="dragOverlay" class="drag-overlay">
    <div class="drag-box">
      <svg class="ic" style="width:28px;height:28px;color:var(--signal);" viewBox="0 0 24 24"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/></svg>
      <div style="font-size:15px;font-weight:500;">Drop stream URL or local media file</div>
      <div style="font-size:12px;color:var(--text-2);" class="mono">URLs open in Studio · Video files open in Container Repair</div>
    </div>
  </div>

  <!-- Command Palette (Ctrl+K) -->
  <div id="cmdPaletteBackdrop" class="modal-backdrop" onclick="if(event.target===this) closeCommandPalette()">
    <div class="cmd-modal">
      <input id="cmdPaletteInput" class="cmd-input" type="text" placeholder="Type a command or jump to a workspace..." oninput="renderCommandPalette(this.value)" onkeydown="onCmdPaletteKey(event)" />
      <div id="cmdPaletteList" class="cmd-list"></div>
    </div>
  </div>

  <div class="app-shell">

    <!-- Topbar -->
    <header class="topbar">
      <div class="topbar-group">
        <button onclick="toggleSidebar()" class="btn btn-ghost btn-icon" title="Toggle sidebar">
          <svg class="ic" viewBox="0 0 24 24"><rect x="3" y="3" width="18" height="18" rx="2"/><line x1="9" y1="3" x2="9" y2="21"/></svg>
        </button>
        <div class="brand">
          <div class="brand-mark">
            <img src="/icon.png" alt="StreamVortex" onerror="this.style.display='none';" />
          </div>
          <span class="brand-name">StreamVortex Studio</span>
          <span class="brand-tag">v2.0</span>
        </div>
        <button onclick="openCommandPalette()" class="cmd-trigger" title="Command palette">
          <span>Quick commands</span>
          <span class="kbd">Ctrl+K</span>
        </button>
      </div>

      <div class="topbar-group">
        <button id="clipWatchBtn" onclick="toggleClipboardWatch()" class="btn btn-ghost btn-sm" title="Watch clipboard for copied stream URLs">
          <span id="clipWatchDot" class="status-dot dot-muted"></span>
          <span>Clipboard watch</span>
        </button>

        <button onclick="pyCall('open_folder')" class="btn btn-ghost btn-sm" title="Open active download directory">
          <svg class="ic ic-sm" viewBox="0 0 24 24"><path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/></svg>
          <span id="hdrDlDir" class="mono truncate" style="max-width:150px;">__CONF_DIR__</span>
        </button>

        <span id="hdrDiskBadge" class="chip mono">
          <span id="hdrDiskText">-- GB</span>
        </span>

        <button id="queueIndicator" onclick="openRightPanelTab('queue')" class="btn btn-tally-soft btn-sm hidden">
          <span class="tally-dot live"></span>
          <span id="navQueueCount" class="mono">0</span>
          <span>active</span>
        </button>

        <button onclick="toggleRightPanel()" id="rightPanelToggleBtn" class="btn btn-secondary btn-icon" title="Toggle telemetry &amp; console dock">
          <svg class="ic" viewBox="0 0 24 24"><rect x="3" y="3" width="18" height="18" rx="2"/><line x1="15" y1="3" x2="15" y2="21"/></svg>
        </button>
      </div>
    </header>

    <!-- 3-Pane Workspace -->
    <div class="workspace">

      <!-- Left Navigation Rail -->
      <aside id="leftSidebar" class="left-rail">
        <div class="rail-scroll">
          <div>
            <div class="rail-section-label">Workspace</div>
            <nav class="nav-list">
              <button onclick="switchTab('studio')" id="tabBtn-studio" class="nav-btn active">
                <span class="nav-btn-left">
                  <svg class="ic" viewBox="0 0 24 24"><polygon points="5 3 19 12 5 21 5 3"/></svg>
                  <span class="truncate">Studio &amp; Sniffer</span>
                </span>
              </button>
              <button onclick="switchTab('batch')" id="tabBtn-batch" class="nav-btn">
                <span class="nav-btn-left">
                  <svg class="ic" viewBox="0 0 24 24"><line x1="8" y1="6" x2="21" y2="6"/><line x1="8" y1="12" x2="21" y2="12"/><line x1="8" y1="18" x2="21" y2="18"/><line x1="3" y1="6" x2="3.01" y2="6"/><line x1="3" y1="12" x2="3.01" y2="12"/><line x1="3" y1="18" x2="3.01" y2="18"/></svg>
                  <span class="truncate">Batch Queue</span>
                </span>
              </button>
              <button onclick="switchTab('watchdog')" id="tabBtn-watchdog" class="nav-btn">
                <span class="nav-btn-left">
                  <svg class="ic" viewBox="0 0 24 24"><path d="M4.9 19.1C1 15.2 1 8.8 4.9 4.9"/><path d="M7.8 16.2c-2.3-2.3-2.3-6.1 0-8.5"/><circle cx="12" cy="12" r="2"/><path d="M16.2 7.8c2.3 2.3 2.3 6.1 0 8.5"/><path d="M19.1 4.9C23 8.8 23 15.1 19.1 19"/></svg>
                  <span class="truncate">Creator Watchdog</span>
                </span>
                <span id="navWatchCount" class="nav-count">0</span>
              </button>
              <button onclick="switchTab('repair')" id="tabBtn-repair" class="nav-btn">
                <span class="nav-btn-left">
                  <svg class="ic" viewBox="0 0 24 24"><path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z"/></svg>
                  <span class="truncate">Container Repair</span>
                </span>
              </button>
              <button onclick="switchTab('library')" id="tabBtn-library" class="nav-btn">
                <span class="nav-btn-left">
                  <svg class="ic" viewBox="0 0 24 24"><path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/></svg>
                  <span class="truncate">Media Library</span>
                </span>
              </button>
              <button onclick="switchTab('settings')" id="tabBtn-settings" class="nav-btn">
                <span class="nav-btn-left">
                  <svg class="ic" viewBox="0 0 24 24"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"/></svg>
                  <span class="truncate">Engine &amp; Settings</span>
                </span>
              </button>
            </nav>
          </div>

          <div>
            <div class="rail-section-label">Test feeds</div>
            <div class="nav-list">
              <button onclick="setPreset('https://test-streams.mux.dev/x36xhzz/x36xhzz.m3u8')" class="nav-btn">
                <span class="nav-btn-left">
                  <svg class="ic ic-sm" viewBox="0 0 24 24"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/></svg>
                  <span class="truncate">Mux HLS manifest</span>
                </span>
              </button>
              <button onclick="setPreset('https://www.tiktok.com/@weathernewslive/live')" class="nav-btn">
                <span class="nav-btn-left">
                  <svg class="ic ic-sm" viewBox="0 0 24 24"><circle cx="12" cy="12" r="2"/><path d="M16.2 7.8c2.3 2.3 2.3 6.1 0 8.5"/><path d="M7.8 16.2c-2.3-2.3-2.3-6.1 0-8.5"/></svg>
                  <span class="truncate">TikTok Live probe</span>
                </span>
              </button>
              <button onclick="setPreset('https://www.youtube.com/watch?v=dQw4w9WgXcQ')" class="nav-btn">
                <span class="nav-btn-left">
                  <svg class="ic ic-sm" viewBox="0 0 24 24"><rect x="2" y="4" width="20" height="16" rx="3"/><polygon points="10 9 15 12 10 15 10 9"/></svg>
                  <span class="truncate">YouTube VOD probe</span>
                </span>
              </button>
            </div>
          </div>
        </div>

        <div class="rail-footer">
          <div class="rail-stat-row">
            <span>yt-dlp</span>
            <span class="rail-stat-val"><span id="sideYtDot" class="status-dot dot-ok"></span><span id="sideYtStatus">Ready</span></span>
          </div>
          <div class="rail-stat-row">
            <span>FFmpeg</span>
            <span class="rail-stat-val"><span id="sideFfDot" class="status-dot dot-ok"></span><span id="sideFfStatus">Ready</span></span>
          </div>
          <div class="rail-stat-row">
            <span>Storage</span>
            <span id="sideDiskText" class="rail-stat-val">-- GB</span>
          </div>
          <div style="display:flex;gap:6px;margin-top:4px;">
            <button onclick="switchTab('settings'); runInlineDiagnostics();" class="btn btn-secondary btn-sm flex-1">Diagnostics</button>
            <button onclick="openRightPanelTab('console')" class="btn btn-ghost btn-sm" title="Open engine console">Logs</button>
          </div>
        </div>
      </aside>

      <!-- Center Main Stage -->
      <main class="center-stage">
        <div class="stage-inner">

          <!-- Auto-Clipboard Detection Banner -->
          <div id="clipboardBanner" class="clip-banner hidden">
            <div style="display:flex;align-items:center;gap:10px;min-width:0;">
              <span class="chip chip-signal mono" id="clipBannerPlatform">Stream</span>
              <span id="clipBannerUrl" class="mono truncate" style="font-size:12px;color:var(--text-1);"></span>
            </div>
            <div style="display:flex;align-items:center;gap:6px;flex-shrink:0;">
              <button onclick="acceptClipboardUrl(false)" class="btn btn-primary btn-sm">Analyze</button>
              <button onclick="acceptClipboardUrl(true)" class="btn btn-secondary btn-sm">Quick Download</button>
              <button onclick="dismissClipboardBanner()" class="btn btn-ghost btn-icon-sm" title="Dismiss">
                <svg class="ic ic-sm" viewBox="0 0 24 24"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
              </button>
            </div>
          </div>

          <!-- Inline Error Alert -->
          <div id="inlineAlert" class="alert-bar hidden">
            <span id="inlineAlertText"></span>
            <button onclick="hideAlert()" class="btn btn-ghost btn-icon-sm" style="color:inherit;">
              <svg class="ic ic-sm" viewBox="0 0 24 24"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
            </button>
          </div>

          <!-- ============================================================= -->
          <!-- TAB 1: STUDIO & SNIFFER                                       -->
          <!-- ============================================================= -->
          <section id="tab-studio" class="tab-content active">

            <!-- Active Capture HUD -->
            <div id="studioLiveHud" class="capture-hud hidden">
              <div class="panel-header">
                <div style="display:flex;align-items:center;gap:10px;min-width:0;">
                  <span class="chip chip-live">
                    <span class="tally-dot live"></span>
                    <span id="hudLiveDot">Recording</span>
                  </span>
                  <span id="hudStreamTitle" class="panel-title truncate" style="max-width:440px;">Active capture</span>
                </div>
                <div style="display:flex;align-items:center;gap:8px;">
                  <span id="hudStatusDesc" class="mono" style="font-size:12px;color:var(--text-2);">Capturing stream</span>
                  <button onclick="stopActiveStudioDownload()" id="hudStopBtn" class="btn btn-tally btn-sm">
                    <svg class="ic ic-sm" viewBox="0 0 24 24"><rect x="6" y="6" width="12" height="12" rx="1"/></svg>
                    <span>Stop &amp; finalize</span>
                  </button>
                </div>
              </div>

              <div class="grid-4">
                <div class="stat-tile">
                  <span class="stat-label">Elapsed</span>
                  <span id="hudElapsed" class="stat-val">00:00</span>
                </div>
                <div class="stat-tile">
                  <span class="stat-label">Captured</span>
                  <span id="hudSize" class="stat-val">0.0 MB</span>
                </div>
                <div class="stat-tile">
                  <span class="stat-label">Throughput</span>
                  <span id="hudSpeed" class="stat-val">--</span>
                </div>
                <div class="stat-tile">
                  <span class="stat-label">Output</span>
                  <span id="hudFile" class="mono truncate" style="font-size:12px;color:var(--text-1);margin-top:2px;">Writing to disk</span>
                </div>
              </div>

              <div class="progress-track">
                <div id="hudProgressBar" class="progress-fill live" style="width: 100%;"></div>
              </div>

              <div style="display:flex;align-items:center;justify-content:space-between;font-size:12px;color:var(--text-3);" class="mono">
                <span>Auto-remux faststart active</span>
                <div style="display:flex;gap:12px;">
                  <button onclick="openRightPanelTab('console')" class="btn btn-ghost btn-sm">Inspect logs</button>
                  <button onclick="pyCall('open_folder')" class="btn btn-ghost btn-sm">Open folder</button>
                </div>
              </div>
            </div>

            <!-- Target URL Command Panel -->
            <div class="panel">
              <div class="panel-header">
                <div>
                  <div class="panel-title">Stream sniffer &amp; capture</div>
                  <div class="panel-sub">Paste any live channel, VOD, playlist, or direct HLS/DASH manifest</div>
                </div>
                <span id="platformDetectBadge" class="chip mono">Universal sniffer</span>
              </div>

              <div class="url-bar-wrap">
                <span class="url-bar-icon">
                  <svg class="ic" viewBox="0 0 24 24"><path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"/><path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"/></svg>
                </span>
                <input
                  type="text"
                  id="streamUrlInput"
                  placeholder="https://www.tiktok.com/@creator/live, YouTube URL, playlist, or .m3u8"
                  class="input url-bar-input"
                  oninput="onUrlInputChanged(this.value)"
                  onkeydown="if(event.key==='Enter') onAnalyzeClick()"
                />
                <div class="url-bar-actions">
                  <button onclick="clearUrlInput()" id="clearUrlBtn" class="btn btn-ghost btn-icon-sm hidden" title="Clear">
                    <svg class="ic ic-sm" viewBox="0 0 24 24"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
                  </button>
                  <button onclick="onPasteClick()" class="btn btn-secondary btn-sm">Paste</button>
                </div>
              </div>

              <div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap;">
                <button onclick="onAnalyzeClick()" id="analyzeBtn" class="btn btn-primary btn-lg flex-1">
                  <svg class="ic" viewBox="0 0 24 24"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
                  <span>Analyze stream</span>
                </button>
                <button onclick="onHeroDownloadBtnClick()" class="btn btn-secondary btn-lg">
                  <svg class="ic" viewBox="0 0 24 24"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>
                  <span>Quick download</span>
                </button>
              </div>

              <div style="display:flex;align-items:center;justify-content:space-between;font-size:11.5px;color:var(--text-3);flex-wrap:wrap;gap:8px;">
                <span>Multi-tier extractor with direct HLS bypass and browser sniffer fallback</span>
                <div style="display:flex;align-items:center;gap:8px;">
                  <span><span class="kbd">/</span> focus</span>
                  <span><span class="kbd">Ctrl+Enter</span> download</span>
                  <span><span class="kbd">Ctrl+K</span> commands</span>
                </div>
              </div>

              <div id="loader" class="hidden" style="display:flex;align-items:center;gap:10px;padding:12px 14px;background:var(--bg-input);border:1px solid var(--hairline);border-radius:var(--r-md);">
                <div class="spin"></div>
                <span style="font-size:12.5px;color:var(--text-2);">Resolving manifest, codecs, and bitrate variants...</span>
              </div>
            </div>

            <!-- Playlist Selector Panel (Auto-shown for Playlists) -->
            <div id="playlistSection" class="panel hidden">
              <div class="panel-header">
                <div class="min-w-0">
                  <div id="playlistTitle" class="panel-title truncate">Playlist</div>
                  <div id="playlistMeta" class="panel-sub mono">0 items</div>
                </div>
                <div style="display:flex;align-items:center;gap:6px;">
                  <button onclick="toggleAllPlaylistItems(true)" class="btn btn-secondary btn-sm">Select all</button>
                  <button onclick="toggleAllPlaylistItems(false)" class="btn btn-ghost btn-sm">None</button>
                  <button onclick="downloadSelectedPlaylist()" class="btn btn-primary btn-sm">Queue selected</button>
                </div>
              </div>
              <div id="playlistEntriesList" class="list-stack" style="max-height:320px;overflow-y:auto;"></div>
            </div>

            <!-- Broadcast Monitor & Format Matrix (Visual Moment 1) -->
            <div id="playerSection" class="panel hidden">
              <div class="panel-header">
                <div style="display:flex;flex-direction:column;gap:4px;min-width:0;">
                  <div style="display:flex;align-items:center;gap:6px;flex-wrap:wrap;">
                    <span id="platformBadge" class="chip mono">Universal</span>
                    <span id="liveStatusBadge" class="chip chip-live">
                      <span class="tally-dot live"></span>
                      <span id="liveStatusText">Live</span>
                    </span>
                    <span id="uploaderBadge" class="chip mono">@creator</span>
                    <span id="durationBadge" class="chip mono hidden">00:00</span>
                  </div>
                  <h2 id="streamTitle" style="font-size:16px;font-weight:500;color:var(--text-1);margin-top:2px;">Stream Title</h2>
                </div>

                <div style="display:flex;align-items:center;gap:6px;flex-wrap:wrap;">
                  <button onclick="startDownloadCurrent('video')" id="theaterDownloadBtn" class="btn btn-primary btn-sm">Download best</button>
                  <button onclick="startDownloadCurrent('audio')" class="btn btn-secondary btn-sm">Audio MP3</button>
                  <button onclick="copyStreamUrl()" class="btn btn-secondary btn-sm">Copy URL</button>
                  <button onclick="playInExternalPlayer()" class="btn btn-secondary btn-sm">VLC / MPV</button>
                  <button onclick="onAnalyzeClick()" class="btn btn-ghost btn-icon-sm" title="Refresh stream">
                    <svg class="ic ic-sm" viewBox="0 0 24 24"><polyline points="23 4 23 10 17 10"/><path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"/></svg>
                  </button>
                </div>
              </div>

              <!-- Matte Broadcast Monitor Bezel -->
              <div class="monitor-frame">
                <div class="monitor-viewport">
                  <video id="hlsVideo" controls autoplay muted playsinline></video>
                </div>
                <div class="monitor-hud-strip">
                  <div style="display:flex;align-items:center;gap:10px;" class="mono">
                    <span id="monitorSourceTag" style="color:var(--text-2);">Monitor ready</span>
                    <span id="monitorResTag" style="color:var(--text-3);">--</span>
                  </div>
                  <!-- Mark-In / Mark-Out Clip Controls -->
                  <div style="display:flex;align-items:center;gap:6px;">
                    <button onclick="markClipPoint('start')" class="btn btn-secondary btn-sm" title="Set clip start to current video timestamp">Mark In</button>
                    <button onclick="markClipPoint('end')" class="btn btn-secondary btn-sm" title="Set clip end to current video timestamp">Mark Out</button>
                    <button onclick="clearClipRange()" class="btn btn-ghost btn-sm" title="Clear clip timestamps">Reset clip</button>
                  </div>
                </div>
              </div>

              <!-- Discovered Formats Matrix -->
              <div>
                <div class="panel-header" style="margin-bottom:8px;">
                  <span style="font-size:12.5px;font-weight:500;color:var(--text-2);">Discovered streams &amp; bitrates <span id="formatsCountBadge" class="mono" style="color:var(--text-3);margin-left:6px;">0</span></span>
                  <span style="font-size:11.5px;color:var(--text-3);">Click card to preview · Download button captures that exact format</span>
                </div>
                <div id="formatsList" class="format-grid"></div>
              </div>
            </div>

            <!-- Download & Capture Configuration Panel -->
            <div class="panel">
              <div class="panel-header">
                <div>
                  <div class="panel-title">Capture configuration</div>
                  <div class="panel-sub">Quality profile, container target, clip range, and metadata pipeline</div>
                </div>
                <span class="chip mono">Config: __CONF_NAME__</span>
              </div>

              <div class="grid-3">
                <div class="field">
                  <label class="field-label">Quality profile</label>
                  <select id="qualitySelect" class="select mono">
                    <option value="max">Best available (4K / 2K / 1080p)</option>
                    <option value="1080p">1080p Full HD</option>
                    <option value="720p">720p HD</option>
                    <option value="480p">480p Compact</option>
                    <option value="audio_mp3">Audio MP3 (320 kbps)</option>
                    <option value="audio_m4a">Audio M4A (AAC)</option>
                    <option value="conf">Use yt-dlp.conf rule</option>
                  </select>
                </div>

                <div class="field">
                  <label class="field-label">Container</label>
                  <select id="containerSelect" class="select mono">
                    <option value="mp4">MP4 (Universal faststart)</option>
                    <option value="mkv">MKV (Matroska multi-track)</option>
                    <option value="webm">WebM (VP9 / Opus)</option>
                    <option value="ts">TS (Raw MPEG-TS)</option>
                    <option value="flv">FLV (Flash stream)</option>
                  </select>
                </div>

                <div class="field">
                  <label class="field-label">
                    <span>Clip trim (optional)</span>
                    <span class="mono" style="font-size:11px;color:var(--text-3);">HH:MM:SS</span>
                  </label>
                  <div style="display:flex;gap:6px;">
                    <input id="clipStartInput" type="text" class="input mono" placeholder="Start" style="font-size:12px;" />
                    <input id="clipEndInput" type="text" class="input mono" placeholder="End" style="font-size:12px;" />
                  </div>
                </div>
              </div>

              <div class="grid-4">
                <label class="toggle-chip">
                  <input type="checkbox" id="chkSubtitles" checked />
                  <span>Subtitles</span>
                </label>
                <label class="toggle-chip">
                  <input type="checkbox" id="chkAudioOnly" onchange="onAudioToggle()" />
                  <span>Audio only</span>
                </label>
                <label class="toggle-chip">
                  <input type="checkbox" id="chkMetadata" checked />
                  <span>Embed metadata</span>
                </label>
                <label class="toggle-chip">
                  <input type="checkbox" id="chkThumbnail" checked />
                  <span>Embed thumbnail</span>
                </label>
              </div>

              <div class="divider"></div>

              <div class="field">
                <label class="field-label">
                  <span>Destination directory</span>
                  <span class="mono" style="font-size:11px;color:var(--text-3);">Synced with yt-dlp.conf</span>
                </label>
                <div style="display:flex;gap:8px;align-items:center;">
                  <input type="text" id="saveFolderInput" value="__CONF_DIR__" class="input mono flex-1" readonly />
                  <button onclick="onSelectFolderClick()" class="btn btn-secondary">Browse</button>
                  <button onclick="pyCall('open_folder')" class="btn btn-ghost">Open</button>
                </div>
              </div>

              <div style="display:flex;align-items:center;justify-content:space-between;gap:12px;flex-wrap:wrap;padding-top:4px;">
                <label class="toggle-chip" style="padding:5px 10px;">
                  <input type="checkbox" id="chkSponsorblock" />
                  <span>Remove SponsorBlock segments</span>
                </label>

                <button onclick="onHeroDownloadBtnClick()" id="heroDownloadBtn" class="btn btn-primary btn-lg" style="min-width:196px;">
                  <svg class="ic" viewBox="0 0 24 24"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>
                  <span id="heroBtnLabel">Start download</span>
                </button>
              </div>
            </div>
          </section>

          <!-- ============================================================= -->
          <!-- TAB 2: BATCH QUEUE                                            -->
          <!-- ============================================================= -->
          <section id="tab-batch" class="tab-content">
            <div class="panel">
              <div class="panel-header">
                <div>
                  <div class="panel-title">Batch URL downloader</div>
                  <div class="panel-sub">Queue multiple videos or live streams with parallel worker concurrency</div>
                </div>
                <div style="display:flex;align-items:center;gap:8px;">
                  <span id="batchCountBadge" class="chip mono">0 valid URLs</span>
                  <button onclick="onLoadBatchFileClick()" class="btn btn-secondary btn-sm">Load .txt</button>
                  <button onclick="dedupeBatchUrls()" class="btn btn-ghost btn-sm">Deduplicate</button>
                </div>
              </div>

              <textarea
                id="batchUrlsInput"
                rows="10"
                placeholder="One URL per line&#10;https://www.youtube.com/watch?v=...&#10;https://www.tiktok.com/@creator/live&#10;https://twitch.tv/channel&#10;https://example.com/playlist.m3u8"
                class="textarea mono"
                oninput="updateBatchUrlCount()"
              ></textarea>

              <div class="grid-3">
                <div class="field">
                  <label class="field-label">Quality</label>
                  <select id="batchQualitySelect" class="select mono">
                    <option value="max">Best available</option>
                    <option value="1080p">1080p Full HD</option>
                    <option value="720p">720p HD</option>
                    <option value="audio_mp3">Audio MP3 (320k)</option>
                  </select>
                </div>
                <div class="field">
                  <label class="field-label">Container</label>
                  <select id="batchContainerSelect" class="select mono">
                    <option value="mp4">MP4</option>
                    <option value="mkv">MKV</option>
                    <option value="webm">WebM</option>
                  </select>
                </div>
                <div class="field">
                  <label class="field-label">Parallel workers</label>
                  <select id="batchConcurrencySelect" class="select mono">
                    <option value="1">1 (Sequential)</option>
                    <option value="2" selected>2 concurrent</option>
                    <option value="3">3 concurrent</option>
                    <option value="4">4 concurrent</option>
                  </select>
                </div>
              </div>

              <div style="display:flex;justify-content:flex-end;gap:8px;">
                <button onclick="document.getElementById('batchUrlsInput').value=''; updateBatchUrlCount();" class="btn btn-ghost">Clear</button>
                <button onclick="onSubmitBatchClick()" class="btn btn-primary btn-lg">Start batch queue</button>
              </div>
            </div>
          </section>

          <!-- ============================================================= -->
          <!-- TAB 3: CREATOR WATCHDOG                                       -->
          <!-- ============================================================= -->
          <section id="tab-watchdog" class="tab-content">
            <div class="panel">
              <div class="panel-header">
                <div>
                  <div class="panel-title">Creator live watchdog</div>
                  <div class="panel-sub">Background polling across TikTok, Twitch, Kick, and YouTube with automatic lossless capture</div>
                </div>
                <div style="display:flex;align-items:center;gap:10px;">
                  <span id="watchdogLastCycle" class="mono" style="font-size:11.5px;color:var(--text-3);">Idle</span>
                  <button onclick="checkAllWatchdogClick()" class="btn btn-secondary btn-sm">Check all now</button>
                </div>
              </div>

              <!-- Daemon Controls Bar -->
              <div style="display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:12px;padding:12px;background:var(--bg-input);border:1px solid var(--hairline);border-radius:var(--r-md);">
                <div style="display:flex;align-items:center;gap:18px;flex-wrap:wrap;">
                  <label class="switch tally">
                    <input type="checkbox" id="watchdogEnabledToggle" onchange="saveWatchdogConfig()" />
                    <span class="switch-track"></span>
                    <span>Background monitor</span>
                  </label>
                  <label class="switch">
                    <input type="checkbox" id="watchdogGlobalAutoRec" onchange="saveWatchdogConfig()" />
                    <span class="switch-track"></span>
                    <span>Auto-record all live</span>
                  </label>
                </div>
                <div style="display:flex;align-items:center;gap:8px;">
                  <span style="font-size:12px;color:var(--text-3);">Interval</span>
                  <select id="watchdogIntervalSelect" class="select mono" style="width:110px;height:28px;font-size:12px;" onchange="saveWatchdogConfig()">
                    <option value="30">30 sec</option>
                    <option value="60" selected>60 sec</option>
                    <option value="120">2 min</option>
                    <option value="300">5 min</option>
                  </select>
                </div>
              </div>

              <!-- Add Creator Row -->
              <div style="display:flex;gap:8px;flex-wrap:wrap;">
                <select id="watchdogPlatformSelect" class="select mono" style="width:130px;">
                  <option value="tiktok">TikTok</option>
                  <option value="twitch">Twitch</option>
                  <option value="kick">Kick</option>
                  <option value="youtube">YouTube</option>
                  <option value="generic">Direct URL</option>
                </select>
                <input
                  type="text"
                  id="watchdogInput"
                  placeholder="Creator handle or full channel URL..."
                  class="input mono flex-1"
                  onkeydown="if(event.key==='Enter') onAddWatchlistClick()"
                />
                <button onclick="onAddWatchlistClick()" class="btn btn-primary">Add creator</button>
              </div>

              <div class="divider"></div>

              <div class="panel-header">
                <span style="font-size:12.5px;color:var(--text-2);font-weight:500;">Monitored channels</span>
                <span id="watchlistCount" class="mono" style="font-size:12px;color:var(--text-3);">0 creators</span>
              </div>

              <div id="watchlistContainer" class="grid-2"></div>
            </div>
          </section>

          <!-- ============================================================= -->
          <!-- TAB 4: CONTAINER REPAIR & FFPROBE INSPECTOR                   -->
          <!-- ============================================================= -->
          <section id="tab-repair" class="tab-content">
            <div class="panel">
              <div class="panel-header">
                <div>
                  <div class="panel-title">Container inspector &amp; lossless repair</div>
                  <div class="panel-sub">Inspect codecs with ffprobe, normalize legacy FLV/MPEG-TS/part files to faststart MP4/MKV, or extract audio</div>
                </div>
                <button onclick="onScanRepairFolderClick()" class="btn btn-secondary btn-sm">Scan folder for issues</button>
              </div>

              <div id="repairDropZone" onclick="onSelectRepairFileClick()" class="dropzone">
                <svg class="ic" style="width:22px;height:22px;color:var(--text-3);" viewBox="0 0 24 24"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>
                <div style="font-size:13px;font-weight:500;color:var(--text-1);">Select a media file or drop anywhere in window</div>
                <div class="mono" style="font-size:11.5px;color:var(--text-3);">.mp4 · .mkv · .ts · .flv · .part · .webm · .mov</div>
              </div>

              <div style="display:flex;gap:8px;">
                <input
                  type="text"
                  id="repairPathInput"
                  placeholder="Path to media file..."
                  class="input mono flex-1"
                  onkeydown="if(event.key==='Enter') onInspectRepairClick()"
                />
                <button onclick="onSelectRepairFileClick()" class="btn btn-secondary">Browse</button>
                <button onclick="onInspectRepairClick()" class="btn btn-primary">Inspect</button>
              </div>

              <!-- Deep Inspection Result Card -->
              <div id="repairCard" class="hidden" style="background:var(--bg-raised);border:1px solid var(--hairline-strong);border-radius:var(--r-lg);padding:16px;display:flex;flex-direction:column;gap:14px;">
                <div class="panel-header">
                  <span id="repairFileName" class="mono truncate" style="font-size:13.5px;font-weight:500;max-width:520px;">video.mp4</span>
                  <span id="repairStatusBadge" class="chip mono">Inspected</span>
                </div>

                <div class="grid-4">
                  <div class="stat-tile">
                    <span class="stat-label">Extension / Magic</span>
                    <span class="stat-val" style="font-size:13px;"><span id="repairExt">mp4</span> / <span id="repairContainer">--</span></span>
                  </div>
                  <div class="stat-tile">
                    <span class="stat-label">Video stream</span>
                    <span id="repairVideoSpec" class="stat-val" style="font-size:13px;">--</span>
                  </div>
                  <div class="stat-tile">
                    <span class="stat-label">Audio stream</span>
                    <span id="repairAudioSpec" class="stat-val" style="font-size:13px;">--</span>
                  </div>
                  <div class="stat-tile">
                    <span class="stat-label">Size / Duration</span>
                    <span class="stat-val" style="font-size:13px;"><span id="repairSize">--</span> · <span id="repairDuration">--</span></span>
                  </div>
                </div>

                <div id="repairNotice" style="font-size:12px;color:var(--text-2);padding:10px 12px;background:var(--bg-input);border:1px solid var(--hairline);border-radius:var(--r-md);"></div>

                <div style="display:flex;align-items:center;justify-content:space-between;gap:10px;flex-wrap:wrap;">
                  <div style="display:flex;align-items:center;gap:8px;">
                    <span style="font-size:12px;color:var(--text-2);">Action</span>
                    <select id="repairTargetSelect" class="select mono" style="width:220px;height:32px;font-size:12px;">
                      <option value="mp4">Remux to MP4 (faststart)</option>
                      <option value="mkv">Remux to MKV (lossless)</option>
                      <option value="mp3">Extract Audio (MP3 320k)</option>
                      <option value="m4a">Extract Audio (M4A AAC)</option>
                    </select>
                  </div>
                  <div style="display:flex;gap:8px;">
                    <button onclick="previewRepairedFile()" class="btn btn-secondary">Preview in Studio</button>
                    <button onclick="onExecuteRepairClick()" id="executeRepairBtn" class="btn btn-primary">Run repair / convert</button>
                  </div>
                </div>
              </div>

              <!-- Batch Folder Scan Results -->
              <div id="folderScanResults" class="hidden" style="display:flex;flex-direction:column;gap:8px;">
                <div class="divider"></div>
                <div class="panel-header">
                  <span id="folderScanSummary" style="font-size:12.5px;color:var(--text-2);">Scanned folder</span>
                  <button onclick="repairAllMismatched()" id="repairAllBtn" class="btn btn-primary btn-sm hidden">Repair all mismatched</button>
                </div>
                <div id="folderScanList" class="list-stack" style="max-height:280px;overflow-y:auto;"></div>
              </div>
            </div>
          </section>

          <!-- ============================================================= -->
          <!-- TAB 5: MEDIA LIBRARY & LOCAL FILES                            -->
          <!-- ============================================================= -->
          <section id="tab-library" class="tab-content">
            <div class="panel">
              <div class="panel-header">
                <div>
                  <div class="panel-title">Media library</div>
                  <div class="panel-sub">Play recorded streams inline, reveal in Explorer, or send directly to Container Repair</div>
                </div>
                <div style="display:flex;align-items:center;gap:8px;">
                  <div class="seg-group">
                    <button id="libModeHistory" onclick="setLibraryMode('history')" class="seg-btn active">History</button>
                    <button id="libModeFolder" onclick="setLibraryMode('folder')" class="seg-btn">Downloads folder</button>
                  </div>
                  <button onclick="loadHistory()" class="btn btn-secondary btn-sm">Refresh</button>
                  <button onclick="pyCall('open_folder')" class="btn btn-ghost btn-sm">Explorer</button>
                </div>
              </div>

              <div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap;">
                <input
                  type="text"
                  id="libSearchInput"
                  placeholder="Filter by title, path, or format..."
                  class="input mono flex-1"
                  oninput="filterHistory()"
                />
                <div class="seg-group">
                  <button onclick="setLibraryTypeFilter('all')" id="libFilter-all" class="seg-btn active">All</button>
                  <button onclick="setLibraryTypeFilter('video')" id="libFilter-video" class="seg-btn">Video</button>
                  <button onclick="setLibraryTypeFilter('live')" id="libFilter-live" class="seg-btn">Live</button>
                  <button onclick="setLibraryTypeFilter('audio')" id="libFilter-audio" class="seg-btn">Audio</button>
                </div>
              </div>

              <div style="display:flex;align-items:center;justify-content:space-between;font-size:12px;color:var(--text-3);" class="mono">
                <span id="histTotalBadge">0 items</span>
                <button onclick="onClearHistoryClick()" class="btn btn-ghost btn-sm" style="color:var(--text-3);">Clear history</button>
              </div>

              <div id="historyContainer" class="list-stack" style="max-height:520px;overflow-y:auto;"></div>
            </div>
          </section>

          <!-- ============================================================= -->
          <!-- TAB 6: ENGINE, SETTINGS & YT-DLP.CONF EDITOR                  -->
          <!-- ============================================================= -->
          <section id="tab-settings" class="tab-content">
            <!-- Studio Preferences -->
            <div class="panel">
              <div class="panel-header">
                <div>
                  <div class="panel-title">Studio engine settings</div>
                  <div class="panel-sub">Authentication cookies, download concurrency, bandwidth shaping, and destination path</div>
                </div>
                <button onclick="saveStudioSettingsClick()" class="btn btn-primary btn-sm">Save settings</button>
              </div>

              <div class="grid-3">
                <div class="field">
                  <label class="field-label">Browser cookies auth</label>
                  <select id="setCookiesSelect" class="select mono">
                    <option value="none">Disabled</option>
                    <option value="chrome">Google Chrome</option>
                    <option value="edge">Microsoft Edge</option>
                    <option value="firefox">Mozilla Firefox</option>
                    <option value="brave">Brave</option>
                    <option value="opera">Opera</option>
                  </select>
                </div>

                <div class="field">
                  <label class="field-label">Max concurrent batch</label>
                  <select id="setConcurrencySelect" class="select mono">
                    <option value="1">1 worker</option>
                    <option value="2">2 workers</option>
                    <option value="3">3 workers</option>
                    <option value="4">4 workers</option>
                  </select>
                </div>

                <div class="field">
                  <label class="field-label">Bandwidth rate limit</label>
                  <select id="setRateLimitSelect" class="select mono">
                    <option value="">Unlimited</option>
                    <option value="25M">25 MB/s</option>
                    <option value="10M">10 MB/s</option>
                    <option value="5M">5 MB/s</option>
                    <option value="2M">2 MB/s</option>
                    <option value="1M">1 MB/s</option>
                  </select>
                </div>
              </div>

              <div class="grid-2">
                <div class="field">
                  <label class="field-label">Global downloads directory</label>
                  <div style="display:flex;gap:8px;">
                    <input type="text" id="settingsDlDir" value="__CONF_DIR__" class="input mono flex-1" readonly />
                    <button onclick="onSelectFolderClick()" class="btn btn-secondary">Browse</button>
                  </div>
                </div>
                <div class="field">
                  <label class="field-label">HTTP / SOCKS5 proxy (optional)</label>
                  <input type="text" id="setProxyInput" placeholder="http://127.0.0.1:8080 or socks5://..." class="input mono" />
                </div>
              </div>
            </div>

            <!-- Inline System Diagnostics -->
            <div class="panel">
              <div class="panel-header">
                <div>
                  <div class="panel-title">System diagnostics</div>
                  <div class="panel-sub">Verified runtime paths, versions, and binary health</div>
                </div>
                <div style="display:flex;gap:8px;flex-wrap:wrap;">
                  <button onclick="updateYtdlpClick()" id="updateYtdlpBtn" class="btn btn-secondary btn-sm">Update yt-dlp</button>
                  <button onclick="pyCall('run_1click_setup')" class="btn btn-secondary btn-sm">Setup wizard</button>
                  <button onclick="runInlineDiagnostics()" class="btn btn-secondary btn-sm">Re-check</button>
                </div>
              </div>

              <table class="diag-table">
                <thead>
                  <tr>
                    <th style="width:180px;">Component</th>
                    <th style="width:90px;">Status</th>
                    <th>Details</th>
                  </tr>
                </thead>
                <tbody id="diagTableBody">
                  <tr><td colspan="3" style="color:var(--text-3);" class="mono">Loading diagnostics...</td></tr>
                </tbody>
              </table>
            </div>

            <!-- Live yt-dlp.conf Editor -->
            <div class="panel">
              <div class="panel-header">
                <div>
                  <div class="panel-title">yt-dlp.conf editor</div>
                  <div id="confEditorPath" class="panel-sub mono">__CONF_NAME__</div>
                </div>
                <div style="display:flex;gap:8px;">
                  <button onclick="pyCall('open_conf_folder')" class="btn btn-ghost btn-sm">Reveal file</button>
                  <button onclick="saveConfEditor()" class="btn btn-primary btn-sm">Save yt-dlp.conf</button>
                </div>
              </div>
              <textarea id="confEditorArea" rows="12" class="textarea mono" style="font-size:12px;" spellcheck="false"></textarea>
            </div>
          </section>

        </div>
      </main>

      <!-- Right Telemetry, Queue, Inspector & Console Dock -->
      <aside id="rightSidebar" class="right-dock">
        <div class="dock-header">
          <div class="dock-tabs">
            <button onclick="openRightPanelTab('hud')" id="rightTabBtn-hud" class="dock-tab active">Telemetry</button>
            <button onclick="openRightPanelTab('queue')" id="rightTabBtn-queue" class="dock-tab">Queue <span id="rightQueueCount" class="mono">0</span></button>
            <button onclick="openRightPanelTab('inspector')" id="rightTabBtn-inspector" class="dock-tab">Inspector</button>
            <button onclick="openRightPanelTab('console')" id="rightTabBtn-console" class="dock-tab">Console</button>
          </div>
          <button onclick="toggleRightPanel()" class="btn btn-ghost btn-icon-sm" title="Hide dock">
            <svg class="ic ic-sm" viewBox="0 0 24 24"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
          </button>
        </div>

        <!-- Dock Tab 1: Telemetry & Oscilloscope (Visual Moment 2) -->
        <div id="rightTab-hud" class="dock-body">
          <div class="scope-card">
            <div style="display:flex;align-items:baseline;justify-content:space-between;">
              <span style="font-size:12px;color:var(--text-2);font-weight:500;">Live throughput</span>
              <span id="scopeCurrentRate" class="mono" style="font-size:15px;font-weight:500;color:var(--text-1);">0.00 MB/s</span>
            </div>
            <svg id="throughputSvg" class="scope-svg" viewBox="0 0 280 100" preserveAspectRatio="none">
              <line x1="0" y1="25" x2="280" y2="25" stroke="rgba(237,240,247,0.06)" stroke-width="1"/>
              <line x1="0" y1="50" x2="280" y2="50" stroke="rgba(237,240,247,0.06)" stroke-width="1"/>
              <line x1="0" y1="75" x2="280" y2="75" stroke="rgba(237,240,247,0.06)" stroke-width="1"/>
              <path id="scopeArea" d="M 0 100 L 280 100 Z" fill="rgba(79,143,247,0.14)"/>
              <polyline id="scopeLine" points="0,98 280,98" fill="none" stroke="#4f8ff7" stroke-width="1.75" stroke-linejoin="round"/>
            </svg>
            <div style="display:flex;justify-content:space-between;font-size:11.5px;color:var(--text-3);" class="mono">
              <span>Peak <strong id="scopePeakRate" style="color:var(--text-2);font-weight:500;">0.00 MB/s</strong></span>
              <span>Done <strong id="scopeDoneCount" style="color:var(--text-2);font-weight:500;">0</strong></span>
            </div>
          </div>

          <div id="sideHudActiveCard" class="row-card hidden" style="border-color:var(--tally-border);">
            <div style="display:flex;align-items:center;justify-content:space-between;">
              <span class="chip chip-live"><span class="tally-dot live"></span>Active</span>
              <span id="sideLiveTime" class="mono" style="font-size:12px;color:var(--text-1);">00:00</span>
            </div>
            <div id="sideLiveTitle" class="truncate" style="font-size:13px;font-weight:500;">Capture job</div>
            <div style="display:flex;justify-content:space-between;font-size:12px;color:var(--text-2);" class="mono">
              <span>Captured</span>
              <span id="sideLiveSize" style="color:var(--text-1);">0.0 MB</span>
            </div>
            <button onclick="stopActiveStudioDownload()" class="btn btn-tally btn-sm" style="width:100%;">Stop &amp; finalize</button>
          </div>

          <div id="sideHudIdleCard" class="row-card" style="padding:16px;text-align:left;gap:6px;">
            <div style="font-size:13px;font-weight:500;color:var(--text-1);">Standby</div>
            <div style="font-size:12px;color:var(--text-3);">Paste a stream URL or drop a media file into the window to analyze, preview, or record losslessly.</div>
          </div>
        </div>

        <!-- Dock Tab 2: Transfers Queue -->
        <div id="rightTab-queue" class="dock-body hidden">
          <div id="activeDownloadsContainer" style="display:flex;flex-direction:column;gap:10px;">
            <div style="display:flex;align-items:center;justify-content:space-between;">
              <span id="activeCount" class="mono" style="font-size:12px;color:var(--text-2);">0 active</span>
              <button onclick="onClearCompletedClick()" class="btn btn-ghost btn-sm">Clear done</button>
            </div>
            <div id="activeJobsList" class="list-stack">
              <div style="font-size:12px;color:var(--text-3);padding:24px 0;text-align:center;" class="mono">No active transfers</div>
            </div>
          </div>
        </div>

        <!-- Dock Tab 3: Technical Stream Inspector -->
        <div id="rightTab-inspector" class="dock-body hidden">
          <div class="row-card">
            <div style="font-size:12px;font-weight:500;color:var(--text-2);">Stream profile</div>
            <div style="display:flex;flex-direction:column;gap:6px;font-size:12px;" class="mono">
              <div style="display:flex;justify-content:space-between;"><span style="color:var(--text-3);">Platform</span><span id="inspPlatform">--</span></div>
              <div style="display:flex;justify-content:space-between;"><span style="color:var(--text-3);">Protocol</span><span id="inspProtocol">--</span></div>
              <div style="display:flex;justify-content:space-between;"><span style="color:var(--text-3);">Container</span><span id="inspContainer">--</span></div>
              <div style="display:flex;justify-content:space-between;"><span style="color:var(--text-3);">Formats</span><span id="inspFormats">0</span></div>
            </div>
          </div>

          <div class="row-card">
            <div style="font-size:12px;font-weight:500;color:var(--text-2);">Direct manifest URL</div>
            <div id="inspUrlBox" class="mono" style="padding:8px;background:var(--bg-input);border:1px solid var(--hairline);border-radius:var(--r-sm);font-size:11.5px;color:var(--text-2);word-break:break-all;max-height:130px;overflow-y:auto;">No stream analyzed</div>
            <button onclick="copyStreamUrl()" class="btn btn-secondary btn-sm" style="width:100%;">Copy manifest URL</button>
          </div>

          <div class="row-card">
            <div style="font-size:12px;font-weight:500;color:var(--text-2);">Captured HTTP headers</div>
            <pre id="inspHeadersBox" class="mono" style="padding:8px;background:var(--bg-input);border:1px solid var(--hairline);border-radius:var(--r-sm);font-size:11px;color:var(--text-3);overflow-x:auto;max-height:130px;">{}</pre>
          </div>
        </div>

        <!-- Dock Tab 4: Live Engine Console -->
        <div id="rightTab-console" class="dock-body hidden" style="padding:10px;">
          <div style="display:flex;align-items:center;justify-content:space-between;gap:6px;">
            <input id="consoleFilterInput" type="text" class="input mono" placeholder="Filter logs..." style="height:28px;font-size:11.5px;" oninput="renderConsoleLogs()" />
            <button onclick="clearConsoleClick()" class="btn btn-ghost btn-sm">Clear</button>
          </div>
          <div id="consoleLogBox" class="console-box">
            <div class="log-line"><span class="log-ts">--:--:--</span>Engine console ready</div>
          </div>
        </div>

        <div class="dock-footer mono">
          <span>FFmpeg auto-remux</span>
          <button onclick="pyCall('open_folder')" class="btn btn-ghost btn-sm" style="height:24px;">Downloads</button>
        </div>
      </aside>

    </div>
  </div>

  <!-- Toast -->
  <div id="toast" class="toast">
    <span id="toastDot" class="status-dot dot-ok"></span>
    <span id="toastText">Ready</span>
  </div>

  <script>
    let currentStream = null;
    let currentPlaylist = null;
    let hls = null;
    let rawLibrary = [];
    let libraryMode = 'history';
    let libraryTypeFilter = 'all';
    let activeStudioJobId = null;
    let activeStudioStartTime = null;
    let activeStudioTimer = null;
    let consoleCache = [];
    let folderScanCache = [];
    let clipboardWatchEnabled = false;
    let clipboardBannerPendingUrl = '';
    let lastRepairedPath = '';
    let pollHandle = null;

    // -------------------------------------------------------------------------
    // Python Bridge (PyWebView native or HTTP /api/call fallback)
    // -------------------------------------------------------------------------
    async function pyCall(method, ...args) {
      if (window.pywebview && window.pywebview.api && typeof window.pywebview.api[method] === 'function') {
        try {
          return await window.pywebview.api[method](...args);
        } catch (e) {
          console.error('pywebview error:', method, e);
        }
      }
      try {
        const res = await fetch('/api/call', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ method, args })
        });
        if (res.ok) return await res.json();
      } catch (e) {
        console.error('HTTP API error:', method, e);
      }
      return null;
    }

    function escHtml(str) {
      return String(str == null ? '' : str)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
    }

    function showToast(msg, kind = 'ok') {
      const t = document.getElementById('toast');
      const dot = document.getElementById('toastDot');
      document.getElementById('toastText').textContent = msg;
      dot.className = 'status-dot ' + (kind === 'err' ? 'dot-err' : (kind === 'warn' ? 'dot-warn' : 'dot-ok'));
      t.classList.add('show');
      if (window._toastTmr) clearTimeout(window._toastTmr);
      window._toastTmr = setTimeout(() => t.classList.remove('show'), 3200);
    }

    function showAlert(msg) {
      const el = document.getElementById('inlineAlert');
      document.getElementById('inlineAlertText').textContent = msg;
      el.classList.remove('hidden');
    }
    function hideAlert() {
      document.getElementById('inlineAlert').classList.add('hidden');
    }

    function formatSeconds(secs) {
      const s = Math.max(0, Math.floor(secs || 0));
      const h = Math.floor(s / 3600);
      const m = Math.floor((s % 3600) / 60);
      const r = s % 60;
      const pad = n => String(n).padStart(2, '0');
      return h > 0 ? `${pad(h)}:${pad(m)}:${pad(r)}` : `${pad(m)}:${pad(r)}`;
    }

    function formatBytes(bytes) {
      if (!bytes || bytes <= 0) return '';
      const mb = bytes / (1024 * 1024);
      return mb >= 1024 ? (mb / 1024).toFixed(2) + ' GB' : mb.toFixed(1) + ' MB';
    }

    // -------------------------------------------------------------------------
    // Navigation & Layout
    // -------------------------------------------------------------------------
    function toggleSidebar() {
      document.getElementById('leftSidebar').classList.toggle('collapsed');
    }
    function toggleRightPanel() {
      document.getElementById('rightSidebar').classList.toggle('collapsed');
    }

    function openRightPanelTab(tabId) {
      document.getElementById('rightSidebar').classList.remove('collapsed');
      ['hud', 'queue', 'inspector', 'console'].forEach(t => {
        document.getElementById('rightTabBtn-' + t)?.classList.toggle('active', t === tabId);
        document.getElementById('rightTab-' + t)?.classList.toggle('hidden', t !== tabId);
      });
      if (tabId === 'console') refreshConsoleLogs();
    }

    function switchTab(tabId) {
      hideAlert();
      document.querySelectorAll('.tab-content').forEach(el => el.classList.remove('active'));
      document.querySelectorAll('.nav-btn').forEach(b => b.classList.remove('active'));
      document.getElementById('tab-' + tabId)?.classList.add('active');
      document.getElementById('tabBtn-' + tabId)?.classList.add('active');
      if (tabId === 'library') loadHistory();
      if (tabId === 'watchdog') loadWatchdog();
      if (tabId === 'settings') { loadSettingsTab(); }
    }

    // -------------------------------------------------------------------------
    // Command Palette (Ctrl+K)
    // -------------------------------------------------------------------------
    const COMMANDS = [
      { label: 'Go to Studio & Sniffer', hint: 'Tab', run: () => switchTab('studio') },
      { label: 'Go to Batch Queue', hint: 'Tab', run: () => switchTab('batch') },
      { label: 'Go to Creator Watchdog', hint: 'Tab', run: () => switchTab('watchdog') },
      { label: 'Go to Container Repair', hint: 'Tab', run: () => switchTab('repair') },
      { label: 'Go to Media Library', hint: 'Tab', run: () => switchTab('library') },
      { label: 'Go to Engine & Settings', hint: 'Tab', run: () => switchTab('settings') },
      { label: 'Paste URL & Analyze', hint: 'Action', run: async () => { switchTab('studio'); await onPasteClick(); onAnalyzeClick(); } },
      { label: 'Start / Stop Current Download', hint: 'Ctrl+Enter', run: () => onHeroDownloadBtnClick() },
      { label: 'Open Live Engine Console', hint: 'Dock', run: () => openRightPanelTab('console') },
      { label: 'Open Transfers Queue', hint: 'Dock', run: () => openRightPanelTab('queue') },
      { label: 'Toggle Clipboard Watch', hint: 'Toggle', run: () => toggleClipboardWatch() },
      { label: 'Scan Downloads Folder for Broken Containers', hint: 'Repair', run: () => { switchTab('repair'); onScanRepairFolderClick(); } },
      { label: 'Run System Diagnostics', hint: 'Health', run: () => { switchTab('settings'); runInlineDiagnostics(); } },
      { label: 'Open Downloads Folder in Explorer', hint: 'OS', run: () => pyCall('open_folder') },
    ];
    let cmdFiltered = COMMANDS;
    let cmdActiveIdx = 0;

    function openCommandPalette() {
      const bd = document.getElementById('cmdPaletteBackdrop');
      const inp = document.getElementById('cmdPaletteInput');
      bd.classList.add('open');
      inp.value = '';
      renderCommandPalette('');
      setTimeout(() => inp.focus(), 20);
    }
    function closeCommandPalette() {
      document.getElementById('cmdPaletteBackdrop').classList.remove('open');
    }
    function renderCommandPalette(q) {
      const clean = (q || '').toLowerCase().trim();
      cmdFiltered = COMMANDS.filter(c => c.label.toLowerCase().includes(clean) || c.hint.toLowerCase().includes(clean));
      cmdActiveIdx = 0;
      const list = document.getElementById('cmdPaletteList');
      list.innerHTML = '';
      cmdFiltered.forEach((cmd, idx) => {
        const btn = document.createElement('button');
        btn.className = 'cmd-item' + (idx === cmdActiveIdx ? ' active' : '');
        btn.innerHTML = `<span>${escHtml(cmd.label)}</span><span class="kbd">${escHtml(cmd.hint)}</span>`;
        btn.onclick = () => { closeCommandPalette(); cmd.run(); };
        list.appendChild(btn);
      });
    }
    function onCmdPaletteKey(e) {
      if (e.key === 'Escape') { closeCommandPalette(); return; }
      if (e.key === 'ArrowDown') {
        e.preventDefault();
        cmdActiveIdx = Math.min(cmdFiltered.length - 1, cmdActiveIdx + 1);
      } else if (e.key === 'ArrowUp') {
        e.preventDefault();
        cmdActiveIdx = Math.max(0, cmdActiveIdx - 1);
      } else if (e.key === 'Enter' && cmdFiltered[cmdActiveIdx]) {
        e.preventDefault();
        const fn = cmdFiltered[cmdActiveIdx].run;
        closeCommandPalette();
        fn();
        return;
      } else { return; }
      document.querySelectorAll('#cmdPaletteList .cmd-item').forEach((el, i) => el.classList.toggle('active', i === cmdActiveIdx));
    }

    // -------------------------------------------------------------------------
    // Clipboard Watch
    // -------------------------------------------------------------------------
    async function toggleClipboardWatch() {
      clipboardWatchEnabled = !clipboardWatchEnabled;
      updateClipboardWatchUI();
      await pyCall('save_studio_settings', { clipboard_watch: clipboardWatchEnabled });
      showToast(clipboardWatchEnabled ? 'Clipboard watch enabled' : 'Clipboard watch paused');
    }
    function updateClipboardWatchUI() {
      const dot = document.getElementById('clipWatchDot');
      dot.className = 'status-dot ' + (clipboardWatchEnabled ? 'dot-ok' : 'dot-muted');
    }
    async function pollClipboardWatch() {
      if (!clipboardWatchEnabled) return;
      const res = await pyCall('check_clipboard_url');
      if (res && res.found && res.url) {
        clipboardBannerPendingUrl = res.url;
        document.getElementById('clipBannerPlatform').textContent = (res.platform && res.platform.name) || 'Stream URL';
        document.getElementById('clipBannerUrl').textContent = res.url;
        document.getElementById('clipboardBanner').classList.remove('hidden');
      }
    }
    function dismissClipboardBanner() {
      document.getElementById('clipboardBanner').classList.add('hidden');
    }
    function acceptClipboardUrl(quickDownload) {
      const u = clipboardBannerPendingUrl;
      dismissClipboardBanner();
      if (!u) return;
      document.getElementById('streamUrlInput').value = u;
      onUrlInputChanged(u);
      switchTab('studio');
      if (quickDownload) onHeroDownloadBtnClick();
      else onAnalyzeClick();
    }

    // -------------------------------------------------------------------------
    // Studio URL Input, Analysis, Player & Clipper
    // -------------------------------------------------------------------------
    function clearUrlInput() {
      const inp = document.getElementById('streamUrlInput');
      inp.value = '';
      onUrlInputChanged('');
      inp.focus();
    }

    function onUrlInputChanged(val) {
      const clearBtn = document.getElementById('clearUrlBtn');
      const badge = document.getElementById('platformDetectBadge');
      const clean = (val || '').toLowerCase().trim();
      clearBtn.classList.toggle('hidden', clean.length === 0);

      if (clean.includes('tiktok.com')) badge.textContent = clean.includes('/live') ? 'TikTok Live' : 'TikTok Video';
      else if (clean.includes('youtube.com') || clean.includes('youtu.be')) badge.textContent = clean.includes('list=') ? 'YouTube Playlist' : 'YouTube';
      else if (clean.includes('twitch.tv')) badge.textContent = 'Twitch';
      else if (clean.includes('kick.com')) badge.textContent = 'Kick Live';
      else if (clean.includes('.m3u8')) badge.textContent = 'HLS Manifest';
      else if (clean.includes('.mpd')) badge.textContent = 'DASH Stream';
      else badge.textContent = 'Universal sniffer';
    }

    async function onPasteClick() {
      const res = await pyCall('get_clipboard_text');
      let text = (res && res.text) ? res.text.trim() : '';
      if (!text) {
        try { text = (await navigator.clipboard.readText() || '').trim(); } catch (e) {}
      }
      if (text) {
        const inp = document.getElementById('streamUrlInput');
        inp.value = text;
        onUrlInputChanged(text);
        showToast('URL pasted from clipboard');
      } else {
        showToast('Clipboard is empty', 'warn');
      }
    }

    function setPreset(url) {
      const inp = document.getElementById('streamUrlInput');
      inp.value = url;
      onUrlInputChanged(url);
      switchTab('studio');
      onAnalyzeClick();
    }

    async function onAnalyzeClick() {
      hideAlert();
      const url = document.getElementById('streamUrlInput').value.trim();
      if (!url) {
        showToast('Enter a stream or video URL first', 'warn');
        return;
      }

      const loader = document.getElementById('loader');
      const playerSection = document.getElementById('playerSection');
      const playlistSection = document.getElementById('playlistSection');
      loader.classList.remove('hidden');
      playerSection.classList.add('hidden');
      playlistSection.classList.add('hidden');

      try {
        const data = await pyCall('resolve_url', url);
        loader.classList.add('hidden');

        if (!data || data.error) {
          showAlert('Resolution failed: ' + (data ? data.error : 'Stream offline or unreachable'));
          return;
        }

        // Playlist Mode
        if (data.is_playlist && data.playlist_entries && data.playlist_entries.length > 0) {
          currentPlaylist = data;
          renderPlaylist(data);
          playlistSection.classList.remove('hidden');
          showToast(`Playlist loaded (${data.playlist_entries.length} items)`);
          return;
        }

        currentStream = data;
        currentPlaylist = null;
        document.getElementById('streamTitle').textContent = data.title || 'Untitled stream';
        document.getElementById('uploaderBadge').textContent = data.uploader ? '@' + data.uploader : 'Direct source';
        document.getElementById('platformBadge').textContent = (data.platform && data.platform.name) || 'Universal';

        const liveChip = document.getElementById('liveStatusBadge');
        const liveTxt = document.getElementById('liveStatusText');
        if (data.is_live) {
          liveChip.className = 'chip chip-live';
          liveTxt.textContent = 'Live';
        } else {
          liveChip.className = 'chip';
          liveTxt.textContent = 'VOD';
        }

        const durBadge = document.getElementById('durationBadge');
        if (data.duration) {
          durBadge.textContent = formatSeconds(data.duration);
          durBadge.classList.remove('hidden');
        } else {
          durBadge.classList.add('hidden');
        }

        // Populate Inspector Dock
        document.getElementById('inspPlatform').textContent = (data.platform && data.platform.name) || 'Universal';
        document.getElementById('inspProtocol').textContent = data.is_live ? 'HLS / Live' : 'HTTPS';
        document.getElementById('inspContainer').textContent = (data.formats && data.formats[0]) ? (data.formats[0].ext || 'mp4') : 'mp4';
        document.getElementById('inspFormats').textContent = String((data.formats || []).length);
        document.getElementById('inspUrlBox').textContent = data.direct_url || data.preview_url || url;
        document.getElementById('inspHeadersBox').textContent = JSON.stringify(data.http_headers || {}, null, 2);

        renderFormats(data.formats || []);

        const previewTarget = data.preview_url || data.direct_url;
        if (previewTarget) {
          playStream(previewTarget, data.title || 'Live preview');
        }

        playerSection.classList.remove('hidden');
        showToast('Stream analyzed');
      } catch (e) {
        loader.classList.add('hidden');
        showAlert('Failed to analyze stream: ' + e);
      }
    }

    function renderPlaylist(data) {
      document.getElementById('playlistTitle').textContent = data.title || 'Playlist';
      document.getElementById('playlistMeta').textContent = `${data.playlist_entries.length} selectable items`;
      const container = document.getElementById('playlistEntriesList');
      container.innerHTML = '';
      data.playlist_entries.forEach(item => {
        const row = document.createElement('label');
        row.className = 'lib-row';
        row.style.cursor = 'pointer';
        row.innerHTML = `
          <div style="display:flex;align-items:center;gap:10px;min-width:0;">
            <input type="checkbox" class="pl-item-chk" value="${escHtml(item.url)}" checked style="accent-color:var(--signal);width:14px;height:14px;" />
            <span class="mono" style="font-size:11.5px;color:var(--text-3);width:26px;">#${item.index}</span>
            <span class="truncate" style="font-size:12.5px;color:var(--text-1);">${escHtml(item.title)}</span>
          </div>
          <span class="mono" style="font-size:11.5px;color:var(--text-3);flex-shrink:0;">${item.duration ? formatSeconds(item.duration) : '--'}</span>
        `;
        container.appendChild(row);
      });
    }

    function toggleAllPlaylistItems(checked) {
      document.querySelectorAll('.pl-item-chk').forEach(c => { c.checked = checked; });
    }

    async function downloadSelectedPlaylist() {
      const urls = Array.from(document.querySelectorAll('.pl-item-chk:checked')).map(c => c.value);
      if (urls.length === 0) {
        showToast('Select at least one playlist item', 'warn');
        return;
      }
      const q = document.getElementById('qualitySelect').value;
      const container = document.getElementById('containerSelect').value;
      const res = await pyCall('batch_download', {
        urls,
        quality: q,
        container,
        subtitles: document.getElementById('chkSubtitles').checked,
        embed_metadata: document.getElementById('chkMetadata').checked,
        embed_thumbnail: document.getElementById('chkThumbnail').checked,
      });
      if (res && res.count) {
        showToast(`Queued ${res.count} playlist item(s)`);
        openRightPanelTab('queue');
        pollLoop();
      }
    }

    function renderFormats(formats) {
      const container = document.getElementById('formatsList');
      const badge = document.getElementById('formatsCountBadge');
      container.innerHTML = '';
      badge.textContent = `${formats.length} found`;

      if (!formats || formats.length === 0) {
        container.innerHTML = '<div class="mono" style="font-size:12px;color:var(--text-3);padding:8px 0;">No separate bitrate variants reported</div>';
        return;
      }

      formats.forEach((f, idx) => {
        const card = document.createElement('div');
        card.className = 'format-card';
        const resLabel = f.height ? `${f.height}p${f.fps ? ' ' + Math.round(f.fps) + 'fps' : ''}` : (f.acodec ? 'Audio' : (f.ext || 'stream').toUpperCase());
        const metaParts = [];
        if (f.tbr) metaParts.push(`${f.tbr} kbps`);
        if (f.vcodec) metaParts.push(f.vcodec.split('.')[0]);
        else if (f.acodec) metaParts.push(f.acodec.split('.')[0]);
        if (f.filesize) metaParts.push(formatBytes(f.filesize));
        if (!metaParts.length) metaParts.push(f.protocol || 'hls');

        const left = document.createElement('div');
        left.className = 'min-w-0';
        left.innerHTML = `
          <div class="mono truncate" style="font-size:12.5px;color:var(--text-1);font-weight:500;">${escHtml(resLabel)} <span style="color:var(--text-3);font-weight:400;">· ${escHtml(f.id || 'fmt-' + (idx + 1))}</span></div>
          <div class="mono truncate" style="font-size:11.5px;color:var(--text-3);margin-top:2px;">${escHtml(metaParts.join(' · '))}</div>
        `;

        const right = document.createElement('div');
        right.style.display = 'flex';
        right.style.gap = '4px';
        right.style.flexShrink = '0';

        const copyBtn = document.createElement('button');
        copyBtn.className = 'btn btn-ghost btn-sm';
        copyBtn.textContent = 'Copy';
        copyBtn.onclick = (e) => {
          e.stopPropagation();
          pyCall('copy_to_clipboard', f.url);
          showToast('Format URL copied');
        };

        const dlBtn = document.createElement('button');
        dlBtn.className = 'btn btn-secondary btn-sm';
        dlBtn.textContent = 'Get';
        dlBtn.onclick = (e) => {
          e.stopPropagation();
          triggerDownloadDirect(currentStream?.original_url || f.url, f.id);
        };

        right.appendChild(copyBtn);
        right.appendChild(dlBtn);
        card.appendChild(left);
        card.appendChild(right);

        card.onclick = () => {
          document.querySelectorAll('.format-card').forEach(c => c.classList.remove('selected'));
          card.classList.add('selected');
          const playUrl = (f.url && (f.url.includes('.m3u8') || f.url.includes('pull-hls')))
            ? '/api/proxy_hls?url=' + encodeURIComponent(f.url)
            : f.url;
          playStream(playUrl, `${resLabel} (${f.id})`);
          showToast(`Previewing ${resLabel}`);
        };

        container.appendChild(card);
      });
    }

    function playStream(url, label = 'Stream monitor') {
      const video = document.getElementById('hlsVideo');
      document.getElementById('monitorSourceTag').textContent = label;
      video.onloadedmetadata = () => {
        const res = (video.videoWidth && video.videoHeight) ? `${video.videoWidth}x${video.videoHeight}` : 'Audio / Stream';
        document.getElementById('monitorResTag').textContent = res;
      };

      const isHls = url.includes('.m3u8') || url.includes('proxy_hls') || url.includes('pull-hls');
      if (window.Hls && Hls.isSupported() && isHls) {
        if (hls) { hls.destroy(); hls = null; }
        hls = new Hls({ enableWorker: true, lowLatencyMode: true });
        hls.loadSource(url);
        hls.attachMedia(video);
        hls.on(Hls.Events.MANIFEST_PARSED, () => video.play().catch(() => {}));
        hls.on(Hls.Events.ERROR, (ev, data) => {
          if (data && data.fatal) {
            if (data.type === Hls.ErrorTypes.NETWORK_ERROR && !url.includes('proxy_hls') && currentStream?.direct_url) {
              hls.loadSource('/api/proxy_hls?url=' + encodeURIComponent(currentStream.direct_url));
            } else if (data.type === Hls.ErrorTypes.MEDIA_ERROR) {
              hls.recoverMediaError();
            }
          }
        });
      } else {
        if (hls) { hls.destroy(); hls = null; }
        video.src = url;
        video.play().catch(() => {});
      }
    }

    function playLocalMediaInStudio(filePath, title) {
      if (!filePath) return;
      switchTab('studio');
      const mediaUrl = '/api/media?path=' + encodeURIComponent(filePath);
      document.getElementById('streamTitle').textContent = title || filePath.split(/[\\/]/).pop();
      document.getElementById('platformBadge').textContent = 'Local file';
      document.getElementById('liveStatusBadge').className = 'chip chip-ok';
      document.getElementById('liveStatusText').textContent = 'Local';
      document.getElementById('uploaderBadge').textContent = 'Disk playback';
      document.getElementById('formatsList').innerHTML = '';
      document.getElementById('formatsCountBadge').textContent = 'Local media';
      document.getElementById('playerSection').classList.remove('hidden');
      playStream(mediaUrl, 'Local playback');
      showToast('Playing local file in Broadcast Monitor');
    }

    function markClipPoint(which) {
      const video = document.getElementById('hlsVideo');
      const t = video && !isNaN(video.currentTime) ? formatSeconds(video.currentTime) : '00:00';
      if (which === 'start') {
        document.getElementById('clipStartInput').value = t;
        showToast(`Clip start marked at ${t}`);
      } else {
        document.getElementById('clipEndInput').value = t;
        showToast(`Clip end marked at ${t}`);
      }
    }
    function clearClipRange() {
      document.getElementById('clipStartInput').value = '';
      document.getElementById('clipEndInput').value = '';
      showToast('Clip trim cleared');
    }

    function copyStreamUrl() {
      if (!currentStream) return;
      const u = currentStream.direct_url || (currentStream.formats && currentStream.formats[0] ? currentStream.formats[0].url : '');
      if (u) {
        pyCall('copy_to_clipboard', u);
        showToast('Stream URL copied');
      }
    }
    function playInExternalPlayer() {
      if (!currentStream) return;
      const u = currentStream.direct_url || (currentStream.formats && currentStream.formats[0] ? currentStream.formats[0].url : '');
      if (u) {
        pyCall('play_in_external_player', u);
        showToast('Launching external media player');
      }
    }

    async function onSelectFolderClick() {
      const res = await pyCall('select_folder');
      if (res && res.folder) {
        document.getElementById('saveFolderInput').value = res.folder;
        document.getElementById('settingsDlDir').value = res.folder;
        document.getElementById('hdrDlDir').textContent = res.folder;
        showToast('Destination folder updated');
      }
    }

    function onAudioToggle() {
      const isAudio = document.getElementById('chkAudioOnly').checked;
      const q = document.getElementById('qualitySelect');
      if (isAudio) q.value = 'audio_mp3';
      else if (q.value.startsWith('audio_')) q.value = 'max';
    }

    // -------------------------------------------------------------------------
    // Download & Live Recording Controller
    // -------------------------------------------------------------------------
    function setHeroButtonToRecording(jobId, isLive, title) {
      activeStudioJobId = jobId;
      activeStudioStartTime = Date.now();

      const btn = document.getElementById('heroDownloadBtn');
      const label = document.getElementById('heroBtnLabel');
      const theaterBtn = document.getElementById('theaterDownloadBtn');
      const hud = document.getElementById('studioLiveHud');

      document.getElementById('sideHudActiveCard').classList.remove('hidden');
      document.getElementById('sideHudIdleCard').classList.add('hidden');
      document.getElementById('sideLiveTitle').textContent = title || 'Active capture';

      btn.className = 'btn btn-tally btn-lg';
      btn.style.minWidth = '196px';
      label.textContent = isLive ? 'Stop recording (00:00)' : 'Stop download (00:00)';
      if (theaterBtn) {
        theaterBtn.className = 'btn btn-tally btn-sm';
        theaterBtn.textContent = 'Stop';
      }

      hud.classList.remove('hidden');
      document.getElementById('hudStopBtn').classList.remove('hidden');
      document.getElementById('hudStopBtn').disabled = false;
      document.getElementById('hudLiveDot').textContent = isLive ? 'Recording live' : 'Downloading';
      document.getElementById('hudStreamTitle').textContent = title || 'Active capture';
      document.getElementById('hudProgressBar').className = 'progress-fill ' + (isLive ? 'live' : '');
      document.getElementById('hudProgressBar').style.width = isLive ? '100%' : '5%';

      if (activeStudioTimer) clearInterval(activeStudioTimer);
      activeStudioTimer = setInterval(() => {
        if (!activeStudioStartTime) return;
        const fmt = formatSeconds((Date.now() - activeStudioStartTime) / 1000);
        document.getElementById('hudElapsed').textContent = fmt;
        document.getElementById('sideLiveTime').textContent = fmt;
        if (activeStudioJobId) {
          label.textContent = isLive ? `Stop recording (${fmt})` : `Stop download (${fmt})`;
        }
      }, 1000);
    }

    function resetHeroButtonToIdle(completedPath = null, failed = false) {
      activeStudioJobId = null;
      if (activeStudioTimer) { clearInterval(activeStudioTimer); activeStudioTimer = null; }

      const btn = document.getElementById('heroDownloadBtn');
      const label = document.getElementById('heroBtnLabel');
      const theaterBtn = document.getElementById('theaterDownloadBtn');
      const hud = document.getElementById('studioLiveHud');

      document.getElementById('sideHudActiveCard').classList.add('hidden');
      document.getElementById('sideHudIdleCard').classList.remove('hidden');

      btn.className = 'btn btn-primary btn-lg';
      btn.style.minWidth = '196px';
      label.textContent = 'Start download';
      if (theaterBtn) {
        theaterBtn.className = 'btn btn-primary btn-sm';
        theaterBtn.textContent = 'Download best';
      }

      if (completedPath && !failed) {
        document.getElementById('hudStatusDesc').textContent = 'Completed and verified';
        document.getElementById('hudFile').textContent = completedPath;
        document.getElementById('hudProgressBar').className = 'progress-fill done';
        document.getElementById('hudProgressBar').style.width = '100%';
        document.getElementById('hudStopBtn').classList.add('hidden');
      } else {
        hud.classList.add('hidden');
      }
    }

    async function onHeroDownloadBtnClick() {
      if (activeStudioJobId) await stopActiveStudioDownload();
      else await startDownloadCurrent('custom');
    }

    async function stopActiveStudioDownload() {
      if (!activeStudioJobId) return;
      const targetId = activeStudioJobId;
      const hudStopBtn = document.getElementById('hudStopBtn');
      hudStopBtn.disabled = true;
      document.getElementById('heroBtnLabel').textContent = 'Finalizing container...';
      showToast('Stopping capture and finalizing container', 'warn');

      const res = await pyCall('stop_job', targetId);
      const savedPath = res && res.saved_path ? res.saved_path : null;
      resetHeroButtonToIdle(savedPath, false);
      pollActiveDownloads();
      showToast(savedPath ? 'Recording finalized cleanly' : 'Transfer stopped');
    }

    async function startDownloadCurrent(mode) {
      if (activeStudioJobId) {
        await stopActiveStudioDownload();
        return;
      }
      const inputUrl = document.getElementById('streamUrlInput').value.trim();
      const targetUrl = (currentStream && (currentStream.original_url || currentStream.direct_url)) || inputUrl;
      if (!targetUrl) {
        showToast('Enter a URL first', 'warn');
        return;
      }

      const title = currentStream ? currentStream.title : '';
      const uploader = currentStream ? currentStream.uploader : '';
      const isLive = currentStream ? Boolean(currentStream.is_live) : false;
      const q = mode === 'audio' ? 'audio_mp3' : document.getElementById('qualitySelect').value;
      const isAudio = mode === 'audio' || document.getElementById('chkAudioOnly').checked || q.startsWith('audio_');
      const container = document.getElementById('containerSelect').value;
      const folder = document.getElementById('saveFolderInput').value;

      const res = await pyCall('start_download', {
        url: targetUrl,
        title,
        uploader,
        is_live: isLive,
        quality: q,
        audio_only: isAudio,
        container,
        folder,
        subtitles: document.getElementById('chkSubtitles').checked,
        embed_metadata: document.getElementById('chkMetadata').checked,
        embed_thumbnail: document.getElementById('chkThumbnail').checked,
        sponsorblock: document.getElementById('chkSponsorblock').checked,
        clip_start: document.getElementById('clipStartInput').value.trim(),
        clip_end: document.getElementById('clipEndInput').value.trim(),
      });

      if (res && res.job_id) {
        setHeroButtonToRecording(res.job_id, isLive, title || targetUrl);
        showToast(isLive ? 'Live recording started' : 'Download started');
        pollActiveDownloads();
      } else if (res && res.error) {
        showAlert(res.error);
      }
    }

    async function triggerDownloadDirect(url, formatId) {
      const title = currentStream ? currentStream.title : formatId;
      const uploader = currentStream ? currentStream.uploader : '';
      const isLive = currentStream ? Boolean(currentStream.is_live) : false;
      const container = document.getElementById('containerSelect').value;
      const res = await pyCall('start_download', {
        url,
        title,
        uploader,
        is_live: isLive,
        quality: 'max',
        container,
        format_id: isLive ? null : formatId,
        subtitles: document.getElementById('chkSubtitles').checked,
        embed_metadata: document.getElementById('chkMetadata').checked,
        embed_thumbnail: document.getElementById('chkThumbnail').checked,
      });
      if (res && res.job_id) {
        setHeroButtonToRecording(res.job_id, isLive, title);
        showToast(`Downloading format ${formatId}`);
        pollActiveDownloads();
      }
    }

    // -------------------------------------------------------------------------
    // Live Oscilloscope Telemetry, Queue & Console Polling
    // -------------------------------------------------------------------------
    function renderOscilloscope(telemetry) {
      if (!telemetry) return;
      document.getElementById('scopeCurrentRate').textContent = `${(telemetry.current_mbps || 0).toFixed(2)} MB/s`;
      document.getElementById('scopePeakRate').textContent = `${(telemetry.peak_mbps || 0).toFixed(2)} MB/s`;
      document.getElementById('scopeDoneCount').textContent = String(telemetry.completed_count || 0);

      const series = telemetry.series || [];
      if (series.length < 2) return;
      const maxVal = Math.max(1, ...series) * 1.15;
      const w = 280, h = 100;
      const step = w / (series.length - 1);
      const pts = series.map((v, i) => {
        const x = (i * step).toFixed(1);
        const y = (h - Math.max(2, (v / maxVal) * (h - 8))).toFixed(1);
        return `${x},${y}`;
      });
      document.getElementById('scopeLine').setAttribute('points', pts.join(' '));
      document.getElementById('scopeArea').setAttribute('d', `M 0,${h} L ${pts.join(' L ')} L ${w},${h} Z`);
    }

    async function pollActiveDownloads() {
      try {
        const [jobs, telemetry] = await Promise.all([
          pyCall('get_active_jobs'),
          pyCall('get_telemetry'),
        ]);
        renderOscilloscope(telemetry);
        const safeJobs = Array.isArray(jobs) ? jobs : [];
        const running = safeJobs.filter(j => !j.completed);

        document.getElementById('navQueueCount').textContent = String(running.length);
        document.getElementById('rightQueueCount').textContent = String(running.length);
        document.getElementById('queueIndicator').classList.toggle('hidden', running.length === 0);
        document.getElementById('activeCount').textContent = `${running.length} active · ${safeJobs.length} total`;

        // Sync active studio job HUD
        if (activeStudioJobId) {
          const cj = safeJobs.find(j => j.id === activeStudioJobId);
          if (cj) {
            if (cj.completed) {
              const failed = !cj.success && cj.status === 'failed';
              resetHeroButtonToIdle(cj.saved_path, failed);
              if (failed) showToast('Download failed — inspect Console logs', 'err');
              else showToast('Transfer complete');
            } else {
              if (cj.size && cj.size !== '--') {
                document.getElementById('hudSize').textContent = cj.size;
                document.getElementById('sideLiveSize').textContent = cj.size;
              }
              if (cj.speed && cj.speed !== '--') document.getElementById('hudSpeed').textContent = cj.speed;
              if (cj.saved_path) document.getElementById('hudFile').textContent = cj.saved_path;
              if (!cj.is_live && cj.percent > 0) {
                document.getElementById('hudProgressBar').style.width = `${Math.min(100, cj.percent)}%`;
                document.getElementById('hudStatusDesc').textContent = `${cj.percent.toFixed(1)}% · ETA ${cj.eta || '--'}`;
              }
            }
          }
        }

        // Render Queue Cards
        const list = document.getElementById('activeJobsList');
        list.innerHTML = '';
        if (safeJobs.length === 0) {
          list.innerHTML = '<div style="font-size:12px;color:var(--text-3);padding:24px 0;text-align:center;" class="mono">No active transfers</div>';
        } else {
          safeJobs.slice().reverse().forEach(j => {
            const card = document.createElement('div');
            card.className = 'row-card';
            const isDone = j.completed && (j.success || j.status === 'completed');
            const isStopped = j.completed && j.status === 'stopped';
            const isFail = j.completed && j.status === 'failed';

            let statusChip = `<span class="chip chip-signal mono">${escHtml(j.status || 'Running')}</span>`;
            if (isDone) statusChip = `<span class="chip chip-ok mono">Finished</span>`;
            else if (isStopped) statusChip = `<span class="chip chip-warn mono">Stopped</span>`;
            else if (isFail) statusChip = `<span class="chip chip-live mono">Failed</span>`;
            else if (j.is_live) statusChip = `<span class="chip chip-live mono"><span class="tally-dot live"></span>Live</span>`;

            const pct = isDone ? 100 : (j.percent > 0 ? Math.min(100, j.percent) : (j.is_live ? 100 : 10));
            const fillCls = isDone ? 'done' : (isFail ? 'err' : (j.is_live ? 'live' : ''));

            const top = document.createElement('div');
            top.style.display = 'flex';
            top.style.alignItems = 'center';
            top.style.justifyContent = 'space-between';
            top.innerHTML = `${statusChip}<span class="mono" style="font-size:11.5px;color:var(--text-2);">${escHtml(j.size || '--')}</span>`;

            const titleEl = document.createElement('div');
            titleEl.className = 'truncate';
            titleEl.style.fontSize = '12.5px';
            titleEl.style.fontWeight = '500';
            titleEl.title = j.title || j.url;
            titleEl.textContent = j.title || j.url;

            const prog = document.createElement('div');
            prog.className = 'progress-track';
            prog.innerHTML = `<div class="progress-fill ${fillCls}" style="width:${pct}%"></div>`;

            const foot = document.createElement('div');
            foot.style.display = 'flex';
            foot.style.alignItems = 'center';
            foot.style.justifyContent = 'space-between';
            foot.style.fontSize = '11.5px';
            foot.className = 'mono';

            const meta = document.createElement('span');
            meta.className = 'truncate';
            meta.style.color = 'var(--text-3)';
            meta.textContent = isFail ? (j.error || 'Error') : `${j.speed || '--'}${j.eta && j.eta !== '--' ? ' · ' + j.eta : ''}`;

            const acts = document.createElement('div');
            acts.style.display = 'flex';
            acts.style.gap = '4px';

            if (!j.completed) {
              const stopB = document.createElement('button');
              stopB.className = 'btn btn-tally-soft btn-sm';
              stopB.style.height = '24px';
              stopB.textContent = 'Stop';
              stopB.onclick = async () => { await pyCall('stop_job', j.id); pollActiveDownloads(); };
              acts.appendChild(stopB);
            }
            if (isFail || isStopped) {
              const retryB = document.createElement('button');
              retryB.className = 'btn btn-secondary btn-sm';
              retryB.style.height = '24px';
              retryB.textContent = 'Retry';
              retryB.onclick = async () => { await pyCall('retry_job', j.id); showToast('Retrying transfer'); pollActiveDownloads(); };
              acts.appendChild(retryB);
            }
            if (j.saved_path && !String(j.saved_path).startsWith('Configured in')) {
              const playB = document.createElement('button');
              playB.className = 'btn btn-secondary btn-sm';
              playB.style.height = '24px';
              playB.textContent = 'Play';
              playB.onclick = () => playLocalMediaInStudio(j.saved_path, j.title);
              acts.appendChild(playB);

              const revB = document.createElement('button');
              revB.className = 'btn btn-ghost btn-sm';
              revB.style.height = '24px';
              revB.textContent = 'Reveal';
              revB.onclick = () => pyCall('reveal_in_explorer', j.saved_path);
              acts.appendChild(revB);
            }

            foot.appendChild(meta);
            foot.appendChild(acts);
            card.appendChild(top);
            card.appendChild(titleEl);
            card.appendChild(prog);
            card.appendChild(foot);
            list.appendChild(card);
          });
        }

        // Refresh console if visible
        if (!document.getElementById('rightTab-console').classList.contains('hidden')) {
          refreshConsoleLogs();
        }
      } catch (e) {}
    }

    async function refreshConsoleLogs() {
      const logs = await pyCall('get_console_logs', 200);
      if (Array.isArray(logs)) {
        consoleCache = logs;
        renderConsoleLogs();
      }
    }

    function renderConsoleLogs() {
      const box = document.getElementById('consoleLogBox');
      const filter = (document.getElementById('consoleFilterInput').value || '').toLowerCase().trim();
      const filtered = filter
        ? consoleCache.filter(l => (l.line || '').toLowerCase().includes(filter) || (l.job_id || '').toLowerCase().includes(filter))
        : consoleCache;
      box.innerHTML = '';
      if (filtered.length === 0) {
        box.innerHTML = '<div class="log-line"><span class="log-ts">--:--:--</span>No log entries</div>';
        return;
      }
      filtered.forEach(entry => {
        const div = document.createElement('div');
        div.className = 'log-line ' + (entry.level || 'info');
        div.innerHTML = `<span class="log-ts">${escHtml(entry.ts)}</span>${escHtml(entry.line)}`;
        box.appendChild(div);
      });
      box.scrollTop = box.scrollHeight;
    }

    async function clearConsoleClick() {
      await pyCall('clear_console_logs');
      consoleCache = [];
      renderConsoleLogs();
    }

    async function onClearCompletedClick() {
      await pyCall('clear_completed_jobs');
      pollActiveDownloads();
      showToast('Cleared finished jobs');
    }

    function pollLoop() {
      if (pollHandle) clearTimeout(pollHandle);
      pollActiveDownloads();
      pollClipboardWatch();
      pollHandle = setTimeout(pollLoop, 1200);
    }

    // -------------------------------------------------------------------------
    // Batch Queue
    // -------------------------------------------------------------------------
    function updateBatchUrlCount() {
      const txt = document.getElementById('batchUrlsInput').value.trim();
      const urls = txt.split('\n').map(u => u.trim()).filter(u => u.startsWith('http'));
      document.getElementById('batchCountBadge').textContent = `${urls.length} valid URLs`;
    }

    function dedupeBatchUrls() {
      const inp = document.getElementById('batchUrlsInput');
      const lines = inp.value.split('\n').map(u => u.trim()).filter(Boolean);
      const unique = Array.from(new Set(lines));
      inp.value = unique.join('\n');
      updateBatchUrlCount();
      showToast(`Deduplicated to ${unique.length} lines`);
    }

    async function onLoadBatchFileClick() {
      const res = await pyCall('select_batch_file');
      if (res && res.content) {
        const inp = document.getElementById('batchUrlsInput');
        inp.value = (inp.value ? inp.value + '\n' : '') + res.content.trim();
        updateBatchUrlCount();
        showToast('Loaded URLs from text file');
      }
    }

    async function onSubmitBatchClick() {
      const txt = document.getElementById('batchUrlsInput').value.trim();
      const urls = txt.split('\n').map(u => u.trim()).filter(u => u.startsWith('http'));
      if (urls.length === 0) {
        showToast('Paste at least one valid HTTP(S) URL', 'warn');
        return;
      }
      const res = await pyCall('batch_download', {
        urls,
        quality: document.getElementById('batchQualitySelect').value,
        container: document.getElementById('batchContainerSelect').value,
        concurrency: parseInt(document.getElementById('batchConcurrencySelect').value, 10) || 2,
      });
      if (res && res.count) {
        showToast(`Queued ${res.count} items (${res.concurrency} workers)`);
        document.getElementById('batchUrlsInput').value = '';
        updateBatchUrlCount();
        openRightPanelTab('queue');
        pollActiveDownloads();
      }
    }

    // -------------------------------------------------------------------------
    // Creator Watchdog
    // -------------------------------------------------------------------------
    async function loadWatchdog() {
      const snap = await pyCall('get_watchdog_state');
      if (!snap) return;
      document.getElementById('watchdogEnabledToggle').checked = Boolean(snap.enabled);
      document.getElementById('watchdogGlobalAutoRec').checked = Boolean(snap.global_auto_record);
      document.getElementById('watchdogIntervalSelect').value = String(snap.interval || 60);
      document.getElementById('watchdogLastCycle').textContent = snap.enabled ? `Last poll ${snap.last_cycle}` : 'Monitor paused';

      const items = snap.items || [];
      document.getElementById('watchlistCount').textContent = `${items.length} creators`;
      document.getElementById('navWatchCount').textContent = String(items.length);

      const container = document.getElementById('watchlistContainer');
      container.innerHTML = '';
      if (items.length === 0) {
        container.innerHTML = '<div class="mono" style="grid-column:1/-1;font-size:12px;color:var(--text-3);padding:24px 0;text-align:center;">No creators monitored yet</div>';
        return;
      }

      items.forEach(it => {
        const card = document.createElement('div');
        card.className = 'row-card';
        if (it.is_live) card.style.borderColor = 'var(--tally-border)';

        const top = document.createElement('div');
        top.style.display = 'flex';
        top.style.alignItems = 'center';
        top.style.justifyContent = 'space-between';
        top.style.gap = '8px';

        const statusBadge = it.is_recording
          ? '<span class="chip chip-live mono"><span class="tally-dot live"></span>Recording</span>'
          : (it.is_live
            ? '<span class="chip chip-live mono"><span class="tally-dot live"></span>Live now</span>'
            : '<span class="chip mono">Offline</span>');

        top.innerHTML = `
          <div style="display:flex;align-items:center;gap:8px;min-width:0;">
            <span class="chip mono">${escHtml(it.platform)}</span>
            <span class="mono truncate" style="font-size:13px;font-weight:500;">@${escHtml(it.handle)}</span>
          </div>
          ${statusBadge}
        `;

        const sub = document.createElement('div');
        sub.className = 'truncate';
        sub.style.fontSize = '12px';
        sub.style.color = 'var(--text-3)';
        sub.textContent = it.is_live && it.title ? it.title : `Checked: ${it.checked_at || 'Never'}`;

        const foot = document.createElement('div');
        foot.style.display = 'flex';
        foot.style.alignItems = 'center';
        foot.style.justifyContent = 'space-between';
        foot.style.gap = '8px';

        const autoLbl = document.createElement('label');
        autoLbl.className = 'switch';
        autoLbl.style.fontSize = '11.5px';
        const autoChk = document.createElement('input');
        autoChk.type = 'checkbox';
        autoChk.checked = Boolean(it.auto_record);
        autoChk.onchange = async () => {
          await pyCall('toggle_watchdog_auto_record', it.handle, autoChk.checked, it.platform);
          showToast(`Auto-record ${autoChk.checked ? 'enabled' : 'disabled'} for @${it.handle}`);
        };
        const track = document.createElement('span');
        track.className = 'switch-track';
        const spanTxt = document.createElement('span');
        spanTxt.textContent = 'Auto-rec';
        autoLbl.appendChild(autoChk);
        autoLbl.appendChild(track);
        autoLbl.appendChild(spanTxt);

        const btns = document.createElement('div');
        btns.style.display = 'flex';
        btns.style.gap = '4px';

        if (it.is_live) {
          const watchB = document.createElement('button');
          watchB.className = 'btn btn-primary btn-sm';
          watchB.textContent = 'Watch';
          watchB.onclick = () => setPreset(it.stream_url || it.url);
          btns.appendChild(watchB);
        }

        const checkB = document.createElement('button');
        checkB.className = 'btn btn-secondary btn-sm';
        checkB.textContent = 'Check';
        checkB.onclick = async () => {
          checkB.disabled = true;
          showToast(`Checking @${it.handle}...`);
          await pyCall('check_creator_live', it.handle, it.platform, it.url);
          await loadWatchdog();
        };
        btns.appendChild(checkB);

        const rmB = document.createElement('button');
        rmB.className = 'btn btn-ghost btn-icon-sm';
        rmB.title = 'Remove';
        rmB.innerHTML = '<svg class="ic ic-sm" viewBox="0 0 24 24"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>';
        rmB.onclick = async () => {
          await pyCall('remove_from_watchlist', it.handle, it.platform);
          loadWatchdog();
          showToast(`Removed @${it.handle}`);
        };
        btns.appendChild(rmB);

        foot.appendChild(autoLbl);
        foot.appendChild(btns);
        card.appendChild(top);
        card.appendChild(sub);
        card.appendChild(foot);
        container.appendChild(card);
      });
    }

    async function saveWatchdogConfig() {
      const enabled = document.getElementById('watchdogEnabledToggle').checked;
      const interval = parseInt(document.getElementById('watchdogIntervalSelect').value, 10) || 60;
      const autoRec = document.getElementById('watchdogGlobalAutoRec').checked;
      await pyCall('set_watchdog_config', enabled, interval, autoRec);
      showToast(enabled ? `Watchdog active (every ${interval}s)` : 'Watchdog paused');
      loadWatchdog();
    }

    async function onAddWatchlistClick() {
      const inp = document.getElementById('watchdogInput');
      const val = inp.value.trim();
      if (!val) return;
      const plat = document.getElementById('watchdogPlatformSelect').value;
      await pyCall('add_to_watchlist', val, plat, false);
      inp.value = '';
      loadWatchdog();
      showToast('Added creator to watchdog');
    }

    async function checkAllWatchdogClick() {
      showToast('Polling all monitored creators...');
      await pyCall('check_all_watchdog');
      loadWatchdog();
      showToast('Watchdog check complete');
    }

    // -------------------------------------------------------------------------
    // Container Repair & ffprobe Inspector
    // -------------------------------------------------------------------------
    async function onSelectRepairFileClick() {
      const res = await pyCall('select_file');
      if (res && res.file) {
        document.getElementById('repairPathInput').value = res.file;
        onInspectRepairClick();
      }
    }

    async function onInspectRepairClick() {
      hideAlert();
      const path = document.getElementById('repairPathInput').value.trim();
      if (!path) { showToast('Select a media file first', 'warn'); return; }
      const data = await pyCall('inspect_file_container', path);
      if (!data || data.error) {
        showAlert('Inspection error: ' + (data ? data.error : 'File not accessible'));
        return;
      }

      lastRepairedPath = data.path || path;
      document.getElementById('repairFileName').textContent = data.filename || path;
      document.getElementById('repairExt').textContent = data.extension || '--';
      document.getElementById('repairContainer').textContent = data.detected_container || 'unknown';
      document.getElementById('repairSize').textContent = data.size_formatted || '--';

      const probe = data.probe || {};
      const vSpec = [probe.video_codec, probe.resolution, probe.fps ? `${probe.fps}fps` : ''].filter(Boolean).join(' · ') || 'No video / unknown';
      const aSpec = [probe.audio_codec, probe.sample_rate, probe.audio_channels].filter(Boolean).join(' · ') || 'No audio / unknown';
      document.getElementById('repairVideoSpec').textContent = vSpec;
      document.getElementById('repairAudioSpec').textContent = aSpec;
      document.getElementById('repairDuration').textContent = probe.duration_formatted || '--';

      const badge = document.getElementById('repairStatusBadge');
      const notice = document.getElementById('repairNotice');
      if (data.is_mismatched) {
        badge.className = 'chip chip-warn mono';
        badge.textContent = data.status_label || 'Mismatch detected';
        notice.textContent = 'Container header mismatch detected. Lossless remux will rewrite clean headers with faststart moov atom without re-encoding video quality.';
      } else {
        badge.className = 'chip chip-ok mono';
        badge.textContent = 'Container clean';
        notice.textContent = 'Header matches disk extension. You can still remux to faststart MP4/MKV or extract lossless audio below.';
      }
      document.getElementById('repairCard').classList.remove('hidden');
    }

    async function onExecuteRepairClick() {
      const path = document.getElementById('repairPathInput').value.trim();
      if (!path) return;
      const targetFmt = document.getElementById('repairTargetSelect').value;
      const btn = document.getElementById('executeRepairBtn');
      btn.disabled = true;
      btn.textContent = 'Processing...';
      showToast(`Running FFmpeg (${targetFmt.toUpperCase()})...`);
      const res = await pyCall('repair_container', path, targetFmt);
      btn.disabled = false;
      btn.textContent = 'Run repair / convert';

      if (res && res.repaired_path) {
        lastRepairedPath = res.repaired_path;
        document.getElementById('repairPathInput').value = res.repaired_path;
        showToast(`Saved: ${res.repaired_name}`);
        onInspectRepairClick();
      } else {
        showAlert((res && res.error) ? res.error : 'Repair failed');
      }
    }

    function previewRepairedFile() {
      const p = lastRepairedPath || document.getElementById('repairPathInput').value.trim();
      if (p) playLocalMediaInStudio(p);
    }

    async function onScanRepairFolderClick() {
      showToast('Scanning download folder for broken containers...');
      const res = await pyCall('scan_repair_folder');
      if (!res || res.error) { showAlert(res ? res.error : 'Scan failed'); return; }
      folderScanCache = res.items || [];
      document.getElementById('folderScanResults').classList.remove('hidden');
      document.getElementById('folderScanSummary').textContent = `${res.total} files scanned · ${res.mismatched_count} need repair`;
      document.getElementById('repairAllBtn').classList.toggle('hidden', res.mismatched_count === 0);

      const list = document.getElementById('folderScanList');
      list.innerHTML = '';
      if (folderScanCache.length === 0) {
        list.innerHTML = '<div class="mono" style="font-size:12px;color:var(--text-3);padding:12px 0;">No media files found in folder</div>';
        return;
      }
      folderScanCache.forEach(item => {
        const row = document.createElement('div');
        row.className = 'lib-row';
        const statusCls = item.is_mismatched ? 'chip-warn' : 'chip-ok';
        row.innerHTML = `
          <div class="min-w-0">
            <div class="mono truncate" style="font-size:12.5px;color:var(--text-1);">${escHtml(item.filename)}</div>
            <div class="mono" style="font-size:11.5px;color:var(--text-3);">${item.size_mb} MB · ext .${escHtml(item.extension)} · header ${escHtml(item.detected_container)}</div>
          </div>
          <div style="display:flex;align-items:center;gap:6px;flex-shrink:0;">
            <span class="chip ${statusCls} mono">${escHtml(item.reason)}</span>
          </div>
        `;
        const actBtn = document.createElement('button');
        actBtn.className = item.is_mismatched ? 'btn btn-primary btn-sm' : 'btn btn-secondary btn-sm';
        actBtn.textContent = item.is_mismatched ? 'Repair' : 'Inspect';
        actBtn.onclick = () => {
          document.getElementById('repairPathInput').value = item.path;
          if (item.is_mismatched) onExecuteRepairClick();
          else onInspectRepairClick();
        };
        row.lastElementChild.appendChild(actBtn);
        list.appendChild(row);
      });
    }

    async function repairAllMismatched() {
      const broken = folderScanCache.filter(i => i.is_mismatched);
      if (broken.length === 0) return;
      showToast(`Repairing ${broken.length} file(s)...`);
      for (const item of broken) {
        await pyCall('repair_container', item.path, 'mp4');
      }
      showToast(`Completed batch repair of ${broken.length} file(s)`);
      onScanRepairFolderClick();
    }

    // -------------------------------------------------------------------------
    // Media Library (History & Local Folder Browser)
    // -------------------------------------------------------------------------
    function setLibraryMode(mode) {
      libraryMode = mode;
      document.getElementById('libModeHistory').classList.toggle('active', mode === 'history');
      document.getElementById('libModeFolder').classList.toggle('active', mode === 'folder');
      loadHistory();
    }

    function setLibraryTypeFilter(type) {
      libraryTypeFilter = type;
      ['all', 'video', 'live', 'audio'].forEach(t => {
        document.getElementById('libFilter-' + t)?.classList.toggle('active', t === type);
      });
      filterHistory();
    }

    async function loadHistory() {
      rawLibrary = (libraryMode === 'folder'
        ? await pyCall('scan_downloads_folder')
        : await pyCall('get_history')) || [];
      filterHistory();
    }

    function filterHistory() {
      const q = (document.getElementById('libSearchInput').value || '').toLowerCase().trim();
      const filtered = rawLibrary.filter(h => {
        const mt = (h.media_type || h.type || 'video').toLowerCase();
        if (libraryTypeFilter !== 'all') {
          if (libraryTypeFilter === 'live' && !mt.includes('live')) return false;
          if (libraryTypeFilter === 'audio' && mt !== 'audio') return false;
          if (libraryTypeFilter === 'video' && (mt === 'audio' || mt.includes('live'))) return false;
        }
        if (!q) return true;
        return (h.title || '').toLowerCase().includes(q)
          || (h.filename || '').toLowerCase().includes(q)
          || (h.ext || '').toLowerCase().includes(q);
      });
      renderHistoryList(filtered);
    }

    function renderHistoryList(items) {
      const container = document.getElementById('historyContainer');
      const totalMb = items.reduce((acc, i) => acc + (i.size_mb || 0), 0);
      document.getElementById('histTotalBadge').textContent = `${items.length} items · ${totalMb.toFixed(1)} MB`;
      container.innerHTML = '';

      if (!items || items.length === 0) {
        container.innerHTML = '<div class="mono" style="font-size:12px;color:var(--text-3);padding:32px 0;text-align:center;">No media items found</div>';
        return;
      }

      items.forEach(h => {
        const row = document.createElement('div');
        row.className = 'lib-row';
        const mt = (h.media_type || h.type || 'video').toLowerCase();
        const tag = mt.includes('live') ? 'Live' : (mt === 'audio' ? 'Audio' : (h.ext || 'Video'));
        const tagCls = mt.includes('live') ? 'chip-live' : (mt === 'audio' ? 'chip-signal' : '');

        const left = document.createElement('div');
        left.style.display = 'flex';
        left.style.alignItems = 'center';
        left.style.gap = '10px';
        left.className = 'min-w-0';
        left.innerHTML = `
          <span class="chip ${tagCls} mono" style="min-width:52px;justify-content:center;">${escHtml(tag)}</span>
          <div class="min-w-0">
            <div class="truncate" style="font-size:13px;font-weight:500;color:var(--text-1);">${escHtml(h.title || 'Media file')}</div>
            <div class="mono truncate" style="font-size:11.5px;color:var(--text-3);margin-top:2px;">
              ${escHtml(h.date_str || '')}${h.size_mb ? ' · ' + h.size_mb + ' MB' : ''}${h.exists === false ? ' · Missing on disk' : ''}
            </div>
          </div>
        `;

        const right = document.createElement('div');
        right.style.display = 'flex';
        right.style.gap = '6px';
        right.style.flexShrink = '0';

        if (h.exists && h.filename) {
          const playB = document.createElement('button');
          playB.className = 'btn btn-primary btn-sm';
          playB.textContent = 'Play';
          playB.onclick = () => playLocalMediaInStudio(h.filename, h.title);
          right.appendChild(playB);

          const revB = document.createElement('button');
          revB.className = 'btn btn-secondary btn-sm';
          revB.textContent = 'Reveal';
          revB.onclick = () => pyCall('reveal_in_explorer', h.filename);
          right.appendChild(revB);

          const repB = document.createElement('button');
          repB.className = 'btn btn-ghost btn-sm';
          repB.textContent = 'Repair';
          repB.onclick = () => {
            document.getElementById('repairPathInput').value = h.filename;
            switchTab('repair');
            onInspectRepairClick();
          };
          right.appendChild(repB);
        }

        const delB = document.createElement('button');
        delB.className = 'btn btn-ghost btn-icon-sm';
        delB.title = 'Remove';
        delB.innerHTML = '<svg class="ic ic-sm" viewBox="0 0 24 24"><polyline points="3 6 5 6 21 6"/><path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6"/><path d="M10 11v6"/><path d="M14 11v6"/></svg>';
        delB.onclick = async () => {
          await pyCall('delete_media_file', h.filename || '', h.timestamp || null);
          showToast('Removed media entry');
          loadHistory();
        };
        right.appendChild(delB);

        row.appendChild(left);
        row.appendChild(right);
        container.appendChild(row);
      });
    }

    async function onClearHistoryClick() {
      await pyCall('clear_history');
      showToast('Download history cleared');
      loadHistory();
    }

    // -------------------------------------------------------------------------
    // Settings, Diagnostics & yt-dlp.conf Editor
    // -------------------------------------------------------------------------
    async function loadSettingsTab() {
      runInlineDiagnostics();
      const [state, conf] = await Promise.all([
        pyCall('get_initial_state'),
        pyCall('get_ytdlp_conf'),
      ]);
      if (state && state.config) {
        const c = state.config;
        document.getElementById('setCookiesSelect').value = c.cookies_from_browser || 'none';
        document.getElementById('setConcurrencySelect').value = String(c.max_concurrent_downloads || 2);
        document.getElementById('setRateLimitSelect').value = c.rate_limit || '';
        document.getElementById('setProxyInput').value = c.proxy || '';
        if (state.download_dir) document.getElementById('settingsDlDir').value = state.download_dir;
      }
      if (conf && conf.content !== undefined) {
        document.getElementById('confEditorPath').textContent = conf.path || 'Default template';
        document.getElementById('confEditorArea').value = conf.content;
      }
    }

    async function saveStudioSettingsClick() {
      const payload = {
        cookies_from_browser: document.getElementById('setCookiesSelect').value,
        max_concurrent_downloads: parseInt(document.getElementById('setConcurrencySelect').value, 10) || 2,
        rate_limit: document.getElementById('setRateLimitSelect').value,
        proxy: document.getElementById('setProxyInput').value.trim(),
      };
      await pyCall('save_studio_settings', payload);
      document.getElementById('batchConcurrencySelect').value = String(payload.max_concurrent_downloads);
      showToast('Studio settings saved');
    }

    async function saveConfEditor() {
      const content = document.getElementById('confEditorArea').value;
      const res = await pyCall('save_ytdlp_conf', content);
      if (res && res.status === 'saved') {
        showToast('Saved yt-dlp.conf');
        if (res.download_dir) {
          document.getElementById('saveFolderInput').value = res.download_dir;
          document.getElementById('settingsDlDir').value = res.download_dir;
          document.getElementById('hdrDlDir').textContent = res.download_dir;
        }
      } else {
        showAlert((res && res.error) ? res.error : 'Could not save yt-dlp.conf');
      }
    }

    async function runInlineDiagnostics() {
      const res = await pyCall('run_inline_diagnostics');
      if (!res || !res.rows) return;
      const tbody = document.getElementById('diagTableBody');
      tbody.innerHTML = '';
      res.rows.forEach(r => {
        const tr = document.createElement('tr');
        const cls = r.status === 'pass' ? 'chip-ok' : (r.status === 'fail' ? 'chip-live' : (r.status === 'warn' ? 'chip-warn' : ''));
        tr.innerHTML = `
          <td style="font-weight:500;">${escHtml(r.component)}</td>
          <td><span class="chip ${cls} mono">${escHtml(r.status)}</span></td>
          <td class="mono" style="font-size:12px;color:var(--text-2);">${escHtml(r.detail)}</td>
        `;
        tbody.appendChild(tr);
      });

      if (res.health) {
        const ytOk = Boolean(res.health.ytdlp && res.health.ytdlp.ok);
        const ffOk = Boolean(res.health.ffmpeg && res.health.ffmpeg.ok);
        document.getElementById('sideYtStatus').textContent = ytOk ? 'Ready' : 'Missing';
        document.getElementById('sideYtDot').className = 'status-dot ' + (ytOk ? 'dot-ok' : 'dot-err');
        document.getElementById('sideFfStatus').textContent = ffOk ? 'Ready' : 'Missing';
        document.getElementById('sideFfDot').className = 'status-dot ' + (ffOk ? 'dot-ok' : 'dot-warn');
        if (res.health.disk_free_gb != null) {
          const dStr = `${res.health.disk_free_gb.toFixed(1)} GB`;
          document.getElementById('hdrDiskText').textContent = dStr;
          document.getElementById('sideDiskText').textContent = dStr;
        }
      }
    }

    async function updateYtdlpClick() {
      const btn = document.getElementById('updateYtdlpBtn');
      btn.disabled = true;
      btn.textContent = 'Updating...';
      showToast('Updating yt-dlp binary...');
      const res = await pyCall('update_ytdlp_binary');
      btn.disabled = false;
      btn.textContent = 'Update yt-dlp';
      if (res && res.ok) {
        showToast('yt-dlp is up to date');
        runInlineDiagnostics();
      } else {
        showToast('Update check finished — see Console logs', 'warn');
        openRightPanelTab('console');
      }
    }

    // -------------------------------------------------------------------------
    // Initialization, Keyboard Shortcuts & Global Drag-Drop
    // -------------------------------------------------------------------------
    window.addEventListener('DOMContentLoaded', () => {
      if (window.innerWidth < 1180) {
        document.getElementById('rightSidebar').classList.add('collapsed');
      }

      window.addEventListener('keydown', (e) => {
        if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') {
          e.preventDefault();
          openCommandPalette();
          return;
        }
        if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
          e.preventDefault();
          onHeroDownloadBtnClick();
          return;
        }
        if (e.key === '/' && !['INPUT', 'TEXTAREA', 'SELECT'].includes(document.activeElement.tagName)) {
          e.preventDefault();
          switchTab('studio');
          const inp = document.getElementById('streamUrlInput');
          inp.focus();
          inp.select();
        }
        if (e.key === 'Escape') {
          closeCommandPalette();
          document.getElementById('dragOverlay').classList.remove('active');
        }
      });

      // Drag & drop
      let dragDepth = 0;
      window.addEventListener('dragenter', (e) => {
        e.preventDefault();
        dragDepth++;
        document.getElementById('dragOverlay').classList.add('active');
      });
      window.addEventListener('dragleave', (e) => {
        e.preventDefault();
        dragDepth--;
        if (dragDepth <= 0) { dragDepth = 0; document.getElementById('dragOverlay').classList.remove('active'); }
      });
      window.addEventListener('dragover', (e) => e.preventDefault());
      window.addEventListener('drop', (e) => {
        e.preventDefault();
        dragDepth = 0;
        document.getElementById('dragOverlay').classList.remove('active');
        let text = e.dataTransfer.getData('text/plain') || '';
        if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
          const f = e.dataTransfer.files[0];
          if (f.path || f.name) text = f.path || f.name;
        }
        text = text.trim().replace(/^["']|["']$/g, '');
        if (!text) return;
        if (text.startsWith('http://') || text.startsWith('https://')) {
          document.getElementById('streamUrlInput').value = text;
          onUrlInputChanged(text);
          switchTab('studio');
          onAnalyzeClick();
        } else {
          document.getElementById('repairPathInput').value = text;
          switchTab('repair');
          onInspectRepairClick();
        }
      });

      // Boot state sync
      setTimeout(async () => {
        const state = await pyCall('get_initial_state');
        if (state) {
          if (state.download_dir) {
            document.getElementById('saveFolderInput').value = state.download_dir;
            document.getElementById('settingsDlDir').value = state.download_dir;
            document.getElementById('hdrDlDir').textContent = state.download_dir;
          }
          if (state.free_disk_gb != null) {
            const dStr = `${state.free_disk_gb} GB`;
            document.getElementById('hdrDiskText').textContent = dStr;
            document.getElementById('sideDiskText').textContent = dStr;
          }
          if (state.config) {
            clipboardWatchEnabled = Boolean(state.config.clipboard_watch);
            updateClipboardWatchUI();
            document.getElementById('batchConcurrencySelect').value = String(state.config.max_concurrent_downloads || 2);
            document.getElementById('chkSponsorblock').checked = Boolean(state.config.sponsorblock);
          }
          if (state.watchdog && state.watchdog.items) {
            document.getElementById('navWatchCount').textContent = String(state.watchdog.items.length);
          }
          if (!state.ffmpeg_ready) {
            document.getElementById('sideFfStatus').textContent = 'Missing';
            document.getElementById('sideFfDot').className = 'status-dot dot-warn';
          }
          if (Array.isArray(state.console_logs)) {
            consoleCache = state.console_logs;
          }
        }
        pollLoop();
      }, 150);
    });
  </script>
</body>
</html>
"""


def generate_studio_html() -> str:
    conf = find_ytdlp_conf()
    conf_name = html.escape(conf.name if conf else "Default")
    conf_dir = html.escape(str(get_conf_download_dir(conf)))
    return (
        _STUDIO_HTML
        .replace("__CONF_NAME__", conf_name)
        .replace("__CONF_DIR__", conf_dir)
    )
