import numpy as np
from PIL import Image, ImageDraw, ImageFilter
from pathlib import Path
import math

SRC_DIR = Path(r"c:\Users\alame\Downloads\Desktop-Pet-main\Desktop-Pet-main\assets\goth_girl_sources")
OUT_DIR = Path(r"c:\Users\alame\Downloads\Desktop-Pet-main\Desktop-Pet-main\assets\sprites\goth_girl")
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


def load_goth_asset(filename: str, target_height: int = 150) -> Image.Image:
    path = SRC_DIR / filename
    if not path.exists():
        path = SRC_DIR / "goth_girl_cutout.png"
    img = Image.open(path).convert("RGBA")
    bbox = img.getbbox()
    if bbox:
        img = img.crop(bbox)
    cw, ch = img.size
    scale = target_height / ch
    nw, nh = max(1, int(cw * scale)), max(1, int(ch * scale))
    return img.resize((nw, nh), RESAMPLE_LANCZOS)


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


def draw_butterfly(draw: ImageDraw.ImageDraw, cx: float, cy: float, size: float, fill: tuple):
    s = size / 2.0
    # Left upper wing
    draw.ellipse([cx - s * 1.8, cy - s * 1.5, cx, cy], fill=fill)
    # Right upper wing
    draw.ellipse([cx, cy - s * 1.5, cx + s * 1.8, cy], fill=fill)
    # Left lower wing
    draw.ellipse([cx - s * 1.3, cy - s * 0.3, cx, cy + s * 1.2], fill=fill)
    # Right lower wing
    draw.ellipse([cx, cy - s * 0.3, cx + s * 1.3, cy + s * 1.2], fill=fill)
    # Body
    draw.line([(cx, cy - s * 1.2), (cx, cy + s * 1.0)], fill=(30, 20, 45, 240), width=1)


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


