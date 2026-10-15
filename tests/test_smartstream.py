"""
Unit and integration tests for StreamVortex.
"""

import unittest
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
            self.assertTrue((td_path / "tiktok-live.conf.txt").exists())
            with open(td_path / "yt-dlp.conf", "r", encoding="utf-8") as f:
                content = f.read()
                self.assertIn("-o", content)
                self.assertIn("av01", content)

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


if __name__ == "__main__":
    unittest.main()
