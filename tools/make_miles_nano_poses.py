import numpy as np
from PIL import Image
from pathlib import Path
import scipy.ndimage as ndi

BRAIN_DIR = Path(r"C:\Users\alame\.gemini\antigravity-ide\brain\39d2fa9e-9b0d-4564-9852-7c140f8d8f57")
OUT_DIR = Path(__file__).parent / "miles_sources"

def convert_spidey_to_miles(img_path: Path, out_path: Path):
    im = Image.open(img_path).convert("RGB")
    arr = np.array(im, dtype=np.float32)
    h, w, _ = arr.shape
    r, g, b = arr[:, :, 0], arr[:, :, 1], arr[:, :, 2]

    # Detect regions:
    # 1. Background (White)
    is_bg = (r > 235) & (g > 235) & (b > 235)
    
    # 2. Black outlines
    is_black_line = (r < 50) & (g < 50) & (b < 50)
    
    # 3. White eye lenses (inside head, white)
    is_eye = (r > 200) & (g > 200) & (b > 200) & ~is_bg
    
    # 4. Red suit areas (head, chest, gloves, boots)
    # Red in Spidey is: r > 160, g < 90, b < 90
    is_red = (r > 140) & (g < 110) & (b < 110) & (r - np.maximum(g, b) > 50)
    
    # 5. Blue suit areas (torso sides, legs)
    # Blue in Spidey is: b > 120, r < 100
    is_blue = (b > 110) & (r < 110) & (b - r > 30)

    # In Miles Morales suit:
    # - Suit base (both red and blue parts of body & head) becomes Jet Black / Charcoal Black (RGB ~ 20, 20, 28) with subtle shading
    # - The webbing lines and chest V-stripe / spider logo become Bright Crimson Red (RGB ~ 220, 25, 25)
    # - Eye outlines get red rim accent
    # - Finger tips stay red
    
    out_arr = arr.copy()
    
    # Convert blue areas to jet black suit
    out_arr[is_blue, 0] = arr[is_blue, 0] * 0.15 + 15
    out_arr[is_blue, 1] = arr[is_blue, 1] * 0.15 + 15
    out_arr[is_blue, 2] = arr[is_blue, 2] * 0.20 + 20

    # Convert red suit areas to stylish Miles black suit
    # Keep web lines (which were black) as bright red lines!
    # Where black lines overlap the red areas (mask webbing, chest webbing):
    dist_to_line = ndi.distance_transform_edt(~is_black_line)
    
    # Head & torso red base becomes black suit
    out_arr[is_red, 0] = arr[is_red, 0] * 0.12 + 18
    out_arr[is_red, 1] = arr[is_red, 1] * 0.12 + 18
    out_arr[is_red, 2] = arr[is_red, 2] * 0.15 + 24

    # Red V-chest accent and web lines on black mask
    # Lines inside the character head become glowing red webbing
    y_grid, x_grid = np.indices((h, w))
    is_head_web = is_black_line & (y_grid < h * 0.62) & (dist_to_line <= 1.5)
    
    # Red web pattern
    out_arr[is_head_web, 0] = 230
    out_arr[is_head_web, 1] = 28
    out_arr[is_head_web, 2] = 28

    # Outer head border stays bold black
    is_outer_border = ndi.binary_dilation(is_bg, iterations=3) & is_black_line
    out_arr[is_outer_border, 0] = 12
    out_arr[is_outer_border, 1] = 12
    out_arr[is_outer_border, 2] = 16

    # Red spider chest logo
    is_chest = (y_grid > h * 0.58) & (y_grid < h * 0.72) & (np.abs(x_grid - w * 0.5) < w * 0.12) & is_black_line
    out_arr[is_chest, 0] = 240
    out_arr[is_chest, 1] = 25
    out_arr[is_chest, 2] = 25

    # Red rim around eye lenses
    dist_to_eye = ndi.distance_transform_edt(~is_eye)
    is_eye_rim = (dist_to_eye <= 3.0) & (dist_to_eye > 0.5) & is_black_line
    out_arr[is_eye_rim, 0] = 235
    out_arr[is_eye_rim, 1] = 30
    out_arr[is_eye_rim, 2] = 30

    result = Image.fromarray(np.clip(out_arr, 0, 255).astype(np.uint8), "RGB")
    result.save(out_path)
    print(f"Generated Miles conversion saved to {out_path}")

idle_src = list(BRAIN_DIR.glob("spidey_idle_standing_*.jpg"))[-1]
walk_src = list(BRAIN_DIR.glob("spidey_walking_stride_*.jpg"))[-1]

convert_spidey_to_miles(idle_src, OUT_DIR / "miles_nano_idle_standing.png")
convert_spidey_to_miles(walk_src, OUT_DIR / "miles_nano_walking_stride.png")
