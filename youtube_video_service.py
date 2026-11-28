import ctypes
import ctypes.wintypes
import io
import json
import os
import re
import struct
import subprocess
import sys
import threading
import time
import urllib.parse
import urllib.request
from typing import Optional, Tuple, Dict, Any, List

from PIL import Image, ImageDraw

try:
    import mss
    HAS_MSS = True
except Exception:
    HAS_MSS = False

try:
    import win32gui
    import win32ui
    import win32con
    HAS_WIN32 = True
except Exception:
    HAS_WIN32 = False

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32
PW_RENDERFULLCONTENT = 2
WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.wintypes.HWND, ctypes.wintypes.LPARAM)

BROWSER_PROCS = (
    "brave.exe", "chrome.exe", "msedge.exe", "firefox.exe",
    "opera.exe", "vivaldi.exe", "arc.exe"
)


def _attach_default_desktop():
    """Ensures the calling thread is attached to the interactive 'Default' desktop."""
    try:
        h = user32.OpenDesktopW("Default", 0, False, 0x01FF)
        if h:
            user32.SetThreadDesktop(h)
            user32.CloseDesktop(h)
    except Exception:
        pass


def _get_proc_name(hwnd: int) -> str:
    try:
        pid = ctypes.wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        if pid.value == 0:
            return ""
        h_proc = kernel32.OpenProcess(0x1000, False, pid.value)
        if not h_proc:
            return ""
        buf = ctypes.create_unicode_buffer(1024)
        size = ctypes.wintypes.DWORD(1024)
        kernel32.QueryFullProcessImageNameW(h_proc, 0, buf, ctypes.byref(size))
        kernel32.CloseHandle(h_proc)
        return buf.value.split("\\")[-1].lower()
    except Exception:
        return ""


