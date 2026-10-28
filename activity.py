import ctypes
import ctypes.wintypes
import random
import re
import time
from typing import Optional, List, Tuple
import psutil
from media_service import MediaService, MediaInfo

user32 = ctypes.windll.user32
WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.wintypes.HWND, ctypes.wintypes.LPARAM)

MUSIC_PROCESSES = {
    "spotify.exe", "vlc.exe", "music.ui.exe", "wmplayer.exe",
    "foobar2000.exe", "aimp.exe", "itunes.exe", "tidal.exe", "deezer.exe"
}

MUSIC_WINDOW_KEYWORDS = [
    "spotify", "youtube", "soundcloud", "music", "vlc media player",
    "apple music", "tidal", "deezer", "pandora", "winamp", "groove music"
]

DEV_KEYWORDS = [
    "visual studio", "vscode", "vs code", "cursor", "pycharm", "sublime",
    "terminal", "powershell", "cmd.exe", "github", "git", "bash", "command prompt"
]

BROWSER_KEYWORDS = [
    "google chrome", "chrome", "microsoft edge", "edge", "firefox",
    "brave", "opera", "safari", "stackoverflow", "stack overflow"
]

DOCS_KEYWORDS = [
    "word", "notepad", "notion", "obsidian", "google docs", "excel", "onenote"
]


def get_active_window_title() -> str:
    try:
        hwnd = user32.GetForegroundWindow()
        if not hwnd:
            return ""
        length = user32.GetWindowTextLengthW(hwnd)
        if length > 0:
            buff = ctypes.create_unicode_buffer(length + 1)
            user32.GetWindowTextW(hwnd, buff, length + 1)
            return buff.value.strip()
    except Exception:
        pass
    return ""


def get_all_open_window_titles() -> List[str]:
    titles = []
    try:
        def enum_cb(hwnd, lparam):
            if user32.IsWindowVisible(hwnd):
                length = user32.GetWindowTextLengthW(hwnd)
                if length > 0:
                    buff = ctypes.create_unicode_buffer(length + 1)
                    user32.GetWindowTextW(hwnd, buff, length + 1)
                    val = buff.value.strip()
                    if val:
                        titles.append(val)
            return True
        user32.EnumWindows(WNDENUMPROC(enum_cb), 0)
    except Exception:
        pass
    return titles


TYPING_KEYS = [0x08, 0x09, 0x0D, 0x20] + list(range(0x30, 0x3A)) + list(range(0x41, 0x5B))


