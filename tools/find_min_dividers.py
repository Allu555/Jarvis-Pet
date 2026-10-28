import numpy as np
from PIL import Image

src_path = r"C:\Users\alame\.gemini\antigravity-ide\brain\39d2fa9e-9b0d-4564-9852-7c140f8d8f57\.user_uploaded\media_1788675494202.png"
img = Image.open(src_path).convert("RGBA")
w, h = img.size

walk_strip = img.crop((int(0.20 * w), int(0.12 * h), w, int(0.50 * h)))
arr = np.array(walk_strip)
rgb = arr[:, :, :3]
non_white_col = ((rgb[:, :, 0] < 235) | (rgb[:, :, 1] < 235) | (rgb[:, :, 2] < 235)).sum(axis=0)

base_x = int(0.20 * w)

# Find minimums in regions:
# Region 1: 180 to 240
m1 = 180 + np.argmin(non_white_col[180:240])
# Region 2: 380 to 440
m2 = 380 + np.argmin(non_white_col[380:440])
# Region 3: 580 to 640
m3 = 580 + np.argmin(non_white_col[580:640])

print(f"Dividers in strip: {m1}, {m2}, {m3}")
print(f"Global x dividers: {base_x + m1}, {base_x + m2}, {base_x + m3}")
