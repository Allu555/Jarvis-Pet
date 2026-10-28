import numpy as np
from PIL import Image

def generate_perfect_miles():
    base = Image.open(r"C:\Users\alame\.gemini\antigravity-ide\brain\39d2fa9e-9b0d-4564-9852-7c140f8d8f57\scratch\miles_perfect_crop.png").convert("RGBA")
    bw, bh = base.size

    target_h = 96
    scale = target_h / bh
    target_w = int(bw * scale)
    base = base.resize((target_w, target_h), Image.Resampling.LANCZOS)
    bw, bh = base.size
    print(f"Base size: {bw}x{bh}")

    FRAME_SIZE = 128
    base_x = (FRAME_SIZE - bw) // 2
    ground_y = 116

    # 1. Idle Sprite Sheet (4 frames of breathing & subtle eye shimmer)
    idle_sheet = Image.new("RGBA", (FRAME_SIZE * 4, FRAME_SIZE), (0, 0, 0, 0))
    # Inhale & Exhale breathing curve
    for i, (dy, sy, sx) in enumerate([
        (0, 1.0, 1.0),         # Neutral stance
        (-1, 1.02, 0.99),      # Inhale lift
        (-2, 1.035, 0.985),    # Peak breath
        (-1, 1.015, 0.995)     # Exhale settling
    ]):
        fh = int(bh * sy)
        fw = int(bw * sx)
        frame_img = base.resize((fw, fh), Image.Resampling.LANCZOS)
        px = (FRAME_SIZE - fw) // 2
        py = ground_y - fh + dy
        
        canvas = Image.new("RGBA", (FRAME_SIZE, FRAME_SIZE), (0, 0, 0, 0))
        canvas.paste(frame_img, (px, py), frame_img)
        idle_sheet.paste(canvas, (i * FRAME_SIZE, 0))

    # 2. Walk Cycle (4 frames of dynamic bouncy chibi waddle stride)
    walk_sheet = Image.new("RGBA", (FRAME_SIZE * 4, FRAME_SIZE), (0, 0, 0, 0))
    
    walk_keyframes = [
        # Frame 0: Left stride forward (tilt left, lift right foot, forward step)
        {"angle": -4.5, "dx": -2, "dy": -3, "sx": 0.97, "sy": 1.03},
        # Frame 1: Ground contact & passing dip
        {"angle": 0.0,  "dx": 0,  "dy": 1,  "sx": 1.04, "sy": 0.96},
        # Frame 2: Right stride forward (tilt right, lift left foot, forward step)
        {"angle": 4.5,  "dx": 2,  "dy": -3, "sx": 0.97, "sy": 1.03},
        # Frame 3: Ground contact & passing dip
        {"angle": 0.0,  "dx": 0,  "dy": 1,  "sx": 1.04, "sy": 0.96},
    ]

    for i, kf in enumerate(walk_keyframes):
        cur_w = int(bw * kf["sx"])
        cur_h = int(bh * kf["sy"])
        scaled = base.resize((cur_w, cur_h), Image.Resampling.LANCZOS)
        
        # Rotate from feet/hip base
        if kf["angle"] != 0:
            pad = 20
            padded = Image.new("RGBA", (cur_w + pad * 2, cur_h + pad * 2), (0, 0, 0, 0))
            padded.paste(scaled, (pad, pad))
            # Rotate
            rotated = padded.rotate(kf["angle"], resample=Image.Resampling.BICUBIC)
            # Crop
            bbox = rotated.getbbox()
            rot_img = rotated.crop(bbox)
            rw, rh = rot_img.size
            px = (FRAME_SIZE - rw) // 2 + kf["dx"]
            py = ground_y - rh + kf["dy"]
            frame = Image.new("RGBA", (FRAME_SIZE, FRAME_SIZE), (0, 0, 0, 0))
            frame.paste(rot_img, (px, py), rot_img)
        else:
            px = (FRAME_SIZE - cur_w) // 2 + kf["dx"]
            py = ground_y - cur_h + kf["dy"]
            frame = Image.new("RGBA", (FRAME_SIZE, FRAME_SIZE), (0, 0, 0, 0))
            frame.paste(scaled, (px, py), scaled)
            
        walk_sheet.paste(frame, (i * FRAME_SIZE, 0))

    # Save to pet sprite directory
    out_dir = r"c:\Users\alame\Downloads\Desktop-Pet-main\Desktop-Pet-main\assets\sprites\miles"
    idle_right = idle_sheet
    idle_left = idle_sheet.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
    walk_right = walk_sheet
    walk_left = walk_sheet.transpose(Image.Transpose.FLIP_LEFT_RIGHT)

    idle_right.save(f"{out_dir}\\idle_right.png")
    idle_left.save(f"{out_dir}\\idle_left.png")
    walk_right.save(f"{out_dir}\\walk_right.png")
    walk_left.save(f"{out_dir}\\walk_left.png")

    # Generate showcase
    showcase = Image.new("RGBA", (FRAME_SIZE * 4, FRAME_SIZE * 2), (24, 24, 30, 255))
    showcase.paste(idle_right, (0, 0), idle_right)
    showcase.paste(walk_right, (0, FRAME_SIZE), walk_right)
    showcase.save(r"C:\Users\alame\.gemini\antigravity-ide\brain\39d2fa9e-9b0d-4564-9852-7c140f8d8f57\miles_reference_poses.png")
    print("Exported perfectly!")

if __name__ == "__main__":
    generate_perfect_miles()
