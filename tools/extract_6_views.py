import numpy as np
from PIL import Image, ImageFilter
from pathlib import Path

SRC_IMG = Path(r"C:\Users\alame\.gemini\antigravity-ide\brain\9c8acd29-534c-4785-8252-1cf94fd344bc\.user_uploaded\media_1788612091275.jpg")
DEST_DIR = Path(r"c:\Users\alame\Downloads\Desktop-Pet-main\Desktop-Pet-main\assets\dragon_sources")
DEST_DIR.mkdir(parents=True, exist_ok=True)

def clean_cutout(crop_img: Image.Image) -> Image.Image:
    arr = np.array(crop_img.convert("RGB"), dtype=np.float32)
    # Sample corners
    corners = np.concatenate([
        arr[:15, :15].reshape(-1, 3),
        arr[:15, -15:].reshape(-1, 3),
        arr[-15:, :15].reshape(-1, 3),
        arr[-15:, -15:].reshape(-1, 3),
    ], axis=0)
    bg_mean = np.median(corners, axis=0)
    diff = np.sqrt(np.sum((arr - bg_mean) ** 2, axis=2))
    
    max_c = np.max(arr, axis=2)
    min_c = np.min(arr, axis=2)
    sat = (max_c - min_c) / (max_c + 1e-5)

    thresh_low = 13.0
    thresh_high = 32.0
    alpha = np.clip((diff - thresh_low) / (thresh_high - thresh_low), 0.0, 1.0)

    # Force background cream parchment to 0
    bright_bg_mask = (arr[:, :, 0] > 225) & (arr[:, :, 1] > 220) & (arr[:, :, 2] > 210) & (sat < 0.12) & (diff < 26.0)
    alpha[bright_bg_mask] = 0.0

    alpha = (alpha * 255).astype(np.uint8)
    alpha_img = Image.fromarray(alpha, mode="L").filter(ImageFilter.MedianFilter(size=3))

    rgba = crop_img.convert("RGBA")
    rgba.putalpha(alpha_img)

    # Remove any text caption at bottom (or top)
    bw, bh = rgba.size
    alpha_arr = np.array(rgba.split()[-1])
    row_sums = np.sum(alpha_arr > 50, axis=1)

    # Scan from bottom to remove bottom caption text
    for r in range(bh - 1, int(bh * 0.70), -1):
        if row_sums[r] == 0:
            rgba = rgba.crop((0, 0, bw, r))
            break
            
    # Scan from top to remove top caption text
    alpha_arr = np.array(rgba.split()[-1])
    row_sums = np.sum(alpha_arr > 50, axis=1)
    for r in range(0, int(rgba.height * 0.30)):
        if row_sums[r] == 0 and np.sum(row_sums[:r]) > 0:
            rgba = rgba.crop((0, r, rgba.width, rgba.height))
            break

    bbox = rgba.getbbox()
    if bbox:
        rgba = rgba.crop(bbox)
    return rgba


def extract_6_views():
    full = Image.open(SRC_IMG)
    w, h = full.size
    print(f"6-View Sheet size: {w}x{h}")
    
    col_w = w / 3.0
    row_h = h / 2.0

    # Grid 3 cols x 2 rows
    boxes = {
        "fly_dorsal.png": (0, 0, int(col_w * 1.02), int(row_h * 0.96)),
        "fly_frontal.png": (int(col_w * 0.98), 0, int(col_w * 2.02), int(row_h * 0.96)),
        "fly_bank_right.png": (int(col_w * 1.98), 0, w, int(row_h * 0.96)),
        
        "fly_profile_left.png": (0, int(row_h * 0.98), int(col_w * 1.02), h),
        "fly_ventral.png": (int(col_w * 0.98), int(row_h * 0.98), int(col_w * 2.02), h),
        "fly_profile_right.png": (int(col_w * 1.98), int(row_h * 0.98), w, h),
    }

    for name, box in boxes.items():
        crop_img = full.crop(box)
        cutout = clean_cutout(crop_img)
        dest = DEST_DIR / name
        cutout.save(dest, "PNG")
        print(f"Extracted {name}: size {cutout.size}")

if __name__ == "__main__":
    extract_6_views()
