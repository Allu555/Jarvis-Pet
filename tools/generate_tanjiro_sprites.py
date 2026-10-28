import math
import random
from pathlib import Path
from PIL import Image, ImageDraw
import numpy as np

FRAME_SIZE = 192
OUT_DIR = Path(__file__).parent / "sprites" / "tanjiro"
SOURCE_DIR = Path(__file__).parent / "tanjiro_sources"
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

def draw_water_wave(draw: ImageDraw.ImageDraw, cx: int, cy: int, r: int, color=(0, 180, 255, 200), width=3):
    points = []
    for angle in range(0, 360, 15):
        rad = math.radians(angle)
        offset = math.sin(rad * 4) * 4
        x = cx + int((r + offset) * math.cos(rad))
        y = cy + int((r + offset) * math.sin(rad))
        points.append((x, y))
    if len(points) > 1:
        draw.polygon(points, outline=color, width=width)


def draw_water_splash(draw: ImageDraw.ImageDraw, x: int, y: int, size: int = 6, color=(80, 210, 255, 220)):
    draw.ellipse([x - size, y - size, x + size, y + size], fill=color)
    draw.ellipse([x - size + 2, y - size + 2, x, y], fill=(255, 255, 255, 230))


def draw_music_note(draw: ImageDraw.ImageDraw, x: int, y: int, color=(0, 220, 255, 230)):
    draw.ellipse([x, y + 6, x + 5, y + 10], fill=color)
    draw.line([x + 4, y + 8, x + 4, y], fill=color, width=2)
    draw.line([x + 4, y, x + 8, y + 2], fill=color, width=2)


def draw_sparkle(draw: ImageDraw.ImageDraw, cx: int, cy: int, size: int = 8, color=(255, 230, 80, 240)):
    draw.line([cx - size, cy, cx + size, cy], fill=color, width=2)
    draw.line([cx, cy - size, cx, cy + size], fill=color, width=2)
    s2 = size // 2
    draw.line([cx - s2, cy - s2, cx + s2, cy + s2], fill=color, width=1)
    draw.line([cx - s2, cy + s2, cx + s2, cy - s2], fill=color, width=1)


def draw_flame_particle(draw: ImageDraw.ImageDraw, x: int, y: int, r: int = 4, color=(255, 90, 20, 220)):
    draw.polygon([(x, y - r * 2), (x - r, y + r), (x + r, y + r)], fill=color)


# ── Generators ──

def gen_idle(standing: Image.Image) -> Image.Image:
    scale = 162.0 / standing.height
    nw = int(standing.width * scale)
    nh = int(standing.height * scale)
    base = standing.resize((nw, nh), Image.Resampling.LANCZOS)
    head_x = get_head_center_x(base)

    frames = []
    offsets = [0, -1, -2, -3, -2, -1]
    for dy in offsets:
        canvas = Image.new("RGBA", (FRAME_SIZE, FRAME_SIZE), (0, 0, 0, 0))
        px = int(96 - head_x)
        py = 192 - nh - 10 + dy
        canvas.paste(base, (px, py), base)
        frames.append(canvas)
    return create_sheet(frames)


def gen_walk(walk_poses: list) -> Image.Image:
    frames = []
    for pose in walk_poses:
        head_x = get_head_center_x(pose)
        scale = 160.0 / pose.height
        nw = int(pose.width * scale)
        nh = int(pose.height * scale)
        scaled_head_x = head_x * scale

        resized = pose.resize((nw, nh), Image.Resampling.LANCZOS)
        canvas = Image.new("RGBA", (FRAME_SIZE, FRAME_SIZE), (0, 0, 0, 0))

        # Head/Torso centered at x=96, feet grounded at bottom
        px = int(96 - scaled_head_x)
        py = 192 - nh - 10
        canvas.paste(resized, (px, py), resized)
        frames.append(canvas)
    return create_sheet(frames)


