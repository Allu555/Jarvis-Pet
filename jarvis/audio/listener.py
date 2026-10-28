"""
audio/listener.py – Wake word detection, VAD, and speech-to-text for JARVIS.

Pipeline:
  1. Always-on microphone stream (PyAudio)
  2. Wake-word detection: try openWakeWord → fall back to keyword-in-Whisper
  3. Voice Activity Detection: webrtcvad (30 ms frames)
  4. Batch the voiced audio, transcribe with faster-whisper
  5. Return the transcribed string

Also exposes push_to_talk_record() for the PTT hotkey path.
"""

import collections
import logging
import queue
import re
import struct
import threading
import time
from typing import Callable

import numpy as np
import pyaudio                          # type: ignore
import webrtcvad                        # type: ignore
from faster_whisper import WhisperModel # type: ignore

from config import (
    SAMPLE_RATE, CHUNK_MS, CHUNK_SAMPLES,
    VAD_AGGRESSIVENESS, SILENCE_TIMEOUT_SEC,
    MAX_RECORD_SEC, WHISPER_MODEL_SIZE,
    WHISPER_DEVICE, WHISPER_COMPUTE,
    WHISPER_LANGUAGE, WAKE_WORD, WAKE_WORD_ALIASES,
    WHISPER_CPU_THREADS,
)

logger = logging.getLogger("jarvis.listener")

# ─── Load Whisper model once ──────────────────────────────────────────────────
logger.info(f"Loading Whisper model '{WHISPER_MODEL_SIZE}' on {WHISPER_DEVICE} …")
_whisper: WhisperModel | None = None


def _get_whisper() -> WhisperModel:
    global _whisper
    if _whisper is None:
        _whisper = WhisperModel(
            WHISPER_MODEL_SIZE,
            device=WHISPER_DEVICE,
            compute_type=WHISPER_COMPUTE,
            cpu_threads=WHISPER_CPU_THREADS,
            num_workers=1,
        )
        logger.info("Whisper model ready.")
    return _whisper


# ─── openWakeWord (optional) ──────────────────────────────────────────────────
_oww_model = None

def _try_load_oww():
    global _oww_model
    try:
        from openwakeword.model import Model  # type: ignore
        _oww_model = Model(wakeword_models=["hey_jarvis"], inference_framework="onnx")
        logger.info("openWakeWord model loaded.")
        return True
    except Exception as e:
        logger.warning(f"openWakeWord not available ({e}). Using Whisper wake-word fallback.")
        return False


# ─── PyAudio helpers ──────────────────────────────────────────────────────────

def _open_mic() -> tuple[pyaudio.PyAudio, pyaudio.Stream]:
    pa = pyaudio.PyAudio()
    stream = pa.open(
        format=pyaudio.paInt16,
        channels=1,
        rate=SAMPLE_RATE,
        input=True,
        frames_per_buffer=CHUNK_SAMPLES,
    )
    return pa, stream


def _read_chunk(stream: pyaudio.Stream) -> bytes:
    return stream.read(CHUNK_SAMPLES, exception_on_overflow=False)


# ─── VAD recording ────────────────────────────────────────────────────────────

def _rms_to_meter(rms: float, ambient: float) -> str:
    """Return dynamic visual sound waves for live UI feedback."""
    diff = max(0.0, rms - ambient)
    scale = max(ambient * 1.5, 80.0)
    bars = int(min(6, (diff / scale) * 4))
    if bars <= 0:
        return "▪"
    return "▰" * bars + "▱" * (6 - bars)


class _InterimTranscriber:
    """Background worker for live partial transcription during speech recording."""
    def __init__(self, callback: Callable[[str], None]):
        self._callback = callback
        self._q = queue.Queue(maxsize=1)
        self._running = True
        self._thread = threading.Thread(target=self._run, daemon=True, name="interim_stt")
        self._thread.start()

    def submit(self, pcm_bytes: bytes):
        try:
            self._q.get_nowait()
        except queue.Empty:
            pass
        try:
            self._q.put_nowait(pcm_bytes)
        except queue.Full:
            pass

    def _run(self):
        while self._running:
            try:
                raw = self._q.get(timeout=0.15)
                if not self._running:
                    break
                text = transcribe(raw).strip()
                if text and self._running:
                    self._callback(text)
            except queue.Empty:
                pass
            except Exception:
                pass

    def stop(self):
        self._running = False


