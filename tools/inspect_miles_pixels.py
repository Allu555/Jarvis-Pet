from pathlib import Path
from PIL import Image
import numpy as np

p = Path(__file__).parent / "miles_sources" / "miles_raw.png"
im = Image.open(p).convert("RGB")
arr = np.array(im)
print("Shape:", arr.shape)
print("Top-left pixel:", arr[0, 0])
print("Center pixel:", arr[512, 288])
# Detect dark character pixels vs white background
brightness = arr.mean(axis=2)
print("Brightness min, max, mean:", brightness.min(), brightness.max(), brightness.mean())
is_dark = brightness < 200
y_idx, x_idx = np.where(is_dark)
print(f"Character dark pixels: y in [{y_idx.min()}, {y_idx.max()}], x in [{x_idx.min()}, {x_idx.max()}]")
