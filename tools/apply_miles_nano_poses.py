from pathlib import Path
from PIL import Image
import numpy as np
import scipy.ndimage as ndi

SRC_DIR = Path(__file__).parent / "miles_sources"
OUT_SPRITES = Path(__file__).parent / "sprites" / "miles"

FRAME_SIZE = 192

def extract_cutout(img_path: Path, target_height: int = 140) -> Image.Image:
    img = Image.open(img_path).convert("RGB")
    w, h = img.size
    arr = np.array(img, dtype=np.float32)

    r, g, b = arr[:, :, 0], arr[:, :, 1], arr[:, :, 2]
    brightness = (r + g + b) / 3.0
    diff = np.maximum.reduce([r, g, b]) - np.minimum.reduce([r, g, b])
    is_white_bg = (brightness > 230) & (diff < 30)

    labeled, num_features = ndi.label(is_white_bg)
    border_mask = np.zeros((h, w), dtype=bool)
    border_mask[0, :] = border_mask[-1, :] = border_mask[:, 0] = border_mask[:, -1] = True
    border_labels = np.unique(labeled[border_mask])
    border_labels = border_labels[border_labels > 0]
    bg_mask = np.isin(labeled, border_labels)

    # Clear cavities outside the head (preserving white eye lenses)
    for lbl in range(1, num_features + 1):
        if lbl not in border_labels:
            m = labeled == lbl
            cy, cx = ndi.center_of_mass(m)
            is_eye = (0.20 * h <= cy <= 0.65 * h) and (0.22 * w <= cx <= 0.78 * w)
            if not is_eye and (cx < 0.20 * w or cx > 0.80 * w or cy > 0.80 * h or cy < 0.15 * h):
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
    rgba = Image.fromarray(np.dstack([arr.astype(np.uint8), alpha]), mode="RGBA")

    bbox = rgba.getbbox()
    if bbox:
        rgba = rgba.crop(bbox)

    cw, ch = rgba.size
    scale = target_height / float(ch)
    nw, nh = max(1, int(cw * scale)), max(1, int(ch * scale))
    return rgba.resize((nw, nh), Image.Resampling.LANCZOS if hasattr(Image, "Resampling") else Image.LANCZOS)


def place_on_canvas(img: Image.Image, ox_offset: int = 0, oy_offset: int = 0, align_bottom: bool = True) -> Image.Image:
    canvas = Image.new("RGBA", (FRAME_SIZE, FRAME_SIZE), (0, 0, 0, 0))
    nw, nh = img.size
    ox = (FRAME_SIZE - nw) // 2 + ox_offset
    if align_bottom:
        oy = FRAME_SIZE - nh - 8 + oy_offset
    else:
        oy = (FRAME_SIZE - nh) // 2 + oy_offset
    canvas.paste(img, (ox, oy), img)
    return canvas


def mirror(im: Image.Image) -> Image.Image:
    return im.transpose(Image.Transpose.FLIP_LEFT_RIGHT if hasattr(Image, "Transpose") else Image.FLIP_LEFT_RIGHT)


def create_strip(frames: list) -> Image.Image:
    h = frames[0].height
    w = sum(f.width for f in frames)
    strip = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    cx = 0
    for f in frames:
        strip.paste(f, (cx, 0), f)
        cx += f.width
    return strip


def update_miles_idle_and_walk():
    c_idle = extract_cutout(SRC_DIR / "miles_nano_idle_standing.png", 138)
    c_walk = extract_cutout(SRC_DIR / "miles_nano_walking_stride.png", 138)

    # 1. Idle
    idle_frames = [
        place_on_canvas(c_idle, 0, 0, align_bottom=True),
        place_on_canvas(c_idle, 0, -2, align_bottom=True),
        place_on_canvas(c_idle, 0, -3, align_bottom=True),
        place_on_canvas(c_idle, 0, -1, align_bottom=True),
    ]
    idle_f_frames = [mirror(f) for f in idle_frames]

    # 2. Walk Right & Walk Left
    c_walk_m = mirror(c_walk)
    walk_r_frames = [
        place_on_canvas(c_walk, 0, 0, align_bottom=True),
        place_on_canvas(c_idle, 0, -3, align_bottom=True),
        place_on_canvas(c_walk_m, 0, 0, align_bottom=True),
        place_on_canvas(c_idle, 0, -1, align_bottom=True),
    ]
    walk_l_frames = [mirror(f) for f in walk_r_frames]

    create_strip(idle_frames).save(OUT_SPRITES / "idle.png", "PNG")
    create_strip(idle_f_frames).save(OUT_SPRITES / "idle_flip.png", "PNG")
    create_strip(walk_r_frames).save(OUT_SPRITES / "walk_right.png", "PNG")
    create_strip(walk_l_frames).save(OUT_SPRITES / "walk_left.png", "PNG")

    # Update individual pose previews
    place_on_canvas(c_idle, 0, 0).save(SRC_DIR / "miles_pose_idle_standing.png")
    place_on_canvas(c_walk, 0, 0).save(SRC_DIR / "miles_pose_walking_stride.png")

    print("Updated Miles idle.png and walk_right.png / walk_left.png with new poses!")

if __name__ == "__main__":
    update_miles_idle_and_walk()
