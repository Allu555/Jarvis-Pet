import numpy as np
from PIL import Image
from collections import deque

src_path = r"C:\Users\alame\.gemini\antigravity-ide\brain\39d2fa9e-9b0d-4564-9852-7c140f8d8f57\.user_uploaded\media_1788674470246.png"
orig_img = Image.open(src_path).convert("RGBA")
w, h = orig_img.size
arr = np.array(orig_img)

# Flood fill from the outer boundary pixels where background is pure/near white
# (R >= 240, G >= 240, B >= 240)
rgb = arr[:, :, :3].astype(np.int32)
is_white = (rgb[:, :, 0] >= 238) & (rgb[:, :, 1] >= 238) & (rgb[:, :, 2] >= 238)

visited = np.zeros((h, w), dtype=bool)
bg_mask = np.zeros((h, w), dtype=bool)

queue = deque()

# Add all image border pixels that are white to the queue
for x in range(w):
    if is_white[0, x]:
        queue.append((0, x))
        visited[0, x] = True
    if is_white[h - 1, x]:
        queue.append((h - 1, x))
        visited[h - 1, x] = True

for y in range(h):
    if is_white[y, 0]:
        queue.append((y, 0))
        visited[y, 0] = True
    if is_white[y, w - 1]:
        queue.append((y, w - 1))
        visited[y, w - 1] = True

# 4-connectivity BFS
while queue:
    cy, cx = queue.popleft()
    bg_mask[cy, cx] = True
    
    for dy, dx in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
        ny, nx = cy + dy, cx + dx
        if 0 <= ny < h and 0 <= nx < w:
            if not visited[ny, nx] and is_white[ny, nx]:
                visited[ny, nx] = True
                queue.append((ny, nx))

# Make background transparent
arr[bg_mask, 3] = 0

flood_clean = Image.fromarray(arr)
flood_clean.save(r"C:\Users\alame\Downloads\Desktop-Pet-main\Desktop-Pet-main\assets\ghost_spider_sources\sheet_flood_clean.png")
print("Saved sheet_flood_clean.png with preserved white hoods and masks!")
