import math
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
import scipy.ndimage as ndi

BASE_DIR = Path(__file__).parent.parent
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


def extract_clean_spiderman_base() -> Image.Image:
    """Extracts transparent chibi Spider-Man from the user's authentic sticker image."""
    raw_path = SRC_DIR / "spiderman_raw.png"
    if not raw_path.exists():
        raw_path = SRC_DIR / "spiderman_cutout.png"
    img = Image.open(raw_path).convert("RGB")
    w, h = img.size
    arr = np.array(img, dtype=np.float32)

    r, g, b = arr[:, :, 0], arr[:, :, 1], arr[:, :, 2]
    brightness = (r + g + b) / 3.0
    diff = np.maximum.reduce([r, g, b]) - np.minimum.reduce([r, g, b])
    is_white_bg = (brightness > 235) & (diff < 25)

    labeled, num_features = ndi.label(is_white_bg)
    border_mask = np.zeros((h, w), dtype=bool)
    border_mask[0, :] = border_mask[-1, :] = border_mask[:, 0] = border_mask[:, -1] = True
    border_labels = np.unique(labeled[border_mask])
    border_labels = border_labels[border_labels > 0]

    bg_mask = np.isin(labeled, border_labels)

    # Clear cavities outside the head (between web strands, hand, etc.)
    for lbl in range(1, num_features + 1):
        if lbl not in border_labels:
            m = labeled == lbl
            cy, cx = ndi.center_of_mass(m)
            # Spider-Man white eyes are inside head region
            is_eye = (0.28 * h <= cy <= 0.60 * h) and (0.28 * w <= cx <= 0.62 * w)
            if not is_eye:
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

    # Crop to non-transparent bbox
    bbox = rgba.getbbox()
    if bbox:
        rgba = rgba.crop(bbox)

    # Scale to standard pet canvas height (~140px inside 192px box)
    cw, ch = rgba.size
    target_h = 138
    scale = target_h / float(ch)
    nw, nh = max(1, int(cw * scale)), max(1, int(ch * scale))
    scaled = rgba.resize((nw, nh), RESAMPLE_LANCZOS)
    return scaled


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


