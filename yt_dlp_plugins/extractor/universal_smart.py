"""
yt-dlp plugin extractor for universal stream sniffing.
Allows downloading any stream by prefixing the URL with 'smart:' or 'sniff:'.
Example: yt-dlp smart:https://some-problematic-site.com/live/123
Works in both Python environment and standalone yt-dlp.exe.
"""

import json
import subprocess
from yt_dlp.extractor.common import InfoExtractor
from yt_dlp.utils import ExtractorError

try:
    from ytdlp_smartstream.sniffer import smart_sniff
    HAS_LOCAL_MODULE = True
except ImportError:
    HAS_LOCAL_MODULE = False


class UniversalSmartIE(InfoExtractor):
    IE_NAME = 'smartstream'
    IE_DESC = 'Universal Stream Sniffer & Fallback Extractor'
    _VALID_URL = r'(?:smart|sniff):(?P<url>https?://.+)'

    def _real_extract(self, url):
        target_url = self._match_valid_url(url).group('url')
        self.to_screen(f'[SmartStream] Sniffing stream from {target_url}...')

        stream_url = None
        stream_type = 'hls'
        page_title = None
        headers = {}

        if HAS_LOCAL_MODULE:
            sniffed = smart_sniff(target_url, timeout=15)
            if not sniffed:
                raise ExtractorError(
                    f'Could not detect any active stream on {target_url}',
                    expected=True
                )
            stream_url = sniffed.url
            stream_type = sniffed.stream_type
            page_title = sniffed.page_title
            headers = sniffed.headers
        else:
            cmd = ['python', '-m', 'ytdlp_smartstream.cli', '--json', target_url]
            try:
                proc = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', timeout=25)
                if proc.returncode != 0 or not proc.stdout.strip():
                    raise ExtractorError(f'Could not detect any active stream on {target_url}', expected=True)
                data = json.loads(proc.stdout)
                stream_url = data.get('url')
                formats_data = data.get('formats') or []
                if not stream_url and formats_data:
                    stream_url = formats_data[0].get('url')
                stream_type = data.get('stream_type', 'hls')
                page_title = data.get('title')
                headers = data.get('headers', {})
            except Exception as e:
                if isinstance(e, ExtractorError):
                    raise
                raise ExtractorError(f'Sniffing bridge error: {e}', expected=True)

        self.to_screen(f'[SmartStream] Found {stream_type.upper()} stream: {stream_url}')

        formats = []
        if stream_type == 'hls':
            try:
                formats = self._extract_m3u8_formats(
                    stream_url,
                    video_id=target_url,
                    ext='mp4',
                    entry_protocol='m3u8_native',
                    m3u8_id='hls',
                    fatal=False
                )
            except Exception:
                pass

        if not formats:
            formats.append({
                'format_id': f'{stream_type}-main',
                'url': stream_url,
                'ext': 'mp4' if stream_type == 'hls' else stream_type,
                'protocol': 'm3u8_native' if stream_type == 'hls' else 'https',
            })

        return {
            'id': target_url,
            'title': page_title or self._generic_title(target_url),
            'formats': formats,
            'http_headers': headers,
            'is_live': True,
        }


__all__ = ['UniversalSmartIE']
