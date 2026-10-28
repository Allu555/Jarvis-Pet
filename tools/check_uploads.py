from pathlib import Path
from PIL import Image

UPLOAD_DIR = Path(r"C:\Users\alame\.gemini\antigravity-ide\brain\39d2fa9e-9b0d-4564-9852-7c140f8d8f57\.user_uploaded")
DEST_DIR = Path(r"c:\Users\alame\Downloads\Desktop-Pet-main\Desktop-Pet-main\assets\spiderman_sources")
DEST_DIR.mkdir(parents=True, exist_ok=True)

for p in UPLOAD_DIR.glob("*.*"):
    try:
        im = Image.open(p)
        print(f"File: {p.name}, format: {im.format}, size: {im.size}, mode: {im.mode}")
        # Save as spiderman_raw.png if it's the high-res spiderman image
        if "1788671420005" in p.name:
            im.save(DEST_DIR / "spiderman_raw.png")
            print(f"Saved {p.name} as {DEST_DIR / 'spiderman_raw.png'}")
        elif "1788671797315" in p.name:
            im.save(DEST_DIR / "spiderman_raw_thumb.jpg")
    except Exception as e:
        print(f"Error reading {p}: {e}")
