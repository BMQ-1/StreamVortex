"""
Unit and integration tests for StreamVortex.
"""

import unittest
import sys
from pathlib import Path
from ytdlp_smartstream.sniffer import sniff_static
from ytdlp_smartstream.tiktok_resolver import (
    _parse_stream_data_json,
    TikTokMediaResult,
    StreamQuality
)
from ytdlp_smartstream.recorder import copy_to_clipboard


class TestStreamVortex(unittest.TestCase):

    def test_parse_stream_data_json(self):
        sample_stream_data = """{
            "common": {"session_id": "test_session"},
            "data": {
                "origin": {
                    "main": {
                        "hls": "https://pull-hls.example.com/live/origin.m3u8",
                        "flv": "https://pull-flv.example.com/live/origin.flv",
                        "sdk_params": "{\\"vcodec\\": \\"h264\\", \\"vbitrate\\": 2500000, \\"resolution\\": \\"1920x1080\\"}"
                    }
                },
                "hd": {
                    "main": {
                        "hls": "https://pull-hls.example.com/live/hd.m3u8",
                        "flv": "https://pull-flv.example.com/live/hd.flv",
                        "sdk_params": "{\\"vcodec\\": \\"h264\\", \\"vbitrate\\": 1200000, \\"resolution\\": \\"1280x720\\"}"
                    }
                }
            }
        }"""

        formats = _parse_stream_data_json(sample_stream_data)
        self.assertEqual(len(formats), 4)

        origin_hls = next(f for f in formats if f.quality_id == "hls-origin")
        self.assertEqual(origin_hls.url, "https://pull-hls.example.com/live/origin.m3u8")
        self.assertEqual(origin_hls.width, 1920)
        self.assertEqual(origin_hls.height, 1080)
        self.assertEqual(origin_hls.tbr, 2500)
        self.assertEqual(origin_hls.protocol, "m3u8_native")

        hd_flv = next(f for f in formats if f.quality_id == "flv-hd")
        self.assertEqual(hd_flv.url, "https://pull-flv.example.com/live/hd.flv")
        self.assertEqual(hd_flv.width, 1280)
        self.assertEqual(hd_flv.height, 720)
        self.assertEqual(hd_flv.tbr, 1200)
        self.assertEqual(hd_flv.protocol, "https")

    def test_media_result_dataclass(self):
        res = TikTokMediaResult(
            media_id="123456",
            uploader="creator",
            title="Live Stream Title",
            is_live=True,
            formats=[StreamQuality(
                quality_id="hls-hd",
                url="https://example.com/stream.m3u8",
                protocol="m3u8_native",
                ext="mp4",
                width=1280,
                height=720
            )]
        )
        self.assertEqual(res.media_id, "123456")
        self.assertTrue(res.is_live)
        self.assertEqual(len(res.formats), 1)

    def test_copy_to_clipboard(self):
        success = copy_to_clipboard("https://pull-hls.example.com/test.m3u8")
        # On headless Linux without X11/xclip (e.g. GitHub Actions runner), pyperclip returns False
        self.assertIsInstance(success, bool)
        if sys.platform == "win32":
            self.assertTrue(success)

    def test_sniff_static_no_stream(self):
        res = sniff_static("https://example.com")
        self.assertIsNone(res)

    def test_sanitize_filename(self):
        from ytdlp_smartstream.engine import sanitize_filename
        dirty = 'My Video: "Live Stream" *Exclusive* / Test? <1> | \\'
        cleaned = sanitize_filename(dirty)
        for char in r'\/:*?"<>|':
            self.assertNotIn(char, cleaned)
        self.assertTrue(len(cleaned) > 0)

    def test_sanitize_title_for_filename(self):
        from ytdlp_smartstream.engine import sanitize_title_for_filename
        title = sanitize_title_for_filename("Awesome Stream", uploader="coolcreator", ext="mp4")
        self.assertEqual(title, "coolcreator - Awesome Stream.mp4")

        # When uploader already in title
        title2 = sanitize_title_for_filename("coolcreator - Today's Live", uploader="coolcreator", ext="mp4")
        self.assertEqual(title2, "coolcreator - Today's Live.mp4")

    def test_conf_has_output_template(self):
        import tempfile
        from pathlib import Path
        from ytdlp_smartstream.engine import conf_has_output_template

        with tempfile.NamedTemporaryFile("w", delete=False, suffix=".conf") as tf:
            tf.write("-f best\n-o %(title)s.%(ext)s\n")
            tf_path = Path(tf.name)

        try:
            self.assertTrue(conf_has_output_template(tf_path))
        finally:
            tf_path.unlink(missing_ok=True)

    def test_find_ytdlp_conf(self):
        from ytdlp_smartstream.engine import find_ytdlp_conf
        conf = find_ytdlp_conf()
        if conf:
            self.assertTrue(conf.exists())

    def test_find_global_python(self):
        from ytdlp_smartstream.engine import find_global_python
        py = find_global_python()
        self.assertTrue(bool(py))

    def test_find_ytdlp_global(self):
        from ytdlp_smartstream.engine import find_ytdlp
        ytdlp = find_ytdlp()
        self.assertTrue(len(ytdlp) > 0)

    def test_find_ffmpeg_global(self):
        from ytdlp_smartstream.engine import find_ffmpeg
        ffmpeg = find_ffmpeg()
        if ffmpeg:
            self.assertTrue(bool(ffmpeg))

    def test_check_environment_status(self):
        from ytdlp_smartstream.onboarding import check_environment_status
        status = check_environment_status()
        self.assertIn("ytdlp", status)
        self.assertIn("ffmpeg", status)
        self.assertIn("python", status)
        self.assertIn("player", status)
        self.assertIn("is_ready", status)

    def test_get_default_tools_dir(self):
        from ytdlp_smartstream.onboarding import get_default_tools_dir
        td = get_default_tools_dir()
        self.assertTrue(td.exists())

    def test_install_optimized_configs(self):
        import tempfile
        from pathlib import Path
        from ytdlp_smartstream.onboarding import install_optimized_configs

        with tempfile.TemporaryDirectory() as td:
            td_path = Path(td)
            ok, msg = install_optimized_configs(td_path)
            self.assertTrue(ok)
            self.assertTrue((td_path / "yt-dlp.conf").exists())
            with open(td_path / "yt-dlp.conf", "r", encoding="utf-8") as f:
                content = f.read()
                self.assertIn("-o", content)
                self.assertIn("av01", content)

    def test_deploy_embedded_ytdlp_conf(self):
        import tempfile
        from pathlib import Path
        from ytdlp_smartstream.engine import deploy_embedded_ytdlp_conf

        with tempfile.TemporaryDirectory() as td:
            td_path = Path(td)
            conf_deployed = deploy_embedded_ytdlp_conf(target_dir=td_path)
            self.assertIsNotNone(conf_deployed)
            self.assertTrue(conf_deployed.exists())
            self.assertEqual(conf_deployed.name, "yt-dlp.conf")
            content = conf_deployed.read_text(encoding="utf-8")
            self.assertIn("-o", content)
            self.assertIn("av01", content)

    def test_update_ytdlp_conf_destinations(self):
        import tempfile
        from pathlib import Path
        from ytdlp_smartstream.engine import update_ytdlp_conf_destinations, get_conf_download_dir

        with tempfile.TemporaryDirectory() as td:
            td_path = Path(td)
            conf_file = td_path / "yt-dlp.conf"
            custom_dl = td_path / "CustomDownloads"
            custom_dl.mkdir()

            ok, msg = update_ytdlp_conf_destinations(custom_dl, conf_path=conf_file)
            self.assertTrue(ok)
            self.assertTrue(conf_file.exists())

            content = conf_file.read_text(encoding="utf-8")
            self.assertIn(str(custom_dl).replace("/", "\\"), content)
            self.assertIn("subtitle:", content)
            self.assertIn("thumbnail:", content)

            detected = get_conf_download_dir(conf_file)
            self.assertEqual(detected.resolve(), custom_dl.resolve())

    def test_download_manager(self):
        from ytdlp_smartstream.engine import DownloadManager
        dm = DownloadManager()
        job = dm.start_job("job-1", "Test Stream", "https://example.com/test.m3u8")
        self.assertEqual(job["status"], "starting")
        self.assertEqual(job["title"], "Test Stream")

        dm.update_job("job-1", progress=50.0, speed="10MiB/s", eta="00:02")
        jobs = dm.get_active_jobs()
        self.assertEqual(len(jobs), 1)
        self.assertEqual(jobs[0]["progress"], 50.0)
        self.assertEqual(jobs[0]["speed"], "10MiB/s")

        dm.finish_job("job-1", success=True)
        jobs = dm.get_active_jobs()
        self.assertTrue(jobs[0]["completed"])
        self.assertEqual(jobs[0]["status"], "completed")

    def test_progress_regex(self):
        from ytdlp_smartstream.engine import PROGRESS_REGEX
        line = "[download]  65.4% of  150.25MiB at  14.20MiB/s ETA 00:04"
        m = PROGRESS_REGEX.search(line)
        self.assertIsNotNone(m)
        self.assertEqual(float(m.group(1)), 65.4)
        self.assertEqual(m.group(3), "14.20MiB/s")
        self.assertEqual(m.group(4), "00:04")

    def test_detect_platform(self):
        from ytdlp_smartstream.engine import detect_platform
        p_tt = detect_platform("https://www.tiktok.com/@creator/live")
        self.assertEqual(p_tt["id"], "tiktok")
        self.assertEqual(p_tt["name"], "TikTok Live")

        p_yt = detect_platform("https://www.youtube.com/watch?v=12345")
        self.assertEqual(p_yt["id"], "youtube")

        p_tw = detect_platform("https://www.twitch.tv/ninja")
        self.assertEqual(p_tw["id"], "twitch")

        p_kick = detect_platform("https://kick.com/streamer")
        self.assertEqual(p_kick["id"], "kick")

        p_hls = detect_platform("https://example.com/playlist.m3u8")
        self.assertEqual(p_hls["id"], "hls")

    def test_clean_target_url(self):
        from ytdlp_smartstream.engine import clean_target_url
        raw = " https://www.youtube.com/watch?v=12345&utm_source=share&si=abc123 "
        cleaned = clean_target_url(raw)
        self.assertIn("v=12345", cleaned)
        self.assertNotIn("utm_source", cleaned)
        self.assertNotIn("si=", cleaned)

    def test_check_free_disk_space(self):
        from ytdlp_smartstream.engine import check_free_disk_space
        has_space, free_gb = check_free_disk_space()
        self.assertIsInstance(has_space, bool)
        self.assertGreater(free_gb, 0.0)

    def test_get_conf_format(self):
        import tempfile
        from pathlib import Path
        from ytdlp_smartstream.engine import get_conf_format

        with tempfile.NamedTemporaryFile("w", delete=False, suffix=".conf") as tf:
            tf.write("# -f 1080p\n-f \"(bestvideo[height<=720]+bestaudio/best[height<=720])\"\n--merge-output-format mkv\n")
            tf_path = Path(tf.name)

        try:
            fmt = get_conf_format(tf_path)
            self.assertEqual(fmt, "(bestvideo[height<=720]+bestaudio/best[height<=720])")
        finally:
            tf_path.unlink(missing_ok=True)

    def test_build_format_args_best_overrides_720p_conf(self):
        import tempfile
        from pathlib import Path
        from ytdlp_smartstream.engine import build_format_args

        with tempfile.NamedTemporaryFile("w", delete=False, suffix=".conf") as tf:
            tf.write("-f \"(bestvideo[height<=720]+bestaudio/best[height<=720])\"\n")
            tf_path = Path(tf.name)

        try:
            # Test 'bestquality', 'best', and 'max'
            for pref in ["bestquality", "best", "max"]:
                args, reason = build_format_args(quality_preference=pref, conf_path=tf_path)
                self.assertIn("-f", args)
                f_idx = args.index("-f")
                self.assertEqual(args[f_idx + 1], "(bestvideo+bestaudio/best)")
                self.assertIn("-S", args)
                self.assertIn("overriding", reason.lower())
                self.assertIn("720", reason)
        finally:
            tf_path.unlink(missing_ok=True)

    def test_build_format_args_respect_conf(self):
        import tempfile
        from pathlib import Path
        from ytdlp_smartstream.engine import build_format_args

        with tempfile.NamedTemporaryFile("w", delete=False, suffix=".conf") as tf:
            tf.write("-f \"(bestvideo[height<=720]+bestaudio/best[height<=720])\"\n")
            tf_path = Path(tf.name)

        try:
            args, reason = build_format_args(quality_preference="conf", conf_path=tf_path)
            self.assertEqual(args, [])
            self.assertIn("Respecting", reason)
            self.assertIn("720", reason)
        finally:
            tf_path.unlink(missing_ok=True)

    def test_build_format_args_audio_overrides_video_conf(self):
        import tempfile
        from pathlib import Path
        from ytdlp_smartstream.engine import build_format_args

        with tempfile.NamedTemporaryFile("w", delete=False, suffix=".conf") as tf:
            tf.write("-f \"(bestvideo[height>=1440]+bestaudio)\"\n--merge-output-format mkv\n")
            tf_path = Path(tf.name)

        try:
            args, reason = build_format_args(quality_preference="audio_mp3", conf_path=tf_path)
            self.assertIn("-f", args)
            f_idx = args.index("-f")
            self.assertEqual(args[f_idx + 1], "bestaudio/best")
            self.assertIn("--no-keep-video", args)
            self.assertIn("pure audio", reason.lower())
        finally:
            tf_path.unlink(missing_ok=True)

    def test_build_format_args_explicit_resolutions(self):
        from ytdlp_smartstream.engine import build_format_args

        # 1080p
        args_1080, _ = build_format_args("1080p")
        self.assertIn("-f", args_1080)
        self.assertIn("height<=1080", args_1080[args_1080.index("-f") + 1])
        self.assertIn("--merge-output-format", args_1080)
        self.assertIn("mp4", args_1080)

        # 720p
        args_720, _ = build_format_args("720p")
        self.assertIn("-f", args_720)
        self.assertIn("height<=720", args_720[args_720.index("-f") + 1])

        # 480p
        args_480, _ = build_format_args("480p")
        self.assertIn("-f", args_480)
        self.assertIn("height<=480", args_480[args_480.index("-f") + 1])

    def test_build_format_args_live_stream(self):
        from ytdlp_smartstream.engine import build_format_args

        args_live, reason = build_format_args("max", is_live=True)
        self.assertIn("-f", args_live)
        self.assertEqual(args_live[args_live.index("-f") + 1], "best/bestvideo+bestaudio/b")
        self.assertIn("Live stream", reason)


    def test_sanitize_filename_reserved_names(self):
        from ytdlp_smartstream.engine import sanitize_filename
        self.assertEqual(sanitize_filename("CON"), "media_CON")
        self.assertEqual(sanitize_filename("aux.mp4"), "media_aux.mp4")
        self.assertEqual(sanitize_filename("NUL"), "media_NUL")
        self.assertEqual(sanitize_filename("com1"), "media_com1")
        self.assertEqual(sanitize_filename("lpt3.mkv"), "media_lpt3.mkv")
        # Regular safe names should not be touched
        self.assertEqual(sanitize_filename("concert_live"), "concert_live")

    def test_clean_target_url_injection_defense(self):
        from ytdlp_smartstream.engine import clean_target_url
        # Strips leading dashes meant for CLI option injection
        dirty_url = "--output evil.sh https://www.youtube.com/watch?v=12345&utm_source=share"
        cleaned = clean_target_url(dirty_url)
        self.assertFalse(cleaned.startswith("-"))
        self.assertNotIn("utm_source", cleaned)

    def test_progress_live_regex(self):
        from ytdlp_smartstream.engine import PROGRESS_LIVE_REGEX
        line = "[download]  14.25MiB at    1.50MiB/s (00:01:23)"
        m = PROGRESS_LIVE_REGEX.search(line)
        self.assertIsNotNone(m)
        self.assertEqual(m.group(1), "14.25MiB")
        self.assertEqual(m.group(2), "1.50MiB/s")
        self.assertEqual(m.group(3), "00:01:23")

    def test_ffmpeg_progress_regex(self):
        from ytdlp_smartstream.engine import FFMPEG_PROGRESS_REGEX
        line = "frame= 1245 fps= 30 q=-1.0 size=   18432kB time=00:01:02.34 bitrate=2422.1kbits/s speed=1.01x"
        m = FFMPEG_PROGRESS_REGEX.search(line)
        self.assertIsNotNone(m)
        self.assertEqual(m.group(1), "18432kB")
        self.assertEqual(m.group(2), "00:01:02.34")
        self.assertEqual(m.group(3), "2422.1kbits/s")
        self.assertEqual(m.group(4), "1.01x")

    def test_cleanup_empty_or_broken_files(self):
        import tempfile
        from ytdlp_smartstream.engine import cleanup_empty_or_broken_files

        with tempfile.TemporaryDirectory() as td:
            td_path = Path(td)
            # Create a 0-byte file
            ghost_file = td_path / "test_stream.mp4"
            ghost_file.write_bytes(b"")

            # Create an incomplete .part file
            part_file = td_path / "test_stream.mp4.part"
            part_file.write_bytes(b"partial content")

            # Create a valid non-empty file
            valid_file = td_path / "other_valid.mp4"
            valid_file.write_bytes(b"valid content here")

            cleanup_empty_or_broken_files(td_path, target_stem="test_stream")

            self.assertFalse(ghost_file.exists(), "Ghost 0-byte file should have been cleaned up")
            self.assertFalse(part_file.exists(), "Part file should have been cleaned up")
            self.assertTrue(valid_file.exists(), "Valid non-empty file should remain untouched")

    def test_version(self):
        import ytdlp_smartstream
        self.assertEqual(ytdlp_smartstream.__version__, "1.0")


if __name__ == "__main__":
    unittest.main()

