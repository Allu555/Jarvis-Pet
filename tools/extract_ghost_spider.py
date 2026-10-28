import os
import pathlib
import numpy as np
from PIL import Image

src_path = r"C:\Users\alame\.gemini\antigravity-ide\brain\39d2fa9e-9b0d-4564-9852-7c140f8d8f57\.user_uploaded\media_1788674470246.png"
out_dir = pathlib.Path(r"c:\Users\alame\Downloads\Desktop-Pet-main\Desktop-Pet-main\assets\ghost_spider_sources")
out_dir.mkdir(parents=True, exist_ok=True)

img = Image.open(src_path).convert("RGBA")
w, h = img.size
print(f"Sheet size: {w}x{h}")

arr = np.array(img)
rgb = arr[:, :, :3]
alpha = arr[:, :, 3].copy()

# Background is pure white (R>245, G>245, B>245)
white_mask = (rgb[:, :, 0] > 240) & (rgb[:, :, 1] > 240) & (rgb[:, :, 2] > 240)
alpha[white_mask] = 0
arr[:, :, 3] = alpha

# Also save full transparent sheet
cleaned_sheet = Image.fromarray(arr)
cleaned_sheet.save(out_dir / "sheet_clean.png")
print("Saved sheet_clean.png")

# Define crops for key poses based on coordinates on 564x1003 image (or whatever resolution it is)
# Let's find connected components or slice key regions:
print(f"Image dimensions: {w}x{h}")
