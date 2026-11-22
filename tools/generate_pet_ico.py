import io
import struct
import sys
from pathlib import Path
from PIL import Image, ImageDraw

PROJECT_ROOT = Path(__file__).resolve().parent.parent
assets_dir = PROJECT_ROOT / "assets"
master_jpg = assets_dir / "app_icon_master.jpg"

if not master_jpg.exists():
    pass

im = Image.open(master_jpg).convert("RGBA")
w, h = im.size

# High-quality anti-aliased squircle alpha mask (oversampled 4x)
scale = 4
mask = Image.new("L", (w * scale, h * scale), 0)
d = ImageDraw.Draw(mask)
# Match squircle boundary: [60, 60, 964, 964] with radius 210
d.rounded_rectangle([60 * scale, 60 * scale, 964 * scale, 964 * scale], radius=210 * scale, fill=255)
mask = mask.resize((w, h), Image.Resampling.LANCZOS)

out_rgba = im.copy()
out_rgba.putalpha(mask)

# Save preview PNG for Settings dialog header
preview_png = assets_dir / "desktop_pet_preview.png"
out_rgba.save(preview_png, format="PNG")

def make_perfect_windows_ico(img_rgba: Image.Image) -> bytes:
    """
    Creates a 100% Windows Shell & GDI-compliant multi-resolution ICO file.
    Sizes <= 64x64 are encoded as 32bpp BGRA DIB BMP (native Win32 GDI format).
    Sizes 128x128 and 256x256 are encoded as PNG.
    This prevents any blank squares, icon distortion, or scanline glitches in Windows Explorer.
    """
    sizes = [16, 24, 32, 48, 64, 128, 256]
    entries = []
    image_datas = []

    for sz in sizes:
        resized = img_rgba.resize((sz, sz), Image.Resampling.LANCZOS)
        if sz <= 64:
            # 32bpp uncompressed DIB BMP
            bih = struct.pack('<IIIHHIIIIII',
                40, sz, sz * 2, 1, 32, 0,
                sz * sz * 4, 0, 0, 0, 0
            )
            # Pixels: bottom-up BGRA
            bgra_bytes = bytearray()
            for y in range(sz - 1, -1, -1):
                for x in range(sz):
                    r, g, b, a = resized.getpixel((x, y))
                    bgra_bytes.extend([b, g, r, a])
            
            # AND mask: 1 bit per pixel, row padded to 32 bits (4 bytes)
            row_bytes_len = ((sz + 31) // 32) * 4
            and_mask = bytearray(row_bytes_len * sz)
            data = bih + bytes(bgra_bytes) + bytes(and_mask)
        else:
            # 128 and 256: PNG compressed
            buf = io.BytesIO()
            resized.save(buf, format='PNG')
            data = buf.getvalue()

        image_datas.append(data)
        w_byte = sz if sz < 256 else 0
        h_byte = sz if sz < 256 else 0
        entries.append({
            'w': w_byte,
            'h': h_byte,
            'colors': 0,
            'reserved': 0,
            'planes': 1,
            'bpp': 32,
            'bytes': len(data)
        })

    # Header: 6 bytes
    out = bytearray(struct.pack('<HHH', 0, 1, len(entries)))
    offset = 6 + len(entries) * 16
    for entry in entries:
        out.extend(struct.pack('<BBBBHHII',
            entry['w'], entry['h'], entry['colors'], entry['reserved'],
            entry['planes'], entry['bpp'], entry['bytes'], offset
        ))
        offset += entry['bytes']

    for data in image_datas:
        out.extend(data)

    return bytes(out)

ico_bytes = make_perfect_windows_ico(out_rgba)

app_ico = assets_dir / "app_icon.ico"
desktop_ico = assets_dir / "desktop_pet.ico"

with open(app_ico, "wb") as f:
    f.write(ico_bytes)
with open(desktop_ico, "wb") as f:
    f.write(ico_bytes)

print("Icons generated successfully in all 7 standard Windows resolutions.")
