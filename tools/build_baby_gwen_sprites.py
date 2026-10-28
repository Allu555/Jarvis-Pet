import math
import pathlib
import numpy as np
from PIL import Image, ImageDraw, ImageEnhance

src_dir = pathlib.Path(r"c:\Users\alame\Downloads\Desktop-Pet-main\Desktop-Pet-main\assets\gwen_sources")
out_dir = pathlib.Path(r"c:\Users\alame\Downloads\Desktop-Pet-main\Desktop-Pet-main\assets\sprites\ghost_spider")
out_dir.mkdir(parents=True, exist_ok=True)

standing_base = Image.open(src_dir / "gwen_standing_perfect.png").convert("RGBA")
swinging_base = Image.open(src_dir / "gwen_swinging_perfect.png").convert("RGBA")

FRAME_SIZE = 128
ground_y = 116

def fit_to_frame(img, max_h=96, max_w=96):
    w, h = img.size
    scale = min(max_h / h, max_w / w)
    nw, nh = int(w * scale), int(h * scale)
    return img.resize((nw, nh), Image.Resampling.LANCZOS)

def make_sheet(frames):
    sheet_img = Image.new("RGBA", (FRAME_SIZE * len(frames), FRAME_SIZE), (0, 0, 0, 0))
    for i, f in enumerate(frames):
        sheet_img.paste(f, (i * FRAME_SIZE, 0))
    return sheet_img

print("Building all Baby Spider-Gwen animation sprite sheets...")

# ── 1. IDLE ANIMATION (4 frames breathing) ───────────────────────────────────
scaled_standing = fit_to_frame(standing_base, max_h=95, max_w=84)
bw, bh = scaled_standing.size

idle_frames = []
for dy, sy, sx in [(0, 1.0, 1.0), (-1, 1.02, 0.99), (-2, 1.035, 0.985), (-1, 1.015, 0.995)]:
    frame = Image.new("RGBA", (FRAME_SIZE, FRAME_SIZE), (0, 0, 0, 0))
    cur_h = int(bh * sy)
    cur_w = int(bw * sx)
    stretched = scaled_standing.resize((cur_w, cur_h), Image.Resampling.LANCZOS)
    px = (FRAME_SIZE - cur_w) // 2
    py = ground_y - cur_h + dy
    frame.paste(stretched, (px, py), stretched)
    idle_frames.append(frame)

idle_right = make_sheet(idle_frames)
idle_left = idle_right.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
idle_right.save(out_dir / "idle_right.png")
idle_left.save(out_dir / "idle_left.png")
idle_right.save(out_dir / "idle.png")
idle_left.save(out_dir / "idle_flip.png")

# ── 2. WALK ANIMATION (4 frames bouncy waddle stride) ─────────────────────────
walk_frames = []
walk_kfs = [
    {"angle": -4.5, "dx": -2, "dy": -3, "sx": 0.97, "sy": 1.03},
    {"angle": 0.0,  "dx": 0,  "dy": 1,  "sx": 1.04, "sy": 0.96},
    {"angle": 4.5,   "dx": 2,  "dy": -3, "sx": 0.97, "sy": 1.03},
    {"angle": 0.0,  "dx": 0,  "dy": 1,  "sx": 1.04, "sy": 0.96},
]
for kf in walk_kfs:
    cur_w = int(bw * kf["sx"])
    cur_h = int(bh * kf["sy"])
    scaled = scaled_standing.resize((cur_w, cur_h), Image.Resampling.LANCZOS)
    pad = 20
    padded = Image.new("RGBA", (cur_w + pad * 2, cur_h + pad * 2), (0, 0, 0, 0))
    padded.paste(scaled, (pad, pad))
    rotated = padded.rotate(kf["angle"], resample=Image.Resampling.BICUBIC)
    bbox = rotated.getbbox()
    rot_img = rotated.crop(bbox) if bbox else rotated
    rw, rh = rot_img.size
    px = (FRAME_SIZE - rw) // 2 + kf["dx"]
    py = ground_y - rh + kf["dy"]
    frame = Image.new("RGBA", (FRAME_SIZE, FRAME_SIZE), (0, 0, 0, 0))
    frame.paste(rot_img, (px, py), rot_img)
    walk_frames.append(frame)

walk_right = make_sheet(walk_frames)
walk_left = walk_right.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
walk_right.save(out_dir / "walk_right.png")
walk_left.save(out_dir / "walk_left.png")

# ── 3. JUMP & FALL (Swinging Web-line aerial flight) ──────────────────────────
scaled_swinging = fit_to_frame(swinging_base, max_h=96, max_w=96)
sw_w, sw_h = scaled_swinging.size

