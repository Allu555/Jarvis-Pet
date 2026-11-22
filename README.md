# Desktop Pet & JARVIS AI Companion 🛸🐾

An ultra-lightweight, high-performance desktop companion for Windows featuring **autonomous pixel pets**, an interactive **Dynamic Origin Island**, and **JARVIS** — an intelligent voice, vision, and system automation agent.

Designed with an ultra-lightweight architecture: **~60 MB RAM**, **< 1% idle CPU**, and a **100% in-memory zero-disk lyrics engine**.

---

![Desktop Pet Preview](docs/images/desktop_pet_preview.png)

---

## ⚡ Highlights & Features

### 🐾 1. Autonomous Desktop Pets
- **21 Animated Retro Pets**: Tanjiro, Spider-Bot, Robot, Gwen, Inosuke, Zenitsu, Nezuko, Goku, and more.
- **16 Autonomous Behaviors & State Machine**:
  - `walk_left` & `walk_right`: Fluid 8-phase articulated walking along screen edges.
  - `work`: Typing and researching on a holographic cyber-tablet.
  - `idea`: Deep thinking followed by an animated eureka lightbulb.
  - `sleep` & `wake`: Resting after inactivity with animated Zzz and natural wake-up.
  - `happy`, `shrug`, `sit`, `jump`, `roar`, `cry`, `blink`, and more.
- **Interactive Controls**: Click to play, double-click for eureka reactions, and right-click for the context menu.
- **Always-on-Top Click-Through Overlay**: Native Windows Desktop Window Manager (`DWM`) integration with hardware composited alpha transparency.

---

### 🏝️ 2. Dynamic Origin Island
Floating interactive top-notch overlay inspired by modern mobile dynamic islands:

<p align="center">
  <img src="docs/images/origin_island_notch.png" width="100%" alt="Origin Island Flush Notch">
</p>

#### 🎛️ Multi-Feature Island Suite

| 🎵 Expanded Music Player & Waveform EQ | 🌤️ Live Weather & Clock HUD |
| :---: | :---: |
| ![Origin Island Player](docs/images/origin_island_player.png) | ![Origin Island Weather](docs/images/origin_island_weather.png) |
| **⚙️ Control Center & Quick Toggles** | **📁 Smart Shelf (File & QR Stash)** |
| ![Origin Island Controls](docs/images/origin_island_controls.png) | ![Origin Island Smart Shelf](docs/images/origin_island_shelf.png) |
| **⚡ Live Hardware Telemetry & Tools** | **📱 Wireless Phone Drop & QR Remote** |
| ![Origin Island Telemetry](docs/images/origin_island_telemetry.png) | ![Phone Drop QR Pairing](docs/images/phone_drop_qr.png) |

- **Real-Time Media Detection**: Windows SMTC integration for Spotify, YouTube, and media players.
- **Live WASAPI Audio Visualizer**: 60 FPS real-time audio loopback frequency spectrum with adaptive theme colors.
- **100% In-Memory Karaoke Lyrics Engine**: Real-time synchronized lyrics via LRCLIB with zero disk writes, keeping the repository clean and lightweight.
- **Control Center & HUD**: Live battery percentage, weather updates, pomodoro focus timer, and quick tool shortcuts.

---

### 🤖 3. JARVIS Voice & Vision Agent

<p align="center">
  <img src="docs/images/jarvis_hud.png" width="450" alt="JARVIS HUD">
</p>

- **Agent Brain**: Powered by NVIDIA NIM (`nvidia/nemotron-3.5-bolt-e4b`) for low-latency tool orchestration and reasoning.
- **Vision Grounding**: Set-of-Marks visual perception (`nvidia/nemotron-3.5-super-vl-120b-a12b`) for precise UI element localization.
- **Direct App Control**: Native window management (`user32.dll`), full-screen window maximization, PWA launch, and intelligent Spotify search & playback.
- **Hands-Free Speech Engine**:
  - **Wake Word**: `openWakeWord` (`hey_jarvis_v0.1` ONNX) operating at < 0.5% CPU.
  - **Speech-to-Text (STT)**: `faster-whisper` (`small.en`) with custom prompt biasing.
  - **Speech Synthesis (TTS)**: Microsoft Neural voice streaming (`edge-tts`) with offline Windows SAPI5 fallback.

