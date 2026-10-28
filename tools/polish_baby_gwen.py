import pathlib
import numpy as np
from PIL import Image

src_dir = pathlib.Path(r"c:\Users\alame\Downloads\Desktop-Pet-main\Desktop-Pet-main\assets\gwen_sources")

def polish_gwen_image(img_path, trim_top_px=0):
    img = Image.open(img_path).convert("RGBA")
    arr = np.array(img)
    rgb = arr[:, :, :3]
    alpha = arr[:, :, 3]
    
    r = rgb[:, :, 0].astype(np.int32)
    g = rgb[:, :, 1].astype(np.int32)
    b = rgb[:, :, 2].astype(np.int32)
    
    # White / light grey surfaces (grid lines on white mask/hood)
    is_light = (r > 185) & (g > 185) & (b > 185)
    is_neutral = (np.abs(r - g) < 25) & (np.abs(g - b) < 25)
    white_surface = (alpha > 50) & is_light & is_neutral
    
    arr[white_surface, 0] = 255
    arr[white_surface, 1] = 255
    arr[white_surface, 2] = 255
    
    if trim_top_px > 0:
        arr[:trim_top_px, :, 3] = 0
        
    res = Image.fromarray(arr)
    bbox = res.getbbox()
    if bbox:
        res = res.crop(bbox)
    return res

standing_polished = polish_gwen_image(src_dir / "gwen_standing_clean.png")
standing_polished.save(src_dir / "gwen_standing_perfect.png")
print(f"Saved standing perfect: {standing_polished.size}")

swinging_polished = polish_gwen_image(src_dir / "gwen_swinging_clean.png", trim_top_px=22)
swinging_polished.save(src_dir / "gwen_swinging_perfect.png")
print(f"Saved swinging perfect: {swinging_polished.size}")