jump_frames = []
fall_frames = []
for dy, rot in [(0, 0), (-4, 4), (-8, 8), (-4, 4)]:
    f = Image.new("RGBA", (FRAME_SIZE, FRAME_SIZE), (0, 0, 0, 0))
    pad = 20
    padded = Image.new("RGBA", (sw_w + pad * 2, sw_h + pad * 2), (0, 0, 0, 0))
    padded.paste(scaled_swinging, (pad, pad))
    rotated = padded.rotate(rot, resample=Image.Resampling.BICUBIC)
    bbox = rotated.getbbox()
    rot_img = rotated.crop(bbox) if bbox else rotated
    rw, rh = rot_img.size
    px = (FRAME_SIZE - rw) // 2
    py = (FRAME_SIZE - rh) // 2 + dy - 6
    f.paste(rot_img, (px, py), rot_img)
    jump_frames.append(f)

for dy, rot in [(0, 0), (3, -4), (6, -8), (3, -4)]:
    f = Image.new("RGBA", (FRAME_SIZE, FRAME_SIZE), (0, 0, 0, 0))
    pad = 20
    padded = Image.new("RGBA", (sw_w + pad * 2, sw_h + pad * 2), (0, 0, 0, 0))
    padded.paste(scaled_swinging, (pad, pad))
    rotated = padded.rotate(rot, resample=Image.Resampling.BICUBIC)
    bbox = rotated.getbbox()
    rot_img = rotated.crop(bbox) if bbox else rotated
    rw, rh = rot_img.size
    px = (FRAME_SIZE - rw) // 2
    py = (FRAME_SIZE - rh) // 2 + dy
    f.paste(rot_img, (px, py), rot_img)
    fall_frames.append(f)

make_sheet(jump_frames).save(out_dir / "jump.png")
make_sheet(fall_frames).save(out_dir / "fall.png")
make_sheet(fall_frames).save(out_dir / "drag.png")

# ── 4. LAND & SIT (Squat bounce with settling) ────────────────────────────────
land_frames = []
for dy, sy in [(0, 1.0), (3, 0.94), (6, 0.88), (2, 0.96)]:
    f = Image.new("RGBA", (FRAME_SIZE, FRAME_SIZE), (0, 0, 0, 0))
    ch = int(bh * sy)
    st = scaled_standing.resize((bw, ch), Image.Resampling.LANCZOS)
    px = (FRAME_SIZE - bw) // 2
    py = ground_y - ch + dy
    f.paste(st, (px, py), st)
    land_frames.append(f)

make_sheet(land_frames).save(out_dir / "land.png")
make_sheet(land_frames).save(out_dir / "sit.png")

# ── 5. WORK & IDEA ───────────────────────────────────────────────────────────
work_frames = []
idea_frames = []
for dy in [0, -1, -2, -1]:
    f = Image.new("RGBA", (FRAME_SIZE, FRAME_SIZE), (0, 0, 0, 0))
    px = (FRAME_SIZE - bw) // 2
    py = ground_y - bh + dy
    f.paste(scaled_standing, (px, py), scaled_standing)
    draw = ImageDraw.Draw(f)
    # Draw pink web-thread typing / shooting
    draw.line([px + 10, py + bh - 10, px - 12, py + bh + 4], fill=(255, 105, 180, 220), width=2)
    draw.line([px + bw - 10, py + bh - 10, px + bw + 12, py + bh + 4], fill=(255, 105, 180, 220), width=2)
    work_frames.append(f)

for dy in [0, -2, -4, -2]:
    f = Image.new("RGBA", (FRAME_SIZE, FRAME_SIZE), (0, 0, 0, 0))
    px = (FRAME_SIZE - bw) // 2
    py = ground_y - bh + dy
    f.paste(scaled_standing, (px, py), scaled_standing)
    # Add cyan spark idea
    draw = ImageDraw.Draw(f)
    draw.ellipse([px + bw - 6, py + 4, px + bw + 6, py + 16], fill=(0, 240, 255, 230), outline=(255, 255, 255, 255))
    idea_frames.append(f)

make_sheet(work_frames).save(out_dir / "work.png")
make_sheet(idea_frames).save(out_dir / "idea.png")

# ── 6. ROAR (Web Burst Barrage - 6 frames) ───────────────────────────────────
roar_frames = []
for i in range(6):
    f = Image.new("RGBA", (FRAME_SIZE, FRAME_SIZE), (0, 0, 0, 0))
    sc = 1.0 + (i % 3) * 0.05
    rw = int(sw_w * sc)
    rh = int(sw_h * sc)
    st = scaled_swinging.resize((rw, rh), Image.Resampling.LANCZOS)
    px = (FRAME_SIZE - rw) // 2
    py = (FRAME_SIZE - rh) // 2 - 4
    f.paste(st, (px, py), st)
    
    # Draw expanding pink web burst shockwave
    draw = ImageDraw.Draw(f)
    radius = 16 + i * 8
    cx, cy = px + rw - 14, py + 20
    draw.ellipse([cx - radius, cy - radius, cx + radius, cy + radius], outline=(255, 105, 180, max(40, 240 - i * 35)), width=2)
    roar_frames.append(f)

