"""
control/apps.py – Launch, focus, and close applications on Windows.
OS-specific code is isolated here.
"""

import ctypes
import glob
import logging
import os
import re
import subprocess
import time
import winreg
from pathlib import Path

import psutil         # type: ignore
import pygetwindow as gw  # type: ignore

# ─── Fix: Prevent LP_RECT / RECT ctypes collision in pygetwindow ─────────────
try:
    ctypes.windll.user32.GetWindowRect.argtypes = None
    _orig_gw_getWindowRect = gw.Win32Window._getWindowRect

    def _safe_gw_getWindowRect(self):
        try:
            ctypes.windll.user32.GetWindowRect.argtypes = None
            return _orig_gw_getWindowRect(self)
        except Exception:
            import pyrect
            class _LocalRECT(ctypes.Structure):
                _fields_ = [('left', ctypes.c_long), ('top', ctypes.c_long), ('right', ctypes.c_long), ('bottom', ctypes.c_long)]
            r = _LocalRECT()
            ctypes.windll.user32.GetWindowRect.argtypes = None
            if ctypes.windll.user32.GetWindowRect(int(self._hWnd), ctypes.byref(r)) != 0:
                return pyrect.Rect(r.left, r.top, r.right - r.left, r.bottom - r.top)
            return pyrect.Rect(0, 0, 800, 600)

    gw.Win32Window._getWindowRect = _safe_gw_getWindowRect
except Exception:
    pass

from config import APP_MAP
from control.keyboard_mouse import ensure_desktop_attached

logger = logging.getLogger("jarvis.control.apps")

# ─── Windows Shell Folders & Protocols ────────────────────────────────────────

SPECIAL_PROTOCOLS: dict[str, str] = {
    "settings": "ms-settings:",
    "windows settings": "ms-settings:",
    "calculator": "ms-calculator:",
    "calc": "ms-calculator:",
    "camera": "microsoft.windows.camera:",
    "webcam": "microsoft.windows.camera:",
    "store": "ms-windows-store:",
    "microsoft store": "ms-windows-store:",
    "photos": "ms-photos:",
    "weather": "bingweather:",
    "clock": "ms-clock:",
    "alarms": "ms-clock:",
    "paint 3d": "ms-paint:",
}

SPECIAL_FOLDERS: dict[str, Path] = {
    "downloads": Path.home() / "Downloads",
    "download": Path.home() / "Downloads",
    "documents": Path.home() / "Documents",
    "document": Path.home() / "Documents",
    "desktop": Path.home() / "Desktop",
    "pictures": Path.home() / "Pictures",
    "photos folder": Path.home() / "Pictures",
    "videos": Path.home() / "Videos",
    "music": Path.home() / "Music",
}


def bring_window_to_front(hwnd: int) -> bool:
    """Reliably bring any window HWND to the foreground ahead of all other windows."""
    ensure_desktop_attached()
    user32 = ctypes.windll.user32
    kernel32 = ctypes.windll.kernel32

    try:
        if not user32.IsWindow(hwnd):
            return False

        # Bypass Windows ForegroundLockTimeout
        user32.SystemParametersInfoW(0x2001, 0, 0, 0x0002)  # SPI_SETFOREGROUNDLOCKTIMEOUT = 0
        user32.AllowSetForegroundWindow(-1)                 # ASFW_ANY
        user32.LockSetForegroundWindow(2)                   # LSFW_UNLOCK

        # Restore if minimized (SW_RESTORE = 9), then maximize or show
        if user32.IsIconic(hwnd):
            user32.ShowWindow(hwnd, 9)
        else:
            user32.ShowWindow(hwnd, 5)

        cur_thread = kernel32.GetCurrentThreadId()
        fg_hwnd = user32.GetForegroundWindow()
        fg_thread = user32.GetWindowThreadProcessId(fg_hwnd, None) if fg_hwnd else 0
        target_thread = user32.GetWindowThreadProcessId(hwnd, None)

        if fg_thread and cur_thread != fg_thread:
            user32.AttachThreadInput(cur_thread, fg_thread, True)
        if target_thread and cur_thread != target_thread:
            user32.AttachThreadInput(cur_thread, target_thread, True)

        # Windows Alt-key trick to bypass SetForegroundWindow restrictions
        VK_MENU = 0x12
        KEYEVENTF_KEYUP = 0x0002
        user32.keybd_event(VK_MENU, 0, 0, 0)
        time.sleep(0.02)
        user32.SetForegroundWindow(hwnd)
        user32.BringWindowToTop(hwnd)
        user32.keybd_event(VK_MENU, 0, KEYEVENTF_KEYUP, 0)

        # Flash TOPMOST briefly to surface above maximized background windows
        HWND_TOPMOST = -1
        HWND_NOTOPMOST = -2
        SWP_NOSIZE = 0x0001
        SWP_NOMOVE = 0x0002
        SWP_SHOWWINDOW = 0x0040
        user32.SetWindowPos(hwnd, HWND_TOPMOST, 0, 0, 0, 0, SWP_NOMOVE | SWP_NOSIZE | SWP_SHOWWINDOW)
        time.sleep(0.04)
        user32.SetWindowPos(hwnd, HWND_NOTOPMOST, 0, 0, 0, 0, SWP_NOMOVE | SWP_NOSIZE | SWP_SHOWWINDOW)
        user32.SetForegroundWindow(hwnd)

        if fg_thread and cur_thread != fg_thread:
            user32.AttachThreadInput(cur_thread, fg_thread, False)
        if target_thread and cur_thread != target_thread:
            user32.AttachThreadInput(cur_thread, target_thread, False)

        return True
    except Exception as e:
        logger.warning(f"Could not bring window {hwnd} to front: {e}")
        return False


