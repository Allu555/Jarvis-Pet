"""
brain/intent.py – Ultra-fast local intent matching for instant JARVIS actions.

Bypasses slow cloud LLM roundtrips (5-9s) for common desktop commands:
- Media controls (pause, play, volume, mute)
- App launching & web navigation (YouTube, Chrome, Notepad, etc.)
- System info (time, battery, screenshot, lock screen)
- Window controls (minimize, maximize, close)
- Web search and direct typing

Returns (tool_name, tool_args) or None if the command requires general LLM reasoning.
"""

import re
import logging

logger = logging.getLogger("jarvis.brain.intent")

# Known application names mapped for fast launching
FAST_APP_NAMES = {
    "chrome", "google chrome", "notepad", "calculator", "calc",
    "spotify", "youtube", "brave", "edge", "code", "vscode", "vs code",
    "word", "excel", "powerpoint", "paint", "settings", "camera",
    "terminal", "cmd", "powershell", "task manager", "file explorer",
    "explorer", "discord", "telegram", "vlc", "zoom", "teams", "obs"
}


def try_fast_intent(command: str) -> tuple[str, dict] | None:
    """
    Parse a user command for instant local actions.
    Returns (tool_name, tool_args) or None if complex reasoning is needed.
    """
    if not command or not command.strip():
        return None

    # Strip leading wake words, polite prefixes, and punctuation
    c = re.sub(r'^(hey\s+)?(jarvis|service|harvest|javis|charvis)[,\s]+', '', command.strip(), flags=re.IGNORECASE).strip()
    c = re.sub(r'^(please|can you|could you|would you)\s+', '', c, flags=re.IGNORECASE).strip()
    c = c.strip(" ,.!?:\n\t")
    c_lower = c.lower().strip()
    c_lower = re.sub(r'\b(support\s+design|sportify|spottify|spot\s+if\s+i|spotty)\b', 'spotify', c_lower)

    if not c_lower:
        return None

    # ── 1. Time / Clock / Date ────────────────────────────────────────────────
    if re.search(r'\b(time|what time|what time is it|what is the time|current time|tell me the time|time please|date|what date|what is the date|today\'s date|current date)\b', c_lower) or c_lower in ("time", "date"):
        return ("get_time", {})

    # ── 2. Media Controls (Toggle play / pause) ───────────────────────────────
    if re.search(r'^(pause|play|resume|unpause|play\s+pause)(\s+(it|this|media|the\s+video|video|the\s+music|music|the\s+song))?$', c_lower):
        return ("play_pause_media", {})
    if re.search(r'\b(play\s*pause|pause\s+video|resume\s+video|pause\s+music|resume\s+music)\b', c_lower):
        return ("play_pause_media", {})

    # ── 3. Volume & Audio ─────────────────────────────────────────────────────
    if re.search(r'\b(volume up|increase volume|raise volume|turn up the volume|louder)\b', c_lower):
        return ("volume_up", {})
    if re.search(r'\b(volume down|decrease volume|lower volume|turn down the volume|quieter)\b', c_lower):
        return ("volume_down", {})
    if re.search(r'\b(mute|unmute|mute audio|mute volume|silence)\b', c_lower):
        return ("volume_mute", {})

    # ── 4. Battery / Power ────────────────────────────────────────────────────
    if re.search(r'\b(battery|battery status|battery percentage|battery level|power status)\b', c_lower):
        return ("battery_status", {})

    # ── 5. Lock Screen ────────────────────────────────────────────────────────
    if re.search(r'\b(lock screen|lock pc|lock computer|lock windows)\b', c_lower) or c_lower == "lock":
        return ("lock_screen", {})

    # ── 6. Screenshot ─────────────────────────────────────────────────────────
    if re.search(r'\b(take a screenshot|take screenshot|capture screen|screenshot)\b', c_lower):
        return ("take_screenshot", {})

    # ── 7. Window Management ──────────────────────────────────────────────────
    if re.search(r'\b(minimize window|minimize it|minimize all)\b', c_lower) or c_lower == "minimize":
        return ("minimize_window", {"title": ""})
    if re.search(r'\b(maximize window|maximize it|fullscreen)\b', c_lower) or c_lower == "maximize":
        return ("maximize_window", {"title": ""})
    if re.search(r'\b(close window|close application|close this|close it)\b', c_lower):
        return ("close_application", {"name": ""})

    # ── 8. Spotify Song & Music Playback ──────────────────────────────────────
    # e.g. "open spotify and play a song animal", "play animal on spotify", "open spotify then search song animal and play for me"
    m_spot = re.search(r'open\s+spotify\s+(?:and|then)?\s*(?:search\s+(?:for\s+)?(?:and|then)\s+play|search\s+and\s+play|play)\s+(?:a\s+song\s+|the\s+song\s+|song\s+)?(.+)', c_lower)
    if not m_spot:
        m_spot = re.search(r'play\s+(?:a\s+song\s+|the\s+song\s+|song\s+)?(.+?)\s+(?:on|in)\s+spotify', c_lower)
    if not m_spot:
        m_spot = re.search(r'open\s+spotify\s+(?:and|then)?\s*search\s+(?:for\s+)?(?:a\s+song\s+|the\s+song\s+|song\s+)?(.+)', c_lower)
    if not m_spot:
        # e.g. "play a song animal", "play song animal" (default to Spotify)
        m_spot = re.search(r'^play\s+(?:a\s+song|the\s+song|song)\s+(.+)', c_lower)
    if m_spot:
        raw_song = m_spot.group(1).strip(" .!?")
        raw_song = re.sub(r'\s+(and\s+play.*|by\s+clicking.*|for\s+me|please|fast|now)$', '', raw_song, flags=re.IGNORECASE).strip(" .!?")
        if raw_song:
            return ("play_spotify", {"query": raw_song})

    # ── 9. YouTube Video / Music Playback ─────────────────────────────────────
    # e.g. "open youtube and play animal", "play faded on youtube"
    m_yt = re.search(r'open\s+youtube\s+(?:and|then)?\s*(?:search\s+(?:for\s+)?(?:and|then)\s+play|search\s+and\s+play|play)\s+(?:a\s+song\s+|the\s+song\s+|song\s+|video\s+)?(.+)', c_lower)
    if not m_yt:
        m_yt = re.search(r'play\s+(?:a\s+song\s+|the\s+song\s+|song\s+|video\s+)?(.+?)\s+(?:on|in)\s+youtube', c_lower)
    if not m_yt:
        m_yt = re.search(r'open\s+youtube\s+(?:and|then)?\s*search\s+(?:for\s+)?(?:a\s+song\s+|the\s+song\s+|song\s+|video\s+)?(.+)', c_lower)
    if m_yt:
        raw_yt = m_yt.group(1).strip(" .!?")
        raw_yt = re.sub(r'\s+(and\s+play.*|by\s+clicking.*|for\s+me|please|fast|now)$', '', raw_yt, flags=re.IGNORECASE).strip(" .!?")
        if raw_yt:
            return ("play_youtube", {"query": raw_yt})

    # ── 10. Multi-App Open & Search ───────────────────────────────────────────
    # e.g. "open brave and search weather in tokyo", "open chrome and search react docs"
    m_app_search = re.search(r'^(open|launch)\s+([a-z0-9_\s]+?)\s+(and|then)\s+search\s+(for\s+)?(.+)', c_lower)
    if m_app_search:
        app = m_app_search.group(2).strip()
        query = m_app_search.group(5).strip(" .!?")
        query = re.sub(r'\s+(for\s+me|please|fast|now)$', '', query, flags=re.IGNORECASE).strip(" .!?")
        if app in ("spotify",):
            return ("play_spotify", {"query": query})
        if app in ("youtube",):
            return ("play_youtube", {"query": query})
        if app in ("google", "browser", "chrome", "brave", "edge", "firefox"):
            return ("web_search", {"query": query})
        return ("open_and_search", {"app": app, "query": query})

    # ── 11. Direct Web Search ──────────────────────────────────────────────────
    # e.g. "search google for kerala weather", "google python list methods", "search for tesla"
    m_search = re.search(r'^(search\s+for|search\s+google\s+for|google|search)\s+(.+)', c_lower)
    if m_search:
        query = m_search.group(2).strip(" .!?")
        if query:
            return ("web_search", {"query": query})

    # ── 10. In <app> write <topic> or Write <topic> in <app> ──────────────────
    # e.g. "In Notepad, write a program for Hello World in Python."
    m_in_app = re.search(r'^in\s+([a-z0-9_\s]+?)[,\s]+(write|type|code)\s+(.+)', c_lower)
    if m_in_app:
        app = m_in_app.group(1).strip()
        topic = m_in_app.group(3).strip(" .!?")
        return ("open_and_write", {"app": app, "topic": topic})

    # e.g. "Write a python script in notepad", "write hello world in notepad"
    m_write_in = re.search(r'^(write|type|code)\s+(.+?)\s+in\s+([a-z0-9_\s]+)$', c_lower)
    if m_write_in:
        app = m_write_in.group(3).strip()
        topic = m_write_in.group(2).strip(" .!?")
        return ("open_and_write", {"app": app, "topic": topic})

    # e.g. "Open notepad and write a python script"
    m_open_and = re.search(r'^(open|launch)\s+([a-z0-9_\s]+?)\s+and\s+(write|type|code)\s+(.+)', c_lower)
    if m_open_and:
        app = m_open_and.group(2).strip()
        topic = m_open_and.group(4).strip(" .!?")
        return ("open_and_write", {"app": app, "topic": topic})

    # ── 11. Type <text> in/on <element> ───────────────────────────────────────
    # e.g. "type animal on search bar", "type python in search box"
    m_click_type = re.search(r'^type\s+(.+?)\s+(on|in|into)\s+(the\s+)?(.+)', c_lower)
    if m_click_type:
        text = m_click_type.group(1).strip()
        elem = m_click_type.group(4).strip(" .!?")
        if elem not in FAST_APP_NAMES:
            return ("click_and_type", {"description": elem, "text": text})

    # ── 12. Click on <element> ────────────────────────────────────────────────
    # e.g. "click on the search bar", "click the first video", "click submit"
    m_click = re.search(r'^(click|tap)\s+(on\s+)?(the\s+)?(.+)', c_lower)
    if m_click:
        target = m_click.group(4).strip(" .!?")
        if target and target not in ("enter", "space", "escape", "tab", "backspace", "up", "down", "left", "right"):
            return ("click_element_by_description", {"description": target})

    # Double click
    m_dclick = re.search(r'^(double\s+click)\s+(on\s+)?(the\s+)?(.+)', c_lower)
    if m_dclick:
        target = m_dclick.group(4).strip(" .!?")
        if target:
            return ("click_element_by_description", {"description": target})

    # ── 13. Direct Plain Typing ───────────────────────────────────────────────
    # e.g. "type hello world", "write congratulations"
    m_type = re.search(r'^(type|write)\s+(.+)', c_lower)
    if m_type:
        text = m_type.group(2).strip()
        if text and not text.startswith("a ") and not text.startswith("an "):
            return ("type_text", {"text": text})

    # ── 14. Open Application / Website ────────────────────────────────────────
    # Matches: "open youtube", "open chrome", "launch notepad", "open calculator"
    m_open = re.search(r'^(open|launch|start)\s+(.+)', c_lower)
    if m_open:
        target = m_open.group(2).strip(" .!?")
        if target:
            # Special case for youtube
            if target in ("youtube", "you tube"):
                return ("open_url", {"url": "https://www.youtube.com"})
            # Any known friendly app or URL
            return ("open_application", {"name": target})

    # Just app name by itself (e.g. user just said "youtube" or "chrome" or "calculator")
    if c_lower in FAST_APP_NAMES:
        if c_lower in ("youtube", "you tube"):
            return ("open_url", {"url": "https://www.youtube.com"})
        return ("open_application", {"name": c_lower})

    return None
