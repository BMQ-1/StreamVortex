"""
Plugin Installer for yt-dlp.
Automatically copies/links the smartstream plugin files into yt-dlp's roaming config directory
so standalone yt-dlp.exe can auto-detect and use it without any configuration.
"""

import sys
import shutil
from pathlib import Path
from yt_dlp.utils import get_user_config_dirs


def install():
    source_dir = Path(__file__).resolve().parent / "yt_dlp_plugins" / "extractor"
    if not source_dir.is_dir():
        print(f"[-] Source extractor directory not found: {source_dir}")
        sys.exit(1)

    # Resolve target yt-dlp plugins directory
    config_dirs = list(get_user_config_dirs("yt-dlp"))
    roaming_dir = next((d for d in config_dirs if "Roaming" in str(d)), config_dirs[0])
    target_plugin_dir = Path(roaming_dir) / "plugins" / "smartstream" / "yt_dlp_plugins" / "extractor"

    target_plugin_dir.mkdir(parents=True, exist_ok=True)

    # Copy files
    for file in source_dir.glob("*.py"):
        dest_file = target_plugin_dir / file.name
        shutil.copy2(file, dest_file)
        print(f"[+] Installed plugin module: {dest_file}")

    print("\n[SUCCESS] Plugin installed into yt-dlp roaming plugins folder:")
    print(f"Target: {target_plugin_dir.parent.parent}")
    print("\nYou can now run standard `yt-dlp` from any terminal!")


if __name__ == "__main__":
    install()
