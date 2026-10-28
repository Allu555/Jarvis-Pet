import numpy as np
from PIL import Image, ImageDraw, ImageFilter
from pathlib import Path
import math

SRC_DIR = Path(r"c:\Users\alame\Downloads\Desktop-Pet-main\Desktop-Pet-main\assets\dragon_sources")
OUT_DIR = Path(r"c:\Users\alame\Downloads\Desktop-Pet-main\Desktop-Pet-main\assets\sprites\dragon")
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


def load_view(filename: str, target_size: int = FRAME_SIZE) -> Image.Image:
    path = SRC_DIR / filename
    if not path.exists():
        path = SRC_DIR / "dragon_cutout.png"
    img = Image.open(path).convert("RGBA")
    bbox = img.getbbox()
    if bbox:
        img = img.crop(bbox)
    cw, ch = img.size
    scale = (target_size - 18) / max(cw, ch)
    nw, nh = max(1, int(cw * scale)), max(1, int(ch * scale))
    return img.resize((nw, nh), RESAMPLE_LANCZOS)


def mirror_frame(frame: Image.Image) -> Image.Image:
    return frame.transpose(Image.Transpose.FLIP_LEFT_RIGHT if hasattr(Image, "Transpose") else Image.FLIP_LEFT_RIGHT)


def ensure_facing_direction(img: Image.Image, want_facing_right: bool) -> Image.Image:
    """Strictly checks image alpha distribution to guarantee head/snout is facing desired direction."""
    arr = np.array(img)[:, :, 3] > 30
    w = arr.shape[1]
    # Check top half where head resides
    top_half = arr[:int(arr.shape[0] * 0.45), :]
    left_mass = np.sum(top_half[:, :int(w * 0.4)])
    right_mass = np.sum(top_half[:, int(w * 0.6):])
    
    # Currently facing right if right mass has higher head profile
    is_facing_right = (right_mass > left_mass)
    if is_facing_right != want_facing_right:
        return mirror_frame(img)
    return img


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


# ── True Quadruped Ground Walking Kinematics (Correct Direction) ─────────────

def build_quadruped_walk_cycle(base_img: Image.Image, is_facing_right: bool) -> list:
    """
    8-frame authentic quadruped ground walk cycle.
    Guarantees:
    - Moving right -> Faces RIGHT (Head on right side).
    - Moving left -> Faces LEFT (Head on left side).
    - Alternating 4-leg gait, ground-planted footfalls, spinal bob & tail counter-sway.
    """
    # Force guaranteed facing direction
    img = ensure_facing_direction(base_img, want_facing_right=is_facing_right)
    w, h = img.size
    arr = np.array(img, dtype=np.float32)

    frames = []
    num_frames = 8

    for i in range(num_frames):
        phase = (i / num_frames) * 2 * math.pi
        
        # Torso vertical translation (2 bobs per 4-leg walk cycle)
        dy = int(math.sin(phase * 2) * 2.5)
        # Forward/Backward pitch
        pitch = math.sin(phase) * 2.0
        
        deformed = np.copy(arr)
        leg_y_start = int(h * 0.58)
        
        for y in range(leg_y_start, h):
            depth = (y - leg_y_start) / (h - leg_y_start) # 0.0 at hip to 1.0 at foot
            # Front leg offset
            front_shift = math.sin(phase) * 4.5 * depth
            # Rear leg offset (out of phase)
            rear_shift = -math.sin(phase) * 4.0 * depth
            
            row = arr[y]
            new_row = np.zeros_like(row)
            mid_leg_x = int(w * 0.52)
            
            if is_facing_right:
                # Head/Front paws are at RIGHT (x > mid_leg_x), Hind legs at LEFT (x < mid_leg_x)
                s_f = int(front_shift)
                s_r = int(rear_shift)
                # Front legs (Right side)
                if s_f != 0:
                    new_row[mid_leg_x:] = np.roll(row[mid_leg_x:], s_f, axis=0)
                else:
                    new_row[mid_leg_x:] = row[mid_leg_x:]
                # Rear legs (Left side)
                if s_r != 0:
                    new_row[:mid_leg_x] = np.roll(row[:mid_leg_x], s_r, axis=0)
                else:
                    new_row[:mid_leg_x] = row[:mid_leg_x]
            else:
                # Head/Front paws are at LEFT (x < mid_leg_x), Hind legs at RIGHT (x > mid_leg_x)
                s_f = int(front_shift)
                s_r = int(rear_shift)
                # Front legs (Left side)
                if s_f != 0:
                    new_row[:mid_leg_x] = np.roll(row[:mid_leg_x], -s_f, axis=0)
                else:
                    new_row[:mid_leg_x] = row[:mid_leg_x]
                # Rear legs (Right side)
                if s_r != 0:
                    new_row[mid_leg_x:] = np.roll(row[mid_leg_x:], -s_r, axis=0)
                else:
                    new_row[mid_leg_x:] = row[mid_leg_x:]
                    
            deformed[y] = new_row

        step_img = Image.fromarray(np.clip(deformed, 0, 255).astype(np.uint8), "RGBA")
        
        # Subtle wing flexion
        sx = 1.0 + math.cos(phase * 2) * 0.02
        sy = 1.0 - math.cos(phase * 2) * 0.02
        cur_w = max(1, int(w * sx))
        cur_h = max(1, int(h * sy))
        scaled = step_img.resize((cur_w, cur_h), RESAMPLE_LANCZOS)
        
        rot_angle = pitch if is_facing_right else -pitch
        if abs(rot_angle) > 0.3:
            scaled = scaled.rotate(rot_angle, resample=RESAMPLE_BICUBIC, expand=True)

        f = place_on_canvas(scaled, ox_offset=0, oy_offset=dy, align_bottom=True)
        frames.append(f)

    return frames


