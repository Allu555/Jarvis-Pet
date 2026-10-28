from pathlib import Path
from PIL import Image
import numpy as np
import scipy.ndimage as ndi

SRC_PATH = Path(__file__).parent / "miles_sources" / "miles_raw.png"
OUT_CUTOUT = Path(__file__).parent / "miles_sources" / "miles_cutout.png"

def extract_clean_miles():
    img = Image.open(SRC_PATH).convert("RGB")
    arr = np.array(img, dtype=np.float32)

    # 1. Crop to character area
    brightness = arr.mean(axis=2)
    is_char = brightness < 235
    y_idx, x_idx = np.where(is_char)
    pad = 10
    min_y = max(0, y_idx.min() - pad)
    max_y = min(arr.shape[0] - 1, y_idx.max() + pad)
    min_x = max(0, x_idx.min() - pad)
    max_x = min(arr.shape[1] - 1, x_idx.max() + pad)

    char_arr = arr[min_y:max_y+1, min_x:max_x+1]
    h, w, _ = char_arr.shape
    print(f"Cropped character block: {w}x{h}")

    # 2. Flood fill background starting from borders
    char_brightness = char_arr.mean(axis=2)
    diff = np.maximum.reduce([char_arr[:, :, 0], char_arr[:, :, 1], char_arr[:, :, 2]]) - np.minimum.reduce([char_arr[:, :, 0], char_arr[:, :, 1], char_arr[:, :, 2]])
    is_white_bg = (char_brightness > 235) & (diff < 25)

    labeled, num_features = ndi.label(is_white_bg)
    border_mask = np.zeros((h, w), dtype=bool)
    border_mask[0, :] = border_mask[-1, :] = border_mask[:, 0] = border_mask[:, -1] = True
    border_labels = np.unique(labeled[border_mask])
    border_labels = border_labels[border_labels > 0]

    bg_mask = np.isin(labeled, border_labels)

    # Check for cavity regions between arms / legs
    for lbl in range(1, num_features + 1):
        if lbl not in border_labels:
            m = labeled == lbl
            cy, cx = ndi.center_of_mass(m)
            # Eyes are inside head in upper third
            is_eye = (0.25 * h <= cy <= 0.60 * h) and (0.30 * w <= cx <= 0.70 * w)
            if not is_eye:
                print(f"Clearing cavity {lbl} at ({cx:.1f}, {cy:.1f})")
                bg_mask |= m

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
    rgba = Image.fromarray(np.dstack([char_arr.astype(np.uint8), alpha]), mode="RGBA")

    bbox = rgba.getbbox()
    if bbox:
        rgba = rgba.crop(bbox)

    # Scale to 138px height
    cw, ch = rgba.size
    target_h = 138
    scale = target_h / float(ch)
    nw, nh = max(1, int(cw * scale)), max(1, int(ch * scale))
    scaled = rgba.resize((nw, nh), Image.Resampling.LANCZOS if hasattr(Image, "Resampling") else Image.LANCZOS)
    scaled.save(OUT_CUTOUT, "PNG")
    print(f"Saved pristine Miles Morales cutout to {OUT_CUTOUT} (size: {scaled.size})")

if __name__ == "__main__":
    extract_clean_miles()
