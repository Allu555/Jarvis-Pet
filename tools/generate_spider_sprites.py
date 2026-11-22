"""
generate_spider_sprites.py – Extracts and formats high-tech Spider Mech sprites
from assets/spider_spritesheet.jpg into the Desktop-Pet assets/sprites/spider_bot/ directory.
"""

import os
from pathlib import Path
import numpy as np
from PIL import Image

BASE_DIR = Path(__file__).resolve().parent.parent
SHEET_PATH = BASE_DIR / "assets" / "spider_spritesheet.jpg"
OUT_DIR = BASE_DIR / "assets" / "sprites" / "spider_bot"
OUT_DIR.mkdir(parents=True, exist_ok=True)

FRAME_SIZE = 128


def clean_frame(crop_img: Image.Image, remove_bottom_caption_px: int = 12) -> Image.Image:
    """
    Removes black background, cuts off bottom caption text,
    and returns transparent RGBA image cropped to bounding box.
    """
    w, h = crop_img.size
    if h > remove_bottom_caption_px + 10:
        crop_img = crop_img.crop((0, 0, w, h - remove_bottom_caption_px))
    
    rgba = crop_img.convert("RGBA")
    arr = np.array(rgba)
    
    # Calculate luminance / max RGB
    rgb_max = np.max(arr[:, :, :3], axis=2).astype(float)
    
    # Smooth alpha ramp: black <= 18 is 0, >= 40 is 255
    alpha = np.clip((rgb_max - 18.0) * (255.0 / 22.0), 0, 255).astype(np.uint8)
    arr[:, :, 3] = alpha
    
    cleaned = Image.fromarray(arr)
    bbox = cleaned.getbbox()
    if bbox:
        cleaned = cleaned.crop(bbox)
    return cleaned


def place_in_frame(img: Image.Image, frame_size: int = FRAME_SIZE, y_offset: int = 10) -> Image.Image:
    """Scales and centers a sprite inside a square transparent frame."""
    cw, ch = img.size
    if cw == 0 or ch == 0:
        return Image.new("RGBA", (frame_size, frame_size), (0, 0, 0, 0))
    
    # Target maximum dimension ~ 80% of frame_size
    target_max = int(frame_size * 0.82)
    scale = target_max / max(cw, ch)
    nw = max(1, int(cw * scale))
    nh = max(1, int(ch * scale))
    
    resized = img.resize((nw, nh), Image.Resampling.LANCZOS)
    
    frame = Image.new("RGBA", (frame_size, frame_size), (0, 0, 0, 0))
    x = (frame_size - nw) // 2
    # Place slightly lower so feet align with ground
    y = frame_size - nh - y_offset
    frame.paste(resized, (x, y), resized)
    return frame


def create_strip(frames: list) -> Image.Image:
    """Stitches square frames horizontally into a sprite strip."""
    if not frames:
        return Image.new("RGBA", (FRAME_SIZE, FRAME_SIZE), (0, 0, 0, 0))
    w = len(frames) * FRAME_SIZE
    h = FRAME_SIZE
    strip = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    for i, f in enumerate(frames):
        strip.paste(f, (i * FRAME_SIZE, 0), f)
    return strip


def mirror_frame(frame: Image.Image) -> Image.Image:
    return frame.transpose(Image.Transpose.FLIP_LEFT_RIGHT)


