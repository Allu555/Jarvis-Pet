"""
phone_drop_service.py – Instant Phone <-> Laptop Bi-directional QR Code Connect & Drop Service.

Apple iOS Design Language:
- Pure OLED true black (#000000) with dynamic ambient album art backlight glow.
- Apple Music signature pink/red accent (#fa2d48) and iOS System Blue (#007aff).
- Real-time synchronized karaoke lyrics (Apple Music Sing style) with auto-centering spring scroll & tap-to-seek.
- Instant JARVIS AI controls (skip track, previous track, pause/play, volume, screenshot, lock PC, taskbar styles).
- Direct Wi-Fi LAN QR pairing that connects reliably on all Android & iOS devices.
"""

from __future__ import annotations

import os
import io
import sys
import shutil
import json
import time
import socket
import ctypes
import urllib.parse
import threading
import queue
import collections
from pathlib import Path
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from typing import Optional, Callable, Dict, Any, List, Tuple

import qrcode
from PIL import Image, ImageDraw, ImageGrab

BASE_DIR = Path(__file__).resolve().parent
ASSETS_DIR = BASE_DIR / "assets"
APK_FILE = ASSETS_DIR / "JarvisRemote.apk"

class _POINT(ctypes.Structure):
    _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]


class _KEYBDINPUT(ctypes.Structure):
    _fields_ = [
        ("wVk", ctypes.c_ushort),
        ("wScan", ctypes.c_ushort),
        ("dwFlags", ctypes.c_ulong),
        ("time", ctypes.c_ulong),
        ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong)),
    ]


class _INPUT_UNION(ctypes.Union):
    _fields_ = [("ki", _KEYBDINPUT)]


class _INPUT(ctypes.Structure):
    _fields_ = [
        ("type", ctypes.c_ulong),
        ("u", _INPUT_UNION),
    ]

# Default directory where files from phone are saved
DOWNLOADS_DIR = Path.home() / "Downloads" / "PhoneDrop"
DOWNLOADS_DIR.mkdir(parents=True, exist_ok=True)


def get_hostname() -> str:
    """Return lowercase hostname."""
    try:
        return socket.gethostname().lower()
    except Exception:
        return "laptop"


