import ctypes
import math
import random
import re
import subprocess
import sys
import time
import urllib.parse
import webbrowser
from pathlib import Path
from typing import Optional, List, Dict, Any

try:
    import psutil
    HAS_PSUTIL = True
except Exception:
    HAS_PSUTIL = False

from PySide6.QtCore import (
    Qt, QTimer, QPoint, QPointF, QRect, QRectF, QPropertyAnimation,
    QEasingCurve, Signal, QUrl
)
from PySide6.QtGui import (
    QPainter, QColor, QFont, QFontMetrics, QPainterPath, QPen,
    QPixmap, QImage, QLinearGradient, QRadialGradient, QCursor,
    QGuiApplication, QDesktopServices, QPolygonF
)
from PySide6.QtWidgets import (
    QWidget, QApplication, QPushButton, QHBoxLayout, QVBoxLayout,
    QLabel, QGraphicsDropShadowEffect
)

from media_service import MediaService, MediaInfo
from weather_service import WeatherService, WeatherInfo
from bluetooth_service import BluetoothService, BluetoothInfo

ALBUM_ART_PATH = Path(__file__).parent / "assets" / "sprites" / "album_art.png"


ISLAND_THEMES = {
    "apple_dynamic": {
        "name": "Apple Dynamic Glass (iOS Pro) 🍎",
        "bg_top": QColor(14, 14, 18, 245),
        "bg_bottom": QColor(6, 6, 8, 252),
        "border": QColor(255, 255, 255, 45),
        "border_width": 1.0,
        "accent": QColor(255, 255, 255),
        "accent_glow": QColor(255, 255, 255, 25),
        "text_primary": QColor(255, 255, 255),
        "text_secondary": QColor(155, 155, 165),
        "badge_bg": QColor(35, 35, 42, 210),
        "btn_bg": QColor(255, 255, 255, 22),
        "btn_hover": QColor(255, 255, 255, 70),
        "eq_0": QColor(52, 199, 89),
        "eq_1": QColor(48, 209, 88),
    },
    "originos_dark": {
        "name": "OriginOS Obsidian Glass (Deep Space) 🖤",
        "bg_top": QColor(12, 14, 20, 245),
        "bg_bottom": QColor(6, 7, 12, 252),
        "border": QColor(100, 160, 255, 60),
        "border_width": 1.0,
        "accent": QColor(96, 165, 250),
        "accent_glow": QColor(96, 165, 250, 30),
        "text_primary": QColor(255, 255, 255),
        "text_secondary": QColor(148, 163, 184),
        "badge_bg": QColor(30, 41, 59, 200),
        "btn_bg": QColor(255, 255, 255, 20),
        "btn_hover": QColor(96, 165, 250, 80),
        "eq_0": QColor(96, 165, 250),
        "eq_1": QColor(147, 197, 253),
    },
    "cyber_glow": {
        "name": "Cyberpunk Titanium (Neon Glow) ⚡",
        "bg_top": QColor(12, 12, 22, 245),
        "bg_bottom": QColor(6, 6, 14, 252),
        "border": QColor(0, 240, 255, 110),
        "border_width": 1.0,
        "accent": QColor(0, 240, 255),
        "accent_glow": QColor(255, 0, 128, 50),
        "text_primary": QColor(255, 255, 255),
        "text_secondary": QColor(120, 225, 245),
        "badge_bg": QColor(255, 0, 128, 120),
        "btn_bg": QColor(0, 240, 255, 25),
        "btn_hover": QColor(0, 240, 255, 90),
        "eq_0": QColor(0, 240, 255),
        "eq_1": QColor(255, 0, 128),
    },
    "frosted_crystal": {
        "name": "Frosted Crystal (Ultra Clear) 🫧",
        "bg_top": QColor(30, 35, 50, 150),
        "bg_bottom": QColor(15, 20, 32, 190),
        "border": QColor(255, 255, 255, 100),
        "border_width": 1.0,
        "accent": QColor(160, 235, 255),
        "accent_glow": QColor(255, 255, 255, 40),
        "text_primary": QColor(255, 255, 255),
        "text_secondary": QColor(215, 230, 245),
        "badge_bg": QColor(255, 255, 255, 30),
        "btn_bg": QColor(255, 255, 255, 30),
        "btn_hover": QColor(160, 235, 255, 80),
        "eq_0": QColor(255, 255, 255),
        "eq_1": QColor(160, 235, 255),
    }
}


ISLAND_AMBIENT_NAMES = {
    "adaptive_album": "🎨 Adaptive Album Art Aura",
    "aurora_borealis": "🌌 Aurora Borealis Flow",
    "neon_cyber_pulse": "⚡ Cyberpunk Neon Strobe",
    "sunset_chroma": "🌅 Synthwave Sunset Glow",
    "lava_fire_glow": "🔥 Inferno Magma Pulse",
    "rainbow_flow": "🌈 RGB Chroma Spectrum",
    "minimal_frost": "✨ Apple Minimal Frost",
}


