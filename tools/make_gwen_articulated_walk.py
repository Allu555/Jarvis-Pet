import math
import pathlib
import numpy as np
from PIL import Image, ImageDraw

src_dir = pathlib.Path(r"c:\Users\alame\Downloads\Desktop-Pet-main\Desktop-Pet-main\assets\gwen_sources")
out_dir = pathlib.Path(r"c:\Users\alame\Downloads\Desktop-Pet-main\Desktop-Pet-main\assets\sprites\ghost_spider")

standing_img = Image.open(src_dir / "gwen_standing_perfect.png").convert("RGBA")
target_h = 96
scale = target_h / standing_img.height
target_w = int(standing_img.width * scale)
base = standing_img.resize((target_w, target_h), Image.Resampling.LANCZOS)
bw, bh = base.size

# Build solid suit backdrop for torso and inner limbs (fill with dark indigo RGB 38, 24, 66)
backdrop = Image.new("RGBA", (bw, bh), (0, 0, 0, 0))
draw = ImageDraw.Draw(backdrop)
# Draw rounded torso body capsule
draw.rounded_rectangle([int(0.15*bw), int(0.48*bh), int(0.85*bw), int(0.88*bh)], radius=8, fill=(38, 24, 66, 255))
# Paste head & chest over backdrop
backdrop.paste(base.crop((0, 0, bw, int(0.55*bh))), (0, 0), base.crop((0, 0, bw, int(0.55*bh))))
backdrop.paste(base.crop((int(0.3*bw), int(0.55*bh), int(0.7*bw), int(0.75*bh))), (int(0.3*bw), int(0.55*bh)), base.crop((int(0.3*bw), int(0.55*bh), int(0.7*bw), int(0.75*bh))))

# Extract articulated body parts
head = base.crop((0, 0, bw, int(0.55*bh)))
arm_left = base.crop((0, int(0.48*bh), int(0.32*bw), int(0.78*bh)))
arm_right = base.crop((int(0.68*bw), int(0.48*bh), bw, int(0.78*bh)))
leg_left = base.crop((int(0.08*bw), int(0.68*bh), int(0.52*bw), bh))
leg_right = base.crop((int(0.48*bw), int(0.68*bh), int(0.92*bw), bh))
torso_middle = base.crop((int(0.18*bw), int(0.48*bh), int(0.82*bw), int(0.76*bh)))

FRAME_SIZE = 128
ground_y = 116
base_x = (FRAME_SIZE - bw) // 2

def rotate_pivot_joint(img, angle, pivot_top=True):
    if angle == 0:
        return img, 0, 0
    w, h = img.size
    pad = max(w, h)
    padded = Image.new("RGBA", (w + pad * 2, h + pad * 2), (0, 0, 0, 0))
    padded.paste(img, (pad, pad))
    rotated = padded.rotate(angle, resample=Image.Resampling.BICUBIC)
    bbox = rotated.getbbox()
    if not bbox:
        return img, 0, 0
    cropped = rotated.crop(bbox)
    rw, rh = cropped.size
    dx = (w - rw) // 2
    dy = (h - rh) // 2
    return cropped, dx, dy

