import sys
import os
from pathlib import Path
from PIL import Image
import numpy as np
from collections import deque
from scipy import ndimage

SOURCE_DIR = Path(__file__).parent / "nezuko_sources"
SOURCE_DIR.mkdir(parents=True, exist_ok=True)

REF_PATH = Path(r"C:\Users\alame\.gemini\antigravity-ide\brain\9c8acd29-534c-4785-8252-1cf94fd344bc\.user_uploaded\media_1788618250733.png")
WALK_PATH = Path(r"C:\Users\alame\.gemini\antigravity-ide\brain\9c8acd29-534c-4785-8252-1cf94fd344bc\nezuko_walk_sheet_1788618573110.jpg")
ACTIONS_PATH = Path(r"C:\Users\alame\.gemini\antigravity-ide\brain\9c8acd29-534c-4785-8252-1cf94fd344bc\nezuko_actions_sheet_1788618594116.jpg")


def flood_fill_transparency(img_rgb: Image.Image, threshold: int = 242) -> Image.Image:
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
    print("Extracting Nezuko...")
    if REF_PATH.exists():
        ref = Image.open(REF_PATH).convert("RGBA")
        # Ensure pure transparency
        ref_arr = np.array(ref)
        # If alpha already clean
        ref.save(SOURCE_DIR / "ref_standing.png")
        print("  Saved ref_standing.png")

    if WALK_PATH.exists():
        walk_img = Image.open(WALK_PATH).convert("RGB")
        walk_transparent = flood_fill_transparency(walk_img, 240)
        arr = np.array(walk_transparent)
        alpha = arr[:, :, 3] > 0
        labeled, _ = ndimage.label(alpha)
        objs = ndimage.find_objects(labeled)
        big_objs = [s for s in objs if s is not None and (s[0].stop - s[0].start) > 200 and (s[1].stop - s[1].start) > 100]
        big_objs.sort(key=lambda s: (s[0].start // 450, s[1].start))

        for i, s in enumerate(big_objs[:6]):
            crop = walk_transparent.crop((s[1].start, s[0].start, s[1].stop, s[0].stop))
            crop.save(SOURCE_DIR / f"walk_{i}.png")
            print(f"  Saved walk_{i}.png size={crop.size}")

    if ACTIONS_PATH.exists():
        act_img = Image.open(ACTIONS_PATH).convert("RGB")
        act_transparent = flood_fill_transparency(act_img, 240)
        arr = np.array(act_transparent)
        alpha = arr[:, :, 3] > 0
        labeled, _ = ndimage.label(alpha)
        objs = ndimage.find_objects(labeled)
        big_objs = [s for s in objs if s is not None and (s[0].stop - s[0].start) > 150 and (s[1].stop - s[1].start) > 100]
        big_objs.sort(key=lambda s: (s[0].start // 450, s[1].start))
        names = ["flame_attack", "tiny_run", "box_sleep", "kick", "eat_candy", "celebrate"]
        for i, s in enumerate(big_objs):
            name = names[i] if i < len(names) else f"act_{i}"
            crop = act_transparent.crop((s[1].start, s[0].start, s[1].stop, s[0].stop))
            crop.save(SOURCE_DIR / f"{name}.png")
            print(f"  Saved {name}.png size={crop.size}")


if __name__ == "__main__":
    extract()
