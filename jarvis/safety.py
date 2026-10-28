"""
safety.py – Confirmation, blocklist, and kill-switch logic for JARVIS.
"""

import re
import sys
import threading
import logging
from pathlib import Path

import keyboard  # type: ignore

from config import DANGEROUS_PATTERNS, SENSITIVE_EXTENSIONS, KILL_HOTKEY, ACTION_LOG

# ─── Logger ───────────────────────────────────────────────────────────────────
logger = logging.getLogger("jarvis.safety")

# ─── Global kill flag ─────────────────────────────────────────────────────────
_kill_event = threading.Event()

def is_killed() -> bool:
    return _kill_event.is_set()

def reset_kill():
    _kill_event.clear()

def trigger_kill():
    """Called when Ctrl+Alt+Q is pressed."""
    _kill_event.set()
    logger.warning("🛑 EMERGENCY KILL TRIGGERED – halting all actions.")


def register_kill_hotkey():
    """Register the global emergency kill hotkey. Call once at startup."""
    try:
        keyboard.add_hotkey(KILL_HOTKEY, trigger_kill, suppress=False)
        logger.info(f"Kill hotkey registered: {KILL_HOTKEY}")
    except Exception as e:
        logger.error(f"Could not register kill hotkey: {e}")


# ─── Action logger ────────────────────────────────────────────────────────────
def log_action(action: str, detail: str = ""):
    """Append an action record to the log file."""
    from datetime import datetime
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {action}"
    if detail:
        line += f" | {detail}"
    with open(ACTION_LOG, "a", encoding="utf-8") as f:
        f.write(line + "\n")
    logger.info(f"ACTION: {action} | {detail}")


# ─── Blocklist check ──────────────────────────────────────────────────────────
def is_command_dangerous(cmd: str) -> bool:
    """Return True if the shell command matches a known dangerous pattern."""
    lower = cmd.lower()
    for pattern in DANGEROUS_PATTERNS:
        if pattern in lower:
            return True
    return False


def is_file_deletion_sensitive(path: str) -> bool:
    """Return True if the file has an extension that warrants confirmation."""
    ext = Path(path).suffix.lower()
    return ext in SENSITIVE_EXTENSIONS


# ─── Spoken confirmation ──────────────────────────────────────────────────────
def ask_confirmation(question: str, speak_fn, listen_fn) -> bool:
    """
    Speak `question`, wait for yes/no voice response.
    Returns True if user says yes, False otherwise.
    
    speak_fn(text)  → speaks text aloud
    listen_fn()     → returns transcribed string (short timeout)
    """
    speak_fn(question + " Say yes or no.")
    try:
        answer = listen_fn()
        if answer:
            answer = answer.lower().strip()
            if any(w in answer for w in ("yes", "yeah", "yep", "sure", "ok", "okay", "do it", "confirm")):
                log_action("CONFIRMATION_GRANTED", question)
                return True
            else:
                log_action("CONFIRMATION_DENIED", question)
                speak_fn("Alright, I've cancelled that.")
                return False
    except Exception:
        pass
    speak_fn("I didn't catch that. Cancelling to be safe.")
    log_action("CONFIRMATION_TIMEOUT", question)
    return False


# ─── Password guard ───────────────────────────────────────────────────────────
PASSWORD_KEYWORDS = re.compile(
    r"\b(password|passwd|secret|api[_\s]?key|token|credential)\b",
    re.IGNORECASE,
)

def contains_password_hint(text: str) -> bool:
    return bool(PASSWORD_KEYWORDS.search(text))
