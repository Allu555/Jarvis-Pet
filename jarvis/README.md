# JARVIS – Voice-Controlled Desktop AI Assistant

> A local, always-on JARVIS-style assistant powered by **Claude claude-sonnet-4-5** (Anthropic), **faster-whisper** STT, and **edge-tts** voice. Runs entirely on your Windows 11 laptop with full computer-control capabilities.

---

## 📁 File Structure

```
jarvis/
├── main.py                  ← Entry point
├── config.py                ← All settings & constants
├── safety.py                ← Confirmations, blocklist, kill-switch
├── memory.py                ← Persistent user memory + session history
├── requirements.txt
├── .env.example
│
├── audio/
│   ├── listener.py          ← Wake word, VAD, Whisper STT
│   └── speaker.py           ← edge-tts + pyttsx3 TTS
│
├── brain/
│   ├── agent.py             ← Claude tool-use agent loop
│   └── tools.py             ← Tool schemas + dispatcher
│
├── control/
│   ├── apps.py              ← Open/close applications
│   ├── keyboard_mouse.py    ← Typing, hotkeys, mouse
│   ├── vision.py            ← Screenshot + Claude Vision
│   ├── files.py             ← Sandboxed file operations
│   └── system.py            ← Volume, brightness, browser, shell
│
├── ui/
│   └── overlay.py           ← tkinter status overlay + tray icon
│
├── logs/
│   ├── jarvis.log           ← Runtime log
│   └── actions.log          ← Every action with timestamp
│
└── memory_store/
    └── user_memory.json     ← Persistent user facts & preferences
```

---

## 🔑 Getting Your Anthropic API Key

1. Go to **https://console.anthropic.com/settings/keys**
2. Sign up / log in
3. Click **"Create Key"** → copy the `sk-ant-...` string
4. Paste it in your `.env` file (see below)

---

## ⚙️ Setup Instructions (Windows 11, Python 3.11+)

### Step 1 – Install Python 3.11+

Download from **https://python.org** — check **"Add to PATH"** during install.

```powershell
python --version   # should show 3.11 or higher
```

### Step 2 – Install FFmpeg

```powershell
winget install Gyan.FFmpeg
# Then open a NEW terminal and verify:
ffmpeg -version
```

If `winget` isn't available, download from **https://ffmpeg.org/download.html** and add the `bin/` folder to your system PATH manually.

### Step 3 – Install PyAudio (tricky on Windows)

```powershell
pip install pipwin
pipwin install pyaudio
```

If that fails, download the matching `.whl` from:
**https://www.lfd.uci.edu/~gohlke/pythonlibs/#pyaudio**

Example for Python 3.11 64-bit:
```powershell
pip install PyAudio-0.2.14-cp311-cp311-win_amd64.whl
```

### Step 4 – Install all other dependencies

```powershell
cd path\to\jarvis
pip install -r requirements.txt
```

### Step 5 – Configure your API key

```powershell
copy .env.example .env
# Now open .env in Notepad and paste your Anthropic key
notepad .env
```

### Step 6 – (Optional) Install nircmd for precise volume control