---

## 📊 System Telemetry & Model Architecture

The entire suite is engineered for zero system lag and minimal resource consumption:

![System Resource Dashboard](docs/images/system_resource_dashboard.png)

| Subsystem | Model / Technology | Execution | Memory Footprint |
| :--- | :--- | :--- | :--- |
| **Agent Brain** | `nvidia/nemotron-3.5-bolt-e4b` | Cloud API (NVIDIA NIM) | **0 MB** |
| **Vision Grounding** | `nvidia/nemotron-3.5-super-vl-120b-a12b` | Cloud API (NVIDIA NIM) | **0 MB** |
| **Local Screen OCR** | `Windows.Media.Ocr` (WinRT) | Hardware Accelerated | **~20 MB** (on-demand) |
| **Speech-to-Text (STT)**| `faster-whisper` (`small.en`) | Local CTranslate2 | **~180 - 320 MB** (on-demand) |
| **Wake Word Engine** | `openWakeWord` (`hey_jarvis_v0.1` ONNX) | Local ONNX Runtime | **~22 MB** (< 0.5% CPU) |
| **Speech Synthesis (TTS)**| `edge-tts` (`en-GB-RyanNeural`) | Cloud WebSockets | **0 MB** |
| **Karaoke Lyrics** | `LRCLIB` Synced Engine | In-Memory LRU Cache | **< 0.1 MB** (0 Disk Files) |
| **GUI & Overlay** | `PySide6` (Qt 6) | DWM Hardware Composited | **~42 MB** |

---

## 🚀 Getting Started

### Prerequisites
- Windows 10 or Windows 11 (64-bit)
- Python 3.10 or 3.11

### Installation

1. **Clone the repository**:
   ```bash
   git clone https://github.com/Allu555/Jarvis-Pet.git
   cd Jarvis-Pet
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure API Keys (Optional for Cloud Agent)**:
   Create a `.env` file in the project root:
   ```env
   NVIDIA_API_KEY=your_nvidia_nim_api_key
   ```

4. **Launch Application**:
   ```bash
   python main.py
   ```
   Or double-click `start_everything.vbs` to start silently in the background without any command prompt windows.

---

## 🎮 Controls & Shortcuts

| Action | Control |
| :--- | :--- |
| **Pet Reaction** | Left-Click on pet |
| **Eureka / Hologram Work** | Double-Click on pet |
| **Context Menu & Pet Switcher**| Right-Click on pet |
| **Expand Dynamic Island** | Hover or click top notch |
| **Phone Link QR** | Click Phone icon on Island shelf |
| **Settings Dialog** | Right-click pet → Settings ⚙️ |

---

## 👥 Contributors & Credits

<div align="center">
  <table>
    <tr>
      <td align="center" width="180">
        <a href="https://github.com/Allu555">
          <img src="https://github.com/Allu555.png" width="96px;" style="border-radius: 50%;" alt="Alameen Najeeb"/><br /><br />
          <sub><b>Alameen Najeeb</b></sub><br />
          <sub>Creator & Lead Architect</sub>
        </a>
      </td>
      <td align="center" width="180">
        <a href="https://github.com/google-antigravity">
          <img src="https://avatars.githubusercontent.com/u/242056456?v=4" width="96px;" style="border-radius: 50%;" alt="Google Antigravity"/><br /><br />
          <sub><b>Google Antigravity</b></sub><br />
          <sub>AI Autonomous Co-Developer</sub>
        </a>
      </td>
    </tr>
  </table>
</div>

---

## 🛡️ License

This project is licensed under the MIT License.
