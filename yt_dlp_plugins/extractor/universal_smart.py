"""
yt-dlp plugin extractor for universal stream sniffing.
  yt-dlp smart:https://site.example/live/123
  yt-dlp sniff:https://site.example/live/123
`smart:` TikTok live/video URLs are left to the TikTok extractors.

Options (--extractor-args "smartstream:key=value;..."):
  timeout=20        sniff timeout in seconds
  live=auto|yes|no  force live/VOD handling (auto checks #EXT-X-ENDLIST)
  container=mp4|ts  save live HLS as .mp4 (auto-fixed) or raw .ts
  fixup=on|off      auto-register the MPEG-TS/FLV fix-up postprocessor
"""
import urllib.parse

from yt_dlp.extractor.common import InfoExtractor
from yt_dlp.utils import ExtractorError

try:
    from ytdlp_smartstream.sniffer import smart_sniff
    HAS_LOCAL_MODULE = True
except Exception:                         # not installed / standalone yt-dlp.exe
    HAS_LOCAL_MODULE = False

try:
    from . import smartstream_common as C
except ImportError:
    from yt_dlp_plugins.extractor import smartstream_common as C


class UniversalSmartIE(InfoExtractor):
    IE_NAME = 'smartstream'
    IE_DESC = 'Universal Stream Sniffer & Fallback Extractor'
    _VALID_URL = (r'(?:smart:(?!https?://(?:[\w-]+\.)?tiktok\.com/@[\w.-]+/(?:live\b|video/\d+))'
                  r'|sniff:)(?P<url>https?://.+)')

    def _sniff(self, target_url, timeout):
        """Return {'streams': [normalized dicts], 'title': str|None, 'headers': dict}."""
        parsed = urllib.parse.urlparse(target_url)
        path = parsed.path.lower()
        u_lower = target_url.lower()
        if path.endswith(('.m3u8', '.m3u')) or '.m3u8' in u_lower:
            stem = parsed.path.rsplit('/', 1)[-1].split('?')[0].rsplit('.', 1)[0] or 'HLS Stream'
            return {
                'streams': [{'id': 'hls-main', 'url': target_url, 'protocol': 'hls', 'ext': 'mp4'}],
                'title': stem,
                'headers': {'Referer': target_url, 'Origin': f'{parsed.scheme}://{parsed.netloc}'},
            }
        if path.endswith('.mpd') or '.mpd' in u_lower:
            stem = parsed.path.rsplit('/', 1)[-1].split('?')[0].rsplit('.', 1)[0] or 'DASH Stream'
            return {
                'streams': [{'id': 'dash-main', 'url': target_url, 'protocol': 'dash', 'ext': 'mp4'}],
                'title': stem,
                'headers': {'Referer': target_url, 'Origin': f'{parsed.scheme}://{parsed.netloc}'},
            }
        if path.endswith('.flv') or '.flv' in u_lower:
            stem = parsed.path.rsplit('/', 1)[-1].split('?')[0].rsplit('.', 1)[0] or 'FLV Stream'
            return {
                'streams': [{'id': 'flv-main', 'url': target_url, 'protocol': 'flv', 'ext': 'flv'}],
                'title': stem,
                'headers': {'Referer': target_url, 'Origin': f'{parsed.scheme}://{parsed.netloc}'},
            }

        if HAS_LOCAL_MODULE:
            try:
                sniffed = smart_sniff(target_url, timeout=timeout)
            except Exception as e:
                raise ExtractorError(f'Sniffer error: {e}', expected=True, cause=e)
            if not sniffed or not getattr(sniffed, 'url', None):
                raise ExtractorError(f'Could not detect any active stream on {target_url}',
                                     expected=True)
            stype = str(C.pick(sniffed, 'stream_type', default='hls')).lower()
            return {
                'streams': [{'id': 'main', 'url': sniffed.url, 'protocol': stype, 'ext': stype}],
                'title': C.pick(sniffed, 'page_title'),
                'headers': C.pick(sniffed, 'headers') or {},
            }
        try:
            data = C.run_bridge(self, target_url, timeout + 10)
        except C.BridgeError as e:
            if e.code == C.EXIT_NOT_FOUND:
                raise ExtractorError(f'Could not detect any active stream on {target_url}',
                                     expected=True)
            raise ExtractorError(f'Sniffing bridge failed: {e}', expected=True, cause=e)

        streams = [C.normalize_format(f) for f in (data.get('formats') or [])]
        streams = [s for s in streams if s.get('url')]
        if not streams and data.get('url'):
            stype = str(data.get('stream_type') or 'hls').lower()
            streams = [{'id': 'main', 'url': data['url'], 'protocol': stype, 'ext': stype}]
        if not streams:
            raise ExtractorError(f'Could not detect any active stream on {target_url}',
                                 expected=True)
        return {'streams': streams, 'title': data.get('title'),
                'headers': data.get('headers') or {}}

    def _real_extract(self, url):
        target_url = self._match_valid_url(url).group('url')
        self.to_screen(f'[SmartStream] Sniffing stream from {target_url}...')

        sniffed = self._sniff(target_url, C.int_arg(self, 'timeout', 20))
        parsed = urllib.parse.urlparse(target_url)
        headers = C.merge_headers(
            {'Referer': target_url, 'Origin': f'{parsed.scheme}://{parsed.netloc}'},
            sniffed['headers'])
        video_id = C.stable_id(target_url)
        container = 'ts' if C.arg(self, 'container', 'mp4').lower() == 'ts' else 'mp4'

        # live / VOD decision
        mode = C.arg(self, 'live', 'auto').lower()
        is_live = {'yes': True, 'true': True, 'no': False, 'false': False}.get(mode)

        first_hls = next((s for s in sniffed['streams'] if C.classify(s) == 'hls'), None)
        if first_hls:
            hls_live, drm = C.inspect_hls(self, first_hls['url'], video_id, headers)
            if drm:
                self.report_drm(video_id)
            if is_live is None:
                is_live = True if hls_live is None else hls_live
        if is_live is None:
            is_live = any(C.classify(s) == 'flv' for s in sniffed['streams'])

        formats = []
        for s in sniffed['streams']:
            formats.extend(C.build_formats(self, s, video_id, headers, live=is_live,
                                           container=container))
        if not formats:
            raise ExtractorError(f'Found a stream on {target_url} but could not read any formats',
                                 expected=True)
        C.dedupe_format_ids(formats)
        self.write_debug(f'Sniffed {len(formats)} format(s); live={is_live}')

        if is_live:
            C.register_fixup(self)

        title = (sniffed['title'] or self._generic_title(target_url)
                 or parsed.hostname or 'stream')
        if is_live:
            title = f'{title} {C.stamp()}'

        return {
            'id': video_id,
            'title': title,
            'formats': formats,
            'http_headers': headers,
            'is_live': is_live,
            'live_status': 'is_live' if is_live else 'not_live',
            'webpage_url': target_url,
        }


__all__ = ['UniversalSmartIE']