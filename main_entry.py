"""
StreamVortex Standalone Executable Entry Point.
"""
import sys
import os
from pathlib import Path

# Configure Windows process identity and icons immediately before any framework loads
if sys.platform == "win32":
    try:
        import ctypes
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass
    try:
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("StreamVortex.1.3")
        ctypes.windll.kernel32.SetConsoleTitleW("StreamVortex v1.3")
        
        # Apply icon to console window
        hwnd = ctypes.windll.kernel32.GetConsoleWindow()
        if hwnd:
            base_p = Path(sys.executable).parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parent
            candidates = [
                base_p / "StreamVortex.ico",
                base_p / "assets" / "icon.ico",
                Path(__file__).resolve().parent / "StreamVortex.ico",
                Path(__file__).resolve().parent / "assets" / "icon.ico",
            ]
            for ico in candidates:
                if ico.exists():
                    IMAGE_ICON = 1
                    LR_LOADFROMFILE = 0x00000010
                    h_sm = ctypes.windll.user32.LoadImageW(0, str(ico), IMAGE_ICON, 16, 16, LR_LOADFROMFILE)
                    h_lg = ctypes.windll.user32.LoadImageW(0, str(ico), IMAGE_ICON, 32, 32, LR_LOADFROMFILE)
                    WM_SETICON = 0x0080
                    if h_sm:
                        ctypes.windll.user32.SendMessageW(hwnd, WM_SETICON, 0, h_sm)
                    if h_lg:
                        ctypes.windll.user32.SendMessageW(hwnd, WM_SETICON, 1, h_lg)
                    break
        # Force Explorer icon cache refresh
        ctypes.windll.shell32.SHChangeNotify(0x08000000, 0x0000, None, None)
    except Exception:
        pass

# Ensure base directory is in sys.path
base_dir = os.path.dirname(os.path.abspath(__file__))
if base_dir not in sys.path:
    sys.path.insert(0, base_dir)

# Configure default Playwright browsers location
if "PLAYWRIGHT_BROWSERS_PATH" not in os.environ:
    appdata_local = os.environ.get("LOCALAPPDATA", "")
    if appdata_local:
        os.environ["PLAYWRIGHT_BROWSERS_PATH"] = str(Path(appdata_local) / "ms-playwright")

import multiprocessing

from ytdlp_smartstream.cli import main

if __name__ == "__main__":
    multiprocessing.freeze_support()
    main()