def _find_in_registry_app_paths(name: str) -> str | None:
    """Look up executable path in Windows App Paths registry keys."""
    key_name = name.lower().strip()
    roots = [
        (winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\App Paths"),
        (winreg.HKEY_LOCAL_MACHINE, r"Software\Microsoft\Windows\CurrentVersion\App Paths"),
    ]
    for root, subkey in roots:
        try:
            with winreg.OpenKey(root, subkey) as master:
                num_subkeys, _, _ = winreg.QueryInfoKey(master)
                for i in range(num_subkeys):
                    sub = winreg.EnumKey(master, i)
                    sub_lower = sub.lower()
                    if key_name == sub_lower or key_name in sub_lower or f"{key_name}.exe" == sub_lower:
                        with winreg.OpenKey(master, sub) as app_key:
                            val, _ = winreg.QueryValueEx(app_key, "")
                            if val and Path(val).exists():
                                return val
        except Exception:
            pass
    return None


def _find_in_local_programs(name: str) -> str | None:
    """Scan LocalAppData/Programs and ProgramFiles for matching .exe."""
    key = name.lower().strip()
    search_dirs = [
        Path(os.environ.get("LOCALAPPDATA", "")) / "Programs",
        Path(os.environ.get("ProgramFiles", "C:/Program Files")),
        Path(os.environ.get("ProgramFiles(x86)", "C:/Program Files (x86)")),
    ]
    for pdir in search_dirs:
        if not pdir.exists():
            continue
        try:
            for item in pdir.iterdir():
                if item.is_dir() and key in item.name.lower():
                    # Look for executable inside
                    for exe in item.glob("*.exe"):
                        if "update" not in exe.name.lower() and "unins" not in exe.name.lower():
                            return str(exe)
                    # Look one level down
                    for exe in item.glob("*/*.exe"):
                        if "update" not in exe.name.lower() and "unins" not in exe.name.lower():
                            return str(exe)
        except Exception:
            pass
    return None


def _resolve_path(name: str) -> str | None:
    """
    Find executable path, URI, or folder for `name`:
      1. Special protocol schemes (ms-settings:, ms-calculator:)
      2. Special folders (Downloads, Documents, Desktop)
      3. Config APP_MAP
      4. Windows App Paths registry
      5. Start Menu shortcuts (.lnk)
      6. Local Programs and Program Files
      7. PATH lookup via 'where'
    """
    key = name.lower().strip()

    # 1. Protocols
    if key in SPECIAL_PROTOCOLS:
        return SPECIAL_PROTOCOLS[key]

    # 2. Folders
    if key in SPECIAL_FOLDERS:
        return str(SPECIAL_FOLDERS[key])

    # 3. Config APP_MAP
    candidate = APP_MAP.get(key) or APP_MAP.get(key.replace(" ", ""))
    if candidate:
        if candidate.startswith(("http://", "https://", "ms-")):
            return candidate
        if candidate.endswith(".exe") and ("/" not in candidate and "\\" not in candidate):
            return candidate
        if "*" in candidate:
            matches = glob.glob(candidate)
            if matches:
                candidate = sorted(matches)[-1]
        if Path(candidate).exists():
            return candidate
        try:
            r = subprocess.run(["where", candidate], capture_output=True, text=True, timeout=2, creationflags=0x08000000)
            if r.returncode == 0:
                return r.stdout.strip().splitlines()[0]
        except Exception:
            pass

    # 4. Registry App Paths
    reg_path = _find_in_registry_app_paths(key) or _find_in_registry_app_paths(key.replace(" ", ""))
    if reg_path:
        return reg_path

    # 5. Start Menu shortcuts (.lnk)
    start_dirs = [
        Path(os.environ.get("APPDATA", "")) / "Microsoft/Windows/Start Menu/Programs",
        Path("C:/ProgramData/Microsoft/Windows/Start Menu/Programs"),
    ]
    clean_k = key.replace(" ", "")
    for sdir in start_dirs:
        if not sdir.exists():
            continue
        for lnk in sdir.rglob("*.lnk"):
            stem_clean = lnk.stem.lower().replace(" ", "")
            if key in lnk.stem.lower() or clean_k in stem_clean:
                return str(lnk)

    # 6. Local Programs & Program Files
    local_prog = _find_in_local_programs(key) or _find_in_local_programs(clean_k)
    if local_prog:
        return local_prog

    # 7. PATH lookup via 'where'
    for lookup in (name, key, clean_k):
        try:
            result = subprocess.run(
                ["where", lookup], capture_output=True, text=True, timeout=2, creationflags=0x08000000
            )
            if result.returncode == 0:
                found = result.stdout.strip().splitlines()[0]
                if Path(found).exists():
                    return found
        except Exception:
            pass

    return None


class WindowItem:
    def __init__(self, hwnd: int, title: str, pid: int, pname: str):
        self.hwnd = hwnd
        self._hWnd = hwnd
        self.title = title
        self.pid = pid
        self.pname = pname

    def __repr__(self):
        return f"<WindowItem hwnd={self.hwnd} title={self.title!r} pname={self.pname!r}>"


_last_minimized_title: str = ""
_last_minimized_hwnd: int = 0
_last_interacted_app: str = ""


def _get_all_windows() -> list[WindowItem]:
    """
    Enumerate all real application windows using Windows native Win32 APIs.
    Returns a list of WindowItem objects.
    """
    ensure_desktop_attached()
    import win32gui, win32process
    user32 = ctypes.windll.user32
    result: list[WindowItem] = []

    def _cb(hwnd, extra):
        if user32.IsWindow(hwnd):
            t = win32gui.GetWindowText(hwnd).strip()
            is_vis = user32.IsWindowVisible(hwnd)
            is_icon = user32.IsIconic(hwnd)
            if is_vis or is_icon:
                pid_c = ctypes.c_ulong()
                user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid_c))
                pid = pid_c.value
                pname = ""
                try:
                    pname = psutil.Process(pid).name().lower()
                except Exception:
                    pass
                if t or pname:
                    extra.append(WindowItem(hwnd, t, pid, pname))

    win32gui.EnumWindows(_cb, result)
    return result