Download **nircmd.exe** from **https://www.nirsoft.net/utils/nircmd.html**
Copy it to `C:\Windows\System32\`

### Step 7 – Run JARVIS!

```powershell
python main.py
```

On first run, faster-whisper will download the `small` model (~500 MB). This only happens once.

---

## 🎤 Voice Commands – Examples

### Easy
| Say | What happens |
|-----|-------------|
| "Jarvis, open Calculator" | Launches Windows Calculator |
| "Jarvis, what time is it?" | Speaks current time and date |
| "Jarvis, take a screenshot" | Saves PNG to your Desktop |
| "Jarvis, volume up" | Increases system volume |
| "Jarvis, mute" | Toggles mute |

### Medium
| Say | What happens |
|-----|-------------|
| "Jarvis, open Notepad and type Hello World" | Opens Notepad, types text |
| "Jarvis, search Google for Python tutorials" | Opens browser with search |
| "Jarvis, set a timer for 5 minutes" | Fires spoken alert after 5 min |
| "Jarvis, what's on my screen right now?" | Describes screen with AI Vision |
| "Jarvis, open Chrome and go to youtube.com" | Launches Chrome, navigates |

### Complex (multi-step)
| Say | What happens |
|-----|-------------|
| "Jarvis, open Notepad, write a leave application for tomorrow, and save it as leave.txt" | Full multi-step task |
| "Jarvis, open Chrome, search for today's weather in Kochi, and read me the result" | Search + Vision + speech |
| "Jarvis, minimize all windows, then take a screenshot of the desktop" | Win+D + screenshot |
| "Jarvis, check my battery and tell me if I need to charge" | Battery status + advice |
| "Jarvis, create a folder called Projects in JarvisFiles and make a file called ideas.txt inside it" | Nested file ops |

---

## ⌨️ Hotkeys

| Hotkey | Action |
|--------|--------|
| **Ctrl+Alt+Space** | Push-to-talk (speak without wake word) |
| **Ctrl+Alt+S** | Stop speaking immediately |
| **Ctrl+Alt+Q** | Emergency kill – stops ALL actions instantly |

---

## 🛡️ Safety Features

- **File deletion**: Always asks "Are you sure? Say yes or no."
- **Shell commands**: Dangerous patterns are blocked; suspicious ones require confirmation
- **PyAutoGUI failsafe**: Move mouse to **top-left corner** to abort any automation
- **Sandboxed files**: File operations are restricted to `~/JarvisFiles/`
- **No passwords**: JARVIS never reads out or stores password-related content
- **Action log**: Every action logged to `logs/actions.log` with timestamp

---

## 🖥️ UI Overlay

The small always-on-top overlay shows:
- **Status**: Idle / Listening / Thinking / Acting / Speaking
- **Last command** you said
- **Last response** from JARVIS

Drag it anywhere on screen by clicking and dragging. Close with the ✕ button.

The **system tray icon** (bottom-right) has Pause / Resume / Quit options.

---

## 🔧 Troubleshooting

### ❌ "Microphone not detected" / PyAudio error

```powershell
# List audio devices
python -c "import pyaudio; p=pyaudio.PyAudio(); [print(i, p.get_device_info_by_index(i)['name']) for i in range(p.get_device_count())]"
```

Set your default recording device in Windows Sound Settings → Input.

### ❌ Clicks landing in wrong place (high-DPI / 4K screen)

The DPI awareness is set automatically in `control/keyboard_mouse.py`. If clicks are still off:

1. Right-click `python.exe` → Properties → Compatibility → Change high DPI settings
2. Check "Override high DPI scaling behavior" → select "Application"
3. Alternatively, set the monitor to 100% scaling in Display Settings

### ❌ "ANTHROPIC_API_KEY not set"

Make sure your `.env` file is in the `jarvis/` directory (same folder as `main.py`) and contains:
```
ANTHROPIC_API_KEY=sk-ant-your-actual-key
```

### ❌ Wake word not working

The system falls back to Whisper-based keyword detection if openWakeWord is unavailable. Speak clearly: **"Jarvis"** followed by a short pause before your command.

### ❌ edge-tts not speaking

Check internet connectivity (edge-tts requires internet). JARVIS automatically falls back to pyttsx3 (offline) if edge-tts fails.

### ❌ faster-whisper download fails

The model downloads on first run. If it fails, download manually:
```powershell
python -c "from faster_whisper import WhisperModel; WhisperModel('small')"
```

### ❌ "Cannot import openwakeword"

Run:
```powershell
pip install openwakeword onnxruntime
```

JARVIS works fine without it — it just uses Whisper for wake-word detection instead.

---

## 🧪 10-Command Test Plan

Run these in order after starting JARVIS. Each tests progressively more capability.

| # | Command | Expected behaviour | Tests |
|---|---------|-------------------|-------|
| 1 | *"Jarvis, what time is it?"* | Speaks current time/date | API connection, TTS |
| 2 | *"Jarvis, open Calculator"* | Calculator window opens | App launch |
| 3 | *"Jarvis, take a screenshot"* | Saves PNG to Desktop | System control |
| 4 | *"Jarvis, volume up"* | Volume increases | System, no confirmation |
| 5 | *"Jarvis, open Notepad and type Hello from JARVIS"* | Notepad opens, text typed | Multi-step, keyboard |
| 6 | *"Jarvis, press Control S to save, then close Notepad"* | Saves and closes | Hotkey + app control |
| 7 | *"Jarvis, search Google for best Python projects 2025"* | Browser opens with search | Web integration |
| 8 | *"Jarvis, what's on my screen right now?"* | Describes screen contents | Claude Vision |
| 9 | *"Jarvis, set a 30 second timer called pasta"* | Speaks "pasta is done!" after 30s | Timer with label |
| 10 | *"Jarvis, open Chrome, go to weather.com, and read me what the weather looks like"* | Chrome → weather.com → Vision → spoken summary | Full pipeline: app + URL + vision + speech |

---

## 🌐 Supported Languages

JARVIS uses faster-whisper's multilingual model. It auto-detects language.
Hindi commands work out of the box — just speak naturally.

---

## 📄 License

MIT License. Use freely for personal projects.
