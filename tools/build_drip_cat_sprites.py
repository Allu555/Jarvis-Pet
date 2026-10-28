import pathlib
import numpy as np
from PIL import Image, ImageDraw
from collections import deque

src_path = r"C:\Users\alame\.gemini\antigravity-ide\brain\39d2fa9e-9b0d-4564-9852-7c140f8d8f57\.user_uploaded\media_1788675494202.png"
out_dir = pathlib.Path(r"c:\Users\alame\Downloads\Desktop-Pet-main\Desktop-Pet-main\assets\sprites\drip_cat")
out_dir.mkdir(parents=True, exist_ok=True)

img = Image.open(src_path).convert("RGBA")
w, h = img.size
print(f"Sheet dimensions: {w}x{h}")

arr = np.array(img)
rgb = arr[:, :, :3].astype(np.int32)

# Flood fill from image boundary where background is pure/near white
is_white_bg = (rgb[:, :, 0] > 235) & (rgb[:, :, 1] > 235) & (rgb[:, :, 2] > 235)
visited = np.zeros((h, w), dtype=bool)
bg_mask = np.zeros((h, w), dtype=bool)
queue = deque()

for x in range(w):
    if is_white_bg[0, x]:
        queue.append((0, x))
        visited[0, x] = True
    if is_white_bg[h-1, x]:
        queue.append((h-1, x))
        visited[h-1, x] = True

for y in range(h):
    if is_white_bg[y, 0]:
        queue.append((y, 0))
        visited[y, 0] = True
    if is_white_bg[y, w-1]:
        queue.append((y, w-1))
        visited[y, w-1] = True

while queue:
    cy, cx = queue.popleft()
    bg_mask[cy, cx] = True
    for dy, dx in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
        ny, nx = cy + dy, cx + dx
        if 0 <= ny < h and 0 <= nx < w:
            if not visited[ny, nx] and is_white_bg[ny, nx]:
                visited[ny, nx] = True
                queue.append((ny, nx))

arr[bg_mask, 3] = 0
clean_sheet = Image.fromarray(arr)

# 1. IDLE (top left)
idle_crop = clean_sheet.crop((0, int(0.06 * h), int(0.21 * w), int(0.50 * h)))
idle_bbox = idle_crop.getbbox()
if idle_bbox: idle_crop = idle_crop.crop(idle_bbox)

# 2. WALKING frames 1, 2, 3, 4 (strictly separated bounding boxes)
walk_boxes = [
    (210, 110, 395, 340),
    (405, 110, 585, 340),
    (590, 110, 780, 340),
    (785, 110, 995, 340),
]
walk_crops = []
for box in walk_boxes:
    wc = clean_sheet.crop(box)
    bb = wc.getbbox()
    if bb: wc = wc.crop(bb)
    walk_crops.append(wc)

# 3. WORKING (bottom left)
work_crop = clean_sheet.crop((0, int(0.50 * h), int(0.51 * w), int(0.96 * h)))
work_bbox = work_crop.getbbox()
if work_bbox: work_crop = work_crop.crop(work_bbox)

# 4. SLEEPING (bottom right)
sleep_crop = clean_sheet.crop((int(0.52 * w), int(0.48 * h), w, int(0.96 * h)))
sleep_bbox = sleep_crop.getbbox()
if sleep_bbox: sleep_crop = sleep_crop.crop(sleep_bbox)

print(f"Extracted: Idle={idle_crop.size}, Walk={[wc.size for wc in walk_crops]}, Work={work_crop.size}, Sleep={sleep_crop.size}")

FRAME_SIZE = 128
ground_y = 116

def fit_to_frame(img, max_h=92, max_w=108):
    cw, ch = img.size
    scale = min(max_h / ch, max_w / cw)
    nw, nh = int(cw * scale), int(ch * scale)
    return img.resize((nw, nh), Image.Resampling.LANCZOS)

def make_sheet(frames):
    sheet_img = Image.new("RGBA", (FRAME_SIZE * len(frames), FRAME_SIZE), (0, 0, 0, 0))
    for i, f in enumerate(frames):
        sheet_img.paste(f, (i * FRAME_SIZE, 0))
    return sheet_img

# ── 1. IDLE ANIMATION (4 frames breathing) ───────────────────────────────────
scaled_idle = fit_to_frame(idle_crop, max_h=96, max_w=96)
iw, ih = scaled_idle.size

