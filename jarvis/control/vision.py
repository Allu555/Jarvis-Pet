"""
control/vision.py – Next-Generation Screen Perception & Localization Engine for JARVIS.

Strategy: Cheapest and most accurate method first, escalate only on failure.
  Layer 1 - Windows UIAutomation:
    Reads control tree of foreground window (name, role, bounding box, enabled state).
    Fuzzy-matches target name with RapidFuzz. Caches the tree for 1.0 second.
    Extracts COM control references for zero-coordinate direct pattern invocation.
  Layer 2 - Active Window Cropped OCR:
    Crops to the active window rectangle (with multi-monitor offset awareness).
    Upscales small text regions with bicubic interpolation.
    Runs offline Windows Native OCR (winsdk.windows.media.ocr).
    Fuzzy word/phrase matching with contextual & positional ranking.
  Layer 3 - Set-of-Marks (SoM) Vision Grounding:
    Combines candidate interactive bounding boxes (UIA + OCR + visual contours).
    Overlays bright numbered label badges ([1], [2], [3]...).
    Queries NVIDIA Vision NIM: "Which number [N] is <target>?"
    Maps selected mark number back to physical screen coordinates (0 coordinate hallucination).

Correctness Essentials:
  - Per-Monitor v2 DPI awareness.
  - Fast screenshots via mss with fallback to PyAutoGUI.
  - Structured output: {"found": bool, "x": int, "y": int, "bbox": tuple, "confidence": float, "method": str, "name": str}
  - Multi-match disambiguation ("first video", "second button", "third link").
  - "describe_screen" and "read_screen_text" tools.
"""

import asyncio
import base64
import ctypes
from ctypes import wintypes
import io
import json
import logging
import re
import time
from typing import Any

import numpy as np
import pyautogui          # type: ignore
from PIL import Image, ImageDraw, ImageFont # type: ignore
from openai import OpenAI # type: ignore
from rapidfuzz import fuzz # type: ignore

try:
    import mss           # type: ignore
    HAS_MSS = True
except ImportError:
    HAS_MSS = False

from config import NVIDIA_API_KEY, NVIDIA_BASE_URL, NVIDIA_VISION_MODEL
from control.keyboard_mouse import ensure_desktop_attached

logger = logging.getLogger("jarvis.control.vision")

# ─── DPI Awareness Setup (Per-Monitor v2) ─────────────────────────────────────
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception:
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass

_client = OpenAI(api_key=NVIDIA_API_KEY, base_url=NVIDIA_BASE_URL)

# ─── Visual Laser Scan Callback Hook ─────────────────────────────────────────
_scan_overlay_callback = None

def set_scan_overlay_callback(cb):
    global _scan_overlay_callback
    _scan_overlay_callback = cb

def trigger_scan_animation(target_x=None, target_y=None, label=""):
    if _scan_overlay_callback:
        try:
            _scan_overlay_callback(target_x, target_y, label)
        except Exception:
            pass

# ─── Ordinal Word Parsing ──────────────────────────────────────────────────────
ORDINALS = {
    "first": 0, "1st": 0, "one": 0,
    "second": 1, "2nd": 1, "two": 1,
    "third": 2, "3rd": 2, "three": 2,
    "fourth": 3, "4th": 3, "four": 3,
    "fifth": 4, "5th": 4, "five": 4,
    "last": -1, "bottom": -1,
}


def _extract_ordinal(text: str) -> tuple[int, str]:
    """Check if query specifies an ordinal like 'first video' or '2nd button'."""
    tokens = text.lower().split()
    target_idx = 0
    clean_tokens = []
    for t in tokens:
        if t in ORDINALS:
            target_idx = ORDINALS[t]
        else:
            clean_tokens.append(t)
    return target_idx, " ".join(clean_tokens).strip()


# ─── Fast Screenshot Helper ───────────────────────────────────────────────────

def get_active_window_rect() -> tuple[int, int, int, int]:
    """
    Get (left, top, right, bottom) of the active foreground window.
    Falls back to primary monitor bounds if unable to retrieve.
    """
    ensure_desktop_attached()
    try:
        user32 = ctypes.windll.user32
        hwnd = user32.GetForegroundWindow()
        if hwnd:
            rect = wintypes.RECT()
            if user32.GetWindowRect(hwnd, ctypes.byref(rect)):
                w = rect.right - rect.left
                h = rect.bottom - rect.top
                if w > 50 and h > 50:
                    return (rect.left, rect.top, rect.right, rect.bottom)
    except Exception as e:
        logger.debug(f"Could not get active window rect: {e}")

    sw, sh = pyautogui.size()
    return (0, 0, sw, sh)


