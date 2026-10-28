import math
import shutil
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
import scipy.ndimage as ndi

BRAIN_DIR = Path(r"C:\Users\alame\.gemini\antigravity-ide\brain\39d2fa9e-9b0d-4564-9852-7c140f8d8f57")
SRC_DIR = Path(__file__).parent / "spiderman_sources"
OUT_DIR = Path(__file__).parent / "sprites" / "spiderman"
OUT_DIR.mkdir(parents=True, exist_ok=True)

FRAME_SIZE = 192

# Pillow compatibility helpers
try:
    RESAMPLE_LANCZOS = Image.Resampling.LANCZOS
    RESAMPLE_BICUBIC = Image.Resampling.BICUBIC
    RESAMPLE_NEAREST = Image.Resampling.NEAREST
except AttributeError:
    RESAMPLE_LANCZOS = getattr(Image, "LANCZOS", getattr(Image, "ANTIALIAS", Image.BICUBIC))
    RESAMPLE_BICUBIC = Image.BICUBIC
    RESAMPLE_NEAREST = Image.NEAREST


def extract_cutout_from_image(img_path: Path, target_height: int = 140) -> Image.Image:
    """Extracts a transparent cutout from an AI-generated white-background sticker."""
    img = Image.open(img_path).convert("RGB")
    w, h = img.size
    arr = np.array(img, dtype=np.float32)

    r, g, b = arr[:, :, 0], arr[:, :, 1], arr[:, :, 2]
    brightness = (r + g + b) / 3.0
    diff = np.maximum.reduce([r, g, b]) - np.minimum.reduce([r, g, b])
    
    # White background sticker detection
    is_white_bg = (brightness > 230) & (diff < 30)

    labeled, num_features = ndi.label(is_white_bg)
    border_mask = np.zeros((h, w), dtype=bool)
    border_mask[0, :] = border_mask[-1, :] = border_mask[:, 0] = border_mask[:, -1] = True
    border_labels = np.unique(labeled[border_mask])
    border_labels = border_labels[border_labels > 0]

    bg_mask = np.isin(labeled, border_labels)

    # Clean small cavities outside the main head (preserving eyes)
    for lbl in range(1, num_features + 1):
        if lbl not in border_labels:
            m = labeled == lbl
            cy, cx = ndi.center_of_mass(m)
            # Eyes are typically in upper center
            is_eye = (0.20 * h <= cy <= 0.65 * h) and (0.22 * w <= cx <= 0.78 * w)
            # If it's a huge white area outside or between limbs, clear it
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
    return rgba.resize((nw, nh), RESAMPLE_LANCZOS)


def mirror_frame(frame: Image.Image) -> Image.Image:
    return frame.transpose(Image.Transpose.FLIP_LEFT_RIGHT if hasattr(Image, "Transpose") else Image.FLIP_LEFT_RIGHT)


def create_strip(frames: list) -> Image.Image:
    if not frames:
        return Image.new("RGBA", (FRAME_SIZE, FRAME_SIZE), (0, 0, 0, 0))
    h = frames[0].height
    w = sum(f.width for f in frames)
    strip = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    cx = 0
    for f in frames:
        strip.paste(f, (cx, 0), f)
        cx += f.width
    return strip


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


