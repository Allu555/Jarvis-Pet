import math
import random
from pathlib import Path
from PIL import Image, ImageDraw
import numpy as np

# Compatible resampling constants
RESAMPLE_LANCZOS = getattr(getattr(Image, "Resampling", Image), "LANCZOS", Image.LANCZOS if hasattr(Image, "LANCZOS") else Image.BICUBIC)
RESAMPLE_BICUBIC = getattr(getattr(Image, "Resampling", Image), "BICUBIC", Image.BICUBIC if hasattr(Image, "BICUBIC") else Image.BILINEAR)

FRAME_SIZE = 192
OUT_DIR = Path(__file__).parent / "sprites" / "batman_cat"
SOURCE_DIR = Path(__file__).parent / "batman_cat_sources"
OUT_DIR.mkdir(parents=True, exist_ok=True)


def load_source(name: str) -> Image.Image:
    path = SOURCE_DIR / f"{name}.png"
    if path.exists():
        return Image.open(path).convert("RGBA")
    return Image.new("RGBA", (100, 100), (0, 0, 0, 0))


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
    top_mask = (y_indices < (y_indices.min() + (y_indices.max() - y_indices.min()) * 0.35))
    if not np.any(top_mask):
        return img.width / 2.0
    return float(np.mean(x_indices[top_mask]))


# ── Vector Effect Helpers ──