def open_application(name: str) -> str:
    """
    Launch or focus an application, folder, or service by friendly name.
    """
    ensure_desktop_attached()
    global _last_minimized_title, _last_minimized_hwnd, _last_interacted_app
    key = name.lower().strip()

    # Contextual keywords like "open again", "open it", "restore it"
    if key in ("again", "it", "that", "this", "window", "app", "application", "previous", "last") or key.startswith("again"):
        return restore_window()

    # Tab management requests routed via open_application (e.g. "another tab", "another tab in chrome", "new tab")
    if "tab" in key:
        m_br = re.search(r'\b(chrome|brave|edge|firefox|opera)\b', key)
        browser = m_br.group(1) if m_br else ""
        return open_browser_tab(browser)

    # 1. First check if a matching window is ALREADY running and simply bring it to front
    windows = _get_all_windows()
    for w in windows:
        if (key in w.title.lower()) or (key in w.pname):
            ctypes.windll.user32.ShowWindow(w.hwnd, 9)  # SW_RESTORE
            bring_window_to_front(w.hwnd)
            _last_interacted_app = name
            logger.info(f"App '{name}' was already open; brought window {w.hwnd} ({w.title!r}) to front")
            return f"Brought {name.title()} to the foreground for you, sir."

    # 2. Path resolution
    path = _resolve_path(name)
    if not path:
        logger.warning(f"Could not resolve path for '{name}'")
        return f"I couldn't locate an application called '{name}'. Please verify the name."

    _last_interacted_app = name
    try:
        # Web URL
        if path.startswith(("http://", "https://")):
            import webbrowser
            webbrowser.open(path)
            logger.info(f"Opened URL: {path}")
            time.sleep(0.6)
            _focus_browser()
            return f"Opened {name.title()} in your browser, sir."

        # UWP Protocol
        elif path.startswith("ms-") or path.startswith("microsoft.") or path.startswith("bing"):
            os.startfile(path)
            logger.info(f"Launched protocol: {path}")
            time.sleep(1.0)
            focus_window(name)
            return f"Opened {name.title()} for you, sir."

        # Folder
        elif Path(path).is_dir():
            os.startfile(path)
            logger.info(f"Opened folder: {path}")
            time.sleep(0.8)
            focus_window(name)
            return f"Opened your {name.title()} folder, sir."

        # Shortcut (.lnk)
        elif path.endswith(".lnk"):
            os.startfile(path)
            logger.info(f"Launched shortcut: {path}")
            time.sleep(1.2)
            focus_window(name)
            return f"Opened {name.title()} for you, sir."

        # Executable
        else:
            if "chrome.exe" in path.lower() or "brave.exe" in path.lower():
                try:
                    os.startfile(path)
                except Exception:
                    subprocess.Popen([path])
            else:
                subprocess.Popen([path])
            logger.info(f"Launched binary: {path}")
            time.sleep(1.2)
            focus_window(name)
            return f"Opened {name.title()} for you, sir."

    except Exception as e:
        logger.error(f"Failed to open {name}: {e}")
        return f"Failed to open {name}: {e}"


