"""
Universal Stream Sniffer
Provides fast static and headless dynamic interception of HLS (.m3u8), DASH (.mpd), and FLV (.flv) streams.
"""

from dataclasses import dataclass, field
from typing import Optional, Dict, List
import re
import urllib.request
import urllib.parse
import json
import time

M3U8_REGEX = re.compile(
    r'(https?://[^\s"\'<>]+\.m3u8[^\s"\'<>]*)',
    re.IGNORECASE
)
FLV_REGEX = re.compile(
    r'(https?://[^\s"\'<>]+\.flv[^\s"\'<>]*)',
    re.IGNORECASE
)
MPD_REGEX = re.compile(
    r'(https?://[^\s"\'<>]+\.mpd[^\s"\'<>]*)',
    re.IGNORECASE
)

DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
)

# Ad or analytics URL patterns to ignore
IGNORE_KEYWORDS = [
    "ad-delivery", "googleads", "analytics", "telemetry",
    "doubleclick", "scorecardresearch", "statcounter"
]


@dataclass
class SniffedStream:
    url: str
    stream_type: str  # 'hls', 'flv', 'dash'
    headers: Dict[str, str] = field(default_factory=dict)
    cookies: Dict[str, str] = field(default_factory=dict)
    page_title: Optional[str] = None
    all_streams: List[Dict[str, str]] = field(default_factory=list)


def is_ad_or_tracker(url: str) -> bool:
    url_lower = url.lower()
    return any(keyword in url_lower for keyword in IGNORE_KEYWORDS)


def sniff_static(url: str, custom_headers: Optional[Dict[str, str]] = None) -> Optional[SniffedStream]:
    """
    Tier 1: Fast static regex scan of page content for .m3u8 / .flv / .mpd.
    Returns SniffedStream if found, otherwise None.
    """
    headers = {
        "User-Agent": DEFAULT_USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
    }
    if custom_headers:
        headers.update(custom_headers)

    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=8) as resp:
            html = resp.read().decode("utf-8", errors="ignore")

            # Look for master.m3u8 or any .m3u8
            m3u8_matches = [m.replace("\\u002F", "/").replace("\\/", "/") for m in M3U8_REGEX.findall(html)]
            m3u8_clean = [u for u in m3u8_matches if not is_ad_or_tracker(u)]
            if m3u8_clean:
                # Prefer master / live playlists
                chosen = next((u for u in m3u8_clean if "master" in u.lower() or "live" in u.lower()), m3u8_clean[0])
                return SniffedStream(
                    url=chosen,
                    stream_type="hls",
                    headers={"User-Agent": headers["User-Agent"], "Referer": url},
                    all_streams=[{"url": u, "type": "hls"} for u in m3u8_clean]
                )

            # Look for .mpd
            mpd_matches = [m.replace("\\u002F", "/").replace("\\/", "/") for m in MPD_REGEX.findall(html)]
            mpd_clean = [u for u in mpd_matches if not is_ad_or_tracker(u)]
            if mpd_clean:
                return SniffedStream(
                    url=mpd_clean[0],
                    stream_type="dash",
                    headers={"User-Agent": headers["User-Agent"], "Referer": url},
                    all_streams=[{"url": u, "type": "dash"} for u in mpd_clean]
                )
    except Exception:
        pass
    return None


