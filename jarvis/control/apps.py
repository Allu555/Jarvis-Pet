"""
control/apps.py – Launch, focus, and close applications on Windows.
OS-specific code is isolated here.
"""

import ctypes
import glob
import logging
import os
import subprocess
import time
import winreg
from pathlib import Path

import psutil         # type: ignore
import pygetwindow as gw  # type: ignore

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
            r = subprocess.run(["where", candidate], capture_output=True, text=True, timeout=2)
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
                ["where", lookup], capture_output=True, text=True, timeout=2
            )
            if result.returncode == 0:
                found = result.stdout.strip().splitlines()[0]
                if Path(found).exists():
                    return found
        except Exception:
            pass

    return None


def open_application(name: str) -> str:
    """
    Launch or focus an application, folder, or service by friendly name.
    """
    ensure_desktop_attached()
    key = name.lower().strip()

    # First check if a matching window is ALREADY running and can simply be focused
    try:
        windows = [w for w in gw.getAllWindows() if w.title.strip()]
        for w in windows:
            if key in w.title.lower():
                bring_window_to_front(w._hWnd)
                logger.info(f"App '{name}' was already open; focused window: {w.title}")
                return f"Brought {name.title()} to the foreground for you, sir."
    except Exception:
        pass

    path = _resolve_path(name)
    if not path:
        logger.warning(f"Could not resolve path for '{name}'")
        return f"I couldn't locate an application called '{name}'. Please verify the name."

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
            return f"Opened {name.title()} for you, sir."

        # Folder
        elif Path(path).is_dir():
            os.startfile(path)
            logger.info(f"Opened folder: {path}")
            time.sleep(0.8)
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
            subprocess.Popen(
                [path],
                creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP,
            )
            logger.info(f"Launched binary: {path}")
            time.sleep(1.2)
            focus_window(name)
            return f"Opened {name.title()} for you, sir."

    except Exception as e:
        logger.error(f"Failed to open {name}: {e}")
        return f"Failed to open {name}: {e}"


def _focus_browser() -> None:
    """Bring the active browser window to the front."""
    ensure_desktop_attached()
    browser_names = ["brave", "edge", "chrome", "firefox", "opera"]
    try:
        windows = [w for w in gw.getAllWindows() if w.title.strip()]
        for b in browser_names:
            for w in windows:
                if b in w.title.lower():
                    bring_window_to_front(w._hWnd)
                    return
    except Exception:
        pass


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


def focus_window(title: str) -> str:
    """Bring a window with the given title substring or process name to the foreground."""
    ensure_desktop_attached()
    search_key = _normalize_title_search(title)
    wins = gw.getWindowsWithTitle(search_key)
    if not wins:
        all_wins = [w for w in gw.getAllWindows() if w.title.strip()]
        wins = [w for w in all_wins if search_key in w.title.lower()]

    # If title search fails, search by process executable or command line (e.g. Spotify PWA, media apps)
    if not wins:
        user32 = ctypes.windll.user32
        all_wins = [w for w in gw.getAllWindows() if w.title.strip()]
        for w in all_wins:
            pid = ctypes.c_ulong()
            user32.GetWindowThreadProcessId(w._hWnd, ctypes.byref(pid))
            try:
                proc = psutil.Process(pid.value)
                pname = proc.name().lower()
                cmd = " ".join(proc.cmdline()).lower()
                if search_key in ("spotify", "music", "song") and (
                    "spotify" in pname or "spotify" in cmd or "pjibgclleladliembfgfagdaldikeohf" in cmd
                ):
                    wins.append(w)
                    break
                elif search_key in pname or search_key in cmd:
                    wins.append(w)
                    break
            except Exception:
                pass

    if not wins:
        return f"No active window found matching '{title}'."

    win = wins[0]
    success = bring_window_to_front(win._hWnd)
    if success:
        return f"Focused {win.title}, sir."
    return f"Could not bring window to foreground: {win.title}"



def list_windows() -> str:
    """Return a list of all visible window titles."""
    ensure_desktop_attached()
    titles = [w.title for w in gw.getAllWindows() if w.title.strip()]
    return "Open windows:\n" + "\n".join(f"  • {t}" for t in titles[:30])


def minimize_window(title: str) -> str:
    ensure_desktop_attached()
    search_key = _normalize_title_search(title)
    wins = gw.getWindowsWithTitle(search_key)
    if not wins:
        all_wins = [w for w in gw.getAllWindows() if w.title.strip()]
        wins = [w for w in all_wins if search_key in w.title.lower()]
    if not wins:
        return f"No open window found matching '{title}'."
    try:
        ctypes.windll.user32.ShowWindow(wins[0]._hWnd, 6)  # SW_MINIMIZE
        return f"Minimized {wins[0].title}, sir."
    except Exception:
        wins[0].minimize()
        return f"Minimized {wins[0].title}, sir."


def maximize_window(title: str) -> str:
    ensure_desktop_attached()
    search_key = _normalize_title_search(title)
    wins = gw.getWindowsWithTitle(search_key)
    if not wins:
        all_wins = [w for w in gw.getAllWindows() if w.title.strip()]
        wins = [w for w in all_wins if search_key in w.title.lower()]
    if not wins:
        return f"No open window found matching '{title}'."
    try:
        bring_window_to_front(wins[0]._hWnd)
        ctypes.windll.user32.ShowWindow(wins[0]._hWnd, 3)  # SW_MAXIMIZE
        return f"Maximized {wins[0].title}, sir."
    except Exception:
        wins[0].maximize()
        return f"Maximized {wins[0].title}, sir."