def _focus_browser(maximize: bool = False) -> bool:
    """Bring the active browser window to the front."""
    ensure_desktop_attached()
    browser_names = ["chrome", "brave", "firefox", "edge", "opera"]
    try:
        windows = _get_all_windows()
        for b in browser_names:
            for w in windows:
                if (b in w.title.lower() or b in w.pname) and "spotify" not in w.title.lower():
                    if maximize:
                        ctypes.windll.user32.ShowWindow(w.hwnd, 3)  # SW_MAXIMIZE
                    else:
                        ctypes.windll.user32.ShowWindow(w.hwnd, 9)  # SW_RESTORE
                    bring_window_to_front(w.hwnd)
                    return True
    except Exception:
        pass
    return False


def close_application(name: str) -> str:
    """Terminate a running process by name or window title."""
    closed = []
    key = name.lower().strip()

    for proc in psutil.process_iter(["pid", "name", "exe"]):
        try:
            proc_name = (proc.info["name"] or "").lower()
            proc_exe  = (proc.info["exe"]  or "").lower()
            if key in proc_name or key in proc_exe:
                proc.terminate()
                closed.append(proc.info["name"])
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass

    if closed:
        return f"Closed {', '.join(set(closed))} for you, sir."

    # If no process matched by executable name, try matching and closing active window (e.g. Spotify PWA)
    all_wins = _get_all_windows()
    win = _find_matching_window(name, all_wins)
    if win:
        try:
            WM_CLOSE = 0x0010
            ctypes.windll.user32.PostMessageW(win.hwnd, WM_CLOSE, 0, 0)
            return f"Closed {win.title or name} for you, sir."
        except Exception:
            pass

    return f"No running application found matching '{name}'."


def _normalize_title_search(title: str) -> str:
    key = title.lower().strip()
    alias_map = {
        "not pad": "notepad",
        "not tab": "notepad",
        "not bad": "notepad",
        "northbound": "notepad",
        "note pad": "notepad",
        "calcy": "calculator",
        "calculater": "calculator",
        "calc": "calculator",
        "chrom": "chrome",
        "crome": "chrome",
    }
    return alias_map.get(key, key)


