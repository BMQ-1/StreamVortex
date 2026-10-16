"""
Robust multi-tier TikTok Live & Video Resolver.
Bypasses Akamai/Slardar WAF challenges and extracts all multi-bitrate HLS, FLV, and MP4 VOD streams.
"""

import json
import re
import urllib.request
import urllib.parse
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field

try:
    from .sniffer import DEFAULT_USER_AGENT
except Exception:
    DEFAULT_USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"

M3U8_OR_FLV_REGEX = re.compile(
    r'(https?://pull-[^\s"\'<>]+\.(?:m3u8|flv)[^\s"\'<>]*)',
    re.IGNORECASE
)


@dataclass
class StreamQuality:
    quality_id: str
    url: str
    protocol: str  # 'm3u8_native', 'https', or 'http'
    ext: str       # 'mp4' or 'flv'
    width: Optional[int] = None
    height: Optional[int] = None
    vcodec: Optional[str] = None
    tbr: Optional[int] = None
    format_note: Optional[str] = None


@dataclass
class TikTokMediaResult:
    media_id: str
    uploader: str
    title: str
    is_live: bool
    formats: List[StreamQuality] = field(default_factory=list)
    http_headers: Dict[str, str] = field(default_factory=dict)
    thumbnail: Optional[str] = None
    duration: Optional[float] = None
    raw_data: Dict[str, Any] = field(default_factory=dict)
    direct_url: Optional[str] = None

    def __post_init__(self):
        if not self.direct_url and self.formats:
            self.direct_url = self.formats[0].url


# Backwards compatibility alias
TikTokLiveResult = TikTokMediaResult


def _parse_stream_data_json(stream_data_str: str) -> List[StreamQuality]:
    """
    Parses TikTok's live_core_sdk_data.pull_data.stream_data JSON string
    and returns a structured list of formats for each quality.
    """
    formats: List[StreamQuality] = []
    try:
        data = json.loads(stream_data_str)
        quality_map = data.get("data", {})

        for q_id, q_data in quality_map.items():
            main = q_data.get("main", {})
            sdk_params_raw = main.get("sdk_params", "{}")
            sdk_params = {}
            if isinstance(sdk_params_raw, str):
                try:
                    sdk_params = json.loads(sdk_params_raw)
                except Exception:
                    pass

            vcodec = sdk_params.get("vcodec") or sdk_params.get("VCodec")
            vbitrate = sdk_params.get("vbitrate")
            tbr = int(vbitrate / 1000) if vbitrate else None
            res_str = sdk_params.get("resolution", "")
            width, height = None, None
            if "x" in res_str:
                parts = res_str.split("x")
                try:
                    width, height = int(parts[0]), int(parts[1])
                except Exception:
                    pass

            hls_url = main.get("hls")
            if hls_url:
                formats.append(StreamQuality(
                    quality_id=f"hls-{q_id}",
                    url=hls_url,
                    protocol="m3u8_native",
                    ext="mp4",
                    width=width,
                    height=height,
                    vcodec=vcodec,
                    tbr=tbr,
                    format_note=f"HLS {q_id}"
                ))

            flv_url = main.get("flv")
            if flv_url:
                formats.append(StreamQuality(
                    quality_id=f"flv-{q_id}",
                    url=flv_url,
                    protocol="https",
                    ext="flv",
                    width=width,
                    height=height,
                    vcodec=vcodec,
                    tbr=tbr,
                    format_note=f"FLV {q_id}"
                ))
    except Exception:
        pass

    return formats


def _find_stream_data_recursively(obj):
    """Recursively search any dictionary/list for TikTok stream data or pull URLs."""
    if isinstance(obj, dict):
        if "live_core_sdk_data" in obj and isinstance(obj["live_core_sdk_data"], dict):
            s_str = obj["live_core_sdk_data"].get("pull_data", {}).get("stream_data")
            if s_str:
                return s_str, obj
        if "stream_data" in obj and isinstance(obj["stream_data"], str):
            return obj["stream_data"], obj
        for k in ("streamUrl", "stream_url", "streamData", "stream_data"):
            if k in obj and isinstance(obj[k], dict):
                inner = obj[k]
                s_str = inner.get("live_core_sdk_data", {}).get("pull_data", {}).get("stream_data") or inner.get("pull_data", {}).get("stream_data")
                if s_str:
                    return s_str, inner
                if inner.get("hls_pull_url") or inner.get("flv_pull_url"):
                    return None, inner

        for v in obj.values():
            s_str, parent = _find_stream_data_recursively(v)
            if s_str or parent:
                return s_str, parent
    elif isinstance(obj, list):
        for item in obj:
            s_str, parent = _find_stream_data_recursively(item)
            if s_str or parent:
                return s_str, parent
    return None, None


