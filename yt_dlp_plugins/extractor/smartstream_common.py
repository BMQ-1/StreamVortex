"""
Shared helpers for the SmartStream extractors: bridge, format building,
HLS inspection and the fix-up hook. Contains no *IE classes.
"""
import hashlib
import json
import os
import shutil
import subprocess
import sys
import urllib.parse
from datetime import datetime, timezone

IE_KEY = 'smartstream'          # --extractor-args "smartstream:key=value;..."
EXIT_NOT_FOUND = 3              # bridge CLI should exit 3 for "not live / no stream"
_FALSY = {'0', 'off', 'no', 'false', 'n'}
_HLS = {'m3u8', 'm3u8_native', 'hls'}
_DASH = {'dash', 'mpd', 'http_dash_segments'}
_DRM_MARKERS = ('urn:uuid:edef8ba9', 'com.apple.streamingkeydelivery', 'com.microsoft.playready')


class BridgeError(Exception):
    def __init__(self, msg, code=None):
        super().__init__(msg)
        self.code = code


# ---------------------------------------------------------------- small utils
def arg(ie, name, default):
    vals = ie._configuration_arg(name, [default], ie_key=IE_KEY)
    return vals[0] if vals else default


def int_arg(ie, name, default):
    try:
        return max(1, int(float(arg(ie, name, str(default)))))
    except (TypeError, ValueError):
        return default


def flag(ie, name, default=True):
    return arg(ie, name, 'on' if default else 'off').strip().lower() not in _FALSY


def pick(obj, *names, default=None):
    """Read the first non-empty value from a dict key or object attribute."""
    for n in names:
        v = obj.get(n) if isinstance(obj, dict) else getattr(obj, n, None)
        if v not in (None, ''):
            return v
    return default


def stamp():
    return datetime.now(timezone.utc).strftime('%Y-%m-%d %H-%M')


def merge_headers(*dicts):
    """Merge header dicts case-insensitively; later dicts win."""
    out = {}
    for d in dicts:
        for k, v in (d or {}).items():
            if v is None or str(k).startswith(':'):
                continue
            for existing in [x for x in out if x.lower() == str(k).lower()]:
                del out[existing]
            out[k] = v
    return out


def stable_id(url):
    host = urllib.parse.urlparse(url).hostname or 'stream'
    host = ''.join(c if c.isalnum() or c in '.-' else '_' for c in host)
    return f'{host}-{hashlib.md5(url.encode()).hexdigest()[:10]}'


def _is_valid_python(path):
    if not path or not os.path.isfile(path):
        return False
    # Reject WindowsApps redirector shims that trigger "Python was not found" error
    norm = os.path.normcase(os.path.abspath(path))
    if 'windowsapps' in norm:
        return False
    try:
        proc = subprocess.run(
            [path, '-c', 'import sys; sys.exit(0)'],
            capture_output=True,
            timeout=2
        )
        return proc.returncode == 0
    except Exception:
        return False


def _find_python():
    explicit = os.environ.get('SMARTSTREAM_PYTHON')
    if explicit and _is_valid_python(explicit):
        return explicit

    if not getattr(sys, 'frozen', False):
        if _is_valid_python(sys.executable):
            return sys.executable

    cwd = os.path.normcase(os.path.abspath(os.getcwd()))

    # Check on PATH: 'python', 'py', 'python3' (order matters: 'python'/'py' first, never WindowsApps)
    for name in ('python', 'py', 'python3'):
        p = shutil.which(name)
        if p and os.path.normcase(os.path.abspath(os.path.dirname(p))) != cwd:
            if _is_valid_python(p):
                return p

    # Standard Windows install locations fallback
    if os.name == 'nt':
        local_app = os.environ.get('LOCALAPPDATA', '')
        prog_files = os.environ.get('ProgramFiles', 'C:\\Program Files')
        prog_files_x86 = os.environ.get('ProgramFiles(x86)', 'C:\\Program Files (x86)')
        cand_dirs = [
            os.path.join(local_app, 'Programs', 'Python'),
            'C:\\',
            prog_files,
            prog_files_x86,
        ]
        for base in cand_dirs:
            if os.path.isdir(base):
                try:
                    for entry in os.listdir(base):
                        if entry.lower().startswith('python3'):
                            exe = os.path.join(base, entry, 'python.exe')
                            if _is_valid_python(exe):
                                return exe
                except Exception:
                    pass

    return None


