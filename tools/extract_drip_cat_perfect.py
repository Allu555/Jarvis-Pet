import pathlib
import numpy as np
from PIL import Image
from scipy.ndimage import binary_fill_holes, sobel

src_path = r"C:\Users\alame\.gemini\antigravity-ide\brain\39d2fa9e-9b0d-4564-9852-7c140f8d8f57\.user_uploaded\media_1788675390295.jpg"
img = Image.open(src_path).convert("RGBA")
w, h = img.size

# Let's inspect the IDLE card:
idle_crop = img.crop((int(0.03 * w), int(0.16 * h), int(0.22 * w), int(0.48 * h)))
arr = np.array(idle_crop)
ch, cw = arr.shape[:2]
rgb = arr[:, :, :3]

# The card background is very uniform: RGB around [21, 22, 26] with variance < 2
# Let's measure the background color at the corners:
c1 = rgb[2, 2]
c2 = rgb[2, cw-3]
c3 = rgb[ch-3, 2]
c4 = rgb[ch-3, cw-3]
print("Corners:", c1, c2, c3, c4)

# The background is precisely within distance <= 5 from [21, 22, 26]
bg_ref = np.array([21, 22, 26], dtype=np.float32)
dist = np.linalg.norm(rgb.astype(np.float32) - bg_ref, axis=2)

# But inside the cat, the hoodie has highlights, folds, shading, and the cat body is surrounded by the head, gold chain, paws, and grey fur.
# Let's use watershed / BFS that only expands from the image edges through connected background pixels and stops at any high gradient edge or non-background color.
from collections import deque

visited = np.zeros((ch, cw), dtype=bool)
bg_mask = np.zeros((ch, cw), dtype=bool)
queue = deque()

# Add outer border pixels
for x in range(cw):
    if dist[0, x] < 6.0:
        queue.append((0, x))
        visited[0, x] = True
    if dist[ch-1, x] < 6.0:
        queue.append((ch-1, x))
        visited[ch-1, x] = True
for y in range(ch):
    if dist[y, 0] < 6.0:
        queue.append((y, 0))
        visited[y, 0] = True
    if dist[y, cw-1] < 6.0:
        queue.append((y, cw-1))
        visited[y, cw-1] = True

# Also compute gradient magnitude
gx = sobel(rgb.mean(axis=2), axis=1)
gy = sobel(rgb.mean(axis=2), axis=0)
grad = np.hypot(gx, gy)

while queue:
    cy, cx = queue.popleft()
    bg_mask[cy, cx] = True
    for dy, dx in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
        ny, nx = cy + dy, cx + dx
        if 0 <= ny < ch and 0 <= nx < cw:
            if not visited[ny, nx]:
                # If pixel is flat background and gradient is low
                if dist[ny, nx] < 6.0 and grad[ny, nx] < 15:
                    visited[ny, nx] = True
                    queue.append((ny, nx))

arr[bg_mask, 3] = 0

# Fill any internal holes enclosed within the cat
cat_mask = ~bg_mask
cat_mask_filled = binary_fill_holes(cat_mask)
arr[cat_mask_filled, 3] = 255

res = Image.fromarray(arr)
bbox = res.getbbox()
if bbox:
    res = res.crop(bbox)
res.save(r"C:\Users\alame\Downloads\Desktop-Pet-main\Desktop-Pet-main\assets\drip_cat_sources\idle_perfect.png")
print("Saved idle_perfect.png!")
