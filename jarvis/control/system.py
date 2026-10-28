"""
control/system.py – System-level controls (volume, brightness, lock, browser, etc.)
Windows-specific implementations isolated here.
"""

import logging
import os
import subprocess
import webbrowser
from datetime import datetime

import psutil           # type: ignore
import pyautogui        # type: ignore
from pathlib import Path

logger = logging.getLogger("jarvis.control.system")


# ─── Volume ───────────────────────────────────────────────────────────────────

def _run_nircmd(cmd: str) -> bool:
    """Run a nircmd command; returns False if nircmd not found."""
    try:
        subprocess.run(["nircmd.exe", *cmd.split()], check=True, timeout=5,
                       capture_output=True)
        return True
    except FileNotFoundError:
        return False
    except subprocess.CalledProcessError:
        return False


def volume_up(amount: int = 2000) -> str:
    """Increase system volume."""
    if _run_nircmd(f"changesysvolume {amount}"):
        return "Volume increased."
    # Fallback: media key
    pyautogui.press("volumeup")
    return "Volume increased (key press)."


def volume_down(amount: int = 2000) -> str:
    if _run_nircmd(f"changesysvolume -{amount}"):
        return "Volume decreased."
    pyautogui.press("volumedown")
    return "Volume decreased (key press)."


def volume_mute() -> str:
    if _run_nircmd("mutesysvolume 2"):
        return "Volume toggled mute."
    pyautogui.press("volumemute")
    return "Volume muted/unmuted (key press)."


# ─── Brightness ───────────────────────────────────────────────────────────────

def set_brightness(level: int) -> str:
    """Set display brightness (0–100). Requires WMI."""
    level = max(0, min(100, level))
    try:
        import wmi  # type: ignore
        c = wmi.WMI(namespace="wmi")
        methods = c.WmiMonitorBrightnessMethods()[0]
        methods.WmiSetBrightness(level, 0)
        return f"Brightness set to {level}%."
    except Exception as e:
        logger.warning(f"WMI brightness failed: {e}")
        return f"Could not set brightness: {e}"


# ─── Screen lock ──────────────────────────────────────────────────────────────

def lock_screen() -> str:
    import ctypes
    ctypes.windll.user32.LockWorkStation()
    return "Screen locked."


# ─── Screenshot ───────────────────────────────────────────────────────────────

def take_screenshot(filename: str = "") -> str:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    desktop = Path.home() / "Desktop"
    fname = filename or f"screenshot_{ts}.png"
    save_path = desktop / fname
    img = pyautogui.screenshot()
    img.save(str(save_path))
    return f"Screenshot saved to {save_path}."


# ─── Battery ──────────────────────────────────────────────────────────────────

