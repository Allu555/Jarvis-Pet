from pathlib import Path
from PIL import Image, ImageDraw
import numpy as np
import scipy.ndimage as ndi
import math

BASE_DIR = Path(__file__).parent.parent
SRC_DIR = Path(__file__).parent / "cat_sources"
OUT_DIR = Path(__file__).parent / "sprites" / "drip_cat"
OUT_DIR.mkdir(parents=True, exist_ok=True)

FRAME_SIZE = 192

try:
    RESAMPLE_LANCZOS = Image.Resampling.LANCZOS
    RESAMPLE_BICUBIC = Image.Resampling.BICUBIC
    RESAMPLE_BILINEAR = Image.Resampling.BILINEAR
except AttributeError:
    RESAMPLE_LANCZOS = getattr(Image, "LANCZOS", getattr(Image, "ANTIALIAS", Image.BICUBIC))
    RESAMPLE_BICUBIC = Image.BICUBIC
    RESAMPLE_BILINEAR = Image.BILINEAR


def extract_cat_walk_frames(sheet_path: Path, target_size: int = FRAME_SIZE) -> list:
    im = Image.open(sheet_path).convert("RGBA")
    arr = np.array(im)

    boxes = [
        (38, 287, 263, 504),
        (300, 550, 263, 504),
        (563, 813, 263, 504),
        (826, 1076, 263, 504),
        (1089, 1338, 263, 504),
    ]

    frames = []
    for x0, x1, y0, y1 in boxes:
        inner = arr[y0 + 4:y1 - 4, x0 + 4:x1 - 4]
        r, g, b = inner[:, :, 0].astype(int), inner[:, :, 1].astype(int), inner[:, :, 2].astype(int)
        is_white = (r > 240) & (g > 240) & (b > 240)

        labeled_bg, _ = ndi.label(is_white)
        border_mask = np.zeros_like(is_white, dtype=bool)
        border_mask[0, :] = border_mask[-1, :] = border_mask[:, 0] = border_mask[:, -1] = True
        border_labels = np.unique(labeled_bg[border_mask & is_white])
        bg_mask = np.isin(labeled_bg, border_labels)

        dist = ndi.distance_transform_edt(bg_mask)
        alpha = np.clip((dist - 0.5) * 255.0, 0, 255).astype(np.uint8)
        alpha = 255 - alpha
        clean_inner = Image.fromarray(np.dstack([inner[:, :, :3], alpha]), mode="RGBA")

        fg_mask = alpha > 20
        ys, xs = np.where(fg_mask)
        if len(xs) > 0:
            crop_box = (xs.min(), ys.min(), xs.max() + 1, ys.max() + 1)
            char_crop = clean_inner.crop(crop_box)
        else:
            char_crop = clean_inner

        cw, ch = char_crop.size
        scale = (target_size - 32) / max(cw, ch)
        nw, nh = max(1, int(cw * scale)), max(1, int(ch * scale))
        scaled = char_crop.resize((nw, nh), RESAMPLE_LANCZOS)

        canvas = Image.new("RGBA", (target_size, target_size), (0, 0, 0, 0))
        ox = (target_size - nw) // 2
        oy = target_size - nh - 10
        canvas.paste(scaled, (ox, oy), scaled)
        frames.append(canvas)

    return frames