def capture_screen_image(region: tuple[int, int, int, int] | None = None) -> tuple[Image.Image, int, int]:
    """
    Fast screen capture using mss with fallback to PyAutoGUI.
    region: (left, top, right, bottom) or None for full primary monitor.
    Returns: (PIL Image, offset_x, offset_y)
    """
    ensure_desktop_attached()
    offset_x, offset_y = 0, 0

    if region:
        left, top, right, bottom = region
        width = max(1, right - left)
        height = max(1, bottom - top)
        offset_x, offset_y = left, top
    else:
        left, top = 0, 0
        sw, sh = pyautogui.size()
        width, height = sw, sh

    if HAS_MSS:
        try:
            with mss.MSS() as sct:
                # Capture specified box
                shot = sct.grab({"left": left, "top": top, "width": width, "height": height})
                img = Image.frombytes("RGB", shot.size, shot.bgra, "raw", "BGRX")
                return img, offset_x, offset_y
        except Exception as e:
            logger.debug(f"MSS grab failed ({e}), falling back to PyAutoGUI…")

    try:
        if region:
            img = pyautogui.screenshot(region=(left, top, width, height))
        else:
            img = pyautogui.screenshot()
        return img, offset_x, offset_y
    except Exception as e:
        logger.warning(f"Screenshot capture failed: {e}")
        sw, sh = pyautogui.size()
        return Image.new("RGB", (sw, sh), color=(0, 0, 0)), 0, 0


def _take_screenshot(region: tuple[int, int, int, int] | None = None) -> tuple[Image.Image, str, int, int]:
    """Compatibility helper returning (img, base64_str, offset_x, offset_y)."""
    img, off_x, off_y = capture_screen_image(region)
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=85)
    b64 = base64.b64encode(buf.getvalue()).decode("utf-8")
    return img, b64, off_x, off_y


# ─── Layer 1: UIAutomation Control Tree (1s Cached + Fuzzy Matching) ──────────

_uia_cache: dict[str, Any] = {
    "timestamp": 0.0,
    "hwnd": 0,
    "elements": [],
}


def _refresh_uia_tree(max_depth: int = 7) -> list[dict[str, Any]]:
    """Traverse foreground window control tree and cache elements for 1.0 second."""
    now = time.time()
    try:
        user32 = ctypes.windll.user32
        fg_hwnd = user32.GetForegroundWindow()
    except Exception:
        fg_hwnd = 0

    if _uia_cache["elements"] and (now - _uia_cache["timestamp"] < 1.0) and (_uia_cache["hwnd"] == fg_hwnd):
        return _uia_cache["elements"]

    elements = []
    try:
        import uiautomation as uia
        fg_ctrl = uia.GetFocusedControl()
        top_ctrl = fg_ctrl.GetTopLevelControl() if fg_ctrl else None
        if not top_ctrl:
            top_ctrl = uia.GetRootControl()

        if top_ctrl:
            for ctrl, depth in uia.WalkControl(top_ctrl, maxDepth=max_depth):
                try:
                    name = (ctrl.Name or "").strip()
                    c_type = ctrl.ControlTypeName or ""
                    rect = ctrl.BoundingRectangle
                    if not rect or rect.width() < 8 or rect.height() < 8:
                        continue
                    cx = (rect.left + rect.right) // 2
                    cy = (rect.top + rect.bottom) // 2
                    if cx <= 5 or cy <= 5:
                        continue

                    elements.append({
                        "name": name,
                        "type": c_type,
                        "x": cx,
                        "y": cy,
                        "bbox": (rect.left, rect.top, rect.right, rect.bottom),
                        "enabled": getattr(ctrl, "IsEnabled", True),
                        "ctrl": ctrl,
                    })
                except Exception:
                    continue
    except Exception as e:
        logger.debug(f"UIAutomation tree walk error: {e}")

    _uia_cache["timestamp"] = now
    _uia_cache["hwnd"] = fg_hwnd
    _uia_cache["elements"] = elements
    return elements


