"""
bake_sprites.py - Embeds all 3D Spider sprites as base64 data URIs into index.html
"""
import base64
from pathlib import Path

SPRITES_DIR = Path(__file__).parent / "sprites"
INDEX_PATH = Path(__file__).parent / "index.html"

sprites = {}
for f in sorted(SPRITES_DIR.glob("*.png")):
    b64 = base64.b64encode(f.read_bytes()).decode("ascii")
    sprites[f.stem] = f"data:image/png;base64,{b64}"

js_obj_lines = []
for name, uri in sprites.items():
    js_obj_lines.append(f'    "{name}": "{uri}"')

js_block = "const SPRITE_DATA = {\n" + ",\n".join(js_obj_lines) + "\n};"

# Write standalone file
out = Path(__file__).parent / "sprite_data.js"
out.write_text(js_block, encoding="utf-8")
print(f"Written: {out}  ({out.stat().st_size // 1024} KB)")

