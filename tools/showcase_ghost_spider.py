import pathlib
from PIL import Image

sp_dir = pathlib.Path(r"c:\Users\alame\Downloads\Desktop-Pet-main\Desktop-Pet-main\assets\sprites\ghost_spider")
FRAME_SIZE = 128

poses = [
    ("1. Idle Breathing", sp_dir / "idle_right.png"),
    ("2. Walking Stride", sp_dir / "walk_right.png"),
    ("3. Gliding Jump", sp_dir / "jump.png"),
    ("4. Hero Landing", sp_dir / "land.png"),
    ("5. Spider-Bot Comm", sp_dir / "work.png"),
    ("6. Web Burst Blast", sp_dir / "roar.png"),
]

showcase = Image.new("RGBA", (FRAME_SIZE * 4, FRAME_SIZE * len(poses)), (24, 24, 32, 255))

for idx, (label, img_path) in enumerate(poses):
    if img_path.exists():
        sheet = Image.open(img_path).convert("RGBA")
        # take first 4 frames
        sub = sheet.crop((0, 0, min(sheet.width, FRAME_SIZE * 4), FRAME_SIZE))
        showcase.paste(sub, (0, idx * FRAME_SIZE), sub)

out_showcase = pathlib.Path(r"C:\Users\alame\.gemini\antigravity-ide\brain\39d2fa9e-9b0d-4564-9852-7c140f8d8f57\ghost_spider_animation_showcase.png")
showcase.save(out_showcase)
print(f"Saved animation showcase to {out_showcase}")
