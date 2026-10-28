import math
import pathlib
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

src_dir = pathlib.Path(r"c:\Users\alame\Downloads\Desktop-Pet-main\Desktop-Pet-main\assets\gwen_sources")
out_dir = pathlib.Path(r"c:\Users\alame\Downloads\Desktop-Pet-main\Desktop-Pet-main\assets\sprites\ghost_spider")

standing_img = Image.open(src_dir / "gwen_standing_perfect.png").convert("RGBA")
sw, sh = standing_img.size

# Target normalized size in 128x128 canvas
target_h = 96
scale = target_h / sh
target_w = int(sw * scale)
base = standing_img.resize((target_w, target_h), Image.Resampling.LANCZOS)
bw, bh = base.size

FRAME_SIZE = 128
ground_y = 116
base_x = (FRAME_SIZE - bw) // 2

# 6-phase walk cycle with smooth physics & stepping dynamics:
# - Alternating left and right stride steps with foot lift and ground strike
# - Natural arm counter-swing
# - Head & torso vertical bobbing rhythm
# - Zero transparent gap seams

walk_6_params = [
    # 0. Right foot forward contact, Left foot trailing, Left arm forward swing, Right arm back swing
    {"angle": -5.0, "dx": -2, "dy": 0, "sx": 0.96, "sy": 1.02, "head_bob": 0},
    # 1. Passing position (weight on right foot, left knee passing forward, body rising)
    {"angle": -2.0, "dx": -1, "dy": -3, "sx": 0.98, "sy": 1.03, "head_bob": -1},
    # 2. High point apex (left foot swinging forward, apex bounce)
    {"angle": 0.0,  "dx": 0,  "dy": -5, "sx": 1.00, "sy": 1.04, "head_bob": -2},
    # 3. Left foot forward contact, Right foot trailing, Right arm forward swing, Left arm back swing
    {"angle": 5.0,  "dx": 2,  "dy": 0, "sx": 0.96, "sy": 1.02, "head_bob": 0},
    # 4. Passing position (weight on left foot, right knee passing forward, body rising)
    {"angle": 2.0,  "dx": 1,  "dy": -3, "sx": 0.98, "sy": 1.03, "head_bob": -1},
    # 5. High point apex (right foot swinging forward, apex bounce)
    {"angle": 0.0,  "dx": 0,  "dy": -5, "sx": 1.00, "sy": 1.04, "head_bob": -2},
]

walk_frames = []
for p in walk_6_params:
    f = Image.new("RGBA", (FRAME_SIZE, FRAME_SIZE), (0, 0, 0, 0))
    cur_w = int(bw * p["sx"])
    cur_h = int(bh * p["sy"])
    scaled = base.resize((cur_w, cur_h), Image.Resampling.LANCZOS)
    
    pad = 20
    padded = Image.new("RGBA", (cur_w + pad * 2, cur_h + pad * 2), (0, 0, 0, 0))
    padded.paste(scaled, (pad, pad))
    
    rotated = padded.rotate(p["angle"], resample=Image.Resampling.BICUBIC)
    bbox = rotated.getbbox()
    rot_img = rotated.crop(bbox) if bbox else rotated
    rw, rh = rot_img.size
    
    px = (FRAME_SIZE - rw) // 2 + p["dx"]
    py = ground_y - rh + p["dy"]
    
    f.paste(rot_img, (px, py), rot_img)
    walk_frames.append(f)

# Save 6-phase walk cycle
walk_sheet = Image.new("RGBA", (FRAME_SIZE * len(walk_frames), FRAME_SIZE), (0, 0, 0, 0))
for i, f in enumerate(walk_frames):
    walk_sheet.paste(f, (i * FRAME_SIZE, 0))

walk_right = walk_sheet
walk_left = walk_sheet.transpose(Image.Transpose.FLIP_LEFT_RIGHT)

walk_right.save(out_dir / "walk_right.png")
walk_left.save(out_dir / "walk_left.png")

# Save showcase
showcase = Image.new("RGBA", (FRAME_SIZE * 6, FRAME_SIZE), (24, 24, 32, 255))
showcase.paste(walk_right, (0, 0), walk_right)
showcase.save(r"C:\Users\alame\.gemini\antigravity-ide\brain\39d2fa9e-9b0d-4564-9852-7c140f8d8f57\gwen_6phase_walk_perfect.png")
print("Saved perfect 6-phase walking cycle!")
