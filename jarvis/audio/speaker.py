"""
audio/speaker.py – Text-to-speech for JARVIS.

Primary: edge-tts (async, natural Microsoft neural voices)
Fallback: pyttsx3 (offline, always available)
"""

import asyncio
import io
import logging
import threading
import time

import pyttsx3  # type: ignore

from config import EDGE_TTS_VOICE, PYTTSX3_RATE

logger = logging.getLogger("jarvis.speaker")

# Global flag so other threads can interrupt playback
_stop_speaking = threading.Event()


def stop_speaking():
    """Signal the speaker to stop current speech immediately."""
    _stop_speaking.set()


def reset_stop():
    _stop_speaking.clear()


# ─── Edge-TTS (primary) ───────────────────────────────────────────────────────

def _get_voice_for_text(text: str) -> str:
    """Return Malayalam voice if text contains Malayalam Unicode, else Indian English."""
    if any("\u0D00" <= ch <= "\u0D7F" for ch in text):
        return "ml-IN-MidhunNeural"
    return EDGE_TTS_VOICE


async def _edge_speak_async(text: str):
    """Synthesise text with edge-tts and play via sounddevice."""
    try:
        import edge_tts   # type: ignore
        import sounddevice as sd  # type: ignore
        import soundfile as sf    # type: ignore
        import numpy as np

        voice = _get_voice_for_text(text)
        communicate = edge_tts.Communicate(text, voice)
        audio_data = b""
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                audio_data += chunk["data"]
            if _stop_speaking.is_set():
                return

        if not audio_data or _stop_speaking.is_set():
            return

        # Decode mp3 bytes → numpy array
        buf = io.BytesIO(audio_data)
        data, samplerate = sf.read(buf, dtype="float32")

        # Play smoothly with sounddevice
        sd.play(data, samplerate=samplerate)
        while sd.get_stream().active:
            if _stop_speaking.is_set():
                sd.stop()
                break
            await asyncio.sleep(0.05)
    except Exception as e:
        logger.warning(f"edge-tts failed ({e}); falling back to pyttsx3.")
        raise


def _edge_speak(text: str):
    loop = asyncio.new_event_loop()
    try:
        loop.run_until_complete(_edge_speak_async(text))
    finally:
        loop.close()


# ─── pyttsx3 fallback ─────────────────────────────────────────────────────────

_pyttsx3_engine = None
_pyttsx3_lock = threading.Lock()


def _get_pyttsx3_engine():
    global _pyttsx3_engine
    with _pyttsx3_lock:
        if _pyttsx3_engine is None:
            _pyttsx3_engine = pyttsx3.init()
            _pyttsx3_engine.setProperty("rate", PYTTSX3_RATE)
            # Prefer a female voice if available
            voices = _pyttsx3_engine.getProperty("voices")
            for v in voices:
                if "female" in v.name.lower() or "zira" in v.name.lower():
                    _pyttsx3_engine.setProperty("voice", v.id)
                    break
        return _pyttsx3_engine


def _pyttsx3_speak(text: str):
    engine = _get_pyttsx3_engine()
    with _pyttsx3_lock:
        engine.say(text)
        engine.runAndWait()


# ─── Public API ───────────────────────────────────────────────────────────────

def speak(text: str, use_edge: bool = True):
    """
    Speak `text` aloud. Blocks until done or interrupted.
    Set use_edge=False to force pyttsx3.
    """
    if not text or not text.strip():
        return

    reset_stop()
    logger.info(f"Speaking: {text[:80]}{'...' if len(text) > 80 else ''}")

    if use_edge:
        try:
            _edge_speak(text)
            return
        except Exception:
            pass  # already logged inside _edge_speak

    # Fallback
    _pyttsx3_speak(text)