def uia_find_element(description: str) -> dict[str, Any] | None:
    """
    Layer 1: Find interactive element using UIAutomation tree cache with RapidFuzz.
    Supports ordinals ('first video', 'second button').
    Returns structured dict or None.
    """
    ord_idx, clean_query = _extract_ordinal(description)
    q_lower = clean_query.lower().strip()
    if not q_lower:
        q_lower = description.lower().strip()

    elements = _refresh_uia_tree()
    if not elements:
        return None

    # Filter candidates with fuzzy matching
    candidates = []
    for el in elements:
        name = el["name"].lower()
        if not name and el["type"].lower() not in ("edit", "button", "hyperlink"):
            continue

        score = 0.0
        if q_lower == name:
            score = 100.0
        elif q_lower in name:
            score = 85.0
        else:
            score = float(fuzz.token_set_ratio(q_lower, name))

        # Boost interactive controls (Buttons, Edits, Links)
        c_type = el["type"].lower()
        if any(t in c_type for t in ("button", "edit", "hyperlink", "menuitem", "tabitem", "listitem")):
            score += 10.0

        if score >= 65.0:
            candidates.append((score, el))

    if not candidates:
        return None

    # Sort candidates: highest score first, then top-to-bottom on screen
    candidates.sort(key=lambda item: (-item[0], item[1]["y"], item[1]["x"]))

    # Handle ordinals
    if ord_idx < len(candidates):
        chosen = candidates[ord_idx][1]
    else:
        chosen = candidates[0][1]

    logger.info(f"Layer 1 (UIA) matched {chosen['name']!r} ({chosen['type']}) at ({chosen['x']}, {chosen['y']})")
    return {
        "found": True,
        "x": chosen["x"],
        "y": chosen["y"],
        "bbox": chosen["bbox"],
        "confidence": 0.95,
        "method": "uia",
        "name": chosen["name"],
        "ctrl": chosen["ctrl"],
    }


# ─── Layer 2: Cropped Active Window OCR (Windows Native OCR) ─────────────────

