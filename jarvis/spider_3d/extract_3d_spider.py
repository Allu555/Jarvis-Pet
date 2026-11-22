"""
extract_3d_spider.py – Slices the 3D Spider Recon Sheet into transparent 3D pose assets.
"""

from pathlib import Path
import numpy as np
from PIL import Image

BASE_DIR = Path(__file__).resolve().parent
SHEET_PATH = BASE_DIR / "spider_3d_sheet.jpg"
OUT_DIR = BASE_DIR / "sprites"
OUT_DIR.mkdir(parents=True, exist_ok=True)

POSE_NAMES = [
    ["front_view", "side_view", "back_view", "top_view"],
    ["idle", "walk", "run", "turn"],
    ["scan", "shoot_web", "climb", "jump"]
]


def clean_checkerboard(img_arr: np.ndarray, is_scan_cell: bool = False) -> Image.Image:
    """Removes the gray/white checkerboard while preserving the spider, orange optics, and blue laser cone."""
    h, w, _ = img_arr.shape
    
    r = img_arr[:, :, 0].astype(float)
    g = img_arr[:, :, 1].astype(float)
    b = img_arr[:, :, 2].astype(float)
    
    # Calculate saturation / color difference from grayscale
    max_c = np.maximum(r, np.maximum(g, b))
    min_c = np.minimum(r, np.minimum(g, b))
    chroma = max_c - min_c
    brightness = (r + g + b) / 3.0
    
    # In checkerboard: brightness >= 195 and chroma < 14
    # The blue laser cone has chroma > 25 and high blue!
    is_checker = (brightness >= 195) & (chroma < 14)
    
    # Refined boundary anti-aliasing
    alpha = np.ones((h, w), dtype=np.uint8) * 255
    alpha[is_checker] = 0
    
    # Smooth edges where brightness is high but near the border
    edge = (brightness >= 180) & (brightness < 195) & (chroma < 12)
    alpha[edge] = np.clip((195 - brightness[edge]) * (255.0 / 15.0), 0, 255).astype(np.uint8)
    
    rgba = np.dstack([img_arr[:, :, :3], alpha])
    img = Image.fromarray(rgba, "RGBA")
    
    # Crop to bounding box of content
    bbox = img.getbbox()
    if bbox:
        img = img.crop(bbox)
    return img


def extract_all():
    if not SHEET_PATH.exists():
        print(f"Error: {SHEET_PATH} not found.")
        return

    sheet = Image.open(SHEET_PATH)
    arr = np.array(sheet)
    w, h = sheet.size
    
    col_w = w / 4.0
    row_h = h / 3.0
    
    print(f"Extracting 12 3D Spider poses from {w}x{h} sheet...")
    
    for row_idx, row in enumerate(POSE_NAMES):
        for col_idx, name in enumerate(row):
            x0 = int(col_idx * col_w)
            x1 = int((col_idx + 1) * col_w)
            y0 = int(row_idx * row_h)
            y1 = int((row_idx + 1) * row_h)
            
            cell = arr[y0:y1, x0:x1]
            # Exclude bottom ~38px where the black text label is located
            cell_content = cell[:int(row_h - 38), :]
            
            is_scan = (name == "scan")
            cleaned = clean_checkerboard(cell_content, is_scan_cell=is_scan)
            
            out_file = OUT_DIR / f"{name}.png"
            cleaned.save(out_file, "PNG")
            print(f"  [SAVED] {name}.png ({cleaned.width}x{cleaned.height})")

    print("\nExtraction finished successfully!")


if __name__ == "__main__":
    extract_all()

