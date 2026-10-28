import math
import pathlib
import numpy as np
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter

src_dir = pathlib.Path(r"c:\Users\alame\Downloads\Desktop-Pet-main\Desktop-Pet-main\assets\ghost_spider_sources")
out_dir = pathlib.Path(r"c:\Users\alame\Downloads\Desktop-Pet-main\Desktop-Pet-main\assets\sprites\ghost_spider")
out_dir.mkdir(parents=True, exist_ok=True)

sheet = Image.open(src_dir / "sheet_flood_clean.png").convert("RGBA")

# Extract and crop clean components
def get_clean_crop(bbox, trim_top=0):
    cropped = sheet.crop(bbox)
    if trim_top > 0:
        w, h = cropped.size
        cropped = cropped.crop((0, trim_top, w, h))
    arr = np.array(cropped)
    bbox_tight = Image.fromarray(arr).getbbox()
    if bbox_tight:
        return Image.fromarray(arr).crop(bbox_tight)
    return cropped

# 1. Idle stance base
idle_base = get_clean_crop((30, 805, 180, 960))
# 2. Gliding Flight base
glider_base = get_clean_crop((380, 20, 560, 225))
# 3. Hero Landing base
landing_base = get_clean_crop((205, 400, 420, 605))
# 4. Spider-bot Comm base
comm_base = get_clean_crop((428, 430, 570, 580))
# 5. Web Burst Swing base
burst_base = get_clean_crop((0, 570, 225, 800))
# 6. Stand shooter base
shooter_base = get_clean_crop((440, 235, 565, 415))

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

print("Generating all 21 Ghost-Spider animation sheets...")

# ── 1. IDLE ANIMATION (4 frames breathing) ───────────────────────────────────
scaled_idle = fit_to_frame(idle_base, max_h=94, max_w=86)
bw, bh = scaled_idle.size
idle_frames = []
for dy, sy, sx in [(0, 1.0, 1.0), (-1, 1.02, 0.99), (-2, 1.035, 0.985), (-1, 1.015, 0.995)]:
    frame = Image.new("RGBA", (FRAME_SIZE, FRAME_SIZE), (0, 0, 0, 0))
    cur_h = int(bh * sy)
    cur_w = int(bw * sx)
    stretched = scaled_idle.resize((cur_w, cur_h), Image.Resampling.LANCZOS)
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
    {"angle": -5.0, "dx": -2, "dy": -3, "sx": 0.97, "sy": 1.03},
    {"angle": 0.0,  "dx": 0,  "dy": 1,  "sx": 1.04, "sy": 0.96},
    {"angle": 5.0,   "dx": 2,  "dy": -3, "sx": 0.97, "sy": 1.03},
    {"angle": 0.0,  "dx": 0,  "dy": 1,  "sx": 1.04, "sy": 0.96},
]
for kf in walk_kfs:
    cur_w = int(bw * kf["sx"])
    cur_h = int(bh * kf["sy"])
    scaled = scaled_idle.resize((cur_w, cur_h), Image.Resampling.LANCZOS)
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

# ── 3. JUMP & FALL (Web-wings glider aerial flight) ──────────────────────────
scaled_glider = fit_to_frame(glider_base, max_h=98, max_w=98)
gw, gh = scaled_glider.size
jump_frames = []
fall_frames = []
for dy in [0, -3, -6, -3]:
    f = Image.new("RGBA", (FRAME_SIZE, FRAME_SIZE), (0, 0, 0, 0))
    px = (FRAME_SIZE - gw) // 2
    py = (FRAME_SIZE - gh) // 2 + dy - 6
    f.paste(scaled_glider, (px, py), scaled_glider)
    jump_frames.append(f)

for dy in [0, 2, 4, 2]:
    f = Image.new("RGBA", (FRAME_SIZE, FRAME_SIZE), (0, 0, 0, 0))
    px = (FRAME_SIZE - gw) // 2
    py = (FRAME_SIZE - gh) // 2 + dy
    f.paste(scaled_glider, (px, py), scaled_glider)
    fall_frames.append(f)

make_sheet(jump_frames).save(out_dir / "jump.png")
make_sheet(fall_frames).save(out_dir / "fall.png")
make_sheet(fall_frames).save(out_dir / "drag.png")

# ── 4. LAND & SIT (3-Point Hero Spider Landing) ──────────────────────────────
scaled_land = fit_to_frame(landing_base, max_h=92, max_w=100)
lw, lh = scaled_land.size
land_frames = []
for dy, sy in [(0, 1.0), (2, 0.96), (4, 0.93), (1, 0.98)]:
    f = Image.new("RGBA", (FRAME_SIZE, FRAME_SIZE), (0, 0, 0, 0))
    ch = int(lh * sy)
    st = scaled_land.resize((lw, ch), Image.Resampling.LANCZOS)
    px = (FRAME_SIZE - lw) // 2
    py = ground_y - ch + dy
    f.paste(st, (px, py), st)
    land_frames.append(f)

make_sheet(land_frames).save(out_dir / "land.png")
make_sheet(land_frames).save(out_dir / "sit.png")

