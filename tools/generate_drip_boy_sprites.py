import pathlib
import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage

clean_path = pathlib.Path(r"c:\Users\alame\Downloads\Desktop-Pet-main\Desktop-Pet-main\assets\drip_boy_sources\drip_boy_clean.png")
clean = Image.open(clean_path).convert("RGBA")
w, h = clean.size

out_dir = pathlib.Path(r"c:\Users\alame\Downloads\Desktop-Pet-main\Desktop-Pet-main\assets\sprites\drip_boy")
out_dir.mkdir(parents=True, exist_ok=True)

FRAME_SIZE = 128
ground_y = 118

def clean_crop(box):
    c = clean.crop(box)
    arr = np.array(c)
    alpha = arr[:, :, 3] > 20
    labeled, num_features = ndimage.label(alpha)
    if num_features > 1:
        sizes = ndimage.sum(alpha, labeled, range(1, num_features + 1))
        max_label = np.argmax(sizes) + 1
        clean_mask = (labeled == max_label)
        arr[:, :, 3] = np.where(clean_mask, arr[:, :, 3], 0)
    out = Image.fromarray(arr)
    bb = out.getbbox()
    return out.crop(bb) if bb else out

def fit_to_frame(img, max_h=96, max_w=108):
    cw, ch = img.size
    scale = min(max_h / ch, max_w / cw)
    nw, nh = int(cw * scale), int(ch * scale)
    return img.resize((nw, nh), Image.Resampling.LANCZOS)

def make_sheet(frames):
    sheet_img = Image.new("RGBA", (FRAME_SIZE * len(frames), FRAME_SIZE), (0, 0, 0, 0))
    for i, f in enumerate(frames):
        sheet_img.paste(f, (i * FRAME_SIZE, 0))
    return sheet_img

print("Extracting poses for Streetwear Drip Boy...")

# 1. IDLE (Row 1 front 3/4 poses)
idle1 = clean_crop((10, 20, 85, 160))
idle2 = clean_crop((85, 20, 155, 160))
scaled_idle = fit_to_frame(idle1, max_h=96, max_w=85)
iw, ih = scaled_idle.size

idle_frames = []
for dy, sy, sx in [(0, 1.0, 1.0), (-1, 1.015, 0.99), (-2, 1.03, 0.985), (-1, 1.015, 0.99)]:
    f = Image.new("RGBA", (FRAME_SIZE, FRAME_SIZE), (0, 0, 0, 0))
    ch = int(ih * sy)
    cw = int(iw * sx)
    st = scaled_idle.resize((cw, ch), Image.Resampling.LANCZOS)
    px = (FRAME_SIZE - cw) // 2
    py = ground_y - ch + dy
    f.paste(st, (px, py), st)
    idle_frames.append(f)

idle_r = make_sheet(idle_frames)
idle_l = make_sheet([f.transpose(Image.Transpose.FLIP_LEFT_RIGHT) for f in idle_frames])
idle_r.save(out_dir / "idle_right.png")
idle_l.save(out_dir / "idle_left.png")
idle_r.save(out_dir / "idle.png")
idle_l.save(out_dir / "idle_flip.png")

# 2. WALKING (6-frame continuous stride cycle from Row 1 WALKING)
walk_boxes = [
    (235, 20, 310, 160),
    (305, 20, 375, 160),
    (370, 20, 440, 160),
    (435, 20, 505, 160),
    (500, 20, 570, 160),
    (565, 20, 635, 160),
]
walk_crops = [clean_crop(b) for b in walk_boxes]
walk_frames = []
for wc in walk_crops:
    scaled = fit_to_frame(wc, max_h=94, max_w=90)
    f = Image.new("RGBA", (FRAME_SIZE, FRAME_SIZE), (0, 0, 0, 0))
    px = (FRAME_SIZE - scaled.width) // 2
    py = ground_y - scaled.height
    f.paste(scaled, (px, py), scaled)
    walk_frames.append(f)

walk_r = make_sheet(walk_frames)
walk_l = make_sheet([f.transpose(Image.Transpose.FLIP_LEFT_RIGHT) for f in walk_frames])
walk_r.save(out_dir / "walk_right.png")
walk_l.save(out_dir / "walk_left.png")
walk_r.save(out_dir / "land.png")

# 3. RUNNING (3-frame sprint cycle from Row 1 RUNNING)
run_boxes = [
    (625, 20, 715, 160),
    (715, 20, 805, 160),
    (805, 20, 895, 160),
]
run_crops = [clean_crop(b) for b in run_boxes]
run_frames = []
for rc in run_crops:
    scaled = fit_to_frame(rc, max_h=94, max_w=98)
    f = Image.new("RGBA", (FRAME_SIZE, FRAME_SIZE), (0, 0, 0, 0))
    px = (FRAME_SIZE - scaled.width) // 2
    py = ground_y - scaled.height
    f.paste(scaled, (px, py), scaled)
    run_frames.append(f)

