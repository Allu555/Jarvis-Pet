from pathlib import Path
from PIL import Image, ImageDraw
import numpy as np
import scipy.ndimage as ndi

BASE_DIR = Path(__file__).parent.parent
SOURCE_DIR = Path(__file__).parent / "source_images"
OUT_DIR = Path(__file__).parent / "sprites"
OUT_DIR.mkdir(parents=True, exist_ok=True)

FRAME_SIZE = 192

SHEET_COLS = {
    1: 8,  # media_1788580771545.png (Walk / Run)
    2: 8,  # media_1788580771600.png (Sleep / Sit / Lay / Cry)
    3: 8,  # media_1788580771631.png (Sit / Drag / Stumble)
    4: 6,  # media_1788580771700.png (Tablet / Idea / Cheer / Roar)
    5: 6,  # media_1788580771750.png (Idle / Greet / Happy / Look)
}


def find_source_images():
    patterns = ["media_*.png", "*.png"]
    files = []
    if SOURCE_DIR.exists():
        for p in patterns:
            files.extend(list(SOURCE_DIR.glob(p)))
    
    seen = set()
    unique = []
    for f in sorted(files, key=lambda x: x.name):
        if f.name not in seen and f.name != "album_art.png":
            seen.add(f.name)
            unique.append(f)
    return unique


def despill_and_clean_matte(frame: Image.Image) -> Image.Image:
    arr = np.array(frame).astype(np.float32)
    r, g, b = arr[:, :, 0], arr[:, :, 1], arr[:, :, 2]
    
    magenta_metric = (r + b) / 2.0 - g
    bg_mask = np.clip((magenta_metric - 25.0) / 45.0, 0.0, 1.0)
    
    alpha = (1.0 - bg_mask) * 255.0
    
    r_corr = np.where(magenta_metric > 0, np.minimum(r, g * 1.1 + 25), r)
    b_corr = np.where(magenta_metric > 0, np.minimum(b, g * 1.1 + 25), b)
    
    clean_arr = np.stack([r_corr, g, b_corr, alpha], axis=-1)
    clean_arr = np.clip(clean_arr, 0, 255).astype(np.uint8)
    
    return Image.fromarray(clean_arr, mode="RGBA")


def extract_all_raw_frames(source_files, target_size: int = FRAME_SIZE):
    """
    Intelligently splits character sheets by detecting empty gap partitions between
    characters using connected component bounding analysis.
    Crops each character tightly, scales it to fill the canvas proportionally, and
    grounds it properly on a transparent 192x192 frame.
    """
    sheets = {}
    for idx, fpath in enumerate(source_files, start=1):
        img = Image.open(fpath).convert("RGBA")
        clean = despill_and_clean_matte(img)
        arr = np.array(clean)
        alpha = arr[:, :, 3] > 35
        
        labeled, num_features = ndi.label(alpha)
        objects = ndi.find_objects(labeled)
        
        comps = []
        for o_idx, obj in enumerate(objects):
            mask = (labeled[obj] == (o_idx + 1))
            area = np.sum(mask)
            if area > 1000:
                y_slice, x_slice = obj
                comps.append((x_slice.start, x_slice.stop, y_slice.start, y_slice.stop, area))
                
        comps.sort(key=lambda c: c[0])
        
        splits = [0]
        for i in range(len(comps) - 1):
            mid = (comps[i][1] + comps[i+1][0]) // 2
            splits.append(mid)
        splits.append(arr.shape[1])
        
        frames = []
        for i in range(len(splits) - 1):
            x_start, x_end = splits[i], splits[i+1]
            
            # Find the actual tight bounding box of this character within its slice
            slice_arr = arr[:, x_start:x_end]
            slice_alpha = slice_arr[:, :, 3] > 35
            ys, xs = np.where(slice_alpha)
            
            if len(xs) > 0 and len(ys) > 0:
                min_x = x_start + xs.min()
                max_x = x_start + xs.max()
                min_y = ys.min()
                max_y = ys.max()
                
                pad = 2
                crop_box = (
                    max(x_start, min_x - pad),
                    max(0, min_y - pad),
                    min(x_end, max_x + pad + 1),
                    min(arr.shape[0], max_y + pad + 1)
                )
                char_crop = clean.crop(crop_box)
            else:
                char_crop = clean.crop((x_start, 0, x_end, clean.height))
                
            # Scale proportionally to fill the target size beautifully
            cw, ch = char_crop.size
            scale = (target_size - 12) / max(cw, ch)
            nw, nh = max(1, int(cw * scale)), max(1, int(ch * scale))
            
            try:
                resample_lanczos = Image.Resampling.LANCZOS
            except AttributeError:
                resample_lanczos = getattr(Image, "LANCZOS", getattr(Image, "ANTIALIAS", Image.BICUBIC))
            scaled = char_crop.resize((nw, nh), resample_lanczos)
            
            # Center horizontally and ground at bottom
            canvas = Image.new("RGBA", (target_size, target_size), (0, 0, 0, 0))
            ox = (target_size - nw) // 2
            oy = target_size - nh - 6
            canvas.paste(scaled, (ox, oy), scaled)
            
            frames.append(canvas)
            
        sheets[idx] = frames
        print(f"Loaded & HD Scaled {fpath.name} -> Sheet {idx}: {len(frames)} frames")
        
    return sheets


