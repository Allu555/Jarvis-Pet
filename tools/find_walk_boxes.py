import numpy as np
from PIL import Image
from scipy.ndimage import label, find_objects

src_path = r"C:\Users\alame\.gemini\antigravity-ide\brain\39d2fa9e-9b0d-4564-9852-7c140f8d8f57\.user_uploaded\media_1788675494202.png"
img = Image.open(src_path).convert("RGBA")
arr = np.array(img)
h, w = arr.shape[:2]

# Walking strip is located at y in [int(0.10*h), int(0.50*h)], x in [int(0.20*w), w]
walk_strip = img.crop((int(0.20 * w), int(0.12 * h), w, int(0.50 * h)))
warr = np.array(walk_strip)
wrgb = warr[:, :, :3]

# Non-white pixels (the cat)
non_white = (wrgb[:, :, 0] < 235) | (wrgb[:, :, 1] < 235) | (wrgb[:, :, 2] < 235)

# Label connected components
labeled, num_features = label(non_white)
objs = find_objects(labeled)

cats = []
for idx, sl in enumerate(objs):
    if sl is None: continue
    ymin, ymax = sl[0].start, sl[0].stop
    xmin, xmax = sl[1].start, sl[1].stop
    cw, ch = xmax - xmin, ymax - ymin
    if cw > 100 and ch > 100:
        cats.append((xmin, ymin, xmax, ymax, cw, ch))

cats.sort(key=lambda c: c[0])
print(f"Found {len(cats)} major walking cat components:")
for i, c in enumerate(cats):
    print(f"  Cat {i+1}: x in [{c[0]}, {c[2]}], y in [{c[1]}, {c[3]}], size: {c[4]}x{c[5]}")