idle_frames = []
for dy, sy, sx in [(0, 1.0, 1.0), (-1, 1.02, 0.99), (-2, 1.035, 0.985), (-1, 1.015, 0.995)]:
    f = Image.new("RGBA", (FRAME_SIZE, FRAME_SIZE), (0, 0, 0, 0))
    ch = int(ih * sy)
    cw = int(iw * sx)
    st = scaled_idle.resize((cw, ch), Image.Resampling.LANCZOS)
    px = (FRAME_SIZE - cw) // 2
    py = ground_y - ch + dy
    f.paste(st, (px, py), st)
    idle_frames.append(f)

idle_right = make_sheet(idle_frames)
idle_left = idle_right.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
idle_right.save(out_dir / "idle_right.png")
idle_left.save(out_dir / "idle_left.png")
idle_right.save(out_dir / "idle.png")
idle_left.save(out_dir / "idle_flip.png")

# ── 2. WALKING ANIMATION (4 frames true stride sequence) ─────────────────────
walk_frames = []
for wc in walk_crops:
    f = Image.new("RGBA", (FRAME_SIZE, FRAME_SIZE), (0, 0, 0, 0))
    scaled_w = fit_to_frame(wc, max_h=90, max_w=112)
    ww, wh = scaled_w.size
    px = (FRAME_SIZE - ww) // 2
    py = ground_y - wh
    f.paste(scaled_w, (px, py), scaled_w)
    walk_frames.append(f)

walk_right = make_sheet(walk_frames)
walk_left = walk_right.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
walk_right.save(out_dir / "walk_right.png")
walk_left.save(out_dir / "walk_left.png")

# ── 3. SLEEP & WAKE ANIMATION (Curled on cushion with thought bubble) ─────────
scaled_sleep = fit_to_frame(sleep_crop, max_h=96, max_w=118)
sl_w, sl_h = scaled_sleep.size

sleep_frames = []
for dy, sy in [(0, 1.0), (1, 0.985), (2, 0.97), (1, 0.985)]:
    f = Image.new("RGBA", (FRAME_SIZE, FRAME_SIZE), (0, 0, 0, 0))
    ch = int(sl_h * sy)
    st = scaled_sleep.resize((sl_w, ch), Image.Resampling.LANCZOS)
    px = (FRAME_SIZE - sl_w) // 2
    py = ground_y - ch + dy
    f.paste(st, (px, py), st)
    sleep_frames.append(f)

make_sheet(sleep_frames).save(out_dir / "sleep.png")
make_sheet(sleep_frames[::-1]).save(out_dir / "wake.png")
make_sheet(sleep_frames).save(out_dir / "sit.png")

# ── 4. WORKING & IDEA (Laptop coding cat with coffee) ─────────────────────────
scaled_work = fit_to_frame(work_crop, max_h=94, max_w=118)
wk_w, wk_h = scaled_work.size

work_frames = []
idea_frames = []
for dy in [0, -1, -2, -1]:
    f = Image.new("RGBA", (FRAME_SIZE, FRAME_SIZE), (0, 0, 0, 0))
    px = (FRAME_SIZE - wk_w) // 2
    py = ground_y - wk_h + dy
    f.paste(scaled_work, (px, py), scaled_work)
    work_frames.append(f)