def _record_until_silence(
    stream: pyaudio.Stream,
    vad: webrtcvad.Vad,
    is_ptt: bool = False,
    on_interim: Callable[[str], None] | None = None,
    stop_event: threading.Event | None = None,
) -> bytes:
    """
    Read audio until speech finishes or silence timeout occurs.
    Includes live audio visualization and streaming interim text on overlay.
    """
    global _ambient_rms
    frames: list[bytes] = []
    silence_frames = 0
    # Snappy 0.65s silence (22 frames) finishes immediately when user finishes talking
    silence_limit = int((0.65 if is_ptt else 0.8) * 1000 / CHUNK_MS)
    max_frames = int((8.0 if is_ptt else MAX_RECORD_SEC) * 1000 / CHUNK_MS)
    wait_start_limit = int((4.5 if is_ptt else 3.0) * 1000 / CHUNK_MS)
    total_frames = 0
    speech_started = False
    voiced_count = 0

    interim_worker = None
    interim_text = [""]
    if on_interim:
        def _update_text(t: str):
            interim_text[0] = t
            on_interim(f'"{t}…" 🎙️')
        interim_worker = _InterimTranscriber(_update_text)

    last_ui_update = 0.0
    last_interim_submit = 0.0

    while total_frames < max_frames:
        if stop_event and stop_event.is_set():
            break

        chunk = _read_chunk(stream)
        frames.append(chunk)
        total_frames += 1

        samples = np.frombuffer(chunk, dtype=np.int16)
        rms = float(np.sqrt(np.mean(samples.astype(np.float32) ** 2)))
        now = time.time()

        try:
            vad_flag = vad.is_speech(chunk, SAMPLE_RATE)
        except Exception:
            vad_flag = False

        voice_thresh = max(180.0, _ambient_rms * 1.3)
        is_voice = (vad_flag and rms > voice_thresh) or (rms > max(350.0, _ambient_rms * 1.6))

        if is_voice:
            voiced_count += 1
            if voiced_count >= 2:
                speech_started = True
            silence_frames = 0
        else:
            if speech_started:
                silence_frames += 1
                if silence_frames >= silence_limit:
                    break
            else:
                if total_frames >= wait_start_limit:
                    break

        # Live visual feedback on overlay
        if on_interim and (now - last_ui_update > 0.1):
            last_ui_update = now
            meter = _rms_to_meter(rms, _ambient_rms)
            if speech_started:
                if interim_text[0]:
                    on_interim(f'"{interim_text[0]}…" {meter}')
                else:
                    on_interim(f"🎙️ Hearing you… {meter}")
            else:
                on_interim(f"🎙️ Listening… {meter}")

        # Stream audio to interim transcriber every 0.75s
        if interim_worker and speech_started and (now - last_interim_submit > 0.75) and len(frames) >= 20:
            last_interim_submit = now
            interim_worker.submit(b"".join(frames))

    if interim_worker:
        interim_worker.stop()

    return b"".join(frames)


# ─── Transcription ────────────────────────────────────────────────────────────

def transcribe(audio_bytes: bytes) -> str:
    """Convert raw PCM bytes to text using faster-whisper tuned for Indian accent."""
    if not audio_bytes or len(audio_bytes) < 4000:
        return ""
    try:
        model = _get_whisper()
        # Convert int16 PCM → float32 normalised
        audio_np = np.frombuffer(audio_bytes, dtype=np.int16).astype(np.float32) / 32768.0
        
        # Audio must have non-zero amplitude to avoid empty sequence
        if float(np.max(np.abs(audio_np))) < 0.002:
            return ""

        segments, _ = model.transcribe(
            audio_np,
            language=WHISPER_LANGUAGE or "en",
            beam_size=1,  # greedy decoding is 2x faster than beam_size=5
            vad_filter=False,  # we already clipped silence; avoid chopping Indian syllables
            initial_prompt="Jarvis, namaskaram, open YouTube, what time is it, Chrome.",
            condition_on_previous_text=False,
            no_speech_threshold=0.5,
        )
        text = " ".join(seg.text for seg in segments).strip()
        if text:
            logger.info(f"Transcribed: {text!r}")
        return text
    except Exception as e:
        logger.debug(f"Transcribe suppressed error: {e}")
        return ""


