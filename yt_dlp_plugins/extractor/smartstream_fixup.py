"""
yt-dlp postprocessor and exit-hook: makes finished AND interrupted live recordings valid.

Live HLS is saved as MPEG-TS even when the filename says .mp4 (and FLV lives
can be left in a similar state). This detects the REAL container from the
file's bytes and remuxes it to match the extension, with timestamp
regeneration and faststart metadata. If remuxing is impossible the file is
renamed to its true extension instead of staying mislabelled.

Crucially, when a user interrupts yt-dlp (e.g. Ctrl+C on a live stream),
yt-dlp normally aborts without running postprocessors, leaving an unplayable
or mislabelled .mp4.part file on disk. This module hooks progress and atexit /
interruption signals so the emergency fixup runs EVEN WHEN INTERRUPTED BY USER.

Auto-registered by the SmartStream extractors. Manual use:
  yt-dlp --use-postprocessor "SmartStreamFixup:when=after_move;force=true" URL
Args: on_fail=rename|keep (default rename), force=true (process any extractor)
"""
import atexit
import os
import shutil
import subprocess
import sys
import threading
import time

try:
    from yt_dlp.postprocessor.ffmpeg import FFmpegPostProcessor
    from yt_dlp.utils import prepend_extension
except ImportError:
    # Minimal fallback stubs if imported outside yt-dlp runtime
    class FFmpegPostProcessor:
        def __init__(self, downloader=None):
            self._downloader = downloader

        def to_screen(self, msg):
            sys.stderr.write(f'{msg}\n')

        def report_warning(self, msg):
            sys.stderr.write(f'WARNING: {msg}\n')

        def write_debug(self, msg):
            pass

    def prepend_extension(path, ext):
        root, e = os.path.splitext(path)
        return f'{root}.{ext}{e}'

HANDLED = {'TikTokSmartLive', 'TikTokSmartVideo', 'UniversalSmart'}
EXT_TO_CONTAINER = {
    'mp4': 'mp4', 'm4v': 'mp4', 'mov': 'mp4', 'm4a': 'mp4',
    'mkv': 'matroska', 'flv': 'flv', 'ts': 'mpegts'
}
CONTAINER_EXT = {'mpegts': 'ts', 'flv': 'flv', 'matroska': 'mkv', 'mp4': 'mp4'}
_MP4_BOXES = (b'ftyp', b'moov', b'mdat', b'free', b'skip', b'wide')
_FFMPEG_FMT = {
    'mp4': ['-f', 'mp4', '-movflags', '+faststart'],
    'matroska': ['-f', 'matroska'],
    'flv': ['-f', 'flv'],
    'mpegts': ['-f', 'mpegts'],
}

# Thread-safe tracker of in-flight live recordings and completed fixups
_ACTIVE_LOCK = threading.Lock()
_ACTIVE_DOWNLOADS = {}   # abs_final_path -> {'tmp': abs_tmp_path, 'info': dict, 'ydl': ydl_instance}
_FIXED_FILES = set()     # set of abs_paths already fixed
_ATEXIT_REGISTERED = False


def sniff_container(path):
    """
    Return 'mpegts' | 'flv' | 'mp4' | 'matroska' | None from magic bytes.
    Tolerates truncated headers, BDAV/Reed-Solomon strides, and missing atoms.
    """
    try:
        with open(path, 'rb') as f:
            head = f.read(188 * 16)
    except OSError:
        return None

    if not head:
        return None
    if head[:4] == b'FLV\x01' or head[:3] == b'FLV':
        return 'flv'
    if head[4:8] in _MP4_BOXES or (len(head) >= 12 and head[8:12] in _MP4_BOXES):
        return 'mp4'
    if head[:4] == b'\x1a\x45\xdf\xa3':
        return 'matroska'

    # Check for MPEG-TS sync byte 0x47 across standard strides (188, 192, 204)
    if len(head) >= 188 * 2:
        for stride in (188, 192, 204):
            for off in range(min(stride, len(head) - stride)):
                if off + stride * 3 <= len(head):
                    if all(head[off + i * stride] == 0x47 for i in range(4 if off + stride * 4 <= len(head) else 3)):
                        return 'mpegts'
        # Direct check at offset 0
        if head[0] == 0x47 and len(head) >= 376 and head[188] == 0x47:
            return 'mpegts'

    return None


