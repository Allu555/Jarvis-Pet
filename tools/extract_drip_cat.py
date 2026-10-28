import pathlib
import numpy as np
from PIL import Image

src_path = r"C:\Users\alame\.gemini\antigravity-ide\brain\39d2fa9e-9b0d-4564-9852-7c140f8d8f57\.user_uploaded\media_1788675287111.png"
out_dir = pathlib.Path(r"c:\Users\alame\Downloads\Desktop-Pet-main\Desktop-Pet-main\assets\drip_cat_sources")
out_dir.mkdir(parents=True, exist_ok=True)

img = Image.open(src_path).convert("RGBA")
w, h = img.size
print(f"Original size: {w}x{h}")

arr = np.array(img)
rgb = arr[:, :, :3].astype(np.int32)
alpha = arr[:, :, 3].copy()

# The background has a checkerboard pattern (dark squares ~ RGB(18,18,18) to (30,30,30))
# Let's flood fill from outer border pixels or remove the dark checkerboard background
from collections import deque

# Check border pixels
border_colors = []
for x in range(w):
    border_colors.append(rgb[0, x])
    border_colors.append(rgb[h-1, x])
for y in range(h):
    border_colors.append(rgb[y, 0])
    border_colors.append(rgb[y, w-1])

border_colors = np.array(border_colors)
print(f"Border colors min: {border_colors.min(axis=0)}, max: {border_colors.max(axis=0)}, mean: {border_colors.mean(axis=0)}")

# Dark checkerboard squares are dark grey/black: R<40, G<40, B<40
is_bg = (rgb[:, :, 0] < 38) & (rgb[:, :, 1] < 38) & (rgb[:, :, 2] < 38)

visited = np.zeros((h, w), dtype=bool)
bg_mask = np.zeros((h, w), dtype=bool)
queue = deque()

for x in range(w):
    if is_bg[0, x]:
        queue.append((0, x))
        visited[0, x] = True
    if is_bg[h-1, x]:
        queue.append((h-1, x))
        visited[h-1, x] = True

for y in range(h):
    if is_bg[y, 0]:
        queue.append((y, 0))
        visited[y, 0] = True
    if is_bg[y, w-1]:
        queue.append((y, w-1))
        visited[y, w-1] = True

while queue:
    cy, cx = queue.popleft()
    bg_mask[cy, cx] = True
    for dy, dx in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
        ny, nx = cy + dy, cx + dx
        if 0 <= ny < h and 0 <= nx < w:
            if not visited[ny, nx] and is_bg[ny, nx]:
                visited[ny, nx] = True
                queue.append((ny, nx))

arr[bg_mask, 3] = 0

# Also check for artifact at right edge (there was a tiny crop artifact on far right)
for y in range(h):
    for x in range(int(w * 0.95), w):
        if y > int(h * 0.5):
            arr[y, x, 3] = 0

cleaned = Image.fromarray(arr)
bbox = cleaned.getbbox()
if bbox:
    cleaned = cleaned.crop(bbox)
cleaned.save(out_dir / "drip_cat_raw_cutout.png")
print(f"Saved raw cutout: {cleaned.size}")
