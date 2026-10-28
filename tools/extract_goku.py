from PIL import Image
from pathlib import Path

SRC_IMG = Path(r"C:\Users\alame\.gemini\antigravity-ide\brain\9c8acd29-534c-4785-8252-1cf94fd344bc\.user_uploaded\media_1788612968634.png")
DEST_DIR = Path(r"c:\Users\alame\Downloads\Desktop-Pet-main\Desktop-Pet-main\assets\goku_sources")
DEST_DIR.mkdir(parents=True, exist_ok=True)
OUT_FILE = DEST_DIR / "goku_cutout.png"

def prepare_goku():
    img = Image.open(SRC_IMG).convert("RGBA")
    bbox = img.getbbox()
    if bbox:
        img = img.crop(bbox)
    img.save(OUT_FILE, "PNG")
    print(f"Saved Goku cutout: {OUT_FILE} with size {img.size}")

if __name__ == "__main__":
    prepare_goku()
