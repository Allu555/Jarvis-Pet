import pathlib
import numpy as np
from PIL import Image

src_dir = pathlib.Path(r"c:\Users\alame\Downloads\Desktop-Pet-main\Desktop-Pet-main\assets\ghost_spider_sources")
sheet = Image.open(src_dir / "sheet_flood_clean.png").convert("RGBA")

# Bounding boxes for key poses:
poses = {
    # 1. Idle ready stance (bottom left)
    "idle_stance": (30, 780, 180, 955),
    # 2. Standing with web shooter extended (middle right top)
    "work_stand_shooter": (440, 235, 565, 415),
    # 3. Web Gliding / Flying Pose (top right)
    "gliding_flight": (380, 20, 560, 225),
    # 4. Spider-Bot communicator crouching (middle right bottom)
    "spiderbot_comm": (428, 430, 570, 580),
    # 5. Dynamic 3-Point Spider Landing (center)
    "hero_landing": (205, 400, 420, 605),
    # 6. Web Blaster Swing with pink web burst (middle left)
    "web_burst_swing": (0, 570, 225, 800),
    # 7. Spider-Gwen Hooded Mask Icon (middle left top)
    "hood_icon": (35, 220, 165, 365),
    # 8. Gliding Flight Angle 2 (bottom center)
    "gliding_dive": (200, 790, 375, 995),
    # 9. Landing Pose Angle 2 (bottom right)
    "landing_crouch": (380, 795, 570, 985),
}

gallery_items = []
for name, bbox in poses.items():
    cropped = sheet.crop(bbox)
    
    # Tight crop on alpha
    arr = np.array(cropped)
    crop_bbox = Image.fromarray(arr).getbbox()
    if crop_bbox:
        cleaned = Image.fromarray(arr).crop(crop_bbox)
    else:
        cleaned = cropped
        
    save_path = src_dir / f"gwen_{name}.png"
    cleaned.save(save_path)
    print(f"Saved {name}: {cleaned.size} -> {save_path.name}")
    gallery_items.append((name, cleaned))

# Assemble a pose gallery image
gw, gh = 200, 200
cols = 3
rows = (len(gallery_items) + cols - 1) // cols
gallery_img = Image.new("RGBA", (cols * gw, rows * gh), (26, 26, 34, 255))

for i, (pname, pimg) in enumerate(gallery_items):
    col = i % cols
    row = i // cols
    thumb = pimg.copy()
    thumb.thumbnail((170, 170), Image.Resampling.LANCZOS)
    tw, th = thumb.size
    px = col * gw + (gw - tw) // 2
    py = row * gh + (gh - th) // 2
    gallery_img.paste(thumb, (px, py), thumb)

gallery_out = pathlib.Path(r"C:\Users\alame\.gemini\antigravity-ide\brain\39d2fa9e-9b0d-4564-9852-7c140f8d8f57\ghost_spider_poses_gallery.png")
gallery_img.save(gallery_out)
print(f"Saved gallery to {gallery_out}")