def get_raw_cat(sheet_path: Path) -> Image.Image:
    im = Image.open(sheet_path).convert("RGBA")
    arr = np.array(im)
    x0, x1, y0, y1 = 38, 287, 263, 504
    inner = arr[y0 + 4:y1 - 4, x0 + 4:x1 - 4]
    r, g, b = inner[:, :, 0].astype(int), inner[:, :, 1].astype(int), inner[:, :, 2].astype(int)
    is_white = (r > 240) & (g > 240) & (b > 240)
    labeled_bg, _ = ndi.label(is_white)
    border_mask = np.zeros_like(is_white, dtype=bool)
    border_mask[0, :] = border_mask[-1, :] = border_mask[:, 0] = border_mask[:, -1] = True
    border_labels = np.unique(labeled_bg[border_mask & is_white])
    bg_mask = np.isin(labeled_bg, border_labels)
    dist = ndi.distance_transform_edt(bg_mask)
    alpha = np.clip((dist - 0.5) * 255.0, 0, 255).astype(np.uint8)
    alpha = 255 - alpha
    clean = Image.fromarray(np.dstack([inner[:, :, :3], alpha]), mode="RGBA")
    ys, xs = np.where(alpha > 20)
    return clean.crop((xs.min(), ys.min(), xs.max() + 1, ys.max() + 1))


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


# ── Vector Effect Helpers ─────────────────────────────────────────────────────

def draw_star(draw: ImageDraw.ImageDraw, cx: float, cy: float, r: float, fill: tuple):
    """Draws a 4-pointed golden sparkle star."""
    points = [
        (cx, cy - r),
        (cx + r * 0.28, cy - r * 0.28),
        (cx + r, cy),
        (cx + r * 0.28, cy + r * 0.28),
        (cx, cy + r),
        (cx - r * 0.28, cy + r * 0.28),
        (cx - r, cy),
        (cx - r * 0.28, cy - r * 0.28),
    ]
    draw.polygon(points, fill=fill)


def draw_lightbulb(draw: ImageDraw.ImageDraw, cx: int, cy: int):
    """Draws a glowing eureka lightbulb with radiating rays."""
    # Rays
    for ang in range(0, 360, 45):
        rad = math.radians(ang)
        x1 = cx + math.cos(rad) * 16
        y1 = cy + math.sin(rad) * 16
        x2 = cx + math.cos(rad) * 25
        y2 = cy + math.sin(rad) * 25
        draw.line([(x1, y1), (x2, y2)], fill=(255, 235, 80, 220), width=2)
    # Bulb glow
    draw.ellipse([cx - 12, cy - 12, cx + 12, cy + 12], fill=(255, 225, 30, 255), outline=(255, 180, 0, 255), width=2)
    # Base
    draw.rectangle([cx - 5, cy + 10, cx + 5, cy + 16], fill=(180, 180, 190, 255))