def _extract_from_universal_data(data: Dict[str, Any], uploader: str) -> Optional[TikTokMediaResult]:
    """
    Extracts live stream formats from parsed __UNIVERSAL_DATA_FOR_REHYDRATION__ or SIGI_STATE.
    Searches webapp.live-detail, webapp.user-detail, webapp.room-detail, and recursive tree.
    """
    scope = data.get("__DEFAULT_SCOPE__", {})
    
    # Check modern webapp.live-detail, webapp.user-detail, webapp.room-detail
    live_detail = scope.get("webapp.live-detail", {})
    live_room = live_detail.get("liveRoom") or live_detail.get("liveInfo") or {}
    
    if not live_room:
        user_detail = scope.get("webapp.user-detail", {})
        live_room = user_detail.get("liveInfo") or user_detail.get("liveRoom") or {}

    if not live_room:
        room_detail = scope.get("webapp.room-detail", {})
        live_room = room_detail.get("liveRoom") or room_detail.get("roomInfo") or {}

    title = live_room.get("title") or f"TikTok Live by {uploader}"
    room_id = str(live_room.get("roomId") or live_room.get("id") or "")

    formats: List[StreamQuality] = []

    # 1. Look for streamUrl / stream_url / streamData in live_room
    stream_url_obj = live_room.get("streamUrl") or live_room.get("stream_url") or live_room.get("streamData") or {}
    if isinstance(stream_url_obj, dict):
        pull_data = stream_url_obj.get("live_core_sdk_data", {}).get("pull_data", {}) or stream_url_obj.get("pull_data", {})
        stream_data_str = pull_data.get("stream_data")
        if stream_data_str:
            formats.extend(_parse_stream_data_json(stream_data_str))

        hls_main = stream_url_obj.get("hls_pull_url")
        if hls_main and not any(f.url == hls_main for f in formats):
            formats.append(StreamQuality(
                quality_id="hls-origin",
                url=hls_main,
                protocol="m3u8_native",
                ext="mp4",
                format_note="HLS Master"
            ))

        flv_pull = stream_url_obj.get("flv_pull_url", {})
        if isinstance(flv_pull, dict):
            for q, u in flv_pull.items():
                if u and not any(f.url == u for f in formats):
                    formats.append(StreamQuality(
                        quality_id=f"flv-{q.lower()}",
                        url=u,
                        protocol="https",
                        ext="flv",
                        format_note=f"FLV {q}"
                    ))

    # 2. Deep recursive search if not found in top-level structures
    if not formats:
        s_str, parent_obj = _find_stream_data_recursively(data)
        if s_str:
            formats.extend(_parse_stream_data_json(s_str))
        if parent_obj and isinstance(parent_obj, dict):
            hls = parent_obj.get("hls_pull_url")
            if hls and not any(f.url == hls for f in formats):
                formats.append(StreamQuality(
                    quality_id="hls-origin",
                    url=hls,
                    protocol="m3u8_native",
                    ext="mp4",
                    format_note="HLS Master"
                ))
            flv = parent_obj.get("flv_pull_url", {})
            if isinstance(flv, dict):
                for q, u in flv.items():
                    if u and not any(f.url == u for f in formats):
                        formats.append(StreamQuality(
                            quality_id=f"flv-{q.lower()}",
                            url=u,
                            protocol="https",
                            ext="flv",
                            format_note=f"FLV {q}"
                        ))

    if formats:
        return TikTokMediaResult(
            media_id=room_id or uploader,
            uploader=uploader,
            title=title,
            is_live=True,
            formats=formats,
            http_headers={
                "User-Agent": DEFAULT_USER_AGENT,
                "Referer": f"https://www.tiktok.com/@{uploader}/live"
            }
        )
    return None