def get_local_ip() -> str:
    """Detect local Wi-Fi / LAN IP address."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('10.255.255.255', 1))
        ip = s.getsockname()[0]
    except Exception:
        ip = '127.0.0.1'
    finally:
        s.close()
    return ip


class _SYSTEM_POWER_STATUS(ctypes.Structure):
    _fields_ = [
        ("ACLineStatus", ctypes.c_byte),
        ("BatteryFlag", ctypes.c_byte),
        ("BatteryLifePercent", ctypes.c_byte),
        ("SystemStatusFlag", ctypes.c_byte),
        ("BatteryLifeTime", ctypes.c_ulong),
        ("BatteryFullLifeTime", ctypes.c_ulong),
    ]


def get_win32_power_status() -> Optional[Dict[str, Any]]:
    """Returns real-time laptop battery percentage and AC charging state."""
    try:
        sps = _SYSTEM_POWER_STATUS()
        if ctypes.windll.kernel32.GetSystemPowerStatus(ctypes.byref(sps)):
            percent = int(sps.BatteryLifePercent)
            if percent == 255:
                return None
            is_charging = bool(sps.BatteryFlag & 8) or (sps.ACLineStatus == 1 and percent < 100)
            is_plugged = bool(sps.ACLineStatus == 1)
            return {
                "percent": min(100, max(0, percent)),
                "charging": is_charging,
                "power_plugged": is_plugged,
            }
    except Exception:
        pass
    return None



# ─── Apple iOS Mobile Web Application (HTML / CSS / JS) ──────────────────────────

MOBILE_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no, viewport-fit=cover">
<meta name="theme-color" content="#000000">
<meta name="mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
<meta name="apple-mobile-web-app-title" content="Origin Link">
<title>Origin Link · Apple iOS Hub</title>
<style>
:root {
  --ios-black: #000000;
  --ios-card: rgba(28, 28, 30, 0.72);
  --ios-card-elevated: rgba(44, 44, 46, 0.78);
  --ios-border: rgba(255, 255, 255, 0.12);
  --ios-red: #fa2d48;         /* Apple Music Red */
  --ios-blue: #007aff;        /* iOS Blue */
  --ios-green: #34c759;       /* iOS Green */
  --ios-purple: #af52de;      /* iOS Purple */
  --ios-indigo: #5856d6;      /* iOS Indigo */
  --ios-orange: #ff9500;      /* iOS Orange */
  --ios-gray-text: #8e8e93;
  --ios-light-gray: #aeaeb2;
  --font-stack: -apple-system, BlinkMacSystemFont, "SF Pro Display", "SF Pro Text", "Helvetica Neue", Helvetica, Arial, sans-serif;
  --safe-bottom: env(safe-area-inset-bottom, 18px);
}

* {
  box-sizing: border-box;
  margin: 0;
  padding: 0;
  -webkit-tap-highlight-color: transparent;
  user-select: none;
}

body {
  background-color: var(--ios-black);
  color: #ffffff;
  font-family: var(--font-stack);
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  overflow-x: hidden;
  padding-bottom: calc(84px + var(--safe-bottom));
  position: relative;
}

/* Dynamic Ambient Backdrop Aura (Apple Music style) */
.ambient-backdrop {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  pointer-events: none;
  z-index: 0;
  overflow: hidden;
}

.ambient-blob {
  position: absolute;
  border-radius: 50%;
  filter: blur(80px);
  opacity: 0.38;
  transition: all 1.2s cubic-bezier(0.25, 1, 0.5, 1);
}

.blob-1 {
  width: 320px;
  height: 320px;
  top: -60px;
  left: 50%;
  transform: translateX(-50%);
  background: radial-gradient(circle, var(--ios-red) 0%, transparent 70%);
}

.blob-2 {
  width: 280px;
  height: 280px;
  bottom: 120px;
  right: -40px;
  background: radial-gradient(circle, var(--ios-indigo) 0%, transparent 70%);
}

/* iOS Glass Header */
header {
  position: sticky;
  top: 0;
  z-index: 50;
  backdrop-filter: blur(35px) saturate(200%);
  -webkit-backdrop-filter: blur(35px) saturate(200%);
  background: rgba(0, 0, 0, 0.75);
  border-bottom: 0.5px solid var(--ios-border);
  padding: max(14px, env(safe-area-inset-top)) 16px 12px 16px;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.brand {
  display: flex;
  align-items: center;
  gap: 10px;
}

.brand-icon {
  width: 32px;
  height: 32px;
  border-radius: 9px;
  background: linear-gradient(135deg, #fc3c44, #fa2d48);
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 4px 14px rgba(250, 45, 72, 0.4);
}

.brand-titles {
  display: flex;
  flex-direction: column;
}

.brand-title {
  font-size: 16px;
  font-weight: 700;
  letter-spacing: -0.4px;
}

.brand-subtitle {
  font-size: 11px;
  color: var(--ios-gray-text);
  font-weight: 500;
}

.ios-pill-badge {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 5px 12px;
  border-radius: 999px;
  background: rgba(52, 199, 89, 0.14);
  border: 0.5px solid rgba(52, 199, 89, 0.35);
  font-size: 12px;
  font-weight: 600;
  color: var(--ios-green);
}

.ios-pulse-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: var(--ios-green);
  box-shadow: 0 0 8px var(--ios-green);
  animation: iosPulse 2s infinite ease-in-out;
}

@keyframes iosPulse {
  0%, 100% { opacity: 1; transform: scale(1); }
  50% { opacity: 0.45; transform: scale(0.85); }
}

/* Main Container */
.main-content {
  position: relative;
  z-index: 10;
  flex: 1;
  padding: 16px 18px;
  max-width: 520px;
  width: 100%;
  margin: 0 auto;
}

.view-section {
  display: none;
  animation: iosSpringIn 0.32s cubic-bezier(0.25, 1, 0.5, 1) forwards;
}

.view-section.active {
  display: block;
}

@keyframes iosSpringIn {
  from { opacity: 0; transform: scale(0.97) translateY(8px); }
  to { opacity: 1; transform: scale(1) translateY(0); }
}

/* iOS Card Surfaces */
.ios-card {
  background: rgba(24, 24, 28, 0.58);
  backdrop-filter: blur(50px) saturate(220%);
  -webkit-backdrop-filter: blur(50px) saturate(220%);
  border: 1px solid rgba(255, 255, 255, 0.14);
  border-radius: 26px;
  padding: 22px;
  margin-bottom: 16px;
  box-shadow: 0 24px 64px rgba(0, 0, 0, 0.65), inset 0 1px 1.5px rgba(255, 255, 255, 0.25);
}

.card-header {
  font-size: 13px;
  font-weight: 700;
  color: var(--ios-light-gray);
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin-bottom: 16px;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

/* ══════════ VIEW 1: APPLE MUSIC & SYNCED LYRICS ══════════ */
.now-playing-box {
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
}

.cover-wrapper {
  width: min(280px, 80vw);
  height: min(280px, 80vw);
  margin: 6px 0 20px;
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
}

.cover-reflection {
  position: absolute;
  width: 90%;
  height: 90%;
  border-radius: 28px;
  filter: blur(45px) saturate(220%);
  opacity: 0.72;
  transform: translateY(14px) scale(0.96);
  z-index: 1;
  pointer-events: none;
  transition: opacity 0.5s ease;
}

.cover-art {
  width: 100%;
  height: 100%;
  border-radius: 26px;
  object-fit: cover;
  position: relative;
  z-index: 2;
  box-shadow: 0 24px 60px rgba(0, 0, 0, 0.8), 0 4px 16px rgba(0, 0, 0, 0.4);
  border: 1px solid rgba(255, 255, 255, 0.2);
  image-rendering: -webkit-optimize-contrast;
  transition: transform 0.4s cubic-bezier(0.25, 1, 0.5, 1);
}

.cover-art.playing {
  animation: vinylBreathe 5s infinite ease-in-out;
}

@keyframes vinylBreathe {
  0%, 100% { transform: scale(1); }
  50% { transform: scale(1.028); }
}

.track-name {
  font-size: 21px;
  font-weight: 700;
  letter-spacing: -0.4px;
  color: #ffffff;
  max-width: 90%;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  margin-bottom: 4px;
}

.artist-name {
  font-size: 15px;
  font-weight: 500;
  color: var(--ios-gray-text);
  margin-bottom: 20px;
}

/* Apple iOS Scrubber */
.scrub-container {
  width: 100%;
  margin-bottom: 20px;
}

.scrub-track {
  width: 100%;
  height: 7px;
  background: rgba(255, 255, 255, 0.16);
  border-radius: 999px;
  position: relative;
  cursor: pointer;
}

.scrub-progress {
  position: absolute;
  top: 0;
  left: 0;
  height: 100%;
  width: 0%;
  background: #ffffff;
  border-radius: 999px;
  box-shadow: 0 0 12px rgba(255, 255, 255, 0.6);
  transition: width 0.1s linear;
}

.scrub-labels {
  display: flex;
  justify-content: space-between;
  margin-top: 8px;
  font-size: 12px;
  color: var(--ios-gray-text);
  font-weight: 500;
  font-variant-numeric: tabular-nums;
}

/* Playback Control Hub */
.controls-hub {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 32px;
  margin-bottom: 22px;
}

.ctrl-btn {
  background: none;
  border: none;
  color: #ffffff;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: transform 0.12s cubic-bezier(0.25, 1, 0.5, 1);
}

.ctrl-btn:active {
  transform: scale(0.86);
}

.ctrl-btn.play-circle {
  width: 66px;
  height: 66px;
  border-radius: 50%;
  background: #ffffff;
  color: #000000;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 10px 28px rgba(255, 255, 255, 0.35);
}

.ctrl-btn.play-circle:active {
  transform: scale(0.92);
}

/* Apple Control Center Liquid Glass Volume Capsule */
.ios-volume-capsule {
  width: 100%;
  height: 40px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.1);
  backdrop-filter: blur(35px);
  -webkit-backdrop-filter: blur(35px);
  border: 1px solid rgba(255, 255, 255, 0.18);
  position: relative;
  overflow: hidden;
  cursor: pointer;
  touch-action: none;
  box-shadow: inset 0 1px 2px rgba(255, 255, 255, 0.25), 0 6px 20px rgba(0, 0, 0, 0.35);
}

.ios-volume-fill {
  position: absolute;
  top: 0;
  left: 0;
  bottom: 0;
  width: 50%;
  background: linear-gradient(90deg, rgba(255, 255, 255, 0.9), #ffffff);
  border-radius: 999px;
  box-shadow: 0 0 20px rgba(255, 255, 255, 0.45);
  pointer-events: none;
  transition: width 0.08s ease;
}

.ios-volume-content {
  position: relative;
  z-index: 3;
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
  height: 100%;
  padding: 0 16px;
  pointer-events: none;
  mix-blend-mode: difference;
  color: #ffffff;
  font-weight: 700;
  font-size: 13px;
}

/* Apple Music Live Synced Lyrics Sheet */
.lyrics-card {
  min-height: 320px;
  max-height: 480px;
  display: flex;
  flex-direction: column;
  position: relative;
  overflow: hidden;
}

.lyrics-container {
  flex: 1;
  overflow-y: auto;
  scroll-behavior: smooth;
  padding: 30px 12px 60px;
  text-align: center;
  mask-image: linear-gradient(to bottom, transparent 0%, black 15%, black 85%, transparent 100%);
  -webkit-mask-image: linear-gradient(to bottom, transparent 0%, black 15%, black 85%, transparent 100%);
}

.lyric-item {
  padding: 10px 14px;
  margin: 4px 0;
  font-size: 18px;
  line-height: 1.45;
  color: rgba(255, 255, 255, 0.32);
  font-weight: 600;
  border-radius: 14px;
  cursor: pointer;
  filter: blur(0.4px);
  transition: all 0.32s cubic-bezier(0.25, 1, 0.5, 1);
}

.lyric-item.active {
  color: #ffffff;
  font-size: 23px;
  font-weight: 700;
  letter-spacing: -0.3px;
  transform: scale(1.05);
  filter: blur(0px);
  text-shadow: 0 0 20px rgba(255, 255, 255, 0.7);
  background: rgba(255, 255, 255, 0.08);
}

.lyric-item:active {
  background: rgba(255, 255, 255, 0.14);
}

.lyrics-placeholder {
  color: var(--ios-gray-text);
  font-size: 15px;
  padding: 50px 10px;
  font-style: italic;
}

/* ══════════ VIEW 2: JARVIS AI ASSISTANT ══════════ */
.jarvis-hero {
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
}

.siri-ring {
  width: 76px;
  height: 76px;
  border-radius: 50%;
  padding: 3px;
  background: linear-gradient(45deg, #007aff, #af52de, #fa2d48, #ff9500);
  animation: siriSpin 6s linear infinite;
  box-shadow: 0 0 28px rgba(250, 45, 72, 0.35);
  margin-bottom: 12px;
}

@keyframes siriSpin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

.siri-inner {
  width: 100%;
  height: 100%;
  border-radius: 50%;
  background: #000000;
  display: flex;
  align-items: center;
  justify-content: center;
}

.siri-badge {
  font-size: 13px;
  font-weight: 600;
  color: var(--ios-light-gray);
  margin-bottom: 16px;
}

/* Chat Messages (Apple iMessage style) */
.chat-window {
  width: 100%;
  min-height: 220px;
  max-height: min(440px, 50vh);
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding: 4px;
  margin-bottom: 12px;
  scroll-behavior: smooth;
}

.imessage {
  max-width: 82%;
  padding: 10px 16px;
  font-size: 14.5px;
  line-height: 1.4;
  word-break: break-word;
}

.imessage.user {
  align-self: flex-end;
  background: var(--ios-blue);
  color: #ffffff;
  border-radius: 18px 18px 4px 18px;
}

.imessage.jarvis {
  align-self: flex-start;
  background: var(--ios-card-elevated);
  border: 0.5px solid var(--ios-border);
  color: #f2f2f7;
  border-radius: 18px 18px 18px 4px;
}

/* Apple iOS Horizontal Suggestion Rail (Smart Chips) */
.ios-suggestion-rail {
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;
  overflow-x: auto;
  white-space: nowrap;
  -webkit-overflow-scrolling: touch;
  padding: 4px 2px 10px 2px;
  margin-bottom: 8px;
  scrollbar-width: none;
}

.ios-suggestion-rail::-webkit-scrollbar {
  display: none;
}

.action-chip {
  background: rgba(255, 255, 255, 0.08);
  backdrop-filter: blur(25px);
  -webkit-backdrop-filter: blur(25px);
  border: 0.5px solid rgba(255, 255, 255, 0.16);
  border-radius: 999px;
  padding: 7px 14px;
  font-size: 12.5px;
  font-weight: 500;
  color: #f2f2f7;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  flex-shrink: 0;
  box-shadow: inset 0 1px 1px rgba(255, 255, 255, 0.15);
  transition: transform 0.12s cubic-bezier(0.2, 0.8, 0.2, 1), background 0.15s ease, border-color 0.15s ease;
  user-select: none;
}

.action-chip:active {
  transform: scale(0.95);
  background: rgba(255, 255, 255, 0.2);
  border-color: rgba(255, 255, 255, 0.35);
}

.action-chip svg {
  flex-shrink: 0;
  opacity: 0.9;
}

/* iOS Prompt Bar */
.ios-input-dock {
  width: 100%;
  display: flex;
  align-items: center;
  gap: 8px;
  background: rgba(255, 255, 255, 0.08);
  border: 0.5px solid var(--ios-border);
  border-radius: 999px;
  padding: 4px 6px 4px 16px;
}

.ios-input-dock:focus-within {
  border-color: var(--ios-blue);
  box-shadow: 0 0 16px rgba(0, 122, 255, 0.35);
}

.text-input {
  flex: 1;
  background: transparent;
  border: none;
  outline: none;
  color: #ffffff;
  font-size: 14px;
  font-family: inherit;
}

.text-input::placeholder {
  color: var(--ios-gray-text);
}

.round-btn {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  border: none;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: transform 0.12s ease;
}

.round-btn:active {
  transform: scale(0.9);
}

.btn-mic {
  background: rgba(255, 255, 255, 0.1);
  color: #ffffff;
}

.btn-mic.active-listening {
  background: var(--ios-red);
  color: #ffffff;
  box-shadow: 0 0 16px var(--ios-red);
  animation: iosPulse 1.2s infinite ease-in-out;
}

.btn-send {
  background: var(--ios-blue);
  color: #ffffff;
}

/* ══════════ VIEW 3: AIRDROP & FILES ══════════ */
.airdrop-hub {
  border: 1.5px dashed rgba(0, 122, 255, 0.45);
  background: radial-gradient(circle at 50% 30%, rgba(0, 122, 255, 0.12) 0%, rgba(255, 255, 255, 0.02) 80%);
  border-radius: 26px;
  padding: 26px 16px 20px 16px;
  text-align: center;
  cursor: pointer;
  margin-bottom: 16px;
  transition: all 0.25s cubic-bezier(0.16, 1, 0.3, 1);
  position: relative;
  overflow: hidden;
  box-shadow: 0 12px 32px rgba(0, 0, 0, 0.35), inset 0 1px 1.5px rgba(255, 255, 255, 0.15);
  user-select: none;
  -webkit-tap-highlight-color: transparent;
}

.airdrop-hub:active, .airdrop-hub.drag-over {
  border-color: var(--ios-blue);
  background: radial-gradient(circle at 50% 30%, rgba(0, 122, 255, 0.25) 0%, rgba(0, 122, 255, 0.06) 80%);
  transform: scale(0.985);
}

.airdrop-icon-container {
  position: relative;
  width: 76px;
  height: 76px;
  margin: 0 auto 12px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.airdrop-pulse-ring {
  position: absolute;
  width: 100%;
  height: 100%;
  border-radius: 50%;
  border: 1.5px solid rgba(0, 122, 255, 0.45);
  animation: airdropRadar 2.4s ease-out infinite;
  pointer-events: none;
}

.airdrop-pulse-ring:nth-child(2) {
  animation-delay: 1.2s;
}

@keyframes airdropRadar {
  0% { transform: scale(0.65); opacity: 0.85; }
  100% { transform: scale(1.6); opacity: 0; }
}

.airdrop-icon-ring {
  width: 62px;
  height: 62px;
  border-radius: 50%;
  background: linear-gradient(135deg, rgba(0, 122, 255, 0.35), rgba(90, 200, 250, 0.22));
  border: 1px solid rgba(0, 122, 255, 0.55);
  display: flex;
  align-items: center;
  justify-content: center;
  color: #ffffff;
  box-shadow: 0 0 24px rgba(0, 122, 255, 0.4);
  z-index: 2;
  transition: transform 0.2s ease;
}

.airdrop-hub:active .airdrop-icon-ring {
  transform: scale(0.92);
}

.airdrop-pills-row {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  justify-content: center;
  margin-top: 14px;
}

.airdrop-pill-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 8px 14px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.08);
  border: 0.5px solid rgba(255, 255, 255, 0.16);
  color: #f2f2f7;
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s ease;
  backdrop-filter: blur(10px);
  -webkit-backdrop-filter: blur(10px);
  user-select: none;
  -webkit-tap-highlight-color: transparent;
}

.airdrop-pill-btn:active {
  transform: scale(0.95);
  background: rgba(0, 122, 255, 0.22);
  border-color: var(--ios-blue);
  color: #5ac8fa;
}

/* Upload Progress Box */
.airdrop-progress-box {
  background: rgba(28, 28, 30, 0.85);
  border: 0.5px solid rgba(0, 122, 255, 0.45);
  border-radius: 18px;
  padding: 14px 16px;
  margin-bottom: 16px;
  display: none;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.4);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
}

.airdrop-prog-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.airdrop-prog-name {
  font-size: 13px;
  font-weight: 600;
  color: #ffffff;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 220px;
}

.airdrop-prog-pct {
  font-size: 12px;
  font-weight: 700;
  color: #5ac8fa;
}

.airdrop-prog-track {
  width: 100%;
  height: 6px;
  background: rgba(255, 255, 255, 0.1);
  border-radius: 999px;
  overflow: hidden;
}

.airdrop-prog-bar {
  height: 100%;
  width: 0%;
  background: linear-gradient(90deg, #007aff, #5ac8fa);
  border-radius: 999px;
  transition: width 0.12s ease;
  box-shadow: 0 0 10px rgba(0, 122, 255, 0.6);
}

.airdrop-prog-status {
  font-size: 11px;
  color: var(--ios-gray-text);
  margin-top: 6px;
}

.shelf-card-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.shelf-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 14px;
  background: rgba(255, 255, 255, 0.04);
  border: 0.5px solid var(--ios-border);
  border-radius: 14px;
}

.shelf-file-badge {
  font-size: 10px;
  font-weight: 800;
  padding: 3px 6px;
  border-radius: 6px;
  background: rgba(0, 122, 255, 0.18);
  color: var(--ios-blue);
  text-transform: uppercase;
}

.shelf-file-name {
  font-size: 13.5px;
  font-weight: 500;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 190px;
}

.shelf-dl-btn {
  background: rgba(255, 255, 255, 0.08);
  border: 0.5px solid var(--ios-border);
  border-radius: 8px;
  padding: 6px 12px;
  font-size: 11.5px;
  font-weight: 600;
  color: #ffffff;
  text-decoration: none;
  cursor: pointer;
}

/* ══════════ VIEW 4: CONTROL CENTER ══════════ */
.control-tiles {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 10px;
  margin-bottom: 16px;
}

.ios-tile {
  background: rgba(255, 255, 255, 0.05);
  border: 0.5px solid var(--ios-border);
  border-radius: 18px;
  padding: 16px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 8px;
  color: #ffffff;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: transform 0.12s ease;
}

.ios-tile:active {
  transform: scale(0.95);
  background: rgba(255, 255, 255, 0.1);
}

.clipboard-textarea {
  width: 100%;
  min-height: 70px;
  background: rgba(255, 255, 255, 0.04);
  border: 0.5px solid var(--ios-border);
  border-radius: 14px;
  padding: 12px;
  color: #ffffff;
  font-size: 13px;
  font-family: inherit;
  outline: none;
  resize: vertical;
  margin-bottom: 8px;
}

.clipboard-textarea:focus {
  border-color: var(--ios-blue);
}

.ios-btn {
  background: rgba(255, 255, 255, 0.08);
  border: 0.5px solid var(--ios-border);
  border-radius: 12px;
  padding: 10px 14px;
  color: #ffffff;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  transition: transform 0.12s ease;
}

.ios-btn:active {
  transform: scale(0.96);
  background: rgba(255, 255, 255, 0.15);
}

/* Floating iOS Tab Bar */
.ios-tab-bar {
  position: fixed;
  bottom: 0;
  left: 0;
  right: 0;
  z-index: 60;
  backdrop-filter: blur(40px) saturate(210%);
  -webkit-backdrop-filter: blur(40px) saturate(210%);
  background: rgba(18, 18, 20, 0.84);
  border-top: 0.5px solid var(--ios-border);
  padding: 8px 16px calc(8px + var(--safe-bottom));
  display: flex;
  justify-content: space-around;
  align-items: center;
  max-width: 520px;
  margin: 0 auto;
}

.tab-btn {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 3px;
  color: var(--ios-gray-text);
  font-size: 10.5px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.16s ease;
  padding: 4px 10px;
}

.tab-btn.active {
  color: var(--ios-red);
}

.tab-btn:active {
  transform: scale(0.92);
}

/* ══════════ RESPONSIVE ADAPTATIONS (MOBILE & LAPTOP RATIOS) ══════════ */
.remote-mode-switcher {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 4px;
  background: rgba(22, 22, 28, 0.92);
  backdrop-filter: blur(25px);
  border: 1px solid rgba(255, 255, 255, 0.12);
  border-radius: 999px;
  padding: 4px;
  max-width: 480px;
  margin: 0 auto 14px;
  box-shadow: 0 4px 18px rgba(0, 0, 0, 0.4);
}

.mode-tab-btn {
  padding: 9px 0;
  border-radius: 999px;
  font-size: 11.5px;
  font-weight: 700;
  border: none;
  background: transparent;
  color: var(--ios-gray-text);
  cursor: pointer;
  text-align: center;
  transition: all 0.2s cubic-bezier(0.25, 1, 0.5, 1);
  white-space: nowrap;
  user-select: none;
}

.mode-tab-btn.active {
  background: linear-gradient(135deg, #fa2d48, #d81c34);
  color: #ffffff;
  box-shadow: 0 4px 14px rgba(250, 45, 72, 0.45), inset 0 1px 1px rgba(255, 255, 255, 0.3);
}

.remote-type-bar {
  display: flex;
  gap: 6px;
  align-items: center;
  margin-top: 10px;
}

.remote-type-input {
  flex: 1;
  min-width: 0;
  height: 42px;
  background: rgba(22, 22, 28, 0.94);
  border: 1px solid rgba(255, 255, 255, 0.14);
  border-radius: 13px;
  padding: 0 14px;
  color: #ffffff;
  font-size: 13.5px;
  outline: none;
  box-shadow: inset 0 1.5px 3px rgba(0, 0, 0, 0.4);
  transition: border-color 0.18s ease, box-shadow 0.18s ease;
}

.remote-type-input:focus {
  border-color: var(--ios-red);
  box-shadow: 0 0 12px rgba(250, 45, 72, 0.35), inset 0 1.5px 3px rgba(0, 0, 0, 0.4);
}

.remote-btn-type {
  height: 42px;
  padding: 0 16px;
  background: linear-gradient(135deg, #fa2d48, #d81c34);
  border: 1px solid rgba(255, 255, 255, 0.2);
  border-radius: 13px;
  color: #ffffff;
  font-size: 12.5px;
  font-weight: 700;
  cursor: pointer;
  white-space: nowrap;
  display: flex;
  align-items: center;
  gap: 5px;
  box-shadow: 0 4px 14px rgba(250, 45, 72, 0.38), inset 0 1px 0 rgba(255, 255, 255, 0.28);
  transition: transform 0.12s ease, opacity 0.12s ease;
  user-select: none;
}

.remote-btn-type:active {
  transform: scale(0.95);
  opacity: 0.9;
}

.remote-btn-paste {
  height: 42px;
  padding: 0 14px;
  background: linear-gradient(180deg, rgba(50, 50, 60, 0.9) 0%, rgba(32, 32, 40, 0.96) 100%);
  border: 1px solid rgba(255, 255, 255, 0.15);
  border-radius: 13px;
  color: #ffffff;
  font-size: 12.5px;
  font-weight: 700;
  cursor: pointer;
  white-space: nowrap;
  display: flex;
  align-items: center;
  gap: 5px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.4), inset 0 1px 0 rgba(255, 255, 255, 0.18);
  transition: transform 0.12s ease, background 0.12s ease;
  user-select: none;
}

.remote-btn-paste:active {
  transform: scale(0.95);
  background: rgba(65, 65, 78, 0.95);
}

/* 3D Physical Chiclet Keycaps */
.pc-key-btn {
  height: 38px;
  padding: 0 4px;
  background: linear-gradient(180deg, rgba(46, 46, 56, 0.9) 0%, rgba(26, 26, 32, 0.96) 100%);
  border: 1px solid rgba(255, 255, 255, 0.12);
  border-bottom: 2px solid rgba(0, 0, 0, 0.65);
  border-radius: 11px;
  color: #ffffff;
  font-size: 11.5px;
  font-weight: 700;
  cursor: pointer;
  white-space: nowrap;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 3px;
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.16), 0 3px 8px rgba(0, 0, 0, 0.35);
  transition: all 0.1s ease;
  user-select: none;
}

.pc-key-btn:active {
  transform: translateY(2px);
  border-bottom: 1px solid rgba(0, 0, 0, 0.65);
  box-shadow: inset 0 1px 2px rgba(0, 0, 0, 0.5);
  background: rgba(35, 35, 42, 0.95);
}

.pc-keys-grid {
  display: grid;
  grid-template-columns: repeat(6, 1fr);
  gap: 6px;
  margin-top: 10px;
}

.trackpad-action-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 6px;
  margin-bottom: 12px;
}

/* Tactile 3-Button Click Pads */
.click-pads-grid-3 {
  display: grid;
  grid-template-columns: 1.2fr 1fr 1fr;
  gap: 8px;
  margin-top: 10px;
}

.click-pad-btn {
  height: 44px;
  border-radius: 13px;
  font-size: 12px;
  font-weight: 700;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  transition: all 0.12s ease;
  user-select: none;
}

.click-pad-btn.primary {
  background: linear-gradient(180deg, rgba(0, 122, 255, 0.4) 0%, rgba(0, 122, 255, 0.18) 100%);
  border: 1px solid rgba(0, 122, 255, 0.55);
  color: #ffffff;
  box-shadow: 0 4px 14px rgba(0, 122, 255, 0.28), inset 0 1px 0 rgba(255, 255, 255, 0.25);
}

.click-pad-btn.secondary {
  background: linear-gradient(180deg, rgba(48, 48, 58, 0.9) 0%, rgba(28, 28, 36, 0.96) 100%);
  border: 1px solid rgba(255, 255, 255, 0.14);
  color: #ffffff;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.4), inset 0 1px 0 rgba(255, 255, 255, 0.16);
}

.click-pad-btn.accent {
  background: linear-gradient(180deg, rgba(250, 45, 72, 0.32) 0%, rgba(250, 45, 72, 0.14) 100%);
  border: 1px solid rgba(250, 45, 72, 0.48);
  color: #ffffff;
  box-shadow: 0 4px 14px rgba(250, 45, 72, 0.22), inset 0 1px 0 rgba(255, 255, 255, 0.25);
}

.click-pad-btn:active {
  transform: scale(0.96);
  opacity: 0.9;
}

/* Dedicated Tactile PC Scroll Bar */
.pc-scrollbar-track {
  width: 44px;
  background: rgba(20, 20, 26, 0.88);
  backdrop-filter: blur(25px);
  border: 1px solid rgba(255, 255, 255, 0.12);
  border-radius: 16px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: space-between;
  padding: 6px 4px;
  user-select: none;
  touch-action: none;
  box-shadow: 0 10px 28px rgba(0, 0, 0, 0.5), inset 0 1px 0 rgba(255, 255, 255, 0.1);
}

.pc-scrollbar-track.compact {
  width: 38px;
  border-radius: 14px;
  padding: 4px 3px;
}

.scrollbar-btn {
  width: 100%;
  height: 36px;
  border-radius: 10px;
  background: rgba(45, 45, 54, 0.85);
  border: 1px solid rgba(255, 255, 255, 0.1);
  color: #ffffff;
  font-size: 13px;
  font-weight: 800;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.12s ease;
  user-select: none;
}

.scrollbar-btn.compact {
  height: 30px;
  font-size: 11px;
}

.scrollbar-btn:active {
  background: var(--ios-red);
  transform: scale(0.92);
}

.scrollbar-gutter {
  flex: 1;
  width: 100%;
  margin: 6px 0;
  background: rgba(10, 10, 14, 0.7);
  border-radius: 12px;
  border: 1px solid rgba(255, 255, 255, 0.06);
  position: relative;
  overflow: hidden;
  cursor: ns-resize;
  display: flex;
  justify-content: center;
}

.scrollbar-thumb {
  position: absolute;
  top: 50%;
  transform: translateY(-50%);
  width: 82%;
  height: 48px;
  border-radius: 8px;
  background: linear-gradient(180deg, rgba(70, 70, 84, 0.95) 0%, rgba(40, 40, 50, 0.98) 100%);
  border: 1px solid rgba(255, 255, 255, 0.22);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.5), inset 0 1px 0 rgba(255, 255, 255, 0.2);
  display: flex;
  align-items: center;
  justify-content: center;
  color: rgba(255, 255, 255, 0.75);
  font-size: 12px;
  font-weight: 700;
  transition: top 0.08s ease-out;
  pointer-events: none;
}

.scrollbar-thumb.compact {
  height: 40px;
  font-size: 10px;
}

/* Mini Precision Touchpad for Live Screen */
.mini-touchpad-card {
  margin-top: 10px;
  background: rgba(22, 22, 28, 0.94);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 16px;
  padding: 8px 10px;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.45);
}

.mini-touchpad-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 6px;
  padding: 0 4px;
}

.live-dot-pulse {
  display: inline-block;
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: #30d158;
  box-shadow: 0 0 8px #30d158;
  animation: pulse-dot 1.8s infinite;
}

@keyframes pulse-dot {
  0% { transform: scale(0.95); opacity: 0.8; }
  50% { transform: scale(1.25); opacity: 1; }
  100% { transform: scale(0.95); opacity: 0.8; }
}

.screen-mini-trackpad {
  width: 100%;
  height: 115px;
  background: radial-gradient(circle at 50% 50%, rgba(45, 45, 54, 0.72), rgba(16, 16, 22, 0.98));
  border-radius: 13px;
  border: 1px solid rgba(255, 255, 255, 0.08);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  touch-action: none;
  user-select: none;
  position: relative;
  overflow: hidden;
  cursor: crosshair;
  transition: border-color 0.15s ease, box-shadow 0.15s ease;
}

.screen-mini-trackpad.active-touch {
  border-color: rgba(0, 122, 255, 0.55);
  box-shadow: inset 0 0 18px rgba(0, 122, 255, 0.2);
}

.mini-trackpad-reticle {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  pointer-events: none;
  opacity: 0.85;
  transition: opacity 0.15s ease;
}

.screen-mini-trackpad.active-touch .mini-trackpad-reticle {
  opacity: 0.35;
}

/* Perfectly Aligned 6-Column Mathematical Keypad Grid */
.live-screen-keypad {
  margin-top: 10px;
  display: flex;
  flex-direction: column;
  gap: 6px;
  width: 100%;
}

.pc-keys-grid-6 {
  display: grid;
  grid-template-columns: repeat(6, 1fr);
  gap: 6px;
  width: 100%;
}

.pc-keys-grid-6 .pc-key-btn {
  height: 38px;
  padding: 0 2px;
  font-size: 11px;
  font-weight: 700;
  display: flex;
  align-items: center;
  justify-content: center;
  text-align: center;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  min-width: 0;
  width: 100%;
}

/* Distinct System Badges for Window & Tab Controls */
.pc-key-btn.btn-win-min {
  color: #ffd60a;
  border-color: rgba(255, 214, 10, 0.35);
  background: linear-gradient(180deg, rgba(255, 214, 10, 0.12) 0%, rgba(32, 32, 38, 0.95) 100%);
}

.pc-key-btn.btn-win-max {
  color: #30d158;
  border-color: rgba(48, 209, 88, 0.35);
  background: linear-gradient(180deg, rgba(48, 209, 88, 0.12) 0%, rgba(32, 32, 38, 0.95) 100%);
}

.pc-key-btn.btn-win-close {
  color: #ff453a;
  border-color: rgba(255, 69, 58, 0.4);
  background: linear-gradient(180deg, rgba(255, 69, 58, 0.15) 0%, rgba(32, 32, 38, 0.95) 100%);
}

.pc-key-btn.btn-win-alttab {
  color: #bf5af2;
  border-color: rgba(191, 90, 242, 0.35);
  background: linear-gradient(180deg, rgba(191, 90, 242, 0.12) 0%, rgba(32, 32, 38, 0.95) 100%);
}

.pc-key-btn.btn-tab-new {
  color: #64d2ff;
  border-color: rgba(100, 210, 255, 0.35);
  background: linear-gradient(180deg, rgba(100, 210, 255, 0.12) 0%, rgba(32, 32, 38, 0.95) 100%);
}

.pc-key-btn.btn-tab-close {
  color: #ff9f0a;
  border-color: rgba(255, 159, 10, 0.35);
  background: linear-gradient(180deg, rgba(255, 159, 10, 0.12) 0%, rgba(32, 32, 38, 0.95) 100%);
}

/* Responsive Viewport & Native 16:9 Aspect Ratio */
#screen-viewport {
  flex: 1;
  width: 100%;
  aspect-ratio: 16 / 9;
  background: #000000;
  border-radius: 14px;
  overflow: hidden;
  position: relative;
  border: 1px solid rgba(255, 255, 255, 0.12);
  touch-action: none;
  user-select: none;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 10px 28px rgba(0, 0, 0, 0.55);
  transition: all 0.25s ease;
}

#live-screen-img {
  width: 100%;
  height: 100%;
  aspect-ratio: 16 / 9;
  object-fit: contain;
  display: block;
}

.remote-display-layout {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.remote-display-screen-col,
.remote-display-controls-col {
  width: 100%;
}

.music-layout-grid {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

/* ════════════ UNIVERSAL RATIO ADAPTATION ════════════ */
@media (min-width: 768px) {
  .main-content {
    max-width: 860px;
    padding: 20px 24px 110px;
  }
  .ios-tab-bar {
    max-width: 600px;
    left: 50%;
    transform: translateX(-50%);
    border-radius: 28px;
    bottom: 18px;
    box-shadow: 0 20px 48px rgba(0, 0, 0, 0.75);
    border: 1px solid rgba(255, 255, 255, 0.16);
  }
}

@media (min-width: 992px) {
  .main-content {
    max-width: 1240px;
    padding: 24px 36px 120px;
  }
  /* 2-Column Command Console for Live Screen */
  .remote-display-layout {
    display: grid;
    grid-template-columns: minmax(0, 1.45fr) minmax(360px, 1fr);
    gap: 20px;
    align-items: start;
  }
  .remote-display-screen-col {
    position: sticky;
    top: 20px;
  }
  #screen-viewport {
    aspect-ratio: 16 / 9 !important;
    height: auto !important;
    max-height: calc(100vh - 200px);
  }
  #trackpad-surface {
    height: 380px !important;
    aspect-ratio: 16 / 10;
  }
  .screen-mini-trackpad {
    height: 125px !important;
  }
  /* 2-Column Side-by-Side for Music */
  .music-layout-grid {
    display: grid;
    grid-template-columns: 1fr 1.25fr;
    gap: 20px;
    align-items: start;
  }
  .now-playing-box {
    position: sticky;
    top: 20px;
  }
  .lyrics-card {
    min-height: 520px;
    max-height: calc(100vh - 180px);
  }
}

@media (min-width: 1400px) {
  .main-content {
    max-width: 1400px;
    padding: 28px 48px 120px;
  }
  .remote-display-layout {
    grid-template-columns: minmax(0, 1.6fr) minmax(400px, 1fr);
    gap: 24px;
  }
}

@media (max-width: 600px) {
  .main-content {
    padding: 10px 8px 96px;
  }
  .ios-card {
    padding: 10px 8px;
    border-radius: 16px;
  }
  #screen-viewport {
    aspect-ratio: 16 / 9 !important;
    height: auto !important;
  }
  .pc-scrollbar-track.compact {
    width: 34px;
  }
  .scrollbar-btn.compact {
    height: 28px;
  }
  .scrollbar-thumb.compact {
    height: 34px;
  }
  .click-pads-grid-3 {
    gap: 5px;
  }
  .click-pad-btn {
    height: 38px;
    font-size: 11px;
    gap: 4px;
  }
  .pc-keys-grid-6 {
    gap: 4px;
  }
  .pc-keys-grid-6 .pc-key-btn {
    height: 36px;
    font-size: 10px;
    padding: 0 1px;
  }
}

@media (orientation: landscape) and (max-height: 520px) {
  .main-content {
    padding: 8px 14px 68px;
    max-width: 100%;
  }
  .remote-display-layout {
    display: grid;
    grid-template-columns: 1.35fr 1fr;
    gap: 12px;
    align-items: start;
  }
  #screen-viewport {
    aspect-ratio: 16 / 9 !important;
    max-height: calc(100vh - 90px);
  }
  .screen-mini-trackpad {
    height: 85px;
  }
  .click-pad-btn {
    height: 34px;
  }
  .pc-keys-grid-6 .pc-key-btn {
    height: 32px;
    font-size: 9.5px;
  }
  .ios-tab-bar {
    height: 48px;
    bottom: 4px;
  }
}

/* Toast */
.ios-toast {
  position: fixed;
  top: 68px;
  left: 50%;
  transform: translateX(-50%) translateY(-20px);
  background: rgba(30, 30, 32, 0.95);
  backdrop-filter: blur(25px);
  border: 0.5px solid var(--ios-border);
  color: #ffffff;
  padding: 8px 18px;
  border-radius: 999px;
  font-size: 13px;
  font-weight: 600;
  box-shadow: 0 10px 28px rgba(0, 0, 0, 0.6);
  z-index: 100;
  opacity: 0;
  pointer-events: none;
  transition: all 0.28s cubic-bezier(0.25, 1, 0.5, 1);
}

.ios-toast.visible {
  transform: translateX(-50%) translateY(0);
  opacity: 1;
}

/* ════════════ WIRELESS EARPHONES / LIVE PC AUDIO STREAM ════════════ */
.wireless-earphones-card {
  margin-top: 12px;
  background: rgba(22, 22, 28, 0.95);
  border: 1px solid rgba(255, 255, 255, 0.12);
  border-radius: 18px;
  padding: 14px 16px;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.45);
}

.audio-status-pill {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 3px 9px;
  border-radius: 12px;
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.5px;
  text-transform: uppercase;
}

.audio-status-pill .status-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
}

.audio-status-pill.offline {
  background: rgba(255, 255, 255, 0.08);
  color: rgba(255, 255, 255, 0.5);
}
.audio-status-pill.offline .status-dot {
  background: rgba(255, 255, 255, 0.3);
}

.audio-status-pill.online {
  background: rgba(48, 209, 88, 0.18);
  color: #30d158;
  border: 1px solid rgba(48, 209, 88, 0.4);
}
.audio-status-pill.online .status-dot {
  background: #30d158;
  box-shadow: 0 0 8px #30d158;
  animation: pulse-dot 1.2s infinite ease-in-out;
}

@keyframes pulse-dot {
  0%, 100% { opacity: 1; transform: scale(1); }
  50% { opacity: 0.4; transform: scale(0.85); }
}

.audio-stream-btn {
  flex: 1;
  height: 44px;
  border-radius: 14px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  font-size: 13px;
  font-weight: 700;
  cursor: pointer;
  border: none;
  transition: all 0.15s ease;
  user-select: none;
}

.audio-stream-btn.start {
  background: linear-gradient(135deg, #fa2d48 0%, #ff526b 100%);
  color: #fff;
  box-shadow: 0 4px 16px rgba(250, 45, 72, 0.35);
}
.audio-stream-btn.start:active {
  transform: scale(0.95);
  box-shadow: 0 2px 8px rgba(250, 45, 72, 0.2);
}

.audio-stream-btn.stop {
  background: rgba(255, 69, 58, 0.2);
  color: #ff453a;
  border: 1px solid rgba(255, 69, 58, 0.4);
}
.audio-stream-btn.stop:active {
  transform: scale(0.95);
}

/* Equalizer Bars */
.audio-eq-bars {
  display: flex;
  align-items: flex-end;
  gap: 3px;
  height: 24px;
  padding: 0 8px;
}

.audio-eq-bars .bar {
  width: 4px;
  height: 4px;
  border-radius: 2px;
  background: rgba(255, 255, 255, 0.25);
  transition: height 0.15s ease, background-color 0.2s ease;
}

.audio-eq-bars.active .bar {
  background: var(--ios-red);
}

.audio-eq-bars.active .bar-1 { animation: eq-bounce 0.6s infinite ease-in-out; }
.audio-eq-bars.active .bar-2 { animation: eq-bounce 0.8s infinite ease-in-out 0.15s; }
.audio-eq-bars.active .bar-3 { animation: eq-bounce 0.5s infinite ease-in-out 0.3s; }
.audio-eq-bars.active .bar-4 { animation: eq-bounce 0.7s infinite ease-in-out 0.45s; }

@keyframes eq-bounce {
  0%, 100% { height: 5px; }
  50% { height: 22px; }
}

.live-screen-audio-btn {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 4px 10px;
  border-radius: 8px;
  font-size: 11px;
  font-weight: 700;
  border: 0.5px solid rgba(255, 255, 255, 0.18);
  background: rgba(40, 40, 48, 0.85);
  color: rgba(255, 255, 255, 0.8);
  cursor: pointer;
  transition: all 0.15s ease;
}
.live-screen-audio-btn.active {
  background: rgba(250, 45, 72, 0.25);
  border-color: var(--ios-red);
  color: #fff;
}

/* ══════════ 1. DUAL BATTERY WIDGET STYLES ══════════ */
.battery-grid-2 {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
  margin-bottom: 12px;
}
.battery-tile {
  background: rgba(28, 28, 34, 0.85);
  border: 0.5px solid rgba(255, 255, 255, 0.1);
  border-radius: 16px;
  padding: 12px 14px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.battery-tile-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.battery-tile-title {
  font-size: 11px;
  font-weight: 700;
  color: var(--ios-gray-text);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}
.battery-bar-container {
  width: 100%;
  height: 8px;
  background: rgba(255, 255, 255, 0.12);
  border-radius: 4px;
  overflow: hidden;
  margin-top: 2px;
}
.battery-bar-fill {
  height: 100%;
  width: 0%;
  border-radius: 4px;
  background: #30d158;
  transition: width 0.3s ease, background-color 0.3s ease;
}
.battery-val-row {
  display: flex;
  align-items: baseline;
  gap: 5px;
}
.battery-pct-text {
  font-size: 20px;
  font-weight: 800;
  color: #ffffff;
}
.battery-bolt-icon {
  color: #ffd60a;
  font-size: 14px;
  display: none;
}
.battery-state-text {
  font-size: 11px;
  color: rgba(255, 255, 255, 0.5);
}

/* ══════════ 3. WIRELESS MIC & DICTATION STYLES ══════════ */
.mic-action-box {
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.mic-dictate-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  width: 100%;
  padding: 14px;
  border-radius: 16px;
  background: linear-gradient(135deg, rgba(0, 122, 255, 0.25), rgba(88, 86, 214, 0.3));
  border: 1px solid rgba(0, 122, 255, 0.5);
  color: #ffffff;
  font-size: 13.5px;
  font-weight: 700;
  cursor: pointer;
  transition: all 0.2s ease;
}
.mic-dictate-btn.recording {
  background: linear-gradient(135deg, rgba(255, 69, 58, 0.4), rgba(255, 45, 85, 0.6));
  border-color: var(--ios-red);
  animation: pulse-ring 1.2s infinite;
}
.dictate-transcript-box {
  background: rgba(18, 18, 22, 0.9);
  border: 0.5px solid rgba(255, 255, 255, 0.1);
  border-radius: 12px;
  padding: 10px 12px;
  min-height: 48px;
  font-size: 12.5px;
  color: rgba(255, 255, 255, 0.85);
  font-style: italic;
  display: none;
}
.voice-memo-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  width: 100%;
  padding: 12px;
  border-radius: 14px;
  background: rgba(35, 35, 42, 0.85);
  border: 0.5px solid rgba(255, 255, 255, 0.12);
  color: rgba(255, 255, 255, 0.85);
  font-size: 12.5px;
  font-weight: 700;
  cursor: pointer;
}
.voice-memo-btn.recording {
  background: rgba(255, 69, 58, 0.25);
  border-color: #ff453a;
  color: #ff453a;
}

/* ══════════ 4. BEDTIME SLEEP TIMER STYLES ══════════ */
.sleep-timer-presets {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 8px;
  margin-bottom: 12px;
}
.sleep-preset-btn {
  padding: 10px 6px;
  border-radius: 12px;
  background: rgba(36, 36, 44, 0.85);
  border: 0.5px solid rgba(255, 255, 255, 0.12);
  color: #ffffff;
  font-size: 12px;
  font-weight: 700;
  cursor: pointer;
  text-align: center;
  transition: all 0.15s ease;
}
.sleep-preset-btn.active {
  background: rgba(250, 45, 72, 0.25);
  border-color: var(--ios-red);
  color: #fff;
}
.sleep-action-select {
  width: 100%;
  padding: 11px 12px;
  border-radius: 12px;
  background: rgba(24, 24, 30, 0.95);
  border: 0.5px solid rgba(255, 255, 255, 0.15);
  color: #ffffff;
  font-size: 12.5px;
  font-weight: 600;
  outline: none;
  margin-bottom: 12px;
}
.sleep-countdown-banner {
  background: linear-gradient(135deg, rgba(88, 86, 214, 0.2), rgba(0, 122, 255, 0.15));
  border: 0.5px solid rgba(88, 86, 214, 0.4);
  border-radius: 14px;
  padding: 12px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}
.sleep-countdown-time {
  font-size: 18px;
  font-weight: 800;
  color: #fff;
}
.quick-header-pill {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 5px 11px;
  border-radius: 999px;
  background: rgba(40, 40, 50, 0.85);
  border: 0.5px solid rgba(255, 255, 255, 0.15);
  color: #ffffff;
  font-size: 11px;
  font-weight: 700;
  cursor: pointer;
}
.header-battery-pill {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 4px 9px;
  border-radius: 999px;
  background: rgba(25, 25, 32, 0.85);
  border: 0.5px solid rgba(255, 255, 255, 0.1);
  font-size: 10.5px;
  color: rgba(255, 255, 255, 0.7);
}
@keyframes pulse-ring {
  0% { box-shadow: 0 0 0 0 rgba(255, 69, 58, 0.6); }
  70% { box-shadow: 0 0 0 10px rgba(255, 69, 58, 0); }
  100% { box-shadow: 0 0 0 0 rgba(255, 69, 58, 0); }
}
</style>
</head>
<body>
<audio id="pc-audio-stream-player" preload="none" playsinline webkit-playsinline></audio>

<!-- Ambient Backlight -->
<div class="ambient-backdrop">
  <div class="ambient-blob blob-1"></div>
  <div class="ambient-blob blob-2"></div>
</div>

<!-- Header -->
<header>
  <div class="brand">
    <div class="brand-icon">
      <!-- Apple Music Vector Note -->
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#ffffff" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
        <path d="M9 18V5l12-2v13"></path>
        <circle cx="6" cy="18" r="3"></circle>
        <circle cx="18" cy="16" r="3"></circle>
      </svg>
    </div>
    <div class="brand-titles">
      <span class="brand-title">Origin Link</span>
      <span class="brand-subtitle">Connected to Laptop</span>
    </div>
  </div>
  <div style="display:flex;align-items:center;gap:8px;">
    <button id="btn-quick-screen" class="quick-header-pill" title="Open Live Screen Mirror">
      <span>🖥️ Screen</span>
    </button>
    <div id="header-battery-pill" class="header-battery-pill" style="display:none;" title="Battery Levels">
      <span id="header-pc-bat">💻 --%</span>
      <span id="header-phone-bat">📱 --%</span>
    </div>
    <a href="/app" id="header-apk-link" style="display:inline-flex;align-items:center;gap:5px;padding:5px 12px;border-radius:999px;background:rgba(0,122,255,0.18);border:0.5px solid rgba(0,122,255,0.4);color:#5ac8fa;font-size:11px;font-weight:700;text-decoration:none;letter-spacing:0.2px;" title="Download JARVIS Remote Android APK v2.2">
      <svg width="12" height="12" viewBox="0 0 24 24" fill="currentColor"><path d="M17.523 15.3414c-.5511 0-.9993-.4486-.9993-1.0001s.4482-1.0001.9993-1.0001c.552 0 .9997.4486.9997 1.0001s-.4477 1.0001-.9997 1.0001m-11.046 0c-.5511 0-.9993-.4486-.9993-1.0001s.4482-1.0001.9993-1.0001c.552 0 .9997.4486.9997 1.0001s-.4477 1.0001-.9997 1.0001m11.4045-6.02l1.9973-3.4592a.416.416 0 00-.1521-.5676.416.416 0 00-.5682.1523l-2.0223 3.503C15.5902 8.4116 13.8533 8.125 12 8.125s-3.5902.2866-5.1322.8299L4.8455 5.4519a.416.416 0 00-.5682-.1523.416.416 0 00-.1521.5676l1.9973 3.4592C2.6889 11.1867.3432 14.6589 0 18.761h24c-.3432-4.1021-2.6889-7.5743-6.1185-9.4396"/></svg>
      APK v2.2
    </a>
    <div class="ios-pill-badge">
      <div class="ios-pulse-dot"></div>
      <span>Live</span>
    </div>
  </div>
</header>

<div class="main-content">

  <!-- ══════════ TAB 1: NOW PLAYING & SYNCED LYRICS ══════════ -->
  <section id="tab-music" class="view-section active">
    <div class="music-layout-grid">
      <div class="ios-card now-playing-box">
        <div class="cover-wrapper">
          <img id="cover-reflection" class="cover-reflection" src="/api/media/cover" alt="" onerror="this.style.opacity='0'">
          <img id="track-cover" class="cover-art" src="/api/media/cover" alt="Album Artwork" onerror="this.src='/api/media/cover'">
        </div>

        <div class="track-name" id="track-name">No Music Playing</div>
        <div class="artist-name" id="track-artist">Desktop Idle</div>

        <!-- Scrubber -->
        <div class="scrub-container">
          <div class="scrub-track" id="scrub-track">
            <div class="scrub-progress" id="scrub-progress"></div>
          </div>
          <div class="scrub-labels">
            <span id="label-pos">0:00</span>
            <span id="label-dur">0:00</span>
          </div>
        </div>

        <!-- Controls Hub -->
        <div class="controls-hub">
          <!-- Previous -->
          <button class="ctrl-btn" id="ctrl-prev" title="Previous Track">
            <svg width="28" height="28" viewBox="0 0 24 24" fill="currentColor">
              <polygon points="19 20 9 12 19 4 19 20"></polygon>
              <rect x="5" y="4" width="3" height="16" rx="1"></rect>
            </svg>
          </button>

          <!-- Play / Pause -->
          <button class="ctrl-btn play-circle" id="ctrl-playpause" title="Play/Pause">
            <svg id="glyph-play" width="28" height="28" viewBox="0 0 24 24" fill="currentColor">
              <polygon points="6 4 20 12 6 20 6 4"></polygon>
            </svg>
            <svg id="glyph-pause" style="display:none;" width="26" height="26" viewBox="0 0 24 24" fill="currentColor">
              <rect x="6" y="4" width="4" height="16" rx="1.5"></rect>
              <rect x="14" y="4" width="4" height="16" rx="1.5"></rect>
            </svg>
          </button>

          <!-- Next / Skip -->
          <button class="ctrl-btn" id="ctrl-next" title="Next Track">
            <svg width="28" height="28" viewBox="0 0 24 24" fill="currentColor">
              <polygon points="5 4 15 12 5 20 5 4"></polygon>
              <rect x="16" y="4" width="3" height="16" rx="1"></rect>
            </svg>
          </button>
        </div>

        <!-- Apple Control Center Liquid Glass Volume Capsule -->
        <div class="ios-volume-capsule" id="vol-capsule">
          <div class="ios-volume-fill" id="vol-fill"></div>
          <div class="ios-volume-content">
            <div style="display:flex; align-items:center; gap:8px;">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor">
                <polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"></polygon>
                <path d="M15.54 8.46a5 5 0 0 1 0 7.07"></path>
                <path d="M19.07 4.93a10 10 0 0 1 0 14.14"></path>
              </svg>
              <span style="font-size:12px; letter-spacing:0.4px;">VOLUME</span>
            </div>
            <span class="vol-label" id="vol-pct-text">50%</span>
          </div>
        </div>

        <!-- Wireless Earphones Mode / Live PC Audio Streaming -->
        <div class="wireless-earphones-card">
          <div style="display:flex; align-items:center; justify-content:space-between; margin-bottom:10px;">
            <div style="display:flex; align-items:center; gap:8px;">
              <span style="font-size:18px;">🎧</span>
              <div>
                <div style="font-size:12.5px; font-weight:700; color:#fff;">Wireless Earphones Mode</div>
                <div style="font-size:10px; color:rgba(255,255,255,0.45);">Stream PC Audio to Phone</div>
              </div>
            </div>
            <div id="audio-stream-status" class="audio-status-pill offline">
              <span class="status-dot"></span>
              <span id="audio-status-text">OFFLINE</span>
            </div>
          </div>

          <div style="display:flex; align-items:center; justify-content:space-between; gap:10px; margin-bottom:10px;">
            <button id="btn-toggle-audio-stream" class="audio-stream-btn start">
              <span id="audio-btn-icon">▶</span>
              <span id="audio-btn-label">Listen to PC</span>
            </button>
            <div class="audio-eq-bars" id="audio-eq-bars">
              <div class="bar bar-1"></div>
              <div class="bar bar-2"></div>
              <div class="bar bar-3"></div>
              <div class="bar bar-4"></div>
            </div>
          </div>

          <!-- Earphones Volume Control -->
          <div style="display:flex; align-items:center; gap:8px;">
            <span style="font-size:12px; color:rgba(255,255,255,0.5);">🔈</span>
            <input type="range" id="slider-earphones-vol" min="0" max="100" value="80" style="flex:1; accent-color:var(--ios-red);">
            <span style="font-size:12px; color:rgba(255,255,255,0.5);">🔊</span>
            <span id="earphones-vol-label" style="font-size:11px; font-weight:700; min-width:32px; color:rgba(255,255,255,0.85); text-align:right;">80%</span>
          </div>
          <div style="font-size:9.5px; color:rgba(255,255,255,0.35); margin-top:6px; line-height:1.4;">
            ⚡ Low-latency live stream of all PC audio (YouTube, Spotify, Movies, Games) directly through phone earphones. Keeps playing in background.
          </div>
        </div>
      </div>

      <!-- Apple Music Real-Time Synced Lyrics -->
      <div class="ios-card lyrics-card">
        <div class="card-header">
          <span>Synchronized Lyrics</span>
          <span style="color:var(--ios-red); font-size:11px; font-weight:700;">LIVE</span>
        </div>
        <div class="lyrics-container" id="lyrics-container">
          <div class="lyrics-placeholder" id="lyrics-loading">Connecting to music stream...</div>
        </div>
      </div>
    </div>
  </section>

  <!-- ══════════ TAB 2: JARVIS AI ══════════ -->
  <section id="tab-jarvis" class="view-section">
    <div class="ios-card jarvis-hero">
      <div class="siri-ring">
        <div class="siri-inner">
          <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="#fa2d48" stroke-width="2.5">
            <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"></polygon>
          </svg>
        </div>
      </div>
      <div class="siri-badge" id="jarvis-status-badge">JARVIS Ready</div>

      <!-- Chat Bubbles -->
      <div class="chat-window" id="chat-window">
        <div class="imessage jarvis">Hello! I am JARVIS. Ask a task, tap a quick action below, or speak hands-free.</div>
      </div>

      <!-- Apple iOS Horizontal Suggestion Rail -->
      <div class="ios-suggestion-rail">
        <div class="action-chip action-tile" data-action="vision mode">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#00f0ff" stroke-width="2.5">
            <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"></path>
            <circle cx="12" cy="12" r="3"></circle>
          </svg>
          <span style="color:#00f0ff; font-weight:600;">Vision Scan</span>
        </div>

        <div class="action-chip action-tile" data-action="open notepad and do code of hello world in python">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#30d158" stroke-width="2.5">
            <polyline points="16 18 22 12 16 6"></polyline>
            <polyline points="8 6 2 12 8 18"></polyline>
          </svg>
          <span>Notepad &amp; Python</span>
        </div>

        <div class="action-chip action-tile" data-action="skip song">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor">
            <polygon points="5 4 15 12 5 20 5 4"></polygon>
            <rect x="16" y="4" width="3" height="16" rx="1"></rect>
          </svg>
          <span>Skip Track</span>
        </div>

        <div class="action-chip action-tile" data-action="previous song">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor">
            <polygon points="19 20 9 12 19 4 19 20"></polygon>
            <rect x="5" y="4" width="3" height="16" rx="1"></rect>
          </svg>
          <span>Prev Track</span>
        </div>

        <div class="action-chip action-tile" data-action="take a screenshot">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z"></path>
            <circle cx="12" cy="13" r="4"></circle>
          </svg>
          <span>Screenshot</span>
        </div>

        <div class="action-chip action-tile" data-action="make taskbar clear glass">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#0a84ff" stroke-width="2">
            <rect x="2" y="3" width="20" height="14" rx="2"></rect>
            <line x1="8" y1="21" x2="16" y2="21"></line>
            <line x1="12" y1="17" x2="12" y2="21"></line>
          </svg>
          <span>Clear Taskbar</span>
        </div>

        <div class="action-chip action-tile" data-action="what is my battery level">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#30d158" stroke-width="2">
            <rect x="2" y="7" width="16" height="10" rx="2"></rect>
            <line x1="22" y1="11" x2="22" y2="13"></line>
          </svg>
          <span>Battery</span>
        </div>

        <div class="action-chip action-tile" data-action="set volume to 80">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"></polygon>
            <path d="M15.54 8.46a5 5 0 0 1 0 7.07"></path>
          </svg>
          <span>Volume 80%</span>
        </div>

        <div class="action-chip action-tile" data-action="lock pc">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#ff453a" stroke-width="2">
            <rect x="3" y="11" width="18" height="11" rx="2"></rect>
            <path d="M7 11V7a5 5 0 0 1 10 0v4"></path>
          </svg>
          <span>Lock Laptop</span>
        </div>
      </div>

      <!-- Prompt Input -->
      <div class="ios-input-dock">
        <input type="text" class="text-input" id="jarvis-input" placeholder="Ask JARVIS (e.g. 'skip', 'volume 80')...">
        <button class="round-btn btn-mic" id="jarvis-mic" title="Voice Input">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"></path>
            <path d="M19 10v2a7 7 0 0 1-14 0v-2"></path>
            <line x1="12" y1="19" x2="12" y2="23"></line>
          </svg>
        </button>
        <button class="round-btn btn-send" id="jarvis-send" title="Send">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
            <line x1="22" y1="2" x2="11" y2="13"></line>
            <polygon points="22 2 15 22 11 13 2 9 22 2"></polygon>
          </svg>
        </button>
      </div>
    </div>
  </section>

  <!-- ══════════ TAB 3: AIRDROP & FILES ══════════ -->
  <section id="tab-airdrop" class="view-section">
    <div class="ios-card">
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:14px;">
        <div class="card-header" style="margin-bottom:0;">AirDrop to Laptop Shelf</div>
        <span style="font-size:11px;font-weight:700;padding:3px 9px;border-radius:999px;background:rgba(48,209,88,0.18);border:0.5px solid rgba(48,209,88,0.35);color:#30d158;">● Ready</span>
      </div>

      <!-- Multiple file inputs with specific filters for instant Android & Web picker opening -->
      <input type="file" id="upload-input" multiple style="display:none;">
      <input type="file" id="upload-media" accept="image/*,video/*" multiple style="display:none;">
      <input type="file" id="upload-audio" accept="audio/*" multiple style="display:none;">
      <input type="file" id="upload-docs" accept=".pdf,.doc,.docx,.txt,.zip,.xls,.xlsx,.ppt,.pptx" multiple style="display:none;">

      <!-- Live upload progress box -->
      <div id="airdrop-progress-box" class="airdrop-progress-box">
        <div class="airdrop-prog-header">
          <span id="airdrop-prog-name" class="airdrop-prog-name">Uploading...</span>
          <span id="airdrop-prog-pct" class="airdrop-prog-pct">0%</span>
        </div>
        <div class="airdrop-prog-track">
          <div id="airdrop-prog-bar" class="airdrop-prog-bar"></div>
        </div>
        <div id="airdrop-prog-status" class="airdrop-prog-status">Transferring to PC desktop shelf...</div>
      </div>

      <!-- AirDrop Main Interactive Hub -->
      <div class="airdrop-hub" id="airdrop-dropzone" title="Tap to choose any files to send to PC">
        <div class="airdrop-icon-container">
          <div class="airdrop-pulse-ring"></div>
          <div class="airdrop-pulse-ring"></div>
          <div class="airdrop-icon-ring">
            <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.3" stroke-linecap="round" stroke-linejoin="round">
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
              <polyline points="17 8 12 3 7 8"></polyline>
              <line x1="12" y1="3" x2="12" y2="15"></line>
            </svg>
          </div>
        </div>
        <div style="font-size:17px; font-weight:700; margin-bottom:4px; letter-spacing:-0.2px;">Tap to Send Files to Laptop</div>
        <div style="font-size:12.5px; color:var(--ios-gray-text);">Instant Wi-Fi AirDrop into PC Desktop Shelf</div>

        <!-- Quick filter pills -->
        <div class="airdrop-pills-row" id="airdrop-pills">
          <button type="button" class="airdrop-pill-btn" id="pill-send-media" title="Select photos and videos">
            <span>📸</span><span>Photos & Videos</span>
          </button>
          <button type="button" class="airdrop-pill-btn" id="pill-send-audio" title="Select audio and voice recordings">
            <span>🎵</span><span>Audio</span>
          </button>
          <button type="button" class="airdrop-pill-btn" id="pill-send-docs" title="Select documents and PDFs">
            <span>📄</span><span>Documents</span>
          </button>
          <button type="button" class="airdrop-pill-btn" id="pill-send-all" title="Select all file types">
            <span>🗂️</span><span>Browse Files</span>
          </button>
        </div>
      </div>
    </div>

    <!-- Shelf Files List Card -->
    <div class="ios-card">
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:14px;">
        <div class="card-header" style="margin-bottom:0;">Desktop Shelf Files</div>
        <button id="btn-refresh-shelf" class="ios-btn" style="padding:5px 12px;font-size:11.5px;border-radius:12px;background:rgba(255,255,255,0.08);cursor:pointer;" title="Refresh shelf list">
          🔄 Refresh
        </button>
      </div>
      <div class="shelf-card-list" id="shelf-items">
        <div style="font-size:13px; color:var(--ios-gray-text); text-align:center; padding:18px;">
          No files on laptop shelf.
        </div>
      </div>
    </div>
  </section>

  <!-- ══════════ TAB 4: CONTROL CENTER ══════════ -->
  <section id="tab-control" class="view-section">
    <div class="ios-card">
      <div class="card-header">Control Center</div>
      <div class="control-tiles">
        <div class="ios-tile" data-cmd="screenshot">
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="var(--ios-blue)" stroke-width="2">
            <path d="M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z"></path>
            <circle cx="12" cy="13" r="4"></circle>
          </svg>
          <span>Screenshot</span>
        </div>

        <div class="ios-tile" data-cmd="lock_pc">
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="var(--ios-red)" stroke-width="2">
            <rect x="3" y="11" width="18" height="11" rx="2"></rect>
            <path d="M7 11V7a5 5 0 0 1 10 0v4"></path>
          </svg>
          <span>Lock Laptop</span>
        </div>
      </div>
    </div>

    <!-- 2-Way Clipboard Bridge -->
    <div class="ios-card">
      <div class="card-header">Clipboard Bridge</div>
      <textarea class="clipboard-textarea" id="clip-text" placeholder="Type text to send to laptop clipboard..."></textarea>
      <div style="display:flex; gap:8px;">
        <button class="ios-btn" style="flex:1;" id="btn-push-clip">Send to PC</button>
        <button class="ios-btn" style="flex:1;" id="btn-pull-clip">Copy from PC</button>
      </div>
    </div>

    <!-- Dual Battery Status Widget (Feature 4) -->
    <div class="ios-card" id="card-battery-widget">
      <div class="card-header">Bi-Directional Battery Status</div>
      <div class="battery-grid-2">
        <!-- PC Battery -->
        <div class="battery-tile" id="tile-pc-bat">
          <div class="battery-tile-header">
            <span class="battery-tile-title">Laptop</span>
            <span id="bolt-pc-bat" class="battery-bolt-icon">⚡</span>
          </div>
          <div class="battery-val-row">
            <span id="pct-pc-bat" class="battery-pct-text">--%</span>
          </div>
          <div class="battery-bar-container">
            <div id="bar-pc-bat" class="battery-bar-fill" style="width:0%;"></div>
          </div>
          <span id="state-pc-bat" class="battery-state-text">Checking status...</span>
        </div>

        <!-- Phone Battery -->
        <div class="battery-tile" id="tile-phone-bat">
          <div class="battery-tile-header">
            <span class="battery-tile-title">Phone</span>
            <span id="bolt-phone-bat" class="battery-bolt-icon">⚡</span>
          </div>
          <div class="battery-val-row">
            <span id="pct-phone-bat" class="battery-pct-text">--%</span>
          </div>
          <div class="battery-bar-container">
            <div id="bar-phone-bat" class="battery-bar-fill" style="width:0%;"></div>
          </div>
          <span id="state-phone-bat" class="battery-state-text">Checking status...</span>
        </div>
      </div>
    </div>

    <!-- Wireless Phone Mic & Voice Dictation (Feature 3) -->
    <div class="ios-card" id="card-mic-dictate">
      <div class="card-header">Wireless Phone Mic to PC</div>
      <div class="mic-action-box">
        <button id="btn-start-dictate" class="mic-dictate-btn" title="Speak into phone to type live into active PC window">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"></path>
            <path d="M19 10v2a7 7 0 0 1-14 0v-2"></path>
            <line x1="12" y1="19" x2="12" y2="23"></line>
            <line x1="8" y1="23" x2="16" y2="23"></line>
          </svg>
          <span id="label-dictate">Tap to Dictate (Live into PC)</span>
        </button>
        <div id="dictate-transcript" class="dictate-transcript-box">Listening... speak naturally.</div>

        <button id="btn-record-voice-memo" class="voice-memo-btn" title="Record high-quality audio note and send to laptop desktop shelf">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
            <circle cx="12" cy="12" r="8"></circle>
          </svg>
          <span id="label-voice-memo">Record Voice Memo to Shelf</span>
        </button>
      </div>
    </div>

    <!-- Bedtime Sleep Timer & PC Power Automation (Feature 5) -->
    <div class="ios-card" id="card-sleep-timer">
      <div class="card-header">Bedtime Sleep Timer</div>
      <div class="sleep-timer-presets">
        <button class="sleep-preset-btn active" data-min="15">15 Min</button>
        <button class="sleep-preset-btn" data-min="30">30 Min</button>
        <button class="sleep-preset-btn" data-min="45">45 Min</button>
        <button class="sleep-preset-btn" data-min="60">60 Min</button>
      </div>

      <select id="select-sleep-action" class="sleep-action-select">
        <option value="fade_and_sleep" selected>🌙 Fade Music & Sleep PC (Bedtime)</option>
        <option value="sleep">💤 Sleep PC Instantly</option>
        <option value="lock">🔒 Lock PC</option>
        <option value="shutdown">🛑 Shut Down PC</option>
      </select>

      <div id="sleep-countdown-banner" class="sleep-countdown-banner" style="display:none;">
        <div>
          <div style="font-size:11px; font-weight:700; color:rgba(255,255,255,0.7); text-transform:uppercase;">Timer Active</div>
          <div id="sleep-countdown-time" class="sleep-countdown-time">00:00</div>
        </div>
        <button id="btn-cancel-sleep-timer" class="ios-btn" style="padding:6px 14px; background:rgba(255,69,58,0.3); border:0.5px solid #ff453a; color:#fff; font-size:11.5px;">Cancel</button>
      </div>

      <button id="btn-start-sleep-timer" class="ios-btn" style="width:100%;">Start Sleep Timer</button>
    </div>
  </section>

  <!-- ══════════ TAB 5: WIRELESS TRACKPAD, LIVE DISPLAY & REMOTE KEYBOARD ══════════ -->
  <section id="tab-remote" class="view-section">
    <!-- Mode Switcher (Trackpad, Live Display, Keyboard, Presentation) -->
    <div class="remote-mode-switcher">
      <button id="mode-trackpad" class="mode-tab-btn active">Trackpad</button>
      <button id="mode-display" class="mode-tab-btn">Live Screen</button>
      <button id="mode-keyboard" class="mode-tab-btn">Keyboard</button>
      <button id="mode-present" class="mode-tab-btn">Present</button>
    </div>

    <!-- 1. TRACKPAD VIEW -->
    <div id="view-trackpad-content">
      <!-- Window & Tab Quick Control Strip -->
      <div class="pc-keys-grid-6" style="margin-bottom:8px;">
        <button class="pc-key-btn btn-win-min" data-key="minimize" title="Minimize Window">🗕 Min</button>
        <button class="pc-key-btn btn-win-max" data-key="maximize" title="Maximize Window">🗖 Max</button>
        <button class="pc-key-btn btn-win-close" data-key="close" title="Close Window">✕ Close</button>
        <button class="pc-key-btn btn-win-alttab" data-key="alttab" title="Switch App">⇋ AltTab</button>
        <button class="pc-key-btn btn-tab-new" data-key="newtab" title="New Tab">＋ NewTab</button>
        <button class="pc-key-btn btn-tab-close" data-key="closetab" title="Close Tab">⌧ ClsTab</button>
      </div>

      <div class="ios-card" style="padding:12px; margin-bottom:12px;">
        <div style="display:flex; gap:10px; align-items:stretch; width:100%;">
          <!-- High-Precision Trackpad Surface -->
          <div id="trackpad-surface" style="flex:1; height:270px; background:radial-gradient(circle at 50% 50%, rgba(45,45,54,0.65), rgba(16,16,20,0.96)); border-radius:18px; border:1px solid rgba(255,255,255,0.08); display:flex; flex-direction:column; align-items:center; justify-content:center; touch-action:none; user-select:none; position:relative; overflow:hidden;">
            <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="rgba(255,255,255,0.35)" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
              <rect x="2" y="3" width="20" height="14" rx="2"></rect>
              <line x1="8" y1="21" x2="16" y2="21"></line>
              <line x1="12" y1="17" x2="12" y2="21"></line>
            </svg>
            <span style="font-size:12px; font-weight:600; color:rgba(255,255,255,0.5); margin-top:8px;">Swipe: Move • Tap: Click • 2-Finger: Scroll</span>
            <span style="font-size:10.5px; color:rgba(255,255,255,0.32); margin-top:3px;">Double-tap & drag to select • Pinch to zoom PC</span>
          </div>

          <!-- Dedicated Tactile PC Scroll Bar Strip -->
          <div class="pc-scrollbar-track" id="trackpad-scrollbar">
            <button class="scrollbar-btn" id="btn-scroll-up" title="Scroll Up">▲</button>
            <div class="scrollbar-gutter" id="trackpad-scroll-gutter">
              <div class="scrollbar-thumb" id="trackpad-scroll-thumb">
                <span class="scrollbar-thumb-icon">⇅</span>
              </div>
            </div>
            <button class="scrollbar-btn" id="btn-scroll-down" title="Scroll Down">▼</button>
          </div>
        </div>
      </div>

      <!-- Tactile 3-Button Click Pads -->
      <div class="click-pads-grid-3">
        <button class="click-pad-btn primary" id="btn-mouse-left">
          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2"><rect x="6" y="3" width="12" height="18" rx="6"/><path d="M12 3v6"/><path d="M6 9h6"/></svg>
          <span>Left Click</span>
        </button>
        <button class="click-pad-btn accent" id="btn-mouse-double">
          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2"><rect x="6" y="3" width="12" height="18" rx="6"/><path d="M12 3v6"/></svg>
          <span>2x Click</span>
        </button>
        <button class="click-pad-btn secondary" id="btn-mouse-right">
          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2"><rect x="6" y="3" width="12" height="18" rx="6"/><path d="M12 3v6"/><path d="M12 9h6"/></svg>
          <span>Right Click</span>
        </button>
      </div>

      <!-- Quick Clipboard & Selection Strip -->
      <div class="pc-keys-grid-6" style="margin-top:8px; margin-bottom:8px;">
        <button class="pc-key-btn clip-quick-btn" data-key="copy">📋 Copy</button>
        <button class="pc-key-btn clip-quick-btn" data-key="paste">📥 Paste</button>
        <button class="pc-key-btn clip-quick-btn" data-key="selectall">🔲 All</button>
        <button class="pc-key-btn" id="btn-drag-lock" style="color:#ff9f0a;">✋ Select</button>
        <button class="pc-key-btn" data-key="ctrlz" style="color:#ff9f0a;">↶ Undo</button>
        <button class="pc-key-btn" data-key="win" style="color:#007aff;">⊞ Win</button>
      </div>

      <!-- Fast Typing & Paste Strip on Trackpad -->
      <form id="form-trackpad-type" class="remote-type-bar" onsubmit="return false;">
        <input id="input-trackpad-type" class="remote-type-input" type="text" placeholder="Type on PC directly..." autocomplete="off">
        <button type="button" id="btn-trackpad-paste" class="remote-btn-paste">📥 Paste</button>
        <button type="submit" id="btn-trackpad-send" class="remote-btn-type">⌨ Type ↵</button>
      </form>
    </div>

    <!-- 2. LIVE PC DISPLAY & DIRECT TOUCH CONTROL VIEW -->
    <div id="view-display-content" style="display:none;">
      <div class="ios-card" style="padding:12px; margin-bottom:12px;">
        <div class="remote-display-layout">
          <!-- Column 1: Live PC Stream Viewport (Native 16:9 Aspect Ratio) -->
          <div class="remote-display-screen-col">
            <!-- Display Header with Zoom & Fullscreen Controls -->
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
              <div style="display:flex; align-items:center; gap:6px;">
                <span style="display:inline-block; width:8px; height:8px; border-radius:50%; background:#30d158; box-shadow:0 0 8px #30d158;"></span>
                <span style="font-size:12px; font-weight:700; color:#fff;">Live 1080p Screen (16:9)</span>
              </div>

              <div style="display:flex; gap:6px; align-items:center;">
                <!-- Quick Zoom Buttons -->
                <div style="display:flex; gap:3px; align-items:center; background:rgba(255,255,255,0.06); padding:2px 4px; border-radius:8px;">
                  <button class="screen-zoom-btn" data-zoom="1.0" style="padding:3px 7px; border-radius:6px; font-size:10.5px; font-weight:700; border:none; background:var(--ios-red); color:#fff; cursor:pointer;">1x</button>
                  <button class="screen-zoom-btn" data-zoom="1.5" style="padding:3px 7px; border-radius:6px; font-size:10.5px; font-weight:700; border:none; background:transparent; color:#fff; cursor:pointer;">1.5x</button>
                  <button class="screen-zoom-btn" data-zoom="2.0" style="padding:3px 7px; border-radius:6px; font-size:10.5px; font-weight:700; border:none; background:transparent; color:#fff; cursor:pointer;">2x</button>
                  <button class="screen-zoom-btn" data-zoom="3.0" style="padding:3px 7px; border-radius:6px; font-size:10.5px; font-weight:700; border:none; background:transparent; color:#fff; cursor:pointer;">3x</button>
                </div>
                <!-- Screen Quality & Tap Mode -->
                <button id="btn-screen-quality" style="padding:4px 8px; border-radius:8px; font-size:11px; font-weight:700; border:0.5px solid var(--ios-border); background:rgba(40,40,48,0.85); color:#30d158; cursor:pointer;" title="Toggle Quality / Speed">⚡ 30 FPS</button>
                <button id="btn-screen-tap-mode" style="padding:4px 8px; border-radius:8px; font-size:11px; font-weight:700; border:0.5px solid var(--ios-border); background:rgba(40,40,48,0.85); color:#ffffff; cursor:pointer;" title="Tap to Click Action">🖱️ Left</button>

                <!-- Live Screen Audio Toggle -->
                <button id="btn-live-screen-audio" class="live-screen-audio-btn" title="Toggle Live Audio Stream">
                  <span>🎧</span> <span id="label-live-audio">Audio</span>
                </button>
                <!-- Expand / Compact Viewport -->
                <button id="btn-viewport-expand" style="padding:4px 9px; border-radius:8px; font-size:11px; font-weight:700; border:0.5px solid var(--ios-border); background:rgba(40,40,48,0.85); color:#007aff; cursor:pointer;">⛶ Expand</button>
              </div>
            </div>

            <!-- Live Viewport Window with Integrated PC Scroll Bar -->
            <div style="display:flex; gap:8px; align-items:stretch; width:100%;">
              <div id="screen-viewport">
                <img id="live-screen-img" src="" style="width:100%; height:100%; object-fit:contain; display:block; transform-origin:center center; transition:transform 0.12s ease-out; pointer-events:none;" alt="Live PC View">
                <div id="screen-loading-overlay" style="position:absolute; inset:0; background:rgba(10,10,14,0.85); display:flex; flex-direction:column; align-items:center; justify-content:center; gap:8px;">
                  <div style="width:24px; height:24px; border:2.5px solid rgba(255,255,255,0.2); border-top-color:var(--ios-red); border-radius:50%; animation:spin 0.8s linear infinite;"></div>
                  <span style="font-size:11px; color:rgba(255,255,255,0.6);">Loading live PC display…</span>
                </div>
              </div>

              <!-- Live Screen Dedicated PC Scroll Bar Strip -->
              <div class="pc-scrollbar-track compact" id="screen-scrollbar">
                <button class="scrollbar-btn compact" id="btn-screen-scroll-up" title="Scroll Up">▲</button>
                <div class="scrollbar-gutter" id="screen-scroll-gutter">
                  <div class="scrollbar-thumb compact" id="screen-scroll-thumb">
                    <span class="scrollbar-thumb-icon">⇅</span>
                  </div>
                </div>
                <button class="scrollbar-btn compact" id="btn-screen-scroll-down" title="Scroll Down">▼</button>
              </div>
            </div>

            <div style="display:flex; justify-content:space-between; align-items:center; margin-top:8px; font-size:11px; color:var(--ios-gray-text);">
              <span>Tap screen to direct-click • 16:9 PC View</span>
              <button id="btn-screen-refresh" style="background:transparent; border:none; color:var(--ios-blue); font-size:11px; font-weight:700; cursor:pointer;">Reconnect ↻</button>
            </div>
          </div>

          <!-- Column 2: Controls Hub (Live Touchpad, Click Pads, Type Bar, Keypad) -->
          <div class="remote-display-controls-col">
            <!-- Live Precision Touchpad Strip (Steer mouse while watching screen above) -->
            <div class="mini-touchpad-card" id="screen-mini-trackpad-card">
              <div class="mini-touchpad-header">
                <div style="display:flex; align-items:center; gap:6px;">
                  <span class="live-dot-pulse"></span>
                  <span style="font-size:11.5px; font-weight:700; color:#fff;">Live Touchpad</span>
                </div>
                <span style="font-size:10.5px; color:rgba(255,255,255,0.45);">Swipe to steer • Tap to click • 2-finger scroll</span>
              </div>
              <div id="screen-mini-trackpad" class="screen-mini-trackpad">
                <div class="mini-trackpad-reticle">
                  <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="rgba(255,255,255,0.38)" stroke-width="1.8">
                    <circle cx="12" cy="12" r="9"/>
                    <line x1="12" y1="3" x2="12" y2="7"/>
                    <line x1="12" y1="17" x2="12" y2="21"/>
                    <line x1="3" y1="12" x2="7" y2="12"/>
                    <line x1="17" y1="12" x2="21" y2="12"/>
                    <circle cx="12" cy="12" r="2.5" fill="rgba(255,255,255,0.45)"/>
                  </svg>
                  <span style="font-size:10.5px; color:rgba(255,255,255,0.45); font-weight:600; margin-top:3px;">Steer PC Cursor</span>
                </div>
              </div>
            </div>

            <!-- Tactile Mouse Click Pads for Live Screen -->
            <div class="click-pads-grid-3">
              <button class="click-pad-btn primary" id="btn-screen-left-click">
                <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2"><rect x="6" y="3" width="12" height="18" rx="6"/><path d="M12 3v6"/><path d="M6 9h6"/></svg>
                <span>Left Click</span>
              </button>
              <button class="click-pad-btn accent" id="btn-screen-double-click">
                <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2"><rect x="6" y="3" width="12" height="18" rx="6"/><path d="M12 3v6"/></svg>
                <span>2x Click</span>
              </button>
              <button class="click-pad-btn secondary" id="btn-screen-right-click">
                <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2"><rect x="6" y="3" width="12" height="18" rx="6"/><path d="M12 3v6"/><path d="M12 9h6"/></svg>
                <span>Right Click</span>
              </button>
            </div>

            <!-- Quick Typing & Paste bar directly below screen -->
            <form id="form-screen-type" class="remote-type-bar" onsubmit="return false;">
              <input id="input-screen-type" class="remote-type-input" type="text" placeholder="Type on PC while watching screen..." autocomplete="off">
              <button type="button" id="btn-screen-paste" class="remote-btn-paste">📥 Paste</button>
              <button type="submit" id="btn-screen-send" class="remote-btn-type">⌨ Type ↵</button>
            </form>

            <!-- Unified Remote Keypad & Window Control Hub (4 Perfectly Aligned 6-Column Rows) -->
            <div class="live-screen-keypad">
              <!-- Row 1: Window & Tab Management -->
              <div class="pc-keys-grid-6">
                <button class="pc-key-btn btn-win-min" data-key="minimize" title="Minimize Window (Win+Down)">🗕 Min</button>
                <button class="pc-key-btn btn-win-max" data-key="maximize" title="Maximize Window (Win+Up)">🗖 Max</button>
                <button class="pc-key-btn btn-win-close" data-key="close" title="Close Window (Alt+F4)">✕ Close</button>
                <button class="pc-key-btn btn-win-alttab" data-key="alttab" title="Switch App (Alt+Tab)">⇋ AltTab</button>
                <button class="pc-key-btn btn-tab-new" data-key="newtab" title="New Tab (Ctrl+T)">＋ NewTab</button>
                <button class="pc-key-btn btn-tab-close" data-key="closetab" title="Close Tab (Ctrl+W)">⌧ ClsTab</button>
              </div>

              <!-- Row 2: System & Core Execution -->
              <div class="pc-keys-grid-6">
                <button class="pc-key-btn" data-key="esc" style="color:#ff453a;">⎋ Esc</button>
                <button class="pc-key-btn" data-key="tab">⇥ Tab</button>
                <button class="pc-key-btn" data-key="win" style="color:#007aff;">⊞ Win</button>
                <button class="pc-key-btn" data-key="backspace">⌫ Back</button>
                <button class="pc-key-btn" data-key="space">␣ Space</button>
                <button class="pc-key-btn" data-key="enter" style="background:linear-gradient(135deg, rgba(250,45,72,0.7), rgba(250,45,72,0.95)); border-color:var(--ios-red); color:#fff;">↵ Enter</button>
              </div>

              <!-- Row 3: Directional & Page Navigation -->
              <div class="pc-keys-grid-6">
                <button class="pc-key-btn" data-key="left">◀ Left</button>
                <button class="pc-key-btn" data-key="up">▲ Up</button>
                <button class="pc-key-btn" data-key="down">▼ Down</button>
                <button class="pc-key-btn" data-key="right">▶ Right</button>
                <button class="pc-key-btn" data-key="pgup" style="color:#30d158;">⇞ PgUp</button>
                <button class="pc-key-btn" data-key="pgdn" style="color:#30d158;">⇟ PgDn</button>
              </div>

              <!-- Row 4: Clipboard & Jump Actions -->
              <div class="pc-keys-grid-6">
                <button class="pc-key-btn clip-quick-btn" data-key="copy">📋 Copy</button>
                <button class="pc-key-btn clip-quick-btn" data-key="paste">📥 Paste</button>
                <button class="pc-key-btn clip-quick-btn" data-key="selectall">🔲 All</button>
                <button class="pc-key-btn" data-key="ctrlz" style="color:#ff9f0a;">↶ Undo</button>
                <button class="pc-key-btn" data-key="home">⏮ Home</button>
                <button class="pc-key-btn" data-key="end">⏭ End</button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 3. DEDICATED FULL KEYBOARD VIEW -->
    <div id="view-keyboard-content" style="display:none;">
      <div class="ios-card" style="padding:14px; margin-bottom:12px;">
        <div style="font-size:11.5px; font-weight:700; color:var(--ios-gray-text); margin-bottom:8px; text-transform:uppercase; letter-spacing:0.6px;">Remote PC Keyboard</div>
        
        <!-- Main Text Input Box -->
        <textarea id="input-full-keyboard" placeholder="Type words, paragraphs, or commands here..." style="width:100%; height:90px; background:rgba(20,20,24,0.9); border:0.5px solid var(--ios-border); border-radius:14px; color:#fff; font-size:14px; padding:10px; outline:none; resize:none; font-family:var(--font-stack);" autocomplete="off"></textarea>
        
        <div style="display:flex; justify-content:space-between; align-items:center; margin-top:10px; gap:8px;">
          <label style="display:flex; align-items:center; gap:6px; font-size:11.5px; color:var(--ios-gray-text); cursor:pointer;">
            <input type="checkbox" id="check-live-type" style="accent-color:var(--ios-red);">
            <span>Live Keystrokes</span>
          </label>
          <div style="display:flex; gap:6px;">
            <button id="btn-full-keyboard-paste" class="remote-btn-paste">📥 Paste</button>
            <button id="btn-full-keyboard-send" class="remote-btn-type">⌨ Type ↵</button>
          </div>
        </div>
      </div>

      <!-- Full PC Modifier Keys Pad -->
      <div class="ios-card" style="padding:14px; margin-bottom:12px;">
        <div style="font-size:11.5px; font-weight:700; color:var(--ios-gray-text); margin-bottom:10px; text-transform:uppercase; letter-spacing:0.6px;">System & Editing Keys</div>
        <div style="display:grid; grid-template-columns:repeat(4, 1fr); gap:8px; margin-bottom:12px;">
          <button class="pc-key-btn" data-key="esc" style="color:#ff453a;">⎋ Esc</button>
          <button class="pc-key-btn" data-key="tab">⇥ Tab</button>
          <button class="pc-key-btn" data-key="win" style="color:#007aff;">⊞ Win</button>
          <button class="pc-key-btn" data-key="backspace">⌫ Back</button>
          
          <button class="pc-key-btn" data-key="ctrlz" style="color:#ff9f0a;">↶ Undo</button>
          <button class="pc-key-btn" data-key="copy">📋 Copy</button>
          <button class="pc-key-btn" data-key="paste">📥 Paste</button>
          <button class="pc-key-btn" data-key="alttab" style="color:#5856d6;">⇥ Alt+Tab</button>
        </div>

        <div style="font-size:11.5px; font-weight:700; color:var(--ios-gray-text); margin-bottom:10px; text-transform:uppercase; letter-spacing:0.6px;">Arrow Navigation</div>
        <div style="display:flex; flex-direction:column; align-items:center; gap:6px;">
          <button class="pc-key-btn" data-key="up" style="width:76px; height:40px; font-size:15px; font-weight:800;">▲</button>
          <div style="display:flex; gap:8px;">
            <button class="pc-key-btn" data-key="left" style="width:76px; height:40px; font-size:15px; font-weight:800;">◀</button>
            <button class="pc-key-btn" data-key="down" style="width:76px; height:40px; font-size:15px; font-weight:800;">▼</button>
            <button class="pc-key-btn" data-key="right" style="width:76px; height:40px; font-size:15px; font-weight:800;">▶</button>
          </div>
          <div style="display:flex; gap:8px; width:100%; margin-top:6px;">
            <button class="pc-key-btn" data-key="space" style="flex:2; height:40px;">␣ Space</button>
            <button class="pc-key-btn" data-key="enter" style="flex:1; height:40px; background:linear-gradient(135deg, rgba(255,45,85,0.7), rgba(255,45,85,0.95)); border:none;">↵ Enter</button>
          </div>
        </div>
      </div>
    </div>

    <!-- 4. PRESENTATION CLICKER VIEW -->
    <div id="view-present-content" style="display:none;">
      <div class="ios-card" style="padding:16px; margin-bottom:14px;">
        <div style="font-size:11.5px; font-weight:700; color:var(--ios-gray-text); margin-bottom:12px; text-transform:uppercase; letter-spacing:0.6px;">Slide Navigation</div>
        <div style="display:flex; gap:12px; margin-bottom:14px;">
          <button class="present-btn" data-key="prev" style="flex:1; height:120px; background:rgba(35,35,42,0.9); border:1px solid rgba(255,255,255,0.1); border-radius:20px; color:#fff; font-size:17px; font-weight:800; display:flex; flex-direction:column; align-items:center; justify-content:center; gap:8px; cursor:pointer;">
            <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
              <polyline points="15 18 9 12 15 6"></polyline>
            </svg>
            <span>PREV</span>
          </button>
          <button class="present-btn" data-key="next" style="flex:1; height:120px; background:linear-gradient(135deg, rgba(255,69,58,0.3), rgba(255,69,58,0.55)); border:1.5px solid var(--ios-red); border-radius:20px; color:#fff; font-size:17px; font-weight:800; display:flex; flex-direction:column; align-items:center; justify-content:center; gap:8px; cursor:pointer;">
            <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
              <polyline points="9 18 15 12 9 6"></polyline>
            </svg>
            <span>NEXT</span>
          </button>
        </div>

        <div style="font-size:11.5px; font-weight:700; color:var(--ios-gray-text); margin-bottom:12px; text-transform:uppercase; letter-spacing:0.6px;">Slide Controls</div>
        <div style="display:grid; grid-template-columns:1fr 1fr; gap:10px;">
          <button class="present-btn" data-key="f5" style="padding:14px; background:rgba(32,32,36,0.9); border:0.5px solid var(--ios-border); border-radius:14px; color:#fff; font-size:12.5px; font-weight:700; cursor:pointer; display:flex; align-items:center; justify-content:center; gap:6px;">
            <span>▶ Start (F5)</span>
          </button>
          <button class="present-btn" data-key="esc" style="padding:14px; background:rgba(32,32,36,0.9); border:0.5px solid var(--ios-border); border-radius:14px; color:#ff453a; font-size:12.5px; font-weight:700; cursor:pointer; display:flex; align-items:center; justify-content:center; gap:6px;">
            <span>✕ Exit (Esc)</span>
          </button>
          <button class="present-btn" data-key="b" style="padding:14px; background:rgba(32,32,36,0.9); border:0.5px solid var(--ios-border); border-radius:14px; color:#fff; font-size:12.5px; font-weight:700; cursor:pointer; display:flex; align-items:center; justify-content:center; gap:6px;">
            <span>⬛ Blackout (B)</span>
          </button>
          <button class="present-btn" data-key="space" style="padding:14px; background:rgba(32,32,36,0.9); border:0.5px solid var(--ios-border); border-radius:14px; color:#fff; font-size:12.5px; font-weight:700; cursor:pointer; display:flex; align-items:center; justify-content:center; gap:6px;">
            <span>␣ Advance (Space)</span>
          </button>
        </div>
      </div>
    </div>
  </section>

</div>

<!-- Floating Apple Tab Bar -->
<nav class="ios-tab-bar">
  <div class="tab-btn active" data-tab="tab-music">
    <svg width="22" height="22" viewBox="0 0 24 24" fill="currentColor">
      <path d="M12 3v10.55c-.59-.34-1.27-.55-2-.55-2.21 0-4 1.79-4 4s1.79 4 4 4 4-1.79 4-4V7h4V3h-6z"></path>
    </svg>
    <span>Music</span>
  </div>

  <div class="tab-btn" data-tab="tab-remote">
    <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
      <rect x="2" y="3" width="20" height="14" rx="2"></rect>
      <line x1="8" y1="21" x2="16" y2="21"></line>
      <line x1="12" y1="17" x2="12" y2="21"></line>
    </svg>
    <span>Remote</span>
  </div>

  <div class="tab-btn" data-tab="tab-jarvis">
    <svg width="22" height="22" viewBox="0 0 24 24" fill="currentColor">
      <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"></polygon>
    </svg>
    <span>JARVIS</span>
  </div>

  <div class="tab-btn" data-tab="tab-airdrop">
    <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
      <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
      <polyline points="17 8 12 3 7 8"></polyline>
      <line x1="12" y1="3" x2="12" y2="15"></line>
    </svg>
    <span>AirDrop</span>
  </div>

  <div class="tab-btn" data-tab="tab-control">
    <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
      <line x1="4" y1="21" x2="4" y2="14"></line>
      <line x1="4" y1="10" x2="4" y2="3"></line>
      <line x1="12" y1="21" x2="12" y2="12"></line>
      <line x1="12" y1="8" x2="12" y2="3"></line>
      <line x1="20" y1="21" x2="20" y2="16"></line>
      <line x1="20" y1="12" x2="20" y2="3"></line>
      <line x1="1" y1="14" x2="7" y2="14"></line>
      <line x1="9" y1="8" x2="15" y2="8"></line>
      <line x1="17" y1="16" x2="23" y2="16"></line>
    </svg>
    <span>Control</span>
  </div>
</nav>

<!-- iOS Toast -->
<div class="ios-toast" id="ios-toast">
  <span id="toast-msg">Success</span>
</div>

<script>
// State
let isPlaying = false;
let currentPos = 0.0;
let currentDur = 0.0;
let lyricsList = [];
let activeIdx = -1;
let currentSongTitle = "";

function showToast(msg) {
  const t = document.getElementById("ios-toast");
  document.getElementById("toast-msg").innerText = msg;
  t.classList.add("visible");
  setTimeout(() => t.classList.remove("visible"), 2000);
}

function fmtTime(sec) {
  if (isNaN(sec) || sec < 0) return "0:00";
  const m = Math.floor(sec / 60);
  const s = Math.floor(sec % 60);
  return `${m}:${s < 10 ? '0' : ''}${s}`;
}

// Tab Switching
function activateTab(tabId) {
  document.querySelectorAll(".tab-btn").forEach(b => b.classList.remove("active"));
  document.querySelectorAll(".view-section").forEach(v => v.classList.remove("active"));
  const btn = document.querySelector(`.tab-btn[data-tab="${tabId}"]`);
  const target = document.getElementById(tabId);
  if (btn) btn.classList.add("active");
  if (target) target.classList.add("active");
}

document.querySelectorAll(".tab-btn").forEach(btn => {
  btn.addEventListener("click", () => {
    activateTab(btn.dataset.tab);
  });
});

// Auto-activate Remote tab if accessed via /remote or #remote
window.addEventListener("DOMContentLoaded", () => {
  const p = window.location.pathname.toLowerCase();
  const h = window.location.hash.toLowerCase();
  if (p.includes("remote") || h.includes("remote")) {
    activateTab("tab-remote");
    if (h.includes("screen") || h.includes("display")) {
      setRemoteMode("display");
    } else if (h.includes("keyboard")) {
      setRemoteMode("keyboard");
    } else {
      setRemoteMode("trackpad");
    }
  }
});

// ══════════ MUSIC & LYRICS CONTROLLER ══════════
const trackCover = document.getElementById("track-cover");
const coverReflection = document.getElementById("cover-reflection");
const trackName = document.getElementById("track-name");
const trackArtist = document.getElementById("track-artist");
const labelPos = document.getElementById("label-pos");
const labelDur = document.getElementById("label-dur");
const scrubProgress = document.getElementById("scrub-progress");
const scrubTrack = document.getElementById("scrub-track");
const glyphPlay = document.getElementById("glyph-play");
const glyphPause = document.getElementById("glyph-pause");
const lyricsBox = document.getElementById("lyrics-container");
const volCapsule = document.getElementById("vol-capsule");
const volFill = document.getElementById("vol-fill");
const volPctText = document.getElementById("vol-pct-text");

let isDraggingVol = false;

function setVolumePct(pct, shouldSend = true) {
  const clamped = Math.max(0, Math.min(100, Math.round(pct)));
  if (volFill) volFill.style.width = clamped + "%";
  if (volPctText) volPctText.innerText = clamped + "%";
  if (shouldSend) {
    sendCommand("set_volume", clamped);
  }
}

function handleVolTouch(e) {
  if (!volCapsule) return;
  const rect = volCapsule.getBoundingClientRect();
  const clientX = e.touches ? e.touches[0].clientX : e.clientX;
  const ratio = Math.max(0, Math.min(1, (clientX - rect.left) / rect.width));
  setVolumePct(ratio * 100, true);
}

if (volCapsule) {
  volCapsule.addEventListener("mousedown", (e) => {
    isDraggingVol = true;
    handleVolTouch(e);
  });
  window.addEventListener("mousemove", (e) => {
    if (isDraggingVol) handleVolTouch(e);
  });
  window.addEventListener("mouseup", () => { isDraggingVol = false; });

  volCapsule.addEventListener("touchstart", (e) => {
    isDraggingVol = true;
    handleVolTouch(e);
  }, { passive: true });
  window.addEventListener("touchmove", (e) => {
    if (isDraggingVol) handleVolTouch(e);
  }, { passive: true });
  window.addEventListener("touchend", () => { isDraggingVol = false; });
}

// Next / Skip
document.getElementById("ctrl-next").addEventListener("click", () => {
  sendCommand("next_track");
  showToast("Skipping to next track");
});

// Previous
document.getElementById("ctrl-prev").addEventListener("click", () => {
  sendCommand("prev_track");
  showToast("Playing previous track");
});

// Play / Pause
document.getElementById("ctrl-playpause").addEventListener("click", () => {
  sendCommand("play_pause");
  isPlaying = !isPlaying;
  setPlayState(isPlaying);
});

function setPlayState(playing) {
  glyphPlay.style.display = playing ? "none" : "block";
  glyphPause.style.display = playing ? "block" : "none";
  if (playing) {
    trackCover.classList.add("playing");
  } else {
    trackCover.classList.remove("playing");
  }
}

// Scrubber Click
scrubTrack.addEventListener("click", (e) => {
  if (currentDur <= 0) return;
  const rect = scrubTrack.getBoundingClientRect();
  const ratio = Math.max(0, Math.min(1, (e.clientX - rect.left) / rect.width));
  const target = ratio * currentDur;
  currentPos = target;
  updateScrubber();
  sendCommand("seek", target);
});

function updateScrubber() {
  if (currentDur > 0) {
    const pct = Math.min(100, (currentPos / currentDur) * 100);
    scrubProgress.style.width = pct + "%";
    labelPos.innerText = fmtTime(currentPos);
    labelDur.innerText = fmtTime(currentDur);
  }
}

// Render Lyrics
function renderLyrics(lines) {
  lyricsBox.innerHTML = "";
  if (!lines || lines.length === 0) {
    lyricsBox.innerHTML = '<div class="lyrics-placeholder">♪ Instrumental or searching lyrics... ♪</div>';
    return;
  }
  lines.forEach((item, idx) => {
    const el = document.createElement("div");
    el.className = "lyric-item";
    el.dataset.idx = idx;
    el.dataset.sec = item.sec;
    el.innerText = item.text || "♪";
    el.addEventListener("click", () => {
      const sec = parseFloat(item.sec);
      sendCommand("seek", sec);
      currentPos = sec;
      highlightLyric(idx, true);
    });
    lyricsBox.appendChild(el);
  });
}

function highlightLyric(idx, force = false) {
  if (idx === activeIdx && !force) return;
  activeIdx = idx;
  const all = lyricsBox.querySelectorAll(".lyric-item");
  all.forEach((item, i) => {
    if (i === idx) {
      item.classList.add("active");
      // Center active lyric with Apple smooth scroll
      const boxRect = lyricsBox.getBoundingClientRect();
      const lineRect = item.getBoundingClientRect();
      const offset = (lineRect.top - boxRect.top) - (boxRect.height / 2) + (lineRect.height / 2);
      lyricsBox.scrollTop += offset;
    } else {
      item.classList.remove("active");
    }
  });
}

// High-Frequency Real-Time Lyrics Evaluator (Matches playback timestamp exactly)
function evaluateCurrentLyric() {
  if (!lyricsList || lyricsList.length === 0) return;
  let targetIdx = 0;
  for (let i = 0; i < lyricsList.length; i++) {
    if (currentPos >= lyricsList[i].sec) {
      targetIdx = i;
    } else {
      break;
    }
  }
  highlightLyric(targetIdx);
}

let isFetchingLyrics = false;
async function fetchLyrics() {
  if (isFetchingLyrics) return;
  isFetchingLyrics = true;
  try {
    const res = await fetch("/api/media/lyrics");
    if (!res.ok) return;
    const data = await res.json();
    if (data.lines && data.lines.length > 0) {
      if (lyricsList.length !== data.lines.length || data.title !== currentSongTitle) {
        currentSongTitle = data.title;
        lyricsList = data.lines;
        renderLyrics(lyricsList);
        evaluateCurrentLyric();
      }
    }
  } catch (e) {
  } finally {
    isFetchingLyrics = false;
  }
}

// ══════════ JARVIS AI CONTROLLER ══════════
const chatWindow = document.getElementById("chat-window");
const jarvisInput = document.getElementById("jarvis-input");
const jarvisStatus = document.getElementById("jarvis-status-badge");
const jarvisSend = document.getElementById("jarvis-send");
const jarvisMic = document.getElementById("jarvis-mic");

function addMessage(role, text) {
  const el = document.createElement("div");
  el.className = `imessage ${role}`;
  el.innerText = text;
  chatWindow.appendChild(el);
  chatWindow.scrollTop = chatWindow.scrollHeight;
}

async function askJarvis(query) {
  if (!query || !query.trim()) return;
  const q = query.trim();
  addMessage("user", q);
  jarvisInput.value = "";
  jarvisStatus.innerText = "Executing...";

  try {
    const res = await fetch("/api/jarvis", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query: q })
    });
    const data = await res.json();
    if (!data.success) {
      addMessage("jarvis", "Could not dispatch request.");
    }
  } catch (e) {
    addMessage("jarvis", "Network error contacting laptop.");
  }
}

jarvisSend.addEventListener("click", () => askJarvis(jarvisInput.value));
jarvisInput.addEventListener("keydown", (e) => {
  if (e.key === "Enter") askJarvis(jarvisInput.value);
});

// Action buttons (Skip track, previous, screenshot, etc.)
document.querySelectorAll(".action-tile").forEach(tile => {
  tile.addEventListener("click", () => {
    const action = tile.dataset.action;
    if (action) {
      askJarvis(action);
      showToast(`Triggered ${action}`);
    }
  });
});

// Voice Input
if ("webkitSpeechRecognition" in window || "SpeechRecognition" in window) {
  const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
  const rec = new SR();
  rec.continuous = false;
  rec.interimResults = false;
  rec.lang = "en-US";

  rec.onstart = () => {
    jarvisMic.classList.add("active-listening");
    jarvisStatus.innerText = "Listening to phone mic...";
  };
  rec.onresult = (e) => {
    const text = e.results[0][0].transcript;
    askJarvis(text);
  };
  rec.onend = () => jarvisMic.classList.remove("active-listening");
  rec.onerror = () => jarvisMic.classList.remove("active-listening");

  jarvisMic.addEventListener("click", () => {
    try { rec.start(); } catch (e) { rec.stop(); }
  });
}

// ══════════ AIRDROP & FILES ══════════
const airdropDropzone = document.getElementById("airdrop-dropzone");
const uploadInput = document.getElementById("upload-input");
const uploadMedia = document.getElementById("upload-media");
const uploadAudio = document.getElementById("upload-audio");
const uploadDocs = document.getElementById("upload-docs");

function triggerFilePicker(inputEl) {
  if (window.AndroidBridge && typeof window.AndroidBridge.vibrate === "function") {
    try { window.AndroidBridge.vibrate(20); } catch (e) {}
  } else if (navigator.vibrate) {
    try { navigator.vibrate(20); } catch (e) {}
  }

  if (inputEl) {
    try {
      inputEl.value = "";
      inputEl.click();
    } catch (e) {
      if (window.AndroidBridge && typeof window.AndroidBridge.triggerNativeFilePicker === "function") {
        window.AndroidBridge.triggerNativeFilePicker();
      }
    }
  }
}

// Hook up main dropzone
if (airdropDropzone) {
  airdropDropzone.addEventListener("click", (e) => {
    if (e.target.closest(".airdrop-pill-btn")) return;
    triggerFilePicker(uploadInput);
  });
}

// Hook up category pills
const pillMedia = document.getElementById("pill-send-media");
const pillAudio = document.getElementById("pill-send-audio");
const pillDocs = document.getElementById("pill-send-docs");
const pillAll = document.getElementById("pill-send-all");

if (pillMedia) pillMedia.addEventListener("click", (e) => { e.stopPropagation(); triggerFilePicker(uploadMedia || uploadInput); });
if (pillAudio) pillAudio.addEventListener("click", (e) => { e.stopPropagation(); triggerFilePicker(uploadAudio || uploadInput); });
if (pillDocs) pillDocs.addEventListener("click", (e) => { e.stopPropagation(); triggerFilePicker(uploadDocs || uploadInput); });
if (pillAll) pillAll.addEventListener("click", (e) => { e.stopPropagation(); triggerFilePicker(uploadInput); });

// Attach change listeners to all file inputs
[uploadInput, uploadMedia, uploadAudio, uploadDocs].forEach(input => {
  if (!input) return;
  input.addEventListener("change", (e) => {
    if (e.target.files && e.target.files.length > 0) {
      uploadFiles(Array.from(e.target.files));
    }
  });
});

function formatBytes(bytes, decimals = 1) {
  if (!bytes || bytes === 0) return '0 B';
  const k = 1024;
  const dm = decimals < 0 ? 0 : decimals;
  const sizes = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + ' ' + sizes[i];
}

async function uploadFiles(files) {
  if (!files || files.length === 0) return;
  const progBox = document.getElementById("airdrop-progress-box");
  const progName = document.getElementById("airdrop-prog-name");
  const progPct = document.getElementById("airdrop-prog-pct");
  const progBar = document.getElementById("airdrop-prog-bar");
  const progStatus = document.getElementById("airdrop-prog-status");

  if (progBox) progBox.style.display = "block";

  for (let i = 0; i < files.length; i++) {
    const f = files[i];
    const prefix = files.length > 1 ? `(${i + 1}/${files.length}) ` : "";
    if (progName) progName.textContent = `${prefix}${f.name}`;
    if (progPct) progPct.textContent = "0%";
    if (progBar) progBar.style.width = "0%";
    if (progStatus) progStatus.textContent = `Sending ${formatBytes(f.size)} to laptop shelf...`;

    await new Promise((resolve) => {
      const xhr = new XMLHttpRequest();
      xhr.open("POST", `/api/upload?filename=${encodeURIComponent(f.name)}`, true);

      xhr.upload.onprogress = (e) => {
        if (e.lengthComputable) {
          const pct = Math.round((e.loaded / e.total) * 100);
          if (progPct) progPct.textContent = `${pct}%`;
          if (progBar) progBar.style.width = `${pct}%`;
        }
      };

      xhr.onload = () => {
        if (xhr.status === 200) {
          if (progPct) progPct.textContent = "100%";
          if (progBar) progBar.style.width = "100%";
          if (progStatus) progStatus.textContent = "✅ Saved to Laptop Desktop Shelf!";
          showToast(`AirDropped ${f.name}!`);
        } else {
          if (progStatus) progStatus.textContent = "⚠️ Upload error";
          showToast(`Upload failed for ${f.name}`);
        }
        resolve();
      };

      xhr.onerror = () => {
        if (progStatus) progStatus.textContent = "⚠️ Connection error";
        resolve();
      };

      xhr.send(f);
    });
  }

  fetchStatus();

  if (window.AndroidBridge && typeof window.AndroidBridge.vibrate === "function") {
    try { window.AndroidBridge.vibrate(40); } catch (e) {}
  } else if (navigator.vibrate) {
    try { navigator.vibrate(40); } catch (e) {}
  }

  setTimeout(() => {
    if (progBox) progBox.style.display = "none";
  }, 2200);
}

const btnRefreshShelf = document.getElementById("btn-refresh-shelf");
if (btnRefreshShelf) {
  btnRefreshShelf.addEventListener("click", () => {
    btnRefreshShelf.textContent = "⏳...";
    fetchStatus().finally(() => {
      setTimeout(() => { btnRefreshShelf.textContent = "🔄 Refresh"; }, 400);
    });
  });
}

// ══════════ REMOTE TILES & CLIPBOARD ══════════
document.querySelectorAll(".ios-tile").forEach(tile => {
  tile.addEventListener("click", () => {
    sendCommand(tile.dataset.cmd);
    showToast(`Executed ${tile.dataset.cmd}`);
  });
});

document.getElementById("btn-push-clip").addEventListener("click", async () => {
  const text = document.getElementById("clip-text").value;
  if (!text) return;
  await fetch("/api/clipboard", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text })
  });
  showToast("Sent to Laptop Clipboard");
});

document.getElementById("btn-pull-clip").addEventListener("click", async () => {
  const res = await fetch("/api/status");
  const data = await res.json();
  if (data.clipboard) {
    document.getElementById("clip-text").value = data.clipboard;
    showToast("Copied from Laptop Clipboard");
  } else {
    showToast("Laptop clipboard is empty");
  }
});

async function sendCommand(command, query = "") {
  try {
    await fetch("/api/command", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ command, query: String(query) })
    });
  } catch (e) {}
}

// ══════════ POLLING LOOP ══════════
let lastSongId = "";
let lastCoverId = "";
let lastReply = "";
let isFetchingStatus = false;

async function pollStatus() {
  if (isFetchingStatus) return;
  isFetchingStatus = true;
  try {
    const res = await fetch("/api/status");
    if (!res.ok) return;
    const data = await res.json();

    const song = data.now_playing;
    if (song && song.title) {
      trackName.innerText = song.title;
      trackArtist.innerText = song.artist || "Unknown Artist";
      isPlaying = song.is_playing || false;
      setPlayState(isPlaying);

      // Smooth position sync: avoid jitter if delta is minor
      const serverPos = song.pos_sec || 0.0;
      currentDur = song.dur_sec || 0.0;
      if (!isPlaying || Math.abs(currentPos - serverPos) > 1.8) {
        currentPos = serverPos;
      } else {
        currentPos = currentPos * 0.25 + serverPos * 0.75;
      }
      updateScrubber();

      // Accurate cover loading matching the exact song and thumbnail state
      const coverId = song.cover_id || `${song.title}_${song.artist}_${song.has_cover}`;
      if (coverId !== lastCoverId) {
        lastCoverId = coverId;
        const newCover = `/api/media/cover?id=${encodeURIComponent(coverId)}&t=${Date.now()}`;
        trackCover.src = newCover;
        const coverRefl = document.getElementById("cover-reflection");
        if (coverRefl) coverRefl.src = newCover;
      }

      const songId = `${song.title}:${song.artist}`;
      if (songId !== lastSongId) {
        lastSongId = songId;
        lyricsList = [];
        currentSongTitle = "";
        if (lyricsContainer) {
          lyricsContainer.innerHTML = '<div class="lyrics-placeholder" id="lyrics-loading">Connecting to music stream...</div>';
        }
      }

      // 1. Direct lyrics from bundled status packet (0ms latency, zero second request)
      if (song.lines && song.lines.length > 0) {
        if (lyricsList.length !== song.lines.length || song.title !== currentSongTitle) {
          currentSongTitle = song.title;
          lyricsList = song.lines;
          renderLyrics(lyricsList);
          evaluateCurrentLyric();
        }
      } else if (lyricsList.length === 0) {
        // Fallback to /api/media/lyrics if not yet bundled
        fetchLyrics();
      }
    } else {
      trackName.innerText = "No Music Playing";
      trackArtist.innerText = "Desktop Idle";
      setPlayState(false);
      lastSongId = "";
      lyricsList = [];
      if (lyricsContainer) {
        lyricsContainer.innerHTML = '<div class="lyrics-placeholder" id="lyrics-loading">Connecting to music stream...</div>';
      }
    }

    if (data.volume !== undefined && !isDraggingVol) {
      setVolumePct(data.volume, false);
    }

    // JARVIS reply stream
    if (data.jarvis) {
      jarvisStatus.innerText = data.jarvis.status || "JARVIS Ready";
      if (data.jarvis.reply && data.jarvis.reply !== lastReply) {
        lastReply = data.jarvis.reply;
        addMessage("jarvis", data.jarvis.reply);
      }
    }

    // Shelf files
    if (data.shelf_files && Array.isArray(data.shelf_files)) {
      renderShelf(data.shelf_files);
    }

    // Bi-Directional Battery Sync
    if (data.pc_battery) {
      updatePCBatteryUI(data.pc_battery);
    }

    // Bedtime Sleep Timer Sync
    if (data.sleep_timer) {
      updateSleepTimerUI(data.sleep_timer);
    }
  } catch (e) {
  } finally {
    isFetchingStatus = false;
  }
}

function getFileIcon(ext) {
  const e = (ext || "").toLowerCase();
  if (["png", "jpg", "jpeg", "webp", "gif", "bmp", "svg"].includes(e)) return "🖼️";
  if (["mp3", "wav", "flac", "m4a", "ogg", "aac", "webm"].includes(e)) return "🎵";
  if (["mp4", "mkv", "mov", "avi"].includes(e)) return "🎬";
  if (["pdf", "doc", "docx", "txt", "md", "rtf", "xls", "xlsx", "ppt", "pptx"].includes(e)) return "📄";
  if (["zip", "rar", "7z", "tar", "gz"].includes(e)) return "📦";
  if (["py", "js", "html", "css", "json", "java", "c", "cpp"].includes(e)) return "💻";
  return "📁";
}

function renderShelf(files) {
  const container = document.getElementById("shelf-items");
  if (!container) return;
  if (!files || files.length === 0) {
    container.innerHTML = '<div style="font-size:13px; color:var(--ios-gray-text); text-align:center; padding:18px;">No files on laptop shelf.</div>';
    return;
  }
  container.innerHTML = "";
  files.forEach(f => {
    const row = document.createElement("div");
    row.className = "shelf-row";
    const icon = getFileIcon(f.ext);
    const sizeStr = f.size ? formatBytes(f.size) : "";
    row.innerHTML = `
      <div style="display:flex; align-items:center; gap:10px; overflow:hidden;">
        <span style="font-size:18px;">${icon}</span>
        <div style="overflow:hidden;">
          <div class="shelf-file-name" title="${f.name}">${f.name}</div>
          <div style="font-size:10.5px; color:var(--ios-gray-text);">${f.ext ? f.ext.toUpperCase() : "FILE"}${sizeStr ? ' • ' + sizeStr : ''}</div>
        </div>
      </div>
      <a class="shelf-dl-btn" href="/api/download/${encodeURIComponent(f.name)}" download title="Download to phone">Save ⬇️</a>
    `;
    container.appendChild(row);
  });
}

// ══════════ WIRELESS TRACKPAD, LIVE PC DISPLAY & REMOTE KEYBOARD ══════════
const btnModeTrackpad = document.getElementById("mode-trackpad");
const btnModeDisplay = document.getElementById("mode-display");
const btnModeKeyboard = document.getElementById("mode-keyboard");
const btnModePresent = document.getElementById("mode-present");
const viewTrackpadContent = document.getElementById("view-trackpad-content");
const viewDisplayContent = document.getElementById("view-display-content");
const viewKeyboardContent = document.getElementById("view-keyboard-content");
const viewPresentContent = document.getElementById("view-present-content");

const liveScreenImg = document.getElementById("live-screen-img");
const screenLoadingOverlay = document.getElementById("screen-loading-overlay");
const screenViewport = document.getElementById("screen-viewport");
const btnViewportExpand = document.getElementById("btn-viewport-expand");
const btnScreenQuality = document.getElementById("btn-screen-quality");
const btnScreenTapMode = document.getElementById("btn-screen-tap-mode");

let isLiveDisplayActive = false;
let isViewportExpanded = false;
let currentScreenZoom = 1.0;
let panOffsetX = 0, panOffsetY = 0;
let liveScreenQuality = "fast";
let screenTapBtn = "left";

function setRemoteMode(mode) {
  const allBtns = [btnModeTrackpad, btnModeDisplay, btnModeKeyboard, btnModePresent];
  const allViews = [viewTrackpadContent, viewDisplayContent, viewKeyboardContent, viewPresentContent];

  allBtns.forEach(b => {
    if (b) {
      b.classList.remove("active");
      b.style.background = "";
      b.style.color = "";
    }
  });
  allViews.forEach(v => {
    if (v) v.style.display = "none";
  });

  if (mode === "trackpad") {
    if (btnModeTrackpad) btnModeTrackpad.classList.add("active");
    if (viewTrackpadContent) viewTrackpadContent.style.display = "block";
    stopLiveStream();
  } else if (mode === "display") {
    if (btnModeDisplay) btnModeDisplay.classList.add("active");
    if (viewDisplayContent) viewDisplayContent.style.display = "block";
    startLiveStream();
  } else if (mode === "keyboard") {
    if (btnModeKeyboard) btnModeKeyboard.classList.add("active");
    if (viewKeyboardContent) viewKeyboardContent.style.display = "block";
    stopLiveStream();
  } else if (mode === "present") {
    if (btnModePresent) btnModePresent.classList.add("active");
    if (viewPresentContent) viewPresentContent.style.display = "block";
    stopLiveStream();
  }
}

if (btnModeTrackpad) btnModeTrackpad.addEventListener("click", () => setRemoteMode("trackpad"));
if (btnModeDisplay) btnModeDisplay.addEventListener("click", () => setRemoteMode("display"));
if (btnModeKeyboard) btnModeKeyboard.addEventListener("click", () => setRemoteMode("keyboard"));
if (btnModePresent) btnModePresent.addEventListener("click", () => setRemoteMode("present"));

if (btnScreenQuality) {
  btnScreenQuality.addEventListener("click", () => {
    if (liveScreenQuality === "fast") {
      liveScreenQuality = "hd";
      btnScreenQuality.textContent = "🎨 Crisp HD";
      btnScreenQuality.style.color = "#ffd60a";
    } else {
      liveScreenQuality = "fast";
      btnScreenQuality.textContent = "⚡ 30 FPS";
      btnScreenQuality.style.color = "#30d158";
    }
    if (isLiveDisplayActive) {
      stopLiveStream();
      setTimeout(startLiveStream, 100);
    }
  });
}

if (btnScreenTapMode) {
  btnScreenTapMode.addEventListener("click", () => {
    if (screenTapBtn === "left") {
      screenTapBtn = "right";
      btnScreenTapMode.textContent = "🖱️ Right";
      btnScreenTapMode.style.color = "#ff453a";
    } else {
      screenTapBtn = "left";
      btnScreenTapMode.textContent = "🖱️ Left";
      btnScreenTapMode.style.color = "#ffffff";
    }
  });
}

const btnQuickScreen = document.getElementById("btn-quick-screen");
if (btnQuickScreen) {
  btnQuickScreen.addEventListener("click", () => {
    const tabRemoteBtn = document.querySelector('.tab-btn[data-tab="tab-remote"]');
    if (tabRemoteBtn) tabRemoteBtn.click();
    setRemoteMode("display");
  });
}

if (btnViewportExpand && screenViewport) {
  btnViewportExpand.addEventListener("click", () => {
    isViewportExpanded = !isViewportExpanded;
    if (isViewportExpanded) {
      screenViewport.style.aspectRatio = "unset";
      screenViewport.style.height = "75vh";
      btnViewportExpand.textContent = "⊟ 16:9 Fit";
      btnViewportExpand.style.color = "var(--ios-red)";
    } else {
      screenViewport.style.aspectRatio = "16 / 9";
      screenViewport.style.height = "auto";
      btnViewportExpand.textContent = "⛶ Expand";
      btnViewportExpand.style.color = "#007aff";
    }
  });
}

function startLiveStream() {
  isLiveDisplayActive = true;
  if (liveScreenImg) {
    if (screenLoadingOverlay) screenLoadingOverlay.style.display = "flex";
    liveScreenImg.onload = () => {
      if (screenLoadingOverlay) screenLoadingOverlay.style.display = "none";
    };
    liveScreenImg.onerror = () => {
      if (screenLoadingOverlay) screenLoadingOverlay.style.display = "flex";
    };
    const qual = liveScreenQuality === "hd" ? 80 : 55;
    liveScreenImg.src = "/api/remote/mjpeg?quality=" + qual + "&t=" + Date.now();
  }
}

function stopLiveStream() {
  isLiveDisplayActive = false;
  if (liveScreenImg) {
    liveScreenImg.src = "";
  }
}

const btnScreenRefresh = document.getElementById("btn-screen-refresh");
if (btnScreenRefresh) {
  btnScreenRefresh.addEventListener("click", () => {
    stopLiveStream();
    setTimeout(startLiveStream, 150);
  });
}

// Zoom Buttons for Live Display View
document.querySelectorAll(".screen-zoom-btn").forEach(btn => {
  btn.addEventListener("click", () => {
    document.querySelectorAll(".screen-zoom-btn").forEach(b => {
      b.style.background = "transparent";
      b.style.color = "#fff";
    });
    btn.style.background = "var(--ios-red)";
    btn.style.color = "#fff";
    currentScreenZoom = parseFloat(btn.dataset.zoom) || 1.0;
    panOffsetX = 0;
    panOffsetY = 0;
    applyScreenTransform();
  });
});

function applyScreenTransform() {
  if (liveScreenImg) {
    liveScreenImg.style.transform = `scale(${currentScreenZoom}) translate(${panOffsetX}px, ${panOffsetY}px)`;
  }
}

// Direct Touch Controls on Live PC Screen (Compensates for letterbox and screen zoom)
if (screenViewport) {
  let isScreenTouching = false;
  let screenTouchStart = 0;
  let screenMoveDist = 0;

  function dispatchScreenEvent(e, isClick = false) {
    if (!liveScreenImg) return;
    const imgRect = liveScreenImg.getBoundingClientRect();
    if (imgRect.width <= 0 || imgRect.height <= 0) return;
    const touch = e.touches ? e.touches[0] : (e.changedTouches ? e.changedTouches[0] : e);
    if (!touch) return;
    const normX = Math.max(0, Math.min(1, (touch.clientX - imgRect.left) / imgRect.width));
    const normY = Math.max(0, Math.min(1, (touch.clientY - imgRect.top) / imgRect.height));

    const targetX = Math.round(normX * 1920);
    const targetY = Math.round(normY * 1080);

    if (isClick) {
      sendMouse({action: "abs_click", x: targetX, y: targetY, btn: screenTapBtn});
      showToast(screenTapBtn === "right" ? "Right Clicked PC Screen" : "Clicked PC Screen");
    } else {
      sendMouse({action: "abs_move", x: targetX, y: targetY});
    }
  }

  screenViewport.addEventListener("touchstart", (e) => {
    if (e.touches.length === 1) {
      isScreenTouching = true;
      screenTouchStart = Date.now();
      screenMoveDist = 0;
    }
  }, {passive: false});

  screenViewport.addEventListener("touchmove", (e) => {
    e.preventDefault();
    if (e.touches.length === 1 && isScreenTouching) {
      screenMoveDist += 1;
      dispatchScreenEvent(e, false);
    }
  }, {passive: false});

  screenViewport.addEventListener("touchend", (e) => {
    if (isScreenTouching) {
      isScreenTouching = false;
      const elapsed = Date.now() - screenTouchStart;
      if (screenMoveDist < 8 && elapsed < 350) {
        dispatchScreenEvent(e, true);
      }
    }
  });
}

function sendMouse(payload) {
  fetch("/api/remote/mouse", {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify(payload)
  }).catch(() => {});
}

function sendKey(key) {
  fetch("/api/remote/key", {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify({key: key})
  }).catch(() => {});
}

function sendType(text, mode = "auto") {
  if (!text) return;
  fetch("/api/remote/type", {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify({text: text, mode: mode})
  }).then(r => r.json()).then(data => {
    if (data && data.success) {
      showToast(mode === "paste" ? "Pasted on PC" : "Typed on PC");
    }
  }).catch(() => {
    showToast("Wi-Fi Error");
  });
}

// ─── Remote PC Keyboard & Typing Listeners ───
document.querySelectorAll(".pc-key-btn").forEach(btn => {
  btn.addEventListener("click", () => {
    const k = btn.dataset.key;
    if (k) {
      sendKey(k);
      showToast(k.toUpperCase());
      btn.style.transform = "scale(0.92)";
      setTimeout(() => { btn.style.transform = "none"; }, 120);
    }
  });
});

// Quick typing on Live Screen
const inputScreenType = document.getElementById("input-screen-type");
const btnScreenSend = document.getElementById("btn-screen-send");
const btnScreenPaste = document.getElementById("btn-screen-paste");
const formScreenType = document.getElementById("form-screen-type");

const doScreenSend = (mode = "auto") => {
  if (!inputScreenType) return;
  const val = inputScreenType.value.trim();
  if (val) {
    sendType(val, mode);
    inputScreenType.value = "";
  } else {
    if (mode === "paste") sendKey("paste");
    else sendKey("enter");
  }
};

if (formScreenType) {
  formScreenType.addEventListener("submit", (e) => {
    e.preventDefault();
    doScreenSend("auto");
  });
}
if (btnScreenSend) btnScreenSend.addEventListener("click", () => doScreenSend("auto"));
if (btnScreenPaste) btnScreenPaste.addEventListener("click", () => doScreenSend("paste"));
if (inputScreenType) {
  inputScreenType.addEventListener("keydown", (e) => {
    if (e.key === "Enter" || e.keyCode === 13) {
      e.preventDefault();
      doScreenSend("auto");
    }
  });
}

// Quick typing on Trackpad
const inputTrackpadType = document.getElementById("input-trackpad-type");
const btnTrackpadSend = document.getElementById("btn-trackpad-send");
const btnTrackpadPaste = document.getElementById("btn-trackpad-paste");
const formTrackpadType = document.getElementById("form-trackpad-type");

const doTrackpadSend = (mode = "auto") => {
  if (!inputTrackpadType) return;
  const val = inputTrackpadType.value.trim();
  if (val) {
    sendType(val, mode);
    inputTrackpadType.value = "";
  } else {
    if (mode === "paste") sendKey("paste");
    else sendKey("enter");
  }
};

if (formTrackpadType) {
  formTrackpadType.addEventListener("submit", (e) => {
    e.preventDefault();
    doTrackpadSend("auto");
  });
}
if (btnTrackpadSend) btnTrackpadSend.addEventListener("click", () => doTrackpadSend("auto"));
if (btnTrackpadPaste) btnTrackpadPaste.addEventListener("click", () => doTrackpadSend("paste"));
if (inputTrackpadType) {
  inputTrackpadType.addEventListener("keydown", (e) => {
    if (e.key === "Enter" || e.keyCode === 13) {
      e.preventDefault();
      doTrackpadSend("auto");
    }
  });
}

// Dedicated Full Keyboard View
const inputFullKeyboard = document.getElementById("input-full-keyboard");
const btnFullKeyboardSend = document.getElementById("btn-full-keyboard-send");
const btnFullKeyboardPaste = document.getElementById("btn-full-keyboard-paste");
const checkLiveType = document.getElementById("check-live-type");
let lastLiveText = "";

if (btnFullKeyboardSend && inputFullKeyboard) {
  btnFullKeyboardSend.addEventListener("click", () => {
    const val = inputFullKeyboard.value;
    if (val) {
      sendType(val, "auto");
      inputFullKeyboard.value = "";
      lastLiveText = "";
    }
  });
}

if (btnFullKeyboardPaste && inputFullKeyboard) {
  btnFullKeyboardPaste.addEventListener("click", () => {
    const val = inputFullKeyboard.value;
    if (val) {
      sendType(val, "paste");
      inputFullKeyboard.value = "";
      lastLiveText = "";
    }
  });
}

if (inputFullKeyboard) {
  inputFullKeyboard.addEventListener("input", () => {
    if (checkLiveType && checkLiveType.checked) {
      const cur = inputFullKeyboard.value;
      if (cur.length > lastLiveText.length && cur.startsWith(lastLiveText)) {
        const added = cur.slice(lastLiveText.length);
        sendType(added, "auto");
      } else if (cur.length < lastLiveText.length) {
        const diff = lastLiveText.length - cur.length;
        for (let i = 0; i < diff; i++) {
          sendKey("backspace");
        }
      }
      lastLiveText = cur;
    }
  });
}

// ─── Clipboard & Text Selection Quick Buttons ───
document.querySelectorAll(".clip-quick-btn").forEach(btn => {
  btn.addEventListener("click", () => {
    const k = btn.dataset.key;
    if (k) {
      sendKey(k);
      showToast(k.toUpperCase());
      btn.style.transform = "scale(0.94)";
      setTimeout(() => { btn.style.transform = "none"; }, 120);
    }
  });
});

let isDragLocked = false;
const btnDragLock = document.getElementById("btn-drag-lock");
if (btnDragLock) {
  btnDragLock.addEventListener("click", () => {
    isDragLocked = !isDragLocked;
    if (isDragLocked) {
      sendMouse({action: "down"});
      btnDragLock.style.background = "#ff9f0a";
      btnDragLock.style.color = "#000";
      showToast("Selection Locked (Swipe to select)");
    } else {
      sendMouse({action: "up"});
      btnDragLock.style.background = "rgba(32,32,38,0.9)";
      btnDragLock.style.color = "#ff9f0a";
      showToast("Selection Released");
    }
  });
}

// ─── Precision Trackpad Surface with Double-Tap Drag & Pinch Zoom ───
const trackpad = document.getElementById("trackpad-surface");
let touchStartX = 0, touchStartY = 0, lastTouchX = 0, lastTouchY = 0;
let lastScrollY = 0;
let touchStartTime = 0;
let totalMoveDist = 0;
let accumDx = 0.0;
let accumDy = 0.0;
let isSendingMouse = false;

// Double-tap & drag state (Lap pad style copy/selection)
let lastTapTime = 0;
let isDoubleTapDragging = false;
let initialTouchCount = 1;
let lastPinchDist = 0;

function flushMouseMove() {
  if (isSendingMouse) return;
  if (Math.abs(accumDx) >= 0.5 || Math.abs(accumDy) >= 0.5) {
    const toSendX = accumDx;
    const toSendY = accumDy;
    accumDx = 0.0;
    accumDy = 0.0;
    isSendingMouse = true;
    fetch("/api/remote/mouse", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({action: "move", dx: toSendX, dy: toSendY})
    }).catch(() => {}).finally(() => {
      isSendingMouse = false;
    });
  }
}
setInterval(flushMouseMove, 20);

function attachTouchpad(padElement, sensitivity = 2.2) {
  if (!padElement) return;

  padElement.addEventListener("touchstart", (e) => {
    padElement.classList.add("active-touch");
    const now = Date.now();
    touchStartTime = now;
    totalMoveDist = 0;
    initialTouchCount = e.touches.length;
    lastPinchDist = 0;

    if (e.touches.length === 1) {
      touchStartX = e.touches[0].clientX;
      touchStartY = e.touches[0].clientY;
      lastTouchX = touchStartX;
      lastTouchY = touchStartY;

      // Double-tap & drag detection (like laptop precision touchpad)
      if (now - lastTapTime < 320) {
        isDoubleTapDragging = true;
        sendMouse({action: "down"});
        showToast("Drag / Select Active");
      }
      lastTapTime = now;
    } else if (e.touches.length === 2) {
      lastScrollY = (e.touches[0].clientY + e.touches[1].clientY) / 2;
      lastPinchDist = Math.hypot(e.touches[0].clientX - e.touches[1].clientX, e.touches[0].clientY - e.touches[1].clientY);
    }
  }, {passive: false});

  padElement.addEventListener("touchmove", (e) => {
    e.preventDefault();
    if (e.touches.length === 1) {
      const curX = e.touches[0].clientX;
      const curY = e.touches[0].clientY;
      const dx = (curX - lastTouchX) * sensitivity;
      const dy = (curY - lastTouchY) * sensitivity;
      lastTouchX = curX;
      lastTouchY = curY;
      totalMoveDist += Math.abs(dx) + Math.abs(dy);
      accumDx += dx;
      accumDy += dy;
    } else if (e.touches.length === 2) {
      // 1. Pinch to Zoom gesture
      const curPinchDist = Math.hypot(e.touches[0].clientX - e.touches[1].clientX, e.touches[0].clientY - e.touches[1].clientY);
      if (lastPinchDist > 0 && Math.abs(curPinchDist - lastPinchDist) > 16) {
        const pinchDelta = curPinchDist - lastPinchDist;
        sendMouse({action: "zoom", dy: pinchDelta > 0 ? 1 : -1});
        lastPinchDist = curPinchDist;
      } else {
        // 2. Parallel vertical scroll
        const curScrollY = (e.touches[0].clientY + e.touches[1].clientY) / 2;
        const dy = curScrollY - lastScrollY;
        lastScrollY = curScrollY;
        if (Math.abs(dy) > 1.5) {
          const scrollTicks = dy > 0 ? 1 : -1;
          sendMouse({action: "scroll", dy: scrollTicks});
        }
      }
    }
  }, {passive: false});

  padElement.addEventListener("touchend", (e) => {
    padElement.classList.remove("active-touch");
    const elapsed = Date.now() - touchStartTime;

    if (isDoubleTapDragging) {
      isDoubleTapDragging = false;
      sendMouse({action: "up"});
      showToast("Selection Dropped");
      return;
    }

    if (initialTouchCount === 2 && totalMoveDist < 16 && elapsed < 320) {
      // Two-Finger Tap -> Right Click Context Menu (Lap pad style)
      sendMouse({action: "click", btn: "right"});
      showToast("Right Click");
    } else if (e.touches.length === 0 && totalMoveDist < 14 && elapsed < 320) {
      // Single Finger Tap -> Left Click
      sendMouse({action: "click", btn: "left"});
      showToast("Tap Click");
    }
  });

  // Pointer event support for desktop / mouse testing
  let isPointerActive = false;
  padElement.addEventListener("pointerdown", (e) => {
    if (e.pointerType === "mouse") {
      isPointerActive = true;
      padElement.classList.add("active-touch");
      touchStartTime = Date.now();
      totalMoveDist = 0;
      touchStartX = e.clientX;
      touchStartY = e.clientY;
      lastTouchX = e.clientX;
      lastTouchY = e.clientY;
      try { padElement.setPointerCapture(e.pointerId); } catch(err){}
    }
  });

  window.addEventListener("pointermove", (e) => {
    if (isPointerActive && e.pointerType === "mouse") {
      const curX = e.clientX;
      const curY = e.clientY;
      const dx = (curX - lastTouchX) * sensitivity;
      const dy = (curY - lastTouchY) * sensitivity;
      lastTouchX = curX;
      lastTouchY = curY;
      totalMoveDist += Math.abs(dx) + Math.abs(dy);
      accumDx += dx;
      accumDy += dy;
    }
  });

  window.addEventListener("pointerup", (e) => {
    if (isPointerActive && e.pointerType === "mouse") {
      isPointerActive = false;
      padElement.classList.remove("active-touch");
      const elapsed = Date.now() - touchStartTime;
      if (totalMoveDist < 14 && elapsed < 320) {
        sendMouse({action: "click", btn: "left"});
        showToast("Tap Click");
      }
      try { padElement.releasePointerCapture(e.pointerId); } catch(err){}
    }
  });
}

attachTouchpad(document.getElementById("trackpad-surface"), 2.2);
attachTouchpad(document.getElementById("screen-mini-trackpad"), 2.2);

function setupScrollBar(upBtnId, downBtnId, gutterId, thumbId) {
  const upBtn = document.getElementById(upBtnId);
  const downBtn = document.getElementById(downBtnId);
  const gutter = document.getElementById(gutterId);
  const thumb = document.getElementById(thumbId);
  if (!gutter || !thumb) return;

  let scrollInterval = null;
  const startContinuousScroll = (direction) => {
    sendMouse({action: "scroll", dy: direction > 0 ? 1 : -1});
    if (scrollInterval) clearInterval(scrollInterval);
    scrollInterval = setInterval(() => {
      sendMouse({action: "scroll", dy: direction > 0 ? 1 : -1});
    }, 90);
  };
  const stopContinuousScroll = () => {
    if (scrollInterval) {
      clearInterval(scrollInterval);
      scrollInterval = null;
    }
  };

  if (upBtn) {
    const pressUp = (e) => {
      e.preventDefault();
      upBtn.style.transform = "scale(0.88)";
      thumb.style.transform = "translateY(-6px)";
      startContinuousScroll(1);
    };
    const releaseUp = (e) => {
      upBtn.style.transform = "none";
      thumb.style.transform = "none";
      stopContinuousScroll();
    };
    upBtn.addEventListener("mousedown", pressUp);
    upBtn.addEventListener("touchstart", pressUp, {passive: false});
    window.addEventListener("mouseup", releaseUp);
    window.addEventListener("touchend", releaseUp);
    window.addEventListener("touchcancel", releaseUp);
  }

  if (downBtn) {
    const pressDown = (e) => {
      e.preventDefault();
      downBtn.style.transform = "scale(0.88)";
      thumb.style.transform = "translateY(6px)";
      startContinuousScroll(-1);
    };
    const releaseDown = (e) => {
      downBtn.style.transform = "none";
      thumb.style.transform = "none";
      stopContinuousScroll();
    };
    downBtn.addEventListener("mousedown", pressDown);
    downBtn.addEventListener("touchstart", pressDown, {passive: false});
    window.addEventListener("mouseup", releaseDown);
    window.addEventListener("touchend", releaseDown);
    window.addEventListener("touchcancel", releaseDown);
  }

  // Draggable Thumb & Gutter interaction
  let isDragging = false;
  let startY = 0;
  let lastY = 0;
  let accumulatedDelta = 0;

  const onPointerDown = (e) => {
    isDragging = true;
    startY = e.clientY || (e.touches && e.touches[0].clientY) || 0;
    lastY = startY;
    accumulatedDelta = 0;
    thumb.classList.add("dragging");
    try { gutter.setPointerCapture(e.pointerId); } catch(err){}
  };

  const onPointerMove = (e) => {
    if (!isDragging) return;
    const clientY = e.clientY || (e.touches && e.touches[0].clientY) || 0;
    const step = clientY - lastY;
    lastY = clientY;
    accumulatedDelta += step;

    // Visual drag deflection
    const maxOffset = 22;
    const visualOffset = Math.max(-maxOffset, Math.min(maxOffset, accumulatedDelta * 0.45));
    thumb.style.transform = `translateY(${visualOffset}px)`;

    // When delta exceeds threshold, send scroll event to Windows
    const SCROLL_THRESHOLD = 8;
    if (Math.abs(accumulatedDelta) >= SCROLL_THRESHOLD) {
      const direction = accumulatedDelta > 0 ? -1 : 1; // Dragging down scrolls content down (negative wheel delta)
      const notches = Math.max(1, Math.round(Math.abs(accumulatedDelta) / SCROLL_THRESHOLD));
      sendMouse({action: "scroll", dy: direction * notches});
      accumulatedDelta = 0;
    }
  };

  const onPointerUp = (e) => {
    if (!isDragging) return;
    isDragging = false;
    thumb.classList.remove("dragging");
    thumb.style.transform = "none";
    accumulatedDelta = 0;
    try { gutter.releasePointerCapture(e.pointerId); } catch(err){}
  };

  gutter.addEventListener("pointerdown", onPointerDown);
  gutter.addEventListener("pointermove", onPointerMove);
  gutter.addEventListener("pointerup", onPointerUp);
  gutter.addEventListener("pointercancel", onPointerUp);
}

setupScrollBar("btn-scroll-up", "btn-scroll-down", "trackpad-scroll-gutter", "trackpad-scroll-thumb");
setupScrollBar("btn-screen-scroll-up", "btn-screen-scroll-down", "screen-scroll-gutter", "screen-scroll-thumb");

const bindClickPad = (btnId, action, btnType) => {
  const el = document.getElementById(btnId);
  if (!el) return;
  el.addEventListener("click", () => {
    sendMouse({action: action, btn: btnType || "left"});
    el.style.transform = "scale(0.92)";
    setTimeout(() => { el.style.transform = "none"; }, 100);
  });
};

bindClickPad("btn-mouse-left", "click", "left");
bindClickPad("btn-mouse-double", "double_click", "left");
bindClickPad("btn-mouse-right", "click", "right");

bindClickPad("btn-screen-left-click", "click", "left");
bindClickPad("btn-screen-double-click", "double_click", "left");
bindClickPad("btn-screen-right-click", "click", "right");

document.querySelectorAll(".pc-key-btn[data-key], .present-btn[data-key]").forEach(btn => {
  btn.addEventListener("click", (e) => {
    e.preventDefault();
    const k = btn.dataset.key;
    if (k) {
      sendKey(k);
      btn.style.transform = "scale(0.92)";
      setTimeout(() => { btn.style.transform = "none"; }, 110);
    }
  });
});

// Adaptive Live Sync: 400ms when playing/music tab active, 1000ms idle
let pollTimer = null;
function scheduleNextPoll() {
  const isMusicActive = isPlaying || (document.getElementById("tab-music") && document.getElementById("tab-music").classList.contains("active"));
  const interval = isMusicActive ? 400 : 1000;
  clearTimeout(pollTimer);
  pollTimer = setTimeout(async () => {
    await pollStatus();
    scheduleNextPoll();
  }, interval);
}

// Initial Fast Start
pollStatus().then(scheduleNextPoll);
fetchLyrics();

// Instant Re-sync on Tab Switch, Phone Unlock, and Window Focus
document.addEventListener("visibilitychange", () => {
  if (document.visibilityState === "visible") {
    pollStatus().then(scheduleNextPoll);
  }
});
window.addEventListener("focus", () => {
  pollStatus().then(scheduleNextPoll);
});

// Ultra-smooth 100ms real-time lyrics & progress sync loop
setInterval(() => {
  if (isPlaying && currentDur > 0) {
    currentPos = Math.min(currentDur, currentPos + 0.1);
    updateScrubber();
    evaluateCurrentLyric();
  }
}, 100);
// ════════════ WIRELESS EARPHONES LIVE PC AUDIO STREAM ════════════
const btnToggleAudioStream = document.getElementById("btn-toggle-audio-stream");
const btnLiveScreenAudio = document.getElementById("btn-live-screen-audio");
const audioStreamStatus = document.getElementById("audio-stream-status");
const audioStatusText = document.getElementById("audio-status-text");
const audioEqBars = document.getElementById("audio-eq-bars");
const sliderEarphonesVol = document.getElementById("slider-earphones-vol");
const earphonesVolLabel = document.getElementById("earphones-vol-label");
const labelLiveAudio = document.getElementById("label-live-audio");

let isLiveAudioActive = false;

function getAudioPlayer() {
  let p = document.getElementById("pc-audio-stream-player");
  if (!p) {
    p = document.createElement("audio");
    p.id = "pc-audio-stream-player";
    p.setAttribute("playsinline", "true");
    p.setAttribute("webkit-playsinline", "true");
    p.preload = "none";
    document.body.appendChild(p);
  }
  return p;
}

function updateAudioStreamUI(active) {
  isLiveAudioActive = active;
  if (active) {
    if (audioStreamStatus) audioStreamStatus.className = "audio-status-pill online";
    if (audioStatusText) audioStatusText.innerText = "LIVE (PLAYING)";
    if (btnToggleAudioStream) {
      btnToggleAudioStream.className = "audio-stream-btn stop";
      btnToggleAudioStream.innerHTML = "<span>⏹</span><span>Stop Listening</span>";
    }
    if (audioEqBars) audioEqBars.classList.add("active");
    if (btnLiveScreenAudio) {
      btnLiveScreenAudio.classList.add("active");
      if (labelLiveAudio) labelLiveAudio.innerText = "Audio: ON";
    }
  } else {
    if (audioStreamStatus) audioStreamStatus.className = "audio-status-pill offline";
    if (audioStatusText) audioStatusText.innerText = "OFFLINE";
    if (btnToggleAudioStream) {
      btnToggleAudioStream.className = "audio-stream-btn start";
      btnToggleAudioStream.innerHTML = "<span>▶</span><span>Listen to PC</span>";
    }
    if (audioEqBars) audioEqBars.classList.remove("active");
    if (btnLiveScreenAudio) {
      btnLiveScreenAudio.classList.remove("active");
      if (labelLiveAudio) labelLiveAudio.innerText = "Audio";
    }
  }
}

function startAudioStream() {
  const p = getAudioPlayer();
  p.crossOrigin = "anonymous";
  p.src = "/api/audio/stream?t=" + Date.now();
  if (sliderEarphonesVol) {
    p.volume = parseInt(sliderEarphonesVol.value, 10) / 100;
  }

  p.onplaying = () => {
    updateAudioStreamUI(true);
    showToast("🎧 Earphones Active: Streaming PC Audio");
  };
  p.onwaiting = () => {
    if (audioStatusText) audioStatusText.innerText = "BUFFERING…";
  };
  p.onerror = () => {
    console.warn("Audio stream playback error:", p.error);
    updateAudioStreamUI(false);
    showToast("Audio stream error - Tap to retry");
  };

  p.load();
  const playPromise = p.play();
  if (playPromise !== undefined) {
    playPromise.then(() => {
      updateAudioStreamUI(true);
    }).catch((err) => {
      console.warn("Audio autoplay blocked:", err);
      updateAudioStreamUI(false);
      showToast("Tap again to allow phone audio playback");
    });
  }
}

function stopAudioStream() {
  const p = getAudioPlayer();
  p.pause();
  p.removeAttribute("src");
  p.load();
  updateAudioStreamUI(false);
  showToast("Audio Stream Stopped");
}

function toggleAudioStream() {
  if (isLiveAudioActive) {
    stopAudioStream();
  } else {
    startAudioStream();
  }
}

if (btnToggleAudioStream) {
  btnToggleAudioStream.addEventListener("click", toggleAudioStream);
}

if (btnLiveScreenAudio) {
  btnLiveScreenAudio.addEventListener("click", toggleAudioStream);
}

if (sliderEarphonesVol) {
  sliderEarphonesVol.addEventListener("input", (e) => {
    const val = parseInt(e.target.value, 10);
    const p = getAudioPlayer();
    if (p) p.volume = val / 100;
    if (earphonesVolLabel) earphonesVolLabel.innerText = val + "%";
  });
}


// ══════════ 2. WIRELESS PHONE MIC & DICTATION (Feature 3) ══════════
const btnStartDictate = document.getElementById("btn-start-dictate");
const labelDictate = document.getElementById("label-dictate");
const dictateTranscript = document.getElementById("dictate-transcript");
let isDictating = false;
let speechRecognizer = null;

if (window.webkitSpeechRecognition || window.SpeechRecognition) {
  const SpeechRec = window.SpeechRecognition || window.webkitSpeechRecognition;
  speechRecognizer = new SpeechRec();
  speechRecognizer.continuous = true;
  speechRecognizer.interimResults = true;
  speechRecognizer.lang = navigator.language || "en-US";

  speechRecognizer.onstart = () => {
    isDictating = true;
    if (btnStartDictate) btnStartDictate.classList.add("recording");
    if (labelDictate) labelDictate.textContent = "Listening... Speak naturally";
    if (dictateTranscript) {
      dictateTranscript.style.display = "block";
      dictateTranscript.textContent = "Listening...";
    }
  };

  speechRecognizer.onresult = (event) => {
    let interim = "";
    let finalStr = "";
    for (let i = event.resultIndex; i < event.results.length; ++i) {
      if (event.results[i].isFinal) {
        finalStr += event.results[i][0].transcript;
      } else {
        interim += event.results[i][0].transcript;
      }
    }
    const current = finalStr || interim;
    if (dictateTranscript) dictateTranscript.textContent = current;
    if (finalStr.trim()) {
      fetch("/api/mic/dictate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text: finalStr.trim(), mode: "paste" })
      }).then(() => showToast("Dictated to active PC window")).catch(() => {});
    }
  };

  speechRecognizer.onerror = () => {
    isDictating = false;
    if (btnStartDictate) btnStartDictate.classList.remove("recording");
    if (labelDictate) labelDictate.textContent = "Tap to Dictate (Live into PC)";
    if (dictateTranscript) dictateTranscript.style.display = "none";
  };

  speechRecognizer.onend = () => {
    isDictating = false;
    if (btnStartDictate) btnStartDictate.classList.remove("recording");
    if (labelDictate) labelDictate.textContent = "Tap to Dictate (Live into PC)";
  };
}

// Global native dictation bridge from Android app
window.onNativeDictationResult = function(text) {
  if (dictateTranscript) {
    dictateTranscript.textContent = `“${text}”`;
    dictateTranscript.style.color = "#30d158";
  }
  showToast(`Dictated: ${text.slice(0, 32)}...`);
  if (btnStartDictate) btnStartDictate.classList.remove("recording");
  if (labelDictate) labelDictate.textContent = "Tap to Dictate (Live into PC)";
};

if (btnStartDictate) {
  btnStartDictate.addEventListener("click", () => {
    if (window.AndroidBridge && typeof window.AndroidBridge.startNativeDictation === "function") {
      btnStartDictate.classList.add("recording");
      if (labelDictate) labelDictate.textContent = "🎙️ Listening... speak now";
      if (dictateTranscript) dictateTranscript.textContent = "Listening to speech...";
      window.AndroidBridge.startNativeDictation();
      return;
    }

    if (speechRecognizer) {
      if (!isDictating) {
        try { speechRecognizer.start(); } catch (e) {}
      } else {
        speechRecognizer.stop();
      }
    } else {
      const text = prompt("Type or dictate text to send live to active PC window:");
      if (text) {
        fetch("/api/mic/dictate", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ text, mode: "paste" })
        }).then(() => showToast("Typed into active PC window"));
      }
    }
  });
}

// Voice Memo Recording & Upload
const btnRecordVoiceMemo = document.getElementById("btn-record-voice-memo");
const labelVoiceMemo = document.getElementById("label-voice-memo");
let mediaRecorder = null;
let recordedAudioChunks = [];
let isRecordingMemo = false;

if (btnRecordVoiceMemo && navigator.mediaDevices && navigator.mediaDevices.getUserMedia) {
  btnRecordVoiceMemo.addEventListener("click", async () => {
    if (!isRecordingMemo) {
      try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        mediaRecorder = new MediaRecorder(stream);
        recordedAudioChunks = [];
        mediaRecorder.ondataavailable = (e) => {
          if (e.data.size > 0) recordedAudioChunks.push(e.data);
        };
        mediaRecorder.onstop = async () => {
          stream.getTracks().forEach(t => t.stop());
          const blob = new Blob(recordedAudioChunks, { type: "audio/webm" });
          const fname = `VoiceNote_${Date.now()}.webm`;
          showToast("Sending Voice Memo to PC...");
          try {
            await fetch(`/api/mic/upload?filename=${encodeURIComponent(fname)}`, {
              method: "POST",
              headers: { "Content-Type": "audio/webm" },
              body: blob
            });
            showToast("🎙️ Voice Memo saved to PC Shelf!");
          } catch (e) {
            showToast("Failed to upload voice memo");
          }
        };
        mediaRecorder.start();
        isRecordingMemo = true;
        btnRecordVoiceMemo.classList.add("recording");
        if (labelVoiceMemo) labelVoiceMemo.textContent = "⏹ Stop & Send Memo";
      } catch (e) {
        alert("Microphone access denied or unavailable.");
      }
    } else {
      if (mediaRecorder && mediaRecorder.state !== "inactive") {
        mediaRecorder.stop();
      }
      isRecordingMemo = false;
      btnRecordVoiceMemo.classList.remove("recording");
      if (labelVoiceMemo) labelVoiceMemo.textContent = "Record Voice Memo to Shelf";
    }
  });
}

// ══════════ 3. BI-DIRECTIONAL BATTERY SYNC (Feature 4) ══════════
function updatePCBatteryUI(bat) {
  const pctEl = document.getElementById("pct-pc-bat");
  const barEl = document.getElementById("bar-pc-bat");
  const stateEl = document.getElementById("state-pc-bat");
  const boltEl = document.getElementById("bolt-pc-bat");
  const headerPc = document.getElementById("header-pc-bat");
  const headerPill = document.getElementById("header-battery-pill");

  if (pctEl && bat) {
    pctEl.textContent = `${bat.percent}%`;
    if (barEl) {
      barEl.style.width = `${bat.percent}%`;
      barEl.style.background = bat.percent < 20 ? "#ff453a" : (bat.percent < 50 ? "#ffd60a" : "#30d158");
    }
    if (boltEl) boltEl.style.display = bat.charging ? "inline" : "none";
    if (stateEl) {
      stateEl.textContent = bat.charging ? "⚡ Charging" : (bat.power_plugged ? "Power Connected" : "On Battery");
    }
    if (headerPc) headerPc.textContent = `💻 ${bat.percent}%${bat.charging ? "⚡" : ""}`;
    if (headerPill) headerPill.style.display = "inline-flex";
  }
}

function updatePhoneBatteryDisplay(level, charging) {
  const pct = Math.max(0, Math.min(100, Math.round(level <= 1.0 ? level * 100 : level)));
  const pctEl = document.getElementById("pct-phone-bat");
  const barEl = document.getElementById("bar-phone-bat");
  const stateEl = document.getElementById("state-phone-bat");
  const boltEl = document.getElementById("bolt-phone-bat");
  const headerPhone = document.getElementById("header-phone-bat");
  const headerPill = document.getElementById("header-battery-pill");

  if (pctEl) pctEl.textContent = `${pct}%`;
  if (barEl) {
    barEl.style.width = `${pct}%`;
    barEl.style.background = pct < 20 ? "#ff453a" : (pct < 50 ? "#ffd60a" : "#30d158");
  }
  if (boltEl) boltEl.style.display = charging ? "inline" : "none";
  if (stateEl) stateEl.textContent = charging ? "⚡ Charging" : "On Battery";
  if (headerPhone) headerPhone.textContent = `📱 ${pct}%${charging ? "⚡" : ""}`;
  if (headerPill) headerPill.style.display = "inline-flex";

  fetch("/api/phone/battery", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ level: pct / 100.0, charging })
  }).catch(() => {});
}

function checkNativeBridgeBattery() {
  if (window.AndroidBridge && typeof window.AndroidBridge.getBatteryLevel === "function") {
    try {
      const level = window.AndroidBridge.getBatteryLevel();
      const charging = typeof window.AndroidBridge.isCharging === "function" ? window.AndroidBridge.isCharging() : false;
      if (level >= 0) {
        updatePhoneBatteryDisplay(level, charging);
        return true;
      }
    } catch (e) {}
  }
  return false;
}

function checkNativeAppEnv() {
  if (window.AndroidBridge && typeof window.AndroidBridge.isNativeApp === "function") {
    const apkLink = document.getElementById("header-apk-link");
    if (apkLink) apkLink.style.display = "none";
    document.body.classList.add("is-native-android-app");
  }
}

async function initPhoneBatterySync() {
  checkNativeAppEnv();
  const fromNative = checkNativeBridgeBattery();
  if (fromNative) {
    setInterval(checkNativeBridgeBattery, 20000);
  }

  if ('getBattery' in navigator) {
    try {
      const bat = await navigator.getBattery();
      function reportBattery() {
        updatePhoneBatteryDisplay(bat.level, bat.charging);
      }
      reportBattery();
      bat.addEventListener("levelchange", reportBattery);
      bat.addEventListener("chargingchange", reportBattery);
      setInterval(reportBattery, 30000);
    } catch (e) {}
  }
}
initPhoneBatterySync();
setTimeout(checkNativeAppEnv, 500);

// ══════════ 4. BEDTIME SLEEP TIMER (Feature 5) ══════════
let selectedSleepMinutes = 15;
document.querySelectorAll(".sleep-preset-btn").forEach(btn => {
  btn.addEventListener("click", () => {
    document.querySelectorAll(".sleep-preset-btn").forEach(b => b.classList.remove("active"));
    btn.classList.add("active");
    selectedSleepMinutes = parseInt(btn.dataset.min, 10) || 15;
  });
});

const btnStartSleepTimer = document.getElementById("btn-start-sleep-timer");
const btnCancelSleepTimer = document.getElementById("btn-cancel-sleep-timer");
const selectSleepAction = document.getElementById("select-sleep-action");
const sleepCountdownBanner = document.getElementById("sleep-countdown-banner");
const sleepCountdownTime = document.getElementById("sleep-countdown-time");

if (btnStartSleepTimer) {
  btnStartSleepTimer.addEventListener("click", async () => {
    const act = selectSleepAction ? selectSleepAction.value : "fade_and_sleep";
    try {
      const res = await fetch("/api/timer/start", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ duration_minutes: selectedSleepMinutes, action: act })
      });
      const data = await res.json();
      updateSleepTimerUI(data);
      showToast(`Sleep timer started for ${selectedSleepMinutes} min`);
    } catch (e) {}
  });
}

if (btnCancelSleepTimer) {
  btnCancelSleepTimer.addEventListener("click", async () => {
    try {
      const res = await fetch("/api/timer/cancel", { method: "POST" });
      const data = await res.json();
      updateSleepTimerUI(data);
      showToast("Sleep timer cancelled");
    } catch (e) {}
  });
}

function updateSleepTimerUI(timer) {
  if (!sleepCountdownBanner || !sleepCountdownTime) return;
  if (timer && timer.active && timer.remaining_seconds > 0) {
    const m = Math.floor(timer.remaining_seconds / 60);
    const s = timer.remaining_seconds % 60;
    sleepCountdownTime.textContent = `${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`;
    sleepCountdownBanner.style.display = "flex";
    if (btnStartSleepTimer) btnStartSleepTimer.style.display = "none";
  } else {
    sleepCountdownBanner.style.display = "none";
    if (btnStartSleepTimer) btnStartSleepTimer.style.display = "block";
  }
}
</script>
</body>
</html>
"""