def mirror_frame(frame: Image.Image) -> Image.Image:
    return frame.transpose(Image.Transpose.FLIP_LEFT_RIGHT if hasattr(Image, "Transpose") else Image.FLIP_LEFT_RIGHT)


def create_strip(frames: list) -> Image.Image:
    if not frames:
        return Image.new("RGBA", (FRAME_SIZE, FRAME_SIZE), (0, 0, 0, 0))
    h = frames[0].height
    w = sum(f.width for f in frames)
    strip = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    cx = 0
    for f in frames:
        strip.paste(f, (cx, 0), f)
        cx += f.width
    return strip


def add_zzz_overlay_hd(frame: Image.Image, level: int) -> Image.Image:
    f = frame.copy()
    draw = ImageDraw.Draw(f)
    if level >= 1:
        draw.text((120, 50), "z", fill=(130, 200, 255, 200))
    if level >= 2:
        draw.text((135, 30), "z", fill=(150, 215, 255, 220))
    if level >= 3:
        draw.text((150, 10), "Z", fill=(180, 235, 255, 240))
    return f


def draw_music_note(draw: ImageDraw.ImageDraw, x: int, y: int, fill: tuple):
    draw.ellipse([x, y + 10, x + 8, y + 16], fill=fill)
    draw.line([(x + 7, y), (x + 7, y + 13)], fill=fill, width=2)
    draw.line([(x + 7, y), (x + 13, y + 4)], fill=fill, width=2)


def add_music_notes(frame: Image.Image, frame_idx: int) -> Image.Image:
    f = frame.copy()
    draw = ImageDraw.Draw(f)
    notes = [
        [(25, 40, (60, 220, 255, 240)), (145, 30, (255, 120, 220, 240))],
        [(35, 25, (255, 210, 60, 240)), (155, 45, (80, 255, 180, 240))],
        [(20, 50, (255, 100, 180, 240)), (140, 20, (70, 220, 255, 240))],
        [(40, 30, (255, 220, 80, 240)), (150, 55, (180, 100, 255, 240))],
        [(25, 20, (80, 240, 255, 240)), (145, 35, (255, 130, 200, 240))],
        [(30, 45, (255, 200, 60, 240)), (155, 25, (60, 220, 255, 240))],
    ]
    for nx, ny, col in notes[frame_idx % len(notes)]:
        draw_music_note(draw, nx, ny, col)
    return f


