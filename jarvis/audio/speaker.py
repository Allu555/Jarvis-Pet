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

from config import EDGE_TTS_VOICE, PYTTSX3_RATE, USE_EDGE_TTS

logger = logging.getLogger("jarvis.speaker")

# Global flag so other threads can interrupt playback
_stop_speaking = threading.Event()
_is_speaking_flag = False
_edge_tts_disabled_until = 0.0


def is_speaking() -> bool:
    """Return True if speaker is actively playing audio."""
    return _is_speaking_flag


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
        global _edge_tts_disabled_until
        _edge_tts_disabled_until = time.time() + 300.0  # 5-minute circuit breaker
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
            try:
                import pythoncom
                pythoncom.CoInitialize()
            except Exception:
                pass
            _pyttsx3_engine = pyttsx3.init()
            _pyttsx3_engine.setProperty("rate", PYTTSX3_RATE)
            voices = _pyttsx3_engine.getProperty("voices")
            for v in voices:
                if "female" in v.name.lower() or "zira" in v.name.lower():
                    _pyttsx3_engine.setProperty("voice", v.id)
                    break
        return _pyttsx3_engine


def _pyttsx3_speak(text: str):
    try:
        import pythoncom
        pythoncom.CoInitialize()
    except Exception:
        pass
    engine = _get_pyttsx3_engine()
    with _pyttsx3_lock:
        engine.say(text)
        engine.runAndWait()


# ─── Public API ───────────────────────────────────────────────────────────────

def speak(text: str, use_edge: bool = None):
    """
    Speak `text` aloud. Blocks until done or interrupted.
    If use_edge is None, defaults to config.USE_EDGE_TTS.
    """
    global _is_speaking_flag
    if not text or not text.strip():
        return

    if use_edge is None:
        use_edge = USE_EDGE_TTS
    else:
        use_edge = use_edge and USE_EDGE_TTS

    reset_stop()
    logger.info(f"Speaking: {text[:80]}{'...' if len(text) > 80 else ''}")
    _is_speaking_flag = True
    try:
        if use_edge and time.time() > _edge_tts_disabled_until:
            try:
                _edge_speak(text)
                return
            except Exception:
                pass

        # Fallback to offline pyttsx3 (ultra-fast, zero network latency)
        _pyttsx3_speak(text)
    finally:
        _is_speaking_flag = False
