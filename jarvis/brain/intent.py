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

from __future__ import annotations

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


FAST_URLS = {
    "github": "https://github.com",
    "git hub": "https://github.com",
    "google": "https://www.google.com",
    "youtube": "https://www.youtube.com",
    "chatgpt": "https://chatgpt.com",
    "chat gpt": "https://chatgpt.com",
    "reddit": "https://www.reddit.com",
    "twitter": "https://x.com",
    "netflix": "https://www.netflix.com",
    "spotify": "https://open.spotify.com",
    "linkedin": "https://www.linkedin.com",
    "wikipedia": "https://www.wikipedia.org"
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
    c_lower = re.sub(r'\bnote\s*pad\b', 'notepad', c_lower)
    c_lower = re.sub(r'\bvs\s*code\b', 'code', c_lower)
    c_lower = re.sub(r'\byou\s*tube\b', 'youtube', c_lower)

    if not c_lower:
        return None

    # ── 0. Conversational Fast Path (0ms instant response) ──────────────────────
    if re.search(r'^(hi|hello|hey|yo|sup|greetings|good\s+(morning|afternoon|evening|night))(\s+jarvis)?$', c_lower) or c_lower in ("hi", "hello", "hey", "yo", "sup", "greetings", "namaste", "namaskaram"):
        return ("direct_reply", {"message": "Hello! How can I assist you today, sir?"})

    if re.search(r'^(how\s+are\s+you|how\'s\s+it\s+going|how\s+are\s+you\s+doing)(\s+jarvis|\s+today)?$', c_lower):
        return ("direct_reply", {"message": "Operating at peak performance. How can I help you, sir?"})

    if re.search(r'^(who\s+are\s+you|what\s+is\s+your\s+name|what\'s\s+your\s+name)$', c_lower):
        return ("direct_reply", {"message": "I am JARVIS, your Windows AI assistant."})

    if re.search(r'^(what\s+can\s+you\s+do|help|what\s+are\s+your\s+commands)$', c_lower):
        return ("direct_reply", {"message": "I can open apps, write text in Notepad, control media & Spotify, inspect your screen, and automate tasks."})

    if re.search(r'^(thank\s+you|thanks|thank\s+you\s+so\s+much)(\s+jarvis)?$', c_lower):
        return ("direct_reply", {"message": "You are very welcome, sir!"})

    if re.search(r'^(bye|goodbye|see\s+you|exit|quit)(\s+jarvis)?$', c_lower):
        return ("direct_reply", {"message": "Goodbye, sir! Call me whenever you need me."})

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

    # ── 6b. System Info / Hardware Status ────────────────────────────────────
    if re.search(r'\b(system info|system status|pc status|computer status|cpu usage|ram usage|memory usage|pc specs|hardware status)\b', c_lower):
        return ("system_info", {})

    # ── 6c. Live Weather & Temperature ───────────────────────────────────────
    m_w = re.search(r'\b(?:what(?:\'s|\s+is)\s+the\s+)?(?:weather|temperature|forecast)(?:\s+(?:like\s+)?(?:in|at|for)\s+([a-zA-Z\s]+))?', c_lower)
    if m_w:
        loc = (m_w.group(1) or "").strip(" .!?")
        return ("get_weather", {"location": loc})

    # ── 6d. Real-time News Headlines ──────────────────────────────────────────
    m_news = re.search(r'\b(?:what(?:\'s|\s+is)\s+the\s+)?(?:latest\s+)?(?:news|headlines)(?:\s+(?:on|about|for)\s+([a-zA-Z\s]+))?', c_lower)
    if m_news:
        topic = (m_news.group(1) or "general").strip(" .!?")
        return ("get_news", {"topic": topic})

    # ── 6e. Drag & Drop on Screen ─────────────────────────────────────────────
    m_drag = re.search(r'^drag\s+(?:the\s+)?(.+?)\s+(?:to|into|onto)\s+(?:the\s+)?(.+)', c_lower)
    if m_drag:
        start_desc = m_drag.group(1).strip(" .!?")
        end_desc = m_drag.group(2).strip(" .!?")
        return ("drag_with_description", {"start_description": start_desc, "end_description": end_desc})

    # ── 6f. Reminders ─────────────────────────────────────────────────────────
    m_rem = re.search(r'remind\s+me\s+(?:in\s+)?(\d+)\s*([a-z]+)?\s+(?:to|that|about)\s+(.+)', c_lower)
    if not m_rem:
        m_rem = re.search(r'remind\s+me\s+(?:in\s+)?(\d+)\s*([a-z]+)?', c_lower)
    if m_rem:
        val = int(m_rem.group(1))
        unit = (m_rem.group(2) or "minute").lower()
        msg = (m_rem.group(3) if len(m_rem.groups()) >= 3 and m_rem.group(3) else "your reminder").strip(" .!?")
        mult = 60
        if unit.startswith("s"): mult = 1
        elif unit.startswith("m"): mult = 60
        elif unit.startswith("h"): mult = 3600
        return ("set_reminder", {"seconds": val * mult, "message": msg})

    # ── 7. Window Management ──────────────────────────────────────────────────
    m_min = re.search(r'^(?:minimize|hide)(?:\s+(?:the\s+|this\s+)?window)?(?:\s+(.+))?$', c_lower)
    if m_min:
        tgt = (m_min.group(1) or "").strip(" .!?")
        if tgt in ("it", "this", "window", "all"): tgt = ""
        return ("minimize_window", {"title": tgt})

    if re.search(r'^(?:open|show)\s+(?:it\s+)?again$', c_lower) or c_lower in ("open again", "open it again", "open it", "show again", "bring it back", "restore", "unminimize"):
        return ("restore_window", {"title": ""})

    m_rest = re.search(r'^(?:restore|unminimize|un-minimize|bring\s+back)(?:\s+(?:the\s+|this\s+)?window)?(?:\s+(.+))?$', c_lower)
    if m_rest:
        tgt = (m_rest.group(1) or "").strip(" .!?")
        if tgt in ("it", "this", "window"): tgt = ""
        return ("restore_window", {"title": tgt})

    m_max = re.search(r'^(?:maximize|fullscreen)(?:\s+(?:the\s+|this\s+)?window)?(?:\s+(.+))?$', c_lower)
    if m_max:
        tgt = (m_max.group(1) or "").strip(" .!?")
        if tgt in ("it", "this", "window"): tgt = ""
        return ("maximize_window", {"title": tgt})

    if re.search(r'^(?:close|quit|exit)\s+(?:the\s+|this\s+)?window$', c_lower) or c_lower in ("close window", "close this", "close it"):
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

    # ── 10. In <app> write <topic> or Write <topic> in <app> or Open <app> and write/do <topic> ──
    # e.g. "open notepad and do code of hello world in python", "open notepad and write python script"
    m_open_and = re.search(
        r'^(?:open|launch|start)\s+([a-z0-9_]+)\s+and\s+(?:write|type|code|do|make|create|generate)(?:\s+(?:code|program|script|a\s+code|a\s+program))?(?:\s+(?:of|for|to))?\s+(.+)',
        c_lower
    )
    if m_open_and:
        app = m_open_and.group(1).strip()
        topic = m_open_and.group(2).strip(" .!?")
        return ("open_and_write", {"app": app, "topic": topic})

    # e.g. "in notepad write hello world in python"
    m_in_app = re.search(
        r'^in\s+([a-z0-9_]+)[,\s]+(?:write|type|code|do|make|create|generate)(?:\s+(?:code|program|script|a\s+code|a\s+program))?(?:\s+(?:of|for|to))?\s+(.+)',
        c_lower
    )
    if m_in_app:
        app = m_in_app.group(1).strip()
        topic = m_in_app.group(2).strip(" .!?")
        return ("open_and_write", {"app": app, "topic": topic})

    # e.g. "write hello world in python in notepad", "do code of hello world in notepad"
    m_write_in = re.search(
        r'^(?:write|type|code|do|make|create|generate)(?:\s+(?:code|program|script|a\s+code|a\s+program))?(?:\s+(?:of|for|to))?\s+(.+?)\s+in\s+([a-z0-9_]+)$',
        c_lower
    )
    if m_write_in:
        app = m_write_in.group(2).strip()
        topic = m_write_in.group(1).strip(" .!?")
        return ("open_and_write", {"app": app, "topic": topic})

    # e.g. "do code of hello world in python" (defaults to notepad)
    m_prog_req = re.search(
        r'^(?:write|code|create|generate|do)\s+(?:code\s+(?:of|for)|program\s+(?:of|for)|script\s+(?:of|for)|a\s+program\s+(?:of|for))?\s*(.+?\s+in\s+(?:python|c\+\+|cpp|c|java|javascript|html|rust|go))$',
        c_lower
    )
    if m_prog_req:
        topic = m_prog_req.group(1).strip(" .!?")
        return ("open_and_write", {"app": "notepad", "topic": topic})

    # ── 11. Type <text> in/on <element> ───────────────────────────────────────
    # e.g. "type animal on search bar", "type python in search box"
    m_click_type = re.search(r'^type\s+(.+?)\s+(on|in|into)\s+(the\s+)?(.+)', c_lower)
    if m_click_type:
        text = m_click_type.group(1).strip()
        elem = m_click_type.group(4).strip(" .!?")
        if elem not in FAST_APP_NAMES:
            return ("click_and_type", {"description": elem, "text": text})

    # ── 12. Click on <element> / Link ─────────────────────────────────────────
    # e.g. "open the link", "click the link", "click first link"
    if re.search(r'^(?:open|click|tap)(?:\s+on)?\s+(?:the\s+)?(?:first\s+)?link$', c_lower) or c_lower in ("open the link", "click the link", "open link", "click link", "open first link"):
        return ("click_element_by_description", {"description": "link"})

    # e.g. "github and open the link", "open github and open the link", "go to github"
    for site, u in FAST_URLS.items():
        if site in c_lower and any(w in c_lower for w in ("open", "link", "go to", "launch", "visit")):
            return ("open_url", {"url": u})

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

    # ── 13b. Browser Tab Controls ─────────────────────────────────────────────
    # e.g. "open another tab", "open another tab in chrome", "open a new tab", "open new tab in chrome", "new tab in chrome", "new tab"
    m_tab = re.search(r'^(?:open|launch|create)?\s*(?:another|a\s+new|new)?\s*tab(?:\s+in\s+([a-z0-9_]+))?(?:\s+(?:for|with|to)\s+(.+))?$', c_lower)
    if not m_tab:
        m_tab = re.search(r'^(?:open|launch)\s+([a-z0-9_]+)\s+(?:and\s+)?(?:open\s+)?(?:another|a\s+new|new)?\s*tab(?:\s+(?:for|with|to)\s+(.+))?$', c_lower)
    if m_tab:
        browser = m_tab.group(1) or ""
        url = m_tab.group(2) or ""
        return ("open_browser_tab", {"browser": browser, "url": url})

    if re.search(r'^(?:close|shut)\s+(?:this\s+|the\s+|current\s+)?tab$', c_lower):
        return ("close_browser_tab", {})

    if re.search(r'^(?:next\s+tab|switch\s+tab|go\s+to\s+next\s+tab)$', c_lower):
        return ("switch_next_tab", {})

    if re.search(r'^(?:previous|prev)\s+tab$', c_lower):
        return ("switch_prev_tab", {})

    if re.search(r'^(?:reopen|undo\s+close)\s+(?:closed\s+)?tab$', c_lower):
        return ("reopen_closed_tab", {})

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
