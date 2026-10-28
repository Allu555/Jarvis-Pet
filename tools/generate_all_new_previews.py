import sys
from pathlib import Path
from PIL import Image

PREVIEW_DIR = Path(r"C:\Users\alame\.gemini\antigravity-ide\brain\9c8acd29-534c-4785-8252-1cf94fd344bc")
SPRITE_DIR = Path(__file__).parent / "sprites"
FRAME_SIZE = 192


def make_gif(sprite_path: Path, out_path: Path, duration: int = 120):
    if not sprite_path.exists():
        return
    sheet = Image.open(sprite_path).convert("RGBA")
    n = sheet.width // FRAME_SIZE
    frames = []
    for i in range(n):
        crop = sheet.crop((i * FRAME_SIZE, 0, (i + 1) * FRAME_SIZE, FRAME_SIZE))
        # Composite over a nice modern checkerboard
        bg = Image.new("RGBA", (FRAME_SIZE, FRAME_SIZE), (28, 32, 42, 255))
        bg.paste(crop, (0, 0), crop)
        frames.append(bg.convert("P", palette=Image.ADAPTIVE))
    if frames:
        frames[0].save(
            out_path,
            save_all=True,
            append_images=frames[1:],
            duration=duration,
            loop=0,
            disposal=2
        )
        print(f"Generated preview: {out_path.name}")


def generate_previews():
    make_gif(SPRITE_DIR / "batman_cat" / "walk_right.png", PREVIEW_DIR / "batman_cat_walk_preview.gif", 100)
    make_gif(SPRITE_DIR / "batman_cat" / "jump.png", PREVIEW_DIR / "batman_cat_pounce_preview.gif", 140)
    make_gif(SPRITE_DIR / "batman_cat" / "roar.png", PREVIEW_DIR / "batman_cat_hiss_preview.gif", 140)

    make_gif(SPRITE_DIR / "nezuko" / "walk_right.png", PREVIEW_DIR / "nezuko_walk_preview.gif", 100)
    make_gif(SPRITE_DIR / "nezuko" / "roar.png", PREVIEW_DIR / "nezuko_flame_preview.gif", 140)
    make_gif(SPRITE_DIR / "nezuko" / "music.png", PREVIEW_DIR / "nezuko_tiny_dance_preview.gif", 120)

    make_gif(SPRITE_DIR / "zenitsu" / "walk_right.png", PREVIEW_DIR / "zenitsu_walk_preview.gif", 90)
    make_gif(SPRITE_DIR / "zenitsu" / "roar.png", PREVIEW_DIR / "zenitsu_thunder_preview.gif", 120)

    make_gif(SPRITE_DIR / "inosuke" / "walk_right.png", PREVIEW_DIR / "inosuke_charge_preview.gif", 90)
    make_gif(SPRITE_DIR / "inosuke" / "roar.png", PREVIEW_DIR / "inosuke_slash_preview.gif", 120)

    make_gif(SPRITE_DIR / "akaza" / "walk_right.png", PREVIEW_DIR / "akaza_walk_preview.gif", 100)
    make_gif(SPRITE_DIR / "akaza" / "roar.png", PREVIEW_DIR / "akaza_compass_preview.gif", 120)


if __name__ == "__main__":
    generate_previews()
