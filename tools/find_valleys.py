import numpy as np
from PIL import Image

src_path = r"C:\Users\alame\.gemini\antigravity-ide\brain\39d2fa9e-9b0d-4564-9852-7c140f8d8f57\.user_uploaded\media_1788675494202.png"
img = Image.open(src_path).convert("RGBA")
w, h = img.size

walk_strip = img.crop((int(0.20 * w), int(0.12 * h), w, int(0.50 * h)))
arr = np.array(walk_strip)
rgb = arr[:, :, :3]

# Count non-white pixels per column
non_white_col = ((rgb[:, :, 0] < 235) | (rgb[:, :, 1] < 235) | (rgb[:, :, 2] < 235)).sum(axis=0)

# Print local minima / valleys in columns:
valleys = []
for x in range(10, len(non_white_col) - 10):
    if non_white_col[x] == 0 or (non_white_col[x] < 5 and non_white_col[x] <= min(non_white_col[x-5:x+6])):
        valleys.append(x)

print("Zero / low columns in walk strip:", valleys)

# Relative to global image x (global_x = x + int(0.20*w))
base_x = int(0.20 * w)
for v in valleys:
    print(f"  global x = {base_x + v} (val = {non_white_col[v]})")
