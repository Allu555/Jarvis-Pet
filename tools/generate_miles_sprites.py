import math
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
import scipy.ndimage as ndi

SRC_CUTOUT = Path(__file__).parent / "miles_sources" / "miles_cutout.png"
OUT_DIR = Path(__file__).parent / "sprites" / "miles"
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


def load_base() -> Image.Image:
    return Image.open(SRC_CUTOUT).convert("RGBA")


def mirror(im: Image.Image) -> Image.Image:
    return im.transpose(Image.Transpose.FLIP_LEFT_RIGHT if hasattr(Image, "Transpose") else Image.FLIP_LEFT_RIGHT)


def place_on_canvas(img: Image.Image, ox_offset: int = 0, oy_offset: int = 0, align_bottom: bool = True) -> Image.Image:
    canvas = Image.new("RGBA", (FRAME_SIZE, FRAME_SIZE), (0, 0, 0, 0))
    nw, nh = img.size
    ox = (FRAME_SIZE - nw) // 2 + ox_offset
    if align_bottom:
        oy = FRAME_SIZE - nh - 10 + oy_offset
    else:
        oy = (FRAME_SIZE - nh) // 2 + oy_offset
    canvas.paste(img, (ox, oy), img)
    return canvas


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


def draw_bio_lightning(draw: ImageDraw.ImageDraw, x0: int, y0: int, x1: int, y1: int, stage: int = 0):
    dist = math.hypot(x1 - x0, y1 - y0)
    steps = max(3, int(dist / 12))
    points = [(x0, y0)]
    for i in range(1, steps):
        t = i / float(steps)
        bx = x0 + t * (x1 - x0)
        by = y0 + t * (y1 - y0)
        offset = math.sin(i * 2.5 + stage * 2.0) * 9.0
        norm_x = -(y1 - y0) / max(1.0, dist)
        norm_y = (x1 - x0) / max(1.0, dist)
        points.append((int(bx + norm_x * offset), int(by + norm_y * offset)))
    points.append((x1, y1))

    for i in range(len(points) - 1):
        draw.line([points[i], points[i+1]], fill=(255, 100, 20, 240), width=5)
    for i in range(len(points) - 1):
        draw.line([points[i], points[i+1]], fill=(255, 245, 70, 255), width=2)


