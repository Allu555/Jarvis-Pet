import asyncio
import calendar
import ctypes
import datetime
import math
import os
import random
import re
import subprocess
import sys
import time
import urllib.parse
import webbrowser
import json
import threading
from collections import OrderedDict
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple

# Ensure 1ms OS multimedia timer precision on Windows for rock-solid 60 FPS animation
if sys.platform == "win32":
    try:
        ctypes.windll.winmm.timeBeginPeriod(1)
    except Exception:
        pass

try:
    import psutil
    HAS_PSUTIL = True
except Exception:
    HAS_PSUTIL = False

def _win_get_system_volume() -> float:
    try:
        from comtypes import CLSCTX_ALL, CoCreateInstance, GUID
        import comtypes
        from comtypes import IUnknown

        CLSID_MMDeviceEnumerator = GUID('{BCDE0395-E52F-467C-8E3D-C4579291692E}')
        IID_IMMDeviceEnumerator = GUID('{A95664D2-9614-4F35-A746-DE8DB63617E6}')
        IID_IAudioEndpointVolume = GUID('{5CDF2C82-841E-4546-9722-0CF74078229A}')

        class IAudioEndpointVolume(IUnknown):
            _iid_ = IID_IAudioEndpointVolume
            _methods_ = [
                comtypes.STDMETHOD(comtypes.HRESULT, 'RegisterControlChangeNotify', []),
                comtypes.STDMETHOD(comtypes.HRESULT, 'UnregisterControlChangeNotify', []),
                comtypes.STDMETHOD(comtypes.HRESULT, 'GetChannelCount', [ctypes.POINTER(ctypes.c_uint)]),
                comtypes.STDMETHOD(comtypes.HRESULT, 'SetMasterVolumeLevel', [ctypes.c_float, ctypes.c_void_p]),
                comtypes.STDMETHOD(comtypes.HRESULT, 'SetMasterVolumeLevelScalar', [ctypes.c_float, ctypes.c_void_p]),
                comtypes.STDMETHOD(comtypes.HRESULT, 'GetMasterVolumeLevel', [ctypes.POINTER(ctypes.c_float)]),
                comtypes.STDMETHOD(comtypes.HRESULT, 'GetMasterVolumeLevelScalar', [ctypes.POINTER(ctypes.c_float)]),
                comtypes.STDMETHOD(comtypes.HRESULT, 'SetMute', [ctypes.c_bool, ctypes.c_void_p]),
                comtypes.STDMETHOD(comtypes.HRESULT, 'GetMute', [ctypes.POINTER(ctypes.c_bool)]),
            ]

        class IMMDevice(IUnknown):
            _iid_ = GUID('{D666063F-1587-4E43-81F1-B948E807363F}')
            _methods_ = [
                comtypes.STDMETHOD(comtypes.HRESULT, 'Activate', [ctypes.POINTER(GUID), ctypes.c_ulong, ctypes.c_void_p, ctypes.POINTER(ctypes.POINTER(IUnknown))]),
            ]

        class IMMDeviceEnumerator(IUnknown):
            _iid_ = IID_IMMDeviceEnumerator
            _methods_ = [
                comtypes.STDMETHOD(comtypes.HRESULT, 'EnumAudioEndpoints', []),
                comtypes.STDMETHOD(comtypes.HRESULT, 'GetDefaultAudioEndpoint', [ctypes.c_int, ctypes.c_int, ctypes.POINTER(ctypes.POINTER(IMMDevice))]),
            ]

        enumerator = CoCreateInstance(CLSID_MMDeviceEnumerator, IMMDeviceEnumerator, CLSCTX_ALL)
        endpoint = ctypes.POINTER(IMMDevice)()
        enumerator.GetDefaultAudioEndpoint(0, 1, ctypes.byref(endpoint))
        vol_ptr = ctypes.POINTER(IUnknown)()
        endpoint.Activate(ctypes.byref(IID_IAudioEndpointVolume), CLSCTX_ALL, None, ctypes.byref(vol_ptr))
        volume = vol_ptr.QueryInterface(IAudioEndpointVolume)
        cur = ctypes.c_float()
        volume.GetMasterVolumeLevelScalar(ctypes.byref(cur))
        return float(cur.value * 100.0)
    except Exception:
        return 50.0

def _win_set_system_volume(val_pct: float):
    try:
        from comtypes import CLSCTX_ALL, CoCreateInstance, GUID
        import comtypes
        from comtypes import IUnknown

        CLSID_MMDeviceEnumerator = GUID('{BCDE0395-E52F-467C-8E3D-C4579291692E}')
        IID_IMMDeviceEnumerator = GUID('{A95664D2-9614-4F35-A746-DE8DB63617E6}')
        IID_IAudioEndpointVolume = GUID('{5CDF2C82-841E-4546-9722-0CF74078229A}')

        class IAudioEndpointVolume(IUnknown):
            _iid_ = IID_IAudioEndpointVolume
            _methods_ = [
                comtypes.STDMETHOD(comtypes.HRESULT, 'RegisterControlChangeNotify', []),
                comtypes.STDMETHOD(comtypes.HRESULT, 'UnregisterControlChangeNotify', []),
                comtypes.STDMETHOD(comtypes.HRESULT, 'GetChannelCount', [ctypes.POINTER(ctypes.c_uint)]),
                comtypes.STDMETHOD(comtypes.HRESULT, 'SetMasterVolumeLevel', [ctypes.c_float, ctypes.c_void_p]),
                comtypes.STDMETHOD(comtypes.HRESULT, 'SetMasterVolumeLevelScalar', [ctypes.c_float, ctypes.c_void_p]),
                comtypes.STDMETHOD(comtypes.HRESULT, 'GetMasterVolumeLevel', [ctypes.POINTER(ctypes.c_float)]),
                comtypes.STDMETHOD(comtypes.HRESULT, 'GetMasterVolumeLevelScalar', [ctypes.POINTER(ctypes.c_float)]),
                comtypes.STDMETHOD(comtypes.HRESULT, 'SetMute', [ctypes.c_bool, ctypes.c_void_p]),
                comtypes.STDMETHOD(comtypes.HRESULT, 'GetMute', [ctypes.POINTER(ctypes.c_bool)]),
            ]

        class IMMDevice(IUnknown):
            _iid_ = GUID('{D666063F-1587-4E43-81F1-B948E807363F}')
            _methods_ = [
                comtypes.STDMETHOD(comtypes.HRESULT, 'Activate', [ctypes.POINTER(GUID), ctypes.c_ulong, ctypes.c_void_p, ctypes.POINTER(ctypes.POINTER(IUnknown))]),
            ]

        class IMMDeviceEnumerator(IUnknown):
            _iid_ = IID_IMMDeviceEnumerator
            _methods_ = [
                comtypes.STDMETHOD(comtypes.HRESULT, 'EnumAudioEndpoints', []),
                comtypes.STDMETHOD(comtypes.HRESULT, 'GetDefaultAudioEndpoint', [ctypes.c_int, ctypes.c_int, ctypes.POINTER(ctypes.POINTER(IMMDevice))]),
            ]

        enumerator = CoCreateInstance(CLSID_MMDeviceEnumerator, IMMDeviceEnumerator, CLSCTX_ALL)
        endpoint = ctypes.POINTER(IMMDevice)()
        enumerator.GetDefaultAudioEndpoint(0, 1, ctypes.byref(endpoint))
        vol_ptr = ctypes.POINTER(IUnknown)()
        endpoint.Activate(ctypes.byref(IID_IAudioEndpointVolume), CLSCTX_ALL, None, ctypes.byref(vol_ptr))
        volume = vol_ptr.QueryInterface(IAudioEndpointVolume)
        scalar = max(0.0, min(1.0, float(val_pct) / 100.0))
        volume.SetMasterVolumeLevelScalar(scalar, None)
    except Exception:
        pass

class AudioMeterService:
    """Windows Core Audio WASAPI hardware audio meter with 0ms latency."""
    _meter = None
    _last_init_attempt = 0.0
    _failed = False

    @classmethod
    def get_peaks(cls) -> Tuple[float, float, float]:
        """Returns (master_peak, left_peak, right_peak) in range 0.0 - 1.0."""
        now = time.time()
        if cls._meter is None:
            if cls._failed and (now - cls._last_init_attempt < 3.0):
                return 0.0, 0.0, 0.0
            cls._last_init_attempt = now
            try:
                from comtypes import CLSCTX_ALL, CoCreateInstance, GUID
                import comtypes
                from comtypes import IUnknown

                CLSID_MMDeviceEnumerator = GUID('{BCDE0395-E52F-467C-8E3D-C4579291692E}')
                IID_IMMDeviceEnumerator = GUID('{A95664D2-9614-4F35-A746-DE8DB63617E6}')
                IID_IAudioMeterInformation = GUID('{C02216F6-8C67-4B5B-9D00-D008E73E0064}')

                class IMMDevice(IUnknown):
                    _iid_ = GUID('{D666063F-1587-4E43-81F1-B948E807363F}')
                    _methods_ = [
                        comtypes.STDMETHOD(comtypes.HRESULT, 'Activate', [ctypes.POINTER(GUID), ctypes.c_ulong, ctypes.c_void_p, ctypes.POINTER(ctypes.POINTER(IUnknown))]),
                    ]

                class IMMDeviceEnumerator(IUnknown):
                    _iid_ = IID_IMMDeviceEnumerator
                    _methods_ = [
                        comtypes.STDMETHOD(comtypes.HRESULT, 'EnumAudioEndpoints', []),
                        comtypes.STDMETHOD(comtypes.HRESULT, 'GetDefaultAudioEndpoint', [ctypes.c_int, ctypes.c_int, ctypes.POINTER(ctypes.POINTER(IMMDevice))]),
                    ]

                class IAudioMeterInformation(IUnknown):
                    _iid_ = IID_IAudioMeterInformation
                    _methods_ = [
                        comtypes.STDMETHOD(comtypes.HRESULT, 'GetPeakValue', [ctypes.POINTER(ctypes.c_float)]),
                        comtypes.STDMETHOD(comtypes.HRESULT, 'GetMeteringChannelCount', [ctypes.POINTER(ctypes.c_uint)]),
                        comtypes.STDMETHOD(comtypes.HRESULT, 'GetChannelsPeakValues', [ctypes.c_uint, ctypes.POINTER(ctypes.c_float)]),
                        comtypes.STDMETHOD(comtypes.HRESULT, 'QueryHardwareSupport', [ctypes.POINTER(ctypes.c_uint)]),
                    ]

                enumerator = CoCreateInstance(CLSID_MMDeviceEnumerator, IMMDeviceEnumerator, CLSCTX_ALL)
                endpoint = ctypes.POINTER(IMMDevice)()
                enumerator.GetDefaultAudioEndpoint(0, 1, ctypes.byref(endpoint))
                meter_ptr = ctypes.POINTER(IUnknown)()
                endpoint.Activate(ctypes.byref(IID_IAudioMeterInformation), CLSCTX_ALL, None, ctypes.byref(meter_ptr))
                cls._meter = meter_ptr.QueryInterface(IAudioMeterInformation)
                cls._failed = False
            except Exception:
                cls._failed = True
                cls._meter = None
                return 0.0, 0.0, 0.0

        try:
            cur = ctypes.c_float()
            cls._meter.GetPeakValue(ctypes.byref(cur))
            master_peak = float(cur.value)

            ch_count = ctypes.c_uint()
            cls._meter.GetMeteringChannelCount(ctypes.byref(ch_count))
            ch_num = ch_count.value
            left_peak = master_peak
            right_peak = master_peak
            if ch_num >= 2:
                arr_type = ctypes.c_float * ch_num
                ch_peaks = arr_type()
                cls._meter.GetChannelsPeakValues(ch_num, ch_peaks)
                left_peak = float(ch_peaks[0])
                right_peak = float(ch_peaks[1])
            return master_peak, left_peak, right_peak
        except Exception:
            cls._meter = None
            return 0.0, 0.0, 0.0

def _win_set_system_brightness(val_pct: float):
    try:
        from ctypes import wintypes
        class RAMP(ctypes.Structure):
            _fields_ = [
                ('Red', wintypes.WORD * 256),
                ('Green', wintypes.WORD * 256),
                ('Blue', wintypes.WORD * 256),
            ]
        hdc = ctypes.windll.user32.GetDC(None)
        ramp = RAMP()
        pct = max(15.0, min(100.0, float(val_pct)))
        multiplier = pct / 100.0
        for i in range(256):
            val = int(min(65535, max(0, i * 256 * multiplier)))
            ramp.Red[i] = val
            ramp.Green[i] = val
            ramp.Blue[i] = val
        ctypes.windll.gdi32.SetDeviceGammaRamp(hdc, ctypes.byref(ramp))
        ctypes.windll.user32.ReleaseDC(None, hdc)
    except Exception:
        pass

def _win_get_internet_connected() -> bool:
    try:
        flags = ctypes.c_ulong()
        return bool(ctypes.windll.wininet.InternetGetConnectedState(ctypes.byref(flags), 0))
    except Exception:
        return True

_JARVIS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "jarvis")
if _JARVIS_DIR not in sys.path:
    sys.path.insert(0, _JARVIS_DIR)

from PySide6.QtCore import (
    Qt, QTimer, QPoint, QPointF, QRect, QRectF, QSize, QPropertyAnimation,
    QEasingCurve, Signal, QUrl, QMimeData, QThread
)
from PySide6.QtGui import (
    QPainter, QColor, QFont, QFontMetrics, QPainterPath, QPen, QBrush,
    QPixmap, QImage, QLinearGradient, QRadialGradient, QCursor,
    QGuiApplication, QDesktopServices, QPolygonF, QDrag,
    QDropEvent, QDragEnterEvent, QDragMoveEvent, QDragLeaveEvent
)
from PySide6.QtWidgets import (
    QWidget, QApplication, QPushButton, QHBoxLayout, QVBoxLayout,
    QLabel, QGraphicsDropShadowEffect, QLineEdit
)

from media_service import MediaService, MediaInfo
from weather_service import WeatherService, WeatherInfo
from bluetooth_service import BluetoothService, BluetoothInfo
from phone_drop_service import PhoneDropService


def parse_rgba_color(val) -> QColor:
    if isinstance(val, QColor):
        return val if val.isValid() else QColor(255, 255, 255, 255)
    if not val or not isinstance(val, str):
        return QColor(255, 255, 255, 255)
    s = val.strip()
    m = re.match(r'rgba?\s*\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)(?:\s*,\s*([\d\.]+))?\s*\)', s, re.IGNORECASE)
    if m:
        r = int(m.group(1))
        g = int(m.group(2))
        b = int(m.group(3))
        a_str = m.group(4)
        if a_str is not None:
            a_val = float(a_str)
            a = int(a_val * 255) if a_val <= 1.0 and '.' in a_str else int(a_val)
        else:
            a = 255
        return QColor(r, g, b, max(0, min(255, a)))
    col = QColor(s)
    if col.isValid():
        return col
    return QColor(255, 255, 255, 255)


class LyricsEngine:
    """
    Ultra-lightweight real-time synchronized karaoke lyrics engine.
    Purely in-memory LRU cache (capped at 25 tracks) — ZERO disk writes,
    keeping the project repository lightweight, clean, and fast with no file bloat.
    """
    _mem_cache: "OrderedDict[str, Tuple[List[Tuple[float, str]], float]]" = OrderedDict()
    _cache: Dict[str, List[Tuple[float, str]]] = {}
    _cache_offsets: Dict[str, float] = {}
    MAX_CACHE_ENTRIES = 25

    @classmethod
    def _make_key(cls, title: str, artist: str) -> str:
        clean_t, clean_a = cls.clean_song_info(title, artist)
        return f"{clean_a.lower()}:{clean_t.lower()}"

    @classmethod
    def get_disk_cached_lyrics(cls, title: str, artist: str) -> Optional[Tuple[List[Tuple[float, str]], float]]:
        """Fast in-memory cache lookup. Zero disk I/O."""
        key = cls._make_key(title, artist)
        if key in cls._mem_cache:
            cls._mem_cache.move_to_end(key)
            return cls._mem_cache[key]
        return None

    @classmethod
    def save_disk_cached_lyrics(cls, title: str, artist: str, album: str, duration_sec: float, lines: List[Tuple[float, str]], lrc_text: str = "", user_offset: float = 0.0):
        """Stores lyrics purely in-memory in an LRU cache with zero disk writes."""
        key = cls._make_key(title, artist)
        cls._mem_cache[key] = (lines, user_offset)
        cls._mem_cache.move_to_end(key)
        cls._cache[key] = lines
        cls._cache_offsets[key] = user_offset
        while len(cls._mem_cache) > cls.MAX_CACHE_ENTRIES:
            old_k, _ = cls._mem_cache.popitem(last=False)
            cls._cache.pop(old_k, None)
            cls._cache_offsets.pop(old_k, None)

    @classmethod
    def update_cached_offset(cls, title: str, artist: str, offset: float):
        """Updates user timing offset in memory."""
        key = cls._make_key(title, artist)
        if key in cls._mem_cache:
            lines, _ = cls._mem_cache[key]
            cls._mem_cache[key] = (lines, offset)
            cls._cache_offsets[key] = offset

    @classmethod
    def clear_cache(cls):
        """Wipes in-memory cache and cleans up any legacy disk files."""
        cls._mem_cache.clear()
        cls._cache.clear()
        cls._cache_offsets.clear()
        try:
            legacy_dir = Path(__file__).parent / "lyrics"
            if legacy_dir.exists():
                import shutil
                shutil.rmtree(legacy_dir, ignore_errors=True)
        except Exception:
            pass

    @classmethod
    def clean_song_info(cls, title: str, artist: str) -> Tuple[str, str]:
        t = title
        # Strip brackets, parentheses, curly braces: e.g. (From "Jawan"), [Official Video], (Full Song)
        t = re.sub(r"\s*[\(\[\{].*?[\)\]\}]", "", t)
        # Strip trailing suffixes like - From Movie, - Remastered, - Lyrical
        t = re.sub(r"\s*-\s*(?:From|Original|Remastered|Remix|Live|Audio|Video|Single|Deluxe|Soundtrack|Lyrical|Official).*", "", t, flags=re.IGNORECASE)
        # Strip pipe separators common in YouTube: Title | Movie | Singer
        if "|" in t:
            t = t.split("|")[0].strip()
        # Strip common video tags
        t = re.sub(r"\b(Official\s*(?:Music\s*)?Video|Lyric\s*Video|Full\s*Song|Video\s*Song|Audio\s*Track|4K|HD)\b", "", t, flags=re.IGNORECASE)

        a = artist
        a = re.sub(r"\s*[\(\[\{].*?[\)\]\}]", "", a)
        # Only keep primary artist if multiple are comma-separated or joined by feat/ft
        a = re.split(r"[,&/|]|\bfeat\.?\b|\bft\.?\b", a, flags=re.IGNORECASE)[0]

        clean_t = t.strip() or title.strip()
        clean_a = a.strip() or artist.strip()
        return clean_t, clean_a

    @classmethod
    def fetch_lyrics(cls, req_key: str, artist: str, title: str, album: str, duration_sec: float, callback):
        clean_title, clean_artist = cls.clean_song_info(title, artist)
        cache_key = f"{clean_artist.lower()}:{clean_title.lower()}"

        # 1. In-memory Cache Check
        if cache_key in cls._cache:
            callback(req_key, cls._cache[cache_key], getattr(cls, "_cache_offsets", {}).get(cache_key, 0.0))
            return

        # 2. Local Disk Cache Check (0ms Instant Load from 'lyrics' subfolder)
        disk_result = cls.get_disk_cached_lyrics(clean_title, clean_artist)
        if disk_result:
            disk_lines, disk_offset = disk_result
            cls._cache[cache_key] = disk_lines
            if not hasattr(cls, "_cache_offsets"):
                cls._cache_offsets = {}
            cls._cache_offsets[cache_key] = disk_offset
            callback(req_key, disk_lines, disk_offset)
            return

        # Immediate preview lines for 0ms latency while network fetches
        dur = duration_sec if duration_sec > 10 else 210.0
        instant_lines = [
            (0.0, f"♪ {clean_title} ♪"),
            (max(3.0, dur * 0.05), f"{clean_artist}"),
            (max(8.0, dur * 0.12), "♪ Fetching synchronized live lyrics... ♪"),
            (max(18.0, dur * 0.28), f"♪ Listening to {clean_title} ♪"),
            (max(35.0, dur * 0.50), "♪ In harmony with the music ♪"),
            (max(60.0, dur * 0.75), "♪ Enjoy the melody ♪")
        ]
        callback(req_key, instant_lines, 0.0)

        def _worker():
            lines: List[Tuple[float, str]] = []
            lrc_content = ""
            import urllib.request, json, urllib.parse

            # Strategy 1: Direct LRCLIB /api/get endpoint (title, artist, album, duration)
            if clean_artist.lower() not in ["youtube", "media", "desktop-pet", "unknown", ""]:
                try:
                    q_params = {
                        "artist_name": clean_artist,
                        "track_name": clean_title,
                        "duration": int(duration_sec) if duration_sec > 0 else 0
                    }
                    if album and album.strip():
                        q_params["album_name"] = album.strip()
                    params = urllib.parse.urlencode(q_params)
                    url = f"https://lrclib.net/api/get?{params}"
                    req = urllib.request.Request(url, headers={"User-Agent": "OriginIsland/2.0"})
                    with urllib.request.urlopen(req, timeout=3.5) as resp:
                        data = json.loads(resp.read().decode("utf-8", errors="ignore"))
                        synced = data.get("syncedLyrics")
                        plain = data.get("plainLyrics")
                        if synced:
                            lrc_content = synced
                            lines = cls._parse_lrc(synced)
                        elif plain:
                            lrc_content = plain
                            raw_lines = [l.strip() for l in plain.split("\n") if l.strip()]
                            if raw_lines:
                                step = (duration_sec if duration_sec > 10 else 180.0) / max(1, len(raw_lines))
                                lines = [(i * step, text) for i, text in enumerate(raw_lines)]
                except Exception:
                    pass

            # Strategy 2: LRCLIB /api/search fallback
            if not lines:
                try:
                    search_query = clean_title if clean_artist.lower() in ["youtube", "media", "desktop-pet", "unknown", ""] else f"{clean_title} {clean_artist}"
                    q = urllib.parse.quote(search_query)
                    search_url = f"https://lrclib.net/api/search?q={q}"
                    req = urllib.request.Request(search_url, headers={"User-Agent": "OriginIsland/2.0"})
                    with urllib.request.urlopen(req, timeout=3.5) as resp:
                        results = json.loads(resp.read().decode("utf-8", errors="ignore"))
                        if results and isinstance(results, list):
                            for item in results:
                                if item.get("syncedLyrics"):
                                    lrc_content = item["syncedLyrics"]
                                    lines = cls._parse_lrc(item["syncedLyrics"])
                                    break
                            if not lines:
                                for item in results:
                                    if item.get("plainLyrics"):
                                        lrc_content = item["plainLyrics"]
                                        raw_lines = [l.strip() for l in item["plainLyrics"].split("\n") if l.strip()]
                                        if raw_lines:
                                            step = (duration_sec if duration_sec > 10 else 180.0) / max(1, len(raw_lines))
                                            lines = [(i * step, text) for i, text in enumerate(raw_lines)]
                                            break
                except Exception:
                    pass

            # Strategy 2b: Search clean_title alone fallback
            if not lines:
                try:
                    q2 = urllib.parse.quote(clean_title)
                    search_url2 = f"https://lrclib.net/api/search?q={q2}"
                    req2 = urllib.request.Request(search_url2, headers={"User-Agent": "OriginIsland/2.0"})
                    with urllib.request.urlopen(req2, timeout=3.5) as resp:
                        results2 = json.loads(resp.read().decode("utf-8", errors="ignore"))
                        if results2 and isinstance(results2, list):
                            for item in results2:
                                if item.get("syncedLyrics"):
                                    lrc_content = item["syncedLyrics"]
                                    lines = cls._parse_lrc(item["syncedLyrics"])
                                    break
                            if not lines:
                                for item in results2:
                                    if item.get("plainLyrics"):
                                        lrc_content = item["plainLyrics"]
                                        raw_lines = [l.strip() for l in item["plainLyrics"].split("\n") if l.strip()]
                                        if raw_lines:
                                            step = (duration_sec if duration_sec > 10 else 180.0) / max(1, len(raw_lines))
                                            lines = [(i * step, text) for i, text in enumerate(raw_lines)]
                                            break
                except Exception:
                    pass

            # Strategy 2c: Search with first 3 words of clean_title
            if not lines and len(clean_title.split()) > 3:
                try:
                    short_q = " ".join(clean_title.split()[:3])
                    q3 = urllib.parse.quote(short_q)
                    search_url3 = f"https://lrclib.net/api/search?q={q3}"
                    req3 = urllib.request.Request(search_url3, headers={"User-Agent": "OriginIsland/2.0"})
                    with urllib.request.urlopen(req3, timeout=3.5) as resp:
                        results3 = json.loads(resp.read().decode("utf-8", errors="ignore"))
                        if results3 and isinstance(results3, list):
                            for item in results3:
                                if item.get("syncedLyrics"):
                                    lrc_content = item["syncedLyrics"]
                                    lines = cls._parse_lrc(item["syncedLyrics"])
                                    break
                except Exception:
                    pass

            if not lines:
                lines = [
                    (0.0, f"♪ {clean_title} ♪"),
                    (max(4.0, duration_sec * 0.10), f"Artist: {clean_artist}"),
                    (max(12.0, duration_sec * 0.25), "♪ Live Audio Stream ♪"),
                    (max(28.0, duration_sec * 0.55), f"♪ Playing {clean_title} ♪"),
                    (max(50.0, duration_sec * 0.85), "♪ Enjoy the beat ♪")
                ]

            # Save to disk cache in 'lyrics' subfolder for instant re-loads
            cls.save_disk_cached_lyrics(clean_title, clean_artist, album, duration_sec, lines, lrc_content, user_offset=0.0)
            cls._cache[cache_key] = lines
            callback(req_key, lines, 0.0)

        threading.Thread(target=_worker, daemon=True, name="lyrics_worker").start()

    @classmethod
    def _parse_lrc(cls, lrc_text: str) -> List[Tuple[float, str]]:
        # 1. Parse global offset tag [offset:+/-milliseconds] if present
        offset_sec = 0.0
        offset_match = re.search(r"\[offset:\s*([+-]?\d+)\s*\]", lrc_text, re.IGNORECASE)
        if offset_match:
            try:
                offset_sec = float(offset_match.group(1)) / 1000.0
            except Exception:
                offset_sec = 0.0

        time_tag_pattern = re.compile(r"\[(\d+):(\d+(?:\.\d+)?)\]")
        result = []
        for raw_line in lrc_text.splitlines():
            line = raw_line.strip()
            if not line or line.startswith("[offset:") or line.startswith("[ar:") or line.startswith("[ti:") or line.startswith("[al:"):
                continue
            matches = list(time_tag_pattern.finditer(line))
            if not matches:
                continue
            clean_text = time_tag_pattern.sub("", line).strip()
            if not clean_text:
                clean_text = "♪"  # Instrumental break marker
            for m in matches:
                m_val = float(m.group(1))
                s_val = float(m.group(2))
                t_sec = max(0.0, m_val * 60.0 + s_val + offset_sec)
                result.append((t_sec, clean_text))

        result.sort(key=lambda x: x[0])
        return result


ALBUM_ART_PATH = Path(__file__).parent / "assets" / "sprites" / "album_art.png"


ISLAND_THEMES = {
    "bloom_dark": {
        "name": "Dark (Translucent) 🌙",
        "bg_top": QColor(13, 14, 18, 215),
        "bg_bottom": QColor(8, 9, 12, 235),
        "border": QColor(255, 255, 255, 30),
        "border_width": 1.0,
        "accent": QColor(255, 255, 255),
        "accent_glow": QColor(255, 255, 255, 20),
        "text_primary": QColor(255, 255, 255),
        "text_secondary": QColor(148, 153, 165),
        "badge_bg": QColor(255, 255, 255, 20),
        "btn_bg": QColor(255, 255, 255, 22),
        "btn_hover": QColor(255, 255, 255, 55),
        "eq_0": QColor(255, 255, 255),
        "eq_1": QColor(180, 185, 195),
        "accent_green": QColor(52, 199, 89),
        "card_bg": QColor(255, 255, 255, 16),
        "card_hover": QColor(255, 255, 255, 28),
        "notch_gradient": (QColor(15, 17, 23, 230), QColor(8, 9, 13, 245)),
        "eye_color": QColor(255, 255, 255),
    },
    "amoled_black": {
        "name": "AMOLED Pure Black (OLED) 🖤",
        "bg_top": QColor(0, 0, 0, 255),
        "bg_bottom": QColor(0, 0, 0, 255),
        "border": QColor(255, 255, 255, 28),
        "border_width": 1.0,
        "accent": QColor(255, 255, 255),
        "accent_glow": QColor(255, 255, 255, 30),
        "text_primary": QColor(255, 255, 255),
        "text_secondary": QColor(140, 145, 155),
        "badge_bg": QColor(24, 24, 26, 220),
        "btn_bg": QColor(24, 24, 26, 220),
        "btn_hover": QColor(40, 40, 44, 240),
        "eq_0": QColor(255, 255, 255),
        "eq_1": QColor(180, 185, 195),
        "accent_green": QColor(52, 199, 89),
        "card_bg": QColor(18, 18, 20, 220),
        "card_hover": QColor(28, 28, 32, 240),
        "notch_gradient": (QColor(0, 0, 0, 255), QColor(3, 3, 5, 255)),
        "eye_color": QColor(255, 255, 255),
    },
    "electric_neon": {
        "name": "Electric Neon Aura ⚡",
        "bg_top": QColor(8, 12, 28, 240),
        "bg_bottom": QColor(16, 6, 26, 248),
        "border": QColor(0, 160, 255, 90),
        "border_width": 1.2,
        "accent": QColor(0, 210, 255),
        "accent_glow": QColor(180, 50, 255, 45),
        "text_primary": QColor(255, 255, 255),
        "text_secondary": QColor(170, 190, 225),
        "badge_bg": QColor(20, 30, 60, 210),
        "btn_bg": QColor(255, 255, 255, 22),
        "btn_hover": QColor(0, 210, 255, 70),
        "eq_0": QColor(0, 220, 255),
        "eq_1": QColor(180, 50, 255),
        "accent_green": QColor(52, 199, 89),
        "card_bg": QColor(255, 255, 255, 18),
        "card_hover": QColor(255, 255, 255, 32),
        "notch_gradient": (QColor(0, 115, 235, 245), QColor(50, 40, 220, 250), QColor(135, 25, 215, 245)),
        "eye_color": QColor(255, 255, 255),
    },
    "apple_dynamic": {
        "name": "Apple Dynamic Glass (iOS Pro) 🍎",
        "bg_top": QColor(14, 14, 18, 245),
        "bg_bottom": QColor(6, 6, 8, 252),
        "border": QColor(255, 255, 255, 45),
        "border_width": 1.0,
        "accent": QColor(255, 255, 255),
        "accent_glow": QColor(255, 255, 255, 25),
        "text_primary": QColor(255, 255, 255),
        "text_secondary": QColor(155, 155, 165),
        "badge_bg": QColor(35, 35, 42, 210),
        "btn_bg": QColor(255, 255, 255, 22),
        "btn_hover": QColor(255, 255, 255, 70),
        "eq_0": QColor(52, 199, 89),
        "eq_1": QColor(48, 209, 88),
        "accent_green": QColor(52, 199, 89),
        "card_bg": QColor(255, 255, 255, 16),
        "card_hover": QColor(255, 255, 255, 28),
        "notch_gradient": (QColor(16, 16, 20, 240), QColor(8, 8, 10, 250)),
        "eye_color": QColor(255, 255, 255),
    },
    "originos_dark": {
        "name": "OriginOS Obsidian (Deep Space) 🌑",
        "bg_top": QColor(12, 14, 20, 245),
        "bg_bottom": QColor(6, 7, 12, 252),
        "border": QColor(100, 160, 255, 60),
        "border_width": 1.0,
        "accent": QColor(96, 165, 250),
        "accent_glow": QColor(96, 165, 250, 30),
        "text_primary": QColor(255, 255, 255),
        "text_secondary": QColor(148, 163, 184),
        "badge_bg": QColor(30, 41, 59, 200),
        "btn_bg": QColor(255, 255, 255, 20),
        "btn_hover": QColor(96, 165, 250, 80),
        "eq_0": QColor(96, 165, 250),
        "eq_1": QColor(147, 197, 253),
        "accent_green": QColor(52, 199, 89),
        "card_bg": QColor(255, 255, 255, 16),
        "card_hover": QColor(255, 255, 255, 28),
        "notch_gradient": (QColor(14, 18, 28, 240), QColor(8, 10, 16, 250)),
        "eye_color": QColor(255, 255, 255),
    },
    "cyber_glow": {
        "name": "Cyberpunk Titanium (Neon Glow) 🚀",
        "bg_top": QColor(12, 12, 22, 245),
        "bg_bottom": QColor(6, 6, 14, 252),
        "border": QColor(0, 240, 255, 110),
        "border_width": 1.0,
        "accent": QColor(0, 240, 255),
        "accent_glow": QColor(255, 0, 128, 50),
        "text_primary": QColor(255, 255, 255),
        "text_secondary": QColor(120, 225, 245),
        "badge_bg": QColor(255, 0, 128, 120),
        "btn_bg": QColor(0, 240, 255, 25),
        "btn_hover": QColor(0, 240, 255, 90),
        "eq_0": QColor(0, 240, 255),
        "eq_1": QColor(255, 0, 128),
        "accent_green": QColor(52, 199, 89),
        "card_bg": QColor(255, 255, 255, 16),
        "card_hover": QColor(255, 255, 255, 28),
        "notch_gradient": (QColor(0, 180, 240, 240), QColor(10, 40, 160, 245), QColor(255, 0, 128, 240)),
        "eye_color": QColor(255, 255, 255),
    },
    "sunset_warm": {
        "name": "Sunset Horizon (Warm Amber) 🌇",
        "bg_top": QColor(28, 14, 22, 245),
        "bg_bottom": QColor(15, 8, 14, 252),
        "border": QColor(255, 130, 60, 90),
        "border_width": 1.0,
        "accent": QColor(255, 140, 60),
        "accent_glow": QColor(235, 40, 95, 40),
        "text_primary": QColor(255, 255, 255),
        "text_secondary": QColor(240, 180, 170),
        "badge_bg": QColor(60, 20, 35, 210),
        "btn_bg": QColor(255, 255, 255, 20),
        "btn_hover": QColor(255, 140, 60, 80),
        "eq_0": QColor(255, 130, 50),
        "eq_1": QColor(235, 40, 95),
        "accent_green": QColor(52, 199, 89),
        "card_bg": QColor(255, 255, 255, 16),
        "card_hover": QColor(255, 255, 255, 28),
        "notch_gradient": (QColor(255, 100, 45, 240), QColor(210, 35, 85, 245), QColor(135, 18, 120, 240)),
        "eye_color": QColor(255, 255, 255),
    },
    "frosted_crystal": {
        "name": "Frosted Crystal (Ultra Clear) 🫧",
        "bg_top": QColor(30, 35, 50, 150),
        "bg_bottom": QColor(15, 20, 32, 190),
        "border": QColor(255, 255, 255, 100),
        "border_width": 1.0,
        "accent": QColor(160, 235, 255),
        "accent_glow": QColor(255, 255, 255, 40),
        "text_primary": QColor(255, 255, 255),
        "text_secondary": QColor(215, 230, 245),
        "badge_bg": QColor(255, 255, 255, 30),
        "btn_bg": QColor(255, 255, 255, 30),
        "btn_hover": QColor(160, 235, 255, 80),
        "eq_0": QColor(255, 255, 255),
        "eq_1": QColor(160, 235, 255),
        "accent_green": QColor(52, 199, 89),
        "card_bg": QColor(255, 255, 255, 20),
        "card_hover": QColor(255, 255, 255, 35),
        "notch_gradient": (QColor(35, 45, 70, 220), QColor(18, 24, 40, 235)),
        "eye_color": QColor(255, 255, 255),
    },
    "frost_white": {
        "name": "Frost Titanium (Light Mode) ❄️",
        "bg_top": QColor(245, 247, 252, 235),
        "bg_bottom": QColor(225, 230, 240, 248),
        "border": QColor(0, 0, 0, 35),
        "border_width": 1.0,
        "accent": QColor(0, 122, 255),
        "accent_glow": QColor(0, 122, 255, 35),
        "text_primary": QColor(18, 20, 26),
        "text_secondary": QColor(105, 115, 130),
        "badge_bg": QColor(0, 0, 0, 18),
        "btn_bg": QColor(0, 0, 0, 16),
        "btn_hover": QColor(0, 122, 255, 40),
        "eq_0": QColor(0, 122, 255),
        "eq_1": QColor(88, 86, 214),
        "accent_green": QColor(52, 199, 89),
        "card_bg": QColor(0, 0, 0, 12),
        "card_hover": QColor(0, 0, 0, 22),
        "notch_gradient": (QColor(240, 244, 250, 240), QColor(220, 228, 240, 245)),
        "eye_color": QColor(25, 28, 38),
    }
}


ISLAND_AMBIENT_NAMES = {
    "adaptive_album": "🎨 Adaptive Album Art Aura",
    "aurora_borealis": "🌌 Aurora Borealis Flow",
    "neon_cyber_pulse": "⚡ Cyberpunk Neon Strobe",
    "sunset_chroma": "🌅 Synthwave Sunset Glow",
    "lava_fire_glow": "🔥 Inferno Magma Pulse",
    "rainbow_flow": "🌈 RGB Chroma Spectrum",
    "minimal_frost": "✨ Apple Minimal Frost",
}


# Nixi Notch Eye Colors (White, Blue, Green, Yellow, Orange, Pink, Purple)
NIXI_EYE_COLORS = {
    "white": ("Pure White ✨", QColor(255, 255, 255)),
    "blue": ("Cyber Sky Blue 🌊", QColor(56, 189, 248)),
    "green": ("Mint Emerald 🍀", QColor(74, 222, 128)),
    "yellow": ("Amber Sunlight ⚡", QColor(250, 204, 21)),
    "orange": ("Sunset Orange 🍊", QColor(251, 146, 60)),
    "pink": ("Neon Sakura 🌸", QColor(244, 114, 182)),
    "purple": ("Cosmic Violet 🔮", QColor(192, 132, 252)),
}


class VisionScanOverlay(QWidget):
    """
    Full-Screen Holographic Blue Laser Screen Scanner (Codex & Claude Computer Use style).
    Renders an unmistakable vibrant neon-cyan border glow around the entire display,
    a continuous ping-pong sweeping laser beam with luminous trailing veil,
    high-tech corner brackets, and precision target lock-on reticle.
    100% click-through (WS_EX_TRANSPARENT) and strictly HWND_TOPMOST over maximized windows.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
            | Qt.WindowType.WindowTransparentForInput
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)

        self._scan_y = 0.0
        self._scan_phase = 0.0      # 0.0 -> 1.0 (sweeping top to bottom)
        self._scan_dir = 1.0        # +1.0 down, -1.0 up
        self._sweep_count = 0
        self._is_active = False
        self._alpha = 0.0           # 0.0 -> 1.0 (smooth fade in/out)
        self._fading_out = False
        self._target_x = None
        self._target_y = None
        self._target_label = ""
        self._pulse_ring = 10.0
        self._hold_ticks = 0

        self._timer = QTimer(self)
        self._timer.setInterval(16) # ~60 FPS
        self._timer.timeout.connect(self._on_tick)

    def showEvent(self, event):
        super().showEvent(event)
        try:
            hwnd = int(self.winId())
            import ctypes
            user32 = ctypes.windll.user32
            GWL_EXSTYLE = -20
            WS_EX_LAYERED = 0x00080000
            WS_EX_TRANSPARENT = 0x00000020
            WS_EX_TOPMOST = 0x00000008
            cur_style = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
            user32.SetWindowLongW(hwnd, GWL_EXSTYLE, cur_style | WS_EX_LAYERED | WS_EX_TRANSPARENT | WS_EX_TOPMOST)
            user32.SetWindowPos(hwnd, -1, 0, 0, 0, 0, 0x0001 | 0x0002 | 0x0010 | 0x0040)
        except Exception:
            pass

    def trigger(self, target_x=None, target_y=None, label=""):
        """Triggers the full-screen holographic blue laser scan sweep."""
        screen = QApplication.primaryScreen()
        if screen:
            geom = screen.geometry()
            self.setGeometry(geom)
        else:
            self.setGeometry(0, 0, 1920, 1080)

        self._target_x = target_x
        self._target_y = target_y
        self._target_label = label or "Vision Processing"
        self._scan_phase = 0.0
        self._scan_dir = 1.0
        self._sweep_count = 0
        self._scan_y = 0.0
        self._alpha = 1.0
        self._fading_out = False
        self._pulse_ring = 12.0
        self._hold_ticks = 0
        self._is_active = True

        self.show()
        self.raise_()
        try:
            hwnd = int(self.winId())
            import ctypes
            ctypes.windll.user32.SetWindowPos(hwnd, -1, 0, 0, 0, 0, 0x0001 | 0x0002 | 0x0010 | 0x0040)
        except Exception:
            pass

        if not self._timer.isActive():
            self._timer.start(16)
        self.update()

    def _on_tick(self):
        if not self._is_active:
            self._timer.stop()
            self.hide()
            return

        if not self._fading_out:
            # Sweeps across screen in smooth ping-pong motion (~1.0s down, ~1.0s up)
            self._scan_phase += self._scan_dir * 0.016
            if self._scan_phase >= 1.0:
                self._scan_phase = 1.0
                self._scan_dir = -1.0
                self._sweep_count += 1
            elif self._scan_phase <= 0.0:
                self._scan_phase = 0.0
                self._scan_dir = 1.0
                self._sweep_count += 1

            self._scan_y = self._scan_phase * self.height()
            if self._target_x is not None:
                self._pulse_ring += 1.5

            # Run at least 3 full sweeps (~3.5 seconds) so user clearly perceives the Claude/Codex blue laser aura
            if self._sweep_count >= 3:
                self._hold_ticks += 1
                if self._hold_ticks > 25:
                    self._fading_out = True
        else:
            self._alpha -= 0.05
            if self._alpha <= 0.02:
                self._alpha = 0.0
                self._is_active = False
                self._timer.stop()
                self.hide()

        self.update()

    def paintEvent(self, event):
        if not self._is_active or self._alpha <= 0.01:
            return

        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        w, h = self.width(), self.height()
        a = self._alpha

        # 1. Subtle holographic dark-blue tint over the scanned area
        p.fillRect(0, 0, w, h, QColor(0, 15, 30, int(22 * a)))

        # 2. Signature Codex/Claude Glowing Blue Screen Perimeter Border (All 4 Edges)
        glow_size = 32.0
        # Top edge glow
        g_top = QLinearGradient(0, 0, 0, glow_size)
        g_top.setColorAt(0.0, QColor(0, 240, 255, int(180 * a)))
        g_top.setColorAt(0.4, QColor(0, 180, 255, int(90 * a)))
        g_top.setColorAt(1.0, QColor(0, 140, 255, 0))
        p.fillRect(QRectF(0, 0, w, glow_size), g_top)

        # Bottom edge glow
        g_bot = QLinearGradient(0, h, 0, h - glow_size)
        g_bot.setColorAt(0.0, QColor(0, 240, 255, int(180 * a)))
        g_bot.setColorAt(0.4, QColor(0, 180, 255, int(90 * a)))
        g_bot.setColorAt(1.0, QColor(0, 140, 255, 0))
        p.fillRect(QRectF(0, h - glow_size, w, glow_size), g_bot)

        # Left edge glow
        g_left = QLinearGradient(0, 0, glow_size, 0)
        g_left.setColorAt(0.0, QColor(0, 240, 255, int(180 * a)))
        g_left.setColorAt(0.4, QColor(0, 180, 255, int(90 * a)))
        g_left.setColorAt(1.0, QColor(0, 140, 255, 0))
        p.fillRect(QRectF(0, 0, glow_size, h), g_left)

        # Right edge glow
        g_right = QLinearGradient(w, 0, w - glow_size, 0)
        g_right.setColorAt(0.0, QColor(0, 240, 255, int(180 * a)))
        g_right.setColorAt(0.4, QColor(0, 180, 255, int(90 * a)))
        g_right.setColorAt(1.0, QColor(0, 140, 255, 0))
        p.fillRect(QRectF(w - glow_size, 0, glow_size, h), g_right)

        # Crisp outer perimeter stroke
        p.setPen(QPen(QColor(0, 245, 255, int(220 * a)), 3.0))
        p.drawRect(QRectF(1.5, 1.5, w - 3.0, h - 3.0))

        # 3. Sweeping Laser Beam & Gradient Trail (Codex / Claude blue light)
        trail_h = 160.0
        if self._scan_dir >= 0:
            top_y = max(0.0, self._scan_y - trail_h)
            grad = QLinearGradient(0, top_y, 0, self._scan_y)
            grad.setColorAt(0.0, QColor(0, 160, 255, 0))
            grad.setColorAt(0.65, QColor(0, 210, 255, int(45 * a)))
            grad.setColorAt(1.0, QColor(0, 245, 255, int(120 * a)))
            p.fillRect(QRectF(0, top_y, w, self._scan_y - top_y), grad)
        else:
            bot_y = min(float(h), self._scan_y + trail_h)
            grad = QLinearGradient(0, bot_y, 0, self._scan_y)
            grad.setColorAt(0.0, QColor(0, 160, 255, 0))
            grad.setColorAt(0.65, QColor(0, 210, 255, int(45 * a)))
            grad.setColorAt(1.0, QColor(0, 245, 255, int(120 * a)))
            p.fillRect(QRectF(0, self._scan_y, w, bot_y - self._scan_y), grad)

        # High-intensity White-Blue Laser Core Beam Line
        p.setPen(QPen(QColor(0, 220, 255, int(200 * a)), 7.0))
        p.drawLine(0, int(self._scan_y), w, int(self._scan_y))

        p.setPen(QPen(QColor(180, 245, 255, int(240 * a)), 3.5))
        p.drawLine(0, int(self._scan_y), w, int(self._scan_y))

        p.setPen(QPen(QColor(255, 255, 255, int(255 * a)), 1.5))
        p.drawLine(0, int(self._scan_y), w, int(self._scan_y))

        # 4. Holographic Tech Corner Brackets
        p.setPen(QPen(QColor(0, 240, 255, int(220 * a)), 3.0))
        b_len = 42.0
        m = 24.0
        p.drawLine(int(m), int(m), int(m + b_len), int(m))
        p.drawLine(int(m), int(m), int(m), int(m + b_len))
        p.drawLine(int(w - m - b_len), int(m), int(w - m), int(m))
        p.drawLine(int(w - m), int(m), int(w - m), int(m + b_len))
        p.drawLine(int(m), int(h - m), int(m + b_len), int(h - m))
        p.drawLine(int(m), int(h - m - b_len), int(m), int(h - m))
        p.drawLine(int(w - m - b_len), int(h - m), int(w - m), int(h - m))
        p.drawLine(int(w - m), int(h - m - b_len), int(w - m), int(h - m))

        # 5. Top Telemetry Banner
        p.setFont(QFont("Consolas", 10, QFont.Weight.Bold))
        banner_text = f"[ ⦿ JARVIS AI VISION COPILOT • {w}x{h} • {self._target_label.upper()} ]"
        p.fillRect(QRectF(w / 2 - 220, 28, 440, 28), QColor(0, 20, 35, int(200 * a)))
        p.setPen(QPen(QColor(0, 240, 255, int(160 * a)), 1.0))
        p.drawRect(QRectF(w / 2 - 220, 28, 440, 28))
        p.setPen(QPen(QColor(0, 245, 255, int(240 * a))))
        p.drawText(QRectF(w / 2 - 220, 28, 440, 28), Qt.AlignmentFlag.AlignCenter, banner_text)

        # 6. Targeted Lock-On Reticle & Pulsing Ripple
        if self._target_x is not None and self._target_y is not None:
            tx, ty = self._target_x, self._target_y
            box_r = 38.0
            p.setPen(QPen(QColor(0, 240, 255, int(230 * a)), 2.0))
            p.setBrush(Qt.BrushStyle.NoBrush)
            c_len = 12.0
            p.drawLine(int(tx - box_r), int(ty - box_r), int(tx - box_r + c_len), int(ty - box_r))
            p.drawLine(int(tx - box_r), int(ty - box_r), int(tx - box_r), int(ty - box_r + c_len))
            p.drawLine(int(tx + box_r - c_len), int(ty - box_r), int(tx + box_r), int(ty - box_r))
            p.drawLine(int(tx + box_r), int(ty - box_r), int(tx + box_r), int(ty - box_r + c_len))
            p.drawLine(int(tx - box_r), int(ty + box_r), int(tx - box_r + c_len), int(ty + box_r))
            p.drawLine(int(tx - box_r), int(ty + box_r - c_len), int(tx - box_r), int(ty + box_r))
            p.drawLine(int(tx + box_r - c_len), int(ty + box_r), int(tx + box_r), int(ty + box_r))
            p.drawLine(int(tx + box_r), int(ty + box_r - c_len), int(tx + box_r), int(ty + box_r))

            p.setPen(QPen(QColor(0, 255, 255, int(240 * a)), 1.5))
            p.drawEllipse(QPointF(tx, ty), 6.0, 6.0)
            
            r1 = (self._pulse_ring % 35) + 8
            r2 = ((self._pulse_ring + 18) % 35) + 8
            p.setPen(QPen(QColor(0, 240, 255, int(150 * (1.0 - r1 / 45.0) * a)), 1.5))
            p.drawEllipse(QPointF(tx, ty), r1, r1)
            p.setPen(QPen(QColor(0, 240, 255, int(150 * (1.0 - r2 / 45.0) * a)), 1.5))
            p.drawEllipse(QPointF(tx, ty), r2, r2)

            p.setFont(QFont("Consolas", 9, QFont.Weight.Bold))
            label_tag = f"● LOCKED: {self._target_label[:24]}"
            tag_w = len(label_tag) * 8 + 16
            p.fillRect(QRectF(tx - tag_w / 2, ty + box_r + 6, tag_w, 20), QColor(0, 20, 35, int(210 * a)))
            p.setPen(QPen(QColor(0, 240, 255, int(160 * a)), 1.0))
            p.drawRect(QRectF(tx - tag_w / 2, ty + box_r + 6, tag_w, 20))
            p.setPen(QColor(0, 255, 255, int(250 * a)))
            p.drawText(QRectF(tx - tag_w / 2, ty + box_r + 6, tag_w, 20), Qt.AlignmentFlag.AlignCenter, label_tag)


class WindowsNotificationWatcher(QThread):
    """
    Lightweight background watcher for Windows 10/11 system notifications & toasts
    (WhatsApp, Discord, Telegram, Calendar, Outlook, etc.) using the native WinRT
    UserNotificationListener API. Operates with 0% idle CPU and minimal RAM footprint.
    """
    notification_received = Signal(str, str, str)  # app_name, title, body

    def __init__(self, parent=None):
        super().__init__(parent)
        self._running = True
        self._seen_ids = set()

    def run(self):
        try:
            import winsdk.windows.ui.notifications as notifs
            import winsdk.windows.ui.notifications.management as mgmt
            listener = mgmt.UserNotificationListener.current
            try:
                # 1 = UserNotificationListenerAccessStatus.ALLOWED
                if listener.get_access_status() != 1:
                    return
            except Exception:
                pass

            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            async def _fetch():
                try:
                    return await listener.get_notifications_async(notifs.NotificationKinds.TOAST)
                except Exception:
                    return []

            # Populate initial seen IDs so stale historical notifications are not spammed on boot
            try:
                initial = loop.run_until_complete(_fetch())
                for it in initial:
                    self._seen_ids.add(it.id)
            except Exception:
                pass

            while self._running:
                try:
                    items = loop.run_until_complete(_fetch())
                    for it in items:
                        if it.id not in self._seen_ids:
                            self._seen_ids.add(it.id)
                            app_name = "Notification"
                            try:
                                if it.app_info and it.app_info.display_info:
                                    app_name = it.app_info.display_info.display_name or "Notification"
                            except Exception:
                                pass

                            title = ""
                            body = ""
                            try:
                                bindings = it.notification.visual.get_binding(notifs.KnownNotificationBindings.TOAST_GENERIC)
                                if bindings:
                                    texts = [t.text for t in bindings.get_text_elements()]
                                    if len(texts) > 0:
                                        title = texts[0]
                                    if len(texts) > 1:
                                        body = " ".join(texts[1:])
                            except Exception:
                                pass

                            if title or body:
                                self.notification_received.emit(app_name, title, body)
                except Exception:
                    pass
                time.sleep(1.0)
        except Exception:
            pass

    def stop(self):
        self._running = False


class OriginIsland(QWidget):
    """
    OriginOS & Apple Dynamic Island Widget for Desktop.
    Features live music equalizer/controls, real-time weather & precision digital clock,
    smart clipboard manager with one-click URL opening & web searching, and fluid shape-morphing physics.
    """

    # Island States
    STATE_COMPACT = "compact"
    STATE_ASSISTANT = "assistant"
    STATE_MUSIC = "music"
    STATE_WEATHER = "weather"
    STATE_CONTROL = "control"
    STATE_CALENDAR = "calendar"
    STATE_SHELF = "shelf"
    STATE_MAP = "map"
    STATE_CLIPBOARD = "clipboard"
    STATE_TOOLS = "tools"
    STATE_NOTIFICATION = "notification"

    # Size configurations
    SIZES = {
        STATE_COMPACT: (235, 40),
        STATE_ASSISTANT: (430, 260),
        STATE_MUSIC: (420, 204),
        STATE_WEATHER: (420, 192),
        STATE_CONTROL: (420, 288),
        STATE_CALENDAR: (420, 192),
        STATE_SHELF: (420, 192),
        STATE_MAP: (400, 150),
        STATE_CLIPBOARD: (400, 150),
        STATE_TOOLS: (420, 192),
        STATE_NOTIFICATION: (420, 80),
    }

    def __init__(self, settings=None, parent=None):
        super().__init__(parent)
        self._settings = settings

        # Window styling: Frameless, transparent background, top-level overlay
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)
        self.setMouseTracking(True)

        # State management & OriginOS Spring Physics Engine
        self._state = self.STATE_COMPACT
        self._prev_state = self.STATE_COMPACT
        self._current_w, self._current_h = self.SIZES[self.STATE_COMPACT]
        self._target_w, self._target_h = float(self._current_w), float(self._current_h)
        self._anim_w, self._anim_h = float(self._current_w), float(self._current_h)
        self._vel_w, self._vel_h = 0.0, 0.0
        self._is_morphing = False
        self._morph_progress = 0.0  # 0.0 (compact pill) -> 1.0 (expanded squircle card)
        self._corner_radius = 19.0
        self._last_tick_time = time.monotonic()

        # OriginOS Sliding Tab Indicator & Fluid Squash-and-Stretch
        self._tab_from = "music"
        self._tab_to = "music"
        self._tab_transition_progress = 1.0
        self._indicator_x = float(self.SIZES[self.STATE_MUSIC][0] - 194 - 6)
        self._indicator_target_x = self._indicator_x
        self._indicator_vel = 0.0
        self._indicator_w = 22.0
        self._indicator_w_vel = 0.0

        # Tactile Micro-Interactions: Button Hover Glow & Elastic Press Bounce
        self._hovered_btn: Optional[str] = None
        self._btn_hover_anim: Dict[str, float] = {}
        self._btn_press_anim: Dict[str, float] = {}

        # OriginOS Animated Drop-Down Volume HUD & Toast Banner
        self._volume_hud_y = -32.0
        self._anim_volume_level = 50.0
        self._toast_y = -30.0

        # Magnetic Notch Snap Flight Physics
        self._is_snapping_to_notch = False

        # Interactive Edge Dragging / Resizing & Fullscreen Theater Mode
        self._is_edge_resizing: bool = False
        self._resize_edge: Optional[str] = None
        self._resize_start_pos: QPoint = QPoint()
        self._resize_start_size: QSize = QSize()
        self._is_theater_mode: bool = False
        self._theater_lyrics_rects: Dict[int, QRect] = {}
        self._theater_ctrl_y: int = 0
        self._theater_bar_y: int = 0
        self._snap_target_x = 0.0
        self._snap_target_y = 0.0
        self._snap_vel_x = 0.0
        self._snap_vel_y = 0.0

        self._theme_key = "bloom_dark"
        if settings and hasattr(settings, "island_style"):
            self._theme_key = settings.island_style or "bloom_dark"
        if self._theme_key not in ISLAND_THEMES:
            self._theme_key = "bloom_dark"

        self._position_mode = "top_notch"
        if settings and hasattr(settings, "island_position"):
            self._position_mode = settings.island_position or "top_notch"

        # Bloom Notch & Control Center State
        self._dock_mode = "Fixed"
        if settings and hasattr(settings, "dock_mode"):
            self._dock_mode = settings.get("dock_mode", "Fixed")
        self._notch_mode = "Fixed"
        if settings and hasattr(settings, "notch_mode"):
            self._notch_mode = settings.get("notch_mode", "Fixed")
        self._notch_style = "flush_notch"
        if settings and hasattr(settings, "notch_style"):
            self._notch_style = settings.get("notch_style", "flush_notch")
        self._background_opacity = 80
        if settings and hasattr(settings, "background_opacity"):
            self._background_opacity = int(settings.get("background_opacity", 80))

        # Battery & Sliders State (Control Center)
        self._battery_percent = 75
        self._battery_plugged = True
        self._last_battery_check = 0.0
        self._control_volume = _win_get_system_volume()
        self._control_brightness = 50.0
        self._is_dragging_volume = False
        self._is_dragging_brightness = False
        self._dark_mode_active = True
        self._eco_mode_active = False
        self._dnd_active = False
        self._wifi_connected = _win_get_internet_connected()
        self._wifi_name = "Wi-Fi"

        # Focus / Pomodoro Timer & Calendar State
        self._pomo_duration_sec = 25 * 60.0
        self._pomo_time_left_sec = 25 * 60.0
        self._pomo_is_running = False
        self._pomo_preset = 25

        # Media service
        self._media = MediaService.get_instance()
        self._media.add_listener(self._on_media_listener_callback)
        self._last_media_info = self._media.current_info

        # Weather service
        self._weather = WeatherService.get_instance()
        if settings and hasattr(settings, "weather_location") and settings.weather_location:
            self._weather.set_location(settings.weather_location)
        self._weather.add_listener(self._on_weather_listener_callback)
        self._last_weather_info = self._weather.current_weather

        # Bluetooth service
        self._bluetooth = BluetoothService.get_instance()
        self._bluetooth.add_listener(self._on_bluetooth_updated)
        self._last_bluetooth_info = self._bluetooth.current_info

        # Taskbar Styling Service (Clear Glass, Acrylic, Blur, OLED, Default)
        try:
            from taskbar_service import TaskbarService
            self._taskbar_service = TaskbarService.get_instance()
            self._taskbar_service.start_watchdog()
        except Exception:
            self._taskbar_service = None

        # Smart Clipboard Tracking & History
        self._last_clipboard_text = ""
        self._clipboard_preview_text = ""
        self._clipboard_word_count = 0
        self._clipboard_char_count = 0
        self._last_clipboard_url: Optional[str] = None
        self._clipboard_color_hex: Optional[str] = None
        self._clipboard_calc_result: Optional[str] = None
        self._clipboard_history: list = []
        self._clipboard_copy_feedback = 0.0
        self._clipboard_banner_time = 0.0
        self._last_clipboard_change_time = 0.0
        self._clipboard = QApplication.clipboard()
        self._clipboard.dataChanged.connect(self._on_clipboard_changed)

        # System Performance Monitoring (CPU & RAM)
        self._last_cpu_percent = 0.0
        self._last_ram_percent = 0.0
        self._last_sys_check_time = 0.0

        # Real-Time Network Speedometer (Download & Upload)
        self._last_net_bytes_recv = 0
        self._last_net_bytes_sent = 0
        self._last_net_check_time = 0.0
        self._net_down_bps = 0.0
        self._net_up_bps = 0.0
        self._net_down_str = "0 B/s"
        self._net_up_str = "0 B/s"

        # OriginOS Aesthetics & Customization
        self._wave_style = "sine"  # "sine" (Android 13), "harmonic" (Liquid Ribbon), "cyber" (Neon Pulse)
        if settings and hasattr(settings, "get") and settings.get("wave_style"):
            self._wave_style = settings.get("wave_style", "sine")

        self._compact_idle_mode = "eyes"  # "eyes", "network", "weather", "vitals"
        if settings and hasattr(settings, "get") and settings.get("compact_idle_mode"):
            self._compact_idle_mode = settings.get("compact_idle_mode", "eyes")

        self._accent_theme_key = "adaptive"  # "adaptive", "cyberpunk", "tokyo", "gold", "emerald", "crimson"
        if settings and hasattr(settings, "get") and settings.get("accent_theme"):
            self._accent_theme_key = settings.get("accent_theme", "adaptive")

        self._scratchpad_path = Path(__file__).parent / "scratchpad.txt"
        self._scratchpad_text = ""
        try:
            if self._scratchpad_path.exists():
                self._scratchpad_text = self._scratchpad_path.read_text(encoding="utf-8")
        except Exception:
            pass

        # Interactive Volume HUD Overlay State
        self._volume_hud_time = 0.0
        self._volume_hud_action = "+"
        self._volume_hud_level = 50

        # Equalizer & ticker state
        self._eq_bars = [0.3, 0.6, 0.9, 0.5, 0.8, 0.4]
        self._dynamic_accent_color = QColor(240, 181, 166)
        self._last_audio_peak = 0.0
        self._ticker_offset = 0
        self._is_hovered = False
        self._pinned = False
        self._last_expanded_tab = self.STATE_MUSIC
        self._compact_ticker_x = 0.0
        self._music_ticker_x = 0.0
        self._compact_ticker_pause = 1.5
        self._music_ticker_pause = 1.5
        self._compact_lyric_ticker_x = 0.0
        self._compact_lyric_pause = 1.0
        self._compact_lyric_last_idx = -1
        self._marquee_pixmap_cache: Dict[tuple, tuple] = {}
        self._anim_cpu = 15.0
        self._anim_ram = 45.0
        self._collapse_timer = QTimer(self)
        self._collapse_timer.setSingleShot(True)
        self._collapse_timer.timeout.connect(self._auto_collapse)

        # Retracted small trigger icon mode & auto-retract timer
        self._is_retracted = False
        self._auto_retract = True
        if settings and hasattr(settings, "island_auto_retract"):
            self._auto_retract = bool(settings.island_auto_retract)
        self._retract_timer = QTimer(self)
        self._retract_timer.setSingleShot(True)
        self._retract_timer.timeout.connect(self._auto_retract_timeout)

        # Ambient Light & Music Beat Flow Engine
        self._ambient_style = "adaptive_album"
        if settings and hasattr(settings, "island_ambient_style"):
            self._ambient_style = settings.island_ambient_style or "adaptive_album"
        self._ambient_hue = 210.0
        self._ambient_color_current = QColor(0, 122, 255)
        self._ambient_color_secondary = QColor(168, 85, 247)
        self._ambient_beat_energy = 0.0
        self._extracted_art_color: Optional[QColor] = None
        self._last_thumb_len: int = 0
        self._ambient_toast_time = 0.0
        self._ambient_toast_name = ""

        # Ambient Inferno Magma Embers (for lava_fire_glow)
        self._lava_embers = [
            {"x": random.uniform(20, 370), "y": random.uniform(80, 150), "speed": random.uniform(0.7, 2.2), "r": random.uniform(1.2, 2.8), "alpha": random.uniform(0.35, 0.95)}
            for _ in range(22)
        ]

        # Precision Compass & Live Navigation Engine
        self._compass_heading = 0.0
        self._compass_current_heading = 0.0
        self._compass_mode = "drift"  # "drift", "mouse", "north"
        self._compass_calibrated = True

        # Live Google Maps & Route Navigation Simulator
        self._map_view_mode = "split"  # "split" (Compass + Live Map) or "panoramic" (Full Route View)
        self._compass_left_view = "compass"  # "compass" or "turn_hud"
        self._nav_progress = 0.0  # 0.0 to 1.0 along the route path
        self._nav_speed = 0.0035  # simulation movement speed per frame
        self._traffic_enabled = True

        # Interactive Media Progress State
        self._playback_pos_sec = 0.0
        self._playback_dur_sec = 214.0  # ~3:34 min default track duration
        self._is_scrubbing = False
        self._last_played_title = ""

        # Procedural Weather Physics Particles (60 FPS Vector Animation Engine)
        self._anim_time = 0.0
        # 1. Rain & Splashes
        self._rain_drops = [
            {"x": random.uniform(0, 150), "y": random.uniform(0, 108), "speed": random.uniform(4.5, 8.0), "len": random.uniform(6, 12), "alpha": random.uniform(0.4, 0.95)}
            for _ in range(35)
        ]
        self._rain_splashes = []
        # 2. Snowflakes
        self._snow_flakes = [
            {"x": random.uniform(0, 150), "y": random.uniform(0, 108), "speed": random.uniform(0.6, 1.8), "r": random.uniform(1.2, 2.6), "phase": random.uniform(0, 6.28), "alpha": random.uniform(0.4, 0.95)}
            for _ in range(30)
        ]
        # 3. Wind Ribbons & Breeze Particles
        self._wind_particles = [
            {"x": random.uniform(0, 150), "y": random.uniform(10, 98), "speed": random.uniform(2.5, 5.0), "size": random.uniform(1.5, 3.0), "alpha": random.uniform(0.3, 0.8)}
            for _ in range(16)
        ]
        # 4. Heat / Hot Embers & Shimmer
        self._heat_embers = [
            {"x": random.uniform(10, 140), "y": random.uniform(20, 108), "speed": random.uniform(0.8, 2.0), "r": random.uniform(1.0, 2.5), "phase": random.uniform(0, 6.28), "alpha": random.uniform(0.3, 0.85)}
            for _ in range(18)
        ]
        # 5. Thunder Lightning state
        self._lightning_flash = 0.0
        self._lightning_timer = 0
        self._lightning_bolt_pts = []
        # 6. Night Stars
        self._night_stars = [
            {"x": random.uniform(10, 140), "y": random.uniform(10, 100), "r": random.uniform(1.0, 2.2), "freq": random.uniform(1.5, 4.0), "phase": random.uniform(0, 6.28)}
            for _ in range(18)
        ]
        # 7. Cloud Drift Layers
        self._cloud_drift = [0.0, 40.0, 90.0]

        # Drag tracking
        self._is_dragging = False
        self._drag_start = QPoint()

        # "Drop it on the Shelf" System (Screenshot 2)
        self.setAcceptDrops(True)
        self._shelf_files: List[Dict[str, Any]] = []
        self._shelf_page: int = 0
        self._shelf_is_drag_over: bool = False
        self._shelf_pressed_file_idx: Optional[int] = None
        self._shelf_drag_start_pos: Optional[QPoint] = None
        self._shelf_item_rects: Dict[int, QRect] = {}

        # Phone Link & Drop Service (Instant QR Code Phone Sync)
        self._phone_qr_visible: bool = False
        self._phone_drop_service = PhoneDropService.get_instance()
        self._phone_drop_service.cb_file_received = self._on_phone_file_received
        self._phone_drop_service.cb_clipboard_received = self._on_phone_clipboard_received
        self._phone_drop_service.cb_url_received = self._on_phone_url_received
        self._phone_drop_service.cb_command_received = self._on_phone_command_received
        self._phone_drop_service.cb_get_status = self._get_phone_status_data
        self._phone_drop_service.cb_get_cover_bytes = self._get_phone_cover_bytes
        self._phone_drop_service.cb_get_lyrics = self._get_phone_lyrics_data
        self._phone_drop_service.cb_jarvis_query = self._run_assistant_task
        self._phone_battery_info: Dict[str, Any] = {}
        self._phone_fully_charged_notified: bool = False
        self._phone_low_battery_notified: bool = False
        self._phone_drop_service.cb_phone_battery = self._on_phone_battery_updated
        try:
            self._phone_drop_service.start()
        except Exception as _e:
            print(f"[OriginIsland] Warning starting PhoneDropService: {_e}")

        # Windows Notification Hub (WhatsApp, Discord, Telegram, Calendar, etc.)
        self._current_notification: Optional[Dict[str, Any]] = None
        self._notification_dismiss_timer = QTimer(self)
        self._notification_dismiss_timer.setSingleShot(True)
        self._notification_dismiss_timer.timeout.connect(self._auto_dismiss_notification)

        self._notif_watcher: Optional[WindowsNotificationWatcher] = None
        try:
            self._notif_watcher = WindowsNotificationWatcher(self)
            self._notif_watcher.notification_received.connect(self.show_notification)
            self._notif_watcher.start()
        except Exception as _e:
            print(f"[OriginIsland] Warning starting WindowsNotificationWatcher: {_e}")

        # Full-Screen Holographic Blue Laser Scanner Overlay (Codex & Claude style)
        self._vision_overlay = VisionScanOverlay()
        try:
            from control import vision
            vision.set_scan_overlay_callback(self.trigger_vision_scan)
        except Exception:
            pass

        # Animated Pet Eyes in Compact Notch (Screenshots 1 & 3)
        self._compact_mode: str = "auto"       # "auto" (songs when playing, pet eyes when idle), "pet_eyes", "song"
        self._pet_eye_state: str = "idle"     # "idle", "smiling", "blinking", "drowsy", "winking"
        self._pet_eye_blink_phase: float = 0.0
        self._pet_eye_blink_timer: float = random.uniform(2.5, 4.5)
        self._pet_eye_glance_x: float = 0.0
        self._pet_eye_glance_y: float = 0.0
        self._pet_eye_glance_target_x: float = 0.0
        self._pet_eye_glance_target_y: float = 0.0
        self._pet_eye_glance_timer: float = random.uniform(1.8, 3.2)
        self._pet_eye_cursor_glance_x: float = 0.0
        self._pet_eye_cursor_glance_y: float = 0.0
        self._pet_eye_cursor_target_x: float = 0.0
        self._pet_eye_cursor_target_y: float = 0.0
        self._last_cursor_move_time: float = 0.0
        self._pet_eye_wink_timer: float = random.uniform(7.0, 14.0)
        self._pet_eye_wink_phase: float = 0.0
        self._pet_eye_wink_which: str = "left"
        self._pet_eye_drowse_level: float = 0.0
        self._pet_eye_alert_phase: float = 0.0
        self._last_user_activity_time: float = time.monotonic()
        self._last_cursor_pos: QPoint = QPoint(0, 0)

        # Rich Pet Emotion & Particle Engine
        self._pet_emotion: str = "idle"        # "idle", "love", "happy", "surprised", "angry", "sad"
        self._pet_emotion_timer: float = 0.0
        self._pet_emotion_cycle: List[str] = ["love", "surprised", "happy", "sad", "angry"]
        self._pet_emotion_idx: int = 0
        self._pet_particles: List[Dict[str, Any]] = []
        self._pet_blush_alpha: float = 0.0
        self._pet_bounce_y: float = 0.0
        self._pet_bounce_vel: float = 0.0
        self._pet_last_click_time: float = 0.0

        # Real-time Synced Karaoke Lyrics System (False by default -> shows song details; True -> shows synced lyrics)
        self._music_show_lyrics: bool = bool(settings.get("compact_show_lyrics", False)) if (settings and hasattr(settings, "get")) else False
        self._lyrics_lines: List[Tuple[float, str]] = []
        self._lyrics_cache_key: str = ""
        self._lyrics_active_idx: int = 0
        self._lyrics_scroll_y: float = 0.0
        self._lyrics_item_rects: Dict[int, QRect] = {}
        self._lyrics_offset_sec: float = 0.0

        # Nixi Features (7 Eye Colors, RGBA Custom Color Picker, Water Logger, Keep Awake, Stopwatch, Windows Popups)
        self._eye_color_key: str = "white"
        self._custom_eye_color: Optional[QColor] = None
        if settings and hasattr(settings, "get"):
            c_str = settings.get("island_eye_color", None)
            if c_str:
                col = parse_rgba_color(c_str)
                if col.isValid():
                    self._custom_eye_color = col
        self._water_glasses_today: int = 3
        self._water_goal: int = 8
        self._keep_awake_active: bool = False
        self._keep_awake_end_time: float = 0.0
        self._stopwatch_running: bool = False
        self._stopwatch_elapsed: float = 0.0
        self._stopwatch_last_tick: float = time.monotonic()
        self._last_caps_lock_state: int = -1
        self._last_num_lock_state: int = -1
        self._cal_month_offset: int = 0
        self._sys_hud_toast_type: str = ""
        self._sys_hud_toast_text: str = ""
        self._sys_hud_toast_time: float = 0.0
        self._sys_hud_toast_val: int = 0
        self._sys_hud_toast_icon: str = ""
        self._sys_hud_toast_data: str = ""
        self._last_system_volume: float = _win_get_system_volume()
        self._last_vol_poll_time: float = 0.0
        self._last_power_plugged: Optional[bool] = None
        self._last_batt_poll_time: float = 0.0
        self._known_disks: set = set()
        self._last_disk_poll_time: float = 0.0
        self._voice_output_enabled: bool = True

        # JARVIS Core AI Assistant & Windows Automation System
        self._assistant_query = ""
        self._assistant_reply = "Hello! I am JARVIS. Ask a task, dictate, or type below."
        self._assistant_typewriter_idx = len(self._assistant_reply)
        self._assistant_status = "Ready"
        self._assistant_status_detail = "Ready"
        self._assistant_tool_action = ""
        self._assistant_history: List[Dict[str, str]] = []
        self._is_jarvis_talking = False
        self._live_jarvis_speech = ""
        self._jarvis_speech_time = 0.0
        self._is_voice_listening = False
        self._jarvis_compact_ticker_x = 0.0

        # Embedded JARVIS Chat Input Box (Styled glassmorphic QLineEdit matching active Island theme)
        self._chat_input = QLineEdit(self)
        self._chat_input.setPlaceholderText("Ask JARVIS or type task... (Enter to run)")
        self._chat_input.returnPressed.connect(self._on_assistant_submit)
        self._chat_input.textChanged.connect(lambda: self._wake_timer())
        self._update_chat_input_theme()
        self._chat_input.hide()

        # Render loop (OriginOS 60 FPS ultra-smooth physics, throttles to 1s when idle)
        self._timer = QTimer(self)
        self._timer.setTimerType(Qt.TimerType.PreciseTimer)
        self._timer.setInterval(16)
        self._timer.timeout.connect(self._render_tick)
        self._timer.start()

        # Initial geometry setup
        self._reposition()
        self.resize(self._current_w, self._current_h)

        # Check initial clipboard
        self._check_initial_clipboard()

    # ── Geometry & Morphing Physics ──────────────────────────────────────────

    def _reposition(self):
        screen = QGuiApplication.primaryScreen()
        if not screen:
            return
        geo = screen.geometry()

        if self._position_mode == "top_notch":
            target_x = geo.x() + (geo.width() - self._current_w) // 2
            target_y = geo.y()  # Hang directly flush from the top screen bezel (y = 0)
            self.move(target_x, target_y)
        elif self._position_mode == "follow_pet":
            pass  # Position updated by pet instance
        # "floating" keeps its current position

    def set_notch_style(self, style: str):
        self._notch_style = style
        if self._settings:
            self._settings.notch_style = style
            self._settings.save()
        self._reposition()
        self.update()



    @staticmethod
    def _format_net_speed(bps: float) -> str:
        if bps >= 1048576.0 * 10.0:
            return f"{bps / 1048576.0:.1f} M/s"
        elif bps >= 1048576.0:
            return f"{bps / 1048576.0:.1f} M/s"
        elif bps >= 1024.0:
            return f"{bps / 1024.0:.0f} K/s"
        else:
            return f"{bps:.0f} B/s"

    def _get_active_accent_color(self) -> QColor:
        theme_key = getattr(self, "_accent_theme_key", "adaptive")
        presets = {
            "cyberpunk": QColor(0, 240, 255),
            "tokyo": QColor(168, 85, 247),
            "gold": QColor(245, 158, 11),
            "emerald": QColor(16, 185, 129),
            "crimson": QColor(239, 68, 68),
        }
        if theme_key in presets:
            return presets[theme_key]
        return getattr(self, "_dynamic_accent_color", QColor(240, 181, 166))

    def _get_background_color(self) -> QColor:
        """Returns the background color modulated by the user's background_opacity setting (20% to 100%)."""
        alpha = int(255 * (getattr(self, "_background_opacity", 100) / 100.0))
        return QColor(0, 0, 0, max(25, min(255, alpha)))

    def set_background_opacity(self, opacity: int):
        self._background_opacity = max(20, min(100, int(opacity)))
        if self._settings:
            self._settings.set("background_opacity", self._background_opacity, save_now=True)
        self._ambient_toast_time = time.monotonic()
        if self._background_opacity >= 95:
            self._ambient_toast_name = "Island Opacity: 100% Solid AMOLED 🖤"
        elif self._background_opacity >= 75:
            self._ambient_toast_name = f"Island Opacity: {self._background_opacity}% Frosted Glass ✨"
        elif self._background_opacity >= 55:
            self._ambient_toast_name = f"Island Opacity: {self._background_opacity}% Translucent 🌫️"
        else:
            self._ambient_toast_name = f"Island Opacity: {self._background_opacity}% Ultra Clear 💎"
        self._wake_timer()
        self.update()

    def cycle_background_opacity(self):
        presets = [100, 85, 65, 45, 25]
        cur = getattr(self, "_background_opacity", 100)
        nxt = 100
        for p in presets:
            if cur > p:
                nxt = p
                break
        else:
            nxt = presets[0]
        self.set_background_opacity(nxt)
        return nxt



    def set_pet_anchor(self, pet_x: int, pet_y: int, pet_size: int):
        if self._position_mode == "follow_pet":
            target_x = pet_x + (pet_size - self._current_w) // 2
            target_y = max(10, pet_y - self._current_h - 12)
            self.move(target_x, target_y)

    def _update_chat_input_theme(self, theme: Optional[dict] = None):
        """Dynamically styles the embedded chat input box with a sleek, premium dark aesthetic."""
        if not hasattr(self, "_chat_input") or not self._chat_input:
            return
        if not theme:
            theme = ISLAND_THEMES.get(getattr(self, "_theme_key", "apple_dynamic"), ISLAND_THEMES["apple_dynamic"])
        accent = theme.get("accent", QColor(0, 240, 255))
        ar, ag, ab = accent.red(), accent.green(), accent.blue()

        is_light_theme = getattr(self, "_theme_key", "") == "frost_white"
        if is_light_theme:
            bg_normal = "rgba(240, 243, 248, 0.95)"
            bg_focus = "#ffffff"
            border_normal = "rgba(0, 0, 0, 0.16)"
            border_focus = f"rgb({ar}, {ag}, {ab})"
            text_col = "#0f172a"
            ph_col = "#64748b"
        else:
            # Deep sleek obsidian glass with neon cyan / accent border
            bg_normal = "rgba(10, 14, 22, 0.92)"
            bg_focus = "rgba(14, 18, 28, 0.98)"
            border_normal = f"rgba({ar}, {ag}, {ab}, 120)" if (ar, ag, ab) != (255, 255, 255) else "rgba(0, 240, 255, 140)"
            border_focus = f"rgb({ar}, {ag}, {ab})" if (ar, ag, ab) != (255, 255, 255) else "#00f0ff"
            text_col = "#ffffff"
            ph_col = "rgba(160, 175, 200, 0.70)"

        self._chat_input.setStyleSheet(f"""
            QLineEdit {{
                background-color: {bg_normal};
                border: 1.5px solid {border_normal};
                border-radius: 9px;
                padding-left: 14px;
                padding-right: 14px;
                color: {text_col};
                font-family: 'Segoe UI', system-ui, sans-serif;
                font-size: 13px;
                selection-background-color: rgba(0, 240, 255, 0.45);
                selection-color: #ffffff;
            }}
            QLineEdit:focus {{
                border: 2px solid {border_focus};
                background-color: {bg_focus};
            }}
            QLineEdit::placeholder {{
                color: {ph_col};
            }}
        """)

    def set_theme(self, theme_key: str):
        if theme_key in ISLAND_THEMES:
            self._theme_key = theme_key
            if self._settings:
                self._settings.island_style = theme_key
                self._settings.save()
            self._update_chat_input_theme(ISLAND_THEMES[theme_key])
            self.update()



    def cycle_theme(self):
        theme_order = [
            "bloom_dark",
            "amoled_black",
            "electric_neon",
            "apple_dynamic",
            "originos_dark",
            "cyber_glow",
            "sunset_warm",
            "frosted_crystal",
            "frost_white",
        ]
        try:
            cur_idx = theme_order.index(self._theme_key)
            next_key = theme_order[(cur_idx + 1) % len(theme_order)]
        except ValueError:
            next_key = "amoled_black"
        self.set_theme(next_key)
        th_name = ISLAND_THEMES.get(next_key, {}).get("name", next_key)
        self._ambient_toast_time = time.monotonic()
        self._ambient_toast_name = f"Theme: {th_name}"
        self.update()



    def _is_genuine_music_playing(self) -> bool:
        """
        Validates that audio is ACTUALLY playing from a genuine media source right now.
        Strictly rejects non-media apps (File Explorer, IDEs, code files, documents),
        and strictly requires active playback (returns False when paused/stopped).
        """
        cur = getattr(self._media, "current_info", None) if hasattr(self, "_media") else None
        active_info = None
        if self._last_media_info and self._last_media_info.is_playing:
            active_info = self._last_media_info
        elif cur and cur.is_playing:
            active_info = cur

        if not active_info or not active_info.is_playing:
            return False

        title = (active_info.title or "").strip().lower()
        artist = (active_info.artist or "").strip().lower()
        app = (active_info.app_name or "").strip().lower()

        if not title and not artist:
            return False

        # Reject common code and document file extensions in title
        doc_exts = (
            ".py", ".pyw", ".js", ".jsx", ".ts", ".tsx", ".html", ".htm", ".css", ".json",
            ".yaml", ".yml", ".md", ".txt", ".log", ".c", ".cpp", ".h", ".cs", ".java",
            ".go", ".rs", ".php", ".sh", ".bat", ".ps1", ".pdf", ".doc", ".docx", ".xls",
            ".xlsx", ".ppt", ".pptx", ".zip", ".tar", ".gz", ".7z", ".rar"
        )
        if any(title.endswith(ext) or f"{ext} " in title or f"{ext} -" in title for ext in doc_exts):
            return False

        # Reject non-media development tools and applications
        blacklist = (
            "antigravity", "ide", "file explorer", "explorer.exe", "explorer", "visual studio",
            "vscode", "vs code", "cursor", "pycharm", "intellij", "sublime", "atom", "notepad",
            "terminal", "powershell", "cmd.exe", "command prompt", "task manager", "settings",
            "calculator", "snipping tool", "snip", "word", "excel", "powerpoint", "git", "github"
        )
        if any(b in title or b in artist or b in app for b in blacklist):
            return False

        return True

    def set_eye_color(self, color_key: str):
        if color_key in NIXI_EYE_COLORS:
            self._eye_color_key = color_key
            name = NIXI_EYE_COLORS[color_key][0]
            self._ambient_toast_time = time.monotonic()
            self._ambient_toast_name = f"Nixi Eyes: {name}"
            self._wake_timer()
            self.update()



    def cycle_eye_color(self):
        keys = list(NIXI_EYE_COLORS.keys())
        try:
            idx = keys.index(self._eye_color_key)
            next_k = keys[(idx + 1) % len(keys)]
        except ValueError:
            next_k = "white"
        self.set_eye_color(next_k)

    def trigger_pet_emotion(self, emotion: str = ""):
        """
        Triggers rich, lifelike emotional reactions with expressive eyes,
        blush, bounce animation, and particle effects (hearts, tears, anger marks, sparkles).
        Cycles through love -> surprised -> happy -> sad -> angry when clicked.
        """
        if not emotion:
            self._pet_emotion_idx = (self._pet_emotion_idx + 1) % len(self._pet_emotion_cycle)
            emotion = self._pet_emotion_cycle[self._pet_emotion_idx]
        else:
            if emotion in self._pet_emotion_cycle:
                self._pet_emotion_idx = self._pet_emotion_cycle.index(emotion)

        self._pet_emotion = emotion
        self._pet_emotion_timer = 12.0  # Stays active for 12 seconds so user can enjoy it
        self._pet_bounce_vel = -3.8
        self._pet_particles.clear()
        self._wake_timer()

        cx = self.width() // 2
        cy = self.height() // 2

        if emotion == "love":
            self._pet_blush_alpha = 1.0
            for _ in range(7):
                self._spawn_particle("heart", cx + random.uniform(-22, 22), cy + random.uniform(-2, 4))
        elif emotion == "happy":
            self._pet_blush_alpha = 0.85
            for _ in range(6):
                self._spawn_particle("sparkle", cx + random.uniform(-24, 24), cy + random.uniform(-4, 4))
        elif emotion == "sad":
            self._pet_blush_alpha = 0.0
            for _ in range(4):
                self._spawn_particle("tear", cx + random.choice([-12, 12]) + random.uniform(-2, 2), cy + 4)
        elif emotion == "angry":
            self._pet_blush_alpha = 0.0
            for _ in range(3):
                self._spawn_particle("anger", cx + 18 + random.uniform(-2, 4), cy - 6 + random.uniform(-3, 3))
        elif emotion == "surprised":
            self._pet_blush_alpha = 0.0
            for _ in range(4):
                self._spawn_particle("sparkle", cx + random.uniform(-18, 18), cy + random.uniform(-4, 4))

        self.update()

    def set_custom_eye_color(self, color):
        """Sets custom user-selected RGBA eye color with alpha/transparency support."""
        col = parse_rgba_color(color)
        if col.isValid():
            self._custom_eye_color = col
            if self._settings:
                r, g, b, a = col.red(), col.green(), col.blue(), col.alpha()
                self._settings.set("island_eye_color", f"rgba({r},{g},{b},{a})", save_now=True)
            self._ambient_toast_time = time.monotonic()
            self._ambient_toast_name = f"Eye Color: rgba({col.red()}, {col.green()}, {col.blue()}, {col.alpha()})"
            self._wake_timer()
            self.update()

    def open_eye_color_picker(self):
        """Opens native RGBA color picker dialog for pet eyes."""
        try:
            from PySide6.QtWidgets import QColorDialog
            init_col = getattr(self, "_custom_eye_color", None) or QColor(255, 255, 255, 255)
            dlg = QColorDialog(self)
            dlg.setWindowTitle("Select Pet Eye RGBA Color")
            dlg.setOption(QColorDialog.ColorDialogOption.ShowAlphaChannel, True)
            dlg.setCurrentColor(init_col)
            if dlg.exec():
                selected = dlg.selectedColor()
                if selected.isValid():
                    self.set_custom_eye_color(selected)
        except Exception as e:
            print("Failed to open eye color dialog:", e)

    def _spawn_particle(self, p_type: str, x: Optional[float] = None, y: Optional[float] = None):
        cx = (self.width() / 2.0) if x is None else float(x)
        cy = (self.height() / 2.0) if y is None else float(y)

        if p_type == "heart":
            self._pet_particles.append({
                "type": "heart",
                "x": cx + random.uniform(-10, 10),
                "y": cy + random.uniform(-2, 4),
                "vx": random.uniform(-6.0, 6.0),
                "vy": random.uniform(-22.0, -14.0),
                "sway_phase": random.uniform(0.0, 6.28),
                "size": random.uniform(6.0, 9.5),
                "life": random.uniform(1.2, 1.8),
                "max_life": 1.8,
                "color": random.choice([QColor(255, 75, 120), QColor(255, 105, 180), QColor(244, 63, 94)])
            })
        elif p_type == "tear":
            self._pet_particles.append({
                "type": "tear",
                "x": cx,
                "y": cy,
                "vx": random.uniform(-2.5, 2.5),
                "vy": random.uniform(16.0, 26.0),
                "size": random.uniform(4.0, 6.0),
                "life": random.uniform(1.0, 1.4),
                "max_life": 1.4,
                "color": QColor(56, 189, 248)
            })
        elif p_type == "sparkle":
            self._pet_particles.append({
                "type": "sparkle",
                "x": cx + random.uniform(-16, 16),
                "y": cy + random.uniform(-5, 5),
                "vx": random.uniform(-8.0, 8.0),
                "vy": random.uniform(-12.0, 6.0),
                "size": random.uniform(4.5, 7.5),
                "life": random.uniform(0.8, 1.3),
                "max_life": 1.3,
                "color": random.choice([QColor(250, 204, 21), QColor(0, 240, 255), QColor(255, 255, 255)])
            })
        elif p_type == "anger":
            self._pet_particles.append({
                "type": "anger",
                "x": cx,
                "y": cy,
                "vx": random.uniform(-2.0, 4.0),
                "vy": random.uniform(-7.0, -2.0),
                "size": random.uniform(8.0, 11.0),
                "life": random.uniform(1.0, 1.4),
                "max_life": 1.4,
                "color": QColor(239, 68, 68)
            })

    def log_water_glass(self):
        """Nixi Feature 11: Gentle water reminder - click to log a glass."""
        self._water_glasses_today += 1
        self._ambient_toast_time = time.monotonic()
        self._ambient_toast_name = f"💧 Hydration Logged: {self._water_glasses_today}/{self._water_goal} glasses"
        self._wake_timer()
        self.update()



    def toggle_keep_awake(self, enable: Optional[bool] = None):
        """Nixi Feature 09: Keep your PC awake for an hour without screen sleep/lock."""
        if enable is None:
            self._keep_awake_active = not self._keep_awake_active
        else:
            self._keep_awake_active = enable

        ES_CONTINUOUS = 0x80000000
        ES_SYSTEM_REQUIRED = 0x00000001
        ES_DISPLAY_REQUIRED = 0x00000002

        try:
            if self._keep_awake_active:
                self._keep_awake_end_time = time.monotonic() + 3600.0
                ctypes.windll.kernel32.SetThreadExecutionState(ES_CONTINUOUS | ES_SYSTEM_REQUIRED | ES_DISPLAY_REQUIRED)
                self._ambient_toast_name = "☕ Keep PC Awake: Active (1 Hour)"
            else:
                ctypes.windll.kernel32.SetThreadExecutionState(ES_CONTINUOUS)
                self._ambient_toast_name = "☕ Keep PC Awake: Disabled"
            self._ambient_toast_time = time.monotonic()
        except Exception:
            pass
        self._wake_timer()
        self.update()



    def toggle_stopwatch(self):
        """Nixi Feature 08: Start/Pause a stopwatch counting up in the notch."""
        self._stopwatch_running = not self._stopwatch_running
        self._stopwatch_last_tick = time.monotonic()
        self._ambient_toast_time = time.monotonic()
        self._ambient_toast_name = "⏳ Stopwatch: Started" if self._stopwatch_running else "⏸ Stopwatch: Paused"
        self._wake_timer()
        self.update()



    def reset_stopwatch(self):
        self._stopwatch_running = False
        self._stopwatch_elapsed = 0.0
        self._ambient_toast_time = time.monotonic()
        self._ambient_toast_name = "🔄 Stopwatch: Reset"
        self._wake_timer()
        self.update()



    def set_island_style(self, theme_key: str):
        self.set_theme(theme_key)

    def set_ambient_style(self, style_key: str, notify: bool = True):
        if style_key in ISLAND_AMBIENT_NAMES:
            self._ambient_style = style_key
            if self._settings:
                self._settings.island_ambient_style = style_key
                self._settings.save()
            if notify:
                self._ambient_toast_time = time.monotonic()
                self._ambient_toast_name = ISLAND_AMBIENT_NAMES.get(style_key, style_key)
            self.update()

    def set_wave_style(self, style: str):
        if style in ["sine", "harmonic", "cyber"]:
            self._wave_style = style
            if self._settings:
                self._settings.set("wave_style", style, save_now=True)
            self.update()

    def set_compact_idle_mode(self, mode: str):
        if mode in ["eyes", "network", "weather", "vitals"]:
            self._compact_idle_mode = mode
            if self._settings:
                self._settings.set("compact_idle_mode", mode, save_now=True)
            self.update()

    def set_accent_theme(self, theme: str):
        if theme in ["adaptive", "cyberpunk", "tokyo", "gold", "emerald", "crimson"]:
            self._accent_theme_key = theme
            if self._settings:
                self._settings.set("accent_theme", theme, save_now=True)
            self.update()



    def _cycle_ambient_style(self):
        styles = list(ISLAND_AMBIENT_NAMES.keys())
        try:
            cur_idx = styles.index(self._ambient_style)
            next_style = styles[(cur_idx + 1) % len(styles)]
        except ValueError:
            next_style = styles[0]
        self.set_ambient_style(next_style, notify=True)

    def set_position_mode(self, mode: str):
        self._position_mode = mode
        if mode == "top_notch":
            self._notch_style = "flush_notch"
            if self._settings:
                self._settings.notch_style = "flush_notch"
        if self._settings:
            self._settings.island_position = mode
            self._settings.save()
        self._reposition()

    def set_island_position(self, mode: str):
        self.set_position_mode(mode)

    def set_weather_location(self, loc: str):
        self._weather.set_location(loc)
        if self._settings:
            self._settings.weather_location = loc
            self._settings.save()

    def show_notification(self, app_name: str, title: str, body: str):
        """Presents a Windows toast notification as a sleek animated Dynamic Island expansion."""
        self._current_notification = {
            "app_name": app_name or "Notification",
            "title": title or "",
            "body": body or "",
            "time": time.time(),
        }
        self._wake_timer()
        self.switch_state(self.STATE_NOTIFICATION)
        # 6-second auto-dismiss back to compact pill
        self._notification_dismiss_timer.start(6000)

    def _auto_dismiss_notification(self):
        if self._state == self.STATE_NOTIFICATION:
            self.switch_state(self.STATE_COMPACT)

    def _activate_notification_app(self):
        """Brings the notification sender app to foreground focus."""
        if not self._current_notification:
            return
        app_name = self._current_notification.get("app_name", "").lower()
        if not app_name:
            return
        try:
            import win32gui
            import win32con
            matched_hwnd = None
            def enum_windows_cb(hwnd, _):
                nonlocal matched_hwnd
                if matched_hwnd:
                    return
                if win32gui.IsWindowVisible(hwnd):
                    title = win32gui.GetWindowText(hwnd).lower()
                    if title and app_name in title:
                        matched_hwnd = hwnd
            win32gui.EnumWindows(enum_windows_cb, None)
            if matched_hwnd:
                win32gui.ShowWindow(matched_hwnd, win32con.SW_RESTORE)
                win32gui.SetForegroundWindow(matched_hwnd)
        except Exception:
            pass

    def expand_to_state(self, state_id: int):
        mapping = {
            0: self.STATE_COMPACT,
            1: self.STATE_MUSIC,
            2: self.STATE_WEATHER,
            3: self.STATE_CLIPBOARD,
            4: self.STATE_TOOLS,
        }
        self.switch_state(mapping.get(state_id, self.STATE_COMPACT))

    def _on_media_listener_callback(self, info: MediaInfo):
        self._wake_timer()
        QTimer.singleShot(0, lambda: self._on_media_updated(info))

    def _on_weather_listener_callback(self, info: WeatherInfo):
        QTimer.singleShot(0, lambda: self._on_weather_updated(info))

    def _on_weather_updated(self, info: WeatherInfo):
        self._last_weather_info = info
        self.update()



    def _on_lyrics_loaded(self, key: str, lines: list, user_offset: float = 0.0):
        try:
            if key == self._lyrics_cache_key or not self._lyrics_lines:
                self._lyrics_lines = lines
                self._lyrics_offset_sec = float(user_offset)
                self.update()
        except Exception:
            pass



    def _render_tick(self):
        # 0. Sync Media & Weather Info
        cur_media = getattr(self._media, "current_info", None) if hasattr(self, "_media") else None
        if cur_media:
            from media_service import is_valid_media_info
            if is_valid_media_info(cur_media) and cur_media.is_playing:
                self._last_media_info = cur_media
            else:
                if self._last_media_info:
                    self._last_media_info.is_playing = False

            # Keep track duration accurately synced to the active player
            if cur_media.duration_sec > 0:
                self._playback_dur_sec = cur_media.duration_sec

            # Detect track change: update title and reset ticker marquee
            if cur_media.title and cur_media.title != self._last_played_title:
                self._last_played_title = cur_media.title
                self._playback_pos_sec = cur_media.current_position()
                self._compact_ticker_x = 0.0
                self._music_ticker_x = 0.0
                self._compact_ticker_pause = 2.0
                self._music_ticker_pause = 2.0
        elif self._last_media_info:
            if not getattr(self._last_media_info, "is_playing", False):
                self._last_media_info.is_playing = False

        # Ensure cover art color is extracted immediately whenever thumbnail is present (either in cur_media or last_media_info)
        active_thumb = None
        if cur_media and cur_media.thumbnail_bytes:
            active_thumb = cur_media.thumbnail_bytes
        elif self._last_media_info and self._last_media_info.thumbnail_bytes:
            active_thumb = self._last_media_info.thumbnail_bytes

        if active_thumb and (len(active_thumb) != getattr(self, "_last_thumb_len", 0) or getattr(self, "_extracted_art_color", None) is None):
            self._last_thumb_len = len(active_thumb)
            extracted = self._extract_artwork_color(active_thumb)
            if extracted and extracted.isValid():
                self._extracted_art_color = extracted
                self._dynamic_accent_color = extracted

        cur_weather = self._weather.current_weather
        if cur_weather:
            self._last_weather_info = cur_weather

        # Global animation timer with true delta time
        now = time.monotonic()
        dt = min(0.04, max(0.001, now - self._last_tick_time))
        self._last_tick_time = now
        self._anim_time += dt

        # 1. Advance Playback Progress & High-Precision Real-Time Sync
        is_playing = bool(self._last_media_info and self._last_media_info.is_playing)
        if cur_media and cur_media.has_media and not self._is_scrubbing:
            target_pos = cur_media.current_position()
            if is_playing:
                # Advance smoothly by dt every 16ms frame (fluid 60 FPS motion)
                self._playback_pos_sec += dt

                # Reconcile with actual media position from player
                diff = target_pos - self._playback_pos_sec
                if abs(diff) > 2.0:
                    # External scrub / skip in Spotify, YouTube or Chrome: snap immediately
                    self._playback_pos_sec = target_pos
                elif abs(diff) > 0.04:
                    # Invisible smooth drift correction
                    self._playback_pos_sec += diff * min(1.0, dt * 4.0)
            else:
                # Paused: lock directly to actual player paused timestamp
                self._playback_pos_sec = target_pos

            # Clamp playback position safely within track bounds
            if self._playback_dur_sec > 0:
                self._playback_pos_sec = min(self._playback_dur_sec, max(0.0, self._playback_pos_sec))
        elif is_playing and not self._is_scrubbing:
            self._playback_pos_sec += dt
            if self._playback_dur_sec > 0 and self._playback_pos_sec >= self._playback_dur_sec:
                self._playback_pos_sec = 0.0

        # Auto-fetch synced lyrics from disk cache or LRCLIB when new track begins
        is_playing = self._is_genuine_music_playing()
        was_playing = getattr(self, "_last_was_genuine_playing", False)
        self._last_was_genuine_playing = is_playing

        # Check if playback state changed
        if was_playing and not is_playing:
            pass  # Keep lyrics and cached lines available during pause

        if cur_media and cur_media.has_media and cur_media.title and is_playing:
            track_key = f"{cur_media.artist or ''}:{cur_media.title or ''}".strip().lower()
            if track_key and track_key != self._lyrics_cache_key:
                self._lyrics_cache_key = track_key
                self._lyrics_lines = []
                self._lyrics_active_idx = 0
                self._lyrics_scroll_y = 0.0
                LyricsEngine.fetch_lyrics(
                    track_key,
                    cur_media.artist or "",
                    cur_media.title or "",
                    getattr(cur_media, "album", "") or "",
                    self._playback_dur_sec,
                    self._on_lyrics_loaded
                )

        # Align active lyric line with playback position & smooth scroll
        if self._lyrics_lines:
            active_idx = 0
            pos = self._playback_pos_sec + getattr(self, "_lyrics_offset_sec", 0.0)
            for i, (t_sec, _) in enumerate(self._lyrics_lines):
                if pos >= t_sec:
                    active_idx = i
                else:
                    break
            if active_idx != getattr(self, "_compact_lyric_last_idx", -1):
                self._compact_lyric_last_idx = active_idx
                self._compact_lyric_ticker_x = 0.0
                self._compact_lyric_pause = 1.0
            self._lyrics_active_idx = active_idx
            target_scroll = -float(active_idx * 26.0)
            self._lyrics_scroll_y += (target_scroll - self._lyrics_scroll_y) * min(1.0, dt * 8.0)

        # Pet Eye Animation Engine (Natural blinking, cursor tracking, winks, drowse)
        self._pet_eye_blink_timer -= dt
        if self._pet_eye_blink_timer <= 0.0:
            if self._pet_eye_blink_phase == 0.0:
                self._pet_eye_blink_phase = 0.01
            self._pet_eye_blink_phase += dt * 7.5
            if self._pet_eye_blink_phase >= 2.0:
                self._pet_eye_blink_phase = 0.0
                # 30% chance for rapid natural double-blink
                if random.random() < 0.30:
                    self._pet_eye_blink_timer = 0.16
                else:
                    self._pet_eye_blink_timer = random.uniform(2.5, 5.0)

        # Winking timer
        self._pet_eye_wink_timer -= dt
        if self._pet_eye_wink_timer <= 0.0:
            self._pet_eye_wink_which = random.choice(["left", "right"])
            self._pet_eye_wink_phase = 0.01
            self._pet_eye_wink_timer = random.uniform(7.0, 14.0)

        if self._pet_eye_wink_phase > 0.0:
            self._pet_eye_wink_phase += dt * 5.2
            if self._pet_eye_wink_phase >= 2.0:
                self._pet_eye_wink_phase = 0.0

        self._pet_eye_glance_timer -= dt
        if self._pet_eye_glance_timer <= 0.0:
            self._pet_eye_glance_target_x = random.uniform(-1.8, 1.8)
            self._pet_eye_glance_target_y = random.uniform(-1.0, 1.0)
            self._pet_eye_glance_timer = random.uniform(2.0, 4.2)

        # Cursor tracking: smooth glance towards mouse position across desktop
        try:
            m_pos = QCursor.pos()
            c_pos = self.mapToGlobal(QPoint(int(self.width() / 2), int(self.height() / 2)))
            dx = float(m_pos.x() - c_pos.x())
            dy = float(m_pos.y() - c_pos.y())
            target_cur_x = max(-6.5, min(6.5, dx / 110.0))
            target_cur_y = max(-3.0, min(4.5, dy / 80.0))
            self._pet_eye_cursor_target_x = target_cur_x
            self._pet_eye_cursor_target_y = target_cur_y
            smooth_rate = 1.0 - math.exp(-12.0 * dt)
            self._pet_eye_cursor_glance_x += (target_cur_x - self._pet_eye_cursor_glance_x) * smooth_rate
            self._pet_eye_cursor_glance_y += (target_cur_y - self._pet_eye_cursor_glance_y) * smooth_rate

            # Inactivity / Drowse tracking & wake on nearby cursor movement
            now = time.monotonic()
            if (m_pos - self._last_cursor_pos).manhattanLength() > 2:
                self._last_cursor_pos = m_pos
                self._last_user_activity_time = now
                self._last_cursor_move_time = now
                self._pet_eye_alert_phase = min(1.0, self._pet_eye_alert_phase + 0.3)
                self._wake_timer()

            idle_dur = now - self._last_user_activity_time
            if idle_dur > 14.0:
                self._pet_eye_drowse_level = min(1.0, self._pet_eye_drowse_level + dt * 0.35)
            else:
                self._pet_eye_drowse_level = max(0.0, self._pet_eye_drowse_level - dt * 2.5)

            if self._pet_eye_alert_phase > 0.0:
                self._pet_eye_alert_phase = max(0.0, self._pet_eye_alert_phase - dt * 1.5)
        except Exception:
            pass

        # Smooth glance easing
        glance_smooth = 1.0 - math.exp(-8.0 * dt)
        self._pet_eye_glance_x += (self._pet_eye_glance_target_x - self._pet_eye_glance_x) * glance_smooth
        self._pet_eye_glance_y += (self._pet_eye_glance_target_y - self._pet_eye_glance_y) * glance_smooth

        # Pet Emotion Physics & Particle Engine Loop
        if self._pet_particles or self._pet_emotion_timer > 0.0:
            if self._pet_emotion_timer > 0.0:
                self._pet_emotion_timer = max(0.0, self._pet_emotion_timer - dt)
                if self._pet_emotion_timer <= 0.0:
                    self._pet_emotion = "idle"

            # Spring bounce physics
            self._pet_bounce_y += self._pet_bounce_vel * dt * 60.0
            self._pet_bounce_vel += (0.0 - self._pet_bounce_y) * min(1.0, dt * 14.0)
            self._pet_bounce_vel *= 0.82

            # Blush fade
            target_blush = 1.0 if self._pet_emotion in ("love", "happy") else 0.0
            self._pet_blush_alpha += (target_blush - self._pet_blush_alpha) * min(1.0, dt * 6.0)

            # Spawn continuous gentle particles during emotional peak
            if self._pet_emotion == "love" and random.random() < dt * 3.2:
                self._spawn_particle("heart")
            elif self._pet_emotion == "sad" and random.random() < dt * 2.8:
                self._spawn_particle("tear", self.width() / 2.0 + random.choice([-12, 12]), self.height() / 2.0 + 4)
            elif self._pet_emotion == "happy" and random.random() < dt * 2.5:
                self._spawn_particle("sparkle")
            elif self._pet_emotion == "angry" and random.random() < dt * 2.2:
                self._spawn_particle("anger", self.width() / 2.0 + 18 + random.uniform(-2, 4), self.height() / 2.0 - 6)

            # Update active particles
            alive_particles = []
            for p_obj in self._pet_particles:
                p_obj["x"] += p_obj["vx"] * dt
                if p_obj["type"] == "heart":
                    p_obj["sway_phase"] += dt * 5.0
                    p_obj["x"] += math.sin(p_obj["sway_phase"]) * 14.0 * dt
                p_obj["y"] += p_obj["vy"] * dt
                p_obj["life"] -= dt
                if p_obj["life"] > 0.0:
                    alive_particles.append(p_obj)
            self._pet_particles = alive_particles

        # Dynamic size optimization for compact mode & retracted trigger icon mode
        if self._is_retracted:
            des_w, des_h = 52.0, 10.0
            if abs(self._target_w - des_w) > 0.1 or abs(self._target_h - des_h) > 0.1:
                self._target_w = des_w
                self._target_h = des_h
            if self._is_genuine_music_playing():
                # Music started while retracted -> wake up and unretract automatically!
                self.unretract()
            else:
                # Instant unretract if cursor approaches top bezel right above the trigger notch
                try:
                    m_pos = QCursor.pos()
                    screen = QGuiApplication.primaryScreen()
                    if screen:
                        geo = screen.geometry()
                        notch_cx = geo.x() + geo.width() // 2
                        if abs(m_pos.x() - notch_cx) <= 60 and m_pos.y() <= geo.y() + 18:
                            self.unretract()
                except Exception:
                    pass
        elif self._state == self.STATE_COMPACT:
            is_flush = self._is_flush_notch()
            if (self._is_jarvis_talking or getattr(self, "_is_voice_listening", False) or 
                time.monotonic() - getattr(self, "_jarvis_speech_time", 0.0) < 3.5):
                des_w, des_h = (340.0 if is_flush else 320.0), 44.0
            elif self._is_genuine_music_playing():
                des_w, des_h = (345.0 if is_flush else 315.0), 44.0
            else:
                des_w, des_h = (255.0 if is_flush else 235.0), 40.0
            if abs(self._target_w - des_w) > 0.1 or abs(self._target_h - des_h) > 0.1:
                self._target_w = des_w
                self._target_h = des_h

            # Auto-hide / tuck into top bezel when not in use
            if (
                getattr(self, "_auto_retract", True)
                and not self._is_retracted
                and not self._is_genuine_music_playing()
                and not self._pinned
                and not self._is_hovered
                and getattr(self, "_pet_emotion_timer", 0.0) <= 0.0
                and not self._is_jarvis_talking
                and not getattr(self, "_is_voice_listening", False)
            ):
                idle_dur = now - getattr(self, "_last_user_activity_time", now)
                if idle_dur > 3.8 and not self._retract_timer.isActive():
                    self.retract()

        # 2. Critically Damped Fluid Spring Engine for Morphing Width & Height (Zero Jitter, Silky 60 FPS)
        diff_w = self._target_w - self._anim_w
        diff_h = self._target_h - self._anim_h

        # Critically damped spring (damping ratio = 1.0) guarantees zero overshoot, zero ringing, and zero micro-jitter
        tension = 320.0
        damping = 36.0

        if abs(diff_w) > 0.6 or abs(diff_h) > 0.6 or abs(self._vel_w) > 2.5 or abs(self._vel_h) > 2.5:
            self._is_morphing = True
            acc_w = tension * diff_w - damping * self._vel_w
            acc_h = tension * diff_h - damping * self._vel_h
            self._vel_w += acc_w * dt
            self._vel_h += acc_h * dt
            self._anim_w += self._vel_w * dt
            self._anim_h += self._vel_h * dt

            # Calculate continuous expansion progress 0.0 (compact) <-> 1.0 (expanded card) in both directions
            compact_h = 36.0
            target_expanded_h = max(120.0, float(self._target_h if self._state != self.STATE_COMPACT else getattr(self, "_prev_h", 192.0)))
            h_range = max(1.0, target_expanded_h - compact_h)
            self._morph_progress = min(1.0, max(0.0, (self._anim_h - compact_h) / h_range))

            # Dynamic corner radius interpolation (Pill 18.0 <-> Squircle 24.0)
            smooth_p = self._morph_progress * self._morph_progress * (3.0 - 2.0 * self._morph_progress)
            self._corner_radius = 18.0 * (1.0 - smooth_p) + 24.0 * smooth_p

            new_w = max(48, int(round(self._anim_w))) if self._is_retracted else max(120, int(round(self._anim_w)))
            new_h = max(8, int(round(self._anim_h))) if self._is_retracted else max(30, int(round(self._anim_h)))

            if new_w != self._current_w or new_h != self._current_h:
                old_w = self._current_w
                self._current_w = new_w
                self._current_h = new_h

                screen = self.screen() or QGuiApplication.primaryScreen()
                geo = screen.geometry() if screen else QRect(0, 0, 1920, 1080)

                if self._position_mode == "top_notch":
                    target_x = geo.x() + (geo.width() - new_w) // 2
                    target_y = geo.y()
                    self.setGeometry(target_x, target_y, new_w, new_h)
                elif self._position_mode == "floating":
                    # Strictly anchor to center coordinate to completely eliminate cumulative leftward drift!
                    if not hasattr(self, "_floating_center_x") or not self._is_morphing:
                        self._floating_center_x = float(self.x() + old_w / 2.0)
                    target_x = int(round(self._floating_center_x - new_w / 2.0))
                    # Prevent going offscreen
                    target_x = max(geo.x(), min(geo.x() + geo.width() - new_w, target_x))
                    self.setGeometry(target_x, self.y(), new_w, new_h)
                else:
                    self.resize(new_w, new_h)
        else:
            if self._is_morphing:
                self._is_morphing = False
                self._anim_w = float(self._target_w)
                self._anim_h = float(self._target_h)
                self._vel_w = 0.0
                self._vel_h = 0.0
                self._current_w = int(self._target_w)
                self._current_h = int(self._target_h)
                if self._is_retracted or self._state == self.STATE_COMPACT or self._target_h <= 55.0:
                    self._morph_progress = 0.0
                    self._corner_radius = 5.0 if self._is_retracted else 18.0
                else:
                    self._morph_progress = 1.0
                    self._corner_radius = 24.0

                screen = self.screen() or QGuiApplication.primaryScreen()
                geo = screen.geometry() if screen else QRect(0, 0, 1920, 1080)
                if self._position_mode == "top_notch":
                    target_x = geo.x() + (geo.width() - self._current_w) // 2
                    target_y = geo.y()
                    self.setGeometry(target_x, target_y, self._current_w, self._current_h)
                elif self._position_mode == "floating":
                    if hasattr(self, "_floating_center_x"):
                        target_x = int(round(self._floating_center_x - self._current_w / 2.0))
                        target_x = max(geo.x(), min(geo.x() + geo.width() - self._current_w, target_x))
                        self.setGeometry(target_x, self.y(), self._current_w, self._current_h)
                    else:
                        self.resize(self._current_w, self._current_h)
                else:
                    self.resize(self._current_w, self._current_h)

        # Magnetic Snap to Notch Spring Flight
        if self._is_snapping_to_notch:
            cur_x = float(self.x())
            cur_y = float(self.y())
            dx = self._snap_target_x - cur_x
            dy = self._snap_target_y - cur_y
            if abs(dx) < 0.5 and abs(dy) < 0.5 and abs(self._snap_vel_x) < 1.0 and abs(self._snap_vel_y) < 1.0:
                self.move(int(round(self._snap_target_x)), int(round(self._snap_target_y)))
                self._is_snapping_to_notch = False
                self.set_position_mode("top_notch")
            else:
                acc_x = 280.0 * dx - 24.0 * self._snap_vel_x
                acc_y = 280.0 * dy - 24.0 * self._snap_vel_y
                self._snap_vel_x += acc_x * dt
                self._snap_vel_y += acc_y * dt
                new_x = cur_x + self._snap_vel_x * dt
                new_y = cur_y + self._snap_vel_y * dt
                self.move(int(round(new_x)), int(round(new_y)))

        # OriginOS Sliding Tab Indicator Spring Physics
        ind_diff = self._indicator_target_x - self._indicator_x
        ind_acc = 340.0 * ind_diff - 27.0 * self._indicator_vel
        self._indicator_vel += ind_acc * dt
        self._indicator_x += self._indicator_vel * dt

        speed = abs(self._indicator_vel)
        target_stretch = min(10.0, speed * 0.018)
        stretch_diff = (22.0 + target_stretch) - self._indicator_w
        self._indicator_w_vel += (280.0 * stretch_diff - 24.0 * self._indicator_w_vel) * dt
        self._indicator_w += self._indicator_w_vel * dt

        # Tab cross-fade progress
        if self._tab_transition_progress < 1.0:
            self._tab_transition_progress = min(1.0, self._tab_transition_progress + dt * 5.0)

        # Volume HUD Drop-Down Spring Animation
        hud_elapsed = time.monotonic() - self._volume_hud_time
        if hud_elapsed < 1.4:
            target_hud_y = 5.0
        else:
            target_hud_y = -32.0
        hud_y_diff = target_hud_y - self._volume_hud_y
        self._volume_hud_y += hud_y_diff * min(1.0, dt * 16.0)

        # Smooth Volume Bar Spring Interpolation
        self._anim_volume_level += (float(self._volume_hud_level) - self._anim_volume_level) * min(1.0, dt * 14.0)

        # Toast Banner Drop-Down Spring Animation
        toast_elapsed = time.monotonic() - self._ambient_toast_time
        if toast_elapsed < 1.8:
            target_toast_y = 4.0
        else:
            target_toast_y = -30.0
        toast_y_diff = target_toast_y - self._toast_y
        self._toast_y += toast_y_diff * min(1.0, dt * 16.0)

        # Tactile Button Micro-Animation Decays
        for b_name in list(self._btn_hover_anim.keys()):
            t_target = 1.0 if (self._hovered_btn == b_name) else 0.0
            self._btn_hover_anim[b_name] += (t_target - self._btn_hover_anim[b_name]) * min(1.0, dt * 16.0)
            if self._btn_hover_anim[b_name] < 0.005 and t_target == 0.0:
                self._btn_hover_anim[b_name] = 0.0

        for b_name in list(self._btn_press_anim.keys()):
            if self._btn_press_anim[b_name] > 0.001:
                self._btn_press_anim[b_name] = max(0.0, self._btn_press_anim[b_name] - dt * 6.5)

        # Smooth Morphing of Cover-Art Adaptive Accent Color
        is_genuine = self._is_genuine_music_playing()
        if is_genuine and getattr(self, "_extracted_art_color", None) and self._extracted_art_color.isValid():
            target_col = self._extracted_art_color
        elif not is_genuine:
            target_col = QColor(255, 255, 255)
        else:
            target_col = QColor(240, 181, 166)

        if not hasattr(self, "_dynamic_accent_color") or not self._dynamic_accent_color.isValid():
            self._dynamic_accent_color = target_col
        col_blend = min(1.0, dt * 8.5)
        cur_r = self._dynamic_accent_color.redF()
        cur_g = self._dynamic_accent_color.greenF()
        cur_b = self._dynamic_accent_color.blueF()
        self._dynamic_accent_color = QColor.fromRgbF(
            cur_r + (target_col.redF() - cur_r) * col_blend,
            cur_g + (target_col.greenF() - cur_g) * col_blend,
            cur_b + (target_col.blueF() - cur_b) * col_blend
        )

        # 3. Real Hardware Audio Metering & Beat/Flow Synced Equalizer
        if is_playing:
            master_peak, left_peak, right_peak = AudioMeterService.get_peaks()
            prev_peak = getattr(self, "_last_audio_peak", 0.0)
            self._last_audio_peak = master_peak
            transient_kick = max(0.0, master_peak - prev_peak)
            t = self._anim_time

            # Update ambient energy with real hardware audio volume / beat kicks
            target_energy = max(0.12, min(1.0, master_peak * 1.30 + transient_kick * 1.6))
            self._ambient_beat_energy += (target_energy - self._ambient_beat_energy) * min(1.0, dt * 16.0)
            self._ambient_hue = (self._ambient_hue + 0.5) % 360.0

            if master_peak > 0.005:
                # Direct hardware audio metering with frequency band emulation and stereo separation:
                # 6 bars: [0: Sub-bass, 1: Bass Kick, 2: Low-mid, 3: Vocal mid, 4: Treble, 5: Air]
                b0 = 0.22 + 0.74 * min(1.0, master_peak * 1.35 + transient_kick * 1.8)
                b1 = 0.25 + 0.75 * min(1.0, left_peak * 1.40 + transient_kick * 2.2)
                b2 = 0.28 + 0.68 * min(1.0, (left_peak * 0.7 + right_peak * 0.3) * 1.25 + math.sin(t * 14.0) * 0.08 * master_peak)
                b3 = 0.30 + 0.68 * min(1.0, master_peak * 1.20 + math.cos(t * 18.0) * 0.08 * master_peak)
                b4 = 0.26 + 0.70 * min(1.0, right_peak * 1.40 + transient_kick * 1.4)
                b5 = 0.20 + 0.65 * min(1.0, right_peak * 1.35 + math.sin(t * 26.0) * 0.12 * master_peak)
                targets = [b0, b1, b2, b3, b4, b5]
            else:
                # Flowing rhythmic harmonic waves with gentle breathing when idle/silent
                freqs = [12.5, 18.0, 25.0, 19.5, 14.0, 27.5]
                phases = [0.0, 1.4, 2.7, 0.8, 3.5, 1.9]
                beat = self._ambient_beat_energy
                targets = []
                for i in range(len(self._eq_bars)):
                    w1 = math.sin(t * freqs[i] + phases[i])
                    w2 = math.cos(t * (freqs[i] * 0.65) + phases[(i + 2) % len(phases)])
                    wave = (w1 * 0.6 + w2 * 0.4) * 0.5 + 0.5
                    pulse = (math.sin(t * 8.5 + phases[i]) * 0.5 + 0.5) * beat
                    targets.append(0.18 + 0.52 * wave + 0.30 * pulse)

            for i in range(len(self._eq_bars)):
                target = targets[i]
                # Snappy responsive attack jump on kick, silky liquid decay
                lerp_speed = (dt * 26.0) if target > self._eq_bars[i] else (dt * 12.0)
                self._eq_bars[i] += (target - self._eq_bars[i]) * min(1.0, lerp_speed)
        else:
            for i in range(len(self._eq_bars)):
                self._eq_bars[i] += (0.08 - self._eq_bars[i]) * min(1.0, dt * 8.0)
            self._ambient_beat_energy += (0.0 - self._ambient_beat_energy) * min(1.0, dt * 6.0)

        if is_playing:
            style = self._ambient_style
            if style == "aurora_borealis":
                # Aurora Borealis: Emerald Green (#10b981) + Deep Cosmic Violet (#8b5cf6) with harmonic wave phase
                wave = (math.sin(self._anim_time * 1.5) + 1.0) * 0.5
                target_pri = QColor(16, int(185 + 40 * wave), int(129 + 60 * wave))
                target_sec = QColor(int(139 + 30 * (1.0 - wave)), 92, int(246 - 20 * wave))
            elif style == "neon_cyber_pulse":
                # Cyberpunk Neon: Electric Cyan (#00f0ff) + Synth Laser Magenta (#ff0080) with beat strobe
                strobe = 1.0 + (0.25 if self._ambient_beat_energy > 0.6 else 0.0)
                target_pri = QColor(0, min(255, int(240 * strobe)), 255)
                target_sec = QColor(255, 0, min(255, int(128 * strobe)))
            elif style == "sunset_chroma":
                # Synthwave Sunset: Solar Amber Gold (#f59e0b) + Deep Sunset Rose (#e11d48)
                pulse = (math.sin(self._anim_time * 2.0) + 1.0) * 0.5
                target_pri = QColor(245, int(158 + 25 * pulse), 11)
                target_sec = QColor(225, 29, int(72 + 30 * pulse))
            elif style == "lava_fire_glow":
                # Inferno Magma: Blazing Crimson (#ef4444) + Molten Orange (#f97316) with bass flare
                surge = int(45 * self._ambient_beat_energy)
                target_pri = QColor(min(255, 239 + surge), min(255, 68 + surge * 2), 68)
                target_sec = QColor(249, min(255, 115 + surge * 2), 22)
            elif style == "rainbow_flow":
                # RGB Chroma Spectrum: Continuous 360-degree rotating prism
                h1 = (self._anim_time * 0.15) % 1.0
                h2 = (h1 + 0.28) % 1.0
                target_pri = QColor.fromHsvF(h1, 0.90, 0.98)
                target_sec = QColor.fromHsvF(h2, 0.85, 0.95)
            elif style == "minimal_frost":
                # Apple Minimal Frost: Diamond Crisp White + Glacial Ice Blue (#93c5fd)
                shimmer = int(15 * math.sin(self._anim_time * 2.5))
                target_pri = QColor(255, 255, 255)
                target_sec = QColor(min(255, 147 + shimmer), min(255, 197 + shimmer), 253)
            else:
                # adaptive_album (default)
                if self._extracted_art_color:
                    target_pri = self._extracted_art_color
                    h = (target_pri.hsvHueF() + 0.18) % 1.0
                    target_sec = QColor.fromHsvF(h if h >= 0 else 0.5, min(1.0, target_pri.hsvSaturationF() + 0.1), max(0.6, target_pri.valueF()))
                else:
                    target_pri = QColor.fromHsvF(self._ambient_hue / 360.0, 0.85, 0.95)
                    target_sec = QColor.fromHsvF(((self._ambient_hue + 60.0) % 360.0) / 360.0, 0.80, 0.90)
        else:
            self._ambient_beat_energy += (0.0 - self._ambient_beat_energy) * 0.08
            style = self._ambient_style
            if style == "aurora_borealis":
                target_pri = QColor(16, 185, 129)
                target_sec = QColor(139, 92, 246)
            elif style == "neon_cyber_pulse":
                target_pri = QColor(0, 240, 255)
                target_sec = QColor(255, 0, 128)
            elif style == "sunset_chroma":
                target_pri = QColor(245, 158, 11)
                target_sec = QColor(225, 29, 72)
            elif style == "lava_fire_glow":
                target_pri = QColor(239, 68, 68)
                target_sec = QColor(249, 115, 22)
            elif style == "rainbow_flow":
                h1 = (self._anim_time * 0.08) % 1.0
                target_pri = QColor.fromHsvF(h1, 0.75, 0.85)
                target_sec = QColor.fromHsvF((h1 + 0.3) % 1.0, 0.75, 0.85)
            elif style == "minimal_frost":
                target_pri = QColor(240, 245, 255)
                target_sec = QColor(147, 197, 253)
            else:
                target_pri = QColor(0, 122, 255)
                target_sec = QColor(168, 85, 247)

        # Smooth ambient light color morphing
        c1, c2 = self._ambient_color_current, self._ambient_color_secondary
        r1 = int(c1.red() + (target_pri.red() - c1.red()) * 0.12)
        g1 = int(c1.green() + (target_pri.green() - c1.green()) * 0.12)
        b1 = int(c1.blue() + (target_pri.blue() - c1.blue()) * 0.12)
        self._ambient_color_current = QColor(r1, g1, b1)

        r2 = int(c2.red() + (target_sec.red() - c2.red()) * 0.12)
        g2 = int(c2.green() + (target_sec.green() - c2.green()) * 0.12)
        b2 = int(c2.blue() + (target_sec.blue() - c2.blue()) * 0.12)
        self._ambient_color_secondary = QColor(r2, g2, b2)

        # Lava Magma Embers update (only when style is active and expanded)
        if self._ambient_style == "lava_fire_glow" and self._state != self.STATE_COMPACT:
            speed_mult = 1.0 + self._ambient_beat_energy * 2.2
            for ember in self._lava_embers:
                ember["y"] -= ember["speed"] * speed_mult
                ember["x"] += math.sin(self._anim_time * 2.5 + ember["speed"]) * 0.6
                if ember["y"] <= 10:
                    ember["y"] = random.uniform(self._current_h - 15, self._current_h + 10)
                    ember["x"] = random.uniform(10, max(20, self._current_w - 10))

        # 4. Weather Physics Particles Updates (only when weather state is visible)
        if self._state == self.STATE_WEATHER:
            # Rain Drops & Splashes
            for d in self._rain_drops:
                d["y"] += d["speed"]
                d["x"] += 1.2
                if d["y"] >= 104:
                    if len(self._rain_splashes) < 16 and random.random() < 0.4:
                        self._rain_splashes.append({"x": d["x"], "y": 104, "r": 1.0, "alpha": 0.85})
                    d["y"] = random.uniform(-15, 0)
                    d["x"] = random.uniform(0, 150)

            surviving_splashes = []
            for s in self._rain_splashes:
                s["r"] += 0.45
                s["alpha"] -= 0.075
                if s["alpha"] > 0.05 and s["r"] < 7.5:
                    surviving_splashes.append(s)
            self._rain_splashes = surviving_splashes

            # Snowflakes
            for f in self._snow_flakes:
                f["y"] += f["speed"]
                f["x"] += math.sin(f["phase"] + self._anim_time * 1.5) * 0.65
                if f["y"] >= 108:
                    f["y"] = random.uniform(-12, 0)
                    f["x"] = random.uniform(0, 150)

            # Wind Particles
            for p_w in self._wind_particles:
                p_w["x"] += p_w["speed"]
                p_w["y"] += math.sin(self._anim_time * 3.0 + p_w["x"] * 0.05) * 0.35
                if p_w["x"] >= 155:
                    p_w["x"] = random.uniform(-20, 0)
                    p_w["y"] = random.uniform(10, 98)

            # Heat Embers
            for e in self._heat_embers:
                e["y"] -= e["speed"]
                e["x"] += math.sin(e["phase"] + self._anim_time * 2.0) * 0.55
                if e["y"] <= 10:
                    e["y"] = random.uniform(95, 108)
                    e["x"] = random.uniform(10, 140)

            # Cloud Drift Layers
            for i in range(len(self._cloud_drift)):
                self._cloud_drift[i] += (0.18 + i * 0.14)
                if self._cloud_drift[i] >= 195.0:
                    self._cloud_drift[i] = -65.0

            # Thunder Lightning Generator
            self._lightning_timer += 1
            if self._lightning_flash > 0:
                self._lightning_flash = max(0.0, self._lightning_flash - 0.10)
            if self._lightning_timer > 80 and random.random() < 0.05:
                self._lightning_timer = 0
                self._lightning_flash = 1.0
                lx, ly = random.uniform(35, 75), 32
                pts = [(lx, ly)]
                for _ in range(5):
                    lx += random.uniform(-10, 10)
                    ly += random.uniform(12, 16)
                    pts.append((lx, ly))
                self._lightning_bolt_pts = pts

        # 5. Compass Heading & Route Simulation (only when map state is visible)
        if self._state == self.STATE_MAP:
            if self._compass_mode == "drift":
                self._compass_heading = (self._compass_heading + 0.35 + math.sin(self._anim_time * 0.8) * 0.25) % 360.0
            elif self._compass_mode == "mouse":
                cursor_pos = QCursor.pos() - self.pos()
                dx = cursor_pos.x() - 86
                dy = cursor_pos.y() - 74
                target_ang = (math.degrees(math.atan2(dx, -dy)) + 360.0) % 360.0
                self._compass_heading = target_ang
            elif self._compass_mode == "north":
                self._compass_heading = 0.0

            diff = (self._compass_heading - self._compass_current_heading + 180.0) % 360.0 - 180.0
            self._compass_current_heading = (self._compass_current_heading + diff * 0.14) % 360.0
            self._nav_progress = (self._nav_progress + self._nav_speed) % 1.0

        # Ticker text scroll
        if self._state != self.STATE_COMPACT:
            self._ticker_offset = (self._ticker_offset + 1) % 1000

        # System metrics sampling (every 3s when tools or expanded)
        now = time.monotonic()
        if HAS_PSUTIL and (self._state == self.STATE_TOOLS or self._state != self.STATE_COMPACT) and (now - self._last_sys_check_time > 3.0):
            self._last_sys_check_time = now
            try:
                self._last_cpu_percent = psutil.cpu_percent(interval=None)
                self._last_ram_percent = psutil.virtual_memory().percent
            except Exception:
                pass

        # Live Battery sampling (for Control Center and Calendar top bars)
        if HAS_PSUTIL and (now - self._last_battery_check > 3.0):
            self._last_battery_check = now
            try:
                b = psutil.sensors_battery()
                if b:
                    self._battery_percent = int(b.percent)
                    self._battery_plugged = bool(b.power_plugged)
            except Exception:
                pass

        # Real-time Network Speedometer sampling (every 1.0s)
        if HAS_PSUTIL and (now - getattr(self, "_last_net_check_time", 0.0) >= 1.0):
            last_t = getattr(self, "_last_net_check_time", 0.0)
            self._last_net_check_time = now
            try:
                net = psutil.net_io_counters()
                if last_t > 0.0:
                    dt_net = max(0.2, now - last_t)
                    recv_delta = max(0, net.bytes_recv - getattr(self, "_last_net_bytes_recv", net.bytes_recv))
                    sent_delta = max(0, net.bytes_sent - getattr(self, "_last_net_bytes_sent", net.bytes_sent))
                    self._net_down_bps = recv_delta / dt_net
                    self._net_up_bps = sent_delta / dt_net
                    self._net_down_str = self._format_net_speed(self._net_down_bps)
                    self._net_up_str = self._format_net_speed(self._net_up_bps)
                self._last_net_bytes_recv = net.bytes_recv
                self._last_net_bytes_sent = net.bytes_sent
            except Exception:
                pass

        # Focus / Pomodoro Timer tick
        if self._pomo_is_running:
            self._pomo_time_left_sec = max(0.0, self._pomo_time_left_sec - dt)
            if self._pomo_time_left_sec <= 0.0:
                self._pomo_is_running = False
                self._ambient_toast_time = time.monotonic()
                self._ambient_toast_name = "Focus Session Completed! 🏆"

        # Stopwatch tick (Nixi Feature 08)
        if getattr(self, "_stopwatch_running", False):
            now_m = time.monotonic()
            self._stopwatch_elapsed += (now_m - getattr(self, "_stopwatch_last_tick", now_m))
            self._stopwatch_last_tick = now_m

        # Keep Awake timeout (Nixi Feature 09: 1-hour auto-reset)
        if getattr(self, "_keep_awake_active", False) and time.monotonic() > getattr(self, "_keep_awake_end_time", 0.0):
            self.toggle_keep_awake(False)

        # Windows Pop-ups in Notch: Caps Lock & Num Lock Detection (Hardware Capsules)
        try:
            caps_state = ctypes.windll.user32.GetKeyState(0x14) & 1
            if self._last_caps_lock_state != -1 and caps_state != self._last_caps_lock_state:
                self.show_system_hud("caps", val=caps_state, text="CAPS LOCK ON ⇪" if caps_state else "CAPS LOCK OFF")
            self._last_caps_lock_state = caps_state

            num_state = ctypes.windll.user32.GetKeyState(0x90) & 1
            if getattr(self, "_last_num_lock_state", -1) != -1 and num_state != self._last_num_lock_state:
                self.show_system_hud("num_lock", val=num_state, text="NUM LOCK ON ⇸" if num_state else "NUM LOCK OFF")
            self._last_num_lock_state = num_state
        except Exception:
            pass

        # Dynamic Island Hardware Volume HUD Detection
        now_t = time.monotonic()
        if now_t - getattr(self, "_last_vol_poll_time", 0.0) >= 0.20:
            self._last_vol_poll_time = now_t
            try:
                cur_vol = _win_get_system_volume()
                if abs(cur_vol - getattr(self, "_last_system_volume", cur_vol)) >= 1.0:
                    self._last_system_volume = cur_vol
                    # Only trigger if user is not actively dragging island internal volume slider
                    if getattr(self, "_active_slider", None) != "volume":
                        self.show_system_hud("volume", val=int(round(cur_vol)))
            except Exception:
                pass

        # Dynamic Island Battery & AC Power Toast
        if HAS_PSUTIL and now_t - getattr(self, "_last_batt_poll_time", 0.0) >= 2.5:
            self._last_batt_poll_time = now_t
            try:
                batt = psutil.sensors_battery()
                if batt:
                    plugged = bool(batt.power_plugged)
                    pct = int(batt.percent)
                    last_plugged = getattr(self, "_last_power_plugged", None)
                    if last_plugged is not None and plugged != last_plugged:
                        self.show_system_hud("charging" if plugged else "battery", val=pct, text=f"Charging • {pct}%" if plugged else f"On Battery • {pct}%")
                    elif not plugged and pct <= 18 and not getattr(self, "_low_batt_warned", False):
                        self._low_batt_warned = True
                        self.show_system_hud("low_battery", val=pct, text=f"Battery Low • {pct}%", duration=3.0)
                    elif plugged:
                        self._low_batt_warned = False
                    self._last_power_plugged = plugged
            except Exception:
                pass

        # Dynamic Island USB Removable Drive Detection
        if HAS_PSUTIL and now_t - getattr(self, "_last_disk_poll_time", 0.0) >= 2.0:
            self._last_disk_poll_time = now_t
            try:
                parts = psutil.disk_partitions()
                removable = {p.device.rstrip("\/"): p.mountpoint for p in parts if "removable" in p.opts or p.fstype in ("FAT32", "exFAT")}
                known = getattr(self, "_known_disks", set())
                new_disks = set(removable.keys()) - known
                if known and new_disks:
                    for d in new_disks:
                        self.show_system_hud("usb", val=0, text=f"USB Drive ({d}) Connected", duration=3.5, extra=removable[d])
                self._known_disks = set(removable.keys())
            except Exception:
                pass

        # Smooth metric interpolation
        self._anim_cpu += (self._last_cpu_percent - self._anim_cpu) * min(1.0, dt * 5.0)
        self._anim_ram += (self._last_ram_percent - self._anim_ram) * min(1.0, dt * 5.0)

        # Smooth continuous marquee scrolling for compact & expanded modes with initial reading pause
        if self._compact_ticker_pause > 0.0:
            self._compact_ticker_pause = max(0.0, self._compact_ticker_pause - dt)
        else:
            self._compact_ticker_x += dt * 36.0

        if getattr(self, "_compact_lyric_pause", 0.0) > 0.0:
            self._compact_lyric_pause = max(0.0, self._compact_lyric_pause - dt)
        else:
            self._compact_lyric_ticker_x += dt * 38.0

        if self._music_ticker_pause > 0.0:
            self._music_ticker_pause = max(0.0, self._music_ticker_pause - dt)
        else:
            self._music_ticker_x += dt * 34.0

        # JARVIS Live Talking Words Typewriter Animation & Speech Marquee
        if self._assistant_reply and self._assistant_typewriter_idx < len(self._assistant_reply):
            chars_to_add = max(1, int(dt * 55.0))
            self._assistant_typewriter_idx = min(len(self._assistant_reply), self._assistant_typewriter_idx + chars_to_add)
            self.update()



        if self._is_jarvis_talking or (time.monotonic() - getattr(self, "_jarvis_speech_time", 0.0) < 3.5):
            self._jarvis_compact_ticker_x += dt * 38.0

        # Update JARVIS Chat Input Box placement and visibility
        if self._state == self.STATE_ASSISTANT and self._morph_progress > 0.85:
            w, h = self.width(), self.height()
            input_w = w - 104
            self._chat_input.setGeometry(18, h - 44, input_w, 32)
            if not self._chat_input.isVisible():
                self._chat_input.show()
                self._chat_input.setFocus()
        else:
            if self._chat_input.isVisible():
                self._chat_input.hide()

        # Smart Dynamic Frame Rate / Zero Idle CPU Conservation (0.0% CPU when resting)
        needs_high_fps = (
            self._is_morphing
            or self._is_hovered
            or self._is_genuine_music_playing()
            or self._pomo_is_running
            or getattr(self, "_stopwatch_running", False)
            or (self._state == self.STATE_WEATHER and (bool(self._rain_drops) or bool(self._snow_flakes)))
            or (self._tab_transition_progress < 1.0)
            or self._pet_eye_blink_phase > 0.0
            or self._pet_eye_wink_phase > 0.0
            or abs(self._pet_eye_glance_target_x - self._pet_eye_glance_x) > 0.05
            or abs(getattr(self, "_pet_eye_cursor_target_x", 0.0) - getattr(self, "_pet_eye_cursor_glance_x", 0.0)) > 0.04
            or abs(getattr(self, "_pet_eye_cursor_target_y", 0.0) - getattr(self, "_pet_eye_cursor_glance_y", 0.0)) > 0.04
            or (time.monotonic() - getattr(self, "_last_cursor_move_time", 0.0) < 1.2)
            or abs(self._anim_w - self._target_w) > 0.5
            or abs(self._anim_h - self._target_h) > 0.5
            or (time.monotonic() - getattr(self, "_sys_hud_toast_time", 0.0) < 2.5)
            or (time.monotonic() - getattr(self, "_ambient_toast_time", 0.0) < 2.5)
            or (self._assistant_typewriter_idx < len(self._assistant_reply))
            or self._is_jarvis_talking
            or getattr(self, "_is_voice_listening", False)
            or (self._pet_emotion_timer > 0.0)
            or bool(self._pet_particles)
            or abs(self._pet_bounce_vel) > 0.05
        )

        if needs_high_fps:
            if self._timer.interval() != 16:
                self._timer.setInterval(16)
            self.update()


        else:
            # Idle resting state: throttle to 250ms (0.0% CPU usage)
            if self._timer.interval() != 250:
                self._timer.setInterval(250)
            self.update()



    def _wake_timer(self):
        try:
            if hasattr(self, "_timer") and self._timer is not None:
                if self._timer.interval() != 16:
                    self._timer.setInterval(16)
                if not self._timer.isActive():
                    self._timer.start(16)
            self._last_tick_time = time.monotonic()
            self.update()
        except Exception:
            pass



    def _get_tab_x(self, tab_name: str, w: int) -> int:
        """Centralized position generator for all 9 top right tabs (24.5px spacing)."""
        idx_map = {
            "assistant": 8,
            "music": 7,
            "weather": 6,
            "control": 5,
            "calendar": 4,
            "shelf": 3,
            "map": 2,
            "clipboard": 1,
            "tools": 0,
        }
        idx = idx_map.get(tab_name, 0)
        return int(w - 22 - idx * 24.5)

    def _update_tab_indicator_target(self, tab_name: str, snap: bool = False):
        w = max(self.SIZES[self.STATE_MUSIC][0], int(self._target_w))
        target_x = float(self._get_tab_x(tab_name, w) - 10.0)
        self._indicator_target_x = target_x
        if snap:
            self._indicator_x = target_x
            self._indicator_vel = 0.0
            self._indicator_w = 20.0
            self._indicator_w_vel = 0.0

    def switch_state(self, new_state: str):
        if new_state in self.SIZES:
            self._wake_timer()
            if new_state != self.STATE_COMPACT:
                self._last_expanded_tab = new_state
            else:
                # When collapsing to compact, ensure theater mode is reset for clean next open
                if getattr(self, "_is_theater_mode", False):
                    self._is_theater_mode = False
                    self.SIZES[self.STATE_MUSIC] = (420, 204)

            # Anchor floating center X so it never drifts to the left
            self._floating_center_x = float(self.x() + self.width() / 2.0)

            if new_state == self._state and not self._is_morphing:
                return

            old_state = self._state
            self._prev_state = old_state
            self._prev_h = float(self._current_h)
            self._state = new_state
            tw, th = self.SIZES[new_state]
            self._target_w = float(tw)
            self._target_h = float(th)

            # If switching between expanded tabs: trigger fluid sliding indicator & cross-fade
            if old_state != self.STATE_COMPACT and new_state != self.STATE_COMPACT:
                self._tab_from = old_state
                self._tab_to = new_state
                self._tab_transition_progress = 0.0
                self._update_tab_indicator_target(new_state)
            elif new_state != self.STATE_COMPACT and old_state == self.STATE_COMPACT:
                # Expanding from compact pill
                self._tab_from = new_state
                self._tab_to = new_state
                self._tab_transition_progress = 1.0
                self._update_tab_indicator_target(new_state, snap=True)

            self._is_morphing = True
            self.update()



    def expand_to_state(self, state_id: int):
        mapping = {
            0: self.STATE_COMPACT,
            1: self.STATE_MUSIC,
            2: self.STATE_WEATHER,
            3: self.STATE_CONTROL,
            4: self.STATE_CALENDAR,
            5: self.STATE_MAP,
            6: self.STATE_CLIPBOARD,
            7: self.STATE_TOOLS,
        }
        self.switch_state(mapping.get(state_id, self.STATE_COMPACT))

    def _auto_collapse(self):
        cursor_global = QCursor.pos()
        if self.geometry().contains(cursor_global):
            self._is_hovered = True
            return
        self._is_hovered = False
        if self._state != self.STATE_COMPACT:
            self._last_expanded_tab = self._state
            self.switch_state(self.STATE_COMPACT)
            if getattr(self, "_auto_retract", True) and not self._is_genuine_music_playing() and not self._pinned:
                self._retract_timer.start(2500)

    def _auto_retract_timeout(self):
        cursor_global = QCursor.pos()
        if self.geometry().contains(cursor_global):
            return
        if not self._is_genuine_music_playing() and not self._pinned:
            self.retract()

    def retract(self):
        """Tuck the island into a discreet top trigger icon."""
        self._is_retracted = True
        self._target_w = 52.0
        self._target_h = 10.0
        self._wake_timer()
        self.update()



    def unretract(self):
        """Expand the island smoothly down from the trigger icon."""
        self._is_retracted = False
        if hasattr(self, "_retract_timer") and self._retract_timer.isActive():
            self._retract_timer.stop()
        is_flush = self._is_flush_notch()
        if self._is_genuine_music_playing():
            self._target_w = 345.0 if is_flush else 315.0
            self._target_h = 44.0
        else:
            self._target_w = 255.0 if is_flush else 235.0
            self._target_h = 40.0
        self._wake_timer()
        self.update()



    def toggle_retract(self):
        if self._is_retracted:
            self.unretract()
        else:
            self.retract()

    def toggle_auto_retract(self):
        self._auto_retract = not getattr(self, "_auto_retract", False)
        if self._settings:
            self._settings.island_auto_retract = self._auto_retract
            self._settings.save()
        status_str = "Auto-Retract: ON (Tucks into small icon when idle)" if self._auto_retract else "Auto-Retract: OFF (Always stays on screen)"
        self._ambient_toast_time = time.monotonic()
        self._ambient_toast_name = status_str
        self._wake_timer()
        self.update()

    def toggle_lyrics_view(self, show: Optional[bool] = None):
        """Toggle between standard player view and synchronized live lyrics view."""
        if show is None:
            self._music_show_lyrics = not getattr(self, "_music_show_lyrics", False)
        else:
            self._music_show_lyrics = bool(show)

        if self._settings:
            self._settings.set("compact_show_lyrics", self._music_show_lyrics, save_now=True)

        status_str = "Lyrics ON (Showing in Notch & Player) 🎵" if self._music_show_lyrics else "Lyrics OFF (Showing Song Details) 🎶"
        self._ambient_toast_time = time.monotonic()
        self._ambient_toast_name = status_str

        if self._state == self.STATE_MUSIC:
            self.SIZES[self.STATE_MUSIC] = (420, 204)
            tw, th = self.SIZES[self.STATE_MUSIC]
            self._target_w = float(tw)
            self._target_h = float(th)
            self._is_morphing = False
            self._wake_timer()
            self.update()
        else:
            self._wake_timer()
            self.update()

    def toggle_theater_mode(self):
        """Toggles between standard island card view (420x192) and full responsive theater mode with smooth fluid animation."""
        if getattr(self, "_is_theater_mode", False) or self.width() >= 540 or self.height() >= 260:
            self.restore_from_theater_mode()
        else:
            self.expand_to_theater_mode()

    def expand_to_theater_mode(self):
        """Smoothly animates island to full responsive cinema theater player with device width."""
        screen = self.screen() or QGuiApplication.primaryScreen()
        geo = screen.geometry() if screen else QRect(0, 0, 1920, 1080)
        th_w = min(1280, geo.width() - 32)
        th_h = min(680, geo.height() - 48)

        self._is_theater_mode = True
        self.SIZES[self.STATE_MUSIC] = (th_w, th_h)
        self._prev_state = self._state
        self._prev_h = float(self._current_h)
        self._target_w = float(th_w)
        self._target_h = float(th_h)
        self._state = self.STATE_MUSIC
        self._is_morphing = True

        # Pin horizontal center coordinate so it expands symmetrically with ZERO leftward drift
        self._floating_center_x = float(self.x() + self.width() / 2.0)

        self._ambient_toast_time = time.monotonic()
        self._ambient_toast_name = "Player: Fullscreen Cinema Mode"
        self._wake_timer()
        self.update()

    def restore_from_theater_mode(self):
        """Smoothly animates island back to standard card size (420x192)."""
        self._is_theater_mode = False
        std_w, std_h = (420, 204)
        self.SIZES[self.STATE_MUSIC] = (std_w, std_h)
        self._prev_state = self.STATE_MUSIC
        self._prev_h = float(self._current_h)
        self._target_w = float(std_w)
        self._target_h = float(std_h)
        self._state = self.STATE_MUSIC
        self._is_morphing = True

        # Pin horizontal center coordinate so it contracts symmetrically with ZERO leftward drift
        self._floating_center_x = float(self.x() + self.width() / 2.0)

        self._ambient_toast_time = time.monotonic()
        self._ambient_toast_name = "Player: Standard Card View"
        self._wake_timer()
        self.update()


    def _open_settings_dialog(self):
        try:
            from settings import SettingsDialog
            dlg = SettingsDialog(self._settings, parent=None)
            dlg.settings_changed.connect(self._on_settings_dialog_applied)
            dlg.finished.connect(lambda _res: self._on_settings_dialog_applied(self._settings))
            dlg.exec()
        except Exception as e:
            print("Failed to open settings dialog:", e)

    def _on_settings_dialog_applied(self, s):
        if hasattr(s, "island_style"):
            self.set_island_style(s.island_style)
        if hasattr(s, "background_opacity"):
            self.set_background_opacity(s.background_opacity)
        if hasattr(s, "notch_style"):
            self.set_notch_style(s.notch_style)
        if hasattr(s, "weather_location"):
            self.set_weather_location(s.weather_location)
        if hasattr(s, "dock_mode"):
            self._dock_mode = s.dock_mode
        if hasattr(s, "island_eye_color"):
            c_str = s.get("island_eye_color", "")
            if c_str:
                col = parse_rgba_color(c_str)
                if col.isValid():
                    self.set_custom_eye_color(col)
        # Broadcast settings to all active desktop pet windows
        try:
            from pet_manager import PetManager
            for pet in PetManager.instance().pets:
                if hasattr(pet, "_apply_settings"):
                    pet._apply_settings(s)
        except Exception:
            pass
        self.update()



    def _open_google_maps(self, query: Optional[str] = None, mode: str = "search"):
        """Launches Google Maps centered on the location directly in Brave Browser or default browser."""
        if not query:
            if self._weather and self._weather.current_weather and self._weather.current_weather.city:
                query = self._weather.current_weather.city
            elif self._settings and hasattr(self._settings, "weather_location") and self._settings.weather_location:
                query = self._settings.weather_location
            else:
                query = "Kochi, Kerala, India"

        clean_q = query.strip()
        encoded = urllib.parse.quote(clean_q)

        if mode == "directions":
            url = f"https://www.google.com/maps/dir/?api=1&destination={encoded}"
        elif mode == "satellite":
            url = f"https://www.google.com/maps/search/{encoded}/@?data=!3m1!1e3"
        elif mode == "traffic":
            url = f"https://www.google.com/maps/search/{encoded}/@?layer=t"
        else:
            url = f"https://www.google.com/maps/search/?api=1&query={encoded}"

        self._open_url_in_brave_or_default(url)

    def _open_chatgpt(self):
        """Launches ChatGPT directly in user's logged-in Brave Browser or default browser."""
        import os
        brave_paths = [
            r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe",
            r"C:\Program Files (x86)\BraveSoftware\Brave-Browser\Application\brave.exe",
            os.path.expandvars(r"%LOCALAPPDATA%\BraveSoftware\Brave-Browser\Application\brave.exe"),
        ]
        for p in brave_paths:
            if os.path.exists(p):
                try:
                    subprocess.Popen([p, "https://chatgpt.com"])
                    return
                except Exception:
                    pass
        try:
            QDesktopServices.openUrl(QUrl("https://chatgpt.com"))
        except Exception:
            webbrowser.open("https://chatgpt.com")

    def _trigger_volume_hud(self, action: str):
        self._volume_hud_time = time.monotonic()
        self._volume_hud_action = action
        try:
            cur = _win_get_system_volume()
            if action == "+":
                val = min(100, int(round(cur)) + 2)
                _win_set_system_volume(float(val))
            elif action == "-":
                val = max(0, int(round(cur)) - 2)
                _win_set_system_volume(float(val))
            elif action == "mute":
                val = int(round(cur))
            else:
                val = int(round(cur))
        except Exception:
            if action == "+":
                self._media.volume_up()
                self._volume_hud_level = min(100, self._volume_hud_level + 2)
            elif action == "-":
                self._media.volume_down()
                self._volume_hud_level = max(0, self._volume_hud_level - 2)
            val = int(self._volume_hud_level)
        self._volume_hud_level = val
        self._control_volume = float(val)
        self.show_system_hud("volume", val=val)
        self._wake_timer()
        self.update()



    # ── Clipboard Monitor & URL Detection ───────────────────────────────────

    def _check_initial_clipboard(self):
        try:
            text = self._clipboard.text()
            if text:
                self._process_clipboard_text(text, notify=False)
        except Exception:
            pass

    def _on_clipboard_changed(self):
        try:
            now = time.monotonic()
            if now - self._last_clipboard_change_time < 0.08:
                return
            self._last_clipboard_change_time = now
            text = self._clipboard.text()
            if text and text != self._last_clipboard_text:
                self._process_clipboard_text(text, notify=True)
        except Exception:
            pass

    def _process_clipboard_text(self, text: str, notify: bool = True):
        self._last_clipboard_text = text
        self._clipboard_char_count = len(text)

        # Fast preview slice (max 300 chars for drawing)
        self._clipboard_preview_text = text[:300]
        preview = text[:2000]

        # Fast non-blocking word count calculation
        if len(text) > 10000:
            self._clipboard_word_count = len(text[:10000].split())
        else:
            self._clipboard_word_count = len(text.split())

        clean = text[:500].strip()

        # 1. History Reel (stored as clean lightweight strings)
        if clean:
            if clean in self._clipboard_history:
                self._clipboard_history.remove(clean)
            self._clipboard_history.insert(0, clean)
            if len(self._clipboard_history) > 5:
                self._clipboard_history = self._clipboard_history[:5]

        # 2. Check for URL / Link (search on first 1500 chars)
        url_match = re.search(r"(https?://[^\s]+|www\.[^\s]+)", preview, re.IGNORECASE)
        if url_match:
            url = url_match.group(0)
            if not url.startswith("http"):
                url = "https://" + url
            self._last_clipboard_url = url
        else:
            self._last_clipboard_url = None

        # 3. Check for Hex Color Code (#RGB, #RRGGBB, #RRGGBBAA on short text)
        if len(clean) <= 12:
            hex_match = re.match(r"^#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6}|[0-9a-fA-F]{8})$", clean)
            if hex_match:
                self._clipboard_color_hex = hex_match.group(0)
            else:
                self._clipboard_color_hex = None
        else:
            self._clipboard_color_hex = None

        # 4. Check for Math Calculation Expression (only on clean short text < 80 chars)
        if len(clean) <= 80:
            clean_math = re.sub(r"[^0-9\.\+\-\*\/\(\)\%\s]", "", clean)
            if clean_math and any(op in clean_math for op in ["+", "-", "*", "/", "%"]) and len(clean_math) >= 3:
                try:
                    res = eval(clean_math, {"__builtins__": None}, {})
                    if isinstance(res, (int, float)):
                        self._clipboard_calc_result = f"{res:.4g}" if isinstance(res, float) else str(res)
                    else:
                        self._clipboard_calc_result = None
                except Exception:
                    self._clipboard_calc_result = None
            else:
                self._clipboard_calc_result = None
        else:
            self._clipboard_calc_result = None

        if notify:
            self._clipboard_banner_time = time.monotonic()
            self.switch_state(self.STATE_CLIPBOARD)
            self._collapse_timer.start(7000)

    def _open_last_url(self):
        if self._last_clipboard_url:
            self._open_url_in_brave_or_default(self._last_clipboard_url)

    def _open_url_in_brave_or_default(self, url: str):
        import os
        brave_paths = [
            r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe",
            r"C:\Program Files (x86)\BraveSoftware\Brave-Browser\Application\brave.exe",
            os.path.expandvars(r"%LOCALAPPDATA%\BraveSoftware\Brave-Browser\Application\brave.exe"),
        ]
        for p in brave_paths:
            if os.path.exists(p):
                try:
                    subprocess.Popen([p, url])
                    return
                except Exception:
                    pass
        try:
            QDesktopServices.openUrl(QUrl(url))
        except Exception:
            webbrowser.open(url)

    def _search_google(self):
        if self._last_clipboard_text:
            query = urllib.parse.quote(self._last_clipboard_text[:120])
            url = f"https://www.google.com/search?q={query}"
            self._open_url_in_brave_or_default(url)

    def _ask_chatgpt_with_clipboard(self):
        if self._last_clipboard_text:
            query = urllib.parse.quote(self._last_clipboard_text[:200])
            url = f"https://chatgpt.com/?q={query}"
            self._open_url_in_brave_or_default(url)
        else:
            self._open_chatgpt()

    def _copy_again(self):
        if self._last_clipboard_text:
            self._clipboard.setText(self._last_clipboard_text)
            self._clipboard_copy_feedback = time.monotonic()
            self.update()



    def _copy_calc_result(self):
        if self._clipboard_calc_result:
            self._clipboard.setText(self._clipboard_calc_result)
            self._last_clipboard_text = self._clipboard_calc_result
            self._clipboard_copy_feedback = time.monotonic()
            self.update()



    def _toggle_case(self):
        if not self._last_clipboard_text or len(self._last_clipboard_text) > 50000:
            return
        t = self._last_clipboard_text
        if t.isupper():
            new_t = t.lower()
        elif t.islower():
            new_t = t.title()
        else:
            new_t = t.upper()
        self._last_clipboard_text = new_t
        self._clipboard.setText(new_t)
        self._clipboard_copy_feedback = time.monotonic()
        self.update()



    def _clear_clipboard(self):
        try:
            self._clipboard.clear()
        except Exception:
            pass
        self._last_clipboard_text = ""
        self._clipboard_preview_text = ""
        self._clipboard_word_count = 0
        self._clipboard_char_count = 0
        self._last_clipboard_url = None
        self._clipboard_calc_result = None
        self._clipboard_color_hex = None
        self.update()



    def _restore_clip_history(self, idx: int):
        if 0 <= idx < len(self._clipboard_history):
            text = self._clipboard_history[idx]
            self._last_clipboard_text = text
            self._clipboard.setText(text)
            self._process_clipboard_text(text, notify=False)
            self._clipboard_copy_feedback = time.monotonic()
            self.update()



    # ── Media Events & Ambient Color Extraction ──────────────────────────────

    def _get_scaled_album_art(self, thumb_bytes: bytes, target_size: int):
        """
        Returns an ultra-high-quality, high-DPI retina cached QPixmap of the cover art.
        Cached in memory by (hash, target_size, dpr) so JPEG decoding and scaling happen ONCE,
        achieving 0% CPU overhead and zero RAM churn on subsequent frames.
        """
        if not thumb_bytes:
            return None

        dpr = max(1.0, self.devicePixelRatioF())
        cache_key = (len(thumb_bytes), hash(thumb_bytes[:64]), int(target_size), round(dpr, 2))

        if hasattr(self, "_art_cache_key") and self._art_cache_key == cache_key and getattr(self, "_cached_art_pix", None) is not None:
            return self._cached_art_pix

        raw_pix = QPixmap()
        if not raw_pix.loadFromData(thumb_bytes):
            return None

        phys_size = max(1, int(round(target_size * dpr)))
        scaled_pix = raw_pix.scaled(
            phys_size,
            phys_size,
            Qt.AspectRatioMode.KeepAspectRatioByExpanding,
            Qt.TransformationMode.SmoothTransformation
        )
        scaled_pix.setDevicePixelRatio(dpr)

        self._art_cache_key = cache_key
        self._cached_art_pix = scaled_pix
        return scaled_pix

    def _extract_artwork_color(self, thumb_data) -> Optional[QColor]:
        """Fast sampling to extract dominant vibrant accent color from album artwork tuned for dark UI."""
        try:
            pix = None
            if isinstance(thumb_data, QPixmap):
                pix = thumb_data
            elif isinstance(thumb_data, QImage):
                pix = QPixmap.fromImage(thumb_data)
            elif isinstance(thumb_data, (bytes, bytearray, memoryview)):
                pix = QPixmap()
                if not pix.loadFromData(thumb_data):
                    return None
            else:
                return None

            if not pix or pix.isNull():
                return None

            img = pix.toImage().scaled(32, 32, Qt.AspectRatioMode.IgnoreAspectRatio, Qt.TransformationMode.FastTransformation)
            best_score = -1.0
            best_col = None
            r_tot, g_tot, b_tot, count = 0, 0, 0, 0
            for y in range(img.height()):
                for x in range(img.width()):
                    c = img.pixelColor(x, y)
                    val = c.value()
                    sat = c.hsvSaturationF()
                    # Filter out near-black, washed-out white, and low saturation
                    if 35 < val < 248 and sat > 0.16:
                        score = sat * 2.2 + (val / 255.0) * 1.1
                        if score > best_score:
                            best_score = score
                            best_col = c
                        r_tot += c.red()
                        g_tot += c.green()
                        b_tot += c.blue()
                        count += 1
            if best_col is not None:
                # Tune for dark UI: ensure saturation 0.45..0.85 and value 0.85..0.98
                h = best_col.hsvHueF()
                s = max(0.45, min(0.85, best_col.hsvSaturationF()))
                v = max(0.85, min(0.98, best_col.valueF()))
                return QColor.fromHsvF(h, s, v)
            elif count > 0:
                avg_c = QColor(r_tot // count, g_tot // count, b_tot // count)
                h = avg_c.hsvHueF()
                s = max(0.45, min(0.85, avg_c.hsvSaturationF()))
                v = max(0.85, min(0.98, avg_c.valueF()))
                return QColor.fromHsvF(h, s, v)
        except Exception:
            pass
        return None

    def _on_media_updated(self, info: MediaInfo):
        from media_service import is_valid_media_info
        if not is_valid_media_info(info):
            self._last_media_info = MediaInfo()
            self._extracted_art_color = None
            self.update()


            return

        self._last_media_info = info
        if info.duration_sec > 0:
            self._playback_dur_sec = info.duration_sec
        if not self._is_scrubbing and info.position_sec >= 0:
            target = info.current_position()
            if abs(target - self._playback_pos_sec) > 1.5:
                self._playback_pos_sec = target
        if info.thumbnail_bytes and len(info.thumbnail_bytes) != self._last_thumb_len:
            self._last_thumb_len = len(info.thumbnail_bytes)
            self._extracted_art_color = self._extract_artwork_color(info.thumbnail_bytes)
        elif not info.thumbnail_bytes:
            self._last_thumb_len = 0
            self._extracted_art_color = None
        if self._is_genuine_music_playing():
            self._wake_timer()
        self.update()



    def _on_playback_changed(self, is_playing: bool):
        if self._last_media_info:
            self._last_media_info.is_playing = is_playing
        self.update()



    def _on_bluetooth_updated(self, info: BluetoothInfo):
        self._last_bluetooth_info = info
        self.update()



    # ── Mouse & Interaction ──────────────────────────────────────────────────

    def wheelEvent(self, event):
        delta = event.angleDelta().y()
        w, h = self.width(), self.height()
        pos = event.position().toPoint()
        modifiers = event.modifiers()

        # If retracted into top bezel, any mouse scroll smoothly unretracts the island
        if getattr(self, "_is_retracted", False):
            self.unretract()

        self._last_user_activity_time = time.monotonic()

        # In expanded modes: Scroll UP at the top header area collapses back to compact notch
        if self._state != self.STATE_COMPACT:
            if delta > 0 and pos.y() < 34:
                self._last_expanded_tab = self._state
                self.switch_state(self.STATE_COMPACT)
                event.accept()
                return

        # 1. In lyrics view: Ctrl/Shift + wheel nudges fine-grained timing calibration (±0.25s) with live toast; regular wheel seeks
        if getattr(self, "_music_show_lyrics", False) and self._state == self.STATE_MUSIC and 35 <= pos.y() <= 125 and pos.x() < w - 30:
            if modifiers & (Qt.KeyboardModifier.ControlModifier | Qt.KeyboardModifier.ShiftModifier):
                step = 0.25 if delta > 0 else -0.25
                self._lyrics_offset_sec = getattr(self, "_lyrics_offset_sec", 0.0) + step
                if self._last_media_info:
                    c_t, c_a = LyricsEngine.clean_song_info(self._last_media_info.title, self._last_media_info.artist)
                    LyricsEngine.update_cached_offset(c_t, c_a, self._lyrics_offset_sec)
                sign = "+" if self._lyrics_offset_sec > 0 else ""
                self.show_system_hud("calibration", text=f"⏱ SYNC: {sign}{self._lyrics_offset_sec:.2f}s", duration=1.5)
                self.update()
                event.accept()
                return
            if self._lyrics_lines:
                if delta < 0:
                    self._lyrics_active_idx = min(len(self._lyrics_lines) - 1, self._lyrics_active_idx + 1)
                else:
                    self._lyrics_active_idx = max(0, self._lyrics_active_idx - 1)
                t_sec = self._lyrics_lines[self._lyrics_active_idx][0]
                self._playback_pos_sec = t_sec
                self._media.seek_to(t_sec)
                self.update()
                event.accept()
                return

        # 2. Scrolling specifically over the right carousel dots area switches pages (5 cards)
        if pos.x() >= w - 32 and self._state != self.STATE_COMPACT:
            page_list = [self.STATE_MUSIC, self.STATE_CALENDAR, self.STATE_TOOLS, self.STATE_CONTROL, self.STATE_WEATHER]
            if self._state in page_list:
                cur_idx = page_list.index(self._state)
                if delta < 0:
                    next_idx = (cur_idx + 1) % len(page_list)
                else:
                    next_idx = (cur_idx - 1) % len(page_list)
                self.switch_state(page_list[next_idx])
                event.accept()
                return

        # 3. Dynamic Island Volume Control on Scroll with HUD animation across ALL states!
        if delta > 0:
            self._trigger_volume_hud("+")
        elif delta < 0:
            self._trigger_volume_hud("-")
        event.accept()

    def _get_button_style(self, btn_name: str, base_bg: Optional[QColor] = None, base_border: Optional[QColor] = None):
        """Calculates dynamic tactile hover glow, micro-spring scale bounce, and press depression for any button."""
        h_val = self._btn_hover_anim.get(btn_name, 0.0)
        p_val = self._btn_press_anim.get(btn_name, 0.0)
        scale = (1.0 + 0.045 * h_val) * (1.0 - 0.08 * p_val)

        if base_bg is None:
            base_bg = QColor(255, 255, 255, 18)

        alpha = min(255, int(base_bg.alpha() + h_val * 60 - p_val * 20))
        r = min(255, int(base_bg.red() + h_val * 35))
        g = min(255, int(base_bg.green() + h_val * 35))
        b = min(255, int(base_bg.blue() + h_val * 35))
        bg_color = QColor(r, g, b, max(0, alpha))

        if base_border is None:
            border_alpha = int(25 + h_val * 85)
            border_color = QColor(255, 255, 255, border_alpha)
        else:
            border_alpha = min(255, int(base_border.alpha() + h_val * 65))
            border_color = QColor(base_border.red(), base_border.green(), base_border.blue(), border_alpha)

        return bg_color, border_color, scale, h_val, p_val

    def enterEvent(self, event):
        self._is_hovered = True
        self._last_user_activity_time = time.monotonic()
        self._wake_timer()
        self._collapse_timer.stop()
        if hasattr(self, "_retract_timer") and self._retract_timer.isActive():
            self._retract_timer.stop()

        # When retracted: hovering over the small trigger icon immediately brings our island down!
        if getattr(self, "_is_retracted", False) or self.height() <= 16:
            self.unretract()
            super().enterEvent(event)
            return

        super().enterEvent(event)

    def leaveEvent(self, event):
        self._is_hovered = False
        self._is_scrubbing = False
        self._last_user_activity_time = time.monotonic()
        if self._state != self.STATE_COMPACT:
            self._collapse_timer.start(1200)
        if getattr(self, "_auto_retract", True) and not self._is_genuine_music_playing() and not self._pinned:
            self._retract_timer.start(2500)
        super().leaveEvent(event)

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            self._shelf_is_drag_over = True
            if self._state != self.STATE_SHELF:
                self.switch_state(self.STATE_SHELF)
            self._wake_timer()
            self.update()



    def dragMoveEvent(self, event: QDragMoveEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dragLeaveEvent(self, event: QDragLeaveEvent):
        self._shelf_is_drag_over = False
        self.update()



    def dropEvent(self, event: QDropEvent):
        self._shelf_is_drag_over = False
        if event.mimeData().hasUrls():
            added_any = False
            existing = {f.get("path") for f in self._shelf_files}
            for url in event.mimeData().urls():
                lpath = url.toLocalFile()
                if lpath and os.path.exists(lpath) and lpath not in existing:
                    p = Path(lpath)
                    try:
                        sz = os.path.getsize(lpath)
                    except Exception:
                        sz = 0
                    self._shelf_files.append({
                        "path": lpath,
                        "name": p.name,
                        "stem": p.stem,
                        "ext": p.suffix.upper().lstrip("."),
                        "size": sz,
                        "time": time.time()
                    })
                    existing.add(lpath)
                    added_any = True
            if added_any:
                event.acceptProposedAction()
                if self._state != self.STATE_SHELF:
                    self.switch_state(self.STATE_SHELF)
                self._wake_timer()
                self.update()



    def _get_button_at(self, pos: QPoint) -> Optional[str]:
        w, h = self.width(), self.height()
        if getattr(self, "_is_retracted", False) or h <= 18:
            return "retracted_icon"

        if self._state == self.STATE_COMPACT or h < 55:
            # Subtle tuck handle at top center
            if pos.y() <= 10 and (w / 2 - 20) <= pos.x() <= (w / 2 + 20):
                return "compact_tuck"
            # Tuck chevron at top right
            if pos.y() <= 16 and pos.x() >= (w - 24):
                return "compact_tuck"
            return "compact_pill"

        # Top-left subtle collapse indicator notch and theater/maximize toggle
        if pos.y() < 28:
            if pos.x() < 42:
                return "collapse"
            if 42 <= pos.x() <= 72:
                return "theater_toggle"

        # Tabs at top-right (active across all 9 tabs)
        if pos.y() < 30:
            for tab_id in ["assistant", "music", "weather", "control", "calendar", "shelf", "map", "clipboard", "tools"]:
                tx = self._get_tab_x(tab_id, w)
                if tx - 12 <= pos.x() <= tx + 14:
                    return f"tab_{tab_id}"

        if self._state == self.STATE_ASSISTANT:
            if (w - 80 <= pos.x() <= w - 48) and (h - 46 <= pos.y() <= h - 10):
                return "assistant_send"
            if (w - 46 <= pos.x() <= w - 12) and (h - 46 <= pos.y() <= h - 10):
                return "assistant_mic"
            if 170 <= pos.y() <= 198:
                chip_xs = [16, 86, 156, 244, 328]
                chip_widths = [64, 64, 82, 78, 68]
                for idx, (cx, cw) in enumerate(zip(chip_xs, chip_widths)):
                    if cx <= pos.x() <= cx + cw:
                        return f"chip_{idx}"

        elif self._state == self.STATE_MUSIC:
            if getattr(self, "_is_theater_mode", False) or w >= 540 or h >= 260:
                left_w = min(560, max(290, int(w * 0.46)))
                bar_y = getattr(self, "_theater_bar_y", h - 96)
                track_x = 36
                track_w = left_w - 72
                if abs(pos.y() - bar_y) <= 14 and track_x - 10 <= pos.x() <= track_x + track_w + 10:
                    return "theater_scrub"
                ctrl_y = getattr(self, "_theater_ctrl_y", h - 48)
                cx = left_w // 2
                if (pos.x() - (cx - 55)) ** 2 + (pos.y() - ctrl_y) ** 2 <= 24 ** 2:
                    return "prev"
                if (pos.x() - cx) ** 2 + (pos.y() - ctrl_y) ** 2 <= 30 ** 2:
                    return "play"
                if (pos.x() - (cx + 55)) ** 2 + (pos.y() - ctrl_y) ** 2 <= 24 ** 2:
                    return "next"
                if (pos.x() - (cx - 108)) ** 2 + (pos.y() - ctrl_y) ** 2 <= 22 ** 2:
                    return "theater_wave_cycle"
                if (pos.x() - (cx + 108)) ** 2 + (pos.y() - ctrl_y) ** 2 <= 22 ** 2:
                    return "lyrics_toggle"
                if hasattr(self, "_theater_lyrics_rects"):
                    for l_idx, r in self._theater_lyrics_rects.items():
                        if r.contains(pos):
                            return f"theater_lyric_{l_idx}"
                return None

            ctrl_y = 164
            cx = w // 2
            if (pos.x() - (w - 56)) ** 2 + (pos.y() - ctrl_y) ** 2 <= 22 ** 2:
                return "lyrics_toggle"
            if (pos.x() - (cx - 48)) ** 2 + (pos.y() - ctrl_y) ** 2 <= 20 ** 2:
                return "prev"
            if (pos.x() - cx) ** 2 + (pos.y() - ctrl_y) ** 2 <= 26 ** 2:
                return "play"
            if (pos.x() - (cx + 48)) ** 2 + (pos.y() - ctrl_y) ** 2 <= 20 ** 2:
                return "next"
            bar_y = 130 if getattr(self, "_music_show_lyrics", False) else 124
            if abs(pos.y() - bar_y) <= 12 and 55 <= pos.x() <= w - 55:
                return "scrub"
            if 18 <= pos.x() <= 88 and 34 <= pos.y() <= 104:
                return "album_art"

        elif self._state == self.STATE_SHELF:
            # Subheader buttons: Phone QR, Snip and Clear all
            if w - 232 <= pos.x() <= w - 152 and 26 <= pos.y() <= 50:
                return "shelf_phone_qr"
            if w - 150 <= pos.x() <= w - 80 and 26 <= pos.y() <= 50:
                return "shelf_snip"
            if w - 74 <= pos.x() <= w - 18 and 26 <= pos.y() <= 50:
                return "shelf_clear_all"

            # Empty zone quick action helper buttons (y = 138 to 166)
            if len(self._shelf_files) == 0:
                if 138 <= pos.y() <= 168:
                    if 18 <= pos.x() <= 106:
                        return "shelf_phone_qr"
                    elif 114 <= pos.x() <= 202:
                        return "shelf_snip"
                    elif 210 <= pos.x() <= 298:
                        return "shelf_paste"
                    elif 306 <= pos.x() <= 394:
                        return "shelf_browse"
            else:
                # Populated state: Browse file button at bottom right
                if w - 90 <= pos.x() <= w - 18 and 166 <= pos.y() <= 190:
                    return "shelf_browse"
                if len(self._shelf_files) > 4:
                    if pos.x() <= 24 and 75 <= pos.y() <= 145:
                        return "shelf_prev"
                    if pos.x() >= w - 24 and 75 <= pos.y() <= 145:
                        return "shelf_next"

            # File chips and remove buttons
            if getattr(self, '_shelf_item_rects', None):
                for f_idx, r in self._shelf_item_rects.items():
                    if r.contains(pos):
                        del_r = QRect(r.right() - 22, r.top() + 4, 18, 18)
                        if del_r.contains(pos):
                            return f"shelf_del_{f_idx}"
                        return f"shelf_file_{f_idx}"

        elif self._state == self.STATE_WEATHER:
            if 16 <= pos.x() <= 166 and 76 <= pos.y() <= 136:
                return "weather_city"
            if h >= 120 and pos.x() >= w - 45 and pos.y() >= h - 35:
                return "collapse"

        elif self._state == self.STATE_CONTROL:
            if 34 <= pos.y() <= 78:
                if 18 <= pos.x() <= 204:
                    return "ctrl_tile_wifi"
                elif 216 <= pos.x() <= 402:
                    return "ctrl_tile_taskbar"
            elif 86 <= pos.y() <= 130:
                if 18 <= pos.x() <= 204:
                    return "ctrl_tile_bt"
                elif 216 <= pos.x() <= 402:
                    return "ctrl_tile_notch"
            elif 136 <= pos.y() <= 164:
                pill_w = 58
                pill_gap = 7
                pill_start_x = 78
                tb_btn_ids = ["ctrl_tb_clear", "ctrl_tb_acrylic", "ctrl_tb_blur", "ctrl_tb_black", "ctrl_tb_default"]
                for i, b_id in enumerate(tb_btn_ids):
                    px = pill_start_x + i * (pill_w + pill_gap)
                    if px <= pos.x() <= px + pill_w:
                        return b_id
            elif 168 <= pos.y() <= 204:
                circle_xs = [48, 112, 176, 244, 308, 372]
                circle_btns = [
                    "ctrl_icon_moon", "ctrl_icon_battery", "ctrl_icon_apps",
                    "ctrl_icon_bell", "ctrl_icon_settings", "ctrl_icon_refresh"
                ]
                for cx, bname in zip(circle_xs, circle_btns):
                    if (pos.x() - cx) ** 2 + (pos.y() - 186) ** 2 <= 18 ** 2:
                        return bname
            elif 212 <= pos.y() <= 238:
                if 100 <= pos.x() <= 356:
                    return "ctrl_slider_volume"
                elif 18 <= pos.x() <= 100:
                    return "ctrl_btn_mute"
            elif 242 <= pos.y() <= 268:
                if 100 <= pos.x() <= 356:
                    return "ctrl_slider_brightness"

        elif self._state == self.STATE_CALENDAR:
            if 88 <= pos.y() <= 116:
                if 238 <= pos.x() <= 312:
                    return "pomo_start_pause"
                elif 320 <= pos.x() <= 390:
                    return "pomo_reset"
            elif 126 <= pos.y() <= 154:
                if 238 <= pos.x() <= 312:
                    return "pomo_preset_5"
                elif 320 <= pos.x() <= 390:
                    return "pomo_preset_15"
            elif 162 <= pos.y() <= 190:
                if 238 <= pos.x() <= 312:
                    return "pomo_preset_25"
                elif 320 <= pos.x() <= 390:
                    return "pomo_preset_50"

        elif self._state == self.STATE_MAP:
            if self._map_view_mode == "panoramic":
                if (w - 58) <= pos.x() <= (w - 26) and 28 <= pos.y() <= 58:
                    return "map_compass"
                if 104 <= pos.y() <= 136:
                    c_w = (w - 32 - 36) // 4
                    rx = 16
                    if rx <= pos.x() <= rx + c_w + 6:
                        return "map_chip_split"
                    elif rx + c_w + 6 <= pos.x() <= rx + (c_w + 6) * 2:
                        return "map_chip_traffic"
                    elif rx + (c_w + 6) * 2 <= pos.x() <= rx + (c_w + 6) * 3:
                        return "map_chip_reset"
                    elif rx + (c_w + 6) * 3 <= pos.x() <= w - 16:
                        return "map_chip_open"
                if 16 <= pos.x() <= w - 16 and 28 <= pos.y() <= 104:
                    return "map_body"
            else:
                if 16 <= pos.x() <= 156 and 28 <= pos.y() <= 136:
                    return "map_compass"
                if 104 <= pos.y() <= 136:
                    rw = w - 180
                    rx = 164
                    c_w = (rw - 28) // 4
                    if rx <= pos.x() <= rx + c_w + 5:
                        return "map_chip_panoramic"
                    elif rx + c_w + 5 <= pos.x() <= rx + (c_w + 5) * 2:
                        return "map_chip_traffic"
                    elif rx + (c_w + 5) * 2 <= pos.x() <= rx + (c_w + 5) * 3:
                        return "map_chip_reset"
                    elif rx + (c_w + 5) * 3 <= pos.x() <= w - 16:
                        return "map_chip_open"
                if 164 <= pos.x() <= w - 16 and 28 <= pos.y() <= 104:
                    return "map_body"

        elif self._state == self.STATE_CLIPBOARD:
            if 28 <= pos.y() <= 46:
                hx = 16
                for idx in range(min(4, len(self._clipboard_history))):
                    chip_w = 84
                    if hx <= pos.x() <= hx + chip_w:
                        return f"clip_hist_{idx}"
                    hx += chip_w + 6
            if 106 <= pos.y() <= 144:
                if 16 <= pos.x() <= 82:
                    return "clip_act_link"
                elif 89 <= pos.x() <= 155:
                    return "clip_act_gpt"
                elif 162 <= pos.x() <= 228:
                    return "clip_act_case"
                elif 235 <= pos.x() <= 301:
                    return "clip_act_copy"
                elif 308 <= pos.x() <= 374:
                    return "clip_act_clear"

        elif self._state == self.STATE_TOOLS:
            if 16 <= pos.x() <= w - 16 and 76 <= pos.y() <= 108:
                return "tool_bluetooth"
            btn_y = h - 38
            if btn_y <= pos.y() <= btn_y + 30:
                if 16 <= pos.x() <= 64:
                    return "tool_snip"
                elif 68 <= pos.x() <= 116:
                    return "tool_wallpaper"
                elif 120 <= pos.x() <= 168:
                    return "tool_calc"
                elif 172 <= pos.x() <= 220:
                    return "tool_notes"
                elif 224 <= pos.x() <= 272:
                    return "tool_gpt"
                elif 276 <= pos.x() <= 324:
                    return "tool_mute"
                elif 328 <= pos.x() <= 376:
                    return "tool_lock"

        elif self._state == self.STATE_NOTIFICATION:
            if w - 74 <= pos.x() <= w - 42 and (h - 36) // 2 <= pos.y() <= (h + 36) // 2:
                return "notif_open"
            elif w - 38 <= pos.x() <= w - 10 and (h - 36) // 2 <= pos.y() <= (h + 36) // 2:
                return "notif_dismiss"

        return None

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            pos = event.position().toPoint()
            w, h = self.width(), self.height()

            # Tactile click spring feedback
            btn = self._get_button_at(pos)
            if btn:
                self._btn_press_anim[btn] = 1.0
                self._wake_timer()
                self.update()

            # 0. Edge Resizing Grab Detection (Bottom edge, Right edge, Bottom pull handle, Corner)
            if self._state != self.STATE_COMPACT:
                is_bottom_handle = (abs(pos.x() - w // 2) <= 45 and pos.y() >= h - 18)
                is_bottom_edge = (pos.y() >= h - 14)
                is_right_edge = (pos.x() >= w - 14)
                is_corner = (pos.x() >= w - 18 and pos.y() >= h - 18)

                if is_bottom_handle or is_bottom_edge or is_right_edge or is_corner:
                    self._is_edge_resizing = True
                    if is_corner:
                        self._resize_edge = "bottom_right"
                    elif is_right_edge:
                        self._resize_edge = "right"
                    else:
                        self._resize_edge = "bottom"
                    self._resize_start_pos = event.globalPosition().toPoint()
                    self._resize_start_size = QSize(w, h)
                    return

            # 1. Interactive Progress Bar Scrubbing in Music Mode
            if self._state == self.STATE_MUSIC:
                if getattr(self, "_is_theater_mode", False) or w >= 540 or h >= 260:
                    left_w = min(560, max(290, int(w * 0.46)))
                    bar_y = getattr(self, "_theater_bar_y", h - 96)
                    track_x = 36
                    track_w = left_w - 72
                    if abs(pos.y() - bar_y) <= 14 and track_x <= pos.x() <= track_x + track_w:
                        self._is_scrubbing = True
                        self._is_theater_scrubbing = True
                        ratio = min(1.0, max(0.0, (pos.x() - track_x) / float(max(1.0, track_w))))
                        self._playback_pos_sec = ratio * self._playback_dur_sec
                        self.update()
                        return
                else:
                    bar_y = 114 if getattr(self, "_music_show_lyrics", False) else 106
                    if abs(pos.y() - bar_y) <= 12 and 55 <= pos.x() <= w - 55:
                        self._is_scrubbing = True
                        self._is_theater_scrubbing = False
                        track_x = 60
                        track_w = w - 126
                        ratio = min(1.0, max(0.0, (pos.x() - track_x) / float(max(1.0, track_w))))
                        self._playback_pos_sec = ratio * self._playback_dur_sec
                        self.update()
                        return

            # Control Center Sliders Dragging
            if self._state == self.STATE_CONTROL:
                if 212 <= pos.y() <= 238 and 100 <= pos.x() <= 356:
                    self._is_dragging_volume = True
                    ratio = min(1.0, max(0.0, (pos.x() - 110) / 236.0))
                    self._set_volume(ratio * 100.0)
                    return
                elif 242 <= pos.y() <= 268 and 100 <= pos.x() <= 356:
                    self._is_dragging_brightness = True
                    ratio = min(1.0, max(0.0, (pos.x() - 110) / 236.0))
                    self._set_brightness(ratio * 100.0)
                    return

            # Record shelf file click/drag start
            if self._state == self.STATE_SHELF and getattr(self, '_shelf_item_rects', None):
                for f_idx, r in self._shelf_item_rects.items():
                    if r.contains(pos):
                        self._shelf_pressed_file_idx = f_idx
                        self._shelf_drag_start_pos = pos
                        break

            # 2. Record drag start coordinates
            self._drag_start_pos = event.globalPosition().toPoint()
            self._drag_window_pos = self.pos()
            self._has_dragged = False
            self._press_pos = pos

        elif event.button() == Qt.MouseButton.MiddleButton:
            # Middle click cycles opacity presets (100% Solid AMOLED -> 85% Frosted Glass -> 65% -> 45% -> 25%)
            if event.modifiers() & Qt.KeyboardModifier.ShiftModifier:
                self.cycle_theme()
            else:
                self.cycle_background_opacity()
            return

        elif event.button() == Qt.MouseButton.RightButton:
            # Right click cycles island tabs
            states = [
                self.STATE_COMPACT,
                self.STATE_MUSIC,
                self.STATE_WEATHER,
                self.STATE_CONTROL,
                self.STATE_CALENDAR,
                self.STATE_SHELF,
                self.STATE_MAP,
                self.STATE_CLIPBOARD,
                self.STATE_TOOLS
            ]
            try:
                cur_idx = states.index(self._state)
                next_state = states[(cur_idx + 1) % len(states)]
            except ValueError:
                next_state = self.STATE_COMPACT
            self.switch_state(next_state)

    def mouseMoveEvent(self, event):
        self._is_hovered = True
        self._collapse_timer.stop()
        self._wake_timer()

        w, h = self.width(), self.height()
        pos = event.position().toPoint()

        # Check edge resize cursor shapes
        if self._state != self.STATE_COMPACT and not getattr(self, "_is_dragging", False):
            is_bottom_handle = (abs(pos.x() - w // 2) <= 45 and pos.y() >= h - 18)
            is_bottom_edge = (pos.y() >= h - 14)
            is_right_edge = (pos.x() >= w - 14)
            is_corner = (pos.x() >= w - 18 and pos.y() >= h - 18)

            if is_corner:
                self.setCursor(Qt.CursorShape.SizeFDiagCursor)
                if not getattr(self, "_is_edge_resizing", False):
                    return
            elif is_bottom_handle or is_bottom_edge:
                self.setCursor(Qt.CursorShape.SizeVerCursor)
                if not getattr(self, "_is_edge_resizing", False):
                    return
            elif is_right_edge:
                self.setCursor(Qt.CursorShape.SizeHorCursor)
                if not getattr(self, "_is_edge_resizing", False):
                    return

        # Active edge dragging / live dynamic responsive window resizing
        if getattr(self, "_is_edge_resizing", False):
            delta = event.globalPosition().toPoint() - self._resize_start_pos
            min_w, min_h = 380, 180
            screen = QGuiApplication.primaryScreen()
            max_w = (screen.geometry().width() - 24) if screen else 1920
            max_h = (screen.geometry().height() - 48) if screen else 1080

            new_w = self._resize_start_size.width()
            new_h = self._resize_start_size.height()

            if "right" in self._resize_edge:
                new_w = max(min_w, min(max_w, self._resize_start_size.width() + delta.x()))
            if "bottom" in self._resize_edge or self._resize_edge == "bottom":
                new_h = max(min_h, min(max_h, self._resize_start_size.height() + delta.y()))
                if abs(delta.x()) > 15:
                    new_w = max(min_w, min(max_w, self._resize_start_size.width() + delta.x() * 2))

            self._is_theater_mode = (new_w >= 540 or new_h >= 260)
            self.SIZES[self._state] = (new_w, new_h)
            self._target_w = float(new_w)
            self._target_h = float(new_h)

            if screen and self.y() <= 3:
                target_x = screen.geometry().x() + (screen.geometry().width() - new_w) // 2
                self.setGeometry(target_x, self.y(), new_w, new_h)
            else:
                self.resize(new_w, new_h)

            self.update()
            return

        # Drag out file from shelf anytime (Screenshot 2: "Drag out anytime")
        if self._state == self.STATE_SHELF and getattr(self, '_shelf_pressed_file_idx', None) is not None:
            if (pos - getattr(self, '_shelf_drag_start_pos', pos)).manhattanLength() > 6:
                idx = self._shelf_pressed_file_idx
                self._shelf_pressed_file_idx = None
                if 0 <= idx < len(self._shelf_files):
                    fpath = self._shelf_files[idx].get("path")
                    if fpath and os.path.exists(fpath):
                        drag = QDrag(self)
                        mime = QMimeData()
                        mime.setUrls([QUrl.fromLocalFile(fpath)])
                        drag.setMimeData(mime)
                        drag.exec(Qt.DropAction.CopyAction)
                        return

        # If compact mode, hover activates cute smiling eyes & paw print sheen
        if self._state == self.STATE_COMPACT:
            self._hovered_btn = "compact_pill"
            self.setCursor(Qt.CursorShape.PointingHandCursor)
            self.update()
            return

        hovered = self._get_button_at(pos)
        if hovered != self._hovered_btn:
            self._hovered_btn = hovered
            if hovered and hovered not in self._btn_hover_anim:
                self._btn_hover_anim[hovered] = 0.0
            self.update()

        if hovered is not None:
            self.setCursor(Qt.CursorShape.PointingHandCursor)
        else:
            self.setCursor(Qt.CursorShape.ArrowCursor)

        if self._is_scrubbing and self._state == self.STATE_MUSIC:
            pos_x = event.position().x()
            if getattr(self, "_is_theater_scrubbing", False):
                left_w = min(560, max(290, int(w * 0.46)))
                track_x = 36
                track_w = left_w - 72
            else:
                track_x = 60
                track_w = w - 126
            ratio = min(1.0, max(0.0, (pos_x - track_x) / float(max(1.0, track_w))))
            self._playback_pos_sec = ratio * self._playback_dur_sec
            self.update()
            return

        if self._is_dragging_volume:
            ratio = min(1.0, max(0.0, (pos.x() - 110) / 236.0))
            self._set_volume(ratio * 100.0)
            return

        if self._is_dragging_brightness:
            ratio = min(1.0, max(0.0, (pos.x() - 110) / 236.0))
            self._set_brightness(ratio * 100.0)
            return

        if event.buttons() & Qt.MouseButton.LeftButton and hasattr(self, '_drag_start_pos'):
            delta = event.globalPosition().toPoint() - self._drag_start_pos
            if delta.manhattanLength() > 4:
                self._has_dragged = True
                self._is_dragging = True
                self._is_snapping_to_notch = False
                self._position_mode = "floating"
                self.move(self._drag_window_pos + delta)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            if getattr(self, "_is_edge_resizing", False):
                self._is_edge_resizing = False
                screen = QGuiApplication.primaryScreen()
                max_h = screen.geometry().height() if screen else 1080
                max_w = screen.geometry().width() if screen else 1920

                if self.height() > max_h * 0.5 or self.width() > max_w * 0.65:
                    self.expand_to_theater_mode()
                elif self.height() < 220 and self.width() < 460:
                    self.restore_from_theater_mode()
                else:
                    self.update()
                return

            if self._is_scrubbing:
                self._is_scrubbing = False
                self._is_theater_scrubbing = False
                self._media.seek_to(self._playback_pos_sec)
                return

            if self._is_dragging_volume:
                self._is_dragging_volume = False
                return

            if self._is_dragging_brightness:
                self._is_dragging_brightness = False
                return

            if getattr(self, '_has_dragged', False):
                self._is_dragging = False
                self._has_dragged = False
                # Magnetic snap to top notch if dropped near top-center
                screen = QGuiApplication.primaryScreen()
                if screen:
                    geo = screen.geometry()
                    center_x = geo.x() + (geo.width() - self.width()) // 2
                    if abs(self.x() - center_x) < 140 and self.y() < 65:
                        self._is_snapping_to_notch = True
                        self._snap_target_x = float(center_x)
                        self._snap_target_y = float(geo.y())  # Hang flush at y = 0
                        self._snap_vel_x = 0.0
                        self._snap_vel_y = 0.0
                        self._position_mode = "top_notch"
                        if self._settings:
                            self._settings.island_position = "top_notch"
                            self._settings.save()
                        self._wake_timer()
                    else:
                        if self._settings:
                            self._settings.island_position = "floating"
                            self._settings.save()
                return

            self._is_dragging = False
            self._has_dragged = False
            pos = getattr(self, '_press_pos', event.position().toPoint())

            btn = self._get_button_at(pos)
            if btn == "compact_tuck":
                self.retract()
                return

            if btn == "retracted_icon" or getattr(self, "_is_retracted", False):
                self.unretract()
                return

            # 1. Click in compact mode
            if self._state == self.STATE_COMPACT:
                w = self.width()
                if self._is_genuine_music_playing():
                    is_flush_notch = self._is_flush_notch()
                    ear_pad = 14.0 if is_flush_notch else 2.0
                    art_right = int(ear_pad + 6.0 + 28.0)
                    eyes_right = int(art_right + 38.0)
                    # Clicking directly on the equalizer badge on the right cycles visualizer styles live!
                    if pos.x() >= w - 46:
                        self.cycle_eq_style()
                        return
                    # Clicking the grooving pet eyes beside the album art triggers cute emotional reactions!
                    if art_right <= pos.x() <= eyes_right:
                        self.trigger_pet_emotion()
                        return
                    # Clicking track text in compact notch toggles between song details and live lyrics!
                    if eyes_right < pos.x() < w - 46:
                        self.toggle_lyrics_view()
                        return
                    # Clicking album art on the left expands full music player
                    self.switch_state(self.STATE_MUSIC)
                    return
                # Clicking flanks cycles compact status modes (Eyes 🐾 -> Network ⚡ -> Weather ⛅ -> Vitals 💻)
                if pos.x() <= 54 or pos.x() >= w - 54 or getattr(self, "_compact_idle_mode", "eyes") != "eyes":
                    self.cycle_compact_idle_mode()
                    return
                # Clicking center pet eyes triggers lively, expressive emotional reactions!
                self.trigger_pet_emotion()
                return

            # 2. Clicking equalizer in expanded music mode cycles wave styles live! (Android 13 -> Harmonic -> Cyber)
            if self._state == self.STATE_MUSIC:
                w = self.width()
                if pos.x() >= w - 82 and 22 <= pos.y() <= 68:
                    self.cycle_wave_style()
                    return

            # 2. Check button click areas in expanded modes
            if self._state != self.STATE_COMPACT:
                handled = self._handle_click(pos)
                if not handled:
                    if getattr(self, "_is_theater_mode", False):
                        # In fullscreen cinema mode, clicking background smoothly restores to standard card
                        self.restore_from_theater_mode()
                    else:
                        # User clicked on background/header in standard mode -> close back to compact!
                        self._last_expanded_tab = self._state
                        self.switch_state(self.STATE_COMPACT)

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            pos = event.position().toPoint()
            # Double click on top header area toggles theater/maximize mode!
            if pos.y() <= 32:
                if self._state == self.STATE_MUSIC or getattr(self, "_is_theater_mode", False):
                    self.toggle_theater_mode()
                    return
            if self._state == self.STATE_COMPACT:
                target = getattr(self, '_last_expanded_tab', None) or (self.STATE_MUSIC if self._is_genuine_music_playing() else self.STATE_CONTROL)
                self.switch_state(target)
            else:
                self._last_expanded_tab = self._state
                self.switch_state(self.STATE_COMPACT)

    def keyPressEvent(self, event):
        key = event.key()
        if key == Qt.Key.Key_E:
            self.cycle_eye_color()
        elif key == Qt.Key.Key_W:
            self.log_water_glass()
        elif key == Qt.Key.Key_A:
            self.toggle_keep_awake()
        elif key == Qt.Key.Key_S:
            self.toggle_stopwatch()
        elif key == Qt.Key.Key_T:
            self.cycle_theme()
        elif key == Qt.Key.Key_V:
            self._start_voice_recording()
        elif key == Qt.Key.Key_Escape:
            if self._state != self.STATE_COMPACT:
                self.switch_state(self.STATE_COMPACT)
        else:
            super().keyPressEvent(event)

    def _handle_click(self, pos: QPoint) -> bool:
        w, h = self.width(), self.height()

        # 0. Phone Link QR Overlay Modal Intercept
        if getattr(self, "_phone_qr_visible", False):
            mw = min(376.0, float(w - 24))
            mh = min(156.0, float(h - 32))
            mx = (w - mw) / 2.0
            my = 28.0
            # Close button [✕]
            if mx + mw - 34 <= pos.x() <= mx + mw and my <= pos.y() <= my + 34:
                self._phone_qr_visible = False
                self._wake_timer()
                self.update()
                return True
            # URL copy pill
            if mx + 130 <= pos.x() <= mx + mw - 12 and my + 58 <= pos.y() <= my + 92:
                try:
                    self._clipboard.setText(self._phone_drop_service.url)
                    self.show_ambient_toast("clipboard", text="URL Copied to Clipboard 📋")
                except Exception:
                    pass
                self._wake_timer()
                self.update()
                return True
            # Outside click closes modal
            if not (mx <= pos.x() <= mx + mw and my <= pos.y() <= my + mh):
                self._phone_qr_visible = False
                self._wake_timer()
                self.update()
                return True
            return True

        # 1. Top Bar Header Clicks (y <= 32) - Priority tab and button routing
        if pos.y() <= 32:
            # A. Top-left subtle collapse indicator (x < 38)
            if pos.x() < 38:
                if getattr(self, "_is_theater_mode", False):
                    self.restore_from_theater_mode()
                else:
                    self._last_expanded_tab = self._state
                    self.switch_state(self.STATE_COMPACT)
                return True

            # B. Theater / Maximize toggle button (x: 42 to 74) - ONLY in music mode!
            if self._state == self.STATE_MUSIC and 42 <= pos.x() <= 74:
                self.toggle_theater_mode()
                return True

            # C. 9-Tab Switcher at top right (robust hit targets tx ± 13px)
            for tab_id in ["assistant", "music", "weather", "control", "calendar", "shelf", "map", "clipboard", "tools"]:
                tx = self._get_tab_x(tab_id, w)
                if (tx - 13) <= pos.x() <= (tx + 13):
                    if self._state == tab_id:
                        self._last_expanded_tab = tab_id
                        self.switch_state(self.STATE_COMPACT)
                    else:
                        self.switch_state(tab_id)
                    return True

        # 2. Vertical page navigation dots on the right edge (only below header, y > 35)
        if pos.y() > 35 and pos.x() >= w - 24 and (h // 2 - 45) <= pos.y() <= (h // 2 + 45):
            cy = h // 2
            dot_spacing = 11.5
            total_pages = 5
            start_y = cy - ((total_pages - 1) * dot_spacing) / 2.0
            clicked_page = int(round((pos.y() - start_y) / dot_spacing))
            page_map = {
                0: self.STATE_MUSIC,
                1: self.STATE_CALENDAR,
                2: self.STATE_TOOLS,
                3: self.STATE_CONTROL,
                4: self.STATE_WEATHER
            }
            target_state = page_map.get(clicked_page)
            if target_state and target_state != self._state:
                self.switch_state(target_state)
            return True

        # Calendar Month Switcher Arrows [ ◀ ] and [ ▶ ]
        if self._state == self.STATE_CALENDAR:
            # ◀ Previous Month
            if 16 <= pos.x() <= 40 and 32 <= pos.y() <= 58:
                self._cal_month_offset = getattr(self, "_cal_month_offset", 0) - 1
                self.update()
                return True
            # ▶ Next Month
            if 100 <= pos.x() <= 130 and 32 <= pos.y() <= 58:
                self._cal_month_offset = getattr(self, "_cal_month_offset", 0) + 1
                self.update()
                return True
            # Today capsule click: resets to current month!
            if 16 <= pos.x() <= 130 and 136 <= pos.y() <= 170:
                self._cal_month_offset = 0
                self.update()
                return True


        if self._state == self.STATE_ASSISTANT:
            # Send button [➤]
            if (w - 80 <= pos.x() <= w - 48) and (h - 46 <= pos.y() <= h - 10):
                self._on_assistant_submit()
                return True
            # Mic button [🎙️]
            if (w - 46 <= pos.x() <= w - 12) and (h - 46 <= pos.y() <= h - 10):
                self._start_voice_recording()
                return True
            # Quick Chips (y: 170 to 198)
            if 170 <= pos.y() <= 198:
                chip_xs = [16, 86, 156, 244, 328]
                chip_widths = [64, 64, 82, 78, 68]
                chip_actions = [
                    "play lo-fi on spotify",
                    "open notepad and write quick thoughts",
                    "battery status",
                    "analyze screen",
                    "search latest tech news"
                ]
                for idx, (cx, cw) in enumerate(zip(chip_xs, chip_widths)):
                    if cx <= pos.x() <= cx + cw:
                        if idx == 3:
                            self.analyze_screen()
                        else:
                            self._chat_input.setText(chip_actions[idx])
                            self._on_assistant_submit()
                        return True
            # Clicking inside the chat input box focuses it
            if (18 <= pos.x() <= w - 85) and (h - 46 <= pos.y() <= h - 10):
                self._chat_input.setFocus()
                return True

        elif self._state == self.STATE_CONTROL:
            # 1. Big Pill Tiles
            if 34 <= pos.y() <= 78:
                if 18 <= pos.x() <= 204:
                    try:
                        subprocess.Popen("explorer.exe ms-settings:network-wifi")
                    except Exception:
                        pass
                    self._ambient_toast_time = time.monotonic()
                    self._ambient_toast_name = "Wi-Fi & Network Settings 📶"
                    self.update()


                    return True
                elif 216 <= pos.x() <= 402:
                    # Tile 2: Taskbar Style Cycle
                    if hasattr(self, "_taskbar_service") and self._taskbar_service:
                        new_style = self._taskbar_service.cycle_style()
                        disp = self._taskbar_service.display_name
                    else:
                        disp = "Clear Glass"
                    self._ambient_toast_time = time.monotonic()
                    self._ambient_toast_name = f"Taskbar: {disp}"
                    self._wake_timer()
                    self.update()
                    return True
            elif 86 <= pos.y() <= 130:
                if 18 <= pos.x() <= 204:
                    try:
                        subprocess.Popen("explorer.exe ms-settings:bluetooth")
                    except Exception:
                        pass
                    self._ambient_toast_time = time.monotonic()
                    self._ambient_toast_name = "Bluetooth Settings 🎧"
                    self.update()


                    return True
                elif 216 <= pos.x() <= 402:
                    n_modes = ["Fixed", "Smart", "Auto"]
                    try:
                        cur_idx = n_modes.index(self._notch_mode)
                        self._notch_mode = n_modes[(cur_idx + 1) % len(n_modes)]
                    except ValueError:
                        self._notch_mode = "Fixed"
                    self._ambient_toast_time = time.monotonic()
                    self._ambient_toast_name = f"Notch Mode: {self._notch_mode} 📱"
                    self.update()


                    return True

            # 1.5. One-Tap Quick Taskbar Style Pills (y: 136 to 164)
            if 136 <= pos.y() <= 164:
                pill_w = 58
                pill_gap = 7
                pill_start_x = 78
                from taskbar_service import TaskbarStyle
                tb_style_keys = [
                    TaskbarStyle.CLEAR, TaskbarStyle.ACRYLIC,
                    TaskbarStyle.BLUR, TaskbarStyle.BLACK, TaskbarStyle.DEFAULT
                ]
                for i, s_key in enumerate(tb_style_keys):
                    px = pill_start_x + i * (pill_w + pill_gap)
                    if px <= pos.x() <= px + pill_w:
                        if hasattr(self, "_taskbar_service") and self._taskbar_service:
                            self._taskbar_service.set_style(s_key)
                            disp = self._taskbar_service.display_name
                        else:
                            disp = s_key.capitalize()
                        self._ambient_toast_time = time.monotonic()
                        self._ambient_toast_name = f"Taskbar: {disp}"
                        self._wake_timer()
                        self.update()
                        return True

            # 2. Circular Quick Actions Row (y: 168 to 204, cy: 186)
            circle_xs = [48, 112, 176, 244, 308, 372]
            for idx, cx in enumerate(circle_xs):
                if (pos.x() - cx) ** 2 + (pos.y() - 186) ** 2 <= 18 ** 2:
                    if idx == 0:  # Theme Switcher (AMOLED Pure Black, Bloom Dark, Electric Neon, etc.)
                        self.cycle_theme()
                    elif idx == 1:  # Battery
                        self._refresh_battery_status()
                        self._ambient_toast_time = time.monotonic()
                        plug_str = " (Plugged In ⚡)" if self._battery_plugged else ""
                        self._ambient_toast_name = f"Battery: {self._battery_percent}%{plug_str} 🔋"
                    elif idx == 2:  # Apps / Launchpad
                        try:
                            ctypes.windll.user32.keybd_event(0x5B, 0, 0, 0)
                            ctypes.windll.user32.keybd_event(0x5B, 0, 2, 0)
                        except Exception:
                            pass
                        self._ambient_toast_time = time.monotonic()
                        self._ambient_toast_name = "Windows Start / Apps 🚀"
                    elif idx == 3:  # Bell / DND
                        self._media.volume_mute()
                        self._ambient_toast_time = time.monotonic()
                        self._ambient_toast_name = "Mute / Do Not Disturb 🔔"
                    elif idx == 4:  # Settings
                        self._open_settings_dialog()
                    elif idx == 5:  # Refresh
                        self._refresh_battery_status()
                        self._refresh_weather()
                        self._control_volume = _win_get_system_volume()
                        self._wifi_connected = _win_get_internet_connected()
                        self._ambient_toast_time = time.monotonic()
                        self._ambient_toast_name = "Refreshed Live Stats 🔄"
                    self.update()


                    return True

            # 3. Sliders / Mute
            if 186 <= pos.y() <= 214:
                if 18 <= pos.x() <= 100:
                    self._media.volume_mute()
                    self._ambient_toast_time = time.monotonic()
                    self._ambient_toast_name = "Volume Mute / Unmute 🔇"
                    self.update()


                    return True
                elif 100 <= pos.x() <= 356:
                    ratio = min(1.0, max(0.0, (pos.x() - 110) / 236.0))
                    self._set_volume(ratio * 100.0)
                    return True
            elif 216 <= pos.y() <= 244:
                if 100 <= pos.x() <= 356:
                    ratio = min(1.0, max(0.0, (pos.x() - 110) / 236.0))
                    self._set_brightness(ratio * 100.0)
                    return True

        elif self._state == self.STATE_CALENDAR:
            # Pomodoro Controls
            if 88 <= pos.y() <= 116:
                if 238 <= pos.x() <= 312:
                    self._pomo_is_running = not self._pomo_is_running
                    self._ambient_toast_time = time.monotonic()
                    self._ambient_toast_name = "Focus Timer: Running ▶" if self._pomo_is_running else "Focus Timer: Paused ⏸"
                    self.update()


                    return True
                elif 320 <= pos.x() <= 390:
                    self._pomo_is_running = False
                    self._pomo_time_left_sec = self._pomo_preset * 60.0
                    self._ambient_toast_time = time.monotonic()
                    self._ambient_toast_name = f"Focus Timer: Reset ({self._pomo_preset}m) 🔄"
                    self.update()


                    return True
            elif 126 <= pos.y() <= 154:
                if 238 <= pos.x() <= 312:
                    self._pomo_preset = 5
                    self._pomo_time_left_sec = 5 * 60.0
                    self._ambient_toast_time = time.monotonic()
                    self._ambient_toast_name = "Preset: 5m Focus ⏱️"
                    self.update()


                    return True
                elif 320 <= pos.x() <= 390:
                    self._pomo_preset = 15
                    self._pomo_time_left_sec = 15 * 60.0
                    self._ambient_toast_time = time.monotonic()
                    self._ambient_toast_name = "Preset: 15m Focus ⏱️"
                    self.update()


                    return True
            elif 162 <= pos.y() <= 190:
                if 238 <= pos.x() <= 312:
                    self._pomo_preset = 25
                    self._pomo_time_left_sec = 25 * 60.0
                    self._ambient_toast_time = time.monotonic()
                    self._ambient_toast_name = "Preset: 25m Focus ⏱️"
                    self.update()


                    return True
                elif 320 <= pos.x() <= 390:
                    self._pomo_preset = 50
                    self._pomo_time_left_sec = 50 * 60.0
                    self._ambient_toast_time = time.monotonic()
                    self._ambient_toast_name = "Preset: 50m Focus ⏱️"
                    self.update()


                    return True

        if self._state == self.STATE_MUSIC:
            if getattr(self, "_is_theater_mode", False) or w >= 540 or h >= 260:
                left_w = min(560, max(290, int(w * 0.46)))
                ctrl_y = getattr(self, "_theater_ctrl_y", h - 48)
                cx = left_w // 2

                # Wave Style Switcher Button at (cx - 108, ctrl_y)
                if (pos.x() - (cx - 108)) ** 2 + (pos.y() - ctrl_y) ** 2 <= 22 ** 2:
                    self.cycle_wave_style()
                    return True

                # Prev Button (cx - 55, ctrl_y)
                if (pos.x() - (cx - 55)) ** 2 + (pos.y() - ctrl_y) ** 2 <= 24 ** 2:
                    self._media.previous_track()
                    return True

                # Play / Pause button (Center cx, ctrl_y)
                if (pos.x() - cx) ** 2 + (pos.y() - ctrl_y) ** 2 <= 30 ** 2:
                    self._media.play_pause()
                    return True

                # Next Button (cx + 55, ctrl_y)
                if (pos.x() - (cx + 55)) ** 2 + (pos.y() - ctrl_y) ** 2 <= 24 ** 2:
                    self._media.next_track()
                    return True

                # Lyrics toggle button (cx + 108, ctrl_y)
                if (pos.x() - (cx + 108)) ** 2 + (pos.y() - ctrl_y) ** 2 <= 22 ** 2:
                    self.toggle_lyrics_view()
                    return True

                # Theater Scrubber click
                bar_y = getattr(self, "_theater_bar_y", h - 96)
                track_x = 36
                track_w = left_w - 72
                if abs(pos.y() - bar_y) <= 14 and track_x <= pos.x() <= track_x + track_w:
                    ratio = min(1.0, max(0.0, (pos.x() - track_x) / float(max(1.0, track_w))))
                    self._playback_pos_sec = ratio * self._playback_dur_sec
                    self._media.seek_to(self._playback_pos_sec)
                    self.update()
                    return True

                # Click on any Lyric line in the Theater synchronized lyrics sheet to seek immediately!
                if hasattr(self, "_theater_lyrics_rects") and self._theater_lyrics_rects:
                    for l_idx, r in self._theater_lyrics_rects.items():
                        if r.contains(pos) and self._lyrics_lines and 0 <= l_idx < len(self._lyrics_lines):
                            target_sec = self._lyrics_lines[l_idx][0]
                            self._playback_pos_sec = target_sec
                            self._media.seek_to(target_sec)
                            self._lyrics_active_idx = l_idx
                            m, s = divmod(int(target_sec), 60)
                            self._ambient_toast_time = time.monotonic()
                            self._ambient_toast_name = f"Seek: {m}:{s:02d} 🎵"
                            self.update()
                            return True

                return True

            ctrl_y = 164
            cx = w // 2

            # Lyrics toggle button (w - 56, ctrl_y)
            if (pos.x() - (w - 56)) ** 2 + (pos.y() - ctrl_y) ** 2 <= 22 ** 2:
                self.toggle_lyrics_view()
                return True

            # Prev Button (cx - 48, ctrl_y)
            if (pos.x() - (cx - 48)) ** 2 + (pos.y() - ctrl_y) ** 2 <= 20 ** 2:
                self._media.previous_track()
                return True

            # Play / Pause button (Center cx, ctrl_y)
            if (pos.x() - cx) ** 2 + (pos.y() - ctrl_y) ** 2 <= 26 ** 2:
                self._media.play_pause()
                return True

            # Next Button (cx + 48, ctrl_y)
            if (pos.x() - (cx + 48)) ** 2 + (pos.y() - ctrl_y) ** 2 <= 20 ** 2:
                self._media.next_track()
                return True

            # Album Art / App Badge (x: 18 to 88, y: 34 to 104) toggles lyrics view!
            if 18 <= pos.x() <= 88 and 34 <= pos.y() <= 104:
                self.toggle_lyrics_view()
                return True

            # In Lyrics mode, clicking any lyric line seeks playback immediately
            if getattr(self, "_music_show_lyrics", False):
                if 58 <= pos.y() <= 78 and self._lyrics_lines and self._lyrics_active_idx > 0:
                    prev_t = self._lyrics_lines[self._lyrics_active_idx - 1][0]
                    self._playback_pos_sec = prev_t
                    self._media.seek_to(prev_t)
                    self._lyrics_active_idx -= 1
                    self.update()
                    return True
                elif 78 < pos.y() <= 104 and self._lyrics_lines and 0 <= self._lyrics_active_idx < len(self._lyrics_lines):
                    cur_t = self._lyrics_lines[self._lyrics_active_idx][0]
                    self._playback_pos_sec = cur_t
                    self._media.seek_to(cur_t)
                    self.update()
                    return True
                elif 104 < pos.y() <= 126 and self._lyrics_lines and self._lyrics_active_idx + 1 < len(self._lyrics_lines):
                    next_t = self._lyrics_lines[self._lyrics_active_idx + 1][0]
                    self._playback_pos_sec = next_t
                    self._media.seek_to(next_t)
                    self._lyrics_active_idx += 1
                    self.update()
                    return True

            # Scrubber click
            bar_y = 130 if getattr(self, "_music_show_lyrics", False) else 124
            if abs(pos.y() - bar_y) <= 12 and 55 <= pos.x() <= w - 55:
                track_x = 60
                track_w = w - 126
                ratio = min(1.0, max(0.0, (pos.x() - track_x) / float(max(1.0, track_w))))
                self._playback_pos_sec = ratio * self._playback_dur_sec
                self._media.seek_to(self._playback_pos_sec)
                self.update()
                return True
                return True

            # Keep card open on click
            return True

        elif self._state == self.STATE_SHELF:
            # 0. Phone Link QR button (Subheader or Empty Hub pill)
            if (w - 232 <= pos.x() <= w - 152 and 26 <= pos.y() <= 50) or (len(self._shelf_files) == 0 and 18 <= pos.x() <= 106 and 138 <= pos.y() <= 168):
                self._phone_qr_visible = not getattr(self, "_phone_qr_visible", False)
                self._wake_timer()
                self.update()
                return True

            # 1. Snip screen button (Subheader or Empty Hub pill)
            if (w - 150 <= pos.x() <= w - 80 and 26 <= pos.y() <= 50) or (len(self._shelf_files) == 0 and 114 <= pos.x() <= 202 and 138 <= pos.y() <= 168):
                self._shelf_snip_screen()
                return True

            # 2. Clear all button
            if w - 74 <= pos.x() <= w - 18 and 26 <= pos.y() <= 50:
                if len(self._shelf_files) > 0:
                    self._shelf_files.clear()
                    self._shelf_page = 0
                    self._ambient_toast_time = time.monotonic()
                    self._ambient_toast_name = "Shelf Cleared 🗑️"
                    self._wake_timer()
                    self.update()
                return True

            # 3. Paste Clipboard button
            if len(self._shelf_files) == 0 and 210 <= pos.x() <= 298 and 138 <= pos.y() <= 168:
                self._shelf_paste_clipboard()
                return True

            # 4. Browse File button
            if (len(self._shelf_files) == 0 and 306 <= pos.x() <= 394 and 138 <= pos.y() <= 168) or (len(self._shelf_files) > 0 and w - 90 <= pos.x() <= w - 18 and 166 <= pos.y() <= 190):
                self._shelf_browse_files()
                return True

            # 5. Pagination
            if len(self._shelf_files) > 4:
                if pos.x() <= 24 and 75 <= pos.y() <= 145:
                    self._shelf_page = max(0, self._shelf_page - 1)
                    self._wake_timer()
                    self.update()
                    return True
                if pos.x() >= w - 24 and 75 <= pos.y() <= 145:
                    max_p = max(1, math.ceil(len(self._shelf_files) / 4.0))
                    self._shelf_page = min(max_p - 1, self._shelf_page + 1)
                    self._wake_timer()
                    self.update()
                    return True

            # 6. File chips and remove (x) clicks
            if getattr(self, '_shelf_item_rects', None):
                for f_idx, r in self._shelf_item_rects.items():
                    if r.contains(pos) and 0 <= f_idx < len(self._shelf_files):
                        del_r = QRect(r.right() - 22, r.top() + 4, 18, 18)
                        if del_r.contains(pos):
                            self._shelf_files.pop(f_idx)
                            self._wake_timer()
                            self.update()
                            return True
                        else:
                            fpath = self._shelf_files[f_idx].get("path")
                            if fpath and os.path.exists(fpath):
                                try:
                                    os.startfile(fpath)
                                except Exception:
                                    pass
                            return True
            return True

        elif self._state == self.STATE_WEATHER:
            # Click City / Location on Hero Card to switch to Maps tab
            if 16 <= pos.x() <= 166 and 76 <= pos.y() <= 136:
                self.switch_state(self.STATE_MAP)
                return True
            # Quick collapse button on bottom right corner only
            if h >= 120 and pos.x() >= w - 45 and pos.y() >= h - 35:
                self._pinned = False
                self.switch_state(self.STATE_COMPACT)
                return True

        elif self._state == self.STATE_MAP:
            if self._map_view_mode == "panoramic":
                # Panoramic Mode Clicks
                # 1. Mini Top-Right Compass Dial (w - 58 to w - 26, y: 28 to 58)
                if (w - 58) <= pos.x() <= (w - 26) and 28 <= pos.y() <= 58:
                    modes = ["drift", "mouse", "north"]
                    try:
                        cur_idx = modes.index(self._compass_mode)
                        self._compass_mode = modes[(cur_idx + 1) % len(modes)]
                    except ValueError:
                        self._compass_mode = "drift"
                    mode_labels = {
                        "drift": "Compass: Live Gyro Drift 🧭",
                        "mouse": "Compass: Track Mouse Cursor 🎯",
                        "north": "Compass: Locked True North 📍"
                    }
                    self._ambient_toast_time = time.monotonic()
                    self._ambient_toast_name = mode_labels.get(self._compass_mode, "Compass")
                    self.update()


                    return True

                # 2. Bottom 4 Action Chips in Panoramic Mode (y: 104 to 136)
                if 104 <= pos.y() <= 136:
                    c_w = (w - 32 - 36) // 4
                    rx = 16
                    # B1: ⤡ Split View
                    if rx <= pos.x() <= rx + c_w + 6:
                        self._map_view_mode = "split"
                        self._ambient_toast_time = time.monotonic()
                        self._ambient_toast_name = "Layout: Split View (Compass + Map) 🧭🗺️"
                        self.update()


                        return True
                    # B2: 🚦 Traffic Toggle
                    if rx + c_w + 6 <= pos.x() <= rx + (c_w + 6) * 2:
                        self._traffic_enabled = not self._traffic_enabled
                        self._ambient_toast_time = time.monotonic()
                        self._ambient_toast_name = "Live Traffic: ON 🚦" if self._traffic_enabled else "Live Traffic: OFF ⚪"
                        self.update()


                        return True
                    # B3: ⚡ Route Simulation Restart
                    if rx + (c_w + 6) * 2 <= pos.x() <= rx + (c_w + 6) * 3:
                        self._nav_progress = 0.0
                        self._ambient_toast_time = time.monotonic()
                        self._ambient_toast_name = "Route: Reset to Origin 📍"
                        self.update()


                        return True
                    # B4: 🌐 Open in Google Maps
                    if rx + (c_w + 6) * 3 <= pos.x() <= w - 16:
                        self._open_google_maps(mode="directions")
                        return True

                # 3. Click Canvas Body -> Open Google Maps
                if 16 <= pos.x() <= w - 16 and 28 <= pos.y() <= 104:
                    self._open_google_maps(mode="search")
                    return True

            else:
                # Split Mode Clicks
                # 1. Left Card (x: 16 to 156, y: 28 to 136)
                if 16 <= pos.x() <= 156 and 28 <= pos.y() <= 136:
                    if pos.y() >= 110:
                        # Bottom toggle text clicked: switch between Turn HUD & Compass
                        self._compass_left_view = "turn_hud" if self._compass_left_view == "compass" else "compass"
                        self._ambient_toast_time = time.monotonic()
                        self._ambient_toast_name = "Turn HUD Active ↱" if self._compass_left_view == "turn_hud" else "Compass Active 🧭"
                    else:
                        # Center Compass dial clicked: cycle compass mode
                        modes = ["drift", "mouse", "north"]
                        try:
                            cur_idx = modes.index(self._compass_mode)
                            self._compass_mode = modes[(cur_idx + 1) % len(modes)]
                        except ValueError:
                            self._compass_mode = "drift"
                        mode_labels = {
                            "drift": "Compass: Live Gyro Drift 🧭",
                            "mouse": "Compass: Track Mouse Cursor 🎯",
                            "north": "Compass: Locked True North 📍"
                        }
                        self._ambient_toast_time = time.monotonic()
                        self._ambient_toast_name = mode_labels.get(self._compass_mode, "Compass")
                    self.update()


                    return True

                # 2. Right Map Card Bottom 4 Action Chips (y: 104 to 136)
                if 104 <= pos.y() <= 136:
                    rw = w - 180
                    rx = 164
                    c_w = (rw - 28) // 4
                    # B1: ⤢ Full Panoramic View
                    if rx <= pos.x() <= rx + c_w + 5:
                        self._map_view_mode = "panoramic"
                        self._ambient_toast_time = time.monotonic()
                        self._ambient_toast_name = "Layout: Panoramic Ultra-Wide Map 🗺️"
                        self.update()


                        return True
                    # B2: 🚦 Traffic Toggle
                    if rx + c_w + 5 <= pos.x() <= rx + (c_w + 5) * 2:
                        self._traffic_enabled = not self._traffic_enabled
                        self._ambient_toast_time = time.monotonic()
                        self._ambient_toast_name = "Live Traffic: ON 🚦" if self._traffic_enabled else "Live Traffic: OFF ⚪"
                        self.update()


                        return True
                    # B3: ⚡ Route Simulation Restart
                    if rx + (c_w + 5) * 2 <= pos.x() <= rx + (c_w + 5) * 3:
                        self._nav_progress = 0.0
                        self._ambient_toast_time = time.monotonic()
                        self._ambient_toast_name = "Route: Reset to Origin 📍"
                        self.update()


                        return True
                    # B4: 🌐 Open in Google Maps
                    if rx + (c_w + 5) * 3 <= pos.x() <= w - 16:
                        self._open_google_maps(mode="directions")
                        return True

                # 3. Right Map Upper Body (x: 164 to w - 16, y: 28 to 104) -> Open Google Maps
                if 164 <= pos.x() <= w - 16 and 28 <= pos.y() <= 104:
                    self._open_google_maps(mode="search")
                    return True

        elif self._state == self.STATE_CLIPBOARD:
            # 1. History Reel Chips Click (y: 28 to 46)
            if 28 <= pos.y() <= 46:
                hx = 16
                for idx in range(min(4, len(self._clipboard_history))):
                    chip_w = 84
                    if hx <= pos.x() <= hx + chip_w:
                        self._restore_clip_history(idx)
                        return True
                    hx += chip_w + 6

            # 2. 5 Smart Action Buttons Click (y: 106 to 144)
            if 106 <= pos.y() <= 144:
                # B1 (16 to 82): Open Link / Copy Result / Search Google
                if 16 <= pos.x() <= 82:
                    if self._last_clipboard_url:
                        self._open_last_url()
                    elif self._clipboard_calc_result:
                        self._copy_calc_result()
                    else:
                        self._search_google()
                    return True

                # B2 (89 to 155): Ask GPT in Brave Browser
                if 89 <= pos.x() <= 155:
                    self._ask_chatgpt_with_clipboard()
                    return True

                # B3 (162 to 228): Search or Case Convert (UPPER/lower/Title)
                if 162 <= pos.x() <= 228:
                    if self._last_clipboard_url or self._clipboard_calc_result:
                        self._search_google()
                    else:
                        self._toggle_case()
                    return True

                # B4 (235 to 301): Copy Again
                if 235 <= pos.x() <= 301:
                    self._copy_again()
                    return True

                # B5 (308 to 374): Clear Clipboard
                if 308 <= pos.x() <= 374:
                    self._clear_clipboard()
                    return True

        elif self._state == self.STATE_TOOLS:
            # Click Bluetooth Card -> opens Windows Bluetooth settings
            if 16 <= pos.x() <= w - 16 and 76 <= pos.y() <= 108:
                try:
                    subprocess.Popen("explorer.exe ms-settings:bluetooth")
                except Exception:
                    pass
                return True

            # 7 Quick Desktop Tool Buttons on bottom row
            btn_y = h - 38
            if btn_y <= pos.y() <= btn_y + 30:
                # B1: Snip (x: 16 to 64)
                if 16 <= pos.x() <= 64:
                    try:
                        subprocess.Popen("explorer.exe ms-screenclip:")
                    except Exception:
                        try:
                            subprocess.Popen("SnippingTool.exe")
                        except Exception:
                            pass
                    return True
                # B2: Desktop Wallpaper (x: 68 to 116)
                if 68 <= pos.x() <= 116:
                    from tools.wallpaper import pick_and_set_wallpaper
                    path = pick_and_set_wallpaper(self)
                    if path:
                        self._ambient_toast_time = time.monotonic()
                        self._ambient_toast_name = f"Wallpaper: {os.path.basename(path)} 🖼️"
                        self._wake_timer()
                        self.update()
                    return True
                # B3: Calc (x: 120 to 168)
                if 120 <= pos.x() <= 168:
                    try:
                        subprocess.Popen("calc.exe")
                    except Exception:
                        pass
                    return True
                # B4: Quick Scratchpad / Notes (x: 172 to 220)
                if 172 <= pos.x() <= 220:
                    try:
                        notepad_target = str(self._scratchpad_path)
                        if not self._scratchpad_path.exists():
                            self._scratchpad_path.write_text("# Origin Island Quick Scratchpad 📝\n- \n", encoding="utf-8")
                        subprocess.Popen(["notepad.exe", notepad_target])
                    except Exception:
                        subprocess.Popen("notepad.exe")
                    self._ambient_toast_time = time.monotonic()
                    self._ambient_toast_name = "Quick Scratchpad 📝"
                    self._wake_timer()
                    self.update()
                    return True
                # B5: ChatGPT in Brave Browser (x: 224 to 272)
                if 224 <= pos.x() <= 272:
                    self._open_chatgpt()
                    return True
                # B6: Master Mute (x: 276 to 324)
                if 276 <= pos.x() <= 324:
                    self._media.volume_mute()
                    self._trigger_volume_hud("mute")
                    return True
                # B7: Lock PC (x: 328 to 376)
                if 328 <= pos.x() <= 376:
                    try:
                        ctypes.windll.user32.LockWorkStation()
                    except Exception:
                        pass
                    return True

        elif self._state == self.STATE_NOTIFICATION:
            # Action 1: Dismiss [ ✕ ]
            if w - 38 <= pos.x() <= w - 10 and (h - 36) // 2 <= pos.y() <= (h + 36) // 2:
                self._notification_dismiss_timer.stop()
                self.switch_state(self.STATE_COMPACT)
                return True
            # Action 2: Open / Focus app [ ↗ ]
            if w - 74 <= pos.x() <= w - 42 and (h - 36) // 2 <= pos.y() <= (h + 36) // 2:
                self._notification_dismiss_timer.stop()
                self._activate_notification_app()
                self.switch_state(self.STATE_COMPACT)
                return True
            # Clicking anywhere on the card activates app
            if 12 <= pos.x() <= w - 80 and 12 <= pos.y() <= h - 12:
                self._notification_dismiss_timer.stop()
                self._activate_notification_app()
                self.switch_state(self.STATE_COMPACT)
                return True

        return False

    # ── Ultra-Smooth 60 FPS Subpixel Marquee Engine ──────────────────────────

    def _draw_smooth_marquee(
        self,
        p: QPainter,
        rect: QRectF,
        text: str,
        font: QFont,
        color: QColor,
        offset_x: float,
        gap: float = 48.0,
        fade_width: float = 16.0
    ):
        """
        Renders fluid 60 FPS subpixel marquee scrolling text with hardware-accelerated direct
        pixmap blitting and luxurious soft alpha-edge fade masks dynamically harmonized with
        all transparent and AMOLED glass presets (Apple Dynamic Island & OriginOS aesthetic).
        """
        if not text or rect.width() <= 0 or rect.height() <= 0:
            return

        fm = QFontMetrics(font)
        t_width = fm.horizontalAdvance(text)

        # If text fully fits within the bounding box, render statically without any marquee overhead
        if t_width <= rect.width():
            p.save()
            p.setFont(font)
            p.setPen(color)
            p.drawText(rect, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, text)
            p.restore()
            return

        dpr = p.devicePixelRatio() if hasattr(p, "devicePixelRatio") else 1.0
        if dpr <= 0.0:
            dpr = 1.0

        cache_key = (text, font.key(), color.rgba(), int(rect.height()), float(dpr))
        cached = self._marquee_pixmap_cache.get(cache_key)

        if cached is None:
            pix_w = int(math.ceil(t_width + 8))
            pix_h = int(math.ceil(rect.height()))
            img = QImage(int(pix_w * dpr), int(pix_h * dpr), QImage.Format.Format_ARGB32_Premultiplied)
            img.setDevicePixelRatio(dpr)
            img.fill(0)

            ip = QPainter(img)
            ip.setRenderHint(QPainter.RenderHint.Antialiasing, True)
            ip.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)
            ip.setFont(font)
            ip.setPen(color)
            ip.drawText(QRectF(0, 0, pix_w, pix_h), Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, text)
            ip.end()

            cached = (QPixmap.fromImage(img), t_width)
            if len(self._marquee_pixmap_cache) > 40:
                self._marquee_pixmap_cache.pop(next(iter(self._marquee_pixmap_cache)))
            self._marquee_pixmap_cache[cache_key] = cached

        pix, text_w = cached
        span = float(text_w + gap)
        cur_off = float(offset_x % span)

        box_w = int(math.ceil(rect.width()))
        box_h = int(math.ceil(rect.height()))
        box_img = QImage(int(box_w * dpr), int(box_h * dpr), QImage.Format.Format_ARGB32_Premultiplied)
        box_img.setDevicePixelRatio(dpr)
        box_img.fill(0)

        bp = QPainter(box_img)
        bp.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
        bp.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        y_pos = float((rect.height() - (pix.height() / dpr)) / 2.0)
        x1 = float(-cur_off)
        bp.drawPixmap(QPointF(x1, y_pos), pix)

        x2 = float(x1 + span)
        if x2 < box_w:
            bp.drawPixmap(QPointF(x2, y_pos), pix)
        if x2 + text_w < box_w:
            bp.drawPixmap(QPointF(x2 + span, y_pos), pix)

        # Apply pure text alpha dissolution gradient (zero background interference across all transparent styles!)
        if fade_width > 0 and box_w > fade_width * 2:
            alpha_grad = QLinearGradient(0, 0, box_w, 0)
            if cur_off > 1.2:
                alpha_grad.setColorAt(0.0, QColor(0, 0, 0, 0))
                alpha_grad.setColorAt(fade_width / float(box_w), QColor(0, 0, 0, 255))
            else:
                alpha_grad.setColorAt(0.0, QColor(0, 0, 0, 255))

            alpha_grad.setColorAt(max(0.0, 1.0 - (fade_width / float(box_w))), QColor(0, 0, 0, 255))
            alpha_grad.setColorAt(1.0, QColor(0, 0, 0, 0))

            bp.setCompositionMode(QPainter.CompositionMode.CompositionMode_DestinationIn)
            bp.fillRect(QRectF(0, 0, box_w, box_h), alpha_grad)

        bp.end()

        # Draw the perfectly alpha-faded text onto p!
        p.save()
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
        p.drawImage(QPointF(rect.left(), rect.top()), box_img)
        p.restore()

    # ── Vector Icon Drawing Helpers (Apple SF Symbols Geometric Line Style) ───

    def _draw_vector_spark(self, p: QPainter, cx: int, cy: int, color: QColor = QColor(0, 240, 255), scale: float = 1.0):
        """Draws a sleek 4-point AI spark icon (Gemini/Claude/JARVIS AI Core)."""
        p.save()
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(color)
        path = QPainterPath()
        r = 7.0 * scale
        inner = 2.0 * scale
        path.moveTo(cx, cy - r)
        path.quadTo(cx, cy - inner, cx + inner, cy)
        path.quadTo(cx, cy + inner, cx, cy + r)
        path.quadTo(cx, cy + inner, cx - inner, cy)
        path.quadTo(cx, cy - inner, cx, cy - r)
        p.drawPath(path)
        # Center glow core dot
        p.setBrush(QColor(255, 255, 255, 230))
        p.drawEllipse(QPointF(cx, cy), 1.2 * scale, 1.2 * scale)
        p.restore()

    def _draw_vector_mic(self, p: QPainter, cx: int, cy: int, color: QColor = QColor(255, 255, 255), scale: float = 1.0):
        """Draws a crisp vector microphone icon."""
        p.save()
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(color)
        p.drawRoundedRect(QRectF(cx - 3.0 * scale, cy - 6.5 * scale, 6.0 * scale, 10.0 * scale), 3.0 * scale, 3.0 * scale)
        p.setPen(QPen(color, 1.4 * scale, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        p.setBrush(Qt.BrushStyle.NoBrush)
        arc_rect = QRectF(cx - 5.5 * scale, cy - 4.0 * scale, 11.0 * scale, 9.5 * scale)
        p.drawArc(arc_rect, 0, -180 * 16)
        p.drawLine(QPointF(cx, cy + 5.5 * scale), QPointF(cx, cy + 8.5 * scale))
        p.drawLine(QPointF(cx - 3.5 * scale, cy + 8.5 * scale), QPointF(cx + 3.5 * scale, cy + 8.5 * scale))
        p.restore()

    def _draw_vector_send(self, p: QPainter, cx: int, cy: int, color: QColor = QColor(255, 255, 255), scale: float = 1.0):
        """Draws a crisp paper airplane send icon."""
        p.save()
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        p.setPen(QPen(color, 1.3 * scale, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
        p.setBrush(Qt.BrushStyle.NoBrush)
        path = QPainterPath()
        path.moveTo(cx - 4.5 * scale, cy - 4.5 * scale)
        path.lineTo(cx + 5.5 * scale, cy)
        path.lineTo(cx - 4.5 * scale, cy + 4.5 * scale)
        path.lineTo(cx - 1.5 * scale, cy)
        path.closeSubpath()
        p.drawPath(path)
        p.restore()

    def _draw_vector_camera(self, p: QPainter, cx: int, cy: int, color: QColor = QColor(255, 255, 255), scale: float = 1.0):
        """Draws a clean minimal vector camera icon for screenshots without emojis."""
        p.save()
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        pen = QPen(color, 1.25 * scale, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
        p.setPen(pen)
        p.setBrush(Qt.BrushStyle.NoBrush)
        w_cam, h_cam = 13.0 * scale, 8.5 * scale
        p.drawRoundedRect(QRectF(cx - w_cam / 2.0, cy - h_cam / 2.0 + 1.2 * scale, w_cam, h_cam), 2.0 * scale, 2.0 * scale)
        # Top bump
        p.drawRoundedRect(QRectF(cx - 3.2 * scale, cy - h_cam / 2.0 - 1.2 * scale, 6.4 * scale, 2.2 * scale), 1.0 * scale, 1.0 * scale)
        # Lens
        p.drawEllipse(QPointF(cx, cy + 1.2 * scale), 2.4 * scale, 2.4 * scale)
        p.restore()

    def _draw_vector_play_circle(self, p: QPainter, cx: int, cy: int, r: int = 10, is_playing: bool = False, color: QColor = QColor(255, 255, 255)):
        p.save()
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        pen = QPen(color, 1.5)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        p.setPen(pen)
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawEllipse(QPoint(cx, cy), r, r)

        if is_playing:
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(color)
            p.drawRoundedRect(QRectF(cx - 3.5, cy - 4.5, 2.2, 9), 1, 1)
            p.drawRoundedRect(QRectF(cx + 1.3, cy - 4.5, 2.2, 9), 1, 1)
        else:
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(color)
            tri = QPainterPath()
            tri.moveTo(cx - 2.5, cy - 4.8)
            tri.lineTo(cx - 2.5, cy + 4.8)
            tri.lineTo(cx + 4.8, cy)
            tri.closeSubpath()
            p.drawPath(tri)
        p.restore()

    EQ_STYLES_LIST = [
        "neon_purple",
        "adaptive",
        "electric_cyan",
        "spotify_green",
        "sunset_fire",
        "diamond_white",
        "rainbow_rgb",
        "luxury_gold",
        "crimson_red",
    ]

    def cycle_eq_style(self):
        cur = self._settings.get("eq_style", "neon_purple") if self._settings else "neon_purple"
        try:
            cur_idx = self.EQ_STYLES_LIST.index(cur)
            next_idx = (cur_idx + 1) % len(self.EQ_STYLES_LIST)
        except ValueError:
            next_idx = 0
        new_style = self.EQ_STYLES_LIST[next_idx]
        if self._settings:
            self._settings.set("eq_style", new_style, save_now=True)
        self.update()

    def _get_eq_style_colors(self, bar_idx: int = 0, total_bars: int = 5):
        style = self._settings.get("eq_style", "neon_purple") if self._settings else "neon_purple"
        beat = getattr(self, "_ambient_beat_energy", 0.0)
        t = getattr(self, "_anim_time", 0.0)

        if style == "adaptive":
            c_pri = getattr(self, "_ambient_color_current", QColor(168, 85, 247))
            c_sec = getattr(self, "_ambient_color_secondary", QColor(124, 58, 237))
            aura = QColor(c_pri.red(), c_pri.green(), c_pri.blue())
            return c_pri, c_sec, aura

        elif style == "neon_purple":
            c_top = QColor(217, 70, 239)   # Vibrant magenta purple #d946ef
            c_bot = QColor(124, 58, 237)   # Deep electric violet #7c3aed
            aura = QColor(168, 85, 247)    # Purple aura #a855f7
            return c_top, c_bot, aura

        elif style == "electric_cyan":
            c_top = QColor(56, 189, 248)   # Sky cyan #38bdf8
            c_bot = QColor(2, 132, 199)    # Electric deep cyan #0284c7
            aura = QColor(6, 182, 212)     # Cyan aura #06b6d4
            return c_top, c_bot, aura

        elif style == "spotify_green":
            c_top = QColor(74, 222, 128)   # Lime / mint green #4ade80
            c_bot = QColor(22, 163, 74)    # Deep emerald green #16a34a
            aura = QColor(34, 197, 94)     # Emerald aura #22c55e
            return c_top, c_bot, aura

        elif style == "sunset_fire":
            c_top = QColor(251, 146, 60)   # Solar orange #fb923c
            c_bot = QColor(225, 29, 72)    # Crimson rose #e11d48
            aura = QColor(244, 63, 94)     # Rose aura #f43f5e
            return c_top, c_bot, aura

        elif style == "diamond_white":
            c_top = QColor(255, 255, 255)  # Diamond white
            c_bot = QColor(148, 163, 184)  # Platinum slate #94a3b8
            aura = QColor(255, 255, 255)   # White frosted aura
            return c_top, c_bot, aura

        elif style == "rainbow_rgb":
            hue_top = int((t * 90.0 + bar_idx * (360.0 / max(1, total_bars))) % 360)
            hue_bot = (hue_top + 45) % 360
            c_top = QColor.fromHsv(hue_top, 210, 255)
            c_bot = QColor.fromHsv(hue_bot, 240, 230)
            aura = QColor.fromHsv(hue_top, 180, 220)
            return c_top, c_bot, aura

        elif style == "luxury_gold":
            c_top = QColor(253, 224, 71)   # Bright gold #fde047
            c_bot = QColor(217, 119, 6)    # Amber bronze #d97706
            aura = QColor(234, 179, 8)     # Golden aura #eab308
            return c_top, c_bot, aura

        elif style == "crimson_red":
            c_top = QColor(248, 113, 113)  # Coral flame #f87171
            c_bot = QColor(220, 38, 38)    # Deep ruby crimson #dc2626
            aura = QColor(239, 68, 68)     # Crimson aura #ef4444
            return c_top, c_bot, aura

        return QColor(217, 70, 239), QColor(124, 58, 237), QColor(168, 85, 247)

    def cycle_wave_style(self):
        styles = ["sine", "harmonic", "cyber"]
        cur = getattr(self, "_wave_style", "sine")
        try:
            nxt = styles[(styles.index(cur) + 1) % len(styles)]
        except ValueError:
            nxt = "sine"
        self._wave_style = nxt
        names = {
            "sine": "Android 13 Sine 🌊",
            "harmonic": "Harmonic Ribbon 🎶",
            "cyber": "Cyber Pulse ⚡"
        }
        self._ambient_toast_time = time.monotonic()
        self._ambient_toast_name = f"Wave Style: {names.get(nxt, nxt)}"
        self._wake_timer()
        self.update()

    def cycle_accent_theme(self):
        themes = ["adaptive", "cyberpunk", "tokyo", "gold", "emerald", "crimson"]
        cur = getattr(self, "_accent_theme_key", "adaptive")
        try:
            nxt = themes[(themes.index(cur) + 1) % len(themes)]
        except ValueError:
            nxt = "adaptive"
        self._accent_theme_key = nxt
        names = {
            "adaptive": "Adaptive Album Art 🎨",
            "cyberpunk": "Cyberpunk Cyan 💎",
            "tokyo": "Tokyo Midnight Purple 💜",
            "gold": "Gold Titanium 👑",
            "emerald": "Emerald Matrix 🍃",
            "crimson": "Crimson Red 🔴",
        }
        self._ambient_toast_time = time.monotonic()
        self._ambient_toast_name = f"Theme: {names.get(nxt, nxt)}"
        self._wake_timer()
        self.update()

    def cycle_compact_idle_mode(self):
        modes = ["eyes", "network", "weather", "vitals"]
        cur = getattr(self, "_compact_idle_mode", "eyes")
        try:
            nxt = modes[(modes.index(cur) + 1) % len(modes)]
        except ValueError:
            nxt = "eyes"
        self._compact_idle_mode = nxt
        names = {
            "eyes": "Living Pet Eyes 🐾",
            "network": "Network Speedometer ⚡",
            "weather": "Mini Weather ⛅",
            "vitals": "Hardware Vitals 💻",
        }
        self._ambient_toast_time = time.monotonic()
        self._ambient_toast_name = f"Notch: {names.get(nxt, nxt)}"
        self._wake_timer()
        self.update()

    def _launch_quick_app(self, app_key: str):
        import subprocess, os
        names = {
            "app_brave": "Opening Browser 🌐",
            "app_code": "Opening VS Code 💻",
            "app_spotify": "Opening Spotify 🎵",
            "app_discord": "Opening Discord 💬",
            "app_files": "Opening File Explorer 📁",
            "app_term": "Opening Terminal ⚡",
        }
        self._ambient_toast_time = time.monotonic()
        self._ambient_toast_name = names.get(app_key, "Launching App 🚀")
        self._wake_timer()
        self.update()

        try:
            if app_key == "app_brave":
                os.system("start https://www.google.com")
            elif app_key == "app_code":
                subprocess.Popen(["code"], shell=True)
            elif app_key == "app_spotify":
                os.system("start spotify:")
            elif app_key == "app_discord":
                os.system("start discord:")
            elif app_key == "app_files":
                subprocess.Popen(["explorer.exe"])
            elif app_key == "app_term":
                try:
                    subprocess.Popen(["wt.exe"], shell=True)
                except Exception:
                    subprocess.Popen(["powershell.exe"], shell=True)
        except Exception as e:
            print(f"Error launching {app_key}: {e}")

    def _shelf_snip_screen(self):
        """Grabs desktop screen snip and stashes it directly to the Smart Shelf."""
        try:
            screen = QGuiApplication.primaryScreen()
            if not screen:
                return
            import tempfile
            shelf_dir = os.path.join(tempfile.gettempdir(), "DesktopPetShelf")
            os.makedirs(shelf_dir, exist_ok=True)
            snip_path = os.path.join(shelf_dir, f"Snip_{time.strftime('%Y%m%d_%H%M%S')}.png")
            pix = screen.grabWindow(0)
            if pix and not pix.isNull():
                pix.save(snip_path, "PNG")
                sz = os.path.getsize(snip_path)
                self._shelf_files.insert(0, {
                    "path": snip_path,
                    "name": os.path.basename(snip_path),
                    "ext": "PNG",
                    "size": sz,
                })
                self._ambient_toast_time = time.monotonic()
                self._ambient_toast_name = "Screen Stashed 📸"
                self._wake_timer()
                self.update()
        except Exception as e:
            print(f"Shelf snip error: {e}")

    def _shelf_paste_clipboard(self):
        """Pastes clipboard image, URL, file, or text snippet to Smart Shelf."""
        try:
            cb = QApplication.clipboard()
            md = cb.mimeData()
            added = False
            if md.hasUrls():
                for url in md.urls():
                    lpath = url.toLocalFile()
                    if lpath and os.path.exists(lpath):
                        p = Path(lpath)
                        ext = p.suffix.upper().lstrip(".")
                        sz = os.path.getsize(lpath)
                        self._shelf_files.insert(0, {
                            "path": lpath,
                            "name": p.name,
                            "ext": ext or "FILE",
                            "size": sz,
                        })
                        added = True
            elif md.hasImage():
                img = cb.image()
                if not img.isNull():
                    import tempfile
                    shelf_dir = os.path.join(tempfile.gettempdir(), "DesktopPetShelf")
                    os.makedirs(shelf_dir, exist_ok=True)
                    clip_path = os.path.join(shelf_dir, f"Clip_{time.strftime('%Y%m%d_%H%M%S')}.png")
                    img.save(clip_path, "PNG")
                    sz = os.path.getsize(clip_path)
                    self._shelf_files.insert(0, {
                        "path": clip_path,
                        "name": os.path.basename(clip_path),
                        "ext": "PNG",
                        "size": sz,
                    })
                    added = True
            elif md.hasText():
                txt = cb.text().strip()
                if txt:
                    import tempfile
                    shelf_dir = os.path.join(tempfile.gettempdir(), "DesktopPetShelf")
                    os.makedirs(shelf_dir, exist_ok=True)
                    snippet_name = f"Snippet_{time.strftime('%Y%m%d_%H%M%S')}.txt"
                    txt_path = os.path.join(shelf_dir, snippet_name)
                    with open(txt_path, "w", encoding="utf-8") as f:
                        f.write(txt)
                    sz = os.path.getsize(txt_path)
                    self._shelf_files.insert(0, {
                        "path": txt_path,
                        "name": snippet_name,
                        "ext": "TXT",
                        "size": sz,
                    })
                    added = True

            if added:
                self._ambient_toast_time = time.monotonic()
                self._ambient_toast_name = "Pasted to Shelf 📋"
            else:
                self._ambient_toast_time = time.monotonic()
                self._ambient_toast_name = "Clipboard is empty 📋"
            self._wake_timer()
            self.update()
        except Exception as e:
            print(f"Shelf paste error: {e}")

    def _shelf_browse_files(self):
        """Opens native file picker to stash any files to the Smart Shelf."""
        try:
            from PySide6.QtWidgets import QFileDialog
            files, _ = QFileDialog.getOpenFileNames(self, "Add Files to Shelf")
            if files:
                for fpath in files:
                    if os.path.exists(fpath):
                        p = Path(fpath)
                        ext = p.suffix.upper().lstrip(".")
                        sz = os.path.getsize(fpath)
                        self._shelf_files.insert(0, {
                            "path": fpath,
                            "name": p.name,
                            "ext": ext or "FILE",
                            "size": sz,
                        })
                self._ambient_toast_time = time.monotonic()
                self._ambient_toast_name = f"Stashed {len(files)} files 📂"
                self._wake_timer()
                self.update()
        except Exception as e:
            print(f"Shelf browse error: {e}")

    # ── Phone Link & Drop Callbacks & Overlay ────────────────────────────────

    def show_ambient_toast(self, text: str):
        self._ambient_toast_time = time.monotonic()
        self._ambient_toast_name = text
        self._wake_timer()
        self.update()

    def _on_phone_file_received(self, file_path: str, filename: str):
        """Called by PhoneDropService when phone sends photos/files to laptop."""
        p = Path(file_path)
        sz = 0
        try:
            sz = os.path.getsize(file_path)
        except Exception:
            pass
        file_entry = {
            "path": file_path,
            "name": filename,
            "stem": p.stem,
            "ext": p.suffix.upper().lstrip("."),
            "size": sz,
            "time": time.time()
        }
        self._shelf_files.insert(0, file_entry)
        self.show_ambient_toast(f"📥 Received from Phone: {filename[:22]}")
        self.show_system_hud("battery", text=f"📥 Received: {filename[:18]}", duration=2.5)
        self._wake_timer()
        self.update()

    def _on_phone_battery_updated(self, info: Dict[str, Any]):
        """Called by PhoneDropService when phone battery report is received."""
        self._phone_battery_info = info
        pct = int(info.get("percent", 0))
        chg = bool(info.get("charging", False))

        if pct == 100 and chg and not self._phone_fully_charged_notified:
            self.show_ambient_toast("📱 Phone Fully Charged (100%) ⚡")
            self._phone_fully_charged_notified = True
        elif pct < 100:
            self._phone_fully_charged_notified = False

        if pct <= 20 and not chg and not self._phone_low_battery_notified:
            self.show_ambient_toast(f"⚠️ Phone Battery Low ({pct}%) - Connect Charger")
            self._phone_low_battery_notified = True
        elif chg or pct > 25:
            self._phone_low_battery_notified = False

        self._wake_timer()
        self.update()

    def _on_phone_clipboard_received(self, text: str):
        """Called by PhoneDropService when phone copies text to laptop clipboard."""
        try:
            import pyperclip
            pyperclip.copy(text)
        except Exception:
            try:
                self._clipboard.setText(text)
            except Exception:
                pass
        self.show_ambient_toast("📋 Phone text copied to PC")
        self._wake_timer()
        self.update()

    def _on_phone_url_received(self, url: str):
        """Called by PhoneDropService when phone sends URL to open on laptop browser."""
        try:
            QDesktopServices.openUrl(QUrl(url))
        except Exception:
            pass
        self.show_ambient_toast("🌐 Opening link from phone...")
        self._wake_timer()
        self.update()

    def _on_phone_command_received(self, cmd: str, query: str):
        """Called by PhoneDropService when phone sends remote media / quick action / JARVIS command."""
        if cmd == "play_pause":
            self._media.play_pause()
        elif cmd == "volume_up":
            self._trigger_volume_hud("+")
        elif cmd == "volume_down":
            self._trigger_volume_hud("-")
        elif cmd == "volume_mute":
            self._media.volume_mute()
        elif cmd == "next_track":
            self._media.next_track()
        elif cmd == "prev_track":
            self._media.previous_track()
        elif cmd == "seek":
            try:
                target_sec = float(query)
                self._playback_pos_sec = target_sec
                self._media.seek_to(target_sec)
            except Exception as e:
                print(f"[OriginIsland] Phone seek error: {e}")
        elif cmd == "set_volume":
            try:
                v = float(query)
                _win_set_system_volume(v)
                self._anim_volume_level = v
                self._volume_hud_y = 0.0
                self._volume_hud_time = time.monotonic()
            except Exception as e:
                print(f"[OriginIsland] Phone volume error: {e}")
        elif cmd == "screenshot":
            self._shelf_snip_screen()
        elif cmd == "lock_pc":
            try:
                ctypes.windll.user32.LockWorkStation()
            except Exception:
                pass
        elif cmd == "jarvis" and query:
            self._run_assistant_task(query)
        self._wake_timer()
        self.update()

    def _get_phone_cover_bytes(self) -> Optional[Tuple[bytes, str]]:
        """Returns album art bytes and mime type for phone display matching the active song."""
        cur_media = getattr(self._media, "current_info", None) if hasattr(self, "_media") else None
        tb = None
        if cur_media and cur_media.has_media and cur_media.thumbnail_bytes:
            tb = cur_media.thumbnail_bytes
        elif self._last_media_info and self._last_media_info.has_media and self._last_media_info.thumbnail_bytes:
            # Only use last_media_info if it matches the current song title
            if cur_media is None or (cur_media.title == self._last_media_info.title and cur_media.artist == self._last_media_info.artist):
                tb = self._last_media_info.thumbnail_bytes

        if tb:
            mime = "image/png" if tb.startswith(b"\x89PNG") else "image/jpeg"
            return tb, mime

        return None

    def _get_phone_lyrics_data(self) -> dict:
        """Returns live synchronized lyrics, active line index, and current playback position."""
        cur_media = getattr(self._media, "current_info", None) if hasattr(self, "_media") else None
        media_src = cur_media if (cur_media and cur_media.has_media) else self._last_media_info

        lines = []
        for t, text in getattr(self, "_lyrics_lines", []):
            lines.append({"sec": float(t), "text": str(text)})

        # If in-memory lines are empty, attempt immediate disk-cache recovery or background fetch
        if not lines and media_src and media_src.title:
            try:
                title = media_src.title
                artist = media_src.artist or ""
                clean_title, clean_artist = LyricsEngine.clean_song_info(title, artist)
                cached = LyricsEngine.get_disk_cached_lyrics(clean_title, clean_artist)
                if cached:
                    cached_lines, offset = cached
                    self._lyrics_lines = cached_lines
                    lines = [{"sec": float(t), "text": str(text)} for t, text in cached_lines]
                else:
                    track_key = f"{artist}:{title}".strip().lower()
                    if track_key != getattr(self, "_lyrics_cache_key", ""):
                        self._lyrics_cache_key = track_key
                        dur = media_src.duration_sec if media_src.duration_sec > 0 else getattr(self, "_playback_dur_sec", 210.0)
                        LyricsEngine.fetch_lyrics(track_key, artist, title, "", dur, self._on_lyrics_loaded)
            except Exception:
                pass

        pos = media_src.current_position() if (media_src and media_src.is_playing) else getattr(self, "_playback_pos_sec", 0.0)
        dur = media_src.duration_sec if (media_src and media_src.duration_sec > 0) else getattr(self, "_playback_dur_sec", 0.0)

        return {
            "title": media_src.title if media_src else "",
            "artist": media_src.artist if media_src else "",
            "pos_sec": round(float(pos), 2),
            "dur_sec": round(float(dur), 2),
            "active_idx": int(getattr(self, "_lyrics_active_idx", 0)),
            "is_playing": bool(media_src and media_src.is_playing),
            "lines": lines
        }

    def _get_phone_status_data(self) -> dict:
        """Provides live laptop clipboard, music info, synced lyrics state, volume, and jarvis status to phone."""
        cb_text = ""
        try:
            import pyperclip
            cb_text = pyperclip.paste()
        except Exception:
            try:
                cb_text = self._clipboard.text()
            except Exception:
                pass

        cur_media = getattr(self._media, "current_info", None) if hasattr(self, "_media") else None
        media_src = None
        if cur_media and cur_media.has_media:
            from media_service import is_valid_media_info
            if is_valid_media_info(cur_media):
                media_src = cur_media
                self._last_media_info = cur_media
        if not media_src and self._last_media_info and self._last_media_info.has_media:
            media_src = self._last_media_info

        cur_song = None
        if media_src and media_src.title:
            # Detect track change immediately and trigger lyrics fetch
            if media_src.title != getattr(self, "_last_played_title", ""):
                self._last_played_title = media_src.title
                dur_val = media_src.duration_sec if media_src.duration_sec > 0 else getattr(self, "_playback_dur_sec", 210.0)
                if hasattr(self, "_fetch_synced_lyrics_async"):
                    self._fetch_synced_lyrics_async(media_src.title, media_src.artist or "", dur_val)

            lyrics_lines = []
            for t, text in getattr(self, "_lyrics_lines", []):
                lyrics_lines.append({"sec": float(t), "text": str(text)})

            # Real-time position interpolation directly from media session
            pos = media_src.current_position() if media_src.is_playing else getattr(self, "_playback_pos_sec", 0.0)
            dur = media_src.duration_sec if media_src.duration_sec > 0 else getattr(self, "_playback_dur_sec", 0.0)

            # Accurate cover ID tracking and fast in-memory base64 data URI for instant 0ms cover sync
            cur_tb = None
            if cur_media and cur_media.has_media and cur_media.thumbnail_bytes:
                cur_tb = cur_media.thumbnail_bytes
            elif self._last_media_info and self._last_media_info.has_media and self._last_media_info.thumbnail_bytes:
                if cur_media is None or (cur_media.title == self._last_media_info.title):
                    cur_tb = self._last_media_info.thumbnail_bytes

            tb_len = len(cur_tb) if cur_tb else 0
            cover_id = f"{media_src.title}_{media_src.artist}_{tb_len}".replace(" ", "_")

            cover_b64 = ""
            if cur_tb:
                if getattr(self, "_cached_cover_id", "") == cover_id and hasattr(self, "_cached_cover_b64"):
                    cover_b64 = self._cached_cover_b64
                else:
                    try:
                        import base64
                        if len(cur_tb) > 120000:
                            # Optimize large artwork to ~35KB JPEG for 0ms delivery
                            import io
                            from PIL import Image
                            img = Image.open(io.BytesIO(cur_tb))
                            if img.mode not in ("RGB", "L"):
                                img = img.convert("RGB")
                            if max(img.size) > 480:
                                img.thumbnail((480, 480), Image.Resampling.LANCZOS)
                            buf = io.BytesIO()
                            img.save(buf, format="JPEG", quality=84, optimize=True)
                            opt_tb = buf.getvalue()
                            encoded = base64.b64encode(opt_tb).decode("ascii")
                            cover_b64 = f"data:image/jpeg;base64,{encoded}"
                        else:
                            mime = "image/png" if cur_tb.startswith(b"\x89PNG") else "image/jpeg"
                            encoded = base64.b64encode(cur_tb).decode("ascii")
                            cover_b64 = f"data:{mime};base64,{encoded}"
                        self._cached_cover_id = cover_id
                        self._cached_cover_b64 = cover_b64
                    except Exception:
                        try:
                            import base64
                            mime = "image/png" if cur_tb.startswith(b"\x89PNG") else "image/jpeg"
                            encoded = base64.b64encode(cur_tb[:250000]).decode("ascii")
                            cover_b64 = f"data:{mime};base64,{encoded}"
                            self._cached_cover_id = cover_id
                            self._cached_cover_b64 = cover_b64
                        except Exception:
                            cover_b64 = ""

            cur_song = {
                "title": media_src.title,
                "artist": media_src.artist or "Unknown Artist",
                "album": getattr(media_src, "album", ""),
                "is_playing": bool(media_src.is_playing),
                "pos_sec": round(float(pos), 2),
                "dur_sec": round(float(dur), 2),
                "has_cover": bool(cur_tb),
                "cover_id": cover_id,
                "cover_data": cover_b64,
                "has_lyrics": bool(lyrics_lines),
                "active_lyric_idx": int(getattr(self, "_lyrics_active_idx", 0)),
                "lines": lyrics_lines,
            }

        shelf_list = []
        for f in self._shelf_files[:12]:
            shelf_list.append({
                "name": f.get("name", ""),
                "size": f.get("size", 0),
                "ext": f.get("ext", "FILE"),
                "path": f.get("path", "")
            })

        vol = 50
        try:
            vol = int(round(_win_get_system_volume()))
        except Exception:
            pass

        jarvis_info = {
            "status": getattr(self, "_assistant_status", "Ready"),
            "status_detail": getattr(self, "_assistant_status_detail", "Ready"),
            "reply": getattr(self, "_assistant_reply", ""),
            "is_talking": getattr(self, "_is_jarvis_talking", False),
            "history": getattr(self, "_assistant_history", [])[-8:]
        }

        return {
            "clipboard": cb_text,
            "now_playing": cur_song,
            "shelf_files": shelf_list,
            "volume": vol,
            "jarvis": jarvis_info
        }

    def _draw_phone_qr_overlay(self, p: QPainter, w: int, h: int):
        """Draws modern sleek AMOLED Phone Link QR code overlay for instant mobile pairing."""
        p.save()
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        
        # 1. Dark frosted backdrop
        p.fillRect(0, 0, w, h, QColor(0, 0, 0, 210))

        # 2. Centered Modal Card
        mw = min(376.0, float(w - 24))
        mh = min(156.0, float(h - 32))
        mx = (w - mw) / 2.0
        my = 28.0
        modal_rect = QRectF(mx, my, mw, mh)

        # AMOLED dark glass card
        p.setPen(QPen(QColor(0, 240, 255, 90), 1.2))
        p.setBrush(QColor(12, 14, 20, 252))
        p.drawRoundedRect(modal_rect, 16.0, 16.0)

        # Header Title
        p.setFont(QFont("Segoe UI", 9.5, QFont.Weight.Bold))
        p.setPen(QColor(255, 255, 255, 245))
        p.drawText(QRectF(mx + 16, my + 8, mw - 50, 22), Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, "📱 Phone Link · Scan with Camera")

        # Close button [✕]
        close_rect = QRectF(mx + mw - 28, my + 8, 20, 20)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(255, 255, 255, 18))
        p.drawRoundedRect(close_rect, 6, 6)
        p.setFont(QFont("Segoe UI", 8.5, QFont.Weight.Bold))
        p.setPen(QColor(255, 255, 255, 180))
        p.drawText(close_rect, Qt.AlignmentFlag.AlignCenter, "✕")

        # QR Code Card on Left
        qr_box = QRectF(mx + 16, my + 34, 108, 108)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(255, 255, 255, 255))
        p.drawRoundedRect(qr_box, 10, 10)

        # Draw QR Pixmap
        pix = self._phone_drop_service.get_qr_pixmap(size=98)
        if pix:
            p.drawPixmap(int(mx + 21), int(my + 39), pix)

        # Right Information Column
        rx = mx + 134
        rw = mw - 146

        # 1. Connection Status Badge
        status_text = self._phone_drop_service.get_connected_device_summary()
        if self._phone_battery_info and "percent" in self._phone_battery_info:
            pct = self._phone_battery_info["percent"]
            chg = self._phone_battery_info.get("charging", False)
            status_text += f" • 📱 {pct}%{'⚡' if chg else ''}"
        is_conn = "Connected" in status_text
        badge_rect = QRectF(rx, my + 34, rw, 22)
        p.setPen(QPen(QColor(48, 209, 88, 100) if is_conn else QColor(255, 255, 255, 25), 1.0))
        p.setBrush(QColor(48, 209, 88, 25) if is_conn else QColor(255, 255, 255, 12))
        p.drawRoundedRect(badge_rect, 6, 6)
        p.setFont(QFont("Segoe UI", 7.5, QFont.Weight.Bold))
        p.setPen(QColor(48, 209, 88) if is_conn else QColor(200, 210, 225))
        p.drawText(badge_rect, Qt.AlignmentFlag.AlignCenter, status_text)

        # 2. URL Copy Pill
        url_text = self._phone_drop_service.display_url
        url_rect = QRectF(rx, my + 62, rw, 26)
        p.setPen(QPen(QColor(0, 240, 255, 60), 1.0))
        p.setBrush(QColor(0, 240, 255, 15))
        p.drawRoundedRect(url_rect, 8, 8)
        p.setFont(QFont("Segoe UI", 8.2, QFont.Weight.Bold))
        p.setPen(QColor(0, 240, 255))
        p.drawText(url_rect, Qt.AlignmentFlag.AlignCenter, f"⚡ {url_text}  📋")

        # 3. Features subtext
        p.setFont(QFont("Segoe UI", 7.2, QFont.Weight.Normal))
        p.setPen(QColor(150, 160, 175, 210))
        p.drawText(QRectF(rx, my + 94, rw, 34), Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft | Qt.TextFlag.TextWordWrap,
                   "• Send photos, videos & files to laptop\n• Instant 2-way clipboard & media control")

        p.restore()

    def _draw_equalizer_block(self, p: QPainter, eq_x: float, eq_y: float, block_w: float, block_h: float, num_bars: int = 5, is_compact: bool = True):
        mode = self._settings.get("eq_mode", "pill") if self._settings else "pill"
        beat = getattr(self, "_ambient_beat_energy", 0.0)

        c_top_sample, c_bot_sample, c_aura = self._get_eq_style_colors(0, num_bars)
        glow_alpha = int(max(20, min(150, (35 + beat * 75))))

        # 1. Background Badge container (if not floating mode)
        if mode != "floating":
            badge_rect = QRectF(eq_x - 4, eq_y - 2, block_w + 8, block_h + 4)
            # Soft ambient glow aura
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor(c_aura.red(), c_aura.green(), c_aura.blue(), int(glow_alpha * 0.85)))
            p.drawRoundedRect(badge_rect, 7.0, 7.0)

            # Frosted glass inner tint
            p.setBrush(QColor(c_aura.red(), c_aura.green(), c_aura.blue(), int(glow_alpha * 0.40)))
            p.drawRoundedRect(badge_rect, 7.0, 7.0)

            # Subtle glass border
            p.setPen(QPen(QColor(255, 255, 255, int(glow_alpha * 0.55)), 1.0))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawRoundedRect(badge_rect, 7.0, 7.0)

        # 2. Draw Visualizer Bars according to mode
        eq_gap = 2.5
        eq_bar_w = (block_w - (num_bars - 1) * eq_gap) / float(num_bars)
        min_h = 3.5

        for i in range(num_bars):
            val = self._eq_bars[i % len(self._eq_bars)]
            bh = max(min_h, float(val * block_h))
            bx = eq_x + i * (eq_bar_w + eq_gap)
            by = eq_y + (block_h - bh) / 2.0

            c_top, c_bot, _ = self._get_eq_style_colors(i, num_bars)

            if mode == "dots":
                # LED Matrix Dots Mode
                dot_r = max(1.2, (eq_bar_w - 0.5) / 2.0)
                num_dots = max(2, int(bh / (dot_r * 2.2)))
                p.setPen(Qt.PenStyle.NoPen)
                for d_i in range(num_dots):
                    frac = d_i / float(max(1, num_dots - 1))
                    dot_y = (eq_y + block_h - dot_r) - d_i * (dot_r * 2.2)
                    dot_col = QColor(
                        int(c_bot.red() * (1.0 - frac) + c_top.red() * frac),
                        int(c_bot.green() * (1.0 - frac) + c_top.green() * frac),
                        int(c_bot.blue() * (1.0 - frac) + c_top.blue() * frac),
                    )
                    p.setBrush(dot_col)
                    p.drawEllipse(QPointF(bx + eq_bar_w / 2.0, dot_y), dot_r, dot_r)

            elif mode == "neon_beam":
                # High-Intensity Neon Beam
                bar_grad = QLinearGradient(bx, by, bx, by + bh)
                bar_grad.setColorAt(0.0, QColor(255, 255, 255))
                bar_grad.setColorAt(0.25, c_top)
                bar_grad.setColorAt(1.0, c_bot)
                p.setPen(QPen(QColor(c_top.red(), c_top.green(), c_top.blue(), int(glow_alpha * 0.8)), 1.0))
                p.setBrush(bar_grad)
                p.drawRoundedRect(QRectF(bx, by, eq_bar_w, bh), 1.8, 1.8)

            else:
                # Classic Smooth Pill Bars (Pill & Floating modes)
                bar_grad = QLinearGradient(bx, by, bx, by + bh)
                bar_grad.setColorAt(0.0, c_top)
                bar_grad.setColorAt(1.0, c_bot)
                p.setPen(Qt.PenStyle.NoPen)
                p.setBrush(bar_grad)
                p.drawRoundedRect(QRectF(bx, by, eq_bar_w, bh), 1.8, 1.8)

                # Specular tip highlight on active jump
                if bh > block_h * 0.55:
                    p.setBrush(QColor(255, 255, 255, int(180 * (bh / block_h))))
                    p.drawRoundedRect(QRectF(bx + 0.5, by + 0.5, eq_bar_w - 1.0, 2.0), 1.0, 1.0)

    def _draw_vector_note(self, p: QPainter, cx: int, cy: int, size: int = 14, color: QColor = QColor(255, 255, 255)):
        p.save()
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(color)
        p.drawEllipse(QPoint(cx - 3, cy + 3), 3, 2)
        p.drawRect(QRectF(cx - 1, cy - 5, 1.6, 8))
        flag = QPainterPath()
        flag.moveTo(cx - 1, cy - 5)
        flag.quadTo(cx + 4, cy - 4, cx + 4, cy - 1)
        flag.quadTo(cx + 2, cy - 3, cx - 1, cy - 2)
        flag.closeSubpath()
        p.drawPath(flag)
        p.restore()

    def _draw_app_badge(self, p: QPainter, cx: float, cy: float, r: float, app_name: str):
        """Draws the crisp circular app source badge on the album artwork corner matching Screenshot 1."""
        p.save()
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        app_lower = (app_name or "").lower()

        # Background base colors
        if "brave" in app_lower:
            bg_col = QColor(251, 84, 43)  # Brave Vibrant Orange
        elif "spotify" in app_lower:
            bg_col = QColor(29, 185, 84)  # Spotify Green
        elif "chrome" in app_lower:
            bg_col = QColor(66, 133, 244)  # Chrome Blue
        elif "edge" in app_lower:
            bg_col = QColor(0, 120, 215)  # Edge Blue
        elif "apple" in app_lower or "itunes" in app_lower:
            bg_col = QColor(252, 60, 68)  # Apple Red-Pink
        elif "youtube" in app_lower:
            bg_col = QColor(255, 0, 0)    # YouTube Red
        else:
            bg_col = QColor(48, 38, 40)

        # 1. Dark cutout stroke separating badge from album cover art
        p.setPen(QPen(QColor(24, 20, 21), 2.2))
        p.setBrush(bg_col)
        p.drawEllipse(QPointF(cx, cy), r, r)

        # 2. Vector App Icon inside
        if "brave" in app_lower:
            # Brave Lion Head / Crown Shield silhouette
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor(255, 255, 255))
            shield = QPainterPath()
            shield.moveTo(cx - r * 0.52, cy - r * 0.40)
            shield.lineTo(cx - r * 0.22, cy - r * 0.60)
            shield.lineTo(cx, cy - r * 0.38)
            shield.lineTo(cx + r * 0.22, cy - r * 0.60)
            shield.lineTo(cx + r * 0.52, cy - r * 0.40)
            shield.lineTo(cx + r * 0.58, cy + r * 0.12)
            shield.lineTo(cx, cy + r * 0.68)
            shield.lineTo(cx - r * 0.58, cy + r * 0.12)
            shield.closeSubpath()
            p.drawPath(shield)
            # Inner mane detail
            p.setBrush(QColor(251, 84, 43))
            p.drawRoundedRect(QRectF(cx - r * 0.18, cy - r * 0.18, r * 0.36, r * 0.38), 1.0, 1.0)

        elif "spotify" in app_lower:
            # 3 Black sound wave arcs
            p.setPen(QPen(QColor(0, 0, 0), 1.6, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawArc(QRectF(cx - r * 0.65, cy - r * 0.65, r * 1.3, r * 1.3), 35 * 16, 50 * 16)
            p.drawArc(QRectF(cx - r * 0.50, cy - r * 0.45, r * 1.0, r * 1.0), 35 * 16, 50 * 16)
            p.drawArc(QRectF(cx - r * 0.35, cy - r * 0.25, r * 0.7, r * 0.7), 35 * 16, 50 * 16)

        elif "youtube" in app_lower:
            # White Play Triangle
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor(255, 255, 255))
            tri = QPainterPath()
            tri.moveTo(cx - r * 0.3, cy - r * 0.38)
            tri.lineTo(cx + r * 0.42, cy)
            tri.lineTo(cx - r * 0.3, cy + r * 0.38)
            tri.closeSubpath()
            p.drawPath(tri)

        else:
            # Clean miniature vector music note
            self._draw_vector_note(p, int(cx), int(cy), size=int(r * 0.9), color=QColor(255, 255, 255))

        p.restore()

    def _draw_lyrics_icon(self, p: QPainter, cx: float, cy: float, r: float, color: QColor, is_active: bool = False):
        """Draws the speech bubble lyrics icon matching Screenshots 1 and 3."""
        p.save()
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        bw = 18.0
        bh = 13.0
        bubble = QPainterPath()
        bubble.addRoundedRect(QRectF(cx - bw / 2.0, cy - bh / 2.0 - 1.0, bw, bh), 3.5, 3.5)

        # Bubble speech tail at bottom left
        tail = QPainterPath()
        tail.moveTo(cx - 4.5, cy + bh / 2.0 - 1.5)
        tail.lineTo(cx - 7.5, cy + bh / 2.0 + 3.0)
        tail.lineTo(cx - 1.5, cy + bh / 2.0 - 1.5)
        tail.closeSubpath()
        bubble = bubble.united(tail)

        p.setPen(QPen(color, 1.45, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawPath(bubble)

        # Two horizontal text lines inside bubble
        p.drawLine(QPointF(cx - 4.2, cy - 2.8), QPointF(cx + 4.2, cy - 2.8))
        p.drawLine(QPointF(cx - 4.2, cy + 1.2), QPointF(cx + 2.2, cy + 1.2))

        p.restore()

    def _draw_vertical_page_dots(self, p: QPainter, x: float, cy: float, active_page: int, total_pages: int = 5):
        """Draws the vertical carousel page indicator dots on the right edge matching Screenshots 1, 3, and 4."""
        p.save()
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        dot_spacing = 11.5
        start_y = cy - ((total_pages - 1) * dot_spacing) / 2.0

        for i in range(total_pages):
            dy = start_y + i * dot_spacing
            if i == active_page:
                pill_h = 13.5
                pill_w = 3.6
                p.setPen(Qt.PenStyle.NoPen)
                p.setBrush(QColor(255, 255, 255, 230))
                p.drawRoundedRect(QRectF(x - pill_w / 2.0, dy - (pill_h - 3.6) / 2.0, pill_w, pill_h), pill_w / 2.0, pill_w / 2.0)
            else:
                p.setPen(Qt.PenStyle.NoPen)
                p.setBrush(QColor(255, 255, 255, 60))
                p.drawEllipse(QPointF(x, dy), 1.8, 1.8)

        p.restore()

    def _draw_player_equalizer(self, p: QPainter, x: float, y: float, w: float, h: float, color: QColor):
        """Draws the 6 vertical bouncing equalizer bars matching user screenshot, synced to audio beats and flow."""
        p.save()
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        num_bars = 6
        bar_w = 3.2
        gap = (w - (num_bars * bar_w)) / max(1, num_bars - 1)
        is_playing = bool(self._last_media_info and self._last_media_info.is_playing)

        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(color)

        for i in range(num_bars):
            if is_playing and hasattr(self, "_eq_bars") and i < len(self._eq_bars):
                val = self._eq_bars[i]
                bh = max(3.5, min(h, h * val))
            else:
                bh = 3.5
            bx = x + i * (bar_w + gap)
            by = y + (h - bh) / 2.0
            p.drawRoundedRect(QRectF(bx, by, bar_w, bh), bar_w / 2.0, bar_w / 2.0)

        p.restore()

    def _draw_vector_speaker(self, p: QPainter, cx: int, cy: int, level: int = 2, color: QColor = QColor(255, 255, 255)):
        p.save()
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        
        # Speaker cone
        cone = QPainterPath()
        cone.moveTo(cx - 5, cy - 2.5)
        cone.lineTo(cx - 2, cy - 2.5)
        cone.lineTo(cx + 2, cy - 5.5)
        cone.lineTo(cx + 2, cy + 5.5)
        cone.lineTo(cx - 2, cy + 2.5)
        cone.lineTo(cx - 5, cy + 2.5)
        cone.closeSubpath()

        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(color)
        p.drawPath(cone)

        pen = QPen(color, 1.3)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        p.setPen(pen)
        p.setBrush(Qt.BrushStyle.NoBrush)

        if level == 0:
            # Mute X
            p.drawLine(cx + 4, cy - 3, cx + 8, cy + 3)
            p.drawLine(cx + 8, cy - 3, cx + 4, cy + 3)
        elif level == 1:
            # Single sound arc (Volume Down / Low)
            p.drawArc(QRectF(cx + 1, cy - 4, 6, 8), -50 * 16, 100 * 16)
        elif level >= 2:
            # Double sound arcs (Volume Up / High)
            p.drawArc(QRectF(cx + 1, cy - 4, 6, 8), -50 * 16, 100 * 16)
            p.drawArc(QRectF(cx + 4, cy - 6, 7, 12), -50 * 16, 100 * 16)

        p.restore()

    def _draw_vector_weather_icon(self, p: QPainter, cx: int, cy: int, icon_type: str = "sun", color: QColor = QColor(255, 255, 255), scale: float = 1.0):
        p.save()
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        p.translate(cx, cy)
        p.scale(scale, scale)

        t = self._anim_time

        if icon_type in ["sun", "hot"]:
            # Radiant rotating sun corona + pulsating solar flares
            rot = (t * 25.0) % 360.0
            p.save()
            p.rotate(rot)
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor(255, 180, 0, 80))
            p.drawEllipse(QPoint(0, 0), 7, 7)
            
            p.setBrush(QColor(255, 204, 0))
            p.drawEllipse(QPoint(0, 0), 5, 5)

            pen = QPen(QColor(255, 214, 10), 1.4)
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            p.setPen(pen)
            ray_len = 9.5 + math.sin(t * 4.0) * 1.0
            for angle in [0, 45, 90, 135, 180, 225, 270, 315]:
                rad = math.radians(angle)
                x1 = math.cos(rad) * 6.5
                y1 = math.sin(rad) * 6.5
                x2 = math.cos(rad) * ray_len
                y2 = math.sin(rad) * ray_len
                p.drawLine(QPointF(x1, y1), QPointF(x2, y2))
            p.restore()

            if icon_type == "hot":
                # Shimmer wave below sun
                p.setPen(QPen(QColor(255, 150, 50, 180), 1.2))
                wave = QPainterPath()
                wave.moveTo(-6, 8 + math.sin(t * 3.0) * 1.5)
                wave.quadTo(0, 8 - math.sin(t * 3.0) * 1.5, 6, 8 + math.sin(t * 3.0) * 1.5)
                p.drawPath(wave)

        elif icon_type == "night":
            # Glowing crescent moon with starlight halo
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor(255, 214, 10, 40))
            p.drawEllipse(QPoint(0, 0), 9, 9)

            cres = QPainterPath()
            cres.moveTo(2, -6)
            cres.cubicTo(6, -2, 6, 4, 1, 6)
            cres.cubicTo(-5, 6, -7, -1, -3, -6)
            cres.cubicTo(-2, -3, 0, -5, 2, -6)
            cres.closeSubpath()
            p.setBrush(QColor(255, 214, 10))
            p.drawPath(cres)

            # Animated twinkle star
            star_a = int(120 + 130 * abs(math.sin(t * 3.0)))
            p.setBrush(QColor(255, 255, 255, star_a))
            p.drawEllipse(QPointF(5.5, -4.5), 1.2, 1.2)

        elif icon_type in ["rain", "thunder"]:
            # Cloud base
            cloud = QPainterPath()
            cloud.moveTo(-7, 0)
            cloud.cubicTo(-9, -3, -5, -7, -2, -5)
            cloud.cubicTo(0, -9, 6, -8, 6, -4)
            cloud.cubicTo(9, -3, 9, 1, 6, 2)
            cloud.lineTo(-6, 2)
            cloud.closeSubpath()
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor(200, 220, 240, 230))
            p.drawPath(cloud)

            if icon_type == "rain":
                # Animated falling rain drops
                pen = QPen(QColor(96, 165, 250), 1.3)
                pen.setCapStyle(Qt.PenCapStyle.RoundCap)
                p.setPen(pen)
                offset = (t * 14.0) % 4.0
                p.drawLine(QPointF(-4, 3 + offset), QPointF(-5, 6 + offset))
                p.drawLine(QPointF(0, 4 + offset), QPointF(-1, 7 + offset))
                p.drawLine(QPointF(4, 3 + offset), QPointF(3, 6 + offset))
            else:
                # Animated lightning bolt
                bolt = QPainterPath()
                bolt.moveTo(1, 2)
                bolt.lineTo(-2, 6)
                bolt.lineTo(0.5, 6)
                bolt.lineTo(-1, 10)
                bolt.lineTo(3, 5)
                bolt.lineTo(0.5, 5)
                bolt.closeSubpath()
                p.setPen(Qt.PenStyle.NoPen)
                bolt_alpha = 180 + int(75 * abs(math.sin(t * 8.0)))
                p.setBrush(QColor(255, 220, 20, bolt_alpha))
                p.drawPath(bolt)

        elif icon_type == "snow":
            # Cloud + drifting flakes
            cloud = QPainterPath()
            cloud.moveTo(-7, 0)
            cloud.cubicTo(-9, -3, -5, -7, -2, -5)
            cloud.cubicTo(0, -9, 6, -8, 6, -4)
            cloud.cubicTo(9, -3, 9, 1, 6, 2)
            cloud.lineTo(-6, 2)
            cloud.closeSubpath()
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor(220, 235, 255, 230))
            p.drawPath(cloud)
            
            p.setBrush(QColor(255, 255, 255))
            f_offset = (t * 3.0) % 5.0
            p.drawEllipse(QPointF(-4 + math.sin(t * 2) * 1.5, 3 + f_offset), 1.1, 1.1)
            p.drawEllipse(QPointF(1 + math.cos(t * 2) * 1.5, 4 + f_offset), 1.1, 1.1)
            p.drawEllipse(QPointF(5 + math.sin(t * 3) * 1.5, 3 + f_offset), 1.1, 1.1)

        elif icon_type == "wind":
            # Flowing aerodynamic wind streams
            pen = QPen(QColor(148, 163, 184), 1.3)
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            p.setPen(pen)
            p.setBrush(Qt.BrushStyle.NoBrush)

            w1 = QPainterPath()
            w1.moveTo(-8, -3 + math.sin(t * 4.0) * 1.0)
            w1.lineTo(2, -3 + math.sin(t * 4.0) * 1.0)
            w1.quadTo(6, -3, 6, -5)
            p.drawPath(w1)

            w2 = QPainterPath()
            w2.moveTo(-6, 2 + math.cos(t * 4.0) * 1.0)
            w2.lineTo(4, 2 + math.cos(t * 4.0) * 1.0)
            w2.quadTo(8, 2, 8, 4)
            p.drawPath(w2)

        else:  # "cloud"
            # Multi-layer floating cloud with gentle atmospheric bob
            bob = math.sin(t * 2.0) * 0.8
            cloud = QPainterPath()
            cloud.moveTo(-7, 2 + bob)
            cloud.cubicTo(-9, -1 + bob, -5, -6 + bob, -2, -4 + bob)
            cloud.cubicTo(0, -8 + bob, 6, -7 + bob, 7, -2 + bob)
            cloud.cubicTo(10, 0 + bob, 9, 4 + bob, 6, 4 + bob)
            cloud.lineTo(-6, 4 + bob)
            cloud.closeSubpath()
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor(220, 230, 245, 240))
            p.drawPath(cloud)

        p.restore()

    def _draw_vector_clock(self, p: QPainter, cx: int, cy: int, r: int = 7, color: QColor = QColor(255, 255, 255)):
        p.save()
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        pen = QPen(color, 1.3)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        p.setPen(pen)
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawEllipse(QPoint(cx, cy), r, r)
        p.drawLine(cx, cy, cx, cy - (r - 2.5))
        p.drawLine(cx, cy, cx + (r - 3.5), cy)
        p.restore()

    def _draw_vector_droplet(self, p: QPainter, cx: int, cy: int, color: QColor = QColor(96, 165, 250)):
        """Dynamic animated water droplet with surface tension breathing, specular glint, and liquid ripple."""
        p.save()
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        t = self._anim_time

        # Floating vertical bob & organic liquid squash/stretch
        bob_y = math.sin(t * 3.5) * 1.2
        squash = 1.0 + math.sin(t * 3.5) * 0.08
        stretch = 1.0 - math.sin(t * 3.5) * 0.08

        p.translate(cx, cy + bob_y)
        p.scale(squash, stretch)

        # 1. Outer Soft Water Glow
        glow_col = QColor(color.red(), color.green(), color.blue(), 35)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(glow_col)
        p.drawEllipse(QPointF(0, 1), 6, 6)

        # 2. Main Teardrop Path
        drop = QPainterPath()
        drop.moveTo(0, -6.0)
        drop.cubicTo(4.2, -1.5, 4.2, 4.5, 0, 4.5)
        drop.cubicTo(-4.2, 4.5, -4.2, -1.5, 0, -6.0)
        drop.closeSubpath()

        # Gradient shading for 3D liquid volume
        grad = QLinearGradient(0, -6, 0, 5)
        grad.setColorAt(0.0, QColor(min(255, color.red() + 60), min(255, color.green() + 50), 255, 250))
        grad.setColorAt(0.7, color)
        grad.setColorAt(1.0, QColor(max(0, color.red() - 40), max(0, color.green() - 30), max(0, color.blue() - 30), 240))
        p.setBrush(grad)
        p.drawPath(drop)

        # 3. Dynamic Specular Light Glint (shines & pulses)
        glint_alpha = int(160 + 80 * math.sin(t * 4.0))
        p.setBrush(QColor(255, 255, 255, glint_alpha))
        p.drawEllipse(QPointF(-1.4, -1.8), 1.2, 1.8)

        # 4. Tiny Micro Drip Ripple below droplet
        p.restore()
        p.save()
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        ripple_prog = (t * 2.0) % 1.0
        r_w = 2.0 + ripple_prog * 5.5
        r_h = 0.8 + ripple_prog * 2.0
        r_alpha = int((1.0 - ripple_prog) * 110)
        if r_alpha > 0:
            p.setPen(QPen(QColor(color.red(), color.green(), color.blue(), r_alpha), 1.0))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawEllipse(QPointF(cx, cy + 6.0), r_w, r_h)
        p.restore()

    def _draw_vector_wind(self, p: QPainter, cx: int, cy: int, color: QColor = QColor(148, 163, 184)):
        """Dynamic flowing wind streams with animated aerodynamic curls, oscillating gusts, and speed streaks."""
        p.save()
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        t = self._anim_time

        # Oscillation for gust waves
        w1_sin = math.sin(t * 5.0) * 0.9
        w2_sin = math.cos(t * 4.5) * 0.9
        curl_pulse = math.sin(t * 6.0) * 1.2

        pen = QPen(color, 1.3)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        p.setPen(pen)
        p.setBrush(Qt.BrushStyle.NoBrush)

        # Streamline 1 (Top stream with upper aerodynamic curl)
        w1 = QPainterPath()
        w1.moveTo(cx - 7, cy - 2.5 + w1_sin)
        w1.lineTo(cx + 2, cy - 2.5 + w1_sin)
        w1.quadTo(cx + 5.5, cy - 2.5 + w1_sin, cx + 5.5, cy - 5.0 + curl_pulse * 0.6)
        p.drawPath(w1)

        # Streamline 2 (Bottom stream with lower aerodynamic curl)
        w2 = QPainterPath()
        w2.moveTo(cx - 5, cy + 2.5 + w2_sin)
        w2.lineTo(cx + 3, cy + 2.5 + w2_sin)
        w2.quadTo(cx + 7.0, cy + 2.5 + w2_sin, cx + 7.0, cy + 5.0 - curl_pulse * 0.6)
        p.drawPath(w2)

        # Streamline 3 (Middle fast breeze micro-streak)
        mid_prog = (t * 3.5) % 1.0
        streak_x = cx - 6 + mid_prog * 12.0
        streak_alpha = int(math.sin(mid_prog * math.pi) * 220)
        if streak_alpha > 0:
            streak_pen = QPen(QColor(color.red(), color.green(), color.blue(), streak_alpha), 1.2)
            streak_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            p.setPen(streak_pen)
            p.drawLine(QPointF(streak_x - 2.0, cy), QPointF(streak_x + 2.0, cy))

        p.restore()

    def _draw_vector_clipboard_icon(self, p: QPainter, cx: int, cy: int, color: QColor = QColor(255, 255, 255)):
        """Apple SF Symbol style clipboard with rounded clip clamp and interior page lines."""
        p.save()
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        pen = QPen(color, 1.3)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        p.setPen(pen)
        p.setBrush(Qt.BrushStyle.NoBrush)
        # Main board outline
        p.drawRoundedRect(QRectF(cx - 5, cy - 4.5, 10, 11), 1.5, 1.5)
        # Top clip clamp
        p.drawRoundedRect(QRectF(cx - 2.5, cy - 6.5, 5, 2.5), 1, 1)
        # Internal document lines
        p.setPen(QPen(QColor(color.red(), color.green(), color.blue(), 180), 1.0))
        p.drawLine(cx - 2.5, cy - 0.5, cx + 2.5, cy - 0.5)
        p.drawLine(cx - 2.5, cy + 2.2, cx + 1.5, cy + 2.2)
        p.restore()

    def _draw_vector_shelf_icon(self, p: QPainter, cx: int, cy: int, color: QColor = QColor(255, 255, 255)):
        """Vector shelf / drawer icon for tab bar."""
        p.save()
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        pen = QPen(color, 1.3)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        p.setPen(pen)
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRoundedRect(QRectF(cx - 5.5, cy - 4.5, 11, 9.5), 1.5, 1.5)
        p.drawLine(cx - 4, cy - 0.5, cx + 4, cy - 0.5)
        p.drawLine(cx - 1.5, cy + 2.2, cx + 1.5, cy + 2.2)
        p.restore()

    def _draw_vector_shelf_drop_tray(self, p: QPainter, cx: int, cy: int, scale: float = 1.0, color: QColor = QColor(255, 255, 255)):
        """Matching Screenshot 2 tray icon with downward arrow entering box."""
        p.save()
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        p.translate(cx, cy)
        p.scale(scale, scale)
        pen = QPen(color, 1.8)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        p.setPen(pen)
        p.setBrush(Qt.BrushStyle.NoBrush)

        tray = QPainterPath()
        tray.moveTo(-13, -3)
        tray.lineTo(-13, 8)
        tray.lineTo(13, 8)
        tray.lineTo(13, -3)
        tray.moveTo(-13, 2)
        tray.lineTo(-5, 2)
        tray.lineTo(-2.5, 5.5)
        tray.lineTo(2.5, 5.5)
        tray.lineTo(5, 2)
        tray.lineTo(13, 2)
        p.drawPath(tray)

        p.drawLine(0, -12, 0, -1)
        p.drawLine(-4, -4.5, 0, -1)
        p.drawLine(4, -4.5, 0, -1)
        p.restore()

    def _draw_vector_trash(self, p: QPainter, cx: int, cy: int, color: QColor = QColor(255, 255, 255)):
        """Vector trash can icon."""
        p.save()
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        pen = QPen(color, 1.2)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        p.setPen(pen)
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRoundedRect(QRectF(cx - 3.5, cy - 2, 7, 7.5), 1, 1)
        p.drawLine(cx - 5, cy - 3, cx + 5, cy - 3)
        p.drawLine(cx - 1.5, cy - 4.5, cx + 1.5, cy - 4.5)
        p.restore()

    def _draw_vector_case(self, p: QPainter, cx: int, cy: int, color: QColor = QColor(255, 255, 255)):
        """Vector typography case conversion icon."""
        p.save()
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        p.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
        p.setPen(color)
        p.drawText(QRect(cx - 7, cy - 7, 14, 14), Qt.AlignmentFlag.AlignCenter, "Aa")
        p.restore()

    def _draw_vector_swatch(self, p: QPainter, cx: int, cy: int, color_hex: str):
        """Vector color swatch preview box."""
        p.save()
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        p.setPen(QPen(QColor(255, 255, 255, 120), 1.0))
        try:
            p.setBrush(QColor(color_hex))
        except Exception:
            p.setBrush(QColor(255, 255, 255))
        p.drawRoundedRect(QRectF(cx - 5, cy - 5, 10, 10), 2.5, 2.5)
        p.restore()

    def _draw_vector_bolt(self, p: QPainter, cx: int, cy: int, color: QColor = QColor(255, 255, 255)):
        p.save()
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(color)
        bolt = QPainterPath()
        bolt.moveTo(cx + 1, cy - 6)
        bolt.lineTo(cx - 4, cy - 0.5)
        bolt.lineTo(cx - 0.5, cy - 0.5)
        bolt.lineTo(cx - 1.5, cy + 6)
        bolt.lineTo(cx + 3.5, cy + 0.5)
        bolt.lineTo(cx, cy + 0.5)
        bolt.closeSubpath()
        p.drawPath(bolt)
        p.restore()

    def _draw_vector_globe(self, p: QPainter, cx: int, cy: int, r: int = 6, color: QColor = QColor(255, 255, 255)):
        p.save()
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        pen = QPen(color, 1.2)
        p.setPen(pen)
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawEllipse(QPoint(cx, cy), r, r)
        p.drawLine(cx - r, cy, cx + r, cy)
        p.drawEllipse(QPoint(cx, cy), max(1, r // 2), r)
        p.restore()

    def _draw_vector_search(self, p: QPainter, cx: int, cy: int, color: QColor = QColor(255, 255, 255)):
        p.save()
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        pen = QPen(color, 1.3)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        p.setPen(pen)
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawEllipse(QPoint(cx - 1.5, cy - 1.5), 4, 4)
        p.drawLine(cx + 1.5, cy + 1.5, cx + 5, cy + 5)
        p.restore()

    def _draw_vector_copy(self, p: QPainter, cx: int, cy: int, color: QColor = QColor(255, 255, 255)):
        p.save()
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        pen = QPen(color, 1.2)
        p.setPen(pen)
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRoundedRect(QRectF(cx - 5, cy - 5, 7, 8), 1, 1)
        p.setBrush(QColor(0, 0, 0, 180))
        p.drawRoundedRect(QRectF(cx - 2, cy - 2, 7, 8), 1, 1)
        p.restore()

    def _draw_vector_cpu(self, p: QPainter, cx: int, cy: int, color: QColor = QColor(52, 199, 89)):
        p.save()
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        pen = QPen(color, 1.2)
        p.setPen(pen)
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRoundedRect(QRectF(cx - 5, cy - 5, 10, 10), 2, 2)
        # Pins
        p.drawLine(cx - 3, cy - 7, cx - 3, cy - 5)
        p.drawLine(cx + 3, cy - 7, cx + 3, cy - 5)
        p.drawLine(cx - 3, cy + 5, cx - 3, cy + 7)
        p.drawLine(cx + 3, cy + 5, cx + 3, cy + 7)
        p.drawLine(cx - 7, cy - 3, cx - 5, cy - 3)
        p.drawLine(cx - 7, cy + 3, cx - 5, cy + 3)
        p.drawLine(cx + 5, cy - 3, cx + 7, cy - 3)
        p.drawLine(cx + 5, cy + 3, cx + 7, cy + 3)
        p.restore()

    def _draw_vector_ram(self, p: QPainter, cx: int, cy: int, color: QColor = QColor(0, 122, 255)):
        p.save()
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        pen = QPen(color, 1.2)
        p.setPen(pen)
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRoundedRect(QRectF(cx - 7, cy - 4, 14, 8), 1.5, 1.5)
        p.drawLine(cx - 4, cy - 2, cx - 4, cy + 2)
        p.drawLine(cx - 1, cy - 2, cx - 1, cy + 2)
        p.drawLine(cx + 2, cy - 2, cx + 2, cy + 2)
        p.drawLine(cx + 5, cy - 2, cx + 5, cy + 2)
        p.restore()

    def _draw_vector_scissors(self, p: QPainter, cx: int, cy: int, color: QColor = QColor(255, 255, 255)):
        p.save()
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        pen = QPen(color, 1.2)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        p.setPen(pen)
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawEllipse(QPoint(cx - 3, cy + 3), 2, 2)
        p.drawEllipse(QPoint(cx + 3, cy + 3), 2, 2)
        p.drawLine(cx - 2, cy + 1, cx + 4, cy - 5)
        p.drawLine(cx + 2, cy + 1, cx - 4, cy - 5)
        p.restore()

    def _draw_vector_calc(self, p: QPainter, cx: int, cy: int, color: QColor = QColor(255, 255, 255)):
        p.save()
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        pen = QPen(color, 1.2)
        p.setPen(pen)
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRoundedRect(QRectF(cx - 5, cy - 6, 10, 12), 1.5, 1.5)
        p.fillRect(QRectF(cx - 3.5, cy - 4.5, 7, 2.5), color)
        p.setPen(color)
        p.drawPoint(cx - 2, cy + 1)
        p.drawPoint(cx + 2, cy + 1)
        p.drawPoint(cx - 2, cy + 4)
        p.drawPoint(cx + 2, cy + 4)
        p.restore()

    def _draw_vector_notes(self, p: QPainter, cx: int, cy: int, color: QColor = QColor(255, 255, 255)):
        p.save()
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        pen = QPen(color, 1.2)
        p.setPen(pen)
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRoundedRect(QRectF(cx - 5, cy - 6, 10, 12), 1.5, 1.5)
        p.drawLine(cx - 3, cy - 2, cx + 3, cy - 2)
        p.drawLine(cx - 3, cy + 1, cx + 3, cy + 1)
        p.drawLine(cx - 3, cy + 4, cx + 1, cy + 4)
        p.restore()

    def _draw_vector_wallpaper(self, p: QPainter, cx: int, cy: int, color: QColor = QColor(255, 255, 255)):
        p.save()
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        pen = QPen(color, 1.2)
        p.setPen(pen)
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRoundedRect(QRectF(cx - 6, cy - 5, 12, 10), 1.5, 1.5)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(color)
        p.drawEllipse(QPointF(cx + 2.5, cy - 2.0), 1.3, 1.3)
        tri = QPainterPath()
        tri.moveTo(cx - 4.5, cy + 3.5)
        tri.lineTo(cx - 1.0, cy - 0.5)
        tri.lineTo(cx + 1.5, cy + 1.5)
        tri.lineTo(cx + 4.5, cy - 1.0)
        tri.lineTo(cx + 4.5, cy + 3.5)
        tri.closeSubpath()
        p.drawPath(tri)
        p.restore()

    def _draw_vector_lock(self, p: QPainter, cx: int, cy: int, color: QColor = QColor(255, 255, 255)):
        p.save()
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        pen = QPen(color, 1.2)
        p.setPen(pen)
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRoundedRect(QRectF(cx - 4, cy - 1, 8, 7), 1.5, 1.5)
        p.drawArc(QRectF(cx - 2.5, cy - 6, 5, 6), 0, 180 * 16)
        p.restore()

    def _draw_vector_browser_app(self, p: QPainter, cx: float, cy: float, color: QColor = QColor(255, 255, 255)):
        p.save()
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        p.setPen(QPen(color, 1.3))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawEllipse(QPointF(cx, cy), 8.0, 8.0)
        p.drawLine(QPointF(cx - 8.0, cy), QPointF(cx + 8.0, cy))
        p.drawEllipse(QPointF(cx, cy), 4.2, 8.0)
        p.restore()

    def _draw_vector_code_app(self, p: QPainter, cx: float, cy: float, color: QColor = QColor(255, 255, 255)):
        p.save()
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        p.setPen(QPen(color, 1.4, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
        p.drawLine(QPointF(cx - 3.5, cy - 4.5), QPointF(cx - 7.0, cy))
        p.drawLine(QPointF(cx - 7.0, cy), QPointF(cx - 3.5, cy + 4.5))
        p.drawLine(QPointF(cx - 1.0, cy + 5.0), QPointF(cx + 1.0, cy - 5.0))
        p.drawLine(QPointF(cx + 3.5, cy - 4.5), QPointF(cx + 7.0, cy))
        p.drawLine(QPointF(cx + 7.0, cy), QPointF(cx + 3.5, cy + 4.5))
        p.restore()

    def _draw_vector_spotify_app(self, p: QPainter, cx: float, cy: float, color: QColor = QColor(255, 255, 255)):
        p.save()
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        p.setPen(QPen(color, 1.3, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        p.drawArc(QRectF(cx - 7.0, cy - 6.0, 14.0, 8.0), 35 * 16, 110 * 16)
        p.drawArc(QRectF(cx - 5.5, cy - 2.5, 11.0, 7.0), 35 * 16, 110 * 16)
        p.drawArc(QRectF(cx - 4.0, cy + 1.0, 8.0, 6.0), 35 * 16, 110 * 16)
        p.restore()

    def _draw_vector_discord_app(self, p: QPainter, cx: float, cy: float, color: QColor = QColor(255, 255, 255)):
        p.save()
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        p.setPen(QPen(color, 1.2))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRoundedRect(QRectF(cx - 8.0, cy - 5.5, 16.0, 11.0), 3.5, 3.5)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(color)
        p.drawEllipse(QPointF(cx - 3.5, cy), 1.6, 1.6)
        p.drawEllipse(QPointF(cx + 3.5, cy), 1.6, 1.6)
        p.restore()

    def _draw_vector_folder_app(self, p: QPainter, cx: float, cy: float, color: QColor = QColor(255, 255, 255)):
        p.save()
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        p.setPen(QPen(color, 1.2))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRoundedRect(QRectF(cx - 8.0, cy - 4.0, 16.0, 10.0), 1.5, 1.5)
        tab = QPainterPath()
        tab.moveTo(cx - 8.0, cy - 4.0)
        tab.lineTo(cx - 8.0, cy - 6.5)
        tab.lineTo(cx - 3.0, cy - 6.5)
        tab.lineTo(cx - 1.5, cy - 4.0)
        p.drawPath(tab)
        p.restore()

    def _draw_vector_terminal_app(self, p: QPainter, cx: float, cy: float, color: QColor = QColor(255, 255, 255)):
        p.save()
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        p.setPen(QPen(color, 1.2))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRoundedRect(QRectF(cx - 8.0, cy - 5.5, 16.0, 11.0), 1.8, 1.8)
        p.setPen(QPen(color, 1.2, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
        p.drawLine(QPointF(cx - 5.0, cy - 2.5), QPointF(cx - 2.5, cy))
        p.drawLine(QPointF(cx - 2.5, cy), QPointF(cx - 5.0, cy + 2.5))
        p.drawLine(QPointF(cx - 0.5, cy + 2.5), QPointF(cx + 4.0, cy + 2.5))
        p.restore()

    def _draw_vector_bluetooth(self, p: QPainter, cx: int, cy: int, is_connected: bool = True, color: QColor = QColor(0, 122, 255)):
        p.save()
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        pen = QPen(color, 1.4)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        p.setPen(pen)
        p.setBrush(Qt.BrushStyle.NoBrush)

        bt = QPainterPath()
        # Vertical spine
        bt.moveTo(cx, cy - 7)
        bt.lineTo(cx, cy + 7)
        # Upper loop & cross
        bt.moveTo(cx - 4, cy - 3.5)
        bt.lineTo(cx + 4, cy + 3.5)
        bt.lineTo(cx, cy + 7)
        # Lower loop & cross
        bt.lineTo(cx + 4, cy - 3.5)
        bt.lineTo(cx - 4, cy + 3.5)
        p.drawPath(bt)
        p.restore()

    def _draw_vector_chatgpt(self, p: QPainter, cx: int, cy: int, color: QColor = QColor(16, 163, 127), scale: float = 1.0):
        """Vector representation of OpenAI / ChatGPT rosette icon."""
        p.save()
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        p.translate(cx, cy)
        p.scale(scale, scale)
        pen = QPen(color, 1.3)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        p.setPen(pen)
        p.setBrush(Qt.BrushStyle.NoBrush)
        for i in range(6):
            p.save()
            p.rotate(i * 60)
            p.drawArc(QRectF(-4.5, -6.5, 9, 9), 30 * 16, 180 * 16)
            p.restore()
        p.restore()

    def _draw_vector_map_pin(self, p: QPainter, cx: int, cy: int, color: QColor = QColor(234, 67, 53)):
        """Vector Google Maps Pin icon."""
        p.save()
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(color)

        pin = QPainterPath()
        pin.moveTo(cx, cy + 6)
        pin.cubicTo(cx - 5.5, cy + 1, cx - 5.5, cy - 4, cx, cy - 4)
        pin.cubicTo(cx + 5.5, cy - 4, cx + 5.5, cy + 1, cx, cy + 6)
        pin.closeSubpath()
        p.drawPath(pin)

        # Center cutout
        p.setBrush(QColor(255, 255, 255))
        p.drawEllipse(QPoint(cx, cy - 1), 2, 2)
        p.restore()

    def _draw_vector_compass_icon(self, p: QPainter, cx: int, cy: int, color: QColor = QColor(255, 255, 255)):
        """Vector compact compass icon for tab headers."""
        p.save()
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        pen = QPen(color, 1.2)
        p.setPen(pen)
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawEllipse(QPoint(cx, cy), 6, 6)

        needle = QPainterPath()
        needle.moveTo(cx, cy - 4.5)
        needle.lineTo(cx + 2.5, cy + 2.5)
        needle.lineTo(cx - 2.5, cy + 2.5)
        needle.closeSubpath()
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(color)
        p.drawPath(needle)
        p.restore()

    def _draw_vector_directions(self, p: QPainter, cx: int, cy: int, color: QColor = QColor(66, 133, 244)):
        """Vector route turn / navigation direction arrow."""
        p.save()
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        pen = QPen(color, 1.3)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        p.setPen(pen)
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawArc(QRectF(cx - 4, cy - 4, 8, 8), 0, 90 * 16)
        p.drawLine(cx, cy - 4, cx + 4, cy - 4)
        p.drawLine(cx + 4, cy - 4, cx + 2, cy - 6)
        p.drawLine(cx + 4, cy - 4, cx + 2, cy - 2)
        p.restore()

    def _draw_vector_satellite(self, p: QPainter, cx: int, cy: int, color: QColor = QColor(251, 188, 4)):
        """Vector orbital satellite icon."""
        p.save()
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        pen = QPen(color, 1.2)
        p.setPen(pen)
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRoundedRect(QRectF(cx - 2.5, cy - 2.5, 5, 5), 1, 1)
        p.drawLine(cx - 5, cy, cx - 2.5, cy)
        p.drawLine(cx + 2.5, cy, cx + 5, cy)
        p.drawArc(QRectF(cx - 5, cy - 5, 10, 10), 45 * 16, 90 * 16)
        p.restore()

    def _draw_vector_traffic(self, p: QPainter, cx: int, cy: int, color: QColor = QColor(52, 168, 83)):
        """Vector traffic congestion lights icon."""
        p.save()
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(234, 67, 53))
        p.drawEllipse(QPoint(cx, cy - 4), 1.5, 1.5)
        p.setBrush(QColor(251, 188, 4))
        p.drawEllipse(QPoint(cx, cy), 1.5, 1.5)
        p.setBrush(QColor(52, 168, 83))
        p.drawEllipse(QPoint(cx, cy + 4), 1.5, 1.5)
        p.restore()

    def _draw_vector_battery(self, p: QPainter, x: int, y: int, percent: int, is_plugged: bool = False, color: QColor = QColor(255, 255, 255), is_charging: Optional[bool] = None, **kwargs):
        """Vector Apple/Bloom Battery symbol with charge fill and optional charging bolt."""
        if is_charging is not None:
            is_plugged = is_charging
        p.save()
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        # Battery body outline
        body_rect = QRectF(x, y, 22, 11)
        pen = QPen(color, 1.2)
        p.setPen(pen)
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRoundedRect(body_rect, 3.0, 3.0)

        # Terminal cap
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(color)
        p.drawRoundedRect(QRectF(x + 22.8, y + 3, 2, 5), 1, 1)

        # Fill level
        fill_w = max(2.0, min(18.0, 18.0 * (percent / 100.0)))
        fill_col = QColor(52, 199, 89) if percent > 20 else QColor(255, 59, 48)
        p.setBrush(fill_col)
        p.drawRoundedRect(QRectF(x + 2, y + 2, fill_w, 7), 2.0, 2.0)

        # Lightning bolt if charging
        if is_plugged:
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor(255, 255, 255))
            poly = QPolygonF([
                QPointF(x + 12, y + 1),
                QPointF(x + 8.5, y + 6),
                QPointF(x + 11.5, y + 6),
                QPointF(x + 10, y + 10),
                QPointF(x + 14.5, y + 5),
                QPointF(x + 11.5, y + 5),
            ])
            p.drawPolygon(poly)

        p.restore()

    def _draw_vector_taskbar_icon(self, p: QPainter, cx: float, cy: float, color: QColor):
        p.save()
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        mon_w, mon_h = 16.0, 11.0
        x = cx - mon_w / 2.0
        y = cy - mon_h / 2.0 - 2.0
        p.setPen(QPen(color, 1.3))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRoundedRect(QRectF(x, y, mon_w, mon_h), 2.5, 2.5)
        p.drawLine(QPointF(cx, y + mon_h), QPointF(cx, y + mon_h + 3.0))
        p.drawLine(QPointF(cx - 3.5, y + mon_h + 3.0), QPointF(cx + 3.5, y + mon_h + 3.0))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(color)
        p.drawRoundedRect(QRectF(x + 2.0, y + mon_h - 3.0, mon_w - 4.0, 1.8), 0.8, 0.8)
        p.restore()

    def _draw_vector_wifi(self, p: QPainter, cx: int, cy: int, size: int = 14, color: QColor = QColor(255, 255, 255)):
        """Vector Wi-Fi waves and dot."""
        p.save()
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        pen = QPen(color, 1.4)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        p.setPen(pen)
        p.setBrush(Qt.BrushStyle.NoBrush)
        # 3 Arcs
        p.drawArc(QRectF(cx - 7, cy - 7, 14, 14), 45 * 16, 90 * 16)
        p.drawArc(QRectF(cx - 4.5, cy - 4.5, 9, 9), 45 * 16, 90 * 16)
        p.drawArc(QRectF(cx - 2, cy - 2, 4, 4), 45 * 16, 90 * 16)
        # Dot
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(color)
        p.drawEllipse(QPointF(cx, cy + 3.5), 1.2, 1.2)
        p.restore()

    def _draw_vector_sliders_icon(self, p: QPainter, cx: int, cy: int, size: int = 13, color: QColor = QColor(255, 255, 255)):
        """Vector iOS/Bloom Control Center Sliders Icon."""
        p.save()
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        pen = QPen(color, 1.3)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        p.setPen(pen)

        # Left vertical line with upper knob
        p.drawLine(cx - 3.5, cy - 5.5, cx - 3.5, cy + 5.5)
        p.setBrush(color)
        p.drawEllipse(QPointF(cx - 3.5, cy - 2), 2.2, 2.2)

        # Right vertical line with lower knob
        p.drawLine(cx + 3.5, cy - 5.5, cx + 3.5, cy + 5.5)
        p.drawEllipse(QPointF(cx + 3.5, cy + 2), 2.2, 2.2)
        p.restore()

    def _draw_vector_calendar_icon(self, p: QPainter, cx: int, cy: int, size: int = 13, color: QColor = QColor(255, 255, 255)):
        """Vector Mini Calendar page icon."""
        p.save()
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        pen = QPen(color, 1.2)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        p.setPen(pen)
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRoundedRect(QRectF(cx - 5.5, cy - 5.5, 11, 11), 2.5, 2.5)

        # Header divider
        p.drawLine(cx - 5.5, cy - 2, cx + 5.5, cy - 2)

        # Binder rings on top
        p.drawLine(cx - 3, cy - 7, cx - 3, cy - 5)
        p.drawLine(cx + 3, cy - 7, cx + 3, cy - 5)

        # Day dots
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(color)
        p.drawRect(QRectF(cx - 3.5, cy + 0.5, 1.5, 1.5))
        p.drawRect(QRectF(cx - 0.7, cy + 0.5, 1.5, 1.5))
        p.drawRect(QRectF(cx + 2.0, cy + 0.5, 1.5, 1.5))
        p.drawRect(QRectF(cx - 3.5, cy + 3.0, 1.5, 1.5))
        p.drawRect(QRectF(cx - 0.7, cy + 3.0, 1.5, 1.5))
        p.drawRect(QRectF(cx + 2.0, cy + 3.0, 1.5, 1.5))
        p.restore()

    def _draw_vector_moon(self, p: QPainter, cx: int, cy: int, size: int = 13, color: QColor = QColor(255, 255, 255)):
        """Vector Crescent Moon icon for Focus / Night mode."""
        p.save()
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        path = QPainterPath()
        r = size / 2.0
        path.moveTo(cx, cy - r)
        path.arcTo(QRectF(cx - r, cy - r, size, size), 90, -180)
        path.arcTo(QRectF(cx - r * 0.4, cy - r, size * 0.8, size), 270, 180)
        path.closeSubpath()
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(color)
        p.drawPath(path)
        p.restore()

    def _draw_vector_launchpad(self, p: QPainter, cx: int, cy: int, size: int = 12, color: QColor = QColor(255, 255, 255)):
        """Vector App Grid / Launchpad icon."""
        p.save()
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(color)
        offsets = [-3.5, 0, 3.5]
        for ox in offsets:
            for oy in offsets:
                p.drawRoundedRect(QRectF(cx + ox - 1, cy + oy - 1, 2, 2), 0.5, 0.5)
        p.restore()

    def _draw_vector_bell(self, p: QPainter, cx: int, cy: int, size: int = 13, color: QColor = QColor(255, 255, 255)):
        """Vector Notification Bell icon."""
        p.save()
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        pen = QPen(color, 1.2)
        p.setPen(pen)
        p.setBrush(Qt.BrushStyle.NoBrush)
        bell = QPainterPath()
        bell.moveTo(cx - 4.5, cy + 3)
        bell.lineTo(cx + 4.5, cy + 3)
        bell.quadTo(cx + 3.5, cy - 2, cx + 2, cy - 4.5)
        bell.arcTo(QRectF(cx - 2, cy - 6, 4, 3), 0, 180)
        bell.quadTo(cx - 3.5, cy - 2, cx - 4.5, cy + 3)
        bell.closeSubpath()
        p.drawPath(bell)
        p.drawEllipse(QPointF(cx, cy + 4.5), 1.2, 1.2)
        p.restore()

    def _draw_vector_gear(self, p: QPainter, cx: int, cy: int, size: int = 13, color: QColor = QColor(255, 255, 255)):
        """Vector Settings Gear icon."""
        p.save()
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        pen = QPen(color, 1.3)
        p.setPen(pen)
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawEllipse(QPointF(cx, cy), 3, 3)
        for ang in range(0, 360, 60):
            p.save()
            p.translate(cx, cy)
            p.rotate(ang)
            p.drawLine(0, -4.5, 0, -6)
            p.restore()
        p.restore()

    def _draw_vector_refresh(self, p: QPainter, cx: int, cy: int, size: int = 13, color: QColor = QColor(255, 255, 255)):
        """Vector circular refresh / restart arrow."""
        p.save()
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        pen = QPen(color, 1.3)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        p.setPen(pen)
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawArc(QRectF(cx - 5, cy - 5, 10, 10), 45 * 16, 270 * 16)
        # Arrowhead
        p.drawLine(cx + 2, cy - 5, cx + 5, cy - 5)
        p.drawLine(cx + 5, cy - 5, cx + 5, cy - 2)
        p.restore()

    def _draw_precision_compass(self, p: QPainter, cx: int, cy: int, r: int, heading: float, theme: dict):
        """Precision Apple Watch Ultra / iOS Compass Dial with 360-deg ring and 3D needle."""
        p.save()
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        # Outer bezel ring
        p.setPen(QPen(QColor(255, 255, 255, 45), 1.2))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawEllipse(QPoint(cx, cy), r, r)

        # Dial rotation
        p.save()
        p.translate(cx, cy)
        p.rotate(-heading)

        # Tick marks
        for deg in range(0, 360, 15):
            p.save()
            p.rotate(deg)
            is_cardinal = (deg % 90 == 0)
            is_sub = (deg % 30 == 0)
            tick_len = 5 if is_cardinal else (3.5 if is_sub else 2)
            tick_alpha = 240 if is_cardinal else (160 if is_sub else 80)

            if deg == 0:
                p.setPen(QPen(QColor(239, 68, 68, 255), 1.5))
            else:
                p.setPen(QPen(QColor(255, 255, 255, tick_alpha), 1.0 if not is_cardinal else 1.3))

            p.drawLine(0, -r + 1, 0, -r + 1 + tick_len)
            p.restore()

        # Cardinal Letters N, E, S, W
        p.setFont(QFont("Segoe UI", 7, QFont.Weight.Bold))
        # N
        p.setPen(QColor(239, 68, 68))
        p.drawText(QRect(-8, -r + 6, 16, 12), Qt.AlignmentFlag.AlignCenter, "N")
        # E
        p.setPen(QColor(255, 255, 255, 210))
        p.drawText(QRect(r - 16, -6, 14, 12), Qt.AlignmentFlag.AlignCenter, "E")
        # S
        p.drawText(QRect(-7, r - 16, 14, 12), Qt.AlignmentFlag.AlignCenter, "S")
        # W
        p.drawText(QRect(-r + 2, -6, 14, 12), Qt.AlignmentFlag.AlignCenter, "W")

        p.restore()  # Undo rotation for center needle

        # 3D Magnetic Needle
        p.save()
        p.translate(cx, cy)

        # North Pointer (Red / Magma)
        needle_n = QPainterPath()
        needle_n.moveTo(0, -r + 7)
        needle_n.lineTo(3.5, 0)
        needle_n.lineTo(0, -2)
        needle_n.closeSubpath()
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(239, 68, 68, 250))
        p.drawPath(needle_n)

        needle_n_shade = QPainterPath()
        needle_n_shade.moveTo(0, -r + 7)
        needle_n_shade.lineTo(-3.5, 0)
        needle_n_shade.lineTo(0, -2)
        needle_n_shade.closeSubpath()
        p.setBrush(QColor(185, 28, 28, 240))
        p.drawPath(needle_n_shade)

        # South Pointer (White / Silver)
        needle_s = QPainterPath()
        needle_s.moveTo(0, r - 7)
        needle_s.lineTo(3.5, 0)
        needle_s.lineTo(0, 2)
        needle_s.closeSubpath()
        p.setBrush(QColor(226, 232, 240, 220))
        p.drawPath(needle_s)

        needle_s_shade = QPainterPath()
        needle_s_shade.moveTo(0, r - 7)
        needle_s_shade.lineTo(-3.5, 0)
        needle_s_shade.lineTo(0, 2)
        needle_s_shade.closeSubpath()
        p.setBrush(QColor(148, 163, 184, 200))
        p.drawPath(needle_s_shade)

        # Center Pivot Metallic Ring
        p.setPen(QPen(QColor(255, 255, 255, 120), 1.0))
        p.setBrush(QColor(15, 23, 42))
        p.drawEllipse(QPoint(0, 0), 3, 3)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(239, 68, 68))
        p.drawEllipse(QPoint(0, 0), 1, 1)

        p.restore()
        p.restore()

    # ── Dynamic Island System HUD & Screen Copilot ───────────────────────────

    def show_system_hud(self, hud_type: str, val: int = 0, text: str = "", duration: float = 2.0, extra: str = ""):
        """Triggers a high-priority sleek Apple-style Dynamic Island System Capsule."""
        self._sys_hud_toast_type = hud_type
        self._sys_hud_toast_val = val
        self._sys_hud_toast_text = text
        self._sys_hud_toast_data = extra
        self._sys_hud_toast_time = time.monotonic()
        if getattr(self, "_is_retracted", False):
            self.unretract()
        self._wake_timer()
        self.update()

    def trigger_vision_scan(self, target_x=None, target_y=None, label=""):
        """Triggers the full-screen holographic blue laser scan overlay (Codex / Claude style)."""
        try:
            if hasattr(self, "_vision_overlay") and self._vision_overlay:
                if threading.current_thread() != threading.main_thread():
                    QTimer.singleShot(0, lambda: self._vision_overlay.trigger(target_x, target_y, label))
                else:
                    self._vision_overlay.trigger(target_x, target_y, label)
        except Exception as e:
            print(f"[OriginIsland] Warning in trigger_vision_scan: {e}")

    def analyze_screen(self):
        """JARVIS Screen Copilot: Captures foreground/screen, runs multi-modal vision perception with Codex/Claude blue laser scan."""
        self._assistant_query = "Analyze current screen"
        self._assistant_status = "Scanning..."
        self._assistant_status_detail = "Perceiving active window & text..."
        self._assistant_reply = ""
        self._assistant_typewriter_idx = 0
        self._assistant_tool_action = "screen_copilot"
        self._wake_timer()
        self.update()

        # Trigger full-screen holographic blue laser scan sweep
        self.trigger_vision_scan(label="Full Display Perception")

        def _worker():
            active_title = ""
            try:
                import pygetwindow as gw
                win = gw.getActiveWindow()
                if win and win.title:
                    active_title = win.title.strip()
            except Exception:
                pass

            summary = ""
            try:
                from control import vision
                summary = vision.describe_screen()
            except Exception as e:
                print(f"[ScreenCopilot] describe_screen error: {e}")

            if not summary or "error" in summary.lower() or summary.startswith("Active window captured"):
                # Fallback to high-speed Windows Native OCR
                ocr_text = ""
                try:
                    from control import vision
                    ocr_text = vision.read_screen_text()
                except Exception:
                    pass
                if ocr_text and "No readable text" not in ocr_text:
                    summary = f"Screen perception active on '{active_title or 'Desktop'}': {ocr_text[:160]}..."
                elif active_title:
                    summary = f"I scanned your screen. You are currently working in '{active_title}' with all systems nominal."
                else:
                    summary = "Screen scanned with visual perception. Display clear with all systems operating nominally."

            self._assistant_reply = summary
            self._assistant_status = "Speaking..." if self._voice_output_enabled else "Ready"
            self._assistant_status_detail = "Ready"
            self._is_jarvis_talking = self._voice_output_enabled
            self._live_jarvis_speech = summary
            self._jarvis_speech_time = time.monotonic()
            self._jarvis_compact_ticker_x = 0.0
            self._assistant_typewriter_idx = 0
            self._wake_timer()
            self.update()

            if self._voice_output_enabled:
                def _speak():
                    try:
                        from audio import speaker
                        speaker.speak(summary)
                    except Exception:
                        pass
                    finally:
                        self._is_jarvis_talking = False
                        self._assistant_status = "Ready"
                        self._assistant_status_detail = "Ready"
                        self._wake_timer()

                threading.Thread(target=_speak, daemon=True, name="screen_copilot_speech").start()

        threading.Thread(target=_worker, daemon=True, name="screen_copilot").start()

    # ── Paint Engine (Luxury Glass & Morphing Graphics) ──────────────────────

    def _is_flush_notch(self) -> bool:
        """Returns True if the island is docked to the top monitor bezel in flush hanging style."""
        if self._position_mode != "top_notch":
            return False
        if getattr(self, "_notch_style", "flush_notch") != "flush_notch":
            return False
        if getattr(self, "_is_dragging", False) and self.y() > 35:
            return False
        return True

    def _make_notch_path(self, w: float, h: float, radius: float, is_flush: bool) -> QPainterPath:
        path = QPainterPath()
        if not is_flush:
            r = min(radius, (h - 2.0) / 2.0)
            path.addRoundedRect(QRectF(1.0, 1.0, max(10.0, w - 2.0), max(10.0, h - 2.0)), r, r)
            return path

        # True Organic Hanging Bezel Notch (Concave ear fillets flare up into monitor bezel)
        ear_h = min(14.0, max(8.0, h * 0.32))
        ear_w = ear_h * 1.25
        bot_r = min(radius, (h - 2.0) / 2.0 if h <= 48 else radius)

        path.moveTo(0.0, 0.0)
        path.cubicTo(ear_w * 0.55, 0.0, ear_w, ear_h * 0.45, ear_w, ear_h)
        path.lineTo(ear_w, h - bot_r)
        path.cubicTo(ear_w, h - bot_r * 0.45, ear_w + bot_r * 0.45, h, ear_w + bot_r, h)
        path.lineTo(w - ear_w - bot_r, h)
        path.cubicTo(w - ear_w - bot_r * 0.45, h, w - ear_w, h - bot_r * 0.45, w - ear_w, h - bot_r)
        path.lineTo(w - ear_w, ear_h)
        path.cubicTo(w - ear_w, ear_h * 0.45, w - ear_w * 0.55, 0.0, w, 0.0)
        path.closeSubpath()
        return path

    def _make_notch_outline_path(self, w: float, h: float, radius: float, is_flush: bool) -> QPainterPath:
        path = QPainterPath()
        if not is_flush:
            r = min(radius, (h - 2.0) / 2.0)
            path.addRoundedRect(QRectF(1.0, 1.0, max(10.0, w - 2.0), max(10.0, h - 2.0)), r, r)
            return path

        ear_h = min(14.0, max(8.0, h * 0.32))
        ear_w = ear_h * 1.25
        bot_r = min(radius, (h - 2.0) / 2.0 if h <= 48 else radius)

        path.moveTo(0.0, 0.0)
        path.cubicTo(ear_w * 0.55, 0.0, ear_w, ear_h * 0.45, ear_w, ear_h)
        path.lineTo(ear_w, h - bot_r)
        path.cubicTo(ear_w, h - bot_r * 0.45, ear_w + bot_r * 0.45, h, ear_w + bot_r, h)
        path.lineTo(w - ear_w - bot_r, h)
        path.cubicTo(w - ear_w - bot_r * 0.45, h, w - ear_w, h - bot_r * 0.45, w - ear_w, h - bot_r)
        path.lineTo(w - ear_w, ear_h)
        path.cubicTo(w - ear_w, ear_h * 0.45, w - ear_w * 0.55, 0.0, w, 0.0)
        return path

    def _get_notch_flank_point(self, u: float, is_right: bool, w: float, h: float, r: float, is_flush: bool) -> tuple:
        """
        Calculates the exact subpixel coordinates along the notch's left or right edge contour
        for dual-side flowing drop wave animations.
        u: 0.0 (top center) -> 1.0 (bottom center)
        """
        u = max(0.0, min(1.0, u))
        r = min(r, (h - 2.0) / 2.0)
        if not is_right:
            if u <= 0.30:
                st = u / 0.30
                return (w / 2.0 - st * (w / 2.0 - r), 1.0)
            elif u <= 0.50:
                st = (u - 0.30) / 0.20
                ang = math.pi * 1.5 - st * (math.pi / 2.0)
                return (r + r * math.cos(ang), r + r * math.sin(ang))
            elif u <= 0.70:
                st = (u - 0.50) / 0.20
                return (1.0, r + st * (h - 2 * r))
            elif u <= 0.85:
                st = (u - 0.70) / 0.15
                ang = math.pi - st * (math.pi / 2.0)
                return (r + r * math.cos(ang), (h - r) + r * math.sin(ang))
            else:
                st = (u - 0.85) / 0.15
                return (r + st * (w / 2.0 - r), h - 1.0)
        else:
            if u <= 0.30:
                st = u / 0.30
                return (w / 2.0 + st * (w / 2.0 - r), 1.0)
            elif u <= 0.50:
                st = (u - 0.30) / 0.20
                ang = math.pi * 1.5 + st * (math.pi / 2.0)
                return ((w - r) + r * math.cos(ang), r + r * math.sin(ang))
            elif u <= 0.70:
                st = (u - 0.50) / 0.20
                return (w - 1.0, r + st * (h - 2 * r))
            elif u <= 0.85:
                st = (u - 0.70) / 0.15
                ang = 0.0 + st * (math.pi / 2.0)
                return ((w - r) + r * math.cos(ang), (h - r) + r * math.sin(ang))
            else:
                st = (u - 0.85) / 0.15
                return ((w - r) - st * ((w - r) - w / 2.0), h - 1.0)

    def _draw_edge_beat_glow(self, p: QPainter, w: int, h: int, radius: float, is_flush: bool):
        """
        Clean, razor-sharp 1.0px hairline frosted glass rim.
        Completely eliminates thick outer glow, neon halo, or colored borders.
        Provides an ultra-clean, minimal Apple Dynamic Island & OriginOS aesthetic
        matching modern luxury hardware across all transparency levels.
        """
        if getattr(self, "_is_retracted", False) or w <= 68 or h <= 18:
            return

        outline_path = self._make_notch_outline_path(w, h, radius, is_flush)
        p.save()
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        # 1.0px hairline specular glass border: subtle neutral white reflection
        # Top specular highlight fading gently down the sides
        glass_grad = QLinearGradient(0, 0, 0, h)
        glass_grad.setColorAt(0.0, QColor(255, 255, 255, 36))
        glass_grad.setColorAt(0.25, QColor(255, 255, 255, 24))
        glass_grad.setColorAt(1.0, QColor(255, 255, 255, 14))

        p.strokePath(outline_path, QPen(QBrush(glass_grad), 1.0, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
        p.restore()

    def _draw_rgb_edge_waves(self, p: QPainter, w: int, h: int, radius: float, is_flush: bool):
        """
        Renders sleek, elegant, minimal pure-white waterdrop sheens cascading down both flanks
        of the notch in compact mode. Strictly encapsulated inside notch geometry.
        Completely suppressed on expanded cards so no colored drops bleed on card borders.
        """
        # Skip if retracted into micro trigger to preserve 0.0% CPU usage
        if getattr(self, "_is_retracted", False) or w <= 68 or h <= 18:
            return

        # Edge waves only active if explicitly enabled in settings (default OFF for clean, flush border)
        if not self._settings or not self._settings.get("enable_edge_glow", False):
            return

        # CRITICAL: Only draw subtle waterdrop sheen in compact mode!
        # Suppress completely on expanded cards (Music, Weather, Assistant, Control Center, etc.)
        # so borders stay clean, sleek, and unobtrusive.
        if self._state != self.STATE_COMPACT:
            return

        is_music = self._is_genuine_music_playing()
        beat = getattr(self, "_ambient_beat_energy", 0.0)
        t = getattr(self, "_anim_time", 0.0)

        p.save()
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        # 0. Strictly clip to notch geometry so glow NEVER bleeds outside into desktop/apps
        notch_clip = self._make_notch_path(w, h, radius, is_flush)
        p.setClipPath(notch_clip)

        # Drop velocity scales dynamically with music rhythm
        drop_speed = 0.50 + (beat * 0.70 if is_music else 0.0)
        num_drops = 2

        for drop_idx in range(num_drops):
            base_u_raw = (t * drop_speed + drop_idx * 0.50) % 1.0
            # When flush to top screen bezel, map u smoothly to start below bezel
            base_u = (0.05 + base_u_raw * 0.94) if is_flush else base_u_raw
            tail_len = 0.22 + (beat * 0.06 if is_music else 0.0)

            # Left and Right cascading pure white liquid drops ("white thing normal one")
            for is_right in [False, True]:
                # 1. Smooth glowing pure white wave trail
                trail_steps = 18
                prev_pt = None
                for step in range(trail_steps):
                    frac = step / float(trail_steps)
                    u_cur = base_u - (1.0 - frac) * tail_len
                    if u_cur < 0.0 or u_cur > 1.0:
                        continue

                    pt = self._get_notch_flank_point(u_cur, is_right, w, h, radius, is_flush)
                    if prev_pt is not None:
                        # Fade in gracefully near top screen edge to eliminate sharp horns
                        top_fade = min(1.0, max(0.0, pt[1] / 8.0)) if is_flush else 1.0

                        # Pure frosted white liquid sheen
                        alpha = int((frac**2.0) * (130 if is_music else 75) * top_fade)
                        white_col = QColor(255, 255, 255, alpha)

                        stroke_w = 1.0 + frac * (1.8 + (beat * 0.6 if is_music else 0.0))
                        p.setPen(QPen(white_col, stroke_w, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
                        p.drawLine(QPointF(prev_pt[0], prev_pt[1]), QPointF(pt[0], pt[1]))

                        # Outer soft frosted halo
                        if frac > 0.60 and alpha > 25:
                            glow_col = QColor(255, 255, 255, int(alpha * 0.30))
                            p.setPen(QPen(glow_col, stroke_w + 2.0, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
                            p.drawLine(QPointF(prev_pt[0], prev_pt[1]), QPointF(pt[0], pt[1]))

                    prev_pt = pt

                # 2. Glowing Liquid Drop Head Bead (Pure White Specular)
                head_pt = self._get_notch_flank_point(base_u, is_right, w, h, radius, is_flush)
                head_fade = min(1.0, max(0.0, head_pt[1] / 8.0)) if is_flush else 1.0
                if head_fade > 0.05:
                    head_radius = (2.0 + (beat * 0.6 if is_music else 0.0)) * head_fade

                    # Pure white ambient bloom halo
                    glow_r = (6.5 + (beat * 2.0 if is_music else 0.0)) * head_fade
                    glow = QRadialGradient(head_pt[0], head_pt[1], glow_r)
                    glow_alpha = int((140 if is_music else 90) * head_fade)
                    glow.setColorAt(0.0, QColor(255, 255, 255, glow_alpha))
                    glow.setColorAt(0.5, QColor(255, 255, 255, int(glow_alpha * 0.30)))
                    glow.setColorAt(1.0, QColor(0, 0, 0, 0))
                    p.setPen(Qt.PenStyle.NoPen)
                    p.setBrush(glow)
                    p.drawEllipse(QPointF(head_pt[0], head_pt[1]), glow_r, glow_r)

                    # Droplet bead core
                    p.setBrush(QColor(255, 255, 255, int(220 * head_fade)))
                    p.drawEllipse(QPointF(head_pt[0], head_pt[1]), head_radius, head_radius)

                    # Specular photon gleam
                    p.setBrush(QColor(255, 255, 255, int(255 * head_fade)))
                    p.drawEllipse(QPointF(head_pt[0] - 0.5, head_pt[1] - 0.5), 1.0, 1.0)

        # 3. Bottom Collision Ripple (when drops meet at bottom center)
        for drop_idx in range(num_drops):
            base_u = (t * drop_speed + drop_idx * 0.50) % 1.0
            if base_u > 0.88:
                rip_progress = (base_u - 0.88) / 0.12
                rip_w = 4.0 + rip_progress * 18.0
                rip_h = 1.0 + rip_progress * 2.0
                rip_alpha = int((1.0 - rip_progress) * (110 if is_music else 60))
                p.setPen(QPen(QColor(255, 255, 255, rip_alpha), 1.2))
                p.setBrush(Qt.BrushStyle.NoBrush)
                p.drawEllipse(QPointF(w / 2.0, h - 0.5), rip_w, rip_h)

        p.restore()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)

        is_genuine_music = self._is_genuine_music_playing()
        base_theme = ISLAND_THEMES.get(self._theme_key, ISLAND_THEMES["amoled_black"])
        theme = dict(base_theme)

        # Dynamic cover art accent color for foreground interactive elements (bars, scrubbers, highlights)
        accent = getattr(self, "_dynamic_accent_color", QColor(240, 181, 166))
        art_r, art_g, art_b = accent.red(), accent.green(), accent.blue()

        # Pure AMOLED / OLED Black base across all views - "BLACK IS IMPORTANT"
        theme["bg_top"] = QColor(0, 0, 0, 255)
        theme["bg_bottom"] = QColor(0, 0, 0, 255)
        theme["notch_gradient"] = (QColor(0, 0, 0, 255), QColor(0, 0, 0, 255))
        theme["accent"] = accent if is_genuine_music else QColor(255, 255, 255)
        theme["border"] = QColor(255, 255, 255, 24)
        theme["border_width"] = 1.0
        theme["btn_hover"] = QColor(art_r, art_g, art_b, 75) if is_genuine_music else QColor(255, 255, 255, 55)
        theme["card_bg"] = QColor(16, 16, 18, 220)
        theme["card_hover"] = QColor(26, 26, 30, 240)
        theme["text_primary"] = QColor(255, 255, 255)
        theme["text_secondary"] = QColor(160, 160, 165)

        w, h = self.width(), self.height()
        radius = self._corner_radius
        is_music_active = is_genuine_music
        beat = self._ambient_beat_energy
        c_pri = self._ambient_color_current
        c_sec = self._ambient_color_secondary
        t = self._anim_time

        # 1. Main Pill Body Path
        is_flush_notch = self._is_flush_notch()
        path = self._make_notch_path(w, h, radius, is_flush_notch)

        # 2. Pure AMOLED Black Base Fill
        op_mult = getattr(self, "_background_opacity", 80) / 100.0
        c_top = QColor(theme["bg_top"])
        c_bot = QColor(theme["bg_bottom"])
        c_top.setAlpha(int(c_top.alpha() * op_mult))
        c_bot.setAlpha(int(c_bot.alpha() * op_mult))
        grad = QLinearGradient(0, 0, 0, h)
        grad.setColorAt(0.0, c_top)
        grad.setColorAt(1.0, c_bot)
        painter.fillPath(path, grad)

        # 2b. Internal Beat-Reactive Fluid Ambient Light Mesh (Only subtle in compact mode, suppressed on expanded cards)
        if (is_music_active or beat > 0.05) and self._state == self.STATE_COMPACT:
            mesh_alpha = int(max(6, min(20, 6 + beat * 14)))
            mesh_x = 50 + math.cos(t * 1.5) * (w * 0.4)
            mesh_y = (h * 0.45) + math.sin(t * 2.0) * (h * 0.2)
            mesh_grad = QRadialGradient(mesh_x, mesh_y, max(w * 0.65, 100))
            mesh_grad.setColorAt(0.0, QColor(c_pri.red(), c_pri.green(), c_pri.blue(), mesh_alpha))
            mesh_grad.setColorAt(0.65, QColor(c_sec.red(), c_sec.green(), c_sec.blue(), int(mesh_alpha * 0.35)))
            mesh_grad.setColorAt(1.0, QColor(0, 0, 0, 0))

            painter.save()
            painter.setClipPath(path)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(mesh_grad)
            painter.drawPath(path)

            # Special Style Internal Shaders
            style = self._ambient_style
            if style == "aurora_borealis":
                # Wavy Aurora Ribbons inside glass
                painter.setPen(Qt.PenStyle.NoPen)
                for layer_i in range(2):
                    ribbon = QPainterPath()
                    ribbon.moveTo(0, h * 0.5)
                    for rx in range(0, w + 10, 15):
                        ry = (h * 0.5) + math.sin((rx * 0.035) + (t * (2.0 + layer_i * 0.8))) * (12.0 + beat * 10.0)
                        ribbon.lineTo(rx, ry)
                    ribbon.lineTo(w, h)
                    ribbon.lineTo(0, h)
                    ribbon.closeSubpath()
                    rib_col = c_pri if layer_i == 0 else c_sec
                    painter.setBrush(QColor(rib_col.red(), rib_col.green(), rib_col.blue(), int(18 + beat * 30)))
                    painter.drawPath(ribbon)

            elif style == "lava_fire_glow":
                # Ascending Magma Embers inside glass
                painter.setPen(Qt.PenStyle.NoPen)
                for ember in self._lava_embers:
                    e_alpha = int(ember["alpha"] * (60 + beat * 150))
                    painter.setBrush(QColor(249, 115, 22, min(255, e_alpha)))
                    painter.drawEllipse(QPointF(ember["x"], ember["y"]), ember["r"], ember["r"])

            elif style == "neon_cyber_pulse" and beat > 0.5:
                # Laser Corner Flares
                painter.setPen(QPen(QColor(0, 240, 255, int(100 * beat)), 1.5))
                painter.drawLine(8, 8, 28, 8)
                painter.drawLine(8, 8, 8, 24)
                painter.setPen(QPen(QColor(255, 0, 128, int(100 * beat)), 1.5))
                painter.drawLine(w - 28, h - 8, w - 8, h - 8)
                painter.drawLine(w - 8, h - 24, w - 8, h - 8)

            elif style == "sunset_chroma":
                # Synthwave dusk horizon line
                sun_grad = QLinearGradient(0, h - 20, 0, h)
                sun_grad.setColorAt(0.0, QColor(245, 158, 11, 0))
                sun_grad.setColorAt(1.0, QColor(225, 29, 72, int(35 + beat * 45)))
                painter.setBrush(sun_grad)
                painter.drawRect(0, h - 20, w, 20)

            elif style == "minimal_frost":
                # Frosted glass shimmer outline
                shimmer_x = (t * 60.0) % (w + 100) - 50
                shim_grad = QLinearGradient(shimmer_x - 30, 0, shimmer_x + 30, 0)
                shim_grad.setColorAt(0.0, QColor(255, 255, 255, 0))
                shim_grad.setColorAt(0.5, QColor(255, 255, 255, int(25 + beat * 35)))
                shim_grad.setColorAt(1.0, QColor(255, 255, 255, 0))
                painter.setBrush(shim_grad)
                painter.drawRect(0, 0, w, h)

            painter.restore()

        # 3. Inner Gloss Highlight (Top curved sheen clipped cleanly to notch path)
        gloss_grad = QLinearGradient(0, 0, 0, h * 0.45)
        gloss_grad.setColorAt(0.0, QColor(255, 255, 255, 40))
        gloss_grad.setColorAt(1.0, QColor(255, 255, 255, 0))
        painter.save()
        painter.setClipPath(path)
        painter.fillPath(path, gloss_grad)
        painter.restore()

        # 4. Luxury Dynamic Edge & Beat Glow (Responsive across all transparent & solid styles)
        self._draw_edge_beat_glow(painter, w, h, radius, is_flush_notch)

        # 4b. Dual-Side Cascading RGB Edge Drop Waves (Encapsulated)
        self._draw_rgb_edge_waves(painter, w, h, radius, is_flush_notch)

        # 5. Render Specific State Content with OriginOS Fluid Morph & Cross-Fade (Expanding & Collapsing)
        if not self._is_morphing:
            if self._state == self.STATE_COMPACT:
                painter.save()
                self._paint_compact(painter, theme, w, h)
                painter.restore()
            else:
                painter.save()
                self._paint_tab_body(painter, self._state, theme, w, h)
                painter.restore()
        else:
            p_val = max(0.0, min(1.0, self._morph_progress))
            expanded_tab = self._state if self._state != self.STATE_COMPACT else getattr(self, "_prev_state", self.STATE_MUSIC)
            if expanded_tab not in self.SIZES or expanded_tab == self.STATE_COMPACT:
                expanded_tab = self.STATE_MUSIC

            # A. Compact Pill Elements (Fades out 0.0 -> 0.38 on expand, fades in 0.38 -> 0.0 on collapse)
            if p_val < 0.38:
                raw_c = max(0.0, min(1.0, (0.38 - p_val) / 0.38))
                compact_alpha = raw_c * raw_c * (3.0 - 2.0 * raw_c)
                if compact_alpha > 0.01:
                    painter.save()
                    painter.setOpacity(compact_alpha)
                    self._paint_compact(painter, theme, w, h)
                    painter.restore()

            # B. Expanded Card Content (Fades in 0.10 -> 1.0 on expand, fades out 1.0 -> 0.10 on collapse)
            if p_val > 0.10:
                raw_e = max(0.0, min(1.0, (p_val - 0.10) / 0.90))
                expand_alpha = raw_e * raw_e * (3.0 - 2.0 * raw_e)
                slide_y = (1.0 - expand_alpha) * 8.0

                painter.save()
                painter.setOpacity(expand_alpha)
                painter.translate(0, -slide_y)

                if self._tab_transition_progress < 1.0 and self._tab_from in self.SIZES and self._tab_from != self._state and self._state != self.STATE_COMPACT:
                    t_val = self._tab_transition_progress
                    smooth_t = t_val * t_val * (3.0 - 2.0 * t_val)

                    painter.save()
                    painter.setOpacity(expand_alpha * (1.0 - smooth_t))
                    painter.translate(-16.0 * smooth_t, 0)
                    self._paint_tab_body(painter, self._tab_from, theme, w, h)
                    painter.restore()

                    painter.save()
                    painter.setOpacity(expand_alpha * smooth_t)
                    painter.translate(16.0 * (1.0 - smooth_t), 0)
                    self._paint_tab_body(painter, self._state, theme, w, h)
                    painter.restore()
                else:
                    self._paint_tab_body(painter, expanded_tab, theme, w, h)

                painter.restore()

        # 6. (Old mini 140px volume HUD removed; only the full-width Dynamic Island capsule is used)

        # 7. Ambient Style Switching Toast Banner HUD
        toast_elapsed = time.monotonic() - self._ambient_toast_time
        if toast_elapsed < 2.0 or self._toast_y > -26.0:
            t_alpha = int(max(0.0, min(1.0, (2.0 - toast_elapsed) / 0.35)) * 245)
            t_rect = QRect((w - 220) // 2, int(round(self._toast_y)), 220, 24)
            t_path = QPainterPath()
            t_path.addRoundedRect(QRectF(t_rect), 12, 12)

            painter.save()
            painter.setPen(QPen(QColor(255, 255, 255, int(t_alpha * 0.4)), 1.0))
            painter.setBrush(QColor(18, 18, 24, t_alpha))
            painter.drawPath(t_path)

            painter.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
            painter.setPen(QColor(255, 255, 255, t_alpha))
            painter.drawText(t_rect, Qt.AlignmentFlag.AlignCenter, self._ambient_toast_name)
            painter.restore()

        # 8. Floating Dynamic Island Volume Capsule HUD Overlay on Scroll
        if getattr(self, "_sys_hud_toast_type", "") == "volume" and self._state != self.STATE_COMPACT:
            self._draw_expanded_volume_hud(painter, w, h)

        # 9. Phone Link & Drop QR Code Modal Overlay
        if getattr(self, "_phone_qr_visible", False) and self._state != self.STATE_COMPACT:
            self._draw_phone_qr_overlay(painter, w, h)


    def _draw_expanded_volume_hud(self, p: QPainter, w: int, h: int):
        """Draws tactile floating Dynamic Island volume pill animation when scrolling in expanded modes."""
        hud_elapsed = time.monotonic() - getattr(self, "_sys_hud_toast_time", 0.0)
        if hud_elapsed >= 2.0:
            return

        alpha_mult = min(1.0, max(0.0, (2.0 - hud_elapsed) / 0.4))
        if alpha_mult <= 0.01:
            return

        p.save()
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        hud_w = 176.0
        hud_h = 28.0
        hud_x = (w - hud_w) / 2.0
        slide_offset = max(0.0, (0.25 - hud_elapsed) * 20.0) if hud_elapsed < 0.25 else 0.0
        hud_y = 8.0 - slide_offset

        hud_val = getattr(self, "_sys_hud_toast_val", int(self._volume_hud_level))
        is_playing = self._is_genuine_music_playing()
        accent = getattr(self, "_dynamic_accent_color", QColor(240, 181, 166)) if is_playing else QColor(255, 255, 255)

        # Drop shadow
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(0, 0, 0, int(90 * alpha_mult)))
        p.drawRoundedRect(QRectF(hud_x + 1, hud_y + 2, hud_w, hud_h), 14.0, 14.0)

        # Pill background (AMOLED dark)
        p.setBrush(QColor(16, 17, 23, int(245 * alpha_mult)))
        p.drawRoundedRect(QRectF(hud_x, hud_y, hud_w, hud_h), 14.0, 14.0)

        # Border
        p.setPen(QPen(QColor(accent.red(), accent.green(), accent.blue(), int(80 * alpha_mult)), 1.0))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRoundedRect(QRectF(hud_x, hud_y, hud_w, hud_h), 14.0, 14.0)

        # Speaker icon
        spk_level = 0 if hud_val <= 0 else (1 if hud_val <= 40 else 2)
        spk_col = QColor(255, 255, 255, int(240 * alpha_mult))
        self._draw_vector_speaker(p, int(hud_x + 18), int(hud_y + hud_h / 2.0), level=spk_level, color=spk_col)

        # Volume capsule track
        track_x = hud_x + 36.0
        track_w = 88.0
        track_h = 5.0
        track_y = hud_y + (hud_h - track_h) / 2.0

        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(255, 255, 255, int(35 * alpha_mult)))
        p.drawRoundedRect(QRectF(track_x, track_y, track_w, track_h), 2.5, 2.5)

        # Fill with dynamic accent color
        fill_w = max(0.0, min(track_w, track_w * (hud_val / 100.0)))
        p.setBrush(QColor(accent.red(), accent.green(), accent.blue(), int(245 * alpha_mult)))
        p.drawRoundedRect(QRectF(track_x, track_y, fill_w, track_h), 2.5, 2.5)

        # Percentage text
        p.setFont(QFont(["Segoe UI", "sans-serif"], 8.5, QFont.Weight.Bold))
        p.setPen(QColor(255, 255, 255, int(235 * alpha_mult)))
        p.drawText(QRectF(hud_x + 130, hud_y, 38, hud_h), Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight, f"{hud_val}%")

        p.restore()

    def _on_assistant_submit(self):
        text = self._chat_input.text().strip()
        if not text:
            return
        self._chat_input.clear()
        self._run_assistant_task(text)

    def _run_assistant_task(self, query: str):
        if not query or not query.strip():
            return
        query = query.strip()
        self._assistant_query = query
        self._assistant_status = "Thinking..."
        self._assistant_status_detail = f"Processing: '{query[:25]}...'" if len(query) > 25 else f"Processing: '{query}'"
        self._assistant_reply = ""
        self._assistant_typewriter_idx = 0
        self._assistant_tool_action = ""
        self._wake_timer()

        self._assistant_history.append({"role": "user", "text": query})
        if len(self._assistant_history) > 8:
            self._assistant_history.pop(0)

        def _worker():
            result_text = ""
            tool_executed = ""
            answered = False
            try:
                q_clean = query.lower().strip()
                # Conversational greetings (0ms instant response)
                if any(q_clean == g for g in ["hi", "hello", "hey", "yo", "sup", "greetings", "good morning", "good evening"]):
                    result_text = "Hello! JARVIS is online and ready. How may I assist you, sir?"
                    answered = True
                # 0. Instant Direct Media & System Actions (0ms latency)
                elif any(k in q_clean for k in ["skip", "next song", "next track", "skip this", "play next"]):
                    self._media.next_track()
                    result_text = "Skipped to the next track, sir."
                    tool_executed = "next_track"
                    answered = True
                elif any(k in q_clean for k in ["previous song", "prev song", "previous track", "prev track", "last track", "last song", "replay song"]):
                    self._media.previous_track()
                    result_text = "Playing previous track, sir."
                    tool_executed = "previous_track"
                    answered = True
                elif q_clean in ["pause", "pause music", "stop music", "pause playback", "hold music"] or q_clean.startswith("pause "):
                    self._media.pause()
                    result_text = "Music playback paused, sir."
                    tool_executed = "pause_media"
                    answered = True
                elif q_clean in ["play", "resume", "unpause", "resume music", "play music", "start music"] or q_clean.startswith("resume "):
                    self._media.play()
                    result_text = "Resuming music playback, sir."
                    tool_executed = "play_media"
                    answered = True
                elif any(k in q_clean for k in ["mute", "unmute", "silence"]):
                    self._media.volume_mute()
                    result_text = "Toggled audio mute, sir."
                    tool_executed = "volume_mute"
                    answered = True
                elif any(k in q_clean for k in ["volume up", "louder", "turn up the volume", "increase volume", "raise volume"]):
                    self._trigger_volume_hud("+")
                    cur_v = int(round(_win_get_system_volume()))
                    result_text = f"Volume increased to {cur_v}%, sir."
                    tool_executed = "volume_up"
                    answered = True
                elif any(k in q_clean for k in ["volume down", "quieter", "lower volume", "turn down the volume", "decrease volume"]):
                    self._trigger_volume_hud("-")
                    cur_v = int(round(_win_get_system_volume()))
                    result_text = f"Volume decreased to {cur_v}%, sir."
                    tool_executed = "volume_down"
                    answered = True
                elif re.search(r'\b(?:set\s+)?volume\s+(?:to\s+)?(\d{1,3})\b', q_clean):
                    m = re.search(r'\b(?:set\s+)?volume\s+(?:to\s+)?(\d{1,3})\b', q_clean)
                    v = max(0.0, min(100.0, float(m.group(1))))
                    _win_set_system_volume(v)
                    self._anim_volume_level = v
                    self._volume_hud_y = 0.0
                    self._volume_hud_time = time.monotonic()
                    result_text = f"Master volume set to {int(v)}%, sir."
                    tool_executed = "set_volume"
                    answered = True
                elif any(k in q_clean for k in ["screenshot", "snip", "capture screen"]):
                    self._shelf_snip_screen()
                    result_text = "Screenshot captured and pinned to Desktop Shelf."
                    tool_executed = "screenshot"
                    answered = True
                elif any(k in q_clean for k in ["lock pc", "lock laptop", "lock workstation", "lock computer"]) or q_clean == "lock":
                    ctypes.windll.user32.LockWorkStation()
                    result_text = "Computer workstation locked securely, sir."
                    tool_executed = "lock_pc"
                    answered = True
                elif "battery" in q_clean:
                    pct = getattr(self, "_battery_pct", 100.0)
                    status = getattr(self, "_battery_status", "Battery")
                    result_text = f"Laptop battery is at {int(pct)}% ({status})."
                    tool_executed = "battery_check"
                    answered = True
                elif "weather" in q_clean:
                    temp = getattr(self, "_weather_temp", "--")
                    desc = getattr(self, "_weather_desc", "")
                    result_text = f"The weather is currently {temp} with {desc}."
                    tool_executed = "weather_check"
                    answered = True
                elif any(k in q_clean for k in ["vision mode", "activate vision", "screen vision", "analyze screen", "what is on my screen", "what's on my screen", "look at my screen", "scan screen"]):
                    self.analyze_screen()
                    result_text = "Scanning full display with holographic blue laser perception, sir."
                    tool_executed = "screen_copilot"
                    answered = True
                elif "github" in q_clean and any(w in q_clean for w in ["open", "link", "go", "launch"]):
                    import webbrowser
                    webbrowser.open("https://github.com")
                    result_text = "Opened GitHub in your browser, sir."
                    tool_executed = "open_url"
                    answered = True
                elif "spotify" in q_clean and any(w in q_clean for w in ["play", "start", "listen", "search"]):
                    from control import system
                    m_spot = re.search(r'(?:play|search(?:\s+for)?)\s+(?:a\s+song\s+|the\s+song\s+|song\s+)?(.+?)(?:\s+(?:on|in)\s+spotify|$)', q_clean)
                    song_target = m_spot.group(1).strip(" .!?") if m_spot else "lo-fi chill"
                    if "spotify" in song_target:
                        song_target = re.sub(r'\bspotify\b', '', song_target).strip()
                    if not song_target or song_target in ("music", "song", "a song"):
                        song_target = "lo-fi beats"
                    result_text = system.play_spotify(song_target)
                    tool_executed = "play_spotify"
                    answered = True
                elif re.search(r'^play\s+(?:a\s+song\s+|the\s+song\s+|song\s+)?(lo-?fi.*)', q_clean):
                    from control import system
                    result_text = system.play_spotify("lo-fi beats")
                    tool_executed = "play_spotify"
                    answered = True
                elif re.search(r'^(?:open|click|tap)(?:\s+on)?\s+(?:the\s+)?(?:first\s+)?link$', q_clean) or q_clean in ("open the link", "click the link", "open link", "click link", "open first link"):
                    from control import vision
                    self.trigger_vision_scan(label="Locating Link")
                    self._assistant_status = "Scanning..."
                    self._assistant_status_detail = "Locating link on screen..."
                    self._wake_timer()
                    click_res = vision.click_element_by_description("link")
                    result_text = click_res
                    tool_executed = "click_element"
                    answered = True
                elif re.search(r'^(?:click|tap)\s+(?:on\s+)?(?:the\s+)?(.+)', q_clean):
                    m = re.search(r'^(?:click|tap)\s+(?:on\s+)?(?:the\s+)?(.+)', q_clean)
                    target = m.group(1).strip(" .!?")
                    if target and target not in ("enter", "space", "escape", "tab", "backspace"):
                        from control import vision
                        self.trigger_vision_scan(label=f"Locating '{target}'")
                        self._assistant_status = "Scanning..."
                        self._assistant_status_detail = f"Locating '{target}'..."
                        self._wake_timer()
                        click_res = vision.click_element_by_description(target)
                        result_text = click_res
                        tool_executed = "click_element"
                        answered = True
                elif re.search(r'^(?:open|launch|create)?\s*(?:another|a\s+new|new)?\s*tab(?:\s+in\s+([a-z0-9_]+))?(?:\s+(?:for|with|to)\s+(.+))?$', q_clean):
                    m = re.search(r'^(?:open|launch|create)?\s*(?:another|a\s+new|new)?\s*tab(?:\s+in\s+([a-z0-9_]+))?(?:\s+(?:for|with|to)\s+(.+))?$', q_clean)
                    browser = m.group(1) if m.group(1) else ""
                    url = m.group(2) if m.group(2) else ""
                    from control import apps
                    result_text = apps.open_browser_tab(browser, url)
                    tool_executed = "open_browser_tab"
                    answered = True
                elif re.search(r'^(?:close|shut)\s+(?:this\s+|the\s+|current\s+)?tab$', q_clean):
                    from control import apps
                    result_text = apps.close_browser_tab()
                    tool_executed = "close_browser_tab"
                    answered = True
                elif re.search(r'^(?:next\s+tab|switch\s+tab|go\s+to\s+next\s+tab)$', q_clean):
                    from control import apps
                    result_text = apps.switch_next_tab()
                    tool_executed = "switch_next_tab"
                    answered = True
                elif re.search(r'^(?:previous|prev)\s+tab$', q_clean):
                    from control import apps
                    result_text = apps.switch_prev_tab()
                    tool_executed = "switch_prev_tab"
                    answered = True
                elif re.search(r'^(?:reopen|undo\s+close)\s+(?:closed\s+)?tab$', q_clean):
                    from control import apps
                    result_text = apps.reopen_closed_tab()
                    tool_executed = "reopen_closed_tab"
                    answered = True
                elif re.search(r'^(?:open|show)\s+(?:it\s+)?again$', q_clean) or q_clean in ("open again", "open it again", "open it", "show again", "bring it back", "restore", "unminimize"):
                    from control import apps
                    result_text = apps.restore_window("")
                    tool_executed = "restore_window"
                    answered = True
                elif re.search(r'^(?:restore|unminimize|un-minimize|bring\s+back)(?:\s+(?:the\s+|this\s+)?window)?(?:\s+(.+))?$', q_clean):
                    m = re.search(r'^(?:restore|unminimize|un-minimize|bring\s+back)(?:\s+(?:the\s+|this\s+)?window)?(?:\s+(.+))?$', q_clean)
                    tgt = (m.group(1) or "").strip(" .!?") if m else ""
                    if tgt in ("it", "this", "window"): tgt = ""
                    from control import apps
                    result_text = apps.restore_window(tgt)
                    tool_executed = "restore_window"
                    answered = True
                elif re.search(r'^(?:minimize|hide)(?:\s+(?:the\s+|this\s+)?window)?(?:\s+(.+))?$', q_clean):
                    m = re.search(r'^(?:minimize|hide)(?:\s+(?:the\s+|this\s+)?window)?(?:\s+(.+))?$', q_clean)
                    tgt = (m.group(1) or "").strip(" .!?") if m else ""
                    if tgt in ("it", "this", "window", "all"): tgt = ""
                    from control import apps
                    result_text = apps.minimize_window(tgt)
                    tool_executed = "minimize_window"
                    answered = True
                elif re.search(r'^(?:maximize|fullscreen)(?:\s+(?:the\s+|this\s+)?window)?(?:\s+(.+))?$', q_clean):
                    m = re.search(r'^(?:maximize|fullscreen)(?:\s+(?:the\s+|this\s+)?window)?(?:\s+(.+))?$', q_clean)
                    tgt = (m.group(1) or "").strip(" .!?") if m else ""
                    if tgt in ("it", "this", "window"): tgt = ""
                    from control import apps
                    result_text = apps.maximize_window(tgt)
                    tool_executed = "maximize_window"
                    answered = True
                else:
                    # Ensure jarvis root is in sys.path for internal dependencies
                    _jarvis_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "jarvis")
                    if _jarvis_dir not in sys.path:
                        sys.path.insert(0, _jarvis_dir)

                    # 1. Fast local intent from jarvis package
                    fast_intent = None
                    try:
                        from jarvis.brain.intent import try_fast_intent
                        fast_intent = try_fast_intent(query)
                    except Exception:
                        pass

                    if fast_intent:
                        tool_name, tool_args = fast_intent
                        tool_executed = tool_name
                        self._assistant_status = "Executing..."
                        self._assistant_status_detail = f"Running: {tool_name}"
                        self._wake_timer()

                        try:
                            from jarvis.brain.tools import dispatch_tool
                            from jarvis.memory import Memory
                            mem = getattr(self, "_jarvis_memory", None)
                            if not mem:
                                self._jarvis_memory = Memory()
                                mem = self._jarvis_memory

                            raw_res = dispatch_tool(
                                tool_name, tool_args,
                                speak_fn=lambda s: None,
                                listen_fn=lambda: "",
                                memory=mem,
                                status_fn=lambda s: None
                            )
                            result_text = str(raw_res) if raw_res else f"Completed {tool_name}."
                            answered = True
                        except Exception as ex:
                            result_text = f"Action finished: {ex}"
                            answered = True
                    else:
                        # 2. General Query / LLM Agent
                        answered = False
                        try:
                            from jarvis.config import NVIDIA_API_KEY
                            if NVIDIA_API_KEY and len(NVIDIA_API_KEY) > 10:
                                from jarvis.brain.agent import run_agent
                                from jarvis.memory import Memory
                                mem = getattr(self, "_jarvis_memory", None)
                                if not mem:
                                    self._jarvis_memory = Memory()
                                    mem = self._jarvis_memory
                                res = run_agent(
                                    query, mem,
                                    speak_fn=lambda s: None,
                                    listen_fn=lambda: "",
                                    status_fn=lambda s: None
                                )
                                if res and not any(err_sig in str(res).lower() for err_sig in ["api error", "404", "function_not_found", "invalid_request_error"]):
                                    result_text = res
                                    answered = True
                        except Exception:
                            pass

                    if not answered:
                        q_lower = query.lower()
                        if "taskbar" in q_lower:
                            from taskbar_service import TaskbarService, TaskbarStyle
                            tb = TaskbarService.get_instance()
                            if any(k in q_lower for k in ["clear", "transparent", "glass"]):
                                tb.set_style(TaskbarStyle.CLEAR)
                                result_text = "Taskbar is now Transparent Clear Glass."
                            elif "acrylic" in q_lower:
                                tb.set_style(TaskbarStyle.ACRYLIC)
                                result_text = "Taskbar is now Frosted Acrylic Blur."
                            elif "blur" in q_lower or "aero" in q_lower:
                                tb.set_style(TaskbarStyle.BLUR)
                                result_text = "Taskbar is now Aero Glass Blur."
                            elif "black" in q_lower or "oled" in q_lower or "dark" in q_lower:
                                tb.set_style(TaskbarStyle.BLACK)
                                result_text = "Taskbar is now OLED Stealth Black."
                            elif "default" in q_lower or "reset" in q_lower or "normal" in q_lower:
                                tb.set_style(TaskbarStyle.DEFAULT)
                                result_text = "Taskbar restored to Windows default."
                            else:
                                new_s = tb.cycle_style()
                                result_text = f"Switched Taskbar to {tb.display_name}."
                        elif "who are you" in q_lower or "your name" in q_lower:
                            result_text = "I am JARVIS, your intelligent AI desktop assistant in Origin Island."
                        elif "what can you do" in q_lower or "help" in q_lower:
                            result_text = "I can open applications, write notes in Notepad, control Spotify & YouTube music, check battery & volume, take screenshots, and automate Windows."
                        elif "time" in q_lower or "date" in q_lower:
                            now = datetime.datetime.now()
                            result_text = f"It is currently {now.strftime('%I:%M %p on %A, %B %d, %Y')}."
                        elif "how are you" in q_lower:
                            result_text = "Operating at peak performance with zero idle CPU usage."
                        elif re.search(r'^(?:hi|hello|hey|yo|sup|greetings|namaste|namaskaram)[\s!,.]*$', q_clean):
                            result_text = "Greetings! How may I assist you today?"
                        elif any(k in q_lower for k in ["search", "google", "find online", "look up"]):
                            try:
                                from control import system
                                result_text = f"Searching web for: {query}"
                                system.web_search(query)
                            except Exception:
                                result_text = f"Task acknowledged: {query}"
                        else:
                            result_text = f"Understood, sir. '{query}' acknowledged."

                self._assistant_reply = result_text
                self._assistant_tool_action = tool_executed
                self._assistant_status = "Speaking..."
                self._assistant_status_detail = "Speaking..."
                self._is_jarvis_talking = True
                self._live_jarvis_speech = result_text
                self._jarvis_speech_time = time.monotonic()
                self._jarvis_compact_ticker_x = 0.0
                self._assistant_typewriter_idx = 0
                self._wake_timer()

                self._assistant_history.append({"role": "jarvis", "text": result_text, "tool": tool_executed})

                # Speak aloud asynchronously in dedicated background thread
                def _speak_async():
                    try:
                        from audio import speaker
                        speaker.speak(result_text)
                    except Exception:
                        pass
                    finally:
                        self._is_jarvis_talking = False
                        self._assistant_status = "Ready"
                        self._assistant_status_detail = "Ready"
                        self._wake_timer()

                threading.Thread(target=_speak_async, daemon=True, name="jarvis_speech").start()

                self._assistant_status = "Speaking..."
                self._assistant_status_detail = "Speaking..."
                self._wake_timer()

            except Exception as e:
                self._assistant_status = "Ready"
                self._assistant_reply = f"Error: {e}"
                self._is_jarvis_talking = False
                self._wake_timer()

        threading.Thread(target=_worker, daemon=True, name="jarvis_worker").start()

    def _start_voice_recording(self):
        if getattr(self, "_is_voice_listening", False):
            return
        self._is_voice_listening = True
        self._assistant_status = "Listening..."
        self._assistant_status_detail = "Listening..."
        self._assistant_reply = "Listening... Speak your command now."
        self._assistant_typewriter_idx = len(self._assistant_reply)
        self._live_jarvis_speech = "Listening to your voice..."
        self._jarvis_speech_time = time.monotonic()
        self._jarvis_compact_ticker_x = 0.0
        self._is_jarvis_talking = True
        self._wake_timer()

        def _voice_worker():
            try:
                from audio.listener import Listener
                listener = getattr(self, "_jarvis_listener", None)
                if not listener:
                    self._jarvis_listener = Listener()
                    listener = self._jarvis_listener

                text = listener.push_to_talk_record()
                self._is_voice_listening = False
                if text and text.strip():
                    self._run_assistant_task(text.strip())
                else:
                    self._assistant_status = "Ready"
                    self._assistant_status_detail = "Ready"
                    self._is_jarvis_talking = False
                    self._wake_timer()
            except Exception:
                self._is_voice_listening = False
                self._assistant_status = "Ready"
                self._assistant_status_detail = "Ready"
                self._is_jarvis_talking = False
                self._wake_timer()

        threading.Thread(target=_voice_worker, daemon=True, name="jarvis_voice_worker").start()

    def _paint_assistant(self, p: QPainter, theme: dict, w: int, h: int):
        p.save()
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        accent = theme.get("accent", QColor(255, 255, 255))
        card_bg = theme.get("card_bg", QColor(255, 255, 255, 16))
        border_col = theme.get("border", QColor(255, 255, 255, 28))

        # Dynamically sync embedded chat input box theme
        self._update_chat_input_theme(theme)

        # 2. Header: Title + Live Status Pill + Top Tabs
        self._draw_vector_spark(p, 23, 16, color=accent, scale=0.92)
        p.setFont(QFont("Segoe UI", 8.5, QFont.Weight.Bold))
        p.setPen(theme.get("text_primary", QColor(255, 255, 255)))
        p.drawText(QRect(33, 6, 46, 20), Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, "JARVIS")

        # Live Status Badge Pill
        status_text = self._assistant_status
        status_pill_rect = QRectF(83, 6, 72, 20)
        p.setPen(QPen(QColor(accent.red(), accent.green(), accent.blue(), 80), 1.0))
        p.setBrush(QColor(12, 16, 26, 200))
        p.drawRoundedRect(status_pill_rect, 10, 10)

        dot_color = QColor(16, 185, 129) if status_text == "Ready" else accent
        pulse = 0.5 + 0.5 * math.sin(self._anim_time * 8.0)
        dot_color.setAlpha(int(180 + 75 * pulse))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(dot_color)
        p.drawEllipse(QPointF(91, 16), 3.0, 3.0)

        p.setFont(QFont("Segoe UI", 7.5, QFont.Weight.DemiBold))
        p.setPen(theme.get("text_primary", QColor(255, 255, 255)))
        p.drawText(QRect(98, 6, 52, 20), Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, status_text)

        # Top Tabs
        self._paint_tab_headers(p, theme, w, self.STATE_ASSISTANT)

        # 3. Main Transcript & Display Card (y = 32 to 164) - Deep Obsidian Dark Glass
        card_rect = QRectF(16, 32, w - 32, 132)
        card_bg_col = QColor(8, 11, 18, 195) if getattr(self, "_theme_key", "") != "frost_white" else QColor(0, 0, 0, 14)
        card_border_col = QColor(255, 255, 255, 26) if getattr(self, "_theme_key", "") != "frost_white" else QColor(0, 0, 0, 24)
        p.setPen(QPen(card_border_col, 1.0))
        p.setBrush(card_bg_col)
        p.drawRoundedRect(card_rect, 12, 12)

        if self._assistant_query or (self._assistant_reply and self._assistant_reply != "Hello! I am JARVIS. Ask a task, dictate, or type below."):
            user_txt = self._assistant_query if self._assistant_query else "User instruction"
            p.setFont(QFont("Segoe UI", 7, QFont.Weight.Bold))
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor(accent.red(), accent.green(), accent.blue(), 30))
            p.drawRoundedRect(QRectF(26, 40, 36, 16), 4, 4)
            p.setPen(accent)
            p.drawText(QRect(26, 40, 36, 16), Qt.AlignmentFlag.AlignCenter, "YOU")

            p.setFont(QFont("Segoe UI", 8.5))
            p.setPen(theme.get("text_primary", QColor(220, 225, 235)))
            p.drawText(QRect(68, 39, int(card_rect.width() - 84), 18), Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, f"\"{user_txt}\"")

            p.setPen(QPen(QColor(255, 255, 255, 12), 1.0))
            p.drawLine(QPointF(26, 62), QPointF(card_rect.right() - 10, 62))

            p.setFont(QFont("Segoe UI", 7, QFont.Weight.Bold))
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor(168, 85, 247, 35))
            p.drawRoundedRect(QRectF(26, 70, 54, 16), 4, 4)
            p.setPen(QColor(168, 85, 247, 240))
            p.drawText(QRect(26, 70, 54, 16), Qt.AlignmentFlag.AlignCenter, "✦ JARVIS")

            if self._assistant_tool_action:
                tool_rect = QRectF(86, 70, 110, 16)
                p.setBrush(QColor(16, 185, 129, 30))
                p.drawRoundedRect(tool_rect, 4, 4)
                p.setFont(QFont("Segoe UI", 7, QFont.Weight.DemiBold))
                p.setPen(QColor(16, 185, 129, 240))
                p.drawText(tool_rect.toRect(), Qt.AlignmentFlag.AlignCenter, f"⚡ {self._assistant_tool_action}")

            displayed_text = self._assistant_reply[:self._assistant_typewriter_idx]
            if self._assistant_typewriter_idx < len(self._assistant_reply):
                displayed_text += "|"

            reply_rect = QRect(26, 92, int(card_rect.width() - 20), 66)
            p.setFont(QFont("Segoe UI", 8.5))
            p.setPen(theme.get("text_primary", QColor(255, 255, 255)))
            p.drawText(reply_rect, Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft | Qt.TextFlag.TextWordWrap, displayed_text)

        else:
            cx = int(card_rect.center().x())
            cy = int(card_rect.top() + 45)

            p.save()
            p.translate(cx, cy)
            p.rotate((self._anim_time * 25.0) % 360.0)
            pen_ring = QPen(QColor(accent.red(), accent.green(), accent.blue(), 80), 1.5, Qt.PenStyle.DashLine)
            p.setPen(pen_ring)
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawEllipse(QPoint(0, 0), 22, 22)
            p.restore()

            rad_grad = QRadialGradient(cx, cy, 18)
            rad_grad.setColorAt(0.0, QColor(accent.red(), accent.green(), accent.blue(), 120))
            rad_grad.setColorAt(0.7, QColor(168, 85, 247, 40))
            rad_grad.setColorAt(1.0, QColor(0, 0, 0, 0))
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(rad_grad)
            p.drawEllipse(QPoint(cx, cy), 18, 18)

            self._draw_vector_spark(p, cx, cy, color=QColor(255, 255, 255), scale=1.2)

            p.setFont(QFont("Segoe UI", 8.5, QFont.Weight.Bold))
            p.setPen(theme.get("text_primary", QColor(255, 255, 255)))
            p.drawText(QRect(20, cy + 28, w - 40, 18), Qt.AlignmentFlag.AlignCenter, "JARVIS Desktop Assistant Ready")
            p.setFont(QFont("Segoe UI", 7.5))
            p.setPen(theme.get("text_secondary", QColor(160, 170, 190)))
            p.drawText(QRect(20, cy + 46, w - 40, 16), Qt.AlignmentFlag.AlignCenter, "Speak with Push-to-Talk or type a command below")

        # 4. Quick Action Chips Row (Zero emojis - clean vector iconography & sleek typography)
        chips = [
            ("chip_0", "Lo-Fi", 16, 64, "music"),
            ("chip_1", "Notes", 86, 64, "notes"),
            ("chip_2", "Battery", 156, 82, "battery"),
            ("chip_3", "Copilot", 244, 78, "camera"),
            ("chip_4", "Search", 328, 68, "search"),
        ]

        for idx, (chip_key, chip_label, ch_x, ch_w, icon_type) in enumerate(chips):
            ch_rect = QRectF(ch_x, 172, ch_w, 24)
            h_anim = self._btn_hover_anim.get(chip_key, 0.0)

            p.save()
            if getattr(self, "_theme_key", "") == "frost_white":
                p.setPen(QPen(QColor(0, 0, 0, int(25 + h_anim * 60)), 1.0))
                p.setBrush(QColor(0, 0, 0, int(10 + h_anim * 25)))
            else:
                # Sleek dark frosted glass chip pill
                chip_border_col = QColor(accent.red(), accent.green(), accent.blue(), int(60 + h_anim * 140)) if h_anim > 0.05 else QColor(255, 255, 255, 25)
                p.setPen(QPen(chip_border_col, 1.0))
                p.setBrush(QColor(18, 22, 34, int(185 + h_anim * 55)))
            p.drawRoundedRect(ch_rect, 6, 6)

            icon_col = QColor(255, 255, 255, int(210 + h_anim * 45))
            mid_y = int(ch_rect.center().y())

            # Draw vector icon without emojis
            if icon_type == "music":
                self._draw_vector_note(p, int(ch_rect.x() + 11), mid_y, size=9, color=icon_col)
                text_rect = QRectF(ch_rect.x() + 20, ch_rect.y(), ch_rect.width() - 22, ch_rect.height())
            elif icon_type == "notes":
                self._draw_vector_notes(p, int(ch_rect.x() + 11), mid_y, color=icon_col)
                text_rect = QRectF(ch_rect.x() + 20, ch_rect.y(), ch_rect.width() - 22, ch_rect.height())
            elif icon_type == "battery":
                self._draw_vector_battery(p, int(ch_rect.x() + 6), mid_y - 5, percent=85, color=icon_col)
                text_rect = QRectF(ch_rect.x() + 32, ch_rect.y(), ch_rect.width() - 34, ch_rect.height())
            elif icon_type == "camera":
                self._draw_vector_camera(p, int(ch_rect.x() + 11), mid_y, color=icon_col, scale=0.85)
                text_rect = QRectF(ch_rect.x() + 20, ch_rect.y(), ch_rect.width() - 22, ch_rect.height())
            elif icon_type == "search":
                self._draw_vector_search(p, int(ch_rect.x() + 11), mid_y, color=icon_col)
                text_rect = QRectF(ch_rect.x() + 20, ch_rect.y(), ch_rect.width() - 22, ch_rect.height())

            # Draw clean minimal text label
            p.setFont(QFont("Segoe UI", 7.5, QFont.Weight.DemiBold))
            text_color = QColor(241, 245, 249) if getattr(self, "_theme_key", "") != "frost_white" else QColor(15, 23, 42)
            p.setPen(text_color)
            p.drawText(text_rect, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, chip_label)
            p.restore()

        # 5. Send & Mic Action Buttons next to QLineEdit - Matching Dark Glass
        btn_y = h - 44
        send_rect = QRectF(w - 78, btn_y, 30, 32)
        is_send_hover = (self._hovered_btn == "assistant_send")
        p.save()
        send_border = QColor(accent.red(), accent.green(), accent.blue(), 160 if is_send_hover else 75)
        send_bg = QColor(18, 22, 34, 230 if is_send_hover else 185)
        p.setPen(QPen(send_border, 1.0))
        p.setBrush(send_bg)
        p.drawRoundedRect(send_rect, 8, 8)
        self._draw_vector_send(p, int(send_rect.center().x()), int(send_rect.center().y()), color=QColor(255, 255, 255), scale=1.0)
        p.restore()

        mic_rect = QRectF(w - 44, btn_y, 30, 32)
        is_mic_listening = getattr(self, "_is_voice_listening", False)
        is_mic_hover = (self._hovered_btn == "assistant_mic")
        p.save()
        if is_mic_listening:
            mic_pulse = 0.5 + 0.5 * math.sin(self._anim_time * 10.0)
            p.setPen(QPen(QColor(239, 68, 68, int(180 + mic_pulse * 75)), 1.5))
            p.setBrush(QColor(239, 68, 68, int(110 + mic_pulse * 60)))
            self._draw_vector_mic(p, int(mic_rect.center().x()), int(mic_rect.center().y()), color=QColor(255, 255, 255), scale=1.1)
        else:
            mic_border = QColor(accent.red(), accent.green(), accent.blue(), 160 if is_mic_hover else 75)
            mic_bg = QColor(18, 22, 34, 230 if is_mic_hover else 185)
            p.setPen(QPen(mic_border, 1.0))
            p.setBrush(mic_bg)
            self._draw_vector_mic(p, int(mic_rect.center().x()), int(mic_rect.center().y()), color=QColor(255, 255, 255), scale=1.0)
        p.drawRoundedRect(mic_rect, 8, 8)
        p.restore()

        p.restore()

    def _paint_tab_body(self, p: QPainter, tab: str, theme: dict, w: int, h: int):
        if tab == self.STATE_ASSISTANT:
            self._paint_assistant(p, theme, w, h)
        elif tab == self.STATE_MUSIC:
            self._paint_music(p, theme, w, h)
        elif tab == self.STATE_WEATHER:
            self._paint_weather(p, theme, w, h)
        elif tab == self.STATE_CONTROL:
            self._paint_control(p, theme, w, h)
        elif tab == self.STATE_CALENDAR:
            self._paint_calendar(p, theme, w, h)
        elif tab == self.STATE_SHELF:
            self._paint_shelf(p, theme, w, h)
        elif tab == self.STATE_MAP:
            self._paint_map(p, theme, w, h)
        elif tab == self.STATE_CLIPBOARD:
            self._paint_clipboard(p, theme, w, h)
        elif tab == self.STATE_TOOLS:
            self._paint_tools(p, theme, w, h)
        elif tab == self.STATE_NOTIFICATION:
            self._paint_notification(p, theme, w, h)

    def _paint_notification(self, p: QPainter, theme: dict, w: int, h: int):
        """Renders Windows toast notification with sleek AMOLED dark styling and 1-click actions."""
        p.save()
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        notif = getattr(self, "_current_notification", None) or {
            "app_name": "Notification",
            "title": "New Alert",
            "body": "System notification received",
            "time": time.time(),
        }
        app_name = str(notif.get("app_name", "Notification"))
        title = str(notif.get("title", ""))
        body = str(notif.get("body", ""))

        app_lower = app_name.lower()
        if "whatsapp" in app_lower:
            accent = QColor(37, 211, 102)      # WhatsApp Green
            brand_glyph = "W"
        elif "discord" in app_lower:
            accent = QColor(88, 101, 242)     # Discord Blurple
            brand_glyph = "D"
        elif "telegram" in app_lower:
            accent = QColor(36, 161, 222)     # Telegram Blue
            brand_glyph = "T"
        elif "calendar" in app_lower:
            accent = QColor(234, 67, 53)      # Google Calendar Red
            brand_glyph = "C"
        elif "spotify" in app_lower:
            accent = QColor(30, 215, 96)      # Spotify Green
            brand_glyph = "S"
        elif "mail" in app_lower or "outlook" in app_lower:
            accent = QColor(0, 120, 212)      # Outlook Blue
            brand_glyph = "M"
        else:
            accent = QColor(0, 195, 255)      # Tech Cyan
            brand_glyph = "🔔"

        # Subtle Glowing Accent Aura Border
        aura_grad = QLinearGradient(0, 0, w, 0)
        aura_grad.setColorAt(0.0, QColor(accent.red(), accent.green(), accent.blue(), 70))
        aura_grad.setColorAt(0.5, QColor(accent.red(), accent.green(), accent.blue(), 160))
        aura_grad.setColorAt(1.0, QColor(accent.red(), accent.green(), accent.blue(), 70))
        p.setPen(QPen(QBrush(aura_grad), 1.2))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRoundedRect(QRectF(1.0, 1.0, float(w - 2), float(h - 2)), 18.0, 18.0)

        # 1. Left Brand Icon Squircle (x: 14, y: centered, w: 48, h: 48)
        icon_rect = QRectF(14.0, (h - 48) / 2.0, 48.0, 48.0)
        icon_grad = QLinearGradient(icon_rect.topLeft(), icon_rect.bottomRight())
        icon_grad.setColorAt(0.0, QColor(accent.red(), accent.green(), accent.blue(), 230))
        icon_grad.setColorAt(1.0, QColor(max(0, accent.red() - 40), max(0, accent.green() - 40), max(0, accent.blue() - 40), 245))
        p.setBrush(QBrush(icon_grad))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawRoundedRect(icon_rect, 13.0, 13.0)

        # Brand Glyph
        p.setPen(QColor(255, 255, 255, 245))
        if brand_glyph == "🔔":
            p.setFont(QFont("Segoe UI Emoji", 15))
        else:
            p.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        p.drawText(icon_rect, Qt.AlignmentFlag.AlignCenter, brand_glyph)

        # 2. Text Details
        text_x = 72
        max_text_w = max(100, w - 160)

        # Line 1: App Name & "• Just Now"
        p.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        p.setPen(accent)
        fm1 = QFontMetrics(p.font())
        app_str = app_name.upper()
        p.drawText(text_x, 26, app_str)
        app_w = fm1.horizontalAdvance(app_str)

        p.setFont(QFont("Segoe UI", 8, QFont.Weight.Normal))
        p.setPen(QColor(180, 180, 190, 180))
        p.drawText(text_x + app_w + 8, 26, "• Just Now")

        # Line 2: Sender / Title
        p.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        p.setPen(QColor(255, 255, 255, 245))
        fm2 = QFontMetrics(p.font())
        disp_title = fm2.elidedText(title or app_name, Qt.TextElideMode.ElideRight, max_text_w)
        p.drawText(text_x, 46, disp_title)

        # Line 3: Body Message Preview
        p.setFont(QFont("Segoe UI", 9, QFont.Weight.Normal))
        p.setPen(QColor(210, 210, 220, 200))
        fm3 = QFontMetrics(p.font())
        disp_body = fm3.elidedText(body or "New notification received", Qt.TextElideMode.ElideRight, max_text_w)
        p.drawText(text_x, 64, disp_body)

        # 3. Action Buttons on Right
        # Button 1: Open [ ↗ ]
        btn_open_rect = QRectF(w - 74.0, (h - 36) / 2.0, 32.0, 36.0)
        p.setBrush(QColor(255, 255, 255, 24))
        p.setPen(QPen(QColor(255, 255, 255, 38), 0.8))
        p.drawRoundedRect(btn_open_rect, 10.0, 10.0)
        p.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        p.setPen(QColor(255, 255, 255, 235))
        p.drawText(btn_open_rect, Qt.AlignmentFlag.AlignCenter, "↗")

        # Button 2: Dismiss [ ✕ ]
        btn_close_rect = QRectF(w - 38.0, (h - 36) / 2.0, 28.0, 36.0)
        p.setBrush(QColor(255, 255, 255, 16))
        p.setPen(QPen(QColor(255, 255, 255, 28), 0.8))
        p.drawRoundedRect(btn_close_rect, 10.0, 10.0)
        p.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        p.setPen(QColor(200, 200, 210, 190))
        p.drawText(btn_close_rect, Qt.AlignmentFlag.AlignCenter, "✕")

        p.restore()


    def _set_volume(self, val_pct: float):
        self._control_volume = max(0.0, min(100.0, float(val_pct)))
        _win_set_system_volume(self._control_volume)
        self.update()



    def _set_brightness(self, val_pct: float):
        self._control_brightness = max(15.0, min(100.0, float(val_pct)))
        _win_set_system_brightness(self._control_brightness)
        self.update()



    def _paint_notch_header(self, p: QPainter, theme: dict, w: int):
        # 1. Top-left subtle collapse indicator notch
        col_hover = self._btn_hover_anim.get("collapse", 0.0)
        col_press = self._btn_press_anim.get("collapse", 0.0)
        p.save()
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(255, 255, 255, int(40 + col_hover * 75)))
        notch_w = 24.0 * (1.0 - 0.12 * col_press)
        notch_x = 14.0 + (24.0 - notch_w) / 2.0
        p.drawRoundedRect(QRectF(notch_x, 11, notch_w, 5), 2.5, 2.5)
        p.restore()

        # 2. Digital Clock Centered
        cur_time_str = time.strftime("%H:%M")
        p.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        p.setPen(theme["text_primary"])
        p.drawText(QRect(0, 5, w, 22), Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter, cur_time_str)

        # 3. Battery Status on Right
        self._draw_vector_battery(p, w - 82, 10, self._battery_percent, self._battery_plugged, color=theme["text_primary"])
        p.setFont(QFont("Segoe UI", 8, QFont.Weight.DemiBold))
        p.setPen(theme["text_secondary"])
        p.drawText(QRect(w - 52, 8, 44, 15), Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, f"{self._battery_percent}%")

    def _paint_control(self, p: QPainter, theme: dict, w: int, h: int):
        """Screenshot 2: Bloom Control Center with Big Pill Tiles, 6 Quick Actions, and Dual Sliders."""
        self._paint_tab_headers(p, theme, w, active_tab="control")

        # 4 Big Pill Tiles (2x2 grid)
        # Tile 1: Wi-Fi
        t1_rect = QRectF(18, 34, 186, 44)
        t1_hover = self._btn_hover_anim.get("ctrl_tile_wifi", 0.0)
        p.save()
        p.setPen(Qt.PenStyle.NoPen)
        t1_bg = QColor(255, 255, 255, int(235 + 20 * t1_hover)) if self._wifi_connected else QColor(255, 255, 255, int(22 + 25 * t1_hover))
        p.setBrush(t1_bg)
        p.drawRoundedRect(t1_rect, 12, 12)
        icon_col1 = QColor(10, 12, 16) if self._wifi_connected else QColor(255, 255, 255)
        self._draw_vector_wifi(p, 42, 56, size=15, color=icon_col1)
        p.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        p.setPen(icon_col1)
        p.drawText(QRect(64, 40, 130, 16), Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, "Wi-Fi")
        p.setFont(QFont("Segoe UI", 8, QFont.Weight.Normal))
        p.setPen(QColor(icon_col1.red(), icon_col1.green(), icon_col1.blue(), 180))
        p.drawText(QRect(64, 56, 130, 16), Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, "Connected" if self._wifi_connected else "Disconnected")
        p.restore()

        # Tile 2: Taskbar Style
        t2_rect = QRectF(216, 34, 186, 44)
        t2_hover = self._btn_hover_anim.get("ctrl_tile_taskbar", 0.0)
        p.save()
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(255, 255, 255, int(235 + 20 * t2_hover)))
        p.drawRoundedRect(t2_rect, 12, 12)
        icon_col2 = QColor(10, 12, 16)
        self._draw_vector_taskbar_icon(p, 42 + 196, 56, color=icon_col2)
        p.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        p.setPen(icon_col2)
        p.drawText(QRect(262, 40, 130, 16), Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, "Taskbar")
        p.setFont(QFont("Segoe UI", 8, QFont.Weight.Normal))
        p.setPen(QColor(icon_col2.red(), icon_col2.green(), icon_col2.blue(), 180))
        tb_disp = getattr(self, "_taskbar_service", None)
        tb_text = tb_disp.short_display_name if tb_disp else "Clear Glass"
        p.drawText(QRect(262, 56, 130, 16), Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, f"Style: {tb_text}")
        p.restore()

        # Tile 3: Bluetooth
        t3_rect = QRectF(18, 86, 186, 44)
        t3_hover = self._btn_hover_anim.get("ctrl_tile_bt", 0.0)
        p.save()
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(255, 255, 255, int(235 + 20 * t3_hover)))
        p.drawRoundedRect(t3_rect, 12, 12)
        icon_col3 = QColor(10, 12, 16)
        is_bt_conn = bool(self._last_bluetooth_info and self._last_bluetooth_info.has_connected)
        bt_sub_text = self._last_bluetooth_info.primary_device_name if (is_bt_conn and self._last_bluetooth_info.primary_device_name) else "On"
        self._draw_vector_bluetooth(p, 42, 108, is_connected=is_bt_conn, color=icon_col3)
        p.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        p.setPen(icon_col3)
        p.drawText(QRect(64, 92, 130, 16), Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, "Bluetooth")
        p.setFont(QFont("Segoe UI", 8, QFont.Weight.Normal))
        p.setPen(QColor(icon_col3.red(), icon_col3.green(), icon_col3.blue(), 180))
        fm_bt = p.fontMetrics()
        p.drawText(QRect(64, 108, 130, 16), Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, fm_bt.elidedText(bt_sub_text, Qt.TextElideMode.ElideRight, 130))
        p.restore()

        # Tile 4: Notch Mode
        t4_rect = QRectF(216, 86, 186, 44)
        t4_hover = self._btn_hover_anim.get("ctrl_tile_notch", 0.0)
        p.save()
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(255, 255, 255, int(235 + 20 * t4_hover)))
        p.drawRoundedRect(t4_rect, 12, 12)
        # Notch icon
        icon_col4 = QColor(10, 12, 16)
        p.setPen(QPen(icon_col4, 1.3))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRoundedRect(QRectF(34 + 204, 101, 15, 12), 2.5, 2.5)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(icon_col4)
        p.drawRoundedRect(QRectF(39 + 204, 101, 5, 2.5), 1, 1)
        p.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        p.setPen(icon_col4)
        p.drawText(QRect(262, 92, 130, 16), Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, "Notch Mode")
        p.setFont(QFont("Segoe UI", 8, QFont.Weight.Normal))
        p.setPen(QColor(icon_col4.red(), icon_col4.green(), icon_col4.blue(), 180))
        p.drawText(QRect(262, 108, 130, 16), Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, f"Mode: {self._notch_mode}")
        p.restore()

        # 1.5. Dedicated One-Tap Quick Taskbar Style Pills Row (y: 138 to 162)
        p.save()
        p.setFont(QFont("Segoe UI", 8, QFont.Weight.DemiBold))
        p.setPen(theme.get("text_secondary", QColor(161, 161, 170)))
        p.drawText(QRect(20, 138, 56, 22), Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, "Taskbar:")

        tb_styles = [
            ("Clear", "clear", "ctrl_tb_clear"),
            ("Acrylic", "acrylic", "ctrl_tb_acrylic"),
            ("Blur", "blur", "ctrl_tb_blur"),
            ("OLED", "black", "ctrl_tb_black"),
            ("Default", "default", "ctrl_tb_default"),
        ]
        cur_tb_style = self._taskbar_service.current_style if getattr(self, "_taskbar_service", None) else "clear"
        pill_w = 58
        pill_h = 22
        pill_start_x = 78
        pill_gap = 7

        for i, (label, s_key, btn_id) in enumerate(tb_styles):
            px = pill_start_x + i * (pill_w + pill_gap)
            py = 138
            pill_rect = QRectF(px, py, pill_w, pill_h)
            is_active = (cur_tb_style == s_key)
            h_anim = self._btn_hover_anim.get(btn_id, 0.0)

            p.setPen(Qt.PenStyle.NoPen)
            if is_active:
                p.setBrush(QColor(255, 255, 255, 235))
                p.drawRoundedRect(pill_rect, 6, 6)
                p.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
                p.setPen(QColor(10, 12, 16))
                p.drawText(pill_rect, Qt.AlignmentFlag.AlignCenter, label)
            else:
                p.setBrush(QColor(255, 255, 255, int(20 + 35 * h_anim)))
                p.drawRoundedRect(pill_rect, 6, 6)
                p.setPen(QPen(QColor(255, 255, 255, int(35 + 40 * h_anim)), 1.0))
                p.setBrush(Qt.BrushStyle.NoBrush)
                p.drawRoundedRect(pill_rect, 6, 6)
                p.setFont(QFont("Segoe UI", 7.5, QFont.Weight.DemiBold))
                p.setPen(QColor(255, 255, 255, int(180 + 75 * h_anim)))
                p.drawText(pill_rect, Qt.AlignmentFlag.AlignCenter, label)
        p.restore()

        # 6 Circular Quick Action Icons Row (y: 170 to 202, cy: 186)
        circle_xs = [48, 112, 176, 244, 308, 372]
        actions = [
            ("ctrl_icon_moon", "moon"),
            ("ctrl_icon_battery", "battery"),
            ("ctrl_icon_apps", "apps"),
            ("ctrl_icon_bell", "bell"),
            ("ctrl_icon_settings", "settings"),
            ("ctrl_icon_refresh", "refresh")
        ]
        for (btn_key, act_type), cx in zip(actions, circle_xs):
            cy = 186
            h_v = self._btn_hover_anim.get(btn_key, 0.0)
            p_v = self._btn_press_anim.get(btn_key, 0.0)
            scale_i = (1.0 + 0.10 * h_v) * (1.0 - 0.12 * p_v)

            p.save()
            p.translate(cx, cy)
            p.scale(scale_i, scale_i)
            p.translate(-cx, -cy)

            p.setPen(QPen(QColor(255, 255, 255, int(30 + 40 * h_v)), 1.0))
            p.setBrush(QColor(255, 255, 255, int(22 + 45 * h_v)))
            p.drawEllipse(QPoint(cx, cy), 16, 16)

            act_col = QColor(255, 255, 255)
            if act_type == "moon":
                self._draw_vector_moon(p, cx, cy, size=13, color=act_col)
            elif act_type == "battery":
                self._draw_vector_battery(p, int(cx - 11), int(cy - 6), self._battery_percent, is_plugged=self._battery_plugged, color=act_col)
            elif act_type == "apps":
                self._draw_vector_launchpad(p, cx, cy, size=12, color=act_col)
            elif act_type == "bell":
                self._draw_vector_bell(p, cx, cy, size=13, color=act_col)
            elif act_type == "settings":
                self._draw_vector_gear(p, cx, cy, size=13, color=act_col)
            elif act_type == "refresh":
                self._draw_vector_refresh(p, cx, cy, size=13, color=act_col)

            p.restore()

        # Dual Sliders: Volume & Brightness
        # 1. Volume Slider (y: 222)
        vol_track_x = 110
        vol_track_w = 236
        vol_track_y = 222
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(255, 255, 255, 30))
        p.drawRoundedRect(QRectF(vol_track_x, vol_track_y, vol_track_w, 7), 3.5, 3.5)

        vol_fill_w = max(4.0, vol_track_w * (self._control_volume / 100.0))
        p.setBrush(QColor(255, 255, 255, 240))
        p.drawRoundedRect(QRectF(vol_track_x, vol_track_y, vol_fill_w, 7), 3.5, 3.5)
        # Thumb
        thumb_vol_x = vol_track_x + vol_fill_w
        p.drawEllipse(QPointF(thumb_vol_x, vol_track_y + 3.5), 6.5, 6.5)

        p.setFont(QFont("Segoe UI", 8, QFont.Weight.DemiBold))
        p.setPen(theme["text_secondary"])
        p.drawText(QRect(356, 218, 46, 16), Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight, f"{int(self._control_volume)}%")

        # 2. Brightness Slider (y: 252)
        self._draw_vector_weather_icon(p, 26, 256, icon_type="sun", color=theme["text_primary"], scale=0.65)
        p.setFont(QFont("Segoe UI", 8, QFont.Weight.DemiBold))
        p.setPen(theme["text_primary"])
        p.drawText(QRect(42, 248, 62, 16), Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, "Brightness")

        bri_track_x = 110
        bri_track_w = 236
        bri_track_y = 252
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(255, 255, 255, 30))
        p.drawRoundedRect(QRectF(bri_track_x, bri_track_y, bri_track_w, 7), 3.5, 3.5)

        bri_fill_w = max(4.0, bri_track_w * (self._control_brightness / 100.0))
        p.setBrush(QColor(255, 255, 255, 240))
        p.drawRoundedRect(QRectF(bri_track_x, bri_track_y, bri_fill_w, 7), 3.5, 3.5)
        # Thumb
        thumb_bri_x = bri_track_x + bri_fill_w
        p.drawEllipse(QPointF(thumb_bri_x, bri_track_y + 3.5), 6.5, 6.5)

        p.setFont(QFont("Segoe UI", 8, QFont.Weight.DemiBold))
        p.setPen(theme["text_secondary"])
        p.drawText(QRect(356, 248, 46, 16), Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight, f"{int(self._control_brightness)}%")

        # Vertical carousel page indicator dots on right edge (Dot 3 = Control)
        self._draw_vertical_page_dots(p, w - 12, h / 2.0, active_page=3, total_pages=5)


    def _paint_calendar(self, p: QPainter, theme: dict, w: int, h: int):
        """Calendar Card View matching modern OriginOS aesthetic with interactive month switcher."""
        # 0. Background: Pure AMOLED Black with Perfect Rounded Edges
        is_flush_notch = self._is_flush_notch()
        bg_path = self._make_notch_path(w, h, self._corner_radius, is_flush_notch)

        cal_bg = self._get_background_color()
        p.save()
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(cal_bg)
        p.fillPath(bg_path, cal_bg)
        border_col = QColor(255, 255, 255, 24)
        p.strokePath(self._make_notch_outline_path(w, h, self._corner_radius, is_flush_notch), QPen(border_col, 1.0))
        p.restore()

        self._paint_tab_headers(p, theme, w, active_tab="calendar")

        now = datetime.datetime.now()
        month_offset = getattr(self, "_cal_month_offset", 0)
        total_months = (now.year * 12 + now.month - 1) + month_offset
        disp_year = total_months // 12
        disp_month = (total_months % 12) + 1
        disp_date = datetime.date(disp_year, disp_month, 1)
        is_current_month = (disp_year == now.year and disp_month == now.month)
        accent = getattr(self, "_dynamic_accent_color", QColor(240, 181, 166))

        # Left Card: Big Date Capsule (x: 16, y: 32, w: 114, h: 148)
        card_rect = QRectF(16, 32, 114, 148)
        p.save()
        p.setPen(QPen(QColor(255, 255, 255, 24), 1.0))
        p.setBrush(QColor(255, 255, 255, 12))
        p.drawRoundedRect(card_rect, 14, 14)

        # Top row: [ ◀ ] Month Year [ ▶ ]
        p.setFont(QFont("Segoe UI", 9.5, QFont.Weight.Bold))
        p.setPen(accent)
        m_str = disp_date.strftime("%B")
        y_str = str(disp_year)
        p.drawText(QRectF(16, 40, 114, 18), Qt.AlignmentFlag.AlignCenter, f"{m_str} {y_str}")

        # Interactive Arrow indicators ◀ and ▶
        p.setFont(QFont("Segoe UI", 8.5, QFont.Weight.Bold))
        p.setPen(QColor(255, 255, 255, 140))
        p.drawText(QRectF(20, 40, 16, 18), Qt.AlignmentFlag.AlignCenter, "◀")
        p.drawText(QRectF(110, 40, 16, 18), Qt.AlignmentFlag.AlignCenter, "▶")

        # Center Huge Day Number with soft ambient glow
        t = self._anim_time
        day_disp = now.day if is_current_month else 1
        p.setFont(QFont("Segoe UI", 38, QFont.Weight.Bold))
        p.setPen(QColor(255, 255, 255))
        p.drawText(QRectF(16, 64, 114, 52), Qt.AlignmentFlag.AlignCenter, str(day_disp))

        # Day Name (e.g. Sunday)
        day_name = now.strftime("%A") if is_current_month else disp_date.strftime("%A")
        p.setFont(QFont("Segoe UI", 8.5, QFont.Weight.DemiBold))
        p.setPen(QColor(180, 175, 175))
        p.drawText(QRectF(16, 118, 114, 16), Qt.AlignmentFlag.AlignCenter, day_name)

        # Bottom Agenda / Focus Capsule
        agenda_rect = QRectF(26, 142, 94, 22)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(255, 255, 255, 18))
        p.drawRoundedRect(agenda_rect, 6, 6)
        p.setFont(QFont("Segoe UI", 7.5, QFont.Weight.Bold))
        p.setPen(accent if is_current_month else QColor(160, 160, 170))
        p.drawText(agenda_rect, Qt.AlignmentFlag.AlignCenter, "⚡ All Clear" if is_current_month else "Jump to Today")
        p.restore()

        # Right Area: Month View Grid (Mo Tu We Th Fr Sa Su)
        p.save()
        grid_x = 144.0
        grid_w = float(w - 170)
        col_w = grid_w / 7.0

        weekdays = ["Mo", "Tu", "We", "Th", "Fr", "Sa", "Su"]
        p.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
        for i, d_name in enumerate(weekdays):
            col_cx = grid_x + i * col_w + col_w / 2.0
            p.setPen(accent if i >= 5 else QColor(170, 170, 175))
            p.drawText(QRectF(col_cx - col_w / 2.0, 36, col_w, 18), Qt.AlignmentFlag.AlignCenter, d_name)

        # Thin divider below weekdays
        p.setPen(QPen(QColor(255, 255, 255, 20), 1.0))
        p.drawLine(QPointF(grid_x, 56), QPointF(grid_x + grid_w, 56))

        # Month Days
        first_weekday, num_days = calendar.monthrange(disp_year, disp_month)
        grid_start = first_weekday
        today_day = now.day if is_current_month else -1

        row = 0
        col = grid_start
        row_h = 20.0
        start_y = 64.0

        for day in range(1, num_days + 1):
            dx = grid_x + col * col_w + col_w / 2.0
            dy = start_y + row * row_h + row_h / 2.0

            if day == today_day:
                # Breathing halo glow behind today's date
                p.setPen(Qt.PenStyle.NoPen)
                halo_alpha = int(70 + 40 * math.sin(t * 3.5))
                halo = QRadialGradient(dx, dy, 13.0)
                halo.setColorAt(0.0, QColor(accent.red(), accent.green(), accent.blue(), halo_alpha))
                halo.setColorAt(1.0, QColor(0, 0, 0, 0))
                p.setBrush(halo)
                p.drawEllipse(QPointF(dx, dy), 13.0, 13.0)

                # Vibrant today badge
                p.setBrush(accent)
                p.drawEllipse(QPointF(dx, dy), 9.0, 9.0)

                p.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
                p.setPen(QColor(16, 16, 20))
                p.drawText(QRectF(dx - 12, dy - 10, 24, 20), Qt.AlignmentFlag.AlignCenter, str(day))
            else:
                p.setFont(QFont("Segoe UI", 8, QFont.Weight.Normal))
                if col >= 5:
                    p.setPen(QColor(180, 160, 160, 190))
                else:
                    p.setPen(QColor(240, 240, 245, 235))
                p.drawText(QRectF(dx - 12, dy - 10, 24, 20), Qt.AlignmentFlag.AlignCenter, str(day))

            col += 1
            if col > 6:
                col = 0
                row += 1

        p.restore()

        # Vertical page dots on right edge (Dot #1 Calendar is active, 5 total pages)
        self._draw_vertical_page_dots(p, w - 12, h / 2.0, active_page=1, total_pages=5)

    def _paint_compact(self, p: QPainter, theme: dict, w: int, h: int):
        # -1. Small Trigger Icon Mode (discrete mini notch handle: hover over it to summon island!)
        if getattr(self, "_is_retracted", False) or w <= 68 or h <= 18:
            self._draw_compact_retracted_icon(p, theme, w, h)
            return

        # Interactive breathing hover highlight sheen across compact pill
        if self._is_hovered or self._hovered_btn == "compact_pill":
            sheen_alpha = int(45 + 35 * math.sin(self._anim_time * 4.0))
            p.save()
            p.setBrush(Qt.BrushStyle.NoBrush)
            is_flush = self._is_flush_notch()
            p.strokePath(self._make_notch_outline_path(w, h, self._corner_radius, is_flush), QPen(QColor(255, 255, 255, sheen_alpha), 1.2))
            p.restore()

        # 0. Windows Pop-up in Notch (Nixi Feature 13: Caps lock, Battery, Hydration, Awake)
        if time.monotonic() - getattr(self, "_sys_hud_toast_time", 0.0) < 2.0:
            self._draw_compact_sys_hud(p, theme, w, h)
            return

        # Auto-timeout safety: never leave JARVIS speech stuck permanently in compact mode
        if self._is_jarvis_talking and (time.monotonic() - getattr(self, "_jarvis_speech_time", 0.0) > 4.5):
            self._is_jarvis_talking = False
            self._assistant_status = "Ready"

        is_music = self._is_genuine_music_playing()
        is_speech = (self._is_jarvis_talking or getattr(self, "_is_voice_listening", False) or 
                     (time.monotonic() - getattr(self, "_jarvis_speech_time", 0.0) < 2.5 and not is_music))

        # 0.5. JARVIS Live Speech & Interaction in Notch
        if is_speech:
            self._draw_compact_jarvis_speech(p, theme, w, h)
            return

        # 1. When genuine music is playing: SHOW THE SONG (Album art + Marquee + Equalizer)
        # Strictly NEVER show it for opening other applications like File Explorer or IDEs!
        if is_music:
            self._paint_compact_song(p, theme, w, h)
            return

        # 2. Idle Modes (Living Pet Eyes, Live Network Speedometer, Mini Weather, Hardware Vitals)
        idle_mode = getattr(self, "_compact_idle_mode", "eyes")
        if idle_mode == "network":
            self._draw_compact_network(p, theme, w, h)
        elif idle_mode == "weather":
            self._draw_compact_weather(p, theme, w, h)
        elif idle_mode == "vitals":
            self._draw_compact_vitals(p, theme, w, h)
        else:
            self._draw_compact_pet_eyes(p, theme, w, h)

    def _draw_compact_retracted_icon(self, p: QPainter, theme: dict, w: int, h: int):
        """
        Draws the sleek discreet top trigger icon at the screen bezel.
        When the user hovers over this icon, our island immediately expands down!
        """
        p.save()
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        is_flush_notch = self._is_flush_notch()
        notch_path = self._make_notch_path(w, h, 5.0, is_flush_notch)

        # 1. Dark glass notch body (AMOLED pure black or theme dark)
        grad_colors = theme.get("notch_gradient")
        bg_col = grad_colors[0] if grad_colors else theme.get("bg_top", QColor(10, 12, 18, 250))
        p.fillPath(notch_path, bg_col)

        # 2. Glowing responsive rim (brightens when hovered)
        pulse = 0.5 + 0.5 * math.sin(self._anim_time * 4.0)
        if self._is_hovered:
            border_col = QColor(0, 240, 255, 230)
            p.strokePath(notch_path, QPen(border_col, 1.2))
        else:
            border_col = QColor(255, 255, 255, int(40 + 35 * pulse))
            p.strokePath(notch_path, QPen(border_col, 1.0))

        # 3. Center Glowing AI Spark & Touch Grip Indicator
        cx, cy = w // 2, h // 2
        glow_rad = 10.0 if self._is_hovered else 6.0
        glow_grad = QRadialGradient(cx, cy, glow_rad)
        acc = theme.get("accent", QColor(0, 240, 255))
        glow_grad.setColorAt(0.0, QColor(acc.red(), acc.green(), acc.blue(), int(180 + 75 * pulse)))
        glow_grad.setColorAt(1.0, QColor(0, 0, 0, 0))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(glow_grad)
        p.drawEllipse(QPointF(cx, cy), glow_rad, glow_rad)

        # Center micro touch bar
        bar_w = 20.0 if self._is_hovered else 14.0
        p.setBrush(QColor(255, 255, 255, 240))
        p.drawRoundedRect(QRectF(cx - bar_w / 2.0, cy - 1.2, bar_w, 2.4), 1.2, 1.2)
        p.restore()

    def _draw_compact_sys_hud(self, p: QPainter, theme: dict, w: int, h: int):
        """Draws Apple Dynamic Island Hardware HUD (Volume capsule, Battery/Charging, USB, Caps/Num Lock)."""
        p.save()
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        is_flush_notch = self._is_flush_notch()
        notch_path = self._make_notch_path(w, h, self._corner_radius, is_flush_notch)
        p.fillPath(notch_path, QColor(0, 0, 0, 255))
        p.strokePath(self._make_notch_outline_path(w, h, self._corner_radius, is_flush_notch), QPen(QColor(255, 255, 255, 35), 1.0))

        hud_type = getattr(self, "_sys_hud_toast_type", "")
        hud_val = getattr(self, "_sys_hud_toast_val", 0)
        hud_text = getattr(self, "_sys_hud_toast_text", "")
        ear_offset = 0.0

        if hud_type == "volume":
            # ── Dynamic Island Hardware Volume HUD ──
            cx = int(ear_offset + 22)
            cy = h // 2
            # Speaker Body
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor(255, 255, 255, 240))
            spk = QPainterPath()
            spk.moveTo(cx - 6, cy - 3)
            spk.lineTo(cx - 2, cy - 3)
            spk.lineTo(cx + 3, cy - 7)
            spk.lineTo(cx + 3, cy + 7)
            spk.lineTo(cx - 2, cy + 3)
            spk.lineTo(cx - 6, cy + 3)
            spk.closeSubpath()
            p.fillPath(spk, QColor(255, 255, 255, 240))

            # Sound Waves
            p.setPen(QPen(QColor(255, 255, 255, 240), 1.5, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            p.setBrush(Qt.BrushStyle.NoBrush)
            if hud_val > 0:
                p.drawArc(QRectF(cx + 4, cy - 5, 8, 10), -55 * 16, 110 * 16)
            if hud_val > 40:
                p.drawArc(QRectF(cx + 6, cy - 8, 12, 16), -55 * 16, 110 * 16)

            # Horizontal Capsule Track
            bar_x = int(cx + 24)
            bar_w = int(w - ear_offset - bar_x - 48)
            bar_h = 6
            bar_y = (h - bar_h) // 2
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor(255, 255, 255, 35))
            p.drawRoundedRect(QRectF(bar_x, bar_y, bar_w, bar_h), 3, 3)

            # Filled Volume Level
            fill_w = max(0.0, bar_w * (hud_val / 100.0))
            p.setBrush(QColor(255, 255, 255, 245))
            p.drawRoundedRect(QRectF(bar_x, bar_y, fill_w, bar_h), 3, 3)

            # Percentage Badge
            p.setFont(QFont("Segoe UI", 8.5, QFont.Weight.Bold))
            p.setPen(QColor(255, 255, 255, 230))
            p.drawText(QRect(int(w - ear_offset - 44), 0, 36, h), Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight, f"{hud_val}%")

        elif hud_type in ("charging", "battery", "low_battery"):
            # ── Dynamic Island Battery / Charging Toast ──
            bx = int(ear_offset + 20)
            by = (h - 14) // 2
            is_charging = (hud_type == "charging")
            is_low = (hud_type == "low_battery")
            theme_col = QColor(52, 199, 89) if is_charging else (QColor(239, 68, 68) if is_low else QColor(255, 255, 255, 220))

            # Battery Outer Shell
            p.setPen(QPen(theme_col, 1.4))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawRoundedRect(QRectF(bx, by, 22, 14), 3, 3)
            p.drawRoundedRect(QRectF(bx + 23, by + 4, 2.5, 6), 1, 1)

            # Battery Fill Level
            fill_w = max(2.0, 18.0 * (hud_val / 100.0))
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(theme_col)
            p.drawRoundedRect(QRectF(bx + 2, by + 2, fill_w, 10), 1.5, 1.5)

            # Lightning Bolt if Charging
            if is_charging:
                p.setBrush(QColor(255, 255, 255))
                bolt = QPainterPath()
                bolt.moveTo(bx + 12, by + 1)
                bolt.lineTo(bx + 7, by + 7)
                bolt.lineTo(bx + 11, by + 7)
                bolt.lineTo(bx + 10, by + 13)
                bolt.lineTo(bx + 15, by + 6)
                bolt.lineTo(bx + 11, by + 6)
                bolt.closeSubpath()
                p.fillPath(bolt, QColor(255, 255, 255))

            # Status Text
            p.setFont(QFont("Segoe UI", 9, QFont.Weight.DemiBold))
            p.setPen(QColor(255, 255, 255, 240))
            p.drawText(QRect(bx + 34, 0, int(w - ear_offset - bx - 44), h), Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, hud_text)

        elif hud_type in ("caps", "num_lock"):
            # ── Apple Dynamic Island Lock Capsule (Caps Lock / Num Lock) ──
            lx = 22
            ly = h // 2
            is_on = (hud_val == 1)
            accent_col = QColor(255, 255, 255) if is_on else QColor(160, 160, 165)
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(accent_col)
            p.drawRoundedRect(QRectF(lx - 6, ly - 2, 12, 10), 2, 2)
            p.setPen(QPen(accent_col, 1.5))
            p.setBrush(Qt.BrushStyle.NoBrush)
            shackle_y = (ly - 8) if is_on else (ly - 10)
            p.drawArc(QRectF(lx - 4, shackle_y, 8, 8), 0, 180 * 16)

            p.setFont(QFont(["Segoe UI", "sans-serif"], 9, QFont.Weight.Bold))
            p.setPen(QColor(255, 255, 255, 245))
            p.drawText(QRect(lx + 16, 0, w - lx - 24, h), Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, hud_text)

        elif hud_type == "usb":
            # ── Dynamic Island USB Connected Toast ──
            ux = int(ear_offset + 22)
            uy = h // 2
            # Vector USB Icon
            p.setPen(QPen(QColor(0, 220, 255), 1.5))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawRoundedRect(QRectF(ux - 7, uy - 4, 14, 8), 2, 2)
            p.setBrush(QColor(0, 220, 255))
            p.drawRect(QRectF(ux + 7, uy - 2.5, 4, 5))

            p.setFont(QFont("Segoe UI", 9, QFont.Weight.DemiBold))
            p.setPen(QColor(255, 255, 255, 245))
            p.drawText(QRect(ux + 20, 0, int(w - ear_offset - ux - 28), h), Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, hud_text)

        else:
            # General Text HUD (Calibration, Hydration, Awake)
            p.setFont(QFont("Segoe UI", 8.5, QFont.Weight.Bold))
            p.setPen(QColor(255, 255, 255, 245))
            p.drawText(QRect(0, 0, w, h), Qt.AlignmentFlag.AlignCenter, hud_text)

        p.restore()

        p.restore()

    def _draw_compact_jarvis_speech(self, p: QPainter, theme: dict, w: int, h: int):
        """Draws living JARVIS speech marquee & voice equalizer in the compact notch."""
        p.save()
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        is_flush_notch = self._is_flush_notch()
        notch_path = self._make_notch_path(w, h, self._corner_radius, is_flush_notch)

        # Pure OLED black notch backdrop
        p.fillPath(notch_path, QColor(8, 10, 16, 255))
        # Pulsing animated cyan/electric edge (outline only; no top bezel stroke)
        pulse_alpha = int(90 + 75 * math.sin(self._anim_time * 6.0))
        p.strokePath(self._make_notch_outline_path(w, h, self._corner_radius, is_flush_notch), QPen(QColor(0, 240, 255, pulse_alpha), 1.2))

        # Left Icon: 4-point glowing AI spark core
        spark_cx, spark_cy = 22, h // 2
        self._draw_vector_spark(p, spark_cx, spark_cy, color=QColor(0, 240, 255), scale=1.1)

        # Center: Live Talking Words Marquee
        text_rect = QRect(38, 0, w - 82, h)
        p.save()
        p.setClipRect(text_rect)
        p.setFont(QFont("Segoe UI", 8.5, QFont.Weight.DemiBold))

        if getattr(self, "_is_voice_listening", False):
            p.setPen(QColor(0, 240, 255, 240))
            p.drawText(text_rect, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, "🎙️ Listening to you...")
        else:
            speech_str = self._live_jarvis_speech if self._live_jarvis_speech else "JARVIS Ready"
            full_str = f"✦ JARVIS: \"{speech_str}\""
            fm = QFontMetrics(p.font())
            tw = fm.horizontalAdvance(full_str)
            if tw > text_rect.width():
                span = float(tw + 36)
                cur_x = text_rect.x() - (self._jarvis_compact_ticker_x % span)
                p.setPen(QColor(255, 255, 255, 240))
                p.drawText(int(cur_x), int(text_rect.y()), int(tw + 10), int(text_rect.height()), Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, full_str)
                if cur_x + tw < text_rect.right():
                    p.drawText(int(cur_x + span), int(text_rect.y()), int(tw + 10), int(text_rect.height()), Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, full_str)
            else:
                p.setPen(QColor(255, 255, 255, 240))
                p.drawText(text_rect, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, full_str)
        p.restore()

        # Right: 4-band animated jumping emerald voice bars
        p.save()
        right_cx = w - 24
        bar_w = 2.4
        gap = 2.2
        total_w = 4 * bar_w + 3 * gap
        bx0 = right_cx - total_w / 2.0
        by_mid = h / 2.0

        for i in range(4):
            bar_pct = 0.25 + 0.70 * (math.sin(self._anim_time * (15.0 + i * 4.5) + i * 1.2) * 0.5 + 0.5)
            bar_h = max(3.0, 16.0 * bar_pct)
            bx = bx0 + i * (bar_w + gap)
            by = by_mid - bar_h / 2.0

            b_grad = QLinearGradient(bx, by, bx, by + bar_h)
            b_grad.setColorAt(0.0, QColor(0, 240, 255))
            b_grad.setColorAt(1.0, QColor(16, 185, 129))
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(b_grad)
            p.drawRoundedRect(QRectF(bx, by, bar_w, bar_h), 1.2, 1.2)
        p.restore()

        p.restore()

    def _draw_compact_grooving_eyes(self, p: QPainter, theme: dict, cx: float, cy: float, scale: float = 1.0, beat_react: bool = True):
        """
        Renders living cute pet eyes grooving rhythmically to playing music.
        Features:
        - Reactive head-bobbing & wobble to audio beat energy
        - Natural blinking (every 3-5s via _pet_eye_blink_phase)
        - Desktop cursor gaze tracking
        - Specular catchlight highlights
        - Custom Cyan / theme eye color with blooming ambient glow
        """
        p.save()
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        # Determine eye color (prefer cyan / user chosen color from settings)
        if getattr(self, "_custom_eye_color", None) and self._custom_eye_color.isValid():
            active_eye_color = self._custom_eye_color
        else:
            active_eye_color = NIXI_EYE_COLORS.get(getattr(self, "_eye_color_key", "white"), ("White", theme.get("eye_color", QColor(0, 212, 255))))[1]

        # Music rhythm bobbing & wobble
        beat = getattr(self, "_ambient_beat_energy", 0.0) if beat_react else 0.0
        bob_y = math.sin(self._anim_time * 8.0) * (1.2 + 2.0 * beat)
        wobble = math.sin(self._anim_time * 4.0) * 3.5

        cy_adj = cy + bob_y

        p.translate(cx, cy_adj)
        p.rotate(wobble)
        p.translate(-cx, -cy_adj)

        # Blink multiplier
        blink_mult = 1.0
        if getattr(self, "_pet_eye_blink_phase", 0.0) > 0.0:
            s = math.sin(self._pet_eye_blink_phase * math.pi / 2.0)
            blink_mult = max(0.12, 1.0 - s)

        # Gaze tracking toward cursor
        glance_x = getattr(self, "_pet_eye_glance_x", 0.0) + getattr(self, "_pet_eye_cursor_glance_x", 0.0)
        glance_y = getattr(self, "_pet_eye_glance_y", 0.0) + getattr(self, "_pet_eye_cursor_glance_y", 0.0)

        # Hover dilation
        is_hovered = self._is_hovered or (self._hovered_btn == "compact_pill")
        hover_dilate = 0.8 if is_hovered else 0.0

        eye_spacing = 13.0 * scale
        base_w = (6.0 + hover_dilate) * scale
        base_h = (9.8 * blink_mult + hover_dilate) * scale

        # Check emotional state (love, happy, etc.)
        cur_emotion = getattr(self, "_pet_emotion", "idle")
        if getattr(self, "_pet_emotion_timer", 0.0) <= 0.0:
            cur_emotion = "idle"

        if cur_emotion in ["love", "happy"]:
            # Smiling arches (⌒ ⌒) grooving to music!
            arch_pen = QPen(active_eye_color, 2.2 * scale)
            arch_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            arch_pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
            p.setPen(arch_pen)
            p.setBrush(Qt.BrushStyle.NoBrush)
            for ox in [-eye_spacing / 2.0, eye_spacing / 2.0]:
                acx = cx + ox
                arch = QPainterPath()
                arch.moveTo(acx - 4.5 * scale, cy_adj + 2.0 * scale)
                arch.quadTo(acx, cy_adj - 3.5 * scale, acx + 4.5 * scale, cy_adj + 2.0 * scale)
                p.drawPath(arch)
        else:
            # Living dilated pills with catchlights and specular glow
            for ox in [-eye_spacing / 2.0, eye_spacing / 2.0]:
                ecx = cx + ox + glance_x * 0.35
                ecy = cy_adj + glance_y * 0.35

                # Ambient glow halo
                glow_r = 11.0 * scale
                glow = QRadialGradient(ecx, ecy, glow_r)
                glow.setColorAt(0.0, QColor(active_eye_color.red(), active_eye_color.green(), active_eye_color.blue(), 110))
                glow.setColorAt(0.5, QColor(active_eye_color.red(), active_eye_color.green(), active_eye_color.blue(), 40))
                glow.setColorAt(1.0, QColor(0, 0, 0, 0))
                p.setPen(Qt.PenStyle.NoPen)
                p.setBrush(glow)
                p.drawEllipse(QPointF(ecx, ecy), glow_r, glow_r)

                # Eye capsule
                p.setBrush(active_eye_color)
                p.drawRoundedRect(QRectF(ecx - base_w / 2.0, ecy - base_h / 2.0, base_w, base_h), base_w / 2.0, base_w / 2.0)

                # Catchlight specular dots (only when eye is open enough)
                if blink_mult > 0.45:
                    p.setBrush(QColor(255, 255, 255, 245))
                    p.drawEllipse(QRectF(ecx - 1.6 * scale, ecy - 2.8 * scale, 2.0 * scale, 2.0 * scale))
                    p.drawEllipse(QRectF(ecx + 0.5 * scale, ecy + 1.2 * scale, 1.2 * scale, 1.2 * scale))

        p.restore()

    def _paint_compact_song(self, p: QPainter, theme: dict, w: int, h: int):
        """
        Draws the active music notch hanging from top edge:
        Left: Squircle album art with dynamic beat aura glow.
        Beside Art: Cute living pet eyes grooving rhythmically to the music beat!
        Center: Track title with smooth marquee if long + artist subtitle / live lyrics.
        Right: Multi-band animated jumping equalizer spectrum bars + accent status dot.
        """
        p.save()
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        p.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)

        # 1. Notch Background from Theme (with transparency / opacity setting)
        op_mult = getattr(self, "_background_opacity", 100) / 100.0
        grad_colors = theme.get("notch_gradient")
        if not grad_colors:
            grad_colors = (theme.get("bg_top", QColor(0, 0, 0, 255)), theme.get("bg_bottom", QColor(0, 0, 0, 255)))

        c_top = QColor(grad_colors[0])
        c_bot = QColor(grad_colors[1])
        c_top.setAlpha(int(255 * op_mult))
        c_bot.setAlpha(int(255 * op_mult))

        grad = QLinearGradient(0, 0, w, 0)
        grad.setColorAt(0.0, c_top)
        grad.setColorAt(1.0, c_bot)

        is_flush_notch = self._is_flush_notch()
        notch_path = self._make_notch_path(w, h, self._corner_radius, is_flush_notch)
        p.fillPath(notch_path, grad)

        # Hairline glass border rim (clean hanging contour)
        border_col = theme.get("border", QColor(255, 255, 255, 36))
        p.strokePath(self._make_notch_outline_path(w, h, self._corner_radius, is_flush_notch), QPen(border_col, 1.0))

        # Top glass sheen clipped to notch body
        sheen_grad = QLinearGradient(0, 0, 0, h * 0.45)
        sheen_grad.setColorAt(0.0, QColor(255, 255, 255, 45))
        sheen_grad.setColorAt(1.0, QColor(255, 255, 255, 0))
        p.save()
        p.setClipPath(notch_path)
        p.fillPath(notch_path, sheen_grad)
        p.restore()

        # Ear offset for flush notch
        ear_pad = 14.0 if is_flush_notch else 2.0

        # 2. Left: 28x28 Album Art Squircle with soft beat glow
        thumb_bytes = self._last_media_info.thumbnail_bytes if self._last_media_info else None
        art_size = 28
        art_x = int(ear_pad + 6.0)
        art_y = int((h - art_size) / 2.0)
        art_rect = QRect(art_x, art_y, art_size, art_size)
        art_path = QPainterPath()
        art_path.addRoundedRect(QRectF(art_rect), 8.0, 8.0)

        # Beat glow aura behind album art
        beat = getattr(self, "_ambient_beat_energy", 0.0)
        if beat > 0.08:
            p.save()
            glow_c = getattr(self, "_dynamic_accent_color", QColor(240, 181, 166))
            glow_grad = QRadialGradient(art_rect.center().x(), art_rect.center().y(), art_size * 0.85)
            glow_grad.setColorAt(0.0, QColor(glow_c.red(), glow_c.green(), glow_c.blue(), int(min(120, 40 + beat * 100))))
            glow_grad.setColorAt(1.0, QColor(0, 0, 0, 0))
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(glow_grad)
            p.drawEllipse(art_rect.center(), int(art_size * 0.85), int(art_size * 0.85))
            p.restore()

        has_art = False
        if thumb_bytes:
            pix = self._get_scaled_album_art(thumb_bytes, art_size)
            if pix and not pix.isNull():
                p.save()
                p.setClipPath(art_path)
                p.drawPixmap(art_rect, pix)
                p.restore()
                has_art = True

        if not has_art:
            art_grad = QLinearGradient(art_x, art_y, art_x + art_size, art_y + art_size)
            art_grad.setColorAt(0.0, QColor(255, 59, 92))
            art_grad.setColorAt(1.0, QColor(220, 38, 127))
            p.fillPath(art_path, art_grad)
            self._draw_vector_note(p, art_x + art_size // 2, art_y + art_size // 2, size=13, color=QColor(255, 255, 255))

        p.strokePath(art_path, QPen(QColor(255, 255, 255, 40), 1.0))

        # 3. Cute Living Pet Eyes: Grooving and bobbing right beside album art!
        eyes_cx = art_x + art_size + 24.0
        eyes_cy = h / 2.0
        self._draw_compact_grooving_eyes(p, theme, eyes_cx, eyes_cy, scale=1.0, beat_react=True)

        # 4. Center: Track Details vs Active Lyrics based on lyrics button toggle
        show_lyrics = getattr(self, "_music_show_lyrics", False)
        active_lyric = None
        if show_lyrics and self._lyrics_lines and 0 <= self._lyrics_active_idx < len(self._lyrics_lines):
            active_lyric = self._lyrics_lines[self._lyrics_active_idx][1].strip()

        eq_block_w = 26
        dot_cx = w - (ear_pad + 10.0)
        eq_x = int(dot_cx - 8.0 - eq_block_w)
        text_x = int(eyes_cx + 20.0)
        avail_w = max(40, eq_x - text_x - 10)

        text_rect = QRectF(text_x, 0, avail_w, h)

        if show_lyrics and active_lyric:
            display_str = f"... {active_lyric}"
            font_size = 9.2
        else:
            title_text = self._last_media_info.title if (self._last_media_info and self._last_media_info.title) else "Playing Music"
            artist_text = self._last_media_info.artist if (self._last_media_info and self._last_media_info.artist) else ""
            if artist_text and artist_text not in ["Unknown Artist", ""]:
                display_str = f"{title_text}  ·  {artist_text}"
            else:
                display_str = title_text
            font_size = 9.0

        lyric_font = QFont()
        lyric_font.setFamilies(["Segoe UI", "Nirmala UI", "sans-serif"])
        lyric_font.setPointSizeF(font_size)
        lyric_font.setWeight(QFont.Weight.Bold)

        ticker_offset = getattr(self, "_compact_lyric_ticker_x", 0.0) if (show_lyrics and active_lyric) else getattr(self, "_compact_ticker_x", 0.0)
        self._draw_smooth_marquee(
            p,
            text_rect,
            display_str,
            lyric_font,
            QColor(255, 255, 255, 250),
            ticker_offset,
            gap=44.0,
            fade_width=14.0
        )

        # 5. Right: 6-band dynamic equalizer bars + accent dot
        accent_color = getattr(self, "_dynamic_accent_color", QColor(240, 181, 166))
        self._draw_player_equalizer(p, eq_x, (h - 16.0) / 2.0, eq_block_w, 16.0, accent_color)

        # Dynamic accent status dot
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(accent_color)
        p.drawEllipse(QPointF(dot_cx, h / 2.0), 3.0, 3.0)

        p.restore()

    def _draw_compact_pet_eyes(self, p: QPainter, theme: dict, w: int, h: int):
        """
        Draws the cute animated living pet notch matching Screenshots 1 & 3:
        Theme-reactive background (pure OLED black for AMOLED, neon for electric neon),
        blinking/wandering glowing eyes with cursor tracking, sleepy idle breathing,
        winking (⌒ •), and smiling arches (⌒ ⌒) + glowing paw print when hovered or listening.
        """
        p.save()
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        # 1. Theme-reactive Background Gradient (pure OLED black for amoled_black)
        grad_colors = theme.get("notch_gradient")
        if not grad_colors:
            grad_colors = (theme.get("bg_top", QColor(0, 0, 0, 255)), theme.get("bg_bottom", QColor(0, 0, 0, 255)))

        grad = QLinearGradient(0, 0, w, 0)
        if len(grad_colors) == 2:
            grad.setColorAt(0.0, grad_colors[0])
            grad.setColorAt(1.0, grad_colors[1])
        elif len(grad_colors) >= 3:
            grad.setColorAt(0.0, grad_colors[0])
            grad.setColorAt(0.5, grad_colors[1])
            grad.setColorAt(1.0, grad_colors[2])

        is_flush_notch = self._is_flush_notch()
        notch_path = self._make_notch_path(w, h, self._corner_radius, is_flush_notch)
        p.fillPath(notch_path, grad)

        # Subtle bottom rim glow (outline only; no top bezel stroke)
        border_col = theme.get("border", QColor(255, 255, 255, 40))
        p.strokePath(self._make_notch_outline_path(w, h, self._corner_radius, is_flush_notch), QPen(border_col, 1.0))

        # Top glass sheen clipped to notch body
        s_margin = 2.0
        sheen_grad = QLinearGradient(0, 0, 0, h * 0.45)
        sheen_grad.setColorAt(0.0, QColor(255, 255, 255, 50))
        sheen_grad.setColorAt(1.0, QColor(255, 255, 255, 0))
        p.save()
        p.setClipPath(notch_path)
        p.fillPath(notch_path, sheen_grad)
        p.restore()

        # Subtle top tuck handle (click to tuck island into small trigger icon)
        is_tuck_hover = (self._hovered_btn == "compact_tuck")
        tuck_alpha = 180 if is_tuck_hover else 40
        p.save()
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(255, 255, 255, tuck_alpha))
        p.drawRoundedRect(QRectF(w / 2.0 - 12.0, 2.0, 24.0, 3.0), 1.5, 1.5)
        p.restore()

        cx = w // 2
        cy = h // 2

        # Custom RGBA Eye Color (from settings/color picker) or Nixi presets
        if getattr(self, "_custom_eye_color", None) and self._custom_eye_color.isValid():
            active_eye_color = self._custom_eye_color
        else:
            active_eye_color = NIXI_EYE_COLORS.get(getattr(self, "_eye_color_key", "white"), ("White", theme.get("eye_color", QColor(255, 255, 255))))[1]

        # Bouncy emotional offset & music beat bob
        beat = self._ambient_beat_energy
        if beat > 0.05:
            cy += int(math.sin(self._anim_time * 8.0) * (beat * 2.5))
        cy += int(getattr(self, "_pet_bounce_y", 0.0))

        cur_emotion = getattr(self, "_pet_emotion", "idle")
        if getattr(self, "_pet_emotion_timer", 0.0) <= 0.0:
            cur_emotion = "idle"

        # ── EMOTIONAL STATE RENDERING ────────────────────────────────────────
        if cur_emotion == "love":
            # ── 1. LOVE EMOTION: Smiling Arches (⌒ ⌒), Soft Pink Blush & Floating Hearts ──
            arch_pen = QPen(active_eye_color, 2.5)
            arch_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            arch_pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
            p.setPen(arch_pen)
            p.setBrush(Qt.BrushStyle.NoBrush)

            # Left & Right smiling arches
            arch1 = QPainterPath()
            arch1.moveTo(cx - 20, cy + 2.5)
            arch1.quadTo(cx - 15, cy - 4.5, cx - 10, cy + 2.5)
            p.drawPath(arch1)

            arch2 = QPainterPath()
            arch2.moveTo(cx + 10, cy + 2.5)
            arch2.quadTo(cx + 15, cy - 4.5, cx + 20, cy + 2.5)
            p.drawPath(arch2)

            # Glowing Rose-Pink Cheeks (Blush)
            blush_a = int(180 * max(0.2, getattr(self, "_pet_blush_alpha", 1.0)))
            if blush_a > 10:
                p.setPen(Qt.PenStyle.NoPen)
                for bx in [cx - 32, cx + 32]:
                    b_grad = QRadialGradient(bx, cy + 2.5, 9.0)
                    b_grad.setColorAt(0.0, QColor(255, 105, 180, blush_a))
                    b_grad.setColorAt(0.65, QColor(255, 105, 180, int(blush_a * 0.45)))
                    b_grad.setColorAt(1.0, QColor(255, 105, 180, 0))
                    p.setBrush(b_grad)
                    p.drawEllipse(QPointF(bx, cy + 2.5), 9.0, 5.5)

            # Glowing paw print
            paw_x = cx + 28
            paw_y = cy - 0.5
            halo_grad = QRadialGradient(paw_x, paw_y, 8.0)
            halo_grad.setColorAt(0.0, QColor(255, 105, 180, 90))
            halo_grad.setColorAt(1.0, QColor(0, 0, 0, 0))
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(halo_grad)
            p.drawEllipse(QPointF(paw_x, paw_y), 8.0, 8.0)
            p.setBrush(active_eye_color)
            p.drawEllipse(QRectF(paw_x - 3.2, paw_y + 0.2, 6.4, 4.8))
            p.drawEllipse(QRectF(paw_x - 4.4, paw_y - 3.6, 2.2, 2.6))
            p.drawEllipse(QRectF(paw_x - 1.8, paw_y - 5.0, 2.2, 2.6))
            p.drawEllipse(QRectF(paw_x + 1.2, paw_y - 5.0, 2.2, 2.6))
            p.drawEllipse(QRectF(paw_x + 3.8, paw_y - 3.6, 2.2, 2.6))

        elif cur_emotion == "happy":
            # ── 2. HAPPY EMOTION: Cheerful Squints & Joyful Waving Paw ──
            arch_pen = QPen(active_eye_color, 2.4)
            arch_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            p.setPen(arch_pen)
            p.setBrush(Qt.BrushStyle.NoBrush)

            arch1 = QPainterPath()
            arch1.moveTo(cx - 18, cy + 2.0)
            arch1.quadTo(cx - 13, cy - 4.0, cx - 8, cy + 2.0)
            p.drawPath(arch1)

            arch2 = QPainterPath()
            arch2.moveTo(cx + 8, cy + 2.0)
            arch2.quadTo(cx + 13, cy - 4.0, cx + 18, cy + 2.0)
            p.drawPath(arch2)

            # Soft blush
            p.setPen(Qt.PenStyle.NoPen)
            for bx in [cx - 28, cx + 28]:
                b_grad = QRadialGradient(bx, cy + 2.5, 7.0)
                b_grad.setColorAt(0.0, QColor(255, 182, 193, 140))
                b_grad.setColorAt(1.0, QColor(255, 182, 193, 0))
                p.setBrush(b_grad)
                p.drawEllipse(QPointF(bx, cy + 2.5), 7.0, 4.5)

            # Waving paw pad
            paw_x = cx + 26 + math.sin(self._anim_time * 12.0) * 1.5
            paw_y = cy - 1.0 + math.cos(self._anim_time * 12.0) * 1.0
            p.setBrush(active_eye_color)
            p.drawEllipse(QRectF(paw_x - 2.8, paw_y + 0.2, 5.6, 4.2))
            p.drawEllipse(QRectF(paw_x - 3.8, paw_y - 3.0, 1.8, 2.2))
            p.drawEllipse(QRectF(paw_x - 1.5, paw_y - 4.2, 1.8, 2.2))
            p.drawEllipse(QRectF(paw_x + 1.0, paw_y - 4.2, 1.8, 2.2))
            p.drawEllipse(QRectF(paw_x + 3.2, paw_y - 3.0, 1.8, 2.2))

        elif cur_emotion == "surprised":
            # ── 3. SURPRISED / ALERT EMOTION: Large Dilated Anime Eyes (⊙ ⊙) ──
            eye_w = 11.0
            eye_h = 13.5
            p.setPen(Qt.PenStyle.NoPen)

            for ecx in [cx - 14, cx + 14]:
                # Glow halo
                glow = QRadialGradient(ecx, cy, 12.0)
                glow.setColorAt(0.0, QColor(active_eye_color.red(), active_eye_color.green(), active_eye_color.blue(), 100))
                glow.setColorAt(1.0, QColor(0, 0, 0, 0))
                p.setBrush(glow)
                p.drawEllipse(QPointF(ecx, cy), 12.0, 12.0)

                # Outer eye
                p.setBrush(active_eye_color)
                p.drawRoundedRect(QRectF(ecx - eye_w / 2.0, cy - eye_h / 2.0, eye_w, eye_h), eye_w / 2.0, eye_w / 2.0)

                # Pupil catchlights
                p.setBrush(QColor(255, 255, 255, 250))
                p.drawEllipse(QRectF(ecx - 3.2, cy - 4.5, 3.4, 3.4))
                p.drawEllipse(QRectF(ecx + 0.8, cy + 1.2, 1.8, 1.8))

        elif cur_emotion == "sad":
            # ── 4. SAD / POUTY EMOTION: Droopy Puppy Eyes (• ︵ •) with Teardrops ──
            eye_w = 7.0
            eye_h = 9.5
            quiver = math.sin(self._anim_time * 14.0) * 0.4
            p.setPen(Qt.PenStyle.NoPen)

            for ecx in [cx - 12, cx + 12]:
                ey = cy + 1.5 + quiver
                # Glow
                glow = QRadialGradient(ecx, ey, 9.0)
                glow.setColorAt(0.0, QColor(active_eye_color.red(), active_eye_color.green(), active_eye_color.blue(), 65))
                glow.setColorAt(1.0, QColor(0, 0, 0, 0))
                p.setBrush(glow)
                p.drawEllipse(QPointF(ecx, ey), 9.0, 9.0)

                # Main droopy eye
                p.setBrush(active_eye_color)
                p.drawRoundedRect(QRectF(ecx - eye_w / 2.0, ey - eye_h / 2.0, eye_w, eye_h), eye_w / 2.0, eye_w / 2.0)

                # Glossy wet puppy reflection
                p.setBrush(QColor(255, 255, 255, 240))
                p.drawEllipse(QRectF(ecx - 1.6, ey - 2.8, 2.2, 2.2))
                p.drawEllipse(QRectF(ecx + 0.2, ey + 1.2, 1.2, 1.2))

            # Sad mouth curve
            m_pen = QPen(active_eye_color, 1.6)
            m_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            p.setPen(m_pen)
            p.setBrush(Qt.BrushStyle.NoBrush)
            m_path = QPainterPath()
            m_path.moveTo(cx - 3.5, cy + 5.5 + quiver)
            m_path.quadTo(cx, cy + 3.8 + quiver, cx + 3.5, cy + 5.5 + quiver)
            p.drawPath(m_path)

        elif cur_emotion == "angry":
            # ── 5. ANGRY EMOTION: Fierce Slanted Eyes (ˋ ˊ) & Pulsing Anger Mark 💢 ──
            fiery_glow = QRadialGradient(cx, cy, 26.0)
            fiery_glow.setColorAt(0.0, QColor(239, 68, 68, 85))
            fiery_glow.setColorAt(1.0, QColor(239, 68, 68, 0))
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(fiery_glow)
            p.drawEllipse(QPointF(cx, cy), 26.0, 26.0)

            # Fierce slanted eye capsules
            brow_pen = QPen(QColor(255, 99, 71), 2.5)
            brow_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            p.setPen(brow_pen)
            p.setBrush(Qt.BrushStyle.NoBrush)

            # Left slanted brow/eye
            p.drawLine(QPointF(cx - 17, cy - 3.5), QPointF(cx - 7, cy + 1.5))
            # Right slanted brow/eye
            p.drawLine(QPointF(cx + 7, cy + 1.5), QPointF(cx + 17, cy - 3.5))

            # Inner intense glowing pupils
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor(255, 255, 255, 245))
            p.drawEllipse(QRectF(cx - 13.5, cy - 0.5, 3.2, 3.2))
            p.drawEllipse(QRectF(cx + 10.3, cy - 0.5, 3.2, 3.2))

            # Pulsing anger mark 💢 at upper right
            a_pulse = 0.85 + 0.35 * abs(math.sin(self._anim_time * 8.0))
            self._draw_vector_anger_mark(p, cx + 24, cy - 7, size=10.0 * a_pulse, alpha=1.0)

        elif self._pet_eye_state == "drowsy" or self._pet_eye_drowse_level > 0.6:
            # ── 6. SLEEPY / DROWSY IDLE: Eyelid Slits (─ ─) with zZ ──
            drowse_pen = QPen(active_eye_color, 2.2)
            drowse_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            p.setPen(drowse_pen)
            p.setBrush(Qt.BrushStyle.NoBrush)

            b_off = math.sin(self._anim_time * 2.2) * 1.0
            p.drawLine(QPointF(cx - 16, cy + b_off), QPointF(cx - 8, cy + b_off))
            p.drawLine(QPointF(cx + 8, cy + b_off), QPointF(cx + 16, cy + b_off))

            p.setFont(QFont("Segoe UI", 6.5, QFont.Weight.Bold))
            p.setPen(QColor(active_eye_color.red(), active_eye_color.green(), active_eye_color.blue(), int(150 + 80 * math.sin(self._anim_time * 3.0))))
            p.drawText(QRect(cx + 20, int(cy - 10 + b_off), 20, 14), Qt.AlignmentFlag.AlignLeft, "zZ")

        else:
            # ── 7. NORMAL CUTE LIVING EYES: Gaze Tracking Cursor across Desktop (• •) ──
            blink_mult = 1.0
            if self._pet_eye_blink_phase > 0.0:
                s = math.sin(self._pet_eye_blink_phase * math.pi / 2.0)
                blink_mult = max(0.12, 1.0 - s)

            # Responsive gaze tracking
            glance_x = self._pet_eye_glance_x + getattr(self, "_pet_eye_cursor_glance_x", 0.0)
            glance_y = self._pet_eye_glance_y + getattr(self, "_pet_eye_cursor_glance_y", 0.0)

            # When hovered: gentle friendly dilation and look at user
            is_hovered = self._is_hovered or (self._hovered_btn == "compact_pill")
            hover_dilate = 1.2 if is_hovered else 0.0

            alert = getattr(self, "_pet_eye_alert_phase", 0.0)
            base_w = 6.4 + alert * 1.0 + hover_dilate * 0.8
            base_h = 10.5 + alert * 1.5 + hover_dilate * 1.2

            left_cx = cx - 12 + glance_x
            right_cx = cx + 12 + glance_x

            wink_which = getattr(self, "_pet_eye_wink_which", "left")
            wink_phase = getattr(self, "_pet_eye_wink_phase", 0.0)
            is_winking = (wink_phase > 0.0) or (self._pet_eye_state == "winking")

            p.setPen(Qt.PenStyle.NoPen)

            for is_right, ecx in [(False, left_cx), (True, right_cx)]:
                is_this_winking = is_winking and ((wink_which == "right") if is_right else (wink_which == "left"))

                if is_this_winking:
                    w_pen = QPen(active_eye_color, 2.2)
                    w_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
                    p.setPen(w_pen)
                    p.setBrush(Qt.BrushStyle.NoBrush)
                    w_path = QPainterPath()
                    w_path.moveTo(ecx - 4, cy + 1.5)
                    w_path.quadTo(ecx, cy - 3.5, ecx + 4, cy + 1.5)
                    p.drawPath(w_path)
                    p.setPen(Qt.PenStyle.NoPen)
                else:
                    eye_h = max(1.8, base_h * blink_mult)
                    eye_y = cy - (eye_h / 2.0) + glance_y

                    # Glow halo
                    glow = QRadialGradient(ecx, cy + glance_y, 9.5)
                    glow.setColorAt(0.0, QColor(active_eye_color.red(), active_eye_color.green(), active_eye_color.blue(), 80))
                    glow.setColorAt(1.0, QColor(0, 0, 0, 0))
                    p.setBrush(glow)
                    p.drawEllipse(QPointF(ecx, cy + glance_y), 9.5, 9.5)

                    # Main eye capsule
                    p.setBrush(active_eye_color)
                    r_c = min(base_w / 2.0, eye_h / 2.0)
                    p.drawRoundedRect(QRectF(ecx - base_w / 2.0, eye_y, base_w, eye_h), r_c, r_c)

                    # Dynamic specular highlights that track glance offset
                    if blink_mult > 0.5:
                        p.setBrush(QColor(255, 255, 255, 245))
                        cat_off_x = max(-1.2, min(1.2, glance_x * 0.25))
                        cat_off_y = max(-1.0, min(1.0, glance_y * 0.25))
                        p.drawEllipse(QRectF(ecx - 1.8 + cat_off_x, eye_y + 1.6 + cat_off_y, 2.2, 2.2))
                        p.drawEllipse(QRectF(ecx + 0.6 + cat_off_x, eye_y + eye_h - 2.8 + cat_off_y, 1.1, 1.1))

        # ── 8. RENDER ACTIVE PARTICLES (Floating Hearts, Tears, Sparkles, Anger) ──
        for p_obj in getattr(self, "_pet_particles", []):
            p_type = p_obj.get("type", "")
            px = p_obj.get("x", cx)
            py = p_obj.get("y", cy)
            p_alpha = max(0.0, min(1.0, p_obj.get("life", 0.0) / max(0.01, p_obj.get("max_life", 1.0))))
            p_size = p_obj.get("size", 6.0)
            p_col = p_obj.get("color", QColor(255, 105, 180))

            if p_type == "heart":
                self._draw_vector_heart(p, px, py, p_size, p_col, p_alpha)
            elif p_type == "tear":
                self._draw_vector_tear(p, px, py, p_size, p_col, p_alpha)
            elif p_type == "sparkle":
                self._draw_vector_sparkle(p, px, py, p_size, p_col, p_alpha)
            elif p_type == "anger":
                self._draw_vector_anger_mark(p, px, py, p_size, p_alpha)

        p.restore()

    def _draw_compact_network(self, p: QPainter, theme: dict, w: int, h: int):
        p.save()
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        cx, cy = w // 2, h // 2

        # Left: Green download arrow
        p.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        p.setPen(QColor(52, 199, 89))
        p.drawText(QRectF(22, cy - 10, 14, 20), Qt.AlignmentFlag.AlignCenter, "↓")

        # Down speed
        p.setFont(QFont("Segoe UI", 8.5, QFont.Weight.Bold))
        p.setPen(QColor(255, 255, 255, 240))
        p.drawText(QRectF(38, cy - 10, 68, 20), Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, self._net_down_str)

        # Center dot
        p.setPen(QColor(255, 255, 255, 60))
        p.drawText(QRectF(cx - 6, cy - 10, 12, 20), Qt.AlignmentFlag.AlignCenter, "·")

        # Right: Cyan upload arrow
        p.setPen(QColor(0, 212, 255))
        p.drawText(QRectF(cx + 8, cy - 10, 14, 20), Qt.AlignmentFlag.AlignCenter, "↑")

        # Up speed
        p.setPen(QColor(255, 255, 255, 240))
        p.drawText(QRectF(cx + 24, cy - 10, 68, 20), Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, self._net_up_str)

        # Far right live pulsing indicator dot
        pulse = 0.5 + 0.5 * math.sin(self._anim_time * 5.0)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(52, 199, 89, int(150 + pulse * 105)))
        p.drawEllipse(QPointF(w - 22, cy), 3.0, 3.0)
        p.restore()

    def _draw_compact_weather(self, p: QPainter, theme: dict, w: int, h: int):
        p.save()
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        cx, cy = w // 2, h // 2

        weather = self._last_weather_info
        temp_str = f"{weather.temp_c}°C" if weather else "28°C"
        cond_str = weather.condition if weather else "Clear"
        icon_type = weather.icon_type if weather else "sun"

        # Left: Weather icon
        self._draw_vector_weather_icon(p, 26, cy, icon_type=icon_type, scale=0.8)

        # Middle: Temp & Condition
        p.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        p.setPen(QColor(255, 255, 255, 255))
        p.drawText(QRectF(44, cy - 10, 42, 20), Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, temp_str)

        p.setFont(QFont("Segoe UI", 8, QFont.Weight.Normal))
        p.setPen(QColor(180, 180, 190, 220))
        p.drawText(QRectF(90, cy - 10, w - 140, 20), Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, cond_str)

        # Right: Clock
        cur_t = time.strftime("%I:%M %p")
        p.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
        p.setPen(QColor(255, 255, 255, 200))
        p.drawText(QRectF(w - 74, cy - 10, 56, 20), Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight, cur_t)
        p.restore()

    def _draw_compact_vitals(self, p: QPainter, theme: dict, w: int, h: int):
        p.save()
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        cx, cy = w // 2, h // 2

        cpu_val = max(1.0, min(100.0, self._anim_cpu))
        ram_val = max(1.0, min(100.0, self._anim_ram))
        batt_pct = self._battery_percent

        # Left: CPU
        p.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
        p.setPen(QColor(52, 199, 89))
        p.drawText(QRectF(20, cy - 10, 54, 20), Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, f"CPU {cpu_val:.0f}%")

        # Mid: RAM
        p.setPen(QColor(0, 190, 255))
        p.drawText(QRectF(82, cy - 10, 56, 20), Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, f"RAM {ram_val:.0f}%")

        # Right: Battery
        p.setPen(QColor(255, 255, 255, 230))
        b_icon = "⚡" if self._battery_plugged else "🔋"
        p.drawText(QRectF(146, cy - 10, 68, 20), Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, f"{b_icon} {batt_pct}%")
        p.restore()

    def _draw_vector_heart(self, p: QPainter, cx: float, cy: float, size: float, color: QColor, alpha: float):
        p.save()
        path = QPainterPath()
        s = size / 10.0
        path.moveTo(cx, cy + 3.0 * s)
        path.cubicTo(cx - 5.5 * s, cy - 2.0 * s, cx - 5.5 * s, cy - 5.8 * s, cx, cy - 3.2 * s)
        path.cubicTo(cx + 5.5 * s, cy - 5.8 * s, cx + 5.5 * s, cy - 2.0 * s, cx, cy + 3.0 * s)
        p.setPen(Qt.PenStyle.NoPen)
        # Soft aura
        glow = QRadialGradient(cx, cy, size * 1.2)
        glow.setColorAt(0.0, QColor(color.red(), color.green(), color.blue(), int(75 * alpha)))
        glow.setColorAt(1.0, QColor(0, 0, 0, 0))
        p.setBrush(glow)
        p.drawEllipse(QPointF(cx, cy), size * 1.2, size * 1.2)
        p.setBrush(QColor(color.red(), color.green(), color.blue(), int(235 * alpha)))
        p.drawPath(path)
        p.restore()

    def _draw_vector_tear(self, p: QPainter, cx: float, cy: float, size: float, color: QColor, alpha: float):
        p.save()
        path = QPainterPath()
        s = size / 8.0
        path.moveTo(cx, cy - 4.0 * s)
        path.cubicTo(cx - 3.2 * s, cy, cx - 3.2 * s, cy + 3.2 * s, cx, cy + 3.8 * s)
        path.cubicTo(cx + 3.2 * s, cy + 3.2 * s, cx + 3.2 * s, cy, cx, cy - 4.0 * s)
        p.setPen(Qt.PenStyle.NoPen)
        glow = QRadialGradient(cx, cy, size * 1.2)
        glow.setColorAt(0.0, QColor(color.red(), color.green(), color.blue(), int(70 * alpha)))
        glow.setColorAt(1.0, QColor(0, 0, 0, 0))
        p.setBrush(glow)
        p.drawEllipse(QPointF(cx, cy), size * 1.2, size * 1.2)
        p.setBrush(QColor(color.red(), color.green(), color.blue(), int(220 * alpha)))
        p.drawPath(path)
        p.restore()

    def _draw_vector_sparkle(self, p: QPainter, cx: float, cy: float, size: float, color: QColor, alpha: float):
        p.save()
        path = QPainterPath()
        s = size / 2.0
        path.moveTo(cx, cy - s)
        path.quadTo(cx, cy, cx + s, cy)
        path.quadTo(cx, cy, cx, cy + s)
        path.quadTo(cx, cy, cx - s, cy)
        path.quadTo(cx, cy, cx, cy - s)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(color.red(), color.green(), color.blue(), int(235 * alpha)))
        p.drawPath(path)
        p.restore()

    def _draw_vector_anger_mark(self, p: QPainter, cx: float, cy: float, size: float, alpha: float):
        p.save()
        pen = QPen(QColor(239, 68, 68, int(235 * alpha)), 1.8)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        p.setPen(pen)
        p.setBrush(Qt.BrushStyle.NoBrush)
        s = size / 2.0
        p.drawLine(QPointF(cx - s, cy - s * 0.45), QPointF(cx + s, cy - s * 0.45))
        p.drawLine(QPointF(cx - s, cy + s * 0.45), QPointF(cx + s, cy + s * 0.45))
        p.drawLine(QPointF(cx - s * 0.45, cy - s), QPointF(cx - s * 0.45, cy + s))
        p.drawLine(QPointF(cx + s * 0.45, cy - s), QPointF(cx + s * 0.45, cy + s))
        p.restore()

        p.restore()

    def _paint_shelf(self, p: QPainter, theme: dict, w: int, h: int):
        """
        Sleek OriginOS / Dynamic Island Smart Shelf & File Drop Hub (Size: 420x192):
        - Universal top tab navigation tray with collapse indicator
        - AMOLED pure black background with subtle titanium border
        - Subheader row: '📁 Smart Shelf' + count badge pill + '📸 Snip' + '🗑️ Clear'
        - Empty Stash: elegant drop zone with breathing vector tray, title, subtitle,
          and 3 quick action pills: [📸 Grab Screen] [📋 Paste Clip] [📂 Browse File]
        - Populated Stash: 2x2 grid of modern frosted file chips with colorful extension squircle badges,
          elided filename, file size, hover remove button (✕), drag-out anytime to apps/Explorer.
        """
        self._shelf_item_rects.clear()

        # 0. Solid opaque AMOLED dark backdrop
        p.save()
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        is_flush_notch = self._is_flush_notch()
        bg_path = self._make_notch_path(w, h, self._corner_radius, is_flush_notch)
        p.fillPath(bg_path, QColor(0, 0, 0, 255))
        # Subtle titanium border
        p.setPen(QPen(QColor(255, 255, 255, 20), 1.0))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawPath(bg_path)
        p.restore()

        # 1. Universal Top Tab Header Tray
        self._paint_tab_headers(p, theme, w, active_tab="shelf")

        accent = getattr(self, "_dynamic_accent_color", QColor(240, 181, 166))
        total_files = len(self._shelf_files)

        # 2. Subheader Row (y = 29 to 49)
        # Left: Smart Shelf vector icon + Title
        p.save()
        self._draw_vector_shelf_icon(p, 25, 39, color=accent)
        p.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        p.setPen(QColor(255, 255, 255, 245))
        p.drawText(QRect(36, 29, 86, 20), Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, "Smart Shelf")

        # Stash item count badge pill
        badge_text = "Empty" if total_files == 0 else (f"{total_files} file" if total_files == 1 else f"{total_files} files")
        badge_w = 48.0 if total_files == 0 else 58.0
        badge_rect = QRectF(124.0, 30.0, badge_w, 18.0)
        p.setPen(QPen(QColor(255, 255, 255, 22), 1.0))
        p.setBrush(QColor(255, 255, 255, 12))
        p.drawRoundedRect(badge_rect, 9.0, 9.0)
        p.setFont(QFont("Segoe UI", 7.5, QFont.Weight.Medium))
        p.setPen(QColor(160, 175, 195, 220) if total_files == 0 else accent)
        p.drawText(badge_rect, Qt.AlignmentFlag.AlignCenter, badge_text)

        # Right Action Buttons: [📱 Phone QR], [📸 Snip] and [🗑️ Clear]
        # Phone Link QR button
        phone_btn_rect = QRectF(w - 232.0, 29.0, 78.0, 20.0)
        p_h = self._btn_hover_anim.get("shelf_phone_qr", 0.0)
        p_p = self._btn_press_anim.get("shelf_phone_qr", 0.0)
        p_scale = (1.0 + 0.04 * p_h) * (1.0 - 0.06 * p_p)

        p.save()
        p.translate(phone_btn_rect.center())
        p.scale(p_scale, p_scale)
        p.translate(-phone_btn_rect.center())
        p.setPen(QPen(QColor(0, 240, 255, int(80 + p_h * 100)), 1.0))
        p.setBrush(QColor(0, 240, 255, int(20 + p_h * 40)))
        p.drawRoundedRect(phone_btn_rect, 10.0, 10.0)
        p.setFont(QFont("Segoe UI", 7.5, QFont.Weight.Bold))
        p.setPen(QColor(0, 240, 255, int(220 + p_h * 35)))
        p.drawText(phone_btn_rect, Qt.AlignmentFlag.AlignCenter, "📱 Phone QR")
        p.restore()

        # Snip button
        snip_btn_rect = QRectF(w - 146.0, 29.0, 66.0, 20.0)
        s_h = self._btn_hover_anim.get("shelf_snip", 0.0)
        s_p = self._btn_press_anim.get("shelf_snip", 0.0)
        s_scale = (1.0 + 0.04 * s_h) * (1.0 - 0.06 * s_p)

        p.save()
        p.translate(snip_btn_rect.center())
        p.scale(s_scale, s_scale)
        p.translate(-snip_btn_rect.center())
        p.setPen(QPen(QColor(255, 255, 255, int(26 + s_h * 50)), 1.0))
        p.setBrush(QColor(255, 255, 255, int(12 + s_h * 30)))
        p.drawRoundedRect(snip_btn_rect, 10.0, 10.0)
        self._draw_vector_camera(p, int(snip_btn_rect.left() + 14), int(snip_btn_rect.center().y()), color=QColor(255, 255, 255, int(200 + s_h * 55)), scale=0.85)
        p.setFont(QFont("Segoe UI", 7.5, QFont.Weight.DemiBold))
        p.setPen(QColor(255, 255, 255, int(200 + s_h * 55)))
        p.drawText(QRectF(snip_btn_rect.left() + 24, snip_btn_rect.top(), snip_btn_rect.width() - 24, snip_btn_rect.height()), Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, "Snip")
        p.restore()

        # Clear button
        clear_btn_rect = QRectF(w - 74.0, 29.0, 56.0, 20.0)
        c_h = self._btn_hover_anim.get("shelf_clear_all", 0.0)
        c_p = self._btn_press_anim.get("shelf_clear_all", 0.0)
        c_scale = (1.0 + 0.04 * c_h) * (1.0 - 0.06 * c_p)

        p.save()
        p.translate(clear_btn_rect.center())
        p.scale(c_scale, c_scale)
        p.translate(-clear_btn_rect.center())
        if total_files > 0:
            p.setPen(QPen(QColor(255, 59, 48, int(80 + c_h * 100)), 1.0))
            p.setBrush(QColor(255, 59, 48, int(35 + c_h * 55)))
            p.drawRoundedRect(clear_btn_rect, 10.0, 10.0)
            self._draw_vector_trash(p, int(clear_btn_rect.left() + 13), int(clear_btn_rect.center().y()), color=QColor(255, 120, 120, 240))
            p.setFont(QFont("Segoe UI", 7.5, QFont.Weight.Bold))
            p.setPen(QColor(255, 140, 140, 240))
            p.drawText(QRectF(clear_btn_rect.left() + 22, clear_btn_rect.top(), clear_btn_rect.width() - 22, clear_btn_rect.height()), Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, "Clear")
        else:
            p.setPen(QPen(QColor(255, 255, 255, 16), 1.0))
            p.setBrush(QColor(255, 255, 255, 8))
            p.drawRoundedRect(clear_btn_rect, 10.0, 10.0)
            self._draw_vector_trash(p, int(clear_btn_rect.left() + 13), int(clear_btn_rect.center().y()), color=QColor(255, 255, 255, 60))
            p.setFont(QFont("Segoe UI", 7.5, QFont.Weight.Normal))
            p.setPen(QColor(255, 255, 255, 70))
            p.drawText(QRectF(clear_btn_rect.left() + 22, clear_btn_rect.top(), clear_btn_rect.width() - 22, clear_btn_rect.height()), Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, "Clear")
        p.restore()
        p.restore()

        # 3. Main Hub / Drop Area (y = 54 to 180)
        dz_x = 16.0
        dz_y = 54.0
        dz_w = float(w - 32)
        dz_h = 126.0
        dz_rect = QRectF(dz_x, dz_y, dz_w, dz_h)

        if total_files == 0:
            # ── Empty Stash Hero Canvas ──
            p.save()
            if self._shelf_is_drag_over:
                dash_pen = QPen(accent, 1.8, Qt.PenStyle.DashLine)
                dash_pen.setDashPattern([5, 4])
                p.setPen(dash_pen)
                p.setBrush(QColor(accent.red(), accent.green(), accent.blue(), 26))
            else:
                dash_pen = QPen(QColor(255, 255, 255, 28), 1.2, Qt.PenStyle.DashLine)
                dash_pen.setDashPattern([6, 5])
                p.setPen(dash_pen)
                p.setBrush(QColor(255, 255, 255, 8))
            p.drawRoundedRect(dz_rect, 14.0, 14.0)

            # Floating Drop Tray Icon with smooth breathing bounce
            bounce = math.sin(self._anim_time * 3.0) * 2.2
            tray_cy = dz_y + 34.0 + bounce
            self._draw_vector_shelf_drop_tray(p, int(w / 2.0), int(tray_cy), scale=1.05, color=accent if self._shelf_is_drag_over else QColor(255, 255, 255, 220))

            # Title & Subtitle
            p.setFont(QFont("Segoe UI", 9.2, QFont.Weight.DemiBold))
            p.setPen(QColor(255, 255, 255, 245))
            p.drawText(QRectF(dz_x, dz_y + 50.0, dz_w, 20.0), Qt.AlignmentFlag.AlignCenter, "Drop files or images here to stash")

            p.setFont(QFont("Segoe UI", 7.5, QFont.Weight.Normal))
            p.setPen(QColor(148, 163, 184, 200))
            p.drawText(QRectF(dz_x, dz_y + 68.0, dz_w, 16.0), Qt.AlignmentFlag.AlignCenter, "Temporary desktop hold · Drag out anytime to apps or chats")

            # 4 Quick Action Helper Pills
            quick_btns = [
                ("shelf_phone_qr", "📱 Connect Phone"),
                ("shelf_snip", "📸 Grab Screen"),
                ("shelf_paste", "📋 Paste Clip"),
                ("shelf_browse", "📂 Browse File"),
            ]
            q_w = 88.0
            q_h = 24.0
            q_gap = 8.0
            q_start_x = dz_x + (dz_w - (4 * q_w + 3 * q_gap)) / 2.0
            q_y = dz_y + 92.0

            for q_idx, (q_key, q_label) in enumerate(quick_btns):
                qx = q_start_x + q_idx * (q_w + q_gap)
                q_rect = QRectF(qx, q_y, q_w, q_h)
                qh_val = self._btn_hover_anim.get(q_key, 0.0)
                qp_val = self._btn_press_anim.get(q_key, 0.0)
                q_scale = (1.0 + 0.04 * qh_val) * (1.0 - 0.06 * qp_val)

                p.save()
                p.translate(q_rect.center())
                p.scale(q_scale, q_scale)
                p.translate(-q_rect.center())

                p.setPen(QPen(QColor(255, 255, 255, int(26 + qh_val * 60)), 1.0))
                p.setBrush(QColor(255, 255, 255, int(14 + qh_val * 35)))
                p.drawRoundedRect(q_rect, 12.0, 12.0)

                p.setFont(QFont("Segoe UI", 7.8, QFont.Weight.DemiBold))
                p.setPen(QColor(255, 255, 255, int(200 + qh_val * 55)))
                p.drawText(q_rect, Qt.AlignmentFlag.AlignCenter, q_label)
                p.restore()

            p.restore()

        else:
            # ── Populated Stash: 2x2 Grid File Chips ──
            page_size = 4
            max_pages = max(1, math.ceil(total_files / float(page_size)))
            cur_page = min(max_pages - 1, max(0, self._shelf_page))
            self._shelf_page = cur_page

            start_idx = cur_page * page_size
            page_files = self._shelf_files[start_idx : start_idx + page_size]

            col_w = int((dz_w - 12.0) / 2.0)
            row_h = 49
            gap_x = 12
            gap_y = 8

            for i, f_info in enumerate(page_files):
                global_idx = start_idx + i
                col = i % 2
                row = i // 2
                item_x = int(dz_x + col * (col_w + gap_x))
                item_y = int(dz_y + 4 + row * (row_h + gap_y))
                card_rect = QRect(item_x, item_y, col_w, row_h)
                self._shelf_item_rects[global_idx] = card_rect

                h_val = self._btn_hover_anim.get(f"shelf_file_{global_idx}", 0.0)

                p.save()
                p.setPen(QPen(QColor(255, 255, 255, int(28 + h_val * 65)), 1.0))
                p.setBrush(QColor(255, 255, 255, int(12 + h_val * 28)))
                p.drawRoundedRect(QRectF(card_rect), 9.0, 9.0)

                ext = f_info.get("ext", "FILE") or "FILE"
                badge_rect = QRect(item_x + 7, item_y + 7, 35, 35)
                # Colorful vibrant squircle badge
                if ext in ["PNG", "JPG", "JPEG", "GIF", "SVG", "WEBP", "BMP"]:
                    badge_bg = QColor(10, 132, 255, 200)
                elif ext in ["PDF", "DOC", "DOCX", "TXT", "MD", "CSV", "XLSX"]:
                    badge_bg = QColor(255, 69, 58, 200)
                elif ext in ["PY", "JS", "TS", "HTML", "CSS", "JSON", "SH", "CPP", "RS", "JAVA"]:
                    badge_bg = QColor(48, 209, 88, 200)
                elif ext in ["ZIP", "RAR", "7Z", "TAR", "GZ"]:
                    badge_bg = QColor(255, 159, 10, 200)
                elif ext in ["MP3", "WAV", "FLAC", "MP4", "MKV"]:
                    badge_bg = QColor(191, 90, 242, 200)
                else:
                    badge_bg = QColor(100, 116, 139, 200)

                p.setPen(Qt.PenStyle.NoPen)
                p.setBrush(badge_bg)
                p.drawRoundedRect(QRectF(badge_rect), 7.0, 7.0)

                p.setFont(QFont("Segoe UI", 7, QFont.Weight.Bold))
                p.setPen(QColor(255, 255, 255, 245))
                p.drawText(badge_rect, Qt.AlignmentFlag.AlignCenter, ext[:4])

                # Filename
                name = f_info.get("name", "Unknown File")
                p.setFont(QFont("Segoe UI", 8.2, QFont.Weight.DemiBold))
                p.setPen(QColor(255, 255, 255, 240))
                fm = p.fontMetrics()
                text_w = col_w - 68
                elided_name = fm.elidedText(name, Qt.TextElideMode.ElideMiddle, text_w)
                p.drawText(QRect(item_x + 48, item_y + 7, text_w, 18), Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, elided_name)

                # Size & Type string
                def _fmt_size(sz_bytes: int) -> str:
                    if sz_bytes < 1024:
                        return f"{sz_bytes} B"
                    elif sz_bytes < 1024 * 1024:
                        return f"{sz_bytes / 1024:.1f} KB"
                    else:
                        return f"{sz_bytes / (1024 * 1024):.1f} MB"

                sz_str = f"{_fmt_size(f_info.get('size', 0))} · {ext}"
                p.setFont(QFont("Segoe UI", 7.0, QFont.Weight.Normal))
                p.setPen(QColor(150, 165, 185, 200))
                p.drawText(QRect(item_x + 48, item_y + 26, text_w, 16), Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, sz_str)

                # Delete (X) button
                del_rect = QRect(item_x + col_w - 20, item_y + 5, 15, 15)
                del_h = self._btn_hover_anim.get(f"shelf_del_{global_idx}", 0.0)
                if del_h > 0.05:
                    p.setPen(Qt.PenStyle.NoPen)
                    p.setBrush(QColor(255, 59, 48, int(del_h * 200)))
                    p.drawEllipse(QRectF(del_rect))
                    p.setPen(QPen(QColor(255, 255, 255, 255), 1.3, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
                else:
                    p.setPen(QPen(QColor(255, 255, 255, 110), 1.2, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
                p.drawLine(del_rect.left() + 4, del_rect.top() + 4, del_rect.right() - 4, del_rect.bottom() - 4)
                p.drawLine(del_rect.right() - 4, del_rect.top() + 4, del_rect.left() + 4, del_rect.bottom() - 4)
                p.restore()

            # Bottom Bar (y = 170): Pagination dots + Add file button
            dots_y = int(dz_y + dz_h - 10)
            dots_cx = int(w / 2)
            dot_spacing = 14
            start_dot_x = dots_cx - ((max_pages - 1) * dot_spacing) // 2
            for p_idx in range(max_pages):
                dot_x = start_dot_x + p_idx * dot_spacing
                p.setPen(Qt.PenStyle.NoPen)
                if p_idx == cur_page:
                    p.setBrush(QColor(255, 255, 255, 230))
                    p.drawRoundedRect(QRectF(dot_x - 5, dots_y - 2, 10, 4), 2, 2)
                else:
                    p.setBrush(QColor(255, 255, 255, 70))
                    p.drawEllipse(QPointF(dot_x, dots_y), 2.2, 2.2)

            # "+ Browse" Pill Button at bottom right
            add_rect = QRectF(w - 86.0, dz_y + dz_h - 18.0, 70.0, 18.0)
            ab_h = self._btn_hover_anim.get("shelf_browse", 0.0)
            p.save()
            p.setPen(QPen(QColor(255, 255, 255, int(24 + ab_h * 60)), 1.0))
            p.setBrush(QColor(255, 255, 255, int(10 + ab_h * 30)))
            p.drawRoundedRect(add_rect, 9.0, 9.0)
            p.setFont(QFont("Segoe UI", 7.2, QFont.Weight.DemiBold))
            p.setPen(QColor(255, 255, 255, int(180 + ab_h * 75)))
            p.drawText(add_rect, Qt.AlignmentFlag.AlignCenter, "+ Browse")
            p.restore()

    def _paint_music(self, p: QPainter, theme: dict, w: int, h: int):
        """
        Music Player Card matching Screenshots 1 & 3:
        Screenshot 1: Sleek dark player with 68x68 album art, app badge (Brave/Spotify/etc.),
                      clean typography, animated peach visualizer bars, progress bar with -rem:ss,
                      and << || >> and lyrics icon.
        Screenshot 3: Synced Lyrics View with small top album art, Title • Artist,
                      3-line synced lyrics (faded previous, large bold white active, faded next),
                      progress bar, and highlighted lyrics icon button.
        Right edge: Vertical carousel page dots in both views.
        """
        p.save()
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        p.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)

        # Check if in Cinema Theater Mode (Width >= 600px for two-column responsive layout)
        if (getattr(self, "_is_theater_mode", False) and w >= 600) or w >= 680 or h >= 300:
            self._paint_music_theater(p, theme, w, h)
            p.restore()
            return

        # 0. Perfect Notch Path & Vivid Cover-Art Background Sync
        is_flush_notch = self._is_flush_notch()
        bg_path = self._make_notch_path(w, h, self._corner_radius, is_flush_notch)

        # Immediate cover-art extraction on first paint frame if not yet extracted
        thumb_bytes = self._last_media_info.thumbnail_bytes if self._last_media_info else None
        if thumb_bytes and (getattr(self, "_extracted_art_color", None) is None or getattr(self, "_last_thumb_len", 0) != len(thumb_bytes)):
            self._last_thumb_len = len(thumb_bytes)
            ext = self._extract_artwork_color(thumb_bytes)
            if ext and ext.isValid():
                self._extracted_art_color = ext
                self._dynamic_accent_color = ext

        is_playing = self._is_genuine_music_playing()
        accent = getattr(self, "_dynamic_accent_color", QColor(240, 181, 166))
        art_r, art_g, art_b = accent.red(), accent.green(), accent.blue()

        p.save()
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(self._get_background_color())
        p.drawPath(bg_path)
        p.restore()
        self._draw_edge_beat_glow(p, w, h, self._corner_radius, is_flush_notch)

        # 1. Top Bar Navigation (Tabs at top right, Collapse chevron at top left)
        self._paint_tab_headers(p, theme, w, active_tab="music")

        self._lyrics_item_rects.clear()

        # Track metadata
        title = "No Music Playing"
        artist = "Play on Spotify, Brave, YouTube..."
        album = ""
        app_name = "Media"
        thumb_bytes = None
        is_playing = False

        if self._last_media_info and self._last_media_info.has_media:
            title = self._last_media_info.title or title
            artist = self._last_media_info.artist or artist
            album = getattr(self._last_media_info, "album", "") or ""
            app_name = getattr(self._last_media_info, "app_name", "Media") or "Media"
            thumb_bytes = self._last_media_info.thumbnail_bytes
            is_playing = bool(self._last_media_info.is_playing)

        # Time formatting
        def _fmt_time(sec: float) -> str:
            if sec < 0:
                return "0:00"
            s = int(round(sec))
            m, s = divmod(s, 60)
            return f"{m}:{s:02d}"

        cur_time_str = _fmt_time(self._playback_pos_sec)
        rem_sec = max(0.0, self._playback_dur_sec - self._playback_pos_sec)
        rem_time_str = f"-{_fmt_time(rem_sec)}" if self._playback_dur_sec > 0 else "--:--"
        ratio = min(1.0, max(0.0, self._playback_pos_sec / max(1.0, self._playback_dur_sec))) if self._playback_dur_sec > 0 else 0.0

        peach_color = self._get_active_accent_color()

        # Helper for tactile button press / hover anim
        def _btn_anim(name: str, base_r: float, base_alpha: int = 16):
            h_v = self._btn_hover_anim.get(name, 0.0)
            p_v = self._btn_press_anim.get(name, 0.0)
            r = base_r * (1.0 - 0.08 * p_v)
            alpha = min(255, int(base_alpha + h_v * 35))
            return r, QColor(255, 255, 255, alpha), h_v, p_v

        # ======================================================================
        # VIEW 1: SYNCHRONIZED LYRICS VIEW (Screenshot 3)
        # ======================================================================
        if getattr(self, "_music_show_lyrics", False):
            # 1. Mini Now-Playing Header Bar (y: 34)
            mini_art_rect = QRect(22, 34, 26, 26)
            mini_art_path = QPainterPath()
            mini_art_path.addEllipse(QRectF(mini_art_rect))

            has_art = False
            if thumb_bytes:
                pix = self._get_scaled_album_art(thumb_bytes, 26)
                if pix and not pix.isNull():
                    p.save()
                    p.setClipPath(mini_art_path)
                    p.drawPixmap(mini_art_rect, pix)
                    p.restore()
                    has_art = True

            if not has_art:
                art_grad = QLinearGradient(22, 34, 48, 60)
                art_grad.setColorAt(0.0, QColor(255, 59, 92))
                art_grad.setColorAt(1.0, QColor(220, 38, 127))
                p.fillPath(mini_art_path, art_grad)
                self._draw_vector_note(p, 35, 47, size=11, color=QColor(255, 255, 255))

            p.strokePath(mini_art_path, QPen(QColor(255, 255, 255, 35), 1.0))

            # Header Track Title & Artist (single line: Title • Artist)
            hdr_rect = QRectF(56, 34, w - 85, 26)
            hdr_font = QFont(["Segoe UI", "Nirmala UI", "sans-serif"], 9.5, QFont.Weight.Bold)
            hdr_text = f"{title}  ·  {artist}"
            self._draw_smooth_marquee(p, hdr_rect, hdr_text, hdr_font, QColor(255, 255, 255, 240), self._music_ticker_x, gap=36.0, fade_width=14.0)

            # 2. Synchronized Lyrics Area (y: 64 to 118)
            active_idx = self._lyrics_active_idx
            total_lines = len(self._lyrics_lines) if self._lyrics_lines else 0

            # Line 1: Previous line (faded)
            prev_text = ""
            if 0 < active_idx < total_lines:
                prev_text = self._lyrics_lines[active_idx - 1][1]
            p.setFont(QFont(["Segoe UI", "Nirmala UI", "sans-serif"], 9.5, QFont.Weight.Normal))
            p.setPen(QColor(165, 155, 155, 120))
            p.drawText(QRectF(20, 62, w - 40, 18), Qt.AlignmentFlag.AlignCenter, prev_text)

            # Line 2: Active lyric line (large, bold, pure white with blooming glow)
            cur_text = "♪ Live synchronized lyrics ♪"
            if total_lines > 0 and 0 <= active_idx < total_lines:
                cur_text = self._lyrics_lines[active_idx][1]
            elif not is_playing:
                cur_text = "♪ Paused ♪"

            p.setFont(QFont(["Segoe UI", "Nirmala UI", "sans-serif"], 13.5, QFont.Weight.Bold))
            if is_playing and cur_text and cur_text != "♪":
                p.setPen(QColor(art_r, art_g, art_b, 60))
                for ox, oy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                    p.drawText(QRectF(20 + ox, 82 + oy, w - 40, 24), Qt.AlignmentFlag.AlignCenter, cur_text)
            p.setPen(QColor(255, 255, 255, 255))
            p.drawText(QRectF(20, 82, w - 40, 24), Qt.AlignmentFlag.AlignCenter, cur_text)

            # Line 3: Next line (faded)
            next_text = ""
            if total_lines > 0 and active_idx + 1 < total_lines:
                next_text = self._lyrics_lines[active_idx + 1][1]
            else:
                next_text = "♪"
            p.setFont(QFont(["Segoe UI", "Nirmala UI", "sans-serif"], 9.0, QFont.Weight.Normal))
            p.setPen(QColor(165, 155, 155, 110))
            p.drawText(QRectF(20, 108, w - 40, 16), Qt.AlignmentFlag.AlignCenter, next_text)

            bar_y = 130
            ctrl_y = 168

        # ======================================================================
        # VIEW 2: STANDARD MUSIC PLAYER (Screenshot 1)
        # ======================================================================
        else:
            # 1. Left: 64x64 Album Artwork Squircle with Drop Shadow
            art_x = 20
            art_y = 36
            art_size = 64
            art_rect = QRect(art_x, art_y, art_size, art_size)
            art_path = QPainterPath()
            art_path.addRoundedRect(QRectF(art_rect), 14.0, 14.0)

            # Soft natural dark shadow underneath album art
            p.save()
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor(0, 0, 0, 80))
            p.drawRoundedRect(QRectF(art_x + 1, art_y + 3, art_size, art_size), 14.0, 14.0)
            p.restore()

            has_art = False
            if thumb_bytes:
                pix = self._get_scaled_album_art(thumb_bytes, art_size)
                if pix and not pix.isNull():
                    p.save()
                    p.setClipPath(art_path)
                    p.drawPixmap(art_rect, pix)
                    p.restore()
                    has_art = True

            if not has_art:
                art_grad = QLinearGradient(art_x, art_y, art_x + art_size, art_y + art_size)
                art_grad.setColorAt(0.0, QColor(255, 75, 95))
                art_grad.setColorAt(0.5, QColor(255, 115, 135))
                art_grad.setColorAt(1.0, QColor(210, 48, 120))
                p.fillPath(art_path, art_grad)
                self._draw_vector_note(p, art_x + art_size // 2, art_y + art_size // 2, size=18, color=QColor(255, 255, 255))

            p.strokePath(art_path, QPen(QColor(255, 255, 255, 30), 1.0))

            # 2. Bottom-Right App Source Badge (e.g. Brave, Spotify, Chrome)
            badge_cx = art_x + art_size - 7.0
            badge_cy = art_y + art_size - 7.0
            self._draw_app_badge(p, badge_cx, badge_cy, r=10.0, app_name=app_name)

            # 3. Track Metadata Block
            meta_x = art_x + art_size + 14
            meta_w = w - meta_x - 24

            # Line 1: Title (Bold White)
            title_rect = QRectF(meta_x, 34, meta_w, 20)
            title_font = QFont(["Segoe UI", "Nirmala UI", "sans-serif"], 11.5, QFont.Weight.Bold)
            self._draw_smooth_marquee(p, title_rect, title, title_font, QColor(255, 255, 255), self._music_ticker_x, gap=40.0, fade_width=14.0)

            # Line 2: Artist (Soft Peach / Coral Muted)
            p.setFont(QFont(["Segoe UI", "Nirmala UI", "sans-serif"], 9.0, QFont.Weight.Medium))
            p.setPen(QColor(204, 165, 154))
            fm_a = p.fontMetrics()
            p.drawText(QRect(meta_x, 56, meta_w, 18), Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, fm_a.elidedText(artist, Qt.TextElideMode.ElideRight, meta_w))

            # Line 3: Album (Dim muted text)
            display_album = album if album else "Single Track"
            p.setFont(QFont(["Segoe UI", "Nirmala UI", "sans-serif"], 8.0, QFont.Weight.Normal))
            p.setPen(QColor(155, 145, 145, 200))
            fm_al = p.fontMetrics()
            p.drawText(QRect(meta_x, 74, meta_w, 16), Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, fm_al.elidedText(display_album, Qt.TextElideMode.ElideRight, meta_w))

            # Line 4: Playing from App
            p.setFont(QFont(["Segoe UI", "sans-serif"], 7.5, QFont.Weight.Normal))
            p.setPen(QColor(135, 125, 125, 180))
            p.drawText(QRect(meta_x, 90, meta_w, 15), Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, f"Playing from {app_name}")

            bar_y = 124
            ctrl_y = 164

        # ======================================================================
        # SHARED: INTERACTIVE LIVE PROGRESS / SCRUB BAR
        # ======================================================================
        # Left Elapsed Timestamp
        p.setFont(QFont(["Segoe UI", "sans-serif"], 8.5, QFont.Weight.Normal))
        p.setPen(QColor(170, 160, 160))
        p.drawText(QRect(16, bar_y - 8, 44, 16), Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, cur_time_str)

        # Track bar
        track_x = 62.0
        track_w = float(w - 134)
        track_h = 3.5

        # 1. Unplayed background track
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(255, 255, 255, 28))
        p.drawRoundedRect(QRectF(track_x, bar_y - track_h / 2.0, track_w, track_h), track_h / 2.0, track_h / 2.0)

        # 2. Played portion with Fluid Animated Squiggly Sound Wave (Android 13 / Apple Music style)
        fill_w = max(3.5, track_w * ratio)
        thumb_x = track_x + fill_w

        if is_playing and fill_w > 10.0:
            wave_path = QPainterPath()
            wave_path.moveTo(track_x, bar_y)
            wave_phase = self._anim_time * 6.5
            step_px = 1.5
            cur_x = track_x
            w_style = getattr(self, "_wave_style", "sine")
            while cur_x <= thumb_x:
                prog = (cur_x - track_x) / fill_w
                envelope = math.sin(prog * math.pi)

                if w_style == "harmonic":
                    # Style 2: Dual-frequency harmonic liquid ribbon
                    w1 = math.sin((cur_x - track_x) * 0.20 - wave_phase)
                    w2 = math.sin((cur_x - track_x) * 0.45 + wave_phase * 0.65)
                    amp = 2.7 * envelope * (0.65 * w1 + 0.35 * w2)
                    wave_y = bar_y + amp
                elif w_style == "cyber":
                    # Style 3: Futuristic segmented cyber pulse wave
                    raw_s = math.sin((cur_x - track_x) * 0.28 - wave_phase)
                    sign_val = 1.0 if raw_s > 0.08 else (-1.0 if raw_s < -0.08 else 0.0)
                    amp = 2.8 * envelope * sign_val
                    wave_y = bar_y + amp
                else:
                    # Style 1: Android 13 smooth tapered sine wave
                    amp = 2.4 * envelope
                    wave_y = bar_y + amp * math.sin((cur_x - track_x) * 0.22 - wave_phase)

                wave_path.lineTo(cur_x, wave_y)
                cur_x += step_px
            wave_path.lineTo(thumb_x, bar_y)

            # Subtle glowing aura underneath wave
            p.setPen(QPen(QColor(peach_color.red(), peach_color.green(), peach_color.blue(), 55), 5.5, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawPath(wave_path)

            # Main wave stroke
            p.setPen(QPen(peach_color, 3.2, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
            p.drawPath(wave_path)
        else:
            # Paused or short progress: clean flat bar
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(peach_color)
            p.drawRoundedRect(QRectF(track_x, bar_y - track_h / 2.0, fill_w, track_h), track_h / 2.0, track_h / 2.0)

        # 3. Scrubber thumb circle knob
        thumb_r = 5.2
        p.setPen(Qt.PenStyle.NoPen)
        # Drop shadow
        p.setBrush(QColor(0, 0, 0, 80))
        p.drawEllipse(QPointF(thumb_x, bar_y + 1.0), thumb_r, thumb_r)
        # White thumb knob
        p.setBrush(QColor(255, 255, 255))
        p.drawEllipse(QPointF(thumb_x, bar_y), thumb_r, thumb_r)
        # Dynamic inner dot
        p.setBrush(peach_color)
        p.drawEllipse(QPointF(thumb_x, bar_y), 2.2, 2.2)

        # Right Remaining Timestamp (-m:ss)
        p.setPen(QColor(170, 160, 160))
        p.drawText(QRect(w - 70, bar_y - 8, 54, 16), Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight, rem_time_str)

        # ======================================================================
        # SHARED: BOTTOM PLAYBACK CONTROLS ROW: <<  ||  >>  and  💬
        # ======================================================================
        cx = w // 2

        # 1. Rewind Button << at (cx - 48, ctrl_y)
        r, col, h_val, _ = _btn_anim("prev", 18.0, 16)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(col)
        p.drawEllipse(QPointF(cx - 48, ctrl_y), r, r)

        p.setBrush(peach_color)
        p1 = QPainterPath()
        p1.moveTo(cx - 44, ctrl_y - 5.5)
        p1.lineTo(cx - 44, ctrl_y + 5.5)
        p1.lineTo(cx - 51, ctrl_y)
        p1.closeSubpath()
        p.drawPath(p1)

        p2 = QPainterPath()
        p2.moveTo(cx - 49, ctrl_y - 5.5)
        p2.lineTo(cx - 49, ctrl_y + 5.5)
        p2.lineTo(cx - 56, ctrl_y)
        p2.closeSubpath()
        p.drawPath(p2)

        # 2. Play / Pause Center Disc || or ▶ at (cx, ctrl_y)
        r, col, h_val, _ = _btn_anim("play", 23.0, 24)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(col)
        p.drawEllipse(QPointF(cx, ctrl_y), r, r)

        p.setBrush(peach_color)
        if is_playing:
            # Two vertical pause bars with rounded ends
            p.drawRoundedRect(QRectF(cx - 5.5, ctrl_y - 7.0, 3.4, 14.0), 1.2, 1.2)
            p.drawRoundedRect(QRectF(cx + 2.0, ctrl_y - 7.0, 3.4, 14.0), 1.2, 1.2)
        else:
            # Play triangle
            play_p = QPainterPath()
            play_p.moveTo(cx - 4.0, ctrl_y - 7.5)
            play_p.lineTo(cx - 4.0, ctrl_y + 7.5)
            play_p.lineTo(cx + 6.5, ctrl_y)
            play_p.closeSubpath()
            p.drawPath(play_p)

        # 3. Next Track Button >> at (cx + 48, ctrl_y)
        r, col, h_val, _ = _btn_anim("next", 18.0, 16)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(col)
        p.drawEllipse(QPointF(cx + 48, ctrl_y), r, r)

        p.setBrush(peach_color)
        n1 = QPainterPath()
        n1.moveTo(cx + 44, ctrl_y - 5.5)
        n1.lineTo(cx + 44, ctrl_y + 5.5)
        n1.lineTo(cx + 51, ctrl_y)
        n1.closeSubpath()
        p.drawPath(n1)

        n2 = QPainterPath()
        n2.moveTo(cx + 49, ctrl_y - 5.5)
        n2.lineTo(cx + 49, ctrl_y + 5.5)
        n2.lineTo(cx + 56, ctrl_y)
        n2.closeSubpath()
        p.drawPath(n2)

        # 4. Lyrics Toggle Button 💬 at (w - 56, ctrl_y)
        is_lyrics_on = getattr(self, "_music_show_lyrics", False)
        base_a = 55 if is_lyrics_on else 16
        r, col, h_val, _ = _btn_anim("lyrics_toggle", 18.0, base_a)

        p.setPen(Qt.PenStyle.NoPen)
        if is_lyrics_on:
            p.setBrush(QColor(peach_color.red(), peach_color.green(), peach_color.blue(), int(45 + h_val * 40)))
            p.drawEllipse(QPointF(w - 56, ctrl_y), r, r)
            p.setPen(QPen(QColor(peach_color.red(), peach_color.green(), peach_color.blue(), 130), 1.2))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawEllipse(QPointF(w - 56, ctrl_y), r, r)
        else:
            p.setBrush(col)
            p.drawEllipse(QPointF(w - 56, ctrl_y), r, r)

        # Speech bubble icon
        self._draw_lyrics_icon(p, w - 56, ctrl_y, r=r, color=peach_color, is_active=is_lyrics_on)

        # Tactile bottom pull handle (shows draggable edge affordance to expand)
        p.save()
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(255, 255, 255, 65))
        p.drawRoundedRect(QRectF(w // 2 - 20, h - 5.5, 40, 2.8), 1.4, 1.4)
        p.restore()

        # ======================================================================
        # VERTICAL PAGE CAROUSEL DOTS (Right Edge, Dot 0 = Music, 5 total pages)
        # ======================================================================
        self._draw_vertical_page_dots(p, w - 12, h / 2.0, active_page=0, total_pages=5)

        p.restore()

    def _paint_music_theater(self, p: QPainter, theme: dict, w: int, h: int):
        """
        Responsive Full-Screen / Device-Width Cinema Theater Real Music Player.
        Two-column responsive layout:
        - Left column: Large hero album art squircle with ambient glow, bold song title marquee,
          artist subtitle, format badge, animated wave progress scrubber with timestamps,
          and tactile playback hub (wave switcher, prev, play/pause disc, next, lyrics toggle).
        - Right column: Frosted glass panel with live synchronized scrolling karaoke lyrics (active line bold white + glow,
          click any line to seek), or 32-band audio spectrum visualizer if lyrics not present.
        - Bottom pull handle & corner resize grip indicators.
        """
        is_flush_notch = self._is_flush_notch()
        bg_path = self._make_notch_path(w, h, self._corner_radius, is_flush_notch)

        # 0. Artwork extraction & dynamic accent colors
        thumb_bytes = self._last_media_info.thumbnail_bytes if self._last_media_info else None
        if thumb_bytes and (getattr(self, "_extracted_art_color", None) is None or getattr(self, "_last_thumb_len", 0) != len(thumb_bytes)):
            self._last_thumb_len = len(thumb_bytes)
            ext = self._extract_artwork_color(thumb_bytes)
            if ext and ext.isValid():
                self._extracted_art_color = ext
                self._dynamic_accent_color = ext

        is_playing = self._is_genuine_music_playing()
        accent = getattr(self, "_dynamic_accent_color", QColor(240, 181, 166))
        art_r, art_g, art_b = accent.red(), accent.green(), accent.blue()
        peach_color = self._get_active_accent_color()

        # Background fill & outline
        p.save()
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(self._get_background_color())
        p.drawPath(bg_path)
        p.restore()
        self._draw_edge_beat_glow(p, w, h, self._corner_radius, is_flush_notch)

        # Dynamic Ambient Radial Glow behind the player
        p.save()
        left_w = min(560, max(290, int(w * 0.46)))
        glow_cx = float(left_w // 2)
        glow_cy = float(h // 2 - 20)
        glow_r = float(max(180, min(w // 2, h // 2 + 60)))
        rad_glow = QRadialGradient(QPointF(glow_cx, glow_cy), glow_r)
        glow_alpha = 75 if is_playing else 35
        rad_glow.setColorAt(0.0, QColor(art_r, art_g, art_b, glow_alpha))
        rad_glow.setColorAt(0.45, QColor(art_r, art_g, art_b, int(glow_alpha * 0.4)))
        rad_glow.setColorAt(1.0, QColor(0, 0, 0, 0))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(rad_glow)
        p.drawPath(bg_path)
        p.restore()

        # 1. Top Bar Navigation (Tabs at top right, Restore/Maximize pill at top left)
        self._paint_tab_headers(p, theme, w, active_tab="music")

        # Track metadata
        title = "No Music Playing"
        artist = "Play on Spotify, Brave, YouTube, Windows Media..."
        album = ""
        app_name = "Media"
        if self._last_media_info and self._last_media_info.has_media:
            title = self._last_media_info.title or title
            artist = self._last_media_info.artist or artist
            album = getattr(self._last_media_info, "album", "") or ""
            app_name = getattr(self._last_media_info, "app_name", "Media") or "Media"

        # Time formatting
        def _fmt_time(sec: float) -> str:
            if sec < 0:
                return "0:00"
            s = int(round(sec))
            m, s = divmod(s, 60)
            return f"{m}:{s:02d}"

        cur_time_str = _fmt_time(self._playback_pos_sec)
        rem_sec = max(0.0, self._playback_dur_sec - self._playback_pos_sec)
        rem_time_str = f"-{_fmt_time(rem_sec)}" if self._playback_dur_sec > 0 else "--:--"
        ratio = min(1.0, max(0.0, self._playback_pos_sec / max(1.0, self._playback_dur_sec))) if self._playback_dur_sec > 0 else 0.0

        # Helper for tactile button press / hover anim
        def _btn_anim(name: str, base_r: float, base_alpha: int = 20):
            h_v = self._btn_hover_anim.get(name, 0.0)
            p_v = self._btn_press_anim.get(name, 0.0)
            r = base_r * (1.0 - 0.08 * p_v)
            alpha = min(255, int(base_alpha + h_v * 45))
            return r, QColor(255, 255, 255, alpha), h_v, p_v

        # ======================================================================
        # LEFT COLUMN: HERO MUSIC PLAYER (Artwork + Meta + Wave Progress + Controls)
        # ======================================================================
        avail_art_h = h - 220
        art_size = int(min(320, max(140, min(left_w - 60, avail_art_h))))
        art_x = int((left_w - art_size) // 2)
        art_y = 44
        art_rect = QRect(art_x, art_y, art_size, art_size)
        art_path = QPainterPath()
        art_radius = min(24.0, max(14.0, art_size * 0.12))
        art_path.addRoundedRect(QRectF(art_rect), art_radius, art_radius)

        # Ambient artwork shadow
        p.save()
        p.setPen(Qt.PenStyle.NoPen)
        if is_playing:
            p.setBrush(QColor(art_r, art_g, art_b, 110))
            p.drawRoundedRect(QRectF(art_x - 3, art_y + 3, art_size + 6, art_size + 6), art_radius + 2, art_radius + 2)
        else:
            p.setBrush(QColor(0, 0, 0, 100))
            p.drawRoundedRect(QRectF(art_x, art_y + 4, art_size, art_size), art_radius, art_radius)

        # Draw Artwork Pixmap
        has_art = False
        if thumb_bytes:
            pix = QPixmap()
            if pix.loadFromData(thumb_bytes):
                p.setClipPath(art_path)
                p.drawPixmap(art_rect, pix.scaled(art_size, art_size, Qt.AspectRatioMode.KeepAspectRatioByExpanding, Qt.TransformationMode.SmoothTransformation))
                has_art = True

        if not has_art:
            art_grad = QLinearGradient(art_x, art_y, art_x + art_size, art_y + art_size)
            art_grad.setColorAt(0.0, QColor(art_r, art_g, art_b))
            art_grad.setColorAt(1.0, QColor(max(0, art_r - 60), max(0, art_g - 60), max(0, art_b - 60)))
            p.fillPath(art_path, art_grad)
            self._draw_vector_note(p, art_x + art_size // 2, art_y + art_size // 2, size=int(art_size * 0.35), color=QColor(255, 255, 255, 220))

        p.restore()

        # Artwork border
        p.strokePath(art_path, QPen(QColor(255, 255, 255, 45), 1.2))

        # App Source Badge on bottom-right of artwork
        badge_size = 28
        badge_x = art_x + art_size - badge_size + 2
        badge_y = art_y + art_size - badge_size + 2
        badge_rect = QRect(badge_x, badge_y, badge_size, badge_size)
        p.save()
        p.setPen(QPen(QColor(0, 0, 0, 180), 2.2))
        p.setBrush(QColor(18, 18, 20))
        p.drawEllipse(badge_rect)
        self._draw_app_badge(p, badge_x + 14.0, badge_y + 14.0, 13.0, app_name)
        p.restore()

        # Typography: Title & Artist
        meta_top = art_y + art_size + 14
        title_font_size = 14.5 if art_size < 200 else 17.5
        title_font = QFont(["Segoe UI", "Nirmala UI", "sans-serif"], title_font_size, QFont.Weight.Bold)
        title_rect = QRectF(24, meta_top, left_w - 48, 26)
        self._draw_smooth_marquee(p, title_rect, title, title_font, QColor(255, 255, 255, 250), self._music_ticker_x, gap=48.0, fade_width=18.0)

        artist_text = f"{artist}  ·  {album}" if album else artist
        artist_font_size = 10.0 if art_size < 200 else 11.5
        artist_font = QFont(["Segoe UI", "Nirmala UI", "sans-serif"], artist_font_size, QFont.Weight.Normal)
        artist_rect = QRectF(24, meta_top + 26, left_w - 48, 20)
        self._draw_smooth_marquee(p, artist_rect, artist_text, artist_font, QColor(215, 210, 210, 190), self._music_ticker_x * 0.8, gap=40.0, fade_width=14.0)

        # Source / Format Capsule Pill
        badge_top = meta_top + 48
        if h >= 480:
            pill_w = min(160, left_w - 100)
            pill_rect = QRectF((left_w - pill_w) / 2.0, badge_top, pill_w, 20.0)
            p.save()
            p.setPen(QPen(QColor(255, 255, 255, 28), 1.0))
            p.setBrush(QColor(255, 255, 255, 14))
            p.drawRoundedRect(pill_rect, 10.0, 10.0)
            p.setFont(QFont(["Segoe UI", "sans-serif"], 8.5, QFont.Weight.Medium))
            p.setPen(QColor(peach_color.red(), peach_color.green(), peach_color.blue(), 230))
            p.drawText(pill_rect, Qt.AlignmentFlag.AlignCenter, f"Lossless  ·  {app_name}")
            p.restore()

        # Wave Progress Bar & Scrubber
        bar_y = h - 94
        self._theater_bar_y = bar_y
        track_x = 36
        track_w = left_w - 72
        track_h = 3.6

        # Timestamps
        p.setFont(QFont(["Segoe UI", "sans-serif"], 9.0, QFont.Weight.Normal))
        p.setPen(QColor(170, 160, 160, 210))
        p.drawText(QRect(track_x, bar_y - 18, 60, 16), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, cur_time_str)
        p.drawText(QRect(track_x + track_w - 60, bar_y - 18, 60, 16), Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, rem_time_str)

        # Background unplayed track
        p.save()
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(255, 255, 255, 28))
        p.drawRoundedRect(QRectF(track_x, bar_y - track_h / 2.0, track_w, track_h), track_h / 2.0, track_h / 2.0)

        # Active Wave / Filled Progress
        fill_w = track_w * ratio
        thumb_x = track_x + fill_w

        if is_playing and fill_w > 12.0:
            wave_path = QPainterPath()
            wave_path.moveTo(track_x, bar_y)
            wave_phase = self._anim_time * 6.5
            step_px = 2.0
            cur_x = track_x
            w_style = getattr(self, "_wave_style", "harmonic")
            while cur_x <= thumb_x:
                prog = (cur_x - track_x) / fill_w
                envelope = math.sin(prog * math.pi)

                if w_style == "harmonic":
                    w1 = math.sin((cur_x - track_x) * 0.18 - wave_phase)
                    w2 = math.sin((cur_x - track_x) * 0.40 + wave_phase * 0.65)
                    amp = 3.2 * envelope * (0.65 * w1 + 0.35 * w2)
                    wave_y = bar_y + amp
                elif w_style == "cyber":
                    raw_s = math.sin((cur_x - track_x) * 0.25 - wave_phase)
                    sign_val = 1.0 if raw_s > 0.08 else (-1.0 if raw_s < -0.08 else 0.0)
                    amp = 3.2 * envelope * sign_val
                    wave_y = bar_y + amp
                else:
                    amp = 2.8 * envelope
                    wave_y = bar_y + amp * math.sin((cur_x - track_x) * 0.20 - wave_phase)

                wave_path.lineTo(cur_x, wave_y)
                cur_x += step_px
            wave_path.lineTo(thumb_x, bar_y)

            # Glowing wave aura
            p.setPen(QPen(QColor(peach_color.red(), peach_color.green(), peach_color.blue(), 60), 6.0, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawPath(wave_path)

            # Main wave
            p.setPen(QPen(peach_color, 3.4, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
            p.drawPath(wave_path)
        else:
            p.setBrush(peach_color)
            p.drawRoundedRect(QRectF(track_x, bar_y - track_h / 2.0, fill_w, track_h), track_h / 2.0, track_h / 2.0)

        # Scrubber Knob
        thumb_r = 6.0
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(0, 0, 0, 90))
        p.drawEllipse(QPointF(thumb_x, bar_y + 1.2), thumb_r, thumb_r)
        p.setBrush(QColor(255, 255, 255))
        p.drawEllipse(QPointF(thumb_x, bar_y), thumb_r, thumb_r)
        p.setBrush(peach_color)
        p.drawEllipse(QPointF(thumb_x, bar_y), 2.5, 2.5)
        p.restore()

        # Playback Controls Hub
        ctrl_y = h - 46
        self._theater_ctrl_y = ctrl_y
        cx = left_w // 2

        # 1. Wave style cycle button at (cx - 108, ctrl_y)
        r, col, h_val, _ = _btn_anim("theater_wave_cycle", 18.0, 18)
        p.save()
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(col)
        p.drawEllipse(QPointF(cx - 108, ctrl_y), r, r)
        p.setPen(QPen(peach_color, 1.5, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        # Mini sine wave icon
        w_p = QPainterPath()
        w_p.moveTo(cx - 114, ctrl_y)
        w_p.quadTo(cx - 111, ctrl_y - 4, cx - 108, ctrl_y)
        w_p.quadTo(cx - 105, ctrl_y + 4, cx - 102, ctrl_y)
        p.drawPath(w_p)
        p.restore()

        # 2. Previous Track Button at (cx - 55, ctrl_y)
        r, col, h_val, _ = _btn_anim("prev", 20.0, 18)
        p.save()
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(col)
        p.drawEllipse(QPointF(cx - 55, ctrl_y), r, r)
        p.setBrush(peach_color)
        p1 = QPainterPath()
        p1.moveTo(cx - 50, ctrl_y - 6.5)
        p1.lineTo(cx - 50, ctrl_y + 6.5)
        p1.lineTo(cx - 58, ctrl_y)
        p1.closeSubpath()
        p.drawPath(p1)
        p2 = QPainterPath()
        p2.moveTo(cx - 56, ctrl_y - 6.5)
        p2.lineTo(cx - 56, ctrl_y + 6.5)
        p2.lineTo(cx - 64, ctrl_y)
        p2.closeSubpath()
        p.drawPath(p2)
        p.restore()

        # 3. Play / Pause Primary Hero Disc at (cx, ctrl_y)
        r, col, h_val, _ = _btn_anim("play", 26.0, 35)
        p.save()
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(peach_color.red(), peach_color.green(), peach_color.blue(), int(45 + h_val * 40)))
        p.drawEllipse(QPointF(cx, ctrl_y), r + 4, r + 4)
        p.setBrush(peach_color)
        p.drawEllipse(QPointF(cx, ctrl_y), r, r)

        p.setBrush(QColor(18, 18, 20))
        if is_playing:
            p.drawRoundedRect(QRectF(cx - 6.0, ctrl_y - 8.0, 4.0, 16.0), 1.5, 1.5)
            p.drawRoundedRect(QRectF(cx + 2.0, ctrl_y - 8.0, 4.0, 16.0), 1.5, 1.5)
        else:
            play_p = QPainterPath()
            play_p.moveTo(cx - 4.5, ctrl_y - 8.5)
            play_p.lineTo(cx - 4.5, ctrl_y + 8.5)
            play_p.lineTo(cx + 7.5, ctrl_y)
            play_p.closeSubpath()
            p.drawPath(play_p)
        p.restore()

        # 4. Next Track Button at (cx + 55, ctrl_y)
        r, col, h_val, _ = _btn_anim("next", 20.0, 18)
        p.save()
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(col)
        p.drawEllipse(QPointF(cx + 55, ctrl_y), r, r)
        p.setBrush(peach_color)
        n1 = QPainterPath()
        n1.moveTo(cx + 50, ctrl_y - 6.5)
        n1.lineTo(cx + 50, ctrl_y + 6.5)
        n1.lineTo(cx + 58, ctrl_y)
        n1.closeSubpath()
        p.drawPath(n1)
        n2 = QPainterPath()
        n2.moveTo(cx + 56, ctrl_y - 6.5)
        n2.lineTo(cx + 56, ctrl_y + 6.5)
        n2.lineTo(cx + 64, ctrl_y)
        n2.closeSubpath()
        p.drawPath(n2)
        p.restore()

        # 5. Lyrics / Visualizer toggle button at (cx + 108, ctrl_y)
        is_lyrics_on = getattr(self, "_music_show_lyrics", True)
        r, col, h_val, _ = _btn_anim("lyrics_toggle", 18.0, 30 if is_lyrics_on else 18)
        p.save()
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(col)
        p.drawEllipse(QPointF(cx + 108, ctrl_y), r, r)
        self._draw_lyrics_icon(p, cx + 108, ctrl_y, r=r, color=peach_color, is_active=is_lyrics_on)
        p.restore()

        # ======================================================================
        # RIGHT COLUMN: RESPONSIVE KARAOKE LYRICS SHEET OR 32-BAND VISUALIZER
        # ======================================================================
        right_x = left_w + 14
        right_w = w - right_x - 22
        panel_y = 44
        panel_h = h - panel_y - 24
        panel_rect = QRect(right_x, panel_y, right_w, panel_h)

        # Frosted Glass Container Panel
        p.save()
        p.setPen(QPen(QColor(255, 255, 255, 18), 1.0))
        p.setBrush(QColor(255, 255, 255, 7))
        p.drawRoundedRect(QRectF(panel_rect), 20.0, 20.0)

        # Panel Header
        p.setFont(QFont(["Segoe UI", "sans-serif"], 9.0, QFont.Weight.Bold))
        p.setPen(QColor(160, 155, 155, 180))
        has_lyrics = bool(self._lyrics_lines and len(self._lyrics_lines) > 0)
        hdr_title = "LIVE SYNCHRONIZED LYRICS" if has_lyrics else "HIGH-RESOLUTION AUDIO VISUALIZER"
        p.drawText(QRect(right_x + 20, panel_y + 14, right_w - 40, 18), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, hdr_title)

        # Pulsating Live Indicator Dot
        dot_alpha = int(140 + 115 * math.sin(self._anim_time * 4.0))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(52, 199, 89, dot_alpha) if is_playing else QColor(160, 160, 160, 120))
        p.drawEllipse(QPointF(right_x + right_w - 24, panel_y + 23), 4.0, 4.0)

        self._theater_lyrics_rects.clear()

        # ── SCENARIO A: Synchronized Scrolling Karaoke Lyrics ──
        if has_lyrics:
            active_idx = self._lyrics_active_idx
            total_lines = len(self._lyrics_lines)
            center_y = panel_y + 36 + (panel_h - 48) // 2
            line_h = 38

            for offset in range(-4, 6):
                idx = active_idx + offset
                if 0 <= idx < total_lines:
                    ly = center_y + offset * line_h
                    if panel_y + 38 <= ly <= panel_y + panel_h - 20:
                        l_rect = QRect(right_x + 16, int(ly - line_h / 2), right_w - 32, line_h)
                        self._theater_lyrics_rects[idx] = l_rect
                        l_sec, l_text = self._lyrics_lines[idx]

                        is_active = (offset == 0)
                        if is_active:
                            p.setFont(QFont(["Segoe UI", "Nirmala UI", "sans-serif"], 15.5, QFont.Weight.Bold))
                            if is_playing:
                                p.setPen(QColor(art_r, art_g, art_b, 85))
                                for ox, oy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                                    p.drawText(QRectF(l_rect.adjusted(ox, oy, ox, oy)), Qt.AlignmentFlag.AlignCenter, f"♪ {l_text} ♪")
                            p.setPen(QColor(255, 255, 255, 255))
                            p.drawText(QRectF(l_rect), Qt.AlignmentFlag.AlignCenter, f"♪ {l_text} ♪")
                        else:
                            dist = abs(offset)
                            alpha = max(30, int(180 - dist * 38))
                            p.setFont(QFont(["Segoe UI", "Nirmala UI", "sans-serif"], 11.5, QFont.Weight.Normal))
                            p.setPen(QColor(230, 225, 225, alpha))
                            p.drawText(QRectF(l_rect), Qt.AlignmentFlag.AlignCenter, l_text)

        # ── SCENARIO B: 32-Band Audio Spectrum Visualizer ──
        else:
            p.save()
            vis_y = panel_y + 50
            vis_h = panel_h - 100
            num_bars = 28
            bar_gap = 5
            total_bar_w = right_w - 60
            bar_w = max(4.0, (total_bar_w - (num_bars - 1) * bar_gap) / float(num_bars))

            start_bx = right_x + 30
            base_by = vis_y + vis_h

            t = self._anim_time
            for b in range(num_bars):
                bx = start_bx + b * (bar_w + bar_gap)
                if is_playing:
                    phase = b * 0.32
                    f1 = math.sin(t * 7.0 + phase)
                    f2 = math.cos(t * 11.0 - phase * 1.5)
                    f3 = math.sin(t * 3.5 + phase * 0.7)
                    val = (f1 * 0.45 + f2 * 0.35 + f3 * 0.20 + 1.0) / 2.0
                    envelope = math.sin((b / float(num_bars)) * math.pi)
                    bh = max(8.0, val * vis_h * (0.45 + 0.55 * envelope))
                else:
                    bh = 8.0

                b_rect = QRectF(bx, base_by - bh, bar_w, bh)
                b_grad = QLinearGradient(bx, base_by - bh, bx, base_by)
                b_grad.setColorAt(0.0, peach_color)
                b_grad.setColorAt(1.0, QColor(art_r, art_g, art_b, 160))
                p.setPen(Qt.PenStyle.NoPen)
                p.setBrush(b_grad)
                p.drawRoundedRect(b_rect, bar_w / 2.0, bar_w / 2.0)

                # Floating peak cap
                p.setBrush(QColor(255, 255, 255, 200))
                p.drawRoundedRect(QRectF(bx, base_by - bh - 4, bar_w, 2.0), 1.0, 1.0)

            # Center caption
            p.setFont(QFont(["Segoe UI", "sans-serif"], 10.5, QFont.Weight.Medium))
            p.setPen(QColor(200, 195, 195, 180))
            p.drawText(QRect(right_x + 20, base_by + 16, right_w - 40, 22), Qt.AlignmentFlag.AlignCenter, f"Studio Master Quality  ·  {title}")
            p.restore()

        p.restore()

        # ======================================================================
        # TACTILE BOTTOM PULL HANDLE & CORNER RESIZE INDICATOR
        # ======================================================================
        p.save()
        p.setPen(Qt.PenStyle.NoPen)
        # Centered pull handle pill
        p.setBrush(QColor(255, 255, 255, 90))
        p.drawRoundedRect(QRectF(w // 2 - 28, h - 7.5, 56, 3.5), 1.75, 1.75)
        # Bottom-right corner diagonal grip lines
        p.setPen(QPen(QColor(255, 255, 255, 65), 1.4, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        p.drawLine(QPointF(w - 14, h - 6), QPointF(w - 6, h - 14))
        p.drawLine(QPointF(w - 10, h - 6), QPointF(w - 6, h - 10))
        p.restore()


    def _paint_weather(self, p: QPainter, theme: dict, w: int, h: int):
        self._paint_tab_headers(p, theme, w, active_tab="weather")

        weather = self._last_weather_info or WeatherInfo()
        icon_type = weather.icon_type
        t = self._anim_time

        # ── 1. Left Hero Weather Card (Procedural Animated Canvas) ───────────
        hero_rect = QRect(16, 32, 164, 106)
        hero_path = QPainterPath()
        hero_path.addRoundedRect(QRectF(hero_rect), 12, 12)

        p.save()
        p.setClipPath(hero_path)

        # Ambient Weather Card Background Theme
        if icon_type in ["hot", "sun"]:
            hero_grad = QLinearGradient(16, 32, 180, 138)
            hero_grad.setColorAt(0.0, QColor(60, 35, 10, 180))
            hero_grad.setColorAt(1.0, QColor(20, 12, 6, 220))
        elif icon_type == "rain":
            hero_grad = QLinearGradient(16, 32, 180, 138)
            hero_grad.setColorAt(0.0, QColor(15, 30, 50, 190))
            hero_grad.setColorAt(1.0, QColor(8, 15, 25, 230))
        elif icon_type == "thunder":
            hero_grad = QLinearGradient(16, 32, 180, 138)
            hero_grad.setColorAt(0.0, QColor(30, 15, 45, 200))
            hero_grad.setColorAt(1.0, QColor(10, 8, 20, 230))
        elif icon_type == "wind":
            hero_grad = QLinearGradient(16, 32, 180, 138)
            hero_grad.setColorAt(0.0, QColor(15, 35, 45, 190))
            hero_grad.setColorAt(1.0, QColor(8, 18, 26, 230))
        elif icon_type == "snow":
            hero_grad = QLinearGradient(16, 32, 180, 138)
            hero_grad.setColorAt(0.0, QColor(20, 35, 55, 190))
            hero_grad.setColorAt(1.0, QColor(10, 18, 30, 230))
        elif icon_type == "night":
            hero_grad = QLinearGradient(16, 32, 180, 138)
            hero_grad.setColorAt(0.0, QColor(12, 14, 30, 210))
            hero_grad.setColorAt(1.0, QColor(6, 6, 16, 240))
        else:
            hero_grad = QLinearGradient(16, 32, 180, 138)
            hero_grad.setColorAt(0.0, QColor(25, 30, 42, 180))
            hero_grad.setColorAt(1.0, QColor(12, 15, 22, 220))

        p.fillPath(hero_path, hero_grad)

        # ── LIVE WEATHER PARTICLES RENDERING ───────────────────────────────
        if icon_type == "rain":
            # 1. Slanted Falling Raindrops
            pen = QPen(QColor(120, 180, 255), 1.2)
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            p.setPen(pen)
            for d in self._rain_drops:
                rx = 16 + d["x"]
                ry = 32 + d["y"]
                p.setPen(QPen(QColor(120, 180, 255, int(d["alpha"] * 240)), 1.2))
                p.drawLine(QPointF(rx, ry), QPointF(rx + 2.0, ry + d["len"]))

            # 2. Ground Splash Ripples
            p.setBrush(Qt.BrushStyle.NoBrush)
            for s in self._rain_splashes:
                sx = 16 + s["x"]
                sy = 32 + s["y"]
                p.setPen(QPen(QColor(140, 200, 255, int(s["alpha"] * 255)), 1.0))
                p.drawEllipse(QPointF(sx, sy), s["r"], s["r"] * 0.45)

        elif icon_type in ["hot", "sun"]:
            # 1. Shimmering Rising Heatwave Curves
            p.setBrush(Qt.BrushStyle.NoBrush)
            for idx, y_base in enumerate([65, 85, 105]):
                heat_p = QPainterPath()
                heat_p.moveTo(16, 32 + y_base)
                for wx in range(0, 151, 15):
                    wy = y_base + math.sin(t * 3.5 + wx * 0.08 + idx) * 3.5
                    heat_p.lineTo(16 + wx, 32 + wy)
                p.setPen(QPen(QColor(255, 160, 40, 35 + idx * 10), 1.5))
                p.drawPath(heat_p)

            # 2. Rising Golden Heat Embers
            p.setPen(Qt.PenStyle.NoPen)
            for e in self._heat_embers:
                ex = 16 + e["x"]
                ey = 32 + e["y"]
                e_alpha = int(e["alpha"] * (0.6 + 0.4 * math.sin(t * 4.0 + e["phase"])) * 220)
                p.setBrush(QColor(255, 190, 50, e_alpha))
                p.drawEllipse(QPointF(ex, ey), e["r"], e["r"])

        elif icon_type == "wind":
            # 1. Aerodynamic Streaming Wind Ribbons
            p.setBrush(Qt.BrushStyle.NoBrush)
            for idx, y_pos in enumerate([48, 68, 88, 102]):
                speed_mod = 1.0 + idx * 0.3
                w_path = QPainterPath()
                w_path.moveTo(16, 32 + y_pos)
                for wx in range(0, 135, 12):
                    wy = y_pos + math.sin(t * 4.0 * speed_mod + wx * 0.07) * 4.0
                    w_path.lineTo(16 + wx, 32 + wy)
                tip_x = 16 + 135
                tip_y = 32 + y_pos + math.sin(t * 4.0 * speed_mod + 135 * 0.07) * 4.0
                w_path.quadTo(tip_x + 8, tip_y - 4, tip_x + 6, tip_y - 8)
                p.setPen(QPen(QColor(160, 210, 245, 60 + idx * 15), 1.4))
                p.drawPath(w_path)

            # 2. Fast Breeze Particle Streaks
            p.setPen(Qt.PenStyle.NoPen)
            for pw in self._wind_particles:
                px = 16 + pw["x"]
                py = 32 + pw["y"]
                p.setBrush(QColor(180, 230, 255, int(pw["alpha"] * 200)))
                p.drawRoundedRect(QRectF(px, py, pw["size"] * 2.5, 1.2), 0.6, 0.6)

        elif icon_type == "thunder":
            # 1. Lightning Ambient Flash
            if self._lightning_flash > 0:
                p.setBrush(QColor(180, 200, 255, int(self._lightning_flash * 120)))
                p.drawRect(hero_rect)

            # 2. Branching Lightning Bolt
            if self._lightning_flash > 0.15 and len(self._lightning_bolt_pts) >= 2:
                pen = QPen(QColor(255, 240, 100, int(self._lightning_flash * 255)), 2.0)
                pen.setJoinStyle(Qt.PenJoinStyle.MiterJoin)
                p.setPen(pen)
                p.setBrush(Qt.BrushStyle.NoBrush)
                l_path = QPainterPath()
                l_path.moveTo(16 + self._lightning_bolt_pts[0][0], 32 + self._lightning_bolt_pts[0][1])
                for pt in self._lightning_bolt_pts[1:]:
                    l_path.lineTo(16 + pt[0], 32 + pt[1])
                p.drawPath(l_path)

            # 3. Fast Rain Underneath
            p.setPen(QPen(QColor(120, 160, 220, 180), 1.2))
            for d in self._rain_drops[:20]:
                rx = 16 + d["x"]
                ry = 32 + d["y"]
                p.drawLine(QPointF(rx, ry), QPointF(rx + 2.5, ry + d["len"] * 1.2))

        elif icon_type == "snow":
            # 1. Drifting Sinusoidal Snowflakes
            p.setPen(Qt.PenStyle.NoPen)
            for f in self._snow_flakes:
                fx = 16 + f["x"]
                fy = 32 + f["y"]
                p.setBrush(QColor(255, 255, 255, int(f["alpha"] * 240)))
                p.drawEllipse(QPointF(fx, fy), f["r"], f["r"])

        elif icon_type == "night":
            # 1. Twinkling Starlight Field
            p.setPen(Qt.PenStyle.NoPen)
            for s in self._night_stars:
                sx = 16 + s["x"]
                sy = 32 + s["y"]
                star_alpha = int((0.3 + 0.7 * abs(math.sin(t * s["freq"] + s["phase"]))) * 230)
                p.setBrush(QColor(255, 255, 255, star_alpha))
                p.drawEllipse(QPointF(sx, sy), s["r"], s["r"])

        elif icon_type == "cloud":
            # 1. Atmospheric Soft Drifting Cloud Mist (feathered gradient wisps)
            p.setPen(Qt.PenStyle.NoPen)
            for idx, drift_x in enumerate(self._cloud_drift):
                y_pos = 48 + idx * 24
                c_alpha = int(18 + idx * 12)
                cx = 16 + (drift_x % 145)
                cy = 32 + y_pos
                cloud_grad = QRadialGradient(cx, cy, 38.0)
                cloud_grad.setColorAt(0.0, QColor(210, 230, 255, c_alpha))
                cloud_grad.setColorAt(0.55, QColor(190, 215, 245, int(c_alpha * 0.4)))
                cloud_grad.setColorAt(1.0, QColor(210, 230, 255, 0))
                p.setBrush(cloud_grad)
                p.drawEllipse(QPointF(cx, cy), 42.0, 16.0)

            # 2. Gentle Ambient Floating Motes
            for pw in self._wind_particles[:8]:
                px = 16 + pw["x"]
                py = 32 + pw["y"]
                p.setBrush(QColor(200, 230, 255, int(pw["alpha"] * 130)))
                p.drawEllipse(QPointF(px, py), 1.2, 1.2)

        else:
            # Sunny / Clear Sky Ambient Glow & Floating Light Specks
            p.setPen(Qt.PenStyle.NoPen)
            for pw in self._wind_particles[:6]:
                px = 16 + pw["x"]
                py = 32 + pw["y"]
                p.setBrush(QColor(255, 240, 180, int(pw["alpha"] * 150)))
                p.drawEllipse(QPointF(px, py), 1.4, 1.4)

        p.restore()

        # Hero Card Glass Rim
        p.strokePath(hero_path, QPen(QColor(255, 255, 255, 45), 1.0))

        # Vector Weather Graphic on Hero card with soft ambient drop glow
        p.save()
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(255, 220, 100, 35))
        p.drawEllipse(QPointF(42, 58), 16.0, 16.0)
        p.restore()
        self._draw_vector_weather_icon(p, 42, 58, icon_type=weather.icon_type, color=QColor(255, 255, 255), scale=1.8)

        # Big Temperature Text
        p.setFont(QFont("Segoe UI", 20, QFont.Weight.Bold))
        p.setPen(theme["text_primary"])
        p.drawText(QRect(72, 42, 90, 32), Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, f"{weather.temp_c}°C")

        # Condition string
        p.setFont(QFont("Segoe UI", 9, QFont.Weight.DemiBold))
        p.setPen(theme["text_primary"])
        cond_rect = QRect(24, 80, 148, 18)
        fm = p.fontMetrics()
        p.drawText(cond_rect, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, fm.elidedText(weather.condition, Qt.TextElideMode.ElideRight, 148))

        # Location City/Country
        p.setFont(QFont("Segoe UI", 8, QFont.Weight.Normal))
        p.setPen(theme["text_secondary"])
        city_rect = QRect(24, 100, 148, 16)
        p.drawText(city_rect, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, fm.elidedText(f"📍 {weather.city}", Qt.TextElideMode.ElideRight, 148))

        # ── 2. Right Live Digital Clock & Details Card ───────────────────────
        clock_rect = QRect(188, 32, w - 204, 106)
        clock_path = QPainterPath()
        clock_path.addRoundedRect(QRectF(clock_rect), 12, 12)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(255, 255, 255, 14))
        p.drawPath(clock_path)
        p.strokePath(clock_path, QPen(QColor(255, 255, 255, 35), 1.0))

        # Precision Digital Clock (HH:MM:SS AM/PM)
        live_clock = time.strftime("%I:%M:%S %p")
        live_date = time.strftime("%A, %b %d, %Y")

        p.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        p.setPen(theme["text_primary"])
        p.drawText(QRect(200, 40, clock_rect.width() - 24, 26), Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, live_clock)

        # Full Date
        p.setFont(QFont("Segoe UI", 8, QFont.Weight.DemiBold))
        p.setPen(theme["text_secondary"])
        p.drawText(QRect(200, 66, clock_rect.width() - 24, 18), Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, live_date)

        # 2 Metric Pills: [💧 Humidity] [💨 Wind]
        pill_y = 92
        pill_w = (clock_rect.width() - 26) // 2

        # Humidity Pill
        p1 = QRect(198, pill_y, pill_w, 26)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(255, 255, 255, 18))
        p.drawRoundedRect(QRectF(p1), 6, 6)
        self._draw_vector_droplet(p, 208, pill_y + 13, color=QColor(96, 165, 250))
        p.setFont(QFont("Segoe UI", 8, QFont.Weight.DemiBold))
        p.setPen(theme["text_primary"])
        p.drawText(QRect(218, pill_y, pill_w - 22, 26), Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, f"Humidity {weather.humidity}")

        # Wind Pill
        p2 = QRect(198 + pill_w + 6, pill_y, pill_w, 26)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(255, 255, 255, 18))
        p.drawRoundedRect(QRectF(p2), 6, 6)
        self._draw_vector_wind(p, 198 + pill_w + 16, pill_y + 13, color=QColor(148, 163, 184))
        p.setFont(QFont("Segoe UI", 8, QFont.Weight.DemiBold))
        p.setPen(theme["text_primary"])
        p.drawText(QRect(198 + pill_w + 26, pill_y, pill_w - 28, 26), Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, f"Wind {weather.wind_speed}")

        # ── 3. Bottom Row: 4 Frosted Environmental & Forecast Horizon Pills ──
        # Eliminates the empty black void and turns this into a luxury weather station!
        b_y = 146
        b_h = 32
        b_w = (w - 32 - 18) // 4
        gap = 6

        pills_data = [
            ("Today", f"{weather.temp_c}°C", "sun" if icon_type in ["sun", "hot"] else ("rain" if "rain" in icon_type else "cloud"), QColor(255, 200, 80)),
            ("Feels", f"{int(float(weather.temp_c or 28) + 2)}°C", "thermometer", QColor(251, 146, 60)),
            ("UV Index", "5 Mod", "uv", QColor(168, 85, 247)),
            ("Air Quality", "38 Good", "leaf", QColor(34, 197, 94))
        ]

        for i, (label, val, icon_k, col) in enumerate(pills_data):
            px = 16 + i * (b_w + gap)
            p_rect = QRectF(px, b_y, b_w, b_h)

            p.setPen(QPen(QColor(255, 255, 255, 24), 1.0))
            p.setBrush(QColor(255, 255, 255, 14))
            p.drawRoundedRect(p_rect, 7, 7)

            # Mini icon / indicator
            icx = px + 12
            icy = b_y + b_h / 2.0
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(col)
            p.drawEllipse(QPointF(icx, icy), 3.0, 3.0)

            p.setFont(QFont("Segoe UI", 7.5, QFont.Weight.DemiBold))
            p.setPen(theme["text_secondary"])
            p.drawText(QRectF(px + 20, b_y + 2, b_w - 24, 14), Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, label)

            p.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
            p.setPen(theme["text_primary"])
            p.drawText(QRectF(px + 20, b_y + 16, b_w - 24, 14), Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, val)

        # Vertical carousel page indicator dots on right edge (Dot 4 = Weather)
        self._draw_vertical_page_dots(p, w - 12, h / 2.0, active_page=4, total_pages=5)

    def _get_route_point_and_angle(self, pts: list, progress: float):
        """Calculates interpolated position and tangent heading angle along a polyline route."""
        if not pts:
            return (0.0, 0.0, 0.0)
        if len(pts) == 1:
            return (float(pts[0][0]), float(pts[0][1]), 0.0)

        # Calculate segment lengths
        seg_lens = []
        total_len = 0.0
        for i in range(len(pts) - 1):
            dx = pts[i + 1][0] - pts[i][0]
            dy = pts[i + 1][1] - pts[i][1]
            dist = math.hypot(dx, dy)
            seg_lens.append(dist)
            total_len += dist

        if total_len <= 0.001:
            return (float(pts[0][0]), float(pts[0][1]), 0.0)

        target_dist = (progress % 1.0) * total_len
        accum = 0.0

        for i, slen in enumerate(seg_lens):
            if accum + slen >= target_dist or i == len(seg_lens) - 1:
                seg_prog = 0.0 if slen <= 0.001 else (target_dist - accum) / slen
                seg_prog = max(0.0, min(1.0, seg_prog))
                p0 = pts[i]
                p1 = pts[i + 1]
                cur_x = p0[0] + (p1[0] - p0[0]) * seg_prog
                cur_y = p0[1] + (p1[1] - p0[1]) * seg_prog
                dx = p1[0] - p0[0]
                dy = p1[1] - p0[1]
                heading_deg = math.degrees(math.atan2(dx, -dy))
                return (cur_x, cur_y, heading_deg)
            accum += slen

        return (float(pts[-1][0]), float(pts[-1][1]), 0.0)

    def _draw_mini_route_map(self, p: QPainter, rect: QRect, mode: str = "split", theme: dict = None):
        """Renders an ultra-modern vector Google Maps canvas with terrain, waterways, road grid, traffic, and glowing animated GPS route."""
        rx, ry, rw, rh = rect.x(), rect.y(), rect.width(), rect.height()
        map_path = QPainterPath()
        map_path.addRoundedRect(QRectF(rect), 12, 12)

        p.save()
        p.setClipPath(map_path)

        # 1. Base Map Terrain (Deep Dark Navigation Slate)
        terrain_grad = QLinearGradient(rx, ry, rx + rw, ry + rh)
        terrain_grad.setColorAt(0.0, QColor(14, 22, 33))
        terrain_grad.setColorAt(0.5, QColor(11, 18, 28))
        terrain_grad.setColorAt(1.0, QColor(8, 14, 22))
        p.fillPath(map_path, terrain_grad)

        # 2. Water Body / Coastal Bay / River
        water_path = QPainterPath()
        if mode == "panoramic":
            water_path.moveTo(rx, ry + 20)
            water_path.cubicTo(rx + rw * 0.3, ry - 10, rx + rw * 0.45, ry + 55, rx + rw, ry + 25)
            water_path.lineTo(rx + rw, ry)
            water_path.lineTo(rx, ry)
            water_path.closeSubpath()
        else:
            water_path.moveTo(rx, ry + 28)
            water_path.cubicTo(rx + rw * 0.35, ry + 8, rx + rw * 0.6, ry + 42, rx + rw, ry + 22)
            water_path.lineTo(rx + rw, ry)
            water_path.lineTo(rx, ry)
            water_path.closeSubpath()

        water_color = QColor(13, 38, 64, 220)
        p.fillPath(water_path, water_color)

        # Subtle wave reflection along coastline
        p.setPen(QPen(QColor(0, 180, 255, 45), 1.2, Qt.PenStyle.DashLine))
        p.drawPath(water_path)

        # 3. Secondary City Road Grid & Blocks
        p.setPen(QPen(QColor(38, 52, 72, 110), 1.6))
        grid_step = 26
        # Horizontal streets
        for gy in range(ry + 16, ry + rh - 10, grid_step):
            p.drawLine(rx + 8, gy, rx + rw - 8, gy)
        # Vertical / Cross streets
        for gx in range(rx + 20, rx + rw - 10, grid_step):
            p.drawLine(gx, ry + 12, gx, ry + rh - 12)

        # 4. Major Arterial Avenues & Highway Overpasses
        arterial_path = QPainterPath()
        if mode == "panoramic":
            arterial_path.moveTo(rx + 10, ry + rh - 30)
            arterial_path.cubicTo(rx + rw * 0.3, ry + rh - 40, rx + rw * 0.5, ry + 60, rx + rw - 15, ry + 45)
        else:
            arterial_path.moveTo(rx + 12, ry + rh - 24)
            arterial_path.cubicTo(rx + rw * 0.4, ry + rh - 35, rx + rw * 0.6, ry + 55, rx + rw - 12, ry + 38)

        # Road base (wide dark slate)
        p.setPen(QPen(QColor(24, 34, 48, 230), 6.5, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
        p.drawPath(arterial_path)
        # Road asphalt core
        p.setPen(QPen(QColor(60, 78, 102, 190), 4.2, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
        p.drawPath(arterial_path)

        # 5. Live Traffic Overlay (Green / Orange / Red Congestion Flow)
        if self._traffic_enabled:
            # Smooth Green flow segment
            p.setPen(QPen(QColor(34, 197, 94, 180), 2.2, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            p.drawLine(int(rx + rw * 0.1), int(ry + rh - 28), int(rx + rw * 0.42), int(ry + rh * 0.65))
            # Moderate Amber traffic segment
            p.setPen(QPen(QColor(245, 158, 11, 200), 2.2, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            p.drawLine(int(rx + rw * 0.42), int(ry + rh * 0.65), int(rx + rw * 0.68), int(ry + rh * 0.48))
            # Smooth Green flow to destination
            p.setPen(QPen(QColor(34, 197, 94, 180), 2.2, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            p.drawLine(int(rx + rw * 0.68), int(ry + rh * 0.48), int(rx + rw - 18), int(ry + 42))

        # 6. Waypoints & GPS Navigation Route
        if mode == "panoramic":
            route_pts = [
                (rx + 30, ry + rh - 24),
                (rx + rw * 0.22, ry + rh - 30),
                (rx + rw * 0.38, ry + 62),
                (rx + rw * 0.58, ry + 56),
                (rx + rw * 0.76, ry + 78),
                (rx + rw - 32, ry + 36),
            ]
        else:
            route_pts = [
                (rx + 16, ry + rh - 22),
                (rx + rw * 0.28, ry + rh - 28),
                (rx + rw * 0.46, ry + 54),
                (rx + rw * 0.68, ry + 50),
                (rx + rw * 0.82, ry + 68),
                (rx + rw - 22, ry + 34),
            ]

        # Draw Multi-Layer Glowing GPS Route Path
        route_path = QPainterPath()
        route_path.moveTo(route_pts[0][0], route_pts[0][1])
        for pt in route_pts[1:]:
            route_path.lineTo(pt[0], pt[1])

        # Layer A: Outer Neon Cyan Ambient Glow
        glow_pen = QPen(QColor(0, 195, 255, 70), 7.5, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
        p.strokePath(route_path, glow_pen)

        # Layer B: Vibrant Google Blue Core Line
        core_pen = QPen(QColor(26, 115, 232), 4.2, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
        p.strokePath(route_path, core_pen)

        # Layer C: Inner Neon Cyan Highlight
        inner_pen = QPen(QColor(0, 229, 255), 2.0, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
        p.strokePath(route_path, inner_pen)

        # Layer D: Animated Forward Pulse Chevrons / Moving Dashes
        dash_pen = QPen(QColor(255, 255, 255, 210), 1.6, Qt.PenStyle.CustomDashLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
        dash_pen.setDashPattern([3.0, 5.0])
        dash_pen.setDashOffset(-self._anim_time * 22.0)
        p.strokePath(route_path, dash_pen)

        # 7. Start Point (Origin Pin / Pulse Dot)
        sx, sy = route_pts[0]
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(34, 197, 94, 90))
        p.drawEllipse(QPointF(sx, sy), 6.5, 6.5)
        p.setBrush(QColor(34, 197, 94))
        p.drawEllipse(QPointF(sx, sy), 4.0, 4.0)
        p.setBrush(QColor(255, 255, 255))
        p.drawEllipse(QPointF(sx, sy), 1.8, 1.8)

        # 8. Destination Point (Google Maps Red Pin)
        dx, dy = route_pts[-1]
        self._draw_vector_map_pin(p, int(dx), int(dy + 6))

        # 9. Live Moving Vehicle / GPS Chevron
        vx, vy, heading_ang = self._get_route_point_and_angle(route_pts, self._nav_progress)

        # Radar Ripple Ring expanding from vehicle
        ripple_frac = (self._anim_time * 1.6) % 1.0
        ripple_r = 5.0 + ripple_frac * 11.0
        ripple_alpha = int(180 * (1.0 - ripple_frac))
        p.setPen(QPen(QColor(0, 195, 255, ripple_alpha), 1.4))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawEllipse(QPointF(vx, vy), ripple_r, ripple_r)

        # Rotated GPS Navigation Vehicle Arrow
        p.save()
        p.translate(vx, vy)
        p.rotate(heading_ang)

        # Vehicle Arrow drop shadow
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(0, 0, 0, 140))
        shadow_poly = QPolygonF([QPointF(0, -6), QPointF(5, 5), QPointF(0, 2.5), QPointF(-5, 5)])
        p.drawPolygon(shadow_poly)

        # Neon Cyan / White Vehicle Body
        p.setBrush(QColor(0, 229, 255))
        veh_poly = QPolygonF([QPointF(0, -7), QPointF(5.5, 4.5), QPointF(0, 2.0), QPointF(-5.5, 4.5)])
        p.drawPolygon(veh_poly)

        # Inner White Cockpit Core
        p.setBrush(QColor(255, 255, 255))
        inner_veh = QPolygonF([QPointF(0, -5), QPointF(2.8, 3.0), QPointF(0, 1.2), QPointF(-2.8, 3.0)])
        p.drawPolygon(inner_veh)
        p.restore()

        # 10. Top Location & Navigation HUD Pill Overlay
        city_name = "Marine Drive, Kochi"
        if self._weather and self._weather.current_weather and self._weather.current_weather.city:
            city_name = f"{self._weather.current_weather.city}"

        p.setFont(QFont("Segoe UI", 7, QFont.Weight.Bold))
        fm = p.fontMetrics()
        full_text = f"📍 {city_name} • Live GPS"
        max_hud_w = rw - 44 if mode == "panoramic" else rw - 24
        req_w = fm.horizontalAdvance(full_text) + 26
        hud_w = max(110, min(req_w, max_hud_w))

        hud_rect = QRect(rx + 8, ry + 6, hud_w, 20)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(10, 16, 26, 220))
        p.drawRoundedRect(QRectF(hud_rect), 6, 6)
        p.setPen(QPen(QColor(255, 255, 255, 45), 1.0))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRoundedRect(QRectF(hud_rect), 6, 6)

        # Green live GPS pulse in HUD
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(34, 197, 94))
        p.drawEllipse(QPointF(rx + 16, ry + 16), 3.0, 3.0)

        p.setPen(QColor(255, 255, 255))
        elided_hud = fm.elidedText(full_text, Qt.TextElideMode.ElideRight, hud_w - 24)
        p.drawText(QRect(rx + 22, ry + 6, hud_w - 24, 20), Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, elided_hud)

        # 11. Interactive Bottom Action Chips Overlay
        chip_y = ry + rh - 25
        if mode == "panoramic":
            c_w = (rw - 36) // 4
            chips = [
                ("⤡ Split", rx + 8, QColor(0, 122, 255), "map_chip_split"),
                ("🚦 Traffic" if self._traffic_enabled else "⚪ Traffic", rx + 8 + (c_w + 6), QColor(34, 197, 94) if self._traffic_enabled else QColor(148, 163, 184), "map_chip_traffic"),
                ("⚡ Route", rx + 8 + (c_w + 6) * 2, QColor(245, 158, 11), "map_chip_reset"),
                ("🌐 Maps", rx + 8 + (c_w + 6) * 3, QColor(234, 67, 53), "map_chip_open"),
            ]
        else:
            c_w = (rw - 28) // 4
            chips = [
                ("⤢ Full", rx + 6, QColor(0, 122, 255), "map_chip_panoramic"),
                ("🚦 Traf" if self._traffic_enabled else "⚪ Traf", rx + 6 + (c_w + 5), QColor(34, 197, 94) if self._traffic_enabled else QColor(148, 163, 184), "map_chip_traffic"),
                ("⚡ Route", rx + 6 + (c_w + 5) * 2, QColor(245, 158, 11), "map_chip_reset"),
                ("🌐 Maps", rx + 6 + (c_w + 5) * 3, QColor(234, 67, 53), "map_chip_open"),
            ]

        for label, cx, col, b_key in chips:
            bg_col, border_col, scale, _, _ = self._get_button_style(b_key, QColor(10, 16, 26, 230))
            p.save()
            bcx, bcy = cx + c_w / 2.0, chip_y + 10.0
            p.translate(bcx, bcy)
            p.scale(scale, scale)
            p.translate(-bcx, -bcy)

            p.setPen(QPen(border_col, 1.0))
            p.setBrush(bg_col)
            p.drawRoundedRect(QRectF(cx, chip_y, c_w, 20), 5, 5)

            p.setFont(QFont("Segoe UI", 7, QFont.Weight.DemiBold))
            p.setPen(col)
            p.drawText(QRect(cx, chip_y, c_w, 20), Qt.AlignmentFlag.AlignCenter, label)
            p.restore()

        p.restore()
        p.strokePath(map_path, QPen(QColor(255, 255, 255, 40), 1.0))

    def _paint_map(self, p: QPainter, theme: dict, w: int, h: int):
        self._paint_tab_headers(p, theme, w, active_tab="map")

        if self._map_view_mode == "panoramic":
            # ── Panoramic Ultra-Wide Live Route Map Mode ───────────────────────
            map_rect = QRect(16, 28, w - 32, 108)
            self._draw_mini_route_map(p, map_rect, mode="panoramic", theme=theme)

            # Miniature Top-Right Compass Dial Overlay in Panoramic Mode
            p.save()
            comp_cx, comp_cy = w - 42, 42
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor(10, 16, 26, 200))
            p.drawEllipse(QPointF(comp_cx, comp_cy), 15, 15)
            p.setPen(QPen(QColor(255, 255, 255, 50), 1.0))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawEllipse(QPointF(comp_cx, comp_cy), 15, 15)
            self._draw_precision_compass(p, comp_cx, comp_cy, r=12, heading=self._compass_current_heading, theme=theme)
            p.restore()
            return

        # ── Split Mode: (Left Card: Compass / Turn HUD | Right Card: Live Map) ──
        compass_rect = QRect(16, 28, 140, 108)
        compass_path = QPainterPath()
        compass_path.addRoundedRect(QRectF(compass_rect), 12, 12)

        p.save()
        p.setClipPath(compass_path)

        # Subtle dark radar gradient inside left card
        radar_grad = QRadialGradient(86, 74, 65)
        radar_grad.setColorAt(0.0, QColor(14, 24, 38, 220))
        radar_grad.setColorAt(0.7, QColor(10, 16, 26, 240))
        radar_grad.setColorAt(1.0, QColor(6, 10, 16, 250))
        p.fillPath(compass_path, radar_grad)

        if self._compass_left_view == "turn_hud":
            # ── Left View: Turn-by-Turn Navigation HUD ────────────────────────
            # Top Turn Maneuver Badge
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor(34, 197, 94, 220))
            p.drawRoundedRect(QRectF(26, 36, 42, 28), 6, 6)
            p.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
            p.setPen(QColor(255, 255, 255))
            p.drawText(QRect(26, 36, 42, 28), Qt.AlignmentFlag.AlignCenter, "↱")

            p.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
            p.setPen(QColor(255, 255, 255))
            p.drawText(QRect(74, 34, 76, 18), Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, "In 200m")

            p.setFont(QFont("Segoe UI", 7, QFont.Weight.DemiBold))
            p.setPen(QColor(148, 163, 184))
            p.drawText(QRect(74, 50, 76, 14), Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, "Turn Right")

            # Street / Avenue Name
            p.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
            p.setPen(theme["text_primary"])
            p.drawText(QRect(22, 68, 128, 18), Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, "Marine Way Blvd")

            # ETA & Distance Pill
            p.setFont(QFont("Segoe UI", 7, QFont.Weight.DemiBold))
            p.setPen(QColor(34, 197, 94))
            p.drawText(QRect(22, 86, 128, 16), Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, "12 min • 4.2 km • Fast")

            p.setFont(QFont("Segoe UI", 6))
            p.setPen(QColor(96, 165, 250))
            p.drawText(QRect(16, 114, 140, 14), Qt.AlignmentFlag.AlignCenter, "Tap for Compass 🧭")
        else:
            # ── Left View: Precision Compass Dial & Azimuth ───────────────────
            heading = self._compass_current_heading
            self._draw_precision_compass(p, 86, 70, r=32, heading=heading, theme=theme)

            # Azimuth Degrees & Cardinal Text below Compass
            cardinals = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE", "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"]
            card_idx = int((heading + 11.25) / 22.5) % 16
            card_str = cardinals[card_idx]
            deg_str = f"{int(heading):03d}° {card_str}"

            p.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
            p.setPen(theme["text_primary"])
            p.drawText(QRect(16, 108, 140, 16), Qt.AlignmentFlag.AlignCenter, deg_str)

            p.setFont(QFont("Segoe UI", 6))
            p.setPen(QColor(96, 165, 250))
            p.drawText(QRect(16, 122, 140, 12), Qt.AlignmentFlag.AlignCenter, f"{self._compass_mode.capitalize()} • Tap for Turn HUD")

        p.restore()
        p.strokePath(compass_path, QPen(QColor(255, 255, 255, 35), 1.0))

        # ── 2. Right Card: Live Mini Route Map Canvas ──────────────────────
        map_rect = QRect(164, 28, w - 180, 108)
        self._draw_mini_route_map(p, map_rect, mode="split", theme=theme)

    def _paint_clipboard(self, p: QPainter, theme: dict, w: int, h: int):
        self._paint_tab_headers(p, theme, w, active_tab="clipboard")

        preview_str = self._clipboard_preview_text.strip() if self._clipboard_preview_text else ""
        is_copied = (time.monotonic() - self._clipboard_copy_feedback) < 1.8

        # 1. Header: Dynamic Smart Badge & Stats (y: 6 to 24)
        if self._last_clipboard_url:
            badge_rect = QRect(16, 6, 126, 20)
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor(0, 122, 255, 45))
            p.drawRoundedRect(QRectF(badge_rect), 5, 5)
            self._draw_vector_globe(p, 26, 16, r=5, color=QColor(96, 165, 250))
            p.setFont(QFont("Segoe UI", 7, QFont.Weight.Bold))
            p.setPen(QColor(96, 165, 250))
            p.drawText(QRect(36, 6, 102, 20), Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, "LINK DETECTED")

        elif self._clipboard_color_hex:
            badge_rect = QRect(16, 6, 124, 20)
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor(255, 255, 255, 18))
            p.drawRoundedRect(QRectF(badge_rect), 5, 5)
            self._draw_vector_swatch(p, 26, 16, self._clipboard_color_hex)
            p.setFont(QFont("Segoe UI", 7, QFont.Weight.Bold))
            p.setPen(theme["text_primary"])
            p.drawText(QRect(36, 6, 98, 20), Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, f"COLOR {self._clipboard_color_hex.upper()}")

        elif self._clipboard_calc_result:
            badge_rect = QRect(16, 6, 128, 20)
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor(245, 158, 11, 45))
            p.drawRoundedRect(QRectF(badge_rect), 5, 5)
            self._draw_vector_calc(p, 26, 16, color=QColor(251, 191, 36))
            p.setFont(QFont("Segoe UI", 7, QFont.Weight.Bold))
            p.setPen(QColor(251, 191, 36))
            p.drawText(QRect(36, 6, 104, 20), Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, f"CALC = {self._clipboard_calc_result}")

        else:
            badge_rect = QRect(16, 6, 112, 20)
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor(255, 255, 255, 18))
            p.drawRoundedRect(QRectF(badge_rect), 5, 5)
            self._draw_vector_clipboard_icon(p, 26, 16, color=theme["text_primary"])
            p.setFont(QFont("Segoe UI", 7, QFont.Weight.Bold))
            p.setPen(theme["text_primary"])
            p.drawText(QRect(36, 6, 88, 20), Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, "CLIPBOARD")

        # Word & Char Count statistics (using precomputed cached metrics - zero lag)
        if self._clipboard_char_count > 0:
            words = self._clipboard_word_count
            chars = self._clipboard_char_count
            p.setFont(QFont("Segoe UI", 7))
            p.setPen(theme["text_secondary"])
            p.drawText(QRect(w - 140, 6, 124, 20), Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight, f"{words}w • {chars}c")

        # 2. Main Content Card / Snippet (y: 30 to 102)
        snippet_rect = QRect(16, 30, w - 32, 72)
        p.setPen(QPen(QColor(255, 255, 255, 18), 1.0))
        p.setBrush(QColor(255, 255, 255, 8))
        p.drawRoundedRect(QRectF(snippet_rect), 8, 8)

        if not preview_str:
            p.setFont(QFont("Segoe UI", 8.5))
            p.setPen(theme["text_secondary"])
            p.drawText(snippet_rect, Qt.AlignmentFlag.AlignCenter, "Clipboard is empty")
        elif self._last_clipboard_url:
            p.setFont(QFont("Segoe UI", 8.5, QFont.Weight.Bold))
            p.setPen(QColor(96, 165, 250))
            p.drawText(QRect(26, 40, snippet_rect.width() - 20, 24), Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, "Web URL Link")
            p.setFont(QFont("Segoe UI", 7.5))
            p.setPen(theme["text_secondary"])
            p.drawText(QRect(26, 64, snippet_rect.width() - 20, 28), Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, preview_str[:120])
        elif self._clipboard_calc_result:
            p.setFont(QFont("Segoe UI", 8))
            p.setPen(theme["text_secondary"])
            p.drawText(QRect(26, 40, snippet_rect.width() - 150, 20), Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, preview_str[:100])
            p.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
            p.setPen(QColor(52, 199, 89))
            p.drawText(QRect(26, 62, snippet_rect.width() - 150, 26), Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, f"= {self._clipboard_calc_result}")
            ans_rect = QRect(w - 140, 48, 96, 36)
            p.setBrush(QColor(52, 199, 89, 35))
            p.drawRoundedRect(QRectF(ans_rect), 6, 6)
            p.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
            p.setPen(QColor(52, 199, 89))
            p.drawText(ans_rect, Qt.AlignmentFlag.AlignCenter, "EVALUATED ✓")
        elif self._clipboard_color_hex:
            swatch_rect = QRect(26, 48, 36, 36)
            p.setPen(QPen(QColor(255, 255, 255, 100), 1.0))
            try:
                p.setBrush(QColor(self._clipboard_color_hex))
            except Exception:
                p.setBrush(QColor(255, 255, 255))
            p.drawRoundedRect(QRectF(swatch_rect), 6, 6)
            p.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
            p.setPen(theme["text_primary"])
            p.drawText(QRect(70, 46, 180, 20), Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, self._clipboard_color_hex.upper())
            c = QColor(self._clipboard_color_hex)
            p.setFont(QFont("Segoe UI", 8))
            p.setPen(theme["text_secondary"])
            p.drawText(QRect(70, 66, 180, 18), Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, f"RGB: {c.red()}, {c.green()}, {c.blue()}")
        else:
            p.setFont(QFont("Segoe UI", 8))
            p.setPen(theme["text_primary"])
            p.drawText(QRect(26, 42, snippet_rect.width() - 20, 50), Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft | Qt.TextFlag.TextWordWrap, preview_str[:180])

        # 3. 5 Smart Action Buttons (y: 108 to 138)
        btn_y = 108
        buttons = []
        if self._last_clipboard_url:
            buttons.append(("Open", 16, self._draw_vector_globe, QColor(0, 122, 255), QColor(255, 255, 255), "clip_act_link"))
        elif self._clipboard_calc_result:
            buttons.append(("Result", 16, self._draw_vector_calc, QColor(245, 158, 11), QColor(255, 255, 255), "clip_act_link"))
        else:
            buttons.append(("Search", 16, self._draw_vector_search, QColor(0, 122, 255), QColor(255, 255, 255), "clip_act_link"))

        buttons.append(("Ask GPT", 89, lambda p, cx, cy: self._draw_vector_chatgpt(p, cx, cy, color=QColor(16, 163, 127)), QColor(255, 255, 255, 20), QColor(16, 185, 129), "clip_act_gpt"))
        if self._last_clipboard_url or self._clipboard_calc_result:
            buttons.append(("Search", 162, self._draw_vector_search, QColor(255, 255, 255, 20), theme["text_primary"], "clip_act_case"))
        else:
            buttons.append(("Case Aa", 162, self._draw_vector_case, QColor(255, 255, 255, 20), theme["text_primary"], "clip_act_case"))

        copy_bg = QColor(16, 185, 129, 60) if is_copied else QColor(255, 255, 255, 20)
        copy_col = QColor(52, 199, 89) if is_copied else theme["text_primary"]
        copy_label = "COPIED!" if is_copied else "Copy"
        buttons.append((copy_label, 235, self._draw_vector_copy, copy_bg, copy_col, "clip_act_copy"))
        buttons.append(("Clear", 308, self._draw_vector_trash, QColor(255, 255, 255, 20), QColor(255, 100, 100), "clip_act_clear"))

        for label, bx, draw_fn, bg_col, txt_col, b_key in buttons:
            b_w = 66
            c_bg, c_border, scale, _, _ = self._get_button_style(b_key, bg_col)
            p.save()
            bcx, bcy = bx + b_w / 2.0, btn_y + 14.0
            p.translate(bcx, bcy)
            p.scale(scale, scale)
            p.translate(-bcx, -bcy)

            p.setPen(QPen(c_border, 1.0))
            p.setBrush(c_bg)
            p.drawRoundedRect(QRectF(bx, btn_y, b_w, 28), 6, 6)

            # Draw vector icon
            draw_fn(p, bx + 12, btn_y + 14)

            # Draw label
            p.setFont(QFont("Segoe UI", 7, QFont.Weight.Bold if label in ["COPIED!", "Ask GPT", "Open", "Result"] else QFont.Weight.DemiBold))
            p.setPen(txt_col)
            p.drawText(QRect(bx + 18, btn_y, b_w - 18, 28), Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignCenter, label)
            p.restore()


    def _paint_tools(self, p: QPainter, theme: dict, w: int, h: int):
        # 0. Pure AMOLED Black Base & Clean Border
        is_flush_notch = self._is_flush_notch()
        bg_path = self._make_notch_path(w, h, self._corner_radius, is_flush_notch)
        p.save()
        p.fillPath(bg_path, QColor(0, 0, 0, 255))
        p.strokePath(self._make_notch_outline_path(w, h, self._corner_radius, is_flush_notch), QPen(QColor(255, 255, 255, 24), 1.0))
        p.restore()

        self._paint_tab_headers(p, theme, w, active_tab="tools")

        # 1. Header: Hardware Telemetry • System Vitals
        cur_time = time.strftime("%I:%M %p")
        p.setFont(QFont("Segoe UI", 8.5, QFont.Weight.Bold))
        p.setPen(theme["text_primary"])
        self._draw_vector_bolt(p, 24, 38, color=theme["accent"])
        p.drawText(QRect(36, 28, 240, 20), Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, f"Hardware Telemetry  ·  {cur_time}")

        # 2. Performance Row (CPU & RAM with Used/Total GB)
        cpu_val = max(1.0, min(100.0, self._anim_cpu))
        ram_val = max(1.0, min(100.0, self._anim_ram))
        card_w = (w - 46) // 2
        card_y = 52
        card_h = 32

        # CPU Card
        c1 = QRect(18, card_y, card_w, card_h)
        cpu_bg, cpu_border, _, _, _ = self._get_button_style("tool_cpu", QColor(255, 255, 255, 14))
        p.setPen(QPen(cpu_border, 1.0))
        p.setBrush(cpu_bg)
        p.drawRoundedRect(QRectF(c1), 7, 7)
        self._draw_vector_cpu(p, 28, card_y + 16, color=QColor(52, 199, 89))
        p.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
        p.setPen(theme["text_primary"])
        p.drawText(QRect(42, card_y + 4, 60, 14), Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, f"CPU {cpu_val:.0f}%")
        bar_x = 42
        bar_w = card_w - 52
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(255, 255, 255, 25))
        p.drawRoundedRect(QRectF(bar_x, card_y + 20, bar_w, 4), 2, 2)
        p.setBrush(QColor(52, 199, 89) if cpu_val < 75 else QColor(255, 159, 10))
        p.drawRoundedRect(QRectF(bar_x, card_y + 20, max(2.0, bar_w * (cpu_val / 100.0)), 4), 2, 2)

        # RAM Card with used / total GB
        c2 = QRect(18 + card_w + 10, card_y, card_w, card_h)
        ram_bg, ram_border, _, _, _ = self._get_button_style("tool_ram", QColor(255, 255, 255, 14))
        p.setPen(QPen(ram_border, 1.0))
        p.setBrush(ram_bg)
        p.drawRoundedRect(QRectF(c2), 7, 7)
        self._draw_vector_ram(p, 18 + card_w + 20, card_y + 16, color=QColor(0, 122, 255))
        p.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
        p.setPen(theme["text_primary"])
        ram_gb_text = f"RAM {ram_val:.0f}%"
        if HAS_PSUTIL:
            try:
                mem = psutil.virtual_memory()
                ram_gb_text = f"RAM {ram_val:.0f}% ({mem.used / (1024**3):.1f}/{mem.total / (1024**3):.0f}G)"
            except Exception:
                pass
        p.drawText(QRect(18 + card_w + 34, card_y + 4, card_w - 40, 14), Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, ram_gb_text)
        r_bar_x = 18 + card_w + 34
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(255, 255, 255, 25))
        p.drawRoundedRect(QRectF(r_bar_x, card_y + 20, bar_w, 4), 2, 2)
        p.setBrush(QColor(0, 122, 255) if ram_val < 80 else QColor(255, 69, 58))
        p.drawRoundedRect(QRectF(r_bar_x, card_y + 20, max(2.0, bar_w * (ram_val / 100.0)), 4), 2, 2)

        # 3. Row 2: Battery / Power (Left) & Bluetooth / Wireless Status (Right)
        row2_y = 90
        # Battery Card
        c3 = QRect(18, row2_y, card_w, card_h)
        batt_bg, batt_border, _, _, _ = self._get_button_style("tool_batt", QColor(255, 255, 255, 14))
        p.setPen(QPen(batt_border, 1.0))
        p.setBrush(batt_bg)
        p.drawRoundedRect(QRectF(c3), 7, 7)
        batt_pct = self._battery_percent
        is_plugged = self._battery_plugged
        self._draw_vector_battery(p, 22, row2_y + 9, batt_pct, is_plugged=is_plugged, color=QColor(52, 199, 89) if is_plugged else QColor(255, 255, 255))
        p.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
        p.setPen(theme["text_primary"])
        batt_label = f"⚡ Charging {batt_pct}%" if is_plugged else f"🔋 Battery {batt_pct}%"
        p.drawText(QRect(48, row2_y + 4, card_w - 54, 14), Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, batt_label)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(255, 255, 255, 25))
        p.drawRoundedRect(QRectF(48, row2_y + 20, bar_w, 4), 2, 2)
        p.setBrush(QColor(52, 199, 89) if is_plugged else (QColor(239, 68, 68) if batt_pct <= 20 else QColor(255, 255, 255, 200)))
        p.drawRoundedRect(QRectF(48, row2_y + 20, max(2.0, bar_w * (batt_pct / 100.0)), 4), 2, 2)

        # Bluetooth / Wireless Status Card
        c4 = QRect(18 + card_w + 10, row2_y, card_w, card_h)
        bt_bg, bt_border, _, _, _ = self._get_button_style("tool_bt", QColor(255, 255, 255, 14))
        p.setPen(QPen(bt_border, 1.0))
        p.setBrush(bt_bg)
        p.drawRoundedRect(QRectF(c4), 7, 7)
        bt_info = self._last_bluetooth_info or BluetoothInfo()
        is_bt_conn = bt_info.has_connected
        bt_col = QColor(0, 122, 255) if is_bt_conn else QColor(160, 160, 165)
        self._draw_vector_bluetooth(p, 18 + card_w + 22, row2_y + 16, is_connected=is_bt_conn, color=bt_col)
        p.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
        p.setPen(theme["text_primary"])
        bt_txt = bt_info.primary_device_name if is_bt_conn and bt_info.primary_device_name else ("Bluetooth On" if is_bt_conn else "Wireless Standby")
        fm_t = p.fontMetrics()
        p.drawText(QRect(18 + card_w + 34, row2_y + 4, card_w - 40, 14), Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, fm_t.elidedText(bt_txt, Qt.TextElideMode.ElideRight, card_w - 40))
        p.setFont(QFont("Segoe UI", 7.5, QFont.Weight.Normal))
        p.setPen(QColor(96, 165, 250) if is_bt_conn else theme["text_secondary"])
        p.drawText(QRect(18 + card_w + 34, row2_y + 18, card_w - 40, 12), Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, "CONNECTED" if is_bt_conn else "READY")

        # 4. Row 3: 7 Quick Desktop Tool Buttons with Tactile Spring Scaling
        btn_y = h - 42
        tools = [
            ("Snip", 18, self._draw_vector_scissors, theme["text_primary"], "tool_snip"),
            ("Wall", 72, self._draw_vector_wallpaper, theme["text_primary"], "tool_wallpaper"),
            ("Calc", 126, self._draw_vector_calc, theme["text_primary"], "tool_calc"),
            ("Notes", 180, self._draw_vector_notes, theme["text_primary"], "tool_notes"),
            ("GPT", 234, lambda p, cx, cy: self._draw_vector_chatgpt(p, cx, cy, color=QColor(16, 163, 127)), QColor(16, 185, 129), "tool_gpt"),
            ("Mute", 288, lambda p, cx, cy: self._draw_vector_speaker(p, cx, cy, level=0), theme["text_primary"], "tool_mute"),
            ("Lock", 342, self._draw_vector_lock, theme["text_primary"], "tool_lock"),
        ]

        for label, bx, draw_fn, txt_col, b_key in tools:
            b_w = 46
            t_bg, t_border, scale, _, _ = self._get_button_style(b_key, QColor(255, 255, 255, 18))

            p.save()
            bcx, bcy = bx + b_w / 2.0, btn_y + 13.0
            p.translate(bcx, bcy)
            p.scale(scale, scale)
            p.translate(-bcx, -bcy)

            p.setPen(QPen(t_border, 1.0))
            p.setBrush(t_bg)
            p.drawRoundedRect(QRectF(bx, btn_y, b_w, 26), 6, 6)

            draw_fn(p, bx + 12, btn_y + 13)
            p.setFont(QFont("Segoe UI", 7, QFont.Weight.Bold if label in ["GPT", "Maps"] else QFont.Weight.DemiBold))
            p.setPen(txt_col)
            p.drawText(QRect(bx + 18, btn_y, b_w - 18, 26), Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignCenter, label)
            p.restore()

        # Vertical carousel page indicator dots on right edge (Dot 2 = Tools, 5 total pages)
        self._draw_vertical_page_dots(p, w - 12, h / 2.0, active_page=2, total_pages=5)

    def _paint_tab_headers(self, p: QPainter, theme: dict, w: int, active_tab: str):
        h = self.height()
        is_th = (getattr(self, "_is_theater_mode", False) or w >= 600 or h >= 280)
        # 1. Top-left subtle collapse indicator notch with tactile hover/press
        col_hover = self._btn_hover_anim.get("collapse", 0.0)
        col_press = self._btn_press_anim.get("collapse", 0.0)
        p.save()
        col_w = 26.0 * (1.0 - 0.10 * col_press)
        col_rect = QRectF(14.0 + (26.0 - col_w) / 2.0, 5.0, col_w, 20.0)
        p.setPen(QPen(QColor(255, 255, 255, int(22 + col_hover * 55)), 1.0))
        p.setBrush(QColor(255, 255, 255, int(12 + col_hover * 40)))
        p.drawRoundedRect(col_rect, 6.0, 6.0)
        # Chevron down icon
        p.setPen(QPen(QColor(255, 255, 255, int(175 + col_hover * 80)), 1.4, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
        ch_y = 15.0
        p.drawLine(QPointF(22.0, ch_y - 2.0), QPointF(27.0, ch_y + 1.8))
        p.drawLine(QPointF(27.0, ch_y + 1.8), QPointF(32.0, ch_y - 2.0))
        p.restore()

        # 2. Sleek Floating Segmented Glass Tray Container around tabs
        p.save()
        tray_x = float(w - 22 - 8 * 24.5 - 12.0)
        tray_w = float(8 * 24.5 + 24.0)
        tray_rect = QRectF(tray_x, 4.5, tray_w, 23.0)
        p.setPen(QPen(QColor(255, 255, 255, 22), 1.0))
        p.setBrush(QColor(255, 255, 255, 12))
        p.drawRoundedRect(tray_rect, 11.5, 11.5)

        # OriginOS Fluid Sliding Active Tab Glass Pill Indicator
        ind_x = getattr(self, "_indicator_x", tray_x)
        ind_w = max(18.0, getattr(self, "_indicator_w", 20.0))
        # Soft ambient glow behind active tab
        p.setPen(Qt.PenStyle.NoPen)
        acc = theme.get("accent", QColor(255, 255, 255))
        p.setBrush(QColor(acc.red(), acc.green(), acc.blue(), 40))
        p.drawRoundedRect(QRectF(ind_x - 1.0, 5.0, ind_w + 2.0, 22.0), 6.5, 6.5)
        # Main sliding glass pill
        p.setBrush(QColor(255, 255, 255, 48))
        p.drawRoundedRect(QRectF(ind_x, 5.5, ind_w, 21.0), 6.0, 6.0)
        # Top gloss sheen
        gloss = QLinearGradient(ind_x, 5.5, ind_x, 15.5)
        gloss.setColorAt(0.0, QColor(255, 255, 255, 55))
        gloss.setColorAt(1.0, QColor(255, 255, 255, 0))
        p.setBrush(gloss)
        p.drawRoundedRect(QRectF(ind_x, 5.5, ind_w, 10.0), 6.0, 6.0)
        p.restore()

        # 3. 9 Tabs: Assistant | Music | Weather | Control | Calendar | Shelf | Maps & Compass | Clipboard | Tools
        tabs = [
            ("assistant", self._get_tab_x("assistant", w)),
            ("music", self._get_tab_x("music", w)),
            ("weather", self._get_tab_x("weather", w)),
            ("control", self._get_tab_x("control", w)),
            ("calendar", self._get_tab_x("calendar", w)),
            ("shelf", self._get_tab_x("shelf", w)),
            ("map", self._get_tab_x("map", w)),
            ("clipboard", self._get_tab_x("clipboard", w)),
            ("tools", self._get_tab_x("tools", w)),
        ]
        for name, tx in tabs:
            rect = QRect(int(tx - 10), 5, 20, 21)
            cx, cy = rect.center().x(), rect.center().y()
            is_active = (name == active_tab)
            h_val = self._btn_hover_anim.get(f"tab_{name}", 0.0)
            p_val = self._btn_press_anim.get(f"tab_{name}", 0.0)
            tab_scale = (1.0 + 0.12 * h_val) * (1.0 - 0.10 * p_val)

            p.save()
            p.translate(cx, cy)
            p.scale(tab_scale, tab_scale)
            p.translate(-cx, -cy)

            if is_active:
                icon_color = QColor(255, 255, 255, 250)
            else:
                if h_val > 0.01:
                    p.save()
                    p.setPen(Qt.PenStyle.NoPen)
                    p.setBrush(QColor(255, 255, 255, int(h_val * 32)))
                    p.drawRoundedRect(QRectF(rect), 5.5, 5.5)
                    p.restore()
                    icon_color = QColor(255, 255, 255, min(255, int(175 + h_val * 80)))
                else:
                    icon_color = QColor(170, 170, 180, 200)

            if name == "assistant":
                self._draw_vector_spark(p, cx, cy, color=icon_color)
            elif name == "music":
                self._draw_vector_note(p, cx, cy, color=icon_color)
            elif name == "weather":
                weather_icon = self._last_weather_info.icon_type if self._last_weather_info else "sun"
                self._draw_vector_weather_icon(p, cx, cy, icon_type=weather_icon, color=icon_color, scale=0.85)
            elif name == "control":
                self._draw_vector_sliders_icon(p, cx, cy, color=icon_color)
            elif name == "calendar":
                self._draw_vector_calendar_icon(p, cx, cy, color=icon_color)
            elif name == "shelf":
                self._draw_vector_shelf_icon(p, cx, cy, color=icon_color)
            elif name == "map":
                self._draw_vector_compass_icon(p, cx, cy, color=icon_color)
            elif name == "clipboard":
                self._draw_vector_clipboard_icon(p, cx, cy, color=icon_color)
            elif name == "tools":
                self._draw_vector_bolt(p, cx, cy, color=icon_color)

            p.restore()


if __name__ == "__main__":
    from settings import Settings
    app = QApplication(sys.argv)
    island = OriginIsland(settings=Settings())
    island.show()
    sys.exit(app.exec())