def draw_bat_signal(draw: ImageDraw.ImageDraw, cx: int, cy: int, r: int = 18, color=(255, 220, 0, 230)):
    # Yellow spotlight oval
    draw.ellipse([cx - r * 1.4, cy - r, cx + r * 1.4, cy + r], fill=(255, 230, 50, 120), outline=color, width=2)
    # Mini black bat silhouette
    bw, bh = int(r * 0.8), int(r * 0.5)
    draw.ellipse([cx - bw, cy - bh, cx + bw, cy + bh], fill=(20, 20, 25, 240))
    # Bat wing cutouts
    draw.polygon([(cx - bw, cy - bh), (cx - bw // 2, cy - bh // 2), (cx - bw, cy)], fill=(255, 230, 50, 120))
    draw.polygon([(cx + bw, cy - bh), (cx + bw // 2, cy - bh // 2), (cx + bw, cy)], fill=(255, 230, 50, 120))


def draw_sparkle(draw: ImageDraw.ImageDraw, cx: int, cy: int, size: int = 8, color=(255, 220, 0, 240)):
    draw.line([cx - size, cy, cx + size, cy], fill=color, width=2)
    draw.line([cx, cy - size, cx, cy + size], fill=color, width=2)
    s2 = size // 2
    draw.line([cx - s2, cy - s2, cx + s2, cy + s2], fill=color, width=1)
    draw.line([cx - s2, cy + s2, cx + s2, cy - s2], fill=color, width=1)


def draw_music_note(draw: ImageDraw.ImageDraw, x: int, y: int, color=(255, 215, 0, 240)):
    draw.ellipse([x, y + 6, x + 5, y + 10], fill=color)
    draw.line([x + 4, y + 8, x + 4, y], fill=color, width=2)
    draw.line([x + 4, y, x + 8, y + 2], fill=color, width=2)


def generate_all():
    print("Generating Batman Cat 20 HD animation sheets...")

    # Load sources
    walk_imgs = [load_source(f"walk_{i}") for i in range(6)]
    sit_upright = load_source("sit_upright")
    pounce_img = load_source("pounce")
    sleep_img = load_source("sleep")
    toy_img = load_source("toy")
    angry_img = load_source("angry")
    eat_img = load_source("eat")

    TARGET_H = 135  # Kitten proportions

    # 1 & 2: WALK LEFT & RIGHT
    walk_frames_right = []
    for i, w_img in enumerate(walk_imgs):
        aspect = w_img.width / max(1, w_img.height)
        new_h = TARGET_H
        new_w = int(new_h * aspect)
        scaled = w_img.resize((new_w, new_h), RESAMPLE_LANCZOS)

        frame = Image.new("RGBA", (FRAME_SIZE, FRAME_SIZE), (0, 0, 0, 0))
        head_x = get_head_center_x(scaled)
        paste_x = int(FRAME_SIZE // 2 - head_x)
        paste_y = FRAME_SIZE - new_h - 10
        frame.paste(scaled, (paste_x, paste_y), scaled)

        # Micro dust puffs
        draw = ImageDraw.Draw(frame)
        if i in [1, 4]:
            draw.ellipse([paste_x + 10, paste_y + new_h - 6, paste_x + 22, paste_y + new_h + 2], fill=(200, 200, 220, 100))

        walk_frames_right.append(frame)

    walk_frames_left = [f.transpose(Image.FLIP_LEFT_RIGHT) for f in walk_frames_right]
    create_sheet(walk_frames_left).save(OUT_DIR / "walk_left.png")
    create_sheet(walk_frames_right).save(OUT_DIR / "walk_right.png")

    # Base sitting frame
    sit_aspect = sit_upright.width / max(1, sit_upright.height)
    sit_h = TARGET_H + 10
    sit_w = int(sit_h * sit_aspect)
    sit_scaled = sit_upright.resize((sit_w, sit_h), RESAMPLE_LANCZOS)
    sit_head_x = get_head_center_x(sit_scaled)
    sit_px = int(FRAME_SIZE // 2 - sit_head_x)
    sit_py = FRAME_SIZE - sit_h - 10

    # 3: IDLE & IDLE_FLIP (4 frames breathing & cape flutter)
    idle_frames = []
    for step in range(4):
        f = Image.new("RGBA", (FRAME_SIZE, FRAME_SIZE), (0, 0, 0, 0))
        bob = int(math.sin(step * math.pi / 2) * 2)
        f.paste(sit_scaled, (sit_px, sit_py + bob), sit_scaled)
        draw = ImageDraw.Draw(f)
        # Subtle yellow bat aura
        if step in [1, 3]:
            draw_sparkle(draw, sit_px + sit_w - 15, sit_py + 25, size=5, color=(255, 230, 80, 180))
        idle_frames.append(f)
    create_sheet(idle_frames).save(OUT_DIR / "idle.png")
    create_sheet([f.transpose(Image.FLIP_LEFT_RIGHT) for f in idle_frames]).save(OUT_DIR / "idle_flip.png")

    # 4: BLINK (4 frames)
    blink_frames = []
    for step in range(4):
        f = Image.new("RGBA", (FRAME_SIZE, FRAME_SIZE), (0, 0, 0, 0))
        f.paste(sit_scaled, (sit_px, sit_py), sit_scaled)
        draw = ImageDraw.Draw(f)
        if step in [1, 2]:
            # Close eyes
            eye_y = sit_py + int(sit_h * 0.32)
            draw.line([sit_px + int(sit_w * 0.38), eye_y, sit_px + int(sit_w * 0.46), eye_y], fill=(60, 40, 30, 255), width=3)
            draw.line([sit_px + int(sit_w * 0.56), eye_y, sit_px + int(sit_w * 0.64), eye_y], fill=(60, 40, 30, 255), width=3)
        blink_frames.append(f)
    create_sheet(blink_frames).save(OUT_DIR / "blink.png")

    # 5: SIT (4 frames)
    sit_frames = []
    for step in range(4):
        f = Image.new("RGBA", (FRAME_SIZE, FRAME_SIZE), (0, 0, 0, 0))
        bob = int(math.sin(step * math.pi / 2) * 1.5)
        f.paste(sit_scaled, (sit_px, sit_py + bob), sit_scaled)
        sit_frames.append(f)
    create_sheet(sit_frames).save(OUT_DIR / "sit.png")

    # 6: SLEEP (4 frames curled up)
    sl_aspect = sleep_img.width / max(1, sleep_img.height)
    sl_h = int(TARGET_H * 0.85)
    sl_w = int(sl_h * sl_aspect)
    sl_scaled = sleep_img.resize((sl_w, sl_h), RESAMPLE_LANCZOS)
    sl_px = (FRAME_SIZE - sl_w) // 2
    sl_py = FRAME_SIZE - sl_h - 10

    sleep_frames = []
    for step in range(4):
        f = Image.new("RGBA", (FRAME_SIZE, FRAME_SIZE), (0, 0, 0, 0))
        breath = int(math.sin(step * math.pi / 2) * 2)
        f.paste(sl_scaled, (sl_px, sl_py + breath), sl_scaled)
        draw = ImageDraw.Draw(f)
        # Zzz bubbles
        zx = sl_px + sl_w - 10 + step * 4
        zy = sl_py - 10 - step * 6
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
            f.paste(sit_scaled, (sit_px, sit_py), sit_scaled)
            draw = ImageDraw.Draw(f)
            draw_sparkle(draw, sit_px + 20, sit_py + 20, size=6, color=(255, 230, 80, 200))
        wake_frames.append(f)
    create_sheet(wake_frames).save(OUT_DIR / "wake.png")

    # 8: EAT (4 frames munching fish)
    eat_aspect = eat_img.width / max(1, eat_img.height)
    eat_h = TARGET_H + 5
    eat_w = int(eat_h * eat_aspect)
    eat_scaled = eat_img.resize((eat_w, eat_h), RESAMPLE_LANCZOS)
    eat_px = (FRAME_SIZE - eat_w) // 2
    eat_py = FRAME_SIZE - eat_h - 10

    eat_frames = []
    for step in range(4):
        f = Image.new("RGBA", (FRAME_SIZE, FRAME_SIZE), (0, 0, 0, 0))
        munch = int(math.sin(step * math.pi) * 3)
        f.paste(eat_scaled, (eat_px, eat_py + munch), eat_scaled)
        draw = ImageDraw.Draw(f)
        draw.text((eat_px + eat_w - 20, eat_py + 10), "Nom!", fill=(255, 180, 50, 240))
        eat_frames.append(f)
    create_sheet(eat_frames).save(OUT_DIR / "eat.png")

    # 9: HAPPY (4 frames wiggling & sparkles)
    happy_frames = []
    for step in range(4):
        f = Image.new("RGBA", (FRAME_SIZE, FRAME_SIZE), (0, 0, 0, 0))
        hop = int(abs(math.sin(step * math.pi / 2)) * 6)
        f.paste(sit_scaled, (sit_px, sit_py - hop), sit_scaled)
        draw = ImageDraw.Draw(f)
        draw_sparkle(draw, sit_px + 10 + step * 12, sit_py - 10, size=7, color=(255, 230, 80, 240))
        draw_sparkle(draw, sit_px + sit_w - 10, sit_py + 15, size=6, color=(255, 215, 0, 220))
        happy_frames.append(f)
    create_sheet(happy_frames).save(OUT_DIR / "happy.png")

    # 10: SAD (4 frames droopy ears)
    sad_frames = []
    for step in range(4):
        f = Image.new("RGBA", (FRAME_SIZE, FRAME_SIZE), (0, 0, 0, 0))
        f.paste(sit_scaled, (sit_px, sit_py + 3), sit_scaled)
        draw = ImageDraw.Draw(f)
        draw.ellipse([sit_px + sit_w // 2 - 15, sit_py + int(sit_h * 0.45) + step * 2, sit_px + sit_w // 2 - 11, sit_py + int(sit_h * 0.45) + 6 + step * 2], fill=(100, 200, 255, 220))
        sad_frames.append(f)
    create_sheet(sad_frames).save(OUT_DIR / "sad.png")

    # 11: CRY (4 frames tears)
    cry_frames = []
    for step in range(4):
        f = Image.new("RGBA", (FRAME_SIZE, FRAME_SIZE), (0, 0, 0, 0))
        f.paste(sit_scaled, (sit_px, sit_py + 4), sit_scaled)
        draw = ImageDraw.Draw(f)
        for side in [-15, 15]:
            tx = sit_px + sit_w // 2 + side
            ty = sit_py + int(sit_h * 0.4) + step * 4
            draw.ellipse([tx - 3, ty, tx + 3, ty + 8], fill=(120, 220, 255, 230))
        cry_frames.append(f)
    create_sheet(cry_frames).save(OUT_DIR / "cry.png")

    # 12: JUMP (4 frames bat-pounce)
    p_aspect = pounce_img.width / max(1, pounce_img.height)
    p_h = TARGET_H + 10
    p_w = int(p_h * p_aspect)
    p_scaled = pounce_img.resize((p_w, p_h), RESAMPLE_LANCZOS)
    p_px = (FRAME_SIZE - p_w) // 2
    p_py = FRAME_SIZE - p_h - 10

    jump_frames = []
    for step in range(4):
        f = Image.new("RGBA", (FRAME_SIZE, FRAME_SIZE), (0, 0, 0, 0))
        lift = int(math.sin((step + 1) * math.pi / 5) * 35)
        f.paste(p_scaled, (p_px, p_py - lift), p_scaled)
        draw = ImageDraw.Draw(f)
        draw.line([p_px - 10, p_py + p_h - lift + 5, p_px + 20, p_py + p_h - lift + 5], fill=(255, 220, 50, 150), width=2)
        jump_frames.append(f)
    create_sheet(jump_frames).save(OUT_DIR / "jump.png")

    # 13: FALL (4 frames gliding down with cape)
    fall_frames = []
    for step in range(4):
        f = Image.new("RGBA", (FRAME_SIZE, FRAME_SIZE), (0, 0, 0, 0))
        drift = int(math.sin(step * math.pi / 2) * 5)
        drop = int(step * 6)
        f.paste(p_scaled, (p_px + drift, p_py - 20 + drop), p_scaled)
        fall_frames.append(f)
    create_sheet(fall_frames).save(OUT_DIR / "fall.png")

    # 14: LAND (4 frames soft touchdown)
    land_frames = []
    for step in range(4):
        f = Image.new("RGBA", (FRAME_SIZE, FRAME_SIZE), (0, 0, 0, 0))
        squish = int(math.sin(step * math.pi / 3) * 6)
        f.paste(sit_scaled, (sit_px, sit_py + squish), sit_scaled)
        draw = ImageDraw.Draw(f)
        if step < 2:
            draw.ellipse([sit_px - 5, sit_py + sit_h - 5, sit_px + sit_w + 5, sit_py + sit_h + 3], outline=(200, 200, 220, 120), width=2)
        land_frames.append(f)
    create_sheet(land_frames).save(OUT_DIR / "land.png")

    # 15: ROAR (4 frames angry bat-hiss & Bat-Signal aura!)
    ang_aspect = angry_img.width / max(1, angry_img.height)
    ang_h = TARGET_H + 5
    ang_w = int(ang_h * ang_aspect)
    ang_scaled = angry_img.resize((ang_w, ang_h), RESAMPLE_LANCZOS)
    ang_px = (FRAME_SIZE - ang_w) // 2
    ang_py = FRAME_SIZE - ang_h - 10

    roar_frames = []
    for step in range(4):
        f = Image.new("RGBA", (FRAME_SIZE, FRAME_SIZE), (0, 0, 0, 0))
        shake = (step % 2) * 3 - 1
        f.paste(ang_scaled, (ang_px + shake, ang_py), ang_scaled)
        draw = ImageDraw.Draw(f)
        draw_bat_signal(draw, ang_px + ang_w // 2, ang_py - 22, r=16 + step * 2)
        roar_frames.append(f)
    create_sheet(roar_frames).save(OUT_DIR / "roar.png")

    # 16: MUSIC (4 frames dancing with batarang & music notes)
    toy_aspect = toy_img.width / max(1, toy_img.height)
    toy_h = TARGET_H + 10
    toy_w = int(toy_h * toy_aspect)
    toy_scaled = toy_img.resize((toy_w, toy_h), RESAMPLE_LANCZOS)
    toy_px = (FRAME_SIZE - toy_w) // 2
    toy_py = FRAME_SIZE - toy_h - 10

    music_frames = []
    for step in range(4):
        f = Image.new("RGBA", (FRAME_SIZE, FRAME_SIZE), (0, 0, 0, 0))
        dance_y = int(math.sin(step * math.pi / 2) * 4)
        f.paste(toy_scaled, (toy_px, toy_py + dance_y), toy_scaled)
        draw = ImageDraw.Draw(f)
        draw_music_note(draw, toy_px + 15, toy_py + 5 + step * 3, color=(255, 215, 0, 240))
        draw_music_note(draw, toy_px + toy_w - 20, toy_py + 15 - step * 2, color=(255, 230, 80, 240))
        music_frames.append(f)
    create_sheet(music_frames).save(OUT_DIR / "music.png")

    # 17: WORK (4 frames typing on Bat-Computer)
    work_frames = []
    for step in range(4):
        f = Image.new("RGBA", (FRAME_SIZE, FRAME_SIZE), (0, 0, 0, 0))
        f.paste(sit_scaled, (sit_px + 20, sit_py), sit_scaled)
        draw = ImageDraw.Draw(f)
        # Bat Computer terminal
        draw.rectangle([sit_px - 35, sit_py + 45, sit_px + 10, sit_py + 90], fill=(20, 25, 35, 240), outline=(0, 200, 255, 220), width=2)
        # Bat logo on screen
        draw.polygon([(sit_px - 25, sit_py + 65), (sit_px - 15, sit_py + 60), (sit_px - 5, sit_py + 65), (sit_px - 15, sit_py + 75)], fill=(0, 255, 200, 240))
        work_frames.append(f)
    create_sheet(work_frames).save(OUT_DIR / "work.png")

    # 18: DRAG (4 frames dangling by cape)
    drag_frames = []
    for step in range(4):
        f = Image.new("RGBA", (FRAME_SIZE, FRAME_SIZE), (0, 0, 0, 0))
        f.paste(p_scaled, (p_px, p_py - 15), p_scaled)
        draw = ImageDraw.Draw(f)
        # Yellow question mark
        draw.text((p_px + p_w - 10, p_py - 25), "?", fill=(255, 220, 0, 240))
        drag_frames.append(f)
    create_sheet(drag_frames).save(OUT_DIR / "drag.png")

    # 19: IDEA (4 frames Bat-Signal eureka)
    idea_frames = []
    for step in range(4):
        f = Image.new("RGBA", (FRAME_SIZE, FRAME_SIZE), (0, 0, 0, 0))
        f.paste(sit_scaled, (sit_px, sit_py), sit_scaled)
        draw = ImageDraw.Draw(f)
        draw_bat_signal(draw, sit_px + sit_w // 2, sit_py - 25, r=16)
        idea_frames.append(f)
    create_sheet(idea_frames).save(OUT_DIR / "idea.png")

    # 20: SHRUG (4 frames head tilt)
    shrug_frames = []
    for step in range(4):
        f = Image.new("RGBA", (FRAME_SIZE, FRAME_SIZE), (0, 0, 0, 0))
        tilt = sit_scaled.rotate(step * 3 - 3, resample=RESAMPLE_BICUBIC)
        f.paste(tilt, (sit_px, sit_py), tilt)
        shrug_frames.append(f)
    create_sheet(shrug_frames).save(OUT_DIR / "shrug.png")

    print("Successfully generated all 20 Batman Cat animation sheets in", OUT_DIR)


if __name__ == "__main__":
    generate_all()
