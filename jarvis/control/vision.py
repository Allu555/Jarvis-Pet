"""
control/vision.py – Ultra-accurate Screen Perception & Localization Engine.

Uses a 3-tier hybrid perception pipeline:
  Tier 1: Windows Native OCR (offline, 0ms latency, exact pixel bounding boxes)
  Tier 2: Windows UIAutomation (accessible native buttons, menus, edit boxes)
  Tier 3: NVIDIA Vision NIM (for unlabelled visual elements, with (0,0) rejection)
"""

import asyncio
import base64
import io
import json
import logging
import re
from io import BytesIO

import pyautogui          # type: ignore
from openai import OpenAI # type: ignore
from PIL import Image     # type: ignore

from config import NVIDIA_API_KEY, NVIDIA_BASE_URL, NVIDIA_VISION_MODEL
from control.keyboard_mouse import click, ensure_desktop_attached

logger = logging.getLogger("jarvis.control.vision")

_client = OpenAI(api_key=NVIDIA_API_KEY, base_url=NVIDIA_BASE_URL)


# ─── Screenshot helper ────────────────────────────────────────────────────────

def _take_screenshot() -> tuple[Image.Image | None, str | None, tuple[int, int], tuple[int, int]]:
    """Take screenshot; returns (scaled_img, b64, (orig_w, orig_h), (screen_w, screen_h))."""
    ensure_desktop_attached()
    try:
        orig_img: Image.Image = pyautogui.screenshot()
    except Exception as e:
        logger.warning(f"Screenshot capture failed: {e}")
        return None, None, (0, 0), (0, 0)

    orig_w, orig_h = orig_img.width, orig_img.height
    try:
        screen_w, screen_h = pyautogui.size()
    except Exception:
        screen_w, screen_h = orig_w, orig_h

    # Scale down for LLM vision tokens (max 1280px)
    max_dim = 1280
    if max(orig_w, orig_h) > max_dim:
        ratio = max_dim / max(orig_w, orig_h)
        scaled_w = int(orig_w * ratio)
        scaled_h = int(orig_h * ratio)
        scaled_img = orig_img.resize((scaled_w, scaled_h), Image.LANCZOS)
    else:
        scaled_img = orig_img

    buf = BytesIO()
    scaled_img.save(buf, format="JPEG", quality=85)
    b64 = base64.standard_b64encode(buf.getvalue()).decode("utf-8")
    return scaled_img, b64, (orig_w, orig_h), (screen_w, screen_h)


# ─── Tier 1: Windows Native OCR (100% accurate text localization) ─────────────

