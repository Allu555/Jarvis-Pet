"""
brain/tools.py – Tool schemas (BOTH Anthropic and OpenAI formats) + dispatcher.

TOOL_SCHEMAS_OPENAI  → sent to NVIDIA NIM / any OpenAI-compatible API
TOOL_SCHEMAS         → kept for reference (Anthropic format)

Dispatcher routes tool_name + input → correct Python function.
"""

import logging
from typing import Any, Callable

from safety import ask_confirmation, is_file_deletion_sensitive, log_action

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
        "description": "Click and drag from (x1, y1) to (x2, y2).",
        "input_schema": {
            "type": "object",
            "properties": {
                "x1": {"type": "integer"}, "y1": {"type": "integer"},
                "x2": {"type": "integer"}, "y2": {"type": "integer"},
            },
            "required": ["x1", "y1", "x2", "y2"],
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
        "description": "Open Google search for the given query in the default browser.",
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
]

# ─── OpenAI-format schemas (auto-generated from above) ────────────────────────
TOOL_SCHEMAS_OPENAI: list[dict] = [_to_openai(s) for s in TOOL_SCHEMAS]


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
    from control import apps, keyboard_mouse, vision, files, system

    def _announce(msg: str):
        if status_fn:
            status_fn(msg)
        log_action(tool_name, msg)

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
            return keyboard_mouse.drag(
                tool_input["x1"], tool_input["y1"],
                tool_input["x2"], tool_input["y2"],
            )

        # ── Vision ────────────────────────────────────────────────────────────
        if tool_name == "read_screen":
            _announce("Reading the screen…")
            return vision.read_screen()

        if tool_name == "click_element_by_description":
            desc = tool_input["description"]
            _announce(f"Locating '{desc}'…")
            return vision.click_element_by_description(desc)

        if tool_name == "click_and_type":
            desc = tool_input["description"]
            text = tool_input["text"]
            press_enter = tool_input.get("press_enter", True)
            _announce(f"Typing into '{desc}'…")
            return vision.click_and_type(desc, text, press_enter)

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

        if tool_name == "write_document":
            return _write_document(
                tool_input["topic"],
                tool_input.get("save_as", ""),
                speak_fn,
            )

        if tool_name == "open_and_write":
            app = tool_input.get("app", "notepad")
            topic = tool_input.get("topic", "")
            content = tool_input.get("content", "")
            return _open_and_write(app, topic, content, _announce)

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
    from control import apps, keyboard_mouse
    import time, re
    from openai import OpenAI
    from config import NVIDIA_API_KEY, NVIDIA_BASE_URL, NVIDIA_MODEL

    announce_fn(f"Opening {app}…")
    apps.open_application(app)
    time.sleep(1.0)
    apps.focus_window(app)
    time.sleep(0.3)

    if not content and topic:
        keywords = (
            "program", "prigrm", "prog", "code", "script", "function", "class", "algorithm",
            "essay", "letter", "application", "email", "poem", "story", "summary",
            "in c", "in python", "in java", "in cpp", "in c++", "in html", "in javascript",
            "hello world", "calculator", "fibonacci", "factorial"
        )
        is_request = any(w in topic.lower() for w in keywords) or len(topic.split()) >= 4
        if is_request:
            announce_fn(f"Writing {topic}…")
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
            content = raw
        else:
            content = topic

    if content:
        announce_fn("Writing content into window…")
        keyboard_mouse.type_text(content)
        return f"Opened {app} and wrote the requested content for you, sir."
    return f"Opened {app}."
