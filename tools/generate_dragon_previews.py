from pathlib import Path
from PIL import Image

ARTIFACTS_DIR = Path(r"C:\Users\alame\.gemini\antigravity-ide\brain\9c8acd29-534c-4785-8252-1cf94fd344bc")
SPRITES_DIR = Path(r"c:\Users\alame\Downloads\Desktop-Pet-main\Desktop-Pet-main\assets\sprites\dragon")

def make_gif_from_strip(strip_path: Path, out_path: Path, fps: int = 10):
    if not strip_path.exists():
        return
    sheet = Image.open(strip_path).convert("RGBA")
    h = sheet.height
    n_frames = sheet.width // h
    frames = []
    for i in range(n_frames):
        crop = sheet.crop((i * h, 0, (i + 1) * h, h))
        # Add slight dark background to make the alpha pop in markdown viewer
        bg = Image.new("RGBA", (h, h), (25, 30, 42, 255))
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
    make_gif_from_strip(SPRITES_DIR / "idle.png", ARTIFACTS_DIR / "dragon_idle_preview.gif", fps=6)
    make_gif_from_strip(SPRITES_DIR / "walk_right.png", ARTIFACTS_DIR / "dragon_flight_preview.gif", fps=10)
    make_gif_from_strip(SPRITES_DIR / "roar.png", ARTIFACTS_DIR / "dragon_fire_roar_preview.gif", fps=8)
    make_gif_from_strip(SPRITES_DIR / "work.png", ARTIFACTS_DIR / "dragon_treasure_hoard_preview.gif", fps=6)

if __name__ == "__main__":
    generate_previews()