def draw_dust_puff(draw: ImageDraw.ImageDraw, cx: int, cy: int, r: int):
    draw.ellipse([cx - r, cy - r // 2, cx + r, cy + r // 2], fill=(220, 225, 235, 210))
    draw.ellipse([cx - r // 2, cy - r, cx + r // 2, cy], fill=(240, 245, 255, 230))


def draw_star(draw: ImageDraw.ImageDraw, cx: float, cy: float, r: float, fill: tuple):
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


def draw_web_line(draw: ImageDraw.ImageDraw, x0: int, y0: int, x1: int, y1: int, color=(245, 245, 255, 240), width=2):
    draw.line([(x0, y0), (x1, y1)], fill=color, width=width)


def build_standing_base(base: Image.Image) -> Image.Image:
    """Builds an upright standing stance for Miles Morales from his leaping base."""
    w, h = base.size
    head_h = int(h * 0.58)
    head = base.crop((0, 0, w, head_h))
    
    # Standing canvas
    out_h = int(h * 1.05)
    canvas = Image.new("RGBA", (w, out_h), (0, 0, 0, 0))
    d = ImageDraw.Draw(canvas)
    
    cx = w // 2
    hip_y = head_h - 10
    
    # Draw body/torso
    torso_w = int(w * 0.44)
    torso_left = cx - torso_w // 2
    torso_top = hip_y - 20
    # Black suit with red spider chest
    d.ellipse([torso_left, torso_top, torso_left + torso_w, hip_y + 18], fill=(18, 18, 24, 255), outline=(10, 10, 15, 255), width=3)
    # Red V-chest accent
    d.polygon([(cx - 14, torso_top + 4), (cx + 14, torso_top + 4), (cx, hip_y + 10)], fill=(220, 30, 30, 255))
    # Spider emblem
    d.ellipse([cx - 4, torso_top + 10, cx + 4, torso_top + 20], fill=(18, 18, 24, 255))
    
    # Left Leg (Standing upright)
    d.polygon([(cx - 16, hip_y + 10), (cx - 24, out_h - 14), (cx - 6, out_h - 14), (cx - 4, hip_y + 10)], fill=(18, 18, 24, 255), outline=(10, 10, 15, 255), width=2)
    # Left Foot
    d.ellipse([cx - 28, out_h - 16, cx - 4, out_h - 2], fill=(220, 30, 30, 255), outline=(10, 10, 15, 255), width=2)
    
    # Right Leg (Standing upright)
    d.polygon([(cx + 4, hip_y + 10), (cx + 6, out_h - 14), (cx + 24, out_h - 14), (cx + 16, hip_y + 10)], fill=(18, 18, 24, 255), outline=(10, 10, 15, 255), width=2)
    # Right Foot
    d.ellipse([cx + 4, out_h - 16, cx + 28, out_h - 2], fill=(220, 30, 30, 255), outline=(10, 10, 15, 255), width=2)
    
    # Arms standing relaxed
    # Left arm
    d.polygon([(cx - torso_w // 2, torso_top + 8), (cx - torso_w // 2 - 12, hip_y + 16), (cx - torso_w // 2 - 4, hip_y + 18), (cx - torso_w // 2 + 4, torso_top + 12)], fill=(18, 18, 24, 255))
    d.ellipse([cx - torso_w // 2 - 14, hip_y + 14, cx - torso_w // 2 - 2, hip_y + 26], fill=(220, 30, 30, 255), outline=(10, 10, 15, 255), width=2)
    
    # Right arm
    d.polygon([(cx + torso_w // 2, torso_top + 8), (cx + torso_w // 2 + 12, hip_y + 16), (cx + torso_w // 2 + 4, hip_y + 18), (cx + torso_w // 2 - 4, torso_top + 12)], fill=(18, 18, 24, 255))
    d.ellipse([cx + torso_w // 2 + 2, hip_y + 14, cx + torso_w // 2 + 14, hip_y + 26], fill=(220, 30, 30, 255), outline=(10, 10, 15, 255), width=2)
    
    # Paste head over body
    canvas.paste(head, (0, 0), head)
    return canvas


def build_walk_frame(base: Image.Image, phase: int, is_facing_right: bool = True) -> Image.Image:
    """Builds an authentic walking stride pose with articulated legs and arms."""
    w, h = base.size
    head_h = int(h * 0.58)
    head = base.crop((0, 0, w, head_h))
    
    out_h = int(h * 1.05)
    canvas = Image.new("RGBA", (w, out_h), (0, 0, 0, 0))
    d = ImageDraw.Draw(canvas)
    
    cx = w // 2
    hip_y = head_h - 10
    torso_w = int(w * 0.44)
    torso_left = cx - torso_w // 2
    
    # 4 Walk Phases:
    # 0: Lead stride (left forward, right back, arms swinging)
    # 1: Pass apex (rebound lift)
    # 2: Opposite stride (right forward, left back)
    # 3: Pass apex 2
    strides = [
        # (left_foot_dx, left_foot_dy, right_foot_dx, right_foot_dy, l_arm_ang, r_arm_ang, body_dy)
        ( 22, -2, -22, -6,  25, -25,  0),
        (  4,  0,   0, -12,  0,   0, -3),
        (-22, -6,  22, -2, -25,  25,  0),
        (  0, -12,  4,   0,  0,   0, -3),
    ]
    
    l_dx, l_dy, r_dx, r_dy, l_arm_ang, r_arm_ang, b_dy = strides[phase % 4]
    
    torso_top = hip_y - 20 + b_dy
    
    # Back Leg
    if phase in (0, 1):
        # Right leg is back
        d.polygon([(cx + 4, hip_y + 10 + b_dy), (cx + 8 + r_dx, out_h - 16 + r_dy), (cx + 22 + r_dx, out_h - 16 + r_dy), (cx + 14, hip_y + 10 + b_dy)], fill=(12, 12, 16, 255))
        d.ellipse([cx + 6 + r_dx, out_h - 18 + r_dy, cx + 24 + r_dx, out_h - 4 + r_dy], fill=(160, 20, 20, 255))
    else:
        # Left leg is back
        d.polygon([(cx - 14, hip_y + 10 + b_dy), (cx - 22 + l_dx, out_h - 16 + l_dy), (cx - 8 + l_dx, out_h - 16 + l_dy), (cx - 4, hip_y + 10 + b_dy)], fill=(12, 12, 16, 255))
        d.ellipse([cx - 24 + l_dx, out_h - 18 + l_dy, cx - 6 + l_dx, out_h - 4 + l_dy], fill=(160, 20, 20, 255))
        
    # Torso
    d.ellipse([torso_left, torso_top, torso_left + torso_w, hip_y + 18 + b_dy], fill=(18, 18, 24, 255), outline=(10, 10, 15, 255), width=3)
    d.polygon([(cx - 14, torso_top + 4), (cx + 14, torso_top + 4), (cx, hip_y + 10 + b_dy)], fill=(220, 30, 30, 255))
    
    # Front Leg
    if phase in (0, 1):
        # Left leg is forward
        d.polygon([(cx - 6, hip_y + 10 + b_dy), (cx - 14 + l_dx, out_h - 14 + l_dy), (cx + 4 + l_dx, out_h - 14 + l_dy), (cx + 6, hip_y + 10 + b_dy)], fill=(22, 22, 30, 255), outline=(10, 10, 15, 255), width=2)
        d.ellipse([cx - 16 + l_dx, out_h - 16 + l_dy, cx + 6 + l_dx, out_h - 2 + l_dy], fill=(220, 30, 30, 255), outline=(10, 10, 15, 255), width=2)
    else:
        # Right leg is forward
        d.polygon([(cx - 6, hip_y + 10 + b_dy), (cx - 4 + r_dx, out_h - 14 + r_dy), (cx + 14 + r_dx, out_h - 14 + r_dy), (cx + 6, hip_y + 10 + b_dy)], fill=(22, 22, 30, 255), outline=(10, 10, 15, 255), width=2)
        d.ellipse([cx - 6 + r_dx, out_h - 16 + r_dy, cx + 16 + r_dx, out_h - 2 + r_dy], fill=(220, 30, 30, 255), outline=(10, 10, 15, 255), width=2)

    # Dynamic Swinging Arms
    # Left Arm
    l_arm_x = cx - torso_w // 2 - int(math.sin(math.radians(l_arm_ang)) * 14)
    l_arm_y = hip_y + 14 + b_dy + int(math.cos(math.radians(l_arm_ang)) * 6)
    d.line([(cx - torso_w // 2 + 4, torso_top + 10), (l_arm_x, l_arm_y)], fill=(18, 18, 24, 255), width=7)
    d.ellipse([l_arm_x - 6, l_arm_y - 6, l_arm_x + 6, l_arm_y + 6], fill=(220, 30, 30, 255), outline=(10, 10, 15, 255), width=2)

    # Right Arm
    r_arm_x = cx + torso_w // 2 + int(math.sin(math.radians(r_arm_ang)) * 14)
    r_arm_y = hip_y + 14 + b_dy + int(math.cos(math.radians(r_arm_ang)) * 6)
    d.line([(cx + torso_w // 2 - 4, torso_top + 10), (r_arm_x, r_arm_y)], fill=(18, 18, 24, 255), width=7)
    d.ellipse([r_arm_x - 6, r_arm_y - 6, r_arm_x + 6, r_arm_y + 6], fill=(220, 30, 30, 255), outline=(10, 10, 15, 255), width=2)

    # Head
    canvas.paste(head, (0, b_dy), head)
    
    placed = canvas if is_facing_right else mirror(canvas)
    return place_on_canvas(placed, ox_offset=0, oy_offset=0, align_bottom=True)


def build_all_miles_sprites():
    raw_leap = load_base()
    standing = build_standing_base(raw_leap)

    # 1. Idle (Standing upright breathing)
    idle_frames = [
        place_on_canvas(standing, 0, 0, align_bottom=True),
        place_on_canvas(standing, 0, -2, align_bottom=True),
        place_on_canvas(standing, 0, -3, align_bottom=True),
        place_on_canvas(standing, 0, -1, align_bottom=True),
    ]
    idle_f_frames = [mirror(f) for f in idle_frames]

    # 2. Walk Right & Walk Left (Actual distinct 4-phase walking strides)
    walk_r_frames = [build_walk_frame(raw_leap, i, is_facing_right=True) for i in range(4)]
    walk_l_frames = [build_walk_frame(raw_leap, i, is_facing_right=False) for i in range(4)]

    # 3. Jump (Crouch launch -> User Leap Pose soaring high -> Apex)
    crouch_stand = standing.resize((int(standing.width * 1.15), int(standing.height * 0.80)), RESAMPLE_LANCZOS)
    jump_f0 = place_on_canvas(crouch_stand, 0, 8, align_bottom=True)
    
    jump_f1 = place_on_canvas(raw_leap.rotate(8, resample=RESAMPLE_BICUBIC, expand=True), 0, -24, align_bottom=False)
    d1 = ImageDraw.Draw(jump_f1)
    draw_bio_lightning(d1, 110, 80, 160, 25, stage=1)

    jump_f2 = place_on_canvas(raw_leap.rotate(-8, resample=RESAMPLE_BICUBIC, expand=True), 0, -48, align_bottom=False)
    d2 = ImageDraw.Draw(jump_f2)
    draw_bio_lightning(d2, 85, 60, 40, 20, stage=2)
    draw_star(d2, 145, 30, 8, (255, 230, 60, 240))

    jump_f3 = place_on_canvas(raw_leap, 0, -20, align_bottom=False)
    jump_frames = [jump_f0, jump_f1, jump_f2, jump_f3]

    # 4. Fall (Diving downward head-first)
    fall_base = raw_leap.rotate(-24, resample=RESAMPLE_BICUBIC, expand=True)
    fall_frames = []
    for i in range(4):
        f = place_on_canvas(fall_base, 0, i * 6, align_bottom=False)
        df = ImageDraw.Draw(f)
        for wx in [30, 65, 125, 160]:
            y1 = ((wx * 3 + i * 28) % 135) + 15
            df.line([(wx, y1), (wx, y1 + 32)], fill=(255, 180, 80, 190), width=2)
        fall_frames.append(f)

    # 5. Land (3-point superhero landing)
    land_f0 = place_on_canvas(crouch_stand, 0, 10, align_bottom=True)
    dl = ImageDraw.Draw(land_f0)
    draw_dust_puff(dl, 42, 164, 15)
    draw_dust_puff(dl, 148, 164, 15)
    dl.line([(32, 174), (58, 168), (78, 176)], fill=(255, 60, 40, 240), width=2)
    dl.line([(118, 174), (144, 168), (168, 176)], fill=(255, 220, 40, 240), width=2)
    land_frames = [land_f0, place_on_canvas(standing, 0, 4, align_bottom=True), place_on_canvas(standing, 0, 0, align_bottom=True), place_on_canvas(standing, 0, 0, align_bottom=True)]

    # 6. Drag (Web swing)
    drag_frames = []
    for rot in [-6, 0, 6, 0]:
        cur = raw_leap.rotate(rot, resample=RESAMPLE_BICUBIC, expand=True) if rot != 0 else raw_leap
        f = place_on_canvas(cur, 0, 6, align_bottom=False)
        d = ImageDraw.Draw(f)
        draw_web_line(d, (FRAME_SIZE // 2) + int(rot * 1.5), (FRAME_SIZE // 2) - 20, (FRAME_SIZE // 2), 0, width=2)
        drag_frames.append(f)

    # 7. Sleep & Wake (Hanging upside down from web thread)
    upside_down = raw_leap.rotate(180, resample=RESAMPLE_BICUBIC, expand=True)
    sleep_frames = []
    zzz_pos = [
        [(136, 95, "z", 200)],
        [(134, 80, "z", 220), (148, 65, "z", 190)],
        [(132, 70, "z", 230), (146, 52, "Z", 210), (160, 38, "z", 170)],
        [(130, 60, "z", 240), (144, 42, "Z", 230), (158, 25, "Z", 200)],
    ]
    for i, z_list in enumerate(zzz_pos):
        f = place_on_canvas(upside_down, 0, -8 + (i % 2) * 2, align_bottom=False)
        d = ImageDraw.Draw(f)
        d.line([(FRAME_SIZE // 2, 0), (FRAME_SIZE // 2, 40)], fill=(245, 245, 255, 240), width=2)
        for zx, zy, ztxt, alpha in z_list:
            d.text((zx, zy), ztxt, fill=(255, 200, 50, alpha))
            draw_dust_puff(d, zx - 4, zy + 6, 3)
        sleep_frames.append(f)

    wake_frames = [
        sleep_frames[0],
        place_on_canvas(raw_leap.rotate(90, resample=RESAMPLE_BICUBIC, expand=True), 0, -10, align_bottom=False),
        place_on_canvas(crouch_stand, 0, 8, align_bottom=True),
        place_on_canvas(standing, 0, 0, align_bottom=True),
    ]

    # 8. Work (Typing on laptop)
    work_frames = []
    for i in range(4):
        rot = 3 if i % 2 == 0 else -3
        dy = -3 if i % 2 == 0 else 0
        f = place_on_canvas(standing.rotate(rot, resample=RESAMPLE_BICUBIC, expand=True), 0, dy, align_bottom=True)
        d = ImageDraw.Draw(f)
        tx, ty = 126, 95
        d.rectangle([tx, ty, tx + 24, ty + 36], fill=(20, 22, 28, 240), outline=(255, 50, 50, 255), width=2)
        d.rectangle([tx + 2, ty + 2, tx + 22, ty + 22], fill=(25, 30, 40, 220))
        d.line([(tx + 4, ty + 6), (tx + 18, ty + 6)], fill=(255, 220, 60, 240), width=1)
        d.line([(tx + 4, ty + 10), (tx + 14, ty + 10)], fill=(255, 60, 60, 240), width=1)
        d.ellipse([tx + 9, ty + 26, tx + 15, ty + 32], fill=(255, 40, 40, 255))
        d.line([(106, 92), (tx + 6, ty + 12)], fill=(255, 230, 80, 220), width=1)
        d.line([(114, 98), (tx + 16, ty + 12)], fill=(255, 230, 80, 220), width=1)
        work_frames.append(f)

    # 9. Idea (Spidey Sense)
    idea_frames = []
    for stage in range(4):
        f = place_on_canvas(standing, 0, -2 if stage % 2 == 1 else 0, align_bottom=True)
        d = ImageDraw.Draw(f)
        hx, hy = (FRAME_SIZE // 2) - 4, (FRAME_SIZE // 2) - 30
        draw_bio_lightning(d, hx - 40, hy - 20, hx - 10, hy - 45, stage=stage)
        draw_bio_lightning(d, hx + 10, hy - 45, hx + 40, hy - 20, stage=stage+1)
        draw_star(d, hx, hy - 50, 8, (255, 240, 60, 255))
        idea_frames.append(f)

    # 10. Happy
    happy_frames = []
    for i in range(4):
        rot = 4 if i % 2 == 0 else -4
        dy = -5 if i % 2 == 0 else 0
        f = place_on_canvas(standing.rotate(rot, resample=RESAMPLE_BICUBIC, expand=True), 0, dy, align_bottom=True)
        d = ImageDraw.Draw(f)
        draw_star(d, 35, 35, 10, (255, 60, 40, 240))
        draw_star(d, 155, 30, 10, (255, 220, 60, 240))
        draw_star(d, 140, 75, 8, (255, 60, 40, 240))
        draw_star(d, 45, 80, 8, (255, 255, 255, 240))
        happy_frames.append(f)

    # 11. Roar / Bio-Electric Venom Strike
    roar_frames = []
    blasts = [(0, 0, 0), (40, -3, -2), (90, -6, -4), (120, -7, -4), (75, -4, -2), (25, 0, 0)]
    for stage_i, (blast_len, rot, dy) in enumerate(blasts):
        cur = raw_leap.rotate(rot, resample=RESAMPLE_BICUBIC, expand=True) if rot != 0 else raw_leap
        f = place_on_canvas(cur, ox_offset=-12, oy_offset=dy, align_bottom=True)
        draw = ImageDraw.Draw(f)
        hx, hy = (FRAME_SIZE // 2) + 18, (FRAME_SIZE // 2) - 8 + dy
        if blast_len > 10:
            draw_bio_lightning(draw, hx, hy, hx + blast_len, hy - int(blast_len * 0.3), stage=stage_i)
            draw_bio_lightning(draw, hx, hy, hx + int(blast_len * 1.1), hy + int(blast_len * 0.1), stage=stage_i+1)
            draw_bio_lightning(draw, hx, hy, hx + blast_len, hy + int(blast_len * 0.4), stage=stage_i+2)
            for ei in range(6):
                ex = hx + int(blast_len * 0.4) + (ei * 12)
                ey = hy - 20 + (ei * 8) + int(math.sin(ei * 2.0) * 10)
                draw.ellipse([ex, ey, ex + 6, ey + 6], fill=(255, 240, 50, 240), outline=(255, 100, 20, 255))
        roar_frames.append(f)

    # 12. Sit & Shrug & Blink & Cry & Music & Eat
    sit_frames = [
        place_on_canvas(crouch_stand, 0, 4, align_bottom=True),
        place_on_canvas(crouch_stand, 0, 3, align_bottom=True),
        place_on_canvas(crouch_stand, 0, 4, align_bottom=True),
        place_on_canvas(crouch_stand, 0, 5, align_bottom=True),
    ]
    f_shrug = place_on_canvas(standing.rotate(3, resample=RESAMPLE_BICUBIC, expand=True), 0, 0, align_bottom=True)
    ds = ImageDraw.Draw(f_shrug)
    ds.ellipse([136, 44, 148, 58], fill=(255, 255, 255, 230))
    shrug_frames = [f_shrug, place_on_canvas(standing.rotate(-3, resample=RESAMPLE_BICUBIC, expand=True), 0, 0, align_bottom=True), f_shrug, place_on_canvas(standing, 0, 0, align_bottom=True)]

    f_cry = place_on_canvas(standing.rotate(3, resample=RESAMPLE_BICUBIC, expand=True), 0, 2, align_bottom=True)
    dc = ImageDraw.Draw(f_cry)
    dc.ellipse([132, 78, 142, 90], fill=(80, 180, 255, 240))
    dc.ellipse([64, 78, 74, 90], fill=(80, 180, 255, 240))
    cry_frames = [f_cry, f_cry, f_cry, f_cry]
    sad_frames = [f_cry, place_on_canvas(standing, 0, 2, align_bottom=True), f_cry, place_on_canvas(standing, 0, 2, align_bottom=True)]

    music_frames = []
    note_pos = [
        [(25, 40, (255, 60, 40, 240)), (145, 30, (255, 220, 60, 240))],
        [(35, 25, (255, 220, 60, 240)), (155, 45, (255, 255, 255, 240))],
        [(20, 50, (255, 60, 40, 240)), (140, 20, (255, 220, 60, 240))],
        [(40, 30, (255, 255, 255, 240)), (150, 55, (255, 60, 40, 240))],
    ]
    for idx in range(4):
        rot = 4 if idx % 2 == 0 else -4
        dy = -4 if idx % 2 == 0 else 1
        f = place_on_canvas(standing.rotate(rot, resample=RESAMPLE_BICUBIC, expand=True), 0, dy, align_bottom=True)
        dm = ImageDraw.Draw(f)
        hx, hy = (FRAME_SIZE // 2) - 4, (FRAME_SIZE // 2) - 34 + dy
        dm.arc([hx - 36, hy - 28, hx + 36, hy + 18], 180, 360, fill=(30, 35, 45, 255), width=4)
        dm.ellipse([hx - 38, hy - 4, hx - 26, hy + 16], fill=(255, 40, 40, 255), outline=(20, 25, 35, 255), width=2)
        dm.ellipse([hx + 26, hy - 4, hx + 38, hy + 16], fill=(255, 40, 40, 255), outline=(20, 25, 35, 255), width=2)
        for nx, ny, col in note_pos[idx % len(note_pos)]:
            dm.ellipse([nx, ny + 10, nx + 8, ny + 16], fill=col)
            dm.line([(nx + 7, ny), (nx + 7, ny + 13)], fill=col, width=2)
            dm.line([(nx + 7, ny), (nx + 13, ny + 4)], fill=col, width=2)
        music_frames.append(f)

    eat_frames = []
    for i in range(4):
        rot = 2 if i % 2 == 0 else -2
        dy = -2 if i % 2 == 0 else 0
        f = place_on_canvas(standing.rotate(rot, resample=RESAMPLE_BICUBIC, expand=True), 0, dy, align_bottom=True)
        d = ImageDraw.Draw(f)
        px, py = 122, 100 + dy
        d.polygon([(px, py), (px + 22, py - 8), (px + 16, py + 22)], fill=(255, 205, 50, 255), outline=(210, 120, 20, 255))
        d.ellipse([px + 8, py, px + 14, py + 6], fill=(190, 40, 30, 255))
        d.ellipse([px + 12, py + 8, px + 17, py + 13], fill=(190, 40, 30, 255))
        d.line([(px + 14, py + 18), (px + 10, py + 28)], fill=(255, 230, 90, 240), width=2)
        eat_frames.append(f)

    blink_f = place_on_canvas(standing, 0, 0, align_bottom=True)
    db = ImageDraw.Draw(blink_f)
    ex1, ey1 = (FRAME_SIZE // 2) - 16, (FRAME_SIZE // 2) - 10
    ex2, ey2 = (FRAME_SIZE // 2) + 14, (FRAME_SIZE // 2) - 8
    db.ellipse([ex1 - 8, ey1 - 4, ex1 + 8, ey1 + 4], fill=(20, 25, 35, 255))
    db.ellipse([ex2 - 8, ey2 - 4, ex2 + 8, ey2 + 4], fill=(20, 25, 35, 255))
    blink_frames = [place_on_canvas(standing, 0, 0, align_bottom=True), blink_f, blink_f, place_on_canvas(standing, 0, 0, align_bottom=True)]

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

    print("\nSaving articulated Miles Morales sprite sheets to assets/sprites/miles/:")
    for name, frames in anims.items():
        strip = create_strip(frames)
        dest = OUT_DIR / f"{name}.png"
        strip.save(dest, "PNG")
        print(f"  [SAVED] {name}.png ({len(frames)} frames, {strip.width}x{strip.height})")


if __name__ == "__main__":
    build_all_miles_sprites()
