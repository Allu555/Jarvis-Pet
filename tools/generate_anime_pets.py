"""
Extracts 4x2 chibi reference sheets into 20 animated 192x192 transparent sprite strips
for Gojo Satoru, Naruto Uzumaki, Luffy (Gear 5), and Kyojuro Rengoku.
"""
import math
from collections import deque
from pathlib import Path
from PIL import Image, ImageDraw

FRAME_SIZE = 192
BASE_DIR = Path(__file__).resolve().parent.parent
REF_OUT_DIR = BASE_DIR / "docs" / "images" / "pets"
SPRITES_DIR = BASE_DIR / "assets" / "sprites"


def remove_white_bg_floodfill(im: Image.Image, thresh: int = 232) -> Image.Image:
    """Flood-fills background from cell borders only, preserving white hair/eyes/clothes inside."""
    rgba = im.convert("RGBA")
    w, h = rgba.size
    px = rgba.load()
    visited = bytearray(w * h)
    q = deque()

    def is_bg(r, g, b):
        return r >= thresh and g >= thresh and b >= thresh and max(r, g, b) - min(r, g, b) < 28

    for x in range(w):
        for y in (0, h - 1):
            r, g, b, _ = px[x, y]
            if is_bg(r, g, b):
                idx = y * w + x
                if not visited[idx]:
                    visited[idx] = 1
                    q.append((x, y))
    for y in range(h):
        for x in (0, w - 1):
            r, g, b, _ = px[x, y]
            if is_bg(r, g, b):
                idx = y * w + x
                if not visited[idx]:
                    visited[idx] = 1
                    q.append((x, y))

    while q:
        cx, cy = q.popleft()
        px[cx, cy] = (0, 0, 0, 0)
        for nx, ny in ((cx - 1, cy), (cx + 1, cy), (cx, cy - 1), (cx, cy + 1)):
            if 0 <= nx < w and 0 <= ny < h:
                idx = ny * w + nx
                if not visited[idx]:
                    r, g, b, _ = px[nx, ny]
                    if is_bg(r, g, b):
                        visited[idx] = 1
                        q.append((nx, ny))

    # Soften 1px fringe adjacent to transparent pixels
    for y in range(1, h - 1):
        for x in range(1, w - 1):
            r, g, b, a = px[x, y]
            if a > 0 and r > 210 and g > 210 and b > 210:
                if (
                    px[x - 1, y][3] == 0
                    or px[x + 1, y][3] == 0
                    or px[x, y - 1][3] == 0
                    or px[x, y + 1][3] == 0
                ):
                    px[x, y] = (r, g, b, 110)

    return rgba


def fit_pose(im: Image.Image, target_h: int = 148) -> Image.Image:
    bbox = im.getbbox()
    if not bbox:
        return Image.new("RGBA", (target_h, target_h), (0, 0, 0, 0))
    cropped = im.crop(bbox)
    cw, ch = cropped.size
    scale = min(156.0 / max(1, cw), float(target_h) / max(1, ch))
    nw = max(1, int(round(cw * scale)))
    nh = max(1, int(round(ch * scale)))
    return cropped.resize((nw, nh), Image.Resampling.LANCZOS)