class ActivityMonitor:
    def __init__(self):
        self._last_check = 0.0
        self._last_typing_time = 0.0
        self._last_typing_check = 0.0
        self._is_typing = False
        self._is_music_playing = False
        self._current_category = "idle"
        self._current_title = ""
        self._current_song = ""
        self._media_service = MediaService.get_instance()

    def is_user_typing(self) -> bool:
        """Detects if user is actively typing right now (rate-limited to minimize syscalls)."""
        now = time.monotonic()
        if now - self._last_typing_check < 0.18:
            return self._is_typing
        self._last_typing_check = now

        for vk in TYPING_KEYS:
            if user32.GetAsyncKeyState(vk) & 0x8000:
                self._last_typing_time = now
                self._is_typing = True
                return True
        self._is_typing = (now - self._last_typing_time) < 2.2
        return self._is_typing

    def update(self) -> Tuple[bool, str]:
        now = time.monotonic()
        if now - self._last_check < 2.5:
            return self._is_music_playing, self._current_category

        self._last_check = now
        active_title = get_active_window_title().lower()
        self._current_title = active_title

        # 1. Check real Media Session first
        media_info = self._media_service.get_current_media()
        if media_info.has_media:
            self._current_song = f"{media_info.display_title()} - {media_info.display_artist()}"
            self._is_music_playing = media_info.is_playing
        else:
            # Check song title from window titles if music keyword in active window
            if any(k in active_title for k in MUSIC_WINDOW_KEYWORDS):
                song = self._detect_song()
                self._current_song = song if song else ""
                self._is_music_playing = bool(self._current_song)
            else:
                self._current_song = ""
                self._is_music_playing = False

        # Check current activity category
        if self._is_music_playing:
            self._current_category = "music"
        elif any(k in active_title for k in DEV_KEYWORDS):
            self._current_category = "coding"
        elif any(k in active_title for k in DOCS_KEYWORDS):
            self._current_category = "writing"
        elif any(k in active_title for k in BROWSER_KEYWORDS):
            self._current_category = "browsing"
        else:
            self._current_category = "idle"

        return self._is_music_playing, self._current_category

    def _detect_song(self) -> Optional[str]:
        """Detect currently playing song from Media Session or window titles."""
        media_info = self._media_service.get_current_media()
        if media_info.has_media:
            if media_info.artist:
                return f"{media_info.title} - {media_info.artist}"
            return media_info.title

        all_titles = get_all_open_window_titles()

        # 1. YouTube check in any browser
        for t in all_titles:
            if " - YouTube" in t or " - youtube" in t.lower():
                cleaned = re.sub(r"\s*-\s*YouTube.*$", "", t, flags=re.IGNORECASE)
                cleaned = re.sub(r"^\(\d+\)\s*", "", cleaned).strip()
                if cleaned and cleaned.lower() != "youtube":
                    return cleaned

        # 2. Spotify check: Spotify window title is 'Artist - Track'
        for t in all_titles:
            t_low = t.lower()
            if " - " in t:
                # Exclude browser / code editor titles
                if not any(k in t_low for k in ["visual studio", "vs code", "cursor", "pycharm", "github", "stack overflow", "google chrome", "microsoft edge"]):
                    if any(p in t_low for p in ["spotify", "vlc", "music", "sound", "track"]):
                        cleaned = re.sub(r"\s*-\s*VLC media player.*$", "", t, flags=re.IGNORECASE)
                        cleaned = re.sub(r"\s*-\s*SoundCloud.*$", "", cleaned, flags=re.IGNORECASE)
                        cleaned = re.sub(r"^\(\d+\)\s*", "", cleaned).strip()
                        return cleaned

        # 3. Check for any title with " - SoundCloud"
        for t in all_titles:
            if " - soundcloud" in t.lower():
                cleaned = re.sub(r"\s*-\s*SoundCloud.*$", "", t, flags=re.IGNORECASE)
                cleaned = re.sub(r"^\(\d+\)\s*", "", cleaned).strip()
                return cleaned

        # 4. Check for VLC
        for t in all_titles:
            if " - vlc media player" in t.lower():
                cleaned = re.sub(r"\s*-\s*VLC media player.*$", "", t, flags=re.IGNORECASE).strip()
                if cleaned:
                    return cleaned

        return None

    def get_now_playing_message(self) -> str:
        song = self._detect_song()
        if song:
            return f"🎶 Now Playing:\n{song}\n🎵✨"
        return "No music detected right now! 🎵\nPlay a song on Spotify/YouTube and I'll vibe to it!"

    def get_context_message(self) -> str:
        song = self._detect_song()
        if song and self._is_music_playing:
            return f"🎶 Listening to:\n{song}\n🎵 Loving the beat!"

        cat = self._current_category
        if self._is_music_playing:
            return random.choice([
                "Vibing to your tunes! 🎵🎧",
                "Great music taste! 🎶",
                "Dancing along with the beat! 💃✨",
                "This melody is super catchy! 🎼",
            ])

        if cat == "coding":
            return random.choice([
                "Coding hard? Remember to test your changes! 💻",
                "Debugging like a champion! 🚀",
                "Got an idea? I'm brainstorming with you! 💡",
                "Clean code makes a happy alien pet! ✨",
                "Don't forget to take short water breaks! 💧",
            ])
        elif cat == "browsing":
            return random.choice([
                "Researching something cool? 🌐",
                "Found what you were looking for? 🔍",
                "Learning something new today! 📚",
                "Surfing the digital universe! 🚀",
            ])
        elif cat == "writing":
            return random.choice([
                "Writing a masterpiece! 📝",
                "Words flowing smoothly! ✍️",
                "Great focus! Keep it up! 🌟",
            ])
        else:
            return random.choice([
                "I'm keeping you company! 😊",
                "Click me 5 times to toggle cursor following! 🎯",
                "Right-click me to see all my actions! 🎮",
                "Hope you're having an awesome day! ✨",
                "Stay hydrated and smile! 💧",
            ])