def ocr_find_text_on_screen(query: str) -> tuple[int, int] | None:
    """
    Use Windows 10/11 built-in offline OCR to locate text on screen.
    Uses multi-candidate ranking to prioritize content results over header/search bar text.
    Returns (center_x, center_y) of matching word or phrase, or None.
    """
    try:
        import winsdk.windows.media.ocr as win_ocr
        import winsdk.windows.graphics.imaging as imaging
        import winsdk.windows.storage.streams as streams

        ensure_desktop_attached()
        orig_img = pyautogui.screenshot()
        buf = io.BytesIO()
        orig_img.save(buf, format="PNG")
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

            q_clean = re.sub(r"[^a-zA-Z0-9\s]", "", query).lower().strip()
            # Remove filler words
            stopwords = {"the", "a", "an", "button", "link", "icon", "on", "in", "play", "click", "song", "video"}
            keywords = [w for w in q_clean.split() if w not in stopwords and len(w) > 1]
            if not keywords:
                keywords = [w for w in q_clean.split() if len(w) > 1]

            is_header_search = any(w in q_clean for w in ("search", "address", "url", "tab", "title", "input", "box"))
            candidates = []

            for line in res.lines:
                l_text = line.text.lower()
                # 1. Full phrase match on line
                if q_clean and q_clean in l_text and line.words:
                    min_x = min(w.bounding_rect.x for w in line.words)
                    max_x = max(w.bounding_rect.x + w.bounding_rect.width for w in line.words)
                    min_y = min(w.bounding_rect.y for w in line.words)
                    max_y = max(w.bounding_rect.y + w.bounding_rect.height for w in line.words)
                    cx, cy = int((min_x + max_x) / 2), int((min_y + max_y) / 2)
                    score = 100
                    if not is_header_search and cy >= 140:
                        score += 60
                    elif is_header_search and cy < 140:
                        score += 60
                    candidates.append((score, cx, cy, line.text))

                # 2. Individual word matches
                for word in line.words:
                    w_clean = re.sub(r"[^a-zA-Z0-9]", "", word.text).lower()
                    if len(w_clean) < 2:
                        continue
                    match_score = 0
                    if any(kw == w_clean for kw in keywords):
                        match_score = 60
                    elif any(len(kw) >= 3 and len(w_clean) >= 3 and (kw.startswith(w_clean) or w_clean.startswith(kw)) for kw in keywords):
                        match_score = 30

                    if match_score > 0:
                        cx = int(word.bounding_rect.x + word.bounding_rect.width / 2)
                        cy = int(word.bounding_rect.y + word.bounding_rect.height / 2)
                        if not is_header_search and cy >= 140:
                            match_score += 40
                        elif is_header_search and cy < 140:
                            match_score += 40
                        candidates.append((match_score, cx, cy, word.text))

            if candidates:
                # Rank highest score first, then prefer top of results
                candidates.sort(key=lambda c: (-c[0], c[2]))
                best = candidates[0]
                logger.info(f"Windows OCR matched best candidate {best[3]!r} at ({best[1]}, {best[2]}) score={best[0]} for query {query!r}")
                return best[1], best[2]

            return None

        return asyncio.run(_run())
    except Exception as e:
        logger.debug(f"Windows OCR localization failed: {e}")
        return None


# ─── Tier 2: Windows UIAutomation (Accessible native controls) ────────────────

def uia_find_element(description: str) -> tuple[int, int] | None:
    """Use Windows UIAutomation to find buttons, edit controls, or items by name."""
    try:
        import uiautomation as uia
        d_lower = description.lower().strip()
        stopwords = {"the", "a", "an", "on", "in", "to", "for"}
        keywords = [w for w in d_lower.split() if w not in stopwords and len(w) > 1]

        root = uia.GetRootControl()
        # Search active window first
        fg = uia.GetFocusedControl()
        search_roots = [fg.GetTopLevelControl()] if fg else [root]

        for s_root in search_roots:
            if not s_root:
                continue
            for ctrl, _ in uia.WalkControl(s_root, maxDepth=8):
                name = (ctrl.Name or "").lower()
                if not name:
                    continue
                if any(kw in name for kw in keywords):
                    rect = ctrl.BoundingRectangle
                    if rect and rect.width() > 10 and rect.height() > 10:
                        cx = (rect.left + rect.right) // 2
                        cy = (rect.top + rect.bottom) // 2
                        if cx > 20 and cy > 20:
                            logger.info(f"UIAutomation matched control {ctrl.Name!r} at ({cx}, {cy})")
                            return cx, cy
        return None
    except Exception as e:
        logger.debug(f"UIAutomation search error: {e}")
        return None


# ─── Tier 3: Parse AI coordinates fallback ────────────────────────────────────

