"""
tools/wallpaper.py
Handles setting the Windows desktop background wallpaper with image format conversion,
instant desktop refresh, and interactive file selection dialog.
"""

import os
import sys
import ctypes
from pathlib import Path
from typing import Optional


def set_desktop_wallpaper(image_path: str) -> bool:
    """
    Sets the Windows desktop background wallpaper with immediate system refresh.
    Supports PNG, JPG, JPEG, BMP, WEBP, and other formats.
    Auto-converts WEBP/non-standard formats into an optimized PNG cache if needed.
    """
    try:
        p = Path(image_path).resolve()
        if not p.exists() or not p.is_file():
            print(f"[!] Wallpaper file does not exist: {p}")
            return False

        # Windows SystemParametersInfo natively prefers standard formats (.png, .jpg, .bmp)
        valid_path = str(p)
        ext = p.suffix.lower()
        if ext not in [".jpg", ".jpeg", ".bmp", ".png"]:
            try:
                from PIL import Image
                cache_dir = Path(os.environ.get("APPDATA", Path.home())) / "PixelPet" / "wallpapers"
                cache_dir.mkdir(parents=True, exist_ok=True)
                cache_file = cache_dir / f"wallpaper_{int(p.stat().st_mtime)}.png"
                im = Image.open(p)
                im.convert("RGB").save(str(cache_file), "PNG")
                valid_path = str(cache_file)
            except Exception as conv_err:
                print(f"Warning converting image: {conv_err}")

        # SystemParametersInfoW: SPI_SETDESKWALLPAPER = 20
        # Flags: SPIF_UPDATEINIFILE (0x01) | SPIF_SENDCHANGE (0x02)
        SPI_SETDESKWALLPAPER = 20
        SPIF_UPDATEINIFILE = 0x01
        SPIF_SENDCHANGE = 0x02

        result = ctypes.windll.user32.SystemParametersInfoW(
            SPI_SETDESKWALLPAPER,
            0,
            valid_path,
            SPIF_UPDATEINIFILE | SPIF_SENDCHANGE
        )
        
        if result:
            print(f"[+] Successfully applied desktop wallpaper: {valid_path}")
            return True
        else:
            print("[!] SystemParametersInfoW returned false")
            return False
            
    except Exception as e:
        print(f"[!] Failed to set desktop wallpaper: {e}")
        return False


def pick_and_set_wallpaper(parent=None) -> Optional[str]:
    """
    Opens native Windows file picker dialog to let user upload / select any image file,
    and immediately sets it as the desktop wallpaper.
    """
    try:
        from PySide6.QtWidgets import QFileDialog
        file_path, _ = QFileDialog.getOpenFileName(
            parent,
            "Select Desktop Wallpaper Image",
            os.path.expanduser("~/Pictures"),
            "Image Files (*.png *.jpg *.jpeg *.webp *.bmp *.gif);;All Files (*.*)"
        )
        if file_path and os.path.exists(file_path):
            success = set_desktop_wallpaper(file_path)
            if success:
                return file_path
        return None
    except Exception as e:
        print(f"[!] Error in pick_and_set_wallpaper: {e}")
        return None

