import pathlib
import numpy as np
from PIL import Image
from scipy.ndimage import label, find_objects

src_dir = pathlib.Path(r"c:\Users\alame\Downloads\Desktop-Pet-main\Desktop-Pet-main\assets\ghost_spider_sources")
img = Image.open(src_dir / "sheet_clean.png").convert("RGBA")
arr = np.array(img)
alpha = arr[:, :, 3]

# Binary mask of non-empty pixels
binary = alpha > 20

# Label connected components
labeled, num_features = label(binary)
print(f"Found {num_features} connected components.")

objs = find_objects(labeled)
items = []
for idx, sl in enumerate(objs):
    if sl is None:
        continue
    ymin, ymax = sl[0].start, sl[0].stop
    xmin, xmax = sl[1].start, sl[1].stop
    w = xmax - xmin
    h = ymax - ymin
    # Filter tiny specks
    if w >= 40 and h >= 40:
        crop_img = img.crop((xmin, ymin, xmax, ymax))
        items.append((idx, ymin, xmin, w, h, crop_img))

print(f"Filtered to {len(items)} major sticker components:")
items.sort(key=lambda it: (it[1] // 100, it[2])) # sort top-to-bottom, left-to-right

for i, (orig_id, y, x, w, h, crop_img) in enumerate(items):
    out_name = f"sticker_{i:02d}_y{y}_x{x}_{w}x{h}.png"
    crop_img.save(src_dir / out_name)
    print(f"  [{i:02d}] at ({x}, {y}), size {w}x{h} -> {out_name}")