class YouTubeVideoService:
    """
    Lightweight, zero-leak live YouTube browser window capture service.
    Shared by Origin Island (desktop PiP) and Phone Drop Service (MJPEG stream).
    Uses PrintWindow (PW_RENDERFULLCONTENT) with automatic mss screen-rect fallback
    for hardware-accelerated Chromium/Brave/Edge video layers.
    """

    def __init__(self):
        self._lock = threading.Lock()
        self._last_hwnd: Optional[int] = None
        self._last_title: str = ""
        self._is_minimized: bool = False
        self._crop_mode: str = "zoom"  # "zoom" (16:9 player), "clean" (no top bar), "full" (whole window)

        self._latest_jpeg: Optional[bytes] = None
        self._latest_rgb: Optional[bytes] = None
        self._latest_size: Tuple[int, int] = (0, 0)
        self._frame_version: int = 0
        self._last_capture_ts: float = 0.0
        self._last_viewer_ts: float = 0.0

        self._worker_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._video_id_cache: Dict[str, str] = {}
        self._video_id_pending: set = set()

        self._ctx_title: str = ""
        self._ctx_artist: str = ""
        self._ctx_pos: float = 0.0
        self._helper_proc: Optional[subprocess.Popen] = None
        self._helper_vid: str = ""
        self._helper_reader: Optional[threading.Thread] = None

    def set_media_context(self, title: str, artist: str = "", pos_sec: float = 0.0):
        self._ctx_title = (title or "").strip()
        self._ctx_artist = (artist or "").strip()
        self._ctx_pos = max(0.0, float(pos_sec or 0.0))

    def resolve_video_id(self, title: str, artist: str = "", async_only: bool = False) -> str:
        """Resolves & caches a YouTube 11-char videoId for (title, artist) without API keys."""
        t = (title or "").strip()
        a = (artist or "").strip()
        if not t or t.lower() in ("no music playing", "unknown track"):
            return ""
        cache_key = f"{t}||{a}".lower()
        with self._lock:
            if cache_key in self._video_id_cache:
                return self._video_id_cache[cache_key]
            if async_only and cache_key in self._video_id_pending:
                return ""
            if async_only:
                self._video_id_pending.add(cache_key)

        def _fetch():
            vid = ""
            try:
                q_parts = [t]
                if a and a.lower() not in ("youtube", "brave", "chrome", "edge", "unknown", "media"):
                    q_parts.append(a)
                q = urllib.parse.quote(" ".join(q_parts))
                req = urllib.request.Request(
                    f"https://www.youtube.com/results?search_query={q}",
                    headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"},
                )
                html = urllib.request.urlopen(req, timeout=5).read().decode("utf-8", errors="ignore")
                m = re.search(r'"videoId":"([a-zA-Z0-9_-]{11})"', html)
                if m:
                    vid = m.group(1)
            except Exception:
                pass
            with self._lock:
                self._video_id_cache[cache_key] = vid
                self._video_id_pending.discard(cache_key)
            return vid

        if async_only:
            threading.Thread(target=_fetch, daemon=True).start()
            return ""
        return _fetch()

    @property
    def crop_mode(self) -> str:
        return self._crop_mode

    def set_crop_mode(self, mode: str):
        if mode in ("zoom", "clean", "full"):
            self._crop_mode = mode

    def cycle_crop_mode(self) -> str:
        order = ("zoom", "clean", "full")
        idx = order.index(self._crop_mode) if self._crop_mode in order else 0
        self._crop_mode = order[(idx + 1) % len(order)]
        return self._crop_mode

    def find_youtube_window(self) -> Tuple[Optional[int], str, bool]:
        """Returns (hwnd, window_title, is_minimized) for the active YouTube/browser window."""
        _attach_default_desktop()
        matches: List[Tuple[int, int, str, bool]] = []

        def _enum_cb(hwnd, _):
            try:
                if not user32.IsWindowVisible(hwnd):
                    return True
                length = user32.GetWindowTextLengthW(hwnd)
                if length <= 0:
                    return True
                buf = ctypes.create_unicode_buffer(length + 1)
                user32.GetWindowTextW(hwnd, buf, length + 1)
                title = buf.value.strip()
                if not title:
                    return True
                tl = title.lower()
                is_min = bool(user32.IsIconic(hwnd))
                proc = _get_proc_name(hwnd)

                if "youtube" in tl or "picture-in-picture" in tl or "picture in picture" in tl:
                    matches.append((0 if not is_min else 1, hwnd, title, is_min))
            except Exception:
                pass
            return True

        try:
            user32.EnumWindows(WNDENUMPROC(_enum_cb), 0)
        except Exception:
            pass

        if matches:
            matches.sort(key=lambda x: x[0])
            _, hwnd, title, is_min = matches[0]
            self._last_hwnd = hwnd
            self._last_title = title
            self._is_minimized = is_min
            return hwnd, title, is_min

        self._is_minimized = False
        return None, "", False

    def is_youtube_available(self) -> Dict[str, Any]:
        hwnd, title, is_min = self.find_youtube_window()
        return {
            "available": hwnd is not None,
            "minimized": is_min,
            "title": title,
            "crop_mode": self._crop_mode,
        }

    def restore_youtube_window(self) -> bool:
        hwnd, _, is_min = self.find_youtube_window()
        if not hwnd:
            return False
        try:
            if is_min:
                user32.ShowWindow(hwnd, 9)  # SW_RESTORE
            user32.SetForegroundWindow(hwnd)
            return True
        except Exception:
            return False

    def _is_mostly_black(self, img: Image.Image) -> bool:
        try:
            tiny = img.resize((16, 16))
            ext = tiny.getextrema()
            return all(hi < 6 for _, hi in ext)
        except Exception:
            return False

    def _capture_mss_rect(self, left: int, top: int, w: int, h: int) -> Optional[Image.Image]:
        if not HAS_MSS or w < 120 or h < 120:
            return None
        try:
            with mss.mss() as sct:
                mon = {"left": max(0, left), "top": max(0, top), "width": w, "height": h}
                shot = sct.grab(mon)
                return Image.frombytes("RGB", shot.size, shot.bgra, "raw", "BGRX")
        except Exception:
            return None

    def _capture_hwnd_image(self, hwnd: int) -> Optional[Image.Image]:
        if not hwnd or user32.IsIconic(hwnd):
            return None

        rect = ctypes.wintypes.RECT()
        if not user32.GetWindowRect(hwnd, ctypes.byref(rect)):
            return None
        left, top, right, bot = rect.left, rect.top, rect.right, rect.bottom
        w = right - left
        h = bot - top
        if w < 120 or h < 120:
            return None

        img: Optional[Image.Image] = None
        if HAS_WIN32:
            hwndDC = None
            mfcDC = None
            saveDC = None
            saveBitMap = None
            try:
                hwndDC = win32gui.GetWindowDC(hwnd)
                mfcDC = win32ui.CreateDCFromHandle(hwndDC)
                saveDC = mfcDC.CreateCompatibleDC()
                saveBitMap = win32ui.CreateBitmap()
                saveBitMap.CreateCompatibleBitmap(mfcDC, w, h)
                saveDC.SelectObject(saveBitMap)

                res = user32.PrintWindow(hwnd, saveDC.GetSafeHdc(), PW_RENDERFULLCONTENT)
                if res == 0:
                    res = user32.PrintWindow(hwnd, saveDC.GetSafeHdc(), 0)
                if res != 0:
                    bmpinfo = saveBitMap.GetInfo()
                    bmpstr = saveBitMap.GetBitmapBits(True)
                    cand = Image.frombuffer(
                        "RGB",
                        (bmpinfo["bmWidth"], bmpinfo["bmHeight"]),
                        bmpstr,
                        "raw",
                        "BGRX",
                        0,
                        1,
                    )
                    if not self._is_mostly_black(cand):
                        img = cand
            except Exception:
                img = None
            finally:
                try:
                    if saveBitMap:
                        win32gui.DeleteObject(saveBitMap.GetHandle())
                except Exception:
                    pass
                try:
                    if saveDC:
                        saveDC.DeleteDC()
                except Exception:
                    pass
                try:
                    if mfcDC:
                        mfcDC.DeleteDC()
                except Exception:
                    pass
                try:
                    if hwndDC:
                        win32gui.ReleaseDC(hwnd, hwndDC)
                except Exception:
                    pass

        if img is None:
            img = self._capture_mss_rect(left, top, w, h)
        return img

    def _apply_smart_crop(self, img: Image.Image) -> Image.Image:
        w, h = img.size
        if w < 200 or h < 150:
            return img

        screen_w = user32.GetSystemMetrics(0)
        screen_h = user32.GetSystemMetrics(1)
        is_fullscreen = (w >= screen_w - 24 and h >= screen_h - 24)

        if self._crop_mode == "full" or is_fullscreen:
            return img

        top_bar = min(132, max(76, int(h * 0.13)))
        if self._crop_mode == "clean":
            return img.crop((8, top_bar, max(16, w - 8), max(top_bar + 40, h - 12)))

        if w > 950 and (w / max(1, h)) > 1.25:
            x1 = int(w * 0.015)
            y1 = top_bar
            x2 = int(w * 0.68)
            y2 = min(h - 16, y1 + int((x2 - x1) * 9 / 16))
            if x2 > x1 + 100 and y2 > y1 + 80:
                return img.crop((x1, y1, x2, y2))

        y1 = top_bar
        x1 = 8
        x2 = max(16, w - 8)
        y2 = min(h - 12, y1 + int((x2 - x1) * 9 / 16))
        if y2 > y1 + 80:
            return img.crop((x1, y1, x2, y2))
        return img.crop((8, top_bar, max(16, w - 8), h - 8))

    def _build_placeholder_jpeg(self, text: str) -> bytes:
        img = Image.new("RGB", (640, 360), (18, 18, 22))
        draw = ImageDraw.Draw(img)
        draw.rounded_rectangle([(24, 24), (616, 336)], radius=24, outline=(250, 45, 72), width=2)
        draw.text((190, 165), text, fill=(235, 235, 240))
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=75)
        return buf.getvalue()

    def _stop_helper(self):
        proc = self._helper_proc
        self._helper_proc = None
        self._helper_vid = ""
        if proc is not None:
            try:
                if proc.stdin:
                    proc.stdin.write(b'{"quit": true}\n')
                    proc.stdin.flush()
            except Exception:
                pass
            try:
                proc.terminate()
            except Exception:
                pass

    def _ensure_helper(self, video_id: str, pos_sec: float):
        if not video_id:
            return
        if self._helper_proc is not None and self._helper_proc.poll() is None:
            if self._helper_vid != video_id:
                self._helper_vid = video_id
                try:
                    msg = json.dumps({"video_id": video_id, "pos": int(pos_sec)}) + "\n"
                    self._helper_proc.stdin.write(msg.encode("utf-8"))
                    self._helper_proc.stdin.flush()
                except Exception:
                    self._stop_helper()
            return

        helper_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "yt_player_helper.py")
        if not os.path.exists(helper_path):
            return
        try:
            creationflags = 0x08000000 if sys.platform == "win32" else 0  # CREATE_NO_WINDOW
            proc = subprocess.Popen(
                [sys.executable, helper_path],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                creationflags=creationflags,
            )
            self._helper_proc = proc
            self._helper_vid = video_id
            msg = json.dumps({"video_id": video_id, "pos": int(pos_sec)}) + "\n"
            proc.stdin.write(msg.encode("utf-8"))
            proc.stdin.flush()

            def _read_frames():
                try:
                    out = proc.stdout
                    while proc.poll() is None and self._helper_proc is proc:
                        hdr = out.read(16)
                        if not hdr or len(hdr) < 16:
                            break
                        magic, fw, fh, flen = struct.unpack("<4sIII", hdr)
                        if magic != b"YTFM" or flen <= 0 or flen > 4_000_000:
                            break
                        rgb = out.read(flen)
                        if not rgb or len(rgb) < flen:
                            break
                        img = Image.frombytes("RGB", (fw, fh), rgb)
                        buf = io.BytesIO()
                        img.save(buf, format="JPEG", quality=72, optimize=False)
                        jbytes = buf.getvalue()
                        with self._lock:
                            self._latest_rgb = rgb
                            self._latest_size = (fw, fh)
                            self._latest_jpeg = jbytes
                            self._frame_version += 1
                            self._last_capture_ts = time.monotonic()
                except Exception:
                    pass

            self._helper_reader = threading.Thread(target=_read_frames, daemon=True, name="YTHelperReader")
            self._helper_reader.start()
        except Exception:
            self._helper_proc = None

    def _capture_once(self):
        hwnd, title, is_min = self.find_youtube_window()
        if not hwnd or is_min:
            # Fallback to offscreen helper when YouTube is minimized or in a background tab
            if self._ctx_title:
                vid = self.resolve_video_id(self._ctx_title, self._ctx_artist, async_only=True)
                if vid:
                    self._ensure_helper(vid, self._ctx_pos)
                    return
            with self._lock:
                self._latest_rgb = None
                self._latest_size = (0, 0)
            return

        self._stop_helper()
        img = self._capture_hwnd_image(hwnd)
        if img is None:
            return

        cropped = self._apply_smart_crop(img)
        cw, ch = cropped.size
        if cw > 960:
            nh = max(1, int(ch * (960.0 / cw)))
            cropped = cropped.resize((960, nh), Image.Resampling.BILINEAR)
            cw, ch = cropped.size

        rgb_bytes = cropped.tobytes("raw", "RGB")
        buf = io.BytesIO()
        cropped.save(buf, format="JPEG", quality=72, optimize=False)
        jpeg_bytes = buf.getvalue()

        with self._lock:
            self._latest_rgb = rgb_bytes
            self._latest_size = (cw, ch)
            self._latest_jpeg = jpeg_bytes
            self._frame_version += 1
            self._last_capture_ts = time.monotonic()

    def _ensure_worker(self):
        self._last_viewer_ts = time.monotonic()
        if self._worker_thread and self._worker_thread.is_alive():
            return
        self._stop_event.clear()

        def _loop():
            _attach_default_desktop()
            while not self._stop_event.is_set():
                if time.monotonic() - self._last_viewer_ts > 2.5:
                    self._stop_helper()
                    break
                t0 = time.monotonic()
                try:
                    self._capture_once()
                except Exception:
                    pass
                elapsed = time.monotonic() - t0
                time.sleep(max(0.01, 0.048 - elapsed))

        self._worker_thread = threading.Thread(target=_loop, daemon=True, name="YouTubeVideoCapture")
        self._worker_thread.start()

    def get_latest_rgb_frame(self) -> Tuple[Optional[bytes], int, int, int]:
        """Called by Origin Island Qt paint/timer. Returns (rgb_bytes, w, h, frame_version)."""
        self._ensure_worker()
        with self._lock:
            return self._latest_rgb, self._latest_size[0], self._latest_size[1], self._frame_version

    def get_latest_jpeg_frame(self) -> Tuple[bytes, bool, bool]:
        """Called by Phone App MJPEG endpoint. Returns (jpeg_bytes, is_available, is_minimized)."""
        self._ensure_worker()
        hwnd, _, is_min = self.find_youtube_window()
        if not hwnd:
            return self._build_placeholder_jpeg("Open a YouTube video on PC to stream"), False, False
        if is_min:
            return self._build_placeholder_jpeg("YouTube window is minimized on PC"), True, True
        with self._lock:
            if self._latest_jpeg and (time.monotonic() - self._last_capture_ts) < 2.0:
                return self._latest_jpeg, True, False
        self._capture_once()
        with self._lock:
            if self._latest_jpeg:
                return self._latest_jpeg, True, False
        return self._build_placeholder_jpeg("Capturing YouTube video..."), True, False

    def stop(self):
        self._stop_event.set()


youtube_video_service = YouTubeVideoService()
