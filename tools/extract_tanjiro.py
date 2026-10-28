import sys
import os
from pathlib import Path
from PIL import Image
import numpy as np
from collections import deque

SOURCE_DIR = Path(__file__).parent / "tanjiro_sources"
SOURCE_DIR.mkdir(parents=True, exist_ok=True)

FULLBODY_PATH = Path(r"C:\Users\alame\.gemini\antigravity-ide\brain\9c8acd29-534c-4785-8252-1cf94fd344bc\tanjiro_fullbody_1788617506602.jpg")
WALK_PATH = Path(r"C:\Users\alame\.gemini\antigravity-ide\brain\9c8acd29-534c-4785-8252-1cf94fd344bc\tanjiro_walk_sheet_1788617537161.jpg")
ACTIONS_PATH = Path(r"C:\Users\alame\.gemini\antigravity-ide\brain\9c8acd29-534c-4785-8252-1cf94fd344bc\tanjiro_actions_sheet_1788617575896.jpg")


def flood_fill_transparency(img_rgb: Image.Image, threshold: int = 242) -> Image.Image:
    """Accurately flood-fills white background from outer borders to preserve white clothes and eyes."""
    arr = np.array(img_rgb.convert("RGB"))
    h, w, _ = arr.shape

    is_bg = (arr[:, :, 0] >= threshold) & (arr[:, :, 1] >= threshold) & (arr[:, :, 2] >= threshold)

    bg_mask = np.zeros((h, w), dtype=bool)
    queue = deque()

    for x in range(w):
        if is_bg[0, x] and not bg_mask[0, x]:
            bg_mask[0, x] = True
            queue.append((0, x))
        if is_bg[h - 1, x] and not bg_mask[h - 1, x]:
            bg_mask[h - 1, x] = True
            queue.append((h - 1, x))

    for y in range(h):
        if is_bg[y, 0] and not bg_mask[y, 0]:
            bg_mask[y, 0] = True
            queue.append((y, 0))
        if is_bg[y, w - 1] and not bg_mask[y, w - 1]:
            bg_mask[y, w - 1] = True
            queue.append((y, w - 1))

    while queue:
        y, x = queue.popleft()
        for dy, dx in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            ny, nx = y + dy, x + dx
            if 0 <= ny < h and 0 <= nx < w:
                if not bg_mask[ny, nx] and is_bg[ny, nx]:
                    bg_mask[ny, nx] = True
                    queue.append((ny, nx))

    rgba = np.zeros((h, w, 4), dtype=np.uint8)
    rgba[:, :, :3] = arr
    rgba[:, :, 3] = np.where(bg_mask, 0, 255)

    return Image.fromarray(rgba, mode="RGBA")


def extract():
    print("1. Extracting standing full-body Tanjiro...")
    if FULLBODY_PATH.exists():
        fb_raw = Image.open(FULLBODY_PATH)
        fb_rgba = flood_fill_transparency(fb_raw, threshold=240)
        
        # Crop to character bounding box
        bbox = fb_rgba.getbbox()
        if bbox:
            fb_cropped = fb_rgba.crop(bbox)
            fb_cropped.save(SOURCE_DIR / "standing.png")
            print(f"Saved standing.png ({fb_cropped.size})")

    print("\n2. Extracting 6-pose walk cycle...")
    if WALK_PATH.exists():
        walk_raw = Image.open(WALK_PATH)
        walk_rgba = flood_fill_transparency(walk_raw, threshold=242)
        w, h = walk_rgba.size
        frame_w = w // 6

        for i in range(6):
            box = (i * frame_w, 0, (i + 1) * frame_w, h)
            cropped = walk_rgba.crop(box)
            c_bbox = cropped.getbbox()
            if c_bbox:
                final_pose = cropped.crop(c_bbox)
                final_pose.save(SOURCE_DIR / f"walk_{i}.png")
                print(f"Saved walk_{i}.png ({final_pose.size})")

    print("\n3. Extracting 4-pose action sheet...")
    if ACTIONS_PATH.exists():
        act_raw = Image.open(ACTIONS_PATH)
        act_rgba = flood_fill_transparency(act_raw, threshold=242)
        w, h = act_rgba.size
        act_w = w // 4

        names = ["water_dragon", "eat_onigiri", "jump_slash", "sit_nezuko"]
        for i, name in enumerate(names):
            box = (i * act_w, 0, (i + 1) * act_w, h)
            cropped = act_rgba.crop(box)
            c_bbox = cropped.getbbox()
            if c_bbox:
                final_pose = cropped.crop(c_bbox)
                final_pose.save(SOURCE_DIR / f"{name}.png")
                print(f"Saved {name}.png ({final_pose.size})")


if __name__ == "__main__":
    extract()
