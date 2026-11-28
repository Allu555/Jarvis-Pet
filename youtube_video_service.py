import ctypes
import io
import threading
import time
from typing import Optional, Tuple, Dict, Any

from PIL import Image, ImageDraw

try:
    import win32gui
    import win32ui
    import win32con
    HAS_WIN32 = True
except Exception:
    HAS_WIN32 = False

user32 = ctypes.windll.user32
PW_RENDERFULLCONTENT = 2

BROWSER_HINTS = ("chrome", "brave", "edge", "firefox", "opera", "vivaldi", "arc")


class YouTubeVideoService:
    """
    Lightweight, zero-leak live YouTube browser window capture service.
    Shared by Origin Island (desktop PiP) and Phone Drop Service (MJPEG stream).
    Captures only when actively viewed; 0% CPU when idle.
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
        """Returns (hwnd, window_title, is_minimized) for the active YouTube browser window."""
        if not HAS_WIN32:
            return None, "", False

        matches = []

        def _enum_cb(hwnd, _):
            try:
                if not win32gui.IsWindowVisible(hwnd):
                    return True
                title = win32gui.GetWindowText(hwnd) or ""
                if not title:
                    return True
                tl = title.lower()
                # Primary match: explicit "- YouTube" tab title
                if "- youtube" in tl or tl.startswith("youtube"):
                    is_min = bool(win32gui.IsIconic(hwnd))
                    matches.append((0 if not is_min else 1, hwnd, title, is_min))
            except Exception:
                pass
            return True

        try:
            win32gui.EnumWindows(_enum_cb, None)
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
                win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
            win32gui.SetForegroundWindow(hwnd)
            return True
        except Exception:
            return False

    def _capture_hwnd_image(self, hwnd: int) -> Optional[Image.Image]:
        if not HAS_WIN32 or not hwnd or win32gui.IsIconic(hwnd):
            return None

        hwndDC = None
        mfcDC = None
        saveDC = None
        saveBitMap = None
        try:
            left, top, right, bot = win32gui.GetWindowRect(hwnd)
            w = right - left
            h = bot - top
            if w < 120 or h < 120:
                return None

            hwndDC = win32gui.GetWindowDC(hwnd)
            mfcDC = win32ui.CreateDCFromHandle(hwndDC)
            saveDC = mfcDC.CreateCompatibleDC()
            saveBitMap = win32ui.CreateBitmap()
            saveBitMap.CreateCompatibleBitmap(mfcDC, w, h)
            saveDC.SelectObject(saveBitMap)

            # PW_RENDERFULLCONTENT = 2 captures hardware-accelerated DWM browser video
            res = user32.PrintWindow(hwnd, saveDC.GetSafeHdc(), PW_RENDERFULLCONTENT)
            if res == 0:
                res = user32.PrintWindow(hwnd, saveDC.GetSafeHdc(), 0)
            if res == 0:
                return None

            bmpinfo = saveBitMap.GetInfo()
            bmpstr = saveBitMap.GetBitmapBits(True)
            img = Image.frombuffer(
                "RGB",
                (bmpinfo["bmWidth"], bmpinfo["bmHeight"]),
                bmpstr,
                "raw",
                "BGRX",
                0,
                1,
            )
            return img
        except Exception:
            return None
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

    def _apply_smart_crop(self, img: Image.Image) -> Image.Image:
        w, h = img.size
        if w < 200 or h < 150:
            return img

        screen_w = user32.GetSystemMetrics(0)
        screen_h = user32.GetSystemMetrics(1)
        is_fullscreen = (w >= screen_w - 24 and h >= screen_h - 24)

        if self._crop_mode == "full" or is_fullscreen:
            return img

        # Remove browser window border & top tabs/address bar + YouTube header
        top_bar = min(132, max(76, int(h * 0.13)))
        if self._crop_mode == "clean":
            return img.crop((8, top_bar, max(16, w - 8), max(top_bar + 40, h - 12)))

        # "zoom" mode: focus on the 16:9 YouTube player region
        if w > 950 and (w / max(1, h)) > 1.25:
            x1 = int(w * 0.015)
            y1 = top_bar
            x2 = int(w * 0.68)
            y2 = min(h - 16, y1 + int((x2 - x1) * 9 / 16))
            if x2 > x1 + 100 and y2 > y1 + 80:
                return img.crop((x1, y1, x2, y2))

        # Narrow / compact window fallback: crop top bar & keep 16:9 upper region
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

    def _capture_once(self):
        hwnd, title, is_min = self.find_youtube_window()
        if not hwnd or is_min:
            return
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
            while not self._stop_event.is_set():
                if time.monotonic() - self._last_viewer_ts > 2.5:
                    break
                t0 = time.monotonic()
                try:
                    self._capture_once()
                except Exception:
                    pass
                elapsed = time.monotonic() - t0
                time.sleep(max(0.01, 0.048 - elapsed))  # ~20 FPS target

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
        # Immediate fallback capture on first request
        self._capture_once()
        with self._lock:
            if self._latest_jpeg:
                return self._latest_jpeg, True, False
        return self._build_placeholder_jpeg("Capturing YouTube video..."), True, False

    def stop(self):
        self._stop_event.set()


# Global singleton shared between Origin Island and Phone Drop Service
youtube_video_service = YouTubeVideoService()
