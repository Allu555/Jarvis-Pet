import asyncio
import ctypes
import ctypes.wintypes
import re
import threading
import time
from typing import Optional, Callable, List, Tuple

user32 = ctypes.windll.user32
VK_VOLUME_MUTE = 0xAD
VK_VOLUME_DOWN = 0xAE
VK_VOLUME_UP = 0xAF
VK_MEDIA_NEXT_TRACK = 0xB0
VK_MEDIA_PREV_TRACK = 0xB1
VK_MEDIA_PLAY_PAUSE = 0xB3

try:
    from winsdk.windows.media.control import (
        GlobalSystemMediaTransportControlsSessionManager as MediaManager,
        GlobalSystemMediaTransportControlsSession as MediaSession,
    )
    from winsdk.windows.storage.streams import DataReader
    HAS_WINSDK = True
except Exception:
    HAS_WINSDK = False


def send_virtual_media_key(vk: int):
    try:
        user32.keybd_event(vk, 0, 0, 0)
        user32.keybd_event(vk, 0, 2, 0)  # KEYEVENTF_KEYUP
    except Exception:
        pass


def volume_up():
    send_virtual_media_key(VK_VOLUME_UP)


def volume_down():
    send_virtual_media_key(VK_VOLUME_DOWN)


def volume_mute():
    send_virtual_media_key(VK_VOLUME_MUTE)


def clean_app_name(raw_app_id: str) -> str:
    if not raw_app_id:
        return "Media Player"
    raw_lower = raw_app_id.lower()
    if "spotify" in raw_lower:
        return "Spotify"
    elif "brave" in raw_lower:
        return "Brave"
    elif "chrome" in raw_lower:
        return "Chrome"
    elif "edge" in raw_lower:
        return "Edge"
    elif "firefox" in raw_lower:
        return "Firefox"
    elif "vlc" in raw_lower:
        return "VLC"
    elif "music.ui" in raw_lower or "zune" in raw_lower or "mediaplayer" in raw_lower:
        return "Windows Media"
    elif "itunes" in raw_lower or "apple" in raw_lower:
        return "Apple Music"
    elif "tidal" in raw_lower:
        return "Tidal"
    elif "deezer" in raw_lower:
        return "Deezer"
    
    cleaned = raw_app_id.split("!")[-1].split(".exe")[0]
    return cleaned.capitalize() if cleaned else "Media"


class MediaInfo:
    def __init__(
        self,
        title: str = "",
        artist: str = "",
        album: str = "",
        app_name: str = "Media Player",
        is_playing: bool = False,
        thumbnail_bytes: Optional[bytes] = None,
        position_sec: float = 0.0,
        duration_sec: float = 0.0,
        timestamp: float = 0.0,
    ):
        self.title = title
        self.artist = artist
        self.album = album
        self.app_name = app_name
        self.is_playing = is_playing
        self.thumbnail_bytes = thumbnail_bytes
        self.position_sec = max(0.0, float(position_sec))
        self.duration_sec = max(0.0, float(duration_sec))
        self.timestamp = timestamp if timestamp > 0 else time.monotonic()

    @property
    def has_media(self) -> bool:
        return bool(self.title or self.artist)

    def display_title(self) -> str:
        return self.title or "Unknown Track"

    def display_artist(self) -> str:
        return self.artist or self.album or self.app_name or "Unknown Artist"

    def current_position(self) -> float:
        """Returns the real-time interpolated playback position in seconds."""
        if not self.is_playing or self.position_sec <= 0:
            return max(0.0, self.position_sec)
        elapsed = max(0.0, time.monotonic() - self.timestamp)
        pos = self.position_sec + elapsed
        if self.duration_sec > 0:
            return min(self.duration_sec, pos)
        return pos

    def __repr__(self) -> str:
        return f"<MediaInfo title='{self.title}' artist='{self.artist}' app='{self.app_name}' playing={self.is_playing} pos={self.current_position():.1f}/{self.duration_sec:.1f}s thumb={bool(self.thumbnail_bytes)}>"


WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.wintypes.HWND, ctypes.wintypes.LPARAM)


def _get_process_name(hwnd: int) -> str:
    try:
        pid = ctypes.wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        if pid.value == 0:
            return ""
        PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
        h_proc = ctypes.windll.kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid.value)
        if not h_proc:
            return ""
        buf = ctypes.create_unicode_buffer(1024)
        size = ctypes.wintypes.DWORD(1024)
        ctypes.windll.kernel32.QueryFullProcessImageNameW(h_proc, 0, buf, ctypes.byref(size))
        ctypes.windll.kernel32.CloseHandle(h_proc)
        return buf.value.split("\\")[-1].lower()
    except Exception:
        return ""


def _get_window_titles_and_hwnds() -> List[Tuple[int, str, str]]:
    results = []
    def enum_cb(hwnd, _):
        if user32.IsWindowVisible(hwnd):
            length = user32.GetWindowTextLengthW(hwnd)
            if length > 0:
                buf = ctypes.create_unicode_buffer(length + 1)
                user32.GetWindowTextW(hwnd, buf, length + 1)
                val = buf.value.strip()
                if val:
                    proc_name = _get_process_name(hwnd)
                    results.append((hwnd, val, proc_name))
        return True
    try:
        user32.EnumWindows(WNDENUMPROC(enum_cb), 0)
    except Exception:
        pass
    return results


def is_valid_media_info(info: Optional[MediaInfo]) -> bool:
    """Strictly validates that detected media is an actual playing song and NOT an application or document."""
    if not info or not info.title:
        return False
    t_lower = info.title.lower().strip()
    a_lower = (info.artist or "").lower().strip()
    app_lower = (info.app_name or "").lower().strip()

    # Reject code & document file extensions (e.g. "origin_island.py", "index.html")
    doc_exts = (
        ".py", ".pyw", ".js", ".jsx", ".ts", ".tsx", ".html", ".htm", ".css", ".json",
        ".yaml", ".yml", ".md", ".txt", ".log", ".c", ".cpp", ".h", ".cs", ".java",
        ".go", ".rs", ".php", ".sh", ".bat", ".ps1", ".pdf", ".doc", ".docx", ".xls",
        ".xlsx", ".ppt", ".pptx", ".zip", ".tar", ".gz", ".7z", ".rar"
    )
    if any(t_lower.endswith(ext) or f"{ext} " in t_lower or f"{ext} -" in t_lower for ext in doc_exts):
        return False

    # Blacklist of development tools, file managers, editors, and system apps (word-boundary matched
    # so song/video titles like "Official Video", "Ride", "Digital", "Words" are never falsely rejected)
    blacklist = (
        "antigravity", "ide", "file explorer", "explorer.exe", "explorer", "visual studio",
        "vscode", "vs code", "cursor", "pycharm", "intellij", "sublime", "atom", "notepad",
        "terminal", "powershell", "cmd.exe", "command prompt", "task manager", "settings",
        "calculator", "snipping tool", "snip", "word", "excel", "powerpoint", "git", "github"
    )
    bl_pattern = r"\b(?:" + "|".join(re.escape(b) for b in blacklist) + r")\b"
    if re.search(bl_pattern, t_lower) or re.search(bl_pattern, a_lower) or re.search(bl_pattern, app_lower):
        return False

    return True


