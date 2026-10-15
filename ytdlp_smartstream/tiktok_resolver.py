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

from .sniffer import DEFAULT_USER_AGENT

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


def _extract_from_universal_data(data: Dict[str, Any], uploader: str) -> Optional[TikTokMediaResult]:
    """
    Extracts live stream formats from parsed __UNIVERSAL_DATA_FOR_REHYDRATION__.
    """
    scope = data.get("__DEFAULT_SCOPE__", {})
    user_detail = scope.get("webapp.user-detail", {})
    live_info = user_detail.get("liveInfo") or {}
    stream_data_obj = live_info.get("streamData", {})
    pull_data = stream_data_obj.get("pull_data", {})
    stream_data_str = pull_data.get("stream_data")

    room_id = str(live_info.get("roomId", ""))
    title = live_info.get("title", f"TikTok Live by {uploader}")

    formats: List[StreamQuality] = []
    if stream_data_str:
        formats = _parse_stream_data_json(stream_data_str)

    if not formats and "stream_url" in live_info:
        s_url = live_info["stream_url"]
        hls_main = s_url.get("hls_pull_url")
        if hls_main:
            formats.append(StreamQuality(
                quality_id="hls-origin",
                url=hls_main,
                protocol="m3u8_native",
                ext="mp4",
                format_note="HLS Master"
            ))

    if formats:
        return TikTokMediaResult(
            media_id=room_id or uploader,
            uploader=uploader,
            title=title,
            is_live=True,
            formats=formats,
            http_headers={"Referer": f"https://www.tiktok.com/@{uploader}/live"}
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
            room_info = await client.web.fetch_room_info(unique_id=uploader)
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
                        http_headers={"Referer": f"https://www.tiktok.com/@{uploader}/live"}
                    )
        except Exception:
            pass
    except ImportError:
        pass

    # Direct Webcast API fallback
    try:
        api_url = f"https://www.tiktok.com/api-live/user/room/?uniqueId={uploader}&sourceType=54"
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
                        http_headers={"Referer": f"https://www.tiktok.com/@{uploader}/live"}
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
            args=["--no-sandbox", "--disable-blink-features=AutomationControlled", "--mute-audio"]
        )
        context = browser.new_context(
            user_agent=DEFAULT_USER_AGENT,
            viewport={"width": 1280, "height": 720}
        )
        page = context.new_page()

        def on_request(req):
            r_url = req.url
            if ".m3u8" in r_url and "pull-" in r_url:
                intercepted_streams.append(StreamQuality(
                    quality_id="hls-intercepted",
                    url=r_url,
                    protocol="m3u8_native",
                    ext="mp4",
                    format_note="Intercepted HLS"
                ))
            elif ".flv" in r_url and "pull-" in r_url:
                intercepted_streams.append(StreamQuality(
                    quality_id="flv-intercepted",
                    url=r_url,
                    protocol="https",
                    ext="flv",
                    format_note="Intercepted FLV"
                ))

        page.on("request", on_request)
        page.route("**/*.{png,jpg,jpeg,gif,webp,svg,woff,woff2,ttf,css}", lambda r: r.abort())

        try:
            page.goto(target_url, timeout=timeout * 1000, wait_until="domcontentloaded")
            page.wait_for_timeout(3000)

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

        browser.close()

    if intercepted_streams:
        return TikTokMediaResult(
            media_id=room_id,
            uploader=uploader,
            title=title,
            is_live=True,
            formats=intercepted_streams,
            http_headers={"Referer": target_url}
        )

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