run_r = make_sheet(run_frames)
run_l = make_sheet([f.transpose(Image.Transpose.FLIP_LEFT_RIGHT) for f in run_frames])
run_r.save(out_dir / "run_right.png")
run_l.save(out_dir / "run_left.png")

# 4. JUMP & FALL
jump_raw = clean_crop((900, 20, 995, 160))
scaled_jump = fit_to_frame(jump_raw, max_h=92, max_w=92)
jw, jh = scaled_jump.size

jump_frames = []
fall_frames = []
for dy in [0, -6, -12, -6]:
    f = Image.new("RGBA", (FRAME_SIZE, FRAME_SIZE), (0, 0, 0, 0))
    px = (FRAME_SIZE - jw) // 2
    py = (FRAME_SIZE - jh) // 2 + dy - 6
    f.paste(scaled_jump, (px, py), scaled_jump)
    jump_frames.append(f)

for dy in [0, 4, 8, 4]:
    f = Image.new("RGBA", (FRAME_SIZE, FRAME_SIZE), (0, 0, 0, 0))
    px = (FRAME_SIZE - jw) // 2
    py = (FRAME_SIZE - jh) // 2 + dy + 4
    f.paste(scaled_jump, (px, py), scaled_jump)
    fall_frames.append(f)

make_sheet(jump_frames).save(out_dir / "jump.png")
make_sheet(fall_frames).save(out_dir / "fall.png")

# 5. DRAG (Skateboarding / floating hover pose)
skate_raw = clean_crop((550, 400, 640, 505))
scaled_skate = fit_to_frame(skate_raw, max_h=92, max_w=98)
sw_sk, sh_sk = scaled_skate.size

drag_frames = []
for dy, sx, sy in [(0, 1.0, 1.0), (-2, 0.98, 1.02), (-4, 0.96, 1.04), (-2, 0.98, 1.02)]:
    f = Image.new("RGBA", (FRAME_SIZE, FRAME_SIZE), (0, 0, 0, 0))
    cw = int(sw_sk * sx)
    ch = int(sh_sk * sy)
    st = scaled_skate.resize((cw, ch), Image.Resampling.LANCZOS)
    px = (FRAME_SIZE - cw) // 2
    py = (FRAME_SIZE - ch) // 2 + dy - 4
    f.paste(st, (px, py), st)
    drag_frames.append(f)

drag_r = make_sheet(drag_frames)
drag_l = make_sheet([f.transpose(Image.Transpose.FLIP_LEFT_RIGHT) for f in drag_frames])
drag_r.save(out_dir / "drag.png")
drag_r.save(out_dir / "drag_right.png")
drag_l.save(out_dir / "drag_left.png")

# 6. SLEEPING & WAKE (Row 2 SLEEPING on pillow)
sleep_boxes = [
    (10, 160, 135, 280),
    (135, 160, 230, 280),
    (230, 160, 345, 280),
]
sleep_crops = [clean_crop(b) for b in sleep_boxes]
sleep_frames = []
for i, sc in enumerate(sleep_crops):
    scaled = fit_to_frame(sc, max_h=75, max_w=112)
    f = Image.new("RGBA", (FRAME_SIZE, FRAME_SIZE), (0, 0, 0, 0))
    px = (FRAME_SIZE - scaled.width) // 2
    py = ground_y - scaled.height
    f.paste(scaled, (px, py), scaled)
    sleep_frames.append(f)

make_sheet(sleep_frames).save(out_dir / "sleep.png")
make_sheet(sleep_frames[::-1]).save(out_dir / "wake.png")

# 7. WORKING & IDEA (Row 2 WORKING with laptop)
work_boxes = [
    (345, 160, 435, 280),
    (430, 160, 515, 280),
    (510, 160, 595, 280),
    (590, 160, 675, 280),
]
work_crops = [clean_crop(b) for b in work_boxes]
work_frames = []
for wc in work_crops:
    scaled = fit_to_frame(wc, max_h=86, max_w=108)
    f = Image.new("RGBA", (FRAME_SIZE, FRAME_SIZE), (0, 0, 0, 0))
    px = (FRAME_SIZE - scaled.width) // 2
    py = ground_y - scaled.height
    f.paste(scaled, (px, py), scaled)
    work_frames.append(f)

make_sheet(work_frames).save(out_dir / "work.png")
make_sheet(work_frames).save(out_dir / "idea.png")

# 8. SIT (Gaming Chair in Row 4 or Sitting cross-legged in Row 5)
chair_raw = clean_crop((460, 400, 550, 505))
scaled_chair = fit_to_frame(chair_raw, max_h=94, max_w=94)
cw_ch, ch_ch = scaled_chair.size

