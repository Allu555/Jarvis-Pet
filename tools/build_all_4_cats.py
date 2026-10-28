import pathlib
import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage

src_path = r"C:\Users\alame\Downloads\Desktop-Pet-main\Desktop-Pet-main\assets\all_cats_clean.png"
clean_sheet = Image.open(src_path).convert("RGBA")
w, h = clean_sheet.size

FRAME_SIZE = 128
ground_y = 116

cat_styles = [
    {
        "key": "drip_cat",
        "name": "Streetwear Drip Cat 🕶️🪙",
        "y": (35, 205),
        "theme_rgb": (255, 215, 0),
        "slices": [
            ("idle", (0, 130), None),
            ("walk_1", (135, 268), None),
            ("walk_2", (285, 396), [(0, 80, 0, 15)]),
            ("walk_3", (400, 508), None),
            ("sit_pose", (508, 608), None),
            ("work", (590, 820), [(0, 80, 0, 15)]),
            ("sleep", (820, 1024), [(120, 170, 0, 15)])
        ]
    },
    {
        "key": "gamer_cat",
        "name": "Gamer Kawaii Cat 🎧🌸",
        "y": (205, 375),
        "theme_rgb": (255, 105, 180),
        "slices": [
            ("idle", (0, 138), None),
            ("walk_1", (138, 275), None),
            ("walk_2", (275, 405), None),
            ("walk_3", (405, 550), None),
            ("sit_pose", (530, 628), None), # extended to preserve complete round face, sunglasses & nose!
            ("work", (618, 818), [(0, 170, 0, 15)]),
            ("sleep", (818, 1024), [(100, 170, 0, 15)])
        ]
    },
    {
        "key": "cyber_cat",
        "name": "Cyberpunk Neon Cat ⚡🕶️",
        "y": (375, 530),
        "theme_rgb": (0, 240, 255),
        "slices": [
            ("idle", (0, 130), None),
            ("walk_1", (130, 275), None),
            ("walk_2", (275, 408), None),
            ("walk_3", (395, 515), None),
            ("sit_pose", (510, 618), None),
            ("work", (608, 818), None),
            ("sleep", (818, 1024), None)
        ]
    },
    {
        "key": "explorer_cat",
        "name": "Explorer Cozy Cat 🎒📖",
        "y": (530, 682),
        "theme_rgb": (120, 220, 90),
        "slices": [
            ("idle", (0, 142), None),
            ("walk_1", (142, 305), None),
            ("walk_2", (290, 428), None),
            ("walk_3", (428, 580), None),
            ("sit_pose", (0, 142), None),
            ("work", (565, 818), None),
            ("sleep", (818, 1024), None)
        ]
    }
]

def clean_and_crop(crop_img, erase_regions=None):
    arr = np.array(crop_img)
    if erase_regions:
        for (y_a, y_b, x_a, x_b) in erase_regions:
            arr[y_a:y_b, x_a:x_b, 3] = 0
    
    alpha = arr[:, :, 3] > 20
    labeled, num_features = ndimage.label(alpha)
    if num_features > 1:
        sizes = ndimage.sum(alpha, labeled, range(1, num_features + 1))
        max_label = np.argmax(sizes) + 1
        clean_alpha = np.zeros_like(alpha)
        for lbl in range(1, num_features + 1):
            mask = (labeled == lbl)
            sz = sizes[lbl - 1]
            touches_left = np.any(mask[:, 0])
            touches_right = np.any(mask[:, -1])
            if (touches_left or touches_right) and sz < sizes[max_label - 1] * 0.15:
                continue
            clean_alpha[mask] = True
        arr[:, :, 3] = np.where(clean_alpha, arr[:, :, 3], 0)
    
    out = Image.fromarray(arr)
    bb = out.getbbox()
    if bb:
        out = out.crop(bb)
    return out

def fit_to_frame(img, max_h=92, max_w=114):
    cw, ch = img.size
    scale = min(max_h / ch, max_w / cw)
    nw, nh = int(cw * scale), int(ch * scale)
    return img.resize((nw, nh), Image.Resampling.LANCZOS)

