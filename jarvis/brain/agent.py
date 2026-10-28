"""
brain/agent.py – JARVIS agent loop with ReAct JSON prompting.

Since NVIDIA NIM's free tier doesn't support native tool-calling API,
we use a ReAct-style prompt where the model outputs structured JSON
actions that we parse and execute.

Format the model must follow:
  THOUGHT: <reasoning>
  ACTION: {"tool": "<name>", "args": {<args>}}

  OR if done:
  THOUGHT: <reasoning>
  FINAL: <spoken reply to user>
"""

import json
import logging
import re
from typing import Callable

from openai import OpenAI  # type: ignore

from config import NVIDIA_API_KEY, NVIDIA_BASE_URL, NVIDIA_MODEL, MAX_AGENT_STEPS
from memory import Memory
from safety import is_killed, log_action
from brain.tools import TOOL_SCHEMAS, dispatch_tool

logger = logging.getLogger("jarvis.brain.agent")

_client = OpenAI(api_key=NVIDIA_API_KEY, base_url=NVIDIA_BASE_URL)

# ── Build a compact tool catalog for the system prompt ─────────────────────────
def _build_tool_catalog() -> str:
    lines = []
    for t in TOOL_SCHEMAS:
        props = t.get("input_schema", {}).get("properties", {})
        args_desc = ", ".join(
            f"{k}: {v.get('type','any')}" for k, v in props.items()
        )
        lines.append(f"  • {t['name']}({args_desc}) — {t['description']}")
    return "\n".join(lines)

_TOOL_CATALOG = _build_tool_catalog()

def get_system_prompt(memory_context: str = "") -> str:
    return f"""You are JARVIS, an autonomous AI desktop assistant running on Windows with FULL PHYSICAL CONTROL of the computer via your tools.
You are courteous, precise, efficient, and speak naturally with a polite and respectful tone (addressing the user as "sir" or by their name).

CRITICAL DIRECTIVES:
- YOU HAVE FULL PHYSICAL CONTROL OVER THIS PC. You can open any application, write text/code directly into Notepad or any window, click buttons, and automate software.
- NEVER tell the user "I am not able to interact with your computer", "I cannot write code into Notepad", or "I can only guide you". That is completely false. You have tools: open_and_write, open_application, type_text, click_element_by_description, click_and_type, click.
- When asked to write, type, or code into an application (e.g. "In Notepad, write a program for Hello World in Python"):
  Use 'open_and_write' with app="notepad" and topic="a program for Hello World in Python", OR call 'open_application' then 'type_text'.
- When asked to click an element, button, link, or icon on screen:
  Use 'click_element_by_description' with a clear visual description of what to click.
- When asked to type into a search bar, text box, or input field on screen:
  Use 'click_and_type' with the description of the field and the text to type.
- When asked to open websites or apps:
  Use 'open_url' or 'open_application'.
- When asked to play music or songs on Spotify (e.g. "open spotify and play animal", "play starboy on spotify"):
  Use 'play_spotify' with query="<song title>".
- When asked to play a video or song on YouTube:
  Use 'play_youtube' with query="<video or song title>".
- When asked to open an app and search for something (e.g. Brave, Chrome, Store):
  Use 'open_and_search' with app="<app>" and query="<query>".
- When asked to pause or play/resume media:
  Use 'play_pause_media'.

AVAILABLE TOOLS:
{_TOOL_CATALOG}

HOW TO RESPOND — you MUST follow this format exactly:

To call a tool:
THOUGHT: <your reasoning in one sentence>
ACTION: {{"tool": "<tool_name>", "args": {{<arguments as JSON>}}}}

To give a final spoken answer (when no more tools needed):
THOUGHT: <your reasoning>
FINAL: <polite and crisp spoken reply, max 30 words>

Rules:
- One ACTION per response — wait for the result before the next step.
- Keep FINAL replies conversational, polite, and SHORT (under 30 words).
- Once the user's requested action is completed, IMMEDIATELY output FINAL and stop!
- For chit-chat, jokes, greetings, or questions that do not need an external tool, DO NOT call any tool! Immediately output FINAL in your very first step.

{memory_context}
"""


def _extract_first_json_object(text: str) -> dict | None:
    """Extract first valid JSON object from string, handling nested braces correctly."""
    start = text.find("{")
    if start == -1:
        return None
    depth = 0
    in_string = False
    escape = False
    for i in range(start, len(text)):
        ch = text[i]
        if escape:
            escape = False
            continue
        if ch == "\\":
            escape = True
            continue
        if ch == '"':
            in_string = not in_string
            continue
        if not in_string:
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    json_str = text[start : i + 1]
                    try:
                        parsed = json.loads(json_str)
                        if isinstance(parsed, dict):
                            return parsed
                    except json.JSONDecodeError:
                        return None
    return None


_FINAL_RE   = re.compile(r'FINAL\s*:\s*(.+)', re.DOTALL | re.IGNORECASE)
_THOUGHT_RE = re.compile(r'THOUGHT\s*:\s*(.+?)(?=ACTION|FINAL|$)', re.DOTALL | re.IGNORECASE)


def _parse_response(text: str) -> tuple[str | None, dict | None, str | None]:
    """
    Returns (thought, action_dict, final_reply).
    Exactly one of action_dict or final_reply will be non-None.
    """
    thought = ""
    tm = _THOUGHT_RE.search(text)
    if tm:
        thought = tm.group(1).strip()

    # Check for ACTION
    action_match = re.search(r'ACTION\s*:\s*(.+)', text, re.DOTALL | re.IGNORECASE)
    if action_match:
        action = _extract_first_json_object(action_match.group(1))
        if action and "tool" in action:
            return thought, action, None

    # Check for FINAL
    fm = _FINAL_RE.search(text)
    if fm:
        return thought, None, fm.group(1).strip()

    # Fallback: treat remainder as final answer, stripping any THOUGHT prefix
    fallback = text.strip()
    if fallback.upper().startswith("THOUGHT:"):
        fallback = re.sub(r'^THOUGHT:\s*', '', fallback, flags=re.IGNORECASE).strip()
    return thought, None, fallback


