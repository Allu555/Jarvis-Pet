from pathlib import Path
from PIL import Image, ImageDraw
import numpy as np
import scipy.ndimage as ndi

BASE_DIR = Path(__file__).parent.parent
SRC_DIR = Path(__file__).parent / "jcb_sources"
OUT_DIR = Path(__file__).parent / "sprites" / "jcb"
OUT_DIR.mkdir(parents=True, exist_ok=True)

FRAME_SIZE = 192

try:
    RESAMPLE_LANCZOS = Image.Resampling.LANCZOS
    RESAMPLE_BICUBIC = Image.Resampling.BICUBIC
except AttributeError:
    RESAMPLE_LANCZOS = getattr(Image, "LANCZOS", getattr(Image, "ANTIALIAS", Image.BICUBIC))
    RESAMPLE_BICUBIC = Image.BICUBIC


def clean_white_sheet(im: Image.Image) -> Image.Image:
    arr = np.array(im.convert("RGBA"))
    r, g, b = arr[:, :, 0].astype(int), arr[:, :, 1].astype(int), arr[:, :, 2].astype(int)
    is_white = (r > 240) & (g > 240) & (b > 240)
    
    labeled, _ = ndi.label(is_white)
    border_mask = np.zeros_like(is_white, dtype=bool)
    border_mask[0, :] = border_mask[-1, :] = border_mask[:, 0] = border_mask[:, -1] = True
    border_labels = np.unique(labeled[border_mask & is_white])
    bg_mask = np.isin(labeled, border_labels)
    
    dist = ndi.distance_transform_edt(bg_mask)
    alpha = np.clip((dist - 0.5) * 255.0, 0, 255).astype(np.uint8)
    alpha = 255 - alpha
    return Image.fromarray(np.dstack([arr[:, :, :3], alpha]), mode="RGBA")


