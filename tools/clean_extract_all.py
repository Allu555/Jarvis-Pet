import sys
import os
from pathlib import Path
from PIL import Image
import numpy as np
from collections import deque
from scipy import ndimage

BRAIN_DIR = Path(r"C:\Users\alame\.gemini\antigravity-ide\brain\9c8acd29-534c-4785-8252-1cf94fd344bc")
UPLOADS_DIR = BRAIN_DIR / ".user_uploaded"


def flood_fill_clean(img_rgb: Image.Image, threshold: int = 230) -> Image.Image:
    arr = np.array(img_rgb.convert("RGB"))
    h, w, _ = arr.shape
    is_bg = (arr[:, :, 0] >= threshold) & (arr[:, :, 1] >= threshold) & (arr[:, :, 2] >= threshold)
    bg_mask = np.zeros((h, w), dtype=bool)
    queue = deque()
    for x in range(w):
        if is_bg[0, x] and not bg_mask[0, x]: bg_mask[0, x] = True; queue.append((0, x))
        if is_bg[h - 1, x] and not bg_mask[h - 1, x]: bg_mask[h - 1, x] = True; queue.append((h - 1, x))
    for y in range(h):
        if is_bg[y, 0] and not bg_mask[y, 0]: bg_mask[y, 0] = True; queue.append((y, 0))
        if is_bg[y, w - 1] and not bg_mask[y, w - 1]: bg_mask[y, w - 1] = True; queue.append((y, w - 1))
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


def extract_nezuko():
    print("Clean extracting Nezuko...")
    out_dir = Path(__file__).parent / "nezuko_sources"
    out_dir.mkdir(parents=True, exist_ok=True)
    
    # 1. Standing reference
    ref_path = UPLOADS_DIR / "media_1788618250733.png"
    if ref_path.exists():
        ref_im = flood_fill_clean(Image.open(ref_path), 220)
        arr = np.array(ref_im)
        alpha = arr[:, :, 3] > 0
        y_idx, x_idx = np.where(alpha)
        crop = ref_im.crop((x_idx.min(), y_idx.min(), x_idx.max() + 1, y_idx.max() + 1))
        crop.save(out_dir / "ref_standing.png")
        print("  Saved clean ref_standing.png", crop.size)

    # 2. Walk sheet
    walk_path = BRAIN_DIR / "nezuko_walk_sheet_1788618573110.jpg"
    if walk_path.exists():
        walk_im = flood_fill_clean(Image.open(walk_path), 230)
        arr = np.array(walk_im)
        alpha = arr[:, :, 3] > 0
        labeled, _ = ndimage.label(alpha)
        objs = ndimage.find_objects(labeled)
        big_objs = [s for s in objs if s is not None and (s[0].stop - s[0].start) > 200 and (s[1].stop - s[1].start) > 100]
        big_objs.sort(key=lambda s: (s[0].start // 450, s[1].start))
        for i, s in enumerate(big_objs[:6]):
            crop = walk_im.crop((s[1].start, s[0].start, s[1].stop, s[0].stop))
            crop.save(out_dir / f"walk_{i}.png")
            print(f"  Saved walk_{i}.png", crop.size)

    # 3. Actions sheet
    act_path = BRAIN_DIR / "nezuko_actions_sheet_1788618594116.jpg"
    if act_path.exists():
        act_im = flood_fill_clean(Image.open(act_path), 230)
        arr = np.array(act_im)
        alpha = arr[:, :, 3] > 0
        labeled, _ = ndimage.label(alpha)
        objs = ndimage.find_objects(labeled)
        big_objs = [s for s in objs if s is not None and (s[0].stop - s[0].start) > 150 and (s[1].stop - s[1].start) > 100]
        big_objs.sort(key=lambda s: (s[0].start // 450, s[1].start))
        names = ["flame_attack", "tiny_run", "box_sleep", "kick", "eat_candy", "celebrate"]
        for i, s in enumerate(big_objs):
            name = names[i] if i < len(names) else f"act_{i}"
            crop = act_im.crop((s[1].start, s[0].start, s[1].stop, s[0].stop))
            crop.save(out_dir / f"{name}.png")
            print(f"  Saved {name}.png", crop.size)


def extract_zenitsu():
    print("Clean extracting Zenitsu...")
    out_dir = Path(__file__).parent / "zenitsu_sources"
    out_dir.mkdir(parents=True, exist_ok=True)
    
    # 1. Standing reference
    ref_path = UPLOADS_DIR / "media_1788618275435.png"
    if ref_path.exists():
        ref_im = flood_fill_clean(Image.open(ref_path), 220)
        arr = np.array(ref_im)
        alpha = arr[:, :, 3] > 0
        y_idx, x_idx = np.where(alpha)
        crop = ref_im.crop((x_idx.min(), y_idx.min(), x_idx.max() + 1, y_idx.max() + 1))
        crop.save(out_dir / "ref_standing.png")
        print("  Saved clean ref_standing.png", crop.size)

    # 2. Walk sheet
    walk_path = BRAIN_DIR / "zenitsu_walk_sheet_1788618616743.jpg"
    if walk_path.exists():
        walk_im = flood_fill_clean(Image.open(walk_path), 230)
        arr = np.array(walk_im)
        alpha = arr[:, :, 3] > 0
        labeled, _ = ndimage.label(alpha)
        objs = ndimage.find_objects(labeled)
        big_objs = [s for s in objs if s is not None and (s[0].stop - s[0].start) > 200 and (s[1].stop - s[1].start) > 100]
        big_objs.sort(key=lambda s: (s[0].start // 450, s[1].start))
        for i, s in enumerate(big_objs[:6]):
            crop = walk_im.crop((s[1].start, s[0].start, s[1].stop, s[0].stop))
            crop.save(out_dir / f"walk_{i}.png")
            print(f"  Saved walk_{i}.png", crop.size)

    # 3. Actions sheet
    act_path = BRAIN_DIR / "zenitsu_actions_sheet_1788618639479.jpg"
    if act_path.exists():
        act_im = flood_fill_clean(Image.open(act_path), 230)
        arr = np.array(act_im)
        alpha = arr[:, :, 3] > 0
        labeled, _ = ndimage.label(alpha)
        objs = ndimage.find_objects(labeled)
        big_objs = [s for s in objs if s is not None and (s[0].stop - s[0].start) > 150 and (s[1].stop - s[1].start) > 100]
        big_objs.sort(key=lambda s: (s[0].start // 450, s[1].start))
        names = ["thunderclap", "crying", "sleep_swordsman", "eat_onigiri", "scared_jump", "confident_sparkle"]
        for i, s in enumerate(big_objs):
            name = names[i] if i < len(names) else f"act_{i}"
            crop = act_im.crop((s[1].start, s[0].start, s[1].stop, s[0].stop))
            crop.save(out_dir / f"{name}.png")
            print(f"  Saved {name}.png", crop.size)


if __name__ == "__main__":
    extract_nezuko()
    extract_zenitsu()
