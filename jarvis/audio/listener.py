"""
audio/listener.py – Next-Gen Hands-Free Voice Engine for JARVIS.

Architecture:
  1. Wake Word: openWakeWord ONNX ('hey_jarvis') with ultra-low CPU/battery footprint.
     Gracefully falls back to Whisper wake detection if unavailable.
  2. VAD & Pre-Roll: 300 ms circular pre-roll buffer + WebRTC VAD with 650 ms endpointing.
     Never clips initial consonants or syllables.
  3. Noise Suppression & AGC: Spectral gating (noisereduce) + software AGC peak normalization.
  4. STT: faster-whisper (small.en) on CUDA float16 / CPU int8 with beam_size=1 and warm startup.
  5. Post-Processing: corrections.json + RapidFuzz lexicon normalization.
  6. Confidence Scoring: Rejects low-confidence hallucinations and prompts clarification.
  7. Echo-Gating & Barge-In: Suppresses speaker feedback while allowing 'Jarvis stop' interruptions.
  8. Follow-up Mode: 6-second active window for multi-turn dialogue without repeating the wake word.
  9. Telemetry: Every utterance, latency, confidence, and correction is logged to logs/voice.log.
"""

import collections
import datetime
import json
import logging
import queue
import re
import threading
import time
from typing import Callable

import numpy as np
import pyaudio                          # type: ignore
import webrtcvad                        # type: ignore
from faster_whisper import WhisperModel # type: ignore

try:
    import noisereduce as nr
    HAS_NOISEREDUCE = True
except ImportError:
    HAS_NOISEREDUCE = False

from audio.corrections import normalize_transcript
from audio import speaker

from config import (
    SAMPLE_RATE, CHUNK_MS, CHUNK_SAMPLES,
    VAD_AGGRESSIVENESS, SILENCE_TIMEOUT_SEC, VAD_PRE_ROLL_MS,
    MAX_RECORD_SEC, WHISPER_MODEL_SIZE, WHISPER_DEVICE,
    WHISPER_COMPUTE, WHISPER_LANGUAGE, WHISPER_BEAM_SIZE,
    WHISPER_CPU_THREADS, WHISPER_INITIAL_PROMPT, CONFIDENCE_THRESHOLD,
    WAKE_WORD, WAKE_WORD_THRESHOLD, WAKE_WORD_ALIASES,
    MICROPHONE_DEVICE_INDEX, ENABLE_NOISE_REDUCTION,
    CONVERSATION_FOLLOWUP_SEC, VOICE_LOG,
)

logger = logging.getLogger("jarvis.listener")

# ─── openWakeWord (Hey Jarvis) Engine (Init first to prevent OpenMP conflict) ───

_oww_model = None
_oww_loaded = False


def _try_load_oww() -> bool:
    global _oww_model, _oww_loaded
    if _oww_loaded:
        return _oww_model is not None
    _oww_loaded = True
    try:
        from openwakeword.model import Model
        _oww_model = Model(wakeword_models=["hey_jarvis_v0.1"])
        logger.info("openWakeWord ONNX 'hey_jarvis_v0.1' engine active (ultra-low CPU).")
        return True
    except Exception as e:
        logger.warning(f"openWakeWord not loaded ({e}). Using Whisper acoustic wake fallback.")
        _oww_model = None
        return False

# Initialize openWakeWord runtime first
_try_load_oww()

# ─── Load Faster-Whisper Model Once at Startup ────────────────────────────────

_whisper: WhisperModel | None = None
_whisper_lock = threading.Lock()