def battery_status() -> str:
    batt = psutil.sensors_battery()
    if batt is None:
        return "No battery detected (desktop PC)."
    percent = batt.percent
    plugged  = "charging" if batt.power_plugged else "on battery"
    secs_left = batt.secsleft
    if secs_left > 0:
        h, m = divmod(secs_left // 60, 60)
        time_str = f", ~{h}h {m}m remaining" if not batt.power_plugged else ""
    else:
        time_str = ""
    return f"Battery is at {percent:.0f}%, {plugged}{time_str}."


# ─── Time & Date ──────────────────────────────────────────────────────────────

def get_time() -> str:
    now = datetime.now()
    return f"It is {now.strftime('%I:%M %p')} on {now.strftime('%A, %B %d, %Y')}."


# ─── Browser & Web ────────────────────────────────────────────────────────────

def _get_friendly_domain(url: str) -> str:
    """Extract a friendly clean name from common domains."""
    url_lower = url.lower()
    mapping = {
        "youtube.com": "YouTube",
        "google.com": "Google",
        "mail.google.com": "Gmail",
        "github.com": "GitHub",
        "chatgpt.com": "ChatGPT",
        "wikipedia.org": "Wikipedia",
        "reddit.com": "Reddit",
        "netflix.com": "Netflix",
        "x.com": "X (Twitter)",
        "twitter.com": "Twitter",
        "whatsapp.com": "WhatsApp",
        "amazon": "Amazon",
        "flipkart": "Flipkart",
        "linkedin.com": "LinkedIn",
    }
    for domain, friendly in mapping.items():
        if domain in url_lower:
            return friendly
    return url


def open_url(url: str) -> str:
    """Open URL and bring the browser window to the foreground."""
    from control.apps import _focus_browser

    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    webbrowser.open(url)
    logger.info(f"Opened URL: {url}")
    import time
    time.sleep(0.6)
    _focus_browser()
    display = _get_friendly_domain(url)
    return f"Opened {display} in your browser for you, sir."


def web_search(query: str) -> str:
    """Search Google for query and bring the browser to the foreground."""
    from control.apps import _focus_browser
    import urllib.parse
    import time

    encoded = urllib.parse.quote_plus(query)
    url = f"https://www.google.com/search?q={encoded}"
    webbrowser.open(url)
    time.sleep(0.6)
    _focus_browser()
    return f"Searched Google for '{query}', sir."


def play_spotify(query: str) -> str:
    """
    Open Spotify directly to the song search page and click to play it with the mouse pointer.
    """
    from control import apps, keyboard_mouse, vision
    from pathlib import Path
    import urllib.parse
    import subprocess
    import time
    import os
    import pyautogui

    # Strip prefixes like "a song", "the song", "song", "an", "a"
    clean_query = query.strip()
    for prefix in ("a song called ", "a song named ", "a song ", "the song ", "song ", "an ", "a "):
        if clean_query.lower().startswith(prefix):
            clean_query = clean_query[len(prefix):].strip()

    logger.info(f"Opening Spotify and playing: {clean_query}")
    encoded = urllib.parse.quote_plus(clean_query)
    search_url = f"https://open.spotify.com/search/{encoded}"

    # 1. Launch Spotify directly on the search results URL
    brave_exe = r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe"
    opened = False
    if os.path.exists(brave_exe):
        try:
            subprocess.Popen([brave_exe, "--profile-directory=Default", f"--app={search_url}"])
            opened = True
            logger.info("Launched Spotify PWA with search URL")
        except Exception as e:
            logger.debug(f"PWA launch failed: {e}")

    if not opened:
        webbrowser.open(search_url)

    time.sleep(2.0)
    apps.focus_window("Spotify")
    time.sleep(0.6)

    sw, sh = pyautogui.size()
    clicked = False

    # 2. Use Windows Native OCR to locate the song in search results (ignoring top search box)
    try:
        pt = vision.ocr_find_text_on_screen(clean_query)
        if pt and pt[0] > 50 and pt[1] >= 140:
            logger.info(f"OCR located song target at ({pt[0]}, {pt[1]})")
            pyautogui.moveTo(pt[0], pt[1], duration=0.4)
            time.sleep(0.15)
            pyautogui.click()
            time.sleep(0.1)
            pyautogui.doubleClick()
            clicked = True
    except Exception as e:
        logger.debug(f"OCR song localization error: {e}")

    # 3. Check for the round green Play button (on Top Result card or bottom player)
    if not clicked:
        try:
            # Hover over Top Result card to trigger hover play button
            top_card_x = int(sw * 0.28)
            top_card_y = int(sh * 0.33)
            pyautogui.moveTo(top_card_x, top_card_y, duration=0.35)
            time.sleep(0.2)

            play_pt = vision.detect_play_button()
            if play_pt:
                logger.info(f"Detected Spotify Play Button at ({play_pt[0]}, {play_pt[1]})")
                pyautogui.moveTo(play_pt[0], play_pt[1], duration=0.3)
                time.sleep(0.1)
                pyautogui.click()
                clicked = True
        except Exception as e:
            logger.debug(f"Play button check error: {e}")

    # 4. Fallback: double click the Top Result card and press Enter
    if not clicked:
        target_x = int(sw * 0.28)
        target_y = int(sh * 0.33)
        pyautogui.moveTo(target_x, target_y, duration=0.4)
        time.sleep(0.15)
        pyautogui.click()
        time.sleep(0.1)
        pyautogui.doubleClick()

    time.sleep(0.2)
    keyboard_mouse.press_single_key("enter")

    return f"Opened Spotify, searched for '{clean_query}', and clicked to play for you, sir."



def play_youtube(query: str) -> str:
    """Search and play a video/song on YouTube and click it with the mouse pointer."""
    from control import apps, keyboard_mouse, vision
    import urllib.parse
    import time
    import pyautogui

    encoded = urllib.parse.quote_plus(query)
    url = f"https://www.youtube.com/results?search_query={encoded}"
    webbrowser.open(url)
    logger.info(f"Opened YouTube search: {url}")
    time.sleep(1.8)
    apps._focus_browser()
    time.sleep(0.5)

    sw, sh = pyautogui.size()
    clicked = False
    try:
        pt = vision.ocr_find_text_on_screen(query)
        if pt and pt[0] > 50 and pt[1] >= 140:
            logger.info(f"OCR located YouTube video at ({pt[0]}, {pt[1]})")
            pyautogui.moveTo(pt[0], pt[1], duration=0.4)
            time.sleep(0.15)
            pyautogui.click()
            clicked = True
    except Exception as e:
        logger.debug(f"YouTube OCR error: {e}")

    if not clicked:
        # Move mouse pointer smoothly to the first video result thumbnail and click
        target_x = int(sw * 0.38)
        target_y = int(sh * 0.34)
        pyautogui.moveTo(target_x, target_y, duration=0.4)
        time.sleep(0.15)
        pyautogui.click()

    return f"Opened YouTube and clicked to play '{query}' for you, sir."



def open_and_search(app: str, query: str) -> str:
    """Open an application, locate its search field, type the query, and press Enter."""
    from control import apps, keyboard_mouse, vision
    import time
    import pyautogui

    apps.open_application(app)
    time.sleep(1.0)
    apps.focus_window(app)
    time.sleep(0.3)

    if app.lower() in ("chrome", "brave", "edge", "firefox", "browser"):
        keyboard_mouse.press_keys("ctrl+l")
    else:
        clicked = False
        try:
            res = vision.click_element_by_description("search bar or search input")
            if "Clicked" in res:
                clicked = True
        except Exception:
            pass
        if not clicked:
            keyboard_mouse.press_keys("ctrl+f")

    time.sleep(0.2)
    keyboard_mouse.type_text(query)
    time.sleep(0.2)
    keyboard_mouse.press_single_key("enter")
    return f"Opened {app.title()} and searched for '{query}' for you, sir."


# ─── Shell command (restricted) ───────────────────────────────────────────────

def run_shell_command(cmd: str) -> str:
    """
    Run a shell command. Caller MUST have checked safety.is_command_dangerous()
    and obtained confirmation before calling this.
    """
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=30,
        )
        output = result.stdout + result.stderr
        logger.info(f"Shell: {cmd!r} → exit {result.returncode}")
        return output.strip() or f"Command ran (exit code {result.returncode})."
    except subprocess.TimeoutExpired:
        return "Command timed out after 30 seconds."
    except Exception as e:
        return f"Error running command: {e}"


# ─── Timer / Reminder ─────────────────────────────────────────────────────────
import threading


def set_timer(seconds: int, label: str = "Timer", speak_fn=None) -> str:
    """Set a non-blocking timer that calls speak_fn when it fires."""
    def _fire():
        import time
        time.sleep(seconds)
        msg = f"{label} is done!" if label != "Timer" else f"Your {seconds}-second timer is done!"
        logger.info(f"Timer fired: {msg}")
        if speak_fn:
            speak_fn(msg)

    t = threading.Thread(target=_fire, daemon=True)
    t.start()
    mins, secs = divmod(seconds, 60)
    if mins:
        readable = f"{mins} minute{'s' if mins > 1 else ''}"
    else:
        readable = f"{secs} second{'s' if secs > 1 else ''}"
    return f"Timer set for {readable}."
