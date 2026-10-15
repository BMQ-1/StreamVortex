"""
yt-dlp plugin extractors for TikTok Live and TikTok Video (VOD).
Replaces fragile built-in extractors with resilient multi-tier resolvers.
"""

import json
import subprocess
from yt_dlp.extractor.common import InfoExtractor
from yt_dlp.utils import ExtractorError

try:
    from ytdlp_smartstream.tiktok_resolver import resolve_tiktok_live, resolve_tiktok_video
    HAS_LOCAL_MODULE = True
except ImportError:
    HAS_LOCAL_MODULE = False


class TikTokSmartLiveIE(InfoExtractor):
    IE_NAME = 'tiktok:smartlive'
    IE_DESC = 'Smart TikTok Live Stream Extractor'
    _VALID_URL = r'''(?x)https?://(?:
        (?:www\.)?tiktok\.com/@(?P<uploader>[\w.-]+)/live|
        m\.tiktok\.com/share/live/(?P<id>\d+)
    )'''

    def _real_extract(self, url):
        uploader, live_id = self._match_valid_url(url).group('uploader', 'id')
        target_name = uploader or live_id

        self.to_screen(f'[StreamVortex] Resolving live stream for @{target_name}...')

        formats = []
        title = f'TikTok Live - {target_name}'
        room_id = target_name
        http_headers = {'Referer': f'https://www.tiktok.com/@{target_name}/live'}

        if HAS_LOCAL_MODULE:
            result = resolve_tiktok_live(target_name)
            if not result or not result.formats:
                raise ExtractorError(
                    f'@{target_name} is not currently live or stream could not be extracted.',
                    expected=True
                )
            title = result.title or title
            room_id = result.media_id or room_id
            http_headers = result.http_headers or http_headers

            for f in result.formats:
                if f.protocol == 'm3u8_native':
                    try:
                        m3u8_formats = self._extract_m3u8_formats(
                            f.url,
                            video_id=room_id,
                            ext='mp4',
                            entry_protocol='m3u8_native',
                            m3u8_id=f.quality_id,
                            fatal=False
                        )
                        if m3u8_formats:
                            formats.extend(m3u8_formats)
                            continue
                    except Exception:
                        pass

                    formats.append({
                        'format_id': f.quality_id,
                        'url': f.url,
                        'ext': 'mp4',
                        'protocol': 'm3u8_native',
                        'width': f.width,
                        'height': f.height,
                        'vcodec': f.vcodec or 'h264',
                        'tbr': f.tbr,
                        'format_note': f.format_note,
                    })
                else:
                    formats.append({
                        'format_id': f.quality_id,
                        'url': f.url,
                        'ext': 'flv',
                        'protocol': 'https',
                        'width': f.width,
                        'height': f.height,
                        'vcodec': f.vcodec or 'h264',
                        'tbr': f.tbr,
                        'format_note': f.format_note,
                    })
        else:
            # Running inside standalone yt-dlp.exe; invoke system python bridge
            cmd = ['python', '-m', 'ytdlp_smartstream.cli', '--json', url]
            try:
                proc = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    encoding='utf-8',
                    timeout=20
                )
                if proc.returncode != 0 or not proc.stdout.strip():
                    raise ExtractorError(
                        f'@{target_name} is not currently live or stream could not be extracted.',
                        expected=True
                    )
                data = json.loads(proc.stdout)
                room_id = data.get('id', target_name)
                title = data.get('title', title)

                for f in data.get('formats', []):
                    f_url = f.get('url')
                    if not f_url:
                        continue
                    if f.get('protocol') == 'm3u8_native':
                        try:
                            m3u8_formats = self._extract_m3u8_formats(
                                f_url,
                                video_id=room_id,
                                ext='mp4',
                                entry_protocol='m3u8_native',
                                m3u8_id=f.get('id', 'hls'),
                                fatal=False
                            )
                            if m3u8_formats:
                                formats.extend(m3u8_formats)
                                continue
                        except Exception:
                            pass

                    formats.append({
                        'format_id': f.get('id', 'stream'),
                        'url': f_url,
                        'ext': f.get('ext', 'mp4'),
                        'protocol': f.get('protocol', 'm3u8_native'),
                        'width': f.get('width'),
                        'height': f.get('height'),
                        'tbr': f.get('tbr'),
                    })
            except Exception as e:
                if isinstance(e, ExtractorError):
                    raise
                raise ExtractorError(f'Bridge resolution error: {e}', expected=True)

        if not formats:
            raise ExtractorError(f'No playable streams found for @{target_name}', expected=True)

        return {
            'id': room_id,
            'title': title,
            'uploader': target_name,
            'uploader_url': f'https://www.tiktok.com/@{target_name}',
            'formats': formats,
            'is_live': True,
            'http_headers': http_headers,
        }


class TikTokSmartVideoIE(InfoExtractor):
    IE_NAME = 'tiktok:smartvideo'
    IE_DESC = 'Smart TikTok Video (VOD) Extractor'
    _VALID_URL = r'smart:(?P<url>https?://(?:www\.)?tiktok\.com/@[\w.-]+/video/\d+)'

    def _real_extract(self, url):
        target_url = self._match_valid_url(url).group('url')
        self.to_screen(f'[StreamVortex] Extracting clean TikTok video for {target_url}...')

        if HAS_LOCAL_MODULE:
            res = resolve_tiktok_video(target_url)
        else:
            cmd = ['python', '-m', 'ytdlp_smartstream.cli', '--json', target_url]
            try:
                proc = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', timeout=20)
                data = json.loads(proc.stdout)
                res = None
            except Exception:
                res = None

        if not res or not res.formats:
            raise ExtractorError('Could not extract TikTok video stream', expected=True)

        formats = []
        for f in res.formats:
            formats.append({
                'format_id': f.quality_id,
                'url': f.url,
                'ext': f.ext,
                'width': f.width,
                'height': f.height,
                'format_note': f.format_note,
            })

        return {
            'id': res.media_id,
            'title': res.title,
            'uploader': res.uploader,
            'formats': formats,
            'thumbnail': res.thumbnail,
            'duration': res.duration,
            'http_headers': res.http_headers,
        }


__all__ = ['TikTokSmartLiveIE', 'TikTokSmartVideoIE']
