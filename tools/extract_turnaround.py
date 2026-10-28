import numpy as np
from PIL import Image, ImageFilter
from pathlib import Path

SRC_IMG = Path(r"C:\Users\alame\.gemini\antigravity-ide\brain\9c8acd29-534c-4785-8252-1cf94fd344bc\.user_uploaded\media_1788611926027.jpg")
DEST_DIR = Path(r"c:\Users\alame\Downloads\Desktop-Pet-main\Desktop-Pet-main\assets\dragon_sources")
DEST_DIR.mkdir(parents=True, exist_ok=True)

def remove_background(img_crop: Image.Image) -> Image.Image:
    arr = np.array(img_crop.convert("RGB"), dtype=np.float32)
    # Corners sample
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

    rgba = img_crop.convert("RGBA")
    rgba.putalpha(alpha_img)

    # Clean bottom text if any (remove text captions at the bottom)
    w, h = rgba.size
    # erase bottom 15% where labels like "FRONT VIEW." reside
    # But only if it's text (we can zero out alpha in bottom caption region or crop before)
    bbox = rgba.getbbox()
    if bbox:
        rgba = rgba.crop(bbox)
    return rgba

def extract_all_views():
    full = Image.open(SRC_IMG)
    w, h = full.size
    print(f"Full sheet size: {w}x{h}")
    mid_x = w // 2
    mid_y = h // 2

    # Front view: (0, 0, mid_x, int(mid_y * 0.90))
    # Back view: (mid_x, 0, w, int(mid_y * 0.90))
    # Left profile view: (0, mid_y, mid_x, int(h * 0.92))
    # Right profile view: (mid_x, mid_y, w, int(h * 0.92))

    crops = {
        "dragon_front.png": full.crop((0, 0, mid_x, int(mid_y * 0.90))),
        "dragon_back.png": full.crop((mid_x, 0, w, int(mid_y * 0.90))),
        "dragon_left.png": full.crop((0, mid_y, mid_x, int(h * 0.92))),
        "dragon_right.png": full.crop((mid_x, mid_y, w, int(h * 0.92))),
    }

    for name, crop_img in crops.items():
        cutout = remove_background(crop_img)
        # remove stray bottom text if bounding box caught text
        # If the height is tall and has text at bottom, crop text
        bw, bh = cutout.size
        # If small island of pixels at bottom, remove
        alpha_arr = np.array(cutout.split()[-1])
        # Find row sums
        row_sums = np.sum(alpha_arr > 50, axis=1)
        # scan from bottom up to find text gap
        for r in range(bh - 1, int(bh * 0.75), -1):
            if row_sums[r] == 0:
                cutout = cutout.crop((0, 0, bw, r))
                break
        
        bbox = cutout.getbbox()
        if bbox:
            cutout = cutout.crop(bbox)
            
        dest = DEST_DIR / name
        cutout.save(dest, "PNG")
        print(f"Extracted {name}: size {cutout.size}")

    # Also save dragon_front as main dragon_cutout.png for compatibility
    front_cutout = Image.open(DEST_DIR / "dragon_front.png")
    front_cutout.save(DEST_DIR / "dragon_cutout.png")

if __name__ == "__main__":
    extract_all_views()