def make_sheet(frames):
    sheet_img = Image.new("RGBA", (FRAME_SIZE * len(frames), FRAME_SIZE), (0, 0, 0, 0))
    for i, f in enumerate(frames):
        sheet_img.paste(f, (i * FRAME_SIZE, 0))
    return sheet_img

sprites_base = pathlib.Path(r"c:\Users\alame\Downloads\Desktop-Pet-main\Desktop-Pet-main\assets\sprites")

for cinfo in cat_styles:
    key = cinfo["key"]
    dname = cinfo["name"]
    y1, y2 = cinfo["y"]
    theme_rgb = cinfo["theme_rgb"]
    
    out_dir = sprites_base / key
    out_dir.mkdir(parents=True, exist_ok=True)
    print(f"\nBuilding sprite sheets for {key} in {out_dir}...")
    
    parts = {}
    for sname, (x1, x2), er in cinfo["slices"]:
        crop_img = clean_sheet.crop((x1, y1, x2, y2))
        cleaned = clean_and_crop(crop_img, er)
        parts[sname] = cleaned

    if key == "drip_cat":
        # Load from the dedicated high-res uncompressed drip cat master sheet
        drip_src = r"C:\Users\alame\.gemini\antigravity-ide\brain\39d2fa9e-9b0d-4564-9852-7c140f8d8f57\.user_uploaded\media_1788675494202.png"
        d_img = Image.open(drip_src).convert("RGBA")
        d_arr = np.array(d_img)
        alpha = d_arr[:, :, 3] > 20
        labeled, num_features = ndimage.label(alpha)
        
        def get_comp(obj_id):
            mask = (labeled == obj_id)
            obj_arr = np.zeros_like(d_arr)
            obj_arr[mask] = d_arr[mask]
            out = Image.fromarray(obj_arr)
            bb = out.getbbox()
            return out.crop(bb)

        parts["idle"] = get_comp(1)
        parts["walk_1"] = get_comp(5)
        parts["walk_2"] = get_comp(6)
        parts["walk_3"] = get_comp(4)
        parts["sit_pose"] = get_comp(7)
        parts["work"] = get_comp(15)
        parts["sleep"] = get_comp(18)

    # 1. IDLE (4 frames breathing)
    scaled_idle = fit_to_frame(parts["idle"], max_h=96, max_w=96)
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
    idle_left = make_sheet([f.transpose(Image.Transpose.FLIP_LEFT_RIGHT) for f in idle_frames])
    idle_right.save(out_dir / "idle_right.png")
    idle_left.save(out_dir / "idle_left.png")
    idle_right.save(out_dir / "idle.png")
    idle_left.save(out_dir / "idle_flip.png")

    # 2. PURE WALKING (4-frame continuous stride cycle: walk_1 -> walk_2 -> walk_3 -> walk_2)
    walk_frames = []
    for wname in ["walk_1", "walk_2", "walk_3", "walk_2"]:
        f = Image.new("RGBA", (FRAME_SIZE, FRAME_SIZE), (0, 0, 0, 0))
        scaled_w = fit_to_frame(parts[wname], max_h=90, max_w=112)
        ww, wh = scaled_w.size
        px = (FRAME_SIZE - ww) // 2
        py = ground_y - wh
        f.paste(scaled_w, (px, py), scaled_w)
        walk_frames.append(f)

    walk_right = make_sheet(walk_frames)
    walk_left = make_sheet([f.transpose(Image.Transpose.FLIP_LEFT_RIGHT) for f in walk_frames])
    walk_right.save(out_dir / "walk_right.png")
    walk_left.save(out_dir / "walk_left.png")

    # 3. SLEEPING & SITTING (Curled on cushion with dream bubble)
    scaled_sleep = fit_to_frame(parts["sleep"], max_h=96, max_w=118)
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
    
    # Sit (Dedicated seated pose with 100% complete face & breathing)
    scaled_sit = fit_to_frame(parts["sit_pose"], max_h=94, max_w=100)
    sw, sh = scaled_sit.size
    sit_frames = []
    for dy, sy in [(0, 1.0), (-1, 1.015), (-2, 1.025), (-1, 1.01)]:
        f = Image.new("RGBA", (FRAME_SIZE, FRAME_SIZE), (0, 0, 0, 0))
        ch = int(sh * sy)
        st = scaled_sit.resize((sw, ch), Image.Resampling.LANCZOS)
        px = (FRAME_SIZE - sw) // 2
        py = ground_y - ch + dy
        f.paste(st, (px, py), st)
        sit_frames.append(f)
    make_sheet(sit_frames).save(out_dir / "sit.png")

    # 4. WORKING & IDEA (Desk with laptop/books and beverage)
    scaled_work = fit_to_frame(parts["work"], max_h=94, max_w=118)
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
        draw = ImageDraw.Draw(f)
        draw.ellipse([px + wk_w // 2 - 6, py - 4, px + wk_w // 2 + 6, py + 8], fill=(*theme_rgb, 240), outline=(255, 255, 255, 255))
        idea_frames.append(f)

    make_sheet(work_frames).save(out_dir / "work.png")
    make_sheet(idea_frames).save(out_dir / "idea.png")

    # 5. JUMP & FALL & DRAG
    drag_pose = parts.get("walk_2", parts["idle"])
    scaled_drag = fit_to_frame(drag_pose, max_h=90, max_w=112)
    dw_w, dw_h = scaled_drag.size
    drag_frames = []
    for dy, sx, sy in [(0, 1.0, 1.0), (-3, 0.98, 1.02), (-6, 0.96, 1.04), (-3, 0.98, 1.02)]:
        f = Image.new("RGBA", (FRAME_SIZE, FRAME_SIZE), (0, 0, 0, 0))
        cur_w = int(dw_w * sx)
        cur_h = int(dw_h * sy)
        st = scaled_drag.resize((cur_w, cur_h), Image.Resampling.LANCZOS)
        px = (FRAME_SIZE - cur_w) // 2
        py = (FRAME_SIZE - cur_h) // 2 + dy - 4
        f.paste(st, (px, py), st)
        drag_frames.append(f)

    drag_right = make_sheet(drag_frames)
    drag_left = make_sheet([f.transpose(Image.Transpose.FLIP_LEFT_RIGHT) for f in drag_frames])
    drag_right.save(out_dir / "drag.png")
    drag_right.save(out_dir / "drag_right.png")
    drag_left.save(out_dir / "drag_left.png")

    jump_frames = []
    fall_frames = []
    for dy in [0, -6, -12, -6]:
        f = Image.new("RGBA", (FRAME_SIZE, FRAME_SIZE), (0, 0, 0, 0))
        px = (FRAME_SIZE - dw_w) // 2
        py = (FRAME_SIZE - dw_h) // 2 + dy - 8
        f.paste(scaled_drag, (px, py), scaled_drag)
        jump_frames.append(f)

    for dy in [0, 4, 8, 4]:
        f = Image.new("RGBA", (FRAME_SIZE, FRAME_SIZE), (0, 0, 0, 0))
        px = (FRAME_SIZE - dw_w) // 2
        py = (FRAME_SIZE - dw_h) // 2 + dy
        f.paste(scaled_drag, (px, py), scaled_drag)
        fall_frames.append(f)

    make_sheet(jump_frames).save(out_dir / "jump.png")
    make_sheet(fall_frames).save(out_dir / "fall.png")
    make_sheet(walk_frames).save(out_dir / "land.png")

    # 6. HAPPY & ROAR & EMOTES
    happy_frames = []
    for dy in [0, -3, -6, -3]:
        f = Image.new("RGBA", (FRAME_SIZE, FRAME_SIZE), (0, 0, 0, 0))
        px = (FRAME_SIZE - iw) // 2
        py = ground_y - ih + dy
        f.paste(scaled_idle, (px, py), scaled_idle)
        draw = ImageDraw.Draw(f)
        draw.text((px + iw - 4, py + 8), "✨", fill=(*theme_rgb, 240))
        happy_frames.append(f)
    make_sheet(happy_frames).save(out_dir / "happy.png")

    roar_frames = []
    for i in range(6):
        f = Image.new("RGBA", (FRAME_SIZE, FRAME_SIZE), (0, 0, 0, 0))
        sc = 1.0 + (i % 3) * 0.05
        rw = int(iw * sc)
        rh = int(ih * sc)
        st = scaled_idle.resize((rw, rh), Image.Resampling.LANCZOS)
        px = (FRAME_SIZE - rw) // 2
        py = ground_y - rh
        f.paste(st, (px, py), st)
        draw = ImageDraw.Draw(f)
        draw.ellipse([px - 4, py - 4, px + rw + 4, py + rh + 4], outline=(*theme_rgb, 180), width=2)
        roar_frames.append(f)
    make_sheet(roar_frames).save(out_dir / "roar.png")

    # Music & Emotes
    music_frames = []
    for i, dx in enumerate([-2, 0, 2, 0]):
        f = Image.new("RGBA", (FRAME_SIZE, FRAME_SIZE), (0, 0, 0, 0))
        px = (FRAME_SIZE - iw) // 2 + dx
        py = ground_y - ih
        f.paste(scaled_idle, (px, py), scaled_idle)
        draw = ImageDraw.Draw(f)
        draw.text((px + iw - 4, py + 4), "♪", fill=(*theme_rgb, 240))
        draw.text((px - 8, py + 14), "♫", fill=(0, 220, 255, 240))
        music_frames.append(f)
    make_sheet(music_frames).save(out_dir / "music.png")

    make_sheet(idle_frames).save(out_dir / "blink.png")
    make_sheet(idle_frames).save(out_dir / "shrug.png")
    make_sheet(idle_frames).save(out_dir / "sad.png")
    make_sheet(idle_frames).save(out_dir / "cry.png")
    make_sheet(idle_frames).save(out_dir / "eat.png")
    print(f"  -> All 21 sheets for {key} saved successfully!")

# Assemble a 4-cat master showcase gallery (4 rows, 4 columns: Idle, Walk, Work, Sleep)
showcase_cols = 4
showcase_rows = len(cat_styles)
master_showcase = Image.new("RGBA", (FRAME_SIZE * 4, FRAME_SIZE * showcase_rows), (20, 20, 28, 255))

for r_idx, cinfo in enumerate(cat_styles):
    key = cinfo["key"]
    id_p = sprites_base / key / "idle_right.png"
    wk_p = sprites_base / key / "walk_right.png"
    wo_p = sprites_base / key / "work.png"
    sl_p = sprites_base / key / "sleep.png"
    
    # 1. Idle frame 0
    id_img = Image.open(id_p).convert("RGBA").crop((0, 0, FRAME_SIZE, FRAME_SIZE))
    # 2. Walk frame 0
    wk_img = Image.open(wk_p).convert("RGBA").crop((0, 0, FRAME_SIZE, FRAME_SIZE))
    # 3. Work frame 0
    wo_img = Image.open(wo_p).convert("RGBA").crop((0, 0, FRAME_SIZE, FRAME_SIZE))
    # 4. Sleep frame 0
    sl_img = Image.open(sl_p).convert("RGBA").crop((0, 0, FRAME_SIZE, FRAME_SIZE))
    
    master_showcase.paste(id_img, (0, r_idx * FRAME_SIZE), id_img)
    master_showcase.paste(wk_img, (FRAME_SIZE, r_idx * FRAME_SIZE), wk_img)
    master_showcase.paste(wo_img, (FRAME_SIZE * 2, r_idx * FRAME_SIZE), wo_img)
    master_showcase.paste(sl_img, (FRAME_SIZE * 3, r_idx * FRAME_SIZE), sl_img)

out_master_showcase = pathlib.Path(r"C:\Users\alame\.gemini\antigravity-ide\brain\39d2fa9e-9b0d-4564-9852-7c140f8d8f57\all_4_cats_showcase.png")
master_showcase.save(out_master_showcase)
print(f"\n[COMPLETE] Saved all 4 cat styles and master showcase to {out_master_showcase}")