def find_ffmpeg():
    """Locate the global FFmpeg binary on the system with Windows search fallbacks."""
    # 1. System PATH
    which_bin = shutil.which('ffmpeg')
    if which_bin and os.path.isfile(which_bin):
        return which_bin

    # 2. Environment variables
    for env_k in ('FFMPEG_PATH', 'SMARTSTREAM_FFMPEG'):
        v = os.environ.get(env_k)
        if v and os.path.isfile(v):
            return v

    # 3. Standard Windows installation paths
    user_home = os.path.expanduser('~')
    candidates = [
        r"C:\ffmpeg_folder\ffmpeg-essentials_build\bin\ffmpeg.exe",
        r"C:\ffmpeg_folder\bin\ffmpeg.exe",
        r"C:\Tools\ffmpeg.exe",
        r"C:\ffmpeg\bin\ffmpeg.exe",
        r"C:\Program Files\ffmpeg\bin\ffmpeg.exe",
        os.path.join(user_home, r"AppData\Local\Microsoft\WinGet\Links\ffmpeg.exe"),
        r"C:\ProgramData\chocolatey\bin\ffmpeg.exe",
    ]
    for cand in candidates:
        if os.path.isfile(cand):
            return cand

    # 4. Relative to python executable or local bin
    local_bin = os.path.join(os.path.dirname(sys.executable), 'bin', 'ffmpeg.exe')
    if os.path.isfile(local_bin):
        return local_bin

    return None


def _unique(path):
    root, ext = os.path.splitext(path)
    cand, n = path, 0
    while os.path.exists(cand):
        n += 1
        cand = f'{root}.{n}{ext}'
    return cand


def remux_file(src, dst=None, want='mp4', log_fn=None):
    """
    Losslessly remuxes src to dst (in-place if dst is None or dst == src).
    Uses FFmpeg with timestamp regeneration (-fflags +genpts+discardcorrupt),
    faststart, and error resilience.
    """
    if dst is None:
        dst = src
    dst = os.path.abspath(dst)
    src = os.path.abspath(src)

    ffmpeg_bin = find_ffmpeg()
    if not ffmpeg_bin:
        if log_fn:
            log_fn('[SmartStream] FFmpeg binary not found; skipping remux.')
        return False

    have = sniff_container(src)
    is_flv = (have == 'flv' or str(src).lower().endswith('.flv') or str(dst).lower().endswith('.flv'))
    if is_flv and want == 'flv':
        want = 'mp4'

    _EXT_MAP = {'mp4': 'mp4', 'matroska': 'mkv', 'flv': 'flv', 'mpegts': 'ts'}
    in_opts = ['-y', '-loglevel', 'warning', '-fflags', '+genpts+discardcorrupt',
               '-err_detect', 'ignore_err', '-i', src]
    base_out = ['-map', '0:v?', '-map', '0:a?', '-sn', '-dn', '-c', 'copy',
                '-avoid_negative_ts', 'make_zero', '-max_muxing_queue_size', '4096']

    attempts = []
    if is_flv:
        # 1. Lossless MP4 with AAC bitstream conversion
        attempts.append(('mp4', base_out + ['-bsf:a', 'aac_adtstoasc'] + _FFMPEG_FMT['mp4']))
        # 2. Lossless MP4 direct copy
        attempts.append(('mp4', base_out + _FFMPEG_FMT['mp4']))
        # 3. Lossless Matroska (MKV accepts legacy FLV codecs natively)
        attempts.append(('mkv', base_out + _FFMPEG_FMT['matroska']))
        # 4. Universal high-speed transcode to MP4 (100% playable anywhere)
        attempts.append(('mp4', [
            '-map', '0:v?', '-map', '0:a?',
            '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '18', '-pix_fmt', 'yuv420p',
            '-c:a', 'aac', '-b:a', '192k',
            '-avoid_negative_ts', 'make_zero', '-max_muxing_queue_size', '4096',
            '-f', 'mp4', '-movflags', '+faststart'
        ]))
    else:
        fmt_opts = _FFMPEG_FMT.get(want, ['-f', want])
        if want in ('mp4', 'flv'):
            attempts.append((want, base_out + ['-bsf:a', 'aac_adtstoasc'] + fmt_opts))
        attempts.append((want, base_out + fmt_opts))

    in_size = os.path.getsize(src) if os.path.exists(src) else 0
    if in_size == 0:
        return False

    for target_fmt, out_opts in attempts:
        dest_ext = 'mkv' if target_fmt in ('mkv', 'matroska') else ('mp4' if target_fmt == 'mp4' else _EXT_MAP.get(target_fmt, 'mp4'))
        candidate_dst = os.path.splitext(dst)[0] + '.' + dest_ext if is_flv else dst
        tmp_out = _unique(candidate_dst + '.smartstream_fix.' + dest_ext)
        cmd = [ffmpeg_bin] + in_opts + out_opts + [tmp_out]
        try:
            res = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
                                 timeout=180, text=True)
            out_size = os.path.getsize(tmp_out) if os.path.exists(tmp_out) else 0
            if res.returncode == 0 and out_size > 0 and out_size >= in_size * 0.3:
                # Success! Preserve timestamps
                try:
                    st = os.stat(src)
                    os.utime(tmp_out, ns=(st.st_atime_ns, st.st_mtime_ns))
                except OSError:
                    pass

                # Safely replace candidate_dst
                for retry in range(4):
                    try:
                        if os.path.exists(candidate_dst) and os.path.abspath(candidate_dst) != os.path.abspath(tmp_out):
                            os.remove(candidate_dst)
                        os.replace(tmp_out, candidate_dst)
                        break
                    except PermissionError:
                        time.sleep(0.15)
                else:
                    os.replace(tmp_out, candidate_dst)

                # Clean up src if different from candidate_dst (e.g. .part or .flv file)
                if os.path.abspath(src) != os.path.abspath(candidate_dst):
                    try:
                        if os.path.exists(src):
                            os.remove(src)
                    except OSError:
                        pass
                return True
        except Exception as e:
            if log_fn:
                log_fn(f'[SmartStream] Remux attempt error: {e}')
        finally:
            if os.path.exists(tmp_out):
                try:
                    os.remove(tmp_out)
                except OSError:
                    pass
    return False