def draw_dust_puff(draw: ImageDraw.ImageDraw, cx: int, cy: int, r: int):
    """Draws cartoon dust impact puffs."""
    draw.ellipse([cx - r, cy - r // 2, cx + r, cy + r // 2], fill=(235, 235, 240, 210))
    draw.ellipse([cx - r // 2, cy - r, cx + r // 2, cy], fill=(245, 245, 250, 230))


def draw_teardrop(draw: ImageDraw.ImageDraw, cx: int, cy: int):
    """Draws a glossy teardrop."""
    draw.ellipse([cx - 4, cy - 2, cx + 4, cy + 8], fill=(0, 190, 255, 240))
    draw.polygon([(cx, cy - 8), (cx - 4, cy), (cx + 4, cy)], fill=(0, 190, 255, 240))


def draw_heart(draw: ImageDraw.ImageDraw, x: int, y: int, r: int = 6, fill: tuple = (255, 100, 150, 240)):
    draw.ellipse([x - r, y - r, x, y + r], fill=fill)
    draw.ellipse([x, y - r, x + r, y + r], fill=fill)
    draw.polygon([(x - r, y), (x + r, y), (x, y + r + 4)], fill=fill)


def draw_music_note(draw: ImageDraw.ImageDraw, x: int, y: int, fill: tuple):
    draw.ellipse([x, y + 10, x + 8, y + 16], fill=fill)
    draw.line([(x + 7, y), (x + 7, y + 13)], fill=fill, width=2)
    draw.line([(x + 7, y), (x + 13, y + 4)], fill=fill, width=2)


# ── Specialized Cat Poses ─────────────────────────────────────────────────────

def create_cat_drag_frames(raw_cat: Image.Image) -> list:
    """Authentic cat dangling by scruff: relaxed elongated body with natural gentle sway."""
    cw, ch = raw_cat.size
    target_size = FRAME_SIZE
    
    # Scale to a naturally elongated dangling posture
    drag_w = int(cw * 0.85)
    drag_h = int(ch * 1.08)
    dangle_base = raw_cat.resize((drag_w, drag_h), RESAMPLE_LANCZOS)
    scale = (target_size - 38) / drag_h
    nw = int(drag_w * scale)
    nh = int(drag_h * scale)
    scaled = dangle_base.resize((nw, nh), RESAMPLE_LANCZOS)

    # Gentle pendulum sway angles around the scruff grab point
    angles = [-3, 0, 3, 0]
    frames = []
    for ang in angles:
        canvas = Image.new("RGBA", (target_size, target_size), (0, 0, 0, 0))
        rot = scaled.rotate(ang, resample=RESAMPLE_BICUBIC, expand=True)
        rw, rh = rot.size
        ox = (target_size - rw) // 2
        oy = (target_size - nh) // 2
        canvas.paste(rot, (ox, oy), rot)

        draw = ImageDraw.Draw(canvas)
        # Small cute pinch wrinkle mark at top of hoodie
        top_cx = target_size // 2
        top_cy = oy + 12
        draw.arc([top_cx - 8, top_cy - 4, top_cx + 8, top_cy + 4], start=180, end=360, fill=(40, 40, 50, 200), width=2)
        
        frames.append(canvas)
    return frames


def create_cat_sleep_frames(raw_cat: Image.Image) -> list:
    """Curled-up sleeping cat loaf with gentle breathing and rising Zzzs."""
    cw, ch = raw_cat.size
    target_size = FRAME_SIZE
    
    # Scale into a relaxed sleeping loaf
    loaf_w = int(cw * 0.95)
    loaf_h = int(ch * 0.55)
    loaf = raw_cat.resize((loaf_w, loaf_h), RESAMPLE_LANCZOS)
    
    scale = (target_size - 40) / loaf_w
    nw = int(loaf_w * scale)
    nh = int(loaf_h * scale)
    scaled_loaf = loaf.resize((nw, nh), RESAMPLE_LANCZOS)

    zzz_positions = [
        [(135, 80, "z", 200)],
        [(133, 65, "z", 220), (148, 48, "z", 190)],
        [(130, 50, "z", 230), (145, 32, "Z", 210), (160, 18, "z", 170)],
        [(128, 40, "z", 240), (142, 22, "Z", 230), (158, 8, "Z", 200)],
    ]

    frames = []
    for i, z_list in enumerate(zzz_positions):
        canvas = Image.new("RGBA", (target_size, target_size), (0, 0, 0, 0))
        # Gentle breathing pulse
        breath_dh = 2 if (i % 2 == 1) else 0
        cur_nh = nh + breath_dh
        cur_loaf = scaled_loaf.resize((nw, cur_nh), RESAMPLE_BILINEAR)
        
        ox = (target_size - nw) // 2
        oy = target_size - cur_nh - 12
        canvas.paste(cur_loaf, (ox, oy), cur_loaf)

        draw = ImageDraw.Draw(canvas)
        # Sleepy closed eyes curve on sunglasses
        draw.arc([ox + nw - 52, oy + 8, ox + nw - 36, oy + 24], start=0, end=180, fill=(255, 215, 0, 240), width=2)
        draw.arc([ox + nw - 32, oy + 8, ox + nw - 16, oy + 24], start=0, end=180, fill=(255, 215, 0, 240), width=2)
        
        # Rising glowing Zzz
        for zx, zy, ztxt, alpha in z_list:
            draw.text((zx, zy), ztxt, fill=(255, 220, 100, alpha))
            
        frames.append(canvas)
    return frames


def create_cat_fall_frames(raw_cat: Image.Image) -> list:
    """Skydiving cat falling downwards with wind speed lines."""
    cw, ch = raw_cat.size
    scale = (FRAME_SIZE - 40) / max(cw, ch)
    nw = int(cw * scale)
    nh = int(ch * scale)
    scaled = raw_cat.resize((nw, nh), RESAMPLE_LANCZOS)

    dived = scaled.rotate(-28, resample=RESAMPLE_BICUBIC, expand=True)
    rw, rh = dived.size

    frames = []
    for i in range(4):
        canvas = Image.new("RGBA", (FRAME_SIZE, FRAME_SIZE), (0, 0, 0, 0))
        ox = (FRAME_SIZE - rw) // 2
        oy = (FRAME_SIZE - rh) // 2 + (i * 4)
        canvas.paste(dived, (ox, oy), dived)

        draw = ImageDraw.Draw(canvas)
        # Wind streaks rushing upward
        wind_lines = [
            (35, 160 - i * 15, 35, 70 - i * 15),
            (70, 175 - i * 15, 70, 90 - i * 15),
            (145, 150 - i * 15, 145, 60 - i * 15),
            (170, 180 - i * 15, 170, 95 - i * 15),
        ]
        for x1, y1, x2, y2 in wind_lines:
            y1_mod = (y1 % 160) + 10
            y2_mod = max(5, y1_mod - 40)
            draw.line([(x1, y1_mod), (x2, y2_mod)], fill=(200, 230, 255, 180), width=2)
            
        frames.append(canvas)
    return frames


def create_cat_jump_frames(raw_cat: Image.Image) -> list:
    """Realistic 4-stage feline pounce & acrobatic leap."""
    cw, ch = raw_cat.size
    scale = (FRAME_SIZE - 40) / max(cw, ch)
    nw = int(cw * scale)
    nh = int(ch * scale)
    base = raw_cat.resize((nw, nh), RESAMPLE_LANCZOS)

    # Frame 0: Crouch compression
    crouch_w = int(nw * 1.15)
    crouch_h = int(nh * 0.70)
    crouch = base.resize((crouch_w, crouch_h), RESAMPLE_LANCZOS)
    f0 = Image.new("RGBA", (FRAME_SIZE, FRAME_SIZE), (0, 0, 0, 0))
    f0.paste(crouch, ((FRAME_SIZE - crouch_w) // 2, FRAME_SIZE - crouch_h - 10), crouch)

    # Frame 1: Upward launch extension
    launch_w = int(nw * 0.9)
    launch_h = int(nh * 1.15)
    launch = base.resize((launch_w, launch_h), RESAMPLE_LANCZOS).rotate(20, resample=RESAMPLE_BICUBIC, expand=True)
    lw, lh = launch.size
    f1 = Image.new("RGBA", (FRAME_SIZE, FRAME_SIZE), (0, 0, 0, 0))
    f1.paste(launch, ((FRAME_SIZE - lw) // 2, 25), launch)
    draw1 = ImageDraw.Draw(f1)
    draw_dust_puff(draw1, 40, 150, 10)

    # Frame 2: Apex leap arch
    apex = base.rotate(5, resample=RESAMPLE_BICUBIC, expand=True)
    aw, ah = apex.size
    f2 = Image.new("RGBA", (FRAME_SIZE, FRAME_SIZE), (0, 0, 0, 0))
    f2.paste(apex, ((FRAME_SIZE - aw) // 2, 10), apex)
    draw2 = ImageDraw.Draw(f2)
    draw_star(draw2, 145, 25, 8, (255, 215, 0, 240))

    # Frame 3: Touchdown descent
    desc = base.rotate(-15, resample=RESAMPLE_BICUBIC, expand=True)
    dw, dh = desc.size
    f3 = Image.new("RGBA", (FRAME_SIZE, FRAME_SIZE), (0, 0, 0, 0))
    f3.paste(desc, ((FRAME_SIZE - dw) // 2, FRAME_SIZE - dh - 20), desc)

    return [f0, f1, f2, f3]


def create_cat_land_frames(raw_cat: Image.Image) -> list:
    """Smooth 4-paw landing impact with dust puffs."""
    cw, ch = raw_cat.size
    scale = (FRAME_SIZE - 36) / max(cw, ch)
    nw = int(cw * scale)
    nh = int(ch * scale)
    base = raw_cat.resize((nw, nh), RESAMPLE_LANCZOS)

    # Frame 0: Impact squash + dust puffs
    sq_w = int(nw * 1.20)
    sq_h = int(nh * 0.75)
    squash = base.resize((sq_w, sq_h), RESAMPLE_LANCZOS)
    f0 = Image.new("RGBA", (FRAME_SIZE, FRAME_SIZE), (0, 0, 0, 0))
    f0.paste(squash, ((FRAME_SIZE - sq_w) // 2, FRAME_SIZE - sq_h - 10), squash)
    draw0 = ImageDraw.Draw(f0)
    draw_dust_puff(draw0, 25, 160, 14)
    draw_dust_puff(draw0, 165, 160, 14)

    # Frame 1: Rebound
    f1 = Image.new("RGBA", (FRAME_SIZE, FRAME_SIZE), (0, 0, 0, 0))
    f1.paste(base, ((FRAME_SIZE - nw) // 2, FRAME_SIZE - nh - 10), base)
    draw1 = ImageDraw.Draw(f1)
    draw_star(draw1, 35, 150, 6, (255, 215, 0, 200))

    # Frames 2 & 3: Normal stance
    f2 = Image.new("RGBA", (FRAME_SIZE, FRAME_SIZE), (0, 0, 0, 0))
    f2.paste(base, ((FRAME_SIZE - nw) // 2, FRAME_SIZE - nh - 10), base)
    f3 = f2.copy()

    return [f0, f1, f2, f3]


def create_cat_eat_frames(raw_cat: Image.Image) -> list:
    """Cat eating yummy tuna fish from a golden bowl with hearts."""
    cw, ch = raw_cat.size
    scale = (FRAME_SIZE - 40) / max(cw, ch)
    nw = int(cw * scale)
    nh = int(ch * scale)
    base = raw_cat.resize((nw, nh), RESAMPLE_LANCZOS)

    frames = []
    bobs = [0, 4, 0, 4]
    for i, bob in enumerate(bobs):
        canvas = Image.new("RGBA", (FRAME_SIZE, FRAME_SIZE), (0, 0, 0, 0))
        ox = ((FRAME_SIZE - nw) // 2) - 10
        oy = FRAME_SIZE - nh - 10 + bob
        canvas.paste(base, (ox, oy), base)

        draw = ImageDraw.Draw(canvas)
        # Golden Food Bowl
        bx0, by0, bx1, by1 = 125, 150, 175, 172
        draw.ellipse([bx0, by0, bx1, by1], fill=(240, 190, 40, 255), outline=(180, 130, 20, 255), width=2)
        # Fish in bowl
        fx0, fy0, fx1, fy1 = 135, 142, 165, 158
        draw.ellipse([fx0, fy0, fx1, fy1], fill=(0, 190, 255, 255))
        draw.polygon([(fx0, fy0 + 8), (fx0 - 6, fy0 + 2), (fx0 - 6, fy0 + 14)], fill=(0, 170, 240, 255))

        # Floating Hearts and Sparkles
        if i % 2 == 1:
            draw_star(draw, 120, 125, 6, (255, 220, 0, 240))
            draw_heart(draw, 140, 105, 6, (255, 80, 130, 240))
        else:
            draw_star(draw, 165, 130, 6, (255, 220, 0, 240))
            draw_heart(draw, 148, 115, 6, (255, 100, 150, 240))
            
        frames.append(canvas)
    return frames


# ── Full Generator ────────────────────────────────────────────────────────────

def generate_all_cat_sprites():
    walk_frames = extract_cat_walk_frames(SRC_DIR / "walk_cycle.jpg")
    raw_cat = get_raw_cat(SRC_DIR / "walk_cycle.jpg")
    p0, p1, p2, p3, p4 = walk_frames

    # Smooth 5-frame walk cycle
    walk_r = [p0, p1, p2, p3, p4]
    walk_l = [mirror_frame(f) for f in walk_r]

    # Idle states
    idle = [p0, p1, p0, p1]
    idle_f = [mirror_frame(f) for f in idle]

    # Specialized states
    sleep = create_cat_sleep_frames(raw_cat)
    drag = create_cat_drag_frames(raw_cat)
    fall = create_cat_fall_frames(raw_cat)
    jump = create_cat_jump_frames(raw_cat)
    land = create_cat_land_frames(raw_cat)
    work = create_cat_eat_frames(raw_cat)

    # Emotes
    blink = [p0, p0, p0, p0]
    
    # Happy pose with gold sparkle stars
    f_happy = p2.copy()
    draw_h = ImageDraw.Draw(f_happy)
    draw_star(draw_h, 30, 35, 10, (255, 215, 0, 240))
    draw_star(draw_h, 155, 30, 10, (255, 215, 0, 240))
    draw_star(draw_h, 140, 75, 7, (255, 230, 80, 240))
    happy = [f_happy, p2, f_happy, p2]

    # Idea pose with vector lightbulb
    f_idea = p1.copy()
    draw_i = ImageDraw.Draw(f_idea)
    draw_lightbulb(draw_i, 130, 35)
    idea = [f_idea, f_idea, p1, p0]

    # Wake pose
    wake = [sleep[0], p0, f_happy, p0]

    # Cry & sad with teardrops
    f_cry = p0.copy()
    draw_c = ImageDraw.Draw(f_cry)
    draw_teardrop(draw_c, 130, 90)
    draw_teardrop(draw_c, 142, 110)
    cry = [f_cry, f_cry, f_cry, f_cry]
    sad = [f_cry, p0, f_cry, p0]
    shrug = [p1, p3, p1, p0]

    # Roar with shockwaves
    f_roar = p2.copy()
    draw_r = ImageDraw.Draw(f_roar)
    draw_r.arc([130, 50, 165, 85], start=-60, end=60, fill=(255, 200, 0, 255), width=3)
    draw_r.arc([138, 42, 180, 93], start=-60, end=60, fill=(255, 100, 100, 240), width=3)
    roar = [f_roar, f_roar, p2, p0]

    # Music dancing with notes
    notes = [
        [(25, 40, (255, 215, 0, 240)), (145, 30, (0, 220, 255, 240))],
        [(35, 25, (255, 100, 220, 240)), (155, 45, (255, 215, 0, 240))],
        [(20, 50, (255, 80, 80, 240)), (140, 20, (0, 255, 150, 240))],
        [(40, 30, (255, 215, 0, 240)), (150, 55, (255, 180, 50, 240))],
    ]
    music = []
    base_m = [p2, p1, p2, p3]
    for idx, f in enumerate(base_m):
        fc = f.copy()
        draw_m = ImageDraw.Draw(fc)
        for nx, ny, col in notes[idx % len(notes)]:
            draw_music_note(draw_m, nx, ny, col)
        music.append(fc)

    anims = {
        "walk_right": walk_r,
        "walk_left": walk_l,
        "idle": idle,
        "idle_flip": idle_f,
        "blink": blink,
        "happy": happy,
        "idea": idea,
        "work": work,
        "sit": [p0, p0, p0, p0],
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

    print("Generating Drip Cat sprite sheets in assets/sprites/drip_cat/:")
    for name, frames in anims.items():
        strip = create_strip(frames)
        dest = OUT_DIR / f"{name}.png"
        strip.save(dest)
        print(f"  [SAVED] {name}.png ({len(frames)} frames, {strip.width}x{strip.height})")


if __name__ == "__main__":
    generate_all_cat_sprites()
