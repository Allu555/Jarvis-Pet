import ctypes
import ctypes.wintypes
import json
import os
import threading
import time
from pathlib import Path
from typing import List, Optional

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

# Configure 64-bit argument and return types
user32.FindWindowW.argtypes = [ctypes.c_wchar_p, ctypes.c_wchar_p]
user32.FindWindowW.restype = ctypes.wintypes.HWND

user32.FindWindowExW.argtypes = [
    ctypes.wintypes.HWND,
    ctypes.wintypes.HWND,
    ctypes.c_wchar_p,
    ctypes.c_wchar_p,
]
user32.FindWindowExW.restype = ctypes.wintypes.HWND

user32.GetWindowRect.argtypes = [ctypes.wintypes.HWND, ctypes.POINTER(ctypes.wintypes.RECT)]
user32.GetWindowRect.restype = ctypes.c_bool


class ACCENT_POLICY(ctypes.Structure):
    _fields_ = [
        ("AccentState", ctypes.c_int),
        ("AccentFlags", ctypes.c_int),
        ("GradientColor", ctypes.c_int),
        ("AnimationId", ctypes.c_int),
    ]


class WINCOMPATTRDATA(ctypes.Structure):
    _fields_ = [
        ("Attribute", ctypes.c_int),
        ("Data", ctypes.c_void_p),
        ("SizeOfData", ctypes.c_size_t),
    ]


# Accent Policies
ACCENT_DISABLED = 0
ACCENT_ENABLE_GRADIENT = 1
ACCENT_ENABLE_TRANSPARENTGRADIENT = 2
ACCENT_ENABLE_BLURBEHIND = 3
ACCENT_ENABLE_ACRYLICBLURBEHIND = 4
ACCENT_ENABLE_HOSTBACKDROP = 5
ACCENT_ENABLE_TRANSPARENT = 6

WCA_ACCENT_POLICY = 19

SetWindowCompositionAttribute = getattr(user32, "SetWindowCompositionAttribute", None)
if SetWindowCompositionAttribute:
    SetWindowCompositionAttribute.restype = ctypes.c_bool
    SetWindowCompositionAttribute.argtypes = [
        ctypes.wintypes.HWND,
        ctypes.POINTER(WINCOMPATTRDATA),
    ]


class TaskbarStyle:
    CLEAR = "clear"           # 100% Transparent See-through Glass
    ACRYLIC = "acrylic"       # Frosted Fluent Acrylic Blur
    BLUR = "blur"             # Classic Aero Blur
    BLACK = "black"           # OLED Stealth Deep Black
    DEFAULT = "default"       # Windows Standard Taskbar

    ORDER = [CLEAR, ACRYLIC, BLUR, BLACK, DEFAULT]

    NAMES = {
        CLEAR: "Clear Glass (Transparent)",
        ACRYLIC: "Frosted Acrylic Blur",
        BLUR: "Aero Glass Blur",
        BLACK: "OLED Stealth Black",
        DEFAULT: "Windows Standard",
    }

    SHORT_NAMES = {
        CLEAR: "Clear Glass",
        ACRYLIC: "Acrylic Blur",
        BLUR: "Aero Blur",
        BLACK: "OLED Black",
        DEFAULT: "Default",
    }


