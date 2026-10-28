import numpy as np
from PIL import Image, ImageDraw, ImageFilter
from pathlib import Path
import scipy.ndimage as ndi
import math

BASE_DIR = Path(__file__).parent.parent
SRC_DIR = Path(__file__).parent / "venom_sources"
OUT_DIR = Path(__file__).parent / "sprites" / "venom"
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


def get_clean_venom(target_size: int = FRAME_SIZE) -> Image.Image:
    cutout = Image.open(SRC_DIR / "venom_cutout.png").convert("RGBA")
    bbox = cutout.getbbox()
    if bbox:
        cutout = cutout.crop(bbox)
    cw, ch = cutout.size
    scale = (target_size - 24) / max(cw, ch)
    nw, nh = max(1, int(cw * scale)), max(1, int(ch * scale))
    return cutout.resize((nw, nh), RESAMPLE_LANCZOS)


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
    draw.ellipse([cx - r, cy - r // 2, cx + r, cy + r // 2], fill=(220, 225, 235, 210))
    draw.ellipse([cx - r // 2, cy - r, cx + r // 2, cy], fill=(235, 240, 245, 230))


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


# ── Full 6-Phase Symbiote Prowl Walk Engine ────────────────────────────────

def build_6_phase_venom_prowl(base: Image.Image, is_facing_right: bool = True) -> list:
    """
    Constructs the predatory 6-phase side-profile walking prowl matching the reference walk cycle:
    Phase 0 (Contact 1): Powerful lead stride (heel strike, claws extended), trail leg push-off, opposite arm swing.
    Phase 1 (Down 1): Low predatory crouch (knee flexed deep, foot flat), body squashes down (dy=+6px), drool drip.
    Phase 2 (Pass 1): Stance leg straightens, body rises to apex (dy=-6px), swing leg lifts high at knee.
    Phase 3 (Contact 2): Opposite contact stride (far leg forward, near leg back).
    Phase 4 (Down 2): Opposite low crouch recoil (far leg planted, knee flexed, body squashes down).
    Phase 5 (Pass 2): Opposite pass pose (far leg straight supporting, near leg lifts high at knee).
    """
    w, h = base.size
    arr = np.array(base, dtype=np.float32)
    frames = []

    # 6 Keyframe configurations:
    # (torso_dy, pitch_deg, n_hip, n_knee, n_foot, f_hip, f_knee, f_foot, n_arm, f_arm, sy, tongue_whip, drool_off)
    phase_configs = [
        # Frame 1: Contact 1 (predatory split stride)
        (0, 3.5,   24, 10,  12,   -24, 15, -15,  -28,  28, 1.00,  5.0, 0),
        # Frame 2: Down 1 (recoil squash / low crouch)
        (6, 5.0,   14, -22,  0,   -12, 38, -10,  -14,  14, 0.95,  2.0, 2),
        # Frame 3: Pass 1 (high apex prowl)
        (-6, -1.0,  0,   2,  0,    20, -48,  20,    8,  -8, 1.04, -3.0, 4),
        # Frame 4: Contact 2 (opposite split stride)
        (0, 3.5,  -24, 15, -15,    24, 10,  12,   28, -28, 1.00, -5.0, 0),
        # Frame 5: Down 2 (recoil squash / low crouch)
        (6, 5.0,  -12, 38, -10,    14, -22,  0,   14, -14, 0.95, -2.0, 2),
        # Frame 6: Pass 2 (high apex prowl)
        (-6, -1.0, 20, -48,  20,    0,   2,  0,   -8,   8, 1.04,  3.0, 4),
    ]

    hip_y = int(h * 0.54)
    knee_y = int(h * 0.75)
    shoulder_y = int(h * 0.36)
    cx = w * 0.50

    y_grid, x_grid = np.indices((h, w), dtype=np.float32)

    for torso_dy, pitch, n_hip, n_knee, n_foot, f_hip, f_knee, f_foot, n_arm, f_arm, sy, tongue_whip, drool_off in phase_configs:
        map_y = np.copy(y_grid)
        map_x = np.copy(x_grid)

        # 1. Torso squash/stretch
        for y in range(h):
            if y < hip_y:
                map_y[y, :] = y / sy

        # 2. Articulated Legs (Hip swing, knee bend, foot angle)
        for y in range(hip_y, h):
            near_dx = math.sin(math.radians(n_hip)) * (y - hip_y) * 0.90
            if y > knee_y:
                knee_frac = (y - knee_y) / (h - knee_y)
                near_dx += math.sin(math.radians(n_knee)) * (y - knee_y) * 0.80
                near_dx += math.sin(math.radians(n_foot)) * knee_frac * 6.5

            far_dx = math.sin(math.radians(f_hip)) * (y - hip_y) * 0.90
            if y > knee_y:
                knee_frac = (y - knee_y) / (h - knee_y)
                far_dx += math.sin(math.radians(f_knee)) * (y - knee_y) * 0.80
                far_dx += math.sin(math.radians(f_foot)) * knee_frac * 6.5

            x_weights = 1.0 / (1.0 + np.exp(-(x_grid[y, :] - cx) / 7.0))
            combined_dx = (1.0 - x_weights) * far_dx + x_weights * near_dx
            map_x[y, :] -= combined_dx

        # 3. Dynamic Arms & Claws
        for y in range(shoulder_y, int(h * 0.74)):
            near_arm_dx = math.sin(math.radians(n_arm)) * (y - shoulder_y) * 0.80
            far_arm_dx = math.sin(math.radians(f_arm)) * (y - shoulder_y) * 0.80
            arm_mask_near = np.clip((x_grid[y, :] - w * 0.55) / (w * 0.25), 0, 1)
            arm_mask_far = np.clip((w * 0.45 - x_grid[y, :]) / (w * 0.25), 0, 1)
            map_x[y, :] -= arm_mask_near * near_arm_dx + arm_mask_far * far_arm_dx

        # 4. Tongue whip (right side of character face)
        for y in range(int(h * 0.32), int(h * 0.55)):
            tongue_mask = np.clip((x_grid[y, :] - w * 0.55) / (w * 0.30), 0, 1)
            map_x[y, :] -= tongue_mask * tongue_whip

        # Sample channels
        deformed_channels = []
        for c in range(4):
            ch = ndi.map_coordinates(arr[:, :, c], [map_y, map_x], order=1, mode='constant', cval=0.0)
            deformed_channels.append(ch)

        deformed_arr = np.dstack(deformed_channels)

        # Depth shading on far leg (18% darker tone)
        far_leg_mask = (x_grid < cx) & (y_grid > hip_y) & (deformed_arr[:, :, 3] > 20)
        for c in range(3):
            deformed_arr[:, :, c] = np.where(far_leg_mask, deformed_arr[:, :, c] * 0.80, deformed_arr[:, :, c])

        step_img = Image.fromarray(np.clip(deformed_arr, 0, 255).astype(np.uint8), "RGBA")

        # Pitch tilt
        rot_angle = pitch
        if abs(rot_angle) > 0.1:
            step_img = step_img.rotate(rot_angle, resample=RESAMPLE_BICUBIC, expand=True)

        placed = step_img if is_facing_right else mirror_frame(step_img)
        f = place_on_canvas(placed, ox_offset=0, oy_offset=torso_dy, align_bottom=True)

        # Saliva droplet
        draw = ImageDraw.Draw(f)
        if is_facing_right:
            tx = (FRAME_SIZE // 2) + 32 + int(tongue_whip * 0.6)
            ty = (FRAME_SIZE // 2) - 10 + torso_dy + drool_off
            draw.ellipse([tx, ty + 12, tx + 3, ty + 17], fill=(130, 230, 255, 220))
        else:
            tx = (FRAME_SIZE // 2) - 34 - int(tongue_whip * 0.6)
            ty = (FRAME_SIZE // 2) - 10 + torso_dy + drool_off
            draw.ellipse([tx, ty + 12, tx + 3, ty + 17], fill=(130, 230, 255, 220))

        frames.append(f)

    return frames


# ── Venom Idle ───────────────────────────────────────────────────────────────

def build_venom_idle(base: Image.Image, is_facing_right: bool = True) -> list:
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


# ── "WE ARE VENOM!" Roar ─────────────────────────────────────────────────────

def build_venom_roar(base: Image.Image) -> list:
    frames = []
    blast_configs = [
        (0, 0, 0),
        (45, -3, -2),
        (90, -5, -4),
        (120, -6, -4),
        (75, -3, -2),
        (25, 0, 0),
    ]
    
    for tl, rot, dy in blast_configs:
        cur = base.rotate(rot, resample=RESAMPLE_BICUBIC, expand=True) if rot != 0 else base
        f = place_on_canvas(cur, ox_offset=-16, oy_offset=dy, align_bottom=True)
        draw = ImageDraw.Draw(f)
        cx, cy = (FRAME_SIZE // 2) + 24, (FRAME_SIZE // 2) - 15 + dy
        
        if tl > 5:
            draw.polygon([(cx, cy - 14), (cx + tl, cy - int(tl * 0.35)), (cx + int(tl * 1.15), cy), (cx + tl, cy + int(tl * 0.35)), (cx, cy + 14)], fill=(15, 18, 24, 255))
            draw.polygon([(cx, cy - 8), (cx + int(tl * 0.85), cy - int(tl * 0.20)), (cx + int(tl * 0.98), cy), (cx + int(tl * 0.85), cy + int(tl * 0.20)), (cx, cy + 8)], fill=(35, 40, 52, 255))
            
            for ri in range(3):
                rx = cx + 18 + (ri * 26)
                draw.arc([rx - 8, cy - 18, rx + 8, cy + 18], 270, 90, fill=(255, 255, 255, 240), width=3)
                
            draw.line([(cx - 5, cy), (cx + int(tl * 0.7), cy - 6)], fill=(220, 40, 60, 255), width=5)
            
            for ei in range(6):
                ex = cx + int(tl * 0.45) + (ei * 10)
                ey = cy - 14 + (ei * 6) + int(math.sin(ei * 1.5) * 6)
                draw.ellipse([ex, ey, ex + 4, ey + 4], fill=(120, 255, 60, 240))
                
        frames.append(f)
    return frames


# ── Full Venom Sprite Sheet Builder ──────────────────────────────────────────

def generate_all_venom_sprites():
    base = get_clean_venom(FRAME_SIZE)

    # 1. Authentic 6-Phase Predatory Prowl Cycles
    walk_r = build_6_phase_venom_prowl(base, is_facing_right=True)
    walk_l = build_6_phase_venom_prowl(base, is_facing_right=False)

    # 2. Idle Stance
    idle = build_venom_idle(base, is_facing_right=True)
    idle_f = build_venom_idle(base, is_facing_right=False)

    # 3. Blink
    blink_f = place_on_canvas(base, 0, 0, align_bottom=True)
    db = ImageDraw.Draw(blink_f)
    ex1, ey1 = (FRAME_SIZE // 2) - 6, (FRAME_SIZE // 2) - 42
    ex2, ey2 = (FRAME_SIZE // 2) + 20, (FRAME_SIZE // 2) - 36
    db.ellipse([ex1 - 10, ey1 - 4, ex1 + 10, ey1 + 4], fill=(255, 255, 255, 255), outline=(15, 18, 24, 255))
    db.ellipse([ex2 - 10, ey2 - 4, ex2 + 10, ey2 + 4], fill=(255, 255, 255, 255), outline=(15, 18, 24, 255))
    blink = [place_on_canvas(base, 0, 0, align_bottom=True), blink_f, blink_f, place_on_canvas(base, 0, 0, align_bottom=True)]

    # 4. Roar ("WE ARE VENOM!" Symbiote Blast)
    roar = build_venom_roar(base)

    # 5. Happy
    happy_frames = []
    for i in range(4):
        rot = 4 if i % 2 == 0 else -4
        dy = -5 if i % 2 == 0 else 0
        f = place_on_canvas(base.rotate(rot, resample=RESAMPLE_BICUBIC, expand=True), 0, dy, align_bottom=True)
        d = ImageDraw.Draw(f)
        draw_star(d, 35, 35, 10, (255, 255, 255, 240))
        draw_star(d, 155, 30, 10, (255, 255, 255, 240))
        draw_star(d, 140, 75, 8, (120, 255, 60, 240))
        draw_star(d, 45, 80, 8, (120, 255, 60, 240))
        happy_frames.append(f)

    # 6. Idea
    idea_frames = []
    for i in range(4):
        f = place_on_canvas(base, 0, 0, align_bottom=True)
        d = ImageDraw.Draw(f)
        hx, hy = (FRAME_SIZE // 2), (FRAME_SIZE // 2) - 68
        d.ellipse([hx - 9, hy - 9, hx + 9, hy + 9], fill=(255, 255, 255, 255), outline=(15, 18, 24, 255), width=2)
        draw_star(d, hx, hy, 14, (255, 255, 255, 255))
        draw_star(d, hx + 14, hy - 10, 5, (120, 255, 60, 240))
        idea_frames.append(f)

    # 7. Work
    work = []
    for i in range(4):
        rot = 4 if i % 2 == 0 else -4
        dy = -3 if i % 2 == 0 else 0
        f = place_on_canvas(base.rotate(rot, resample=RESAMPLE_BICUBIC, expand=True), 0, dy, align_bottom=True)
        d = ImageDraw.Draw(f)
        cx, cy = 135, 100
        d.rectangle([cx, cy, cx + 18, cy + 28], fill=(90, 45, 20, 255), outline=(60, 25, 10, 255), width=2)
        d.rectangle([cx + 2, cy + 2, cx + 16, cy + 12], fill=(200, 200, 210, 255))
        d.line([(110, 85), (145, 85)], fill=(255, 255, 255, 220), width=2)
        work.append(f)

    # 8. Sit
    nw, nh = base.size
    crouch = base.resize((int(nw * 1.12), int(nh * 0.82)), RESAMPLE_LANCZOS)
    sit = [
        place_on_canvas(crouch, 0, 4, align_bottom=True),
        place_on_canvas(crouch, 0, 3, align_bottom=True),
        place_on_canvas(crouch, 0, 4, align_bottom=True),
        place_on_canvas(crouch, 0, 5, align_bottom=True),
    ]

    # 9. Sleep
    sleep_w = int(nw * 1.18)
    sleep_h = int(nh * 0.65)
    loaf = base.resize((sleep_w, sleep_h), RESAMPLE_LANCZOS)
    zzz_pos = [
        [(135, 65, "z", 200)],
        [(133, 50, "z", 220), (148, 32, "z", 190)],
        [(130, 38, "z", 230), (145, 20, "Z", 210), (160, 6, "z", 170)],
        [(128, 28, "z", 240), (142, 12, "Z", 230), (158, -2, "Z", 200)],
    ]
    sleep = []
    for i, z_list in enumerate(zzz_pos):
        f = place_on_canvas(loaf, 0, 10 + (i % 2), align_bottom=True)
        draw = ImageDraw.Draw(f)
        for zx, zy, ztxt, alpha in z_list:
            draw.text((zx, zy), ztxt, fill=(120, 255, 60, alpha))
            draw_dust_puff(draw, zx - 6, zy + 6, 4)
        sleep.append(f)

    wake = [
        sleep[0],
        place_on_canvas(crouch, 0, 4, align_bottom=True),
        place_on_canvas(base, 0, 0, align_bottom=True),
        place_on_canvas(base, 0, -4, align_bottom=True),
    ]

    # 10. Jump
    f_j0 = place_on_canvas(crouch, 0, 10, align_bottom=True)
    f_j1 = place_on_canvas(base.rotate(4, resample=RESAMPLE_BICUBIC, expand=True), 0, -25, align_bottom=False)
    d1 = ImageDraw.Draw(f_j1)
    d1.line([(105, 75), (150, 0)], fill=(15, 18, 24, 255), width=3)
    d1.line([(107, 75), (152, 0)], fill=(255, 255, 255, 200), width=1)
    
    f_j2 = place_on_canvas(base.rotate(-3, resample=RESAMPLE_BICUBIC, expand=True), 0, -42, align_bottom=False)
    d2 = ImageDraw.Draw(f_j2)
    d2.line([(95, 75), (70, 0)], fill=(15, 18, 24, 255), width=3)
    draw_star(d2, 150, 30, 8, (255, 255, 255, 240))
    
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
            df.line([(wx, y1), (wx, y1 + 35)], fill=(180, 200, 220, 190), width=2)
        fall.append(f)

    # 12. Land
    f_l0 = place_on_canvas(crouch, 0, 10, align_bottom=True)
    dl0 = ImageDraw.Draw(f_l0)
    draw_dust_puff(dl0, 45, 165, 16)
    draw_dust_puff(dl0, 145, 165, 16)
    dl0.line([(35, 175), (60, 170), (80, 178)], fill=(15, 18, 24, 240), width=2)
    dl0.line([(125, 175), (150, 170), (170, 178)], fill=(15, 18, 24, 240), width=2)
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
    dc.ellipse([140, 80, 148, 92], fill=(120, 255, 60, 240))
    cry = [f_cry, f_cry, f_cry, f_cry]
    sad = [f_cry, place_on_canvas(base, 0, 2, align_bottom=True), f_cry, place_on_canvas(base, 0, 2, align_bottom=True)]

    # 15. Shrug
    f_shrug = place_on_canvas(base.rotate(3, resample=RESAMPLE_BICUBIC, expand=True), 0, 0, align_bottom=True)
    ds = ImageDraw.Draw(f_shrug)
    ds.ellipse([136, 46, 146, 60], fill=(255, 255, 255, 230))
    shrug = [f_shrug, place_on_canvas(base.rotate(-3, resample=RESAMPLE_BICUBIC, expand=True), 0, 0, align_bottom=True), f_shrug, place_on_canvas(base, 0, 0, align_bottom=True)]

    # 16. Music
    music = []
    note_pos = [
        [(25, 40, (255, 255, 255, 240)), (145, 30, (120, 255, 60, 240))],
        [(35, 25, (120, 255, 60, 240)), (155, 45, (255, 255, 255, 240))],
        [(20, 50, (255, 255, 255, 240)), (140, 20, (120, 255, 60, 240))],
        [(40, 30, (120, 255, 60, 240)), (150, 55, (255, 255, 255, 240))],
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

    print("Generating 6-Phase Walk Venom Sprites in assets/sprites/venom/:")
    for name, frames in anims.items():
        strip = create_strip(frames)
        dest = OUT_DIR / f"{name}.png"
        strip.save(dest)
        print(f"  [SAVED] {name}.png ({len(frames)} frames, {strip.width}x{strip.height})")


if __name__ == "__main__":
    generate_all_venom_sprites()
