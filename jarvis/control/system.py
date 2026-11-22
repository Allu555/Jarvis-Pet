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
    Open Spotify directly in maximized full screen, search for the song/track, and click to play it.
    """
    from control import apps, keyboard_mouse, vision
    from control.keyboard_mouse import ensure_desktop_attached
    import urllib.parse
    import subprocess
    import time
    import os
    import pyautogui
    import ctypes

    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except Exception:
        pass
    ensure_desktop_attached()

    # Strip prefixes like "a song", "the song", "song", "an", "a"
    clean_query = query.strip()
    for prefix in ("a song called ", "a song named ", "a song ", "the song ", "song ", "an ", "a "):
        if clean_query.lower().startswith(prefix):
            clean_query = clean_query[len(prefix):].strip()

    logger.info(f"Opening Spotify in full screen and playing: {clean_query}")

    # 1. Check if Spotify is already running; if not, launch it fresh via the installed PWA
    win = apps._find_matching_window("Spotify", apps._get_all_windows())
    if not win:
        pwa_lnk = os.path.expandvars(r"%APPDATA%\Microsoft\Internet Explorer\Quick Launch\User Pinned\TaskBar\Spotify.lnk")
        desktop_lnk = os.path.expandvars(r"%USERPROFILE%\OneDrive\Desktop\Spotify.lnk")
        lnk_to_use = pwa_lnk if os.path.exists(pwa_lnk) else (desktop_lnk if os.path.exists(desktop_lnk) else "")
        working_dir = r"C:\Program Files\BraveSoftware\Brave-Browser\Application"

        if lnk_to_use and os.path.exists(lnk_to_use):
            ctypes.windll.shell32.ShellExecuteW(None, "open", lnk_to_use, None, working_dir, 3)  # 3 = SW_MAXIMIZE
        else:
            apps.open_application("spotify")
        time.sleep(2.5)

    apps.focus_window("Spotify", maximize=True)
    apps.maximize_window("Spotify")
    time.sleep(0.5)
    sw, sh = pyautogui.size()
    wx1, wy1, ww, wh = 0, 0, sw, sh
    try:
        import win32gui
        def _enum_cb(hwnd, extra):
            if win32gui.IsWindowVisible(hwnd):
                t = win32gui.GetWindowText(hwnd).lower()
                p = ""
                try:
                    import win32process
                    _, pid = win32process.GetWindowThreadProcessId(hwnd)
                    p = psutil.Process(pid).name().lower()
                except Exception:
                    pass
                if "spotify" in t or "spotify" in p or (" • " in win32gui.GetWindowText(hwnd) and any(b in p for b in ("brave", "chrome", "edge", "firefox"))):
                    r = win32gui.GetWindowRect(hwnd)
                    if r[2] - r[0] > 300 and r[3] - r[1] > 300:
                        ctypes.windll.user32.ShowWindow(hwnd, 3)  # SW_MAXIMIZE
                        extra.append((hwnd, r))
        wins = []
        win32gui.EnumWindows(_enum_cb, wins)
        if wins:
            r = win32gui.GetWindowRect(wins[0][0])
            wx1, wy1 = max(0, r[0]), max(0, r[1])
            ww = min(sw, r[2]) - wx1
            wh = min(sh, r[3]) - wy1
    except Exception:
        pass

    # 2. Focus Spotify Search input box and enter query cleanly
    search_bar_x = wx1 + int(ww * 0.49)
    search_bar_y = wy1 + 58
    logger.info(f"Focusing Spotify search input at ({search_bar_x}, {search_bar_y})")
    pyautogui.moveTo(search_bar_x, search_bar_y, duration=0.15)
    time.sleep(0.05)
    keyboard_mouse.click(search_bar_x, search_bar_y)
    time.sleep(0.2)
    keyboard_mouse.press_keys("ctrl+a")
    time.sleep(0.08)
    keyboard_mouse.press_single_key("backspace")
    time.sleep(0.08)

    # Use clipboard paste for instant, 100% accurate text entry without dropping keys
    try:
        import pyperclip
        pyperclip.copy(clean_query)
        keyboard_mouse.press_keys("ctrl+v")
    except Exception:
        keyboard_mouse.type_text(clean_query)

    time.sleep(0.25)
    keyboard_mouse.press_single_key("enter")
    time.sleep(1.3)

    # 3. Locate and play the music from search results
    clicked = False

    # Check if a play button is directly visible (Top Result banner or playlist header)
    play_pt = vision.detect_play_button()
    if play_pt:
        logger.info(f"Directly detected visible Spotify Play Button at ({play_pt[0]}, {play_pt[1]})")
        pyautogui.moveTo(play_pt[0], play_pt[1], duration=0.15)
        time.sleep(0.1)
        keyboard_mouse.click(play_pt[0], play_pt[1])
        clicked = True

    # If direct play button wasn't immediately visible, try hovering candidate cards
    if not clicked:
        candidates = [
            (wx1 + int(ww * 0.22), wy1 + 200),             # Top result card
            (wx1 + int(ww * 0.18), wy1 + int(wh * 0.44)),  # First playlist/genre card
            (wx1 + int(ww * 0.25), wy1 + 300),             # Track 1 row
        ]
        for hx, hy in candidates:
            pyautogui.moveTo(hx, hy, duration=0.18)
            time.sleep(0.25)
            play_pt = vision.detect_play_button(near_x=hx, near_y=hy)
            if play_pt:
                logger.info(f"Detected Spotify Play Button on hover at ({play_pt[0]}, {play_pt[1]})")
                pyautogui.moveTo(play_pt[0], play_pt[1], duration=0.15)
                time.sleep(0.1)
                keyboard_mouse.click(play_pt[0], play_pt[1])
                clicked = True
                break

    # If hovering didn't reveal play button, click the Top Result card to start playback or open playlist
    if not clicked:
        card_x = wx1 + int(ww * 0.18)
        card_y = wy1 + 200
        logger.info(f"Clicking Top Result card at ({card_x}, {card_y})")
        pyautogui.moveTo(card_x, card_y, duration=0.18)
        time.sleep(0.1)
        keyboard_mouse.click(card_x, card_y)
        time.sleep(0.9)

        play_pt2 = vision.detect_play_button()
        if play_pt2:
            logger.info(f"Detected Spotify Play Button inside playlist page at ({play_pt2[0]}, {play_pt2[1]})")
            pyautogui.moveTo(play_pt2[0], play_pt2[1], duration=0.15)
            time.sleep(0.1)
            keyboard_mouse.click(play_pt2[0], play_pt2[1])
            clicked = True
        else:
            track1_x = wx1 + int(ww * 0.25)
            track1_y = wy1 + 300
            logger.info(f"Double clicking Track 1 in playlist at ({track1_x}, {track1_y})")
            pyautogui.moveTo(track1_x, track1_y, duration=0.18)
            time.sleep(0.1)
            keyboard_mouse.double_click(track1_x, track1_y)
            clicked = True

    # 4. Fallback if still not clicked
    if not clicked:
        track1_x = wx1 + int(ww * 0.25)
        track1_y = wy1 + 300
        logger.info(f"Fallback double clicking Track 1 in playlist at ({track1_x}, {track1_y})")
        pyautogui.moveTo(track1_x, track1_y, duration=0.18)
        time.sleep(0.1)
        keyboard_mouse.double_click(track1_x, track1_y)
        clicked = True

    # Move cursor safely away so hover tooltips or card focus do not interfere
    pyautogui.moveTo(wx1 + int(ww * 0.85), wy1 + 100, duration=0.2)

    return f"Opened Spotify in full screen, searched for '{clean_query}', and started playback for you, sir."



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
    apps._focus_browser(maximize=True)
    apps.maximize_window("browser")
    time.sleep(0.5)

    sw, sh = pyautogui.size()
    clicked = False
    try:
        res = vision.ocr_find_text_on_screen(query)
        if res and res.get("found"):
            tx, ty = res["x"], res["y"]
            if ty >= 140:
                logger.info(f"OCR located YouTube video at ({tx}, {ty})")
                pyautogui.moveTo(tx, ty, duration=0.35)
                time.sleep(0.15)
                pyautogui.click()
                clicked = True
    except Exception as e:
        logger.debug(f"YouTube OCR error: {e}")

    if not clicked:
        # Move mouse pointer smoothly to the first video result thumbnail and click
        target_x = int(sw * 0.38)
        target_y = int(sh * 0.34)
        pyautogui.moveTo(target_x, target_y, duration=0.35)
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
            creationflags=0x08000000,
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


def set_reminder(seconds: int, message: str, speak_fn=None) -> str:
    """Set a non-blocking reminder that speaks the message when it fires."""
    def _fire():
        import time
        time.sleep(seconds)
        reminder_msg = f"Sir, here is your reminder: {message}"
        logger.info(f"Reminder fired: {reminder_msg}")
        if speak_fn:
            speak_fn(reminder_msg)

    t = threading.Thread(target=_fire, daemon=True)
    t.start()
    mins, secs = divmod(seconds, 60)
    hours, mins = divmod(mins, 60)
    parts = []
    if hours:
        parts.append(f"{hours} hour{'s' if hours > 1 else ''}")
    if mins:
        parts.append(f"{mins} minute{'s' if mins > 1 else ''}")
    if secs or not parts:
        parts.append(f"{secs} second{'s' if secs > 1 else ''}")
    readable = " and ".join(parts)
    return f"Reminder set for {readable} from now: {message}."


def get_weather(location: str = "") -> str:
    """Get current weather forecast for a specified city or current location via wttr.in."""
    import urllib.request
    import urllib.parse
    import json

    loc = location.strip()
    loc_encoded = urllib.parse.quote(loc) if loc else ""
    url = f"https://wttr.in/{loc_encoded}?format=j1"

    try:
        req = urllib.request.Request(url, headers={"User-Agent": "curl/7.68.0"})
        with urllib.request.urlopen(req, timeout=4.5) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            area_name = loc.title() if loc else (data.get("nearest_area", [{}])[0].get("areaName", [{}])[0].get("value", "your location"))
            curr = data.get("current_condition", [{}])[0]
            desc = curr.get("weatherDesc", [{}])[0].get("value", "Clear")
            temp = curr.get("temp_C", "--")
            feels = curr.get("FeelsLikeC", temp)
            humidity = curr.get("humidity", "--")
            wind = curr.get("windspeedKmph", "--")
            return f"The weather in {area_name} is currently {desc}, {temp}°C (feels like {feels}°C), with {humidity}% humidity and {wind} km/h wind."
    except Exception as e:
        logger.warning(f"Weather lookup error: {e}")
        return f"Could not retrieve weather live ({e}). I can open the forecast in your browser."


def get_news(topic: str = "general") -> str:
    """Fetch top news headlines for topic from Google News RSS."""
    import urllib.request
    import urllib.parse
    import xml.etree.ElementTree as ET

    t = topic.strip() or "top headlines"
    url = f"https://news.google.com/rss/search?q={urllib.parse.quote(t)}&hl=en-US&gl=US&ceid=US:en"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=4.5) as resp:
            xml_data = resp.read()
            root = ET.fromstring(xml_data)
            items = root.findall(".//item")[:3]
            headlines = []
            for idx, item in enumerate(items, 1):
                title_elem = item.find("title")
                if title_elem is not None and title_elem.text:
                    clean_t = title_elem.text.split(" - ")[0]
                    headlines.append(f"{idx}. {clean_t}")
            if headlines:
                return f"Here are the latest headlines on {t}: " + "; ".join(headlines) + "."
            return f"No recent headlines found for '{t}', sir."
    except Exception as e:
        logger.warning(f"News lookup error: {e}")
        return f"Unable to fetch news feed right now ({e})."


def system_info() -> str:
    """Retrieve instant CPU, RAM, disk, battery, and process stats."""
    try:
        cpu = psutil.cpu_percent(interval=0.15)
        ram = psutil.virtual_memory()
        disk = psutil.disk_usage("/")
        batt = psutil.sensors_battery()
        batt_str = f", Battery at {batt.percent}%{' (Charging)' if batt.power_plugged else ''}" if batt else ""
        return (
            f"System Status: CPU usage is {cpu:.0f}%, "
            f"RAM is at {ram.percent:.0f}% ({ram.used // (1024**3)} GB used of {ram.total // (1024**3)} GB), "
            f"Primary drive is {disk.percent:.0f}% full{batt_str}. All systems operating normally, sir."
        )
    except Exception as e:
        logger.warning(f"System info error: {e}")
        return f"Error retrieving system stats: {e}"

