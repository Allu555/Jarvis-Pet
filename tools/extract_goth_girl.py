import numpy as np
from PIL import Image, ImageFilter
from pathlib import Path
import scipy.ndimage as ndi

SRC_DIR = Path(r"C:\Users\alame\.gemini\antigravity-ide\brain\9c8acd29-534c-4785-8252-1cf94fd344bc")
DEST_DIR = Path(r"c:\Users\alame\Downloads\Desktop-Pet-main\Desktop-Pet-main\assets\goth_girl_sources")
DEST_DIR.mkdir(parents=True, exist_ok=True)

FULLBODY_IMG = SRC_DIR / "goth_girl_fullbody_1788615950540.jpg"
WALK_SHEET = SRC_DIR / "goth_girl_walk_sheet_1788615971046.jpg"
ACTIONS_SHEET = SRC_DIR / "goth_girl_actions_sheet_1788615993739.jpg"

def clean_white_background(img: Image.Image, tolerance: float = 35.0) -> Image.Image:
    """Removes clean white/off-white background with border seed flood fill and alpha matting."""
    arr = np.array(img.convert("RGB"), dtype=np.float32)
    h, w, _ = arr.shape
    r, g, b = arr[:, :, 0], arr[:, :, 1], arr[:, :, 2]
    
    # White background detection (high RGB, low color saturation)
    diff = np.sqrt((255 - r)**2 + (255 - g)**2 + (255 - b)**2)
    is_white_bg = (diff < tolerance) | ((r > 235) & (g > 235) & (b > 235) & (np.maximum.reduce([r,g,b]) - np.minimum.reduce([r,g,b]) < 18))
    
    labeled_bg, num_bg = ndi.label(is_white_bg)
    border_mask = np.zeros((h, w), dtype=bool)
    border_mask[:5, :] = border_mask[-5:, :] = border_mask[:, :5] = border_mask[:, -5:] = True
    
    # Also seed enclosed cavities like between legs
    border_labels = np.unique(labeled_bg[border_mask & is_white_bg])
    outer_bg = np.isin(labeled_bg, border_labels)
    
    # In lower body (y > 0.6*h), any white background is between-leg cavity or floor
    cavity_bg = is_white_bg & (np.indices((h, w))[0] > h * 0.60)
    
    total_bg = outer_bg | cavity_bg
    total_bg = ndi.binary_dilation(total_bg, iterations=1)
    
    alpha = np.where(total_bg, 0, 255).astype(np.uint8)
    alpha_img = Image.fromarray(alpha, mode="L").filter(ImageFilter.MedianFilter(size=3))
    
    rgba = img.convert("RGBA")
    rgba.putalpha(alpha_img)
    return rgba

def extract_goth_girl():
    # 1. Fullbody Cutout
    fb = Image.open(FULLBODY_IMG)
    fb_clean = clean_white_background(fb)
    bbox = fb_clean.getbbox()
    if bbox:
        fb_clean = fb_clean.crop(bbox)
    fb_clean.save(DEST_DIR / "goth_girl_cutout.png", "PNG")
    print(f"Extracted goth_girl_cutout.png: size {fb_clean.size}")

    # 2. Extract 6 Walk Frames from Walk Sheet
    ws = Image.open(WALK_SHEET)
    ws_clean = clean_white_background(ws, tolerance=40.0)
    arr_ws = np.array(ws_clean)
    h_ws, w_ws, _ = arr_ws.shape
    
    # 6 columns
    col_w = w_ws / 6.0
    walk_frames = []
    for i in range(6):
        x0 = int(i * col_w)
        x1 = int((i + 1) * col_w)
        col_crop = ws_clean.crop((x0, 0, x1, h_ws))
        c_bbox = col_crop.getbbox()
        if c_bbox:
            col_crop = col_crop.crop(c_bbox)
        col_crop.save(DEST_DIR / f"walk_frame_{i}.png", "PNG")
        walk_frames.append(col_crop)
    print(f"Extracted {len(walk_frames)} walk frames from walk sheet.")

    # 3. Extract 4 Action Poses from Actions Sheet
    act = Image.open(ACTIONS_SHEET)
    act_clean = clean_white_background(act, tolerance=40.0)
    arr_act = np.array(act_clean)
    h_act, w_act, _ = arr_act.shape
    
    col_act_w = w_act / 4.0
    action_names = ["umbrella_happy", "spellbook_work", "cat_sleep", "butterfly_magic"]
    for i, name in enumerate(action_names):
        x0 = int(i * col_act_w)
        x1 = int((i + 1) * col_act_w)
        pose_crop = act_clean.crop((x0, 0, x1, h_act))
        p_bbox = pose_crop.getbbox()
        if p_bbox:
            pose_crop = pose_crop.crop(p_bbox)
        pose_crop.save(DEST_DIR / f"{name}.png", "PNG")
        print(f"Extracted action pose: {name}.png (size {pose_crop.size})")

if __name__ == "__main__":
    extract_goth_girl()