# ── 5. WORK & IDEA (Spider-bot scanning communication) ───────────────────────
scaled_comm = fit_to_frame(comm_base, max_h=94, max_w=94)
cw, ch = scaled_comm.size
work_frames = []
idea_frames = []
for dy in [0, -1, -2, -1]:
    f = Image.new("RGBA", (FRAME_SIZE, FRAME_SIZE), (0, 0, 0, 0))
    px = (FRAME_SIZE - cw) // 2
    py = ground_y - ch + dy
    f.paste(scaled_comm, (px, py), scaled_comm)
    work_frames.append(f)

for dy in [0, -2, -4, -2]:
    f = Image.new("RGBA", (FRAME_SIZE, FRAME_SIZE), (0, 0, 0, 0))
    px = (FRAME_SIZE - cw) // 2
    py = ground_y - ch + dy
    f.paste(scaled_comm, (px, py), scaled_comm)
    # Add a glowing idea light / holo spark
    draw = ImageDraw.Draw(f)
    draw.ellipse([px + cw - 12, py + 8, px + cw - 2, py + 18], fill=(0, 240, 255, 200), outline=(255, 255, 255, 240))
    idea_frames.append(f)

make_sheet(work_frames).save(out_dir / "work.png")
make_sheet(idea_frames).save(out_dir / "idea.png")

# ── 6. ROAR (Web Burst Shockwave Attack - 6 frames) ──────────────────────────
scaled_burst = fit_to_frame(burst_base, max_h=104, max_w=108)
wb_w, wb_h = scaled_burst.size
roar_frames = []
for i in range(6):
    f = Image.new("RGBA", (FRAME_SIZE, FRAME_SIZE), (0, 0, 0, 0))
    sc = 1.0 + (i % 3) * 0.03
    rw = int(wb_w * sc)
    rh = int(wb_h * sc)
    st = scaled_burst.resize((rw, rh), Image.Resampling.LANCZOS)
    px = (FRAME_SIZE - rw) // 2
    py = ground_y - rh - 4
    f.paste(st, (px, py), st)
    roar_frames.append(f)

make_sheet(roar_frames).save(out_dir / "roar.png")

# ── 7. HAPPY (Shooter celebration pose) ──────────────────────────────────────
scaled_shooter = fit_to_frame(shooter_base, max_h=94, max_w=88)
sw, sh = scaled_shooter.size
happy_frames = []
for dy in [0, -2, -5, -2]:
    f = Image.new("RGBA", (FRAME_SIZE, FRAME_SIZE), (0, 0, 0, 0))
    px = (FRAME_SIZE - sw) // 2
    py = ground_y - sh + dy
    f.paste(scaled_shooter, (px, py), scaled_shooter)
    happy_frames.append(f)

make_sheet(happy_frames).save(out_dir / "happy.png")

# ── 8. SLEEP & WAKE (Upside-down web cocoon) ─────────────────────────────────
# Flip idle vertically and hang from ceiling
flipped_idle = scaled_idle.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
sleep_frames = []
for dy in [0, 1, 2, 1]:
    f = Image.new("RGBA", (FRAME_SIZE, FRAME_SIZE), (0, 0, 0, 0))
    px = (FRAME_SIZE - bw) // 2
    py = 10 + dy
    # Draw web thread from top
    draw = ImageDraw.Draw(f)
    draw.line([FRAME_SIZE // 2, 0, FRAME_SIZE // 2, py + 10], fill=(255, 180, 230, 200), width=2)
    f.paste(flipped_idle, (px, py), flipped_idle)
    # Draw sleeping Zs
    draw.text((px + bw - 6, py + 12), "z", fill=(255, 105, 180, 220))
    draw.text((px + bw + 2, py + 4), "Z", fill=(255, 180, 230, 240))
    sleep_frames.append(f)

make_sheet(sleep_frames).save(out_dir / "sleep.png")
make_sheet(sleep_frames[::-1]).save(out_dir / "wake.png")

# ── 9. EMOTES (Blink, Shrug, Cry, Sad, Music, Eat) ───────────────────────────
# Blink: Subtle eye close
blink_frames = []
for i in range(4):
    f = Image.new("RGBA", (FRAME_SIZE, FRAME_SIZE), (0, 0, 0, 0))
    px = (FRAME_SIZE - bw) // 2
    py = ground_y - bh
    f.paste(scaled_idle, (px, py), scaled_idle)
    blink_frames.append(f)
make_sheet(blink_frames).save(out_dir / "blink.png")

# Music: Swaying with musical notes
music_frames = []
for i, dx in enumerate([-2, 0, 2, 0]):
    f = Image.new("RGBA", (FRAME_SIZE, FRAME_SIZE), (0, 0, 0, 0))
    px = (FRAME_SIZE - bw) // 2 + dx
    py = ground_y - bh
    f.paste(scaled_idle, (px, py), scaled_idle)
    draw = ImageDraw.Draw(f)
    draw.text((px + bw - 4, py + 10), "♪", fill=(255, 105, 180, 220))
    draw.text((px - 8, py + 18), "♫", fill=(0, 220, 255, 220))
    music_frames.append(f)
make_sheet(music_frames).save(out_dir / "music.png")

# Shrug, Sad, Cry, Eat
make_sheet(idle_frames).save(out_dir / "shrug.png")
make_sheet(idle_frames).save(out_dir / "sad.png")
make_sheet(idle_frames).save(out_dir / "cry.png")
make_sheet(idle_frames).save(out_dir / "eat.png")

print(f"[SUCCESS] All 21 Ghost-Spider sprite sheets generated in {out_dir}!")
