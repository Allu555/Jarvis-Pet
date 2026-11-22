import os
import sys
import ctypes
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

def find_best_pythonw() -> str:
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

def get_desktop_paths() -> list[Path]:
    paths = []
    user_profile = Path(os.environ.get("USERPROFILE", Path.home()))
    
    # 1. Standard Desktop
    std_desktop = user_profile / "Desktop"
    try:
        if std_desktop.exists():
            paths.append(std_desktop)
    except Exception:
        pass
        
    # 2. OneDrive Desktop
    onedrive_desktop = user_profile / "OneDrive" / "Desktop"
    try:
        if onedrive_desktop.exists() and onedrive_desktop not in paths:
            paths.append(onedrive_desktop)
    except Exception:
        pass
        
    return paths

def get_startup_folder() -> Path:
    appdata = os.environ.get("APPDATA")
    if appdata:
        p = Path(appdata) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup"
        if p.exists():
            return p
    return Path.home() / "AppData" / "Roaming" / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup"

def refresh_windows_icon_cache():
    """Notifies Windows Explorer Shell immediately to reload desktop and shortcut icons."""
    try:
        # SHCNE_ASSOCCHANGED = 0x08000000, SHCNF_IDLIST = 0x0000
        ctypes.windll.shell32.SHChangeNotify(0x08000000, 0x0000, None, None)
        os.system("ie4uinit.exe -show")
        print("Notified Windows Shell of icon changes.")
    except Exception as e:
        print(f"SHChangeNotify error: {e}")

def make_windows_shortcut(lnk_path: Path, target_exe: str, arguments: str, working_dir: str, icon_path: str, description: str):
    abs_icon = str(Path(icon_path).resolve())
    try:
        if lnk_path.exists():
            try:
                lnk_path.unlink()
            except Exception:
                pass
        import win32com.client
        shell = win32com.client.Dispatch("WScript.Shell")
        sc = shell.CreateShortcut(str(lnk_path))
        sc.TargetPath = target_exe
        sc.Arguments = arguments
        sc.WorkingDirectory = working_dir
        if Path(abs_icon).exists():
            sc.IconLocation = f"{abs_icon},0"
        sc.Description = description
        sc.WindowStyle = 1
        sc.Save()
        # Touch modification time
        try:
            os.utime(str(lnk_path), None)
        except Exception:
            pass
        print(f"Created/Updated shortcut via COM: {lnk_path}")
        return True
    except Exception as e:
        # Fallback to PowerShell
        ps_cmd = (
            f"$ws = New-Object -ComObject WScript.Shell; "
            f"$s = $ws.CreateShortcut('{lnk_path}'); "
            f"$s.TargetPath = '{target_exe}'; "
            f"$s.Arguments = '{arguments}'; "
            f"$s.WorkingDirectory = '{working_dir}'; "
            f"$s.IconLocation = '{abs_icon},0'; "
            f"$s.Description = '{description}'; "
            f"$s.Save()"
        )
        try:
            import subprocess
            subprocess.run(["powershell", "-NoProfile", "-Command", ps_cmd], check=True)
            if lnk_path.exists():
                print(f"Created/Updated shortcut via PowerShell: {lnk_path}")
                return True
        except Exception as e2:
            print(f"Failed to create shortcut: {e} / {e2}")
        return False

def install_all_shortcuts():
    pythonw_exe = find_best_pythonw()
    main_script = str(PROJECT_ROOT / "main.py")
    icon_file = str(PROJECT_ROOT / "assets" / "app_icon.ico")
    root_dir = str(PROJECT_ROOT)
    
    print(f"Using interpreter: {pythonw_exe}")
    print(f"Icon file:        {icon_file}")
    print(f"Project root:     {root_dir}")
    
    # 1. Desktop Shortcuts (Homescreen)
    desktop_dirs = get_desktop_paths()
    for d_dir in desktop_dirs:
        lnk = d_dir / "Desktop Pet.lnk"
        try:
            make_windows_shortcut(
                lnk_path=lnk,
                target_exe=pythonw_exe,
                arguments=f'"{main_script}"',
                working_dir=root_dir,
                icon_path=icon_file,
                description="Desktop Pet – Bloom Dynamic Notch Companion"
            )
        except Exception as e:
            print(f"Could not create shortcut in {d_dir}: {e}")

    # 2. Windows Startup Shortcut (Run on Boot)
    startup_dir = get_startup_folder()
    if startup_dir.exists():
        startup_lnk = startup_dir / "DesktopPet.lnk"
        try:
            make_windows_shortcut(
                lnk_path=startup_lnk,
                target_exe=pythonw_exe,
                arguments=f'"{main_script}"',
                working_dir=root_dir,
                icon_path=icon_file,
                description="Desktop Pet – Auto Start with Windows"
            )
        except Exception as e:
            print(f"Could not create startup shortcut: {e}")

    # 3. Refresh Windows Explorer Shell Icon Cache
    refresh_windows_icon_cache()
    print("All shortcuts installed successfully with crisp white icon!")

if __name__ == "__main__":
    install_all_shortcuts()