def gen_water_dragon(water_pose: Image.Image) -> Image.Image:
    scale = min(175.0 / water_pose.width, 172.0 / water_pose.height)
    nw = int(water_pose.width * scale)
    nh = int(water_pose.height * scale)
    base = water_pose.resize((nw, nh), Image.Resampling.LANCZOS)

    frames = []
    for f in range(6):
        canvas = Image.new("RGBA", (FRAME_SIZE, FRAME_SIZE), (0, 0, 0, 0))
        draw = ImageDraw.Draw(canvas)

        # Dynamic Water Dragon auras & ripples
        for i in range(4):
            phase = f * 0.8 + i * 1.5
            sx = int(96 + math.cos(phase) * 65)
            sy = int(96 + math.sin(phase) * 60)
            draw_water_splash(draw, sx, sy, size=random.randint(4, 7), color=(100, 220, 255, 220))
            draw_water_splash(draw, sx + 4, sy - 4, size=random.randint(2, 4), color=(255, 255, 255, 240))

        draw_water_wave(draw, 96, 96, 68 + f * 2, color=(0, 160, 255, 170), width=3)
        draw_water_wave(draw, 96, 96, 48 + f * 2, color=(120, 230, 255, 200), width=2)

        px = (FRAME_SIZE - nw) // 2
        py = (FRAME_SIZE - nh) // 2
        canvas.paste(base, (px, py), base)

        # Hinokami sun spark mix
        draw_flame_particle(draw, 145 + f * 2, 45 + f * 3, r=4, color=(255, 80, 20, 230))
        draw_flame_particle(draw, 55 - f * 2, 65 + f * 2, r=4, color=(255, 170, 0, 220))

        frames.append(canvas)
    return create_sheet(frames)


def gen_eat_onigiri(eat_pose: Image.Image) -> Image.Image:
    scale = 160.0 / eat_pose.height
    nw = int(eat_pose.width * scale)
    nh = int(eat_pose.height * scale)
    base = eat_pose.resize((nw, nh), Image.Resampling.LANCZOS)
    head_x = get_head_center_x(base)

    frames = []
    for f in range(6):
        canvas = Image.new("RGBA", (FRAME_SIZE, FRAME_SIZE), (0, 0, 0, 0))
        draw = ImageDraw.Draw(canvas)

        dy = -2 if f in [1, 3, 5] else 0
        px = int(96 - head_x)
        py = 192 - nh - 10 + dy
        canvas.paste(base, (px, py), base)

        if f % 2 == 1:
            draw.ellipse([98, 70 + dy, 102, 74 + dy], fill=(255, 255, 255, 230))
            draw.ellipse([90, 72 + dy, 93, 75 + dy], fill=(255, 255, 255, 200))
        draw_sparkle(draw, 145, 60, size=6, color=(255, 220, 100, 220))

        frames.append(canvas)
    return create_sheet(frames)


def gen_jump_slash(jump_pose: Image.Image) -> Image.Image:
    scale = min(170.0 / jump_pose.width, 165.0 / jump_pose.height)
    nw = int(jump_pose.width * scale)
    nh = int(jump_pose.height * scale)
    base = jump_pose.resize((nw, nh), Image.Resampling.LANCZOS)

    frames = []
    offsets = [0, -10, -20, -24, -14, -4]
    for i, dy in enumerate(offsets):
        canvas = Image.new("RGBA", (FRAME_SIZE, FRAME_SIZE), (0, 0, 0, 0))
        draw = ImageDraw.Draw(canvas)

        px = (FRAME_SIZE - nw) // 2
        py = (FRAME_SIZE - nh) // 2 + dy
        canvas.paste(base, (px, py), base)

        # Wind & Water motion lines
        draw.line([40, 150 + dy, 65, 130 + dy], fill=(100, 210, 255, 200), width=2)
        draw.line([135, 150 + dy, 160, 130 + dy], fill=(100, 210, 255, 200), width=2)
        draw_sparkle(draw, 155, 45 + dy, size=7, color=(255, 255, 255, 230))

        frames.append(canvas)
    return create_sheet(frames)


def gen_sit_nezuko(sit_pose: Image.Image) -> Image.Image:
    scale = min(170.0 / sit_pose.width, 145.0 / sit_pose.height)
    nw = int(sit_pose.width * scale)
    nh = int(sit_pose.height * scale)
    base = sit_pose.resize((nw, nh), Image.Resampling.LANCZOS)

    frames = []
    for f in range(4):
        canvas = Image.new("RGBA", (FRAME_SIZE, FRAME_SIZE), (0, 0, 0, 0))
        draw = ImageDraw.Draw(canvas)

        dy = -1 if f in [1, 3] else 0
        px = (FRAME_SIZE - nw) // 2
        py = 192 - nh - 10 + dy
        canvas.paste(base, (px, py), base)
        draw_sparkle(draw, 50, 85, size=5, color=(255, 180, 200, 200))

        frames.append(canvas)
    return create_sheet(frames)


