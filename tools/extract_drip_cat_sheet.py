import pathlib
import numpy as np
from PIL import Image

src_path = r"C:\Users\alame\.gemini\antigravity-ide\brain\39d2fa9e-9b0d-4564-9852-7c140f8d8f57\.user_uploaded\media_1788675390295.jpg"
out_dir = pathlib.Path(r"c:\Users\alame\Downloads\Desktop-Pet-main\Desktop-Pet-main\assets\drip_cat_sources")
out_dir.mkdir(parents=True, exist_ok=True)

img = Image.open(src_path).convert("RGBA")
w, h = img.size
print(f"Sheet dimensions: {w}x{h}")

# The image is divided into 4 cards:
# 1. IDLE: x in [0.02*w, 0.22*w], y in [0.12*h, 0.52*h]
# 2. WALKING container: x in [0.25*w, 0.98*w], y in [0.12*h, 0.52*h]
#    - Walk 1: x in [0.25*w, 0.44*w]
#    - Walk 2: x in [0.44*w, 0.62*w]
#    - Walk 3: x in [0.62*w, 0.80*w]
#    - Walk 4: x in [0.80*w, 0.98*w]
# 3. WORKING: x in [0.02*w, 0.49*w], y in [0.57*h, 0.95*h]
# 4. SLEEPING: x in [0.52*w, 0.98*w], y in [0.57*h, 0.95*h]

# Let's write an algorithm to remove dark card background (RGB around 14, 15, 20) using flood fill from card corners
from collections import deque

def remove_dark_background(crop_img, bg_thresh=35):
    arr = np.array(crop_img)
    ch, cw = arr.shape[:2]
    rgb = arr[:, :, :3].astype(np.int32)
    
    # Background is dark grey/black (R<bg_thresh, G<bg_thresh, B<bg_thresh)
    is_bg = (rgb[:, :, 0] < bg_thresh) & (rgb[:, :, 1] < bg_thresh) & (rgb[:, :, 2] < bg_thresh)
    
    visited = np.zeros((ch, cw), dtype=bool)
    bg_mask = np.zeros((ch, cw), dtype=bool)
    queue = deque()
    
    for x in range(cw):
        if is_bg[0, x]:
            queue.append((0, x))
            visited[0, x] = True
        if is_bg[ch-1, x]:
            queue.append((ch-1, x))
            visited[ch-1, x] = True
            
    for y in range(ch):
        if is_bg[y, 0]:
            queue.append((y, 0))
            visited[y, 0] = True
        if is_bg[y, cw-1]:
            queue.append((y, cw-1))
            visited[y, cw-1] = True
            
    while queue:
        cy, cx = queue.popleft()
        bg_mask[cy, cx] = True
        for dy, dx in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            ny, nx = cy + dy, cx + dx
            if 0 <= ny < ch and 0 <= nx < cw:
                if not visited[ny, nx] and is_bg[ny, nx]:
                    visited[ny, nx] = True
                    queue.append((ny, nx))
                    
    arr[bg_mask, 3] = 0
    res = Image.fromarray(arr)
    bbox = res.getbbox()
    if bbox:
        res = res.crop(bbox)
    return res

# Crop regions:
# IDLE
idle_raw = img.crop((int(0.03 * w), int(0.16 * h), int(0.22 * w), int(0.48 * h)))
idle_clean = remove_dark_background(idle_raw, bg_thresh=30)
idle_clean.save(out_dir / "raw_idle.png")
print(f"Saved raw_idle: {idle_clean.size}")

# WALKING 1, 2, 3, 4
walk_boxes = [
    (int(0.25 * w), int(0.18 * h), int(0.44 * w), int(0.46 * h)),
    (int(0.44 * w), int(0.18 * h), int(0.62 * w), int(0.46 * h)),
    (int(0.62 * w), int(0.18 * h), int(0.80 * w), int(0.46 * h)),
    (int(0.80 * w), int(0.18 * h), int(0.98 * w), int(0.46 * h)),
]
for i, box in enumerate(walk_boxes):
    w_raw = img.crop(box)
    w_clean = remove_dark_background(w_raw, bg_thresh=32)
    w_clean.save(out_dir / f"raw_walk_{i+1}.png")
    print(f"Saved raw_walk_{i+1}: {w_clean.size}")

# WORKING
work_raw = img.crop((int(0.04 * w), int(0.59 * h), int(0.48 * w), int(0.91 * h)))
work_clean = remove_dark_background(work_raw, bg_thresh=30)
work_clean.save(out_dir / "raw_work.png")
print(f"Saved raw_work: {work_clean.size}")

# SLEEPING
sleep_raw = img.crop((int(0.53 * w), int(0.58 * h), int(0.95 * w), int(0.92 * h)))
sleep_clean = remove_dark_background(sleep_raw, bg_thresh=30)
sleep_clean.save(out_dir / "raw_sleep.png")
print(f"Saved raw_sleep: {sleep_clean.size}")
