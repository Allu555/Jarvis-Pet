import pathlib
import numpy as np
from PIL import Image
from collections import deque

src_path = r"C:\Users\alame\.gemini\antigravity-ide\brain\39d2fa9e-9b0d-4564-9852-7c140f8d8f57\.user_uploaded\media_1788675650108.png"
sprites_root = pathlib.Path(r"c:\Users\alame\Downloads\Desktop-Pet-main\Desktop-Pet-main\assets\sprites")

img = Image.open(src_path).convert("RGBA")
w, h = img.size
print(f"Full 4-Cat Sheet size: {w}x{h}")

arr = np.array(img)
rgb = arr[:, :, :3].astype(np.int32)

# Transparent background flood fill (from 4 outer borders where R>235, G>235, B>235)
is_white_bg = (rgb[:, :, 0] > 235) & (rgb[:, :, 1] > 235) & (rgb[:, :, 2] > 235)
visited = np.zeros((h, w), dtype=bool)
bg_mask = np.zeros((h, w), dtype=bool)
queue = deque()

for x in range(w):
    if is_white_bg[0, x]:
        queue.append((0, x))
        visited[0, x] = True
    if is_white_bg[h-1, x]:
        queue.append((h-1, x))
        visited[h-1, x] = True

for y in range(h):
    if is_white_bg[y, 0]:
        queue.append((y, 0))
        visited[y, 0] = True
    if is_white_bg[y, w-1]:
        queue.append((y, w-1))
        visited[y, w-1] = True

while queue:
    cy, cx = queue.popleft()
    bg_mask[cy, cx] = True
    for dy, dx in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
        ny, nx = cy + dy, cx + dx
        if 0 <= ny < h and 0 <= nx < w:
            if not visited[ny, nx] and is_white_bg[ny, nx]:
                visited[ny, nx] = True
                queue.append((ny, nx))

arr[bg_mask, 3] = 0
clean_sheet = Image.fromarray(arr)
clean_sheet.save(r"C:\Users\alame\Downloads\Desktop-Pet-main\Desktop-Pet-main\assets\all_cats_clean.png")
print("Saved all_cats_clean.png")

# Define row heights for 4 cat styles
row_height = h / 4.0
print(f"Row height: {row_height}")

cat_styles = [
    ("drip_cat", "Streetwear Drip Cat 🕶️🪙", 0),
    ("gamer_cat", "Gamer Kawaii Cat 🎧🌸", 1),
    ("cyber_cat", "Cyberpunk Neon Cat ⚡🕶️", 2),
    ("explorer_cat", "Explorer Cozy Cat 🎒📖", 3),
]

for key, display_name, r_idx in cat_styles:
    y_start = int(r_idx * row_height)
    y_end = int((r_idx + 1) * row_height)
    row_crop = clean_sheet.crop((0, y_start, w, y_end))
    print(f"Row {r_idx} ({key}): y in [{y_start}, {y_end}], size {row_crop.size}")
