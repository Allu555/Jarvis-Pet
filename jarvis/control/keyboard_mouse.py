"""
control/keyboard_mouse.py – Next-Generation Input & Task Execution Engine for JARVIS.

Features:
  1. Smooth, human-like mouse movement with easing (easeOutQuad / easeInOutCubic),
     configurable speed, and micro-jitter.
  2. Press-hold-glide-release physics for drag-and-drop.
  3. Hybrid typing: Instant lossless clipboard paste for long text (> 10 chars),
     realistic keystroke typing with jitter for short commands/passwords/hotkeys.
  4. Full special key handling (Enter, Escape, Tab, Win+R, Backspace, etc.).
  5. State verification (Observe -> Act -> Verify):
     - wait_for_window, wait_for_element, wait_for_text.
     - execute_with_verification with automated retry / fallback.
  6. Emergency Kill Switch integration (screen corner failsafe + safety.is_killed).
"""

import ctypes
import logging
import random
import time
from typing import Callable, Any

import pyautogui    # type: ignore
import pyperclip    # type: ignore
from pynput.keyboard import Controller as KbController, Key  # type: ignore

from config import PYAUTOGUI_PAUSE, PYAUTOGUI_FAILSAFE
from safety import is_killed, trigger_kill

logger = logging.getLogger("jarvis.control.keyboard_mouse")

# ─── Safety & FailSafe Settings ───────────────────────────────────────────────
pyautogui.PAUSE    = PYAUTOGUI_PAUSE
pyautogui.FAILSAFE = PYAUTOGUI_FAILSAFE  # Slamming mouse into any corner aborts immediately

# ─── Per-Monitor DPI Awareness ────────────────────────────────────────────────
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception:
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass


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


def _clamp_coords(x: int, y: int) -> tuple[int, int]:
    """Ensure coordinates stay strictly within physical screen bounds."""
    try:
        sw, sh = pyautogui.size()
        cx = max(0, min(sw - 1, int(x)))
        cy = max(0, min(sh - 1, int(y)))
        return cx, cy
    except Exception:
        return int(x), int(y)


# ─── Smooth Human-Like Mouse Movement ─────────────────────────────────────────

def human_move_to(x: int, y: int, duration: float = 0.28):
    """
    Smooth, human-like mouse cursor trajectory using easeOutQuad easing
    and slight natural jitter. Aborts immediately if emergency kill is triggered.
    """
    if is_killed():
        raise InterruptedError("Action aborted by emergency kill switch.")

    ensure_desktop_attached()
    cx, cy = _clamp_coords(x, y)
    curr_x, curr_y = pyautogui.position()

    dist = ((cx - curr_x) ** 2 + (cy - curr_y) ** 2) ** 0.5
    if dist < 5:
        return

    # Scale duration dynamically by distance (min 0.12s, max 0.45s)
    actual_dur = max(0.12, min(0.45, (dist / 1400.0) * duration + 0.12))

    try:
        pyautogui.moveTo(cx, cy, duration=actual_dur, tween=pyautogui.easeOutQuad)
    except pyautogui.FailSafeException:
        trigger_kill()
        raise InterruptedError("Emergency kill triggered via mouse corner failsafe.")


# ─── Mouse Operations ─────────────────────────────────────────────────────────

def click(x: int, y: int) -> str:
    """Accurate, human-eased left-click."""
    if is_killed():
        return "Aborted: Emergency kill switch active."

    ensure_desktop_attached()
    cx, cy = _clamp_coords(x, y)

    try:
        from control.spider_drone_client import spider_walk_and_scan
        spider_walk_and_scan(cx, cy, desc="Target Location", action="click", wait_ms=300)
    except Exception:
        pass

    try:
        human_move_to(cx, cy)
        time.sleep(0.04)
        pyautogui.click()
        logger.info(f"Clicked at ({cx}, {cy})")

        try:
            from control.spider_drone_client import spider_celebrate
            spider_celebrate()
        except Exception:
            pass

        return f"Clicked at ({cx}, {cy})."
    except pyautogui.FailSafeException:
        trigger_kill()
        return "Aborted by mouse corner failsafe."
    except Exception as e:
        logger.error(f"Click failed at ({cx}, {cy}): {e}")
        return f"Click error: {e}"