# ─── Live PC Audio Stream Broadcaster ─────────────────────────────────────────

class AudioStreamBroadcaster:
    """Live PC Audio Loopback to MP3 Stream Broadcaster for Wireless Earphones Mode."""

    def __init__(self):
        self._listeners: List[queue.Queue] = []
        self._lock = threading.Lock()
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._header_chunk: bytes = b""
        self._recent_chunks: collections.deque = collections.deque(maxlen=24)
        self._device_name: str = "Default Speaker"
        self._available = False
        try:
            import soundcard as sc
            import numpy as np
            import shutil
            import subprocess
            self._has_ffmpeg = bool(shutil.which("ffmpeg"))
            self._available = self._has_ffmpeg
            if not self._available:
                try:
                    import av
                    self._available = True
                except Exception:
                    self._available = False
        except ImportError:
            self._available = False

    @property
    def is_available(self) -> bool:
        return self._available

    @property
    def is_active(self) -> bool:
        return self._running

    @property
    def listener_count(self) -> int:
        with self._lock:
            return len(self._listeners)

    @property
    def device_name(self) -> str:
        return self._device_name

    def add_listener(self) -> queue.Queue:
        q: queue.Queue = queue.Queue(maxsize=120)
        with self._lock:
            self._listeners.append(q)
            if not self._running and self._available:
                self._running = True
                self._thread = threading.Thread(target=self._capture_loop, daemon=True, name="AudioStreamCapture")
                self._thread.start()
        return q

    def remove_listener(self, q: queue.Queue):
        with self._lock:
            if q in self._listeners:
                self._listeners.remove(q)
            if not self._listeners:
                self._running = False

    def stop(self):
        with self._lock:
            self._running = False
            self._listeners.clear()

    def _capture_loop(self):
        proc = None
        try:
            import soundcard as sc
            import numpy as np
            import subprocess

            spk = sc.default_speaker()
            if not spk:
                return
            self._device_name = str(spk.name)
            mic = sc.get_microphone(id=str(spk.name), include_loopback=True)
            if not mic:
                return

            # Native 48kHz stereo, high-quality 192k MP3 for crystal-clear earphones audio
            ffmpeg_cmd = [
                "ffmpeg", "-y", "-loglevel", "quiet",
                "-f", "s16le", "-ar", "48000", "-ac", "2", "-i", "pipe:0",
                "-c:a", "libmp3lame", "-b:a", "192k", "-flush_packets", "1",
                "-f", "mp3", "pipe:1"
            ]
            creation_flags = 0
            startupinfo = None
            if sys.platform == "win32":
                creation_flags = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= getattr(subprocess, "STARTF_USESHOWWINDOW", 0x00000001)
                startupinfo.wShowWindow = 0  # SW_HIDE
            proc = subprocess.Popen(
                ffmpeg_cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                bufsize=0,
                creationflags=creation_flags,
                startupinfo=startupinfo
            )

            def reader_thread():
                while self._running and proc.poll() is None:
                    try:
                        chunk = proc.stdout.read(4096)
                        if not chunk:
                            break
                        with self._lock:
                            for q in list(self._listeners):
                                try:
                                    q.put_nowait(chunk)
                                except queue.Full:
                                    try:
                                        q.get_nowait()
                                        q.put_nowait(chunk)
                                    except Exception:
                                        pass
                    except Exception:
                        break

            t_reader = threading.Thread(target=reader_thread, daemon=True, name="AudioMp3Reader")
            t_reader.start()

            # Record in native 48kHz WASAPI loopback with 2048 sample blocks (~42.6ms) for crack-free streaming
            with mic.recorder(samplerate=48000, channels=2, blocksize=2048) as rec:
                while self._running and proc.poll() is None:
                    data = rec.record(numframes=2048)
                    pcm = (np.clip(data, -1.0, 1.0) * 32767.0).astype(np.int16).tobytes()
                    try:
                        proc.stdin.write(pcm)
                    except (BrokenPipeError, OSError):
                        break

        except Exception as e:
            print(f"[AudioBroadcaster] Error in loopback audio streaming: {e}")
        finally:
            if proc:
                try:
                    if proc.stdin:
                        proc.stdin.close()
                    proc.terminate()
                except Exception:
                    pass
            with self._lock:
                self._running = False