def _context(ie, url):
    """Proxy / UA / cookies handed to the bridge via env (CLI may ignore them)."""
    ctx = {}
    try:
        proxy = ie.get_param('proxy')
        if proxy:
            ctx['proxy'] = proxy
        ua = (ie.get_param('http_headers') or {}).get('User-Agent')
        if ua:
            ctx['user_agent'] = ua
        ctx['cookies'] = {k: m.value for k, m in ie._get_cookies(url).items()}
    except Exception:
        pass
    return ctx


def run_bridge(ie, url, timeout):
    py = _find_python()
    if not py:
        raise BridgeError('No Python interpreter found for the bridge; set SMARTSTREAM_PYTHON')
    env = {
        **os.environ,
        'PYTHONUTF8': '1',
        'PYTHONIOENCODING': 'utf-8',
        'PYTHONSAFEPATH': '1',   # don't put the current dir on sys.path (3.11+)
        'SMARTSTREAM_CONTEXT': json.dumps(_context(ie, url)),
    }
    cmd = [py, '-m', 'ytdlp_smartstream.cli', '--json', '--', url]
    extra = {'creationflags': 0x08000000} if os.name == 'nt' else {}   # CREATE_NO_WINDOW
    ie.write_debug(f'Bridge: {py} -m ytdlp_smartstream.cli (timeout {timeout}s)')
    try:
        proc = subprocess.run(
            cmd, capture_output=True, text=True, encoding='utf-8', errors='replace',
            timeout=timeout, env=env, stdin=subprocess.DEVNULL, **extra)
    except subprocess.TimeoutExpired:
        raise BridgeError(f'bridge timed out after {timeout}s (raise it with '
                          f'--extractor-args "{IE_KEY}:timeout=60")')
    except OSError as e:
        raise BridgeError(f'cannot start bridge ({py}): {e}')

    err = (proc.stderr or '').strip()
    if err:
        ie.write_debug(f'Bridge stderr: {err[-1000:]}')
    lines = [ln for ln in (proc.stdout or '').splitlines() if ln.strip()]
    if proc.returncode != 0 or not lines:
        raise BridgeError(err[-300:] or f'bridge exited with code {proc.returncode}',
                          code=proc.returncode)
    try:
        return json.loads(lines[-1])      # logs may precede the JSON line
    except ValueError:
        try:
            return json.loads(proc.stdout)
        except ValueError:
            raise BridgeError('bridge returned invalid JSON')


# -------------------------------------------------------------------- formats
def normalize_format(f):
    """Accept resolver objects or bridge dicts; return a plain dict."""
    return {
        'id': pick(f, 'quality_id', 'id', 'format_id'),
        'url': pick(f, 'url'),
        'protocol': pick(f, 'protocol'),
        'ext': pick(f, 'ext'),
        'width': pick(f, 'width'),
        'height': pick(f, 'height'),
        'tbr': pick(f, 'tbr'),
        'vcodec': pick(f, 'vcodec'),
        'acodec': pick(f, 'acodec'),
        'fps': pick(f, 'fps'),
        'note': pick(f, 'format_note'),
    }


def classify(f, default='http'):
    url = str(f.get('url') or '')
    url_lower = url.lower()
    path = urllib.parse.urlparse(url).path.lower()
    proto = str(f.get('protocol') or '').lower()
    ext = str(f.get('ext') or '').lower()
    if proto in _HLS or ext in ('m3u8', 'm3u') or path.endswith(('.m3u8', '.m3u')) or '.m3u8' in url_lower or 'pull-hls' in url_lower:
        return 'hls'
    if proto in _DASH or ext in ('mpd', 'dash') or path.endswith('.mpd') or '.mpd' in url_lower:
        return 'dash'
    if ext == 'flv' or path.endswith('.flv') or '.flv' in url_lower:
        return 'flv'
    if ext or path.rsplit('.', 1)[-1] in ('mp4', 'webm', 'mkv', 'ts', 'mov', 'm4a', 'mp3', 'aac'):
        return 'http'
    return default


