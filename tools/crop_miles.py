from pathlib import Path
from PIL import Image
import numpy as np

p = Path(__file__).parent / "miles_sources" / "miles_cutout.png"
im = Image.open(p)
arr = np.array(im)
alpha = arr[:, :, 3]
y_indices, x_indices = np.where(alpha > 10)
if len(y_indices) > 0:
    min_y, max_y = y_indices.min(), y_indices.max()
    min_x, max_x = x_indices.min(), x_indices.max()
    print(f"Character bounding box: x in [{min_x}, {max_x}], y in [{min_y}, {max_y}] (width={max_x - min_x + 1}, height={max_y - min_y + 1})")
    cropped = im.crop((min_x, min_y, max_x + 1, max_y + 1))
    cropped.save(Path(__file__).parent / "miles_sources" / "miles_tight_cutout.png")
    print(f"Saved tight cutout to {Path(__file__).parent / 'miles_sources' / 'miles_tight_cutout.png'} (size: {cropped.size})")