def _parse_coords(raw: str, max_w: int, max_h: int) -> tuple[int, int] | None:
    raw_clean = raw.strip()
    try:
        parsed = json.loads(raw_clean)
        if isinstance(parsed, dict):
            x = parsed.get("x") or parsed.get("X")
            y = parsed.get("y") or parsed.get("Y")
            if x is not None and y is not None and (int(x) > 20 or int(y) > 20):
                return int(x), int(y)
    except Exception:
        pass

    bm = re.search(r"[\[\(]\s*(\d{1,4})\s*,\s*(\d{1,4})\s*[\]\)]", raw_clean)
    if bm:
        x, y = int(bm.group(1)), int(bm.group(2))
        if x > 20 or y > 20:
            return x, y

    sm = re.search(r"(\d{1,4})\s*[,x\s]\s*(\d{1,4})", raw_clean)
    if sm:
        x, y = int(sm.group(1)), int(sm.group(2))
        if 20 <= x <= max_w and 20 <= y <= max_h:
            return x, y

    return None


# ─── Special Detectors (Media Play Buttons & Icons) ──────────────────────────

def detect_play_button() -> tuple[int, int] | None:
    """Find the Spotify / YouTube green play button or media play icon via color connected components."""
    try:
        import numpy as np
        from scipy import ndimage
        ensure_desktop_attached()
        im = pyautogui.screenshot()
        arr = np.array(im)
        # Spotify vibrant green (#1db954 / #1ed760) mask
        mask = (arr[:, :, 0] < 60) & (arr[:, :, 1] > 170) & (arr[:, :, 2] < 150)
        labeled, num_features = ndimage.label(mask)
        if num_features == 0:
            return None

        blobs = []
        for i in range(1, num_features + 1):
            ys, xs = np.where(labeled == i)
            if len(xs) >= 20:
                cx, cy = int(np.mean(xs)), int(np.mean(ys))
                w = int(np.max(xs) - np.min(xs))
                h = int(np.max(ys) - np.min(ys))
                # Circular or square button preference
                aspect = min(w, h) / max(w, h) if max(w, h) > 0 else 0
                blobs.append((len(xs), aspect, cx, cy, w, h))

        if not blobs:
            return None

        # Sort blobs: largest pixel count & circular aspect
        blobs.sort(key=lambda b: (-b[0], -b[1]))
        best_blob = blobs[0]
        cx, cy = best_blob[2], best_blob[3]
        if cx > 20 and cy > 20:
            logger.info(f"Green Play Button detected at ({cx}, {cy}) (pixels={best_blob[0]}, size={best_blob[4]}x{best_blob[5]})")
            return cx, cy
    except Exception as e:
        logger.debug(f"Play button color detection error: {e}")
    return None


# ─── Public API ───────────────────────────────────────────────────────────────

def read_screen() -> str:
    """Take a screenshot and return a natural language description using NVIDIA Vision."""
    scaled_img, b64, _, _ = _take_screenshot()
    if not scaled_img or not b64:
        return "Screen capture is currently unavailable."
    logger.info("Reading screen with NVIDIA Vision …")
    try:
        response = _client.chat.completions.create(
            model=NVIDIA_VISION_MODEL,
            max_tokens=512,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}},
                        {
                            "type": "text",
                            "text": (
                                "Describe what is currently on the screen in 2-3 sentences. "
                                "Focus on the active application, visible content, and any "
                                "notable UI elements. Be concise."
                            ),
                        },
                    ],
                }
            ],
        )
        description = response.choices[0].message.content.strip()
    except Exception as e:
        logger.warning(f"Vision model failed: {e}")
        description = f"Screenshot taken (vision model unavailable: {e})."

    return description


