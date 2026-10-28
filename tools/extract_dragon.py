import numpy as np
from PIL import Image, ImageFilter
from pathlib import Path

SRC_IMG = Path(r"C:\Users\alame\.gemini\antigravity-ide\brain\9c8acd29-534c-4785-8252-1cf94fd344bc\.user_uploaded\media_1788611645478.jpg")
DEST_DIR = Path(r"c:\Users\alame\Downloads\Desktop-Pet-main\Desktop-Pet-main\assets\dragon_sources")
DEST_DIR.mkdir(parents=True, exist_ok=True)
OUT_FILE = DEST_DIR / "dragon_cutout.png"

def process_dragon_image():
    img = Image.open(SRC_IMG).convert("RGB")
    arr = np.array(img, dtype=np.float32)

    # Sample background color from corners
    corners = np.concatenate([
        arr[:30, :30].reshape(-1, 3),
        arr[:30, -30:].reshape(-1, 3),
        arr[-30:, :30].reshape(-1, 3),
        arr[-30:, -30:].reshape(-1, 3),
    ], axis=0)
    bg_mean = np.median(corners, axis=0) # [R, G, B] of paper bg

    # Calculate color difference from background
    # Background is warm pale cream (approx ~240, 235, 225)
    diff = np.sqrt(np.sum((arr - bg_mean) ** 2, axis=2))
    
    # Also check brightness and saturation
    # Dragon body has strong teal/cyan/grey/brown and darker tones
    # Paper bg is very light (brightness > 220) and low saturation
    max_c = np.max(arr, axis=2)
    min_c = np.min(arr, axis=2)
    sat = (max_c - min_c) / (max_c + 1e-5)
    
    # Create soft alpha mask based on color difference and brightness
    # Foreground pixels have diff > threshold
    thresh_low = 14.0
    thresh_high = 35.0
    alpha = np.clip((diff - thresh_low) / (thresh_high - thresh_low), 0.0, 1.0)
    
    # Also force bright pure background areas to zero
    bright_bg_mask = (arr[:, :, 0] > 225) & (arr[:, :, 1] > 220) & (arr[:, :, 2] > 210) & (sat < 0.12) & (diff < 28.0)
    alpha[bright_bg_mask] = 0.0

    # Clean edges
    alpha = (alpha * 255).astype(np.uint8)
    alpha_img = Image.fromarray(alpha, mode="L")
    # Slight smooth filter to eliminate any speckles
    alpha_img = alpha_img.filter(ImageFilter.MedianFilter(size=3))

    rgba = Image.open(SRC_IMG).convert("RGBA")
    rgba.putalpha(alpha_img)

    # Crop to content bounding box
    bbox = rgba.getbbox()
    if bbox:
        # add slight 5px margin
        x0 = max(0, bbox[0] - 5)
        y0 = max(0, bbox[1] - 5)
        x1 = min(rgba.width, bbox[2] + 5)
        y1 = min(rgba.height, bbox[3] + 5)
        rgba = rgba.crop((x0, y0, x1, y1))

    rgba.save(OUT_FILE, "PNG")
    print(f"Saved dragon cutout: {OUT_FILE} with size {rgba.size}")

if __name__ == "__main__":
    process_dragon_image()
