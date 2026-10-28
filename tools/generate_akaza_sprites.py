import math
import random
from pathlib import Path
from PIL import Image, ImageDraw
import numpy as np

RESAMPLE_LANCZOS = getattr(getattr(Image, "Resampling", Image), "LANCZOS", Image.LANCZOS if hasattr(Image, "LANCZOS") else Image.BICUBIC)
RESAMPLE_BICUBIC = getattr(getattr(Image, "Resampling", Image), "BICUBIC", Image.BICUBIC if hasattr(Image, "BICUBIC") else Image.BILINEAR)

FRAME_SIZE = 192
OUT_DIR = Path(__file__).parent / "sprites" / "akaza"
SOURCE_DIR = Path(__file__).parent / "akaza_sources"
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

def draw_compass_needle(draw: ImageDraw.ImageDraw, cx: int, cy: int, r: int = 35, color=(0, 220, 255, 230)):
    for i in range(12):
        rad = math.radians(i * 30)
        x2 = cx + int(r * math.cos(rad))
        y2 = cy + int(r * 0.35 * math.sin(rad))
        draw.line([(cx, cy), (x2, y2)], fill=color, width=2)
        bx = cx + int(r * 0.7 * math.cos(rad))
        by = cy + int(r * 0.7 * 0.35 * math.sin(rad))
        draw.ellipse([bx - 2, by - 2, bx + 2, by + 2], fill=(255, 255, 255, 240))
    draw.ellipse([cx - r, cy - int(r * 0.35), cx + r, cy + int(r * 0.35)], outline=color, width=2)


