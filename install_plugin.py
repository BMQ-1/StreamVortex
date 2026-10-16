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
    plugins_root = Path(__file__).resolve().parent / "yt_dlp_plugins"
    if not plugins_root.is_dir():
        print(f"[-] Source plugins directory not found: {plugins_root}")
        sys.exit(1)

    # Resolve target yt-dlp plugins directory
    config_dirs = list(get_user_config_dirs("yt-dlp"))
    roaming_dir = next((d for d in config_dirs if "Roaming" in str(d)), config_dirs[0])
    target_base = Path(roaming_dir) / "plugins" / "smartstream" / "yt_dlp_plugins"

    for sub in ["extractor", "postprocessor"]:
        s_dir = plugins_root / sub
        t_dir = target_base / sub
        if s_dir.exists():
            t_dir.mkdir(parents=True, exist_ok=True)
            for file in s_dir.glob("*.py"):
                dest_file = t_dir / file.name
                shutil.copy2(file, dest_file)
                print(f"[+] Installed plugin module ({sub}): {dest_file}")

    print("\n[SUCCESS] Plugin installed into yt-dlp roaming plugins folder:")
    print(f"Target: {target_base.parent}")
    print("\nYou can now run standard `yt-dlp` from any terminal!")


if __name__ == "__main__":
    install()