def gen_sleep(sit_pose: Image.Image) -> Image.Image:
    scale = min(170.0 / sit_pose.width, 145.0 / sit_pose.height)
    nw = int(sit_pose.width * scale)
    nh = int(sit_pose.height * scale)
    base = sit_pose.resize((nw, nh), Image.Resampling.LANCZOS)

    frames = []
    for f in range(4):
        canvas = Image.new("RGBA", (FRAME_SIZE, FRAME_SIZE), (0, 0, 0, 0))
        draw = ImageDraw.Draw(canvas)

        dy = -1 if f in [1, 2] else 0
        px = (FRAME_SIZE - nw) // 2
        py = 192 - nh - 10 + dy
        canvas.paste(base, (px, py), base)

        # Floating "Z z z"
        zx = 145 + f * 4
        zy = 60 - f * 8
        draw.line([zx, zy, zx + 7, zy], fill=(100, 200, 255, 220), width=2)
        draw.line([zx + 7, zy, zx, zy + 7], fill=(100, 200, 255, 220), width=2)
        draw.line([zx, zy + 7, zx + 7, zy + 7], fill=(100, 200, 255, 220), width=2)

        frames.append(canvas)
    return create_sheet(frames)


def gen_happy(standing: Image.Image) -> Image.Image:
    scale = 162.0 / standing.height
    nw = int(standing.width * scale)
    nh = int(standing.height * scale)
    base = standing.resize((nw, nh), Image.Resampling.LANCZOS)
    head_x = get_head_center_x(base)

    frames = []
    for f in range(4):
        canvas = Image.new("RGBA", (FRAME_SIZE, FRAME_SIZE), (0, 0, 0, 0))
        draw = ImageDraw.Draw(canvas)

        dy = -4 if f in [1, 3] else 0
        px = int(96 - head_x)
        py = 192 - nh - 10 + dy
        canvas.paste(base, (px, py), base)

        draw_sparkle(draw, 50, 60, size=7, color=(255, 230, 80, 240))
        draw_sparkle(draw, 142, 65, size=6, color=(255, 230, 80, 240))
        frames.append(canvas)
    return create_sheet(frames)


def gen_music(standing: Image.Image) -> Image.Image:
    scale = 162.0 / standing.height
    nw = int(standing.width * scale)
    nh = int(standing.height * scale)
    base = standing.resize((nw, nh), Image.Resampling.LANCZOS)
    head_x = get_head_center_x(base)

    frames = []
    angles = [0, -3, 0, 3]
    for i, ang in enumerate(angles):
        canvas = Image.new("RGBA", (FRAME_SIZE, FRAME_SIZE), (0, 0, 0, 0))
        draw = ImageDraw.Draw(canvas)

        rotated = base.rotate(ang, resample=Image.BICUBIC, expand=True) if ang != 0 else base
        px = int(96 - (rotated.width / 2))
        py = 192 - rotated.height - 10 + (-2 if i % 2 == 1 else 0)
        canvas.paste(rotated, (px, py), rotated)

        draw_music_note(draw, 45, 55 - i * 3, color=(0, 220, 255, 240))
        draw_music_note(draw, 140, 50 + i * 2, color=(255, 180, 0, 240))

        frames.append(canvas)
    return create_sheet(frames)


def gen_drag(standing: Image.Image) -> Image.Image:
    scale = 155.0 / standing.height
    nw = int(standing.width * scale)
    nh = int(standing.height * scale)
    base = standing.resize((nw, nh), Image.Resampling.LANCZOS)

    frames = []
    for f in range(4):
        canvas = Image.new("RGBA", (FRAME_SIZE, FRAME_SIZE), (0, 0, 0, 0))
        draw = ImageDraw.Draw(canvas)

        rot = base.rotate(8 if f % 2 == 0 else -8, resample=Image.BICUBIC, expand=True)
        px = (FRAME_SIZE - rot.width) // 2
        py = (FRAME_SIZE - rot.height) // 2 - 12
        canvas.paste(rot, (px, py), rot)

        draw.ellipse([90, 18, 102, 30], fill=(255, 255, 255, 180), outline=(0, 160, 255, 220), width=2)
        frames.append(canvas)
    return create_sheet(frames)


