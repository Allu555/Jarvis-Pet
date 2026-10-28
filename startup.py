import sys
from pathlib import Path

APP_NAME = "PixelPet"


def _get_launch_command() -> str:
    if getattr(sys, "frozen", False):
        return f'"{sys.executable}"'

    script = Path(__file__).parent / "main.py"

    # pythonw.exe sits next to python.exe and runs without a console window.
    # It also doesn't inherit the parent process group so it won't die when
    # a terminal (VS Code, cmd, PowerShell) that started it is closed.
    pythonw = Path(sys.executable).with_name("pythonw.exe")
    interpreter = pythonw if pythonw.exists() else Path(sys.executable)

    return f'"{interpreter}" "{script}"'


def enable_startup() -> bool:
    try:
        import winreg
        key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER, key_path,
            0, winreg.KEY_SET_VALUE
        ) as key:
            winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, _get_launch_command())
        return True
    except Exception:
        return False


def disable_startup() -> bool:
    try:
        import winreg
        key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER, key_path,
            0, winreg.KEY_SET_VALUE
        ) as key:
            winreg.DeleteValue(key, APP_NAME)
        return True
    except FileNotFoundError:
        return True   # already absent
    except Exception:
        return False


def is_startup_enabled() -> bool:
    try:
        import winreg
        key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER, key_path,
            0, winreg.KEY_READ
        ) as key:
            winreg.QueryValueEx(key, APP_NAME)
        return True
    except Exception:
        return False


def sync_startup(enabled: bool):
    if enabled:
        enable_startup()
    else:
        disable_startup()


if __name__ == "__main__":
    import main
    main.main()