# ─── Bedtime Sleep Timer Automation ───────────────────────────────────────────

class SleepTimerManager:
    _instance: Optional['SleepTimerManager'] = None

    @classmethod
    def get_instance(cls) -> 'SleepTimerManager':
        if cls._instance is None:
            cls._instance = SleepTimerManager()
        return cls._instance

    def __init__(self):
        self.active: bool = False
        self.action: str = "fade_and_sleep"
        self.total_seconds: int = 0
        self.end_time: float = 0.0
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.RLock()

    def start(self, duration_minutes: int, action: str = "fade_and_sleep") -> Dict[str, Any]:
        with self._lock:
            self.total_seconds = max(10, int(duration_minutes * 60))
            self.action = action
            self.end_time = time.time() + self.total_seconds
            self.active = True
            if self._thread is None or not self._thread.is_alive():
                self._thread = threading.Thread(target=self._run_loop, daemon=True)
                self._thread.start()
            return self.get_status()

    def cancel(self) -> Dict[str, Any]:
        with self._lock:
            self.active = False
            self.total_seconds = 0
            self.end_time = 0.0
            return self.get_status()

    def get_status(self) -> Dict[str, Any]:
        with self._lock:
            if not self.active:
                return {"active": False, "remaining_seconds": 0, "action": self.action, "total_seconds": 0}
            remaining = int(max(0, self.end_time - time.time()))
            if remaining <= 0:
                self.active = False
            return {
                "active": self.active,
                "remaining_seconds": remaining,
                "action": self.action,
                "total_seconds": self.total_seconds,
            }

    def _run_loop(self):
        user32 = ctypes.windll.user32
        action = self.action
        remaining = 0
        while True:
            time.sleep(1.0)
            with self._lock:
                if not self.active:
                    break
                remaining = self.end_time - time.time()
                action = self.action
                if remaining <= 0:
                    self.active = False
                    break
                # If fade_and_sleep and in last 45 seconds, step down volume gradually
                if self.action == "fade_and_sleep" and remaining <= 45:
                    try:
                        if int(remaining) % 2 == 0:
                            user32.keybd_event(0xAE, 0, 0, 0)
                            user32.keybd_event(0xAE, 0, 2, 0)
                    except Exception:
                        pass

        if remaining <= 0 and not self.active:
            self._execute_action(action)

    def _execute_action(self, action: str):
        user32 = ctypes.windll.user32
        try:
            # Pause any currently playing media
            user32.keybd_event(0xB3, 0, 0, 0)
            time.sleep(0.05)
            user32.keybd_event(0xB3, 0, 2, 0)
        except Exception:
            pass

        time.sleep(0.5)

        if action in ("fade_and_sleep", "sleep"):
            try:
                ctypes.windll.PowrProf.SetSuspendState(0, 1, 0)
            except Exception as e:
                print(f"[SleepTimer] Error putting PC to sleep: {e}")
        elif action == "lock":
            try:
                user32.LockWorkStation()
            except Exception as e:
                print(f"[SleepTimer] Error locking PC: {e}")
        elif action == "shutdown":
            try:
                os.system("shutdown /s /t 10")
            except Exception as e:
                print(f"[SleepTimer] Error shutting down: {e}")