def run_agent(
    user_command: str,
    memory: Memory,
    speak_fn: Callable[[str], None],
    listen_fn: Callable[[], str],
    status_fn: Callable[[str], None] | None = None,
) -> str:
    """Execute the ReAct agent loop for one user command."""

    def _status(s: str):
        if status_fn:
            status_fn(s)

    # ── Fast Local Intent Check (Instant < 0.05s response) ───────────────────
    from brain.intent import try_fast_intent
    fast_match = try_fast_intent(user_command)
    if fast_match:
        tool_name, tool_args = fast_match
        logger.info(f"Fast intent matched: {tool_name}({tool_args})")
        _status(f"Executing: {tool_name}")
        log_action("USER_COMMAND", user_command)
        result = dispatch_tool(
            tool_name, tool_args,
            speak_fn, listen_fn, memory,
            status_fn=_status,
        )
        res_str = str(result).strip()
        memory.add_turn("user", user_command)
        memory.add_turn("assistant", {"role": "assistant", "content": f"FINAL: {res_str}"})
        _status("Speaking…")
        speak_fn(res_str)
        log_action("AGENT_REPLY", res_str[:120])
        return res_str

    system = get_system_prompt(memory.summary_for_system_prompt())

    # Build conversation history as plain text turns
    memory.add_turn("user", user_command)

    log_action("USER_COMMAND", user_command)
    _status("Thinking…")

    step = 0
    final_reply = "I'm sorry, I ran into an issue. Please try again."

    while step < MAX_AGENT_STEPS:
        if is_killed():
            speak_fn("Emergency stop activated.")
            return "Stopped."

        step += 1
        logger.info(f"Agent step {step}/{MAX_AGENT_STEPS}")

        # Build messages from session history
        messages = [{"role": "system", "content": system}]
        for msg in memory.get_session_messages():
            if isinstance(msg, dict) and "role" in msg:
                messages.append(msg)
            elif isinstance(msg, dict):
                messages.append({"role": "assistant", "content": str(msg)})

        # ── Call NVIDIA NIM ───────────────────────────────────────────────────
        try:
            response = _client.chat.completions.create(
                model=NVIDIA_MODEL,
                messages=messages,
                max_tokens=512,
                temperature=0.1,
                stop=["OBSERVATION:"],   # stop before it hallucinates results
            )
        except Exception as e:
            err = str(e)
            logger.error(f"NVIDIA API error: {err}")
            if "401" in err or "authentication" in err.lower():
                speak_fn("My NVIDIA API key seems invalid. Please check the config.")
            elif "404" in err or "410" in err:
                speak_fn("The AI model is not available. Please check config.")
            elif "connection" in err.lower() or "timeout" in err.lower():
                speak_fn("I can't reach the NVIDIA API. Please check internet.")
            else:
                speak_fn(f"API error: please try again.")
            return f"API error: {err}"

        raw = response.choices[0].message.content or ""
        logger.info(f"Model response:\n{raw[:400]}")

        thought, action, final = _parse_response(raw)

        # Store the assistant turn
        memory.add_turn("assistant", {"role": "assistant", "content": raw})

        # ── Final answer ──────────────────────────────────────────────────────
        if final is not None:
            final_reply = final
            _status("Speaking…")
            speak_fn(final_reply)
            log_action("AGENT_REPLY", final_reply[:120])
            return final_reply

        # ── Execute action ────────────────────────────────────────────────────
        if action is not None:
            tool_name = action.get("tool", "")
            tool_args = action.get("args", {})

            if not tool_name:
                # Model didn't give a valid tool — treat raw as final
                speak_fn(raw[:200])
                return raw

            logger.info(f"Executing: {tool_name}({tool_args})")
            _status(f"Executing: {tool_name}")

            result = dispatch_tool(
                tool_name, tool_args,
                speak_fn, listen_fn, memory,
                status_fn=_status,
            )
            logger.info(f"Tool result: {str(result)[:200]}")

            # Direct response tools that return a complete polite answer:
            # Complete immediately without doing a second slow API call across the internet!
            DIRECT_ANSWER_TOOLS = {
                "open_url", "play_youtube", "play_pause_media",
                "volume_up", "volume_down", "volume_mute", "lock_screen",
                "minimize_window", "maximize_window", "close_application",
                "get_time", "battery_status", "click_and_type", "type_text", "press_key",
                "open_and_write"
            }
            res_str = str(result).strip()
            if tool_name in DIRECT_ANSWER_TOOLS and not res_str.lower().startswith("error"):
                _status("Speaking…")
                speak_fn(res_str)
                log_action("AGENT_REPLY", res_str[:120])
                memory.add_turn("assistant", {"role": "assistant", "content": f"FINAL: {res_str}"})
                return res_str

            # Add observation so model sees the result for multi-step tasks
            obs_msg = f"OBSERVATION: {result}"
            memory.add_turn("user", {"role": "user", "content": obs_msg})

            if step >= MAX_AGENT_STEPS:
                speak_fn("I've reached my step limit. Let me know if you'd like to continue.")
                return "Max steps reached."
            continue

        # No action and no final — model confused, treat as final
        speak_fn(raw[:200])
        return raw

    return final_reply
