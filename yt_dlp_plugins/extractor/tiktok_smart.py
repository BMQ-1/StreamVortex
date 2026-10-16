"""
yt-dlp plugin extractors for TikTok Live and TikTok Video (VOD).

Options (--extractor-args "smartstream:key=value;key=value"):
  timeout=30        bridge timeout in seconds
  container=mp4|ts  save live HLS as .mp4 (auto-fixed) or raw .ts (never needs a fix)
  prefer=hls|flv    which live format ranks first (hls ends cleanly; default)
  fixup=on|off      auto-register the MPEG-TS/FLV fix-up postprocessor
"""
import re

from yt_dlp.extractor.common import InfoExtractor
from yt_dlp.utils import ExtractorError

try:
    from yt_dlp.utils import UserNotLive
except ImportError:                       # older yt-dlp
    UserNotLive = None

try:
    from .tiktok_resolver import resolve_tiktok_live, resolve_tiktok_video
    HAS_LOCAL_MODULE = True
except Exception:
    try:
        from yt_dlp_plugins.extractor.tiktok_resolver import resolve_tiktok_live, resolve_tiktok_video
        HAS_LOCAL_MODULE = True
    except Exception:
        try:
            from ytdlp_smartstream.tiktok_resolver import resolve_tiktok_live, resolve_tiktok_video
            HAS_LOCAL_MODULE = True
        except Exception:
            HAS_LOCAL_MODULE = False

try:
    from . import smartstream_common as C
except ImportError:
    from yt_dlp_plugins.extractor import smartstream_common as C


class TikTokSmartLiveIE(InfoExtractor):
    IE_NAME = 'tiktok:smartlive'
    IE_DESC = 'Smart TikTok Live Stream Extractor'
    _VALID_URL = r'''(?x)(?:smart:)?https?://(?:
        (?:www\.)?tiktok\.com/@(?P<uploader>[\w.-]+)/live|
        m\.tiktok\.com/share/live/(?P<id>\d+)
    )'''

    def _not_live(self, target):
        if UserNotLive:
            return UserNotLive(video_id=target)
        return ExtractorError(
            f'@{target} is not currently live or the stream could not be extracted.',
            expected=True)

    def _username_from_share(self, url, share_id):
        """m.tiktok.com/share/live/<room_id> -> username via redirect (best effort)."""
        urlh = self._request_webpage(url, share_id, 'Resolving room share link', fatal=False)
        final = ''
        if urlh:
            final = getattr(urlh, 'url', None) or (urlh.geturl() if hasattr(urlh, 'geturl') else '')
        m = re.search(r'tiktok\.com/@([\w.-]+)', final or '')
        return m.group(1) if m else None

    def _resolve(self, target, bridge_url, timeout):
        # 1. Try in-process resolution
        if HAS_LOCAL_MODULE:
            try:
                res = resolve_tiktok_live(target)
                if res and getattr(res, 'formats', None):
                    return {
                        'id': C.pick(res, 'media_id'),
                        'title': C.pick(res, 'title'),
                        'headers': C.pick(res, 'http_headers') or {},
                        'thumbnail': C.pick(res, 'thumbnail'),
                        'formats': [C.normalize_format(f) for f in res.formats],
                    }
            except ExtractorError:
                raise
            except Exception as e:
                self.write_debug(f'In-process resolver attempt failed: {e}')

        # 2. Try native yt-dlp webpage download with yt-dlp session/cookies
        try:
            webpage = self._download_webpage(
                bridge_url, target, note='Checking live stream webpage',
                fatal=False, errnote='Could not fetch live webpage')
            if webpage:
                raw_streams = re.findall(r'(https?://[^\s"\'<>]+\.(?:m3u8|flv)[^\s"\'<>]*)', webpage)
                valid_streams = [u for u in raw_streams if any(k in u for k in ('pull', 'tiktok', 'byteoversea', 'live'))]
                if valid_streams:
                    formats = []
                    for idx, u in enumerate(set(valid_streams)):
                        is_m3u8 = '.m3u8' in u
                        formats.append({
                            'id': f'hls-raw-{idx+1}' if is_m3u8 else f'flv-raw-{idx+1}',
                            'url': u,
                            'protocol': 'm3u8_native' if is_m3u8 else 'https',
                            'ext': 'mp4' if is_m3u8 else 'flv',
                        })
                    return {
                        'id': target,
                        'title': f'TikTok Live - {target} {C.stamp()}',
                        'headers': {'Referer': bridge_url},
                        'thumbnail': None,
                        'formats': formats,
                    }
        except Exception as e:
            self.write_debug(f'Webpage scrape attempt failed: {e}')

        # 3. Fallback to bridge (Playwright WAF solver)
        try:
            data = C.run_bridge(self, bridge_url, timeout)
        except C.BridgeError as e:
            if e.code == C.EXIT_NOT_FOUND:
                raise self._not_live(target)
            raise ExtractorError(f'SmartStream bridge failed: {e}', expected=True, cause=e)

        formats = [C.normalize_format(f) for f in (data.get('formats') or [])]
        if not formats and data.get('direct_url'):
            u = data['direct_url']
            is_m3u8 = '.m3u8' in u
            formats = [{
                'id': 'main',
                'url': u,
                'protocol': 'm3u8_native' if is_m3u8 else 'https',
                'ext': 'mp4' if is_m3u8 else 'flv'
            }]

        if not formats:
            raise self._not_live(target)
        return {
            'id': data.get('id'),
            'title': data.get('title'),
            'headers': data.get('headers') or data.get('http_headers') or {},
            'thumbnail': data.get('thumbnail'),
            'formats': [C.normalize_format(f) for f in (data.get('formats') or [])],
        }

    def _real_extract(self, url):
        uploader, share_id = self._match_valid_url(url).group('uploader', 'id')
        clean_url = re.sub(r'^smart:', '', url)
        if not uploader:
            uploader = self._username_from_share(clean_url, share_id)
        target = uploader or share_id
        self.to_screen(f'[SmartStream] Resolving live stream for '
                       f'{"@" if uploader else "room "}{target}...')

        bridge_url = f'https://www.tiktok.com/@{uploader}/live' if uploader else clean_url
        resolved = self._resolve(target, bridge_url, C.int_arg(self, 'timeout', 30))

        container = 'ts' if C.arg(self, 'container', 'mp4').lower() == 'ts' else 'mp4'
        prefer = 'flv' if C.arg(self, 'prefer', 'hls').lower() == 'flv' else 'hls'
        room_id = str(resolved['id'] or target)
        headers = C.merge_headers(
            {'Referer': f'https://www.tiktok.com/@{target}/live'}, resolved['headers'])

        formats = []
        for f in resolved['formats']:
            if f.get('url'):
                formats.extend(C.build_formats(
                    self, f, room_id, headers, live=True, container=container,
                    default_kind='flv', prefer=prefer))
        if not formats:
            raise ExtractorError(f'No playable streams found for @{target}', expected=True)
        C.dedupe_format_ids(formats)
        C.register_fixup(self)

        info = {
            'id': room_id,
            'title': resolved['title'] or f'TikTok Live - {target} {C.stamp()}',
            'formats': formats,
            'is_live': True,
            'live_status': 'is_live',
            'thumbnail': resolved['thumbnail'],
            'http_headers': headers,
        }
        if uploader:
            info.update({
                'uploader': uploader,
                'uploader_id': uploader,
                'uploader_url': f'https://www.tiktok.com/@{uploader}',
                'webpage_url': f'https://www.tiktok.com/@{uploader}/live',
            })
        return info