def ocr_find_text_on_screen(description: str) -> dict[str, Any] | None:
    """
    Layer 2: Fast Windows Native OCR cropped to active window with upscaling.
    Extracts word & line boxes with fuzzy matching and positional scoring.
    """
    ord_idx, clean_query = _extract_ordinal(description)
    q_lower = clean_query.lower().strip()
    if not q_lower:
        q_lower = description.lower().strip()

    stopwords = {"the", "a", "an", "button", "link", "icon", "on", "in", "play", "click", "song", "video"}
    keywords = [w for w in re.sub(r"[^a-zA-Z0-9\s]", "", q_lower).split() if w not in stopwords and len(w) > 1]
    if not keywords:
        keywords = [w for w in q_lower.split() if len(w) > 1]

    try:
        import winsdk.windows.media.ocr as win_ocr
        import winsdk.windows.graphics.imaging as imaging
        import winsdk.windows.storage.streams as streams

        # Crop to active window for speed & accuracy
        win_rect = get_active_window_rect()
        crop_img, off_x, off_y = capture_screen_image(region=win_rect)

        # Upscale small images / active window for sharp character recognition
        w, h = crop_img.width, crop_img.height
        scale_factor = 1.5 if (w < 1200 or h < 800) else 1.0
        if scale_factor > 1.0:
            proc_img = crop_img.resize((int(w * scale_factor), int(h * scale_factor)), Image.BICUBIC)
        else:
            proc_img = crop_img

        buf = io.BytesIO()
        proc_img.save(buf, format="PNG")
        data = buf.getvalue()

        async def _run():
            writer = streams.DataWriter()
            writer.write_bytes(data)
            ibuf = writer.detach_buffer()

            stream = streams.InMemoryRandomAccessStream()
            await stream.write_async(ibuf)
            stream.seek(0)

            decoder = await imaging.BitmapDecoder.create_async(stream)
            software_bitmap = await decoder.get_software_bitmap_async()

            engine = win_ocr.OcrEngine.try_create_from_user_profile_languages()
            res = await engine.recognize_async(software_bitmap)

            is_header_search = any(w in q_lower for w in ("search", "address", "url", "tab", "title", "input", "box"))
            candidates = []

            for line in res.lines:
                l_text = line.text.lower()
                # 1. Full phrase or line match
                line_score = float(fuzz.partial_ratio(q_lower, l_text))
                if (q_lower in l_text or line_score >= 75.0) and line.words:
                    min_x = min(w.bounding_rect.x for w in line.words) / scale_factor
                    max_x = max(w.bounding_rect.x + w.bounding_rect.width for w in line.words) / scale_factor
                    min_y = min(w.bounding_rect.y for w in line.words) / scale_factor
                    max_y = max(w.bounding_rect.y + w.bounding_rect.height for w in line.words) / scale_factor
                    cx = int((min_x + max_x) / 2) + off_x
                    cy = int((min_y + max_y) / 2) + off_y
                    score = line_score + 20.0
                    if not is_header_search and (cy - off_y) >= 120:
                        score += 30.0
                    elif is_header_search and (cy - off_y) < 140:
                        score += 30.0
                    candidates.append((score, cx, cy, (int(min_x + off_x), int(min_y + off_y), int(max_x + off_x), int(max_y + off_y)), line.text))

                # 2. Word-level matches
                for word in line.words:
                    w_clean = re.sub(r"[^a-zA-Z0-9]", "", word.text).lower()
                    if len(w_clean) < 2:
                        continue
                    m_score = 0.0
                    if any(kw == w_clean for kw in keywords):
                        m_score = 70.0
                    else:
                        for kw in keywords:
                            sim = fuzz.ratio(kw, w_clean)
                            if sim > 80:
                                m_score = max(m_score, sim * 0.75)

                    if m_score > 0:
                        rx = word.bounding_rect.x / scale_factor
                        ry = word.bounding_rect.y / scale_factor
                        rw = word.bounding_rect.width / scale_factor
                        rh = word.bounding_rect.height / scale_factor
                        cx = int(rx + rw / 2) + off_x
                        cy = int(ry + rh / 2) + off_y
                        if not is_header_search and (cy - off_y) >= 120:
                            m_score += 25.0
                        candidates.append((m_score, cx, cy, (int(rx + off_x), int(ry + off_y), int(rx + rw + off_x), int(ry + rh + off_y)), word.text))

            if not candidates:
                return None

            # Sort: highest score first, then top-to-bottom on screen
            candidates.sort(key=lambda c: (-c[0], c[2], c[1]))

            # Disambiguate ordinals
            chosen = candidates[ord_idx] if ord_idx < len(candidates) else candidates[0]
            logger.info(f"Layer 2 (OCR) matched {chosen[4]!r} at ({chosen[1]}, {chosen[2]}) score={chosen[0]:.1f}")
            return {
                "found": True,
                "x": chosen[1],
                "y": chosen[2],
                "bbox": chosen[3],
                "confidence": min(0.95, chosen[0] / 120.0),
                "method": "ocr",
                "name": chosen[4],
                "ctrl": None,
            }

        return asyncio.run(_run())
    except Exception as e:
        logger.debug(f"Layer 2 OCR failed: {e}")
        return None


# ─── Layer 3: Set-of-Marks (SoM) Vision Grounding ─────────────────────────────

def _collect_candidate_marks(crop_img: Image.Image, off_x: int, off_y: int) -> list[tuple[int, int, int, int]]:
    """
    Extract candidate clickable bounding boxes using UIAutomation elements +
    OCR word boxes + connected component visual contours.
    """
    boxes = []

    # 1. Candidate boxes from cached UIA elements in this crop region
    for el in _refresh_uia_tree():
        bx1, by1, bx2, by2 = el["bbox"]
        # Convert to crop-local coordinates
        lx1, ly1 = bx1 - off_x, by1 - off_y
        lx2, ly2 = bx2 - off_x, by2 - off_y
        if 0 <= lx1 < crop_img.width and 0 <= ly1 < crop_img.height:
            w, h = lx2 - lx1, ly2 - ly1
            if 14 <= w <= crop_img.width * 0.9 and 14 <= h <= crop_img.height * 0.8:
                boxes.append((int(lx1), int(ly1), int(lx2), int(ly2)))

    # 2. Visual contour regions using scipy.ndimage
    try:
        from scipy import ndimage
        arr = np.array(crop_img.convert("L"))
        # Edge/gradient thresholding for distinct buttons & cards
        grad = np.abs(np.gradient(arr.astype(np.float32), axis=0)) + np.abs(np.gradient(arr.astype(np.float32), axis=1))
        mask = grad > 25.0
        labeled, num_features = ndimage.label(mask)
        if num_features > 0:
            objects = ndimage.find_objects(labeled)
            for slc in objects[:50]:
                if slc:
                    y_slc, x_slc = slc
                    w = x_slc.stop - x_slc.start
                    h = y_slc.stop - y_slc.start
                    if 20 <= w <= 400 and 16 <= h <= 150:
                        boxes.append((x_slc.start, y_slc.start, x_slc.stop, y_slc.stop))
    except Exception:
        pass

    # Non-maximum suppression / pruning of heavily overlapping boxes
    pruned = []
    for b in boxes:
        bx1, by1, bx2, by2 = b
        overlap = False
        for p in pruned:
            px1, py1, px2, py2 = p
            # Calculate Intersection over Area
            ix1, iy1 = max(bx1, px1), max(by1, py1)
            ix2, iy2 = min(bx2, px2), min(by2, py2)
            if ix1 < ix2 and iy1 < iy2:
                inter_area = (ix2 - ix1) * (iy2 - iy1)
                b_area = (bx2 - bx1) * (by2 - by1)
                if b_area > 0 and (inter_area / b_area) > 0.65:
                    overlap = True
                    break
        if not overlap:
            pruned.append(b)
        if len(pruned) >= 35:
            break

    return pruned


