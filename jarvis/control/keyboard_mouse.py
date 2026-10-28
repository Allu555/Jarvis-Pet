"""
control/keyboard_mouse.py – Keyboard and mouse automation via pyautogui + pynput.
Handles Windows DPI scaling so clicks land in the right place.
"""

import ctypes
import logging
import time

import pyautogui    # type: ignore
import pyperclip    # type: ignore
from pynput.keyboard import Controller as KbController, Key  # type: ignore

from config import PYAUTOGUI_PAUSE, PYAUTOGUI_FAILSAFE

logger = logging.getLogger("jarvis.control.keyboard_mouse")

# ─── PyAutoGUI safety settings ────────────────────────────────────────────────
pyautogui.PAUSE    = PYAUTOGUI_PAUSE
pyautogui.FAILSAFE = PYAUTOGUI_FAILSAFE

# ─── DPI awareness (Windows) ──────────────────────────────────────────────────
try:
    # Per-monitor DPI awareness → pyautogui coordinates match physical pixels
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
    logger.info("DPI awareness set to per-monitor (mode 2).")
except Exception as e:
    try:
        ctypes.windll.user32.SetProcessDPIAware()
        logger.info("DPI awareness set (legacy mode).")
    except Exception:
        logger.warning(f"Could not set DPI awareness: {e}")


def ensure_desktop_attached():
    """Ensure current thread can access the interactive desktop without handle leaks."""
    try:
        user32 = ctypes.windll.user32
        h_input = user32.OpenInputDesktop(0, False, 0x01FF)
        if h_input:
            user32.SetThreadDesktop(h_input)
            user32.CloseDesktop(h_input)
    except Exception:
        pass


def _screen_size():
    ensure_desktop_attached()
    return pyautogui.size()


def _clamp_coords(x: int, y: int) -> tuple[int, int]:
    """Ensure coordinates stay strictly within physical screen bounds."""
    try:
        sw, sh = pyautogui.size()
        cx = max(0, min(sw - 1, int(x)))
        cy = max(0, min(sh - 1, int(y)))
        return cx, cy
    except Exception:
        return int(x), int(y)


# ─── Mouse operations ─────────────────────────────────────────────────────────

def click(x: int, y: int) -> str:
    """Instant, accurate left-click without cursor freezing or artificial pauses."""
    ensure_desktop_attached()
    cx, cy = _clamp_coords(x, y)
    try:
        pyautogui.click(cx, cy)
        logger.info(f"Clicked at ({cx}, {cy})")
        return f"Clicked at ({cx}, {cy})."
    except Exception as e:
        logger.error(f"Click failed at ({cx}, {cy}): {e}")
        return f"Click error: {e}"


def double_click(x: int, y: int) -> str:
    """Instant, accurate double-click."""
    ensure_desktop_attached()
    cx, cy = _clamp_coords(x, y)
    try:
        pyautogui.doubleClick(cx, cy, interval=0.08)
        logger.info(f"Double-clicked at ({cx}, {cy})")
        return f"Double-clicked at ({cx}, {cy})."
    except Exception as e:
        return f"Double-click error: {e}"


def right_click(x: int, y: int) -> str:
    """Instant, accurate right-click."""
    ensure_desktop_attached()
    cx, cy = _clamp_coords(x, y)
    try:
        pyautogui.rightClick(cx, cy)
        logger.info(f"Right-clicked at ({cx}, {cy})")
        return f"Right-clicked at ({cx}, {cy})."
    except Exception as e:
        return f"Right-click error: {e}"


def scroll(direction: str, amount: int = 3) -> str:
    """direction: 'up' | 'down'"""
    ensure_desktop_attached()
    clicks = amount if direction == "up" else -amount
    pyautogui.scroll(clicks)
    return f"Scrolled {direction} by {amount}."


def drag(x1: int, y1: int, x2: int, y2: int, duration: float = 0.3) -> str:
    """Click and drag from (x1, y1) to (x2, y2)."""
    ensure_desktop_attached()
    cx1, cy1 = _clamp_coords(x1, y1)
    cx2, cy2 = _clamp_coords(x2, y2)
    pyautogui.moveTo(cx1, cy1)
    pyautogui.dragTo(cx2, cy2, duration=duration, button="left")
    return f"Dragged from ({cx1},{cy1}) to ({cx2},{cy2})."


def move_mouse(x: int, y: int) -> str:
    """Smooth, quick mouse movement without lingering."""
    ensure_desktop_attached()
    cx, cy = _clamp_coords(x, y)
    pyautogui.moveTo(cx, cy, duration=0.08)
    return f"Mouse moved to ({cx}, {cy})."


# ─── Keyboard operations ──────────────────────────────────────────────────────

_kb = KbController()


def type_text(text: str) -> str:
    """
    Instantly type text into the currently active window using fast clipboard paste.
    Eliminates character-by-character lag, pauses, and keyboard fighting.
    """
    ensure_desktop_attached()
    if not text:
        return "No text to type."
    try:
        pyperclip.copy(text)
        time.sleep(0.02)
        pyautogui.hotkey("ctrl", "v")
        logger.info(f"Typed (pasted): {text[:60]}")
        return f"Typed: {text}"
    except Exception as e:
        pyautogui.write(text, interval=0.002)
        return f"Typed: {text}"


def press_keys(keys: str) -> str:
    """
    Send a hotkey combination.
    keys: comma-separated or plus-separated, e.g. 'ctrl+c' or 'win+d'.
    """
    ensure_desktop_attached()
    parts = [k.strip().lower() for k in keys.replace("+", ",").split(",")]
    pyautogui.hotkey(*parts)
    logger.debug(f"Hotkey: {keys}")
    return f"Pressed {keys}."


def press_single_key(key: str) -> str:
    """Press a single named key, e.g. 'enter', 'escape', 'f5'."""
    ensure_desktop_attached()
    pyautogui.press(key.lower())
    return f"Pressed key: {key}."


def play_pause_media() -> str:
    """Toggle play/pause for video or audio playback."""
    ensure_desktop_attached()
    try:
        pyautogui.press("playpause")
        return "Toggled play/pause."
    except Exception as e:
        return f"Media key error: {e}"


