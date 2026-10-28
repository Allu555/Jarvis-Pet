import math
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import numpy as np

SRC_DIR = Path(__file__).parent / "miles_sources"
SPRITES_DIR = Path(__file__).parent / "sprites" / "miles"
OUT_GALLERY = SRC_DIR / "miles_poses_gallery.png"

def make_miles_pose_gallery():
    pose_map = [
        ("1. Idle Standing", SPRITES_DIR / "idle.png", 0),
        ("2. Walking Stride", SPRITES_DIR / "walk_right.png", 0),
        ("3. Jump Leap", SPRITES_DIR / "jump.png", 1),
        ("4. Diving Fall", SPRITES_DIR / "fall.png", 1),
        ("5. Hero Landing", SPRITES_DIR / "land.png", 0),
        ("6. Venom Strike (Blast)", SPRITES_DIR / "roar.png", 2),
        ("7. Work / Typing", SPRITES_DIR / "work.png", 0),
        ("8. Sleep (Upside-Down)", SPRITES_DIR / "sleep.png", 1),
        ("9. Spidey-Sense", SPRITES_DIR / "idea.png", 1),
        ("10. Happy Celebration", SPRITES_DIR / "happy.png", 1),
    ]

    card_w, card_h = 240, 280
    cols = 5
    rows = 2
    canvas_w = cols * card_w + 60
    canvas_h = rows * card_h + 100

    gallery = Image.new("RGBA", (canvas_w, canvas_h), (20, 24, 32, 255))
    draw = ImageDraw.Draw(gallery)

    # Title header
    draw.text((canvas_w // 2 - 190, 24), "MILES MORALES - PET ANIMATION POSES", fill=(255, 60, 60, 255))

    for idx, (label, sprite_path, frame_idx) in enumerate(pose_map):
        r = idx // cols
        c = idx % cols
        x0 = 30 + c * card_w + 10
        y0 = 70 + r * card_h + 10
        x1 = x0 + card_w - 20
        y1 = y0 + card_h - 20

        # Card background
        draw.rounded_rectangle([x0, y0, x1, y1], radius=14, fill=(30, 36, 48, 255), outline=(60, 70, 90, 255), width=2)

        # Label banner
        draw.rounded_rectangle([x0 + 8, y0 + 8, x1 - 8, y0 + 36], radius=6, fill=(40, 48, 64, 255))
        draw.text((x0 + 14, y0 + 14), label, fill=(255, 230, 90, 255))

        # Extract frame
        if sprite_path.exists():
            strip = Image.open(sprite_path)
            frame_w = strip.height
            frame_crop = strip.crop((frame_idx * frame_w, 0, (frame_idx + 1) * frame_w, frame_w))
            
            # Scale down slightly to fit inside card
            scaled_w = 170
            scaled_h = int(frame_crop.height * (scaled_w / frame_crop.width))
            scaled_frame = frame_crop.resize((scaled_w, scaled_h), Image.Resampling.LANCZOS if hasattr(Image, "Resampling") else Image.LANCZOS)
            
            fx = x0 + (card_w - 20 - scaled_w) // 2
            fy = y0 + 44 + (card_h - 70 - scaled_h) // 2
            gallery.paste(scaled_frame, (fx, fy), scaled_frame)

            # Also save as individual standalone pose image
            clean_name = label.split(". ")[1].lower().replace(" ", "_").replace("(", "").replace(")", "").replace("/", "_")
            single_pose_path = SRC_DIR / f"miles_pose_{clean_name}.png"
            frame_crop.save(single_pose_path)

    gallery.save(OUT_GALLERY, "PNG")
    print(f"Saved complete Miles Morales Pose Gallery to {OUT_GALLERY}")

if __name__ == "__main__":
    make_miles_pose_gallery()