class TikTokSmartVideoIE(InfoExtractor):
    IE_NAME = 'tiktok:smartvideo'
    IE_DESC = 'Smart TikTok Video (VOD) Extractor'
    _VALID_URL = r'smart:(?P<url>https?://(?:www\.|m\.)?tiktok\.com/@(?P<uploader>[\w.-]+)/video/(?P<id>\d+))'

    def _resolve(self, target_url, timeout):
        if HAS_LOCAL_MODULE:
            try:
                res = resolve_tiktok_video(target_url)
            except Exception as e:
                raise ExtractorError(f'TikTok resolver error: {e}', expected=True, cause=e)
            if not res or not getattr(res, 'formats', None):
                raise ExtractorError('Could not extract TikTok video stream', expected=True)
            src = res
            fmts = res.formats
        else:
            try:
                src = C.run_bridge(self, target_url, timeout)
            except C.BridgeError as e:
                raise ExtractorError(f'SmartStream bridge failed: {e}', expected=True, cause=e)
            fmts = src.get('formats') or []
            if not fmts and src.get('url'):
                fmts = [{'id': 'main', 'url': src['url'], 'ext': src.get('ext') or 'mp4'}]
            if not fmts:
                raise ExtractorError('Could not extract TikTok video stream', expected=True)
        return {
            'id': C.pick(src, 'media_id', 'id'),
            'title': C.pick(src, 'title'),
            'uploader': C.pick(src, 'uploader'),
            'thumbnail': C.pick(src, 'thumbnail'),
            'duration': C.pick(src, 'duration'),
            'headers': C.pick(src, 'http_headers', 'headers') or {},
            'formats': [C.normalize_format(f) for f in fmts],
        }

    def _real_extract(self, url):
        mobj = self._match_valid_url(url)
        target_url, vid_hint, user_hint = mobj.group('url', 'id', 'uploader')
        self.to_screen(f'[SmartStream] Extracting TikTok video {target_url}...')
        resolved = self._resolve(target_url, C.int_arg(self, 'timeout', 30))

        video_id = str(resolved['id'] or vid_hint)
        headers = C.merge_headers({'Referer': 'https://www.tiktok.com/'}, resolved['headers'])
        formats = []
        for f in resolved['formats']:
            if f.get('url'):
                formats.extend(C.build_formats(self, f, video_id, headers, live=False,
                                               default_kind='http'))
        if not formats:
            raise ExtractorError('Could not extract TikTok video stream', expected=True)
        C.dedupe_format_ids(formats)

        uploader = resolved['uploader'] or user_hint
        return {
            'id': video_id,
            'title': resolved['title'] or f'TikTok video {video_id}',
            'uploader': uploader,
            'uploader_id': user_hint,
            'uploader_url': f'https://www.tiktok.com/@{user_hint}',
            'formats': formats,
            'thumbnail': resolved['thumbnail'],
            'duration': resolved['duration'],
            'http_headers': headers,
            'webpage_url': target_url,
        }


__all__ = ['TikTokSmartLiveIE', 'TikTokSmartVideoIE']