def _find_matching_window(title: str, all_wins: list[WindowItem]) -> WindowItem | None:
    search_key = _normalize_title_search(title)
    if not search_key:
        return None

    # Special handling for Spotify (native app, PWA, or browser tab with song)
    if search_key in ("spotify", "music", "song"):
        for w in all_wins:
            if w.title.strip().lower() == "spotify" and "antigravity" not in w.pname.lower():
                return w
        for w in all_wins:
            if "spotify" in w.pname.lower():
                return w
        for w in all_wins:
            if "antigravity" in w.pname.lower() or "code.exe" in w.pname.lower():
                continue
            t = w.title.lower()
            p = w.pname.lower()
            if (" • " in w.title or "spotify" in t) and any(b in p for b in ("brave", "chrome", "edge", "opera", "firefox")):
                return w

    # Special handling for Chrome
    if search_key in ("chrome", "google chrome"):
        for w in all_wins:
            if "chrome.exe" in w.pname.lower():
                return w

    # General matching, but exclude IDE/editor windows unless specifically requested
    ide_names = ("antigravity", "code", "ide", "vscode", "vs code")
    is_looking_for_ide = any(i in search_key for i in ide_names)

    filtered = all_wins
    if not is_looking_for_ide:
        filtered = [w for w in all_wins if not any(i in w.pname.lower() for i in ("antigravity", "code.exe"))]

    for w in filtered:
        if w.title and w.title.lower().startswith(search_key):
            return w
    for w in filtered:
        if w.title and search_key in w.title.lower():
            return w
    for w in filtered:
        if search_key in w.pname.lower():
            return w

    return None


def focus_window(title: str, maximize: bool = False) -> str:
    """Bring a window with the given title substring or process name to the foreground."""
    ensure_desktop_attached()
    all_wins = _get_all_windows()
    win = _find_matching_window(title, all_wins)

    if not win:
        return f"No active window found matching '{title}'."

    if maximize:
        ctypes.windll.user32.ShowWindow(win.hwnd, 3)  # SW_MAXIMIZE
    else:
        ctypes.windll.user32.ShowWindow(win.hwnd, 9)  # SW_RESTORE
    success = bring_window_to_front(win.hwnd)
    if success:
        return f"Focused {win.title or win.pname}, sir."
    return f"Could not bring window to foreground: {win.title or win.pname}"


def list_windows() -> str:
    """Return a list of all visible window titles."""
    ensure_desktop_attached()
    titles = [w.title for w in _get_all_windows() if w.title.strip()]
    return "Open windows:\n" + "\n".join(f"  • {t}" for t in titles[:30])


def minimize_window(title: str = "") -> str:
    ensure_desktop_attached()
    global _last_minimized_title, _last_minimized_hwnd, _last_interacted_app
    search_key = _normalize_title_search(title) if title else ""
    user32 = ctypes.windll.user32
    import win32gui

    target_win: WindowItem | None = None
    if not search_key or search_key in ("it", "this", "window", "current"):
        fg_hwnd = user32.GetForegroundWindow()
        if fg_hwnd and user32.IsWindow(fg_hwnd):
            t = win32gui.GetWindowText(fg_hwnd).strip()
            target_win = WindowItem(fg_hwnd, t, 0, "")
    else:
        all_wins = _get_all_windows()
        target_win = _find_matching_window(title, all_wins)

    if not target_win:
        return f"No open window found matching '{title}'."

    _last_minimized_title = target_win.title
    _last_minimized_hwnd = target_win.hwnd
    _last_interacted_app = title or target_win.title
    try:
        user32.ShowWindow(target_win.hwnd, 6)  # SW_MINIMIZE
        return f"Minimized {target_win.title or _last_interacted_app}, sir."
    except Exception as e:
        logger.warning(f"Could not minimize window {target_win.hwnd}: {e}")
        return f"Could not minimize {target_win.title}."