class TaskbarService:
    """
    Singleton service managing Windows Taskbar styling, transparency,
    fluent acrylic blur, and persistence across sessions.
    """
    _instance: Optional['TaskbarService'] = None
    _lock = threading.Lock()

    @classmethod
    def get_instance(cls) -> 'TaskbarService':
        with cls._lock:
            if cls._instance is None:
                cls._instance = TaskbarService()
            return cls._instance

    def __init__(self):
        self._current_style: str = TaskbarStyle.CLEAR
        self._settings_path = Path(__file__).parent / "settings.json"
        self._running = False
        self._worker_thread: Optional[threading.Thread] = None
        self._load_settings()

    def _load_settings(self):
        try:
            if self._settings_path.exists():
                with open(self._settings_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    saved = data.get("taskbar_style", TaskbarStyle.CLEAR)
                    if saved in TaskbarStyle.ORDER:
                        self._current_style = saved
        except Exception:
            pass

    def _save_settings(self):
        try:
            data = {}
            if self._settings_path.exists():
                try:
                    with open(self._settings_path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                except Exception:
                    data = {}
            data["taskbar_style"] = self._current_style
            with open(self._settings_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4)
        except Exception:
            pass

    def get_all_taskbar_hwnds(self) -> List[int]:
        hwnds = []
        try:
            main_tb = user32.FindWindowW("Shell_TrayWnd", None)
            if main_tb:
                hwnds.append(main_tb)

            # Enumerate secondary taskbars across multi-monitor setups
            sec = None
            while True:
                sec = user32.FindWindowExW(None, sec, "Shell_SecondaryTrayWnd", None)
                if not sec:
                    break
                hwnds.append(sec)
        except Exception:
            pass
        return hwnds

    def set_style(self, style_name: str, save: bool = True) -> bool:
        if style_name not in TaskbarStyle.ORDER:
            style_name = TaskbarStyle.DEFAULT

        self._current_style = style_name
        if save:
            self._save_settings()

        success = self.apply_current_style()
        return success

    def cycle_style(self) -> str:
        try:
            curr_idx = TaskbarStyle.ORDER.index(self._current_style)
            next_idx = (curr_idx + 1) % len(TaskbarStyle.ORDER)
        except ValueError:
            next_idx = 0
        new_style = TaskbarStyle.ORDER[next_idx]
        self.set_style(new_style, save=True)
        return new_style

    @property
    def current_style(self) -> str:
        return self._current_style

    @property
    def display_name(self) -> str:
        return TaskbarStyle.NAMES.get(self._current_style, "Windows Standard")

    @property
    def short_display_name(self) -> str:
        return TaskbarStyle.SHORT_NAMES.get(self._current_style, "Default")

    def apply_current_style(self) -> bool:
        if not SetWindowCompositionAttribute:
            return False

        style = self._current_style
        policy = ACCENT_POLICY()

        if style == TaskbarStyle.CLEAR:
            # 100% Transparent See-through Glass
            policy.AccentState = ACCENT_ENABLE_TRANSPARENTGRADIENT
            policy.AccentFlags = 2
            policy.GradientColor = 0x00000000
            policy.AnimationId = 0
        elif style == TaskbarStyle.ACRYLIC:
            # Modern Frosted Acrylic Blur with deep translucent obsidian tint
            policy.AccentState = ACCENT_ENABLE_ACRYLICBLURBEHIND
            policy.AccentFlags = 2
            # ABGR format: Alpha 0xA0 (62% opacity) + Dark Slate 0x141418
            policy.GradientColor = 0xA0181414
            policy.AnimationId = 0
        elif style == TaskbarStyle.BLUR:
            # Classic Aero Glass Blur
            policy.AccentState = ACCENT_ENABLE_BLURBEHIND
            policy.AccentFlags = 2
            policy.GradientColor = 0x00000000
            policy.AnimationId = 0
        elif style == TaskbarStyle.BLACK:
            # OLED Stealth Deep Pitch Black
            policy.AccentState = ACCENT_ENABLE_GRADIENT
            policy.AccentFlags = 2
            policy.GradientColor = 0xFF08080A
            policy.AnimationId = 0
        else:
            # Windows Standard Default
            policy.AccentState = ACCENT_DISABLED
            policy.AccentFlags = 0
            policy.GradientColor = 0
            policy.AnimationId = 0

        data = WINCOMPATTRDATA()
        data.Attribute = WCA_ACCENT_POLICY
        data.Data = ctypes.cast(ctypes.pointer(policy), ctypes.c_void_p)
        data.SizeOfData = ctypes.sizeof(policy)

        taskbars = self.get_all_taskbar_hwnds()
        applied_any = False
        for tb in taskbars:
            try:
                res = SetWindowCompositionAttribute(tb, ctypes.byref(data))
                if res:
                    applied_any = True
            except Exception:
                pass

        # Try enabling system transparency in personal registry if clear/acrylic
        if style in (TaskbarStyle.CLEAR, TaskbarStyle.ACRYLIC):
            try:
                import winreg
                reg_path = r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize"
                with winreg.OpenKey(winreg.HKEY_CURRENT_USER, reg_path, 0, winreg.KEY_SET_VALUE) as key:
                    winreg.SetValueEx(key, "EnableTransparency", 0, winreg.REG_DWORD, 1)
            except Exception:
                pass

        return applied_any

    def start_watchdog(self):
        """
        Starts lightweight background watchdog that gently keeps the chosen
        taskbar style active if Windows Explorer resets or redraws its shell.
        """
        if self._running:
            return
        self._running = True
        self.apply_current_style()

        def _worker():
            while self._running:
                time.sleep(2.0)
                if self._running and self._current_style != TaskbarStyle.DEFAULT:
                    self.apply_current_style()

        self._worker_thread = threading.Thread(target=_worker, daemon=True, name="taskbar_watchdog")
        self._worker_thread.start()

    def stop_watchdog(self):
        self._running = False

    def restore_default(self):
        self._current_style = TaskbarStyle.DEFAULT
        self.apply_current_style()

