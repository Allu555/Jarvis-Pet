import pathlib
import numpy as np
from PIL import Image

src_path = r"C:\Users\alame\.gemini\antigravity-ide\brain\39d2fa9e-9b0d-4564-9852-7c140f8d8f57\.user_uploaded\media_1788674688676.png"
out_dir = pathlib.Path(r"c:\Users\alame\Downloads\Desktop-Pet-main\Desktop-Pet-main\assets\gwen_sources")
out_dir.mkdir(parents=True, exist_ok=True)

img = Image.open(src_path).convert("RGBA")
w, h = img.size
print(f"Original size: {w}x{h}")

arr = np.array(img)
rgb = arr[:, :, :3].astype(np.int32)
alpha = arr[:, :, 3].copy()

# The background has light grid lines and white/off-white (R>230, G>230, B>230)
# But Gwen's hood, mask, and hands are white!
# So we flood-fill from the outer 4 borders to remove ONLY the background grid,
# leaving all internal white parts (hood, mask, hands) 100% solid!

from collections import deque

# Background is white/light-gray (R>215, G>215, B>215)
is_bg = (rgb[:, :, 0] > 215) & (rgb[:, :, 1] > 215) & (rgb[:, :, 2] > 215)

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

# Set background to transparent
arr[bg_mask, 3] = 0

# Remove text watermark at top ("Baby Spider Gwen" and "Work with Cricut") and bottom watermark
# "Baby Spider Gwen" text is top-left x: 0 to 550, y: 0 to 140
for y in range(int(h * 0.14)):
    for x in range(w):
        # Clear top text area above Gwen's hood
        if y < int(h * 0.13) and (x < int(w * 0.55) or x > int(w * 0.75)):
            arr[y, x, 3] = 0

# Bottom watermark at y > 0.90*h
for y in range(int(h * 0.90), h):
    for x in range(w):
        arr[y, x, 3] = 0

cleaned_sheet = Image.fromarray(arr)
cleaned_sheet.save(out_dir / "gwen_clean_sheet.png")

# Now crop Character 1 (Standing on right) and Character 2 (Swinging on left)
# 1. Standing Gwen (Right side)
standing_crop = cleaned_sheet.crop((int(w * 0.58), int(h * 0.32), int(w * 0.98), int(h * 0.89)))
s_bbox = standing_crop.getbbox()
if s_bbox:
    standing_crop = standing_crop.crop(s_bbox)
standing_crop.save(out_dir / "gwen_standing_clean.png")
print(f"Saved standing Gwen: {standing_crop.size}")

# 2. Swinging Gwen (Left side)
swinging_crop = cleaned_sheet.crop((int(w * 0.05), int(h * 0.12), int(w * 0.58), int(h * 0.68)))
sw_bbox = swinging_crop.getbbox()
if sw_bbox:
    swinging_crop = swinging_crop.crop(sw_bbox)
swinging_crop.save(out_dir / "gwen_swinging_clean.png")
print(f"Saved swinging Gwen: {swinging_crop.size}")