# ─── HTTP Request Handler ─────────────────────────────────────────────────────

class PhoneDropHandler(BaseHTTPRequestHandler):
    server: 'PhoneDropServer'

    def log_message(self, format, *args):
        pass

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Range, Authorization")
        self.send_header("Access-Control-Max-Age", "86400")
        self.end_headers()

    def _send_json(self, data: dict, status: int = 200):
        body = json.dumps(data).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        client_ip = self.client_address[0]
        user_agent = self.headers.get("User-Agent", "Unknown Device")
        self.server.service.register_client(client_ip, user_agent)

        if path in ("/", "/index.html", "/remote", "/remote/"):
            body = MOBILE_HTML.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        elif path in ("/app", "/download/app", "/jarvis-remote.apk", "/JarvisRemote.apk"):
            target_apk = APK_FILE if APK_FILE.exists() else (BASE_DIR / "dist" / "JarvisRemote.apk")
            if target_apk.exists():
                sz = target_apk.stat().st_size
                self.send_response(200)
                self.send_header("Content-Type", "application/vnd.android.package-archive")
                self.send_header("Content-Disposition", 'attachment; filename="JarvisRemote.apk"')
                self.send_header("Content-Length", str(sz))
                self.send_header("Cache-Control", "no-cache")
                self.end_headers()
                with open(target_apk, "rb") as f:
                    shutil.copyfileobj(f, self.wfile)
                return
            else:
                self.send_error(404, "APK Not Found")
                return

        elif path == "/qr":
            buf = io.BytesIO()
            qr_img = self.server.service.get_qr_image()
            qr_img.save(buf, format="PNG")
            img_bytes = buf.getvalue()
            self.send_response(200)
            self.send_header("Content-Type", "image/png")
            self.send_header("Content-Length", str(len(img_bytes)))
            self.end_headers()
            self.wfile.write(img_bytes)
            return

        elif path == "/api/status":
            status_data = self.server.service.get_status_data()
            self._send_json(status_data)
            return

        elif path == "/api/media/cover":
            cover_info = self.server.service.get_cover_bytes()
            if cover_info:
                img_bytes, mime = cover_info
                self.send_response(200)
                self.send_header("Content-Type", mime)
                self.send_header("Content-Length", str(len(img_bytes)))
                self.send_header("Cache-Control", "no-cache")
                self.end_headers()
                self.wfile.write(img_bytes)
                return
            else:
                svg = self.server.service.get_placeholder_cover_svg()
                self.send_response(200)
                self.send_header("Content-Type", "image/svg+xml")
                self.send_header("Content-Length", str(len(svg)))
                self.end_headers()
                self.wfile.write(svg)
                return

        elif path == "/api/media/lyrics":
            lyrics_data = self.server.service.get_lyrics_data()
            self._send_json(lyrics_data)
            return

        elif path == "/api/remote/mjpeg":
            self.send_response(200)
            self.send_header("Content-Type", "multipart/x-mixed-replace; boundary=frame")
            self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            try:
                while self.server.service.is_running:
                    frame, orig_w, orig_h = self.server.service.get_screen_bytes(max_width=1920, quality=72)
                    self.wfile.write(b"--frame\r\n")
                    self.wfile.write(b"Content-Type: image/jpeg\r\n")
                    self.wfile.write(f"Content-Length: {len(frame)}\r\n\r\n".encode("utf-8"))
                    self.wfile.write(frame)
                    self.wfile.write(b"\r\n")
                    time.sleep(0.06)
            except (ConnectionResetError, BrokenPipeError, socket.error):
                return

        elif path == "/api/remote/screen":
            frame, orig_w, orig_h = self.server.service.get_screen_bytes(max_width=1920, quality=72)
            self.send_response(200)
            self.send_header("Content-Type", "image/jpeg")
            self.send_header("Content-Length", str(len(frame)))
            self.send_header("X-Screen-Width", str(orig_w))
            self.send_header("X-Screen-Height", str(orig_h))
            self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(frame)
            return

        elif path == "/api/audio/stream":
            broadcaster = getattr(self.server.service, "audio_broadcaster", None)
            if not broadcaster or not broadcaster.is_available:
                self.send_error(503, "Audio streamer unavailable")
                return

            self.send_response(200)
            self.send_header("Content-Type", "audio/mpeg")
            self.send_header("Accept-Ranges", "none")
            self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
            self.send_header("Pragma", "no-cache")
            self.send_header("Expires", "0")
            self.send_header("Connection", "keep-alive")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()

            q = broadcaster.add_listener()
            try:
                while self.server.service.is_running:
                    try:
                        chunk = q.get(timeout=2.0)
                        if chunk:
                            self.wfile.write(chunk)
                            self.wfile.flush()
                    except queue.Empty:
                        continue
            except (ConnectionResetError, BrokenPipeError, ConnectionAbortedError, socket.error):
                return
            finally:
                broadcaster.remove_listener(q)
            return

        elif path == "/api/audio/status":
            broadcaster = getattr(self.server.service, "audio_broadcaster", None)
            data = {
                "available": broadcaster is not None and broadcaster.is_available,
                "active": broadcaster.is_active if broadcaster else False,
                "listeners": broadcaster.listener_count if broadcaster else 0,
                "device": broadcaster.device_name if broadcaster else "None",
            }
            self._send_json(data)
            return

        elif path.startswith("/api/download/"):
            filename = urllib.parse.unquote(path[len("/api/download/"):])
            fpath = self.server.service.find_shared_file(filename)
            if fpath and os.path.exists(fpath):
                sz = os.path.getsize(fpath)
                self.send_response(200)
                self.send_header("Content-Type", "application/octet-stream")
                self.send_header("Content-Disposition", f'attachment; filename="{filename}"')
                self.send_header("Content-Length", str(sz))
                self.end_headers()
                with open(fpath, "rb") as f:
                    while True:
                        chunk = f.read(65536)
                        if not chunk:
                            break
                        self.wfile.write(chunk)
                return
            else:
                self.send_error(404, "File Not Found")
                return

        self.send_error(404, "Not Found")

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        client_ip = self.client_address[0]
        user_agent = self.headers.get("User-Agent", "Unknown Device")
        self.server.service.register_client(client_ip, user_agent)

        content_length = int(self.headers.get("Content-Length", 0))

        if path == "/api/upload":
            params = urllib.parse.parse_qs(parsed.query)
            raw_name = params.get("filename", ["phone_upload.dat"])[0]
            filename = urllib.parse.unquote(raw_name)
            safe_name = Path(filename).name or f"upload_{int(time.time())}.dat"

            target_path = DOWNLOADS_DIR / safe_name
            base_stem = target_path.stem
            ext = target_path.suffix
            counter = 1
            while target_path.exists():
                target_path = DOWNLOADS_DIR / f"{base_stem}_{counter}{ext}"
                counter += 1

            with open(target_path, "wb") as out_f:
                remaining = content_length
                while remaining > 0:
                    read_size = min(remaining, 65536)
                    chunk = self.rfile.read(read_size)
                    if not chunk:
                        break
                    out_f.write(chunk)
                    remaining -= len(chunk)

            self.server.service.on_file_received(str(target_path), target_path.name)
            self._send_json({"success": True, "path": str(target_path), "name": target_path.name})
            return

        elif path == "/api/jarvis":
            body = self.rfile.read(content_length).decode("utf-8")
            data = json.loads(body)
            query = data.get("query", "").strip()
            if query:
                self.server.service.on_jarvis_query(query)
            self._send_json({"success": True, "query": query})
            return

        elif path == "/api/clipboard":
            body = self.rfile.read(content_length).decode("utf-8")
            data = json.loads(body)
            text = data.get("text", "")
            self.server.service.on_clipboard_received(text)
            self._send_json({"success": True})
            return

        elif path == "/api/command":
            body = self.rfile.read(content_length).decode("utf-8")
            data = json.loads(body)
            cmd = data.get("command", "")
            query = data.get("query", "")
            self.server.service.on_command_received(cmd, query)
            self._send_json({"success": True})
            return

        elif path == "/api/remote/mouse":
            body = self.rfile.read(content_length).decode("utf-8")
            data = json.loads(body)
            action = data.get("action", "move")
            dx = float(data.get("dx", 0.0))
            dy = float(data.get("dy", 0.0))
            x = float(data.get("x", 0.0))
            y = float(data.get("y", 0.0))
            btn = data.get("btn", "left")
            self.server.service.handle_remote_mouse(action, dx, dy, btn, x, y)
            self._send_json({"success": True})
            return

        elif path == "/api/remote/key":
            body = self.rfile.read(content_length).decode("utf-8")
            data = json.loads(body)
            key = data.get("key", "")
            self.server.service.handle_remote_key(key)
            self._send_json({"success": True})
            return

        elif path == "/api/remote/type":
            body = self.rfile.read(content_length).decode("utf-8")
            data = json.loads(body)
            text = data.get("text", "")
            mode = data.get("mode", "auto")
            if text:
                self.server.service.handle_remote_type(text, mode)
            self._send_json({"success": True})
            return


        elif path == "/api/phone/battery":
            body = self.rfile.read(content_length).decode("utf-8")
            data = json.loads(body)
            self.server.service.on_phone_battery_received(data)
            self._send_json({"success": True})
            return

        elif path == "/api/timer/start":
            body = self.rfile.read(content_length).decode("utf-8")
            data = json.loads(body)
            dur = int(data.get("duration_minutes", 30))
            act = data.get("action", "fade_and_sleep")
            status = SleepTimerManager.get_instance().start(dur, act)
            self._send_json(status)
            return

        elif path == "/api/timer/cancel":
            status = SleepTimerManager.get_instance().cancel()
            self._send_json(status)
            return

        elif path == "/api/mic/dictate":
            body = self.rfile.read(content_length).decode("utf-8")
            data = json.loads(body)
            text = data.get("text", "").strip()
            mode = data.get("mode", "paste")
            if text:
                self.server.service.handle_remote_type(text, mode)
            self._send_json({"success": True, "text": text})
            return

        elif path == "/api/mic/upload":
            params = urllib.parse.parse_qs(parsed.query)
            raw_name = params.get("filename", [f"VoiceNote_{int(time.time())}.webm"])[0]
            filename = urllib.parse.unquote(raw_name)
            safe_name = Path(filename).name or f"VoiceNote_{int(time.time())}.webm"

            vn_dir = DOWNLOADS_DIR / "VoiceNotes"
            vn_dir.mkdir(parents=True, exist_ok=True)
            target_path = vn_dir / safe_name
            with open(target_path, "wb") as out_f:
                remaining = content_length
                while remaining > 0:
                    read_size = min(remaining, 65536)
                    chunk = self.rfile.read(read_size)
                    if not chunk:
                        break
                    out_f.write(chunk)
                    remaining -= len(chunk)

            self.server.service.on_voice_note_received(str(target_path), target_path.name)
            self._send_json({"success": True, "path": str(target_path), "name": target_path.name})
            return

        self.send_error(404, "Not Found")