def sniff_dynamic(
    target_url: str,
    timeout: int = 15,
    block_resources: bool = True,
    headless: bool = True,
    user_agent: str = DEFAULT_USER_AGENT
) -> Optional[SniffedStream]:
    """
    Tier 2: Playwright CDP network sniffer.
    Intercepts outgoing HTTP/HTTPS traffic to discover stream manifests and segment requests.
    """
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        raise RuntimeError("Playwright is required for dynamic sniffing. Run: pip install playwright && playwright install chromium")

    discovered: List[Dict] = []
    page_title = None

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=headless,
            args=[
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-blink-features=AutomationControlled",
                "--mute-audio"
            ]
        )
        context = browser.new_context(
            user_agent=user_agent,
            viewport={"width": 1280, "height": 720},
            ignore_https_errors=True
        )
        page = context.new_page()

        # Stealth evasion
        page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
        """)

        # Speed up page load by dropping non-essential media & stylesheets
        if block_resources:
            def route_filter(route):
                req = route.request
                res_type = req.resource_type
                req_url = req.url.lower()

                # Don't block potential manifest URLs
                if ".m3u8" in req_url or ".mpd" in req_url or ".flv" in req_url:
                    route.continue_()
                    return

                if res_type in ["image", "font", "media"]:
                    route.abort()
                else:
                    route.continue_()

            page.route("**/*", route_filter)

        def handle_request(req):
            r_url = req.url
            if is_ad_or_tracker(r_url):
                return

            lower = r_url.lower()
            stream_type = None
            if ".m3u8" in lower:
                stream_type = "hls"
            elif ".mpd" in lower:
                stream_type = "dash"
            elif ".flv" in lower:
                stream_type = "flv"

            if stream_type:
                discovered.append({
                    "url": r_url,
                    "type": stream_type,
                    "headers": dict(req.headers)
                })

        def handle_response(resp):
            c_type = resp.headers.get("content-type", "").lower()
            if "mpegurl" in c_type or "x-mpegurl" in c_type:
                if not is_ad_or_tracker(resp.url):
                    discovered.append({
                        "url": resp.url,
                        "type": "hls",
                        "headers": dict(resp.request.headers)
                    })

        page.on("request", handle_request)
        page.on("response", handle_response)

        try:
            page.goto(target_url, timeout=timeout * 1000, wait_until="domcontentloaded")
            page_title = page.title()

            # Wait up to remaining timeout or until at least one stream is caught
            start_time = time.time()
            while time.time() - start_time < timeout:
                if discovered:
                    # Give it 1 extra second for master/higher bitrate playlist to appear
                    time.sleep(1.0)
                    break
                page.wait_for_timeout(500)

            # Try clicking any obvious play button if not playing automatically
            if not discovered:
                try:
                    for selector in ['button[aria-label*="Play"]', 'button.play-button', '.vjs-big-play-button', 'video']:
                        elem = page.query_selector(selector)
                        if elem:
                            elem.click(timeout=1000)
                            page.wait_for_timeout(2000)
                            if discovered:
                                break
                except Exception:
                    pass

        except Exception as e:
            # Navigation might timeout or throw, but we still inspect discovered streams
            pass

        # Capture cookies
        cookies_dict = {c["name"]: c["value"] for c in context.cookies()}
        browser.close()

    if not discovered:
        return None

    # Sort discovered: prefer master playlists or HLS
    def score_stream(s):
        u = s["url"].lower()
        score = 0
        if "master" in u:
            score += 10
        if "live" in u:
            score += 5
        if s["type"] == "hls":
            score += 2
        return score

    discovered.sort(key=score_stream, reverse=True)
    best = discovered[0]

    # Clean headers
    stream_headers = {
        "User-Agent": best["headers"].get("user-agent", user_agent),
        "Referer": target_url,
        "Origin": f"{urllib.parse.urlsplit(target_url).scheme}://{urllib.parse.urlsplit(target_url).netloc}"
    }

    return SniffedStream(
        url=best["url"],
        stream_type=best["type"],
        headers=stream_headers,
        cookies=cookies_dict,
        page_title=page_title,
        all_streams=discovered
    )


def smart_sniff(
    url: str,
    timeout: int = 15,
    force_dynamic: bool = False
) -> Optional[SniffedStream]:
    """
    High-level entry point:
    Attempts static scan first for speed; falls back to dynamic sniffer if needed.
    """
    if not force_dynamic:
        static_result = sniff_static(url)
        if static_result:
            return static_result

    return sniff_dynamic(url, timeout=timeout)
