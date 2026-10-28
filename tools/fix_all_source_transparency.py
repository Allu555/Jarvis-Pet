import os
from pathlib import Path
from PIL import Image
import numpy as np
from collections import deque

SOURCE_DIRS = [
    Path(__file__).parent / "nezuko_sources",
    Path(__file__).parent / "zenitsu_sources",
    Path(__file__).parent / "batman_cat_sources",
    Path(__file__).parent / "inosuke_sources",
    Path(__file__).parent / "akaza_sources",
]


def flood_fill_transparency(img_rgba: Image.Image, threshold: int = 238) -> Image.Image:
    arr = np.array(img_rgba.convert("RGBA"))
    h, w, _ = arr.shape

    # Pixel is background if RGB is bright white or already transparent
    is_bg = ((arr[:, :, 0] >= threshold) & (arr[:, :, 1] >= threshold) & (arr[:, :, 2] >= threshold)) | (arr[:, :, 3] < 30)

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

    arr[:, :, 3] = np.where(bg_mask, 0, arr[:, :, 3])
    # Also crop to tight bounding box
    alpha = arr[:, :, 3] > 10
    if np.any(alpha):
        y_indices, x_indices = np.where(alpha)
        arr = arr[y_indices.min():y_indices.max() + 1, x_indices.min():x_indices.max() + 1]

    return Image.fromarray(arr, mode="RGBA")


def fix_all():
    print("Fixing all source transparency...")
    for sdir in SOURCE_DIRS:
        if not sdir.exists():
            continue
        for f in sdir.glob("*.png"):
            im = Image.open(f)
            cleaned = flood_fill_transparency(im, threshold=235)
            cleaned.save(f)
            print(f"  Fixed {sdir.name}/{f.name} -> size={cleaned.size}")


if __name__ == "__main__":
    fix_all()
