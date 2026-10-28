import pathlib
import numpy as np
from PIL import Image

src_path = r"C:\Users\alame\.gemini\antigravity-ide\brain\39d2fa9e-9b0d-4564-9852-7c140f8d8f57\.user_uploaded\media_1788675287111.png"
out_dir = pathlib.Path(r"c:\Users\alame\Downloads\Desktop-Pet-main\Desktop-Pet-main\assets\drip_cat_sources")

img = Image.open(src_path).convert("RGBA")
arr = np.array(img)
h, w = arr.shape[:2]

# Let's check the checkerboard pattern:
# Top-left corner (0,0) is part of the checkerboard.
# Let's inspect the exact RGB values of the checkerboard squares:
print("Pixel (0,0):", arr[0, 0])
print("Pixel (16,0):", arr[0, 16])
print("Pixel (0,16):", arr[16, 0])
print("Pixel (16,16):", arr[16, 16])

# Let's see: in checkerboard background:
# Every 16x16 block has perfectly uniform color: either [20,20,20] or [34,34,34] (or [21,21,21]/[35,35,35])
# Whereas the cat's hoodie has smooth shading, gradients, anti-aliased outlines, and different texture.
# Moreover, we can trace the outer boundary using edge detection or contour finding.