def som_vision_grounding(description: str) -> dict[str, Any] | None:
    """
    Layer 3: Set-of-Marks visual grounding. Overlays numbered badges on candidates
    and asks the vision model for the mark index. Maps back to screen coordinates.
    """
    try:
        win_rect = get_active_window_rect()
        crop_img, off_x, off_y = capture_screen_image(region=win_rect)

        # Scale down for LLM tokens (max dimension 1280px)
        orig_w, orig_h = crop_img.width, crop_img.height
        max_dim = 1280
        ratio = min(1.0, max_dim / max(orig_w, orig_h))
        scaled_w = int(orig_w * ratio)
        scaled_h = int(orig_h * ratio)

        som_img = crop_img.resize((scaled_w, scaled_h), Image.LANCZOS)
        draw = ImageDraw.Draw(som_img)

        # Collect candidate marks in local image space
        raw_boxes = _collect_candidate_marks(crop_img, off_x, off_y)
        if not raw_boxes:
            return None

        mark_map: dict[int, tuple[int, int, int, int]] = {}
        for idx, (lx1, ly1, lx2, ly2) in enumerate(raw_boxes, start=1):
            sx1, sy1 = int(lx1 * ratio), int(ly1 * ratio)
            sx2, sy2 = int(lx2 * ratio), int(ly2 * ratio)

            # Draw vibrant colored bounding box
            draw.rectangle([sx1, sy1, sx2, sy2], outline=(0, 230, 255), width=2)
            # Draw badge tag
            tag = f"[{idx}]"
            tag_w = len(tag) * 9 + 4
            tag_y1 = max(0, sy1 - 18)
            draw.rectangle([sx1, tag_y1, sx1 + tag_w, tag_y1 + 18], fill=(0, 230, 255))
            draw.text((sx1 + 2, tag_y1 + 1), tag, fill=(0, 0, 0))

            # Store original screen-space center
            cx = int((lx1 + lx2) / 2) + off_x
            cy = int((ly1 + ly2) / 2) + off_y
            mark_map[idx] = (cx, cy, lx1 + off_x, ly1 + off_y)

        # Encode SoM image to JPEG Base64
        buf = io.BytesIO()
        som_img.save(buf, format="JPEG", quality=85)
        b64 = base64.standard_b64encode(buf.getvalue()).decode("utf-8")

        prompt = (
            f"You are looking at a desktop application screenshot overlaid with numbered green/cyan bounding boxes: [1], [2], [3]...\n"
            f"Find the element corresponding to: '{description}'.\n"
            f"Output ONLY a JSON object: {{\"mark\": <number>}} (e.g. {{\"mark\": 3}}).\n"
            f"If the element is not found, output {{\"mark\": null}}."
        )

        response = _client.chat.completions.create(
            model=NVIDIA_VISION_MODEL,
            max_tokens=256,
            temperature=0.0,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}},
                        {"type": "text", "text": prompt},
                    ],
                }
            ],
        )

        msg = response.choices[0].message
        raw_resp = (getattr(msg, "content", "") or getattr(msg, "reasoning_content", "") or "").strip()
        mark_idx = None
        try:
            parsed = json.loads(re.search(r"\{.*?\}", raw_resp, re.DOTALL).group(0))
            mark_val = parsed.get("mark")
            if mark_val is not None:
                mark_idx = int(mark_val)
        except Exception:
            # Fallback regex extraction e.g. "[3]" or "mark: 3"
            m = re.search(r"(?:mark[\"':\s]+|\[)(\d{1,2})", raw_resp, re.IGNORECASE)
            if m:
                mark_idx = int(m.group(1))

        if mark_idx and mark_idx in mark_map:
            cx, cy, bx, by = mark_map[mark_idx]
            logger.info(f"Layer 3 (Set-of-Marks) selected [{mark_idx}] for '{description}' at ({cx}, {cy})")
            return {
                "found": True,
                "x": cx,
                "y": cy,
                "bbox": (bx, by, bx + 50, by + 30),
                "confidence": 0.88,
                "method": "som_vision",
                "name": f"Mark [{mark_idx}]",
                "ctrl": None,
            }
    except Exception as e:
        logger.debug(f"Layer 3 SoM grounding error: {e}")

    return None


