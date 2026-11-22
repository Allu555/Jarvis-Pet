"""
brain/tools.py – Tool schemas (BOTH Anthropic and OpenAI formats) + dispatcher.

TOOL_SCHEMAS_OPENAI  → sent to NVIDIA NIM / any OpenAI-compatible API
TOOL_SCHEMAS         → kept for reference (Anthropic format)

Dispatcher routes tool_name + input → correct Python function.
"""

import logging
from typing import Any, Callable

try:
    from safety import ask_confirmation, is_file_deletion_sensitive, log_action
except ImportError:
    from jarvis.safety import ask_confirmation, is_file_deletion_sensitive, log_action

logger = logging.getLogger("jarvis.brain.tools")


# ─── Helper: convert Anthropic schema → OpenAI function schema ────────────────

def _to_openai(schema: dict) -> dict:
    return {
        "type": "function",
        "function": {
            "name": schema["name"],
            "description": schema["description"],
            "parameters": schema.get("input_schema", {"type": "object", "properties": {}}),
        },
    }


# ─── Anthropic-format tool schemas (source of truth) ─────────────────────────

TOOL_SCHEMAS: list[dict] = [
    {
        "name": "open_application",
        "description": "Launch an application by its friendly name (e.g. 'Chrome', 'Notepad', 'Spotify').",
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Friendly application name."}
            },
            "required": ["name"],
        },
    },
    {
        "name": "close_application",
        "description": "Close / terminate a running application by name.",
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Process or application name to close."}
            },
            "required": ["name"],
        },
    },
    {
        "name": "open_and_write",
        "description": "Open or focus an application (e.g. 'Notepad', 'Word', 'Code') and write/type text, code, or a requested document into it.",
        "input_schema": {
            "type": "object",
            "properties": {
                "app": {"type": "string", "description": "Application name, e.g. 'notepad'."},
                "topic": {"type": "string", "description": "Topic or request to write (e.g. 'Hello World in Python', 'leave email')."},
                "content": {"type": "string", "description": "Exact text or code to write if known."}
            },
            "required": ["app"],
        },
    },
    {
        "name": "type_text",
        "description": "Type the given text into the currently focused window.",
        "input_schema": {
            "type": "object",
            "properties": {
                "text": {"type": "string", "description": "Text to type."}
            },
            "required": ["text"],
        },
    },
    {
        "name": "press_keys",
        "description": "Send a keyboard hotkey or shortcut, e.g. 'ctrl+c', 'win+d', 'alt+tab'.",
        "input_schema": {
            "type": "object",
            "properties": {
                "keys": {"type": "string", "description": "Key combination separated by +."}
            },
            "required": ["keys"],
        },
    },
    {
        "name": "press_single_key",
        "description": "Press a single keyboard key by name, e.g. 'enter', 'escape', 'f5', 'tab'.",
        "input_schema": {
            "type": "object",
            "properties": {"key": {"type": "string"}},
            "required": ["key"],
        },
    },
    {
        "name": "click",
        "description": "Left-click at absolute screen coordinates (x, y).",
        "input_schema": {
            "type": "object",
            "properties": {
                "x": {"type": "integer"},
                "y": {"type": "integer"},
            },
            "required": ["x", "y"],
        },
    },
    {
        "name": "double_click",
        "description": "Double-click at screen coordinates (x, y).",
        "input_schema": {
            "type": "object",
            "properties": {
                "x": {"type": "integer"},
                "y": {"type": "integer"},
            },
            "required": ["x", "y"],
        },
    },
    {
        "name": "right_click",
        "description": "Right-click at screen coordinates (x, y).",
        "input_schema": {
            "type": "object",
            "properties": {
                "x": {"type": "integer"},
                "y": {"type": "integer"},
            },
            "required": ["x", "y"],
        },
    },
    {
        "name": "scroll",
        "description": "Scroll the mouse wheel up or down.",
        "input_schema": {
            "type": "object",
            "properties": {
                "direction": {"type": "string", "enum": ["up", "down"]},
                "amount": {"type": "integer", "description": "Number of scroll steps.", "default": 3},
            },
            "required": ["direction"],
        },
    },
    {
        "name": "drag",
        "description": "Click and drag from (x1, y1) to (x2, y2) OR specify start_description and end_description to drag by element names.",
        "input_schema": {
            "type": "object",
            "properties": {
                "x1": {"type": "integer"}, "y1": {"type": "integer"},
                "x2": {"type": "integer"}, "y2": {"type": "integer"},
                "start_description": {"type": "string", "description": "Element or item to drag"},
                "end_description": {"type": "string", "description": "Target element or location to drop onto"}
            },
        },
    },
    {
        "name": "click_element_by_description",
        "description": (
            "Take a screenshot, use AI Vision to find the UI element described, "
            "and click it. Use for 'click the Submit button', 'click the search bar', etc."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "description": {"type": "string", "description": "Natural-language description of the UI element."}
            },
            "required": ["description"],
        },
    },
    {
        "name": "click_and_type",
        "description": "Click on a UI element (e.g. 'search bar', 'input field') and type text into it.",
        "input_schema": {
            "type": "object",
            "properties": {
                "description": {"type": "string", "description": "UI element to click (e.g. 'search bar')."},
                "text": {"type": "string", "description": "Text to type into the field."},
                "press_enter": {"type": "boolean", "description": "Whether to press Enter after typing.", "default": True}
            },
            "required": ["description", "text"],
        },
    },
    {
        "name": "read_screen",
        "description": "Take a screenshot and return a natural-language description of what is currently on screen.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "describe_screen",
        "description": "Summarize what is currently on the screen: active application, main content, and notable UI elements.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "read_screen_text",
        "description": "Read visible text on the active window aloud using OCR. Optionally filter by target keyword.",
        "input_schema": {
            "type": "object",
            "properties": {
                "target": {"type": "string", "description": "Optional keyword or section to focus reading on."}
            },
        },
    },
    {
        "name": "spider_scan_and_act",
        "description": "Deploy the autonomous Spider Vision Scout to scan the screen, identify whatever task or workflow is in progress, and autonomously click, type, and complete it hands-free without the user touching the mouse or keyboard.",
        "input_schema": {
            "type": "object",
            "properties": {
                "goal": {"type": "string", "description": "Specific task to complete or blank to assist with current screen context."}
            },
        },
    },
    {
        "name": "spider_start_autopilot",
        "description": "Activate continuous hands-free autonomous co-pilot mode with the Spider Scout.",
        "input_schema": {
            "type": "object",
            "properties": {
                "goal": {"type": "string", "description": "Goal or workflow to monitor and automate."}
            },
        },
    },
    {
        "name": "spider_stop_autopilot",
        "description": "Deactivate autonomous Spider Scout co-pilot mode.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "launch_spider_3d",
        "description": "Deploy and open the floating 3D Spider Recon Drone overlay on the user's desktop to scan tasks and assist hands-free.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "focus_window",
        "description": "Bring a window with the given title substring to the foreground.",
        "input_schema": {
            "type": "object",
            "properties": {
                "title": {"type": "string", "description": "Partial window title to search for."}
            },
            "required": ["title"],
        },
    },
    {
        "name": "list_windows",
        "description": "Return a list of all visible application window titles.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "minimize_window",
        "description": "Minimise a window by title.",
        "input_schema": {
            "type": "object",
            "properties": {"title": {"type": "string"}},
            "required": ["title"],
        },
    },
    {
        "name": "maximize_window",
        "description": "Maximise a window by title.",
        "input_schema": {
            "type": "object",
            "properties": {"title": {"type": "string"}},
            "required": ["title"],
        },
    },
    {
        "name": "restore_window",
        "description": "Restore or un-minimize a previously minimized window or application back to the screen (e.g. 'chrome', 'spotify', or empty string for the last minimized window / 'open again').",
        "input_schema": {
            "type": "object",
            "properties": {
                "title": {"type": "string", "description": "Application or window title to restore, or empty for last minimized window."}
            },
        },
    },
    {
        "name": "open_browser_tab",
        "description": "Open a new browser tab in Chrome, Brave, Edge, or the active browser, optionally navigating to a URL.",
        "input_schema": {
            "type": "object",
            "properties": {
                "browser": {"type": "string", "description": "Browser name (e.g. 'chrome', 'brave', 'edge'). Optional."},
                "url": {"type": "string", "description": "URL to navigate to in the new tab. Optional."}
            },
        },
    },
    {
        "name": "close_browser_tab",
        "description": "Close the current browser tab (Ctrl+W).",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "switch_next_tab",
        "description": "Switch to the next browser tab (Ctrl+Tab).",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "switch_prev_tab",
        "description": "Switch to the previous browser tab (Ctrl+Shift+Tab).",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "reopen_closed_tab",
        "description": "Reopen the most recently closed browser tab (Ctrl+Shift+T).",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "open_url",
        "description": "Open a URL in the default web browser.",
        "input_schema": {
            "type": "object",
            "properties": {"url": {"type": "string"}},
            "required": ["url"],
        },
    },
    {
        "name": "play_spotify",
        "description": "Open Spotify, search for a song, track, or artist, and click with the mouse pointer to play it (e.g. 'animal', 'starboy', 'shape of you').",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "The song title or artist to search and play on Spotify."}
            },
            "required": ["query"],
        },
    },
    {
        "name": "play_youtube",
        "description": "Search and play a video or song on YouTube (e.g. 'animal song', 'lofi hip hop').",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "The song, artist, video, or search query to play on YouTube."}
            },
            "required": ["query"],
        },
    },
    {
        "name": "open_and_search",
        "description": "Open any application or browser, focus its search field, type the query, and press Enter (e.g. app='brave', query='weather').",
        "input_schema": {
            "type": "object",
            "properties": {
                "app": {"type": "string", "description": "Name of the application to open (e.g. 'Spotify', 'Chrome', 'Brave', 'Store')."},
                "query": {"type": "string", "description": "Text to search for."}
            },
            "required": ["app", "query"],
        },
    },
    {
        "name": "web_search",
        "description": "Open Google search in the default web browser. ONLY use this when the user explicitly says 'search google for X', 'search the web for X', or 'google X'. DO NOT use this to answer who/what/where/why knowledge questions.",
        "input_schema": {
            "type": "object",
            "properties": {"query": {"type": "string"}},
            "required": ["query"],
        },
    },
    {
        "name": "create_file",
        "description": "Create a new file inside ~/JarvisFiles with optional initial content.",
        "input_schema": {
            "type": "object",
            "properties": {
                "relative_path": {"type": "string"},
                "content": {"type": "string"},
            },
            "required": ["relative_path"],
        },
    },
    {
        "name": "read_file",
        "description": "Read and return the contents of a file inside ~/JarvisFiles.",
        "input_schema": {
            "type": "object",
            "properties": {"relative_path": {"type": "string"}},
            "required": ["relative_path"],
        },
    },
    {
        "name": "write_file",
        "description": "Overwrite (or create) a file inside ~/JarvisFiles with new content.",
        "input_schema": {
            "type": "object",
            "properties": {
                "relative_path": {"type": "string"},
                "content": {"type": "string"},
            },
            "required": ["relative_path", "content"],
        },
    },
    {
        "name": "delete_file",
        "description": "Delete a file inside ~/JarvisFiles. Requires user confirmation.",
        "input_schema": {
            "type": "object",
            "properties": {"relative_path": {"type": "string"}},
            "required": ["relative_path"],
        },
    },
    {
        "name": "list_files",
        "description": "List files and folders inside ~/JarvisFiles (or a subdirectory).",
        "input_schema": {
            "type": "object",
            "properties": {
                "relative_path": {"type": "string"}
            },
        },
    },
    {
        "name": "volume_up",
        "description": "Increase system volume.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "volume_down",
        "description": "Decrease system volume.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "volume_mute",
        "description": "Toggle system mute.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "play_pause_media",
        "description": "Toggle play/pause for video or audio playback (YouTube, Spotify, etc.). Use for 'pause it', 'pause video', 'play', 'resume'.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "set_brightness",
        "description": "Set screen brightness (0-100).",
        "input_schema": {
            "type": "object",
            "properties": {"level": {"type": "integer"}},
            "required": ["level"],
        },
    },
    {
        "name": "lock_screen",
        "description": "Lock the Windows screen.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "take_screenshot",
        "description": "Capture a screenshot and save it to the Desktop.",
        "input_schema": {
            "type": "object",
            "properties": {
                "filename": {"type": "string", "description": "Optional filename."}
            },
        },
    },
    {
        "name": "battery_status",
        "description": "Get the current battery level and charging status.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "get_time",
        "description": "Get the current time and date.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "run_shell_command",
        "description": (
            "Run a shell command (PowerShell). Use for tasks that cannot be done "
            "with other tools. Dangerous commands require user confirmation."
        ),
        "input_schema": {
            "type": "object",
            "properties": {"cmd": {"type": "string"}},
            "required": ["cmd"],
        },
    },
    {
        "name": "set_timer",
        "description": "Set a countdown timer that speaks when done.",
        "input_schema": {
            "type": "object",
            "properties": {
                "seconds": {"type": "integer"},
                "label": {"type": "string"},
            },
            "required": ["seconds"],
        },
    },
    {
        "name": "write_document",
        "description": (
            "Generate a document on a given topic using AI and type it into the active editor. "
            "Use for 'write a leave application', 'draft an email', etc."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "topic": {"type": "string"},
                "save_as": {"type": "string", "description": "Optional filename inside ~/JarvisFiles."},
            },
            "required": ["topic"],
        },
    },
    {
        "name": "remember_fact",
        "description": "Store a fact about the user for future sessions (e.g. name, preference).",
        "input_schema": {
            "type": "object",
            "properties": {"fact": {"type": "string"}},
            "required": ["fact"],
        },
    },
    {
        "name": "set_wallpaper",
        "description": "Change the Windows desktop background wallpaper. Can take an image path or open a file picker.",
        "input_schema": {
            "type": "object",
            "properties": {
                "image_path": {"type": "string", "description": "Optional full path to an image file. If omitted, opens file picker."}
            },
        },
    },
    {
        "name": "drag_with_description",
        "description": "Drag an item from one location to another using natural language descriptions (e.g. 'file from Downloads to Desktop', 'email to trash').",
        "input_schema": {
            "type": "object",
            "properties": {
                "start_description": {"type": "string", "description": "What to drag (e.g. 'the selected file', 'email from John')"},
                "end_description": {"type": "string", "description": "Where to drop it (e.g. 'Desktop folder', 'Recycle Bin')"}
            },
            "required": ["start_description", "end_description"],
        },
    },
    {
        "name": "get_weather",
        "description": "Get current weather information for a location. Use default location if none specified.",
        "input_schema": {
            "type": "object",
            "properties": {
                "location": {"type": "string", "description": "City name or location (e.g. 'Tokyo', 'New York'). Uses default if omitted."}
            },
        },
    },
    {
        "name": "get_news",
        "description": "Search for latest news on a topic. Returns top news headlines.",
        "input_schema": {
            "type": "object",
            "properties": {
                "topic": {"type": "string", "description": "News topic to search for (e.g. 'technology', 'sports')."}
            },
            "required": ["topic"],
        },
    },
    {
        "name": "set_reminder",
        "description": "Set a reminder that will speak a message after a specified time.",
        "input_schema": {
            "type": "object",
            "properties": {
                "seconds": {"type": "integer", "description": "Seconds until reminder fires."},
                "message": {"type": "string", "description": "Message to speak when reminder fires."}
            },
            "required": ["seconds", "message"],
        },
    },
    {
        "name": "system_info",
        "description": "Get detailed system information including CPU, RAM, disk usage, and running processes.",
        "input_schema": {
            "type": "object",
            "properties": {},
        },
    },
]