def build_formats(ie, f, video_id, headers, *, live, container='mp4',
                  default_kind='http', prefer='hls'):
    """Turn one resolved stream into yt-dlp formats (headers used for manifests too)."""
    kind = classify(f, default_kind)
    qid = str(f.get('id') or kind)
    common = {k: f[k] for k in ('width', 'height', 'tbr', 'vcodec', 'acodec', 'fps')
              if f.get(k) is not None}
    if f.get('note'):
        common['format_note'] = f['note']
    pref = 1 if kind == prefer else 0
    out = []

    if kind == 'hls':
        ext = 'ts' if container == 'ts' else 'mp4'
        out = ie._extract_m3u8_formats(
            f['url'], video_id, ext=ext, entry_protocol='m3u8_native', m3u8_id=qid,
            live=live, headers=headers, fatal=False) or []
        if not out:   # manifest unreachable now; let the downloader try the raw URL
            out = [{**common, 'format_id': qid, 'url': f['url'], 'ext': ext,
                    'protocol': 'm3u8_native'}]
        for o in out:
            for k, v in common.items():
                o.setdefault(k, v)
            if headers:
                o.setdefault('http_headers', headers)
            if live:
                o.setdefault('is_live', True)
    elif kind == 'dash':
        out = ie._extract_mpd_formats(f['url'], video_id, mpd_id=qid, headers=headers,
                                      fatal=False) or []
        for o in out:
            if headers:
                o.setdefault('http_headers', headers)
    else:
        ext = 'flv' if kind == 'flv' else (f.get('ext') or 'mp4')
        proto = 'https' if f['url'].lower().startswith('https') else 'http'
        out = [{**common, 'format_id': qid, 'url': f['url'], 'ext': ext, 'protocol': proto}]
        if headers:
            out[0].setdefault('http_headers', headers)

    for o in out:
        o.setdefault('source_preference', pref)
    return out


def dedupe_format_ids(formats):
    seen = {}
    for f in formats:
        fid = str(f.get('format_id') or 'fmt')
        if fid in seen:
            seen[fid] += 1
            f['format_id'] = f'{fid}-{seen[fid]}'
        else:
            seen[fid] = 0
    return formats


def inspect_hls(ie, url, video_id, headers):
    """Return (is_live | None, has_drm) by reading the (first variant) playlist."""
    text = ie._download_webpage(url, video_id, note='Checking playlist', fatal=False,
                                headers=headers)
    if not text:
        return None, False
    if '#EXT-X-STREAM-INF' in text:      # master playlist -> follow first variant
        for line in text.splitlines():
            line = line.strip()
            if line and not line.startswith('#'):
                sub = ie._download_webpage(urllib.parse.urljoin(url, line), video_id,
                                           note='Checking variant playlist', fatal=False,
                                           headers=headers)
                if sub:
                    text = sub
                break
    drm = any(m in text for m in _DRM_MARKERS)
    if '#EXT-X-PLAYLIST-TYPE:VOD' in text:
        return False, drm
    return ('#EXT-X-ENDLIST' not in text), drm


# ------------------------------------------------------------ fix-up register
def register_fixup(ie):
    """Attach SmartStreamFixupPP (after_move) and emergency fixup hooks once per YoutubeDL instance."""
    ydl = getattr(ie, '_downloader', None)
    if ydl is None or getattr(ydl, '_smartstream_fixup_registered', False):
        return
    if not flag(ie, 'fixup', True):
        return
    try:
        try:
            from yt_dlp_plugins.postprocessor.smartstream_fixup import (
                SmartStreamFixupPP, register_active_download_hooks
            )
        except ImportError:
            from yt_dlp_plugins.extractor.smartstream_fixup import (
                SmartStreamFixupPP, register_active_download_hooks
            )
        ydl.add_post_processor(SmartStreamFixupPP(ydl), when='after_move')
        register_active_download_hooks(ydl)
        ydl._smartstream_fixup_registered = True
    except Exception as e:
        ie.write_debug(f'SmartStream fix-up postprocessor unavailable: {e}')