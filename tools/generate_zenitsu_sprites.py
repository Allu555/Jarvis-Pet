import math
import random
from pathlib import Path
from PIL import Image, ImageDraw
import numpy as np

RESAMPLE_LANCZOS = getattr(getattr(Image, "Resampling", Image), "LANCZOS", Image.LANCZOS if hasattr(Image, "LANCZOS") else Image.BICUBIC)
RESAMPLE_BICUBIC = getattr(getattr(Image, "Resampling", Image), "BICUBIC", Image.BICUBIC if hasattr(Image, "BICUBIC") else Image.BILINEAR)

FRAME_SIZE = 192
OUT_DIR = Path(__file__).parent / "sprites" / "zenitsu"
SOURCE_DIR = Path(__file__).parent / "zenitsu_sources"
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

def draw_lightning_bolt(draw: ImageDraw.ImageDraw, x1: int, y1: int, x2: int, y2: int, color=(255, 235, 50, 240), width=3):
    dx = x2 - x1
    dy = y2 - y1
    mid_x = (x1 + x2) // 2 + random.randint(-15, 15)
    mid_y = (y1 + y2) // 2 + random.randint(-15, 15)
    draw.line([(x1, y1), (mid_x, mid_y), (x2, y2)], fill=color, width=width)
    draw.line([(x1, y1), (mid_x, mid_y), (x2, y2)], fill=(255, 255, 255, 255), width=max(1, width - 2))


def draw_sparkle(draw: ImageDraw.ImageDraw, cx: int, cy: int, size: int = 8, color=(255, 215, 0, 240)):
    draw.line([cx - size, cy, cx + size, cy], fill=color, width=2)
    draw.line([cx, cy - size, cx, cy + size], fill=color, width=2)
    s2 = size // 2
    draw.line([cx - s2, cy - s2, cx + s2, cy + s2], fill=color, width=1)
    draw.line([cx - s2, cy + s2, cx + s2, cy - s2], fill=color, width=1)


def draw_music_note(draw: ImageDraw.ImageDraw, x: int, y: int, color=(255, 220, 0, 240)):
    draw.ellipse([x, y + 6, x + 5, y + 10], fill=color)
    draw.line([x + 4, y + 8, x + 4, y], fill=color, width=2)
    draw.line([x + 4, y, x + 8, y + 2], fill=color, width=2)


