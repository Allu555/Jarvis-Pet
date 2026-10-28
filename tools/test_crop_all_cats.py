from PIL import Image, ImageDraw

img = Image.open('assets/all_cats_clean.png').convert('RGBA')

cell_w, cell_h = 240, 180
grid_img = Image.new('RGBA', (cell_w * 7, cell_h * 4), (25, 25, 35, 255))
draw = ImageDraw.Draw(grid_img)

cat_definitions = [
    {
        'name': 'drip_cat',
        'y_range': (35, 205),
        'slices': [
            ('idle', (0, 130)),
            ('walk_1', (130, 260)),
            ('walk_2', (260, 380)),
            ('walk_3', (380, 488)),
            ('walk_4', (488, 588)),
            ('work', (588, 815)),
            ('sleep', (815, 1024))
        ]
    },
    {
        'name': 'gamer_cat',
        'y_range': (205, 375),
        'slices': [
            ('idle', (0, 138)),
            ('walk_1', (138, 268)),
            ('walk_2', (268, 395)),
            ('walk_3', (395, 515)),
            ('walk_4', (515, 608)),
            ('work', (608, 810)),
            ('sleep', (810, 1024))
        ]
    },
    {
        'name': 'cyber_cat',
        'y_range': (375, 530),
        'slices': [
            ('idle', (0, 130)),
            ('walk_1', (130, 275)),
            ('walk_2', (275, 395)),
            ('walk_3', (395, 508)),
            ('walk_4', (508, 605)),
            ('work', (605, 815)),
            ('sleep', (815, 1024))
        ]
    },
    {
        'name': 'explorer_cat',
        'y_range': (530, 682),
        'slices': [
            ('idle', (0, 142)),
            ('walk_1', (142, 290)),
            ('walk_2', (290, 420)),
            ('walk_3', (420, 565)),
            ('walk_4', (420, 565)), # Explorer has 3 walk poses; walk_4 can be walk_2 or walk_3 for 4-frame cycle
            ('work', (565, 815)),
            ('sleep', (815, 1024))
        ]
    }
]

for r_idx, cdata in enumerate(cat_definitions):
    y1, y2 = cdata['y_range']
    cname = cdata['name']
    for c_idx, (sname, (x1, x2)) in enumerate(cdata['slices']):
        crop_img = img.crop((x1, y1, x2, y2))
        bb = crop_img.getbbox()
        if bb:
            trimmed = crop_img.crop(bb)
            tw, th = trimmed.size
            sc = min(1.0, (cell_w - 20) / tw, (cell_h - 30) / th)
            if sc < 1.0:
                trimmed = trimmed.resize((int(tw * sc), int(th * sc)), Image.Resampling.LANCZOS)
                tw, th = trimmed.size
            cx = c_idx * cell_w + (cell_w - tw) // 2
            cy = r_idx * cell_h + (cell_h - 20 - th) // 2 + 15
            grid_img.paste(trimmed, (cx, cy), trimmed)
        
        draw.text((c_idx * cell_w + 10, r_idx * cell_h + 5), f"{cname}:{sname}", fill=(200, 200, 200, 255))
        draw.rectangle([c_idx * cell_w, r_idx * cell_h, (c_idx + 1) * cell_w - 1, (r_idx + 1) * cell_h - 1], outline=(60, 60, 80, 255))

grid_path = r'C:\Users\alame\.gemini\antigravity-ide\brain\39d2fa9e-9b0d-4564-9852-7c140f8d8f57\test_slices_grid.png'
grid_img.save(grid_path)
print('Saved updated inspection grid to:', grid_path)
