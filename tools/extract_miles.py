from pathlib import Path
from PIL import Image
import numpy as np
import scipy.ndimage as ndi

SRC_PATH = Path(__file__).parent / "miles_sources" / "miles_raw.png"
OUT_CUTOUT = Path(__file__).parent / "miles_sources" / "miles_cutout.png"

def inspect_and_extract_miles():
    img = Image.open(SRC_PATH).convert("RGBA")
    w, h = img.size
    print(f"Miles raw size: {w}x{h}")
    arr = np.array(img, dtype=np.float32)

    # In miles_raw.png, background is white/light
    r, g, b, a = arr[:, :, 0], arr[:, :, 1], arr[:, :, 2], arr[:, :, 3]
    brightness = (r + g + b) / 3.0
    diff = np.maximum.reduce([r, g, b]) - np.minimum.reduce([r, g, b])
    
    is_white_bg = (brightness > 235) & (diff < 25)
    labeled, num_features = ndi.label(is_white_bg)
    print(f"Num white features: {num_features}")

    border_mask = np.zeros((h, w), dtype=bool)
    border_mask[0, :] = border_mask[-1, :] = border_mask[:, 0] = border_mask[:, -1] = True
    border_labels = np.unique(labeled[border_mask])
    border_labels = border_labels[border_labels > 0]
    print(f"Border labels: {border_labels}")

    bg_mask = np.isin(labeled, border_labels)

    # Clear cavities outside the head (preserving white eye lenses)
    for lbl in range(1, num_features + 1):
        if lbl not in border_labels:
            m = labeled == lbl
            cnt = np.sum(m)
            cy, cx = ndi.center_of_mass(m)
            # Eyes are in upper middle
            is_eye = (0.30 * h <= cy <= 0.60 * h) and (0.25 * w <= cx <= 0.75 * w)
            if not is_eye:
                print(f"Clearing cavity {lbl} at ({cx:.1f}, {cy:.1f}), size={cnt}")
                bg_mask |= m
            else:
                print(f"Preserving eye {lbl} at ({cx:.1f}, {cy:.1f}), size={cnt}")

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
    rgba = Image.fromarray(np.dstack([arr[:, :, :3].astype(np.uint8), alpha]), mode="RGBA")

    bbox = rgba.getbbox()
    print("Cutout bbox:", bbox)
    if bbox:
        cropped = rgba.crop(bbox)
    else:
        cropped = rgba

    cropped.save(OUT_CUTOUT, "PNG")
    print(f"Saved clean Miles cutout to {OUT_CUTOUT} (size: {cropped.size})")

if __name__ == "__main__":
    inspect_and_extract_miles()