# 6-phase side walk stride keyframes
walk_6_keyframes = [
    # 0. Right contact forward, Left push back (heel contact & toe lift)
    {
        "bob_y": 0, "head_bob": 0,
        "l_leg": {"dx": -5, "dy": 1, "rot": 18},
        "r_leg": {"dx": 5, "dy": -2, "rot": -16},
        "l_arm": {"dx": 6, "dy": -2, "rot": -20},
        "r_arm": {"dx": -5, "dy": 1, "rot": 18},
    },
    # 1. Recoil / Passing position (weight on right foot, left knee lifts and bends forward)
    {
        "bob_y": -2, "head_bob": -1,
        "l_leg": {"dx": 1, "dy": -4, "rot": -10},
        "r_leg": {"dx": 0, "dy": 0, "rot": 0},
        "l_arm": {"dx": 0, "dy": 0, "rot": 0},
        "r_arm": {"dx": 0, "dy": 0, "rot": 0},
    },
    # 2. High point apex (left foot swinging forward, rising up)
    {
        "bob_y": -4, "head_bob": -2,
        "l_leg": {"dx": 4, "dy": -2, "rot": -12},
        "r_leg": {"dx": -3, "dy": 1, "rot": 10},
        "l_arm": {"dx": -4, "dy": 1, "rot": 12},
        "r_arm": {"dx": 4, "dy": -2, "rot": -14},
    },
    # 3. Left contact forward, Right push back (heel contact & toe lift)
    {
        "bob_y": 0, "head_bob": 0,
        "l_leg": {"dx": 5, "dy": -2, "rot": -16},
        "r_leg": {"dx": -5, "dy": 1, "rot": 18},
        "l_arm": {"dx": -5, "dy": 1, "rot": 18},
        "r_arm": {"dx": 6, "dy": -2, "rot": -20},
    },
    # 4. Recoil / Passing position (weight on left foot, right knee lifts and bends forward)
    {
        "bob_y": -2, "head_bob": -1,
        "l_leg": {"dx": 0, "dy": 0, "rot": 0},
        "r_leg": {"dx": 1, "dy": -4, "rot": -10},
        "l_arm": {"dx": 0, "dy": 0, "rot": 0},
        "r_arm": {"dx": 0, "dy": 0, "rot": 0},
    },
    # 5. High point apex (right foot swinging forward, rising up)
    {
        "bob_y": -4, "head_bob": -2,
        "l_leg": {"dx": -3, "dy": 1, "rot": 10},
        "r_leg": {"dx": 4, "dy": -2, "rot": -12},
        "l_arm": {"dx": 4, "dy": -2, "rot": -14},
        "r_arm": {"dx": -4, "dy": 1, "rot": 12},
    },
]

walk_frames = []
for kf in walk_6_keyframes:
    f = Image.new("RGBA", (FRAME_SIZE, FRAME_SIZE), (0, 0, 0, 0))
    by = ground_y - bh + kf["bob_y"]
    bx = base_x

    # Paste solid backdrop first to prevent any transparent seams
    f.paste(backdrop, (bx, by), backdrop)

    # Transform Limbs
    al_img, al_dx, al_dy = rotate_pivot_joint(arm_left, kf["l_arm"]["rot"])
    al_x = bx + kf["l_arm"]["dx"] + al_dx
    al_y = by + int(0.48 * bh) + kf["l_arm"]["dy"] + al_dy

    ar_img, ar_dx, ar_dy = rotate_pivot_joint(arm_right, kf["r_arm"]["rot"])
    ar_x = bx + int(0.68 * bw) + kf["r_arm"]["dx"] + ar_dx
    ar_y = by + int(0.48 * bh) + kf["r_arm"]["dy"] + ar_dy

    ll_img, ll_dx, ll_dy = rotate_pivot_joint(leg_left, kf["l_leg"]["rot"])
    ll_x = bx + int(0.08 * bw) + kf["l_leg"]["dx"] + ll_dx
    ll_y = by + int(0.68 * bh) + kf["l_leg"]["dy"] + ll_dy

    rl_img, rl_dx, rl_dy = rotate_pivot_joint(leg_right, kf["r_leg"]["rot"])
    rl_x = bx + int(0.48 * bw) + kf["r_leg"]["dx"] + rl_dx
    rl_y = by + int(0.68 * bh) + kf["r_leg"]["dy"] + rl_dy

    # Composite Layers
    # 1. Back Arm
    f.paste(al_img, (al_x, al_y), al_img)
    # 2. Both Legs
    f.paste(ll_img, (ll_x, ll_y), ll_img)
    f.paste(rl_img, (rl_x, rl_y), rl_img)
    # 3. Torso details & Chest Spider
    tx = bx + int(0.18 * bw)
    ty = by + int(0.48 * bh)
    f.paste(torso_middle, (tx, ty), torso_middle)
    # 4. Head & Hood
    hy = by + kf["head_bob"]
    f.paste(head, (bx, hy), head)
    # 5. Front Arm
    f.paste(ar_img, (ar_x, ar_y), ar_img)

    walk_frames.append(f)

# Save walking sheets
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
showcase.save(r"C:\Users\alame\.gemini\antigravity-ide\brain\39d2fa9e-9b0d-4564-9852-7c140f8d8f57\gwen_6phase_walk_final.png")
print("Saved final 6-phase walk cycle!")