def extract_components_sorted(sheet_path: Path, target_size: int = FRAME_SIZE):
    im = Image.open(sheet_path)
    clean = clean_white_sheet(im)
    arr = np.array(clean)
    alpha = arr[:, :, 3] > 40
    
    labeled, num_features = ndi.label(alpha)
    objects = ndi.find_objects(labeled)
    
    comps = []
    for o_idx, obj in enumerate(objects):
        mask = (labeled[obj] == (o_idx + 1))
        area = np.sum(mask)
        if area > 4000:
            y_slice, x_slice = obj
            comps.append((x_slice.start, x_slice.stop, y_slice.start, y_slice.stop, area))
            
    # Sort top-to-bottom, then left-to-right
    comps.sort(key=lambda c: (c[2] // 300, c[0]))
    
    frames = []
    for x0, x1, y0, y1, area in comps:
        pad = 2
        crop_box = (
            max(0, x0 - pad),
            max(0, y0 - pad),
            min(arr.shape[1], x1 + pad + 1),
            min(arr.shape[0], y1 + pad + 1)
        )
        char_crop = clean.crop(crop_box)
        cw, ch = char_crop.size
        scale = (target_size - 16) / max(cw, ch)
        nw, nh = max(1, int(cw * scale)), max(1, int(ch * scale))
        scaled = char_crop.resize((nw, nh), RESAMPLE_LANCZOS)
        
        canvas = Image.new("RGBA", (target_size, target_size), (0, 0, 0, 0))
        ox = (target_size - nw) // 2
        oy = target_size - nh - 6
        canvas.paste(scaled, (ox, oy), scaled)
        frames.append(canvas)
    return frames


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


def add_zzz_overlay(frame: Image.Image, level: int) -> Image.Image:
    f = frame.copy()
    draw = ImageDraw.Draw(f)
    if level >= 1:
        draw.text((130, 45), "z", fill=(255, 220, 100, 220))
    if level >= 2:
        draw.text((145, 25), "z", fill=(255, 200, 70, 230))
    if level >= 3:
        draw.text((160, 8), "Z", fill=(255, 180, 40, 245))
    return f


def draw_music_note(draw: ImageDraw.ImageDraw, x: int, y: int, fill: tuple):
    draw.ellipse([x, y + 10, x + 8, y + 16], fill=fill)
    draw.line([(x + 7, y), (x + 7, y + 13)], fill=fill, width=2)
    draw.line([(x + 7, y), (x + 13, y + 4)], fill=fill, width=2)


def add_music_notes(frame: Image.Image, frame_idx: int) -> Image.Image:
    f = frame.copy()
    draw = ImageDraw.Draw(f)
    notes = [
        [(25, 40, (255, 215, 0, 240)), (145, 30, (255, 140, 0, 240))],
        [(35, 25, (0, 220, 255, 240)), (155, 45, (255, 215, 0, 240))],
        [(20, 50, (255, 80, 80, 240)), (140, 20, (0, 255, 150, 240))],
        [(40, 30, (255, 215, 0, 240)), (150, 55, (255, 100, 220, 240))],
    ]
    for nx, ny, col in notes[frame_idx % len(notes)]:
        draw_music_note(draw, nx, ny, col)
    return f


def generate_all_jcb_sprites():
    wc = extract_components_sorted(SRC_DIR / "walk_cycle.jpg")
    p1 = extract_components_sorted(SRC_DIR / "sheet_1.jpg")
    p2 = extract_components_sorted(SRC_DIR / "sheet_2.jpg")
    p3 = extract_components_sorted(SRC_DIR / "sheet_3.jpg")

    # Smooth drive cycle
    walk_r = [wc[0], wc[1], wc[3], wc[4], wc[2]]
    # Ensure walk_right faces right (the source faces right)
    walk_l = [mirror_frame(f) for f in walk_r]

    # Idle states
    idle = [p1[0], p1[0], p1[0], p1[0]]
    idle_f = [mirror_frame(f) for f in idle]
    
    # Emotes and actions
    blink = [p1[0], p1[0], p1[0], p1[0]]
    happy = [p1[2], p1[2], p1[5], p1[2]]
    idea = [p2[2], p2[2], p2[2], p1[0]]
    work = [p1[1], p1[4], p1[1], p1[4]]
    sit = [p2[5], p2[5], p2[5], p2[5]]
    
    sleep_base = p2[0]
    sleep = [add_zzz_overlay(sleep_base, i) for i in range(4)]
    wake = [p3[5], p3[5], p3[5], p1[0]]
    
    cry = [p2[4], p2[4], p2[4], p2[4]]
    sad = [p2[4], p2[4], p2[4], p1[0]]
    shrug = [p3[3], p3[3], p3[3], p1[0]]
    jump = [p2[1], p2[1], p2[1], p1[0]]
    roar = [p2[3], p2[3], p2[3], p1[0]]
    drag = [p3[0], p3[0], p3[0], p3[0]]
    fall = [p3[1], p3[1], p3[1], p3[1]]
    land = [p3[2], p3[2], p1[0], p1[0]]
    
    music_base = [p3[4], p3[4], p2[1], p3[4]]
    music = [add_music_notes(f, i) for i, f in enumerate(music_base)]

    anims = {
        "walk_right": walk_r,
        "walk_left": walk_l,
        "idle": idle,
        "idle_flip": idle_f,
        "blink": blink,
        "happy": happy,
        "idea": idea,
        "work": work,
        "sit": sit,
        "sleep": sleep,
        "wake": wake,
        "cry": cry,
        "sad": sad,
        "shrug": shrug,
        "jump": jump,
        "roar": roar,
        "drag": drag,
        "fall": fall,
        "land": land,
        "music": music,
    }

    print("Generating JCB sprite sheets in assets/sprites/jcb/:")
    for name, frames in anims.items():
        strip = create_strip(frames)
        dest = OUT_DIR / f"{name}.png"
        strip.save(dest)
        print(f"  [SAVED] {name}.png ({len(frames)} frames, {strip.width}x{strip.height})")


if __name__ == "__main__":
    generate_all_jcb_sprites()