class OriginIsland(QWidget):
    """
    OriginOS & Apple Dynamic Island Widget for Desktop.
    Features live music equalizer/controls, real-time weather & precision digital clock,
    smart clipboard manager with one-click URL opening & web searching, and fluid shape-morphing physics.
    """

    # Island States
    STATE_COMPACT = "compact"
    STATE_MUSIC = "music"
    STATE_WEATHER = "weather"
    STATE_MAP = "map"
    STATE_CLIPBOARD = "clipboard"
    STATE_TOOLS = "tools"

    # Size configurations
    SIZES = {
        STATE_COMPACT: (230, 38),
        STATE_MUSIC: (390, 150),
        STATE_WEATHER: (390, 150),
        STATE_MAP: (390, 150),
        STATE_CLIPBOARD: (390, 150),
        STATE_TOOLS: (390, 150),
    }

    def __init__(self, settings=None, parent=None):
        super().__init__(parent)
        self._settings = settings

        # Window styling: Frameless, transparent background, top-level overlay
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)
        self.setMouseTracking(True)

        # State management & OriginOS Spring Physics Engine
        self._state = self.STATE_COMPACT
        self._prev_state = self.STATE_COMPACT
        self._current_w, self._current_h = self.SIZES[self.STATE_COMPACT]
        self._target_w, self._target_h = float(self._current_w), float(self._current_h)
        self._anim_w, self._anim_h = float(self._current_w), float(self._current_h)
        self._vel_w, self._vel_h = 0.0, 0.0
        self._is_morphing = False
        self._morph_progress = 0.0  # 0.0 (compact pill) -> 1.0 (expanded squircle card)
        self._corner_radius = 19.0
        self._last_tick_time = time.monotonic()

        # OriginOS Sliding Tab Indicator & Fluid Squash-and-Stretch
        self._tab_from = "music"
        self._tab_to = "music"
        self._tab_transition_progress = 1.0
        self._indicator_x = float(self.SIZES[self.STATE_MUSIC][0] - 138 - 6)
        self._indicator_target_x = self._indicator_x
        self._indicator_vel = 0.0
        self._indicator_w = 22.0
        self._indicator_w_vel = 0.0

        # Tactile Micro-Interactions: Button Hover Glow & Elastic Press Bounce
        self._hovered_btn: Optional[str] = None
        self._btn_hover_anim: Dict[str, float] = {}
        self._btn_press_anim: Dict[str, float] = {}

        # OriginOS Animated Drop-Down Volume HUD & Toast Banner
        self._volume_hud_y = -32.0
        self._anim_volume_level = 50.0
        self._toast_y = -30.0

        # Magnetic Notch Snap Flight Physics
        self._is_snapping_to_notch = False
        self._snap_target_x = 0.0
        self._snap_target_y = 0.0
        self._snap_vel_x = 0.0
        self._snap_vel_y = 0.0

        self._theme_key = "apple_dynamic"
        if settings and hasattr(settings, "island_style"):
            self._theme_key = settings.island_style or "apple_dynamic"
        if self._theme_key not in ISLAND_THEMES:
            self._theme_key = "apple_dynamic"

        self._position_mode = "top_notch"
        if settings and hasattr(settings, "island_position"):
            self._position_mode = settings.island_position or "top_notch"

        # Media service
        self._media = MediaService.get_instance()
        self._media.add_listener(self._on_media_listener_callback)
        self._last_media_info = self._media.current_info

        # Weather service
        self._weather = WeatherService.get_instance()
        if settings and hasattr(settings, "weather_location") and settings.weather_location:
            self._weather.set_location(settings.weather_location)
        self._weather.add_listener(self._on_weather_listener_callback)
        self._last_weather_info = self._weather.current_weather

        # Bluetooth service
        self._bluetooth = BluetoothService.get_instance()
        self._bluetooth.add_listener(self._on_bluetooth_updated)
        self._last_bluetooth_info = self._bluetooth.current_info

        # Smart Clipboard Tracking & History
        self._last_clipboard_text = ""
        self._clipboard_preview_text = ""
        self._clipboard_word_count = 0
        self._clipboard_char_count = 0
        self._last_clipboard_url: Optional[str] = None
        self._clipboard_color_hex: Optional[str] = None
        self._clipboard_calc_result: Optional[str] = None
        self._clipboard_history: list = []
        self._clipboard_copy_feedback = 0.0
        self._clipboard_banner_time = 0.0
        self._last_clipboard_change_time = 0.0
        self._clipboard = QApplication.clipboard()
        self._clipboard.dataChanged.connect(self._on_clipboard_changed)

        # System Performance Monitoring (CPU & RAM)
        self._last_cpu_percent = 0.0
        self._last_ram_percent = 0.0
        self._last_sys_check_time = 0.0

        # Interactive Volume HUD Overlay State
        self._volume_hud_time = 0.0
        self._volume_hud_action = "+"
        self._volume_hud_level = 50

        # Equalizer & ticker state
        self._eq_bars = [0.3, 0.6, 0.9, 0.5, 0.8, 0.4]
        self._ticker_offset = 0
        self._is_hovered = False
        self._pinned = False
        self._last_expanded_tab = self.STATE_MUSIC
        self._compact_ticker_x = 0.0
        self._music_ticker_x = 0.0
        self._anim_cpu = 15.0
        self._anim_ram = 45.0
        self._collapse_timer = QTimer(self)
        self._collapse_timer.setSingleShot(True)
        self._collapse_timer.timeout.connect(self._auto_collapse)

        # Ambient Light & Music Beat Flow Engine
        self._ambient_style = "adaptive_album"
        if settings and hasattr(settings, "island_ambient_style"):
            self._ambient_style = settings.island_ambient_style or "adaptive_album"
        self._ambient_hue = 210.0
        self._ambient_color_current = QColor(0, 122, 255)
        self._ambient_color_secondary = QColor(168, 85, 247)
        self._ambient_beat_energy = 0.0
        self._extracted_art_color: Optional[QColor] = None
        self._last_thumb_len: int = 0
        self._ambient_toast_time = 0.0
        self._ambient_toast_name = ""

        # Ambient Inferno Magma Embers (for lava_fire_glow)
        self._lava_embers = [
            {"x": random.uniform(20, 370), "y": random.uniform(80, 150), "speed": random.uniform(0.7, 2.2), "r": random.uniform(1.2, 2.8), "alpha": random.uniform(0.35, 0.95)}
            for _ in range(22)
        ]

        # Precision Compass & Live Navigation Engine
        self._compass_heading = 0.0
        self._compass_current_heading = 0.0
        self._compass_mode = "drift"  # "drift", "mouse", "north"
        self._compass_calibrated = True

        # Live Google Maps & Route Navigation Simulator
        self._map_view_mode = "split"  # "split" (Compass + Live Map) or "panoramic" (Full Route View)
        self._compass_left_view = "compass"  # "compass" or "turn_hud"
        self._nav_progress = 0.0  # 0.0 to 1.0 along the route path
        self._nav_speed = 0.0035  # simulation movement speed per frame
        self._traffic_enabled = True

        # Interactive Media Progress State
        self._playback_pos_sec = 0.0
        self._playback_dur_sec = 214.0  # ~3:34 min default track duration
        self._is_scrubbing = False
        self._last_played_title = ""

        # Procedural Weather Physics Particles (60 FPS Vector Animation Engine)
        self._anim_time = 0.0
        # 1. Rain & Splashes
        self._rain_drops = [
            {"x": random.uniform(0, 150), "y": random.uniform(0, 108), "speed": random.uniform(4.5, 8.0), "len": random.uniform(6, 12), "alpha": random.uniform(0.4, 0.95)}
            for _ in range(35)
        ]
        self._rain_splashes = []
        # 2. Snowflakes
        self._snow_flakes = [
            {"x": random.uniform(0, 150), "y": random.uniform(0, 108), "speed": random.uniform(0.6, 1.8), "r": random.uniform(1.2, 2.6), "phase": random.uniform(0, 6.28), "alpha": random.uniform(0.4, 0.95)}
            for _ in range(30)
        ]
        # 3. Wind Ribbons & Breeze Particles
        self._wind_particles = [
            {"x": random.uniform(0, 150), "y": random.uniform(10, 98), "speed": random.uniform(2.5, 5.0), "size": random.uniform(1.5, 3.0), "alpha": random.uniform(0.3, 0.8)}
            for _ in range(16)
        ]
        # 4. Heat / Hot Embers & Shimmer
        self._heat_embers = [
            {"x": random.uniform(10, 140), "y": random.uniform(20, 108), "speed": random.uniform(0.8, 2.0), "r": random.uniform(1.0, 2.5), "phase": random.uniform(0, 6.28), "alpha": random.uniform(0.3, 0.85)}
            for _ in range(18)
        ]
        # 5. Thunder Lightning state
        self._lightning_flash = 0.0
        self._lightning_timer = 0
        self._lightning_bolt_pts = []
        # 6. Night Stars
        self._night_stars = [
            {"x": random.uniform(10, 140), "y": random.uniform(10, 100), "r": random.uniform(1.0, 2.2), "freq": random.uniform(1.5, 4.0), "phase": random.uniform(0, 6.28)}
            for _ in range(18)
        ]
        # 7. Cloud Drift Layers
        self._cloud_drift = [0.0, 40.0, 90.0]

        # Drag tracking
        self._is_dragging = False
        self._drag_start = QPoint()

        # Render loop (OriginOS 60 FPS ultra-smooth physics, throttles to 1s when idle)
        self._timer = QTimer(self)
        self._timer.setTimerType(Qt.TimerType.PreciseTimer)
        self._timer.setInterval(16)
        self._timer.timeout.connect(self._render_tick)
        self._timer.start()

        # Initial geometry setup
        self._reposition()
        self.resize(self._current_w, self._current_h)

        # Check initial clipboard
        self._check_initial_clipboard()

    # ── Geometry & Morphing Physics ──────────────────────────────────────────

    def _reposition(self):
        screen = QGuiApplication.primaryScreen()
        if not screen:
            return
        geo = screen.geometry()

        if self._position_mode == "top_notch":
            target_x = geo.x() + (geo.width() - self._current_w) // 2
            target_y = geo.y() + 10
            self.move(target_x, target_y)
        elif self._position_mode == "follow_pet":
            pass  # Position updated by pet instance
        # "floating" keeps its current position

    def set_pet_anchor(self, pet_x: int, pet_y: int, pet_size: int):
        if self._position_mode == "follow_pet":
            target_x = pet_x + (pet_size - self._current_w) // 2
            target_y = max(10, pet_y - self._current_h - 12)
            self.move(target_x, target_y)

    def set_theme(self, theme_key: str):
        if theme_key in ISLAND_THEMES:
            self._theme_key = theme_key
            if self._settings:
                self._settings.island_style = theme_key
                self._settings.save()
            self.update()

    def set_island_style(self, theme_key: str):
        self.set_theme(theme_key)

    def set_ambient_style(self, style_key: str, notify: bool = True):
        if style_key in ISLAND_AMBIENT_NAMES:
            self._ambient_style = style_key
            if self._settings:
                self._settings.island_ambient_style = style_key
                self._settings.save()
            if notify:
                self._ambient_toast_time = time.monotonic()
                self._ambient_toast_name = ISLAND_AMBIENT_NAMES.get(style_key, style_key)
            self.update()

    def _cycle_ambient_style(self):
        styles = list(ISLAND_AMBIENT_NAMES.keys())
        try:
            cur_idx = styles.index(self._ambient_style)
            next_style = styles[(cur_idx + 1) % len(styles)]
        except ValueError:
            next_style = styles[0]
        self.set_ambient_style(next_style, notify=True)

    def set_position_mode(self, mode: str):
        self._position_mode = mode
        if self._settings:
            self._settings.island_position = mode
            self._settings.save()
        self._reposition()

    def set_island_position(self, mode: str):
        self.set_position_mode(mode)

    def set_weather_location(self, loc: str):
        self._weather.set_location(loc)
        if self._settings:
            self._settings.weather_location = loc
            self._settings.save()

    def expand_to_state(self, state_id: int):
        mapping = {
            0: self.STATE_COMPACT,
            1: self.STATE_MUSIC,
            2: self.STATE_WEATHER,
            3: self.STATE_CLIPBOARD,
            4: self.STATE_TOOLS,
        }
        self.switch_state(mapping.get(state_id, self.STATE_COMPACT))

    def _on_media_listener_callback(self, info: MediaInfo):
        self._wake_timer()
        QTimer.singleShot(0, lambda: self._on_media_updated(info))

    def _on_weather_listener_callback(self, info: WeatherInfo):
        QTimer.singleShot(0, lambda: self._on_weather_updated(info))

    def _on_weather_updated(self, info: WeatherInfo):
        self._last_weather_info = info
        self.update()

    def _render_tick(self):
        # 0. Sync Media & Weather Info
        cur_media = self._media.current_info
        if cur_media:
            self._last_media_info = cur_media
            if cur_media.title and cur_media.title != self._last_played_title:
                self._last_played_title = cur_media.title
                self._playback_pos_sec = 0.0

        cur_weather = self._weather.current_weather
        if cur_weather:
            self._last_weather_info = cur_weather

        # Global animation timer with true delta time
        now = time.monotonic()
        dt = min(0.04, max(0.001, now - self._last_tick_time))
        self._last_tick_time = now
        self._anim_time += dt

        # 1. Advance Playback Progress
        is_playing = bool(self._last_media_info and self._last_media_info.is_playing)
        if is_playing and not self._is_scrubbing:
            self._playback_pos_sec += dt
            if self._playback_pos_sec >= self._playback_dur_sec:
                self._playback_pos_sec = 0.0

        # 2. OriginOS Physical Spring Engine for Morphing Width & Height
        diff_w = self._target_w - self._anim_w
        diff_h = self._target_h - self._anim_h

        is_expanding = (self._target_h > self._anim_h or self._target_w > self._anim_w)
        if is_expanding:
            tension = 240.0
            damping = 19.5
        else:
            tension = 290.0
            damping = 25.5

        if abs(diff_w) > 0.25 or abs(diff_h) > 0.25 or abs(self._vel_w) > 0.4 or abs(self._vel_h) > 0.4:
            self._is_morphing = True
            acc_w = tension * diff_w - damping * self._vel_w
            acc_h = tension * diff_h - damping * self._vel_h
            self._vel_w += acc_w * dt
            self._vel_h += acc_h * dt
            self._anim_w += self._vel_w * dt
            self._anim_h += self._vel_h * dt

            # Calculate continuous expansion progress 0.0 -> 1.0
            h_range = max(1.0, 150.0 - 38.0)
            self._morph_progress = min(1.0, max(0.0, (self._anim_h - 38.0) / h_range))

            # Dynamic corner radius interpolation (Pill 19.0 -> Squircle 26.0)
            smooth_p = self._morph_progress * self._morph_progress * (3.0 - 2.0 * self._morph_progress)
            self._corner_radius = 19.0 * (1.0 - smooth_p) + 26.0 * smooth_p

            new_w = max(120, int(round(self._anim_w)))
            new_h = max(30, int(round(self._anim_h)))

            if new_w != self._current_w or new_h != self._current_h:
                old_w = self._current_w
                self._current_w = new_w
                self._current_h = new_h

                if self._position_mode == "top_notch":
                    screen = QGuiApplication.primaryScreen()
                    if screen:
                        geo = screen.geometry()
                        target_x = geo.x() + (geo.width() - new_w) // 2
                        target_y = geo.y() + 10
                        self.setGeometry(target_x, target_y, new_w, new_h)
                elif self._position_mode == "floating":
                    shift_x = (new_w - old_w) // 2
                    self.setGeometry(self.x() - shift_x, self.y(), new_w, new_h)
                else:
                    self.resize(new_w, new_h)
        else:
            if self._is_morphing:
                self._is_morphing = False
                self._anim_w = float(self._target_w)
                self._anim_h = float(self._target_h)
                self._vel_w = 0.0
                self._vel_h = 0.0
                self._current_w = int(self._target_w)
                self._current_h = int(self._target_h)
                if self._target_h <= 40:
                    self._morph_progress = 0.0
                    self._corner_radius = 19.0
                else:
                    self._morph_progress = 1.0
                    self._corner_radius = 26.0

                if self._position_mode == "top_notch":
                    screen = QGuiApplication.primaryScreen()
                    if screen:
                        geo = screen.geometry()
                        target_x = geo.x() + (geo.width() - self._current_w) // 2
                        target_y = geo.y() + 10
                        self.setGeometry(target_x, target_y, self._current_w, self._current_h)
                else:
                    self.resize(self._current_w, self._current_h)

        # Magnetic Snap to Notch Spring Flight
        if self._is_snapping_to_notch:
            cur_x = float(self.x())
            cur_y = float(self.y())
            dx = self._snap_target_x - cur_x
            dy = self._snap_target_y - cur_y
            if abs(dx) < 0.5 and abs(dy) < 0.5 and abs(self._snap_vel_x) < 1.0 and abs(self._snap_vel_y) < 1.0:
                self.move(int(round(self._snap_target_x)), int(round(self._snap_target_y)))
                self._is_snapping_to_notch = False
                self.set_position_mode("top_notch")
            else:
                acc_x = 280.0 * dx - 24.0 * self._snap_vel_x
                acc_y = 280.0 * dy - 24.0 * self._snap_vel_y
                self._snap_vel_x += acc_x * dt
                self._snap_vel_y += acc_y * dt
                new_x = cur_x + self._snap_vel_x * dt
                new_y = cur_y + self._snap_vel_y * dt
                self.move(int(round(new_x)), int(round(new_y)))

        # OriginOS Sliding Tab Indicator Spring Physics
        ind_diff = self._indicator_target_x - self._indicator_x
        ind_acc = 340.0 * ind_diff - 27.0 * self._indicator_vel
        self._indicator_vel += ind_acc * dt
        self._indicator_x += self._indicator_vel * dt

        speed = abs(self._indicator_vel)
        target_stretch = min(10.0, speed * 0.018)
        stretch_diff = (22.0 + target_stretch) - self._indicator_w
        self._indicator_w_vel += (280.0 * stretch_diff - 24.0 * self._indicator_w_vel) * dt
        self._indicator_w += self._indicator_w_vel * dt

        # Tab cross-fade progress
        if self._tab_transition_progress < 1.0:
            self._tab_transition_progress = min(1.0, self._tab_transition_progress + dt * 5.0)

        # Volume HUD Drop-Down Spring Animation
        hud_elapsed = time.monotonic() - self._volume_hud_time
        if hud_elapsed < 1.4:
            target_hud_y = 5.0
        else:
            target_hud_y = -32.0
        hud_y_diff = target_hud_y - self._volume_hud_y
        self._volume_hud_y += hud_y_diff * min(1.0, dt * 16.0)

        # Smooth Volume Bar Spring Interpolation
        self._anim_volume_level += (float(self._volume_hud_level) - self._anim_volume_level) * min(1.0, dt * 14.0)

        # Toast Banner Drop-Down Spring Animation
        toast_elapsed = time.monotonic() - self._ambient_toast_time
        if toast_elapsed < 1.8:
            target_toast_y = 4.0
        else:
            target_toast_y = -30.0
        toast_y_diff = target_toast_y - self._toast_y
        self._toast_y += toast_y_diff * min(1.0, dt * 16.0)

        # Tactile Button Micro-Animation Decays
        for b_name in list(self._btn_hover_anim.keys()):
            t_target = 1.0 if (self._hovered_btn == b_name) else 0.0
            self._btn_hover_anim[b_name] += (t_target - self._btn_hover_anim[b_name]) * min(1.0, dt * 16.0)
            if self._btn_hover_anim[b_name] < 0.005 and t_target == 0.0:
                self._btn_hover_anim[b_name] = 0.0

        for b_name in list(self._btn_press_anim.keys()):
            if self._btn_press_anim[b_name] > 0.001:
                self._btn_press_anim[b_name] = max(0.0, self._btn_press_anim[b_name] - dt * 6.5)

        # 3. Harmonic Liquid Wave Equalizer (OriginOS & iOS Dynamic Island Sound Wave)
        if is_playing:
            freqs = [2.4, 3.2, 4.2, 3.6, 2.8, 3.9]
            phases = [0.0, 1.1, 2.3, 0.9, 3.2, 1.8]
            beat = self._ambient_beat_energy
            t = self._anim_time
            for i in range(len(self._eq_bars)):
                wave = (math.sin(t * freqs[i] + phases[i]) * 0.5 + 0.5)
                pulse = (math.sin(t * 2.0) * 0.5 + 0.5) * beat
                target = 0.18 + 0.44 * wave + 0.38 * pulse
                self._eq_bars[i] += (target - self._eq_bars[i]) * min(1.0, dt * 12.0)
        else:
            for i in range(len(self._eq_bars)):
                self._eq_bars[i] += (0.12 - self._eq_bars[i]) * min(1.0, dt * 6.0)

        if is_playing:
            avg_eq = sum(self._eq_bars) / max(1, len(self._eq_bars))
            bass_kick = (self._eq_bars[0] * 0.7 + self._eq_bars[1] * 0.3)
            target_energy = (avg_eq * 0.45 + bass_kick * 0.55)
            self._ambient_beat_energy += (target_energy - self._ambient_beat_energy) * 0.28
            self._ambient_hue = (self._ambient_hue + 0.5) % 360.0

            style = self._ambient_style
            if style == "aurora_borealis":
                # Aurora Borealis: Emerald Green (#10b981) + Deep Cosmic Violet (#8b5cf6) with harmonic wave phase
                wave = (math.sin(self._anim_time * 1.5) + 1.0) * 0.5
                target_pri = QColor(16, int(185 + 40 * wave), int(129 + 60 * wave))
                target_sec = QColor(int(139 + 30 * (1.0 - wave)), 92, int(246 - 20 * wave))
            elif style == "neon_cyber_pulse":
                # Cyberpunk Neon: Electric Cyan (#00f0ff) + Synth Laser Magenta (#ff0080) with beat strobe
                strobe = 1.0 + (0.25 if self._ambient_beat_energy > 0.6 else 0.0)
                target_pri = QColor(0, min(255, int(240 * strobe)), 255)
                target_sec = QColor(255, 0, min(255, int(128 * strobe)))
            elif style == "sunset_chroma":
                # Synthwave Sunset: Solar Amber Gold (#f59e0b) + Deep Sunset Rose (#e11d48)
                pulse = (math.sin(self._anim_time * 2.0) + 1.0) * 0.5
                target_pri = QColor(245, int(158 + 25 * pulse), 11)
                target_sec = QColor(225, 29, int(72 + 30 * pulse))
            elif style == "lava_fire_glow":
                # Inferno Magma: Blazing Crimson (#ef4444) + Molten Orange (#f97316) with bass flare
                surge = int(45 * self._ambient_beat_energy)
                target_pri = QColor(min(255, 239 + surge), min(255, 68 + surge * 2), 68)
                target_sec = QColor(249, min(255, 115 + surge * 2), 22)
            elif style == "rainbow_flow":
                # RGB Chroma Spectrum: Continuous 360-degree rotating prism
                h1 = (self._anim_time * 0.15) % 1.0
                h2 = (h1 + 0.28) % 1.0
                target_pri = QColor.fromHsvF(h1, 0.90, 0.98)
                target_sec = QColor.fromHsvF(h2, 0.85, 0.95)
            elif style == "minimal_frost":
                # Apple Minimal Frost: Diamond Crisp White + Glacial Ice Blue (#93c5fd)
                shimmer = int(15 * math.sin(self._anim_time * 2.5))
                target_pri = QColor(255, 255, 255)
                target_sec = QColor(min(255, 147 + shimmer), min(255, 197 + shimmer), 253)
            else:
                # adaptive_album (default)
                if self._extracted_art_color:
                    target_pri = self._extracted_art_color
                    h = (target_pri.hsvHueF() + 0.18) % 1.0
                    target_sec = QColor.fromHsvF(h if h >= 0 else 0.5, min(1.0, target_pri.hsvSaturationF() + 0.1), max(0.6, target_pri.valueF()))
                else:
                    target_pri = QColor.fromHsvF(self._ambient_hue / 360.0, 0.85, 0.95)
                    target_sec = QColor.fromHsvF(((self._ambient_hue + 60.0) % 360.0) / 360.0, 0.80, 0.90)
        else:
            self._ambient_beat_energy += (0.0 - self._ambient_beat_energy) * 0.08
            style = self._ambient_style
            if style == "aurora_borealis":
                target_pri = QColor(16, 185, 129)
                target_sec = QColor(139, 92, 246)
            elif style == "neon_cyber_pulse":
                target_pri = QColor(0, 240, 255)
                target_sec = QColor(255, 0, 128)
            elif style == "sunset_chroma":
                target_pri = QColor(245, 158, 11)
                target_sec = QColor(225, 29, 72)
            elif style == "lava_fire_glow":
                target_pri = QColor(239, 68, 68)
                target_sec = QColor(249, 115, 22)
            elif style == "rainbow_flow":
                h1 = (self._anim_time * 0.08) % 1.0
                target_pri = QColor.fromHsvF(h1, 0.75, 0.85)
                target_sec = QColor.fromHsvF((h1 + 0.3) % 1.0, 0.75, 0.85)
            elif style == "minimal_frost":
                target_pri = QColor(240, 245, 255)
                target_sec = QColor(147, 197, 253)
            else:
                target_pri = QColor(0, 122, 255)
                target_sec = QColor(168, 85, 247)

        # Smooth ambient light color morphing
        c1, c2 = self._ambient_color_current, self._ambient_color_secondary
        r1 = int(c1.red() + (target_pri.red() - c1.red()) * 0.12)
        g1 = int(c1.green() + (target_pri.green() - c1.green()) * 0.12)
        b1 = int(c1.blue() + (target_pri.blue() - c1.blue()) * 0.12)
        self._ambient_color_current = QColor(r1, g1, b1)

        r2 = int(c2.red() + (target_sec.red() - c2.red()) * 0.12)
        g2 = int(c2.green() + (target_sec.green() - c2.green()) * 0.12)
        b2 = int(c2.blue() + (target_sec.blue() - c2.blue()) * 0.12)
        self._ambient_color_secondary = QColor(r2, g2, b2)

        # Lava Magma Embers update (only when style is active and expanded)
        if self._ambient_style == "lava_fire_glow" and self._state != self.STATE_COMPACT:
            speed_mult = 1.0 + self._ambient_beat_energy * 2.2
            for ember in self._lava_embers:
                ember["y"] -= ember["speed"] * speed_mult
                ember["x"] += math.sin(self._anim_time * 2.5 + ember["speed"]) * 0.6
                if ember["y"] <= 10:
                    ember["y"] = random.uniform(self._current_h - 15, self._current_h + 10)
                    ember["x"] = random.uniform(10, max(20, self._current_w - 10))

        # 4. Weather Physics Particles Updates (only when weather state is visible)
        if self._state == self.STATE_WEATHER:
            # Rain Drops & Splashes
            for d in self._rain_drops:
                d["y"] += d["speed"]
                d["x"] += 1.2
                if d["y"] >= 104:
                    if len(self._rain_splashes) < 16 and random.random() < 0.4:
                        self._rain_splashes.append({"x": d["x"], "y": 104, "r": 1.0, "alpha": 0.85})
                    d["y"] = random.uniform(-15, 0)
                    d["x"] = random.uniform(0, 150)

            surviving_splashes = []
            for s in self._rain_splashes:
                s["r"] += 0.45
                s["alpha"] -= 0.075
                if s["alpha"] > 0.05 and s["r"] < 7.5:
                    surviving_splashes.append(s)
            self._rain_splashes = surviving_splashes

            # Snowflakes
            for f in self._snow_flakes:
                f["y"] += f["speed"]
                f["x"] += math.sin(f["phase"] + self._anim_time * 1.5) * 0.65
                if f["y"] >= 108:
                    f["y"] = random.uniform(-12, 0)
                    f["x"] = random.uniform(0, 150)

            # Wind Particles
            for p_w in self._wind_particles:
                p_w["x"] += p_w["speed"]
                p_w["y"] += math.sin(self._anim_time * 3.0 + p_w["x"] * 0.05) * 0.35
                if p_w["x"] >= 155:
                    p_w["x"] = random.uniform(-20, 0)
                    p_w["y"] = random.uniform(10, 98)

            # Heat Embers
            for e in self._heat_embers:
                e["y"] -= e["speed"]
                e["x"] += math.sin(e["phase"] + self._anim_time * 2.0) * 0.55
                if e["y"] <= 10:
                    e["y"] = random.uniform(95, 108)
                    e["x"] = random.uniform(10, 140)

            # Cloud Drift Layers
            for i in range(len(self._cloud_drift)):
                self._cloud_drift[i] += (0.18 + i * 0.14)
                if self._cloud_drift[i] >= 195.0:
                    self._cloud_drift[i] = -65.0

            # Thunder Lightning Generator
            self._lightning_timer += 1
            if self._lightning_flash > 0:
                self._lightning_flash = max(0.0, self._lightning_flash - 0.10)
            if self._lightning_timer > 80 and random.random() < 0.05:
                self._lightning_timer = 0
                self._lightning_flash = 1.0
                lx, ly = random.uniform(35, 75), 32
                pts = [(lx, ly)]
                for _ in range(5):
                    lx += random.uniform(-10, 10)
                    ly += random.uniform(12, 16)
                    pts.append((lx, ly))
                self._lightning_bolt_pts = pts

        # 5. Compass Heading & Route Simulation (only when map state is visible)
        if self._state == self.STATE_MAP:
            if self._compass_mode == "drift":
                self._compass_heading = (self._compass_heading + 0.35 + math.sin(self._anim_time * 0.8) * 0.25) % 360.0
            elif self._compass_mode == "mouse":
                cursor_pos = QCursor.pos() - self.pos()
                dx = cursor_pos.x() - 86
                dy = cursor_pos.y() - 74
                target_ang = (math.degrees(math.atan2(dx, -dy)) + 360.0) % 360.0
                self._compass_heading = target_ang
            elif self._compass_mode == "north":
                self._compass_heading = 0.0

            diff = (self._compass_heading - self._compass_current_heading + 180.0) % 360.0 - 180.0
            self._compass_current_heading = (self._compass_current_heading + diff * 0.14) % 360.0
            self._nav_progress = (self._nav_progress + self._nav_speed) % 1.0

        # Ticker text scroll
        if self._state != self.STATE_COMPACT:
            self._ticker_offset = (self._ticker_offset + 1) % 1000

        # System metrics sampling (every 3s when tools or expanded)
        now = time.monotonic()
        if HAS_PSUTIL and (self._state == self.STATE_TOOLS or self._state != self.STATE_COMPACT) and (now - self._last_sys_check_time > 3.0):
            self._last_sys_check_time = now
            try:
                self._last_cpu_percent = psutil.cpu_percent(interval=None)
                self._last_ram_percent = psutil.virtual_memory().percent
            except Exception:
                pass

        # Smooth metric interpolation
        self._anim_cpu += (self._last_cpu_percent - self._anim_cpu) * min(1.0, dt * 5.0)
        self._anim_ram += (self._last_ram_percent - self._anim_ram) * min(1.0, dt * 5.0)

        # Smooth continuous marquee scrolling for compact & expanded modes
        self._compact_ticker_x += dt * 38.0
        self._music_ticker_x += dt * 32.0

        # Maintain 60 FPS update rate (16ms)
        if self._timer.interval() != 16:
            self._timer.setInterval(16)
        if not self._timer.isActive():
            self._timer.start(16)

        self.update()

    def _wake_timer(self):
        if self._timer.interval() != 16:
            self._timer.setInterval(16)
        if not self._timer.isActive():
            self._timer.start(16)
        self._last_tick_time = time.monotonic()
        self.update()

    def _update_tab_indicator_target(self, tab_name: str, snap: bool = False):
        w = max(self.SIZES[self.STATE_MUSIC][0], int(self._target_w))
        tab_positions = {
            "music": w - 138 - 6,
            "weather": w - 110 - 6,
            "map": w - 82 - 6,
            "clipboard": w - 54 - 6,
            "tools": w - 26 - 6,
        }
        target_x = float(tab_positions.get(tab_name, w - 138 - 6))
        self._indicator_target_x = target_x
        if snap:
            self._indicator_x = target_x
            self._indicator_vel = 0.0
            self._indicator_w = 22.0
            self._indicator_w_vel = 0.0

    def switch_state(self, new_state: str):
        if new_state in self.SIZES:
            self._wake_timer()
            if new_state != self.STATE_COMPACT:
                self._last_expanded_tab = new_state

            if new_state == self._state and not self._is_morphing:
                return

            old_state = self._state
            self._prev_state = old_state
            self._state = new_state
            tw, th = self.SIZES[new_state]
            self._target_w = float(tw)
            self._target_h = float(th)

            # If switching between expanded tabs: trigger fluid sliding indicator & cross-fade
            if old_state != self.STATE_COMPACT and new_state != self.STATE_COMPACT:
                self._tab_from = old_state
                self._tab_to = new_state
                self._tab_transition_progress = 0.0
                self._update_tab_indicator_target(new_state)
            elif new_state != self.STATE_COMPACT and old_state == self.STATE_COMPACT:
                # Expanding from compact pill
                self._tab_from = new_state
                self._tab_to = new_state
                self._tab_transition_progress = 1.0
                self._update_tab_indicator_target(new_state, snap=True)

            self._is_morphing = True
            self.update()

    def expand_to_state(self, state_id: int):
        mapping = {
            0: self.STATE_COMPACT,
            1: self.STATE_MUSIC,
            2: self.STATE_WEATHER,
            3: self.STATE_MAP,
            4: self.STATE_CLIPBOARD,
            5: self.STATE_TOOLS,
        }
        self.switch_state(mapping.get(state_id, self.STATE_COMPACT))

    def _auto_collapse(self):
        cursor_global = QCursor.pos()
        if self.geometry().contains(cursor_global):
            self._is_hovered = True
            return
        self._is_hovered = False
        if self._state != self.STATE_COMPACT:
            self._last_expanded_tab = self._state
            self.switch_state(self.STATE_COMPACT)

    def _open_google_maps(self, query: Optional[str] = None, mode: str = "search"):
        """Launches Google Maps centered on the location directly in Brave Browser or default browser."""
        if not query:
            if self._weather and self._weather.current_weather and self._weather.current_weather.city:
                query = self._weather.current_weather.city
            elif self._settings and hasattr(self._settings, "weather_location") and self._settings.weather_location:
                query = self._settings.weather_location
            else:
                query = "Kochi, Kerala, India"

        clean_q = query.strip()
        encoded = urllib.parse.quote(clean_q)

        if mode == "directions":
            url = f"https://www.google.com/maps/dir/?api=1&destination={encoded}"
        elif mode == "satellite":
            url = f"https://www.google.com/maps/search/{encoded}/@?data=!3m1!1e3"
        elif mode == "traffic":
            url = f"https://www.google.com/maps/search/{encoded}/@?layer=t"
        else:
            url = f"https://www.google.com/maps/search/?api=1&query={encoded}"

        self._open_url_in_brave_or_default(url)

    def _open_chatgpt(self):
        """Launches ChatGPT directly in user's logged-in Brave Browser or default browser."""
        import os
        brave_paths = [
            r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe",
            r"C:\Program Files (x86)\BraveSoftware\Brave-Browser\Application\brave.exe",
            os.path.expandvars(r"%LOCALAPPDATA%\BraveSoftware\Brave-Browser\Application\brave.exe"),
        ]
        for p in brave_paths:
            if os.path.exists(p):
                try:
                    subprocess.Popen([p, "https://chatgpt.com"])
                    return
                except Exception:
                    pass
        try:
            QDesktopServices.openUrl(QUrl("https://chatgpt.com"))
        except Exception:
            webbrowser.open("https://chatgpt.com")

    def _trigger_volume_hud(self, action: str):
        self._volume_hud_time = time.monotonic()
        self._volume_hud_action = action
        if action == "+":
            self._volume_hud_level = min(100, self._volume_hud_level + 4)
        elif action == "-":
            self._volume_hud_level = max(0, self._volume_hud_level - 4)
        self.update()

    # ── Clipboard Monitor & URL Detection ───────────────────────────────────

    def _check_initial_clipboard(self):
        try:
            text = self._clipboard.text()
            if text:
                self._process_clipboard_text(text, notify=False)
        except Exception:
            pass

    def _on_clipboard_changed(self):
        try:
            now = time.monotonic()
            if now - self._last_clipboard_change_time < 0.08:
                return
            self._last_clipboard_change_time = now
            text = self._clipboard.text()
            if text and text != self._last_clipboard_text:
                self._process_clipboard_text(text, notify=True)
        except Exception:
            pass

    def _process_clipboard_text(self, text: str, notify: bool = True):
        self._last_clipboard_text = text
        self._clipboard_char_count = len(text)

        # Fast preview slice (max 300 chars for drawing)
        self._clipboard_preview_text = text[:300]
        preview = text[:2000]

        # Fast non-blocking word count calculation
        if len(text) > 10000:
            self._clipboard_word_count = len(text[:10000].split())
        else:
            self._clipboard_word_count = len(text.split())

        clean = text[:500].strip()

        # 1. History Reel (stored as clean lightweight strings)
        if clean:
            if clean in self._clipboard_history:
                self._clipboard_history.remove(clean)
            self._clipboard_history.insert(0, clean)
            if len(self._clipboard_history) > 5:
                self._clipboard_history = self._clipboard_history[:5]

        # 2. Check for URL / Link (search on first 1500 chars)
        url_match = re.search(r"(https?://[^\s]+|www\.[^\s]+)", preview, re.IGNORECASE)
        if url_match:
            url = url_match.group(0)
            if not url.startswith("http"):
                url = "https://" + url
            self._last_clipboard_url = url
        else:
            self._last_clipboard_url = None

        # 3. Check for Hex Color Code (#RGB, #RRGGBB, #RRGGBBAA on short text)
        if len(clean) <= 12:
            hex_match = re.match(r"^#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6}|[0-9a-fA-F]{8})$", clean)
            if hex_match:
                self._clipboard_color_hex = hex_match.group(0)
            else:
                self._clipboard_color_hex = None
        else:
            self._clipboard_color_hex = None

        # 4. Check for Math Calculation Expression (only on clean short text < 80 chars)
        if len(clean) <= 80:
            clean_math = re.sub(r"[^0-9\.\+\-\*\/\(\)\%\s]", "", clean)
            if clean_math and any(op in clean_math for op in ["+", "-", "*", "/", "%"]) and len(clean_math) >= 3:
                try:
                    res = eval(clean_math, {"__builtins__": None}, {})
                    if isinstance(res, (int, float)):
                        self._clipboard_calc_result = f"{res:.4g}" if isinstance(res, float) else str(res)
                    else:
                        self._clipboard_calc_result = None
                except Exception:
                    self._clipboard_calc_result = None
            else:
                self._clipboard_calc_result = None
        else:
            self._clipboard_calc_result = None

        if notify:
            self._clipboard_banner_time = time.monotonic()
            self.switch_state(self.STATE_CLIPBOARD)
            self._collapse_timer.start(7000)

    def _open_last_url(self):
        if self._last_clipboard_url:
            self._open_url_in_brave_or_default(self._last_clipboard_url)

    def _open_url_in_brave_or_default(self, url: str):
        import os
        brave_paths = [
            r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe",
            r"C:\Program Files (x86)\BraveSoftware\Brave-Browser\Application\brave.exe",
            os.path.expandvars(r"%LOCALAPPDATA%\BraveSoftware\Brave-Browser\Application\brave.exe"),
        ]
        for p in brave_paths:
            if os.path.exists(p):
                try:
                    subprocess.Popen([p, url])
                    return
                except Exception:
                    pass
        try:
            QDesktopServices.openUrl(QUrl(url))
        except Exception:
            webbrowser.open(url)

    def _search_google(self):
        if self._last_clipboard_text:
            query = urllib.parse.quote(self._last_clipboard_text[:120])
            url = f"https://www.google.com/search?q={query}"
            self._open_url_in_brave_or_default(url)

    def _ask_chatgpt_with_clipboard(self):
        if self._last_clipboard_text:
            query = urllib.parse.quote(self._last_clipboard_text[:200])
            url = f"https://chatgpt.com/?q={query}"
            self._open_url_in_brave_or_default(url)
        else:
            self._open_chatgpt()

    def _copy_again(self):
        if self._last_clipboard_text:
            self._clipboard.setText(self._last_clipboard_text)
            self._clipboard_copy_feedback = time.monotonic()
            self.update()

    def _copy_calc_result(self):
        if self._clipboard_calc_result:
            self._clipboard.setText(self._clipboard_calc_result)
            self._last_clipboard_text = self._clipboard_calc_result
            self._clipboard_copy_feedback = time.monotonic()
            self.update()

    def _toggle_case(self):
        if not self._last_clipboard_text or len(self._last_clipboard_text) > 50000:
            return
        t = self._last_clipboard_text
        if t.isupper():
            new_t = t.lower()
        elif t.islower():
            new_t = t.title()
        else:
            new_t = t.upper()
        self._last_clipboard_text = new_t
        self._clipboard.setText(new_t)
        self._clipboard_copy_feedback = time.monotonic()
        self.update()

    def _clear_clipboard(self):
        try:
            self._clipboard.clear()
        except Exception:
            pass
        self._last_clipboard_text = ""
        self._clipboard_preview_text = ""
        self._clipboard_word_count = 0
        self._clipboard_char_count = 0
        self._last_clipboard_url = None
        self._clipboard_calc_result = None
        self._clipboard_color_hex = None
        self.update()

    def _restore_clip_history(self, idx: int):
        if 0 <= idx < len(self._clipboard_history):
            text = self._clipboard_history[idx]
            self._last_clipboard_text = text
            self._clipboard.setText(text)
            self._process_clipboard_text(text, notify=False)
            self._clipboard_copy_feedback = time.monotonic()
            self.update()

    # ── Media Events & Ambient Color Extraction ──────────────────────────────

    def _extract_artwork_color(self, thumb_bytes: bytes) -> Optional[QColor]:
        """Fast sampling to extract dominant vibrant accent color from album artwork."""
        try:
            pix = QPixmap()
            if not pix.loadFromData(thumb_bytes):
                return None
            img = pix.toImage().scaled(16, 16, Qt.AspectRatioMode.IgnoreAspectRatio, Qt.TransformationMode.FastTransformation)
            r_tot, g_tot, b_tot, count = 0, 0, 0, 0
            max_sat = 0.0
            best_col = None
            for y in range(img.height()):
                for x in range(img.width()):
                    c = img.pixelColor(x, y)
                    # Filter out near-black or washed-out white
                    if 35 < c.value() < 240 and c.hsvSaturationF() > 0.15:
                        sat = c.hsvSaturationF()
                        if sat > max_sat:
                            max_sat = sat
                            best_col = c
                        r_tot += c.red()
                        g_tot += c.green()
                        b_tot += c.blue()
                        count += 1
            if best_col:
                return best_col
            elif count > 0:
                return QColor(r_tot // count, g_tot // count, b_tot // count)
        except Exception:
            pass
        return None

    def _on_media_updated(self, info: MediaInfo):
        self._last_media_info = info
        if info.duration_sec > 0:
            self._playback_dur_sec = info.duration_sec
        if not self._is_scrubbing and info.position_sec >= 0:
            self._playback_pos_sec = info.position_sec
        if info.thumbnail_bytes and len(info.thumbnail_bytes) != self._last_thumb_len:
            self._last_thumb_len = len(info.thumbnail_bytes)
            self._extracted_art_color = self._extract_artwork_color(info.thumbnail_bytes)
        elif not info.thumbnail_bytes:
            self._last_thumb_len = 0
            self._extracted_art_color = None
        if info.title:
            if not self._is_hovered and self._state == self.STATE_COMPACT:
                # Brief pulse to music mode on song change
                self.switch_state(self.STATE_MUSIC)
                self._collapse_timer.start(5000)
        self.update()

    def _on_playback_changed(self, is_playing: bool):
        if self._last_media_info:
            self._last_media_info.is_playing = is_playing
        self.update()

    def _on_bluetooth_updated(self, info: BluetoothInfo):
        self._last_bluetooth_info = info
        self.update()

    # ── Mouse & Interaction ──────────────────────────────────────────────────

    def wheelEvent(self, event):
        delta = event.angleDelta().y()
        if delta > 0:
            self._media.volume_up()
            self._trigger_volume_hud("+")
        elif delta < 0:
            self._media.volume_down()
            self._trigger_volume_hud("-")
        event.accept()

    def _get_button_style(self, btn_name: str, base_bg: Optional[QColor] = None, base_border: Optional[QColor] = None):
        """Calculates dynamic tactile hover glow, micro-spring scale bounce, and press depression for any button."""
        h_val = self._btn_hover_anim.get(btn_name, 0.0)
        p_val = self._btn_press_anim.get(btn_name, 0.0)
        scale = (1.0 + 0.045 * h_val) * (1.0 - 0.08 * p_val)

        if base_bg is None:
            base_bg = QColor(255, 255, 255, 18)

        alpha = min(255, int(base_bg.alpha() + h_val * 60 - p_val * 20))
        r = min(255, int(base_bg.red() + h_val * 35))
        g = min(255, int(base_bg.green() + h_val * 35))
        b = min(255, int(base_bg.blue() + h_val * 35))
        bg_color = QColor(r, g, b, max(0, alpha))

        if base_border is None:
            border_alpha = int(25 + h_val * 85)
            border_color = QColor(255, 255, 255, border_alpha)
        else:
            border_alpha = min(255, int(base_border.alpha() + h_val * 65))
            border_color = QColor(base_border.red(), base_border.green(), base_border.blue(), border_alpha)

        return bg_color, border_color, scale, h_val, p_val

    def enterEvent(self, event):
        self._is_hovered = True
        self._wake_timer()
        self._collapse_timer.stop()
        # Open dynamically on mouse hover if compact!
        if self._state == self.STATE_COMPACT:
            target = getattr(self, '_last_expanded_tab', None)
            if not target:
                if self._last_media_info and self._last_media_info.has_media:
                    target = self.STATE_MUSIC
                else:
                    target = self.STATE_WEATHER
            self.switch_state(target)
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._is_hovered = False
        self._is_scrubbing = False
        # Gracefully collapse back to compact pill on mouse exit
        self._collapse_timer.start(550)
        super().leaveEvent(event)

    def _get_button_at(self, pos: QPoint) -> Optional[str]:
        w, h = self.width(), self.height()
        if self._state == self.STATE_COMPACT or h < 55:
            return "compact_pill"

        # Top-left subtle collapse indicator notch
        if pos.y() < 28 and pos.x() < 45:
            return "collapse"

        # 5 Tabs at top-right
        if pos.y() < 30:
            if w - 150 <= pos.x() <= w - 124:
                return "tab_music"
            elif w - 122 <= pos.x() <= w - 96:
                return "tab_weather"
            elif w - 94 <= pos.x() <= w - 68:
                return "tab_map"
            elif w - 66 <= pos.x() <= w - 40:
                return "tab_clipboard"
            elif w - 38 <= pos.x() <= w - 12:
                return "tab_tools"

        if self._state == self.STATE_MUSIC:
            if 12 <= pos.x() <= 78 and 26 <= pos.y() <= 90:
                return "album_art"
            ctrl_y = h - 44
            cx = w // 2
            if (pos.x() - (cx - 104)) ** 2 + (pos.y() - (ctrl_y + 16)) ** 2 <= 16 ** 2:
                return "vol_down"
            if (pos.x() - (cx - 52)) ** 2 + (pos.y() - (ctrl_y + 16)) ** 2 <= 18 ** 2:
                return "prev"
            if (pos.x() - cx) ** 2 + (pos.y() - (ctrl_y + 16)) ** 2 <= 22 ** 2:
                return "play"
            if (pos.x() - (cx + 52)) ** 2 + (pos.y() - (ctrl_y + 16)) ** 2 <= 18 ** 2:
                return "next"
            if (pos.x() - (cx + 104)) ** 2 + (pos.y() - (ctrl_y + 16)) ** 2 <= 16 ** 2:
                return "vol_up"
            if (pos.x() - (w - 36)) ** 2 + (pos.y() - (ctrl_y + 16)) ** 2 <= 16 ** 2:
                return "mute"
            if 84 <= pos.x() <= w - 14 and 70 <= pos.y() <= 92:
                return "scrub"

        elif self._state == self.STATE_WEATHER:
            if 16 <= pos.x() <= 166 and 76 <= pos.y() <= 136:
                return "weather_city"
            if h >= 120 and pos.x() >= w - 45 and pos.y() >= h - 35:
                return "collapse"

        elif self._state == self.STATE_MAP:
            if self._map_view_mode == "panoramic":
                if (w - 58) <= pos.x() <= (w - 26) and 28 <= pos.y() <= 58:
                    return "map_compass"
                if 104 <= pos.y() <= 136:
                    c_w = (w - 32 - 36) // 4
                    rx = 16
                    if rx <= pos.x() <= rx + c_w + 6:
                        return "map_chip_split"
                    elif rx + c_w + 6 <= pos.x() <= rx + (c_w + 6) * 2:
                        return "map_chip_traffic"
                    elif rx + (c_w + 6) * 2 <= pos.x() <= rx + (c_w + 6) * 3:
                        return "map_chip_reset"
                    elif rx + (c_w + 6) * 3 <= pos.x() <= w - 16:
                        return "map_chip_open"
                if 16 <= pos.x() <= w - 16 and 28 <= pos.y() <= 104:
                    return "map_body"
            else:
                if 16 <= pos.x() <= 156 and 28 <= pos.y() <= 136:
                    return "map_compass"
                if 104 <= pos.y() <= 136:
                    rw = w - 180
                    rx = 164
                    c_w = (rw - 28) // 4
                    if rx <= pos.x() <= rx + c_w + 5:
                        return "map_chip_panoramic"
                    elif rx + c_w + 5 <= pos.x() <= rx + (c_w + 5) * 2:
                        return "map_chip_traffic"
                    elif rx + (c_w + 5) * 2 <= pos.x() <= rx + (c_w + 5) * 3:
                        return "map_chip_reset"
                    elif rx + (c_w + 5) * 3 <= pos.x() <= w - 16:
                        return "map_chip_open"
                if 164 <= pos.x() <= w - 16 and 28 <= pos.y() <= 104:
                    return "map_body"

        elif self._state == self.STATE_CLIPBOARD:
            if 28 <= pos.y() <= 46:
                hx = 16
                for idx in range(min(4, len(self._clipboard_history))):
                    chip_w = 84
                    if hx <= pos.x() <= hx + chip_w:
                        return f"clip_hist_{idx}"
                    hx += chip_w + 6
            if 106 <= pos.y() <= 144:
                if 16 <= pos.x() <= 82:
                    return "clip_act_link"
                elif 89 <= pos.x() <= 155:
                    return "clip_act_gpt"
                elif 162 <= pos.x() <= 228:
                    return "clip_act_case"
                elif 235 <= pos.x() <= 301:
                    return "clip_act_copy"
                elif 308 <= pos.x() <= 374:
                    return "clip_act_clear"

        elif self._state == self.STATE_TOOLS:
            if 16 <= pos.x() <= w - 16 and 76 <= pos.y() <= 108:
                return "tool_bluetooth"
            btn_y = h - 38
            if btn_y <= pos.y() <= btn_y + 30:
                if 16 <= pos.x() <= 64:
                    return "tool_snip"
                elif 68 <= pos.x() <= 116:
                    return "tool_maps"
                elif 120 <= pos.x() <= 168:
                    return "tool_calc"
                elif 172 <= pos.x() <= 220:
                    return "tool_notes"
                elif 224 <= pos.x() <= 272:
                    return "tool_gpt"
                elif 276 <= pos.x() <= 324:
                    return "tool_mute"
                elif 328 <= pos.x() <= 376:
                    return "tool_lock"

        return None

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            pos = event.position().toPoint()
            w, h = self.width(), self.height()

            # Tactile click spring feedback
            btn = self._get_button_at(pos)
            if btn:
                self._btn_press_anim[btn] = 1.0
                self._wake_timer()
                self.update()

            # 1. Interactive Progress Bar Scrubbing in Music Mode
            if self._state == self.STATE_MUSIC and 84 <= pos.x() <= w - 14 and 70 <= pos.y() <= 92:
                self._is_scrubbing = True
                ratio = min(1.0, max(0.0, (pos.x() - 88) / max(1.0, (w - 106))))
                self._playback_pos_sec = ratio * self._playback_dur_sec
                self.update()
                return

            # 2. Record drag start coordinates
            self._drag_start_pos = event.globalPosition().toPoint()
            self._drag_window_pos = self.pos()
            self._has_dragged = False
            self._press_pos = pos

        elif event.button() == Qt.MouseButton.RightButton:
            # Cycle through modes: compact -> music -> weather -> map -> clipboard -> tools -> compact
            states = [self.STATE_COMPACT, self.STATE_MUSIC, self.STATE_WEATHER, self.STATE_MAP, self.STATE_CLIPBOARD, self.STATE_TOOLS]
            try:
                cur_idx = states.index(self._state)
                next_state = states[(cur_idx + 1) % len(states)]
            except ValueError:
                next_state = self.STATE_COMPACT
            self.switch_state(next_state)

    def mouseMoveEvent(self, event):
        self._is_hovered = True
        self._collapse_timer.stop()
        self._wake_timer()

        w = self.width()
        pos = event.position().toPoint()

        # If compact mode and mouse is moving over it, expand!
        if self._state == self.STATE_COMPACT:
            target = getattr(self, '_last_expanded_tab', None)
            if not target:
                if self._last_media_info and self._last_media_info.has_media:
                    target = self.STATE_MUSIC
                else:
                    target = self.STATE_WEATHER
            self.switch_state(target)
            return

        hovered = self._get_button_at(pos)
        if hovered != self._hovered_btn:
            self._hovered_btn = hovered
            if hovered and hovered not in self._btn_hover_anim:
                self._btn_hover_anim[hovered] = 0.0
            self.update()

        if hovered is not None:
            self.setCursor(Qt.CursorShape.PointingHandCursor)
        else:
            self.setCursor(Qt.CursorShape.ArrowCursor)

        if self._is_scrubbing:
            pos_x = event.position().x()
            ratio = min(1.0, max(0.0, (pos_x - 88) / max(1.0, (w - 106))))
            self._playback_pos_sec = ratio * self._playback_dur_sec
            self.update()
            return

        if event.buttons() & Qt.MouseButton.LeftButton and hasattr(self, '_drag_start_pos'):
            delta = event.globalPosition().toPoint() - self._drag_start_pos
            if delta.manhattanLength() > 4:
                self._has_dragged = True
                self._is_dragging = True
                self._is_snapping_to_notch = False
                self._position_mode = "floating"
                self.move(self._drag_window_pos + delta)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            if self._is_scrubbing:
                self._is_scrubbing = False
                self._media.seek_to(self._playback_pos_sec)
                return

            if getattr(self, '_has_dragged', False):
                self._is_dragging = False
                self._has_dragged = False
                # Magnetic snap to top notch if dropped near top-center
                screen = QGuiApplication.primaryScreen()
                if screen:
                    geo = screen.geometry()
                    center_x = geo.x() + (geo.width() - self.width()) // 2
                    if abs(self.x() - center_x) < 80 and self.y() < 55:
                        self._is_snapping_to_notch = True
                        self._snap_target_x = float(center_x)
                        self._snap_target_y = float(geo.y() + 10)
                        self._snap_vel_x = 0.0
                        self._snap_vel_y = 0.0
                        self._wake_timer()
                    else:
                        if self._settings:
                            self._settings.island_position = "floating"
                            self._settings.save()
                return

            self._is_dragging = False
            self._has_dragged = False
            pos = getattr(self, '_press_pos', event.position().toPoint())

            # 1. Click in compact mode -> expand!
            if self._state == self.STATE_COMPACT:
                target = getattr(self, '_last_expanded_tab', None)
                if not target:
                    if self._last_media_info and self._last_media_info.has_media:
                        target = self.STATE_MUSIC
                    else:
                        target = self.STATE_WEATHER
                self.switch_state(target)
                return

            # 2. Check button click areas in expanded modes
            if self._state != self.STATE_COMPACT:
                handled = self._handle_click(pos)
                if not handled:
                    # User clicked on background/header -> close back to compact!
                    self._last_expanded_tab = self._state
                    self.switch_state(self.STATE_COMPACT)

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            if self._state == self.STATE_COMPACT:
                target = getattr(self, '_last_expanded_tab', None) or (self.STATE_MUSIC if (self._last_media_info and self._last_media_info.has_media) else self.STATE_WEATHER)
                self.switch_state(target)
            else:
                self._last_expanded_tab = self._state
                self.switch_state(self.STATE_COMPACT)

    def _handle_click(self, pos: QPoint) -> bool:
        w, h = self.width(), self.height()

        # Top-left subtle collapse indicator (x < 45, y < 28)
        if pos.y() < 28 and pos.x() < 45:
            self._last_expanded_tab = self._state
            self.switch_state(self.STATE_COMPACT)
            return True

        # 5-Tab switcher at top right in expanded mode
        if self._state != self.STATE_COMPACT and pos.y() < 30:
            if w - 150 <= pos.x() <= w - 124:
                if self._state == self.STATE_MUSIC:
                    self._last_expanded_tab = self.STATE_MUSIC
                    self.switch_state(self.STATE_COMPACT)
                else:
                    self.switch_state(self.STATE_MUSIC)
                return True
            elif w - 122 <= pos.x() <= w - 96:
                if self._state == self.STATE_WEATHER:
                    self._last_expanded_tab = self.STATE_WEATHER
                    self.switch_state(self.STATE_COMPACT)
                else:
                    self.switch_state(self.STATE_WEATHER)
                return True
            elif w - 94 <= pos.x() <= w - 68:
                if self._state == self.STATE_MAP:
                    self._last_expanded_tab = self.STATE_MAP
                    self.switch_state(self.STATE_COMPACT)
                else:
                    self.switch_state(self.STATE_MAP)
                return True
            elif w - 66 <= pos.x() <= w - 40:
                if self._state == self.STATE_CLIPBOARD:
                    self._last_expanded_tab = self.STATE_CLIPBOARD
                    self.switch_state(self.STATE_COMPACT)
                else:
                    self.switch_state(self.STATE_CLIPBOARD)
                return True
            elif w - 38 <= pos.x() <= w - 12:
                if self._state == self.STATE_TOOLS:
                    self._last_expanded_tab = self.STATE_TOOLS
                    self.switch_state(self.STATE_COMPACT)
                else:
                    self.switch_state(self.STATE_TOOLS)
                return True

        if self._state == self.STATE_MUSIC:
            # 0. Click Album Art / Ambient Halo on Left (x: 12 to 78, y: 26 to 90) to cycle Ambient Light Effect!
            if 12 <= pos.x() <= 78 and 26 <= pos.y() <= 90:
                self._cycle_ambient_style()
                return True

            ctrl_y = h - 44
            cx = w // 2

            # Vol Down [-] (cx - 104)
            if (pos.x() - (cx - 104)) ** 2 + (pos.y() - (ctrl_y + 16)) ** 2 <= 16 ** 2:
                self._media.volume_down()
                self._trigger_volume_hud("-")
                return True

            # Prev Button (cx - 52)
            if (pos.x() - (cx - 52)) ** 2 + (pos.y() - (ctrl_y + 16)) ** 2 <= 16 ** 2:
                self._media.previous_track()
                return True

            # Play / Pause button (Center cx)
            if (pos.x() - cx) ** 2 + (pos.y() - (ctrl_y + 16)) ** 2 <= 20 ** 2:
                self._media.play_pause()
                return True

            # Next Button (cx + 52)
            if (pos.x() - (cx + 52)) ** 2 + (pos.y() - (ctrl_y + 16)) ** 2 <= 16 ** 2:
                self._media.next_track()
                return True

            # Vol Up [+] (cx + 104)
            if (pos.x() - (cx + 104)) ** 2 + (pos.y() - (ctrl_y + 16)) ** 2 <= 16 ** 2:
                self._media.volume_up()
                self._trigger_volume_hud("+")
                return True

            # Mute Button (w - 36)
            if (pos.x() - (w - 36)) ** 2 + (pos.y() - (ctrl_y + 16)) ** 2 <= 16 ** 2:
                self._media.volume_mute()
                self._trigger_volume_hud("mute")
                return True

        elif self._state == self.STATE_WEATHER:
            # Click City / Location on Hero Card to switch to Maps tab
            if 16 <= pos.x() <= 166 and 76 <= pos.y() <= 136:
                self.switch_state(self.STATE_MAP)
                return True
            # Quick collapse button on bottom right corner only
            if h >= 120 and pos.x() >= w - 45 and pos.y() >= h - 35:
                self._pinned = False
                self.switch_state(self.STATE_COMPACT)
                return True

        elif self._state == self.STATE_MAP:
            if self._map_view_mode == "panoramic":
                # Panoramic Mode Clicks
                # 1. Mini Top-Right Compass Dial (w - 58 to w - 26, y: 28 to 58)
                if (w - 58) <= pos.x() <= (w - 26) and 28 <= pos.y() <= 58:
                    modes = ["drift", "mouse", "north"]
                    try:
                        cur_idx = modes.index(self._compass_mode)
                        self._compass_mode = modes[(cur_idx + 1) % len(modes)]
                    except ValueError:
                        self._compass_mode = "drift"
                    mode_labels = {
                        "drift": "Compass: Live Gyro Drift 🧭",
                        "mouse": "Compass: Track Mouse Cursor 🎯",
                        "north": "Compass: Locked True North 📍"
                    }
                    self._ambient_toast_time = time.monotonic()
                    self._ambient_toast_name = mode_labels.get(self._compass_mode, "Compass")
                    self.update()
                    return True

                # 2. Bottom 4 Action Chips in Panoramic Mode (y: 104 to 136)
                if 104 <= pos.y() <= 136:
                    c_w = (w - 32 - 36) // 4
                    rx = 16
                    # B1: ⤡ Split View
                    if rx <= pos.x() <= rx + c_w + 6:
                        self._map_view_mode = "split"
                        self._ambient_toast_time = time.monotonic()
                        self._ambient_toast_name = "Layout: Split View (Compass + Map) 🧭🗺️"
                        self.update()
                        return True
                    # B2: 🚦 Traffic Toggle
                    if rx + c_w + 6 <= pos.x() <= rx + (c_w + 6) * 2:
                        self._traffic_enabled = not self._traffic_enabled
                        self._ambient_toast_time = time.monotonic()
                        self._ambient_toast_name = "Live Traffic: ON 🚦" if self._traffic_enabled else "Live Traffic: OFF ⚪"
                        self.update()
                        return True
                    # B3: ⚡ Route Simulation Restart
                    if rx + (c_w + 6) * 2 <= pos.x() <= rx + (c_w + 6) * 3:
                        self._nav_progress = 0.0
                        self._ambient_toast_time = time.monotonic()
                        self._ambient_toast_name = "Route: Reset to Origin 📍"
                        self.update()
                        return True
                    # B4: 🌐 Open in Google Maps
                    if rx + (c_w + 6) * 3 <= pos.x() <= w - 16:
                        self._open_google_maps(mode="directions")
                        return True

                # 3. Click Canvas Body -> Open Google Maps
                if 16 <= pos.x() <= w - 16 and 28 <= pos.y() <= 104:
                    self._open_google_maps(mode="search")
                    return True

            else:
                # Split Mode Clicks
                # 1. Left Card (x: 16 to 156, y: 28 to 136)
                if 16 <= pos.x() <= 156 and 28 <= pos.y() <= 136:
                    if pos.y() >= 110:
                        # Bottom toggle text clicked: switch between Turn HUD & Compass
                        self._compass_left_view = "turn_hud" if self._compass_left_view == "compass" else "compass"
                        self._ambient_toast_time = time.monotonic()
                        self._ambient_toast_name = "Turn HUD Active ↱" if self._compass_left_view == "turn_hud" else "Compass Active 🧭"
                    else:
                        # Center Compass dial clicked: cycle compass mode
                        modes = ["drift", "mouse", "north"]
                        try:
                            cur_idx = modes.index(self._compass_mode)
                            self._compass_mode = modes[(cur_idx + 1) % len(modes)]
                        except ValueError:
                            self._compass_mode = "drift"
                        mode_labels = {
                            "drift": "Compass: Live Gyro Drift 🧭",
                            "mouse": "Compass: Track Mouse Cursor 🎯",
                            "north": "Compass: Locked True North 📍"
                        }
                        self._ambient_toast_time = time.monotonic()
                        self._ambient_toast_name = mode_labels.get(self._compass_mode, "Compass")
                    self.update()
                    return True

                # 2. Right Map Card Bottom 4 Action Chips (y: 104 to 136)
                if 104 <= pos.y() <= 136:
                    rw = w - 180
                    rx = 164
                    c_w = (rw - 28) // 4
                    # B1: ⤢ Full Panoramic View
                    if rx <= pos.x() <= rx + c_w + 5:
                        self._map_view_mode = "panoramic"
                        self._ambient_toast_time = time.monotonic()
                        self._ambient_toast_name = "Layout: Panoramic Ultra-Wide Map 🗺️"
                        self.update()
                        return True
                    # B2: 🚦 Traffic Toggle
                    if rx + c_w + 5 <= pos.x() <= rx + (c_w + 5) * 2:
                        self._traffic_enabled = not self._traffic_enabled
                        self._ambient_toast_time = time.monotonic()
                        self._ambient_toast_name = "Live Traffic: ON 🚦" if self._traffic_enabled else "Live Traffic: OFF ⚪"
                        self.update()
                        return True
                    # B3: ⚡ Route Simulation Restart
                    if rx + (c_w + 5) * 2 <= pos.x() <= rx + (c_w + 5) * 3:
                        self._nav_progress = 0.0
                        self._ambient_toast_time = time.monotonic()
                        self._ambient_toast_name = "Route: Reset to Origin 📍"
                        self.update()
                        return True
                    # B4: 🌐 Open in Google Maps
                    if rx + (c_w + 5) * 3 <= pos.x() <= w - 16:
                        self._open_google_maps(mode="directions")
                        return True

                # 3. Right Map Upper Body (x: 164 to w - 16, y: 28 to 104) -> Open Google Maps
                if 164 <= pos.x() <= w - 16 and 28 <= pos.y() <= 104:
                    self._open_google_maps(mode="search")
                    return True

        elif self._state == self.STATE_CLIPBOARD:
            # 1. History Reel Chips Click (y: 28 to 46)
            if 28 <= pos.y() <= 46:
                hx = 16
                for idx in range(min(4, len(self._clipboard_history))):
                    chip_w = 84
                    if hx <= pos.x() <= hx + chip_w:
                        self._restore_clip_history(idx)
                        return True
                    hx += chip_w + 6

            # 2. 5 Smart Action Buttons Click (y: 106 to 144)
            if 106 <= pos.y() <= 144:
                # B1 (16 to 82): Open Link / Copy Result / Search Google
                if 16 <= pos.x() <= 82:
                    if self._last_clipboard_url:
                        self._open_last_url()
                    elif self._clipboard_calc_result:
                        self._copy_calc_result()
                    else:
                        self._search_google()
                    return True

                # B2 (89 to 155): Ask GPT in Brave Browser
                if 89 <= pos.x() <= 155:
                    self._ask_chatgpt_with_clipboard()
                    return True

                # B3 (162 to 228): Search or Case Convert (UPPER/lower/Title)
                if 162 <= pos.x() <= 228:
                    if self._last_clipboard_url or self._clipboard_calc_result:
                        self._search_google()
                    else:
                        self._toggle_case()
                    return True

                # B4 (235 to 301): Copy Again
                if 235 <= pos.x() <= 301:
                    self._copy_again()
                    return True

                # B5 (308 to 374): Clear Clipboard
                if 308 <= pos.x() <= 374:
                    self._clear_clipboard()
                    return True

        elif self._state == self.STATE_TOOLS:
            # Click Bluetooth Card -> opens Windows Bluetooth settings
            if 16 <= pos.x() <= w - 16 and 76 <= pos.y() <= 108:
                try:
                    subprocess.Popen("explorer.exe ms-settings:bluetooth")
                except Exception:
                    pass
                return True

            # 7 Quick Desktop Tool Buttons on bottom row
            btn_y = h - 38
            if btn_y <= pos.y() <= btn_y + 30:
                # B1: Snip (x: 16 to 64)
                if 16 <= pos.x() <= 64:
                    try:
                        subprocess.Popen("explorer.exe ms-screenclip:")
                    except Exception:
                        try:
                            subprocess.Popen("SnippingTool.exe")
                        except Exception:
                            pass
                    return True
                # B2: Maps & Compass (x: 68 to 116)
                if 68 <= pos.x() <= 116:
                    self.switch_state(self.STATE_MAP)
                    return True
                # B3: Calc (x: 120 to 168)
                if 120 <= pos.x() <= 168:
                    try:
                        subprocess.Popen("calc.exe")
                    except Exception:
                        pass
                    return True
                # B4: Notes (x: 172 to 220)
                if 172 <= pos.x() <= 220:
                    try:
                        subprocess.Popen("notepad.exe")
                    except Exception:
                        pass
                    return True
                # B5: ChatGPT in Brave Browser (x: 224 to 272)
                if 224 <= pos.x() <= 272:
                    self._open_chatgpt()
                    return True
                # B6: Master Mute (x: 276 to 324)
                if 276 <= pos.x() <= 324:
                    self._media.volume_mute()
                    self._trigger_volume_hud("mute")
                    return True
                # B7: Lock PC (x: 328 to 376)
                if 328 <= pos.x() <= 376:
                    try:
                        ctypes.windll.user32.LockWorkStation()
                    except Exception:
                        pass
                    return True

        return False

    # ── Vector Icon Drawing Helpers (Apple SF Symbols Geometric Line Style) ───

    def _draw_vector_play_circle(self, p: QPainter, cx: int, cy: int, r: int = 10, is_playing: bool = False, color: QColor = QColor(255, 255, 255)):
        p.save()
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        pen = QPen(color, 1.5)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        p.setPen(pen)
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawEllipse(QPoint(cx, cy), r, r)

        if is_playing:
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(color)
            p.drawRoundedRect(QRectF(cx - 3.5, cy - 4.5, 2.2, 9), 1, 1)
            p.drawRoundedRect(QRectF(cx + 1.3, cy - 4.5, 2.2, 9), 1, 1)
        else:
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(color)
            tri = QPainterPath()
            tri.moveTo(cx - 2.5, cy - 4.8)
            tri.lineTo(cx - 2.5, cy + 4.8)
            tri.lineTo(cx + 4.8, cy)
            tri.closeSubpath()
            p.drawPath(tri)
        p.restore()

    def _draw_vector_note(self, p: QPainter, cx: int, cy: int, size: int = 14, color: QColor = QColor(255, 255, 255)):
        p.save()
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(color)
        p.drawEllipse(QPoint(cx - 3, cy + 3), 3, 2)
        p.drawRect(QRectF(cx - 1, cy - 5, 1.6, 8))
        flag = QPainterPath()
        flag.moveTo(cx - 1, cy - 5)
        flag.quadTo(cx + 4, cy - 4, cx + 4, cy - 1)
        flag.quadTo(cx + 2, cy - 3, cx - 1, cy - 2)
        flag.closeSubpath()
        p.drawPath(flag)
        p.restore()

    def _draw_vector_speaker(self, p: QPainter, cx: int, cy: int, level: int = 2, color: QColor = QColor(255, 255, 255)):
        p.save()
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        
        # Speaker cone
        cone = QPainterPath()
        cone.moveTo(cx - 5, cy - 2.5)
        cone.lineTo(cx - 2, cy - 2.5)
        cone.lineTo(cx + 2, cy - 5.5)
        cone.lineTo(cx + 2, cy + 5.5)
        cone.lineTo(cx - 2, cy + 2.5)
        cone.lineTo(cx - 5, cy + 2.5)
        cone.closeSubpath()

        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(color)
        p.drawPath(cone)

        pen = QPen(color, 1.3)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        p.setPen(pen)
        p.setBrush(Qt.BrushStyle.NoBrush)

        if level == 0:
            # Mute X
            p.drawLine(cx + 4, cy - 3, cx + 8, cy + 3)
            p.drawLine(cx + 8, cy - 3, cx + 4, cy + 3)
        elif level == 1:
            # Single sound arc (Volume Down / Low)
            p.drawArc(QRectF(cx + 1, cy - 4, 6, 8), -50 * 16, 100 * 16)
        elif level >= 2:
            # Double sound arcs (Volume Up / High)
            p.drawArc(QRectF(cx + 1, cy - 4, 6, 8), -50 * 16, 100 * 16)
            p.drawArc(QRectF(cx + 4, cy - 6, 7, 12), -50 * 16, 100 * 16)

        p.restore()

    def _draw_vector_weather_icon(self, p: QPainter, cx: int, cy: int, icon_type: str = "sun", color: QColor = QColor(255, 255, 255), scale: float = 1.0):
        p.save()
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        p.translate(cx, cy)
        p.scale(scale, scale)

        t = self._anim_time

        if icon_type in ["sun", "hot"]:
            # Radiant rotating sun corona + pulsating solar flares
            rot = (t * 25.0) % 360.0
            p.save()
            p.rotate(rot)
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor(255, 180, 0, 80))
            p.drawEllipse(QPoint(0, 0), 7, 7)
            
            p.setBrush(QColor(255, 204, 0))
            p.drawEllipse(QPoint(0, 0), 5, 5)

            pen = QPen(QColor(255, 214, 10), 1.4)
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            p.setPen(pen)
            ray_len = 9.5 + math.sin(t * 4.0) * 1.0
            for angle in [0, 45, 90, 135, 180, 225, 270, 315]:
                rad = math.radians(angle)
                x1 = math.cos(rad) * 6.5
                y1 = math.sin(rad) * 6.5
                x2 = math.cos(rad) * ray_len
                y2 = math.sin(rad) * ray_len
                p.drawLine(QPointF(x1, y1), QPointF(x2, y2))
            p.restore()

            if icon_type == "hot":
                # Shimmer wave below sun
                p.setPen(QPen(QColor(255, 150, 50, 180), 1.2))
                wave = QPainterPath()
                wave.moveTo(-6, 8 + math.sin(t * 3.0) * 1.5)
                wave.quadTo(0, 8 - math.sin(t * 3.0) * 1.5, 6, 8 + math.sin(t * 3.0) * 1.5)
                p.drawPath(wave)

        elif icon_type == "night":
            # Glowing crescent moon with starlight halo
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor(255, 214, 10, 40))
            p.drawEllipse(QPoint(0, 0), 9, 9)

            cres = QPainterPath()
            cres.moveTo(2, -6)
            cres.cubicTo(6, -2, 6, 4, 1, 6)
            cres.cubicTo(-5, 6, -7, -1, -3, -6)
            cres.cubicTo(-2, -3, 0, -5, 2, -6)
            cres.closeSubpath()
            p.setBrush(QColor(255, 214, 10))
            p.drawPath(cres)

            # Animated twinkle star
            star_a = int(120 + 130 * abs(math.sin(t * 3.0)))
            p.setBrush(QColor(255, 255, 255, star_a))
            p.drawEllipse(QPointF(5.5, -4.5), 1.2, 1.2)

        elif icon_type in ["rain", "thunder"]:
            # Cloud base
            cloud = QPainterPath()
            cloud.moveTo(-7, 0)
            cloud.cubicTo(-9, -3, -5, -7, -2, -5)
            cloud.cubicTo(0, -9, 6, -8, 6, -4)
            cloud.cubicTo(9, -3, 9, 1, 6, 2)
            cloud.lineTo(-6, 2)
            cloud.closeSubpath()
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor(200, 220, 240, 230))
            p.drawPath(cloud)

            if icon_type == "rain":
                # Animated falling rain drops
                pen = QPen(QColor(96, 165, 250), 1.3)
                pen.setCapStyle(Qt.PenCapStyle.RoundCap)
                p.setPen(pen)
                offset = (t * 14.0) % 4.0
                p.drawLine(QPointF(-4, 3 + offset), QPointF(-5, 6 + offset))
                p.drawLine(QPointF(0, 4 + offset), QPointF(-1, 7 + offset))
                p.drawLine(QPointF(4, 3 + offset), QPointF(3, 6 + offset))
            else:
                # Animated lightning bolt
                bolt = QPainterPath()
                bolt.moveTo(1, 2)
                bolt.lineTo(-2, 6)
                bolt.lineTo(0.5, 6)
                bolt.lineTo(-1, 10)
                bolt.lineTo(3, 5)
                bolt.lineTo(0.5, 5)
                bolt.closeSubpath()
                p.setPen(Qt.PenStyle.NoPen)
                bolt_alpha = 180 + int(75 * abs(math.sin(t * 8.0)))
                p.setBrush(QColor(255, 220, 20, bolt_alpha))
                p.drawPath(bolt)

        elif icon_type == "snow":
            # Cloud + drifting flakes
            cloud = QPainterPath()
            cloud.moveTo(-7, 0)
            cloud.cubicTo(-9, -3, -5, -7, -2, -5)
            cloud.cubicTo(0, -9, 6, -8, 6, -4)
            cloud.cubicTo(9, -3, 9, 1, 6, 2)
            cloud.lineTo(-6, 2)
            cloud.closeSubpath()
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor(220, 235, 255, 230))
            p.drawPath(cloud)
            
            p.setBrush(QColor(255, 255, 255))
            f_offset = (t * 3.0) % 5.0
            p.drawEllipse(QPointF(-4 + math.sin(t * 2) * 1.5, 3 + f_offset), 1.1, 1.1)
            p.drawEllipse(QPointF(1 + math.cos(t * 2) * 1.5, 4 + f_offset), 1.1, 1.1)
            p.drawEllipse(QPointF(5 + math.sin(t * 3) * 1.5, 3 + f_offset), 1.1, 1.1)

        elif icon_type == "wind":
            # Flowing aerodynamic wind streams
            pen = QPen(QColor(148, 163, 184), 1.3)
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            p.setPen(pen)
            p.setBrush(Qt.BrushStyle.NoBrush)

            w1 = QPainterPath()
            w1.moveTo(-8, -3 + math.sin(t * 4.0) * 1.0)
            w1.lineTo(2, -3 + math.sin(t * 4.0) * 1.0)
            w1.quadTo(6, -3, 6, -5)
            p.drawPath(w1)

            w2 = QPainterPath()
            w2.moveTo(-6, 2 + math.cos(t * 4.0) * 1.0)
            w2.lineTo(4, 2 + math.cos(t * 4.0) * 1.0)
            w2.quadTo(8, 2, 8, 4)
            p.drawPath(w2)

        else:  # "cloud"
            # Multi-layer floating cloud with gentle atmospheric bob
            bob = math.sin(t * 2.0) * 0.8
            cloud = QPainterPath()
            cloud.moveTo(-7, 2 + bob)
            cloud.cubicTo(-9, -1 + bob, -5, -6 + bob, -2, -4 + bob)
            cloud.cubicTo(0, -8 + bob, 6, -7 + bob, 7, -2 + bob)
            cloud.cubicTo(10, 0 + bob, 9, 4 + bob, 6, 4 + bob)
            cloud.lineTo(-6, 4 + bob)
            cloud.closeSubpath()
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor(220, 230, 245, 240))
            p.drawPath(cloud)

        p.restore()

    def _draw_vector_clock(self, p: QPainter, cx: int, cy: int, r: int = 7, color: QColor = QColor(255, 255, 255)):
        p.save()
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        pen = QPen(color, 1.3)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        p.setPen(pen)
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawEllipse(QPoint(cx, cy), r, r)
        p.drawLine(cx, cy, cx, cy - (r - 2.5))
        p.drawLine(cx, cy, cx + (r - 3.5), cy)
        p.restore()

    def _draw_vector_droplet(self, p: QPainter, cx: int, cy: int, color: QColor = QColor(96, 165, 250)):
        """Dynamic animated water droplet with surface tension breathing, specular glint, and liquid ripple."""
        p.save()
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        t = self._anim_time

        # Floating vertical bob & organic liquid squash/stretch
        bob_y = math.sin(t * 3.5) * 1.2
        squash = 1.0 + math.sin(t * 3.5) * 0.08
        stretch = 1.0 - math.sin(t * 3.5) * 0.08

        p.translate(cx, cy + bob_y)
        p.scale(squash, stretch)

        # 1. Outer Soft Water Glow
        glow_col = QColor(color.red(), color.green(), color.blue(), 35)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(glow_col)
        p.drawEllipse(QPointF(0, 1), 6, 6)

        # 2. Main Teardrop Path
        drop = QPainterPath()
        drop.moveTo(0, -6.0)
        drop.cubicTo(4.2, -1.5, 4.2, 4.5, 0, 4.5)
        drop.cubicTo(-4.2, 4.5, -4.2, -1.5, 0, -6.0)
        drop.closeSubpath()

        # Gradient shading for 3D liquid volume
        grad = QLinearGradient(0, -6, 0, 5)
        grad.setColorAt(0.0, QColor(min(255, color.red() + 60), min(255, color.green() + 50), 255, 250))
        grad.setColorAt(0.7, color)
        grad.setColorAt(1.0, QColor(max(0, color.red() - 40), max(0, color.green() - 30), max(0, color.blue() - 30), 240))
        p.setBrush(grad)
        p.drawPath(drop)

        # 3. Dynamic Specular Light Glint (shines & pulses)
        glint_alpha = int(160 + 80 * math.sin(t * 4.0))
        p.setBrush(QColor(255, 255, 255, glint_alpha))
        p.drawEllipse(QPointF(-1.4, -1.8), 1.2, 1.8)

        # 4. Tiny Micro Drip Ripple below droplet
        p.restore()
        p.save()
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        ripple_prog = (t * 2.0) % 1.0
        r_w = 2.0 + ripple_prog * 5.5
        r_h = 0.8 + ripple_prog * 2.0
        r_alpha = int((1.0 - ripple_prog) * 110)
        if r_alpha > 0:
            p.setPen(QPen(QColor(color.red(), color.green(), color.blue(), r_alpha), 1.0))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawEllipse(QPointF(cx, cy + 6.0), r_w, r_h)
        p.restore()

    def _draw_vector_wind(self, p: QPainter, cx: int, cy: int, color: QColor = QColor(148, 163, 184)):
        """Dynamic flowing wind streams with animated aerodynamic curls, oscillating gusts, and speed streaks."""
        p.save()
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        t = self._anim_time

        # Oscillation for gust waves
        w1_sin = math.sin(t * 5.0) * 0.9
        w2_sin = math.cos(t * 4.5) * 0.9
        curl_pulse = math.sin(t * 6.0) * 1.2

        pen = QPen(color, 1.3)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        p.setPen(pen)
        p.setBrush(Qt.BrushStyle.NoBrush)

        # Streamline 1 (Top stream with upper aerodynamic curl)
        w1 = QPainterPath()
        w1.moveTo(cx - 7, cy - 2.5 + w1_sin)
        w1.lineTo(cx + 2, cy - 2.5 + w1_sin)
        w1.quadTo(cx + 5.5, cy - 2.5 + w1_sin, cx + 5.5, cy - 5.0 + curl_pulse * 0.6)
        p.drawPath(w1)

        # Streamline 2 (Bottom stream with lower aerodynamic curl)
        w2 = QPainterPath()
        w2.moveTo(cx - 5, cy + 2.5 + w2_sin)
        w2.lineTo(cx + 3, cy + 2.5 + w2_sin)
        w2.quadTo(cx + 7.0, cy + 2.5 + w2_sin, cx + 7.0, cy + 5.0 - curl_pulse * 0.6)
        p.drawPath(w2)

        # Streamline 3 (Middle fast breeze micro-streak)
        mid_prog = (t * 3.5) % 1.0
        streak_x = cx - 6 + mid_prog * 12.0
        streak_alpha = int(math.sin(mid_prog * math.pi) * 220)
        if streak_alpha > 0:
            streak_pen = QPen(QColor(color.red(), color.green(), color.blue(), streak_alpha), 1.2)
            streak_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            p.setPen(streak_pen)
            p.drawLine(QPointF(streak_x - 2.0, cy), QPointF(streak_x + 2.0, cy))

        p.restore()

    def _draw_vector_clipboard_icon(self, p: QPainter, cx: int, cy: int, color: QColor = QColor(255, 255, 255)):
        """Apple SF Symbol style clipboard with rounded clip clamp and interior page lines."""
        p.save()
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        pen = QPen(color, 1.3)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        p.setPen(pen)
        p.setBrush(Qt.BrushStyle.NoBrush)
        # Main board outline
        p.drawRoundedRect(QRectF(cx - 5, cy - 4.5, 10, 11), 1.5, 1.5)
        # Top clip clamp
        p.drawRoundedRect(QRectF(cx - 2.5, cy - 6.5, 5, 2.5), 1, 1)
        # Internal document lines
        p.setPen(QPen(QColor(color.red(), color.green(), color.blue(), 180), 1.0))
        p.drawLine(cx - 2.5, cy - 0.5, cx + 2.5, cy - 0.5)
        p.drawLine(cx - 2.5, cy + 2.2, cx + 1.5, cy + 2.2)
        p.restore()

    def _draw_vector_trash(self, p: QPainter, cx: int, cy: int, color: QColor = QColor(255, 255, 255)):
        """Vector trash can icon."""
        p.save()
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        pen = QPen(color, 1.2)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        p.setPen(pen)
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRoundedRect(QRectF(cx - 3.5, cy - 2, 7, 7.5), 1, 1)
        p.drawLine(cx - 5, cy - 3, cx + 5, cy - 3)
        p.drawLine(cx - 1.5, cy - 4.5, cx + 1.5, cy - 4.5)
        p.restore()

    def _draw_vector_case(self, p: QPainter, cx: int, cy: int, color: QColor = QColor(255, 255, 255)):
        """Vector typography case conversion icon."""
        p.save()
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        p.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
        p.setPen(color)
        p.drawText(QRect(cx - 7, cy - 7, 14, 14), Qt.AlignmentFlag.AlignCenter, "Aa")
        p.restore()

    def _draw_vector_swatch(self, p: QPainter, cx: int, cy: int, color_hex: str):
        """Vector color swatch preview box."""
        p.save()
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        p.setPen(QPen(QColor(255, 255, 255, 120), 1.0))
        try:
            p.setBrush(QColor(color_hex))
        except Exception:
            p.setBrush(QColor(255, 255, 255))
        p.drawRoundedRect(QRectF(cx - 5, cy - 5, 10, 10), 2.5, 2.5)
        p.restore()

    def _draw_vector_bolt(self, p: QPainter, cx: int, cy: int, color: QColor = QColor(255, 255, 255)):
        p.save()
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(color)
        bolt = QPainterPath()
        bolt.moveTo(cx + 1, cy - 6)
        bolt.lineTo(cx - 4, cy - 0.5)
        bolt.lineTo(cx - 0.5, cy - 0.5)
        bolt.lineTo(cx - 1.5, cy + 6)
        bolt.lineTo(cx + 3.5, cy + 0.5)
        bolt.lineTo(cx, cy + 0.5)
        bolt.closeSubpath()
        p.drawPath(bolt)
        p.restore()

    def _draw_vector_globe(self, p: QPainter, cx: int, cy: int, r: int = 6, color: QColor = QColor(255, 255, 255)):
        p.save()
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        pen = QPen(color, 1.2)
        p.setPen(pen)
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawEllipse(QPoint(cx, cy), r, r)
        p.drawLine(cx - r, cy, cx + r, cy)
        p.drawEllipse(QPoint(cx, cy), max(1, r // 2), r)
        p.restore()

    def _draw_vector_search(self, p: QPainter, cx: int, cy: int, color: QColor = QColor(255, 255, 255)):
        p.save()
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        pen = QPen(color, 1.3)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        p.setPen(pen)
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawEllipse(QPoint(cx - 1.5, cy - 1.5), 4, 4)
        p.drawLine(cx + 1.5, cy + 1.5, cx + 5, cy + 5)
        p.restore()

    def _draw_vector_copy(self, p: QPainter, cx: int, cy: int, color: QColor = QColor(255, 255, 255)):
        p.save()
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        pen = QPen(color, 1.2)
        p.setPen(pen)
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRoundedRect(QRectF(cx - 5, cy - 5, 7, 8), 1, 1)
        p.setBrush(QColor(0, 0, 0, 180))
        p.drawRoundedRect(QRectF(cx - 2, cy - 2, 7, 8), 1, 1)
        p.restore()

    def _draw_vector_cpu(self, p: QPainter, cx: int, cy: int, color: QColor = QColor(52, 199, 89)):
        p.save()
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        pen = QPen(color, 1.2)
        p.setPen(pen)
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRoundedRect(QRectF(cx - 5, cy - 5, 10, 10), 2, 2)
        # Pins
        p.drawLine(cx - 3, cy - 7, cx - 3, cy - 5)
        p.drawLine(cx + 3, cy - 7, cx + 3, cy - 5)
        p.drawLine(cx - 3, cy + 5, cx - 3, cy + 7)
        p.drawLine(cx + 3, cy + 5, cx + 3, cy + 7)
        p.drawLine(cx - 7, cy - 3, cx - 5, cy - 3)
        p.drawLine(cx - 7, cy + 3, cx - 5, cy + 3)
        p.drawLine(cx + 5, cy - 3, cx + 7, cy - 3)
        p.drawLine(cx + 5, cy + 3, cx + 7, cy + 3)
        p.restore()

    def _draw_vector_ram(self, p: QPainter, cx: int, cy: int, color: QColor = QColor(0, 122, 255)):
        p.save()
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        pen = QPen(color, 1.2)
        p.setPen(pen)
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRoundedRect(QRectF(cx - 7, cy - 4, 14, 8), 1.5, 1.5)
        p.drawLine(cx - 4, cy - 2, cx - 4, cy + 2)
        p.drawLine(cx - 1, cy - 2, cx - 1, cy + 2)
        p.drawLine(cx + 2, cy - 2, cx + 2, cy + 2)
        p.drawLine(cx + 5, cy - 2, cx + 5, cy + 2)
        p.restore()

    def _draw_vector_scissors(self, p: QPainter, cx: int, cy: int, color: QColor = QColor(255, 255, 255)):
        p.save()
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        pen = QPen(color, 1.2)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        p.setPen(pen)
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawEllipse(QPoint(cx - 3, cy + 3), 2, 2)
        p.drawEllipse(QPoint(cx + 3, cy + 3), 2, 2)
        p.drawLine(cx - 2, cy + 1, cx + 4, cy - 5)
        p.drawLine(cx + 2, cy + 1, cx - 4, cy - 5)
        p.restore()

    def _draw_vector_calc(self, p: QPainter, cx: int, cy: int, color: QColor = QColor(255, 255, 255)):
        p.save()
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        pen = QPen(color, 1.2)
        p.setPen(pen)
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRoundedRect(QRectF(cx - 5, cy - 6, 10, 12), 1.5, 1.5)
        p.fillRect(QRectF(cx - 3.5, cy - 4.5, 7, 2.5), color)
        p.setPen(color)
        p.drawPoint(cx - 2, cy + 1)
        p.drawPoint(cx + 2, cy + 1)
        p.drawPoint(cx - 2, cy + 4)
        p.drawPoint(cx + 2, cy + 4)
        p.restore()

    def _draw_vector_notes(self, p: QPainter, cx: int, cy: int, color: QColor = QColor(255, 255, 255)):
        p.save()
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        pen = QPen(color, 1.2)
        p.setPen(pen)
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRoundedRect(QRectF(cx - 5, cy - 6, 10, 12), 1.5, 1.5)
        p.drawLine(cx - 3, cy - 2, cx + 3, cy - 2)
        p.drawLine(cx - 3, cy + 1, cx + 3, cy + 1)
        p.drawLine(cx - 3, cy + 4, cx + 1, cy + 4)
        p.restore()

    def _draw_vector_lock(self, p: QPainter, cx: int, cy: int, color: QColor = QColor(255, 255, 255)):
        p.save()
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        pen = QPen(color, 1.2)
        p.setPen(pen)
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRoundedRect(QRectF(cx - 4, cy - 1, 8, 7), 1.5, 1.5)
        p.drawArc(QRectF(cx - 2.5, cy - 6, 5, 6), 0, 180 * 16)
        p.restore()

    def _draw_vector_bluetooth(self, p: QPainter, cx: int, cy: int, is_connected: bool = True, color: QColor = QColor(0, 122, 255)):
        p.save()
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        pen = QPen(color, 1.4)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        p.setPen(pen)
        p.setBrush(Qt.BrushStyle.NoBrush)

        bt = QPainterPath()
        # Vertical spine
        bt.moveTo(cx, cy - 7)
        bt.lineTo(cx, cy + 7)
        # Upper loop & cross
        bt.moveTo(cx - 4, cy - 3.5)
        bt.lineTo(cx + 4, cy + 3.5)
        bt.lineTo(cx, cy + 7)
        # Lower loop & cross
        bt.lineTo(cx + 4, cy - 3.5)
        bt.lineTo(cx - 4, cy + 3.5)
        p.drawPath(bt)
        p.restore()

    def _draw_vector_chatgpt(self, p: QPainter, cx: int, cy: int, color: QColor = QColor(16, 163, 127), scale: float = 1.0):
        """Vector representation of OpenAI / ChatGPT rosette icon."""
        p.save()
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        p.translate(cx, cy)
        p.scale(scale, scale)
        pen = QPen(color, 1.3)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        p.setPen(pen)
        p.setBrush(Qt.BrushStyle.NoBrush)
        for i in range(6):
            p.save()
            p.rotate(i * 60)
            p.drawArc(QRectF(-4.5, -6.5, 9, 9), 30 * 16, 180 * 16)
            p.restore()
        p.restore()

    def _draw_vector_map_pin(self, p: QPainter, cx: int, cy: int, color: QColor = QColor(234, 67, 53)):
        """Vector Google Maps Pin icon."""
        p.save()
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(color)

        pin = QPainterPath()
        pin.moveTo(cx, cy + 6)
        pin.cubicTo(cx - 5.5, cy + 1, cx - 5.5, cy - 4, cx, cy - 4)
        pin.cubicTo(cx + 5.5, cy - 4, cx + 5.5, cy + 1, cx, cy + 6)
        pin.closeSubpath()
        p.drawPath(pin)

        # Center cutout
        p.setBrush(QColor(255, 255, 255))
        p.drawEllipse(QPoint(cx, cy - 1), 2, 2)
        p.restore()

    def _draw_vector_compass_icon(self, p: QPainter, cx: int, cy: int, color: QColor = QColor(255, 255, 255)):
        """Vector compact compass icon for tab headers."""
        p.save()
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        pen = QPen(color, 1.2)
        p.setPen(pen)
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawEllipse(QPoint(cx, cy), 6, 6)

        needle = QPainterPath()
        needle.moveTo(cx, cy - 4.5)
        needle.lineTo(cx + 2.5, cy + 2.5)
        needle.lineTo(cx - 2.5, cy + 2.5)
        needle.closeSubpath()
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(color)
        p.drawPath(needle)
        p.restore()

    def _draw_vector_directions(self, p: QPainter, cx: int, cy: int, color: QColor = QColor(66, 133, 244)):
        """Vector route turn / navigation direction arrow."""
        p.save()
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        pen = QPen(color, 1.3)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        p.setPen(pen)
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawArc(QRectF(cx - 4, cy - 4, 8, 8), 0, 90 * 16)
        p.drawLine(cx, cy - 4, cx + 4, cy - 4)
        p.drawLine(cx + 4, cy - 4, cx + 2, cy - 6)
        p.drawLine(cx + 4, cy - 4, cx + 2, cy - 2)
        p.restore()

    def _draw_vector_satellite(self, p: QPainter, cx: int, cy: int, color: QColor = QColor(251, 188, 4)):
        """Vector orbital satellite icon."""
        p.save()
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        pen = QPen(color, 1.2)
        p.setPen(pen)
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRoundedRect(QRectF(cx - 2.5, cy - 2.5, 5, 5), 1, 1)
        p.drawLine(cx - 5, cy, cx - 2.5, cy)
        p.drawLine(cx + 2.5, cy, cx + 5, cy)
        p.drawArc(QRectF(cx - 5, cy - 5, 10, 10), 45 * 16, 90 * 16)
        p.restore()

    def _draw_vector_traffic(self, p: QPainter, cx: int, cy: int, color: QColor = QColor(52, 168, 83)):
        """Vector traffic congestion lights icon."""
        p.save()
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(234, 67, 53))
        p.drawEllipse(QPoint(cx, cy - 4), 1.5, 1.5)
        p.setBrush(QColor(251, 188, 4))
        p.drawEllipse(QPoint(cx, cy), 1.5, 1.5)
        p.setBrush(QColor(52, 168, 83))
        p.drawEllipse(QPoint(cx, cy + 4), 1.5, 1.5)
        p.restore()

    def _draw_precision_compass(self, p: QPainter, cx: int, cy: int, r: int, heading: float, theme: dict):
        """Precision Apple Watch Ultra / iOS Compass Dial with 360-deg ring and 3D needle."""
        p.save()
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        # Outer bezel ring
        p.setPen(QPen(QColor(255, 255, 255, 45), 1.2))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawEllipse(QPoint(cx, cy), r, r)

        # Dial rotation
        p.save()
        p.translate(cx, cy)
        p.rotate(-heading)

        # Tick marks
        for deg in range(0, 360, 15):
            p.save()
            p.rotate(deg)
            is_cardinal = (deg % 90 == 0)
            is_sub = (deg % 30 == 0)
            tick_len = 5 if is_cardinal else (3.5 if is_sub else 2)
            tick_alpha = 240 if is_cardinal else (160 if is_sub else 80)

            if deg == 0:
                p.setPen(QPen(QColor(239, 68, 68, 255), 1.5))
            else:
                p.setPen(QPen(QColor(255, 255, 255, tick_alpha), 1.0 if not is_cardinal else 1.3))

            p.drawLine(0, -r + 1, 0, -r + 1 + tick_len)
            p.restore()

        # Cardinal Letters N, E, S, W
        p.setFont(QFont("Segoe UI", 7, QFont.Weight.Bold))
        # N
        p.setPen(QColor(239, 68, 68))
        p.drawText(QRect(-8, -r + 6, 16, 12), Qt.AlignmentFlag.AlignCenter, "N")
        # E
        p.setPen(QColor(255, 255, 255, 210))
        p.drawText(QRect(r - 16, -6, 14, 12), Qt.AlignmentFlag.AlignCenter, "E")
        # S
        p.drawText(QRect(-7, r - 16, 14, 12), Qt.AlignmentFlag.AlignCenter, "S")
        # W
        p.drawText(QRect(-r + 2, -6, 14, 12), Qt.AlignmentFlag.AlignCenter, "W")

        p.restore()  # Undo rotation for center needle

        # 3D Magnetic Needle
        p.save()
        p.translate(cx, cy)

        # North Pointer (Red / Magma)
        needle_n = QPainterPath()
        needle_n.moveTo(0, -r + 7)
        needle_n.lineTo(3.5, 0)
        needle_n.lineTo(0, -2)
        needle_n.closeSubpath()
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(239, 68, 68, 250))
        p.drawPath(needle_n)

        needle_n_shade = QPainterPath()
        needle_n_shade.moveTo(0, -r + 7)
        needle_n_shade.lineTo(-3.5, 0)
        needle_n_shade.lineTo(0, -2)
        needle_n_shade.closeSubpath()
        p.setBrush(QColor(185, 28, 28, 240))
        p.drawPath(needle_n_shade)

        # South Pointer (White / Silver)
        needle_s = QPainterPath()
        needle_s.moveTo(0, r - 7)
        needle_s.lineTo(3.5, 0)
        needle_s.lineTo(0, 2)
        needle_s.closeSubpath()
        p.setBrush(QColor(226, 232, 240, 220))
        p.drawPath(needle_s)

        needle_s_shade = QPainterPath()
        needle_s_shade.moveTo(0, r - 7)
        needle_s_shade.lineTo(-3.5, 0)
        needle_s_shade.lineTo(0, 2)
        needle_s_shade.closeSubpath()
        p.setBrush(QColor(148, 163, 184, 200))
        p.drawPath(needle_s_shade)

        # Center Pivot Metallic Ring
        p.setPen(QPen(QColor(255, 255, 255, 120), 1.0))
        p.setBrush(QColor(15, 23, 42))
        p.drawEllipse(QPoint(0, 0), 3, 3)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(239, 68, 68))
        p.drawEllipse(QPoint(0, 0), 1, 1)

        p.restore()
        p.restore()

    # ── Paint Engine (Luxury Glass & Morphing Graphics) ──────────────────────

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)

        theme = ISLAND_THEMES.get(self._theme_key, ISLAND_THEMES["apple_dynamic"])
        w, h = self.width(), self.height()
        radius = self._corner_radius

        is_music_active = bool(self._last_media_info and (self._last_media_info.is_playing or self._state == self.STATE_MUSIC))
        beat = self._ambient_beat_energy
        c_pri = self._ambient_color_current
        c_sec = self._ambient_color_secondary
        t = self._anim_time

        # 0. Reactive Ambient Light Backlight Aura (Outer Radiance that breathes with music beats)
        if is_music_active or beat > 0.05:
            aura_alpha = int(max(15, min(140, 30 + beat * 110)))
            style = self._ambient_style

            if style == "aurora_borealis":
                # Aurora sweep: dual elliptical cosmic gradients
                flow_dx = math.sin(t * 1.6) * (w * 0.35)
                aura_grad = QRadialGradient((w / 2.0) + flow_dx, h / 2.0, max(w, h) * 0.75)
                aura_grad.setColorAt(0.0, QColor(c_pri.red(), c_pri.green(), c_pri.blue(), aura_alpha))
                aura_grad.setColorAt(0.50, QColor(c_sec.red(), c_sec.green(), c_sec.blue(), int(aura_alpha * 0.55)))
                aura_grad.setColorAt(1.0, QColor(0, 0, 0, 0))
            elif style == "neon_cyber_pulse":
                # Sharp cyber strobe with beat punch
                strobe_boost = int(50 * beat) if beat > 0.55 else 0
                aura_grad = QRadialGradient(w / 2.0, h / 2.0, max(w, h) * 0.70)
                aura_grad.setColorAt(0.0, QColor(c_pri.red(), c_pri.green(), c_pri.blue(), min(220, aura_alpha + strobe_boost)))
                aura_grad.setColorAt(0.45, QColor(c_sec.red(), c_sec.green(), c_sec.blue(), min(180, int(aura_alpha * 0.6) + strobe_boost)))
                aura_grad.setColorAt(1.0, QColor(0, 0, 0, 0))
            elif style == "sunset_chroma":
                # Warm horizontal synthwave horizon wash
                aura_grad = QLinearGradient(0, h * 0.2, 0, h * 1.1)
                aura_grad.setColorAt(0.0, QColor(c_pri.red(), c_pri.green(), c_pri.blue(), int(aura_alpha * 0.7)))
                aura_grad.setColorAt(0.65, QColor(c_sec.red(), c_sec.green(), c_sec.blue(), aura_alpha))
                aura_grad.setColorAt(1.0, QColor(0, 0, 0, 0))
            elif style == "lava_fire_glow":
                # Bottom-weighted volcanic magma radiance
                flow_dx = math.sin(t * 2.5) * (w * 0.2)
                aura_grad = QRadialGradient((w / 2.0) + flow_dx, h * 0.95, max(w, h) * 0.70)
                aura_grad.setColorAt(0.0, QColor(c_sec.red(), c_sec.green(), c_sec.blue(), int(aura_alpha * 1.1)))
                aura_grad.setColorAt(0.50, QColor(c_pri.red(), c_pri.green(), c_pri.blue(), int(aura_alpha * 0.6)))
                aura_grad.setColorAt(1.0, QColor(0, 0, 0, 0))
            elif style == "rainbow_flow":
                # Circulating chromatic aura
                flow_dx = math.cos(t * 2.0) * (w * 0.35)
                flow_dy = math.sin(t * 2.0) * (h * 0.25)
                aura_grad = QRadialGradient((w / 2.0) + flow_dx, (h / 2.0) + flow_dy, max(w, h) * 0.75)
                aura_grad.setColorAt(0.0, QColor(c_pri.red(), c_pri.green(), c_pri.blue(), aura_alpha))
                aura_grad.setColorAt(0.55, QColor(c_sec.red(), c_sec.green(), c_sec.blue(), int(aura_alpha * 0.5)))
                aura_grad.setColorAt(1.0, QColor(0, 0, 0, 0))
            elif style == "minimal_frost":
                # Pure frosted diamond white glow
                aura_grad = QRadialGradient(w / 2.0, h / 2.0, max(w, h) * 0.65)
                aura_grad.setColorAt(0.0, QColor(255, 255, 255, int(aura_alpha * 0.85)))
                aura_grad.setColorAt(0.50, QColor(c_sec.red(), c_sec.green(), c_sec.blue(), int(aura_alpha * 0.4)))
                aura_grad.setColorAt(1.0, QColor(0, 0, 0, 0))
            else:
                # adaptive_album
                flow_dx = math.cos(t * 1.8) * (w * 0.30)
                flow_dy = math.sin(t * 2.2) * (h * 0.20)
                aura_grad = QRadialGradient((w / 2.0) + flow_dx, (h / 2.0) + flow_dy, max(w, h) * 0.70)
                aura_grad.setColorAt(0.0, QColor(c_pri.red(), c_pri.green(), c_pri.blue(), aura_alpha))
                aura_grad.setColorAt(0.55, QColor(c_sec.red(), c_sec.green(), c_sec.blue(), int(aura_alpha * 0.45)))
                aura_grad.setColorAt(1.0, QColor(0, 0, 0, 0))

            painter.save()
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(aura_grad)
            painter.drawRoundedRect(QRectF(0, 0, w, h), radius, radius)
            painter.restore()

        # 1. Main Pill Body Path
        path = QPainterPath()
        path.addRoundedRect(QRectF(1, 1, w - 2, h - 2), radius, radius)

        # 2. Outer Glow & Glass Background Gradient
        grad = QLinearGradient(0, 0, 0, h)
        grad.setColorAt(0.0, theme["bg_top"])
        grad.setColorAt(1.0, theme["bg_bottom"])
        painter.fillPath(path, grad)

        # 2b. Internal Beat-Reactive Fluid Ambient Light Mesh & Style Effects (Inside the Glass)
        if is_music_active or beat > 0.05:
            mesh_alpha = int(max(10, min(80, 20 + beat * 55)))
            mesh_x = 50 + math.cos(t * 1.5) * (w * 0.4)
            mesh_y = (h * 0.45) + math.sin(t * 2.0) * (h * 0.2)
            mesh_grad = QRadialGradient(mesh_x, mesh_y, max(w * 0.65, 100))
            mesh_grad.setColorAt(0.0, QColor(c_pri.red(), c_pri.green(), c_pri.blue(), mesh_alpha))
            mesh_grad.setColorAt(0.65, QColor(c_sec.red(), c_sec.green(), c_sec.blue(), int(mesh_alpha * 0.35)))
            mesh_grad.setColorAt(1.0, QColor(0, 0, 0, 0))

            painter.save()
            painter.setClipPath(path)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(mesh_grad)
            painter.drawPath(path)

            # Special Style Internal Shaders
            style = self._ambient_style
            if style == "aurora_borealis":
                # Wavy Aurora Ribbons inside glass
                painter.setPen(Qt.PenStyle.NoPen)
                for layer_i in range(2):
                    ribbon = QPainterPath()
                    ribbon.moveTo(0, h * 0.5)
                    for rx in range(0, w + 10, 15):
                        ry = (h * 0.5) + math.sin((rx * 0.035) + (t * (2.0 + layer_i * 0.8))) * (12.0 + beat * 10.0)
                        ribbon.lineTo(rx, ry)
                    ribbon.lineTo(w, h)
                    ribbon.lineTo(0, h)
                    ribbon.closeSubpath()
                    rib_col = c_pri if layer_i == 0 else c_sec
                    painter.setBrush(QColor(rib_col.red(), rib_col.green(), rib_col.blue(), int(18 + beat * 30)))
                    painter.drawPath(ribbon)

            elif style == "lava_fire_glow":
                # Ascending Magma Embers inside glass
                painter.setPen(Qt.PenStyle.NoPen)
                for ember in self._lava_embers:
                    e_alpha = int(ember["alpha"] * (60 + beat * 150))
                    painter.setBrush(QColor(249, 115, 22, min(255, e_alpha)))
                    painter.drawEllipse(QPointF(ember["x"], ember["y"]), ember["r"], ember["r"])

            elif style == "neon_cyber_pulse" and beat > 0.5:
                # Laser Corner Flares
                painter.setPen(QPen(QColor(0, 240, 255, int(100 * beat)), 1.5))
                painter.drawLine(8, 8, 28, 8)
                painter.drawLine(8, 8, 8, 24)
                painter.setPen(QPen(QColor(255, 0, 128, int(100 * beat)), 1.5))
                painter.drawLine(w - 28, h - 8, w - 8, h - 8)
                painter.drawLine(w - 8, h - 24, w - 8, h - 8)

            elif style == "sunset_chroma":
                # Synthwave dusk horizon line
                sun_grad = QLinearGradient(0, h - 20, 0, h)
                sun_grad.setColorAt(0.0, QColor(245, 158, 11, 0))
                sun_grad.setColorAt(1.0, QColor(225, 29, 72, int(35 + beat * 45)))
                painter.setBrush(sun_grad)
                painter.drawRect(0, h - 20, w, 20)

            elif style == "minimal_frost":
                # Frosted glass shimmer outline
                shimmer_x = (t * 60.0) % (w + 100) - 50
                shim_grad = QLinearGradient(shimmer_x - 30, 0, shimmer_x + 30, 0)
                shim_grad.setColorAt(0.0, QColor(255, 255, 255, 0))
                shim_grad.setColorAt(0.5, QColor(255, 255, 255, int(25 + beat * 35)))
                shim_grad.setColorAt(1.0, QColor(255, 255, 255, 0))
                painter.setBrush(shim_grad)
                painter.drawRect(0, 0, w, h)

            painter.restore()

        # 3. Inner Gloss Highlight (Top curved sheen)
        gloss_path = QPainterPath()
        gloss_path.addRoundedRect(QRectF(2, 2, w - 4, h * 0.45), radius - 1, radius - 1)
        gloss_grad = QLinearGradient(0, 2, 0, h * 0.45)
        gloss_grad.setColorAt(0.0, QColor(255, 255, 255, 40))
        gloss_grad.setColorAt(1.0, QColor(255, 255, 255, 0))
        painter.fillPath(gloss_path, gloss_grad)

        # 4. Premium Titanium / Glass Rim with Dynamic Music Reactive Glow
        if is_music_active and beat > 0.05:
            rim_alpha = int(max(40, min(220, 50 + beat * 160)))
            rim_color = QColor(
                int(theme["border"].red() * 0.4 + c_pri.red() * 0.6),
                int(theme["border"].green() * 0.4 + c_pri.green() * 0.6),
                int(theme["border"].blue() * 0.4 + c_pri.blue() * 0.6),
                rim_alpha
            )
            border_pen = QPen(rim_color, theme["border_width"] + (0.5 if beat > 0.6 else 0.0))
        else:
            border_pen = QPen(theme["border"], theme["border_width"])
        painter.strokePath(path, border_pen)

        # 5. Render Specific State Content with OriginOS Fluid Morph & Cross-Fade
        progress = self._morph_progress  # 0.0 (compact pill) -> 1.0 (expanded squircle card)

        # A. Compact Pill Elements (visible when progress < 0.45)
        if progress < 0.45:
            compact_alpha = max(0.0, min(1.0, 1.0 - (progress / 0.35)))
            if compact_alpha > 0.01:
                painter.save()
                painter.setOpacity(compact_alpha)
                self._paint_compact(painter, theme, w, h)
                painter.restore()

        # B. Expanded Card Content (visible when progress > 0.20)
        if progress > 0.20:
            expand_alpha = max(0.0, min(1.0, (progress - 0.20) / 0.80))
            slide_y = (1.0 - expand_alpha) * 12.0  # subtle upward spring slide

            painter.save()
            painter.setOpacity(expand_alpha)
            painter.translate(0, -slide_y)

            # Check if tab is currently cross-fading
            if self._tab_transition_progress < 1.0 and self._tab_from in self.SIZES and self._tab_from != self._state:
                t_val = self._tab_transition_progress
                smooth_t = t_val * t_val * (3.0 - 2.0 * t_val)

                # Outgoing tab fades & slides slightly left
                painter.save()
                painter.setOpacity(expand_alpha * (1.0 - smooth_t))
                painter.translate(-16.0 * smooth_t, 0)
                self._paint_tab_body(painter, self._tab_from, theme, w, h)
                painter.restore()

                # Incoming tab fades in & slides into place from right
                painter.save()
                painter.setOpacity(expand_alpha * smooth_t)
                painter.translate(16.0 * (1.0 - smooth_t), 0)
                self._paint_tab_body(painter, self._state, theme, w, h)
                painter.restore()
            else:
                self._paint_tab_body(painter, self._state, theme, w, h)

            painter.restore()

        # 6. Interactive OriginOS & Dynamic Island Animated Drop-Down Volume HUD
        hud_elapsed = time.monotonic() - self._volume_hud_time
        if hud_elapsed < 1.6 or self._volume_hud_y > -26.0:
            hud_alpha = int(max(0.0, min(1.0, (1.6 - hud_elapsed) / 0.35)) * 240)
            hud_rect = QRect((w - 140) // 2, int(round(self._volume_hud_y)), 140, 26)
            hud_path = QPainterPath()
            hud_path.addRoundedRect(QRectF(hud_rect), 13, 13)

            painter.save()
            painter.setPen(QPen(QColor(255, 255, 255, int(hud_alpha * 0.4)), 1.0))
            painter.setBrush(QColor(20, 20, 26, hud_alpha))
            painter.drawPath(hud_path)

            # Speaker Icon
            spk_level = 0 if self._volume_hud_action == "mute" else (1 if self._volume_hud_action == "-" else 2)
            self._draw_vector_speaker(painter, hud_rect.left() + 16, hud_rect.center().y(), level=spk_level, color=QColor(255, 255, 255, hud_alpha))

            # Progress volume level bar with smooth spring interpolation
            bar_x = hud_rect.left() + 32
            bar_y = hud_rect.center().y() - 2.5
            bar_w = 92
            bar_h = 5.0

            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(255, 255, 255, int(hud_alpha * 0.25)))
            painter.drawRoundedRect(QRectF(bar_x, bar_y, bar_w, bar_h), 2.5, 2.5)

            fill_w = max(2.0, bar_w * (self._anim_volume_level / 100.0))
            painter.setBrush(QColor(255, 255, 255, hud_alpha))
            painter.drawRoundedRect(QRectF(bar_x, bar_y, fill_w, bar_h), 2.5, 2.5)
            painter.restore()

        # 7. Ambient Style Switching Toast Banner HUD
        toast_elapsed = time.monotonic() - self._ambient_toast_time
        if toast_elapsed < 2.0 or self._toast_y > -26.0:
            t_alpha = int(max(0.0, min(1.0, (2.0 - toast_elapsed) / 0.35)) * 245)
            t_rect = QRect((w - 220) // 2, int(round(self._toast_y)), 220, 24)
            t_path = QPainterPath()
            t_path.addRoundedRect(QRectF(t_rect), 12, 12)

            painter.save()
            painter.setPen(QPen(QColor(255, 255, 255, int(t_alpha * 0.4)), 1.0))
            painter.setBrush(QColor(18, 18, 24, t_alpha))
            painter.drawPath(t_path)

            painter.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
            painter.setPen(QColor(255, 255, 255, t_alpha))
            painter.drawText(t_rect, Qt.AlignmentFlag.AlignCenter, self._ambient_toast_name)
            painter.restore()

    def _paint_tab_body(self, p: QPainter, tab: str, theme: dict, w: int, h: int):
        if tab == self.STATE_MUSIC:
            self._paint_music(p, theme, w, h)
        elif tab == self.STATE_WEATHER:
            self._paint_weather(p, theme, w, h)
        elif tab == self.STATE_MAP:
            self._paint_map(p, theme, w, h)
        elif tab == self.STATE_CLIPBOARD:
            self._paint_clipboard(p, theme, w, h)
        elif tab == self.STATE_TOOLS:
            self._paint_tools(p, theme, w, h)

    def _paint_compact(self, p: QPainter, theme: dict, w: int, h: int):
        has_media = bool(self._last_media_info and self._last_media_info.has_media)
        thumb_bytes = self._last_media_info.thumbnail_bytes if self._last_media_info else None

        # Interactive breathing hover highlight sheen across compact pill
        if self._is_hovered or self._hovered_btn == "compact_pill":
            sheen_alpha = int(45 + 35 * math.sin(self._anim_time * 4.0))
            p.save()
            p.setPen(QPen(QColor(255, 255, 255, sheen_alpha), 1.2))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawRoundedRect(QRectF(1.0, 1.0, w - 2, h - 2), self._corner_radius, self._corner_radius)
            p.restore()

        if has_media:
            # ── Music Mode Active ──────────────────────────────────────────
            left_has_image = False
            if thumb_bytes:
                thumb_rect = QRect(8, (h - 24) // 2, 24, 24)
                thumb_path = QPainterPath()
                thumb_path.addRoundedRect(QRectF(thumb_rect), 6, 6)
                pix = QPixmap()
                if pix.loadFromData(thumb_bytes):
                    p.save()
                    p.setClipPath(thumb_path)
                    p.drawPixmap(thumb_rect, pix.scaled(24, 24, Qt.AspectRatioMode.KeepAspectRatioByExpanding, Qt.TransformationMode.SmoothTransformation))
                    p.restore()
                    p.strokePath(thumb_path, QPen(QColor(255, 255, 255, 50), 1.0))
                    left_has_image = True

            if not left_has_image:
                is_playing = bool(self._last_media_info and self._last_media_info.is_playing)
                self._draw_vector_play_circle(p, 20, h // 2, r=10, is_playing=is_playing, color=QColor(255, 255, 255, 240))

            # Track Title with smooth Marquee Ticker if long
            text = f"{self._last_media_info.title}" if self._last_media_info.title else "Playing Audio"
            if self._last_media_info.artist:
                text += f" • {self._last_media_info.artist}"

            p.setFont(QFont("Segoe UI", 9, QFont.Weight.DemiBold))
            p.setPen(theme["text_primary"])
            text_rect = QRect(38, 0, w - 82, h)
            fm = p.fontMetrics()
            t_width = fm.horizontalAdvance(text)

            p.save()
            p.setClipRect(text_rect)
            if t_width > text_rect.width():
                scroll_span = t_width + 40
                cur_off = int(self._compact_ticker_x) % scroll_span
                p.drawText(text_rect.x() - cur_off, 0, t_width, h, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, text)
                p.drawText(text_rect.x() - cur_off + scroll_span, 0, t_width, h, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, text)
            else:
                p.drawText(text_rect, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, text)
            p.restore()

            # Equalizer Bars on Right with Live Bounce
            eq_x = w - 40
            eq_w = 3
            gap = 3
            max_h = 16
            for i, val in enumerate(self._eq_bars[:4]):
                bar_h = max(3, int(val * max_h))
                bx = eq_x + i * (eq_w + gap)
                by = (h - bar_h) // 2
                bar_grad = QLinearGradient(bx, by, bx, by + bar_h)
                bar_grad.setColorAt(0.0, theme["eq_0"])
                bar_grad.setColorAt(1.0, theme["eq_1"])
                p.fillRect(QRect(bx, by, eq_w, bar_h), bar_grad)

        else:
            # ── Idle Standby Mode: Weather + Live Real-time Clock ───────────
            weather = self._last_weather_info or WeatherInfo()
            icon_type = weather.icon_type

            # Left: Vector Weather Icon & Temperature with live rotation
            self._draw_vector_weather_icon(p, 19, h // 2, icon_type=icon_type, color=QColor(255, 255, 255), scale=1.1)

            p.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
            p.setPen(theme["text_primary"])
            p.drawText(QRect(33, 0, 36, h), Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, f"{weather.temp_c}°")

            # Center/Right: Live Clock with animated pulsing colon
            hours = time.strftime("%I")
            mins = time.strftime("%M")
            ampm = time.strftime("%p")
            cur_date = time.strftime("%a, %b %d")

            clock_x = 72
            p.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
            p.setPen(theme["text_primary"])
            p.drawText(QRect(clock_x, 0, 18, h), Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, hours)

            # Animated pulsing colon
            colon_alpha = int(70 + 185 * abs(math.sin(self._anim_time * 3.14)))
            p.setPen(QColor(255, 255, 255, colon_alpha))
            p.drawText(QRect(clock_x + 18, 0, 6, h), Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignCenter, ":")

            p.setPen(theme["text_primary"])
            p.drawText(QRect(clock_x + 24, 0, 48, h), Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, f"{mins} {ampm}")

            # Live Date
            p.setFont(QFont("Segoe UI", 8, QFont.Weight.Normal))
            p.setPen(theme["text_secondary"])
            date_rect = QRect(144, 0, w - 150, h)
            fm = p.fontMetrics()
            elided_date = fm.elidedText(cur_date, Qt.TextElideMode.ElideRight, date_rect.width())
            p.drawText(date_rect, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, elided_date)

    def _paint_music(self, p: QPainter, theme: dict, w: int, h: int):
        self._paint_tab_headers(p, theme, w, active_tab="music")

        # 0. Beat-Reactive Glowing Ambient Halo behind Album Art
        halo_pulse = int(14 * self._ambient_beat_energy)
        halo_rect = QRect(18 - halo_pulse, 30 - halo_pulse, 56 + halo_pulse * 2, 56 + halo_pulse * 2)
        halo_grad = QRadialGradient(18 + 28, 30 + 28, 28 + halo_pulse * 1.5)
        halo_alpha = int(max(20, min(180, 45 + self._ambient_beat_energy * 130)))
        halo_grad.setColorAt(0.0, QColor(self._ambient_color_current.red(), self._ambient_color_current.green(), self._ambient_color_current.blue(), halo_alpha))
        halo_grad.setColorAt(0.65, QColor(self._ambient_color_secondary.red(), self._ambient_color_secondary.green(), self._ambient_color_secondary.blue(), int(halo_alpha * 0.4)))
        halo_grad.setColorAt(1.0, QColor(0, 0, 0, 0))

        p.save()
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(halo_grad)
        p.drawEllipse(halo_rect)
        p.restore()

        # 1. Album Artwork / Glass Bevel Icon on Left with subtle beat scale
        beat_scale = 1.0 + 0.04 * self._ambient_beat_energy
        art_rect = QRect(18, 30, 56, 56)
        art_path = QPainterPath()
        art_path.addRoundedRect(QRectF(art_rect), 14, 14)

        has_thumb = False
        if self._last_media_info and self._last_media_info.thumbnail_bytes:
            pix = QPixmap()
            if pix.loadFromData(self._last_media_info.thumbnail_bytes):
                p.save()
                if beat_scale > 1.005:
                    p.translate(18 + 28, 30 + 28)
                    p.scale(beat_scale, beat_scale)
                    p.translate(-(18 + 28), -(30 + 28))
                p.setClipPath(art_path)
                p.drawPixmap(art_rect, pix.scaled(56, 56, Qt.AspectRatioMode.KeepAspectRatioByExpanding, Qt.TransformationMode.SmoothTransformation))
                p.restore()
                has_thumb = True

        if not has_thumb:
            # Apple Music Vibrant Gradient Disc
            art_grad = QLinearGradient(18, 30, 74, 86)
            art_grad.setColorAt(0.0, QColor(250, 35, 59))
            art_grad.setColorAt(0.5, QColor(251, 92, 116))
            art_grad.setColorAt(1.0, QColor(186, 62, 189))
            p.save()
            if beat_scale > 1.005:
                p.translate(18 + 28, 30 + 28)
                p.scale(beat_scale, beat_scale)
                p.translate(-(18 + 28), -(30 + 28))
            p.fillPath(art_path, art_grad)
            self._draw_vector_note(p, 18 + 28, 30 + 28, size=18, color=QColor(255, 255, 255))
            p.restore()

        # Subtle 1px glass border around album cover
        p.strokePath(art_path, QPen(QColor(255, 255, 255, 45), 1.0))

        # 2. Track Title & Artist with Marquee Scrolling
        title = "No Music Playing"
        artist = "Play music on Spotify, YouTube, Apple Music"
        if self._last_media_info and self._last_media_info.title:
            title = self._last_media_info.title
            artist = self._last_media_info.artist or "Media Audio"

        # Title (Pure Crisp White)
        p.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        p.setPen(theme["text_primary"])
        title_rect = QRect(88, 30, w - 170, 22)
        fm = p.fontMetrics()
        m_title_w = fm.horizontalAdvance(title)

        p.save()
        p.setClipRect(title_rect)
        if m_title_w > title_rect.width():
            m_scroll = m_title_w + 35
            cur_m_off = int(self._music_ticker_x) % m_scroll
            p.drawText(title_rect.x() - cur_m_off, 30, m_title_w, 22, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, title)
            p.drawText(title_rect.x() - cur_m_off + m_scroll, 30, m_title_w, 22, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, title)
        else:
            p.drawText(title_rect, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, title)
        p.restore()

        # Artist (Muted Frosted Silver)
        p.setFont(QFont("Segoe UI", 9, QFont.Weight.Normal))
        p.setPen(theme["text_secondary"])
        artist_rect = QRect(88, 50, w - 170, 18)
        p.drawText(artist_rect, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, fm.elidedText(artist, Qt.TextElideMode.ElideRight, artist_rect.width()))

        # 3. 6-Band Visualizer Waveform (Apple Neon Green)
        eq_x = w - 75
        for i, val in enumerate(self._eq_bars):
            bar_h = max(4, int(val * 24))
            bx = eq_x + i * 8
            by = 46 - (bar_h // 2)
            bar_grad = QLinearGradient(bx, by, bx, by + bar_h)
            bar_grad.setColorAt(0.0, theme["eq_0"])
            bar_grad.setColorAt(1.0, theme["eq_1"])
            p.fillRect(QRect(bx, by, 4, bar_h), bar_grad)

        # 4. Interactive Live Progress / Scrub Bar & Timestamps
        bar_x = 88
        bar_y = 75
        bar_w = w - 106
        bar_h = 4.0

        cur_sec = int(self._playback_pos_sec)
        dur_sec = int(self._playback_dur_sec)
        ratio = min(1.0, max(0.0, self._playback_pos_sec / max(1.0, self._playback_dur_sec)))

        cur_time_str = f"{cur_sec // 60:02d}:{cur_sec % 60:02d}"
        dur_time_str = f"{dur_sec // 60:02d}:{dur_sec % 60:02d}"

        # Background track
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(255, 255, 255, 30))
        p.drawRoundedRect(QRectF(bar_x, bar_y, bar_w, bar_h), bar_h / 2, bar_h / 2)

        # Active progress bar with sleek gradient
        fill_w = max(4.0, bar_w * ratio)
        fill_grad = QLinearGradient(bar_x, bar_y, bar_x + fill_w, bar_y)
        fill_grad.setColorAt(0.0, theme["accent"])
        fill_grad.setColorAt(1.0, QColor(255, 255, 255, 240))
        p.setBrush(fill_grad)
        p.drawRoundedRect(QRectF(bar_x, bar_y, fill_w, bar_h), bar_h / 2, bar_h / 2)

        # Scrub thumb handle (expands smoothly on hover/scrub)
        thumb_r = 4.5 if self._is_scrubbing else 3.5
        thumb_x = bar_x + bar_w * ratio
        thumb_y = bar_y + bar_h / 2
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(255, 255, 255))
        p.drawEllipse(QPointF(thumb_x, thumb_y), thumb_r, thumb_r)

        # Live Timestamps underneath progress bar
        p.setFont(QFont("Segoe UI", 7, QFont.Weight.DemiBold))
        p.setPen(theme["text_secondary"])
        p.drawText(QRect(bar_x, bar_y + 6, 45, 12), Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, cur_time_str)
        p.drawText(QRect(bar_x + bar_w - 45, bar_y + 6, 45, 12), Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight, dur_time_str)

        # 5. Playback Controls & Master Volume Controls:
        # Layout: [Vol -] [Prev] [Play/Pause] [Next] [Vol +] [Mute]
        ctrl_y = h - 44
        cx = w // 2

        def _get_btn_style(btn_name: str, base_r: float, base_alpha: int = 22):
            h_val = self._btn_hover_anim.get(btn_name, 0.0)
            p_val = self._btn_press_anim.get(btn_name, 0.0)
            r = base_r * (1.0 - 0.12 * p_val)
            alpha = min(255, int(base_alpha + h_val * 65))
            color = QColor(255, 255, 255, alpha)
            return r, color, h_val, p_val

        # Vol Down [-] Button
        r, col, h_val, _ = _get_btn_style("vol_down", 14.0, 20)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(col)
        p.drawEllipse(QPointF(cx - 104, ctrl_y + 16), r, r)
        self._draw_vector_speaker(p, cx - 104, ctrl_y + 16, level=1, color=QColor(255, 255, 255, min(255, int(220 + h_val * 35))))

        # Prev Button
        r, col, h_val, _ = _get_btn_style("prev", 16.0, 22)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(col)
        p.drawEllipse(QPointF(cx - 52, ctrl_y + 16), r, r)
        p.setBrush(QColor(255, 255, 255, min(255, int(230 + h_val * 25))))
        prev_p = QPainterPath()
        prev_p.moveTo(cx - 47, ctrl_y + 11)
        prev_p.lineTo(cx - 47, ctrl_y + 21)
        prev_p.lineTo(cx - 55, ctrl_y + 16)
        prev_p.closeSubpath()
        p.drawPath(prev_p)
        p.fillRect(QRect(cx - 57, ctrl_y + 11, 2, 10), QColor(255, 255, 255, 230))

        # Play / Pause Center Pill (Apple Pure White Disc + Vector Glyph)
        r, col, h_val, _ = _get_btn_style("play", 18.0, 240)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(col)
        p.drawEllipse(QPointF(cx, ctrl_y + 16), r, r)

        is_playing = bool(self._last_media_info and self._last_media_info.is_playing)
        p.setBrush(QColor(12, 12, 16))
        if is_playing:
            p.drawRoundedRect(QRectF(cx - 4.5, ctrl_y + 10, 3, 12), 1, 1)
            p.drawRoundedRect(QRectF(cx + 1.5, ctrl_y + 10, 3, 12), 1, 1)
        else:
            play_p = QPainterPath()
            play_p.moveTo(cx - 3.5, ctrl_y + 9.5)
            play_p.lineTo(cx - 3.5, ctrl_y + 22.5)
            play_p.lineTo(cx + 6.5, ctrl_y + 16)
            play_p.closeSubpath()
            p.drawPath(play_p)

        # Next Button
        r, col, h_val, _ = _get_btn_style("next", 16.0, 22)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(col)
        p.drawEllipse(QPointF(cx + 52, ctrl_y + 16), r, r)
        p.setBrush(QColor(255, 255, 255, min(255, int(230 + h_val * 25))))
        next_p = QPainterPath()
        next_p.moveTo(cx + 47, ctrl_y + 11)
        next_p.lineTo(cx + 47, ctrl_y + 21)
        next_p.lineTo(cx + 55, ctrl_y + 16)
        next_p.closeSubpath()
        p.drawPath(next_p)
        p.fillRect(QRect(cx + 55, ctrl_y + 11, 2, 10), QColor(255, 255, 255, 230))

        # Vol Up [+] Button
        r, col, h_val, _ = _get_btn_style("vol_up", 14.0, 20)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(col)
        p.drawEllipse(QPointF(cx + 104, ctrl_y + 16), r, r)
        self._draw_vector_speaker(p, cx + 104, ctrl_y + 16, level=2, color=QColor(255, 255, 255, min(255, int(220 + h_val * 35))))

        # Master Mute Toggle Button
        r, col, h_val, _ = _get_btn_style("mute", 14.0, 18)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(col)
        p.drawEllipse(QPointF(w - 36, ctrl_y + 16), r, r)
        self._draw_vector_speaker(p, w - 36, ctrl_y + 16, level=0, color=QColor(255, 255, 255, min(255, int(180 + h_val * 40))))

    def _paint_weather(self, p: QPainter, theme: dict, w: int, h: int):
        self._paint_tab_headers(p, theme, w, active_tab="weather")

        weather = self._last_weather_info or WeatherInfo()
        icon_type = weather.icon_type
        t = self._anim_time

        # ── 1. Left Hero Weather Card (Procedural Animated Canvas) ───────────
        hero_rect = QRect(16, 28, 150, 108)
        hero_path = QPainterPath()
        hero_path.addRoundedRect(QRectF(hero_rect), 12, 12)

        p.save()
        p.setClipPath(hero_path)

        # Ambient Weather Card Background Theme
        if icon_type in ["hot", "sun"]:
            hero_grad = QLinearGradient(16, 28, 166, 136)
            hero_grad.setColorAt(0.0, QColor(60, 35, 10, 180))
            hero_grad.setColorAt(1.0, QColor(20, 12, 6, 220))
        elif icon_type == "rain":
            hero_grad = QLinearGradient(16, 28, 166, 136)
            hero_grad.setColorAt(0.0, QColor(15, 30, 50, 190))
            hero_grad.setColorAt(1.0, QColor(8, 15, 25, 230))
        elif icon_type == "thunder":
            hero_grad = QLinearGradient(16, 28, 166, 136)
            hero_grad.setColorAt(0.0, QColor(30, 15, 45, 200))
            hero_grad.setColorAt(1.0, QColor(10, 8, 20, 230))
        elif icon_type == "wind":
            hero_grad = QLinearGradient(16, 28, 166, 136)
            hero_grad.setColorAt(0.0, QColor(15, 35, 45, 190))
            hero_grad.setColorAt(1.0, QColor(8, 18, 26, 230))
        elif icon_type == "snow":
            hero_grad = QLinearGradient(16, 28, 166, 136)
            hero_grad.setColorAt(0.0, QColor(20, 35, 55, 190))
            hero_grad.setColorAt(1.0, QColor(10, 18, 30, 230))
        elif icon_type == "night":
            hero_grad = QLinearGradient(16, 28, 166, 136)
            hero_grad.setColorAt(0.0, QColor(12, 14, 30, 210))
            hero_grad.setColorAt(1.0, QColor(6, 6, 16, 240))
        else:
            hero_grad = QLinearGradient(16, 28, 166, 136)
            hero_grad.setColorAt(0.0, QColor(25, 30, 42, 180))
            hero_grad.setColorAt(1.0, QColor(12, 15, 22, 220))

        p.fillPath(hero_path, hero_grad)

        # ── LIVE WEATHER PARTICLES RENDERING ───────────────────────────────
        if icon_type == "rain":
            # 1. Slanted Falling Raindrops
            pen = QPen(QColor(120, 180, 255), 1.2)
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            p.setPen(pen)
            for d in self._rain_drops:
                rx = 16 + d["x"]
                ry = 28 + d["y"]
                p.setPen(QPen(QColor(120, 180, 255, int(d["alpha"] * 240)), 1.2))
                p.drawLine(QPointF(rx, ry), QPointF(rx + 2.0, ry + d["len"]))

            # 2. Ground Splash Ripples
            p.setBrush(Qt.BrushStyle.NoBrush)
            for s in self._rain_splashes:
                sx = 16 + s["x"]
                sy = 28 + s["y"]
                p.setPen(QPen(QColor(140, 200, 255, int(s["alpha"] * 255)), 1.0))
                p.drawEllipse(QPointF(sx, sy), s["r"], s["r"] * 0.45)

        elif icon_type in ["hot", "sun"]:
            # 1. Shimmering Rising Heatwave Curves
            p.setBrush(Qt.BrushStyle.NoBrush)
            for idx, y_base in enumerate([65, 85, 105]):
                heat_p = QPainterPath()
                heat_p.moveTo(16, 28 + y_base)
                for wx in range(0, 151, 15):
                    wy = y_base + math.sin(t * 3.5 + wx * 0.08 + idx) * 3.5
                    heat_p.lineTo(16 + wx, 28 + wy)
                p.setPen(QPen(QColor(255, 160, 40, 35 + idx * 10), 1.5))
                p.drawPath(heat_p)

            # 2. Rising Golden Heat Embers
            p.setPen(Qt.PenStyle.NoPen)
            for e in self._heat_embers:
                ex = 16 + e["x"]
                ey = 28 + e["y"]
                e_alpha = int(e["alpha"] * (0.6 + 0.4 * math.sin(t * 4.0 + e["phase"])) * 220)
                p.setBrush(QColor(255, 190, 50, e_alpha))
                p.drawEllipse(QPointF(ex, ey), e["r"], e["r"])

        elif icon_type == "wind":
            # 1. Aerodynamic Streaming Wind Ribbons
            p.setBrush(Qt.BrushStyle.NoBrush)
            for idx, y_pos in enumerate([48, 68, 88, 102]):
                speed_mod = 1.0 + idx * 0.3
                w_path = QPainterPath()
                w_path.moveTo(16, 28 + y_pos)
                for wx in range(0, 135, 12):
                    wy = y_pos + math.sin(t * 4.0 * speed_mod + wx * 0.07) * 4.0
                    w_path.lineTo(16 + wx, 28 + wy)
                tip_x = 16 + 135
                tip_y = 28 + y_pos + math.sin(t * 4.0 * speed_mod + 135 * 0.07) * 4.0
                w_path.quadTo(tip_x + 8, tip_y - 4, tip_x + 6, tip_y - 8)
                p.setPen(QPen(QColor(160, 210, 245, 60 + idx * 15), 1.4))
                p.drawPath(w_path)

            # 2. Fast Breeze Particle Streaks
            p.setPen(Qt.PenStyle.NoPen)
            for pw in self._wind_particles:
                px = 16 + pw["x"]
                py = 28 + pw["y"]
                p.setBrush(QColor(180, 230, 255, int(pw["alpha"] * 200)))
                p.drawRoundedRect(QRectF(px, py, pw["size"] * 2.5, 1.2), 0.6, 0.6)

        elif icon_type == "thunder":
            # 1. Lightning Ambient Flash
            if self._lightning_flash > 0:
                p.setBrush(QColor(180, 200, 255, int(self._lightning_flash * 120)))
                p.drawRect(hero_rect)

            # 2. Branching Lightning Bolt
            if self._lightning_flash > 0.15 and len(self._lightning_bolt_pts) >= 2:
                pen = QPen(QColor(255, 240, 100, int(self._lightning_flash * 255)), 2.0)
                pen.setJoinStyle(Qt.PenJoinStyle.MiterJoin)
                p.setPen(pen)
                p.setBrush(Qt.BrushStyle.NoBrush)
                l_path = QPainterPath()
                l_path.moveTo(16 + self._lightning_bolt_pts[0][0], 28 + self._lightning_bolt_pts[0][1])
                for pt in self._lightning_bolt_pts[1:]:
                    l_path.lineTo(16 + pt[0], 28 + pt[1])
                p.drawPath(l_path)

            # 3. Fast Rain Underneath
            p.setPen(QPen(QColor(120, 160, 220, 180), 1.2))
            for d in self._rain_drops[:20]:
                rx = 16 + d["x"]
                ry = 28 + d["y"]
                p.drawLine(QPointF(rx, ry), QPointF(rx + 2.5, ry + d["len"] * 1.2))

        elif icon_type == "snow":
            # 1. Drifting Sinusoidal Snowflakes
            p.setPen(Qt.PenStyle.NoPen)
            for f in self._snow_flakes:
                fx = 16 + f["x"]
                fy = 28 + f["y"]
                p.setBrush(QColor(255, 255, 255, int(f["alpha"] * 240)))
                p.drawEllipse(QPointF(fx, fy), f["r"], f["r"])

        elif icon_type == "night":
            # 1. Twinkling Starlight Field
            p.setPen(Qt.PenStyle.NoPen)
            for s in self._night_stars:
                sx = 16 + s["x"]
                sy = 28 + s["y"]
                star_alpha = int((0.3 + 0.7 * abs(math.sin(t * s["freq"] + s["phase"]))) * 230)
                p.setBrush(QColor(255, 255, 255, star_alpha))
                p.drawEllipse(QPointF(sx, sy), s["r"], s["r"])

        elif icon_type == "cloud":
            # 1. Atmospheric Soft Drifting Cloud Layers
            p.setPen(Qt.PenStyle.NoPen)
            for idx, drift_x in enumerate(self._cloud_drift):
                y_pos = 45 + idx * 22
                c_alpha = int(40 + idx * 25)
                p.setBrush(QColor(210, 230, 255, c_alpha))

                cloud_path = QPainterPath()
                cx = 16 + drift_x
                cy = 28 + y_pos
                cloud_path.addEllipse(QPointF(cx, cy), 22, 12)
                cloud_path.addEllipse(QPointF(cx + 14, cy - 5), 16, 11)
                cloud_path.addEllipse(QPointF(cx - 12, cy + 2), 14, 9)
                p.drawPath(cloud_path)

            # 2. Gentle Ambient Floating Motes
            for pw in self._wind_particles[:8]:
                px = 16 + pw["x"]
                py = 28 + pw["y"]
                p.setBrush(QColor(200, 230, 255, int(pw["alpha"] * 130)))
                p.drawEllipse(QPointF(px, py), 1.2, 1.2)

        else:
            # Sunny / Clear Sky Ambient Glow & Floating Light Specks
            p.setPen(Qt.PenStyle.NoPen)
            for pw in self._wind_particles[:6]:
                px = 16 + pw["x"]
                py = 28 + pw["y"]
                p.setBrush(QColor(255, 240, 180, int(pw["alpha"] * 150)))
                p.drawEllipse(QPointF(px, py), 1.4, 1.4)

        p.restore()

        # Hero Card Glass Rim
        p.strokePath(hero_path, QPen(QColor(255, 255, 255, 45), 1.0))

        # Vector Weather Graphic on Hero card
        self._draw_vector_weather_icon(p, 42, 54, icon_type=weather.icon_type, color=QColor(255, 255, 255), scale=1.8)

        # Big Temperature Text
        p.setFont(QFont("Segoe UI", 20, QFont.Weight.Bold))
        p.setPen(theme["text_primary"])
        p.drawText(QRect(72, 38, 90, 32), Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, f"{weather.temp_c}°C")

        # Condition string
        p.setFont(QFont("Segoe UI", 9, QFont.Weight.DemiBold))
        p.setPen(theme["text_primary"])
        cond_rect = QRect(24, 76, 134, 18)
        fm = p.fontMetrics()
        p.drawText(cond_rect, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, fm.elidedText(weather.condition, Qt.TextElideMode.ElideRight, 134))

        # Location City/Country
        p.setFont(QFont("Segoe UI", 8, QFont.Weight.Normal))
        p.setPen(theme["text_secondary"])
        city_rect = QRect(24, 96, 134, 16)
        p.drawText(city_rect, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, fm.elidedText(weather.city, Qt.TextElideMode.ElideRight, 134))

        # ── 2. Right Live Digital Clock & Details Card ───────────────────────
        clock_rect = QRect(174, 28, w - 190, 108)
        clock_path = QPainterPath()
        clock_path.addRoundedRect(QRectF(clock_rect), 12, 12)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(255, 255, 255, 14))
        p.drawPath(clock_path)
        p.strokePath(clock_path, QPen(QColor(255, 255, 255, 35), 1.0))

        # Precision Digital Clock (HH:MM:SS AM/PM)
        live_clock = time.strftime("%I:%M:%S %p")
        live_date = time.strftime("%A, %b %d, %Y")

        p.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        p.setPen(theme["text_primary"])
        p.drawText(QRect(186, 36, clock_rect.width() - 20, 26), Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, live_clock)

        # Full Date
        p.setFont(QFont("Segoe UI", 8, QFont.Weight.DemiBold))
        p.setPen(theme["text_secondary"])
        p.drawText(QRect(186, 62, clock_rect.width() - 20, 18), Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, live_date)

        # 2 Metric Pills: [💧 Humidity] [💨 Wind]
        pill_y = 86
        pill_w = (clock_rect.width() - 26) // 2

        # Humidity Pill
        p1 = QRect(184, pill_y, pill_w, 24)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(255, 255, 255, 18))
        p.drawRoundedRect(QRectF(p1), 6, 6)
        self._draw_vector_droplet(p, 194, pill_y + 12, color=QColor(96, 165, 250))
        p.setFont(QFont("Segoe UI", 8, QFont.Weight.DemiBold))
        p.setPen(theme["text_primary"])
        p.drawText(QRect(204, pill_y, pill_w - 22, 24), Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, f"{weather.humidity}")

        # Wind Pill
        p2 = QRect(184 + pill_w + 6, pill_y, pill_w, 24)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(255, 255, 255, 18))
        p.drawRoundedRect(QRectF(p2), 6, 6)
        self._draw_vector_wind(p, 184 + pill_w + 16, pill_y + 12, color=QColor(148, 163, 184))
        p.setFont(QFont("Segoe UI", 8, QFont.Weight.DemiBold))
        p.setPen(theme["text_primary"])
        p.drawText(QRect(184 + pill_w + 26, pill_y, pill_w - 28, 24), Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, f"{weather.wind_speed}")

    def _get_route_point_and_angle(self, pts: list, progress: float):
        """Calculates interpolated position and tangent heading angle along a polyline route."""
        if not pts:
            return (0.0, 0.0, 0.0)
        if len(pts) == 1:
            return (float(pts[0][0]), float(pts[0][1]), 0.0)

        # Calculate segment lengths
        seg_lens = []
        total_len = 0.0
        for i in range(len(pts) - 1):
            dx = pts[i + 1][0] - pts[i][0]
            dy = pts[i + 1][1] - pts[i][1]
            dist = math.hypot(dx, dy)
            seg_lens.append(dist)
            total_len += dist

        if total_len <= 0.001:
            return (float(pts[0][0]), float(pts[0][1]), 0.0)

        target_dist = (progress % 1.0) * total_len
        accum = 0.0

        for i, slen in enumerate(seg_lens):
            if accum + slen >= target_dist or i == len(seg_lens) - 1:
                seg_prog = 0.0 if slen <= 0.001 else (target_dist - accum) / slen
                seg_prog = max(0.0, min(1.0, seg_prog))
                p0 = pts[i]
                p1 = pts[i + 1]
                cur_x = p0[0] + (p1[0] - p0[0]) * seg_prog
                cur_y = p0[1] + (p1[1] - p0[1]) * seg_prog
                dx = p1[0] - p0[0]
                dy = p1[1] - p0[1]
                heading_deg = math.degrees(math.atan2(dx, -dy))
                return (cur_x, cur_y, heading_deg)
            accum += slen

        return (float(pts[-1][0]), float(pts[-1][1]), 0.0)

    def _draw_mini_route_map(self, p: QPainter, rect: QRect, mode: str = "split", theme: dict = None):
        """Renders an ultra-modern vector Google Maps canvas with terrain, waterways, road grid, traffic, and glowing animated GPS route."""
        rx, ry, rw, rh = rect.x(), rect.y(), rect.width(), rect.height()
        map_path = QPainterPath()
        map_path.addRoundedRect(QRectF(rect), 12, 12)

        p.save()
        p.setClipPath(map_path)

        # 1. Base Map Terrain (Deep Dark Navigation Slate)
        terrain_grad = QLinearGradient(rx, ry, rx + rw, ry + rh)
        terrain_grad.setColorAt(0.0, QColor(14, 22, 33))
        terrain_grad.setColorAt(0.5, QColor(11, 18, 28))
        terrain_grad.setColorAt(1.0, QColor(8, 14, 22))
        p.fillPath(map_path, terrain_grad)

        # 2. Water Body / Coastal Bay / River
        water_path = QPainterPath()
        if mode == "panoramic":
            water_path.moveTo(rx, ry + 20)
            water_path.cubicTo(rx + rw * 0.3, ry - 10, rx + rw * 0.45, ry + 55, rx + rw, ry + 25)
            water_path.lineTo(rx + rw, ry)
            water_path.lineTo(rx, ry)
            water_path.closeSubpath()
        else:
            water_path.moveTo(rx, ry + 28)
            water_path.cubicTo(rx + rw * 0.35, ry + 8, rx + rw * 0.6, ry + 42, rx + rw, ry + 22)
            water_path.lineTo(rx + rw, ry)
            water_path.lineTo(rx, ry)
            water_path.closeSubpath()

        water_color = QColor(13, 38, 64, 220)
        p.fillPath(water_path, water_color)

        # Subtle wave reflection along coastline
        p.setPen(QPen(QColor(0, 180, 255, 45), 1.2, Qt.PenStyle.DashLine))
        p.drawPath(water_path)

        # 3. Secondary City Road Grid & Blocks
        p.setPen(QPen(QColor(38, 52, 72, 110), 1.6))
        grid_step = 26
        # Horizontal streets
        for gy in range(ry + 16, ry + rh - 10, grid_step):
            p.drawLine(rx + 8, gy, rx + rw - 8, gy)
        # Vertical / Cross streets
        for gx in range(rx + 20, rx + rw - 10, grid_step):
            p.drawLine(gx, ry + 12, gx, ry + rh - 12)

        # 4. Major Arterial Avenues & Highway Overpasses
        arterial_path = QPainterPath()
        if mode == "panoramic":
            arterial_path.moveTo(rx + 10, ry + rh - 30)
            arterial_path.cubicTo(rx + rw * 0.3, ry + rh - 40, rx + rw * 0.5, ry + 60, rx + rw - 15, ry + 45)
        else:
            arterial_path.moveTo(rx + 12, ry + rh - 24)
            arterial_path.cubicTo(rx + rw * 0.4, ry + rh - 35, rx + rw * 0.6, ry + 55, rx + rw - 12, ry + 38)

        # Road base (wide dark slate)
        p.setPen(QPen(QColor(24, 34, 48, 230), 6.5, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
        p.drawPath(arterial_path)
        # Road asphalt core
        p.setPen(QPen(QColor(60, 78, 102, 190), 4.2, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
        p.drawPath(arterial_path)

        # 5. Live Traffic Overlay (Green / Orange / Red Congestion Flow)
        if self._traffic_enabled:
            # Smooth Green flow segment
            p.setPen(QPen(QColor(34, 197, 94, 180), 2.2, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            p.drawLine(int(rx + rw * 0.1), int(ry + rh - 28), int(rx + rw * 0.42), int(ry + rh * 0.65))
            # Moderate Amber traffic segment
            p.setPen(QPen(QColor(245, 158, 11, 200), 2.2, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            p.drawLine(int(rx + rw * 0.42), int(ry + rh * 0.65), int(rx + rw * 0.68), int(ry + rh * 0.48))
            # Smooth Green flow to destination
            p.setPen(QPen(QColor(34, 197, 94, 180), 2.2, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            p.drawLine(int(rx + rw * 0.68), int(ry + rh * 0.48), int(rx + rw - 18), int(ry + 42))

        # 6. Waypoints & GPS Navigation Route
        if mode == "panoramic":
            route_pts = [
                (rx + 30, ry + rh - 24),
                (rx + rw * 0.22, ry + rh - 30),
                (rx + rw * 0.38, ry + 62),
                (rx + rw * 0.58, ry + 56),
                (rx + rw * 0.76, ry + 78),
                (rx + rw - 32, ry + 36),
            ]
        else:
            route_pts = [
                (rx + 16, ry + rh - 22),
                (rx + rw * 0.28, ry + rh - 28),
                (rx + rw * 0.46, ry + 54),
                (rx + rw * 0.68, ry + 50),
                (rx + rw * 0.82, ry + 68),
                (rx + rw - 22, ry + 34),
            ]

        # Draw Multi-Layer Glowing GPS Route Path
        route_path = QPainterPath()
        route_path.moveTo(route_pts[0][0], route_pts[0][1])
        for pt in route_pts[1:]:
            route_path.lineTo(pt[0], pt[1])

        # Layer A: Outer Neon Cyan Ambient Glow
        glow_pen = QPen(QColor(0, 195, 255, 70), 7.5, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
        p.strokePath(route_path, glow_pen)

        # Layer B: Vibrant Google Blue Core Line
        core_pen = QPen(QColor(26, 115, 232), 4.2, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
        p.strokePath(route_path, core_pen)

        # Layer C: Inner Neon Cyan Highlight
        inner_pen = QPen(QColor(0, 229, 255), 2.0, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
        p.strokePath(route_path, inner_pen)

        # Layer D: Animated Forward Pulse Chevrons / Moving Dashes
        dash_pen = QPen(QColor(255, 255, 255, 210), 1.6, Qt.PenStyle.CustomDashLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
        dash_pen.setDashPattern([3.0, 5.0])
        dash_pen.setDashOffset(-self._anim_time * 22.0)
        p.strokePath(route_path, dash_pen)

        # 7. Start Point (Origin Pin / Pulse Dot)
        sx, sy = route_pts[0]
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(34, 197, 94, 90))
        p.drawEllipse(QPointF(sx, sy), 6.5, 6.5)
        p.setBrush(QColor(34, 197, 94))
        p.drawEllipse(QPointF(sx, sy), 4.0, 4.0)
        p.setBrush(QColor(255, 255, 255))
        p.drawEllipse(QPointF(sx, sy), 1.8, 1.8)

        # 8. Destination Point (Google Maps Red Pin)
        dx, dy = route_pts[-1]
        self._draw_vector_map_pin(p, int(dx), int(dy + 6))

        # 9. Live Moving Vehicle / GPS Chevron
        vx, vy, heading_ang = self._get_route_point_and_angle(route_pts, self._nav_progress)

        # Radar Ripple Ring expanding from vehicle
        ripple_frac = (self._anim_time * 1.6) % 1.0
        ripple_r = 5.0 + ripple_frac * 11.0
        ripple_alpha = int(180 * (1.0 - ripple_frac))
        p.setPen(QPen(QColor(0, 195, 255, ripple_alpha), 1.4))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawEllipse(QPointF(vx, vy), ripple_r, ripple_r)

        # Rotated GPS Navigation Vehicle Arrow
        p.save()
        p.translate(vx, vy)
        p.rotate(heading_ang)

        # Vehicle Arrow drop shadow
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(0, 0, 0, 140))
        shadow_poly = QPolygonF([QPointF(0, -6), QPointF(5, 5), QPointF(0, 2.5), QPointF(-5, 5)])
        p.drawPolygon(shadow_poly)

        # Neon Cyan / White Vehicle Body
        p.setBrush(QColor(0, 229, 255))
        veh_poly = QPolygonF([QPointF(0, -7), QPointF(5.5, 4.5), QPointF(0, 2.0), QPointF(-5.5, 4.5)])
        p.drawPolygon(veh_poly)

        # Inner White Cockpit Core
        p.setBrush(QColor(255, 255, 255))
        inner_veh = QPolygonF([QPointF(0, -5), QPointF(2.8, 3.0), QPointF(0, 1.2), QPointF(-2.8, 3.0)])
        p.drawPolygon(inner_veh)
        p.restore()

        # 10. Top Location & Navigation HUD Pill Overlay
        city_name = "Marine Drive, Kochi"
        if self._weather and self._weather.current_weather and self._weather.current_weather.city:
            city_name = f"{self._weather.current_weather.city}"

        p.setFont(QFont("Segoe UI", 7, QFont.Weight.Bold))
        fm = p.fontMetrics()
        full_text = f"📍 {city_name} • Live GPS"
        max_hud_w = rw - 44 if mode == "panoramic" else rw - 24
        req_w = fm.horizontalAdvance(full_text) + 26
        hud_w = max(110, min(req_w, max_hud_w))

        hud_rect = QRect(rx + 8, ry + 6, hud_w, 20)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(10, 16, 26, 220))
        p.drawRoundedRect(QRectF(hud_rect), 6, 6)
        p.setPen(QPen(QColor(255, 255, 255, 45), 1.0))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRoundedRect(QRectF(hud_rect), 6, 6)

        # Green live GPS pulse in HUD
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(34, 197, 94))
        p.drawEllipse(QPointF(rx + 16, ry + 16), 3.0, 3.0)

        p.setPen(QColor(255, 255, 255))
        elided_hud = fm.elidedText(full_text, Qt.TextElideMode.ElideRight, hud_w - 24)
        p.drawText(QRect(rx + 22, ry + 6, hud_w - 24, 20), Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, elided_hud)

        # 11. Interactive Bottom Action Chips Overlay
        chip_y = ry + rh - 25
        if mode == "panoramic":
            c_w = (rw - 36) // 4
            chips = [
                ("⤡ Split", rx + 8, QColor(0, 122, 255), "map_chip_split"),
                ("🚦 Traffic" if self._traffic_enabled else "⚪ Traffic", rx + 8 + (c_w + 6), QColor(34, 197, 94) if self._traffic_enabled else QColor(148, 163, 184), "map_chip_traffic"),
                ("⚡ Route", rx + 8 + (c_w + 6) * 2, QColor(245, 158, 11), "map_chip_reset"),
                ("🌐 Maps", rx + 8 + (c_w + 6) * 3, QColor(234, 67, 53), "map_chip_open"),
            ]
        else:
            c_w = (rw - 28) // 4
            chips = [
                ("⤢ Full", rx + 6, QColor(0, 122, 255), "map_chip_panoramic"),
                ("🚦 Traf" if self._traffic_enabled else "⚪ Traf", rx + 6 + (c_w + 5), QColor(34, 197, 94) if self._traffic_enabled else QColor(148, 163, 184), "map_chip_traffic"),
                ("⚡ Route", rx + 6 + (c_w + 5) * 2, QColor(245, 158, 11), "map_chip_reset"),
                ("🌐 Maps", rx + 6 + (c_w + 5) * 3, QColor(234, 67, 53), "map_chip_open"),
            ]

        for label, cx, col, b_key in chips:
            bg_col, border_col, scale, _, _ = self._get_button_style(b_key, QColor(10, 16, 26, 230))
            p.save()
            bcx, bcy = cx + c_w / 2.0, chip_y + 10.0
            p.translate(bcx, bcy)
            p.scale(scale, scale)
            p.translate(-bcx, -bcy)

            p.setPen(QPen(border_col, 1.0))
            p.setBrush(bg_col)
            p.drawRoundedRect(QRectF(cx, chip_y, c_w, 20), 5, 5)

            p.setFont(QFont("Segoe UI", 7, QFont.Weight.DemiBold))
            p.setPen(col)
            p.drawText(QRect(cx, chip_y, c_w, 20), Qt.AlignmentFlag.AlignCenter, label)
            p.restore()

        p.restore()
        p.strokePath(map_path, QPen(QColor(255, 255, 255, 40), 1.0))

    def _paint_map(self, p: QPainter, theme: dict, w: int, h: int):
        self._paint_tab_headers(p, theme, w, active_tab="map")

        if self._map_view_mode == "panoramic":
            # ── Panoramic Ultra-Wide Live Route Map Mode ───────────────────────
            map_rect = QRect(16, 28, w - 32, 108)
            self._draw_mini_route_map(p, map_rect, mode="panoramic", theme=theme)

            # Miniature Top-Right Compass Dial Overlay in Panoramic Mode
            p.save()
            comp_cx, comp_cy = w - 42, 42
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor(10, 16, 26, 200))
            p.drawEllipse(QPointF(comp_cx, comp_cy), 15, 15)
            p.setPen(QPen(QColor(255, 255, 255, 50), 1.0))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawEllipse(QPointF(comp_cx, comp_cy), 15, 15)
            self._draw_precision_compass(p, comp_cx, comp_cy, r=12, heading=self._compass_current_heading, theme=theme)
            p.restore()
            return

        # ── Split Mode: (Left Card: Compass / Turn HUD | Right Card: Live Map) ──
        compass_rect = QRect(16, 28, 140, 108)
        compass_path = QPainterPath()
        compass_path.addRoundedRect(QRectF(compass_rect), 12, 12)

        p.save()
        p.setClipPath(compass_path)

        # Subtle dark radar gradient inside left card
        radar_grad = QRadialGradient(86, 74, 65)
        radar_grad.setColorAt(0.0, QColor(14, 24, 38, 220))
        radar_grad.setColorAt(0.7, QColor(10, 16, 26, 240))
        radar_grad.setColorAt(1.0, QColor(6, 10, 16, 250))
        p.fillPath(compass_path, radar_grad)

        if self._compass_left_view == "turn_hud":
            # ── Left View: Turn-by-Turn Navigation HUD ────────────────────────
            # Top Turn Maneuver Badge
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor(34, 197, 94, 220))
            p.drawRoundedRect(QRectF(26, 36, 42, 28), 6, 6)
            p.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
            p.setPen(QColor(255, 255, 255))
            p.drawText(QRect(26, 36, 42, 28), Qt.AlignmentFlag.AlignCenter, "↱")

            p.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
            p.setPen(QColor(255, 255, 255))
            p.drawText(QRect(74, 34, 76, 18), Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, "In 200m")

            p.setFont(QFont("Segoe UI", 7, QFont.Weight.DemiBold))
            p.setPen(QColor(148, 163, 184))
            p.drawText(QRect(74, 50, 76, 14), Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, "Turn Right")

            # Street / Avenue Name
            p.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
            p.setPen(theme["text_primary"])
            p.drawText(QRect(22, 68, 128, 18), Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, "Marine Way Blvd")

            # ETA & Distance Pill
            p.setFont(QFont("Segoe UI", 7, QFont.Weight.DemiBold))
            p.setPen(QColor(34, 197, 94))
            p.drawText(QRect(22, 86, 128, 16), Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, "12 min • 4.2 km • Fast")

            p.setFont(QFont("Segoe UI", 6))
            p.setPen(QColor(96, 165, 250))
            p.drawText(QRect(16, 114, 140, 14), Qt.AlignmentFlag.AlignCenter, "Tap for Compass 🧭")
        else:
            # ── Left View: Precision Compass Dial & Azimuth ───────────────────
            heading = self._compass_current_heading
            self._draw_precision_compass(p, 86, 70, r=32, heading=heading, theme=theme)

            # Azimuth Degrees & Cardinal Text below Compass
            cardinals = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE", "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"]
            card_idx = int((heading + 11.25) / 22.5) % 16
            card_str = cardinals[card_idx]
            deg_str = f"{int(heading):03d}° {card_str}"

            p.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
            p.setPen(theme["text_primary"])
            p.drawText(QRect(16, 108, 140, 16), Qt.AlignmentFlag.AlignCenter, deg_str)

            p.setFont(QFont("Segoe UI", 6))
            p.setPen(QColor(96, 165, 250))
            p.drawText(QRect(16, 122, 140, 12), Qt.AlignmentFlag.AlignCenter, f"{self._compass_mode.capitalize()} • Tap for Turn HUD")

        p.restore()
        p.strokePath(compass_path, QPen(QColor(255, 255, 255, 35), 1.0))

        # ── 2. Right Card: Live Mini Route Map Canvas ──────────────────────
        map_rect = QRect(164, 28, w - 180, 108)
        self._draw_mini_route_map(p, map_rect, mode="split", theme=theme)

    def _paint_clipboard(self, p: QPainter, theme: dict, w: int, h: int):
        self._paint_tab_headers(p, theme, w, active_tab="clipboard")

        preview_str = self._clipboard_preview_text.strip() if self._clipboard_preview_text else ""
        is_copied = (time.monotonic() - self._clipboard_copy_feedback) < 1.8

        # 1. Header: Dynamic Smart Badge & Stats (y: 6 to 24)
        if self._last_clipboard_url:
            badge_rect = QRect(16, 6, 126, 20)
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor(0, 122, 255, 45))
            p.drawRoundedRect(QRectF(badge_rect), 5, 5)
            self._draw_vector_globe(p, 26, 16, r=5, color=QColor(96, 165, 250))
            p.setFont(QFont("Segoe UI", 7, QFont.Weight.Bold))
            p.setPen(QColor(96, 165, 250))
            p.drawText(QRect(36, 6, 102, 20), Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, "LINK DETECTED")

        elif self._clipboard_color_hex:
            badge_rect = QRect(16, 6, 124, 20)
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor(255, 255, 255, 18))
            p.drawRoundedRect(QRectF(badge_rect), 5, 5)
            self._draw_vector_swatch(p, 26, 16, self._clipboard_color_hex)
            p.setFont(QFont("Segoe UI", 7, QFont.Weight.Bold))
            p.setPen(theme["text_primary"])
            p.drawText(QRect(36, 6, 98, 20), Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, f"COLOR {self._clipboard_color_hex.upper()}")

        elif self._clipboard_calc_result:
            badge_rect = QRect(16, 6, 128, 20)
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor(245, 158, 11, 45))
            p.drawRoundedRect(QRectF(badge_rect), 5, 5)
            self._draw_vector_calc(p, 26, 16, color=QColor(251, 191, 36))
            p.setFont(QFont("Segoe UI", 7, QFont.Weight.Bold))
            p.setPen(QColor(251, 191, 36))
            p.drawText(QRect(36, 6, 104, 20), Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, f"CALC = {self._clipboard_calc_result}")

        else:
            badge_rect = QRect(16, 6, 112, 20)
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor(255, 255, 255, 18))
            p.drawRoundedRect(QRectF(badge_rect), 5, 5)
            self._draw_vector_clipboard_icon(p, 26, 16, color=theme["text_primary"])
            p.setFont(QFont("Segoe UI", 7, QFont.Weight.Bold))
            p.setPen(theme["text_primary"])
            p.drawText(QRect(36, 6, 88, 20), Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, "CLIPBOARD")

        # Word & Char Count statistics (using precomputed cached metrics - zero lag)
        if self._clipboard_char_count > 0:
            words = self._clipboard_word_count
            chars = self._clipboard_char_count
            p.setFont(QFont("Segoe UI", 7, QFont.Weight.DemiBold))
            p.setPen(theme["text_secondary"])
            p.drawText(QRect(148, 6, 110, 20), Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, f"{words}w • {chars}c")

        # 2. History Reel Chips (y: 28 to 44, h: 16)
        history = self._clipboard_history[:4]
        if history:
            hx = 16
            for idx, clip_item in enumerate(history):
                is_cur = (clip_item == preview_str or clip_item == self._last_clipboard_text[:500].strip())
                chip_w = 84
                b_key = f"clip_hist_{idx}"
                chip_bg, chip_border, chip_scale, _, _ = self._get_button_style(b_key, QColor(0, 122, 255, 60) if is_cur else QColor(255, 255, 255, 14))

                p.save()
                bcx, bcy = hx + chip_w / 2.0, 36.0
                p.translate(bcx, bcy)
                p.scale(chip_scale, chip_scale)
                p.translate(-bcx, -bcy)

                p.setPen(QPen(chip_border, 1.0))
                p.setBrush(chip_bg)
                p.drawRoundedRect(QRectF(hx, 28, chip_w, 16), 4, 4)

                p.setFont(QFont("Segoe UI", 7, QFont.Weight.Bold if is_cur else QFont.Weight.Normal))
                p.setPen(QColor(96, 165, 250) if is_cur else theme["text_secondary"])
                fm = p.fontMetrics()
                clean_snippet = clip_item[:40].replace("\n", " ")
                elided_chip = fm.elidedText(f"{idx+1}: {clean_snippet}", Qt.TextElideMode.ElideRight, chip_w - 8)
                p.drawText(QRect(hx + 4, 28, chip_w - 8, 16), Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, elided_chip)
                p.restore()

                hx += chip_w + 6
                if hx + chip_w > w - 16:
                    break

        # 3. Main Snippet Preview Card (y: 48 to 102, h: 54)
        snippet_rect = QRect(16, 48, w - 32, 54)
        snippet_path = QPainterPath()
        snippet_path.addRoundedRect(QRectF(snippet_rect), 8, 8)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(255, 255, 255, 14))
        p.drawPath(snippet_path)
        p.strokePath(snippet_path, QPen(QColor(255, 255, 255, 30), 1.0))

        if not preview_str:
            p.setFont(QFont("Segoe UI", 8))
            p.setPen(theme["text_secondary"])
            p.drawText(QRect(26, 48, snippet_rect.width() - 20, 54), Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, "Clipboard is empty. Copy text, links, color codes, or math equations anywhere!")

        elif self._clipboard_calc_result:
            p.setFont(QFont("Segoe UI", 8, QFont.Weight.DemiBold))
            p.setPen(theme["text_secondary"])
            p.drawText(QRect(26, 52, snippet_rect.width() - 150, 20), Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, preview_str[:100])

            p.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
            p.setPen(QColor(52, 199, 89))
            p.drawText(QRect(26, 72, snippet_rect.width() - 150, 24), Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, f"= {self._clipboard_calc_result}")

            # Badge pill on right
            ans_rect = QRect(w - 140, 56, 96, 36)
            p.setBrush(QColor(52, 199, 89, 35))
            p.drawRoundedRect(QRectF(ans_rect), 6, 6)
            p.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
            p.setPen(QColor(52, 199, 89))
            p.drawText(ans_rect, Qt.AlignmentFlag.AlignCenter, "EVALUATED ✓")

        elif self._clipboard_color_hex:
            # Color swatch block on left
            swatch_rect = QRect(26, 56, 36, 36)
            p.setPen(QPen(QColor(255, 255, 255, 100), 1.0))
            try:
                p.setBrush(QColor(self._clipboard_color_hex))
            except Exception:
                p.setBrush(QColor(255, 255, 255))
            p.drawRoundedRect(QRectF(swatch_rect), 6, 6)

            # Hex and RGB details
            p.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
            p.setPen(theme["text_primary"])
            p.drawText(QRect(70, 54, 180, 20), Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, self._clipboard_color_hex.upper())

            c = QColor(self._clipboard_color_hex)
            p.setFont(QFont("Segoe UI", 8))
            p.setPen(theme["text_secondary"])
            p.drawText(QRect(70, 74, 180, 18), Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, f"RGB: {c.red()}, {c.green()}, {c.blue()}")

        else:
            p.setFont(QFont("Segoe UI", 8))
            p.setPen(theme["text_primary"])
            p.drawText(QRect(26, 52, snippet_rect.width() - 20, 46), Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft | Qt.TextFlag.TextWordWrap, preview_str[:180])

        # 4. 5 Smart Action Buttons (y: 108 to 138)
        btn_y = 108
        buttons = []

        # B1: Primary action
        if self._last_clipboard_url:
            buttons.append(("Open", 16, self._draw_vector_globe, QColor(0, 122, 255), QColor(255, 255, 255), "clip_act_link"))
        elif self._clipboard_calc_result:
            buttons.append(("Result", 16, self._draw_vector_calc, QColor(245, 158, 11), QColor(255, 255, 255), "clip_act_link"))
        else:
            buttons.append(("Search", 16, self._draw_vector_search, QColor(0, 122, 255), QColor(255, 255, 255), "clip_act_link"))

        # B2: Ask GPT in Brave Browser
        buttons.append(("Ask GPT", 89, lambda p, cx, cy: self._draw_vector_chatgpt(p, cx, cy, color=QColor(16, 163, 127)), QColor(255, 255, 255, 20), QColor(16, 185, 129), "clip_act_gpt"))

        # B3: Search or Case Aa
        if self._last_clipboard_url or self._clipboard_calc_result:
            buttons.append(("Search", 162, self._draw_vector_search, QColor(255, 255, 255, 20), theme["text_primary"], "clip_act_case"))
        else:
            buttons.append(("Case Aa", 162, self._draw_vector_case, QColor(255, 255, 255, 20), theme["text_primary"], "clip_act_case"))

        # B4: Copy with dynamic feedback
        copy_bg = QColor(16, 185, 129, 60) if is_copied else QColor(255, 255, 255, 20)
        copy_col = QColor(52, 199, 89) if is_copied else theme["text_primary"]
        copy_label = "COPIED!" if is_copied else "Copy"
        buttons.append((copy_label, 235, self._draw_vector_copy, copy_bg, copy_col, "clip_act_copy"))

        # B5: Clear
        buttons.append(("Clear", 308, self._draw_vector_trash, QColor(255, 255, 255, 20), QColor(255, 100, 100), "clip_act_clear"))

        for label, bx, draw_fn, bg_col, txt_col, b_key in buttons:
            b_w = 66
            c_bg, c_border, scale, _, _ = self._get_button_style(b_key, bg_col)
            p.save()
            bcx, bcy = bx + b_w / 2.0, btn_y + 14.0
            p.translate(bcx, bcy)
            p.scale(scale, scale)
            p.translate(-bcx, -bcy)

            p.setPen(QPen(c_border, 1.0))
            p.setBrush(c_bg)
            p.drawRoundedRect(QRectF(bx, btn_y, b_w, 28), 6, 6)

            # Draw vector icon
            draw_fn(p, bx + 12, btn_y + 14)

            # Draw label
            p.setFont(QFont("Segoe UI", 7, QFont.Weight.Bold if label in ["COPIED!", "Ask GPT", "Open", "Result"] else QFont.Weight.DemiBold))
            p.setPen(txt_col)
            p.drawText(QRect(bx + 18, btn_y, b_w - 18, 28), Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignCenter, label)
            p.restore()

    def _paint_tools(self, p: QPainter, theme: dict, w: int, h: int):
        self._paint_tab_headers(p, theme, w, active_tab="tools")

        # 1. Header: Control Center Status
        cur_time = time.strftime("%I:%M %p • %a, %b %d")
        p.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        p.setPen(theme["text_primary"])
        self._draw_vector_bolt(p, 26, 36, color=theme["accent"])
        p.drawText(QRect(36, 26, 200, 20), Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, f"Control Center • {cur_time}")

        # 2. Performance Row (CPU & RAM) with smooth live animation
        cpu_val = max(1.0, min(100.0, self._anim_cpu))
        ram_val = max(1.0, min(100.0, self._anim_ram))
        card_w = (w - 42) // 2
        card_y = 48
        card_h = 28

        # CPU Card
        c1 = QRect(16, card_y, card_w, card_h)
        cpu_bg, cpu_border, _, _, _ = self._get_button_style("tool_cpu", QColor(255, 255, 255, 14))
        p.setPen(QPen(cpu_border, 1.0))
        p.setBrush(cpu_bg)
        p.drawRoundedRect(QRectF(c1), 6, 6)
        self._draw_vector_cpu(p, 26, card_y + 14, color=QColor(52, 199, 89))
        p.setFont(QFont("Segoe UI", 8, QFont.Weight.DemiBold))
        p.setPen(theme["text_primary"])
        p.drawText(QRect(38, card_y + 6, 50, 16), Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, f"CPU {cpu_val:.0f}%")
        bar_x = 90
        bar_w = card_w - 80
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(255, 255, 255, 20))
        p.drawRoundedRect(QRectF(bar_x, card_y + 12, bar_w, 4), 2, 2)
        p.setBrush(QColor(52, 199, 89) if cpu_val < 75 else QColor(255, 159, 10))
        p.drawRoundedRect(QRectF(bar_x, card_y + 12, max(2.0, bar_w * (cpu_val / 100.0)), 4), 2, 2)

        # RAM Card
        c2 = QRect(16 + card_w + 10, card_y, card_w, card_h)
        ram_bg, ram_border, _, _, _ = self._get_button_style("tool_ram", QColor(255, 255, 255, 14))
        p.setPen(QPen(ram_border, 1.0))
        p.setBrush(ram_bg)
        p.drawRoundedRect(QRectF(c2), 6, 6)
        self._draw_vector_ram(p, 16 + card_w + 20, card_y + 14, color=QColor(0, 122, 255))
        p.setFont(QFont("Segoe UI", 8, QFont.Weight.DemiBold))
        p.setPen(theme["text_primary"])
        p.drawText(QRect(16 + card_w + 32, card_y + 6, 50, 16), Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, f"RAM {ram_val:.0f}%")
        r_bar_x = 16 + card_w + 84
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(255, 255, 255, 20))
        p.drawRoundedRect(QRectF(r_bar_x, card_y + 12, bar_w, 4), 2, 2)
        p.setBrush(QColor(0, 122, 255) if ram_val < 80 else QColor(255, 69, 58))
        p.drawRoundedRect(QRectF(r_bar_x, card_y + 12, max(2.0, bar_w * (ram_val / 100.0)), 4), 2, 2)

        # 3. Bluetooth Connected Devices Card (Row 2) with Hover Glow
        bt_info = self._last_bluetooth_info or BluetoothInfo()
        bt_rect = QRect(16, 80, w - 32, 28)
        bt_bg, bt_border, _, _, _ = self._get_button_style("tool_bluetooth", QColor(255, 255, 255, 14))
        p.setPen(QPen(bt_border, 1.0))
        p.setBrush(bt_bg)
        p.drawRoundedRect(QRectF(bt_rect), 6, 6)

        is_bt_conn = bt_info.has_connected
        bt_color = QColor(0, 122, 255) if is_bt_conn else QColor(148, 163, 184)
        self._draw_vector_bluetooth(p, 28, 94, is_connected=is_bt_conn, color=bt_color)

        p.setFont(QFont("Segoe UI", 8, QFont.Weight.DemiBold))
        p.setPen(theme["text_primary"])
        bt_name = bt_info.primary_device_name
        fm = p.fontMetrics()
        p.drawText(QRect(42, 80, w - 140, 28), Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, fm.elidedText(bt_name, Qt.TextElideMode.ElideRight, w - 140))

        # Status badge on right
        badge_w = 72
        badge_rect = QRect(w - 16 - badge_w - 6, 84, badge_w, 20)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(0, 122, 255, 60) if is_bt_conn else QColor(255, 255, 255, 18))
        p.drawRoundedRect(QRectF(badge_rect), 4, 4)
        p.setFont(QFont("Segoe UI", 7, QFont.Weight.Bold))
        p.setPen(QColor(96, 165, 250) if is_bt_conn else theme["text_secondary"])
        p.drawText(badge_rect, Qt.AlignmentFlag.AlignCenter, "CONNECTED" if is_bt_conn else "STANDBY")

        # 4. 7 Quick Desktop Tool Buttons (Bottom Row) with Tactile Spring Scaling
        btn_y = h - 38
        tools = [
            ("Snip", 16, self._draw_vector_scissors, theme["text_primary"], "tool_snip"),
            ("Maps", 68, self._draw_vector_map_pin, QColor(234, 67, 53), "tool_maps"),
            ("Calc", 120, self._draw_vector_calc, theme["text_primary"], "tool_calc"),
            ("Notes", 172, self._draw_vector_notes, theme["text_primary"], "tool_notes"),
            ("GPT", 224, lambda p, cx, cy: self._draw_vector_chatgpt(p, cx, cy, color=QColor(16, 163, 127)), QColor(16, 185, 129), "tool_gpt"),
            ("Mute", 276, lambda p, cx, cy: self._draw_vector_speaker(p, cx, cy, level=0), theme["text_primary"], "tool_mute"),
            ("Lock", 328, self._draw_vector_lock, theme["text_primary"], "tool_lock"),
        ]

        for label, bx, draw_fn, txt_col, b_key in tools:
            b_w = 48
            t_bg, t_border, scale, _, _ = self._get_button_style(b_key, QColor(255, 255, 255, 18))

            p.save()
            bcx, bcy = bx + b_w / 2.0, btn_y + 14.0
            p.translate(bcx, bcy)
            p.scale(scale, scale)
            p.translate(-bcx, -bcy)

            p.setPen(QPen(t_border, 1.0))
            p.setBrush(t_bg)
            p.drawRoundedRect(QRectF(bx, btn_y, b_w, 28), 6, 6)

            # Icon
            draw_fn(p, bx + 12, btn_y + 14)

            # Label text
            p.setFont(QFont("Segoe UI", 7, QFont.Weight.Bold if label in ["GPT", "Maps"] else QFont.Weight.DemiBold))
            p.setPen(txt_col)
            p.drawText(QRect(bx + 18, btn_y, b_w - 18, 28), Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignCenter, label)
            p.restore()

    def _paint_tab_headers(self, p: QPainter, theme: dict, w: int, active_tab: str):
        # Top-left subtle collapse indicator notch with tactile hover/press
        col_hover = self._btn_hover_anim.get("collapse", 0.0)
        col_press = self._btn_press_anim.get("collapse", 0.0)
        p.save()
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(255, 255, 255, int(40 + col_hover * 75)))
        notch_w = 24.0 * (1.0 - 0.12 * col_press)
        notch_x = 14.0 + (24.0 - notch_w) / 2.0
        p.drawRoundedRect(QRectF(notch_x, 11, notch_w, 5), 2.5, 2.5)
        p.restore()

        # OriginOS Fluid Sliding Active Tab Glass Pill Indicator with Squash-and-Stretch
        p.save()
        p.setPen(Qt.PenStyle.NoPen)
        # Soft ambient glow behind sliding pill
        p.setBrush(QColor(255, 255, 255, 20))
        p.drawRoundedRect(QRectF(self._indicator_x - 1, 5, self._indicator_w + 2, 22), 6, 6)
        # Main sliding glass pill
        p.setBrush(QColor(255, 255, 255, 45))
        p.drawRoundedRect(QRectF(self._indicator_x, 6, self._indicator_w, 20), 5, 5)
        p.restore()

        # 5 Tabs: Music | Weather | Maps & Compass | Clipboard | Tools with dynamic live vector icons & hover bounce
        tabs = [
            ("music", w - 138),
            ("weather", w - 110),
            ("map", w - 82),
            ("clipboard", w - 54),
            ("tools", w - 26)
        ]
        for name, tx in tabs:
            rect = QRect(tx - 6, 6, 22, 20)
            cx, cy = rect.center().x(), rect.center().y()
            is_active = (name == active_tab)
            h_val = self._btn_hover_anim.get(f"tab_{name}", 0.0)
            p_val = self._btn_press_anim.get(f"tab_{name}", 0.0)
            tab_scale = (1.0 + 0.12 * h_val) * (1.0 - 0.10 * p_val)

            p.save()
            p.translate(cx, cy)
            p.scale(tab_scale, tab_scale)
            p.translate(-cx, -cy)

            if is_active:
                icon_color = theme["accent"]
            else:
                if h_val > 0.01:
                    p.save()
                    p.setPen(Qt.PenStyle.NoPen)
                    p.setBrush(QColor(255, 255, 255, int(h_val * 32)))
                    p.drawRoundedRect(QRectF(rect), 5, 5)
                    p.restore()
                    icon_color = QColor(255, 255, 255, min(255, int(150 + h_val * 95)))
                else:
                    icon_color = theme["text_secondary"]

            if name == "music":
                self._draw_vector_note(p, cx, cy, color=icon_color)
            elif name == "weather":
                weather_icon = self._last_weather_info.icon_type if self._last_weather_info else "sun"
                self._draw_vector_weather_icon(p, cx, cy, icon_type=weather_icon, color=icon_color, scale=0.85)
            elif name == "map":
                self._draw_vector_compass_icon(p, cx, cy, color=icon_color)
            elif name == "clipboard":
                self._draw_vector_clipboard_icon(p, cx, cy, color=icon_color)
            elif name == "tools":
                self._draw_vector_bolt(p, cx, cy, color=icon_color)

            p.restore()


if __name__ == "__main__":
    from settings import Settings
    app = QApplication(sys.argv)
    island = OriginIsland(settings=Settings())
    island.show()
    sys.exit(app.exec())