# ─── Color Connected Components (Media Play Buttons & Icons) ─────────────────

def detect_play_button(near_x: int | None = None, near_y: int | None = None) -> tuple[int, int] | None:
    """
    Find the Spotify green circular play button via color mask.
    Optionally prioritizes the button closest to (near_x, near_y) if multiple are visible.
    """
    try:
        from scipy import ndimage
        ensure_desktop_attached()
        crop_img, off_x, off_y = capture_screen_image()
        arr = np.array(crop_img)

        # Spotify vibrant green (#1db954 / #1ed760) mask
        mask = (arr[:, :, 0] < 60) & (arr[:, :, 1] > 170) & (arr[:, :, 2] < 150)
        labeled, num_features = ndimage.label(mask)
        if num_features == 0:
            return None

        sw, sh = pyautogui.size()
        blobs = []
        for i in range(1, num_features + 1):
            ys, xs = np.where(labeled == i)
            # A true Spotify play button is a large green circle with area >= 250 px
            if len(xs) >= 250:
                cx, cy = int(np.mean(xs)) + off_x, int(np.mean(ys)) + off_y
                w = int(np.max(xs) - np.min(xs))
                h = int(np.max(ys) - np.min(ys))
                aspect = min(w, h) / max(w, h) if max(w, h) > 0 else 0
                # Filter to viewport (ignore titlebar cy < 110, bottom player bar cy > sh - 100, sidebar cx < 55)
                # and circular aspect ratio (aspect >= 0.70, width and height >= 25)
                if 55 <= cx <= sw - 80 and 110 <= cy <= sh - 100 and aspect >= 0.70 and w >= 25 and h >= 25:
                    blobs.append((len(xs), aspect, cx, cy, w, h))

        if not blobs:
            return None

        if near_x is not None and near_y is not None:
            # Sort by proximity to the hovered position
            blobs.sort(key=lambda b: ((b[2] - near_x) ** 2 + (b[3] - near_y) ** 2))
        else:
            # Sort by pixel area then aspect ratio
            blobs.sort(key=lambda b: (-b[0], -b[1]))

        best_blob = blobs[0]
        cx, cy = best_blob[2], best_blob[3]
        logger.info(f"Green Play Button detected at ({cx}, {cy}) [area={best_blob[0]}, aspect={best_blob[1]:.2f}]")
        return cx, cy
    except Exception as e:
        logger.debug(f"Play button color detection error: {e}")
    return None


# ─── Unified Element Localization Pipeline ────────────────────────────────────