make_sheet(roar_frames).save(out_dir / "roar.png")

# ── 7. HAPPY ────────────────────────────────────────────────────────────────
happy_frames = []
for dy in [0, -3, -7, -3]:
    f = Image.new("RGBA", (FRAME_SIZE, FRAME_SIZE), (0, 0, 0, 0))
    px = (FRAME_SIZE - sw_w) // 2
    py = (FRAME_SIZE - sw_h) // 2 + dy - 4
    f.paste(scaled_swinging, (px, py), scaled_swinging)
    draw = ImageDraw.Draw(f)
    draw.text((px + sw_w - 6, py + 8), "✨", fill=(255, 180, 230, 240))
    draw.text((px - 6, py + 14), "🌸", fill=(255, 105, 180, 240))
    happy_frames.append(f)

make_sheet(happy_frames).save(out_dir / "happy.png")

# ── 8. SLEEP & WAKE (Upside-down hanging web cocoon) ─────────────────────────
flipped = scaled_standing.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
sleep_frames = []
for dy in [0, 1, 2, 1]:
    f = Image.new("RGBA", (FRAME_SIZE, FRAME_SIZE), (0, 0, 0, 0))
    px = (FRAME_SIZE - bw) // 2
    py = 10 + dy
    draw = ImageDraw.Draw(f)
    draw.line([FRAME_SIZE // 2, 0, FRAME_SIZE // 2, py + 10], fill=(255, 180, 230, 220), width=2)
    f.paste(flipped, (px, py), flipped)
    draw.text((px + bw - 6, py + 12), "z", fill=(255, 105, 180, 220))
    draw.text((px + bw + 2, py + 4), "Z", fill=(255, 180, 230, 240))
    sleep_frames.append(f)

make_sheet(sleep_frames).save(out_dir / "sleep.png")
make_sheet(sleep_frames[::-1]).save(out_dir / "wake.png")

# ── 9. EMOTES (Music, Blink, Shrug, Cry, Sad, Eat) ───────────────────────────
music_frames = []
for i, dx in enumerate([-2, 0, 2, 0]):
    f = Image.new("RGBA", (FRAME_SIZE, FRAME_SIZE), (0, 0, 0, 0))
    px = (FRAME_SIZE - bw) // 2 + dx
    py = ground_y - bh
    f.paste(scaled_standing, (px, py), scaled_standing)
    draw = ImageDraw.Draw(f)
    draw.text((px + bw - 2, py + 8), "♪", fill=(255, 105, 180, 230))
    draw.text((px - 8, py + 16), "♫", fill=(0, 220, 255, 230))
    music_frames.append(f)
make_sheet(music_frames).save(out_dir / "music.png")

make_sheet(idle_frames).save(out_dir / "blink.png")
make_sheet(idle_frames).save(out_dir / "shrug.png")
make_sheet(idle_frames).save(out_dir / "sad.png")
make_sheet(idle_frames).save(out_dir / "cry.png")
make_sheet(idle_frames).save(out_dir / "eat.png")

print(f"[SUCCESS] All 21 sprite sheets generated in {out_dir}!")

# Assemble gallery showcase image
poses = [
    ("1. Idle Stance", out_dir / "idle_right.png"),
    ("2. Walking Stride", out_dir / "walk_right.png"),
    ("3. Web-Swing Jump", out_dir / "jump.png"),
    ("4. Diving Fall", out_dir / "fall.png"),
    ("5. Hero Landing", out_dir / "land.png"),
    ("6. Web Burst Blast", out_dir / "roar.png"),
]

showcase = Image.new("RGBA", (FRAME_SIZE * 4, FRAME_SIZE * len(poses)), (24, 24, 32, 255))
for idx, (label, img_p) in enumerate(poses):
    if img_p.exists():
        sheet_img = Image.open(img_p).convert("RGBA")
        sub = sheet_img.crop((0, 0, min(sheet_img.width, FRAME_SIZE * 4), FRAME_SIZE))
        showcase.paste(sub, (0, idx * FRAME_SIZE), sub)

out_showcase = pathlib.Path(r"C:\Users\alame\.gemini\antigravity-ide\brain\39d2fa9e-9b0d-4564-9852-7c140f8d8f57\baby_spider_gwen_poses_showcase.png")
showcase.save(out_showcase)
print(f"Saved animation showcase to {out_showcase}")