def restore_window(title: str = "") -> str:
    """Restore a previously minimized window or specific app back to the screen."""
    ensure_desktop_attached()
    global _last_minimized_title, _last_minimized_hwnd, _last_interacted_app
    target = title.lower().strip() if title else ""
    user32 = ctypes.windll.user32

    # Contextual references: "again", "it", "that", "this", "window", empty string
    if not target or target in ("again", "it", "that", "this", "window", "app", "application", "previous", "last") or target.startswith("again"):
        if _last_minimized_hwnd and user32.IsWindow(_last_minimized_hwnd):
            user32.ShowWindow(_last_minimized_hwnd, 9)  # SW_RESTORE
            bring_window_to_front(_last_minimized_hwnd)
            name = _last_minimized_title or _last_interacted_app or "window"
            return f"Restored {name} to the screen, sir."
        elif _last_interacted_app and _last_interacted_app not in ("again", "it", "that", "this", "window"):
            return open_application(_last_interacted_app)

    # Search by title or app name in all windows (including iconic/minimized)
    search_key = _normalize_title_search(title)
    all_wins = _get_all_windows()
    matched = [w for w in all_wins if (w.title and search_key in w.title.lower()) or (search_key in w.pname)]
    if matched:
        target_win = matched[0]
        user32.ShowWindow(target_win.hwnd, 9)  # SW_RESTORE
        bring_window_to_front(target_win.hwnd)
        _last_interacted_app = target_win.title or target_win.pname
        return f"Restored {target_win.title or target_win.pname} to the screen, sir."

    return open_application(title)


def maximize_window(title: str) -> str:
    ensure_desktop_attached()
    all_wins = _get_all_windows()
    win = _find_matching_window(title, all_wins)
    if not win:
        return f"No open window found matching '{title}'."
    ctypes.windll.user32.ShowWindow(win.hwnd, 3)  # SW_MAXIMIZE
    bring_window_to_front(win.hwnd)
    return f"Maximized {win.title or win.pname}, sir."


def open_browser_tab(browser: str = "", url: str = "") -> str:
    """Open a new browser tab in Chrome, Edge, Brave, Firefox, or the currently focused browser."""
    ensure_desktop_attached()
    import time
    try:
        from control import keyboard_mouse
    except ImportError:
        from jarvis.control import keyboard_mouse

    target_app = browser.lower().strip() if browser else ""
    if target_app:
        res = focus_window(target_app, maximize=True)
        if "no active window" in res.lower() or "not found" in res.lower():
            open_application(target_app)
            time.sleep(1.0)
            focus_window(target_app, maximize=True)
        time.sleep(0.3)
    else:
        # Try finding any open browser window
        found = False
        all_wins = _get_all_windows()
        for w in all_wins:
            t = w.title.lower()
            p = w.pname.lower()
            if any(b in t or b in p for b in ["chrome", "edge", "brave", "firefox", "opera"]) and "spotify" not in t:
                ctypes.windll.user32.ShowWindow(w.hwnd, 3)  # SW_MAXIMIZE
                bring_window_to_front(w.hwnd)
                target_app = "browser"
                found = True
                break
        if not found:
            target_app = "browser"
            _focus_browser(maximize=True)

    time.sleep(0.3)
    keyboard_mouse.press_keys("ctrl+t")
    time.sleep(0.3)
    if url:
        keyboard_mouse.type_text(url)
        time.sleep(0.1)
        keyboard_mouse.press_single_key("enter")
        return f"Opened {url} in a new tab, sir."

    disp = target_app.title() if target_app else "Browser"
    return f"Opened a new tab in {disp}, sir."


def close_browser_tab() -> str:
    """Close the current browser tab (Ctrl+W)."""
    ensure_desktop_attached()
    try:
        from control import keyboard_mouse
    except ImportError:
        from jarvis.control import keyboard_mouse
    keyboard_mouse.press_keys("ctrl+w")
    return "Closed current browser tab, sir."


def switch_next_tab() -> str:
    """Switch to the next browser tab (Ctrl+Tab)."""
    ensure_desktop_attached()
    try:
        from control import keyboard_mouse
    except ImportError:
        from jarvis.control import keyboard_mouse
    keyboard_mouse.press_keys("ctrl+tab")
    return "Switched to next tab, sir."


def switch_prev_tab() -> str:
    """Switch to the previous browser tab (Ctrl+Shift+Tab)."""
    ensure_desktop_attached()
    try:
        from control import keyboard_mouse
    except ImportError:
        from jarvis.control import keyboard_mouse
    keyboard_mouse.press_keys("ctrl+shift+tab")
    return "Switched to previous tab, sir."


def reopen_closed_tab() -> str:
    """Reopen the previously closed tab (Ctrl+Shift+T)."""
    ensure_desktop_attached()
    try:
        from control import keyboard_mouse
    except ImportError:
        from jarvis.control import keyboard_mouse
    keyboard_mouse.press_keys("ctrl+shift+t")
    return "Reopened previously closed tab, sir."