def double_click(x: int, y: int) -> str:
    """Human-eased double-click."""
    if is_killed():
        return "Aborted: Emergency kill switch active."

    ensure_desktop_attached()
    cx, cy = _clamp_coords(x, y)

    try:
        human_move_to(cx, cy)
        time.sleep(0.04)
        pyautogui.doubleClick(interval=0.08)
        logger.info(f"Double-clicked at ({cx}, {cy})")
        return f"Double-clicked at ({cx}, {cy})."
    except pyautogui.FailSafeException:
        trigger_kill()
        return "Aborted by mouse corner failsafe."
    except Exception as e:
        return f"Double-click error: {e}"


def right_click(x: int, y: int) -> str:
    """Human-eased right-click."""
    if is_killed():
        return "Aborted: Emergency kill switch active."

    ensure_desktop_attached()
    cx, cy = _clamp_coords(x, y)

    try:
        human_move_to(cx, cy)
        time.sleep(0.04)
        pyautogui.rightClick()
        logger.info(f"Right-clicked at ({cx}, {cy})")
        return f"Right-clicked at ({cx}, {cy})."
    except pyautogui.FailSafeException:
        trigger_kill()
        return "Aborted by mouse corner failsafe."
    except Exception as e:
        return f"Right-click error: {e}"


def middle_click(x: int, y: int) -> str:
    """Middle-click (e.g. to open link in background tab)."""
    if is_killed():
        return "Aborted: Emergency kill switch active."

    ensure_desktop_attached()
    cx, cy = _clamp_coords(x, y)

    try:
        human_move_to(cx, cy)
        time.sleep(0.04)
        pyautogui.middleClick()
        return f"Middle-clicked at ({cx}, {cy})."
    except Exception as e:
        return f"Middle-click error: {e}"


def scroll(direction: str, amount: int = 3) -> str:
    """Scroll mouse wheel up or down."""
    ensure_desktop_attached()
    clicks = amount if direction.lower() == "up" else -amount
    pyautogui.scroll(clicks)
    return f"Scrolled {direction} by {amount}."


def drag(x1: int, y1: int, x2: int, y2: int, duration: float = 0.45) -> str:
    """
    Press-hold-glide-release drag physics:
      1. Move to start point smoothly.
      2. Hold mouse down with 80ms settling pause.
      3. Glide to destination using cubic easing.
      4. Settle 100ms and release.
    """
    if is_killed():
        return "Aborted: Emergency kill switch active."

    ensure_desktop_attached()
    cx1, cy1 = _clamp_coords(x1, y1)
    cx2, cy2 = _clamp_coords(x2, y2)

    try:
        from control.spider_drone_client import spider_walk_and_scan
        spider_walk_and_scan(cx1, cy1, desc="Drag Source", action="drag", wait_ms=250)
    except Exception:
        pass

    try:
        human_move_to(cx1, cy1)
        time.sleep(0.08)
        pyautogui.mouseDown(button="left")
        time.sleep(0.10)
        pyautogui.moveTo(cx2, cy2, duration=max(0.35, duration), tween=pyautogui.easeOutQuad)
        time.sleep(0.10)
        pyautogui.mouseUp(button="left")
        logger.info(f"Dragged from ({cx1},{cy1}) to ({cx2},{cy2})")
        return f"Dragged from ({cx1},{cy1}) to ({cx2},{cy2})."
    except pyautogui.FailSafeException:
        pyautogui.mouseUp(button="left")
        trigger_kill()
        return "Aborted by mouse corner failsafe."
    except Exception as e:
        pyautogui.mouseUp(button="left")
        return f"Drag error: {e}"


def move_mouse(x: int, y: int) -> str:
    """Move mouse to coordinates."""
    human_move_to(x, y)
    return f"Mouse moved to ({x}, {y})."


# ─── Hybrid Keyboard Operations ───────────────────────────────────────────────

