import numpy as np
from PIL import Image, ImageFilter
from pathlib import Path
import scipy.ndimage as ndi

SRC_IMG = Path(r"C:\Users\alame\.gemini\antigravity-ide\brain\9c8acd29-534c-4785-8252-1cf94fd344bc\.user_uploaded\media_1788613556685.jpg")
DEST_DIR = Path(r"c:\Users\alame\Downloads\Desktop-Pet-main\Desktop-Pet-main\assets\venom_sources")
DEST_DIR.mkdir(parents=True, exist_ok=True)
OUT_FILE = DEST_DIR / "venom_cutout.png"

def extract_venom():
    img = Image.open(SRC_IMG).convert("RGB")
    w, h = img.size
    print(f"Original image size: {w}x{h}")
    
    arr = np.array(img, dtype=np.float32)
    r, g, b = arr[:, :, 0], arr[:, :, 1], arr[:, :, 2]
    
    # 1. Background color detection
    bg_mean = np.array([237.0, 237.0, 237.0])
    color_dist = np.sqrt(np.sum((arr - bg_mean) ** 2, axis=2))
    is_bg_color = (color_dist < 32.0) | ((r > 225) & (g > 225) & (b > 225) & (np.maximum.reduce([r,g,b]) - np.minimum.reduce([r,g,b]) < 15))

    labeled_bg, num_bg = ndi.label(is_bg_color)

    # 2. Seeds for all background components:
    # Outer image borders
    border_mask = np.zeros((h, w), dtype=bool)
    border_mask[:5, :] = border_mask[-5:, :] = border_mask[:, :5] = border_mask[:, -5:] = True

    seeds = border_mask.copy()
    seeds[440, 320] = True  # Left arm cavity
    seeds[380, 484] = True  # Right arm cavity
    seeds[580, 380] = True  # Leg cavity

    bg_labels = np.unique(labeled_bg[seeds & is_bg_color])
    true_bg = np.isin(labeled_bg, bg_labels)

    # 3. Floor shadow under feet: y > 635 where r > 65
    y_idx, _ = np.indices((h, w))
    floor_shadow = (y_idx > 635) & (r > 65) & (g > 65) & (b > 65)

    total_bg = true_bg | floor_shadow
    total_bg = ndi.binary_dilation(total_bg, iterations=1)

    alpha = np.where(total_bg, 0, 255).astype(np.uint8)

    rgba = img.convert("RGBA")
    rgba.putalpha(Image.fromarray(alpha, mode="L"))
    bbox = rgba.getbbox()
    if bbox:
        rgba = rgba.crop(bbox)
        
    rgba.save(OUT_FILE, "PNG")
    print(f"Saved pristine Venom cutout to {OUT_FILE} with size {rgba.size}")

if __name__ == "__main__":
    extract_venom()
