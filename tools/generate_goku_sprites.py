import numpy as np
from PIL import Image, ImageDraw, ImageFilter
from pathlib import Path
import scipy.ndimage as ndi
import math

BASE_DIR = Path(__file__).parent.parent
SRC_DIR = Path(__file__).parent / "goku_sources"
OUT_DIR = Path(__file__).parent / "sprites" / "goku"
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


def get_clean_goku(target_size: int = FRAME_SIZE) -> Image.Image:
    cutout = Image.open(SRC_DIR / "goku_cutout.png").convert("RGBA")
    arr = np.array(cutout)
    
    r, g, b = arr[:,:,0].astype(float), arr[:,:,1].astype(float), arr[:,:,2].astype(float)
    dist_from_white = np.sqrt((255 - r)**2 + (255 - g)**2 + (255 - b)**2)
    is_bg = (dist_from_white < 35)
    labeled, _ = ndi.label(is_bg)
    border_mask = np.zeros_like(is_bg, dtype=bool)
    border_mask[:3, :] = border_mask[-3:, :] = border_mask[:, :3] = border_mask[:, -3:] = True
    border_labels = np.unique(labeled[border_mask & is_bg])
    bg_mask = np.isin(labeled, border_labels)
    bg_mask = ndi.binary_dilation(bg_mask, iterations=1)
    
    alpha = np.where(bg_mask, 0, arr[:, :, 3]).astype(np.uint8)
    clean = Image.fromarray(np.dstack([arr[:, :, :3], alpha]), mode="RGBA")
    
    bbox = clean.getbbox()
    if bbox:
        clean = clean.crop(bbox)
        
    cw, ch = clean.size
    scale = (target_size - 32) / max(cw, ch)
    nw, nh = max(1, int(cw * scale)), max(1, int(ch * scale))
    return clean.resize((nw, nh), RESAMPLE_LANCZOS)


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
    draw.ellipse([cx - r, cy - r // 2, cx + r, cy + r // 2], fill=(235, 235, 240, 210))
    draw.ellipse([cx - r // 2, cy - r, cx + r // 2, cy], fill=(245, 245, 250, 230))


def draw_music_note(draw: ImageDraw.ImageDraw, x: int, y: int, fill: tuple):
    draw.ellipse([x, y + 10, x + 8, y + 16], fill=fill)
    draw.line([(x + 7, y), (x + 7, y + 13)], fill=fill, width=2)
    draw.line([(x + 7, y), (x + 13, y + 4)], fill=fill, width=2)


def place_on_canvas(img: Image.Image, ox_offset: int = 0, oy_offset: int = 0, align_bottom: bool = True) -> Image.Image:
    canvas = Image.new("RGBA", (FRAME_SIZE, FRAME_SIZE), (0, 0, 0, 0))
    nw, nh = img.size
    ox = (FRAME_SIZE - nw) // 2 + ox_offset
    if align_bottom:
        oy = FRAME_SIZE - nh - 12 + oy_offset
    else:
        oy = (FRAME_SIZE - nh) // 2 + oy_offset
    canvas.paste(img, (ox, oy), img)
    return canvas


# ── Full 6-Phase Keyframe Human Walk Cycle Engine ────────────────────────────

def build_6_phase_human_walk(base: Image.Image, is_facing_right: bool = True) -> list:
    """
    Constructs the authentic 6-phase side-profile walking cycle matching the reference walk cycle:
    Phase 0 (Contact 1): Lead leg extended forward (heel strike), trail leg back (push-off), arms swinging opposite.
    Phase 1 (Down 1): Weight onto lead leg, knee flexed, foot flat, body squashes down (dy=+6px), trail leg flexes forward.
    Phase 2 (Pass 1): Stance leg straightens, body rises to apex (dy=-6px), swing leg lifts high at knee passing through.
    Phase 3 (Contact 2): Opposite contact stride (far leg forward heel strike, near leg back).
    Phase 4 (Down 2): Opposite down/recoil pose (far leg planted, knee flexed, body squashes down).
    Phase 5 (Pass 2): Opposite pass pose (far leg straight supporting, near leg lifts high at knee).
    """
    w, h = base.size
    arr = np.array(base, dtype=np.float32)
    frames = []

    # 6 Keyframe configurations:
    # (torso_dy, pitch_deg, n_hip, n_knee, n_foot, f_hip, f_knee, f_foot, n_arm, f_arm, sy, tail_sway)
    phase_configs = [
        # Frame 1: Contact 1 (split stride)
        (0, 2.5,   22,  8,  14,   -22, 12, -14,  -26,  26, 1.00, -6.0),
        # Frame 2: Down 1 (recoil squash)
        (6, 4.0,   12, -18,  0,   -10, 34, -10,  -12,  12, 0.95, -3.0),
        # Frame 3: Pass 1 (high apex)
        (-6, -1.5,  0,   0,  0,    18, -44,  18,    6,  -6, 1.04,  4.0),
        # Frame 4: Contact 2 (opposite split stride)
        (0, 2.5,  -22, 12, -14,    22,  8,  14,   26, -26, 1.00,  6.0),
        # Frame 5: Down 2 (recoil squash)
        (6, 4.0,  -10, 34, -10,    12, -18,  0,   12, -12, 0.95,  3.0),
        # Frame 6: Pass 2 (high apex)
        (-6, -1.5, 18, -44,  18,    0,   0,  0,   -6,   6, 1.04, -4.0),
    ]

    hip_y = int(h * 0.52)
    knee_y = int(h * 0.74)
    shoulder_y = int(h * 0.35)
    cx = w * 0.50

    y_grid, x_grid = np.indices((h, w), dtype=np.float32)

    for torso_dy, pitch, n_hip, n_knee, n_foot, f_hip, f_knee, f_foot, n_arm, f_arm, sy, tail_sway in phase_configs:
        map_y = np.copy(y_grid)
        map_x = np.copy(x_grid)

        # 1. Torso squash/stretch
        for y in range(h):
            if y < hip_y:
                map_y[y, :] = y / sy

        # 2. Articulated Legs (Hip swing, knee bend, foot angle)
        for y in range(hip_y, h):
            # Near leg (facing direction: front half)
            near_dx = math.sin(math.radians(n_hip)) * (y - hip_y) * 0.88
            if y > knee_y:
                knee_frac = (y - knee_y) / (h - knee_y)
                near_dx += math.sin(math.radians(n_knee)) * (y - knee_y) * 0.78
                near_dx += math.sin(math.radians(n_foot)) * knee_frac * 6.5

            # Far leg (facing direction: back half)
            far_dx = math.sin(math.radians(f_hip)) * (y - hip_y) * 0.88
            if y > knee_y:
                knee_frac = (y - knee_y) / (h - knee_y)
                far_dx += math.sin(math.radians(f_knee)) * (y - knee_y) * 0.78
                far_dx += math.sin(math.radians(f_foot)) * knee_frac * 6.5

            x_weights = 1.0 / (1.0 + np.exp(-(x_grid[y, :] - cx) / 7.0))
            combined_dx = (1.0 - x_weights) * far_dx + x_weights * near_dx
            map_x[y, :] -= combined_dx

        # 3. Dynamic Arms
        for y in range(shoulder_y, int(h * 0.72)):
            near_arm_dx = math.sin(math.radians(n_arm)) * (y - shoulder_y) * 0.75
            far_arm_dx = math.sin(math.radians(f_arm)) * (y - shoulder_y) * 0.75
            arm_mask_near = np.clip((x_grid[y, :] - w * 0.55) / (w * 0.25), 0, 1)
            arm_mask_far = np.clip((w * 0.45 - x_grid[y, :]) / (w * 0.25), 0, 1)
            map_x[y, :] -= arm_mask_near * near_arm_dx + arm_mask_far * far_arm_dx

        # 4. Tail sway (left side of character)
        for y in range(int(h * 0.42), int(h * 0.68)):
            tail_mask = np.clip((w * 0.35 - x_grid[y, :]) / (w * 0.20), 0, 1)
            map_x[y, :] -= tail_mask * tail_sway

        # Sample channels
        deformed_channels = []
        for c in range(4):
            ch = ndi.map_coordinates(arr[:, :, c], [map_y, map_x], order=1, mode='constant', cval=0.0)
            deformed_channels.append(ch)

        deformed_arr = np.dstack(deformed_channels)

        # Depth shading on far leg (18% darker tone to give 3D depth just like reference image)
        far_leg_mask = (x_grid < cx) & (y_grid > hip_y) & (deformed_arr[:, :, 3] > 20)
        for c in range(3):
            deformed_arr[:, :, c] = np.where(far_leg_mask, deformed_arr[:, :, c] * 0.82, deformed_arr[:, :, c])

        step_img = Image.fromarray(np.clip(deformed_arr, 0, 255).astype(np.uint8), "RGBA")

        # Pitch tilt
        rot_angle = pitch
        if abs(rot_angle) > 0.1:
            step_img = step_img.rotate(rot_angle, resample=RESAMPLE_BICUBIC, expand=True)

        placed = step_img if is_facing_right else mirror_frame(step_img)
        f = place_on_canvas(placed, ox_offset=0, oy_offset=torso_dy, align_bottom=True)
        frames.append(f)

    return frames


# ── Natural Idle ─────────────────────────────────────────────────────────────

def build_goku_idle(base: Image.Image, is_facing_right: bool = True) -> list:
    w, h = base.size
    frames = []
    
    stages = [
        (1.00, 1.00, 0, 0),
        (1.02, 1.02, -1 if is_facing_right else 1, -2),
        (1.03, 1.03, -1 if is_facing_right else 1, -3),
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


# ── Kamehameha Attack ────────────────────────────────────────────────────────

def build_goku_kamehameha(base: Image.Image) -> list:
    frames = []
    nw, nh = base.size
    crouch = base.resize((int(nw * 1.14), int(nh * 0.85)), RESAMPLE_LANCZOS)
    
    beam_configs = [
        (0, 0, 0),
        (40, 0, -2),
        (85, 0, -3),
        (115, 0, -4),
        (70, 0, -2),
        (20, 0, 0),
    ]
    
    for bl, rot, dy in beam_configs:
        f = place_on_canvas(crouch, ox_offset=-16, oy_offset=dy, align_bottom=True)
        draw = ImageDraw.Draw(f)
        cx, cy = (FRAME_SIZE // 2) + 14, (FRAME_SIZE // 2) - 8 + dy
        
        if bl == 0:
            for r in range(16, 0, -3):
                alpha = int(35 * (1 - r / 16))
                draw.ellipse([cx - 8 - r, cy - r, cx - 8 + r, cy + r], fill=(0, 180, 255, alpha))
            draw.ellipse([cx - 14, cy - 6, cx - 2, cy + 6], fill=(180, 245, 255, 240))
            draw_star(draw, cx - 8, cy, 6, (255, 255, 255, 255))
        elif bl > 5:
            draw.polygon([(cx, cy - 16), (cx + bl, cy - int(bl * 0.28)), (cx + int(bl * 1.18), cy), (cx + bl, cy + int(bl * 0.28)), (cx, cy + 16)], fill=(0, 150, 255, 210))
            draw.polygon([(cx, cy - 10), (cx + int(bl * 0.85), cy - int(bl * 0.16)), (cx + int(bl * 0.98), cy), (cx + int(bl * 0.85), cy + int(bl * 0.16)), (cx, cy + 10)], fill=(80, 220, 255, 240))
            draw.polygon([(cx, cy - 5), (cx + int(bl * 0.60), cy - int(bl * 0.08)), (cx + int(bl * 0.72), cy), (cx + int(bl * 0.60), cy + int(bl * 0.08)), (cx, cy + 5)], fill=(255, 255, 255, 255))
            
            for ri in range(3):
                rx = cx + 20 + (ri * 26)
                draw.ellipse([rx - 7, cy - 14, rx + 7, cy + 14], outline=(150, 240, 255, 240), width=2)
                
            for ei in range(5):
                ex = cx + int(bl * 0.5) + (ei * 8)
                ey = cy - 12 + (ei * 5)
                draw.ellipse([ex, ey, ex + 3, ey + 3], fill=(255, 255, 255, 240))
                
        frames.append(f)
    return frames


# ── Full Goku Sprite Sheet Builder ───────────────────────────────────────────

def generate_all_goku_sprites():
    base = get_clean_goku(FRAME_SIZE)

    # 1. Authentic 6-Phase Walk Cycles
    walk_r = build_6_phase_human_walk(base, is_facing_right=True)
    walk_l = build_6_phase_human_walk(base, is_facing_right=False)

    # 2. Idle Stance
    idle = build_goku_idle(base, is_facing_right=True)
    idle_f = build_goku_idle(base, is_facing_right=False)

    # 3. Blink
    blink_f = place_on_canvas(base, 0, 0, align_bottom=True)
    db = ImageDraw.Draw(blink_f)
    ex1, ey1 = (FRAME_SIZE // 2) - 9, (FRAME_SIZE // 2) - 48
    ex2, ey2 = (FRAME_SIZE // 2) + 12, (FRAME_SIZE // 2) - 48
    db.arc([ex1 - 6, ey1 - 4, ex1 + 6, ey1 + 6], 180, 360, fill=(20, 20, 20, 255), width=2)
    db.arc([ex2 - 6, ey2 - 4, ex2 + 6, ey2 + 6], 180, 360, fill=(20, 20, 20, 255), width=2)
    blink = [place_on_canvas(base, 0, 0, align_bottom=True), blink_f, blink_f, place_on_canvas(base, 0, 0, align_bottom=True)]

    # 4. Roar -> Kamehameha Wave!
    roar = build_goku_kamehameha(base)

    # 5. Happy (Victory wave & Super Saiyan gold sparks!)
    happy_frames = []
    for i in range(4):
        rot = 4 if i % 2 == 0 else -4
        dy = -5 if i % 2 == 0 else 0
        f = place_on_canvas(base.rotate(rot, resample=RESAMPLE_BICUBIC, expand=True), 0, dy, align_bottom=True)
        d = ImageDraw.Draw(f)
        draw_star(d, 35, 35, 10, (255, 215, 0, 240))
        draw_star(d, 155, 30, 10, (255, 230, 50, 240))
        draw_star(d, 140, 75, 7, (255, 245, 120, 240))
        draw_star(d, 45, 80, 7, (255, 215, 0, 240))
        happy_frames.append(f)

    # 6. Idea (4-Star Dragon Ball)
    idea_frames = []
    for i in range(4):
        f = place_on_canvas(base, 0, 0, align_bottom=True)
        d = ImageDraw.Draw(f)
        hx, hy = (FRAME_SIZE // 2), (FRAME_SIZE // 2) - 72
        for r in range(16, 0, -2):
            d.ellipse([hx - r, hy - r, hx + r, hy + r], fill=(255, 160, 20, 40))
        d.ellipse([hx - 11, hy - 11, hx + 11, hy + 11], fill=(255, 175, 30, 255), outline=(255, 220, 60, 255), width=2)
        for sx, sy in [(hx - 4, hy - 4), (hx + 4, hy - 4), (hx - 4, hy + 4), (hx + 4, hy + 4)]:
            draw_star(d, sx, sy, 3, (220, 30, 20, 255))
        draw_star(d, hx + 15, hy - 12, 5, (255, 255, 255, 240))
        idea_frames.append(f)

    # 7. Work (Martial Arts Shadow Boxing)
    work = []
    for i in range(4):
        rot = 4 if i % 2 == 0 else -4
        dy = -3 if i % 2 == 0 else 0
        f = place_on_canvas(base.rotate(rot, resample=RESAMPLE_BICUBIC, expand=True), 0, dy, align_bottom=True)
        d = ImageDraw.Draw(f)
        for px, py in [(140, 90), (150, 110), (135, 130)]:
            d.line([(px, py), (px + 15, py)], fill=(255, 255, 255, 220), width=2)
            draw_star(d, px + 18, py, 4, (255, 220, 50, 240))
        work.append(f)

    # 8. Sit (Meditative Monk Pose)
    nw, nh = base.size
    crouch = base.resize((int(nw * 1.08), int(nh * 0.85)), RESAMPLE_LANCZOS)
    sit = [
        place_on_canvas(crouch, 0, 4, align_bottom=True),
        place_on_canvas(crouch, 0, 3, align_bottom=True),
        place_on_canvas(crouch, 0, 4, align_bottom=True),
        place_on_canvas(crouch, 0, 5, align_bottom=True),
    ]

    # 9. Sleep (Sleeping with Snot Bubble)
    sleep_w = int(nw * 1.08)
    sleep_h = int(nh * 0.78)
    loaf = base.resize((sleep_w, sleep_h), RESAMPLE_LANCZOS)
    zzz_pos = [
        [(135, 65, "z", 200)],
        [(133, 50, "z", 220), (148, 32, "z", 190)],
        [(130, 38, "z", 230), (145, 20, "Z", 210), (160, 6, "z", 170)],
        [(128, 28, "z", 240), (142, 12, "Z", 230), (158, -2, "Z", 200)],
    ]
    sleep = []
    for i, z_list in enumerate(zzz_pos):
        f = place_on_canvas(loaf, 0, 8 + (i % 2), align_bottom=True)
        draw = ImageDraw.Draw(f)
        draw.ellipse([86, 76, 96, 86], fill=(160, 220, 255, 180), outline=(220, 240, 255, 230))
        for zx, zy, ztxt, alpha in z_list:
            draw.text((zx, zy), ztxt, fill=(255, 200, 60, alpha))
            draw_dust_puff(draw, zx - 6, zy + 6, 4)
        sleep.append(f)

    wake = [
        sleep[0],
        place_on_canvas(crouch, 0, 4, align_bottom=True),
        place_on_canvas(base, 0, 0, align_bottom=True),
        place_on_canvas(base, 0, -4, align_bottom=True),
    ]

    # 10. Jump (Flying Nimbus Cloud)
    f_j0 = place_on_canvas(crouch, 0, 10, align_bottom=True)
    f_j1 = place_on_canvas(base.rotate(4, resample=RESAMPLE_BICUBIC, expand=True), 0, -25, align_bottom=False)
    d1 = ImageDraw.Draw(f_j1)
    d1.ellipse([70, 140, 125, 168], fill=(255, 225, 60, 240), outline=(230, 180, 20, 255))
    d1.ellipse([60, 145, 90, 172], fill=(255, 235, 90, 240))
    d1.ellipse([100, 144, 135, 172], fill=(255, 235, 90, 240))
    
    f_j2 = place_on_canvas(base.rotate(-3, resample=RESAMPLE_BICUBIC, expand=True), 0, -42, align_bottom=False)
    d2 = ImageDraw.Draw(f_j2)
    d2.ellipse([70, 140, 125, 168], fill=(255, 225, 60, 240), outline=(230, 180, 20, 255))
    draw_star(d2, 150, 30, 8, (255, 230, 50, 240))
    
    f_j3 = place_on_canvas(base, 0, -18, align_bottom=False)
    jump = [f_j0, f_j1, f_j2, f_j3]

    # 11. Fall
    f_fall = base.rotate(-18, resample=RESAMPLE_BICUBIC, expand=True)
    fall = []
    for i in range(4):
        f = place_on_canvas(f_fall, 0, i * 4, align_bottom=False)
        df = ImageDraw.Draw(f)
        for wx in [35, 70, 120, 155]:
            y1 = ((wx * 4 + i * 25) % 140) + 15
            df.line([(wx, y1), (wx, y1 + 35)], fill=(200, 230, 255, 190), width=2)
        fall.append(f)

    # 12. Land
    f_l0 = place_on_canvas(crouch, 0, 10, align_bottom=True)
    dl0 = ImageDraw.Draw(f_l0)
    draw_dust_puff(dl0, 45, 165, 16)
    draw_dust_puff(dl0, 145, 165, 16)
    land = [f_l0, place_on_canvas(base, 0, 4, align_bottom=True), place_on_canvas(base, 0, 0, align_bottom=True), place_on_canvas(base, 0, 0, align_bottom=True)]

    # 13. Drag
    drag = [
        place_on_canvas(base.rotate(-4, resample=RESAMPLE_BICUBIC, expand=True), 0, 4, align_bottom=False),
        place_on_canvas(base, 0, 4, align_bottom=False),
        place_on_canvas(base.rotate(4, resample=RESAMPLE_BICUBIC, expand=True), 0, 4, align_bottom=False),
        place_on_canvas(base, 0, 4, align_bottom=False),
    ]

    # 14. Sad & Cry
    f_cry = place_on_canvas(base.rotate(3, resample=RESAMPLE_BICUBIC, expand=True), 0, 2, align_bottom=True)
    dc = ImageDraw.Draw(f_cry)
    dc.ellipse([140, 80, 148, 92], fill=(0, 200, 255, 240))
    cry = [f_cry, f_cry, f_cry, f_cry]
    sad = [f_cry, place_on_canvas(base, 0, 2, align_bottom=True), f_cry, place_on_canvas(base, 0, 2, align_bottom=True)]

    # 15. Shrug
    f_shrug = place_on_canvas(base.rotate(3, resample=RESAMPLE_BICUBIC, expand=True), 0, 0, align_bottom=True)
    ds = ImageDraw.Draw(f_shrug)
    ds.ellipse([136, 46, 146, 60], fill=(120, 210, 255, 230))
    shrug = [f_shrug, place_on_canvas(base.rotate(-3, resample=RESAMPLE_BICUBIC, expand=True), 0, 0, align_bottom=True), f_shrug, place_on_canvas(base, 0, 0, align_bottom=True)]

    # 16. Music
    music = []
    note_pos = [
        [(25, 40, (255, 80, 20, 240)), (145, 30, (255, 180, 20, 240))],
        [(35, 25, (255, 140, 0, 240)), (155, 45, (255, 215, 0, 240))],
        [(20, 50, (255, 60, 20, 240)), (140, 20, (255, 200, 50, 240))],
        [(40, 30, (255, 160, 20, 240)), (150, 55, (255, 100, 20, 240))],
    ]
    for idx in range(4):
        rot = 3 if idx % 2 == 0 else -3
        dy = -3 if idx % 2 == 0 else 1
        f = place_on_canvas(base.rotate(rot, resample=RESAMPLE_BICUBIC, expand=True), 0, dy, align_bottom=True)
        dm = ImageDraw.Draw(f)
        for nx, ny, col in note_pos[idx % len(note_pos)]:
            draw_music_note(dm, nx, ny, col)
        music.append(f)

    anims = {
        "walk_right": walk_r,
        "walk_left": walk_l,
        "idle": idle,
        "idle_flip": idle_f,
        "blink": blink,
        "happy": happy_frames,
        "idea": idea_frames,
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

    print("Generating 6-Phase Walk Goku Sprites in assets/sprites/goku/:")
    for name, frames in anims.items():
        strip = create_strip(frames)
        dest = OUT_DIR / f"{name}.png"
        strip.save(dest)
        print(f"  [SAVED] {name}.png ({len(frames)} frames, {strip.width}x{strip.height})")


if __name__ == "__main__":
    generate_all_goku_sprites()