def generate_all_sprites():
    source_files = find_source_images()
    print("Found source images:")
    for f in source_files:
        print(" ", f)
        
    sheets = extract_all_raw_frames(source_files)
    
    # Processed high-definition frame collections
    s1 = sheets[1]
    s2 = sheets[2]
    s3 = sheets[3]
    s4 = sheets[4]
    s5 = sheets[5]
    
    # ── BUILD HD ANIMATION STRIPS ─────────────────────────────────────────────
    
    # 1. Walk Right & Walk Left (8 frames)
    walk_right_frames = s1
    walk_left_frames = [mirror_frame(f) for f in s1]
    
    # 2. Idle (Sheet 5 frames in smooth loop)
    idle_frames = [s5[0], s5[1], s5[2], s5[3], s5[4], s5[0]]
    idle_flip_frames = [mirror_frame(f) for f in idle_frames]
    
    # 3. Blink / Cute look
    blink_frames = [s5[0], s4[4], s4[4], s5[0]]
    
    # 4. Happy / Cheer (Giggling & OK-sign winking)
    happy_frames = [s4[4], s4[5], s5[3], s4[5]]
    
    # 5. Idea (Lightbulb eureka!)
    idea_frames = [s4[1], s4[1], s4[2], s4[2], s4[2], s4[4]]
    
    # 6. Work / Hologram Tablet
    work_frames = [s4[0], s4[3], s4[0], s4[3], s4[0], s4[4]]
    
    # 7. Sit Down
    sit_frames = [s3[4], s3[5], s3[4], s2[2]]
    
    # 8. Sleep (Collapsed flat on belly with cute Zzz animation)
    sleep_base = s2[4]
    sleep_frames = [
        add_zzz_overlay_hd(sleep_base, 0),
        add_zzz_overlay_hd(sleep_base, 1),
        add_zzz_overlay_hd(sleep_base, 2),
        add_zzz_overlay_hd(sleep_base, 3),
    ]
    
    # 9. Wake Up (From flat on belly -> sit up -> stand)
    wake_frames = [s2[4], s2[5], s2[2], s2[0], s5[0]]
    
    # 10. Cry / Sad
    cry_frames = [s2[0], s2[2], s2[3], s2[5], s2[6], s2[7]]
    
    # 11. Sad / Pout
    sad_frames = [s3[0], s3[1], s3[2], s3[6], s3[7], s3[0]]
    
    # 12. Shrug / Greet (Hands open welcoming)
    shrug_frames = [s5[0], s5[5], s5[5], s5[0]]
    
    # 13. Jump / Leap
    jump_frames = [s1[2], s1[4], s1[6], s1[0]]
    
    # 14. Roar / Super Cheer
    roar_frames = [s4[1], s4[2], s4[5], s4[5]]

    # 15. Drag / Picked Up (Flailing / dangling in air while being carried)
    drag_frames = [s1[4], s3[2], s5[5], s3[3]]

    # 16. Fall / Freefall (Dangling in air falling downwards)
    fall_frames = [s1[3], s1[4], s5[5], s1[4]]

    # 17. Land (Ground impact & recovery)
    land_frames = [s1[2], s2[6], s5[3], s5[0]]

    # 18. Music Dance (Grooving with floating musical notes)
    music_base = [s4[5], s5[3], s4[4], s4[5], s1[4], s5[4]]
    music_frames = [add_music_notes(f, i) for i, f in enumerate(music_base)]
    
    animations = {
        "walk_right": walk_right_frames,
        "walk_left": walk_left_frames,
        "idle": idle_frames,
        "idle_flip": idle_flip_frames,
        "blink": blink_frames,
        "happy": happy_frames,
        "idea": idea_frames,
        "work": work_frames,
        "sit": sit_frames,
        "sleep": sleep_frames,
        "wake": wake_frames,
        "cry": cry_frames,
        "sad": sad_frames,
        "shrug": shrug_frames,
        "jump": jump_frames,
        "roar": roar_frames,
        "drag": drag_frames,
        "fall": fall_frames,
        "land": land_frames,
        "music": music_frames,
    }
    
    print(f"\nSaving High-Definition (4K crisp) sprite sheets ({FRAME_SIZE}x{FRAME_SIZE}px per frame) to assets/sprites/:")
    for name, frames in animations.items():
        strip = create_strip(frames)
        dest = OUT_DIR / f"{name}.png"
        strip.save(dest)
        print(f"  [SAVED HD] {dest.name} ({len(frames)} frames, {strip.width}x{strip.height}px)")
        
    print("\nAll HD 4K sprite sheets generated successfully!")


generate_all = generate_all_sprites


if __name__ == "__main__":
    generate_all_sprites()