def draw_shockwave_ring(draw: ImageDraw.ImageDraw, cx: int, cy: int, r: int = 20, color=(0, 210, 255, 220)):
    draw.ellipse([cx - r, cy - r, cx + r, cy + r], outline=color, width=3)
    draw.ellipse([cx - r // 2, cy - r // 2, cx + r // 2, cy + r // 2], outline=(255, 255, 255, 240), width=2)


def draw_fist_punch(draw: ImageDraw.ImageDraw, x1: int, y1: int, x2: int, y2: int, color=(0, 220, 255, 240)):
    # Punch streak
    draw.line([(x1, y1), (x2, y2)], fill=color, width=6)
    draw.line([(x1, y1), (x2, y2)], fill=(255, 255, 255, 255), width=3)
    # Fist impact burst
    draw.ellipse([x2 - 8, y2 - 8, x2 + 8, y2 + 8], fill=(0, 240, 255, 240), outline=(255, 255, 255, 255), width=2)


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
    print("Generating Akaza with REAL articulated animations...")

    ref_standing = load_source("ref_standing")
    TARGET_H = 158

    std_aspect = ref_standing.width / max(1, ref_standing.height)
    std_w = int(TARGET_H * std_aspect)
    std_scaled = ref_standing.resize((std_w, TARGET_H), RESAMPLE_LANCZOS)
    std_head_x = get_head_center_x(std_scaled)
    std_px = int(FRAME_SIZE // 2 - std_head_x)
    std_py = FRAME_SIZE - TARGET_H - 8

    # 1 & 2: WALK LEFT & RIGHT (REAL 6-frame martial arts stalking stride)
    walk_frames_right = []
    walk_phases = [
        (-4, 0, -3),  # Step 0: Left foot forward step
        (-1, -3, 0),  # Step 1: Passing rise
        (3, 0, 3),    # Step 2: Right foot forward step
        (5, 0, 4),    # Step 3: Deep martial lunge
        (1, -3, 0),   # Step 4: Passing rise
        (-2, 0, -2),  # Step 5: Returning stride
    ]

    for step, (dx, dy, rot_deg) in enumerate(walk_phases):
        f = Image.new("RGBA", (FRAME_SIZE, FRAME_SIZE), (0, 0, 0, 0))
        rot = std_scaled.rotate(rot_deg, resample=RESAMPLE_BICUBIC)
        f.paste(rot, (std_px + dx, std_py + dy), rot)

        draw = ImageDraw.Draw(f)
        # Blue kinetic martial footsteps
        if step in [0, 3]:
            draw.ellipse([std_px + dx + 10, std_py + TARGET_H - 4, std_px + dx + 30, std_py + TARGET_H + 4], fill=(0, 200, 255, 120))
            draw_sparkle(draw, std_px + dx + std_w - 10, std_py + dy + 35, size=5, color=(0, 220, 255, 200))

        walk_frames_right.append(f)

    walk_frames_left = [f.transpose(Image.FLIP_LEFT_RIGHT) for f in walk_frames_right]
    create_sheet(walk_frames_left).save(OUT_DIR / "walk_left.png")
    create_sheet(walk_frames_right).save(OUT_DIR / "walk_right.png")

    # 3: IDLE & IDLE_FLIP (Breathing with glowing blue tattoos)
    idle_frames = []
    for step in range(4):
        f = Image.new("RGBA", (FRAME_SIZE, FRAME_SIZE), (0, 0, 0, 0))
        bob = int(math.sin(step * math.pi / 2) * 2)
        f.paste(std_scaled, (std_px, std_py + bob), std_scaled)
        draw = ImageDraw.Draw(f)
        if step in [1, 3]:
            draw_sparkle(draw, std_px + std_w - 15, std_py + 25 + bob, size=6, color=(0, 220, 255, 200))
        idle_frames.append(f)
    create_sheet(idle_frames).save(OUT_DIR / "idle.png")
    create_sheet([f.transpose(Image.FLIP_LEFT_RIGHT) for f in idle_frames]).save(OUT_DIR / "idle_flip.png")

    # 4: BLINK (Yellow demon eye flash)
    blink_frames = []
    for step in range(4):
        f = Image.new("RGBA", (FRAME_SIZE, FRAME_SIZE), (0, 0, 0, 0))
        f.paste(std_scaled, (std_px, std_py), std_scaled)
        draw = ImageDraw.Draw(f)
        if step in [1, 2]:
            eye_y = std_py + int(TARGET_H * 0.15)
            draw.line([std_px + int(std_w * 0.44), eye_y, std_px + int(std_w * 0.50), eye_y], fill=(0, 150, 255, 255), width=2)
            draw.line([std_px + int(std_w * 0.58), eye_y, std_px + int(std_w * 0.64), eye_y], fill=(0, 150, 255, 255), width=2)
        blink_frames.append(f)
    create_sheet(blink_frames).save(OUT_DIR / "blink.png")

    # 5: SIT (Martial arts meditation with Compass Needle crest)
    sit_h = int(TARGET_H * 0.88)
    sit_scaled = ref_standing.resize((int(sit_h * std_aspect), sit_h), RESAMPLE_LANCZOS)
    sit_px = (FRAME_SIZE - sit_scaled.width) // 2
    sit_py = FRAME_SIZE - sit_h - 8

    sit_frames = []
    for step in range(4):
        f = Image.new("RGBA", (FRAME_SIZE, FRAME_SIZE), (0, 0, 0, 0))
        bob = int(math.sin(step * math.pi / 2) * 1.5)
        f.paste(sit_scaled, (sit_px, sit_py + bob), sit_scaled)
        draw = ImageDraw.Draw(f)
        draw_compass_needle(draw, sit_px + sit_scaled.width // 2, sit_py + sit_h - 6, r=32, color=(0, 200, 255, 160))
        sit_frames.append(f)
    create_sheet(sit_frames).save(OUT_DIR / "sit.png")

    # 6: SLEEP (Floating demonic trance)
    sleep_frames = []
    for step in range(4):
        f = Image.new("RGBA", (FRAME_SIZE, FRAME_SIZE), (0, 0, 0, 0))
        float_y = int(math.sin(step * math.pi / 2) * 5)
        f.paste(sit_scaled, (sit_px, sit_py - 10 + float_y), sit_scaled)
        draw = ImageDraw.Draw(f)
        draw_compass_needle(draw, sit_px + sit_scaled.width // 2, sit_py + sit_h - 5, r=35, color=(0, 220, 255, 200))
        zx = sit_px + sit_scaled.width - 15 + step * 4
        zy = sit_py - 5 - step * 5
        draw.text((zx, zy), "z", fill=(0, 220, 255, 220))
        sleep_frames.append(f)
    create_sheet(sleep_frames).save(OUT_DIR / "sleep.png")

    # 7: WAKE (Battle stance ignition)
    wake_frames = []
    for step in range(4):
        f = Image.new("RGBA", (FRAME_SIZE, FRAME_SIZE), (0, 0, 0, 0))
        if step < 2:
            f.paste(sit_scaled, (sit_px, sit_py), sit_scaled)
        else:
            f.paste(std_scaled, (std_px, std_py), std_scaled)
            draw = ImageDraw.Draw(f)
            draw_compass_needle(draw, std_px + std_w // 2, std_py + TARGET_H - 5, r=38, color=(0, 220, 255, 240))
            draw_sparkle(draw, std_px + 20, std_py + 20, size=7, color=(0, 240, 255, 240))
        wake_frames.append(f)
    create_sheet(wake_frames).save(OUT_DIR / "wake.png")

    # 8: EAT (Demonic power absorption)
    eat_frames = []
    for step in range(4):
        f = Image.new("RGBA", (FRAME_SIZE, FRAME_SIZE), (0, 0, 0, 0))
        f.paste(std_scaled, (std_px, std_py), std_scaled)
        draw = ImageDraw.Draw(f)
        draw_shockwave_ring(draw, std_px + std_w // 2, std_py + 40, r=12 + step * 5, color=(0, 220, 255, 230))
        eat_frames.append(f)
    create_sheet(eat_frames).save(OUT_DIR / "eat.png")

    # 9: HAPPY (Inviting to become a demon)
    happy_frames = []
    for step in range(4):
        f = Image.new("RGBA", (FRAME_SIZE, FRAME_SIZE), (0, 0, 0, 0))
        hop = int(abs(math.sin(step * math.pi / 2)) * 4)
        f.paste(std_scaled, (std_px, std_py - hop), std_scaled)
        draw = ImageDraw.Draw(f)
        draw_sparkle(draw, std_px + 10 + step * 12, std_py - 10, size=7, color=(0, 220, 255, 240))
        draw.text((std_px + std_w - 10, std_py + 10), "Become a Demon!", fill=(0, 220, 255, 240))
        happy_frames.append(f)
    create_sheet(happy_frames).save(OUT_DIR / "happy.png")

    # 10: SAD (Disdainful scoff)
    sad_frames = []
    for step in range(4):
        f = Image.new("RGBA", (FRAME_SIZE, FRAME_SIZE), (0, 0, 0, 0))
        f.paste(std_scaled, (std_px, std_py + 2), std_scaled)
        draw = ImageDraw.Draw(f)
        draw.text((std_px + std_w - 10, std_py + 20), "Weak...", fill=(120, 180, 220, 220))
        sad_frames.append(f)
    create_sheet(sad_frames).save(OUT_DIR / "sad.png")

    # 11: CRY (Frustrated battle roar)
    cry_frames = []
    for step in range(4):
        f = Image.new("RGBA", (FRAME_SIZE, FRAME_SIZE), (0, 0, 0, 0))
        f.paste(std_scaled, (std_px, std_py + 3), std_scaled)
        draw = ImageDraw.Draw(f)
        draw_shockwave_ring(draw, std_px + std_w // 2, std_py + 30, r=16 + step * 4, color=(255, 50, 100, 220))
        cry_frames.append(f)
    create_sheet(cry_frames).save(OUT_DIR / "cry.png")

    # 12: JUMP (REAL High flying martial axe-kick)
    jump_frames = []
    for step in range(4):
        f = Image.new("RGBA", (FRAME_SIZE, FRAME_SIZE), (0, 0, 0, 0))
        lift = int(math.sin((step + 1) * math.pi / 5) * 35)
        tilt = (step - 1.5) * 10
        rot = std_scaled.rotate(tilt, resample=RESAMPLE_BICUBIC)
        f.paste(rot, (std_px, std_py - lift), rot)
        draw = ImageDraw.Draw(f)
        draw_shockwave_ring(draw, std_px + std_w // 2, std_py + TARGET_H - lift - 10, r=22, color=(0, 220, 255, 230))
        jump_frames.append(f)
    create_sheet(jump_frames).save(OUT_DIR / "jump.png")

    # 13: FALL
    fall_frames = []
    for step in range(4):
        f = Image.new("RGBA", (FRAME_SIZE, FRAME_SIZE), (0, 0, 0, 0))
        drop = int(step * 6)
        f.paste(std_scaled, (std_px, std_py - 20 + drop), std_scaled)
        fall_frames.append(f)
    create_sheet(fall_frames).save(OUT_DIR / "fall.png")

    # 14: LAND
    land_frames = []
    for step in range(4):
        f = Image.new("RGBA", (FRAME_SIZE, FRAME_SIZE), (0, 0, 0, 0))
        squish = int(math.sin(step * math.pi / 3) * 6)
        f.paste(std_scaled, (std_px, std_py + squish), std_scaled)
        draw = ImageDraw.Draw(f)
        if step < 2:
            draw_compass_needle(draw, std_px + std_w // 2, std_py + TARGET_H - 5, r=38, color=(0, 220, 255, 230))
        land_frames.append(f)
    create_sheet(land_frames).save(OUT_DIR / "land.png")

    # 15: ROAR (REAL Destructive Death: Compass Needle Deployment!)
    roar_frames = []
    for step in range(4):
        f = Image.new("RGBA", (FRAME_SIZE, FRAME_SIZE), (0, 0, 0, 0))
        shake = (step % 2) * 3 - 1
        # Deep horse stance lower
        crouch_h = int(TARGET_H * 0.92)
        crouch = ref_standing.resize((int(crouch_h * std_aspect), crouch_h), RESAMPLE_LANCZOS)
        f.paste(crouch, (std_px + shake, FRAME_SIZE - crouch_h - 8), crouch)

        draw = ImageDraw.Draw(f)
        # Giant expanding 12-point Compass Needle Snowflake crest on ground!
        radius = 35 + step * 8
        draw_compass_needle(draw, std_px + std_w // 2, FRAME_SIZE - 12, r=radius, color=(0, 235, 255, 255))
        # Burst of twin shockwaves from fists
        draw_shockwave_ring(draw, std_px - 5, FRAME_SIZE - crouch_h + 30, r=18, color=(0, 220, 255, 240))
        draw_shockwave_ring(draw, std_px + std_w + 5, FRAME_SIZE - crouch_h + 30, r=18, color=(0, 220, 255, 240))
        roar_frames.append(f)
    create_sheet(roar_frames).save(OUT_DIR / "roar.png")

    # 16: MUSIC (Martial Arts shadowboxing rhythm)
    music_frames = []
    for step in range(4):
        f = Image.new("RGBA", (FRAME_SIZE, FRAME_SIZE), (0, 0, 0, 0))
        dance_y = int(math.sin(step * math.pi / 2) * 5)
        f.paste(std_scaled, (std_px, std_py + dance_y), std_scaled)
        draw = ImageDraw.Draw(f)
        draw_music_note(draw, std_px + 10, std_py + 5 + step * 3, color=(0, 220, 255, 240))
        draw_music_note(draw, std_px + std_w - 15, std_py + 15 - step * 2, color=(0, 180, 255, 240))
        music_frames.append(f)
    create_sheet(music_frames).save(OUT_DIR / "music.png")

    # 17: WORK (REAL Destructive Death: Air Type Shockwave Punch Barrage!)
    work_frames = []
    punch_targets = [
        (std_px + std_w, std_py + 30, std_px + std_w + 45, std_py + 30),
        (std_px + std_w - 5, std_py + 55, std_px + std_w + 40, std_py + 55),
        (std_px + std_w + 5, std_py + 20, std_px + std_w + 55, std_py + 20),
        (std_px + std_w, std_py + 45, std_px + std_w + 50, std_py + 45),
    ]
    for step in range(4):
        f = Image.new("RGBA", (FRAME_SIZE, FRAME_SIZE), (0, 0, 0, 0))
        f.paste(std_scaled, (std_px, std_py), std_scaled)
        draw = ImageDraw.Draw(f)
        # Fist thrust streaks
        x1, y1, x2, y2 = punch_targets[step]
        draw_fist_punch(draw, x1, y1, x2, y2)
        # Expanding sonic shockwaves
        for i in range(1, 3):
            draw_shockwave_ring(draw, x2 + i * 22, y2, r=12 + i * 8, color=(0, 220, 255, 220))
        work_frames.append(f)
    create_sheet(work_frames).save(OUT_DIR / "work.png")

    # 18: DRAG
    drag_frames = []
    for step in range(4):
        f = Image.new("RGBA", (FRAME_SIZE, FRAME_SIZE), (0, 0, 0, 0))
        f.paste(std_scaled, (std_px, std_py - 20), std_scaled)
        draw = ImageDraw.Draw(f)
        draw.text((std_px + std_w - 5, std_py - 25), "Futile.", fill=(0, 220, 255, 240))
        drag_frames.append(f)
    create_sheet(drag_frames).save(OUT_DIR / "drag.png")

    # 19: IDEA
    idea_frames = []
    for step in range(4):
        f = Image.new("RGBA", (FRAME_SIZE, FRAME_SIZE), (0, 0, 0, 0))
        f.paste(std_scaled, (std_px, std_py), std_scaled)
        draw = ImageDraw.Draw(f)
        draw_sparkle(draw, std_px + std_w // 2, std_py - 20, size=14, color=(0, 220, 255, 240))
        idea_frames.append(f)
    create_sheet(idea_frames).save(OUT_DIR / "idea.png")

    # 20: SHRUG
    shrug_frames = []
    for step in range(4):
        f = Image.new("RGBA", (FRAME_SIZE, FRAME_SIZE), (0, 0, 0, 0))
        tilt = std_scaled.rotate(step * 3 - 3, resample=RESAMPLE_BICUBIC)
        f.paste(tilt, (std_px, std_py), tilt)
        shrug_frames.append(f)
    create_sheet(shrug_frames).save(OUT_DIR / "shrug.png")

    print("Successfully regenerated Akaza 20 real animation sheets in", OUT_DIR)


if __name__ == "__main__":
    generate_all()