def gen_fall(jump_pose: Image.Image) -> Image.Image:
    scale = min(160.0 / jump_pose.width, 155.0 / jump_pose.height)
    nw = int(jump_pose.width * scale)
    nh = int(jump_pose.height * scale)
    base = jump_pose.resize((nw, nh), Image.Resampling.LANCZOS)

    frames = []
    for f in range(4):
        canvas = Image.new("RGBA", (FRAME_SIZE, FRAME_SIZE), (0, 0, 0, 0))
        draw = ImageDraw.Draw(canvas)

        rot = base.rotate(5 if f % 2 == 0 else -5, resample=Image.BICUBIC, expand=True)
        px = (FRAME_SIZE - rot.width) // 2
        py = (FRAME_SIZE - rot.height) // 2
        canvas.paste(rot, (px, py), rot)

        draw.line([40, 30, 40, 160], fill=(200, 230, 255, 180), width=2)
        draw.line([150, 30, 150, 160], fill=(200, 230, 255, 180), width=2)

        frames.append(canvas)
    return create_sheet(frames)


def gen_land(standing: Image.Image) -> Image.Image:
    scale = 162.0 / standing.height
    nw = int(standing.width * scale)
    nh = int(standing.height * scale)
    base = standing.resize((nw, nh), Image.Resampling.LANCZOS)
    head_x = get_head_center_x(base)

    frames = []
    for f in range(4):
        canvas = Image.new("RGBA", (FRAME_SIZE, FRAME_SIZE), (0, 0, 0, 0))
        draw = ImageDraw.Draw(canvas)

        squash_h = int(base.height * (0.85 if f == 0 else 0.95 if f == 1 else 1.0))
        squashed = base.resize((base.width, squash_h), Image.Resampling.LANCZOS)
        px = int(96 - head_x)
        py = 192 - squash_h - 10
        canvas.paste(squashed, (px, py), squashed)

        if f <= 1:
            draw.ellipse([40, 170, 70, 180], fill=(200, 220, 240, 180))
            draw.ellipse([120, 170, 150, 180], fill=(200, 220, 240, 180))

        frames.append(canvas)
    return create_sheet(frames)


def gen_idea(standing: Image.Image) -> Image.Image:
    scale = 162.0 / standing.height
    nw = int(standing.width * scale)
    nh = int(standing.height * scale)
    base = standing.resize((nw, nh), Image.Resampling.LANCZOS)
    head_x = get_head_center_x(base)

    frames = []
    for f in range(4):
        canvas = Image.new("RGBA", (FRAME_SIZE, FRAME_SIZE), (0, 0, 0, 0))
        draw = ImageDraw.Draw(canvas)

        px = int(96 - head_x)
        py = 192 - nh - 10
        canvas.paste(base, (px, py), base)

        bx, by = 96, 22
        draw.ellipse([bx - 8, by - 8, bx + 8, by + 8], fill=(255, 230, 80, 240), outline=(255, 180, 0, 255), width=2)
        draw.line([bx - 4, by + 10, bx + 4, by + 10], fill=(180, 180, 180, 240), width=2)

        for ang in [0, 45, 90, 135, 180, 225, 270, 315]:
            rad = math.radians(ang)
            lx = bx + int(14 * math.cos(rad))
            ly = by + int(14 * math.sin(rad))
            draw.line([bx, by, lx, ly], fill=(255, 240, 120, 180), width=1)

        frames.append(canvas)
    return create_sheet(frames)