def detect_song_from_windows() -> Optional[MediaInfo]:
    """
    Fallback song detection for standalone music players only.
    Strictly restricted to verified music processes (Spotify, VLC, AIMP, Foobar, etc.)
    and will NEVER match arbitrary windows like File Explorer or IDEs.
    """
    windows = _get_window_titles_and_hwnds()

    for hwnd, title, proc_name in windows:
        t_lower = title.lower()

        # 1. Spotify Desktop Player (spotify.exe)
        if proc_name == "spotify.exe":
            if " - " in title and not any(k in t_lower for k in ["spotify free", "spotify premium", "advertisement"]):
                parts = title.split(" - ", 1)
                if len(parts) == 2 and parts[0].strip() and parts[1].strip():
                    info = MediaInfo(
                        title=parts[1].strip(),
                        artist=parts[0].strip(),
                        app_name="Spotify",
                        is_playing=True  # Active track title in Spotify window indicates playback
                    )
                    if is_valid_media_info(info):
                        return info

        # 2. VLC Media Player (vlc.exe)
        elif proc_name == "vlc.exe":
            if " - vlc media player" in t_lower:
                clean = re.sub(r"\s*-\s*VLC media player.*$", "", title, flags=re.IGNORECASE).strip()
                if clean:
                    if " - " in clean:
                        parts = clean.split(" - ", 1)
                        info = MediaInfo(
                            title=parts[1].strip(),
                            artist=parts[0].strip(),
                            app_name="VLC",
                            is_playing=True
                        )
                    else:
                        info = MediaInfo(
                            title=clean,
                            artist="VLC Player",
                            app_name="VLC",
                            is_playing=False
                        )
                    if is_valid_media_info(info):
                        return info

        # 3. Dedicated Music Players (AIMP, Foobar2000, MusicBee, iTunes)
        elif proc_name in ["aimp.exe", "musicbee.exe", "foobar2000.exe", "itunes.exe", "winamp.exe"]:
            if " - " in title:
                parts = title.split(" - ", 1)
                app_disp = proc_name.replace(".exe", "").capitalize()
                info = MediaInfo(
                    title=parts[1].strip(),
                    artist=parts[0].strip(),
                    app_name=app_disp,
                    is_playing=False
                )
                if is_valid_media_info(info):
                    return info

        # 4. Web Browsers playing YouTube or YouTube Music
        # Supports Chrome, Edge, Brave, Firefox, Opera, Vivaldi, Arc
        elif proc_name in [
            "chrome.exe", "msedge.exe", "brave.exe", "firefox.exe",
            "opera.exe", "operagx.exe", "vivaldi.exe", "arc.exe"
        ]:
            if "youtube" in t_lower:
                # Exclude static non-video pages
                ignored_pages = (
                    "- youtube", "youtube", "home - youtube", "subscriptions - youtube",
                    "explore - youtube", "library - youtube", "history - youtube",
                    "watch later - youtube", "trending - youtube", "liked videos - youtube"
                )
                # Strip browser name from the end
                clean = re.sub(
                    r"\s*[-—]\s*(?:Google\s*Chrome|Microsoft[\s\u200b]*Edge|Personal\s*[-—]\s*Microsoft[\s\u200b]*Edge|Brave|Mozilla\s*Firefox|Firefox|Opera(?:\s*GX)?|Vivaldi|Arc)\s*$",
                    "",
                    title,
                    flags=re.IGNORECASE
                ).strip()

                # Strip leading notification badges like (1) or (99+)
                clean = re.sub(r"^\(\d+\+?\)\s*", "", clean).strip()

                clean_lower = clean.lower()
                if clean_lower in ignored_pages or clean_lower == "youtube":
                    continue

                is_yt_music = bool(re.search(r"[-—]\s*YouTube\s*Music\s*$", clean, re.IGNORECASE)) or ("youtube music" in clean_lower)
                # Strip "- YouTube" or "- YouTube Music" suffix
                clean = re.sub(r"\s*[-—]\s*YouTube(?:\s*Music)?\s*$", "", clean, flags=re.IGNORECASE).strip()

                # Clean video junk tags like (Official Music Video), [Official 4K Video], etc.
                cleaned_title = re.sub(
                    r"\s*[\(\[](?:Official\s*(?:Music\s*)?Video|Official\s*Audio|Lyric\s*Video|Full\s*(?:Audio|Song|Video)|Audio\s*Track|Video\s*Song|4K|HD|Remastered|Official|Lyrics)[\)\]]",
                    "",
                    clean,
                    flags=re.IGNORECASE
                ).strip()

                if cleaned_title:
                    app_label = "YouTube Music" if is_yt_music else "YouTube"
                    # Format A: "Artist - Title" (standard) or "Title - Artist" (YouTube Music)
                    if " - " in cleaned_title and " | " not in cleaned_title:
                        parts = cleaned_title.split(" - ", 1)
                        if is_yt_music:
                            song_part = parts[0].strip()
                            artist_part = parts[1].strip()
                        else:
                            artist_part = parts[0].strip()
                            song_part = parts[1].strip()
                    # Format B: "Title | Movie | Artist"
                    elif " | " in cleaned_title:
                        parts = [p.strip() for p in cleaned_title.split("|") if p.strip()]
                        song_part = parts[0]
                        artist_part = parts[1] if len(parts) > 1 else app_label
                    else:
                        song_part = cleaned_title
                        artist_part = app_label

                    info = MediaInfo(
                        title=song_part,
                        artist=artist_part,
                        app_name=app_label,
                        is_playing=True
                    )
                    if is_valid_media_info(info):
                        return info

    return None