def resolve_tiktok_live_fast(uploader: str) -> Optional[TikTokMediaResult]:
    """
    Tier 1 & 2: Static fetch and TikTokLive client resolution.
    Runs in under 1-2 seconds.
    """
    # Try TikTokLive client if installed
    try:
        import asyncio
        from TikTokLive import TikTokLiveClient

        async def _fetch():
            client = TikTokLiveClient(unique_id=uploader)
            try:
                is_live = await client.web.fetch_is_live(unique_id=uploader)
                if not is_live:
                    return None
            except Exception:
                pass
            room_info = await client.web.fetch_room_info(unique_id=uploader)
            if room_info and room_info.get("status") is not None and room_info.get("status") != 2:
                return None
            return room_info

        try:
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                loop = None

            if loop and loop.is_running():
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as pool:
                    room_info = pool.submit(asyncio.run, _fetch()).result(timeout=6)
            else:
                room_info = asyncio.run(_fetch())

            if room_info:
                stream_url = room_info.get("stream_url", {})
                title = room_info.get("title", f"TikTok Live by {uploader}")
                room_id = str(room_info.get("id", ""))

                formats: List[StreamQuality] = []

                sdk_data = stream_url.get("live_core_sdk_data", {})
                pull_data = sdk_data.get("pull_data", {})
                stream_data_str = pull_data.get("stream_data")
                if stream_data_str:
                    formats.extend(_parse_stream_data_json(stream_data_str))

                hls_main = stream_url.get("hls_pull_url")
                if hls_main and not any(f.url == hls_main for f in formats):
                    formats.append(StreamQuality(
                        quality_id="hls-origin",
                        url=hls_main,
                        protocol="m3u8_native",
                        ext="mp4",
                        format_note="HLS Master"
                    ))

                flv_map = stream_url.get("flv_pull_url", {})
                if isinstance(flv_map, dict):
                    for q, u in flv_map.items():
                        if u and not any(f.url == u for f in formats):
                            formats.append(StreamQuality(
                                quality_id=f"flv-{q.lower()}",
                                url=u,
                                protocol="https",
                                ext="flv",
                                format_note=f"FLV {q}"
                            ))

                if formats:
                    return TikTokMediaResult(
                        media_id=room_id,
                        uploader=uploader,
                        title=title,
                        is_live=True,
                        formats=formats,
                        http_headers={
                            "User-Agent": DEFAULT_USER_AGENT,
                            "Referer": f"https://www.tiktok.com/@{uploader}/live"
                        }
                    )
        except Exception:
            pass
    except ImportError:
        pass

    # Direct Webcast API fallback 1: webcast.tiktok.com
    try:
        webcast_url = f"https://webcast.tiktok.com/webcast/room/info_by_user/?aid=1988&app_language=en-US&app_name=tiktok_web&channel=tiktok_web&device_platform=web&uniqueId={uploader}"
        req = urllib.request.Request(
            webcast_url,
            headers={
                "User-Agent": DEFAULT_USER_AGENT,
                "Referer": f"https://www.tiktok.com/@{uploader}/live",
                "Accept": "application/json"
            }
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            room_data = data.get("data", {})
            if isinstance(room_data, dict) and room_data.get("stream_url"):
                stream_url = room_data.get("stream_url", {})
                formats = []
                pull_data = stream_url.get("live_core_sdk_data", {}).get("pull_data", {})
                stream_data_str = pull_data.get("stream_data")
                if stream_data_str:
                    formats.extend(_parse_stream_data_json(stream_data_str))

                hls_main = stream_url.get("hls_pull_url")
                if hls_main and not any(f.url == hls_main for f in formats):
                    formats.append(StreamQuality(
                        quality_id="hls-origin",
                        url=hls_main,
                        protocol="m3u8_native",
                        ext="mp4",
                        format_note="HLS Master"
                    ))
                flv_map = stream_url.get("flv_pull_url", {})
                if isinstance(flv_map, dict):
                    for q, u in flv_map.items():
                        if u and not any(f.url == u for f in formats):
                            formats.append(StreamQuality(
                                quality_id=f"flv-{q.lower()}",
                                url=u,
                                protocol="https",
                                ext="flv",
                                format_note=f"FLV {q}"
                            ))
                if formats:
                    return TikTokMediaResult(
                        media_id=str(room_data.get("id_str") or room_data.get("id") or uploader),
                        uploader=uploader,
                        title=room_data.get("title", f"TikTok Live by {uploader}"),
                        is_live=True,
                        formats=formats,
                        http_headers={
                            "User-Agent": DEFAULT_USER_AGENT,
                            "Referer": f"https://www.tiktok.com/@{uploader}/live"
                        }
                    )
    except Exception:
        pass

    # Direct Webcast API fallback 2: api-live/user/room
    try:
        api_url = f"https://www.tiktok.com/api-live/user/room/?aid=1988&uniqueId={uploader}&sourceType=54"
        req = urllib.request.Request(
            api_url,
            headers={
                "User-Agent": DEFAULT_USER_AGENT,
                "Referer": f"https://www.tiktok.com/@{uploader}/live",
                "Accept": "application/json"
            }
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            live_room = data.get("data", {}).get("liveRoom", {})
            status = live_room.get("status")
            if status == 2:
                stream_url = live_room.get("streamUrl", {})
                stream_data_str = stream_url.get("live_core_sdk_data", {}).get("pull_data", {}).get("stream_data")
                if stream_data_str:
                    formats = _parse_stream_data_json(stream_data_str)
                    if formats:
                        return TikTokMediaResult(
                            media_id=str(live_room.get("roomId", "")),
                            uploader=uploader,
                            title=live_room.get("title", f"TikTok Live by {uploader}"),
                            is_live=True,
                            formats=formats,
                            http_headers={
                                "User-Agent": DEFAULT_USER_AGENT,
                                "Referer": f"https://www.tiktok.com/@{uploader}/live"
                            }
                        )
    except Exception:
        pass

    # Direct Webpage scrape fallback
    try:
        page_url = f"https://www.tiktok.com/@{uploader}/live"
        req = urllib.request.Request(
            page_url,
            headers={
                "User-Agent": DEFAULT_USER_AGENT,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9",
            }
        )
        with urllib.request.urlopen(req, timeout=6) as resp:
            html = resp.read().decode("utf-8", errors="ignore")
            # 1. Search for rehydration script
            m_rehyd = re.search(r'id=["\']__UNIVERSAL_DATA_FOR_REHYDRATION__["\'][^>]*>(.*?)</script>', html, re.DOTALL)
            if m_rehyd:
                try:
                    d = json.loads(m_rehyd.group(1))
                    res = _extract_from_universal_data(d, uploader)
                    if res and res.formats:
                        return res
                except Exception:
                    pass

            # 2. Search for direct HLS or FLV links in page HTML
            raw_streams = re.findall(r'(https?://[^\s"\'<>]+\.(?:m3u8|flv)[^\s"\'<>]*)', html)
            valid_streams = [u for u in raw_streams if any(k in u for k in ("pull", "tiktok", "byteoversea", "live"))]
            if valid_streams:
                formats = []
                for idx, u in enumerate(set(valid_streams)):
                    is_m3u8 = ".m3u8" in u
                    formats.append(StreamQuality(
                        quality_id=f"hls-raw-{idx+1}" if is_m3u8 else f"flv-raw-{idx+1}",
                        url=u,
                        protocol="m3u8_native" if is_m3u8 else "https",
                        ext="mp4" if is_m3u8 else "flv",
                        format_note="Extracted from Live Page HTML"
                    ))
                return TikTokMediaResult(
                    media_id=uploader,
                    uploader=uploader,
                    title=f"TikTok Live by {uploader}",
                    is_live=True,
                    formats=formats,
                    http_headers={
                        "User-Agent": DEFAULT_USER_AGENT,
                        "Referer": page_url
                    }
                )
    except Exception:
        pass

    return None


def resolve_tiktok_live_browser(uploader: str, timeout: int = 15) -> Optional[TikTokMediaResult]:
    """
    Tier 3: Playwright headless browser extraction.
    Bypasses Slardar/Akamai WAF challenges and extracts stream data from rendered DOM or network.
    """
    target_url = f"https://www.tiktok.com/@{uploader}/live"
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return None

    intercepted_streams: List[StreamQuality] = []
    title = f"TikTok Live by {uploader}"
    room_id = uploader

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-blink-features=AutomationControlled",
                "--mute-audio",
                "--disable-web-security"
            ]
        )
        context = browser.new_context(
            user_agent=DEFAULT_USER_AGENT,
            viewport={"width": 1280, "height": 720}
        )
        page = context.new_page()
        page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined});")

        def on_response(resp):
            try:
                r_url = resp.url
                if ".m3u8" in r_url and "apple.com" not in r_url:
                    if not any(f.url == r_url for f in intercepted_streams):
                        intercepted_streams.append(StreamQuality(
                            quality_id=f"hls-live-{len(intercepted_streams)+1}",
                            url=r_url,
                            protocol="m3u8_native",
                            ext="mp4",
                            format_note="Intercepted HLS Stream"
                        ))
                elif ".flv" in r_url:
                    if not any(f.url == r_url for f in intercepted_streams):
                        intercepted_streams.append(StreamQuality(
                            quality_id=f"flv-live-{len(intercepted_streams)+1}",
                            url=r_url,
                            protocol="https",
                            ext="flv",
                            format_note="Intercepted FLV Stream"
                        ))
            except Exception:
                pass

        page.on("response", on_response)

        try:
            page.goto(target_url, timeout=timeout * 1000, wait_until="domcontentloaded")
            page.wait_for_timeout(4000)

            # Check DOM rehydration
            loc = page.locator("#__UNIVERSAL_DATA_FOR_REHYDRATION__")
            if loc.count() > 0:
                raw_text = loc.text_content()
                if raw_text:
                    dom_data = json.loads(raw_text)
                    result = _extract_from_universal_data(dom_data, uploader)
                    if result and result.formats:
                        browser.close()
                        return result
        except Exception:
            pass

        # If network responses intercepted playable live streams, return them immediately!
        if intercepted_streams:
            browser.close()
            return TikTokMediaResult(
                media_id=room_id,
                uploader=uploader,
                title=title,
                is_live=True,
                formats=intercepted_streams,
                http_headers={
                    "User-Agent": DEFAULT_USER_AGENT,
                    "Referer": target_url
                }
            )

        # Also inspect page HTML for direct stream strings
        try:
            page_html = page.content()
            raw_streams = re.findall(r'(https?://[^\s"\'<>]+\.(?:m3u8|flv)[^\s"\'<>]*)', page_html)
            valid_streams = [u for u in raw_streams if any(k in u for k in ("pull", "tiktok", "byteoversea", "live"))]
            if valid_streams:
                formats = []
                for idx, u in enumerate(set(valid_streams)):
                    is_m3u8 = ".m3u8" in u
                    formats.append(StreamQuality(
                        quality_id=f"hls-page-{idx+1}" if is_m3u8 else f"flv-page-{idx+1}",
                        url=u,
                        protocol="m3u8_native" if is_m3u8 else "https",
                        ext="mp4" if is_m3u8 else "flv",
                        format_note="Captured from Rendered Live Page"
                    ))
                browser.close()
                return TikTokMediaResult(
                    media_id=room_id,
                    uploader=uploader,
                    title=title,
                    is_live=True,
                    formats=formats,
                    http_headers={
                        "User-Agent": DEFAULT_USER_AGENT,
                        "Referer": target_url
                    }
                )
        except Exception:
            pass

        browser.close()

    return None