def draw_dust_puff(draw: ImageDraw.ImageDraw, cx: int, cy: int, r: int):
    draw.ellipse([cx - r, cy - r // 2, cx + r, cy + r // 2], fill=(220, 225, 235, 210))
    draw.ellipse([cx - r // 2, cy - r, cx + r // 2, cy], fill=(240, 245, 255, 230))


def draw_music_note(draw: ImageDraw.ImageDraw, x: int, y: int, fill: tuple):
    draw.ellipse([x, y + 10, x + 8, y + 16], fill=fill)
    draw.line([(x + 7, y), (x + 7, y + 13)], fill=fill, width=2)
    draw.line([(x + 7, y), (x + 13, y + 4)], fill=fill, width=2)


def draw_web_line(draw: ImageDraw.ImageDraw, x0: int, y0: int, x1: int, y1: int, color=(245, 245, 255, 240), width=2):
    draw.line([(x0, y0), (x1, y1)], fill=color, width=width)
    num_segments = max(2, int(math.hypot(x1 - x0, y1 - y0) / 10))
    for i in range(num_segments):
        t = i / float(num_segments)
        px = int(x0 + t * (x1 - x0))
        py = int(y0 + t * (y1 - y0))
        draw.line([(px - 2, py), (px + 2, py)], fill=(200, 210, 230, 180), width=1)


def draw_spidey_sense_sparks(draw: ImageDraw.ImageDraw, cx: int, cy: int, stage: int = 0):
    """Iconic comic-book Spider-Sense yellow & red jagged sparks around head."""
    angles = [25, 60, 95, 130, 160, 200, 235, 270, 305, 340]
    for idx, deg in enumerate(angles):
        rad = math.radians(deg)
        dist1 = 44 + (idx % 3) * 5 + stage * 3
        dist2 = dist1 + 14 + (idx % 2) * 7
        x1 = cx + math.cos(rad) * dist1
        y1 = cy + math.sin(rad) * dist1 * 0.85
        x2 = cx + math.cos(rad) * dist2
        y2 = cy + math.sin(rad) * dist2 * 0.85
        mid_x = (x1 + x2) / 2.0 + math.sin(rad) * 4.0
        mid_y = (y1 + y2) / 2.0 - math.cos(rad) * 4.0
        draw.line([(x1, y1), (mid_x, mid_y), (x2, y2)], fill=(255, 60, 30, 230), width=3)
        draw.line([(x1, y1), (mid_x, mid_y), (x2, y2)], fill=(255, 240, 50, 255), width=1)


# ── Spider-Man 6-Phase Web-Swinging Walk Cycle ──────────────────────────────

def build_6_phase_spiderman_walk(base: Image.Image, is_facing_right: bool = True) -> list:
    w, h = base.size
    arr = np.array(base, dtype=np.float32)
    frames = []

    phase_configs = [
        # (torso_dy, pitch, n_hip, n_knee, n_foot, f_hip, f_knee, f_foot, n_arm, f_arm, sy, web_sway)
        (0,   3.0,   20,  10,   8,   -20,  14, -10,  -20,  20, 1.00,  5),
        (4,   4.0,   10, -18,   0,    -8,  30,  -6,  -10,  10, 0.96,  2),
        (-4, -1.0,    0,   2,   0,    16, -40,  16,    5,  -5, 1.04, -3),
        (0,   3.0,  -20,  14, -10,    20,  10,   8,   20, -20, 1.00, -5),
        (4,   4.0,   -8,  30,  -6,    10, -18,   0,   10, -10, 0.96, -2),
        (-4, -1.0,   16, -40,  16,     0,   2,   0,   -5,   5, 1.04,  3),
    ]

    hip_y = int(h * 0.58)
    knee_y = int(h * 0.78)
    shoulder_y = int(h * 0.42)
    cx = w * 0.50

    y_grid, x_grid = np.indices((h, w), dtype=np.float32)

    for torso_dy, pitch, n_hip, n_knee, n_foot, f_hip, f_knee, f_foot, n_arm, f_arm, sy, web_sway in phase_configs:
        map_y = np.copy(y_grid)
        map_x = np.copy(x_grid)

        # Torso squash/stretch
        for y in range(h):
            if y < hip_y:
                map_y[y, :] = y / sy

        # Articulated Spidey Legs
        for y in range(hip_y, h):
            near_dx = math.sin(math.radians(n_hip)) * (y - hip_y) * 0.85
            if y > knee_y:
                knee_frac = (y - knee_y) / (h - knee_y)
                near_dx += math.sin(math.radians(n_knee)) * (y - knee_y) * 0.75
                near_dx += math.sin(math.radians(n_foot)) * knee_frac * 5.0

            far_dx = math.sin(math.radians(f_hip)) * (y - hip_y) * 0.85
            if y > knee_y:
                knee_frac = (y - knee_y) / (h - knee_y)
                far_dx += math.sin(math.radians(f_knee)) * (y - knee_y) * 0.75
                far_dx += math.sin(math.radians(f_foot)) * knee_frac * 5.0

            x_weights = 1.0 / (1.0 + np.exp(-(x_grid[y, :] - cx) / 6.0))
            combined_dx = (1.0 - x_weights) * far_dx + x_weights * near_dx
            map_x[y, :] -= combined_dx

        deformed_channels = []
        for c in range(4):
            ch = ndi.map_coordinates(arr[:, :, c], [map_y, map_x], order=1, mode='constant', cval=0.0)
            deformed_channels.append(ch)

        deformed_arr = np.dstack(deformed_channels)

        # Subtle depth shading on far leg
        far_leg_mask = (x_grid < cx) & (y_grid > hip_y) & (deformed_arr[:, :, 3] > 20)
        for c in range(3):
            deformed_arr[:, :, c] = np.where(far_leg_mask, deformed_arr[:, :, c] * 0.84, deformed_arr[:, :, c])

        step_img = Image.fromarray(np.clip(deformed_arr, 0, 255).astype(np.uint8), "RGBA")

        if abs(pitch) > 0.1:
            step_img = step_img.rotate(pitch, resample=RESAMPLE_BICUBIC, expand=True)

        placed = step_img if is_facing_right else mirror_frame(step_img)
        f = place_on_canvas(placed, ox_offset=0, oy_offset=torso_dy, align_bottom=True)

        frames.append(f)

    return frames


# ── Spider-Man Idle ─────────────────────────────────────────────────────────

def build_spiderman_idle(base: Image.Image, is_facing_right: bool = True) -> list:
    w, h = base.size
    frames = []

    stages = [
        (1.00, 1.00, 0, 0),
        (1.02, 1.02, -1 if is_facing_right else 1, -2),
        (1.03, 1.03, -1.5 if is_facing_right else 1.5, -4),
        (1.01, 1.01, 0, -1),
    ]

    for sx, sy, rot, dy in stages:
        cur_w = max(1, int(w * sx))
        cur_h = max(1, int(h * sy))
        scaled = base.resize((cur_w, cur_h), RESAMPLE_LANCZOS)
        if rot != 0:
            scaled = scaled.rotate(rot, resample=RESAMPLE_BICUBIC, expand=True)
        placed = scaled if is_facing_right else mirror_frame(scaled)
        f = place_on_canvas(placed, ox_offset=0, oy_offset=dy, align_bottom=True)
        frames.append(f)

    return frames


# ── Spider-Man Roar / Web-Shooter Barrage ───────────────────────────────────

def build_spiderman_roar(base: Image.Image) -> list:
    """Epic Web-Shooter THWIP! 🕸️⚡ Multi-blast combo pose."""
    frames = []
    blasts = [
        (0,  0,  0, 0),
        (35, -3, -2, 1),
        (85, -6, -4, 2),
        (115, -7, -4, 3),
        (70, -4, -2, 2),
        (20,  0,  0, 1),
    ]

    for web_reach, rot, dy, stage in blasts:
        cur = base.rotate(rot, resample=RESAMPLE_BICUBIC, expand=True) if rot != 0 else base
        f = place_on_canvas(cur, ox_offset=-14, oy_offset=dy, align_bottom=True)
        draw = ImageDraw.Draw(f)
        cx, cy = (FRAME_SIZE // 2) + 20, (FRAME_SIZE // 2) - 10 + dy

        if web_reach > 5:
            # Web cone blast
            draw.polygon([
                (cx, cy - 4),
                (cx + web_reach, cy - int(web_reach * 0.45)),
                (cx + int(web_reach * 1.12), cy),
                (cx + web_reach, cy + int(web_reach * 0.45)),
                (cx, cy + 4)
            ], fill=(245, 248, 255, 230), outline=(180, 210, 245, 255))

            # Inner web lattice concentric arcs
            for r_idx in range(1, 4):
                rad_x = int(web_reach * (r_idx / 3.0))
                draw.arc([cx, cy - rad_x // 2, cx + rad_x * 2, cy + rad_x // 2], 270, 90, fill=(200, 225, 255, 240), width=2)

            # Web spider icon impact
            if web_reach > 60:
                sx = cx + web_reach - 8
                draw.ellipse([sx - 6, cy - 6, sx + 6, cy + 6], fill=(20, 25, 35, 255))
                for leg_i in range(4):
                    ang = -45 + leg_i * 30
                    lx = sx + int(math.cos(math.radians(ang)) * 12)
                    ly = cy + int(math.sin(math.radians(ang)) * 10)
                    draw.line([(sx, cy), (lx, ly)], fill=(20, 25, 35, 255), width=2)
                    lx2 = sx - int(math.cos(math.radians(ang)) * 12)
                    draw.line([(sx, cy), (lx2, ly)], fill=(20, 25, 35, 255), width=2)

            # Sparks / Thwip electric crackles
            for ei in range(5):
                ex = cx + int(web_reach * 0.5) + (ei * 12)
                ey = cy - 18 + (ei * 8) + int(math.sin(ei * 2.0) * 8)
                draw.ellipse([ex, ey, ex + 4, ey + 4], fill=(255, 220, 60, 240))

        frames.append(f)
    return frames


# ── Spider-Man Work / Tech Tablet ──────────────────────────────────────────

def build_spiderman_work(base: Image.Image) -> list:
    """Typing fast on a high-tech holographic Stark/Web Tablet 💻⚡"""
    work_frames = []
    for i in range(4):
        rot = 3 if i % 2 == 0 else -3
        dy = -3 if i % 2 == 0 else 0
        f = place_on_canvas(base.rotate(rot, resample=RESAMPLE_BICUBIC, expand=True), 0, dy, align_bottom=True)
        d = ImageDraw.Draw(f)

        # High-tech blue holographic tablet
        tx, ty = 126, 95
        d.rectangle([tx, ty, tx + 24, ty + 36], fill=(20, 30, 45, 240), outline=(80, 180, 255, 255), width=2)
        d.rectangle([tx + 2, ty + 2, tx + 22, ty + 22], fill=(40, 140, 240, 220))
        d.line([(tx + 4, ty + 6), (tx + 18, ty + 6)], fill=(255, 255, 255, 240), width=1)
        d.line([(tx + 4, ty + 10), (tx + 14, ty + 10)], fill=(120, 255, 160, 240), width=1)
        d.line([(tx + 4, ty + 14), (tx + 20, ty + 14)], fill=(255, 210, 80, 240), width=1)
        d.ellipse([tx + 9, ty + 26, tx + 15, ty + 32], fill=(255, 50, 50, 255))

        # Typing beam sparks
        d.line([(106, 92), (tx + 6, ty + 12)], fill=(140, 220, 255, 200), width=1)
        d.line([(114, 98), (tx + 16, ty + 12)], fill=(140, 220, 255, 200), width=1)

        work_frames.append(f)
    return work_frames


# ── Spider-Man Upside-Down Cocoon Sleep & Wake ──────────────────────────────

def build_spiderman_sleep(base: Image.Image) -> list:
    """Hanging upside-down comfortably from ceiling web thread with sleep bubbles 💤🕸️"""
    upside_down = base.rotate(180, resample=RESAMPLE_BICUBIC, expand=True)
    frames = []

    zzz_pos = [
        [(136, 95, "z", 200)],
        [(134, 80, "z", 220), (148, 65, "z", 190)],
        [(132, 70, "z", 230), (146, 52, "Z", 210), (160, 38, "z", 170)],
        [(130, 60, "z", 240), (144, 42, "Z", 230), (158, 25, "Z", 200)],
    ]

    for i, z_list in enumerate(zzz_pos):
        f = place_on_canvas(upside_down, 0, -8 + (i % 2) * 2, align_bottom=False)
        d = ImageDraw.Draw(f)

        for zx, zy, ztxt, alpha in z_list:
            d.text((zx, zy), ztxt, fill=(80, 200, 255, alpha))
            draw_dust_puff(d, zx - 4, zy + 6, 3)

        frames.append(f)
    return frames


def build_spiderman_wake(base: Image.Image, sleep_frame: Image.Image) -> list:
    crouch = base.resize((int(base.width * 1.10), int(base.height * 0.85)), RESAMPLE_LANCZOS)
    flip_frame = base.rotate(90, resample=RESAMPLE_BICUBIC, expand=True)

    return [
        sleep_frame,
        place_on_canvas(flip_frame, 0, -10, align_bottom=False),
        place_on_canvas(crouch, 0, 8, align_bottom=True),
        place_on_canvas(base, 0, 0, align_bottom=True),
    ]


# ── Spider-Man Jump & Fall & Land ──────────────────────────────────────────

def build_spiderman_jump_fall_land(base: Image.Image):
    nw, nh = base.size
    crouch = base.resize((int(nw * 1.15), int(nh * 0.80)), RESAMPLE_LANCZOS)

    # 1. Jump
    f_j0 = place_on_canvas(crouch, 0, 8, align_bottom=True)
    f_j1 = place_on_canvas(base.rotate(6, resample=RESAMPLE_BICUBIC, expand=True), 0, -26, align_bottom=False)
    d1 = ImageDraw.Draw(f_j1)
    draw_web_line(d1, 115, 60, 165, 0)

    f_j2 = place_on_canvas(base.rotate(-6, resample=RESAMPLE_BICUBIC, expand=True), 0, -46, align_bottom=False)
    d2 = ImageDraw.Draw(f_j2)
    draw_web_line(d2, 85, 48, 40, 0)
    draw_star(d2, 145, 25, 7, (255, 230, 80, 240))

    f_j3 = place_on_canvas(base, 0, -20, align_bottom=False)
    jump = [f_j0, f_j1, f_j2, f_j3]

    # 2. Fall
    f_fall_base = base.rotate(-16, resample=RESAMPLE_BICUBIC, expand=True)
    fall = []
    for i in range(4):
        f = place_on_canvas(f_fall_base, 0, i * 5, align_bottom=False)
        df = ImageDraw.Draw(f)
        for wx in [30, 65, 125, 160]:
            y1 = ((wx * 3 + i * 28) % 135) + 15
            df.line([(wx, y1), (wx, y1 + 32)], fill=(210, 230, 255, 190), width=2)
        df.line([(100, 70), (115, 0)], fill=(245, 245, 255, 200), width=2)
        fall.append(f)

    # 3. Land
    f_l0 = place_on_canvas(crouch, 0, 10, align_bottom=True)
    dl0 = ImageDraw.Draw(f_l0)
    draw_dust_puff(dl0, 42, 164, 15)
    draw_dust_puff(dl0, 148, 164, 15)
    dl0.line([(32, 174), (58, 168), (78, 176)], fill=(255, 50, 50, 240), width=2)
    dl0.line([(118, 174), (144, 168), (168, 176)], fill=(80, 160, 255, 240), width=2)
    land = [f_l0, place_on_canvas(base, 0, 4, align_bottom=True), place_on_canvas(base, 0, 0, align_bottom=True), place_on_canvas(base, 0, 0, align_bottom=True)]

    return jump, fall, land


# ── Spider-Man Drag & Sit ──────────────────────────────────────────────────

def build_spiderman_drag(base: Image.Image) -> list:
    drag_frames = []
    swings = [-6, 0, 6, 0]
    for rot in swings:
        cur = base.rotate(rot, resample=RESAMPLE_BICUBIC, expand=True) if rot != 0 else base
        f = place_on_canvas(cur, 0, 6, align_bottom=False)
        drag_frames.append(f)
    return drag_frames


def build_spiderman_sit(base: Image.Image) -> list:
    nw, nh = base.size
    crouch = base.resize((int(nw * 1.10), int(nh * 0.82)), RESAMPLE_LANCZOS)
    return [
        place_on_canvas(crouch, 0, 4, align_bottom=True),
        place_on_canvas(crouch, 0, 3, align_bottom=True),
        place_on_canvas(crouch, 0, 4, align_bottom=True),
        place_on_canvas(crouch, 0, 5, align_bottom=True),
    ]


# ── Spider-Man Idea & Happy & Shrug & Cry & Sad ─────────────────────────────

def build_spiderman_idea(base: Image.Image) -> list:
    idea_frames = []
    for stage in range(4):
        f = place_on_canvas(base, 0, -2 if stage % 2 == 1 else 0, align_bottom=True)
        d = ImageDraw.Draw(f)
        hx, hy = (FRAME_SIZE // 2) - 4, (FRAME_SIZE // 2) - 30
        draw_spidey_sense_sparks(d, hx, hy, stage)
        idea_frames.append(f)
    return idea_frames


def build_spiderman_happy(base: Image.Image) -> list:
    happy_frames = []
    for i in range(4):
        rot = 4 if i % 2 == 0 else -4
        dy = -5 if i % 2 == 0 else 0
        f = place_on_canvas(base.rotate(rot, resample=RESAMPLE_BICUBIC, expand=True), 0, dy, align_bottom=True)
        d = ImageDraw.Draw(f)
        draw_star(d, 35, 35, 10, (255, 230, 80, 240))
        draw_star(d, 155, 30, 10, (255, 60, 60, 240))
        draw_star(d, 140, 75, 8, (80, 180, 255, 240))
        draw_star(d, 45, 80, 8, (255, 255, 255, 240))
        happy_frames.append(f)
    return happy_frames


def build_spiderman_shrug(base: Image.Image) -> list:
    f_shrug = place_on_canvas(base.rotate(3, resample=RESAMPLE_BICUBIC, expand=True), 0, 0, align_bottom=True)
    ds = ImageDraw.Draw(f_shrug)
    ds.ellipse([136, 44, 148, 58], fill=(255, 255, 255, 230))
    return [
        f_shrug,
        place_on_canvas(base.rotate(-3, resample=RESAMPLE_BICUBIC, expand=True), 0, 0, align_bottom=True),
        f_shrug,
        place_on_canvas(base, 0, 0, align_bottom=True),
    ]


def build_spiderman_cry_sad(base: Image.Image):
    f_cry = place_on_canvas(base.rotate(3, resample=RESAMPLE_BICUBIC, expand=True), 0, 2, align_bottom=True)
    dc = ImageDraw.Draw(f_cry)
    dc.ellipse([132, 78, 142, 90], fill=(80, 180, 255, 240))
    dc.ellipse([64, 78, 74, 90], fill=(80, 180, 255, 240))
    cry = [f_cry, f_cry, f_cry, f_cry]
    sad = [f_cry, place_on_canvas(base, 0, 2, align_bottom=True), f_cry, place_on_canvas(base, 0, 2, align_bottom=True)]
    return cry, sad


def build_spiderman_music(base: Image.Image) -> list:
    music = []
    note_pos = [
        [(25, 40, (255, 60, 60, 240)), (145, 30, (80, 180, 255, 240))],
        [(35, 25, (255, 220, 60, 240)), (155, 45, (255, 255, 255, 240))],
        [(20, 50, (80, 180, 255, 240)), (140, 20, (255, 60, 60, 240))],
        [(40, 30, (255, 255, 255, 240)), (150, 55, (255, 220, 60, 240))],
    ]
    for idx in range(4):
        rot = 4 if idx % 2 == 0 else -4
        dy = -4 if idx % 2 == 0 else 1
        f = place_on_canvas(base.rotate(rot, resample=RESAMPLE_BICUBIC, expand=True), 0, dy, align_bottom=True)
        dm = ImageDraw.Draw(f)

        hx, hy = (FRAME_SIZE // 2) - 4, (FRAME_SIZE // 2) - 34 + dy
        dm.arc([hx - 36, hy - 28, hx + 36, hy + 18], 180, 360, fill=(30, 35, 45, 255), width=4)
        dm.ellipse([hx - 38, hy - 4, hx - 26, hy + 16], fill=(255, 50, 50, 255), outline=(20, 25, 35, 255), width=2)
        dm.ellipse([hx + 26, hy - 4, hx + 38, hy + 16], fill=(80, 160, 255, 255), outline=(20, 25, 35, 255), width=2)

        for nx, ny, col in note_pos[idx % len(note_pos)]:
            draw_music_note(dm, nx, ny, col)
        music.append(f)
    return music


def build_spiderman_eat(base: Image.Image) -> list:
    eat_frames = []
    for i in range(4):
        rot = 2 if i % 2 == 0 else -2
        dy = -2 if i % 2 == 0 else 0
        f = place_on_canvas(base.rotate(rot, resample=RESAMPLE_BICUBIC, expand=True), 0, dy, align_bottom=True)
        d = ImageDraw.Draw(f)

        px, py = 122, 100 + dy
        d.polygon([(px, py), (px + 22, py - 8), (px + 16, py + 22)], fill=(255, 205, 50, 255), outline=(210, 120, 20, 255))
        d.ellipse([px + 8, py, px + 14, py + 6], fill=(190, 40, 30, 255))
        d.ellipse([px + 12, py + 8, px + 17, py + 13], fill=(190, 40, 30, 255))
        d.line([(px + 14, py + 18), (px + 10, py + 28)], fill=(255, 230, 90, 240), width=2)

        eat_frames.append(f)
    return eat_frames


def build_spiderman_blink(base: Image.Image) -> list:
    # In the sticker image, Spider-Man head is at upper half
    # Left eye center ~ (FRAME_SIZE//2 - 22, FRAME_SIZE//2 - 12)
    # Right eye center ~ (FRAME_SIZE//2 + 10, FRAME_SIZE//2 - 12)
    blink_f = place_on_canvas(base, 0, 0, align_bottom=True)
    db = ImageDraw.Draw(blink_f)
    ex1, ey1 = (FRAME_SIZE // 2) - 20, (FRAME_SIZE // 2) - 10
    ex2, ey2 = (FRAME_SIZE // 2) + 12, (FRAME_SIZE // 2) - 8
    db.ellipse([ex1 - 10, ey1 - 4, ex1 + 10, ey1 + 4], fill=(20, 25, 35, 255))
    db.ellipse([ex2 - 10, ey2 - 4, ex2 + 10, ey2 + 4], fill=(20, 25, 35, 255))

    return [
        place_on_canvas(base, 0, 0, align_bottom=True),
        blink_f,
        blink_f,
        place_on_canvas(base, 0, 0, align_bottom=True),
    ]


# ── Master Generator ────────────────────────────────────────────────────────

def generate_all_spiderman_sprites():
    print("Extracting authentic Spider-Man cutout from user's image...")
    base = extract_clean_spiderman_base()
    print(f"Base Spider-Man ready with size: {base.size}")

    # 1. Stride & Walk
    walk_r = build_6_phase_spiderman_walk(base, is_facing_right=True)
    walk_l = build_6_phase_spiderman_walk(base, is_facing_right=False)

    # 2. Idle Stance
    idle = build_spiderman_idle(base, is_facing_right=True)
    idle_f = build_spiderman_idle(base, is_facing_right=False)

    # 3. Actions
    roar = build_spiderman_roar(base)
    work = build_spiderman_work(base)
    sleep = build_spiderman_sleep(base)
    wake = build_spiderman_wake(base, sleep[0])
    jump, fall, land = build_spiderman_jump_fall_land(base)
    drag = build_spiderman_drag(base)
    sit = build_spiderman_sit(base)
    idea = build_spiderman_idea(base)
    happy = build_spiderman_happy(base)
    shrug = build_spiderman_shrug(base)
    cry, sad = build_spiderman_cry_sad(base)
    music = build_spiderman_music(base)
    eat = build_spiderman_eat(base)
    blink = build_spiderman_blink(base)

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
        "eat": eat,
    }

    print(f"\nGenerating Spider-Man Sprite Sheets in {OUT_DIR}:")
    for name, frames in anims.items():
        strip = create_strip(frames)
        dest = OUT_DIR / f"{name}.png"
        strip.save(dest, "PNG")
        print(f"  [SAVED] {name}.png ({len(frames)} frames, {strip.width}x{strip.height})")


if __name__ == "__main__":
    generate_all_spiderman_sprites()
