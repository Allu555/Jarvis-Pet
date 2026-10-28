from pathlib import Path
from PIL import Image

UPLOAD_PATH = Path(r"C:\Users\alame\.gemini\antigravity-ide\brain\39d2fa9e-9b0d-4564-9852-7c140f8d8f57\.user_uploaded\media_1788672865319.png")
DEST_DIR = Path(__file__).parent / "miles_sources"
DEST_DIR.mkdir(parents=True, exist_ok=True)
DEST_PATH = DEST_DIR / "miles_raw.png"

im = Image.open(UPLOAD_PATH)
print(f"Loaded Miles raw: format={im.format}, size={im.size}, mode={im.mode}")
im.save(DEST_PATH)
print(f"Saved to {DEST_PATH}")