def _get_whisper() -> WhisperModel:
    global _whisper
    with _whisper_lock:
        if _whisper is None:
            logger.info(f"Loading faster-whisper '{WHISPER_MODEL_SIZE}' on {WHISPER_DEVICE} ({WHISPER_COMPUTE})…")
            try:
                _whisper = WhisperModel(
                    WHISPER_MODEL_SIZE,
                    device=WHISPER_DEVICE,
                    compute_type=WHISPER_COMPUTE,
                    cpu_threads=WHISPER_CPU_THREADS,
                    num_workers=1,
                )
            except Exception as e:
                logger.warning(f"CUDA init failed ({e}), falling back to CPU int8…")
                _whisper = WhisperModel(
                    WHISPER_MODEL_SIZE,
                    device="cpu",
                    compute_type="int8",
                    cpu_threads=WHISPER_CPU_THREADS,
                    num_workers=1,
                )
            # Warm up with a 0.5s silent buffer to eliminate first-query cold latency
            try:
                dummy = np.zeros(SAMPLE_RATE // 2, dtype=np.float32)
                _whisper.transcribe(dummy, language=WHISPER_LANGUAGE or "en", beam_size=1)
                logger.info("Whisper model warmed up and ready.")
            except Exception as e:
                logger.debug(f"Warmup notice: {e}")
    return _whisper



# ─── PyAudio Hardware Layer ───────────────────────────────────────────────────

def _open_mic() -> tuple[pyaudio.PyAudio, pyaudio.Stream]:
    """Open microphone input stream with device index support."""
    pa = pyaudio.PyAudio()
    dev_index = MICROPHONE_DEVICE_INDEX
    kwargs = {
        "format": pyaudio.paInt16,
        "channels": 1,
        "rate": SAMPLE_RATE,
        "input": True,
        "frames_per_buffer": CHUNK_SAMPLES,
    }
    if dev_index is not None:
        kwargs["input_device_index"] = int(dev_index)

    stream = pa.open(**kwargs)
    return pa, stream


def _read_chunk(stream: pyaudio.Stream) -> bytes:
    try:
        return stream.read(CHUNK_SAMPLES, exception_on_overflow=False)
    except Exception as e:
        logger.debug(f"Mic read buffer overflow/skip: {e}")
        return b"\x00" * (CHUNK_SAMPLES * 2)


# ─── Audio Pre-processing: Denoise & AGC ───────────────────────────────────────

def _clean_and_normalize_audio(audio_bytes: bytes) -> np.ndarray:
    """
    Converts int16 PCM bytes to float32 normalized waveform.
    Applies software Automatic Gain Control (AGC) and optional noise reduction.
    """
    audio_np = np.frombuffer(audio_bytes, dtype=np.int16).astype(np.float32) / 32768.0

    # 1. Noise Reduction (spectral gating)
    if ENABLE_NOISE_REDUCTION and HAS_NOISEREDUCE and len(audio_np) >= SAMPLE_RATE // 2:
        try:
            audio_np = nr.reduce_noise(
                y=audio_np,
                sr=SAMPLE_RATE,
                stationary=True,
                prop_decrease=0.60,
                n_fft=512,
            )
        except Exception:
            pass

    # 2. Software AGC Peak Normalization (-16 dBFS target peak ~0.65)
    max_amp = float(np.max(np.abs(audio_np)))
    if max_amp > 0.01:
        target_peak = 0.65
        gain = min(target_peak / max_amp, 4.0)  # max 4x gain boost
        audio_np = np.clip(audio_np * gain, -1.0, 1.0)

    return audio_np


# ─── Telemetry Logger ─────────────────────────────────────────────────────────

def _log_voice_telemetry(audio_sec: float, latency_ms: float, avg_logprob: float,
                         no_speech_prob: float, raw_text: str, normalized_text: str,
                         source: str = "wake_word"):
    try:
        entry = {
            "timestamp": datetime.datetime.now().isoformat(),
            "source": source,
            "audio_duration_sec": round(audio_sec, 2),
            "stt_latency_ms": round(latency_ms, 1),
            "avg_logprob": round(avg_logprob, 3),
            "no_speech_prob": round(no_speech_prob, 3),
            "raw_text": raw_text,
            "normalized_text": normalized_text,
        }
        with open(VOICE_LOG, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")
    except Exception:
        pass


# ─── Transcription API ────────────────────────────────────────────────────────

def transcribe_with_meta(audio_bytes: bytes, source: str = "utterance") -> tuple[str, str, float, float, float]:
    """
    Transcribe raw PCM bytes with faster-whisper.
    Returns: (normalized_text, raw_text, avg_logprob, no_speech_prob, latency_ms)
    """
    if not audio_bytes or len(audio_bytes) < 3200:  # < 100ms
        return "", "", 0.0, 1.0, 0.0

    t_start = time.perf_counter()
    audio_sec = len(audio_bytes) / (SAMPLE_RATE * 2)

    try:
        model = _get_whisper()
        audio_np = _clean_and_normalize_audio(audio_bytes)

        if float(np.max(np.abs(audio_np))) < 0.003:
            return "", "", 0.0, 1.0, 0.0

        segments, info = model.transcribe(
            audio_np,
            language=WHISPER_LANGUAGE or "en",
            beam_size=WHISPER_BEAM_SIZE,
            initial_prompt=WHISPER_INITIAL_PROMPT,
            condition_on_previous_text=False,
            vad_filter=False,  # endpointing already managed cleanly by VAD
        )

        raw_parts = []
        logprobs = []
        no_speech_probs = []

        for seg in segments:
            txt = seg.text.strip()
            if txt:
                raw_parts.append(txt)
                logprobs.append(seg.avg_logprob)
                no_speech_probs.append(getattr(seg, "no_speech_prob", 0.0))

        raw_text = " ".join(raw_parts).strip()
        avg_lp = float(np.mean(logprobs)) if logprobs else -1.0
        no_speech = float(np.max(no_speech_probs)) if no_speech_probs else 0.0
        latency_ms = (time.perf_counter() - t_start) * 1000.0

        normalized_text = normalize_transcript(raw_text)

        _log_voice_telemetry(audio_sec, latency_ms, avg_lp, no_speech, raw_text, normalized_text, source=source)
        logger.info(f"STT [{source}]: {raw_text!r} → {normalized_text!r} ({latency_ms:.0f}ms, lp={avg_lp:.2f})")

        return normalized_text, raw_text, avg_lp, no_speech, latency_ms

    except Exception as e:
        logger.error(f"Transcription error: {e}")
        return "", "", -9.0, 1.0, 0.0


def transcribe(audio_bytes: bytes) -> str:
    """Standard STT returning normalized string."""
    norm, _, _, _, _ = transcribe_with_meta(audio_bytes, source="stt")
    return norm


# ─── VAD Recording with 300ms Pre-Roll & Endpointing ──────────────────────────

def _rms_to_meter(rms: float, ambient: float) -> str:
    diff = max(0.0, rms - ambient)
    scale = max(ambient * 1.5, 80.0)
    bars = int(min(6, (diff / scale) * 4))
    if bars <= 0:
        return "▪"
    return "▰" * bars + "▱" * (6 - bars)


class _InterimTranscriber:
    """Streaming background worker for live interim transcription feedback."""
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
    pre_roll_chunks: list[bytes] | None = None,
    on_interim: Callable[[str], None] | None = None,
    stop_event: threading.Event | None = None,
) -> bytes:
    """
    Records audio until speech completes or silence timeout occurs.
    Prepends the 300ms pre-roll buffer so starting consonants are never cut off.
    Includes echo-gating check and live meter visual callback.
    """
    frames: list[bytes] = []
    # Prepend pre-roll buffer if provided
    if pre_roll_chunks:
        frames.extend(pre_roll_chunks)

    silence_frames = 0
    # 500-700ms endpointing (22 frames of 30ms = 660ms)
    silence_limit = int((0.55 if is_ptt else SILENCE_TIMEOUT_SEC) * 1000 / CHUNK_MS)
    max_frames = int((8.0 if is_ptt else MAX_RECORD_SEC) * 1000 / CHUNK_MS)
    wait_start_limit = int((4.0 if is_ptt else 2.8) * 1000 / CHUNK_MS)
    total_frames = 0
    speech_started = bool(pre_roll_chunks and len(pre_roll_chunks) > 0)
    voiced_count = 1 if speech_started else 0

    interim_worker = None
    interim_text = [""]
    if on_interim:
        def _update_text(t: str):
            interim_text[0] = t
            on_interim(f'"{t}…" 🎙️')
        interim_worker = _InterimTranscriber(_update_text)

    last_ui_update = 0.0
    last_interim_submit = 0.0
    ambient_rms = 120.0

    while total_frames < max_frames:
        if stop_event and stop_event.is_set():
            break

        chunk = _read_chunk(stream)
        frames.append(chunk)
        total_frames += 1

        # Echo-Gating: If JARVIS is currently speaking, check for barge-in interruption
        if speaker.is_speaking():
            samples = np.frombuffer(chunk, dtype=np.int16)
            rms = float(np.sqrt(np.mean(samples.astype(np.float32) ** 2)))
            # Very loud voice during TTS = user trying to barge in
            if rms > 800.0 and len(frames) >= 15:
                # Transcribe small window to see if user said 'stop'
                quick_txt = transcribe(b"".join(frames[-15:])).lower()
                if any(w in quick_txt for w in ("stop", "quiet", "hush", "cancel", "shut")):
                    speaker.stop_speaking()
                    logger.info("Barge-in detected: interrupted TTS.")
                    return b""
            # Otherwise drop speech while TTS is playing to avoid self-echo loop
            continue

        samples = np.frombuffer(chunk, dtype=np.int16)
        rms = float(np.sqrt(np.mean(samples.astype(np.float32) ** 2)))
        now = time.time()

        try:
            vad_flag = vad.is_speech(chunk, SAMPLE_RATE)
        except Exception:
            vad_flag = False

        voice_thresh = max(180.0, ambient_rms * 1.3)
        is_voice = (vad_flag and rms > voice_thresh) or (rms > max(320.0, ambient_rms * 1.5))

        if is_voice:
            voiced_count += 1
            if voiced_count >= 2:
                speech_started = True
            silence_frames = 0
        else:
            ambient_rms = 0.95 * ambient_rms + 0.05 * rms
            if speech_started:
                silence_frames += 1
                if silence_frames >= silence_limit:
                    break
            else:
                if total_frames >= wait_start_limit:
                    break

        if on_interim and (now - last_ui_update > 0.1):
            last_ui_update = now
            meter = _rms_to_meter(rms, ambient_rms)
            if speech_started:
                if interim_text[0]:
                    on_interim(f'"{interim_text[0]}…" {meter}')
                else:
                    on_interim(f"🎙️ Hearing you… {meter}")
            else:
                on_interim(f"🎙️ Listening… {meter}")

        # Stream audio to interim transcriber every 0.7s
        if interim_worker and speech_started and (now - last_interim_submit > 0.7) and len(frames) >= 20:
            last_interim_submit = now
            interim_worker.submit(b"".join(frames))

    if interim_worker:
        interim_worker.stop()

    return b"".join(frames)


# ─── Main Listener Class ──────────────────────────────────────────────────────

class Listener:
    """
    Hands-free autonomous listener supporting openWakeWord, Silero/WebRTC VAD,
    pre-roll buffers, noise suppression, follow-up conversation mode, and barge-in.
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
        self._on_command: Callable[[str], None] | None = None

        # Follow-up conversation mode (6 seconds window after JARVIS speaks)
        self._followup_deadline = 0.0
        self._is_in_followup = False

    def pause(self):
        """Mute listener (e.g. while audio playback is active)."""
        self._paused = True

    def resume(self):
        """Resume listener."""
        self._paused = False

    def enter_followup_mode(self, timeout: float = CONVERSATION_FOLLOWUP_SEC):
        """Keep the microphone active for follow-up questions without wake word."""
        self._followup_deadline = time.time() + timeout
        self._is_in_followup = True
        logger.info(f"Follow-up conversation window open for {timeout}s.")

    def exit_followup_mode(self):
        self._is_in_followup = False
        self._followup_deadline = 0.0

    def start(self, on_command: Callable[[str], None]):
        """Start the background listening thread."""
        self._running = True
        self._on_command = on_command
        self._thread = threading.Thread(target=self._loop, daemon=True, name="jarvis_listener")
        self._thread.start()
        logger.info("Next-Gen Voice Listener started.")

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=3)

    def _loop(self):
        # 300ms pre-roll buffer = 10 chunks of 30ms
        pre_roll_count = max(5, int(VAD_PRE_ROLL_MS / CHUNK_MS))
        pre_roll: collections.deque = collections.deque(maxlen=pre_roll_count)

        # 80ms chunk size for openWakeWord = 1280 samples
        oww_chunk_samples = int(SAMPLE_RATE * 0.08)
        oww_buffer = bytearray()

        pa, stream = _open_mic()
        self._pa = pa
        self._stream = stream

        try:
            while self._running:
                if self._paused or speaker.is_speaking():
                    pre_roll.clear()
                    oww_buffer.clear()
                    time.sleep(0.04)
                    continue

                chunk = _read_chunk(stream)
                pre_roll.append(chunk)

                # ── 1. Check Follow-Up Conversation Mode ──────────────────────
                now = time.time()
                if self._is_in_followup:
                    if now < self._followup_deadline:
                        # Direct speech detection without requiring wake word
                        try:
                            vad_flag = self._vad.is_speech(chunk, SAMPLE_RATE)
                        except Exception:
                            vad_flag = False

                        samples = np.frombuffer(chunk, dtype=np.int16)
                        rms = float(np.sqrt(np.mean(samples.astype(np.float32) ** 2)))

                        if vad_flag and rms > 220.0:
                            logger.info("Follow-up speech detected! Recording utterance…")
                            self.exit_followup_mode()
                            with self._mic_lock:
                                raw = _record_until_silence(
                                    stream, self._vad, is_ptt=False,
                                    pre_roll_chunks=list(pre_roll)
                                )
                            pre_roll.clear()
                            text, raw_t, avg_lp, no_speech, lat = transcribe_with_meta(raw, source="follow_up")
                            if text:
                                if avg_lp < CONFIDENCE_THRESHOLD and len(text.split()) <= 2:
                                    speaker.speak("I didn't quite catch that, sir. Could you repeat?")
                                elif self._on_command:
                                    self._on_command(text)
                            continue
                    else:
                        self.exit_followup_mode()

                # ── 2. Wake Word Detection (openWakeWord ONNX) ─────────────────
                detected = False
                embedded_cmd = None

                if self._use_oww and _oww_model:
                    oww_buffer.extend(chunk)
                    # When buffer reaches 80ms (2560 bytes = 1280 int16 samples)
                    if len(oww_buffer) >= oww_chunk_samples * 2:
                        pcm_80ms = np.frombuffer(oww_buffer[:oww_chunk_samples * 2], dtype=np.int16)
                        oww_buffer = oww_buffer[oww_chunk_samples * 2:]
                        try:
                            scores = _oww_model.predict(pcm_80ms)
                            for name, score in scores.items():
                                if score >= WAKE_WORD_THRESHOLD:
                                    logger.info(f"openWakeWord detected: {name} (score={score:.2f})")
                                    detected = True
                                    break
                        except Exception:
                            pass
                else:
                    # Fallback acoustic detection
                    samples = np.frombuffer(chunk, dtype=np.int16)
                    rms = float(np.sqrt(np.mean(samples.astype(np.float32) ** 2)))
                    try:
                        vad_flag = self._vad.is_speech(chunk, SAMPLE_RATE)
                    except Exception:
                        vad_flag = False

                    if vad_flag and rms > 300.0:
                        # Read utterance and check for wake word
                        raw_test = _record_until_silence(stream, self._vad, is_ptt=False, pre_roll_chunks=list(pre_roll))
                        pre_roll.clear()
                        txt, _, _, _, _ = transcribe_with_meta(raw_test, source="wake_scan")
                        txt_lower = txt.lower()
                        for alias in WAKE_WORD_ALIASES:
                            if re.search(rf"\b{alias}\b", txt_lower):
                                detected = True
                                parts = re.split(rf"\b{alias}\b", txt, flags=re.IGNORECASE)
                                if len(parts) > 1 and len(parts[1].strip()) > 2:
                                    embedded_cmd = parts[1].strip(" ,.!?:\n\t")
                                break

                if not detected:
                    continue

                # ── 3. Wake Word Fired: Record Command ─────────────────────────
                logger.info("Wake word triggered!")
                try:
                    import winsound
                    winsound.Beep(1400, 60)
                except Exception:
                    pass

                if embedded_cmd:
                    logger.info(f"Inline command recognized: {embedded_cmd!r}")
                    if self._on_command:
                        self._on_command(embedded_cmd)
                else:
                    with self._mic_lock:
                        raw = _record_until_silence(stream, self._vad, is_ptt=False, pre_roll_chunks=list(pre_roll))
                    pre_roll.clear()

                    text, raw_t, avg_lp, no_speech, lat = transcribe_with_meta(raw, source="wake_command")
                    if text:
                        # Confidence check
                        if avg_lp < CONFIDENCE_THRESHOLD and len(text.split()) <= 2:
                            speaker.speak("I didn't quite catch that, sir. Could you repeat?")
                        elif self._on_command:
                            self._on_command(text)

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

    # ── Push-to-Talk Recording API ────────────────────────────────────────────

    def push_to_talk_record(
        self,
        on_interim: Callable[[str], None] | None = None,
        on_recording_done: Callable[[], None] | None = None,
        stop_event: threading.Event | None = None,
    ) -> str:
        """
        Records from microphone until silence, transcribes with corrections,
        and returns normalized command string.
        """
        logger.info("Push-to-Talk triggered.")
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

        norm, raw_t, avg_lp, _, lat = transcribe_with_meta(raw, source="ptt")
        return norm