# ─── Wake-word detection with openWakeWord ────────────────────────────────────

def _detect_wake_word_oww(stream: pyaudio.Stream) -> bool:
    """
    Feed 80 ms chunks to openWakeWord; return True when wake word fires.
    """
    oww_chunk = int(SAMPLE_RATE * 0.08)     # 80 ms
    chunk = stream.read(oww_chunk, exception_on_overflow=False)
    audio = np.frombuffer(chunk, dtype=np.int16)
    prediction = _oww_model.predict(audio)
    for name, score in prediction.items():
        if score > 0.5:
            logger.info(f"openWakeWord detected: {name} ({score:.2f})")
            return True
    return False


_last_whisper_check = 0.0
_ambient_rms = 100.0
_voiced_chunks = 0
_silence_chunks = 0
_speech_active = False


def _detect_wake_word_whisper(
    stream: pyaudio.Stream,
    vad: webrtcvad.Vad,
    ring: collections.deque,
) -> tuple[bool, str | None]:
    """
    Ultra CPU-efficient wake-word detection using faster-whisper.
    Only runs neural network inference when a real voice utterance is detected
    and either finishes with a brief silence or reaches duration threshold.
    Zero-cost during room silence, keyboard clatter, or background hiss.
    """
    global _last_whisper_check, _ambient_rms, _voiced_chunks, _silence_chunks, _speech_active
    chunk = _read_chunk(stream)
    ring.append(chunk)

    # Compute fast RMS energy on int16 samples
    samples = np.frombuffer(chunk, dtype=np.int16)
    rms = float(np.sqrt(np.mean(samples.astype(np.float32) ** 2)))

    try:
        vad_speech = vad.is_speech(chunk, SAMPLE_RATE)
    except Exception:
        vad_speech = False

    # Continuously adapt ambient noise baseline when vad does not detect voice
    if not vad_speech:
        _ambient_rms = 0.95 * _ambient_rms + 0.05 * rms

    # True voice requires both VAD phonetic patterns and amplitude above ambient noise
    voice_threshold = max(280.0, _ambient_rms * 1.4)
    is_voice = vad_speech and (rms > voice_threshold)

    now = time.time()

    if is_voice:
        _voiced_chunks += 1
        _silence_chunks = 0
        _speech_active = True
    else:
        if _speech_active:
            _silence_chunks += 1

    # Check if speech finished (user said 'Jarvis' and paused for ~210ms)
    # 7 chunks = 210ms voice, 7 chunks = 210ms silence
    phrase_finished = _speech_active and (_voiced_chunks >= 7) and (_silence_chunks >= 7)
    # Or continuous speech without pause for ~1.5s (45 chunks)
    long_speech = _speech_active and (_voiced_chunks >= 45) and ((now - _last_whisper_check) > 2.0)

    # If it was just transient noise (cough, keyboard, click) followed by silence:
    if _speech_active and (_silence_chunks > 12) and (_voiced_chunks < 7):
        _speech_active = False
        _voiced_chunks = 0
        _silence_chunks = 0
        return False, None

    if (phrase_finished or long_speech) and (now - _last_whisper_check) > 1.0:
        _last_whisper_check = now
        _speech_active = False
        _voiced_chunks = 0
        _silence_chunks = 0

        audio = b"".join(ring)
        ring.clear()
        text = transcribe(audio).strip()
        text_lower = text.lower()

        matched_wake = None
        for alias in WAKE_WORD_ALIASES:
            if re.search(rf"\b{alias}\b", text_lower):
                matched_wake = alias
                break

        if matched_wake:
            logger.info(f"Wake word matched via '{matched_wake}': {text!r}")
            # Extract any command that followed the wake word directly
            parts = re.split(rf"\b{matched_wake}\b", text, flags=re.IGNORECASE)
            cmd = ""
            if len(parts) > 1:
                cmd = parts[1].strip(" ,.!?:\n\t")
            return True, (cmd if len(cmd) > 2 else None)
        else:
            # Utterance wasn't the wake word; back off cooldown by 1.5s so we don't spam CPU on non-wake background audio
            _last_whisper_check = now + 1.5

    return False, None


