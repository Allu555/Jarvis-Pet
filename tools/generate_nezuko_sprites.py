import math
import random
from pathlib import Path
from PIL import Image, ImageDraw
import numpy as np

RESAMPLE_LANCZOS = getattr(getattr(Image, "Resampling", Image), "LANCZOS", Image.LANCZOS if hasattr(Image, "LANCZOS") else Image.BICUBIC)
RESAMPLE_BICUBIC = getattr(getattr(Image, "Resampling", Image), "BICUBIC", Image.BICUBIC if hasattr(Image, "BICUBIC") else Image.BILINEAR)

FRAME_SIZE = 192
OUT_DIR = Path(__file__).parent / "sprites" / "nezuko"
SOURCE_DIR = Path(__file__).parent / "nezuko_sources"
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

def draw_pink_flame(draw: ImageDraw.ImageDraw, cx: int, cy: int, r: int, color=(255, 105, 180, 220)):
    points = []
    for angle in range(0, 360, 20):
        rad = math.radians(angle)
        offset = math.sin(rad * 5) * 6
        x = cx + int((r + offset) * math.cos(rad))
        y = cy + int((r + offset) * math.sin(rad))
        points.append((x, y))
    if len(points) > 1:
        draw.polygon(points, fill=color, outline=(255, 192, 203, 255))


