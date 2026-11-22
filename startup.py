import os
import sys
from pathlib import Path

APP_NAME = "PixelPet"


def _get_project_root() -> Path:
    return Path(__file__).parent.resolve()


def _find_best_interpreter() -> str:
    """Finds the windowless pythonw.exe interpreter that contains PySide6."""
    local_app_data = os.environ.get("LOCALAPPDATA", "")
    candidates = [
        Path(local_app_data) / "Programs" / "Python" / "Python311" / "pythonw.exe",
        Path(local_app_data) / "Programs" / "Python" / "Python312" / "pythonw.exe",
        Path(local_app_data) / "Programs" / "Python" / "Python310" / "pythonw.exe",
        Path(sys.executable).with_name("pythonw.exe"),
        Path(sys.executable),
    ]
    for cand in candidates:
        if cand.exists():
            return str(cand.resolve())
    return "pythonw.exe"


def _get_startup_folder() -> Path:
    """Gets the Windows Startup folder path for the current user."""
    appdata = os.environ.get("APPDATA")
    if appdata:
        p = Path(appdata) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup"
        if p.exists():
            return p
    return Path.home() / "AppData" / "Roaming" / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup"


def _get_launch_command() -> str:
    if getattr(sys, "frozen", False):
        return f'"{sys.executable}"'

    script = _get_project_root() / "main.py"
    interpreter = _find_best_interpreter()
    return f'"{interpreter}" "{script}"'


def _write_vbs_startup_launcher() -> bool:
    """
    Creates a zero-overhead, completely hidden VBScript launcher in the Windows Startup folder.
    This guarantees launching on Windows boot with zero console window flash and 0.0% CPU overhead.
    """
    try:
        startup_dir = _get_startup_folder()
        startup_dir.mkdir(parents=True, exist_ok=True)
        vbs_path = startup_dir / f"{APP_NAME}.vbs"

        root_dir = str(_get_project_root())
        interpreter = _find_best_interpreter()
        script_path = str(_get_project_root() / "main.py")

        vbs_content = (
            'Set WshShell = CreateObject("WScript.Shell")\n'
            f'strDir = "{root_dir}"\n'
            f'strApp = "{interpreter}"\n'
            f'strScript = "{script_path}"\n'
            'WshShell.CurrentDirectory = strDir\n'
            'WshShell.Run """" & strApp & """ """ & strScript & """", 0, False\n'
        )
        vbs_path.write_text(vbs_content, encoding="utf-8")
        return True
    except Exception as e:
        print(f"Warning: Failed to write startup VBS launcher: {e}")
        return False


def _remove_vbs_startup_launcher() -> bool:
    try:
        vbs_path = _get_startup_folder() / f"{APP_NAME}.vbs"
        if vbs_path.exists():
            vbs_path.unlink()
        return True
    except Exception:
        return False


def enable_startup() -> bool:
    """Enables auto-start with Windows via both the Startup folder and the Windows Registry."""
    vbs_ok = _write_vbs_startup_launcher()

    reg_ok = False
    try:
        import winreg
        key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER, key_path,
            0, winreg.KEY_SET_VALUE
        ) as key:
            winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, _get_launch_command())
        reg_ok = True
    except Exception:
        pass

    return vbs_ok or reg_ok


def disable_startup() -> bool:
    """Disables auto-start with Windows."""
    _remove_vbs_startup_launcher()
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
        return True
    except Exception:
        return False


def is_startup_enabled() -> bool:
    """Checks if startup is enabled in either the Startup folder or Registry."""
    vbs_path = _get_startup_folder() / f"{APP_NAME}.vbs"
    if vbs_path.exists():
        return True

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
    success = enable_startup()
    print(f"Startup enabled successfully: {success}")
    print(f"Startup file: {_get_startup_folder() / f'{APP_NAME}.vbs'}")
