import math
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ARTIFACTS_DIR = Path(r"C:\Users\alame\.gemini\antigravity-ide\brain\9c8acd29-534c-4785-8252-1cf94fd344bc")
ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
ASSETS_DIR = Path(__file__).parent / "dragon_options"
ASSETS_DIR.mkdir(parents=True, exist_ok=True)

W, H = 512, 512

def create_chibi_dragon() -> Image.Image:
    """Style 1: Cute Chibi Baby Night Dragon"""
    img = Image.new("RGBA", (W, H), (24, 28, 44, 255))
    draw = ImageDraw.Draw(img)
    
    # Background soft aura
    for r in range(180, 0, -10):
        alpha = int(25 * (1 - r / 180))
        draw.ellipse([256 - r, 260 - r, 256 + r, 260 + r], fill=(70, 50, 120, alpha))
        
    # Tail
    tail_pts = [(280, 360), (360, 380), (410, 340), (400, 310), (370, 330), (300, 340)]
    draw.polygon(tail_pts, fill=(45, 52, 78))
    # Tail spade / flame
    spade = [(410, 340), (440, 315), (430, 355), (415, 360)]
    draw.polygon(spade, fill=(80, 210, 190))

    # Wings (Cute baby wings)
    # Left wing
    draw.polygon([(170, 240), (70, 160), (120, 230), (140, 270)], fill=(38, 44, 66))
    draw.polygon([(80, 170), (125, 235), (150, 260)], fill=(65, 180, 165))
    # Right wing
    draw.polygon([(340, 240), (440, 160), (390, 230), (370, 270)], fill=(38, 44, 66))
    draw.polygon([(430, 170), (385, 235), (360, 260)], fill=(65, 180, 165))

    # Cute chubby body
    draw.ellipse([180, 250, 332, 420], fill=(45, 52, 78))
    # Belly (soft cyan/mint)
    draw.ellipse([210, 280, 302, 405], fill=(75, 195, 180))
    # Belly ridges
    for by in [310, 340, 370]:
        draw.line([(225, by), (287, by)], fill=(45, 140, 130), width=3)

    # Feet
    draw.ellipse([165, 380, 235, 435], fill=(38, 44, 66))
    draw.ellipse([277, 380, 347, 435], fill=(38, 44, 66))
    # Cute claws
    for fx in [180, 198, 216]:
        draw.ellipse([fx, 422, fx+8, 438], fill=(230, 240, 250))
    for fx in [292, 310, 328]:
        draw.ellipse([fx, 422, fx+8, 438], fill=(230, 240, 250))

    # Large Chibi Head
    draw.ellipse([160, 120, 352, 290], fill=(45, 52, 78))
    
    # Cute little horns
    draw.polygon([(185, 140), (145, 75), (210, 125)], fill=(80, 210, 190))
    draw.polygon([(327, 140), (367, 75), (302, 125)], fill=(80, 210, 190))
    # Inner ear/horn detail
    draw.polygon([(188, 135), (155, 90), (202, 125)], fill=(140, 240, 225))
    draw.polygon([(324, 135), (357, 90), (310, 125)], fill=(140, 240, 225))

    # Big expressive anime eyes
    # Left eye
    draw.ellipse([190, 175, 245, 245], fill=(15, 20, 30))
    draw.ellipse([195, 180, 240, 240], fill=(40, 220, 160))
    draw.ellipse([200, 185, 235, 235], fill=(10, 80, 60))
    draw.ellipse([202, 188, 218, 204], fill=(255, 255, 255)) # Sparkle 1
    draw.ellipse([222, 216, 232, 226], fill=(255, 255, 255)) # Sparkle 2

    # Right eye
    draw.ellipse([267, 175, 322, 245], fill=(15, 20, 30))
    draw.ellipse([272, 180, 317, 240], fill=(40, 220, 160))
    draw.ellipse([277, 185, 312, 235], fill=(10, 80, 60))
    draw.ellipse([279, 188, 295, 204], fill=(255, 255, 255))
    draw.ellipse([299, 216, 309, 226], fill=(255, 255, 255))

    # Cute cheeks blush
    draw.ellipse([175, 230, 205, 246], fill=(255, 120, 160, 120))
    draw.ellipse([307, 230, 337, 246], fill=(255, 120, 160, 120))

    # Cute smiling mouth & little fang
    draw.arc([236, 232, 276, 256], 10, 170, fill=(20, 25, 35), width=3)
    draw.polygon([(252, 244), (258, 253), (264, 244)], fill=(255, 255, 255))

    # Sparkles in air
    draw.polygon([(110, 120), (115, 110), (120, 120), (130, 125), (120, 130), (115, 140), (110, 130), (100, 125)], fill=(120, 240, 220))
    draw.polygon([(390, 100), (393, 92), (396, 100), (404, 103), (396, 106), (393, 114), (390, 106), (382, 103)], fill=(255, 220, 120))

    return img


