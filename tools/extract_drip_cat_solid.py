import pathlib
import numpy as np
from PIL import Image
from collections import deque

src_path = r"C:\Users\alame\.gemini\antigravity-ide\brain\39d2fa9e-9b0d-4564-9852-7c140f8d8f57\.user_uploaded\media_1788675287111.png"
out_dir = pathlib.Path(r"c:\Users\alame\Downloads\Desktop-Pet-main\Desktop-Pet-main\assets\drip_cat_sources")

img = Image.open(src_path).convert("RGBA")
arr = np.array(img)
h, w = arr.shape[:2]
rgb = arr[:, :, :3].astype(np.int32)

# The checkerboard background has specific RGB values:
# Checker tile 1: RGB(20,20,20)
# Checker tile 2: RGB(35,35,35) or (34,34,34)
# Let's verify checkerboard colors:
is_checker = (np.abs(rgb[:, :, 0] - rgb[:, :, 1]) < 3) & (np.abs(rgb[:, :, 1] - rgb[:, :, 2]) < 3) & (
    ((rgb[:, :, 0] >= 16) & (rgb[:, :, 0] <= 24)) | ((rgb[:, :, 0] >= 30) & (rgb[:, :, 0] <= 40))
)

visited = np.zeros((h, w), dtype=bool)
bg_mask = np.zeros((h, w), dtype=bool)
queue = deque()

for x in range(w):
    if is_checker[0, x]:
        queue.append((0, x))
        visited[0, x] = True
    if is_checker[h-1, x]:
        queue.append((h-1, x))
        visited[h-1, x] = True

for y in range(h):
    if is_checker[y, 0]:
        queue.append((y, 0))
        visited[y, 0] = True
    if is_checker[y, w-1]:
        queue.append((y, w-1))
        visited[y, w-1] = True

while queue:
    cy, cx = queue.popleft()
    bg_mask[cy, cx] = True
    for dy, dx in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
        ny, nx = cy + dy, cx + dx
        if 0 <= ny < h and 0 <= nx < w:
            if not visited[ny, nx] and is_checker[ny, nx]:
                visited[ny, nx] = True
                queue.append((ny, nx))

# Set transparent
arr[bg_mask, 3] = 0

# Also trim tiny artifact on far right (x > 218)
for y in range(h):
    for x in range(int(w * 0.94), w):
        if y > int(h * 0.5):
            arr[y, x, 3] = 0

cleaned = Image.fromarray(arr)
bbox = cleaned.getbbox()
if bbox:
    cleaned = cleaned.crop(bbox)

cleaned.save(out_dir / "drip_cat_clean.png")
print(f"Saved solid clean Drip Cat: {cleaned.size}")
