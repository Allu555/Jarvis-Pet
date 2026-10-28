from pathlib import Path
from PIL import Image

ARTIFACTS_DIR = Path(r"C:\Users\alame\.gemini\antigravity-ide\brain\9c8acd29-534c-4785-8252-1cf94fd344bc")
SPRITES_DIR = Path(r"c:\Users\alame\Downloads\Desktop-Pet-main\Desktop-Pet-main\assets\sprites\goku")

def make_gif_from_strip(strip_path: Path, out_path: Path, fps: int = 10):
    if not strip_path.exists():
        return
    sheet = Image.open(strip_path).convert("RGBA")
    h = sheet.height
    n_frames = sheet.width // h
    frames = []
    for i in range(n_frames):
        crop = sheet.crop((i * h, 0, (i + 1) * h, h))
        bg = Image.new("RGBA", (h, h), (24, 28, 42, 255))
        bg.paste(crop, (0, 0), crop)
        frames.append(bg)
        
    duration = int(1000 / fps)
    frames[0].save(
        out_path,
        save_all=True,
        append_images=frames[1:],
        duration=duration,
        loop=0,
        optimize=True
    )
    print(f"Generated GIF: {out_path}")

def generate_previews():
    make_gif_from_strip(SPRITES_DIR / "walk_right.png", ARTIFACTS_DIR / "goku_walk_preview.gif", fps=10)
    make_gif_from_strip(SPRITES_DIR / "roar.png", ARTIFACTS_DIR / "goku_kamehameha_preview.gif", fps=8)
    make_gif_from_strip(SPRITES_DIR / "jump.png", ARTIFACTS_DIR / "goku_nimbus_jump_preview.gif", fps=6)
    make_gif_from_strip(SPRITES_DIR / "happy.png", ARTIFACTS_DIR / "goku_victory_preview.gif", fps=6)

if __name__ == "__main__":
    generate_previews()
