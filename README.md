# Pixel Pet 🛸🦕

A cute retro pixel-art desktop pet that lives and plays along the top edge of your Windows screen.

## Features

- **16 Animation States & Actions**:
  - `idle` & `idle_flip`: Curious idle, head tilting, blushing cute.
  - `walk_right` & `walk_left`: Smooth 8-frame walking/running cycle.
  - `idea`: Thinking deeply -> lightbulb pops up with eureka moment!
  - `work`: Typing & researching on a holographic tablet.
  - `happy`: Giggling, clapping, and giving an OK-sign wink.
  - `shrug`: Welcoming hands-open greeting & shrug.
  - `sleep`: Collapsing flat on belly with animated pixel Zzz.
  - `wake`: Waking up, sitting up, and getting back on feet.
  - `sit`: Relaxed sitting pose looking around.
  - `cry` & `sad`: Sobbing tears and pouting.
  - `jump` & `roar`: Excited leaps and super cheer.
  - `blink`: Subtle blinking and winking.
- **Interactive Controls**:
  - **Left-click**: Cheerful random reaction (Happy / Idea / Shrug / Blink)
  - **Double-click**: Lightbulb idea or Hologram tablet typing
  - **Middle-click**: Hologram tablet work
  - **Right-click**: Context menu with **"Pet Actions 🎮"** submenu to trigger any action on demand, plus Pause/Resume, Settings, and Exit.
- **Autonomous Behaviors**:
  - Roams across your top screen edge.
  - Works on its tablet, gets ideas, sits, naps after inactivity, and wakes up naturally.
- **Always-on-top transparent overlay** with pixel-perfect rendering and click-through transparency.
- **Customizable**:
  - Settings dialog for Pet Size (48px – 192px), Walking Speed, Animation FPS, Start with Windows, and Always-on-top.

## Requirements

- Windows 10 or Windows 11
- Python 3.10+ (PySide6 & Pillow)

## Installation & Running

```bash
pip install -r requirements.txt
python main.py
```

Or double-click `start_pet.bat`.

## Project Structure

```
Desktop-Pet/
├── assets/
│   ├── sprites/              # Production pixel-art PNG sprite sheets for all pets
│   └── jarvis.ico            # Application icon
├── launchers/                # Direct launchers for all 21 desktop pets
├── tools/                    # Sprite extraction & generator scripts & raw sources
├── jarvis/                   # Jarvis AI voice assistant companion
├── main.py                   # Application entry point
├── lion.py                   # Low-power PetWindow (transparent overlay widget + game loop)
├── animation.py              # Sprite sheet loader + pre-scaled animation controller
├── movement.py               # Autonomous state machine + physics movement engine
├── origin_island.py          # Dynamic Island overlay with adaptive power throttling
├── media_service.py          # Adaptive Windows SMTC media detection service
├── media_card.py             # Zero-ghosting media notification widget
├── activity.py               # Low-overhead user typing & activity monitor
├── speech_bubble.py          # Floating comic speech bubble
├── settings.py               # Persistent JSON settings + settings dialog UI
├── startup.py                # Windows registry auto-start helper
├── start_pet.bat             # Unified quick launcher batch file (accepts pet name argument)
├── start_island.bat          # Standalone Island launcher
├── requirements.txt
└── README.md
```