def find_element_structured(description: str) -> dict[str, Any]:
    """
    Tiered Perception Strategy: Cheapest and most accurate method first, escalate only on failure.
      1. Color / Media Heuristic (for play/song buttons)
      2. Layer 1: UIAutomation Control Tree (offline, 0ms, exact bounding boxes)
      3. Layer 2: Cropped Active Window OCR (high-speed offline text localization)
      4. Layer 3: Set-of-Marks Vision Grounding (numbered badges + vision model)
    Returns: {"found": bool, "x": int, "y": int, "bbox": tuple, "confidence": float, "method": str, "name": str}
    """
    ensure_desktop_attached()
    d_clean = description.lower().strip()

    # 1. Color / Media detector for songs & play buttons
    if any(w in d_clean for w in ("play", "song", "track", "green button")):
        play_pt = detect_play_button()
        if play_pt:
            return {
                "found": True,
                "x": play_pt[0],
                "y": play_pt[1],
                "bbox": (play_pt[0] - 15, play_pt[1] - 15, play_pt[0] + 15, play_pt[1] + 15),
                "confidence": 0.98,
                "method": "color_detector",
                "name": "Play Button",
                "ctrl": None,
            }

    # 2. Layer 1: UI Automation
    uia_res = uia_find_element(description)
    if uia_res:
        return uia_res

    # 3. Layer 2: Windows Native OCR
    ocr_res = ocr_find_text_on_screen(description)
    if ocr_res:
        return ocr_res

    # 4. Layer 3: Set-of-Marks Vision Grounding
    som_res = som_vision_grounding(description)
    if som_res:
        return som_res

    # 5. Positional fallback heuristics
    sw, sh = pyautogui.size()
    pos_map = {
        "center": (sw // 2, sh // 2),
        "middle": (sw // 2, sh // 2),
        "top left": (sw // 6, sh // 6),
        "top right": (sw * 5 // 6, sh // 6),
        "bottom left": (sw // 6, sh * 5 // 6),
        "bottom right": (sw * 5 // 6, sh * 5 // 6),
    }
    for pos_key, coords in pos_map.items():
        if pos_key in d_clean:
            return {
                "found": True,
                "x": coords[0],
                "y": coords[1],
                "bbox": (coords[0] - 20, coords[1] - 20, coords[0] + 20, coords[1] + 20),
                "confidence": 0.50,
                "method": "positional_heuristic",
                "name": pos_key,
                "ctrl": None,
            }

    return {
        "found": False,
        "x": 0,
        "y": 0,
        "bbox": (0, 0, 0, 0),
        "confidence": 0.0,
        "method": "none",
        "name": "",
        "ctrl": None,
    }


def find_element_coords(description: str) -> tuple[int, int] | None:
    """Convenience wrapper returning (x, y) coordinates or None."""
    res = find_element_structured(description)
    if res["found"] and res["x"] > 10 and res["y"] > 10:
        return res["x"], res["y"]
    return None


# ─── Screen Inspection Tools: Describe Screen & Read This ─────────────────────

def describe_screen() -> str:
    """
    Summarize what's on screen: foreground application, visible titles, and layout
    combining active window UIA context + NVIDIA Vision.
    """
    ensure_desktop_attached()
    # Gather foreground window title and UIA context
    win_rect = get_active_window_rect()
    crop_img, off_x, off_y = capture_screen_image(region=win_rect)

    # Encode crop for Vision NIM
    orig_w, orig_h = crop_img.width, crop_img.height
    max_dim = 1280
    ratio = min(1.0, max_dim / max(orig_w, orig_h))
    scaled_img = crop_img.resize((int(orig_w * ratio), int(orig_h * ratio)), Image.LANCZOS)

    buf = io.BytesIO()
    scaled_img.save(buf, format="JPEG", quality=85)
    b64 = base64.standard_b64encode(buf.getvalue()).decode("utf-8")

    try:
        trigger_scan_animation(label="Screen Perception")
        response = _client.chat.completions.create(
            model=NVIDIA_VISION_MODEL,
            max_tokens=400,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}},
                        {
                            "type": "text",
                            "text": (
                                "Describe what is currently on the screen in 2-3 concise sentences. "
                                "Identify the active application, main visible content, and any prominent buttons or text."
                            ),
                        },
                    ],
                }
            ],
        )
        msg = response.choices[0].message
        desc = (getattr(msg, "content", "") or getattr(msg, "reasoning_content", "") or "").strip()
        if desc:
            return desc
        return f"Active window captured (dimensions: {crop_img.width}x{crop_img.height})."
    except Exception as e:
        logger.warning(f"Vision model error in describe_screen: {e}")
        return f"Active window captured (dimensions: {crop_img.width}x{crop_img.height})."


def read_screen_text(target: str = "") -> str:
    """
    Read visible text on the active window aloud or format it using Windows Native OCR.
    If target is specified, extracts text matching or near that region.
    """
    ensure_desktop_attached()
    try:
        import winsdk.windows.media.ocr as win_ocr
        import winsdk.windows.graphics.imaging as imaging
        import winsdk.windows.storage.streams as streams

        win_rect = get_active_window_rect()
        crop_img, off_x, off_y = capture_screen_image(region=win_rect)

        buf = io.BytesIO()
        crop_img.save(buf, format="PNG")
        data = buf.getvalue()

        async def _run():
            writer = streams.DataWriter()
            writer.write_bytes(data)
            ibuf = writer.detach_buffer()

            stream = streams.InMemoryRandomAccessStream()
            await stream.write_async(ibuf)
            stream.seek(0)

            decoder = await imaging.BitmapDecoder.create_async(stream)
            software_bitmap = await decoder.get_software_bitmap_async()

            engine = win_ocr.OcrEngine.try_create_from_user_profile_languages()
            res = await engine.recognize_async(software_bitmap)

            lines = [line.text.strip() for line in res.lines if line.text.strip()]
            if not lines:
                return "No readable text detected in the active window, sir."

            if target:
                t_lower = target.lower()
                matched = [l for l in lines if t_lower in l.lower() or fuzz.partial_ratio(t_lower, l.lower()) > 70]
                if matched:
                    return "\n".join(matched[:8])

            return "\n".join(lines[:15])

        return asyncio.run(_run())
    except Exception as e:
        logger.debug(f"read_screen_text error: {e}")
        return f"Unable to read text from active window: {e}"


# ─── High-Level Action Helpers ────────────────────────────────────────────────

def click_element_by_description(description: str) -> str:
    """
    Locate and click any element on the screen using UIA -> OCR -> SoM Vision.
    Directly invokes UIA pattern if available for zero-coordinate robustness.
    """
    trigger_scan_animation(label=f"Scanning: {description}")
    res = find_element_structured(description)
    if not res["found"]:
        return f"Could not accurately locate '{description}' on the screen, sir."

    cx, cy = res["x"], res["y"]
    trigger_scan_animation(target_x=cx, target_y=cy, label=description)

    # Direct UIA Invoke pattern execution if supported
    ctrl = res.get("ctrl")
    if ctrl:
        try:
            import uiautomation as uia
            if hasattr(ctrl, "GetInvokePattern"):
                inv = ctrl.GetInvokePattern()
                if inv:
                    inv.Invoke()
                    logger.info(f"Direct UIA InvokePattern executed on {res['name']!r}")
                    return f"Invoked '{res['name']}' directly via UIAutomation."
        except Exception as e:
            logger.debug(f"Direct UIA invoke fell back to mouse click: {e}")

    from control.keyboard_mouse import click as km_click, double_click as km_double_click
    # Double-click is only for table rows/files, NEVER for play buttons or toggle buttons
    if any(w in description.lower() for w in ("song row", "track row", "file", "folder")) and not any(b in description.lower() for b in ("button", "btn", "play", "toggle", "icon")):
        km_double_click(cx, cy)
    else:
        km_click(cx, cy)

    return f"Clicked '{description}' at ({cx}, {cy}) via {res['method']}."


def click_and_type(description: str, text: str, press_enter: bool = True) -> str:
    """Find a UI element, click/focus it, type text into it, and optionally press Enter."""
    res = find_element_structured(description)
    if not res["found"]:
        return f"Could not locate '{description}' to enter text, sir."

    ctrl = res.get("ctrl")
    # If control supports ValuePattern, set text directly without typing delay
    if ctrl:
        try:
            if hasattr(ctrl, "GetValuePattern"):
                vp = ctrl.GetValuePattern()
                if vp:
                    vp.SetValue(text)
                    logger.info(f"Set value directly on {res['name']!r} via UIA ValuePattern")
                    if press_enter:
                        from control.keyboard_mouse import press_single_key
                        press_single_key("enter")
                    return f"Typed '{text}' into '{description}' directly via UIAutomation."
        except Exception:
            pass

    from control.keyboard_mouse import click as km_click, type_text, press_single_key
    km_click(res["x"], res["y"])
    time.sleep(0.08)
    type_text(text)
    if press_enter:
        time.sleep(0.06)
        press_single_key("enter")

    return f"Focused '{description}', entered '{text}'" + (", and pressed Enter." if press_enter else ".")


def drag_by_description(start_description: str, end_description: str) -> str:
    """Find start and end UI elements on screen and drag smoothly from start to end."""
    p1 = find_element_coords(start_description)
    if not p1:
        return f"Could not locate '{start_description}' to start dragging, sir."

    p2 = find_element_coords(end_description)
    if not p2:
        return f"Found '{start_description}', but could not locate destination '{end_description}', sir."

    from control.keyboard_mouse import drag
    drag(p1[0], p1[1], p2[0], p2[1])
    return f"Successfully dragged '{start_description}' to '{end_description}'."