def emergency_fixup(reason='Interrupted / Exit'):
    """
    Emergency container fixup routine called on atexit, KeyboardInterrupt, or ydl error.
    Inspects all tracked active recordings and repairs any MPEG-TS/.part mismatches.
    """
    with _ACTIVE_LOCK:
        items = list(_ACTIVE_DOWNLOADS.items())

    if not items:
        return

    for final_path, meta in items:
        with _ACTIVE_LOCK:
            if final_path in _FIXED_FILES:
                continue

        tmp_path = meta.get('tmp')
        cand_path = None

        # Look for the best existing candidate file
        for p in [tmp_path, final_path, f'{final_path}.part']:
            if p and os.path.isfile(p) and os.path.getsize(p) > 0:
                cand_path = os.path.abspath(p)
                break

        if not cand_path:
            continue

        # Determine desired container from target filename extension
        ext = os.path.splitext(final_path)[1].lstrip('.').lower()
        want = EXT_TO_CONTAINER.get(ext, 'mp4')
        have = sniff_container(cand_path)

        if not have:
            continue

        needs_remux = (have != want) or cand_path.endswith('.part')

        if needs_remux:
            sys.stderr.write(
                f'\n[SmartStream] Interrupted live recording detected for: {os.path.basename(final_path)}\n'
                f'[SmartStream] Container is really {have} (target .{ext}). Remuxing to clean MP4 with faststart...\n'
            )
            sys.stderr.flush()

            ok = remux_file(cand_path, dst=final_path, want=want)
            if ok:
                with _ACTIVE_LOCK:
                    _FIXED_FILES.add(final_path)
                sys.stderr.write(
                    f'[SmartStream] Successfully remuxed {have} -> {want}: {os.path.basename(final_path)} (playable, clean timestamps)\n'
                )
                sys.stderr.flush()
                continue

            # Fallback if remux failed: rename to honest extension so file is playable
            new_ext = CONTAINER_EXT.get(have, 'ts')
            honest_path = _unique(os.path.splitext(final_path)[0] + '.' + new_ext)
            try:
                for retry in range(4):
                    try:
                        os.replace(cand_path, honest_path)
                        break
                    except PermissionError:
                        time.sleep(0.15)
                with _ACTIVE_LOCK:
                    _FIXED_FILES.add(final_path)
                sys.stderr.write(
                    f'[SmartStream] Remux failed; safely renamed to "{os.path.basename(honest_path)}" '
                    f'(valid {have}, playable in VLC/mpv)\n'
                )
                sys.stderr.flush()
            except OSError as err:
                sys.stderr.write(f'[SmartStream] Warning: Could not rename "{cand_path}": {err}\n')
                sys.stderr.flush()


def _atexit_handler():
    emergency_fixup(reason='Process Terminated')


