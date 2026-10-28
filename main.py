import sys
import os
from pathlib import Path

# Ensure the project root is on sys.path when launched as a script
PROJECT_ROOT = Path(__file__).parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

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


def main():
    # High-DPI support
    os.environ.setdefault("QT_ENABLE_HIGHDPI_SCALING", "1")

    app = QApplication(sys.argv)
    app.setApplicationName("PixelPet")
    app.setOrganizationName("PixelPet")
    app.setQuitOnLastWindowClosed(False)   # keep alive via tray / multi-pets

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

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