for dy in [0, -2, -4, -2]:
    f = Image.new("RGBA", (FRAME_SIZE, FRAME_SIZE), (0, 0, 0, 0))
    px = (FRAME_SIZE - wk_w) // 2
    py = ground_y - wk_h + dy
    f.paste(scaled_work, (px, py), scaled_work)
    # Draw glowing yellow idea light bulb
    draw = ImageDraw.Draw(f)
    draw.ellipse([px + wk_w // 2 - 6, py - 4, px + wk_w // 2 + 6, py + 8], fill=(255, 215, 0, 240), outline=(255, 255, 255, 255))
    idea_frames.append(f)

make_sheet(work_frames).save(out_dir / "work.png")
make_sheet(idea_frames).save(out_dir / "idea.png")

# ── 5. JUMP & FALL & DRAG ───────────────────────────────────────────────────
jump_frames = []
fall_frames = []
for dy in [0, -4, -8, -4]:
    f = Image.new("RGBA", (FRAME_SIZE, FRAME_SIZE), (0, 0, 0, 0))
    scaled_j = fit_to_frame(walk_crops[1], max_h=90, max_w=112)
    jw, jh = scaled_j.size
    px = (FRAME_SIZE - jw) // 2
    py = (FRAME_SIZE - jh) // 2 + dy - 6
    f.paste(scaled_j, (px, py), scaled_j)
    jump_frames.append(f)

for dy in [0, 3, 6, 3]:
    f = Image.new("RGBA", (FRAME_SIZE, FRAME_SIZE), (0, 0, 0, 0))
    scaled_f = fit_to_frame(walk_crops[3], max_h=90, max_w=112)
    fw, fh = scaled_f.size
    px = (FRAME_SIZE - fw) // 2
    py = (FRAME_SIZE - fh) // 2 + dy
    f.paste(scaled_f, (px, py), scaled_f)
    fall_frames.append(f)

make_sheet(jump_frames).save(out_dir / "jump.png")
make_sheet(fall_frames).save(out_dir / "fall.png")
make_sheet(fall_frames).save(out_dir / "drag.png")
make_sheet(walk_frames[:2] + walk_frames[2:]).save(out_dir / "land.png")

# ── 6. HAPPY, ROAR & EMOTES ─────────────────────────────────────────────────
happy_frames = []
for dy in [0, -3, -6, -3]:
    f = Image.new("RGBA", (FRAME_SIZE, FRAME_SIZE), (0, 0, 0, 0))
    px = (FRAME_SIZE - iw) // 2
    py = ground_y - ih + dy
    f.paste(scaled_idle, (px, py), scaled_idle)
    draw = ImageDraw.Draw(f)
    draw.text((px + iw - 4, py + 8), "✨", fill=(255, 215, 0, 240))
    draw.text((px - 8, py + 12), "🪙", fill=(255, 200, 50, 240))
    happy_frames.append(f)
make_sheet(happy_frames).save(out_dir / "happy.png")

roar_frames = []
for i in range(6):
    f = Image.new("RGBA", (FRAME_SIZE, FRAME_SIZE), (0, 0, 0, 0))
    sc = 1.0 + (i % 3) * 0.04
    rw = int(iw * sc)
    rh = int(ih * sc)
    st = scaled_idle.resize((rw, rh), Image.Resampling.LANCZOS)
    px = (FRAME_SIZE - rw) // 2
    py = ground_y - rh
    f.paste(st, (px, py), st)
    roar_frames.append(f)
make_sheet(roar_frames).save(out_dir / "roar.png")

# Emotes
music_frames = []
for i, dx in enumerate([-2, 0, 2, 0]):
    f = Image.new("RGBA", (FRAME_SIZE, FRAME_SIZE), (0, 0, 0, 0))
    px = (FRAME_SIZE - iw) // 2 + dx
    py = ground_y - ih
    f.paste(scaled_idle, (px, py), scaled_idle)
    draw = ImageDraw.Draw(f)
    draw.text((px + iw - 4, py + 4), "♪", fill=(255, 215, 0, 240))
    draw.text((px - 8, py + 14), "♫", fill=(0, 220, 255, 240))
    music_frames.append(f)
make_sheet(music_frames).save(out_dir / "music.png")

make_sheet(idle_frames).save(out_dir / "blink.png")
make_sheet(idle_frames).save(out_dir / "shrug.png")
make_sheet(idle_frames).save(out_dir / "sad.png")
make_sheet(idle_frames).save(out_dir / "cry.png")
make_sheet(idle_frames).save(out_dir / "eat.png")

print(f"[SUCCESS] All 21 Drip Cat animation sheets generated in {out_dir}!")

# Assemble showcase image
showcase_items = [
    ("1. Idle Stance", out_dir / "idle_right.png"),
    ("2. 4-Frame Walking", out_dir / "walk_right.png"),
    ("3. Laptop Working", out_dir / "work.png"),
    ("4. Cushion Sleeping", out_dir / "sleep.png"),
]

showcase = Image.new("RGBA", (FRAME_SIZE * 4, FRAME_SIZE * len(showcase_items)), (22, 22, 30, 255))
for idx, (label, pth) in enumerate(showcase_items):
    if pth.exists():
        sim = Image.open(pth).convert("RGBA")
        sub = sim.crop((0, 0, min(sim.width, FRAME_SIZE * 4), FRAME_SIZE))
        showcase.paste(sub, (0, idx * FRAME_SIZE), sub)

showcase_out = pathlib.Path(r"C:\Users\alame\.gemini\antigravity-ide\brain\39d2fa9e-9b0d-4564-9852-7c140f8d8f57\drip_cat_custom_showcase.png")
showcase.save(showcase_out)
print(f"Saved custom showcase to {showcase_out}")
