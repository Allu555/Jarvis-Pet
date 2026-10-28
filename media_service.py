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
    ):
        self.title = title
        self.artist = artist
        self.album = album
        self.app_name = app_name
        self.is_playing = is_playing
        self.thumbnail_bytes = thumbnail_bytes
        self.position_sec = position_sec
        self.duration_sec = duration_sec

    @property
    def has_media(self) -> bool:
        return bool(self.title or self.artist)

    def display_title(self) -> str:
        return self.title or "Unknown Track"

    def display_artist(self) -> str:
        return self.artist or self.album or self.app_name or "Unknown Artist"

    def __repr__(self) -> str:
        return f"<MediaInfo title='{self.title}' artist='{self.artist}' app='{self.app_name}' playing={self.is_playing} pos={self.position_sec:.1f}/{self.duration_sec:.1f}s thumb={bool(self.thumbnail_bytes)}>"


WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.wintypes.HWND, ctypes.wintypes.LPARAM)


def _get_window_titles_and_hwnds() -> List[Tuple[int, str]]:
    results = []
    def enum_cb(hwnd, _):
        if user32.IsWindowVisible(hwnd):
            length = user32.GetWindowTextLengthW(hwnd)
            if length > 0:
                buf = ctypes.create_unicode_buffer(length + 1)
                user32.GetWindowTextW(hwnd, buf, length + 1)
                val = buf.value.strip()
                if val:
                    results.append((hwnd, val))
        return True
    try:
        user32.EnumWindows(WNDENUMPROC(enum_cb), 0)
    except Exception:
        pass
    return results


def detect_song_from_windows() -> Optional[MediaInfo]:
    windows = _get_window_titles_and_hwnds()

    # 1. Spotify check: Spotify window title is 'Artist - Song' when playing
    for hwnd, title in windows:
        t_lower = title.lower()
        if " - " in title:
            # Exclude browser / code editor titles unless it's a known media app
            if any(k in t_lower for k in ["visual studio", "vs code", "cursor", "pycharm", "github", "stack overflow"]):
                continue
            if "spotify" in t_lower or "spotify.exe" in t_lower:
                parts = title.split(" - ", 1)
                if len(parts) == 2 and not any(k in parts[0].lower() for k in ["spotify", "advertisement"]):
                    return MediaInfo(
                        title=parts[1].strip(),
                        artist=parts[0].strip(),
                        app_name="Spotify",
                        is_playing=True
                    )

    # 2. YouTube / YouTube Music in Browser
    for hwnd, title in windows:
        t_lower = title.lower()
        if " - youtube" in t_lower or "youtube music" in t_lower:
            # Strip browser names & notification counts
            clean = re.sub(r"\s*-\s*(Google Chrome|Microsoft Edge|Brave|Firefox|Opera).*$", "", title, flags=re.IGNORECASE)
            clean = re.sub(r"\s*-\s*YouTube\s*(Music)?.*$", "", clean, flags=re.IGNORECASE)
            clean = re.sub(r"^\(\d+\)\s*", "", clean).strip()
            if clean and clean.lower() not in ["youtube", "youtube music", "home", "subscriptions"]:
                # If title contains " - ", extract artist and title
                if " - " in clean:
                    parts = clean.split(" - ", 1)
                    return MediaInfo(
                        title=parts[1].strip(),
                        artist=parts[0].strip(),
                        app_name="YouTube",
                        is_playing=True
                    )
                return MediaInfo(
                    title=clean,
                    artist="YouTube Music",
                    app_name="YouTube",
                    is_playing=True
                )

    # 3. VLC Media Player
    for hwnd, title in windows:
        if " - vlc media player" in title.lower():
            clean = re.sub(r"\s*-\s*VLC media player.*$", "", title, flags=re.IGNORECASE).strip()
            if clean:
                if " - " in clean:
                    parts = clean.split(" - ", 1)
                    return MediaInfo(
                        title=parts[1].strip(),
                        artist=parts[0].strip(),
                        app_name="VLC",
                        is_playing=True
                    )
                return MediaInfo(
                    title=clean,
                    artist="VLC Player",
                    app_name="VLC",
                    is_playing=True
                )

    # 4. SoundCloud
    for hwnd, title in windows:
        if " - soundcloud" in title.lower() or "on soundcloud" in title.lower():
            clean = re.sub(r"\s*-\s*SoundCloud.*$", "", title, flags=re.IGNORECASE)
            clean = re.sub(r"^\(\d+\)\s*", "", clean).strip()
            if clean:
                if " by " in clean:
                    parts = clean.split(" by ", 1)
                    return MediaInfo(
                        title=parts[0].strip(),
                        artist=parts[1].strip(),
                        app_name="SoundCloud",
                        is_playing=True
                    )
                return MediaInfo(
                    title=clean,
                    artist="SoundCloud",
                    app_name="SoundCloud",
                    is_playing=True
                )

    # 5. Generic Spotify window if title has ' - '
    for hwnd, title in windows:
        if " - " in title and not any(k in title.lower() for k in ["chrome", "edge", "code", "studio", "firefox", "brave", "python", "cmd", "powershell"]):
            parts = title.split(" - ", 1)
            if len(parts) == 2 and len(parts[0]) > 1 and len(parts[1]) > 1:
                return MediaInfo(
                    title=parts[1].strip(),
                    artist=parts[0].strip(),
                    app_name="Media",
                    is_playing=True
                )

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

                        # Capture real SMTC timeline position and duration
                        pos_sec = 0.0
                        dur_sec = 0.0
                        try:
                            timeline = target_session.get_timeline_properties()
                            if timeline:
                                if timeline.position:
                                    pos_sec = timeline.position.total_seconds()
                                if timeline.end_time:
                                    dur_sec = timeline.end_time.total_seconds()
                        except Exception:
                            pass

                        if title:
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

        if new_info is None:
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
        if HAS_WINSDK:
            threading.Thread(target=self._async_call, args=(self._create_seek_coro(position_sec),), daemon=True).start()

    def _create_seek_coro(self, position_sec: float):
        async def _coro():
            await self._do_seek(position_sec)
        return _coro

    async def _do_seek(self, position_sec: float):
        try:
            manager = await MediaManager.request_async()
            session = manager.get_current_session()
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