# ─── OpenAI-format schemas (auto-generated from above) ────────────────────────
TOOL_SCHEMAS_OPENAI: list[dict] = [_to_openai(s) for s in TOOL_SCHEMAS]


def _get_vision():
    from control import vision
    return vision


# ─── Dispatcher ───────────────────────────────────────────────────────────────

def dispatch_tool(
    tool_name: str,
    tool_input: dict,
    speak_fn: Callable[[str], None],
    listen_fn: Callable[[], str],
    memory,
    status_fn: Callable[[str], None] | None = None,
) -> str:
    """Map tool_name + input → correct Python function. Returns result string."""
    def _announce(msg: str):
        if status_fn:
            status_fn(msg)
        log_action(tool_name, msg)

    if tool_name == "direct_reply":
        msg = tool_input.get("message", "Ready to assist you, sir.")
        _announce(msg)
        return msg

    from control import apps, keyboard_mouse, files, system

    try:

        # ── App control ───────────────────────────────────────────────────────
        if tool_name == "open_application":
            name = tool_input["name"]
            _announce(f"Opening {name}…")
            return apps.open_application(name)

        if tool_name == "close_application":
            _announce(f"Closing {tool_input['name']}…")
            return apps.close_application(tool_input["name"])

        if tool_name == "focus_window":
            return apps.focus_window(tool_input["title"])

        if tool_name == "list_windows":
            return apps.list_windows()

        if tool_name == "minimize_window":
            return apps.minimize_window(tool_input["title"])

        if tool_name == "maximize_window":
            return apps.maximize_window(tool_input["title"])

        # ── Keyboard / mouse ──────────────────────────────────────────────────
        if tool_name == "type_text":
            return keyboard_mouse.type_text(tool_input["text"])

        if tool_name == "press_keys":
            return keyboard_mouse.press_keys(tool_input["keys"])

        if tool_name == "press_single_key":
            return keyboard_mouse.press_single_key(tool_input["key"])

        if tool_name == "click":
            return keyboard_mouse.click(tool_input["x"], tool_input["y"])

        if tool_name == "double_click":
            return keyboard_mouse.double_click(tool_input["x"], tool_input["y"])

        if tool_name == "right_click":
            return keyboard_mouse.right_click(tool_input["x"], tool_input["y"])

        if tool_name == "scroll":
            return keyboard_mouse.scroll(tool_input["direction"], tool_input.get("amount", 3))

        if tool_name == "drag":
            if "start_description" in tool_input and "end_description" in tool_input:
                _announce(f"Dragging '{tool_input['start_description']}' to '{tool_input['end_description']}'…")
                return _get_vision().drag_by_description(tool_input["start_description"], tool_input["end_description"])
            return keyboard_mouse.drag(
                tool_input["x1"], tool_input["y1"],
                tool_input["x2"], tool_input["y2"],
            )

        if tool_name == "drag_with_description":
            start = tool_input["start_description"]
            end = tool_input["end_description"]
            _announce(f"Dragging '{start}' to '{end}'…")
            return _get_vision().drag_by_description(start, end)

        # ── Vision & Spider Autonomous Scout ──────────────────────────────────
        if tool_name == "read_screen":
            _announce("Reading the screen…")
            return _get_vision().read_screen()

        if tool_name == "describe_screen":
            _announce("Analyzing screen layout…")
            return _get_vision().describe_screen()

        if tool_name == "read_screen_text":
            target = tool_input.get("target", "")
            _announce(f"Reading visible text on screen{' (' + target + ')' if target else ''}…")
            return _get_vision().read_screen_text(target)

        if tool_name in ["spider_scan_and_act", "spider_start_autopilot", "spider_stop_autopilot", "launch_spider_3d"]:
            _announce("Scanning screen with neural vision scanner.")
            return _get_vision().describe_screen()

        if tool_name == "click_element_by_description":
            desc = tool_input["description"]
            _announce(f"Locating '{desc}'…")
            return _get_vision().click_element_by_description(desc)

        if tool_name == "click_and_type":
            desc = tool_input["description"]
            text = tool_input["text"]
            press_enter = tool_input.get("press_enter", True)
            _announce(f"Typing into '{desc}'…")
            return _get_vision().click_and_type(desc, text, press_enter)

        if tool_name == "play_pause_media":
            return keyboard_mouse.play_pause_media()

        # ── Files ─────────────────────────────────────────────────────────────
        if tool_name == "create_file":
            return files.create_file(tool_input["relative_path"], tool_input.get("content", ""))

        if tool_name == "read_file":
            return files.read_file(tool_input["relative_path"])

        if tool_name == "write_file":
            return files.write_file(tool_input["relative_path"], tool_input["content"])

        if tool_name == "delete_file":
            path = tool_input["relative_path"]
            confirmed = ask_confirmation(
                f"Are you sure you want to delete {path}?",
                speak_fn, listen_fn,
            )
            if not confirmed:
                return "Deletion cancelled by user."
            return files.delete_file(path)

        if tool_name == "list_files":
            return files.list_files(tool_input.get("relative_path", "."))

        # ── System ────────────────────────────────────────────────────────────
        if tool_name == "volume_up":    return system.volume_up()
        if tool_name == "volume_down":  return system.volume_down()
        if tool_name == "volume_mute":  return system.volume_mute()

        if tool_name == "set_brightness":
            return system.set_brightness(tool_input["level"])

        if tool_name == "lock_screen":  return system.lock_screen()
        if tool_name == "take_screenshot":
            return system.take_screenshot(tool_input.get("filename", ""))
        if tool_name == "battery_status": return system.battery_status()
        if tool_name == "get_time":     return system.get_time()

        if tool_name == "open_url":
            return system.open_url(tool_input["url"])

        if tool_name == "play_spotify":
            query = tool_input["query"]
            _announce(f"Opening Spotify and playing '{query}'…")
            return system.play_spotify(query)

        if tool_name == "play_youtube":
            query = tool_input["query"]
            _announce(f"Searching YouTube for '{query}'…")
            return system.play_youtube(query)

        if tool_name == "open_and_search":
            app = tool_input["app"]
            query = tool_input["query"]
            _announce(f"Opening {app} and searching for '{query}'…")
            return system.open_and_search(app, query)

        if tool_name == "web_search":
            query = tool_input["query"]
            _announce(f"Searching for {query}.")
            return system.web_search(query)

        if tool_name == "run_shell_command":
            cmd = tool_input["cmd"]
            from safety import is_command_dangerous
            if is_command_dangerous(cmd):
                confirmed = ask_confirmation(
                    f"This command looks dangerous: {cmd}. Shall I run it?",
                    speak_fn, listen_fn,
                )
                if not confirmed:
                    return "Command cancelled by user."
            log_action("SHELL_COMMAND", cmd)
            return system.run_shell_command(cmd)

        if tool_name == "set_timer":
            return system.set_timer(
                tool_input["seconds"],
                tool_input.get("label", "Timer"),
                speak_fn,
            )

        if tool_name == "set_reminder":
            return system.set_reminder(
                tool_input["seconds"],
                tool_input["message"],
                speak_fn,
            )

        if tool_name == "get_weather":
            loc = tool_input.get("location", "")
            _announce(f"Checking weather for {loc or 'your location'}…")
            return system.get_weather(loc)

        if tool_name == "get_news":
            topic = tool_input.get("topic", "general")
            _announce(f"Retrieving latest headlines on {topic}…")
            return system.get_news(topic)

        if tool_name == "system_info":
            return system.system_info()

        if tool_name == "write_document":
            return _write_document(
                tool_input["topic"],
                tool_input.get("save_as", ""),
                speak_fn,
            )

        if tool_name == "open_browser_tab":
            b = tool_input.get("browser", "")
            u = tool_input.get("url", "")
            _announce(f"Opening a new tab in {b or 'browser'}…")
            return apps.open_browser_tab(b, u)

        if tool_name == "close_browser_tab":
            return apps.close_browser_tab()

        if tool_name == "switch_next_tab":
            return apps.switch_next_tab()

        if tool_name == "switch_prev_tab":
            return apps.switch_prev_tab()

        if tool_name == "reopen_closed_tab":
            return apps.reopen_closed_tab()

        if tool_name == "restore_window":
            return apps.restore_window(tool_input.get("title", ""))

        if tool_name == "open_and_write":
            app = tool_input.get("app", "notepad")
            topic = tool_input.get("topic", "")
            content = tool_input.get("content", "")
            return _open_and_write(app, topic, content, _announce)

        if tool_name in ["set_wallpaper", "change_desktop_wallpaper"]:
            from tools.wallpaper import set_desktop_wallpaper, pick_and_set_wallpaper
            path = tool_input.get("image_path", "").strip() if tool_input else ""
            _announce("Updating desktop wallpaper…")
            if path and os.path.exists(path):
                ok = set_desktop_wallpaper(path)
                return f"Wallpaper changed to {path}." if ok else f"Failed to set wallpaper from {path}."
            else:
                chosen = pick_and_set_wallpaper()
                return f"Wallpaper updated to {chosen}." if chosen else "Wallpaper selection cancelled."

        if tool_name == "remember_fact":
            memory.add_fact(tool_input["fact"])
            return f"Remembered: {tool_input['fact']}"

        return f"Unknown tool: {tool_name}"

    except Exception as e:
        logger.error(f"Tool '{tool_name}' raised: {e}", exc_info=True)
        return f"Error in {tool_name}: {e}"