def create_inferno_dragon() -> Image.Image:
    """Style 2: Fierce Mythical Inferno Dragon"""
    img = Image.new("RGBA", (W, H), (30, 15, 15, 255))
    draw = ImageDraw.Draw(img)

    # Volcanic glow
    for r in range(220, 0, -15):
        alpha = int(35 * (1 - r / 220))
        draw.ellipse([256 - r, 256 - r, 256 + r, 256 + r], fill=(255, 80, 20, alpha))

    # Massive Spiky Wings
    # Left Wing
    w1 = [(200, 240), (40, 90), (110, 130), (70, 180), (130, 200), (100, 250), (180, 270)]
    draw.polygon(w1, fill=(160, 25, 15))
    draw.line([(200, 240), (40, 90)], fill=(220, 60, 30), width=6)
    draw.line([(40, 90), (110, 130)], fill=(220, 60, 30), width=4)
    draw.line([(40, 90), (70, 180)], fill=(220, 60, 30), width=4)

    # Right Wing
    w2 = [(312, 240), (472, 90), (402, 130), (442, 180), (382, 200), (412, 250), (332, 270)]
    draw.polygon(w2, fill=(160, 25, 15))
    draw.line([(312, 240), (472, 90)], fill=(220, 60, 30), width=6)
    draw.line([(472, 90), (402, 130)], fill=(220, 60, 30), width=4)
    draw.line([(472, 90), (442, 180)], fill=(220, 60, 30), width=4)

    # Muscular Armored Body
    draw.polygon([(200, 240), (312, 240), (330, 380), (280, 420), (232, 420), (182, 380)], fill=(120, 20, 15))
    # Golden magma chest plates
    chest = [(236, 260), (276, 260), (290, 310), (276, 360), (236, 360), (222, 310)]
    draw.polygon(chest, fill=(245, 160, 20))
    for cy in [285, 315, 345]:
        draw.line([(230, cy), (282, cy)], fill=(180, 40, 10), width=3)

    # Powerful Hind Legs & Claws
    draw.ellipse([160, 350, 230, 430], fill=(95, 15, 10))
    draw.ellipse([282, 350, 352, 430], fill=(95, 15, 10))
    # Sharp Obsidian Talons
    for tx in [165, 185, 205]:
        draw.polygon([(tx, 420), (tx+6, 440), (tx+12, 420)], fill=(20, 20, 20))
    for tx in [287, 307, 327]:
        draw.polygon([(tx, 420), (tx+6, 440), (tx+12, 420)], fill=(20, 20, 20))

    # Fierce Dragon Head & Horns
    # Majestic Horns
    draw.polygon([(210, 160), (130, 70), (190, 140)], fill=(230, 190, 50))
    draw.polygon([(302, 160), (382, 70), (322, 140)], fill=(230, 190, 50))
    draw.polygon([(195, 175), (145, 130), (190, 165)], fill=(190, 140, 30))
    draw.polygon([(317, 175), (367, 130), (322, 165)], fill=(190, 140, 30))

    # Head shape (Snout & Jaw)
    head_poly = [(210, 150), (302, 150), (325, 200), (300, 250), (212, 250), (187, 200)]
    draw.polygon(head_poly, fill=(140, 25, 18))
    # Snout
    draw.polygon([(225, 190), (287, 190), (275, 240), (237, 240)], fill=(170, 35, 22))

    # Glowing Flame Eyes
    draw.polygon([(215, 185), (242, 180), (238, 195), (218, 195)], fill=(255, 230, 50))
    draw.polygon([(297, 185), (270, 180), (274, 195), (294, 195)], fill=(255, 230, 50))
    draw.ellipse([228, 184, 234, 192], fill=(255, 50, 0))
    draw.ellipse([278, 184, 284, 192], fill=(255, 50, 0))

    # Fire breath & sparks
    for fx, fy, fr in [(256, 250, 18), (256, 268, 28), (256, 290, 20), (240, 275, 12), (272, 275, 12)]:
        draw.ellipse([fx-fr, fy-fr, fx+fr, fy+fr], fill=(255, 180, 20, 180))
        draw.ellipse([fx-fr//2, fy-fr//2, fx+fr//2, fy+fr//2], fill=(255, 245, 180, 220))

    # Spikes along spine
    for sy in [120, 140, 160, 260, 285, 310, 335]:
        draw.polygon([(250, sy), (256, sy-14), (262, sy)], fill=(240, 180, 30))

    return img


def create_celestial_dragon() -> Image.Image:
    """Style 3: Serpentine Celestial Eastern Shenron Dragon"""
    img = Image.new("RGBA", (W, H), (16, 28, 32, 255))
    draw = ImageDraw.Draw(img)

    # Celestial mist aura
    for r in range(210, 0, -15):
        alpha = int(30 * (1 - r / 210))
        draw.ellipse([256 - r, 256 - r, 256 + r, 256 + r], fill=(20, 160, 140, alpha))

    # Swirling Serpentine S-Curve Body
    body_segments = [
        (380, 390, 28), (340, 420, 32), (280, 430, 35), (220, 410, 36),
        (160, 360, 36), (130, 300, 38), (140, 230, 40), (180, 180, 42),
        (250, 160, 44), (320, 180, 44), (370, 230, 42), (380, 300, 40),
        (340, 350, 38), (280, 360, 38), (230, 340, 38), (200, 290, 40)
    ]
    
    # Draw body coils (Jade Green)
    for bx, by, br in body_segments:
        draw.ellipse([bx - br, by - br, bx + br, by + br], fill=(22, 120, 95))
        # Inner golden underbelly highlights
        draw.ellipse([bx - br + 8, by - br + 8, bx + br - 8, by + br - 8], fill=(35, 160, 125))

    # Flowing Emerald Dorsal Mane / Fur
    for bx, by, br in body_segments:
        draw.polygon([(bx, by-br), (bx-12, by-br-22), (bx+12, by-br-22)], fill=(60, 215, 170))

    # Celestial Dragon Head (Focal Point)
    hx, hy = 256, 170
    draw.ellipse([hx-55, hy-45, hx+55, hy+45], fill=(28, 145, 115))
    
    # Golden Stag Antlers
    draw.line([(hx-25, hy-35), (hx-65, hy-105)], fill=(240, 195, 50), width=6)
    draw.line([(hx-45, hy-70), (hx-80, hy-80)], fill=(240, 195, 50), width=4)
    draw.line([(hx-55, hy-90), (hx-40, hy-115)], fill=(240, 195, 50), width=4)

    draw.line([(hx+25, hy-35), (hx+65, hy-105)], fill=(240, 195, 50), width=6)
    draw.line([(hx+45, hy-70), (hx+80, hy-80)], fill=(240, 195, 50), width=4)
    draw.line([(hx+55, hy-90), (hx+40, hy-115)], fill=(240, 195, 50), width=4)

    # Snout & Whiskers
    draw.polygon([(hx-35, hy-10), (hx+35, hy-10), (hx+25, hy+40), (hx-25, hy+40)], fill=(35, 165, 130))
    # Long Majestic Whiskers
    whisk_l = [(hx-30, hy+20), (hx-80, hy+40), (hx-130, hy+20), (hx-170, hy+60)]
    whisk_r = [(hx+30, hy+20), (hx+80, hy+40), (hx+130, hy+20), (hx+170, hy+60)]
    for i in range(len(whisk_l)-1):
        draw.line([whisk_l[i], whisk_l[i+1]], fill=(255, 230, 120), width=3)
        draw.line([whisk_r[i], whisk_r[i+1]], fill=(255, 230, 120), width=3)

    # Wise Glowing Golden Eyes
    draw.ellipse([hx-35, hy-15, hx-12, hy+8], fill=(255, 220, 60))
    draw.ellipse([hx+12, hy-15, hx+35, hy+8], fill=(255, 220, 60))
    draw.ellipse([hx-26, hy-10, hx-20, hy+3], fill=(20, 40, 30))
    draw.ellipse([hx+20, hy-10, hx+26, hy+3], fill=(20, 40, 30))

    # Floating Celestial Dragon Pearl / Orb
    ox, oy = 256, 290
    for r in range(45, 0, -5):
        alpha = int(45 * (1 - r / 45))
        draw.ellipse([ox-r, oy-r, ox+r, oy+r], fill=(255, 210, 80, alpha))
    draw.ellipse([ox-24, oy-24, ox+24, oy+24], fill=(255, 245, 180))
    draw.ellipse([ox-18, oy-18, ox+18, oy+18], fill=(255, 255, 240))
    # Swirling energy rings around orb
    draw.arc([ox-34, oy-18, ox+34, oy+18], 0, 360, fill=(120, 240, 210), width=3)

    return img


def create_pixel_dragon() -> Image.Image:
    """Style 4: 16-Bit Retro Pixel Art Dragon"""
    # Create at small 32x32 pixel canvas, then upscale without blurring
    pw, ph = 32, 32
    pimg = Image.new("RGBA", (pw, ph), (0, 0, 0, 0))
    pdraw = ImageDraw.Draw(pimg)

    # Pixel Palette
    c_out = (20, 15, 30, 255)       # Outline
    c_body = (130, 50, 190, 255)    # Purple scale body
    c_light = (180, 90, 240, 255)   # Light highlight
    c_belly = (245, 210, 70, 255)   # Yellow belly
    c_horn = (255, 170, 40, 255)    # Gold horns
    c_wing = (220, 80, 120, 255)    # Magenta wing web
    c_eye = (60, 240, 180, 255)     # Cyan eye

    # Outline / Wings
    for pt in [(6, 8), (7, 7), (8, 6), (9, 7), (10, 8), (11, 9), (10, 11), (9, 13), (8, 14), (7, 13)]:
        pimg.putpixel(pt, c_out)
    for x in range(7, 10):
        for y in range(8, 12):
            pimg.putpixel((x, y), c_wing)

    for pt in [(21, 9), (22, 8), (23, 7), (24, 6), (25, 7), (26, 8), (25, 11), (24, 13), (23, 14)]:
        pimg.putpixel(pt, c_out)
    for x in range(22, 25):
        for y in range(8, 12):
            pimg.putpixel((x, y), c_wing)

    # Body fill
    for y in range(14, 26):
        for x in range(10, 22):
            pimg.putpixel((x, y), c_body)

    # Tail
    for pt in [(6, 24), (7, 24), (8, 25), (9, 25), (5, 23), (4, 22), (3, 22)]:
        pimg.putpixel(pt, c_body)
    pimg.putpixel((2, 21), c_horn)
    pimg.putpixel((3, 20), c_horn)

    # Belly
    for y in range(16, 24):
        for x in range(13, 19):
            pimg.putpixel((x, y), c_belly)

    # Head
    for y in range(8, 15):
        for x in range(11, 23):
            pimg.putpixel((x, y), c_body)
    for y in range(9, 13):
        for x in range(12, 22):
            pimg.putpixel((x, y), c_light)

    # Horns
    pimg.putpixel((12, 6), c_horn)
    pimg.putpixel((13, 7), c_horn)
    pimg.putpixel((20, 6), c_horn)
    pimg.putpixel((19, 7), c_horn)

    # Big retro eyes
    pimg.putpixel((14, 10), c_eye)
    pimg.putpixel((15, 10), (255, 255, 255, 255))
    pimg.putpixel((19, 10), c_eye)
    pimg.putpixel((20, 10), (255, 255, 255, 255))

    # Feet
    for pt in [(11, 26), (12, 26), (13, 26), (18, 26), (19, 26), (20, 26)]:
        pimg.putpixel(pt, c_out)

    # Scale to 512x512 with Nearest Neighbor for crisp pixel look
    try:
        resample_nearest = Image.Resampling.NEAREST
        resample_lanczos = Image.Resampling.LANCZOS
    except AttributeError:
        resample_nearest = Image.NEAREST
        resample_lanczos = getattr(Image, "LANCZOS", getattr(Image, "ANTIALIAS", Image.BICUBIC))

    scaled = pimg.resize((W, H), resample_nearest)
    
    # Add retro game border & backdrop
    bg = Image.new("RGBA", (W, H), (20, 22, 34, 255))
    # Grid pattern
    gdraw = ImageDraw.Draw(bg)
    for gx in range(0, W, 32):
        gdraw.line([(gx, 0), (gx, H)], fill=(28, 32, 48), width=1)
    for gy in range(0, H, 32):
        gdraw.line([(0, gy), (W, gy)], fill=(28, 32, 48), width=1)

    bg.paste(scaled, (0, 0), scaled)
    return bg


def generate_all_showcase():
    s1 = create_chibi_dragon()
    s2 = create_inferno_dragon()
    s3 = create_celestial_dragon()
    s4 = create_pixel_dragon()

    try:
        resample_lanczos = Image.Resampling.LANCZOS
    except AttributeError:
        resample_lanczos = getattr(Image, "LANCZOS", getattr(Image, "ANTIALIAS", Image.BICUBIC))

    s1.save(ASSETS_DIR / "style_1_chibi.png")
    s2.save(ASSETS_DIR / "style_2_inferno.png")
    s3.save(ASSETS_DIR / "style_3_celestial.png")
    s4.save(ASSETS_DIR / "style_4_pixel.png")

    s1.save(ARTIFACTS_DIR / "style_1_chibi.png")
    s2.save(ARTIFACTS_DIR / "style_2_inferno.png")
    s3.save(ARTIFACTS_DIR / "style_3_celestial.png")
    s4.save(ARTIFACTS_DIR / "style_4_pixel.png")

    # Make 2x2 Showcase collage (1080x1140)
    collage = Image.new("RGBA", (1080, 1140), (15, 18, 26, 255))
    cdraw = ImageDraw.Draw(collage)

    # Titles banner
    # Add 4 style cards
    cards = [
        (s1, 30, 40, "Option 1: Cute Chibi / Anime Dragon"),
        (s2, 550, 40, "Option 2: Fierce Inferno Wyvern"),
        (s3, 30, 580, "Option 3: Celestial Jade Shenron"),
        (s4, 550, 580, "Option 4: 16-Bit Retro Pixel Dragon"),
    ]

    for cimg, cx, cy, label in cards:
        # border card
        cdraw.rectangle([cx-6, cy-6, cx+496, cy+526], fill=(35, 40, 58), outline=(70, 85, 120))
        # resize preview to 490x460
        thumb = cimg.resize((490, 460), resample_lanczos)
        collage.paste(thumb, (cx, cy), thumb)
        # label area
        cdraw.rectangle([cx, cy+465, cx+490, cy+520], fill=(22, 26, 38))
        cdraw.text((cx + 15, cy + 480), label, fill=(240, 245, 255))

    collage.save(ASSETS_DIR / "dragon_styles_showcase.png")
    collage.save(ARTIFACTS_DIR / "dragon_styles_showcase.png")
    print("Generated all dragon style previews successfully!")

if __name__ == "__main__":
    generate_all_showcase()