def place_frame(
    pose: Image.Image,
    dx: int = 0,
    dy: int = 0,
    sx: float = 1.0,
    sy: float = 1.0,
    angle: float = 0.0,
    align_bottom: bool = True,
) -> Image.Image:
    im = pose
    if abs(sx - 1.0) > 0.01 or abs(sy - 1.0) > 0.01:
        nw = max(1, int(round(im.width * sx)))
        nh = max(1, int(round(im.height * sy)))
        im = im.resize((nw, nh), Image.Resampling.LANCZOS)
    if abs(angle) > 0.1:
        im = im.rotate(angle, resample=Image.Resampling.BICUBIC, expand=True)

    canvas = Image.new("RGBA", (FRAME_SIZE, FRAME_SIZE), (0, 0, 0, 0))
    ox = (FRAME_SIZE - im.width) // 2 + dx
    oy = (FRAME_SIZE - im.height - 10 + dy) if align_bottom else ((FRAME_SIZE - im.height) // 2 + dy)
    canvas.paste(im, (ox, oy), im)
    return canvas


def make_strip(frames: list) -> Image.Image:
    strip = Image.new("RGBA", (FRAME_SIZE * len(frames), FRAME_SIZE), (0, 0, 0, 0))
    for i, f in enumerate(frames):
        strip.paste(f, (i * FRAME_SIZE, 0), f)
    return strip


def draw_aura_sparks(frame: Image.Image, color: tuple, stage: int, count: int = 6) -> Image.Image:
    out = frame.copy()
    d = ImageDraw.Draw(out)
    for k in range(count):
        ang = (2 * math.pi * k / count) + stage * 0.55
        rad = 56 + 10 * math.sin(stage + k)
        cx = int(FRAME_SIZE // 2 + rad * math.cos(ang))
        cy = int(FRAME_SIZE // 2 + rad * 0.75 * math.sin(ang))
        r = 3 + (k + stage) % 3
        d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(*color[:3], 220))
    return out


def draw_zzz(frame: Image.Image, stage: int) -> Image.Image:
    out = frame.copy()
    d = ImageDraw.Draw(out)
    for i in range(2):
        ox = 128 + i * 14 + (stage % 2) * 3
        oy = 46 - i * 16 - stage * 3
        s = 8 + i * 3
        d.line([(ox, oy), (ox + s, oy), (ox, oy + s), (ox + s, oy + s)], fill=(180, 220, 255, 230), width=2)
    return out


def draw_notes(frame: Image.Image, color: tuple, stage: int) -> Image.Image:
    out = frame.copy()
    d = ImageDraw.Draw(out)
    for i in range(2):
        nx = 36 + i * 110
        ny = 44 + int(6 * math.sin(stage * 1.4 + i * 2.0))
        d.ellipse([nx - 4, ny, nx + 4, ny + 7], fill=(*color[:3], 240))
        d.line([(nx + 3, ny + 3), (nx + 3, ny - 10), (nx + 10, ny - 8)], fill=(*color[:3], 240), width=2)
    return out


def build_pet_sprites(pet_key: str, ref_path: Path, aura_rgb: tuple, bottom_trim_frac: float = 0.0):
    REF_OUT_DIR.mkdir(parents=True, exist_ok=True)
    out_dir = SPRITES_DIR / pet_key
    out_dir.mkdir(parents=True, exist_ok=True)

    sheet = Image.open(ref_path).convert("RGBA")
    sheet.save(REF_OUT_DIR / f"{pet_key}_reference.png", "PNG")

    sw, sh = sheet.size
    cw, ch = sw // 4, sh // 2
    poses = []
    for row in range(2):
        for col in range(4):
            y1 = int((row + 1) * ch - ch * bottom_trim_frac)
            cell = sheet.crop((col * cw, row * ch, (col + 1) * cw, y1))
            clean = remove_white_bg_floodfill(cell)
            poses.append(fit_pose(clean))

    p_idle, p_walk, p_jump, p_sit, p_sleep, p_happy, p_roar, p_music = poses
    p_walk_l = p_walk.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
    p_idle_flip = p_idle.transpose(Image.Transpose.FLIP_LEFT_RIGHT)

    # 6-frame animations
    idle_frames = [place_frame(p_idle, dy=int(-2 * math.sin(i * math.pi / 3)), sy=1.0 + 0.02 * math.sin(i * math.pi / 3)) for i in range(6)]
    make_strip(idle_frames).save(out_dir / "idle.png")
    make_strip([place_frame(p_idle_flip, dy=int(-2 * math.sin(i * math.pi / 3))) for i in range(6)]).save(out_dir / "idle_flip.png")
    make_strip([place_frame(p_idle, sy=0.96 if i == 2 else 1.0) for i in range(6)]).save(out_dir / "blink.png")

    walk_r = [place_frame(p_walk, dy=-abs(int(6 * math.sin(i * math.pi / 3))), angle=3 * math.sin(i * math.pi / 3)) for i in range(6)]
    walk_l = [place_frame(p_walk_l, dy=-abs(int(6 * math.sin(i * math.pi / 3))), angle=-3 * math.sin(i * math.pi / 3)) for i in range(6)]
    make_strip(walk_r).save(out_dir / "walk_right.png")
    make_strip(walk_l).save(out_dir / "walk_left.png")

    jump_frames = [draw_aura_sparks(place_frame(p_jump, dy=-int(16 * math.sin(i * math.pi / 5)), align_bottom=False), aura_rgb, i, 5) for i in range(6)]
    make_strip(jump_frames).save(out_dir / "jump.png")

    roar_frames = [draw_aura_sparks(place_frame(p_roar, sx=1.04 if i % 2 else 1.0, sy=1.04 if i % 2 else 1.0), aura_rgb, i, 8) for i in range(6)]
    make_strip(roar_frames).save(out_dir / "roar.png")

    wake_frames = [place_frame(p_sit if i < 2 else p_idle, dy=-4 if i == 3 else 0) for i in range(6)]
    make_strip(wake_frames).save(out_dir / "wake.png")

    work_frames = [draw_aura_sparks(place_frame(p_sit, dy=-int(2 * (i % 2))), aura_rgb, i, 4) for i in range(6)]
    make_strip(work_frames).save(out_dir / "work.png")

    # 4-frame animations
    make_strip([place_frame(p_jump, dy=i * 3, angle=-6 + i * 3, align_bottom=False) for i in range(4)]).save(out_dir / "fall.png")
    make_strip([place_frame(p_idle, sx=1.08 if i < 2 else 1.0, sy=0.92 if i < 2 else 1.0) for i in range(4)]).save(out_dir / "land.png")
    make_strip([place_frame(p_sit, dy=int(2 * math.sin(i * math.pi / 2))) for i in range(4)]).save(out_dir / "sit.png")
    make_strip([draw_zzz(place_frame(p_sleep, sy=0.97 + 0.03 * (i % 2)), i) for i in range(4)]).save(out_dir / "sleep.png")
    make_strip([place_frame(p_jump, dy=int(4 * math.sin(i * math.pi / 2)), angle=8 * math.sin(i * math.pi / 2), align_bottom=False) for i in range(4)]).save(out_dir / "drag.png")
    make_strip([draw_aura_sparks(place_frame(p_happy, dy=-abs(int(10 * math.sin(i * math.pi / 2)))), (255, 220, 80), i, 5) for i in range(4)]).save(out_dir / "happy.png")
    make_strip([place_frame(p_sit, dy=4, sy=0.94, angle=-3 if i % 2 else 3) for i in range(4)]).save(out_dir / "sad.png")
    make_strip([place_frame(p_sit, dx=-2 if i % 2 else 2, dy=5, sy=0.92) for i in range(4)]).save(out_dir / "cry.png")
    make_strip([draw_notes(place_frame(p_music, dy=-abs(int(6 * math.sin(i * math.pi / 2))), angle=4 * math.sin(i * math.pi / 2)), aura_rgb, i) for i in range(4)]).save(out_dir / "music.png")
    make_strip([draw_aura_sparks(place_frame(p_happy, dy=-4 if i == 1 else 0), (255, 235, 90), i, 4) for i in range(4)]).save(out_dir / "idea.png")
    make_strip([place_frame(p_idle, angle=-5 if i % 2 else 5) for i in range(4)]).save(out_dir / "shrug.png")

    print(f"[OK] Built 20 sprite strips for {pet_key} -> {out_dir}")


if __name__ == "__main__":
    specs = [
        ("gojo", Path(r"C:\Users\alame\.gemini\antigravity\brain\c3a5426e-de13-4bce-9051-4dbb3eefcc22\gojo_reference_1795863308482.jpg"), (130, 190, 255)),
        ("naruto", Path(r"C:\Users\alame\.gemini\antigravity\brain\c3a5426e-de13-4bce-9051-4dbb3eefcc22\naruto_chibi_sprite_sheet_v3_1795863600777.jpg"), (255, 145, 30)),
        ("luffy", Path(r"C:\Users\alame\.gemini\antigravity\brain\c3a5426e-de13-4bce-9051-4dbb3eefcc22\luffy_reference_1795863318321.jpg"), (245, 245, 255)),
        ("rengoku", Path(r"C:\Users\alame\.gemini\antigravity\brain\c3a5426e-de13-4bce-9051-4dbb3eefcc22\rengoku_reference_1795863322767.jpg"), (255, 110, 30)),
    ]
    for key, path, col in specs:
        if path.exists():
            build_pet_sprites(key, path, col)