sit_frames = []
for dy, sy in [(0, 1.0), (-1, 1.015), (-2, 1.025), (-1, 1.01)]:
    f = Image.new("RGBA", (FRAME_SIZE, FRAME_SIZE), (0, 0, 0, 0))
    cur_h = int(ch_ch * sy)
    st = scaled_chair.resize((cw_ch, cur_h), Image.Resampling.LANCZOS)
    px = (FRAME_SIZE - cw_ch) // 2
    py = ground_y - cur_h + dy
    f.paste(st, (px, py), st)
    sit_frames.append(f)

make_sheet(sit_frames).save(out_dir / "sit.png")

# 9. HAPPY (Hugging black cat with hearts from Row 3)
hug_boxes = [
    (625, 290, 725, 400),
    (725, 290, 805, 400),
    (805, 290, 890, 400),
]
hug_crops = [clean_crop(b) for b in hug_boxes]
happy_frames = []
for hc in hug_crops:
    scaled = fit_to_frame(hc, max_h=90, max_w=98)
    f = Image.new("RGBA", (FRAME_SIZE, FRAME_SIZE), (0, 0, 0, 0))
    px = (FRAME_SIZE - scaled.width) // 2
    py = ground_y - scaled.height
    f.paste(scaled, (px, py), scaled)
    happy_frames.append(f)

# 4th frame loop
happy_frames.append(happy_frames[1])
make_sheet(happy_frames).save(out_dir / "happy.png")

# 10. MUSIC (Red gaming headphones from Row 3)
music_raw = clean_crop((890, 290, 995, 400))
scaled_music = fit_to_frame(music_raw, max_h=92, max_w=92)
mw, mh = scaled_music.size

music_frames = []
for i, dx in enumerate([-2, 0, 2, 0]):
    f = Image.new("RGBA", (FRAME_SIZE, FRAME_SIZE), (0, 0, 0, 0))
    px = (FRAME_SIZE - mw) // 2 + dx
    py = ground_y - mh
    f.paste(scaled_music, (px, py), scaled_music)
    draw = ImageDraw.Draw(f)
    draw.text((px + mw - 6, py + 6), "♪", fill=(255, 215, 0, 240))
    draw.text((px - 8, py + 14), "♫", fill=(0, 220, 255, 240))
    music_frames.append(f)

make_sheet(music_frames).save(out_dir / "music.png")

# 11. ROAR / SPECIAL (Skateboard kickflip action)
roar_frames = []
for i in range(6):
    f = Image.new("RGBA", (FRAME_SIZE, FRAME_SIZE), (0, 0, 0, 0))
    sc = 1.0 + (i % 3) * 0.05
    rw = int(sw_sk * sc)
    rh = int(sh_sk * sc)
    st = scaled_skate.resize((rw, rh), Image.Resampling.LANCZOS)
    px = (FRAME_SIZE - rw) // 2
    py = ground_y - rh - (i % 3) * 3
    f.paste(st, (px, py), st)
    draw = ImageDraw.Draw(f)
    draw.ellipse([px - 4, py - 4, px + rw + 4, py + rh + 4], outline=(255, 215, 0, 180), width=2)
    roar_frames.append(f)

make_sheet(roar_frames).save(out_dir / "roar.png")

# 12. EAT (Coffee cup in hand from Row 4)
coffee_raw = clean_crop((10, 400, 90, 505))
scaled_coffee = fit_to_frame(coffee_raw, max_h=94, max_w=85)
cw_cf, ch_cf = scaled_coffee.size
eat_frames = []
for dy in [0, -1, -2, -1]:
    f = Image.new("RGBA", (FRAME_SIZE, FRAME_SIZE), (0, 0, 0, 0))
    px = (FRAME_SIZE - cw_cf) // 2
    py = ground_y - ch_cf + dy
    f.paste(scaled_coffee, (px, py), scaled_coffee)
    eat_frames.append(f)

make_sheet(eat_frames).save(out_dir / "eat.png")
make_sheet(idle_frames).save(out_dir / "blink.png")
make_sheet(idle_frames).save(out_dir / "shrug.png")
make_sheet(idle_frames).save(out_dir / "sad.png")
make_sheet(idle_frames).save(out_dir / "cry.png")

print(f"[SUCCESS] All 25 animation sheets generated in {out_dir}!")

# Create a master visual showcase
showcase = Image.new("RGBA", (FRAME_SIZE * 6, FRAME_SIZE * 4), (22, 25, 32, 255))
showcase.paste(idle_r, (0, 0), idle_r)
showcase.paste(walk_r, (0, FRAME_SIZE), walk_r)
showcase.paste(make_sheet(work_frames), (0, FRAME_SIZE * 2), make_sheet(work_frames))
showcase.paste(make_sheet(sleep_frames), (0, FRAME_SIZE * 3), make_sheet(sleep_frames))

out_showcase = pathlib.Path(r"C:\Users\alame\.gemini\antigravity-ide\brain\39d2fa9e-9b0d-4564-9852-7c140f8d8f57\drip_boy_master_showcase.png")
showcase.save(out_showcase)
print(f"Saved master showcase to {out_showcase}")
