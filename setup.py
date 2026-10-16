from setuptools import setup, find_namespace_packages

setup(
    name="streamvortex",
    version="1.2",
    description="StreamVortex: Resilient HLS/DASH/VOD stream intelligence & live watchdog engine for yt-dlp",
    packages=find_namespace_packages(include=["yt_dlp_plugins*", "ytdlp_smartstream*"]),
    install_requires=[
        "yt-dlp>=2024.01.01",
        "playwright>=1.40.0",
        "rich>=13.0.0",
        "pyperclip>=1.8.0",
    ],
    entry_points={
        "console_scripts": [
            "streamvortex = ytdlp_smartstream.cli:main",
            "smart-stream = ytdlp_smartstream.cli:main",
        ],
    },
    python_requires=">=3.9",
)
