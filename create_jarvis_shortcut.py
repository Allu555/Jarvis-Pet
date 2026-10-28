"""
create_jarvis_shortcut.py
Creates a silent Desktop shortcut for JARVIS with custom Arc Reactor icon.
Directly targets pythonw.exe so NO CMD / terminal window opens.
"""

import os
import sys
import shutil
from pathlib import Path


def ensure_jarvis_icon() -> Path:
    """Locate high-resolution multi-size jarvis.ico."""
    base_dir = Path(__file__).resolve().parent
    icon_path = base_dir / "jarvis" / "jarvis.ico"
    return icon_path


def find_pythonw() -> Path:
    """Find the best pythonw.exe (windowless Python launcher)."""
    # 1. Check Python 3.11 in Local AppData
    local_appdata = os.environ.get("LOCALAPPDATA", "")
    if local_appdata:
        p311 = Path(local_appdata) / "Programs" / "Python" / "Python311" / "pythonw.exe"
        if p311.exists():
            return p311

    # 2. Check sibling to current interpreter
    sibling = Path(sys.executable).with_name("pythonw.exe")
    if sibling.exists():
        return sibling

    # 3. Check system PATH
    which_pythonw = shutil.which("pythonw")
    if which_pythonw:
        return Path(which_pythonw)

    return Path(sys.executable)


def get_desktop_directories() -> list[Path]:
    """Retrieve all active Windows Desktop directories (OneDrive and local)."""
    desktops = []

    # 1. Windows Shell Special Folder for Desktop
    try:
        import win32com.client
        shell = win32com.client.Dispatch("WScript.Shell")
        special_desktop = shell.SpecialFolders("Desktop")
        if special_desktop and Path(special_desktop).exists():
            desktops.append(Path(special_desktop))
    except Exception:
        pass

    # 2. Check user profile paths
    user_profile = Path(os.environ.get("USERPROFILE", "C:/Users/alame"))
    onedrive_desktop = user_profile / "OneDrive" / "Desktop"
    local_desktop = user_profile / "Desktop"

    if onedrive_desktop.exists() and onedrive_desktop not in desktops:
        desktops.append(onedrive_desktop)
    if local_desktop.exists() and local_desktop not in desktops:
        desktops.append(local_desktop)

    return desktops


def create_shortcut():
    base_dir = Path(__file__).resolve().parent
    working_dir = base_dir / "jarvis"
    target_script = working_dir / "main.py"
    icon_path = ensure_jarvis_icon()
    pythonw_exe = find_pythonw()

    print(f"Target interpreter: {pythonw_exe}")
    print(f"Working directory:  {working_dir}")
    print(f"Icon location:      {icon_path}")

    desktop_dirs = get_desktop_directories()
    if not desktop_dirs:
        print("[!] No desktop directory found.")
        return False

    try:
        import win32com.client
        shell = win32com.client.Dispatch("WScript.Shell")

        for desktop in desktop_dirs:
            lnk_path = desktop / "JARVIS.lnk"
            shortcut = shell.CreateShortCut(str(lnk_path))
            # Launch pythonw directly - this ensures NO CMD window ever appears!
            shortcut.TargetPath = str(pythonw_exe)
            shortcut.Arguments = f'"{target_script}"'
            shortcut.WorkingDirectory = str(working_dir)
            if icon_path.exists():
                shortcut.IconLocation = f"{icon_path},0"
            shortcut.Description = "Start JARVIS AI Voice & Desktop Assistant"
            shortcut.WindowStyle = 1
            shortcut.Save()
            print(f"[+] Created silent desktop shortcut at: {lnk_path}")

        print("\nJARVIS Desktop Icon updated successfully (CMD window disabled)!")
        return True

    except Exception as e:
        print(f"[!] Failed via COM: {e}")
        # Fallback to PowerShell
        for desktop in desktop_dirs:
            lnk_path = desktop / "JARVIS.lnk"
            ps_cmd = (
                f'$ws = New-Object -ComObject WScript.Shell; '
                f'$s = $ws.CreateShortcut("{lnk_path}"); '
                f'$s.TargetPath = "{pythonw_exe}"; '
                f'$s.Arguments = "`"{target_script}`""; '
                f'$s.WorkingDirectory = "{working_dir}"; '
                f'$s.IconLocation = "{icon_path},0"; '
                f'$s.Description = "Start JARVIS AI Voice & Desktop Assistant"; '
                f'$s.Save()'
            )
            os.system(f'powershell -NoProfile -Command "{ps_cmd}"')
            if lnk_path.exists():
                print(f"[+] Created silent desktop shortcut at: {lnk_path}")
        return True


if __name__ == "__main__":
    create_shortcut()