# ─── Main listener class ──────────────────────────────────────────────────────

class Listener:
    """
    Always-on listener.
    Call .start(callback) where callback(text: str) is called with each command.
    """

    def __init__(self):
        self._running   = False
        self._paused    = False
        self._thread: threading.Thread | None = None
        self._use_oww   = _try_load_oww()
        self._vad       = webrtcvad.Vad(VAD_AGGRESSIVENESS)
        self._pa        = None
        self._stream    = None
        self._mic_lock  = threading.Lock()

    def pause(self):
        """Mute/pause the listener so it doesn't hear JARVIS's own speaker output."""
        self._paused = True

    def resume(self):
        """Resume listening."""
        self._paused = False

    def start(self, on_command: Callable[[str], None]):
        """Start the background listener thread."""
        self._running = True
        self._on_command = on_command
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()
        logger.info("Listener started.")

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=3)

    def _loop(self):
        pa, stream = _open_mic()
        self._pa = pa
        self._stream = stream
        # 2-second ring buffer for wake-word context
        ring_size = int(2000 / CHUNK_MS)
        ring: collections.deque = collections.deque(maxlen=ring_size)

        # Calibrate ambient noise floor for 300ms
        try:
            calib = []
            for _ in range(10):
                c = _read_chunk(stream)
                s = np.frombuffer(c, dtype=np.int16)
                calib.append(float(np.sqrt(np.mean(s.astype(np.float32) ** 2))))
            global _ambient_rms
            _ambient_rms = max(150.0, float(np.median(calib)))
            logger.info(f"Calibrated ambient mic RMS: {_ambient_rms:.1f}")
        except Exception:
            pass

        try:
            while self._running:
                if self._paused:
                    ring.clear()
                    time.sleep(0.05)
                    continue

                try:
                    # ── Wake-word phase ───────────────────────────────────────
                    with self._mic_lock:
                        if self._use_oww:
                            detected = _detect_wake_word_oww(stream)
                            embedded_cmd = None
                        else:
                            detected, embedded_cmd = _detect_wake_word_whisper(stream, self._vad, ring)

                    if not detected:
                        continue

                    # ── Command execution / recording phase ───────────────────
                    if embedded_cmd:
                        logger.info(f"Inline command detected: {embedded_cmd!r}")
                        self._on_command(embedded_cmd)
                    else:
                        logger.info("Wake word heard – recording command …")
                        try:
                            import winsound
                            winsound.Beep(1400, 60)
                        except Exception:
                            pass
                        with self._mic_lock:
                            raw = _record_until_silence(stream, self._vad, is_ptt=False)
                        text = transcribe(raw)
                        if text:
                            self._on_command(text)
                except Exception as tick_err:
                    logger.debug(f"Listener tick exception handled: {tick_err}")
                    time.sleep(0.05)

        except Exception as e:
            logger.error(f"Listener loop crashed: {e}", exc_info=True)
        finally:
            with self._mic_lock:
                self._stream = None
                self._pa = None
                try:
                    stream.stop_stream()
                    stream.close()
                    pa.terminate()
                except Exception:
                    pass

    # ── Push-to-talk ──────────────────────────────────────────────────────────

    def push_to_talk_record(
        self,
        on_interim: Callable[[str], None] | None = None,
        on_recording_done: Callable[[], None] | None = None,
        stop_event: threading.Event | None = None,
    ) -> str:
        """
        Record from mic until silence, transcribe, and return text.
        Thread-safe: reuses existing active microphone stream.
        """
        logger.info("PTT – recording …")
        raw = b""
        with self._mic_lock:
            stream = self._stream
            if stream is not None and stream.is_active():
                raw = _record_until_silence(
                    stream, self._vad, is_ptt=True,
                    on_interim=on_interim, stop_event=stop_event
                )
            else:
                # Standalone fallback if background listener loop is not active
                pa, st = _open_mic()
                try:
                    raw = _record_until_silence(
                        st, self._vad, is_ptt=True,
                        on_interim=on_interim, stop_event=stop_event
                    )
                finally:
                    try:
                        st.stop_stream()
                        st.close()
                        pa.terminate()
                    except Exception:
                        pass

        if on_recording_done:
            try:
                on_recording_done()
            except Exception:
                pass

        return transcribe(raw)