class MediaService:
    """
    Singleton background service monitoring Windows Media Sessions (SMTC)
    providing real-time song metadata, album artwork stream, playback status,
    and playback control (Play, Pause, Resume, Next, Previous).
    """
    _instance: Optional['MediaService'] = None

    @classmethod
    def get_instance(cls) -> 'MediaService':
        if cls._instance is None:
            cls._instance = MediaService()
        return cls._instance

    def __init__(self):
        self._current_media: MediaInfo = MediaInfo()
        self._lock = threading.Lock()
        self._running = True
        self._thread: Optional[threading.Thread] = None
        self._listeners: List[Callable[[MediaInfo], None]] = []
        self._cached_art_bytes: Optional[bytes] = None
        self._last_song_key: str = ""

        self._thread = threading.Thread(target=self._worker_loop, daemon=True, name="MediaServiceWorker")
        self._thread.start()

    def add_listener(self, callback: Callable[[MediaInfo], None]):
        with self._lock:
            if callback not in self._listeners:
                self._listeners.append(callback)

    def remove_listener(self, callback: Callable[[MediaInfo], None]):
        with self._lock:
            if callback in self._listeners:
                self._listeners.remove(callback)

    def get_current_media(self) -> MediaInfo:
        with self._lock:
            return self._current_media

    @property
    def current_info(self) -> MediaInfo:
        with self._lock:
            return self._current_media

    def play_pause(self):
        self.toggle_play_pause()

    def skip_previous(self):
        """Skip to previous track."""
        if HAS_WINSDK:
            threading.Thread(target=self._async_call, args=(self._do_skip_previous,), daemon=True).start()
        else:
            send_virtual_media_key(VK_MEDIA_PREV_TRACK)

    def next_track(self):
        self.skip_next()

    def previous_track(self):
        self.skip_previous()

    def volume_up(self):
        volume_up()

    def volume_down(self):
        volume_down()

    def volume_mute(self):
        volume_mute()

    def _notify_listeners(self, info: MediaInfo):
        for cb in list(self._listeners):
            try:
                cb(info)
            except Exception:
                pass

    def _worker_loop(self):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(self._async_monitor())
        except Exception:
            pass
        finally:
            loop.close()

    async def _async_monitor(self):
        while self._running:
            try:
                await self._poll_media_session()
            except Exception:
                pass
            with self._lock:
                playing = self._current_media.is_playing
            sleep_time = 0.8 if playing else 1.5
            await asyncio.sleep(sleep_time)

    async def _poll_media_session(self):
        new_info: Optional[MediaInfo] = None

        if HAS_WINSDK:
            try:
                manager = await MediaManager.request_async()
                if manager:
                    sessions = manager.get_sessions()
                    target_session = None

                    # 1. Prefer playing session with media title
                    if sessions and len(sessions) > 0:
                        for s in sessions:
                            try:
                                pb = s.get_playback_info()
                                if pb and pb.playback_status == 4:  # Playing
                                    props = await s.try_get_media_properties_async()
                                    if props and props.title:
                                        target_session = s
                                        break
                            except Exception:
                                pass

                        if target_session is None:
                            for s in sessions:
                                try:
                                    props = await s.try_get_media_properties_async()
                                    if props and props.title:
                                        target_session = s
                                        break
                                except Exception:
                                    pass

                        if target_session is None:
                            target_session = manager.get_current_session() or sessions[0]
                    else:
                        target_session = manager.get_current_session()

                    if target_session:
                        props = await target_session.try_get_media_properties_async()
                        playback = target_session.get_playback_info()
                        status = playback.playback_status if playback else 0
                        is_playing = (status == 4)

                        title = props.title.strip() if props and props.title else ""
                        artist = props.artist.strip() if props and props.artist else ""
                        album = props.album_title.strip() if props and props.album_title else ""
                        app_id = target_session.source_app_user_model_id or ""
                        app_name = clean_app_name(app_id)

                        # Capture real SMTC timeline position and duration with live offset interpolation
                        pos_sec = 0.0
                        dur_sec = 0.0
                        try:
                            timeline = target_session.get_timeline_properties()
                            if timeline:
                                if timeline.end_time:
                                    dur_sec = max(0.0, timeline.end_time.total_seconds())
                                if timeline.position:
                                    pos_sec = max(0.0, timeline.position.total_seconds())
                                    if is_playing and timeline.last_updated_time:
                                        try:
                                            from datetime import datetime, timezone
                                            now_utc = datetime.now(timezone.utc)
                                            last_utc = timeline.last_updated_time
                                            if hasattr(last_utc, "tzinfo") and last_utc.tzinfo is None:
                                                last_utc = last_utc.replace(tzinfo=timezone.utc)
                                            elapsed = (now_utc - last_utc).total_seconds()
                                            if 0 < elapsed < 7200:
                                                pos_sec += elapsed
                                        except Exception:
                                            pass
                                if dur_sec > 0 and pos_sec > dur_sec:
                                    pos_sec = dur_sec
                        except Exception:
                            pass

                        if title:
                            # Clean YouTube and browser video titles in SMTC
                            if "youtube" in title.lower() or "youtube" in app_id.lower() or app_name in ["Chrome", "Edge", "Brave", "Firefox", "Opera"]:
                                clean_t = re.sub(r"\s*[-—]\s*YouTube(?:\s*Music)?\s*$", "", title, flags=re.IGNORECASE).strip()
                                clean_t = re.sub(r"^\(\d+\+?\)\s*", "", clean_t).strip()
                                clean_t = re.sub(
                                    r"\s*[\(\[](?:Official\s*(?:Music\s*)?Video|Official\s*Audio|Lyric\s*Video|Full\s*(?:Audio|Song|Video)|Audio\s*Track|Video\s*Song|4K|HD|Remastered|Official|Lyrics)[\)\]]",
                                    "",
                                    clean_t,
                                    flags=re.IGNORECASE
                                ).strip()
                                if (not artist or artist.lower() == "youtube") and (" - " in clean_t or " | " in clean_t):
                                    if " - " in clean_t and " | " not in clean_t:
                                        parts = clean_t.split(" - ", 1)
                                        artist = parts[0].strip()
                                        title = parts[1].strip()
                                    elif " | " in clean_t:
                                        parts = [p.strip() for p in clean_t.split("|") if p.strip()]
                                        title = parts[0]
                                        artist = parts[1] if len(parts) > 1 else "YouTube"
                                elif clean_t:
                                    title = clean_t
                                if "youtube" in app_id.lower() or not artist or artist.lower() == "youtube":
                                    app_name = "YouTube"
                                    if not artist:
                                        artist = "YouTube"

                            song_key = f"{app_id}::{title}::{artist}"
                            thumb_bytes = self._cached_art_bytes if (song_key == self._last_song_key and self._cached_art_bytes) else None

                            if thumb_bytes is None and props and props.thumbnail:
                                try:
                                    stream = await props.thumbnail.open_read_async()
                                    size = stream.size
                                    if size > 0:
                                        reader = DataReader(stream)
                                        await reader.load_async(size)
                                        thumb_bytes = bytes(reader.read_buffer(size))
                                except Exception:
                                    thumb_bytes = None

                            self._last_song_key = song_key
                            self._cached_art_bytes = thumb_bytes

                            new_info = MediaInfo(
                                title=title,
                                artist=artist,
                                album=album,
                                app_name=app_name,
                                is_playing=is_playing,
                                thumbnail_bytes=thumb_bytes,
                                position_sec=pos_sec,
                                duration_sec=dur_sec,
                            )
            except Exception:
                pass

        # 2. If WinSDK returned no title, fallback to active window title scraping
        if new_info is None or not new_info.title:
            win_info = detect_song_from_windows()
            if win_info:
                new_info = win_info

        # 3. Strictly validate detected info: reject non-media applications (IDEs, File Explorer, etc.)
        if not is_valid_media_info(new_info):
            new_info = MediaInfo()

        changed = False
        with self._lock:
            if (
                self._current_media.title != new_info.title
                or self._current_media.artist != new_info.artist
                or self._current_media.is_playing != new_info.is_playing
                or (new_info.thumbnail_bytes and not self._current_media.thumbnail_bytes)
                or abs(self._current_media.position_sec - new_info.position_sec) > 1.0
                or abs(self._current_media.duration_sec - new_info.duration_sec) > 1.0
            ):
                self._current_media = new_info
                changed = True

        if changed:
            self._notify_listeners(new_info)

    # ── Media Controls ────────────────────────────────────────────────────────

    def seek_to(self, position_sec: float):
        """Seek playback directly to a specific timestamp in seconds (does not skip track)."""
        with self._lock:
            self._current_media.position_sec = max(0.0, float(position_sec))
            self._current_media.timestamp = time.monotonic()
        if HAS_WINSDK:
            threading.Thread(target=self._async_call, args=(self._create_seek_coro(position_sec),), daemon=True).start()

    def _create_seek_coro(self, position_sec: float):
        async def _coro():
            await self._do_seek(position_sec)
        return _coro

    async def _do_seek(self, position_sec: float):
        try:
            manager = await MediaManager.request_async()
            if not manager:
                return
            session = manager.get_current_session()
            if not session:
                sessions = manager.get_sessions()
                if sessions:
                    for s in sessions:
                        try:
                            pb = s.get_playback_info()
                            if pb and pb.playback_status == 4:
                                session = s
                                break
                        except Exception:
                            pass
                    if not session:
                        session = sessions[0]
            if session:
                ticks = int(max(0.0, position_sec) * 10_000_000)
                await session.try_change_playback_position_async(ticks)
                await self._poll_media_session()
        except Exception:
            pass

    def toggle_play_pause(self):
        """Toggle play/pause on active session or send media key."""
        if HAS_WINSDK:
            threading.Thread(target=self._async_call, args=(self._do_toggle_play_pause,), daemon=True).start()
        else:
            send_virtual_media_key(VK_MEDIA_PLAY_PAUSE)

    def play(self):
        """Resume / Play playback."""
        if HAS_WINSDK:
            threading.Thread(target=self._async_call, args=(self._do_play,), daemon=True).start()
        else:
            send_virtual_media_key(VK_MEDIA_PLAY_PAUSE)

    def pause(self):
        """Pause playback."""
        if HAS_WINSDK:
            threading.Thread(target=self._async_call, args=(self._do_pause,), daemon=True).start()
        else:
            send_virtual_media_key(VK_MEDIA_PLAY_PAUSE)

    def skip_next(self):
        """Skip to next track."""
        if HAS_WINSDK:
            threading.Thread(target=self._async_call, args=(self._do_skip_next,), daemon=True).start()
        else:
            send_virtual_media_key(VK_MEDIA_NEXT_TRACK)

    def play_pause(self):
        self.toggle_play_pause()

    def skip_previous(self):
        """Skip to previous track."""
        if HAS_WINSDK:
            threading.Thread(target=self._async_call, args=(self._do_skip_previous,), daemon=True).start()
        else:
            send_virtual_media_key(VK_MEDIA_PREV_TRACK)

    def next_track(self):
        self.skip_next()

    def previous_track(self):
        self.skip_previous()

    def volume_up(self):
        """Increase master/media volume."""
        volume_up()

    def volume_down(self):
        """Decrease master/media volume."""
        volume_down()

    def volume_mute(self):
        """Toggle mute master/media volume."""
        volume_mute()

    def _async_call(self, coro_func):
        loop = asyncio.new_event_loop()
        try:
            loop.run_until_complete(coro_func())
        except Exception:
            pass
        finally:
            loop.close()

    async def _do_toggle_play_pause(self):
        try:
            manager = await MediaManager.request_async()
            session = manager.get_current_session()
            if session:
                success = await session.try_toggle_play_pause_async()
                if not success:
                    send_virtual_media_key(VK_MEDIA_PLAY_PAUSE)
            else:
                send_virtual_media_key(VK_MEDIA_PLAY_PAUSE)
            await self._poll_media_session()
        except Exception:
            send_virtual_media_key(VK_MEDIA_PLAY_PAUSE)

    async def _do_play(self):
        try:
            manager = await MediaManager.request_async()
            session = manager.get_current_session()
            if session:
                success = await session.try_play_async()
                if not success:
                    send_virtual_media_key(VK_MEDIA_PLAY_PAUSE)
            else:
                send_virtual_media_key(VK_MEDIA_PLAY_PAUSE)
            await self._poll_media_session()
        except Exception:
            send_virtual_media_key(VK_MEDIA_PLAY_PAUSE)

    async def _do_pause(self):
        try:
            manager = await MediaManager.request_async()
            session = manager.get_current_session()
            if session:
                success = await session.try_pause_async()
                if not success:
                    send_virtual_media_key(VK_MEDIA_PLAY_PAUSE)
            else:
                send_virtual_media_key(VK_MEDIA_PLAY_PAUSE)
            await self._poll_media_session()
        except Exception:
            send_virtual_media_key(VK_MEDIA_PLAY_PAUSE)

    async def _do_skip_next(self):
        try:
            manager = await MediaManager.request_async()
            session = manager.get_current_session()
            if session:
                success = await session.try_skip_next_async()
                if not success:
                    send_virtual_media_key(VK_MEDIA_NEXT_TRACK)
            else:
                send_virtual_media_key(VK_MEDIA_NEXT_TRACK)
            await self._poll_media_session()
        except Exception:
            send_virtual_media_key(VK_MEDIA_NEXT_TRACK)

    async def _do_skip_previous(self):
        try:
            manager = await MediaManager.request_async()
            session = manager.get_current_session()
            if session:
                success = await session.try_skip_previous_async()
                if not success:
                    send_virtual_media_key(VK_MEDIA_PREV_TRACK)
            else:
                send_virtual_media_key(VK_MEDIA_PREV_TRACK)
            await self._poll_media_session()
        except Exception:
            send_virtual_media_key(VK_MEDIA_PREV_TRACK)