def generate_all():
    print("Generating Zenitsu 20 HD animation sheets...")

    # Load sources
    walk_imgs = [load_source(f"walk_{i}") for i in range(6)]
    ref_standing = load_source("ref_standing")
    thunderclap = load_source("thunderclap")
    crying_img = load_source("crying")
    sleep_swordsman = load_source("sleep_swordsman")
    eat_onigiri = load_source("eat_onigiri")
    scared_jump = load_source("scared_jump")
    confident_sparkle = load_source("confident_sparkle")

    TARGET_H = 158

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
        paste_y = FRAME_SIZE - new_h - 8
        frame.paste(scaled, (paste_x, paste_y), scaled)

        # Micro dust puffs & sparks on sprint
        draw = ImageDraw.Draw(frame)
        if i in [1, 4]:
            draw_sparkle(draw, paste_x + 10, paste_y + new_h - 10, size=4, color=(255, 230, 80, 200))

        walk_frames_right.append(frame)

    walk_frames_left = [f.transpose(Image.FLIP_LEFT_RIGHT) for f in walk_frames_right]
    create_sheet(walk_frames_left).save(OUT_DIR / "walk_left.png")
    create_sheet(walk_frames_right).save(OUT_DIR / "walk_right.png")

    # Base standing frame
    std_aspect = ref_standing.width / max(1, ref_standing.height)
    std_h = TARGET_H
    std_w = int(std_h * std_aspect)
    std_scaled = ref_standing.resize((std_w, std_h), RESAMPLE_LANCZOS)
    std_head_x = get_head_center_x(std_scaled)
    std_px = int(FRAME_SIZE // 2 - std_head_x)
    std_py = FRAME_SIZE - std_h - 8

    # 3: IDLE & IDLE_FLIP (4 frames breathing)
    idle_frames = []
    for step in range(4):
        f = Image.new("RGBA", (FRAME_SIZE, FRAME_SIZE), (0, 0, 0, 0))
        bob = int(math.sin(step * math.pi / 2) * 2)
        f.paste(std_scaled, (std_px, std_py + bob), std_scaled)
        draw = ImageDraw.Draw(f)
        if step in [1, 3]:
            draw_sparkle(draw, std_px + std_w - 15, std_py + 25, size=5, color=(255, 230, 80, 180))
        idle_frames.append(f)
    create_sheet(idle_frames).save(OUT_DIR / "idle.png")
    create_sheet([f.transpose(Image.FLIP_LEFT_RIGHT) for f in idle_frames]).save(OUT_DIR / "idle_flip.png")

    # 4: BLINK (4 frames)
    blink_frames = []
    for step in range(4):
        f = Image.new("RGBA", (FRAME_SIZE, FRAME_SIZE), (0, 0, 0, 0))
        f.paste(std_scaled, (std_px, std_py), std_scaled)
        draw = ImageDraw.Draw(f)
        if step in [1, 2]:
            eye_y = std_py + int(std_h * 0.17)
            draw.line([std_px + int(std_w * 0.38), eye_y, std_px + int(std_w * 0.46), eye_y], fill=(60, 40, 30, 255), width=2)
            draw.line([std_px + int(std_w * 0.54), eye_y, std_px + int(std_w * 0.62), eye_y], fill=(60, 40, 30, 255), width=2)
        blink_frames.append(f)
    create_sheet(blink_frames).save(OUT_DIR / "blink.png")

    # 5: SIT (4 frames resting with onigiri)
    onigiri_aspect = eat_onigiri.width / max(1, eat_onigiri.height)
    onigiri_h = TARGET_H
    onigiri_w = int(onigiri_h * onigiri_aspect)
    onigiri_scaled = eat_onigiri.resize((onigiri_w, onigiri_h), RESAMPLE_LANCZOS)
    onigiri_px = (FRAME_SIZE - onigiri_w) // 2
    onigiri_py = FRAME_SIZE - onigiri_h - 8

    sit_frames = []
    for step in range(4):
        f = Image.new("RGBA", (FRAME_SIZE, FRAME_SIZE), (0, 0, 0, 0))
        bob = int(math.sin(step * math.pi / 2) * 1.5)
        f.paste(onigiri_scaled, (onigiri_px, onigiri_py + bob), onigiri_scaled)
        sit_frames.append(f)
    create_sheet(sit_frames).save(OUT_DIR / "sit.png")

    # 6: SLEEP (Asleep Swordsman Thunder Mode!)
    sl_aspect = sleep_swordsman.width / max(1, sleep_swordsman.height)
    sl_h = TARGET_H
    sl_w = int(sl_h * sl_aspect)
    sl_scaled = sleep_swordsman.resize((sl_w, sl_h), RESAMPLE_LANCZOS)
    sl_px = (FRAME_SIZE - sl_w) // 2
    sl_py = FRAME_SIZE - sl_h - 8

    sleep_frames = []
    for step in range(4):
        f = Image.new("RGBA", (FRAME_SIZE, FRAME_SIZE), (0, 0, 0, 0))
        breath = int(math.sin(step * math.pi / 2) * 2)
        f.paste(sl_scaled, (sl_px, sl_py + breath), sl_scaled)
        draw = ImageDraw.Draw(f)
        # Sleeping snot bubble / Zzz
        zx = sl_px + sl_w - 15 + step * 4
        zy = sl_py + 10 - step * 6
        draw.text((zx, zy), "z", fill=(100, 200, 255, 220))
        # Subtle thunder spark while sleeping!
        if step in [1, 3]:
            draw_sparkle(draw, sl_px + 20, sl_py + sl_h - 20, size=5, color=(255, 230, 80, 220))
        sleep_frames.append(f)
    create_sheet(sleep_frames).save(OUT_DIR / "sleep.png")

    # 7: WAKE
    wake_frames = []
    for step in range(4):
        f = Image.new("RGBA", (FRAME_SIZE, FRAME_SIZE), (0, 0, 0, 0))
        if step < 2:
            f.paste(sl_scaled, (sl_px, sl_py), sl_scaled)
        else:
            f.paste(std_scaled, (std_px, std_py), std_scaled)
            draw = ImageDraw.Draw(f)
            draw_sparkle(draw, std_px + 20, std_py + 20, size=6, color=(255, 230, 80, 220))
        wake_frames.append(f)
    create_sheet(wake_frames).save(OUT_DIR / "wake.png")

    # 8: EAT (4 frames eating onigiri)
    eat_frames = []
    for step in range(4):
        f = Image.new("RGBA", (FRAME_SIZE, FRAME_SIZE), (0, 0, 0, 0))
        munch = int(math.sin(step * math.pi) * 3)
        f.paste(onigiri_scaled, (onigiri_px, onigiri_py + munch), onigiri_scaled)
        draw = ImageDraw.Draw(f)
        draw.text((onigiri_px + onigiri_w - 15, onigiri_py + 25), "Nom!", fill=(255, 200, 50, 240))
        eat_frames.append(f)
    create_sheet(eat_frames).save(OUT_DIR / "eat.png")

    # 9: HAPPY (4 frames confident sparkle stance)
    conf_aspect = confident_sparkle.width / max(1, confident_sparkle.height)
    conf_h = TARGET_H
    conf_w = int(conf_h * conf_aspect)
    conf_scaled = confident_sparkle.resize((conf_w, conf_h), RESAMPLE_LANCZOS)
    conf_px = (FRAME_SIZE - conf_w) // 2
    conf_py = FRAME_SIZE - conf_h - 8

    happy_frames = []
    for step in range(4):
        f = Image.new("RGBA", (FRAME_SIZE, FRAME_SIZE), (0, 0, 0, 0))
        hop = int(abs(math.sin(step * math.pi / 2)) * 5)
        f.paste(conf_scaled, (conf_px, conf_py - hop), conf_scaled)
        draw = ImageDraw.Draw(f)
        draw_sparkle(draw, conf_px + 10 + step * 12, conf_py - 10, size=7, color=(255, 220, 0, 240))
        draw_sparkle(draw, conf_px + conf_w - 10, conf_py + 20, size=6, color=(255, 240, 100, 220))
        happy_frames.append(f)
    create_sheet(happy_frames).save(OUT_DIR / "happy.png")

    # 10: SAD (Trembling shiver)
    sad_frames = []
    for step in range(4):
        f = Image.new("RGBA", (FRAME_SIZE, FRAME_SIZE), (0, 0, 0, 0))
        shiver = (step % 2) * 2 - 1
        f.paste(std_scaled, (std_px + shiver, std_py + 3), std_scaled)
        draw = ImageDraw.Draw(f)
        draw.ellipse([std_px + std_w // 2 - 10, std_py + int(std_h * 0.2) + step * 2, std_px + std_w // 2 - 6, std_py + int(std_h * 0.2) + 6 + step * 2], fill=(150, 200, 255, 220))
        sad_frames.append(f)
    create_sheet(sad_frames).save(OUT_DIR / "sad.png")

    # 11: CRY (Sobbing comically on knees)
    cry_aspect = crying_img.width / max(1, crying_img.height)
    cry_h = int(TARGET_H * 0.85)
    cry_w = int(cry_h * cry_aspect)
    cry_scaled = crying_img.resize((cry_w, cry_h), RESAMPLE_LANCZOS)
    cry_px = (FRAME_SIZE - cry_w) // 2
    cry_py = FRAME_SIZE - cry_h - 8

    cry_frames = []
    for step in range(4):
        f = Image.new("RGBA", (FRAME_SIZE, FRAME_SIZE), (0, 0, 0, 0))
        sob_bob = int(math.sin(step * math.pi) * 3)
        f.paste(cry_scaled, (cry_px, cry_py + sob_bob), cry_scaled)
        draw = ImageDraw.Draw(f)
        for side in [-18, 18]:
            tx = cry_px + cry_w // 2 + side
            ty = cry_py + int(cry_h * 0.25) + step * 5
            draw.ellipse([tx - 4, ty, tx + 4, ty + 10], fill=(100, 210, 255, 240))
        cry_frames.append(f)
    create_sheet(cry_frames).save(OUT_DIR / "cry.png")

    # 12: JUMP (Scared jumping scream)
    jump_aspect = scared_jump.width / max(1, scared_jump.height)
    jump_h = TARGET_H
    jump_w = int(jump_h * jump_aspect)
    jump_scaled = scared_jump.resize((jump_w, jump_h), RESAMPLE_LANCZOS)
    jump_px = (FRAME_SIZE - jump_w) // 2
    jump_py = FRAME_SIZE - jump_h - 8

    jump_frames = []
    for step in range(4):
        f = Image.new("RGBA", (FRAME_SIZE, FRAME_SIZE), (0, 0, 0, 0))
        lift = int(math.sin((step + 1) * math.pi / 5) * 35)
        f.paste(jump_scaled, (jump_px, jump_py - lift), jump_scaled)
        draw = ImageDraw.Draw(f)
        draw.text((jump_px + jump_w - 15, jump_py - lift - 10), "GYAAH!", fill=(255, 220, 50, 240))
        jump_frames.append(f)
    create_sheet(jump_frames).save(OUT_DIR / "jump.png")

    # 13: FALL
    fall_frames = []
    for step in range(4):
        f = Image.new("RGBA", (FRAME_SIZE, FRAME_SIZE), (0, 0, 0, 0))
        drop = int(step * 6)
        f.paste(jump_scaled, (jump_px, jump_py - 20 + drop), jump_scaled)
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
            draw.ellipse([std_px - 8, std_py + std_h - 6, std_px + std_w + 8, std_py + std_h + 4], outline=(255, 230, 80, 150), width=2)
        land_frames.append(f)
    create_sheet(land_frames).save(OUT_DIR / "land.png")

    # 15: ROAR (Thunder Breathing: Thunderclap and Flash!)
    thun_aspect = thunderclap.width / max(1, thunderclap.height)
    thun_h = TARGET_H
    thun_w = int(thun_h * thun_aspect)
    thun_scaled = thunderclap.resize((thun_w, thun_h), RESAMPLE_LANCZOS)
    thun_px = (FRAME_SIZE - thun_w) // 2
    thun_py = FRAME_SIZE - thun_h - 8

    roar_frames = []
    for step in range(4):
        f = Image.new("RGBA", (FRAME_SIZE, FRAME_SIZE), (0, 0, 0, 0))
        shake = (step % 2) * 3 - 1
        f.paste(thun_scaled, (thun_px + shake, thun_py), thun_scaled)
        draw = ImageDraw.Draw(f)
        # Giant lightning bursts
        for _ in range(3):
            draw_lightning_bolt(draw, thun_px + 20, thun_py + 40, thun_px + thun_w + 10, thun_py + 80, color=(255, 235, 50, 240), width=3)
            draw_lightning_bolt(draw, thun_px + thun_w - 20, thun_py + 20, thun_px - 10, thun_py + 100, color=(255, 255, 120, 240), width=2)
        roar_frames.append(f)
    create_sheet(roar_frames).save(OUT_DIR / "roar.png")

    # 16: MUSIC (Dancing with sparks & notes)
    music_frames = []
    for step in range(4):
        f = Image.new("RGBA", (FRAME_SIZE, FRAME_SIZE), (0, 0, 0, 0))
        dance_y = int(math.sin(step * math.pi / 2) * 6)
        f.paste(conf_scaled, (conf_px, conf_py + dance_y), conf_scaled)
        draw = ImageDraw.Draw(f)
        draw_music_note(draw, conf_px + 10, conf_py + 5 + step * 3, color=(255, 215, 0, 240))
        draw_music_note(draw, conf_px + conf_w - 15, conf_py + 15 - step * 2, color=(255, 230, 80, 240))
        music_frames.append(f)
    create_sheet(music_frames).save(OUT_DIR / "music.png")

    # 17: WORK (Godspeed Dash)
    work_frames = []
    for step in range(4):
        f = Image.new("RGBA", (FRAME_SIZE, FRAME_SIZE), (0, 0, 0, 0))
        offset_x = (step - 1.5) * 18
        hop = int(abs(math.sin(step * math.pi)) * 6)
        f.paste(thun_scaled, (int(thun_px + offset_x), thun_py - hop), thun_scaled)
        draw = ImageDraw.Draw(f)
        draw_lightning_bolt(draw, int(thun_px + offset_x - 15), thun_py + thun_h - 20, int(thun_px + offset_x + thun_w), thun_py + thun_h - 10, color=(255, 220, 0, 220), width=2)
        work_frames.append(f)
    create_sheet(work_frames).save(OUT_DIR / "work.png")

    # 18: DRAG (Panicking dangle)
    drag_frames = []
    for step in range(4):
        f = Image.new("RGBA", (FRAME_SIZE, FRAME_SIZE), (0, 0, 0, 0))
        f.paste(jump_scaled, (jump_px, jump_py - 20), jump_scaled)
        draw = ImageDraw.Draw(f)
        draw.text((jump_px + jump_w - 5, jump_py - 25), "!", fill=(255, 220, 0, 240))
        drag_frames.append(f)
    create_sheet(drag_frames).save(OUT_DIR / "drag.png")

    # 19: IDEA (Lightning lightbulb)
    idea_frames = []
    for step in range(4):
        f = Image.new("RGBA", (FRAME_SIZE, FRAME_SIZE), (0, 0, 0, 0))
        f.paste(std_scaled, (std_px, std_py), std_scaled)
        draw = ImageDraw.Draw(f)
        draw_sparkle(draw, std_px + std_w // 2, std_py - 20, size=14, color=(255, 230, 50, 240))
        idea_frames.append(f)
    create_sheet(idea_frames).save(OUT_DIR / "idea.png")

    # 20: SHRUG (Nervous head scratch)
    shrug_frames = []
    for step in range(4):
        f = Image.new("RGBA", (FRAME_SIZE, FRAME_SIZE), (0, 0, 0, 0))
        tilt = std_scaled.rotate(step * 3 - 3, resample=RESAMPLE_BICUBIC)
        f.paste(tilt, (std_px, std_py), tilt)
        shrug_frames.append(f)
    create_sheet(shrug_frames).save(OUT_DIR / "shrug.png")

    print("Successfully generated all 20 Zenitsu animation sheets in", OUT_DIR)


if __name__ == "__main__":
    generate_all()
