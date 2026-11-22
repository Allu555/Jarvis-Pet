"""
audio/corrections.py – Lexicon normalization and fuzzy error correction for JARVIS.

Uses corrections.json and rapidfuzz to fix common phonetic mishears
(e.g., "not bad" -> "notepad", "sportify" -> "spotify", "u tube" -> "youtube").
"""

import json
import logging
import os
import re
from pathlib import Path

try:
    from rapidfuzz import fuzz, process
    HAS_RAPIDFUZZ = True
except ImportError:
    HAS_RAPIDFUZZ = False

from config import CORRECTIONS_FILE

logger = logging.getLogger("jarvis.audio.corrections")

_corrections_cache = {}
_command_lexicon = []
_last_mtime = 0.0


def _load_corrections():
    global _corrections_cache, _command_lexicon, _last_mtime
    try:
        if os.path.exists(CORRECTIONS_FILE):
            mtime = os.path.getmtime(CORRECTIONS_FILE)
            if mtime != _last_mtime:
                with open(CORRECTIONS_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    _corrections_cache = data.get("phonetic_corrections", {})
                    _command_lexicon = data.get("command_lexicon", [])
                    _last_mtime = mtime
                logger.info(f"Loaded {len(_corrections_cache)} corrections from {CORRECTIONS_FILE.name}")
    except Exception as e:
        logger.warning(f"Failed to load corrections.json: {e}")


_load_corrections()


def normalize_transcript(text: str) -> str:
    """
    Apply dictionary replacements and token-level fuzzy corrections.
    Returns normalized text.
    """
    if not text:
        return ""

    _load_corrections()
    t = text.strip()
    t_lower = t.lower()

    # 1. Exact phrase replacements from corrections.json
    for wrong, right in _corrections_cache.items():
        pattern = r"\b" + re.escape(wrong.lower()) + r"\b"
        if re.search(pattern, t_lower):
            t_lower = re.sub(pattern, right, t_lower)

    # 2. Key app names direct regex
    app_fixes = {
        r"\bnot\s*(?:pad|bad|tab|ed)\b": "notepad",
        r"\b(?:sportify|spot\s*if\s*i|spottify|spotty)\b": "spotify",
        r"\b(?:u\s*tube|you\s*tube)\b": "youtube",
        r"\b(?:vs\s*code|visual\s*studio\s*code)\b": "vscode",
    }
    for pat, rep in app_fixes.items():
        t_lower = re.sub(pat, rep, t_lower)

    # 3. Clean extra whitespace
    normalized = re.sub(r"\s+", " ", t_lower).strip()
    return normalized