class PhoneDropServer(ThreadingHTTPServer):
    def __init__(self, server_address, RequestHandlerClass, service: 'PhoneDropService'):
        super().__init__(server_address, RequestHandlerClass)
        self.service = service


def set_win32_clipboard(text: str) -> bool:
    """Thread-safe Win32 clipboard setter using native Windows GlobalAlloc and OpenClipboard."""
    try:
        user32 = ctypes.windll.user32
        kernel32 = ctypes.windll.kernel32
        CF_UNICODETEXT = 13
        GMEM_MOVEABLE = 0x0002

        kernel32.GlobalAlloc.argtypes = [ctypes.c_uint, ctypes.c_size_t]
        kernel32.GlobalAlloc.restype = ctypes.c_void_p
        kernel32.GlobalLock.argtypes = [ctypes.c_void_p]
        kernel32.GlobalLock.restype = ctypes.c_void_p
        kernel32.GlobalUnlock.argtypes = [ctypes.c_void_p]
        kernel32.GlobalUnlock.restype = ctypes.c_int
        user32.SetClipboardData.argtypes = [ctypes.c_uint, ctypes.c_void_p]
        user32.SetClipboardData.restype = ctypes.c_void_p

        # Retry up to 5 times if another application has clipboard open
        for _ in range(5):
            if user32.OpenClipboard(None):
                break
            time.sleep(0.01)
        else:
            return False

        try:
            user32.EmptyClipboard()
            data = (text + '\0').encode('utf-16-le')
            h_mem = kernel32.GlobalAlloc(GMEM_MOVEABLE, len(data))
            if not h_mem:
                return False
            ptr = kernel32.GlobalLock(h_mem)
            if not ptr:
                return False
            ctypes.memmove(ptr, data, len(data))
            kernel32.GlobalUnlock(h_mem)
            user32.SetClipboardData(CF_UNICODETEXT, h_mem)
            return True
        finally:
            user32.CloseClipboard()
    except Exception as e:
        print(f"[PhoneDropService] Error setting clipboard: {e}")
        return False


