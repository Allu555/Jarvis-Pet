"""
config.py – Central configuration for JARVIS.
All tunable settings live here; import this module everywhere.

Brain: NVIDIA NIM (free 1000 credits/month) — OpenAI-compatible API.
Get a free key at: https://build.nvidia.com → Sign in → Get API Key
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# ─── Load .env file if present ────────────────────────────────────────────────
load_dotenv(dotenv_path=Path(__file__).parent / ".env", override=True)

# ─── Paths ────────────────────────────────────────────────────────────────────
BASE_DIR        = Path(__file__).parent
LOG_DIR         = BASE_DIR / "logs"
MEMORY_DIR      = BASE_DIR / "memory_store"
ALLOWED_FILE_DIR = Path.home() / "JarvisFiles"   # sandboxed file-ops directory

LOG_DIR.mkdir(exist_ok=True)
MEMORY_DIR.mkdir(exist_ok=True)
ALLOWED_FILE_DIR.mkdir(exist_ok=True)

ACTION_LOG      = LOG_DIR / "actions.log"
MEMORY_FILE     = MEMORY_DIR / "user_memory.json"

# ─── API Keys ─────────────────────────────────────────────────────────────────
ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")   # kept for reference
NVIDIA_API_KEY:    str = os.getenv("NVIDIA_API_KEY", "")

# ─── NVIDIA NIM (free brain — 1000 credits/month) ─────────────────────────────
# Free key at: https://build.nvidia.com → Sign in → Get API Key
NVIDIA_BASE_URL      = "https://integrate.api.nvidia.com/v1"
NVIDIA_MODEL         = "meta/llama-3.2-11b-vision-instruct"       # verified active free model
NVIDIA_VISION_MODEL  = "meta/llama-3.2-11b-vision-instruct"       # for screenshots

MAX_AGENT_STEPS = 15                        # max tool calls per command

# ─── Wake word ────────────────────────────────────────────────────────────────
WAKE_WORD = "jarvis"                        # primary wake word
WAKE_WORD_ALIASES = [                       # phonetic matches & accent variations
    "jarvis", "service", "harvest", "javis", "charvis", "darvis", "jarves", "sarvis",
    "jaarvis", "jarvish", "jervis", "zarvis"
]

# ─── Audio ────────────────────────────────────────────────────────────────────
SAMPLE_RATE         = 16000                 # Hz – required by Whisper + webrtcvad
CHUNK_MS            = 30                    # ms per VAD frame (10 / 20 / 30 only)
CHUNK_SAMPLES       = SAMPLE_RATE * CHUNK_MS // 1000
VAD_AGGRESSIVENESS  = 1                     # 1 = balanced, prevents cutting off quiet speech or syllables
SILENCE_TIMEOUT_SEC = 1.0                   # 1.0s silence allows natural breathing between words
MAX_RECORD_SEC      = 10                    # max 10s gives comfortable time for full commands

# ─── STT (faster-whisper) ─────────────────────────────────────────────────────
WHISPER_MODEL_SIZE  = "tiny.en"              # tiny.en = 3x faster transcription on CPU (~0.4s)
WHISPER_DEVICE      = "cpu"                 # "cuda" if NVIDIA GPU available
WHISPER_COMPUTE     = "int8"                # int8 fastest on CPU
WHISPER_LANGUAGE    = "en"                  # English default; avoids language auto-detection crash
WHISPER_CPU_THREADS = 6                     # 6 threads = optimal performance on 8-core CPU

# ─── TTS ──────────────────────────────────────────────────────────────────────
EDGE_TTS_VOICE      = "en-IN-PrabhatNeural" # Indian English male voice (natural, crisp)
PYTTSX3_RATE        = 175                   # words-per-minute for fallback TTS

# ─── Hotkeys ──────────────────────────────────────────────────────────────────
PTT_HOTKEY   = "ctrl+alt+space"             # push-to-talk
KILL_HOTKEY  = "ctrl+alt+q"                # emergency kill
STOP_HOTKEY  = "ctrl+alt+s"                # stop speaking

# ─── PyAutoGUI ────────────────────────────────────────────────────────────────
PYAUTOGUI_PAUSE    = 0.01                   # 0.01s eliminates pauses and cursor lag
PYAUTOGUI_FAILSAFE = False                  # False so corner cursor doesn't trigger crash

# ─── UI overlay ───────────────────────────────────────────────────────────────
OVERLAY_WIDTH  = 360
OVERLAY_HEIGHT = 140
OVERLAY_OPACITY = 0.88                      # 0.0–1.0
OVERLAY_BG     = "#0d0d0d"
OVERLAY_FG     = "#00e5ff"

# ─── System tray ──────────────────────────────────────────────────────────────
TRAY_TOOLTIP = "JARVIS Assistant"

# ─── Safety ───────────────────────────────────────────────────────────────────
# Shell commands whose substrings trigger confirmation
DANGEROUS_PATTERNS = [
    "format", "rm -rf", "del /f", "rd /s", "reg delete",
    "shutdown", "taskkill", ":(){", "dd if=", "mkfs",
    "net user", "netsh", "cipher /w",
]
# Extensions that need confirmation before deletion
SENSITIVE_EXTENSIONS = {".docx", ".pdf", ".xlsx", ".py", ".env", ".json"}

# ─── Application shortcuts (Windows-specific, isolated here) ──────────────────
# Keys: friendly names Claude might use; Values: executable or path
APP_MAP: dict[str, str] = {
    "chrome":         r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    "google chrome":  r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    "brave":          "brave.exe",
    "brave browser":  "brave.exe",
    "edge":           "msedge.exe",
    "microsoft edge": "msedge.exe",
    "firefox":        r"C:\Program Files\Mozilla Firefox\firefox.exe",
    "notepad":        "notepad.exe",
    "not bad":        "notepad.exe",
    "not pad":        "notepad.exe",
    "note pad":       "notepad.exe",
    "not tab":        "notepad.exe",
    "northbound":     "notepad.exe",
    "notepad++":      r"C:\Program Files\Notepad++\notepad++.exe",
    "vs code":        r"C:\Users\{user}\AppData\Local\Programs\Microsoft VS Code\Code.exe",
    "vscode":         r"C:\Users\{user}\AppData\Local\Programs\Microsoft VS Code\Code.exe",
    "code":           r"C:\Users\{user}\AppData\Local\Programs\Microsoft VS Code\Code.exe",
    "word":           r"C:\Program Files\Microsoft Office\root\Office16\WINWORD.EXE",
    "excel":          r"C:\Program Files\Microsoft Office\root\Office16\EXCEL.EXE",
    "powerpoint":     r"C:\Program Files\Microsoft Office\root\Office16\POWERPNT.EXE",
    "spotify":        r"C:\Users\{user}\OneDrive\Desktop\Spotify.lnk",
    "spottify":       r"C:\Users\{user}\OneDrive\Desktop\Spotify.lnk",
    "support design": r"C:\Users\{user}\OneDrive\Desktop\Spotify.lnk",
    "sportify":       r"C:\Users\{user}\OneDrive\Desktop\Spotify.lnk",
    "spotty":         r"C:\Users\{user}\OneDrive\Desktop\Spotify.lnk",
    "calculator":     "ms-calculator:",
    "calc":           "ms-calculator:",
    "calculater":     "ms-calculator:",
    "calcy":          "ms-calculator:",
    "paint":          "mspaint.exe",
    "settings":       "ms-settings:",
    "camera":         "microsoft.windows.camera:",
    "explorer":       "explorer.exe",
    "file explorer":  "explorer.exe",
    "task manager":   "taskmgr.exe",
    "terminal":       "cmd.exe",
    "cmd":            "cmd.exe",
    "powershell":     "powershell.exe",
    "vlc":            r"C:\Program Files\VideoLAN\VLC\vlc.exe",
    "telegram":       r"C:\Users\{user}\AppData\Roaming\Telegram Desktop\Telegram.exe",
    "discord":        r"C:\Users\{user}\AppData\Local\Discord\app-*\Discord.exe",
    "zoom":           r"C:\Users\{user}\AppData\Roaming\Zoom\bin\Zoom.exe",
    "teams":          r"C:\Users\{user}\AppData\Local\Microsoft\Teams\current\Teams.exe",
    "obs":            r"C:\Program Files\obs-studio\bin\64bit\obs64.exe",
    "youtube":        "https://www.youtube.com",
    "you tube":       "https://www.youtube.com",
    "u tube":         "https://www.youtube.com",
    "google":         "https://www.google.com",
    "gmail":          "https://mail.google.com",
    "github":         "https://github.com",
    "reddit":         "https://www.reddit.com",
    "chatgpt":        "https://chatgpt.com",
    "netflix":        "https://www.netflix.com",
    "whatsapp":       "https://web.whatsapp.com",
    "instagram":      "https://www.instagram.com",
    "twitter":        "https://x.com",
    "x":              "https://x.com",
    "amazon":         "https://www.amazon.in",
    "flipkart":       "https://www.flipkart.com",
    "linkedin":       "https://www.linkedin.com",
    "maps":           "https://maps.google.com",
    "hotstar":        "https://www.hotstar.com",
    "prime video":    "https://www.primevideo.com",
    "canva":          "https://www.canva.com",
}

# Fill {user} with the actual username
_user = os.getenv("USERNAME", "User")
APP_MAP = {k: v.replace("{user}", _user) for k, v in APP_MAP.items()}