def compile_all():
    # Find latest generated images
    idle_img = list(BRAIN_DIR.glob("spidey_idle_standing_*.jpg"))[-1]
    walk_img = list(BRAIN_DIR.glob("spidey_walking_stride_*.jpg"))[-1]
    jump_img = list(BRAIN_DIR.glob("spidey_jump_leap_*.jpg"))[-1]
    fall_img = list(BRAIN_DIR.glob("spidey_fall_dive_*.jpg"))[-1]
    sleep_img = list(BRAIN_DIR.glob("spidey_sleep_pose_*.jpg"))[-1]
    work_img = list(BRAIN_DIR.glob("spidey_work_typing_*.jpg"))[-1]
    web_img = list(BRAIN_DIR.glob("spidey_web_blast_*.jpg"))[-1]
    sense_img = list(BRAIN_DIR.glob("spidey_spidey_sense_*.jpg"))[-1]
    happy_img = list(BRAIN_DIR.glob("spidey_happy_peace_*.jpg"))[-1]
    swing_img = SRC_DIR / "spiderman_raw.png"

    print("Extracting individual pose cutouts...")
    c_idle = extract_cutout_from_image(idle_img, 138)
    c_walk = extract_cutout_from_image(walk_img, 138)
    c_jump = extract_cutout_from_image(jump_img, 142)
    c_fall = extract_cutout_from_image(fall_img, 145)
    c_sleep = extract_cutout_from_image(sleep_img, 105)
    c_work = extract_cutout_from_image(work_img, 136)
    c_web = extract_cutout_from_image(web_img, 138)
    c_sense = extract_cutout_from_image(sense_img, 138)
    c_happy = extract_cutout_from_image(happy_img, 138)
    c_swing = extract_cutout_from_image(swing_img, 140)

    # 1. Idle animation (breathe/bob with standing pose)
    idle_frames = [
        place_on_canvas(c_idle, 0, 0, align_bottom=True),
        place_on_canvas(c_idle, 0, -2, align_bottom=True),
        place_on_canvas(c_idle, 0, -3, align_bottom=True),
        place_on_canvas(c_idle, 0, -1, align_bottom=True),
    ]
    idle_f_frames = [mirror_frame(f) for f in idle_frames]

    # 2. Walk Right & Left (alternating walk stride and standing contact)
    c_walk_m = mirror_frame(c_walk)
    walk_r_frames = [
        place_on_canvas(c_walk, 0, 0, align_bottom=True),
        place_on_canvas(c_idle, 0, -3, align_bottom=True),
        place_on_canvas(c_walk_m, 0, 0, align_bottom=True),
        place_on_canvas(c_idle, 0, -1, align_bottom=True),
    ]
    walk_l_frames = [mirror_frame(f) for f in walk_r_frames]

    # 3. Jump (crouch launch -> aerial leap -> apex)
    jump_frames = [
        place_on_canvas(c_idle, 0, 6, align_bottom=True),
        place_on_canvas(c_jump, 0, -18, align_bottom=False),
        place_on_canvas(c_jump, 0, -36, align_bottom=False),
        place_on_canvas(c_jump, 0, -12, align_bottom=False),
    ]

    # 4. Fall (diving down)
    fall_frames = [
        place_on_canvas(c_fall, 0, -10, align_bottom=False),
        place_on_canvas(c_fall, 0, 0, align_bottom=False),
        place_on_canvas(c_fall, 0, 10, align_bottom=False),
        place_on_canvas(c_fall, 0, 20, align_bottom=False),
    ]

    # 5. Land
    land_frames = [
        place_on_canvas(c_idle, 0, 10, align_bottom=True),
        place_on_canvas(c_idle, 0, 4, align_bottom=True),
        place_on_canvas(c_idle, 0, 0, align_bottom=True),
        place_on_canvas(c_idle, 0, 0, align_bottom=True),
    ]

    # 6. Drag (Web swing dangling pose)
    drag_frames = [
        place_on_canvas(c_swing.rotate(-4, resample=RESAMPLE_BICUBIC, expand=True), 0, 4, align_bottom=False),
        place_on_canvas(c_swing, 0, 4, align_bottom=False),
        place_on_canvas(c_swing.rotate(4, resample=RESAMPLE_BICUBIC, expand=True), 0, 4, align_bottom=False),
        place_on_canvas(c_swing, 0, 4, align_bottom=False),
    ]

    # 7. Sleep & Wake
    sleep_frames = [
        place_on_canvas(c_sleep, 0, 0, align_bottom=True),
        place_on_canvas(c_sleep, 0, 2, align_bottom=True),
        place_on_canvas(c_sleep, 0, 0, align_bottom=True),
        place_on_canvas(c_sleep, 0, 2, align_bottom=True),
    ]
    wake_frames = [
        place_on_canvas(c_sleep, 0, 0, align_bottom=True),
        place_on_canvas(c_idle, 0, 8, align_bottom=True),
        place_on_canvas(c_idle, 0, 0, align_bottom=True),
        place_on_canvas(c_happy, 0, -4, align_bottom=True),
    ]

    # 8. Work (Typing on laptop)
    work_frames = [
        place_on_canvas(c_work, 0, 0, align_bottom=True),
        place_on_canvas(c_work, 0, -2, align_bottom=True),
        place_on_canvas(c_work, 0, 0, align_bottom=True),
        place_on_canvas(c_work, 0, -2, align_bottom=True),
    ]

    # 9. Idea (Spidey-Sense tingling!)
    idea_frames = [
        place_on_canvas(c_sense, 0, 0, align_bottom=True),
        place_on_canvas(c_sense, 0, -2, align_bottom=True),
        place_on_canvas(c_sense, 0, 0, align_bottom=True),
        place_on_canvas(c_sense, 0, -2, align_bottom=True),
    ]

    # 10. Happy (Double peace sign)
    happy_frames = [
        place_on_canvas(c_happy, 0, 0, align_bottom=True),
        place_on_canvas(c_happy, 0, -3, align_bottom=True),
        place_on_canvas(c_happy, 0, 0, align_bottom=True),
        place_on_canvas(c_happy, 0, -3, align_bottom=True),
    ]

    # 11. Roar / Web-Shooter Blast
    roar_frames = [
        place_on_canvas(c_idle, 0, 0, align_bottom=True),
        place_on_canvas(c_web, 0, 0, align_bottom=True),
        place_on_canvas(c_web, 0, -2, align_bottom=True),
        place_on_canvas(c_web, 0, 0, align_bottom=True),
        place_on_canvas(c_web, 0, -2, align_bottom=True),
        place_on_canvas(c_idle, 0, 0, align_bottom=True),
    ]

    # 12. Sit & Shrug & Blink & Eat & Music
    sit_frames = [
        place_on_canvas(c_sleep, 0, 4, align_bottom=True),
        place_on_canvas(c_sleep, 0, 2, align_bottom=True),
        place_on_canvas(c_sleep, 0, 4, align_bottom=True),
        place_on_canvas(c_sleep, 0, 2, align_bottom=True),
    ]
    shrug_frames = [
        place_on_canvas(c_happy, 0, 0, align_bottom=True),
        place_on_canvas(c_idle, 0, 0, align_bottom=True),
        place_on_canvas(c_happy, 0, 0, align_bottom=True),
        place_on_canvas(c_idle, 0, 0, align_bottom=True),
    ]
    blink_frames = [
        place_on_canvas(c_idle, 0, 0, align_bottom=True),
        place_on_canvas(c_sense, 0, 0, align_bottom=True),
        place_on_canvas(c_sense, 0, 0, align_bottom=True),
        place_on_canvas(c_idle, 0, 0, align_bottom=True),
    ]
    cry_frames = [
        place_on_canvas(c_sleep, 0, 0, align_bottom=True),
        place_on_canvas(c_sleep, 0, 2, align_bottom=True),
        place_on_canvas(c_sleep, 0, 0, align_bottom=True),
        place_on_canvas(c_sleep, 0, 2, align_bottom=True),
    ]
    sad_frames = cry_frames
    music_frames = [
        place_on_canvas(c_happy, 0, -3, align_bottom=True),
        place_on_canvas(c_idle, 0, 1, align_bottom=True),
        place_on_canvas(c_happy, 0, -3, align_bottom=True),
        place_on_canvas(c_idle, 0, 1, align_bottom=True),
    ]
    eat_frames = [
        place_on_canvas(c_work, 0, 0, align_bottom=True),
        place_on_canvas(c_work, 0, -2, align_bottom=True),
        place_on_canvas(c_work, 0, 0, align_bottom=True),
        place_on_canvas(c_work, 0, -2, align_bottom=True),
    ]

    anims = {
        "idle": idle_frames,
        "idle_flip": idle_f_frames,
        "walk_right": walk_r_frames,
        "walk_left": walk_l_frames,
        "jump": jump_frames,
        "fall": fall_frames,
        "land": land_frames,
        "drag": drag_frames,
        "sleep": sleep_frames,
        "wake": wake_frames,
        "work": work_frames,
        "idea": idea_frames,
        "happy": happy_frames,
        "roar": roar_frames,
        "sit": sit_frames,
        "shrug": shrug_frames,
        "blink": blink_frames,
        "cry": cry_frames,
        "sad": sad_frames,
        "music": music_frames,
        "eat": eat_frames,
    }

    print("\nSaving compiled sprite strips to assets/sprites/spiderman/:")
    for name, frames in anims.items():
        strip = create_strip(frames)
        dest = OUT_DIR / f"{name}.png"
        strip.save(dest, "PNG")
        print(f"  [SAVED] {name}.png ({len(frames)} frames, {strip.width}x{strip.height})")


if __name__ == "__main__":
    compile_all()