def register_active_download_hooks(ydl):
    """
    Hooks into YoutubeDL instance to track output filenames in real time
    and register emergency exit / interruption fixup handlers.
    """
    global _ATEXIT_REGISTERED
    if ydl is None:
        return

    if not _ATEXIT_REGISTERED:
        atexit.register(_atexit_handler)
        _ATEXIT_REGISTERED = True

    # 1. Progress Hook: tracks active downloading filenames
    def _progress_hook(d):
        fn = d.get('filename')
        tmp = d.get('tmpfilename')
        if fn:
            abs_fn = os.path.abspath(fn)
            abs_tmp = os.path.abspath(tmp) if tmp else f'{abs_fn}.part'
            with _ACTIVE_LOCK:
                _ACTIVE_DOWNLOADS[abs_fn] = {
                    'tmp': abs_tmp,
                    'info': d.get('info_dict'),
                    'ydl': ydl
                }

    ydl.add_progress_hook(_progress_hook)

    # 2. Hook prepare_filename to capture the destination immediately at extractor resolution
    orig_prepare = getattr(ydl, 'prepare_filename', None)
    if orig_prepare and not getattr(orig_prepare, '_smartstream_wrapped', False):
        def _wrapped_prepare(info_dict, *args, **kwargs):
            fn = orig_prepare(info_dict, *args, **kwargs)
            if fn:
                abs_fn = os.path.abspath(fn)
                with _ACTIVE_LOCK:
                    _ACTIVE_DOWNLOADS.setdefault(abs_fn, {
                        'tmp': f'{abs_fn}.part',
                        'info': info_dict,
                        'ydl': ydl
                    })
            return fn
        _wrapped_prepare._smartstream_wrapped = True
        ydl.prepare_filename = _wrapped_prepare

    # 3. Hook report_error to run emergency fixup on interruption messages
    orig_report_error = getattr(ydl, 'report_error', None)
    if orig_report_error and not getattr(orig_report_error, '_smartstream_wrapped', False):
        def _wrapped_report_error(message, *args, **kwargs):
            if 'interrupted' in str(message).lower():
                try:
                    emergency_fixup(reason='User Interrupted')
                except Exception:
                    pass
            return orig_report_error(message, *args, **kwargs)
        _wrapped_report_error._smartstream_wrapped = True
        ydl.report_error = _wrapped_report_error


class SmartStreamFixupPP(FFmpegPostProcessor):
    def __init__(self, downloader=None, on_fail='rename', force=False):
        super().__init__(downloader)
        self.on_fail = str(on_fail).lower()
        self.force = str(force).strip().lower() in ('1', 'true', 'yes', 'on')

    def run(self, info):
        path = info.get('filepath')
        if not path or not os.path.isfile(path):
            return [], info
        if not self.force and info.get('extractor_key') not in HANDLED:
            return [], info

        abs_path = os.path.abspath(path)
        with _ACTIVE_LOCK:
            if abs_path in _FIXED_FILES:
                return [], info

        ext = os.path.splitext(path)[1].lstrip('.').lower()
        want = EXT_TO_CONTAINER.get(ext)
        have = sniff_container(path)
        if not want or not have or want == have:
            with _ACTIVE_LOCK:
                _FIXED_FILES.add(abs_path)
            return [], info

        self.to_screen(f'File is really {have} but named .{ext}; fixing "{path}"')
        if remux_file(path, dst=path, want=want, log_fn=self.write_debug):
            with _ACTIVE_LOCK:
                _FIXED_FILES.add(abs_path)
            self.to_screen(f'Remuxed {have} -> {want} (clean timestamps and faststart)')
            return [], info

        # Remux failed: rename to honest extension
        new_ext = CONTAINER_EXT.get(have)
        if self.on_fail == 'rename' and new_ext:
            new_path = _unique(os.path.splitext(path)[0] + '.' + new_ext)
            try:
                for retry in range(4):
                    try:
                        os.replace(path, new_path)
                        break
                    except PermissionError:
                        time.sleep(0.15)
                info['filepath'], info['ext'] = new_path, new_ext
                with _ACTIVE_LOCK:
                    _FIXED_FILES.add(abs_path)
                self.report_warning(f'Remux failed; renamed to "{new_path}" (valid {have}, playable in VLC/mpv)')
                return [], info
            except OSError as e:
                self.report_warning(f'Could not rename "{path}": {e}')

        self.report_warning(
            f'Left "{path}" as is; it contains {have} data. Fix manually: '
            'ffmpeg -fflags +genpts+discardcorrupt -i IN -map 0:v? -map 0:a? '
            '-c copy -bsf:a aac_adtstoasc -movflags +faststart OUT.mp4'
        )
        return [], info