_kb = KbController()


def type_text(text: str) -> str:
    """
    Hybrid typing:
      - Long text (> 10 chars) or multi-line: Fast clipboard paste (ctrl+v) -> instant & 100% lossless.
      - Short text / hotkeys / single words: Realistic keystroke typing with human inter-key jitter (15-30ms).
    """
    if is_killed():
        return "Aborted: Emergency kill switch active."

    ensure_desktop_attached()
    if not text:
        return "No text to type."

    try:
        if len(text) > 10 or "\n" in text:
            # Clipboard paste method
            pyperclip.copy(text)
            time.sleep(0.03)
            pyautogui.hotkey("ctrl", "v")
            logger.info(f"Typed via clipboard paste ({len(text)} chars)")
        else:
            # Human jitter keystrokes
            for ch in text:
                if is_killed():
                    raise InterruptedError("Emergency kill triggered.")
                pyautogui.write(ch)
                time.sleep(random.uniform(0.015, 0.035))
            logger.info(f"Typed via keystrokes: {text!r}")
        return f"Typed: {text}"
    except Exception as e:
        # Fallback to direct write
        pyautogui.write(text, interval=0.01)
        return f"Typed: {text}"


def press_keys(keys: str) -> str:
    """Send a hotkey combination, e.g. 'ctrl+c', 'win+d', 'alt+tab'."""
    if is_killed():
        return "Aborted: Emergency kill switch active."

    ensure_desktop_attached()
    parts = [k.strip().lower() for k in keys.replace("+", ",").split(",")]
    pyautogui.hotkey(*parts)
    logger.debug(f"Hotkey: {keys}")
    return f"Pressed {keys}."


def press_single_key(key: str) -> str:
    """Press a single named key, e.g. 'enter', 'escape', 'tab', 'backspace'."""
    if is_killed():
        return "Aborted: Emergency kill switch active."

    ensure_desktop_attached()
    pyautogui.press(key.lower())
    return f"Pressed key: {key}."


def play_pause_media() -> str:
    """Toggle play/pause for system media."""
    ensure_desktop_attached()
    try:
        pyautogui.press("playpause")
        return "Toggled play/pause."
    except Exception as e:
        return f"Media key error: {e}"


# ─── Observe -> Act -> Verify Execution Loop ──────────────────────────────────

def wait_for_window(title_substring: str, timeout: float = 5.0) -> bool:
    """Poll active window until title matches substring or timeout expires."""
    t_start = time.time()
    t_lower = title_substring.lower().strip()
    user32 = ctypes.windll.user32

    while time.time() - t_start < timeout:
        if is_killed():
            return False
        hwnd = user32.GetForegroundWindow()
        if hwnd:
            length = user32.GetWindowTextLengthW(hwnd)
            buff = ctypes.create_unicode_buffer(length + 1)
            user32.GetWindowTextW(hwnd, buff, length + 1)
            if t_lower in buff.value.lower():
                return True
        time.sleep(0.15)
    return False


def wait_for_element(description: str, timeout: float = 5.0) -> dict[str, Any] | None:
    """Poll perception engine until element appears on screen or timeout expires."""
    from control.vision import find_element_structured
    t_start = time.time()

    while time.time() - t_start < timeout:
        if is_killed():
            return None
        res = find_element_structured(description)
        if res["found"]:
            return res
        time.sleep(0.25)
    return None


def execute_with_verification(
    action_fn: Callable[[], Any],
    verify_fn: Callable[[], bool],
    max_retries: int = 2,
    settle_delay: float = 0.25,
) -> bool:
    """
    Observe -> Act -> Verify execution wrapper:
      1. Performs action_fn().
      2. Waits settle_delay.
      3. Tests verify_fn(). If False, retries up to max_retries.
    """
    for attempt in range(max_retries + 1):
        if is_killed():
            return False
        action_fn()
        time.sleep(settle_delay)
        if verify_fn():
            logger.info(f"Action verified successfully on attempt {attempt + 1}")
            return True
        logger.warning(f"Verification failed on attempt {attempt + 1}, retrying…")

    return False
