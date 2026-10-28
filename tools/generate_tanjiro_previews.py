from pathlib import Path
from PIL import Image

ARTIFACTS_DIR = Path(r"C:\Users\alame\.gemini\antigravity-ide\brain\9c8acd29-534c-4785-8252-1cf94fd344bc")
SPRITE_DIR = Path(__file__).parent / "sprites" / "tanjiro"


def make_gif(sheet_path: Path, out_path: Path, duration: int = 100):
    sheet = Image.open(sheet_path)
    fh = sheet.height
    n = sheet.width // fh
    frames = []
    for i in range(n):
        crop = sheet.crop((i * fh, 0, (i + 1) * fh, fh))
        frames.append(crop)
    if frames:
        frames[0].save(
            out_path,
            save_all=True,
            append_images=frames[1:],
            duration=duration,
            loop=0,
            disposal=2,
            transparency=0,
        )
        print(f"Saved {out_path.name}")


def generate_previews():
    make_gif(SPRITE_DIR / "walk_right.png", ARTIFACTS_DIR / "tanjiro_walk_preview.gif", duration=120)
    make_gif(SPRITE_DIR / "roar.png", ARTIFACTS_DIR / "tanjiro_water_dragon_preview.gif", duration=140)
    make_gif(SPRITE_DIR / "work.png", ARTIFACTS_DIR / "tanjiro_onigiri_preview.gif", duration=160)
    make_gif(SPRITE_DIR / "jump.png", ARTIFACTS_DIR / "tanjiro_jump_preview.gif", duration=120)


if __name__ == "__main__":
    generate_previews()