# ── Realistic Idle (Facing Right & Facing Left) ──────────────────────────────

def build_realistic_idle(base_img: Image.Image, is_facing_right: bool = True) -> list:
    img = ensure_facing_direction(base_img, want_facing_right=is_facing_right)
    w, h = img.size
    frames = []
    
    breath_stages = [
        (1.00, 1.00, 0, 0),
        (1.02, 1.03, -1 if is_facing_right else 1, -2),
        (1.03, 1.04, -1 if is_facing_right else 1, -3),
        (1.01, 1.01, 0, -1),
    ]
    
    for sx, sy, rot, dy in breath_stages:
        cur_w = max(1, int(w * sx))
        cur_h = max(1, int(h * sy))
        scaled = img.resize((cur_w, cur_h), RESAMPLE_LANCZOS)
        if rot != 0:
            scaled = scaled.rotate(rot, resample=RESAMPLE_BICUBIC, expand=True)
        f = place_on_canvas(scaled, ox_offset=0, oy_offset=dy, align_bottom=True)
        frames.append(f)
        
    return frames


# ── Realistic Roar & Inferno (Facing Right) ──────────────────────────────────

def build_realistic_roar(base_img: Image.Image) -> list:
    img = ensure_facing_direction(base_img, want_facing_right=True)
    frames = []
    flame_configs = [
        (0, 0, 0),         # Inhale
        (35, -3, -2),      # Ignition
        (80, -6, -3),      # Inferno eruption
        (105, -7, -4),     # Continuous blast
        (60, -4, -2),      # Flame dispersal
        (18, 0, 0),        # Lingering sparks
    ]
    
    for fl, rot, dy in flame_configs:
        cur = img.rotate(rot, resample=RESAMPLE_BICUBIC, expand=True) if rot != 0 else img
        f = place_on_canvas(cur, ox_offset=-15, oy_offset=dy, align_bottom=True)
        
        if fl > 5:
            draw = ImageDraw.Draw(f)
            # Snout on right side
            hx, hy = (FRAME_SIZE // 2) + 26, (FRAME_SIZE // 2) - 8 + dy
            # Outer crimson
            draw.polygon([(hx, hy), (hx + fl, hy - int(fl * 0.40)), (hx + int(fl * 1.18), hy), (hx + fl, hy + int(fl * 0.40))], fill=(255, 45, 10, 215))
            # Mid blaze orange
            draw.polygon([(hx, hy), (hx + int(fl * 0.82), hy - int(fl * 0.24)), (hx + int(fl * 0.96), hy), (hx + int(fl * 0.82), hy + int(fl * 0.24))], fill=(255, 150, 15, 235))
            # White hot plasma
            draw.polygon([(hx, hy), (hx + int(fl * 0.52), hy - int(fl * 0.10)), (hx + int(fl * 0.65), hy), (hx + int(fl * 0.52), hy + int(fl * 0.10))], fill=(255, 255, 210, 255))
            # Sparks
            for ei in range(6):
                ex = hx + int(fl * 0.5) + (ei * 9)
                ey = hy - 12 + (ei * 5) + int(math.sin(ei * 1.6) * 5)
                draw.ellipse([ex, ey, ex + 3, ey + 3], fill=(255, 225, 40, 240))
                
        frames.append(f)
    return frames


# ── Full Sprite Sheet Builder ────────────────────────────────────────────────

def generate_all_realistic_sprites():
    # Load raw profile cutouts
    # Note: dragon_left in sources had head on right, dragon_right had head on left
    raw_prof_a = load_view("dragon_left.png")
    raw_prof_b = load_view("dragon_right.png")

    ground_right = ensure_facing_direction(raw_prof_a, want_facing_right=True)
    ground_left = ensure_facing_direction(raw_prof_b, want_facing_right=False)
    
    ground_front = load_view("dragon_front.png")
    fly_front = load_view("fly_frontal.png")
    fly_dorsal = load_view("fly_dorsal.png")

    # 1. Real Quadruped Ground Walk (8 frames)
    # walk_right MUST face RIGHT
    walk_r = build_quadruped_walk_cycle(ground_right, is_facing_right=True)
    # walk_left MUST face LEFT
    walk_l = build_quadruped_walk_cycle(ground_left, is_facing_right=False)

    # 2. Real Ground Idle
    # idle faces RIGHT, idle_flip faces LEFT
    idle = build_realistic_idle(ground_right, is_facing_right=True)
    idle_f = build_realistic_idle(ground_left, is_facing_right=False)

    # 3. Blink
    blink = [place_on_canvas(ground_right, 0, 0, align_bottom=True)] * 4

    # 4. Roar (Facing right)
    roar = build_realistic_roar(ground_right)

    # 5. Sit / Perch
    sit = [
        place_on_canvas(ground_right, 0, 4, align_bottom=True),
        place_on_canvas(ground_right, 0, 3, align_bottom=True),
        place_on_canvas(ground_right, 0, 4, align_bottom=True),
        place_on_canvas(ground_right, 0, 5, align_bottom=True),
    ]

    # 6. Sleep
    nw, nh = ground_right.size
    loaf = ground_right.resize((int(nw * 1.05), int(nh * 0.74)), RESAMPLE_LANCZOS)
    zzz_pos = [
        [(135, 70, "z", 200)],
        [(133, 56, "z", 220), (148, 38, "z", 190)],
        [(130, 44, "z", 230), (145, 26, "Z", 210), (160, 12, "z", 170)],
        [(128, 34, "z", 240), (142, 16, "Z", 230), (158, 4, "Z", 200)],
    ]
    sleep = []
    for i, z_list in enumerate(zzz_pos):
        f = place_on_canvas(loaf, 0, 10 + (i % 2), align_bottom=True)
        draw = ImageDraw.Draw(f)
        for zx, zy, ztxt, alpha in z_list:
            draw.text((zx, zy), ztxt, fill=(255, 210, 80, alpha))
            draw_dust_puff(draw, zx - 6, zy + 6, 4)
        sleep.append(f)

    wake = [
        sleep[0],
        place_on_canvas(ground_right, 0, 6, align_bottom=True),
        place_on_canvas(ground_right, 0, 0, align_bottom=True),
        place_on_canvas(ground_right, 0, -2, align_bottom=True),
    ]

    # 7. Happy
    happy_frames = []
    for i in range(4):
        rot = 3 if i % 2 == 0 else -3
        dy = -4 if i % 2 == 0 else 0
        f = place_on_canvas(ground_right.rotate(rot, resample=RESAMPLE_BICUBIC, expand=True), 0, dy, align_bottom=True)
        d = ImageDraw.Draw(f)
        draw_star(d, 40, 40, 9, (255, 215, 0, 240))
        draw_star(d, 150, 35, 9, (255, 215, 0, 240))
        draw_star(d, 135, 75, 7, (255, 230, 80, 240))
        happy_frames.append(f)

    # 8. Idea
    idea_frames = []
    for i in range(4):
        f = place_on_canvas(ground_right, 0, 0, align_bottom=True)
        d = ImageDraw.Draw(f)
        hx, hy = (FRAME_SIZE // 2) + 20, (FRAME_SIZE // 2) - 30
        d.ellipse([hx - 7, hy - 7, hx + 7, hy + 7], fill=(255, 160, 20, 240), outline=(255, 240, 90, 255), width=2)
        draw_star(d, hx, hy, 12, (255, 245, 120, 255))
        idea_frames.append(f)

    # 9. Work (Hoard)
    work = []
    for i in range(4):
        dy = -3 if (i % 2 == 0) else 0
        f = place_on_canvas(ground_right, -12, dy, align_bottom=True)
        draw = ImageDraw.Draw(f)
        draw.ellipse([110, 148, 180, 180], fill=(220, 170, 30, 255), outline=(170, 120, 15, 255), width=2)
        for cx, cy in [(120, 155), (135, 152), (150, 156), (165, 158), (128, 162), (144, 164), (160, 160)]:
            draw.ellipse([cx, cy, cx + 7, cy + 5], fill=(255, 225, 70, 255), outline=(200, 150, 20, 255), width=1)
        draw.ellipse([138, 140, 156, 162], fill=(30, 170, 160, 255), outline=(255, 230, 80, 255), width=1)
        draw_star(draw, 147, 148, 4, (255, 255, 255, 240))
        draw_star(draw, 122 + ((i * 18) % 45), 152, 4, (255, 240, 100, 230))
        work.append(f)

    # 10. Jump
    crouch = ground_front.resize((int(ground_front.width * 1.15), int(ground_front.height * 0.78)), RESAMPLE_LANCZOS)
    f_j0 = place_on_canvas(crouch, 0, 12, align_bottom=True)
    f_j1 = place_on_canvas(fly_front.rotate(6, resample=RESAMPLE_BICUBIC, expand=True), 0, -25, align_bottom=False)
    f_j2 = place_on_canvas(fly_dorsal.rotate(-4, resample=RESAMPLE_BICUBIC, expand=True), 0, -42, align_bottom=False)
    f_j3 = place_on_canvas(fly_front, 0, -18, align_bottom=False)
    jump = [f_j0, f_j1, f_j2, f_j3]

    # 11. Fall
    dived = fly_dorsal.rotate(-45, resample=RESAMPLE_BICUBIC, expand=True)
    fall = []
    for i in range(4):
        f = place_on_canvas(dived, 0, i * 4, align_bottom=False)
        df = ImageDraw.Draw(f)
        for wx in [20, 55, 90, 135, 168]:
            y1 = ((wx * 4 + i * 25) % 140) + 15
            df.line([(wx, y1), (wx, y1 + 40)], fill=(210, 235, 255, 190), width=2)
        fall.append(f)

    # 12. Land
    squash = ground_front.resize((int(ground_front.width * 1.18), int(ground_front.height * 0.78)), RESAMPLE_LANCZOS)
    f_l0 = place_on_canvas(squash, 0, 12, align_bottom=True)
    dl0 = ImageDraw.Draw(f_l0)
    draw_dust_puff(dl0, 30, 165, 16)
    draw_dust_puff(dl0, 160, 165, 16)
    land = [f_l0, place_on_canvas(ground_front, 0, 4, align_bottom=True), place_on_canvas(ground_right, 0, 0, align_bottom=True), place_on_canvas(ground_right, 0, 0, align_bottom=True)]

    # 13. Drag
    stretched = fly_front.resize((int(fly_front.width * 0.90), int(fly_front.height * 1.08)), RESAMPLE_LANCZOS)
    drag = [
        place_on_canvas(stretched.rotate(-3, resample=RESAMPLE_BICUBIC, expand=True), 0, 4, align_bottom=False),
        place_on_canvas(stretched, 0, 4, align_bottom=False),
        place_on_canvas(stretched.rotate(3, resample=RESAMPLE_BICUBIC, expand=True), 0, 4, align_bottom=False),
        place_on_canvas(stretched, 0, 4, align_bottom=False),
    ]

    # 14. Sad & Cry
    f_cry = place_on_canvas(ground_right.rotate(4, resample=RESAMPLE_BICUBIC, expand=True), 0, 2, align_bottom=True)
    dc = ImageDraw.Draw(f_cry)
    dc.ellipse([140, 80, 148, 92], fill=(0, 210, 255, 240))
    cry = [f_cry, f_cry, f_cry, f_cry]
    sad = [f_cry, place_on_canvas(ground_right, 0, 2, align_bottom=True), f_cry, place_on_canvas(ground_right, 0, 2, align_bottom=True)]

    # 15. Shrug
    shrug = [
        place_on_canvas(ground_right.rotate(4, resample=RESAMPLE_BICUBIC, expand=True), 0, 0, align_bottom=True),
        place_on_canvas(ground_right.rotate(-4, resample=RESAMPLE_BICUBIC, expand=True), 0, 0, align_bottom=True),
        place_on_canvas(ground_right.rotate(4, resample=RESAMPLE_BICUBIC, expand=True), 0, 0, align_bottom=True),
        place_on_canvas(ground_right, 0, 0, align_bottom=True),
    ]

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
        f = place_on_canvas(ground_right.rotate(rot, resample=RESAMPLE_BICUBIC, expand=True), 0, dy, align_bottom=True)
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

    print("Generating Correctly Oriented Dragon Sprites in assets/sprites/dragon/:")
    for name, frames in anims.items():
        strip = create_strip(frames)
        dest = OUT_DIR / f"{name}.png"
        strip.save(dest)
        print(f"  [SAVED] {name}.png ({len(frames)} frames, {strip.width}x{strip.height})")


if __name__ == "__main__":
    generate_all_realistic_sprites()