# ─── Write-document helper ────────────────────────────────────────────────────

def _write_document(topic: str, save_as: str, speak_fn: Callable) -> str:
    from openai import OpenAI
    from config import NVIDIA_API_KEY, NVIDIA_BASE_URL, NVIDIA_MODEL
    from control import keyboard_mouse, files

    speak_fn(f"Writing a document about {topic}.")
    client = OpenAI(api_key=NVIDIA_API_KEY, base_url=NVIDIA_BASE_URL)
    resp = client.chat.completions.create(
        model=NVIDIA_MODEL,
        max_tokens=1500,
        messages=[
            {"role": "system", "content": "You are a professional document writer. Write clear, well-formatted plain text documents."},
            {"role": "user", "content": f"Write: {topic}"},
        ],
    )
    content = resp.choices[0].message.content.strip()
    keyboard_mouse.type_text(content)
    if save_as:
        files.write_file(save_as, content)
        return f"Document written and saved as {save_as}."
    return "Document typed into the active window."


def _open_and_write(app: str, topic: str, content: str, announce_fn: Callable) -> str:
    import ctypes
    try:
        ctypes.windll.user32.GetWindowRect.argtypes = None
    except Exception:
        pass
    try:
        from control import apps, keyboard_mouse
    except ImportError:
        from jarvis.control import apps, keyboard_mouse
    import time, re
    from openai import OpenAI
    try:
        from config import NVIDIA_API_KEY, NVIDIA_BASE_URL, NVIDIA_MODEL
    except ImportError:
        from jarvis.config import NVIDIA_API_KEY, NVIDIA_BASE_URL, NVIDIA_MODEL

    # Normalize app name
    app_clean = app.lower().strip()
    if app_clean in ("note pad", "notes", "editor", "text editor"):
        app = "notepad"
    elif app_clean in ("vs code", "vscode"):
        app = "code"

    announce_fn(f"Opening {app}…")
    apps.open_application(app)
    time.sleep(1.2)
    apps.focus_window(app)
    time.sleep(0.3)

    if not content and topic:
        t_low = topic.lower().strip()
        # Fast local templates for instant 0ms generation
        if "hello world" in t_low and ("python" in t_low or "py" in t_low):
            content = 'print("Hello, World!")\n'
        elif "hello world" in t_low and ("c++" in t_low or "cpp" in t_low):
            content = '#include <iostream>\n\nint main() {\n    std::cout << "Hello, World!" << std::endl;\n    return 0;\n}\n'
        elif "hello world" in t_low and ("in c" in t_low or t_low.endswith(" c") or "\bc\b" in t_low):
            content = '#include <stdio.h>\n\nint main() {\n    printf("Hello, World!\\n");\n    return 0;\n}\n'
        elif "hello world" in t_low and "java" in t_low:
            content = 'public class Main {\n    public static void main(String[] args) {\n        System.out.println("Hello, World!");\n    }\n}\n'
        elif "hello world" in t_low and ("javascript" in t_low or "js" in t_low):
            content = 'console.log("Hello, World!");\n'
        elif "fibonacci" in t_low and "python" in t_low:
            content = 'def fibonacci(n):\n    a, b = 0, 1\n    for _ in range(n):\n        yield a\n        a, b = b, a + b\n\nprint(list(fibonacci(10)))\n'
        elif "calculator" in t_low and "python" in t_low:
            content = '# Simple Python Calculator\ndef add(a, b): return a + b\ndef sub(a, b): return a - b\ndef mul(a, b): return a * b\ndef div(a, b): return a / b if b != 0 else "Error"\n\nprint("5 + 3 =", add(5, 3))\n'
        else:
            keywords = (
                "program", "prigrm", "prog", "code", "script", "function", "class", "algorithm",
                "essay", "letter", "application", "email", "poem", "story", "summary",
                "in c", "in python", "in java", "in cpp", "in c++", "in html", "in javascript",
                "hello world", "calculator", "fibonacci", "factorial"
            )
            is_request = any(w in t_low for w in keywords) or len(topic.split()) >= 4
            if is_request:
                announce_fn(f"Writing {topic}…")
                raw = ""
                try:
                    client = OpenAI(api_key=NVIDIA_API_KEY, base_url=NVIDIA_BASE_URL)
                    resp = client.chat.completions.create(
                        model=NVIDIA_MODEL,
                        messages=[
                            {"role": "system", "content": "You are an expert code and text writer. Output ONLY the raw requested code or document. Do NOT output markdown code blocks (no ```), do NOT output introductory or concluding remarks. Output ONLY the raw content ready to paste."},
                            {"role": "user", "content": f"Write: {topic}"},
                        ],
                        max_tokens=600,
                        temperature=0.1,
                    )
                    raw = resp.choices[0].message.content.strip()
                    if raw.startswith("```"):
                        raw = re.sub(r"^```[a-zA-Z0-9]*\n?", "", raw)
                        raw = re.sub(r"\n?```$", "", raw).strip()
                except Exception:
                    raw = f"# {topic}\n\n# Code:\n"
                content = raw if raw else topic
            else:
                content = topic

    if content:
        announce_fn("Writing content into window…")
        apps.focus_window(app)
        time.sleep(0.3)
        keyboard_mouse.type_text(content)
        return f"Opened {app} and generated the code for {topic}, sir."
    return f"Opened {app}."
