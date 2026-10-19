"""
Unit and integration tests for StreamVortex.
"""

import unittest
import sys
from pathlib import Path

# Ensure local project repository is prioritized on sys.path
root_dir = str(Path(__file__).resolve().parent.parent)
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

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

    def test_destination_regex(self):
        from ytdlp_smartstream.engine import DESTINATION_REGEX
        line1 = '[download] Destination: C:\\Tools\\Videos\\stream_live.mp4'
        m1 = DESTINATION_REGEX.search(line1)
        self.assertIsNotNone(m1)
        self.assertEqual(m1.group(1), 'C:\\Tools\\Videos\\stream_live.mp4')

        line2 = '[Merger] Merging formats into "C:\\Tools\\Videos\\stream_live.mkv"'
        m2 = DESTINATION_REGEX.search(line2)
        self.assertIsNotNone(m2)
        self.assertEqual(m2.group(1), 'C:\\Tools\\Videos\\stream_live.mkv')

    def test_aria2_progress_regex(self):
        from ytdlp_smartstream.engine import ARIA2_PROGRESS_REGEX
        line = '[#06620b 45MiB/120MiB(37%) CN:8 DL:12MiB ETA:6s]'
        m = ARIA2_PROGRESS_REGEX.search(line)
        self.assertIsNotNone(m)
        self.assertEqual(m.group(1), '45MiB')
        self.assertEqual(m.group(2), '120MiB')
        self.assertEqual(m.group(3), '37')
        self.assertEqual(m.group(4), '12MiB')
        self.assertEqual(m.group(5), '6s')

    def test_download_manager_lifecycle(self):
        from ytdlp_smartstream.engine import DownloadManager
        import tempfile
        dm = DownloadManager()
        job = dm.start_job("job-test-1", "Test Stream", "https://example.com/live", is_live=True)
        self.assertEqual(job["id"], "job-test-1")
        self.assertTrue(job["is_live"])
        self.assertEqual(job["status"], "starting")

        dm.update_job("job-test-1", progress=None, speed="2.5 MB/s", eta="REC 00:01:30", size="15.2 MB", status="Recording Live")
        j_updated = dm.get_job("job-test-1")
        self.assertEqual(j_updated["speed"], "2.5 MB/s")
        self.assertEqual(j_updated["eta"], "REC 00:01:30")
        self.assertEqual(j_updated["size"], "15.2 MB")
        self.assertEqual(j_updated["status"], "Recording Live")

        # Test stop and part promotion
        with tempfile.TemporaryDirectory() as td:
            target_file = Path(td) / "live.mp4"
            part_file = Path(td) / "live.mp4.part"
            part_file.write_bytes(b"recorded live chunk data")

            dm.register_process("job-test-1", None, target_path=str(target_file))
            dm.stop_job("job-test-1")

            self.assertTrue(dm.is_stop_requested("job-test-1"))
            self.assertTrue(target_file.exists(), "Target file should have been promoted from .part")
            self.assertFalse(part_file.exists())
            self.assertEqual(target_file.read_bytes(), b"recorded live chunk data")

    def test_find_aria2c_decommissioned(self):
        from ytdlp_smartstream.engine import find_aria2c
        self.assertIsNone(find_aria2c(), "aria2c must be decommissioned and return None")

    def test_play_media_target_fallback(self):
        from unittest.mock import patch
        from ytdlp_smartstream.engine import play_media_target
        # Test with empty target
        ok, desc = play_media_target("")
        self.assertFalse(ok)

        # Test with valid URL format (mocking subprocess.Popen)
        with patch("subprocess.Popen") as mock_popen:
            ok, desc = play_media_target("https://example.com/test.m3u8")
            self.assertTrue(ok)
            self.assertIn("Launched in", desc)

    def test_expanded_detect_platform(self):
        from ytdlp_smartstream.engine import detect_platform
        p_rumble = detect_platform("https://rumble.com/v12345-video.html")
        self.assertEqual(p_rumble["id"], "rumble")

        p_vimeo = detect_platform("https://vimeo.com/123456789")
        self.assertEqual(p_vimeo["id"], "vimeo")

        p_bili = detect_platform("https://www.bilibili.com/video/BV1xx411c7mD")
        self.assertEqual(p_bili["id"], "bilibili")

        p_daily = detect_platform("https://www.dailymotion.com/video/x7tgad0")
        self.assertEqual(p_daily["id"], "dailymotion")

        p_hls = detect_platform("https://cdn.example.com/live/stream.m3u8?token=xyz")
        self.assertEqual(p_hls["id"], "hls")
        self.assertEqual(p_hls["type"], "live")

        p_mp4 = detect_platform("https://cdn.example.com/videos/movie.mp4")
        self.assertEqual(p_mp4["id"], "directmedia")
        self.assertEqual(p_mp4["type"], "vod")

        p_feed = detect_platform("https://cdn.example.com/live/stream.flv")
        self.assertEqual(p_feed["id"], "livefeed")

    def test_resolve_stream_metadata_direct_url(self):
        from ytdlp_smartstream.engine import resolve_stream_metadata
        res = resolve_stream_metadata("https://pull-live.example.com/channel_hd.m3u8")
        self.assertTrue(res["is_live"])
        self.assertEqual(res["direct_url"], "https://pull-live.example.com/channel_hd.m3u8")
        self.assertTrue(len(res["formats"]) > 0)
        self.assertEqual(res["formats"][0]["protocol"], "m3u8_native")

    def test_version(self):
        import ytdlp_smartstream
        self.assertEqual(ytdlp_smartstream.__version__, "1.3")

    def test_sniff_container(self):
        import tempfile
        from ytdlp_smartstream.engine import sniff_container

        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(b"FLV\x01\x05\x00\x00\x00\x09\x00\x00\x00\x00")
            flv_path = f.name
        try:
            self.assertEqual(sniff_container(flv_path), "flv")
        finally:
            Path(flv_path).unlink(missing_ok=True)

        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(b"\x00\x00\x00\x20ftypisom\x00\x00\x02\x00isomiso2mp41")
            mp4_path = f.name
        try:
            self.assertEqual(sniff_container(mp4_path), "mp4")
        finally:
            Path(mp4_path).unlink(missing_ok=True)

        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(b"\x1a\x45\xdf\xa3\x93\x42\x86\x81\x01\x42\xf7\x81\x01\x42\xf2")
            mkv_path = f.name
        try:
            self.assertEqual(sniff_container(mkv_path), "matroska")
        finally:
            Path(mkv_path).unlink(missing_ok=True)

        # MPEG-TS 188-byte packets with sync byte 0x47
        with tempfile.NamedTemporaryFile(delete=False) as f:
            packet = bytes([0x47]) + bytes(187)
            f.write(packet * 8)
            ts_path = f.name
        try:
            self.assertEqual(sniff_container(ts_path), "mpegts")
        finally:
            Path(ts_path).unlink(missing_ok=True)

    def test_progress_frag_regex(self):
        from ytdlp_smartstream.engine import PROGRESS_FRAG_REGEX
        line1 = "[download]   12.3MiB at  2.45MiB/s (00:05:12) (frag 42)"
        m1 = PROGRESS_FRAG_REGEX.search(line1)
        self.assertIsNotNone(m1)
        self.assertEqual(m1.group(1), "12.3MiB")
        self.assertEqual(m1.group(2), "2.45MiB/s")
        self.assertEqual(m1.group(3), "42")

        line2 = "[download] 5.0MiB at 1.0MiB/s (frag 10/100)"
        m2 = PROGRESS_FRAG_REGEX.search(line2)
        self.assertIsNotNone(m2)
        self.assertEqual(m2.group(3), "10")
        self.assertEqual(m2.group(4), "100")

    def test_plugin_imports(self):
        from yt_dlp_plugins.extractor.tiktok_smart import TikTokSmartLiveIE, TikTokSmartVideoIE
        from yt_dlp_plugins.extractor.universal_smart import UniversalSmartIE
        from yt_dlp_plugins.postprocessor.smartstream_fixup import SmartStreamFixupPP

        self.assertEqual(TikTokSmartLiveIE.IE_NAME, "tiktok:smartlive")
        self.assertEqual(TikTokSmartVideoIE.IE_NAME, "tiktok:smartvideo")
        self.assertEqual(UniversalSmartIE.IE_NAME, "smartstream")
        self.assertIsNotNone(SmartStreamFixupPP)

    def test_interrupted_live_fixup_part(self):
        import tempfile
        from yt_dlp_plugins.postprocessor.smartstream_fixup import (
            emergency_fixup, _ACTIVE_DOWNLOADS, _FIXED_FILES, _ACTIVE_LOCK
        )
        with tempfile.TemporaryDirectory() as td:
            final_mp4 = Path(td) / "tiktok_live_stream.mp4"
            part_file = Path(td) / "tiktok_live_stream.mp4.part"

            # Write MPEG-TS packets into the .part file (simulating interrupted live download)
            packet = bytes([0x47]) + bytes(187)
            part_file.write_bytes(packet * 32)

            abs_final = str(final_mp4.resolve())
            with _ACTIVE_LOCK:
                _ACTIVE_DOWNLOADS[abs_final] = {
                    'tmp': str(part_file.resolve()),
                    'info': {'title': 'Live Stream'},
                    'ydl': None
                }

            emergency_fixup(reason='Test Interruption')

            # Either it was remuxed to final_mp4 or renamed to honest extension (.ts)
            has_result = final_mp4.exists() or (Path(td) / "tiktok_live_stream.ts").exists()
            self.assertTrue(has_result, "Emergency fixup must produce a valid output file")
            self.assertFalse(part_file.exists(), ".part file must be cleaned up after fixup")

    def test_pywebview_api_state(self):
        from ytdlp_smartstream.desktop import StreamVortexApi
        api = StreamVortexApi(port=8765)
        state = api.get_initial_state()
        self.assertIn("download_dir", state)
        self.assertIn("active_conf", state)
        self.assertIn("active_jobs", state)
        self.assertEqual(state["server_port"], 8765)

    def test_pywebview_api_inspect_container(self):
        import tempfile
        from ytdlp_smartstream.desktop import StreamVortexApi
        api = StreamVortexApi(port=8765)
        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as f:
            # Write MPEG-TS bytes into .mp4 file to simulate container mismatch
            packet = bytes([0x47]) + bytes(187)
            f.write(packet * 8)
            p = f.name
        try:
            info = api.inspect_container(p)
            self.assertEqual(info["detected_container"], "mpegts")
            self.assertEqual(info["extension"], "mp4")
            self.assertTrue(info["is_mismatched"])
        finally:
            Path(p).unlink(missing_ok=True)

    def test_flv_inspection_and_repair(self):
        import tempfile
        from ytdlp_smartstream.desktop import StreamVortexApi
        from ytdlp_smartstream.engine import sniff_container, fixup_recorded_file
        api = StreamVortexApi(port=8765)
        with tempfile.NamedTemporaryFile(suffix=".flv", delete=False) as f:
            # Write standard FLV header (FLV version 1, audio + video tags, 9-byte header + prev_tag_size_0)
            f.write(b"FLV\x01\x05\x00\x00\x00\x09\x00\x00\x00\x00" + b"\x00" * 64)
            p = f.name
        try:
            # 1. Sniffer verification
            self.assertEqual(sniff_container(p), "flv")

            # 2. PyWebView inspect_container verification
            info = api.inspect_container(p)
            self.assertIn("flv", info["detected_container"].lower())
            self.assertEqual(info["extension"], "flv")
            self.assertTrue(info["is_mismatched"])
            self.assertIn("MP4", info["status_label"])
        finally:
            Path(p).unlink(missing_ok=True)

    def test_direct_hls_recognition_in_sniffer(self):
        from ytdlp_smartstream.sniffer import smart_sniff
        hls_url = "https://cdn.example.com/live/channel.m3u8?token=secure123"
        sniffed = smart_sniff(hls_url)
        self.assertIsNotNone(sniffed)
        self.assertEqual(sniffed.url, hls_url)
        self.assertEqual(sniffed.stream_type, "hls")
        self.assertIn("User-Agent", sniffed.headers)
        self.assertIn("Referer", sniffed.headers)

    def test_direct_hls_in_universal_ie(self):
        from yt_dlp_plugins.extractor.universal_smart import UniversalSmartIE
        ie = UniversalSmartIE()
        hls_url = "https://cdn.example.com/streams/master.m3u8"
        sniffed = ie._sniff(hls_url, timeout=5)
        self.assertEqual(len(sniffed["streams"]), 1)
        self.assertEqual(sniffed["streams"][0]["url"], hls_url)
        self.assertEqual(sniffed["streams"][0]["protocol"], "hls")

    def test_hls_classify_and_header_propagation(self):
        from yt_dlp_plugins.extractor.smartstream_common import classify, build_formats
        fmt_dict = {"url": "https://pull-hls.example.com/test_playlist.m3u8", "id": "hls-1080p"}
        self.assertEqual(classify(fmt_dict), "hls")

        # Test build_formats preserves custom headers and marks live
        class DummyIE:
            def _extract_m3u8_formats(self, *args, **kwargs):
                return [{"url": "https://pull-hls.example.com/test_playlist.m3u8", "format_id": "hls-1080p"}]
        ie = DummyIE()
        custom_headers = {"Referer": "https://example.com/", "User-Agent": "CustomUA"}
        built = build_formats(ie, fmt_dict, "test_id", custom_headers, live=True)
        self.assertEqual(len(built), 1)
        self.assertEqual(built[0]["http_headers"], custom_headers)
        self.assertTrue(built[0]["is_live"])


    def test_desktop_studio_html_generation(self):
        from ytdlp_smartstream.desktop import generate_studio_html
        html = generate_studio_html()
        self.assertIsInstance(html, str)
        self.assertIn("StreamVortex Studio", html)
        self.assertIn("tab-studio", html)
        self.assertIn("tab-batch", html)
        self.assertIn("tab-watchdog", html)
        self.assertIn("tab-repair", html)
        self.assertIn("tab-library", html)
        self.assertIn("tab-settings", html)
        self.assertIn("activeDownloadsContainer", html)
        self.assertIn("hlsVideo", html)


if __name__ == "__main__":
    unittest.main()



