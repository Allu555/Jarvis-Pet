"""
main.py – JARVIS entry point.

Wires together:
  - Listener  (wake word + VAD + STT)
  - Speaker   (edge-tts / pyttsx3)
  - Agent     (Claude tool-use loop)
  - Overlay   (tkinter status window)
  - Tray      (system tray icon)
  - Hotkeys   (PTT, kill switch, stop-speech)

Run with:  python main.py
"""

import logging
import sys
import threading
import time
from pathlib import Path

# Force UTF-8 on Windows console for ₹ (Rupee), Hindi, emojis, etc.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# ── Project root on path ──────────────────────────────────────────────────────
sys.path.insert(0, str(Path(__file__).parent))

# ── Logging (console + file) ──────────────────────────────────────────────────
from config import ACTION_LOG, LOG_DIR

LOG_DIR.mkdir(exist_ok=True)

_handlers = [logging.FileHandler(LOG_DIR / "jarvis.log", encoding="utf-8")]
if sys.stdout is not None:
    _handlers.append(logging.StreamHandler(sys.stdout))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=_handlers,
)
logger = logging.getLogger("jarvis.main")

# ── Imports (after logging is set up) ─────────────────────────────────────────
import keyboard                              # type: ignore

from config import PTT_HOTKEY, STOP_HOTKEY, WAKE_WORD, NVIDIA_API_KEY
from memory import Memory
from safety import register_kill_hotkey, is_killed, reset_kill
from audio.listener import Listener
from audio.speaker  import speak, stop_speaking, reset_stop
from brain.agent    import run_agent
from ui.overlay     import Overlay, start_tray


# ─── Validate NVIDIA API key early ──────────────────────────────────────────
if not NVIDIA_API_KEY:
    logger.error("NVIDIA_API_KEY not set. Get a free key at https://build.nvidia.com")
    sys.exit(1)


# ─── Global state ─────────────────────────────────────────────────────────────
memory   = Memory()
listener = Listener()
overlay  = Overlay(on_submit=lambda text: threading.Thread(target=handle_command, args=(text,), daemon=True).start())
_paused  = threading.Event()   # set → paused


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _status(msg: str):
    overlay.set_status(msg)
    logger.debug(f"Status: {msg}")


def _speak(text: str):
    _status("Speaking…")
    overlay.set_response(text[:120])
    listener.pause()
    try:
        speak(text)
    finally:
        time.sleep(0.35)
        listener.resume()
        _status("Idle")


def _listen_short() -> str:
    """Record a short confirmation utterance (used in safety confirmations)."""
    try:
        return listener.push_to_talk_record()
    except Exception:
        return ""


# ─── Command handler ──────────────────────────────────────────────────────────

def handle_command(text: str):
    """Called by the listener when a command is transcribed."""
    if _paused.is_set():
        return
    if not text.strip():
        return
    if is_killed():
        reset_kill()

    # Handle "stop" as an interrupt
    if text.strip().lower() in ("stop", "stop it", "be quiet", "shut up"):
        stop_speaking()
        return

    logger.info(f"Command received: {text!r}")
    overlay.set_command(text)
    _status("Thinking…")

    try:
        run_agent(
            user_command=text,
            memory=memory,
            speak_fn=_speak,
            listen_fn=_listen_short,
            status_fn=_status,
        )
    except Exception as e:
        logger.error(f"Agent error: {e}", exc_info=True)
        _speak("I hit an unexpected error. Please try again.")
    finally:
        _status("Idle")


# ─── Hotkeys ──────────────────────────────────────────────────────────────────

def _register_hotkeys():
    # Stop speech
    keyboard.add_hotkey(STOP_HOTKEY, stop_speaking, suppress=False)
    logger.info(f"Stop-speech hotkey: {STOP_HOTKEY}")

    # Push-to-talk
    _ptt_lock = threading.Lock()
    _ptt_stop_event = threading.Event()

    def _ptt_pressed():
        if _paused.is_set():
            return
        if not _ptt_lock.acquire(blocking=False):
            # If already recording, pressing hotkey again stops recording immediately
            _ptt_stop_event.set()
            return
        _ptt_stop_event.clear()
        try:
            _status("Listening (PTT)…")
            overlay.set_command("🎙️ Listening… (speak now)")
            try:
                import winsound
                winsound.Beep(1200, 80)
            except Exception:
                pass

            def _on_done_recording():
                _status("Transcribing…")

            def _on_live_text(live_str: str):
                overlay.set_command(live_str)

            text = listener.push_to_talk_record(
                on_interim=_on_live_text,
                on_recording_done=_on_done_recording,
                stop_event=_ptt_stop_event,
            )
            if text:
                overlay.set_command(text)
                _status("Thinking…")
                threading.Thread(target=handle_command, args=(text,), daemon=True).start()
            else:
                overlay.set_command("—")
                _status("Idle")
        finally:
            _ptt_lock.release()

    keyboard.add_hotkey(PTT_HOTKEY, _ptt_pressed, suppress=False)
    logger.info(f"PTT hotkey: {PTT_HOTKEY}")


# ─── Tray callbacks ───────────────────────────────────────────────────────────

def _pause():
    _paused.set()
    _status("Paused")
    logger.info("JARVIS paused.")


def _resume():
    _paused.clear()
    _status("Idle")
    logger.info("JARVIS resumed.")


def _quit():
    logger.info("Quit requested.")
    overlay.destroy()
    listener.stop()
    sys.exit(0)


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    logger.info("=" * 60)
    logger.info("  JARVIS starting up …")
    logger.info("=" * 60)

    # Safety kill switch
    register_kill_hotkey()

    # Register PTT and stop-speech hotkeys
    _register_hotkeys()

    # Start system tray
    start_tray(_pause, _resume, _quit)

    # Greet the user
    name = memory.user_name
    greeting = (
        f"Namaskaram {name}! JARVIS online. "
        f"Say '{WAKE_WORD}' to activate, or press Control Alt Space to talk."
    )
    _speak(greeting)
    _status("Idle")

    # Start always-on listener in background thread
    listener.start(
        on_command=lambda text: threading.Thread(
            target=handle_command, args=(text,), daemon=True
        ).start()
    )

    logger.info("Listener active. Waiting for wake word …")

    try:
        print("\n" + "=" * 62)
        print("  JARVIS IS READY!")
        print("  • Talk: Say 'Jarvis ...' or press Ctrl+Alt+Space (PTT)")
        print("  • Type: Enter commands below OR in the floating overlay")
        print("  • Quit: Type 'exit' or press Ctrl+C")
        print("=" * 62 + "\n")
    except Exception:
        pass

    # Check if running in an interactive terminal
    is_interactive = False
    try:
        is_interactive = (
            sys.stdin is not None
            and hasattr(sys.stdin, "isatty")
            and sys.stdin.isatty()
        )
    except Exception:
        is_interactive = False

    try:
        while True:
            if not is_interactive:
                time.sleep(1)
                continue

            try:
                user_text = input("You > ").strip()
                if not user_text:
                    continue
                if user_text.lower() in ("exit", "quit", "q"):
                    _quit()
                    break
                threading.Thread(target=handle_command, args=(user_text,), daemon=True).start()
            except (EOFError, RuntimeError, OSError):
                is_interactive = False
                time.sleep(1)
    except KeyboardInterrupt:
        logger.info("KeyboardInterrupt – shutting down.")
        _quit()


if __name__ == "__main__":
    main()