def generate_all_goth_girl_sprites():
    base = load_goth_asset("goth_girl_cutout.png", target_height=146)
    w, h = base.size

    # 1. 6-Phase Authentic Walk Cycle
    walk_frames_raw = []
    for i in range(6):
        wf = load_goth_asset(f"walk_frame_{i}.png", target_height=146)
        walk_frames_raw.append(wf)

    walk_r = [place_on_canvas(wf, 0, 0, align_bottom=True) for wf in walk_frames_raw]
    walk_l = [place_on_canvas(mirror_frame(wf), 0, 0, align_bottom=True) for wf in walk_frames_raw]

    # 2. Idle Stance (Subtle breathing, dress flutter)
    idle = []
    idle_scales = [(1.00, 1.00, 0), (1.02, 1.01, -1), (1.03, 1.02, -2), (1.01, 1.01, -1)]
    for sx, sy, dy in idle_scales:
        cur_w = max(1, int(w * sx))
        cur_h = max(1, int(h * sy))
        scaled = base.resize((cur_w, cur_h), RESAMPLE_LANCZOS)
        f = place_on_canvas(scaled, 0, dy, align_bottom=True)
        idle.append(f)
    idle_f = [mirror_frame(f) for f in idle]

    # 3. Blink
    blink_f = place_on_canvas(base, 0, 0, align_bottom=True)
    d_bl = ImageDraw.Draw(blink_f)
    # Closed eyelashes curve
    ex, ey = (FRAME_SIZE // 2) - 4, (FRAME_SIZE // 2) - 38
    d_bl.arc([ex - 7, ey - 3, ex + 7, ey + 4], start=180, end=360, fill=(35, 30, 40, 255), width=2)
    blink = [place_on_canvas(base, 0, 0, align_bottom=True), blink_f, blink_f, place_on_canvas(base, 0, 0, align_bottom=True)]

    # 4. Happy (Lace umbrella twirl + floating butterflies & sparkles)
    umbrella_raw = load_goth_asset("umbrella_happy.png", target_height=150)
    happy_frames = []
    for i in range(4):
        rot = 3 if i % 2 == 0 else -3
        dy = -4 if i % 2 == 0 else 0
        f = place_on_canvas(umbrella_raw.rotate(rot, resample=RESAMPLE_BICUBIC, expand=True), 0, dy, align_bottom=True)
        d = ImageDraw.Draw(f)
        draw_butterfly(d, 40 + i * 10, 50 - i * 6, 12, (215, 160, 255, 230))
        draw_star(d, 150, 45, 7, (255, 215, 120, 240))
        draw_star(d, 35, 90, 5, (230, 180, 255, 220))
        happy_frames.append(f)

    # 5. Idea
    idea_frames = []
    for i in range(4):
        f = place_on_canvas(base, 0, 0, align_bottom=True)
        d = ImageDraw.Draw(f)
        hx, hy = (FRAME_SIZE // 2), (FRAME_SIZE // 2) - 68
        draw_butterfly(d, hx, hy, 16, (220, 170, 255, 255))
        draw_star(d, hx + 14, hy - 8, 6, (255, 230, 140, 240))
        idea_frames.append(f)

    # 6. Work (Reading Gothic Spellbook with glowing ancient runes)
    spellbook_raw = load_goth_asset("spellbook_work.png", target_height=140)
    work = []
    for i in range(4):
        dy = -2 if i % 2 == 0 else 0
        f = place_on_canvas(spellbook_raw, 0, dy, align_bottom=True)
        d = ImageDraw.Draw(f)
        # Glowing purple magic runes rising from pages
        rx, ry = 110 + i * 5, 85 - i * 6
        draw_star(d, rx, ry, 6, (190, 130, 255, 240))
        draw_butterfly(d, rx + 18, ry - 10, 8, (210, 160, 255, 220))
        work.append(f)

    # 7. Sit (Sitting gracefully)
    sit_raw = load_goth_asset("spellbook_work.png", target_height=138)
    sit = [
        place_on_canvas(sit_raw, 0, 0, align_bottom=True),
        place_on_canvas(sit_raw, 0, -1, align_bottom=True),
        place_on_canvas(sit_raw, 0, 0, align_bottom=True),
        place_on_canvas(sit_raw, 0, -1, align_bottom=True),
    ]

    # 8. Sleep (Curled up hugging black cat with soft breathing & rising Zzzs)
    sleep_raw = load_goth_asset("cat_sleep.png", target_height=135)
    zzz_pos = [
        [(135, 55, "z", 190)],
        [(133, 42, "z", 210), (148, 28, "z", 180)],
        [(130, 32, "z", 230), (145, 18, "Z", 200)],
        [(128, 24, "z", 240), (142, 10, "Z", 220)],
    ]
    sleep = []
    for i, z_list in enumerate(zzz_pos):
        dy = 2 if i % 2 == 1 else 0
        f = place_on_canvas(sleep_raw, 0, dy, align_bottom=True)
        d = ImageDraw.Draw(f)
        for zx, zy, txt, alpha_v in z_list:
            d.text((zx, zy), txt, fill=(210, 180, 255, alpha_v))
        sleep.append(f)

    # 9. Wake
    wake = [
        place_on_canvas(sleep_raw, 0, 0, align_bottom=True),
        place_on_canvas(base, 0, 4, align_bottom=True),
        place_on_canvas(base, 0, -2, align_bottom=True),
        place_on_canvas(base, 0, 0, align_bottom=True),
    ]

    # 10. Cry
    f_cry = place_on_canvas(base, 0, 2, align_bottom=True)
    d_cry = ImageDraw.Draw(f_cry)
    cx_eye = (FRAME_SIZE // 2) - 4
    cy_eye = (FRAME_SIZE // 2) - 34
    d_cry.ellipse([cx_eye - 4, cy_eye + 4, cx_eye + 2, cy_eye + 12], fill=(160, 215, 255, 230))
    d_cry.ellipse([cx_eye + 6, cy_eye + 6, cx_eye + 12, cy_eye + 14], fill=(160, 215, 255, 230))
    cry = [place_on_canvas(base, 0, 0, align_bottom=True), f_cry, f_cry, place_on_canvas(base, 0, 0, align_bottom=True)]

    # 11. Sad
    sad = [
        place_on_canvas(base.rotate(3, resample=RESAMPLE_BICUBIC, expand=True), 0, 3, align_bottom=True),
        place_on_canvas(base.rotate(4, resample=RESAMPLE_BICUBIC, expand=True), 0, 4, align_bottom=True),
        place_on_canvas(base.rotate(3, resample=RESAMPLE_BICUBIC, expand=True), 0, 3, align_bottom=True),
        place_on_canvas(base, 0, 1, align_bottom=True),
    ]

    # 12. Shrug
    f_shrug = place_on_canvas(base.rotate(-3, resample=RESAMPLE_BICUBIC, expand=True), 0, -2, align_bottom=True)
    shrug = [f_shrug, place_on_canvas(base, 0, 0, align_bottom=True), f_shrug, place_on_canvas(base, 0, 0, align_bottom=True)]

    # 13. Jump (Acrobatic butterfly leap)
    crouch = base.resize((int(w * 1.12), int(h * 0.72)), RESAMPLE_LANCZOS)
    f_j0 = place_on_canvas(crouch, 0, 0, align_bottom=True)

    launch = base.rotate(15, resample=RESAMPLE_BICUBIC, expand=True)
    f_j1 = place_on_canvas(launch, 0, -28, align_bottom=True)
    dj1 = ImageDraw.Draw(f_j1)
    draw_dust_puff(dj1, (FRAME_SIZE // 2) - 20, FRAME_SIZE - 20, 10)

    f_j2 = place_on_canvas(base.rotate(-5, resample=RESAMPLE_BICUBIC, expand=True), 0, -45, align_bottom=True)
    dj2 = ImageDraw.Draw(f_j2)
    draw_butterfly(dj2, 45, 45, 14, (220, 160, 255, 240))
    draw_butterfly(dj2, 150, 40, 12, (200, 140, 255, 230))

    f_j3 = place_on_canvas(base.rotate(-15, resample=RESAMPLE_BICUBIC, expand=True), 0, -18, align_bottom=True)
    jump = [f_j0, f_j1, f_j2, f_j3]

    # 14. Roar -> Butterfly Magic Awakening (Purple vortex, butterfly storm)
    magic_raw = load_goth_asset("butterfly_magic.png", target_height=152)
    roar = []
    for i in range(6):
        rot = (i % 2 * 4) - 2
        f = place_on_canvas(magic_raw.rotate(rot, resample=RESAMPLE_BICUBIC, expand=True), 0, -4, align_bottom=True)
        d = ImageDraw.Draw(f)
        # Multiple swirling butterflies
        for b_idx in range(4):
            angle = i * 1.2 + b_idx * 1.57
            bx = (FRAME_SIZE // 2) + math.cos(angle) * (38 + b_idx * 6)
            by = (FRAME_SIZE // 2) - 15 + math.sin(angle) * (28 + b_idx * 4)
            draw_butterfly(d, bx, by, 10 + b_idx * 2, (220, 140, 255, 240))
            draw_star(d, bx + 6, by - 6, 4, (255, 220, 150, 220))
        roar.append(f)

    # 15. Drag (Dangling gracefully)
    drag_scaled = base.resize((int(w * 0.88), int(h * 1.06)), RESAMPLE_LANCZOS)
    drag = []
    for ang in [-3, 0, 3, 0]:
        rot = drag_scaled.rotate(ang, resample=RESAMPLE_BICUBIC, expand=True)
        f = place_on_canvas(rot, 0, -6, align_bottom=True)
        drag.append(f)

    # 16. Fall
    dived = base.rotate(-25, resample=RESAMPLE_BICUBIC, expand=True)
    fall = []
    for i in range(4):
        f = place_on_canvas(dived, 0, -15 + i * 4, align_bottom=True)
        d = ImageDraw.Draw(f)
        draw_butterfly(d, 40, 60 + i * 10, 10, (200, 150, 255, 200))
        fall.append(f)

    # 17. Land
    f_land0 = place_on_canvas(crouch, 0, 0, align_bottom=True)
    d_l0 = ImageDraw.Draw(f_land0)
    draw_dust_puff(d_l0, (FRAME_SIZE // 2) - 25, FRAME_SIZE - 18, 12)
    draw_dust_puff(d_l0, (FRAME_SIZE // 2) + 25, FRAME_SIZE - 18, 12)
    land = [f_land0, place_on_canvas(base, 0, 0, align_bottom=True), place_on_canvas(base, 0, 0, align_bottom=True), place_on_canvas(base, 0, 0, align_bottom=True)]

    # 18. Music
    music = []
    note_pos = [
        [(25, 40, (220, 140, 255, 240)), (145, 30, (255, 180, 220, 240))],
        [(35, 25, (255, 180, 220, 240)), (155, 45, (180, 120, 255, 240))],
        [(20, 50, (180, 120, 255, 240)), (140, 20, (220, 140, 255, 240))],
        [(40, 30, (220, 140, 255, 240)), (150, 55, (255, 200, 140, 240))],
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

    print("Generating Gothic Butterfly Girl Sprites in assets/sprites/goth_girl/:")
    for name, frames in anims.items():
        strip = create_strip(frames)
        dest = OUT_DIR / f"{name}.png"
        strip.save(dest)
        print(f"  [SAVED] {name}.png ({len(frames)} frames, {strip.width}x{strip.height})")


if __name__ == "__main__":
    generate_all_goth_girl_sprites()