def generate():
    if not SHEET_PATH.exists():
        print(f"Error: {SHEET_PATH} does not exist.")
        return

    sheet = Image.open(SHEET_PATH)
    print(f"Loaded sheet: {sheet.size}")

    # Box definitions: (x0, y0, x1, y1)
    # Row 1: Idle (y ~ 100 to 175)
    idle_boxes = [
        (10, 100, 105, 175),
        (110, 100, 215, 175),
        (220, 100, 315, 175),
        (320, 100, 415, 175),
        (420, 100, 520, 175),
        (525, 100, 625, 175),
    ]

    # Row 2: Walk styles (y ~ 185 to 245)
    walk_boxes = [
        (15, 185, 80, 245),
        (85, 185, 140, 245),
        (140, 185, 190, 245),
        (190, 185, 245, 245),
        (245, 185, 305, 245),
        (305, 185, 360, 245),
    ]

    # Row 5: Scanning & Hologram (y ~ 435 to 515)
    scan_boxes = [
        (10, 435, 75, 515),    # Scan start
        (75, 435, 155, 515),   # Blue Holographic beam
        (155, 435, 240, 515),  # 360 Holographic radar
        (310, 435, 385, 515),  # Detect target
        (385, 435, 475, 515),  # Tracking target
    ]

    # Row 6: Climbing / Web Hang (y ~ 530 to 600)
    drag_box = (175, 530, 240, 600)   # Hang from web
    climb_box = (60, 530, 115, 600)   # Climb wall

    # Row 4: Jump & Land (y ~ 345 to 415)
    jump_start = (95, 345, 155, 415)
    jump_air = (160, 345, 225, 415)
    jump_land = (360, 345, 430, 415)
    jump_roll = (430, 345, 510, 415)

    # Row 4 / Attack: Threat display
    threat_box = (930, 345, 1005, 415)

    # Row 7: Emotive (y ~ 615 to 675)
    curious_box = (495, 615, 560, 675)
    alert_box = (575, 615, 635, 675)
    happy_box = (685, 615, 755, 675)
    sleep_box = (755, 615, 825, 675)
    celebrate_box = (830, 615, 905, 675)
    dance_box = (960, 615, 1020, 675)

    # Crop frames
    def crop_and_frame(box, y_off=10):
        c = clean_frame(sheet.crop(box))
        return place_in_frame(c, y_offset=y_off)

    idle_frames = [crop_and_frame(b) for b in idle_boxes]
    walk_r_frames = [crop_and_frame(b) for b in walk_boxes]
    walk_l_frames = [mirror_frame(f) for f in walk_r_frames]

    # Scanning / Work frames (this will show the blue holographic scan beam when doing tasks!)
    scan_frames = [crop_and_frame(b) for b in scan_boxes]
    # Smooth scan loop: start -> beam -> radar -> beam -> tracking
    work_frames = [
        scan_frames[0],
        scan_frames[1],
        scan_frames[2],
        scan_frames[1],
        scan_frames[4],
        scan_frames[3]
    ]

    idea_frames = [scan_frames[2], scan_frames[1], scan_frames[2]]

    happy_frames = [
        crop_and_frame(celebrate_box),
        crop_and_frame(happy_box),
        crop_and_frame(dance_box),
        crop_and_frame(celebrate_box)
    ]

    sleep_frame = crop_and_frame(sleep_box, y_off=6)
    sleep_frames = [sleep_frame, sleep_frame]

    wake_frames = [
        crop_and_frame(sleep_box, y_off=6),
        crop_and_frame(alert_box),
        crop_and_frame(curious_box),
        idle_frames[0]
    ]

    jump_frames = [
        crop_and_frame(jump_start),
        crop_and_frame(jump_air, y_off=25),
        crop_and_frame(jump_air, y_off=28)
    ]

    land_frames = [
        crop_and_frame(jump_land),
        crop_and_frame(jump_roll),
        idle_frames[0]
    ]

    drag_f = crop_and_frame(drag_box, y_off=30)
    drag_frames = [drag_f, mirror_frame(drag_f)]

    shrug_frames = [crop_and_frame(curious_box), crop_and_frame(alert_box)]
    roar_frames = [crop_and_frame(threat_box), crop_and_frame(threat_box)]
    music_frames = [crop_and_frame(dance_box), mirror_frame(crop_and_frame(dance_box))]

    sit_frames = [crop_and_frame(jump_start), crop_and_frame(jump_start)]

    animations = {
        "idle": idle_frames,
        "idle_flip": [mirror_frame(f) for f in idle_frames],
        "idle_left": [mirror_frame(f) for f in idle_frames],
        "idle_right": idle_frames,
        "walk_right": walk_r_frames,
        "walk_left": walk_l_frames,
        "work": work_frames,          # Blue holographic vision scan
        "scan": work_frames,          # Direct scan trigger
        "idea": idea_frames,          # 360 degree holographic radar
        "happy": happy_frames,        # Celebration
        "sleep": sleep_frames,
        "wake": wake_frames,
        "jump": jump_frames,
        "land": land_frames,
        "fall": [crop_and_frame(jump_roll)],
        "drag": drag_frames,          # Hanging from cyber web
        "shrug": shrug_frames,
        "roar": roar_frames,
        "music": music_frames,
        "sit": sit_frames,
        "blink": [idle_frames[0], crop_and_frame(alert_box)],
        "sad": [crop_and_frame(sleep_box)],
        "cry": [crop_and_frame(sleep_box)],
    }

    print(f"Generating sprite strips in {OUT_DIR} ...")
    for name, frames in animations.items():
        strip = create_strip(frames)
        dest = OUT_DIR / f"{name}.png"
        strip.save(dest)
        print(f"  [SAVED] {dest.name} ({len(frames)} frames, {strip.width}x{strip.height})")

    print("\n[SUCCESS] Spider Mech sprite generation completed!")


if __name__ == "__main__":
    generate()