def click_element_by_description(description: str) -> str:
    """
    Locate and click any element on the screen using Play Detect -> OCR -> UIA -> AI Vision.
    Never blindly clicks (0, 0).
    """
    ensure_desktop_attached()
    logger.info(f"Locating UI element: '{description}'")
    d_clean = description.lower().strip()

    # 1. Special case: Play button, music, song, or "it"/"this" when music is active
    if any(w in d_clean for w in ("play", "it", "this", "song", "music", "green")):
        play_pt = detect_play_button()
        if play_pt:
            cx, cy = play_pt
            pyautogui.moveTo(cx, cy, duration=0.35)
            time.sleep(0.1)
            pyautogui.click()
            pyautogui.doubleClick()
            logger.info(f"Clicked Play button at ({cx}, {cy})")
            return f"Clicked Play button at ({cx}, {cy})."

    # If the user literally said "it" or "this", check focused or primary action control
    if d_clean in ("it", "this", "that", "click it", "click this"):
        try:
            import uiautomation as uia
            fg = uia.GetFocusedControl()
            if fg and fg.BoundingRectangle:
                rect = fg.BoundingRectangle
                if rect.width() > 10 and rect.height() > 10:
                    cx = (rect.left + rect.right) // 2
                    cy = (rect.top + rect.bottom) // 2
                    if cx > 20 and cy > 20:
                        pyautogui.moveTo(cx, cy, duration=0.35)
                        pyautogui.click()
                        return f"Clicked focused element at ({cx}, {cy})."
        except Exception:
            pass


    # 2. Tier 1: Windows Native OCR (fastest & most accurate for text/buttons)
    ocr_pt = ocr_find_text_on_screen(description)
    if ocr_pt:
        cx, cy = ocr_pt
        pyautogui.moveTo(cx, cy, duration=0.4)
        pyautogui.click()
        logger.info(f"Clicked '{description}' at ({cx}, {cy}) via Windows OCR")
        return f"Clicked '{description}' at ({cx}, {cy})."

    # 3. Tier 2: Windows UI Automation (native controls)
    uia_pt = uia_find_element(description)
    if uia_pt:
        cx, cy = uia_pt
        pyautogui.moveTo(cx, cy, duration=0.4)
        pyautogui.click()
        logger.info(f"Clicked '{description}' at ({cx}, {cy}) via Windows UIAutomation")
        return f"Clicked '{description}' at ({cx}, {cy})."

    # 3. Tier 3: NVIDIA Vision Model
    scaled_img, b64, (orig_w, orig_h), (screen_w, screen_h) = _take_screenshot()
    if scaled_img and b64:
        sw, sh = scaled_img.width, scaled_img.height
        try:
            response = _client.chat.completions.create(
                model=NVIDIA_VISION_MODEL,
                max_tokens=64,
                temperature=0.0,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are a precise screen localization engine. "
                            "Output ONLY a JSON object: {\"x\": <int>, \"y\": <int>}. "
                            "If the element cannot be found, output {\"error\": \"NOT_FOUND\"}."
                        ),
                    },
                    {
                        "role": "user",
                        "content": [
                            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}},
                            {"type": "text", "text": f"Locate '{description}' in this image of width {sw} and height {sh}."},
                        ],
                    },
                ],
            )
            raw = response.choices[0].message.content.strip()
            coords = _parse_coords(raw, sw, sh)
            if coords:
                model_x, model_y = coords
                scale_x = screen_w / sw if sw else 1.0
                scale_y = screen_h / sh if sh else 1.0
                target_x = int(model_x * scale_x)
                target_y = int(model_y * scale_y)
                if target_x > 25 and target_y > 25:
                    pyautogui.moveTo(target_x, target_y, duration=0.4)
                    pyautogui.click()
                    logger.info(f"Clicked '{description}' at ({target_x}, {target_y}) via AI Vision")
                    return f"Clicked '{description}' at ({target_x}, {target_y})."
        except Exception as e:
            logger.warning(f"Vision model error: {e}")

    return f"Could not accurately locate '{description}' on the screen, sir."


def click_and_type(description: str, text: str, press_enter: bool = True) -> str:
    """Find a UI element, click it, type text into it, and optionally press Enter."""
    res = click_element_by_description(description)
    if "Could not" in res or "unavailable" in res:
        return res
    import time
    time.sleep(0.1)
    from control.keyboard_mouse import type_text, press_single_key
    type_text(text)
    if press_enter:
        time.sleep(0.1)
        press_single_key("enter")
    return f"Clicked '{description}', typed '{text}'" + (", and pressed Enter." if press_enter else ".")