def resolve_tiktok_live(uploader: str, timeout: int = 15) -> Optional[TikTokMediaResult]:
    """
    Master TikTok Live resolver:
    1. Fast API/TikTokLive resolution (instant)
    2. Headless browser WAF resolution fallback
    """
    res = resolve_tiktok_live_fast(uploader)
    if res and res.formats:
        return res

    return resolve_tiktok_live_browser(uploader, timeout=timeout)


def resolve_tiktok_video(video_url: str, timeout: int = 15) -> Optional[TikTokMediaResult]:
    """
    Resolves standard TikTok VOD / Video URLs when yt-dlp gets blocked by Akamai or captcha.
    Extracts high-resolution non-watermarked and watermarked MP4 streams.
    """
    m = re.search(r'tiktok\.com/@([\w.-]+)/video/(\d+)', video_url)
    if not m:
        return None
    uploader, video_id = m.group(1), m.group(2)

    # 1. Try Headless DOM rehydration
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True, args=["--no-sandbox", "--disable-blink-features=AutomationControlled"])
            context = browser.new_context(user_agent=DEFAULT_USER_AGENT)
            page = context.new_page()
            page.route("**/*.{png,jpg,jpeg,gif,webp,svg,woff,woff2,ttf,css}", lambda r: r.abort())

            video_srcs = []
            def on_response(resp):
                c_type = resp.headers.get("content-type", "")
                if "video/mp4" in c_type or ".mp4" in resp.url:
                    video_srcs.append(resp.url)

            page.on("response", on_response)

            try:
                page.goto(video_url, timeout=timeout * 1000, wait_until="domcontentloaded")
                page.wait_for_timeout(2500)

                # Look for rehydration JSON
                loc = page.locator("#__UNIVERSAL_DATA_FOR_REHYDRATION__")
                if loc.count() > 0:
                    raw_text = loc.text_content()
                    if raw_text:
                        data = json.loads(raw_text)
                        item_info = (
                            data.get("__DEFAULT_SCOPE__", {})
                            .get("webapp.video-detail", {})
                            .get("itemInfo", {})
                            .get("itemStruct", {})
                        )
                        if item_info:
                            video_meta = item_info.get("video", {})
                            play_addr = video_meta.get("playAddr")
                            download_addr = video_meta.get("downloadAddr")
                            desc = item_info.get("desc", f"TikTok Video {video_id}")
                            thumb = video_meta.get("cover")
                            duration = item_info.get("video", {}).get("duration")

                            formats = []
                            if play_addr:
                                formats.append(StreamQuality(
                                    quality_id="hd-nowatermark",
                                    url=play_addr,
                                    protocol="https",
                                    ext="mp4",
                                    width=video_meta.get("width"),
                                    height=video_meta.get("height"),
                                    format_note="HD Clean"
                                ))
                            if download_addr and download_addr != play_addr:
                                formats.append(StreamQuality(
                                    quality_id="download",
                                    url=download_addr,
                                    protocol="https",
                                    ext="mp4",
                                    width=video_meta.get("width"),
                                    height=video_meta.get("height"),
                                    format_note="Official Download"
                                ))

                            # Also parse bitrateInfo list
                            for b_info in video_meta.get("bitrateInfo", []):
                                b_url = b_info.get("PlayAddr", {}).get("UrlList", [None])[0]
                                if b_url and not any(f.url == b_url for f in formats):
                                    formats.append(StreamQuality(
                                        quality_id=f"bitrate-{b_info.get('Bitrate', 'custom')}",
                                        url=b_url,
                                        protocol="https",
                                        ext="mp4",
                                        tbr=int(b_info.get("Bitrate", 0) / 1000) or None,
                                        format_note=b_info.get("GearName", "Variable")
                                    ))

                            if formats:
                                browser.close()
                                return TikTokMediaResult(
                                    media_id=video_id,
                                    uploader=uploader,
                                    title=desc,
                                    is_live=False,
                                    formats=formats,
                                    thumbnail=thumb,
                                    duration=duration,
                                    http_headers={"Referer": video_url}
                                )
            except Exception:
                pass

            browser.close()

            if video_srcs:
                return TikTokMediaResult(
                    media_id=video_id,
                    uploader=uploader,
                    title=f"TikTok Video {video_id}",
                    is_live=False,
                    formats=[StreamQuality(
                        quality_id="direct-mp4",
                        url=video_srcs[0],
                        protocol="https",
                        ext="mp4",
                        format_note="Intercepted MP4"
                    )],
                    http_headers={"Referer": video_url}
                )
    except Exception:
        pass

    return None