def draw_sakura_petal(draw: ImageDraw.ImageDraw, x: int, y: int, size: int = 5, color=(255, 182, 193, 230)):
    draw.ellipse([x - size, y - size // 2, x + size, y + size // 2], fill=color)


def draw_sparkle(draw: ImageDraw.ImageDraw, cx: int, cy: int, size: int = 8, color=(255, 150, 200, 240)):
    draw.line([cx - size, cy, cx + size, cy], fill=color, width=2)
    draw.line([cx, cy - size, cx, cy + size], fill=color, width=2)
    s2 = size // 2
    draw.line([cx - s2, cy - s2, cx + s2, cy + s2], fill=color, width=1)
    draw.line([cx - s2, cy + s2, cx + s2, cy - s2], fill=color, width=1)


def draw_music_note(draw: ImageDraw.ImageDraw, x: int, y: int, color=(255, 105, 180, 240)):
    draw.ellipse([x, y + 6, x + 5, y + 10], fill=color)
    draw.line([x + 4, y + 8, x + 4, y], fill=color, width=2)
    draw.line([x + 4, y, x + 8, y + 2], fill=color, width=2)


def generate_all():
    print("Generating Nezuko 20 HD animation sheets...")

    # Load sources
    walk_imgs = [load_source(f"walk_{i}") for i in range(6)]
    ref_standing = load_source("ref_standing")
    flame_attack = load_source("flame_attack")
    tiny_run = load_source("tiny_run")
    box_sleep = load_source("box_sleep")
    kick_img = load_source("kick")
    eat_candy = load_source("eat_candy")
    celebrate_img = load_source("celebrate")

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

        # Subtle sakura petals on step
        draw = ImageDraw.Draw(frame)
        if i in [1, 4]:
            draw_sakura_petal(draw, paste_x + 10, paste_y + new_h - 10, size=4)

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
            draw_sparkle(draw, std_px + std_w - 15, std_py + 30, size=5, color=(255, 180, 220, 200))
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
            draw.line([std_px + int(std_w * 0.38), eye_y, std_px + int(std_w * 0.46), eye_y], fill=(60, 30, 40, 255), width=2)
            draw.line([std_px + int(std_w * 0.54), eye_y, std_px + int(std_w * 0.62), eye_y], fill=(60, 30, 40, 255), width=2)
        blink_frames.append(f)
    create_sheet(blink_frames).save(OUT_DIR / "blink.png")

    # 5: SIT (4 frames polite sitting)
    eat_aspect = eat_candy.width / max(1, eat_candy.height)
    eat_h = int(TARGET_H * 0.85)
    eat_w = int(eat_h * eat_aspect)
    eat_scaled = eat_candy.resize((eat_w, eat_h), RESAMPLE_LANCZOS)
    eat_px = (FRAME_SIZE - eat_w) // 2
    eat_py = FRAME_SIZE - eat_h - 8

    sit_frames = []
    for step in range(4):
        f = Image.new("RGBA", (FRAME_SIZE, FRAME_SIZE), (0, 0, 0, 0))
        bob = int(math.sin(step * math.pi / 2) * 1.5)
        f.paste(eat_scaled, (eat_px, eat_py + bob), eat_scaled)
        sit_frames.append(f)
    create_sheet(sit_frames).save(OUT_DIR / "sit.png")

    # 6: SLEEP (4 frames inside wooden box)
    box_aspect = box_sleep.width / max(1, box_sleep.height)
    box_h = int(TARGET_H * 0.88)
    box_w = int(box_h * box_aspect)
    box_scaled = box_sleep.resize((box_w, box_h), RESAMPLE_LANCZOS)
    box_px = (FRAME_SIZE - box_w) // 2
    box_py = FRAME_SIZE - box_h - 8

    sleep_frames = []
    for step in range(4):
        f = Image.new("RGBA", (FRAME_SIZE, FRAME_SIZE), (0, 0, 0, 0))
        breath = int(math.sin(step * math.pi / 2) * 2)
        f.paste(box_scaled, (box_px, box_py + breath), box_scaled)
        draw = ImageDraw.Draw(f)
        zx = box_px + box_w - 15 + step * 4
        zy = box_py - 5 - step * 6
        draw.text((zx, zy), "z", fill=(255, 180, 220, 220))
        sleep_frames.append(f)
    create_sheet(sleep_frames).save(OUT_DIR / "sleep.png")

    # 7: WAKE
    wake_frames = []
    for step in range(4):
        f = Image.new("RGBA", (FRAME_SIZE, FRAME_SIZE), (0, 0, 0, 0))
        if step < 2:
            f.paste(box_scaled, (box_px, box_py), box_scaled)
        else:
            f.paste(std_scaled, (std_px, std_py), std_scaled)
            draw = ImageDraw.Draw(f)
            draw_sparkle(draw, std_px + 20, std_py + 20, size=6, color=(255, 180, 220, 220))
        wake_frames.append(f)
    create_sheet(wake_frames).save(OUT_DIR / "wake.png")

    # 8: EAT (4 frames eating konpeito candy)
    eat_frames = []
    for step in range(4):
        f = Image.new("RGBA", (FRAME_SIZE, FRAME_SIZE), (0, 0, 0, 0))
        munch = int(math.sin(step * math.pi) * 3)
        f.paste(eat_scaled, (eat_px, eat_py + munch), eat_scaled)
        draw = ImageDraw.Draw(f)
        # Colorful candy sparkles
        colors = [(255, 150, 200, 240), (100, 220, 255, 240), (255, 240, 100, 240), (150, 255, 150, 240)]
        draw_sparkle(draw, eat_px + eat_w - 25, eat_py + 15, size=5, color=colors[step % 4])
        eat_frames.append(f)
    create_sheet(eat_frames).save(OUT_DIR / "eat.png")

    # 9: HAPPY (4 frames celebrating with bamboo smile)
    cel_aspect = celebrate_img.width / max(1, celebrate_img.height)
    cel_h = TARGET_H
    cel_w = int(cel_h * cel_aspect)
    cel_scaled = celebrate_img.resize((cel_w, cel_h), RESAMPLE_LANCZOS)
    cel_px = (FRAME_SIZE - cel_w) // 2
    cel_py = FRAME_SIZE - cel_h - 8

    happy_frames = []
    for step in range(4):
        f = Image.new("RGBA", (FRAME_SIZE, FRAME_SIZE), (0, 0, 0, 0))
        hop = int(abs(math.sin(step * math.pi / 2)) * 6)
        f.paste(cel_scaled, (cel_px, cel_py - hop), cel_scaled)
        draw = ImageDraw.Draw(f)
        draw_sparkle(draw, cel_px + 10 + step * 12, cel_py - 10, size=7, color=(255, 150, 220, 240))
        draw_sakura_petal(draw, cel_px + cel_w - 15, cel_py + 25, size=5)
        happy_frames.append(f)
    create_sheet(happy_frames).save(OUT_DIR / "happy.png")

    # 10: SAD
    sad_frames = []
    for step in range(4):
        f = Image.new("RGBA", (FRAME_SIZE, FRAME_SIZE), (0, 0, 0, 0))
        f.paste(std_scaled, (std_px, std_py + 3), std_scaled)
        draw = ImageDraw.Draw(f)
        draw.ellipse([std_px + std_w // 2 - 12, std_py + int(std_h * 0.22) + step * 2, std_px + std_w // 2 - 8, std_py + int(std_h * 0.22) + 6 + step * 2], fill=(150, 200, 255, 220))
        sad_frames.append(f)
    create_sheet(sad_frames).save(OUT_DIR / "sad.png")

    # 11: CRY
    cry_frames = []
    for step in range(4):
        f = Image.new("RGBA", (FRAME_SIZE, FRAME_SIZE), (0, 0, 0, 0))
        f.paste(std_scaled, (std_px, std_py + 4), std_scaled)
        draw = ImageDraw.Draw(f)
        for side in [-14, 14]:
            tx = std_px + std_w // 2 + side
            ty = std_py + int(std_h * 0.2) + step * 4
            draw.ellipse([tx - 3, ty, tx + 3, ty + 8], fill=(130, 210, 255, 230))
        cry_frames.append(f)
    create_sheet(cry_frames).save(OUT_DIR / "cry.png")

    # 12: JUMP (4 frames flying demon kick)
    kick_aspect = kick_img.width / max(1, kick_img.height)
    kick_h = TARGET_H
    kick_w = int(kick_h * kick_aspect)
    kick_scaled = kick_img.resize((kick_w, kick_h), RESAMPLE_LANCZOS)
    kick_px = (FRAME_SIZE - kick_w) // 2
    kick_py = FRAME_SIZE - kick_h - 8

    jump_frames = []
    for step in range(4):
        f = Image.new("RGBA", (FRAME_SIZE, FRAME_SIZE), (0, 0, 0, 0))
        lift = int(math.sin((step + 1) * math.pi / 5) * 35)
        f.paste(kick_scaled, (kick_px, kick_py - lift), kick_scaled)
        draw = ImageDraw.Draw(f)
        draw_pink_flame(draw, kick_px + kick_w - 20, kick_py + 20 - lift, r=12)
        jump_frames.append(f)
    create_sheet(jump_frames).save(OUT_DIR / "jump.png")

    # 13: FALL
    fall_frames = []
    for step in range(4):
        f = Image.new("RGBA", (FRAME_SIZE, FRAME_SIZE), (0, 0, 0, 0))
        drop = int(step * 6)
        f.paste(kick_scaled, (kick_px, kick_py - 20 + drop), kick_scaled)
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
            draw.ellipse([std_px - 8, std_py + std_h - 6, std_px + std_w + 8, std_py + std_h + 4], outline=(255, 180, 220, 150), width=2)
        land_frames.append(f)
    create_sheet(land_frames).save(OUT_DIR / "land.png")

    # 15: ROAR (Blood Demon Art Pyrokinesis!)
    flm_aspect = flame_attack.width / max(1, flame_attack.height)
    flm_h = TARGET_H
    flm_w = int(flm_h * flm_aspect)
    flm_scaled = flame_attack.resize((flm_w, flm_h), RESAMPLE_LANCZOS)
    flm_px = (FRAME_SIZE - flm_w) // 2
    flm_py = FRAME_SIZE - flm_h - 8

    roar_frames = []
    for step in range(4):
        f = Image.new("RGBA", (FRAME_SIZE, FRAME_SIZE), (0, 0, 0, 0))
        shake = (step % 2) * 3 - 1
        f.paste(flm_scaled, (flm_px + shake, flm_py), flm_scaled)
        draw = ImageDraw.Draw(f)
        draw_pink_flame(draw, flm_px + flm_w - 40, flm_py + 40, r=20 + step * 4, color=(255, 50, 150, 230))
        roar_frames.append(f)
    create_sheet(roar_frames).save(OUT_DIR / "roar.png")

    # 16: MUSIC (Tiny-Nezuko dancing with music notes)
    tiny_aspect = tiny_run.width / max(1, tiny_run.height)
    tiny_h = int(TARGET_H * 0.75)
    tiny_w = int(tiny_h * tiny_aspect)
    tiny_scaled = tiny_run.resize((tiny_w, tiny_h), RESAMPLE_LANCZOS)
    tiny_px = (FRAME_SIZE - tiny_w) // 2
    tiny_py = FRAME_SIZE - tiny_h - 8

    music_frames = []
    for step in range(4):
        f = Image.new("RGBA", (FRAME_SIZE, FRAME_SIZE), (0, 0, 0, 0))
        dance_y = int(math.sin(step * math.pi / 2) * 6)
        f.paste(tiny_scaled, (tiny_px, tiny_py + dance_y), tiny_scaled)
        draw = ImageDraw.Draw(f)
        draw_music_note(draw, tiny_px + 10, tiny_py + 5 + step * 3, color=(255, 105, 180, 240))
        draw_music_note(draw, tiny_px + tiny_w - 15, tiny_py + 15 - step * 2, color=(255, 150, 200, 240))
        music_frames.append(f)
    create_sheet(music_frames).save(OUT_DIR / "music.png")

    # 17: WORK (Tiny-Nezuko running back and forth delivering stuff)
    work_frames = []
    for step in range(4):
        f = Image.new("RGBA", (FRAME_SIZE, FRAME_SIZE), (0, 0, 0, 0))
        offset_x = (step - 1.5) * 15
        hop = int(abs(math.sin(step * math.pi)) * 8)
        f.paste(tiny_scaled, (int(tiny_px + offset_x), tiny_py - hop), tiny_scaled)
        draw = ImageDraw.Draw(f)
        draw_sakura_petal(draw, int(tiny_px + offset_x - 10), tiny_py + tiny_h - 10)
        work_frames.append(f)
    create_sheet(work_frames).save(OUT_DIR / "work.png")

    # 18: DRAG (Tiny-Nezuko dangling)
    drag_frames = []
    for step in range(4):
        f = Image.new("RGBA", (FRAME_SIZE, FRAME_SIZE), (0, 0, 0, 0))
        f.paste(tiny_scaled, (tiny_px, tiny_py - 20), tiny_scaled)
        draw = ImageDraw.Draw(f)
        draw.text((tiny_px + tiny_w - 5, tiny_py - 25), "?", fill=(255, 105, 180, 240))
        drag_frames.append(f)
    create_sheet(drag_frames).save(OUT_DIR / "drag.png")

    # 19: IDEA (Sakura lightbulb)
    idea_frames = []
    for step in range(4):
        f = Image.new("RGBA", (FRAME_SIZE, FRAME_SIZE), (0, 0, 0, 0))
        f.paste(std_scaled, (std_px, std_py), std_scaled)
        draw = ImageDraw.Draw(f)
        draw_sparkle(draw, std_px + std_w // 2, std_py - 20, size=14, color=(255, 150, 220, 240))
        idea_frames.append(f)
    create_sheet(idea_frames).save(OUT_DIR / "idea.png")

    # 20: SHRUG (Bamboo muzzle wiggle & head tilt)
    shrug_frames = []
    for step in range(4):
        f = Image.new("RGBA", (FRAME_SIZE, FRAME_SIZE), (0, 0, 0, 0))
        tilt = std_scaled.rotate(step * 3 - 3, resample=RESAMPLE_BICUBIC)
        f.paste(tilt, (std_px, std_py), tilt)
        shrug_frames.append(f)
    create_sheet(shrug_frames).save(OUT_DIR / "shrug.png")

    print("Successfully generated all 20 Nezuko animation sheets in", OUT_DIR)


if __name__ == "__main__":
    generate_all()
