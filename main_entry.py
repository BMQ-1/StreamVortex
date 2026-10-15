"""
StreamVortex Standalone Executable Entry Point.
"""
import sys
import os

# Ensure base directory is in sys.path
base_dir = os.path.dirname(os.path.abspath(__file__))
if base_dir not in sys.path:
    sys.path.insert(0, base_dir)

from pathlib import Path

# Configure default Playwright browsers location
if "PLAYWRIGHT_BROWSERS_PATH" not in os.environ:
    appdata_local = os.environ.get("LOCALAPPDATA", "")
    if appdata_local:
        os.environ["PLAYWRIGHT_BROWSERS_PATH"] = str(Path(appdata_local) / "ms-playwright")

from ytdlp_smartstream.cli import main

if __name__ == "__main__":
    main()
