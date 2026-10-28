import math
import random
from pathlib import Path
from PIL import Image, ImageDraw
import numpy as np

RESAMPLE_LANCZOS = getattr(getattr(Image, "Resampling", Image), "LANCZOS", Image.LANCZOS if hasattr(Image, "LANCZOS") else Image.BICUBIC)
RESAMPLE_BICUBIC = getattr(getattr(Image, "Resampling", Image), "BICUBIC", Image.BICUBIC if hasattr(Image, "BICUBIC") else Image.BILINEAR)

FRAME_SIZE = 192
OUT_DIR = Path(__file__).parent / "sprites" / "inosuke"
SOURCE_DIR = Path(__file__).parent / "inosuke_sources"
OUT_DIR.mkdir(parents=True, exist_ok=True)


def load_source(name: str) -> Image.Image:
    path = SOURCE_DIR / f"{name}.png"
    if path.exists():
        return Image.open(path).convert("RGBA")
    return Image.new("RGBA", (100, 150), (0, 0, 0, 0))


def create_sheet(frames: list) -> Image.Image:
    n = len(frames)
    sheet = Image.new("RGBA", (FRAME_SIZE * n, FRAME_SIZE), (0, 0, 0, 0))
    for i, f in enumerate(frames):
        sheet.paste(f, (i * FRAME_SIZE, 0), f)
    return sheet


def get_head_center_x(img: Image.Image) -> float:
    arr = np.array(img)
    alpha = arr[:, :, 3] > 0
    if not np.any(alpha):
        return img.width / 2.0
    y_indices, x_indices = np.where(alpha)
    top_mask = (y_indices < (y_indices.min() + (y_indices.max() - y_indices.min()) * 0.25))
    if not np.any(top_mask):
        return img.width / 2.0
    return float(np.mean(x_indices[top_mask]))


# ── Vector Effect Helpers ──

def draw_beast_katana(draw: ImageDraw.ImageDraw, x1: int, y1: int, x2: int, y2: int, serrated=True, color=(210, 230, 245, 240)):
    draw.line([(x1, y1), (x2, y2)], fill=color, width=3)
    draw.line([(x1, y1), (x2, y2)], fill=(255, 255, 255, 255), width=1)
    if serrated:
        for t in [0.3, 0.5, 0.7]:
            nx = int(x1 + (x2 - x1) * t)
            ny = int(y1 + (y2 - y1) * t)
            draw.line([(nx, ny), (nx + 4, ny - 2)], fill=(180, 210, 230, 240), width=2)


