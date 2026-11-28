import sys
import os
from pathlib import Path

# Ensure the project root is on sys.path when launched as a script
PROJECT_ROOT = Path(__file__).parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont, QIcon, QPixmapCache
import gc
import ctypes

from settings import Settings
from animation import PET_TYPES
import startup


def ensure_sprites():
    sprite_dir = PROJECT_ROOT / "assets" / "sprites"
    sprite_dir.mkdir(parents=True, exist_ok=True)
    if not any(sprite_dir.glob("*.png")):
        print("Generating pixel sprites…")
        sys.path.insert(0, str(PROJECT_ROOT / "tools"))
        try:
            import generate_sprites
            generate_sprites.generate_all()
        except Exception as e:
            print(f"Warning: sprite generation failed – {e}")
            print("App will run with placeholder (transparent) sprites.")


_single_instance_mutex = None


def _acquire_single_instance_mutex(mutex_name="Global\\PixelPetDesktop_SingleInstanceMutex"):
    """
    Guarantees only one instance of Desktop Pet & Origin Island runs at a time.
    Prevents duplicate instances and avoids wasting CPU/RAM if launched repeatedly.
    """
    global _single_instance_mutex
    try:
        import ctypes
        from ctypes import wintypes
        kernel32 = ctypes.windll.kernel32
        kernel32.CreateMutexW.argtypes = [wintypes.LPVOID, wintypes.BOOL, wintypes.LPCWSTR]
        kernel32.CreateMutexW.restype = wintypes.HANDLE
        
        handle = kernel32.CreateMutexW(None, True, mutex_name)
        if kernel32.GetLastError() == 183:  # ERROR_ALREADY_EXISTS
            return None
        _single_instance_mutex = handle
        return handle
    except Exception:
        return True


def main():
    # 0. Single instance guard (don't waste resources with duplicate processes)
    if _acquire_single_instance_mutex() is None:
        print("Desktop Pet & Origin Island is already running. Exiting duplicate instance to save resources.")
        sys.exit(0)

    # Ensure window is attached to user's interactive 'Default' desktop
    if sys.platform == "win32":
        try:
            import ctypes
            user32 = ctypes.windll.user32
            h_default_desk = user32.OpenDesktopW("Default", 0, False, 0x01FF)
            if h_default_desk:
                user32.SetThreadDesktop(h_default_desk)
        except Exception:
            pass

    # High-DPI support & WebEngine initialization BEFORE QApplication
    os.environ.setdefault("QT_ENABLE_HIGHDPI_SCALING", "1")
    try:
        from PySide6.QtCore import Qt
        QApplication.setAttribute(Qt.ApplicationAttribute.AA_ShareOpenGLContexts, True)
        import PySide6.QtWebEngineWidgets  # noqa: F401
    except Exception:
        pass

    app = QApplication(sys.argv)
    QPixmapCache.setCacheLimit(2048)   # Cap Qt internal image cache to 2MB to prevent RAM bloat
    app.setApplicationName("PixelPet")
    app.setOrganizationName("PixelPet")
    app.setQuitOnLastWindowClosed(False)   # keep alive via tray / multi-pets

    app_ico = PROJECT_ROOT / "assets" / "app_icon.ico"
    if not app_ico.exists():
        app_ico = PROJECT_ROOT / "assets" / "desktop_pet.ico"
    if app_ico.exists():
        app.setWindowIcon(QIcon(str(app_ico)))

    # Pixel-perfect rendering: disable font antialiasing effects
    font = QFont()
    font.setStyleStrategy(QFont.StyleStrategy.NoAntialias)
    app.setFont(font)

    ensure_sprites()

    settings = Settings()

    # Check for Island standalone mode
    if len(sys.argv) > 1 and sys.argv[1].lower() == "island":
        from origin_island import OriginIsland
        island = OriginIsland(settings=settings)
        island.show()
        sys.exit(app.exec())

    startup.sync_startup(settings.start_with_windows)

    from lion import LionWindow
    from pet_manager import PetManager

    manager = PetManager.instance()

    # Parse command line pets list
    cli_pets = []
    for arg in sys.argv[1:]:
        if arg.startswith("--pets="):
            parts = arg.split("=", 1)[1].split(",")
            cli_pets.extend([p.strip() for p in parts if p.strip() in PET_TYPES])
        elif arg in PET_TYPES:
            cli_pets.append(arg)

    if cli_pets:
        # Spawn first pet as primary
        settings.selected_pet = cli_pets[0]
        settings.save()
        primary_window = LionWindow(settings, is_secondary=False)
        
        # Spawn additional requested pets
        for i, pet_key in enumerate(cli_pets[1:], start=1):
            manager.spawn_pet(pet_key, near_x=200 + i * 220, near_y=500)
    else:
        # Single primary pet from saved settings
        primary_window = LionWindow(settings, is_secondary=False)

    def _trim_working_set():
        gc.collect()
        if sys.platform == "win32":
            try:
                pid = os.getpid()
                h = ctypes.windll.kernel32.OpenProcess(0x1F0FFF, False, pid)
                if h:
                    ctypes.windll.psapi.EmptyWorkingSet(h)
                    ctypes.windll.kernel32.CloseHandle(h)
            except Exception:
                pass

    # Automatic memory optimization: trim 3s after startup, and every 60s during idle
    QTimer.singleShot(3000, _trim_working_set)
    _trim_timer = QTimer(app)
    _trim_timer.setInterval(60000)
    _trim_timer.timeout.connect(_trim_working_set)
    _trim_timer.start()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
