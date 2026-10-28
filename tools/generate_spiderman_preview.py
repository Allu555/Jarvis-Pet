from pathlib import Path
from PIL import Image

SPRITE_DIR = Path(__file__).parent / "sprites" / "spiderman"
OUT_PREVIEW = Path(__file__).parent / "spiderman_all_animations_preview.png"

def make_preview():
    anim_names = [
        "idle", "idle_flip", "walk_right", "walk_left", "jump", "fall", "land", "drag",
        "sleep", "wake", "work", "happy", "idea", "roar", "sit", "music", "eat", "blink", "cry", "shrug"
    ]
    
    rows = []
    max_w = 0
    for name in anim_names:
        p = SPRITE_DIR / f"{name}.png"
        if p.exists():
            im = Image.open(p)
            rows.append((name, im))
            if im.width > max_w:
                max_w = im.width
                
    total_h = len(rows) * (192 + 20) + 40
    total_w = max_w + 40
    
    canvas = Image.new("RGBA", (total_w, total_h), (25, 28, 36, 255))
    y = 20
    for name, im in rows:
        canvas.paste(im, (20, y), im)
        y += 192 + 20
        
    canvas.save(OUT_PREVIEW)
    print(f"Generated complete preview at {OUT_PREVIEW} ({canvas.size})")

if __name__ == "__main__":
    make_preview()
