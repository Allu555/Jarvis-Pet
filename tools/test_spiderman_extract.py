import math
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
import scipy.ndimage as ndi

SRC_IMG = Path(r"c:\Users\alame\Downloads\Desktop-Pet-main\Desktop-Pet-main\assets\spiderman_sources\spiderman_raw.png")
DEST_DIR = Path(r"c:\Users\alame\Downloads\Desktop-Pet-main\Desktop-Pet-main\assets\spiderman_sources")
OUT_FILE = DEST_DIR / "spiderman_cutout.png"

def test_extract():
    img = Image.open(SRC_IMG).convert("RGB")
    w, h = img.size
    print(f"Loaded Spiderman source: {w}x{h}")
    arr = np.array(img, dtype=np.float32)

    # 1. Detect pure white/light background
    # Background in the user's sticker image is solid white (RGB 250..255)
    r, g, b = arr[:, :, 0], arr[:, :, 1], arr[:, :, 2]
    brightness = (r + g + b) / 3.0
    diff = np.maximum.reduce([r, g, b]) - np.minimum.reduce([r, g, b])
    is_white_bg = (brightness > 235) & (diff < 25)

    labeled, num_features = ndi.label(is_white_bg)
    print(f"Num white features: {num_features}")

    # Connected to border
    border_mask = np.zeros((h, w), dtype=bool)
    border_mask[0, :] = border_mask[-1, :] = border_mask[:, 0] = border_mask[:, -1] = True
    border_labels = np.unique(labeled[border_mask])
    border_labels = border_labels[border_labels > 0]
    print(f"Border labels: {border_labels}")

    bg_mask = np.isin(labeled, border_labels)

    # Check for inner cavities (like between hanging hand and head or legs)
    for lbl in range(1, num_features + 1):
        if lbl not in border_labels:
            m = labeled == lbl
            cnt = np.sum(m)
            cy, cx = ndi.center_of_mass(m)
            # Eyes are in the face area
            # Face center is around x in [0.30*w .. 0.65*w], y in [0.25*h .. 0.60*h]
            # Eyes have thick black outlines and are inside the head.
            # Any white area that is between legs or between web strings outside the head is cavity.
            is_eye = (0.28 * h <= cy <= 0.60 * h) and (0.28 * w <= cx <= 0.62 * w)
            if not is_eye:
                print(f"Clearing background cavity {lbl} at ({cx:.1f}, {cy:.1f}), size {cnt}")
                bg_mask |= m
            else:
                print(f"Preserving eye region {lbl} at ({cx:.1f}, {cy:.1f}), size {cnt}")

    bg_mask = ndi.binary_closing(bg_mask, structure=np.ones((3, 3)))
    fg_mask = ~bg_mask

    dist_in = ndi.distance_transform_edt(fg_mask)
    dist_out = ndi.distance_transform_edt(bg_mask)

    alpha = np.zeros((h, w), dtype=np.float32)
    alpha[fg_mask] = 255.0

    edge_blur = (dist_out < 1.8) & bg_mask
    alpha[edge_blur] = 255.0 * (1.0 - dist_out[edge_blur] / 1.8)

    halo_edge = (dist_in < 1.2) & fg_mask
    alpha[halo_edge] = np.minimum(alpha[halo_edge], 255.0 * (dist_in[halo_edge] / 1.2))

    alpha = np.clip(alpha, 0, 255).astype(np.uint8)
    rgba = Image.fromarray(np.dstack([arr.astype(np.uint8), alpha]), mode="RGBA")

    bbox = rgba.getbbox()
    print("Cropped bbox:", bbox)
    if bbox:
        cropped = rgba.crop(bbox)
    else:
        cropped = rgba

    cropped.save(OUT_FILE, "PNG")
    print(f"Saved pristine Spider-Man cutout to {OUT_FILE} (size: {cropped.size})")

if __name__ == "__main__":
    test_extract()