def gen_cry(standing: Image.Image) -> Image.Image:
    scale = 162.0 / standing.height
    nw = int(standing.width * scale)
    nh = int(standing.height * scale)
    base = standing.resize((nw, nh), Image.Resampling.LANCZOS)
    head_x = get_head_center_x(base)

    frames = []
    for f in range(4):
        canvas = Image.new("RGBA", (FRAME_SIZE, FRAME_SIZE), (0, 0, 0, 0))
        draw = ImageDraw.Draw(canvas)

        px = int(96 - head_x)
        py = 192 - nh - 10 + (1 if f in [1, 3] else 0)
        canvas.paste(base, (px, py), base)

        draw.line([85, 60, 82, 75 + f * 3], fill=(80, 200, 255, 240), width=2)
        draw.line([107, 60, 110, 75 + f * 3], fill=(80, 200, 255, 240), width=2)

        frames.append(canvas)
    return create_sheet(frames)


def gen_shrug(standing: Image.Image) -> Image.Image:
    scale = 162.0 / standing.height
    nw = int(standing.width * scale)
    nh = int(standing.height * scale)
    base = standing.resize((nw, nh), Image.Resampling.LANCZOS)
    head_x = get_head_center_x(base)

    frames = []
    for f in range(4):
        canvas = Image.new("RGBA", (FRAME_SIZE, FRAME_SIZE), (0, 0, 0, 0))
        draw = ImageDraw.Draw(canvas)

        dy = -2 if f in [1, 2] else 0
        px = int(96 - head_x)
        py = 192 - nh - 10 + dy
        canvas.paste(base, (px, py), base)

        draw.ellipse([65, 50, 70, 58], fill=(100, 210, 255, 240))

        frames.append(canvas)
    return create_sheet(frames)


def flip_sheet(sheet: Image.Image) -> Image.Image:
    frame_h = sheet.height
    n_frames = max(1, sheet.width // frame_h)
    flipped = Image.new("RGBA", sheet.size, (0, 0, 0, 0))
    for i in range(n_frames):
        crop = sheet.crop((i * frame_h, 0, (i + 1) * frame_h, frame_h))
        crop_f = crop.transpose(Image.FLIP_LEFT_RIGHT)
        flipped.paste(crop_f, (i * frame_h, 0))
    return flipped


def generate_all():
    print("Loading clean Tanjiro cutouts...")
    standing = load_source("standing")
    water_dragon = load_source("water_dragon")
    eat_onigiri = load_source("eat_onigiri")
    jump_slash = load_source("jump_slash")
    sit_nezuko = load_source("sit_nezuko")

    walk_poses = [load_source(f"walk_{i}") for i in range(6)]

    print("Generating all 20 clean Tanjiro sprite sheets...")

    # 1. Idle
    idle = gen_idle(standing)
    idle.save(OUT_DIR / "idle.png")
    flip_sheet(idle).save(OUT_DIR / "idle_flip.png")

    # 2. Walk Right & Left
    walk_r = gen_walk(walk_poses)
    walk_r.save(OUT_DIR / "walk_right.png")
    flip_sheet(walk_r).save(OUT_DIR / "walk_left.png")

    # 3. Actions
    gen_water_dragon(water_dragon).save(OUT_DIR / "roar.png")
    gen_eat_onigiri(eat_onigiri).save(OUT_DIR / "work.png")
    gen_jump_slash(jump_slash).save(OUT_DIR / "jump.png")
    gen_sit_nezuko(sit_nezuko).save(OUT_DIR / "sit.png")
    gen_sleep(sit_nezuko).save(OUT_DIR / "sleep.png")
    gen_idle(standing).save(OUT_DIR / "wake.png")
    gen_idle(standing).save(OUT_DIR / "blink.png")
    gen_happy(standing).save(OUT_DIR / "happy.png")
    gen_idea(standing).save(OUT_DIR / "idea.png")
    gen_cry(standing).save(OUT_DIR / "cry.png")
    gen_cry(standing).save(OUT_DIR / "sad.png")
    gen_shrug(standing).save(OUT_DIR / "shrug.png")
    gen_drag(standing).save(OUT_DIR / "drag.png")
    gen_fall(jump_slash).save(OUT_DIR / "fall.png")
    gen_land(standing).save(OUT_DIR / "land.png")
    gen_music(standing).save(OUT_DIR / "music.png")

    print("Successfully generated all 20 Tanjiro sprite sheets in assets/sprites/tanjiro/!")


if __name__ == "__main__":
    generate_all()