def draw_steam_puff(draw: ImageDraw.ImageDraw, cx: int, cy: int, r: int = 6):
    draw.ellipse([cx - r, cy - r // 2, cx + r, cy + r // 2], fill=(230, 230, 240, 190))


def draw_sparkle(draw: ImageDraw.ImageDraw, cx: int, cy: int, size: int = 8, color=(0, 220, 255, 240)):
    draw.line([cx - size, cy, cx + size, cy], fill=color, width=2)
    draw.line([cx, cy - size, cx, cy + size], fill=color, width=2)
    s2 = size // 2
    draw.line([cx - s2, cy - s2, cx + s2, cy + s2], fill=color, width=1)
    draw.line([cx - s2, cy + s2, cx + s2, cy - s2], fill=color, width=1)


def draw_music_note(draw: ImageDraw.ImageDraw, x: int, y: int, color=(0, 220, 255, 240)):
    draw.ellipse([x, y + 6, x + 5, y + 10], fill=color)
    draw.line([x + 4, y + 8, x + 4, y], fill=color, width=2)
    draw.line([x + 4, y, x + 8, y + 2], fill=color, width=2)


def generate_all():
    print("Generating Inosuke with True Reference Walk Cycle & Legendary Fall...")

    front_img = load_source("front")
    side_img = load_source("side")
    back_flex_img = load_source("back_flex")

    TARGET_H = 158

    f_aspect = front_img.width / max(1, front_img.height)
    front_scaled = front_img.resize((int(TARGET_H * f_aspect), TARGET_H), RESAMPLE_LANCZOS)
    f_head_x = get_head_center_x(front_scaled)
    f_px = int(FRAME_SIZE // 2 - f_head_x)
    f_py = FRAME_SIZE - TARGET_H - 8

    s_aspect = side_img.width / max(1, side_img.height)
    side_scaled = side_img.resize((int(TARGET_H * s_aspect), TARGET_H), RESAMPLE_LANCZOS)
    s_head_x = get_head_center_x(side_scaled)
    s_px = int(FRAME_SIZE // 2 - s_head_x)
    s_py = FRAME_SIZE - TARGET_H - 8

    b_aspect = back_flex_img.width / max(1, back_flex_img.height)
    back_scaled = back_flex_img.resize((int(TARGET_H * b_aspect), TARGET_H), RESAMPLE_LANCZOS)
    b_head_x = get_head_center_x(back_scaled)
    b_px = int(FRAME_SIZE // 2 - b_head_x)
    b_py = FRAME_SIZE - TARGET_H - 8

    # ─────────────────────────────────────────────────────────────────────────────
    # 1 & 2: WALK LEFT & RIGHT (TRUE 6-Frame Reference Walk Cycle)
    # ─────────────────────────────────────────────────────────────────────────────
    # Walk cycle phases matching the user's reference:
    # 0: Contact 1 (Left heel strike forward, right leg back, sword forward-down)
    # 1: Down / Weight acceptance 1 (body lowers +2, front foot flat)
    # 2: Passing / Rise 1 (body rises -3, trailing leg swinging past)
    # 3: Contact 2 (Right heel strike forward, left leg back, sword reverse)
    # 4: Down / Weight acceptance 2 (body lowers +2, right foot flat)
    # 5: Passing / Rise 2 (body rises -3, trailing leg swinging past)
    walk_phases = [
        # (dx, dy, rot_deg, sword_angle, steam_x)
        (-6, 0, -4, 0.4, 0),    # 0: Contact 1
        (-2, 2, -1, 0.2, 0),    # 1: Down 1
        (0, -3, 2, 0.0, 1),     # 2: Pass 1
        (6, 0, 4, -0.4, 0),     # 3: Contact 2
        (2, 2, 1, -0.2, 0),     # 4: Down 2
        (0, -3, -2, 0.0, 1),    # 5: Pass 2
    ]

    walk_frames_right = []
    for i, (dx, dy, rot_deg, sw_ang, is_pass) in enumerate(walk_phases):
        f = Image.new("RGBA", (FRAME_SIZE, FRAME_SIZE), (0, 0, 0, 0))

        # Rotate side view
        rot = side_scaled.rotate(rot_deg, resample=RESAMPLE_BICUBIC)
        # Position anchored by head center
        f.paste(rot, (s_px + dx, s_py + dy), rot)

        draw = ImageDraw.Draw(f)

        # Dual Katana articulated motion
        # Katana 1 (Front sword)
        k1_x1 = s_px + dx + 25
        k1_y1 = s_py + dy + int(TARGET_H * 0.46)
        k1_x2 = k1_x1 + int(48 * math.cos(sw_ang + 0.3))
        k1_y2 = k1_y1 - int(48 * math.sin(sw_ang + 0.3))
        draw_beast_katana(draw, k1_x1, k1_y1, k1_x2, k1_y2, serrated=True)

        # Katana 2 (Back sword)
        k2_x1 = s_px + dx + 10
        k2_y1 = s_py + dy + int(TARGET_H * 0.44)
        k2_x2 = k2_x1 - int(42 * math.cos(sw_ang + 0.2))
        k2_y2 = k2_y1 + int(42 * math.sin(sw_ang + 0.2))
        draw_beast_katana(draw, k2_x1, k2_y1, k2_x2, k2_y2, serrated=True)

        # Dynamic step dust & steam
        if i in [0, 3]:
            # Ground dust puff
            draw.ellipse([s_px + dx + 10, s_py + TARGET_H - 4, s_px + dx + 32, s_py + TARGET_H + 4], fill=(200, 200, 220, 130))
            draw_steam_puff(draw, s_px + dx + side_scaled.width - 5, s_py + dy + 42, r=5)

        walk_frames_right.append(f)

    walk_frames_left = [f.transpose(Image.FLIP_LEFT_RIGHT) for f in walk_frames_right]
    create_sheet(walk_frames_left).save(OUT_DIR / "walk_left.png")
    create_sheet(walk_frames_right).save(OUT_DIR / "walk_right.png")

    # ─────────────────────────────────────────────────────────────────────────────
    # 13 & 14: FALL & LAND (Legendary Inosuke Falling & Faceplant!)
    # ─────────────────────────────────────────────────────────────────────────────
    # Inosuke's iconic Demon Slayer tumble: flailing wildly while spinning mid-air
    fall_frames = []
    fall_angles = [35, 115, 205, 295]  # Full 360 comic tumble
    for step, angle in enumerate(fall_angles):
        f = Image.new("RGBA", (FRAME_SIZE, FRAME_SIZE), (0, 0, 0, 0))
        rot_fall = front_scaled.rotate(angle, resample=RESAMPLE_BICUBIC, expand=True)
        # Scale to fit frame
        rf_scaled = rot_fall.resize((int(rot_fall.width * 0.85), int(rot_fall.height * 0.85)), RESAMPLE_LANCZOS)
        fpx = (FRAME_SIZE - rf_scaled.width) // 2
        fpy = (FRAME_SIZE - rf_scaled.height) // 2 + (step * 8 - 12)
        f.paste(rf_scaled, (fpx, fpy), rf_scaled)

        draw = ImageDraw.Draw(f)
        # Comedic flailing speed streaks
        for trail_x in [30, 80, 140]:
            draw.line([(trail_x, fpy - 25), (trail_x, fpy - 5)], fill=(0, 220, 255, 190), width=2)
        # Panic sweat drops
        draw.ellipse([fpx + rf_scaled.width - 10, fpy + 10, fpx + rf_scaled.width - 4, fpy + 18], fill=(100, 220, 255, 230))
        draw.text((fpx + rf_scaled.width + 5, fpy + 20), "GYAAAAH!", fill=(255, 120, 40, 240))
        fall_frames.append(f)
    create_sheet(fall_frames).save(OUT_DIR / "fall.png")

    # Land: Faceplant with dust cloud & feet kicking
    land_frames = []
    for step in range(4):
        f = Image.new("RGBA", (FRAME_SIZE, FRAME_SIZE), (0, 0, 0, 0))
        if step < 2:
            # Faceplant flat with snout in ground
            fp_rot = front_scaled.rotate(180, resample=RESAMPLE_BICUBIC, expand=True)
            fp_scaled = fp_rot.resize((int(fp_rot.width * 0.75), int(fp_rot.height * 0.75)), RESAMPLE_LANCZOS)
            f.paste(fp_scaled, ((FRAME_SIZE - fp_scaled.width) // 2, FRAME_SIZE - fp_scaled.height - 4), fp_scaled)
            draw = ImageDraw.Draw(f)
            # Big ground impact dust ring
            draw.ellipse([20, FRAME_SIZE - 20, FRAME_SIZE - 20, FRAME_SIZE - 2], outline=(200, 200, 220, 180), width=3)
        else:
            # Popping back up angry
            squish = int(math.sin(step * math.pi / 3) * 6)
            f.paste(front_scaled, (f_px, f_py + squish), front_scaled)
            draw = ImageDraw.Draw(f)
            draw_steam_puff(draw, f_px + front_scaled.width // 2 - 12, f_py + 45, r=7)
            draw_steam_puff(draw, f_px + front_scaled.width // 2 + 12, f_py + 45, r=7)
        land_frames.append(f)
    create_sheet(land_frames).save(OUT_DIR / "land.png")

    # ─────────────────────────────────────────────────────────────────────────────
    # 3: IDLE & IDLE_FLIP (Breathing with dual blades held & steam)
    # ─────────────────────────────────────────────────────────────────────────────
    idle_frames = []
    for step in range(4):
        f = Image.new("RGBA", (FRAME_SIZE, FRAME_SIZE), (0, 0, 0, 0))
        bob = int(math.sin(step * math.pi / 2) * 2)
        f.paste(front_scaled, (f_px, f_py + bob), front_scaled)
        draw = ImageDraw.Draw(f)
        draw_beast_katana(draw, f_px + 10, f_py + bob + 30, f_px + 2, f_py + bob + TARGET_H - 40)
        draw_beast_katana(draw, f_px + front_scaled.width - 10, f_py + bob + 30, f_px + front_scaled.width - 2, f_py + bob + TARGET_H - 40)
        if step in [1, 3]:
            draw_steam_puff(draw, f_px + front_scaled.width // 2 - 12, f_py + 45 + bob, r=5)
            draw_steam_puff(draw, f_px + front_scaled.width // 2 + 12, f_py + 45 + bob, r=5)
        idle_frames.append(f)
    create_sheet(idle_frames).save(OUT_DIR / "idle.png")
    create_sheet([f.transpose(Image.FLIP_LEFT_RIGHT) for f in idle_frames]).save(OUT_DIR / "idle_flip.png")

    # 4: BLINK
    blink_frames = []
    for step in range(4):
        f = Image.new("RGBA", (FRAME_SIZE, FRAME_SIZE), (0, 0, 0, 0))
        f.paste(front_scaled, (f_px, f_py), front_scaled)
        draw = ImageDraw.Draw(f)
        if step in [1, 2]:
            eye_y = f_py + int(TARGET_H * 0.16)
            draw.ellipse([f_px + int(front_scaled.width * 0.35), eye_y, f_px + int(front_scaled.width * 0.42), eye_y + 5], fill=(0, 255, 255, 240))
            draw.ellipse([f_px + int(front_scaled.width * 0.58), eye_y, f_px + int(front_scaled.width * 0.65), eye_y + 5], fill=(0, 255, 255, 240))
        blink_frames.append(f)
    create_sheet(blink_frames).save(OUT_DIR / "blink.png")

    # 5: SIT
    sit_h = int(TARGET_H * 0.88)
    sit_scaled = front_img.resize((int(sit_h * f_aspect), sit_h), RESAMPLE_LANCZOS)
    sit_px = (FRAME_SIZE - sit_scaled.width) // 2
    sit_py = FRAME_SIZE - sit_h - 8

    sit_frames = []
    for step in range(4):
        f = Image.new("RGBA", (FRAME_SIZE, FRAME_SIZE), (0, 0, 0, 0))
        bob = int(math.sin(step * math.pi / 2) * 1.5)
        f.paste(sit_scaled, (sit_px, sit_py + bob), sit_scaled)
        sit_frames.append(f)
    create_sheet(sit_frames).save(OUT_DIR / "sit.png")

    # 6: SLEEP
    sl_rot = front_scaled.rotate(85, resample=RESAMPLE_BICUBIC, expand=True)
    sl_scaled = sl_rot.resize((int(sl_rot.width * 0.7), int(sl_rot.height * 0.7)), RESAMPLE_LANCZOS)
    sl_px = (FRAME_SIZE - sl_scaled.width) // 2
    sl_py = FRAME_SIZE - sl_scaled.height - 10

    sleep_frames = []
    for step in range(4):
        f = Image.new("RGBA", (FRAME_SIZE, FRAME_SIZE), (0, 0, 0, 0))
        snore = int(math.sin(step * math.pi / 2) * 2)
        f.paste(sl_scaled, (sl_px, sl_py + snore), sl_scaled)
        draw = ImageDraw.Draw(f)
        zx = sl_px + sl_scaled.width - 20 + step * 4
        zy = sl_py - 5 - step * 5
        draw.text((zx, zy), "z", fill=(100, 200, 255, 220))
        sleep_frames.append(f)
    create_sheet(sleep_frames).save(OUT_DIR / "sleep.png")

    # 7: WAKE
    wake_frames = []
    for step in range(4):
        f = Image.new("RGBA", (FRAME_SIZE, FRAME_SIZE), (0, 0, 0, 0))
        if step < 2:
            f.paste(sl_scaled, (sl_px, sl_py), sl_scaled)
        else:
            f.paste(front_scaled, (f_px, f_py), front_scaled)
            draw = ImageDraw.Draw(f)
            draw.text((f_px + front_scaled.width - 10, f_py - 10), "FIGHT ME!", fill=(0, 200, 255, 240))
        wake_frames.append(f)
    create_sheet(wake_frames).save(OUT_DIR / "wake.png")

    # 8: EAT
    eat_frames = []
    for step in range(4):
        f = Image.new("RGBA", (FRAME_SIZE, FRAME_SIZE), (0, 0, 0, 0))
        munch = int(math.sin(step * math.pi) * 3)
        f.paste(sit_scaled, (sit_px, sit_py + munch), sit_scaled)
        draw = ImageDraw.Draw(f)
        draw.polygon([(sit_px + sit_scaled.width // 2 - 5, sit_py + 45), (sit_px + sit_scaled.width // 2 + 25, sit_py + 35), (sit_px + sit_scaled.width // 2 + 15, sit_py + 55)], fill=(255, 180, 20, 240))
        draw.text((sit_px + sit_scaled.width - 15, sit_py + 20), "CHOMP!", fill=(255, 200, 50, 240))
        eat_frames.append(f)
    create_sheet(eat_frames).save(OUT_DIR / "eat.png")

    # 9: HAPPY
    happy_frames = []
    for step in range(4):
        f = Image.new("RGBA", (FRAME_SIZE, FRAME_SIZE), (0, 0, 0, 0))
        hop = int(abs(math.sin(step * math.pi / 2)) * 5)
        f.paste(back_scaled, (b_px, b_py - hop), back_scaled)
        draw = ImageDraw.Draw(f)
        draw_sparkle(draw, b_px + back_scaled.width - 10, b_py + 25 - hop, size=8, color=(0, 220, 255, 240))
        draw.text((b_px + back_scaled.width - 10, b_py - 15), "KING OF MOUNTAINS!", fill=(0, 220, 255, 240))
        happy_frames.append(f)
    create_sheet(happy_frames).save(OUT_DIR / "happy.png")

    # 10: SAD
    sad_frames = []
    for step in range(4):
        f = Image.new("RGBA", (FRAME_SIZE, FRAME_SIZE), (0, 0, 0, 0))
        f.paste(front_scaled, (f_px, f_py + 3), front_scaled)
        draw = ImageDraw.Draw(f)
        draw.text((f_px + front_scaled.width - 10, f_py + 20), "...", fill=(150, 180, 220, 220))
        sad_frames.append(f)
    create_sheet(sad_frames).save(OUT_DIR / "sad.png")

    # 11: CRY
    cry_frames = []
    for step in range(4):
        f = Image.new("RGBA", (FRAME_SIZE, FRAME_SIZE), (0, 0, 0, 0))
        f.paste(front_scaled, (f_px, f_py + 4), front_scaled)
        draw = ImageDraw.Draw(f)
        for side in [-15, 15]:
            tx = f_px + front_scaled.width // 2 + side
            ty = f_py + int(TARGET_H * 0.2) + step * 4
            draw.ellipse([tx - 3, ty, tx + 3, ty + 8], fill=(0, 220, 255, 230))
        cry_frames.append(f)
    create_sheet(cry_frames).save(OUT_DIR / "cry.png")

    # 12: JUMP
    jump_frames = []
    for step in range(4):
        f = Image.new("RGBA", (FRAME_SIZE, FRAME_SIZE), (0, 0, 0, 0))
        lift = int(math.sin((step + 1) * math.pi / 5) * 35)
        f.paste(front_scaled, (f_px, f_py - lift), front_scaled)
        draw = ImageDraw.Draw(f)
        draw_beast_katana(draw, f_px - 15, f_py - lift + 20, f_px + front_scaled.width + 15, f_py - lift + 60)
        jump_frames.append(f)
    create_sheet(jump_frames).save(OUT_DIR / "jump.png")

    # 15: ROAR (Beast Breathing Dual Slash)
    roar_frames = []
    for step in range(4):
        f = Image.new("RGBA", (FRAME_SIZE, FRAME_SIZE), (0, 0, 0, 0))
        shake = (step % 2) * 3 - 1
        f.paste(front_scaled, (f_px + shake, f_py), front_scaled)
        draw = ImageDraw.Draw(f)
        progress = (step + 1) / 4.0
        x1_a, y1_a = f_px - 25, f_py + 10
        x2_a, y2_a = int(f_px - 25 + (front_scaled.width + 50) * progress), int(f_py + 10 + (TARGET_H - 20) * progress)
        draw_beast_katana(draw, x1_a, y1_a, x2_a, y2_a, serrated=True)
        draw.line([(x1_a, y1_a), (x2_a, y2_a)], fill=(0, 220, 255, 200), width=5)

        x1_b, y1_b = f_px + front_scaled.width + 25, f_py + 10
        x2_b, y2_b = int(f_px + front_scaled.width + 25 - (front_scaled.width + 50) * progress), int(f_py + 10 + (TARGET_H - 20) * progress)
        draw_beast_katana(draw, x1_b, y1_b, x2_b, y2_b, serrated=True)
        draw.line([(x1_b, y1_b), (x2_b, y2_b)], fill=(0, 220, 255, 200), width=5)
        roar_frames.append(f)
    create_sheet(roar_frames).save(OUT_DIR / "roar.png")

    # 16: MUSIC
    music_frames = []
    for step in range(4):
        f = Image.new("RGBA", (FRAME_SIZE, FRAME_SIZE), (0, 0, 0, 0))
        dance_y = int(math.sin(step * math.pi / 2) * 6)
        f.paste(side_scaled, (s_px, s_py + dance_y), side_scaled)
        draw = ImageDraw.Draw(f)
        draw_music_note(draw, s_px + 10, s_py + 5 + step * 3, color=(0, 220, 255, 240))
        draw_music_note(draw, s_px + side_scaled.width - 15, s_py + 15 - step * 2, color=(0, 180, 255, 240))
        music_frames.append(f)
    create_sheet(music_frames).save(OUT_DIR / "music.png")

    # 17: WORK (Pig Assault)
    work_frames = []
    for step in range(4):
        f = Image.new("RGBA", (FRAME_SIZE, FRAME_SIZE), (0, 0, 0, 0))
        offset_x = (step - 1.5) * 18
        hop = int(abs(math.sin(step * math.pi)) * 6)
        tilt_side = side_scaled.rotate(-12, resample=RESAMPLE_BICUBIC)
        f.paste(tilt_side, (int(s_px + offset_x), s_py - hop), tilt_side)
        draw = ImageDraw.Draw(f)
        for line_y in [s_py + 20, s_py + 60, s_py + 100]:
            draw.line([(int(s_px + offset_x - 30), line_y), (int(s_px + offset_x - 5), line_y)], fill=(0, 220, 255, 180), width=2)
        draw.text((int(s_px + offset_x - 10), s_py - 18), "PIG ASSAULT!", fill=(0, 220, 255, 240))
        work_frames.append(f)
    create_sheet(work_frames).save(OUT_DIR / "work.png")

    # 18: DRAG
    drag_frames = []
    for step in range(4):
        f = Image.new("RGBA", (FRAME_SIZE, FRAME_SIZE), (0, 0, 0, 0))
        f.paste(front_scaled, (f_px, f_py - 20), front_scaled)
        draw = ImageDraw.Draw(f)
        draw.text((f_px + front_scaled.width - 5, f_py - 25), "LET GO!", fill=(255, 100, 50, 240))
        drag_frames.append(f)
    create_sheet(drag_frames).save(OUT_DIR / "drag.png")

    # 19: IDEA
    idea_frames = []
    for step in range(4):
        f = Image.new("RGBA", (FRAME_SIZE, FRAME_SIZE), (0, 0, 0, 0))
        f.paste(front_scaled, (f_px, f_py), front_scaled)
        draw = ImageDraw.Draw(f)
        draw.ellipse([f_px + front_scaled.width // 2 - 10, f_py - 25, f_px + front_scaled.width // 2 + 10, f_py - 5], fill=(255, 230, 50, 240), outline=(255, 180, 0, 255), width=2)
        idea_frames.append(f)
    create_sheet(idea_frames).save(OUT_DIR / "idea.png")

    # 20: SHRUG
    shrug_frames = []
    for step in range(4):
        f = Image.new("RGBA", (FRAME_SIZE, FRAME_SIZE), (0, 0, 0, 0))
        tilt = front_scaled.rotate(step * 3 - 3, resample=RESAMPLE_BICUBIC)
        f.paste(tilt, (f_px, f_py), tilt)
        shrug_frames.append(f)
    create_sheet(shrug_frames).save(OUT_DIR / "shrug.png")

    print("Successfully generated Inosuke with True Walk Cycle & Legendary Fall!")


if __name__ == "__main__":
    generate_all()