# ─── Phone Drop Service Core ──────────────────────────────────────────────────

class PhoneDropService:
    _instance: Optional['PhoneDropService'] = None

    @classmethod
    def get_instance(cls) -> 'PhoneDropService':
        if cls._instance is None:
            cls._instance = PhoneDropService()
        return cls._instance

    def __init__(self, port: int = 8765):
        self.port = port
        self.hostname = get_hostname()
        self.local_ip = get_local_ip()
        self.server: Optional[PhoneDropServer] = None
        self.server_thread: Optional[threading.Thread] = None
        self.is_running = False

        self.connected_clients: Dict[str, Dict[str, Any]] = {}

        self.cb_file_received: Optional[Callable[[str, str], None]] = None
        self.cb_clipboard_received: Optional[Callable[[str], None]] = None
        self.cb_url_received: Optional[Callable[[str], None]] = None
        self.cb_command_received: Optional[Callable[[str, str], None]] = None
        self.cb_get_status: Optional[Callable[[], Dict[str, Any]]] = None
        self.cb_get_cover_bytes: Optional[Callable[[], Optional[Tuple[bytes, str]]]] = None
        self.cb_get_lyrics: Optional[Callable[[], Dict[str, Any]]] = None
        self.cb_jarvis_query: Optional[Callable[[str], None]] = None
        self.cb_phone_battery: Optional[Callable[[Dict[str, Any]], None]] = None
        self.phone_battery_info: Dict[str, Any] = {}

        self.audio_broadcaster = AudioStreamBroadcaster()

        self._qr_image: Optional[Image.Image] = None

    @property
    def url(self) -> str:
        """Reliable direct Wi-Fi URL that connects immediately without DNS errors."""
        return f"http://{self.local_ip}:{self.port}"

    @property
    def display_url(self) -> str:
        """Clean Apple-style label shown on laptop modal pill."""
        return f"origin.link :{self.port}"

    def start(self):
        if self.is_running:
            return

        cur_port = self.port
        for p in range(cur_port, cur_port + 10):
            try:
                self.server = PhoneDropServer(("0.0.0.0", p), PhoneDropHandler, self)
                self.port = p
                self.local_ip = get_local_ip()
                break
            except OSError:
                continue

        if not self.server:
            print("[PhoneDropService] Error: Could not bind to port.")
            return

        self.server_thread = threading.Thread(target=self.server.serve_forever, daemon=True, name="phone_drop_server")
        self.server_thread.start()
        self.is_running = True
        print(f"[PhoneDropService] Apple iOS Hub online at {self.url}")

    def stop(self):
        if hasattr(self, "audio_broadcaster") and self.audio_broadcaster:
            self.audio_broadcaster.stop()
        if self.server:
            self.server.shutdown()
            self.server.server_close()
            self.server = None
        self.is_running = False

    def get_qr_image(self) -> Image.Image:
        if self._qr_image is None:
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_M,
                box_size=8,
                border=2,
            )
            qr.add_data(self.url)
            qr.make(fit=True)
            self._qr_image = qr.make_image(fill_color="black", back_color="white").convert("RGB")
        return self._qr_image

    def get_qr_pixmap(self, size: int = 140):
        img = self.get_qr_image()
        from PIL.ImageQt import ImageQt
        from PySide6.QtGui import QPixmap
        from PySide6.QtCore import Qt
        qim = ImageQt(img)
        pix = QPixmap.fromImage(qim)
        if size and (pix.width() != size or pix.height() != size):
            pix = pix.scaled(size, size, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        return pix

    def register_client(self, ip: str, user_agent: str):
        friendly = "Phone"
        ua_lower = user_agent.lower()
        if "iphone" in ua_lower:
            friendly = "iPhone"
        elif "ipad" in ua_lower:
            friendly = "iPad"
        elif "android" in ua_lower:
            friendly = "Android Phone"
        self.connected_clients[ip] = {
            "name": friendly,
            "agent": user_agent,
            "last_seen": time.time()
        }

    def get_connected_device_summary(self) -> str:
        now = time.time()
        active = [c["name"] for ip, c in self.connected_clients.items() if (now - c["last_seen"]) < 90.0]
        if not active:
            return "Ready to Pair"
        return f"Connected: {active[-1]}"

    def on_file_received(self, fpath: str, filename: str):
        if self.cb_file_received:
            try:
                self.cb_file_received(fpath, filename)
            except Exception as e:
                print(f"[PhoneDropService] Error in cb_file_received: {e}")

    def on_clipboard_received(self, text: str):
        if self.cb_clipboard_received:
            try:
                self.cb_clipboard_received(text)
            except Exception as e:
                print(f"[PhoneDropService] Error in cb_clipboard_received: {e}")

    def on_url_received(self, url: str):
        if self.cb_url_received:
            try:
                self.cb_url_received(url)
            except Exception as e:
                print(f"[PhoneDropService] Error in cb_url_received: {e}")

    def on_command_received(self, cmd: str, query: str):
        if self.cb_command_received:
            try:
                self.cb_command_received(cmd, query)
            except Exception as e:
                print(f"[PhoneDropService] Error in cb_command_received: {e}")

    def on_jarvis_query(self, query: str):
        if self.cb_jarvis_query:
            try:
                self.cb_jarvis_query(query)
            except Exception as e:
                print(f"[PhoneDropService] Error in cb_jarvis_query: {e}")

    def _attach_desktop(self):
        """Attaches the worker thread to the active interactive user desktop session."""
        try:
            user32 = ctypes.windll.user32
            h_desk = user32.OpenDesktopW("Default", 0, False, 0x01FF)
            if h_desk:
                user32.SetThreadDesktop(h_desk)
        except Exception:
            pass

    def get_screen_bytes(self, max_width: int = 1920, quality: int = 75) -> Tuple[bytes, int, int]:
        """Captures real-time screen with glowing dual-ring cursor overlay for high-definition phone display mirroring."""
        try:
            self._attach_desktop()
            user32 = ctypes.windll.user32
            img = ImageGrab.grab()
            orig_w, orig_h = img.size

            # Draw high-visibility target cursor (cyan glow ring + vivid red core + white center)
            pt = _POINT()
            if user32.GetCursorPos(ctypes.byref(pt)):
                draw = ImageDraw.Draw(img)
                cx, cy = pt.x, pt.y
                # Outer cyan aura ring
                r_outer = 16
                draw.ellipse((cx - r_outer, cy - r_outer, cx + r_outer, cy + r_outer), outline=(0, 240, 255), width=3)
                # Inner vivid red core
                r_inner = 8
                draw.ellipse((cx - r_inner, cy - r_inner, cx + r_inner, cy + r_inner), fill=(255, 45, 85), outline=(255, 255, 255), width=2)
                # Center white dot
                draw.ellipse((cx - 2, cy - 2, cx + 2, cy + 2), fill=(255, 255, 255))

            if max_width and orig_w > max_width:
                target_w = max_width
                target_h = int(target_w * orig_h / orig_w)
                img = img.resize((target_w, target_h), Image.Resampling.BILINEAR)

            buf = io.BytesIO()
            img.save(buf, format="JPEG", quality=quality, optimize=False)
            return buf.getvalue(), orig_w, orig_h
        except Exception as e:
            print(f"[PhoneDropService] Error capturing screen: {e}")
            buf = io.BytesIO()
            Image.new("RGB", (320, 180), color="#111115").save(buf, format="JPEG")
            return buf.getvalue(), 1920, 1080

    def _ensure_active_target_window(self) -> int:
        """Ensures an interactive user application window has input focus before keystrokes or clicks."""
        try:
            self._attach_desktop()
            user32 = ctypes.windll.user32
            fg = user32.GetForegroundWindow()
            if fg and user32.IsWindow(fg) and user32.IsWindowVisible(fg):
                buf = ctypes.create_unicode_buffer(256)
                user32.GetClassNameW(fg, buf, 256)
                cls = buf.value
                if cls not in ("Progman", "WorkerW", "Shell_TrayWnd", "Shell_SecondaryTrayWnd"):
                    return fg

            # If foreground is 0 or shell/desktop, look directly under current cursor
            pt = _POINT()
            if user32.GetCursorPos(ctypes.byref(pt)):
                h_under = user32.WindowFromPoint(pt)
                if h_under and user32.IsWindow(h_under):
                    root = user32.GetAncestor(h_under, 2)  # GA_ROOT
                    target = root or h_under
                    if target and user32.IsWindow(target):
                        buf = ctypes.create_unicode_buffer(256)
                        user32.GetClassNameW(target, buf, 256)
                        if buf.value not in ("Progman", "WorkerW", "Shell_TrayWnd", "Shell_SecondaryTrayWnd"):
                            user32.SetForegroundWindow(target)
                            user32.BringWindowToTop(target)
                            time.sleep(0.015)
                            return target

            # Otherwise find the topmost normal visible application window
            top = user32.GetTopWindow(0)
            while top:
                if user32.IsWindowVisible(top) and not user32.IsIconic(top):
                    length = user32.GetWindowTextLengthW(top)
                    if length > 0:
                        buf = ctypes.create_unicode_buffer(256)
                        user32.GetClassNameW(top, buf, 256)
                        cls = buf.value
                        if cls not in ("Progman", "WorkerW", "Shell_TrayWnd", "Shell_SecondaryTrayWnd", "Windows.UI.Core.CoreWindow"):
                            user32.SetForegroundWindow(top)
                            user32.BringWindowToTop(top)
                            time.sleep(0.015)
                            return top
                top = user32.GetWindow(top, 2)  # GW_HWNDNEXT
        except Exception as e:
            print(f"[PhoneDropService] _ensure_active_target_window error: {e}")
        return 0

    def handle_remote_type(self, text: str, mode: str = "auto"):
        """Types text directly into the focused Windows application using hardware keybd_event & clipboard paste."""
        if not text:
            return
        try:
            self._attach_desktop()
            self._ensure_active_target_window()
            user32 = ctypes.windll.user32
            KEYEVENTF_KEYUP = 0x0002

            # Native Win32 clipboard paste (Ctrl+V) is instant, lossless, handles all UTF-8 characters,
            # accents, emojis, and punctuation across all Windows edit controls.
            if mode in ("paste", "auto") and len(text) > 1:
                if set_win32_clipboard(text):
                    time.sleep(0.02)
                    user32.keybd_event(0x11, 0, 0, 0)  # Ctrl down
                    user32.keybd_event(0x56, 0, 0, 0)  # 'V' down
                    time.sleep(0.025)
                    user32.keybd_event(0x56, 0, KEYEVENTF_KEYUP, 0)  # 'V' up
                    user32.keybd_event(0x11, 0, KEYEVENTF_KEYUP, 0)  # Ctrl up
                    time.sleep(0.01)
                    return

            # Character-by-character hardware keyboard injection (keybd_event + VkKeyScanW)
            for ch in text:
                if ch in ("\r", "\n"):
                    user32.keybd_event(0x0D, 0, 0, 0)
                    time.sleep(0.01)
                    user32.keybd_event(0x0D, 0, KEYEVENTF_KEYUP, 0)
                elif ch == "\t":
                    user32.keybd_event(0x09, 0, 0, 0)
                    time.sleep(0.01)
                    user32.keybd_event(0x09, 0, KEYEVENTF_KEYUP, 0)
                elif ch == "\b":
                    user32.keybd_event(0x08, 0, 0, 0)
                    time.sleep(0.01)
                    user32.keybd_event(0x08, 0, KEYEVENTF_KEYUP, 0)
                elif ch == " ":
                    user32.keybd_event(0x20, 0, 0, 0)
                    time.sleep(0.01)
                    user32.keybd_event(0x20, 0, KEYEVENTF_KEYUP, 0)
                else:
                    vk_res = user32.VkKeyScanW(ord(ch))
                    if vk_res != -1:
                        vk = vk_res & 0xFF
                        shift = bool((vk_res >> 8) & 1)
                        ctrl = bool((vk_res >> 8) & 2)
                        alt = bool((vk_res >> 8) & 4)
                        if shift:
                            user32.keybd_event(0x10, 0, 0, 0)
                        if ctrl:
                            user32.keybd_event(0x11, 0, 0, 0)
                        if alt:
                            user32.keybd_event(0x12, 0, 0, 0)
                        time.sleep(0.005)
                        user32.keybd_event(vk, 0, 0, 0)
                        time.sleep(0.01)
                        user32.keybd_event(vk, 0, KEYEVENTF_KEYUP, 0)
                        time.sleep(0.005)
                        if alt:
                            user32.keybd_event(0x12, 0, KEYEVENTF_KEYUP, 0)
                        if ctrl:
                            user32.keybd_event(0x11, 0, KEYEVENTF_KEYUP, 0)
                        if shift:
                            user32.keybd_event(0x10, 0, KEYEVENTF_KEYUP, 0)
                    else:
                        # Fallback for individual emoji / unmappable character
                        if set_win32_clipboard(ch):
                            time.sleep(0.01)
                            user32.keybd_event(0x11, 0, 0, 0)
                            user32.keybd_event(0x56, 0, 0, 0)
                            time.sleep(0.02)
                            user32.keybd_event(0x56, 0, KEYEVENTF_KEYUP, 0)
                            user32.keybd_event(0x11, 0, KEYEVENTF_KEYUP, 0)
                time.sleep(0.008)
        except Exception as e:
            print(f"[PhoneDropService] Error in handle_remote_type: {e}")

    def handle_remote_mouse(self, action: str, dx: float = 0.0, dy: float = 0.0, btn: str = "left", x: float = 0.0, y: float = 0.0):
        """Instant Win32 hardware mouse event injection (move, click, scroll, drag, zoom) with 0ms latency."""
        try:
            self._attach_desktop()
            user32 = ctypes.windll.user32
            if action == "move":
                pt = _POINT()
                if user32.GetCursorPos(ctypes.byref(pt)):
                    new_x = int(pt.x + dx)
                    new_y = int(pt.y + dy)
                    user32.SetCursorPos(new_x, new_y)
                # Also fire relative move event for hover/window updates
                idx = int(round(dx))
                idy = int(round(dy))
                if idx != 0 or idy != 0:
                    user32.mouse_event(0x0001, idx, idy, 0, 0)
            elif action == "abs_move":
                user32.SetCursorPos(int(x), int(y))
                user32.mouse_event(0x0001, 0, 0, 0, 0)
            elif action == "abs_click":
                user32.SetCursorPos(int(x), int(y))
                pt = _POINT(int(x), int(y))
                h_under = user32.WindowFromPoint(pt)
                if h_under and user32.IsWindow(h_under):
                    root = user32.GetAncestor(h_under, 2)
                    target = root or h_under
                    if target and user32.IsWindow(target):
                        user32.SetForegroundWindow(target)
                        user32.BringWindowToTop(target)
                time.sleep(0.015)
                if btn == "right":
                    user32.mouse_event(0x0008, 0, 0, 0, 0)
                    time.sleep(0.02)
                    user32.mouse_event(0x0010, 0, 0, 0, 0)
                else:
                    user32.mouse_event(0x0002, 0, 0, 0, 0)
                    time.sleep(0.02)
                    user32.mouse_event(0x0004, 0, 0, 0, 0)
            elif action == "click":
                if btn == "right":
                    user32.mouse_event(0x0008, 0, 0, 0, 0)  # MOUSEEVENTF_RIGHTDOWN
                    time.sleep(0.02)
                    user32.mouse_event(0x0010, 0, 0, 0, 0)  # MOUSEEVENTF_RIGHTUP
                else:
                    user32.mouse_event(0x0002, 0, 0, 0, 0)  # MOUSEEVENTF_LEFTDOWN
                    time.sleep(0.02)
                    user32.mouse_event(0x0004, 0, 0, 0, 0)  # MOUSEEVENTF_LEFTUP
            elif action == "double_click":
                user32.mouse_event(0x0002, 0, 0, 0, 0)
                time.sleep(0.02)
                user32.mouse_event(0x0004, 0, 0, 0, 0)
                time.sleep(0.04)
                user32.mouse_event(0x0002, 0, 0, 0, 0)
                time.sleep(0.02)
                user32.mouse_event(0x0004, 0, 0, 0, 0)
            elif action == "down":
                user32.mouse_event(0x0002, 0, 0, 0, 0)  # Left button down (Text selection / Drag)
            elif action == "up":
                user32.mouse_event(0x0004, 0, 0, 0, 0)  # Left button up (Release)
            elif action == "zoom":
                # Ctrl + Wheel (Windows native precision zoom)
                KEYEVENTF_KEYUP = 0x0002
                user32.keybd_event(0x11, 0, 0, 0)  # VK_CONTROL down
                wheel_delta = 120 if dy > 0 else -120
                user32.mouse_event(0x0800, 0, 0, wheel_delta, 0)
                time.sleep(0.01)
                user32.keybd_event(0x11, 0, KEYEVENTF_KEYUP, 0)  # VK_CONTROL up
            elif action == "scroll":
                if abs(dy) >= 60:
                    wheel_delta = int(dy)
                else:
                    wheel_delta = int(round(dy * 120))
                if wheel_delta != 0:
                    user32.mouse_event(0x0800, 0, 0, wheel_delta, 0)
        except Exception as e:
            print(f"[PhoneDropService] Error in handle_remote_mouse: {e}")

    def handle_remote_key(self, key: str):
        """Instant Win32 virtual keyboard injection for typing, navigation, and clipboard shortcuts."""
        try:
            self._attach_desktop()
            user32 = ctypes.windll.user32
            KEYEVENTF_KEYUP = 0x0002
            key_lower = key.lower().strip()

            # Clipboard & Editing Shortcuts
            if key_lower in ("copy", "ctrlc"):
                user32.keybd_event(0x11, 0, 0, 0)  # Ctrl
                user32.keybd_event(0x43, 0, 0, 0)  # 'C'
                time.sleep(0.012)
                user32.keybd_event(0x43, 0, KEYEVENTF_KEYUP, 0)
                user32.keybd_event(0x11, 0, KEYEVENTF_KEYUP, 0)
                return
            elif key_lower in ("paste", "ctrlv"):
                user32.keybd_event(0x11, 0, 0, 0)  # Ctrl
                user32.keybd_event(0x56, 0, 0, 0)  # 'V'
                time.sleep(0.012)
                user32.keybd_event(0x56, 0, KEYEVENTF_KEYUP, 0)
                user32.keybd_event(0x11, 0, KEYEVENTF_KEYUP, 0)
                return
            elif key_lower in ("cut", "ctrlx"):
                user32.keybd_event(0x11, 0, 0, 0)  # Ctrl
                user32.keybd_event(0x58, 0, 0, 0)  # 'X'
                time.sleep(0.012)
                user32.keybd_event(0x58, 0, KEYEVENTF_KEYUP, 0)
                user32.keybd_event(0x11, 0, KEYEVENTF_KEYUP, 0)
                return
            elif key_lower in ("selectall", "ctrla"):
                user32.keybd_event(0x11, 0, 0, 0)  # Ctrl
                user32.keybd_event(0x41, 0, 0, 0)  # 'A'
                time.sleep(0.012)
                user32.keybd_event(0x41, 0, KEYEVENTF_KEYUP, 0)
                user32.keybd_event(0x11, 0, KEYEVENTF_KEYUP, 0)
                return
            elif key_lower in ("undo", "ctrlz"):
                user32.keybd_event(0x11, 0, 0, 0)  # Ctrl
                user32.keybd_event(0x5A, 0, 0, 0)  # 'Z'
                time.sleep(0.012)
                user32.keybd_event(0x5A, 0, KEYEVENTF_KEYUP, 0)
                user32.keybd_event(0x11, 0, KEYEVENTF_KEYUP, 0)
                return
            elif key_lower in ("alttab", "switch"):
                user32.keybd_event(0x12, 0, 0, 0)  # Alt
                user32.keybd_event(0x09, 0, 0, 0)  # Tab
                time.sleep(0.015)
                user32.keybd_event(0x09, 0, KEYEVENTF_KEYUP, 0)
                user32.keybd_event(0x12, 0, KEYEVENTF_KEYUP, 0)
                return
            elif key_lower in ("minimize", "min"):
                user32.keybd_event(0x5B, 0, 0, 0)  # Win
                user32.keybd_event(0x28, 0, 0, 0)  # Down
                time.sleep(0.015)
                user32.keybd_event(0x28, 0, KEYEVENTF_KEYUP, 0)
                user32.keybd_event(0x5B, 0, KEYEVENTF_KEYUP, 0)
                return
            elif key_lower in ("maximize", "max"):
                user32.keybd_event(0x5B, 0, 0, 0)  # Win
                user32.keybd_event(0x26, 0, 0, 0)  # Up
                time.sleep(0.015)
                user32.keybd_event(0x26, 0, KEYEVENTF_KEYUP, 0)
                user32.keybd_event(0x5B, 0, KEYEVENTF_KEYUP, 0)
                return
            elif key_lower in ("close", "closewindow", "altf4"):
                user32.keybd_event(0x12, 0, 0, 0)  # Alt
                user32.keybd_event(0x73, 0, 0, 0)  # F4
                time.sleep(0.015)
                user32.keybd_event(0x73, 0, KEYEVENTF_KEYUP, 0)
                user32.keybd_event(0x12, 0, KEYEVENTF_KEYUP, 0)
                return
            elif key_lower in ("newtab", "addtab"):
                user32.keybd_event(0x11, 0, 0, 0)  # Ctrl
                user32.keybd_event(0x54, 0, 0, 0)  # 'T'
                time.sleep(0.015)
                user32.keybd_event(0x54, 0, KEYEVENTF_KEYUP, 0)
                user32.keybd_event(0x11, 0, KEYEVENTF_KEYUP, 0)
                return
            elif key_lower in ("closetab", "ctrlw"):
                user32.keybd_event(0x11, 0, 0, 0)  # Ctrl
                user32.keybd_event(0x57, 0, 0, 0)  # 'W'
                time.sleep(0.015)
                user32.keybd_event(0x57, 0, KEYEVENTF_KEYUP, 0)
                user32.keybd_event(0x11, 0, KEYEVENTF_KEYUP, 0)
                return
            elif key_lower in ("tabswitch", "nexttab", "ctrltab"):
                user32.keybd_event(0x11, 0, 0, 0)  # Ctrl
                user32.keybd_event(0x09, 0, 0, 0)  # Tab
                time.sleep(0.015)
                user32.keybd_event(0x09, 0, KEYEVENTF_KEYUP, 0)
                user32.keybd_event(0x11, 0, KEYEVENTF_KEYUP, 0)
                return

            # Special Keys mapping
            vk_map = {
                "enter": 0x0D,
                "return": 0x0D,
                "backspace": 0x08,
                "tab": 0x09,
                "space": 0x20,
                "esc": 0x1B,
                "escape": 0x1B,
                "win": 0x5B,
                "up": 0x26,
                "down": 0x28,
                "left": 0x25,
                "right": 0x27,
                "pgup": 0x21,
                "pageup": 0x21,
                "pgdn": 0x22,
                "pagedown": 0x22,
                "del": 0x2E,
                "delete": 0x2E,
                "home": 0x24,
                "end": 0x23,
                "next": 0x27,
                "prev": 0x25,
                "f5": 0x74,
                "b": 0x42,
                "volup": 0xAF,
                "voldown": 0xAE,
            }

            vk = vk_map.get(key_lower, 0)
            if vk:
                user32.keybd_event(vk, 0, 0, 0)
                time.sleep(0.012)
                user32.keybd_event(vk, 0, KEYEVENTF_KEYUP, 0)
        except Exception as e:
            print(f"[PhoneDropService] Error in handle_remote_key: {e}")


    def on_phone_battery_received(self, data: Dict[str, Any]):
        """Stores phone battery level and notifies callbacks for desktop toasts."""
        try:
            level = float(data.get("level", 1.0))
            percent = int(round(level * 100)) if level <= 1.0 else int(round(level))
            charging = bool(data.get("charging", False))
            self.phone_battery_info = {
                "percent": max(0, min(100, percent)),
                "charging": charging,
                "updated": time.time()
            }
            if self.cb_phone_battery:
                try:
                    self.cb_phone_battery(self.phone_battery_info)
                except Exception as e:
                    print(f"[PhoneDropService] cb_phone_battery error: {e}")
        except Exception as e:
            print(f"[PhoneDropService] Battery parsing error: {e}")

    def on_voice_note_received(self, path: str, name: str):
        """Called when a voice memo from phone is saved to PC."""
        print(f"[PhoneDropService] Voice memo saved: {path}")
        if self.cb_file_received:
            try:
                self.cb_file_received(path, name)
            except Exception as e:
                print(f"[PhoneDropService] cb_file_received error: {e}")


    def get_cover_bytes(self) -> Optional[Tuple[bytes, str]]:
        if self.cb_get_cover_bytes:
            try:
                return self.cb_get_cover_bytes()
            except Exception:
                pass
        return None

    def get_lyrics_data(self) -> Dict[str, Any]:
        if self.cb_get_lyrics:
            try:
                return self.cb_get_lyrics()
            except Exception:
                pass
        return {"title": "", "artist": "", "pos_sec": 0.0, "active_idx": -1, "lines": []}

    def get_placeholder_cover_svg(self) -> bytes:
        """High-resolution Apple Music style vinyl artwork SVG."""
        svg = """<svg xmlns="http://www.w3.org/2000/svg" width="300" height="300" viewBox="0 0 300 300">
  <defs>
    <linearGradient id="appleGradient" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#fc3c44"/>
      <stop offset="50%" stop-color="#fa2d48"/>
      <stop offset="100%" stop-color="#5856d6"/>
    </linearGradient>
  </defs>
  <rect width="300" height="300" rx="36" fill="url(#appleGradient)"/>
  <circle cx="150" cy="150" r="105" fill="none" stroke="rgba(255,255,255,0.18)" stroke-width="2"/>
  <circle cx="150" cy="150" r="70" fill="none" stroke="rgba(255,255,255,0.12)" stroke-width="1.5"/>
  <circle cx="150" cy="150" r="32" fill="#000000" stroke="rgba(255,255,255,0.3)" stroke-width="2"/>
  <path d="M142 134 v20 a12 12 0 1 0 10 11.8 V140 h14 v-6 z" fill="#ffffff"/>
</svg>"""
        return svg.encode("utf-8")

    def get_status_data(self) -> Dict[str, Any]:
        data = {
            "pc_name": self.hostname.upper(),
            "hostname": self.hostname,
            "url": self.url,
            "clipboard": "",
            "now_playing": None,
            "shelf_files": [],
            "volume": 50,
            "pc_battery": get_win32_power_status(),
            "phone_battery": self.phone_battery_info,
            "sleep_timer": SleepTimerManager.get_instance().get_status(),
            "jarvis": {
                "status": "Ready",
                "status_detail": "Ready",
                "reply": "",
                "is_talking": False,
                "history": []
            }
        }
        if self.cb_get_status:
            try:
                res = self.cb_get_status()
                if isinstance(res, dict):
                    data.update(res)
            except Exception as e:
                print(f"[PhoneDropService] Error in cb_get_status: {e}")
        return data

    def find_shared_file(self, filename: str) -> Optional[str]:
        dl_target = DOWNLOADS_DIR / filename
        if dl_target.exists():
            return str(dl_target)
        status = self.get_status_data()
        for f in status.get("shelf_files", []):
            if f.get("name") == filename and os.path.exists(f.get("path", "")):
                return f.get("path")
        return None
