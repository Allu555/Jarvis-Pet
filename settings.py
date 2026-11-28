import json
import os
import re
from pathlib import Path
from typing import Any, Dict, Optional

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QSlider,
    QCheckBox, QPushButton, QGroupBox, QFormLayout, QSpinBox,
    QComboBox, QLineEdit, QStackedWidget, QListWidget, QListWidgetItem,
    QWidget, QFrame, QScrollArea
)
from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import QFont, QColor, QIcon, QPixmap


def parse_rgba_color(val) -> QColor:
    if isinstance(val, QColor):
        return val if val.isValid() else QColor(255, 255, 255, 255)
    if not val or not isinstance(val, str):
        return QColor(255, 255, 255, 255)
    s = val.strip()
    m = re.match(r'rgba?\s*\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)(?:\s*,\s*([\d\.]+))?\s*\)', s, re.IGNORECASE)
    if m:
        r = int(m.group(1))
        g = int(m.group(2))
        b = int(m.group(3))
        a_str = m.group(4)
        if a_str is not None:
            a_val = float(a_str)
            a = int(a_val * 255) if a_val <= 1.0 and '.' in a_str else int(a_val)
        else:
            a = 255
        return QColor(r, g, b, max(0, min(255, a)))
    col = QColor(s)
    if col.isValid():
        return col
    return QColor(255, 255, 255, 255)


CONFIG_DIR = Path(os.environ.get("APPDATA", Path.home())) / "PixelPet"
CONFIG_FILE = CONFIG_DIR / "settings.json"
LOCAL_CONFIG = Path(__file__).parent / "settings.json"
LEGACY_CONFIG = Path(os.environ.get("APPDATA", Path.home())) / "PixelLion" / "settings.json"

DEFAULTS: Dict[str, Any] = {
    "selected_pet":     "tanjiro",
    "card_style":       "glass",
    "enable_island":    True,
    "island_style":     "bloom_dark",
    "island_ambient_style": "adaptive_album",
    "island_position":  "top_notch",
    "island_auto_retract": True,
    "island_eye_color": "rgba(255, 255, 255, 255)",
    "background_opacity": 80,
    "dock_mode":        "Fixed",
    "notch_mode":       "Fixed",
    "notch_style":      "flush_notch",
    "show_app_previews": True,
    "icon_only":        False,
    "weather_location": "Kochi, Kerala, India",
    "animation_fps":    12,
    "walk_speed":       90,
    "pet_size":         80,
    "follow_cursor":    True,
    "sounds_enabled":   False,
    "start_with_windows": True,
    "always_on_top":    True,
    "enable_edge_glow": False,
    "eq_style":         "neon_purple",
    "eq_mode":          "pill",
    "enable_edge_glow": False,
    "eq_style":         "neon_purple",
    "eq_mode":          "pill",
}

# Clean, professional, emoji-free display names
PET_DISPLAY_NAMES = {
    "tanjiro": "Tanjiro Kamado",
    "rengoku": "Kyojuro Rengoku",
    "gojo": "Gojo Satoru",
    "naruto": "Naruto Uzumaki",
    "luffy": "Luffy (Gear 5)",
    "nezuko": "Nezuko Kamado",
    "zenitsu": "Zenitsu Agatsuma",
    "inosuke": "Inosuke Hashibira",
    "akaza": "Akaza (Upper Moon 3)",
    "spiderman": "Spider-Man",
    "ghost_spider": "Ghost-Spider",
    "venom": "Venom",
    "batman": "Batman",
    "batman_cat": "Batman Cat",
    "spider_bot": "Spider Drone (Spider-Bot)",
    "drip_cat": "Streetwear Drip Cat",
    "gamer_cat": "Gamer Kawaii Cat",
    "cyber_cat": "Cyberpunk Neon Cat",
    "explorer_cat": "Explorer Cozy Cat",
    "goth_girl": "Gothic Butterfly",
    "alien": "Alien Companion",
    "anime_girl": "Anime Companion",
    "jcb": "JCB Excavator",
    "dragon": "Mythical Dragon",
    "goku": "Kid Goku",
    "drip_boy": "Allu (Drip Boy)",
}

CARD_STYLE_NAMES = {
    "glass": "Frosted Glass (Glassmorphism)",
    "crystal_transparent": "Crystal Clear (Transparent)",
    "ghost_transparent": "Ghost Sheer (Ultra Invisible)",
    "hologram_transparent": "Holo Wireframe (Cyan Glow)",
    "professional": "Executive Slate (Professional)",
    "cyberpunk": "Cyberpunk Neon",
    "aurora": "Sunset Aurora",
    "emerald": "Emerald Mint",
}

ISLAND_THEME_NAMES = {
    "bloom_dark": "Dark Translucent (Bloom Notch)",
    "apple_dynamic": "Apple Dynamic Glass",
    "originos_dark": "OriginOS Obsidian Glass",
    "cyber_glow": "Cyberpunk Titanium",
    "frosted_crystal": "Frosted Crystal",
}

NOTCH_STYLE_NAMES = {
    "flush_notch": "Top Screen Bezel Notch (Flush)",
    "floating_island": "Floating Capsule (Dynamic Island)",
}

DOCK_MODE_NAMES = {
    "Fixed": "Fixed (Always visible at dock)",
    "Smart": "Smart (Auto-hide on maximize)",
    "Peek": "Peek (Reveal on cursor proximity)",
}

ISLAND_AMBIENT_NAMES = {
    "adaptive_album": "Adaptive Album Art Aura",
    "aurora_borealis": "Aurora Borealis (Emerald & Violet)",
    "neon_cyber_pulse": "Cyberpunk Neon Pulse (Cyan & Magenta)",
    "sunset_chroma": "Synthwave Sunset",
    "lava_fire_glow": "Inferno Magma",
    "rainbow_flow": "RGB Chroma Spectrum",
    "minimal_frost": "Apple Minimal Frost (Diamond White)",
}

ISLAND_POSITION_NAMES = {
    "top_notch": "Top Screen Center (Notch)",
    "follow_pet": "Floating Companion (Follow Pet)",
    "floating": "Free Draggable (Anywhere)",
}

EQUALIZER_STYLE_NAMES = {
    "neon_purple": "Neon Purple / Violet (Signature)",
    "adaptive": "Adaptive Music Aura (Dynamic)",
    "electric_cyan": "Electric Cyan (Tron)",
    "spotify_green": "Spotify Emerald Green",
    "sunset_fire": "Solar Sunset Fire (Orange / Rose)",
    "diamond_white": "Diamond Frost White",
    "rainbow_rgb": "Chroma RGB Spectrum Wave",
    "luxury_gold": "Champagne Luxury Gold",
    "crimson_red": "Blood Moon Crimson Red",
}

EQUALIZER_MODE_NAMES = {
    "pill": "Pill Glass Badge (Frosted Aura)",
    "floating": "Floating Soundwave Bars",
    "dots": "LED Cyber Matrix Beads",
    "neon_beam": "High-Intensity Neon Laser",
}


class Settings:
    """Load/save settings; attribute access for individual values."""

    def __init__(self):
        self._data: Dict[str, Any] = dict(DEFAULTS)
        self.load()

    def load(self):
        targets = [p for p in (CONFIG_FILE, LOCAL_CONFIG, LEGACY_CONFIG) if p.exists()]
        if not targets:
            return
        # Prefer the most recently modified configuration file
        targets.sort(key=lambda p: p.stat().st_mtime, reverse=True)
        for target in targets:
            try:
                with open(target, "r", encoding="utf-8") as f:
                    loaded = json.load(f)
                for k, v in loaded.items():
                    if k in DEFAULTS:
                        self._data[k] = v
                break
            except (json.JSONDecodeError, OSError):
                pass

    def save(self):
        saved = False
        try:
            CONFIG_DIR.mkdir(parents=True, exist_ok=True)
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(self._data, f, indent=2)
            saved = True
        except OSError:
            pass
        # Mirror to local workspace configuration file
        try:
            with open(LOCAL_CONFIG, "w", encoding="utf-8") as f:
                json.dump(self._data, f, indent=2)
            saved = True
        except OSError:
            pass
        return saved

    def __getattr__(self, name: str) -> Any:
        if name.startswith("_"):
            raise AttributeError(name)
        if name in self._data:
            return self._data[name]
        raise AttributeError(name)

    def __setattr__(self, name: str, value: Any):
        if name.startswith("_"):
            super().__setattr__(name, value)
        elif name in DEFAULTS:
            self._data[name] = value
            self.save()
        else:
            super().__setattr__(name, value)

    def get(self, key: str, default=None):
        return self._data.get(key, default)

    def set(self, key: str, value: Any, save_now: bool = False):
        self._data[key] = value
        if save_now:
            self.save()


class SettingsDialog(QDialog):
    settings_changed = Signal(object)   # emits updated Settings instance

    def __init__(self, settings: Settings, parent=None):
        super().__init__(parent)
        self._s = settings
        self.setWindowTitle("Settings – Desktop Pet & Bloom Notch")
        self.resize(700, 530)
        self.setMinimumSize(620, 470)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowType.WindowContextHelpButtonHint)

        # Set official application icon logo
        icon_path = Path(__file__).parent / "assets" / "app_icon.ico"
        if not icon_path.exists():
            icon_path = Path(__file__).parent / "assets" / "desktop_pet.ico"
        if icon_path.exists():
            self.setWindowIcon(QIcon(str(icon_path)))

        self._apply_dark_style()
        self._build_ui()

    def _apply_dark_style(self):
        self.setStyleSheet("""
            QDialog {
                background-color: #0e1017;
                color: #ffffff;
                font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
            }
            QListWidget {
                background-color: #090a0f;
                border: none;
                color: #8e95a5;
                font-size: 13px;
                padding: 4px;
                outline: none;
            }
            QListWidget::item {
                padding: 10px 14px;
                border-radius: 8px;
                margin-bottom: 4px;
            }
            QListWidget::item:hover {
                background-color: rgba(255, 255, 255, 0.05);
                color: #ffffff;
            }
            QListWidget::item:selected {
                background-color: rgba(255, 255, 255, 0.12);
                color: #ffffff;
                font-weight: 600;
            }
            QLabel {
                color: #ffffff;
            }
            QLabel.section-header {
                color: #64748b;
                font-size: 11px;
                font-weight: 700;
                letter-spacing: 1.1px;
                padding-top: 6px;
                padding-bottom: 4px;
            }
            QLabel.subtext {
                color: #8b92a2;
                font-size: 11px;
            }
            QComboBox {
                background-color: rgba(255, 255, 255, 0.08);
                border: 1px solid rgba(255, 255, 255, 0.14);
                border-radius: 7px;
                padding: 6px 12px;
                color: #ffffff;
                font-size: 12px;
                min-width: 160px;
            }
            QComboBox:hover {
                border: 1px solid rgba(255, 255, 255, 0.28);
                background-color: rgba(255, 255, 255, 0.11);
            }
            QComboBox::drop-down {
                border: none;
                width: 22px;
            }
            QComboBox QAbstractItemView {
                background-color: #141722;
                color: #ffffff;
                selection-background-color: #2b3145;
                border: 1px solid rgba(255, 255, 255, 0.15);
                border-radius: 6px;
                padding: 4px;
            }
            QLineEdit, QSpinBox {
                background-color: rgba(255, 255, 255, 0.08);
                border: 1px solid rgba(255, 255, 255, 0.14);
                border-radius: 7px;
                padding: 6px 12px;
                color: #ffffff;
                font-size: 12px;
            }
            QSlider::groove:horizontal {
                height: 6px;
                background: rgba(255, 255, 255, 0.14);
                border-radius: 3px;
            }
            QSlider::sub-page:horizontal {
                background: #3b82f6;
                border-radius: 3px;
            }
            QSlider::handle:horizontal {
                background: #ffffff;
                border: 1px solid rgba(0, 0, 0, 0.2);
                width: 16px;
                margin-top: -5px;
                margin-bottom: -5px;
                border-radius: 8px;
            }
            QCheckBox {
                color: #ffffff;
                font-size: 12px;
                spacing: 10px;
            }
            QCheckBox::indicator {
                width: 36px;
                height: 20px;
                border-radius: 10px;
                background: rgba(255, 255, 255, 0.15);
            }
            QCheckBox::indicator:checked {
                background: #10b981;
            }
            /* Explicit ID selectors for solid, crystal-clear buttons */
            QPushButton#saveBtn {
                background-color: #2563eb;
                color: #ffffff;
                border: 1px solid #3b82f6;
                border-radius: 8px;
                padding: 8px 22px;
                font-weight: 600;
                font-size: 12px;
            }
            QPushButton#saveBtn:hover {
                background-color: #1d4ed8;
                border: 1px solid #60a5fa;
            }
            QPushButton#saveCloseBtn {
                background-color: #10b981;
                color: #ffffff;
                border: 1px solid #059669;
                border-radius: 8px;
                padding: 8px 18px;
                font-weight: 600;
                font-size: 12px;
            }
            QPushButton#saveCloseBtn:hover {
                background-color: #059669;
            }
            QPushButton#closeBtn, QPushButton.secondary-btn {
                background-color: rgba(255, 255, 255, 0.08);
                color: #c4c8d4;
                border: 1px solid rgba(255, 255, 255, 0.14);
                border-radius: 8px;
                padding: 8px 18px;
                font-size: 12px;
            }
            QPushButton#closeBtn:hover, QPushButton.secondary-btn:hover {
                background-color: rgba(255, 255, 255, 0.15);
                color: #ffffff;
            }
        """)

    def _make_scrollable(self, widget: QWidget) -> QWidget:
        sa = QScrollArea()
        sa.setWidget(widget)
        sa.setWidgetResizable(True)
        sa.setFrameShape(QFrame.Shape.NoFrame)
        sa.setStyleSheet("background: transparent; border: none;")
        return sa

    def _build_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        body_layout = QHBoxLayout()
        body_layout.setContentsMargins(0, 0, 0, 0)
        body_layout.setSpacing(0)

        # ── Left Navigation Sidebar with Brand Logo Header ───────────────────
        nav_container = QWidget()
        nav_container.setFixedWidth(185)
        nav_container.setStyleSheet("background-color: #090a0f; border-right: 1px solid rgba(255, 255, 255, 0.08);")
        nav_vbox = QVBoxLayout(nav_container)
        nav_vbox.setContentsMargins(14, 16, 14, 14)
        nav_vbox.setSpacing(14)

        # Brand header with logo icon
        brand_row = QHBoxLayout()
        brand_row.setSpacing(10)
        
        logo_lbl = QLabel()
        png_path = Path(__file__).parent / "assets" / "desktop_pet_preview.png"
        if png_path.exists():
            pm = QPixmap(str(png_path)).scaled(32, 32, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            logo_lbl.setPixmap(pm)
        else:
            logo_icon_path = Path(__file__).parent / "assets" / "app_icon.ico"
            if logo_icon_path.exists():
                logo_lbl.setPixmap(QIcon(str(logo_icon_path)).pixmap(32, 32))
        logo_lbl.setFixedSize(32, 32)

        brand_text_vbox = QVBoxLayout()
        brand_text_vbox.setSpacing(1)
        brand_title = QLabel("Desktop Pet")
        brand_title.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        brand_title.setStyleSheet("color: #ffffff; border: none; background: transparent;")
        brand_sub = QLabel("Bloom Engine")
        brand_sub.setFont(QFont("Segoe UI", 8))
        brand_sub.setStyleSheet("color: #64748b; border: none; background: transparent;")
        brand_text_vbox.addWidget(brand_title)
        brand_text_vbox.addWidget(brand_sub)

        brand_row.addWidget(logo_lbl)
        brand_row.addLayout(brand_text_vbox)
        brand_row.addStretch()
        nav_vbox.addLayout(brand_row)

        # Clean, professional navigation list without emojis
        self._nav_list = QListWidget()
        self._nav_list.setStyleSheet("background: transparent; border: none;")
        
        items = ["General", "Appearance", "Modules", "About"]
        for title in items:
            item = QListWidgetItem(title)
            self._nav_list.addItem(item)
        self._nav_list.setCurrentRow(0)  # Default to General for immediate pet settings access
        self._nav_list.currentRowChanged.connect(self._on_tab_changed)
        nav_vbox.addWidget(self._nav_list, 1)

        body_layout.addWidget(nav_container)

        # ── Right Stacked Content Pages ───────────────────────────────────────
        self._pages = QStackedWidget()
        self._pages.addWidget(self._make_scrollable(self._build_general_page()))      # Page 0
        self._pages.addWidget(self._make_scrollable(self._build_appearance_page()))   # Page 1
        self._pages.addWidget(self._make_scrollable(self._build_modules_page()))      # Page 2
        self._pages.addWidget(self._make_scrollable(self._build_about_page()))        # Page 3
        self._pages.setCurrentIndex(0)

        body_layout.addWidget(self._pages, 1)
        main_layout.addLayout(body_layout, 1)

        # ── Bottom Action Bar with Solid, Polished Buttons ───────────────────
        bottom_bar = QWidget()
        bottom_bar.setStyleSheet("background-color: #0b0c12; border-top: 1px solid rgba(255, 255, 255, 0.08); padding: 8px 16px;")
        bot_layout = QHBoxLayout(bottom_bar)
        bot_layout.setContentsMargins(16, 8, 16, 10)
        bot_layout.setSpacing(10)

        # Status notification label
        self._save_status_lbl = QLabel("")
        self._save_status_lbl.setStyleSheet("color: #10b981; font-weight: 600; font-size: 12px;")

        self._save_btn = QPushButton("Save Settings")
        self._save_btn.setObjectName("saveBtn")
        self._save_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._save_btn.setToolTip("Save all settings and apply changes immediately")
        self._save_btn.clicked.connect(self._save_settings_action)

        self._save_close_btn = QPushButton("Save and Close")
        self._save_close_btn.setObjectName("saveCloseBtn")
        self._save_close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._save_close_btn.clicked.connect(self._save_and_close)

        cancel_btn = QPushButton("Close")
        cancel_btn.setObjectName("closeBtn")
        cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        cancel_btn.clicked.connect(self._on_close_clicked)

        bot_layout.addWidget(self._save_status_lbl)
        bot_layout.addStretch()
        bot_layout.addWidget(self._save_btn)
        bot_layout.addWidget(self._save_close_btn)
        bot_layout.addWidget(cancel_btn)
        main_layout.addWidget(bottom_bar)

    def _on_tab_changed(self, row: int):
        self._pages.setCurrentIndex(row)

    # ── General Settings Page ─────────────────────────────────────────────────
    def _build_general_page(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(14)

        lbl = QLabel("GENERAL PET SETTINGS")
        lbl.setProperty("class", "section-header")
        layout.addWidget(lbl)

        # 1. Active Pet Character
        row1 = QHBoxLayout()
        v_p_lbl = QVBoxLayout()
        p_lbl = QLabel("Active Pet Character")
        p_lbl.setFont(QFont("Segoe UI", 9, QFont.Weight.DemiBold))
        p_sub = QLabel("Select desktop companion model")
        p_sub.setProperty("class", "subtext")
        v_p_lbl.addWidget(p_lbl)
        v_p_lbl.addWidget(p_sub)

        self._pet_combo = QComboBox()
        for key, name in PET_DISPLAY_NAMES.items():
            self._pet_combo.addItem(name, key)
        cur_idx = self._pet_combo.findData(self._s.selected_pet)
        if cur_idx >= 0:
            self._pet_combo.setCurrentIndex(cur_idx)
        # Connect to live change immediately!
        self._pet_combo.currentIndexChanged.connect(self._on_pet_changed)

        row1.addLayout(v_p_lbl, 1)
        row1.addWidget(self._pet_combo)
        layout.addLayout(row1)

        # 2. Pet Scale / Size Slider
        row_sz = QHBoxLayout()
        v_sz_lbl = QVBoxLayout()
        sz_lbl = QLabel("Pet Size")
        sz_lbl.setFont(QFont("Segoe UI", 9, QFont.Weight.DemiBold))
        sz_sub = QLabel("Adjust companion scale on screen")
        sz_sub.setProperty("class", "subtext")
        v_sz_lbl.addWidget(sz_lbl)
        v_sz_lbl.addWidget(sz_sub)

        self._size_slider = QSlider(Qt.Orientation.Horizontal)
        self._size_slider.setRange(40, 160)
        self._size_slider.setValue(getattr(self._s, "pet_size", 80))
        self._size_slider.setFixedWidth(160)
        self._size_label = QLabel(f"{getattr(self._s, 'pet_size', 80)} px")
        self._size_label.setStyleSheet("color: #c4c8d4; font-size: 12px; min-width: 48px;")
        self._size_slider.valueChanged.connect(self._on_size_changed)

        row_sz.addLayout(v_sz_lbl, 1)
        row_sz.addWidget(self._size_slider)
        row_sz.addWidget(self._size_label)
        layout.addLayout(row_sz)

        # 3. Companion Card Theme
        row_card = QHBoxLayout()
        v_c_lbl = QVBoxLayout()
        c_lbl = QLabel("Companion Card Theme")
        c_lbl.setFont(QFont("Segoe UI", 9, QFont.Weight.DemiBold))
        c_sub = QLabel("Card styling for speech bubbles and media")
        c_sub.setProperty("class", "subtext")
        v_c_lbl.addWidget(c_lbl)
        v_c_lbl.addWidget(c_sub)

        self._card_combo = QComboBox()
        for key, name in CARD_STYLE_NAMES.items():
            self._card_combo.addItem(name, key)
        cur_card_idx = self._card_combo.findData(self._s.card_style)
        if cur_card_idx >= 0:
            self._card_combo.setCurrentIndex(cur_card_idx)
        self._card_combo.currentIndexChanged.connect(self._on_card_style_changed)

        row_card.addLayout(v_c_lbl, 1)
        row_card.addWidget(self._card_combo)
        layout.addLayout(row_card)

        # 4. Walking Speed
        row_spd = QHBoxLayout()
        v_spd_lbl = QVBoxLayout()
        s_lbl = QLabel("Walking Speed")
        s_lbl.setFont(QFont("Segoe UI", 9, QFont.Weight.DemiBold))
        s_sub = QLabel("Velocity when traversing the desktop")
        s_sub.setProperty("class", "subtext")
        v_spd_lbl.addWidget(s_lbl)
        v_spd_lbl.addWidget(s_sub)

        self._speed_slider = QSlider(Qt.Orientation.Horizontal)
        self._speed_slider.setRange(20, 200)
        self._speed_slider.setValue(self._s.walk_speed)
        self._speed_slider.setFixedWidth(160)
        self._speed_label = QLabel(f"{self._s.walk_speed} px/s")
        self._speed_label.setStyleSheet("color: #c4c8d4; font-size: 12px; min-width: 48px;")
        self._speed_slider.valueChanged.connect(self._on_speed_changed)

        row_spd.addLayout(v_spd_lbl, 1)
        row_spd.addWidget(self._speed_slider)
        row_spd.addWidget(self._speed_label)
        layout.addLayout(row_spd)

        # 5. Animation FPS
        row_fps = QHBoxLayout()
        v_fps_lbl = QVBoxLayout()
        fps_lbl = QLabel("Animation FPS")
        fps_lbl.setFont(QFont("Segoe UI", 9, QFont.Weight.DemiBold))
        fps_sub = QLabel("Target frame rate for sprite animations")
        fps_sub.setProperty("class", "subtext")
        v_fps_lbl.addWidget(fps_lbl)
        v_fps_lbl.addWidget(fps_sub)

        self._fps_spin = QSpinBox()
        self._fps_spin.setRange(4, 30)
        self._fps_spin.setValue(self._s.animation_fps)
        self._fps_spin.setSuffix(" fps")
        self._fps_spin.valueChanged.connect(self._on_fps_changed)

        row_fps.addLayout(v_fps_lbl, 1)
        row_fps.addWidget(self._fps_spin)
        layout.addLayout(row_fps)

        # Separator line
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("background-color: rgba(255, 255, 255, 0.08);")
        layout.addWidget(sep)

        # 6. Toggles
        self._follow_cb = QCheckBox("Follow mouse cursor across desktop")
        self._follow_cb.setChecked(self._s.follow_cursor)
        self._follow_cb.toggled.connect(self._on_follow_toggled)
        layout.addWidget(self._follow_cb)

        self._sound_cb = QCheckBox("Enable interaction sounds")
        self._sound_cb.setChecked(self._s.sounds_enabled)
        self._sound_cb.toggled.connect(self._on_sound_toggled)
        layout.addWidget(self._sound_cb)

        self._startup_cb = QCheckBox("Launch automatically on Windows startup")
        self._startup_cb.setChecked(self._s.start_with_windows)
        self._startup_cb.toggled.connect(self._on_startup_toggled)
        layout.addWidget(self._startup_cb)

        self._ontop_cb = QCheckBox("Keep pet and widgets always on top")
        self._ontop_cb.setChecked(self._s.always_on_top)
        self._ontop_cb.toggled.connect(self._on_ontop_toggled)
        layout.addWidget(self._ontop_cb)

        layout.addStretch()
        return w

    def _sync_to_active_pets(self):
        try:
            from pet_manager import PetManager
            for pet in PetManager.instance().pets:
                if hasattr(pet, "_apply_settings"):
                    pet._apply_settings(self._s)
        except Exception:
            pass

    # Live update callbacks for General settings
    def _on_pet_changed(self, idx: int):
        new_pet = self._pet_combo.currentData()
        if new_pet:
            self._s.set("selected_pet", new_pet, save_now=True)
            self._sync_to_active_pets()
            self.settings_changed.emit(self._s)

    def _on_size_changed(self, val: int):
        self._size_label.setText(f"{val} px")
        self._s.set("pet_size", val, save_now=True)
        self._sync_to_active_pets()
        self.settings_changed.emit(self._s)

    def _on_card_style_changed(self, idx: int):
        new_card = self._card_combo.currentData()
        if new_card:
            self._s.set("card_style", new_card, save_now=True)
            self._sync_to_active_pets()
            self.settings_changed.emit(self._s)

    def _on_speed_changed(self, val: int):
        self._speed_label.setText(f"{val} px/s")
        self._s.set("walk_speed", val, save_now=True)
        self._sync_to_active_pets()
        self.settings_changed.emit(self._s)

    def _on_fps_changed(self, val: int):
        self._s.set("animation_fps", val, save_now=True)
        self._sync_to_active_pets()
        self.settings_changed.emit(self._s)

    def _on_follow_toggled(self, checked: bool):
        self._s.set("follow_cursor", checked, save_now=True)
        self._sync_to_active_pets()
        self.settings_changed.emit(self._s)

    def _on_sound_toggled(self, checked: bool):
        self._s.set("sounds_enabled", checked, save_now=True)
        self._sync_to_active_pets()
        self.settings_changed.emit(self._s)

    def _on_startup_toggled(self, checked: bool):
        self._s.set("start_with_windows", checked, save_now=True)
        self._sync_to_active_pets()
        self.settings_changed.emit(self._s)

    def _on_ontop_toggled(self, checked: bool):
        self._s.set("always_on_top", checked, save_now=True)
        self._sync_to_active_pets()
        self.settings_changed.emit(self._s)

    # ── Appearance Page ───────────────────────────────────────────────────────
    def _build_appearance_page(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(14)

        # Header 1: APPEARANCE & THEME
        lbl_app = QLabel("APPEARANCE & THEME")
        lbl_app.setProperty("class", "section-header")
        layout.addWidget(lbl_app)

        # Row 1: Theme Mode
        row_theme = QHBoxLayout()
        v_theme_lbl = QVBoxLayout()
        t_title = QLabel("Theme Mode")
        t_title.setFont(QFont("Segoe UI", 9, QFont.Weight.DemiBold))
        t_sub = QLabel("Configure visual styling")
        t_sub.setProperty("class", "subtext")
        v_theme_lbl.addWidget(t_title)
        v_theme_lbl.addWidget(t_sub)

        self._island_theme_combo = QComboBox()
        for key, name in ISLAND_THEME_NAMES.items():
            self._island_theme_combo.addItem(name, key)
        cur_th = self._s.get("island_style", "bloom_dark")
        idx_th = self._island_theme_combo.findData(cur_th)
        if idx_th >= 0:
            self._island_theme_combo.setCurrentIndex(idx_th)
        self._island_theme_combo.currentIndexChanged.connect(self._on_theme_changed)

        row_theme.addLayout(v_theme_lbl, 1)
        row_theme.addWidget(self._island_theme_combo)
        layout.addLayout(row_theme)

        # Row 2: Background Opacity Slider
        row_op = QHBoxLayout()
        v_op_lbl = QVBoxLayout()
        self._op_title = QLabel("Background Opacity")
        self._op_title.setFont(QFont("Segoe UI", 9, QFont.Weight.DemiBold))
        self._op_sub = QLabel(f"Adjust theme transparency ({self._s.get('background_opacity', 80)}%)")
        self._op_sub.setProperty("class", "subtext")
        v_op_lbl.addWidget(self._op_title)
        v_op_lbl.addWidget(self._op_sub)

        self._opacity_slider = QSlider(Qt.Orientation.Horizontal)
        self._opacity_slider.setRange(30, 100)
        self._opacity_slider.setValue(self._s.get("background_opacity", 80))
        self._opacity_slider.setFixedWidth(160)
        self._opacity_slider.valueChanged.connect(self._on_opacity_slider_changed)

        row_op.addLayout(v_op_lbl, 1)
        row_op.addWidget(self._opacity_slider)
        layout.addLayout(row_op)

        # Separator line
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("background-color: rgba(255, 255, 255, 0.08);")
        layout.addWidget(sep)

        # Header 2: BLOOM DOCK & NOTCH
        lbl_dock = QLabel("BLOOM DOCK & NOTCH")
        lbl_dock.setProperty("class", "section-header")
        layout.addWidget(lbl_dock)

        # Row 3: Bloom Dock toggle
        row_dock = QHBoxLayout()
        v_dock_lbl = QVBoxLayout()
        d_title = QLabel("Bloom Dock")
        d_title.setFont(QFont("Segoe UI", 9, QFont.Weight.DemiBold))
        d_sub = QLabel("Enable dynamic island companion notch")
        d_sub.setProperty("class", "subtext")
        v_dock_lbl.addWidget(d_title)
        v_dock_lbl.addWidget(d_sub)

        self._dock_cb = QCheckBox()
        self._dock_cb.setChecked(self._s.get("enable_island", True))
        self._dock_cb.toggled.connect(self._on_dock_toggled)
        row_dock.addLayout(v_dock_lbl, 1)
        row_dock.addWidget(self._dock_cb)
        layout.addLayout(row_dock)

        # Row 4: Behavior
        row_beh = QHBoxLayout()
        v_beh_lbl = QVBoxLayout()
        b_title = QLabel("Behavior")
        b_title.setFont(QFont("Segoe UI", 9, QFont.Weight.DemiBold))
        b_sub = QLabel("Choose how the dock appears")
        b_sub.setProperty("class", "subtext")
        v_beh_lbl.addWidget(b_title)
        v_beh_lbl.addWidget(b_sub)

        self._dock_mode_combo = QComboBox()
        for key, name in DOCK_MODE_NAMES.items():
            self._dock_mode_combo.addItem(name, key)
        cur_dm = self._s.get("dock_mode", "Fixed")
        idx_dm = self._dock_mode_combo.findData(cur_dm)
        if idx_dm >= 0:
            self._dock_mode_combo.setCurrentIndex(idx_dm)
        self._dock_mode_combo.currentIndexChanged.connect(self._on_dock_mode_changed)

        row_beh.addLayout(v_beh_lbl, 1)
        row_beh.addWidget(self._dock_mode_combo)
        layout.addLayout(row_beh)

        # Row 5: Show App Previews
        row_prev = QHBoxLayout()
        v_prev_lbl = QVBoxLayout()
        p_title = QLabel("Show App Previews")
        p_title.setFont(QFont("Segoe UI", 9, QFont.Weight.DemiBold))
        p_sub = QLabel("Show window thumbnails on hover")
        p_sub.setProperty("class", "subtext")
        v_prev_lbl.addWidget(p_title)
        v_prev_lbl.addWidget(p_sub)

        self._preview_cb = QCheckBox()
        self._preview_cb.setChecked(self._s.get("show_app_previews", True))
        self._preview_cb.toggled.connect(self._on_preview_toggled)
        row_prev.addLayout(v_prev_lbl, 1)
        row_prev.addWidget(self._preview_cb)
        layout.addLayout(row_prev)

        # Row 6: Icon Only
        row_icon = QHBoxLayout()
        v_icon_lbl = QVBoxLayout()
        i_title = QLabel("Icon Only")
        i_title.setFont(QFont("Segoe UI", 9, QFont.Weight.DemiBold))
        i_sub = QLabel("Remove icon background and padding")
        i_sub.setProperty("class", "subtext")
        v_icon_lbl.addWidget(i_title)
        v_icon_lbl.addWidget(i_sub)

        self._icon_cb = QCheckBox()
        self._icon_cb.setChecked(self._s.get("icon_only", False))
        self._icon_cb.toggled.connect(self._on_icon_only_toggled)
        row_icon.addLayout(v_icon_lbl, 1)
        row_icon.addWidget(self._icon_cb)
        layout.addLayout(row_icon)

        # Row 7: Top Notch Bezel Style
        row_notch = QHBoxLayout()
        v_notch_lbl = QVBoxLayout()
        n_title = QLabel("Notch Geometry")
        n_title.setFont(QFont("Segoe UI", 9, QFont.Weight.DemiBold))
        n_sub = QLabel("Bezel notch flush drop-down vs floating island")
        n_sub.setProperty("class", "subtext")
        v_notch_lbl.addWidget(n_title)
        v_notch_lbl.addWidget(n_sub)

        self._notch_style_combo = QComboBox()
        for key, name in NOTCH_STYLE_NAMES.items():
            self._notch_style_combo.addItem(name, key)
        cur_ns = self._s.get("notch_style", "flush_notch")
        idx_ns = self._notch_style_combo.findData(cur_ns)
        if idx_ns >= 0:
            self._notch_style_combo.setCurrentIndex(idx_ns)
        self._notch_style_combo.currentIndexChanged.connect(self._on_notch_style_changed)

        row_notch.addLayout(v_notch_lbl, 1)
        row_notch.addWidget(self._notch_style_combo)
        layout.addLayout(row_notch)

        # Row 8: Pet Eye Color (RGBA Color Picker)
        row_eye = QHBoxLayout()
        v_eye_lbl = QVBoxLayout()
        e_title = QLabel("Pet Eye Color (RGBA)")
        e_title.setFont(QFont("Segoe UI", 9, QFont.Weight.DemiBold))
        self._eye_sub = QLabel(f"Custom eye glow and transparency ({self._s.get('island_eye_color', 'rgba(255, 255, 255, 255)')})")
        self._eye_sub.setProperty("class", "subtext")
        v_eye_lbl.addWidget(e_title)
        v_eye_lbl.addWidget(self._eye_sub)

        h_picker = QHBoxLayout()
        h_picker.setSpacing(8)
        self._eye_swatch = QPushButton()
        self._eye_swatch.setFixedSize(36, 26)
        self._eye_swatch.setCursor(Qt.CursorShape.PointingHandCursor)
        cur_eye_str = self._s.get("island_eye_color", "rgba(255, 255, 255, 255)")
        self._current_eye_color = parse_rgba_color(cur_eye_str)
        self._update_eye_swatch(self._current_eye_color)
        self._eye_swatch.clicked.connect(self._open_eye_color_picker)

        self._pick_eye_btn = QPushButton("Choose Color...")
        self._pick_eye_btn.setProperty("class", "secondary-btn")
        self._pick_eye_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._pick_eye_btn.clicked.connect(self._open_eye_color_picker)

        h_picker.addWidget(self._eye_swatch)
        h_picker.addWidget(self._pick_eye_btn)

        row_eye.addLayout(v_eye_lbl, 1)
        row_eye.addLayout(h_picker)
        layout.addLayout(row_eye)

        # Row 9: Desktop Wallpaper
        row_wp = QHBoxLayout()
        v_wp_lbl = QVBoxLayout()
        wp_title = QLabel("Desktop Wallpaper")
        wp_title.setFont(QFont("Segoe UI", 9, QFont.Weight.DemiBold))
        self._wp_sub = QLabel("Set Windows desktop wallpaper image")
        self._wp_sub.setProperty("class", "subtext")
        v_wp_lbl.addWidget(wp_title)
        v_wp_lbl.addWidget(self._wp_sub)

        self._pick_wp_btn = QPushButton("Upload Image...")
        self._pick_wp_btn.setProperty("class", "secondary-btn")
        self._pick_wp_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._pick_wp_btn.clicked.connect(self._choose_wallpaper)

        row_wp.addLayout(v_wp_lbl, 1)
        row_wp.addWidget(self._pick_wp_btn)
        layout.addLayout(row_wp)

        # Row 10: Edge Lighting Glow Waves
        row_glow = QHBoxLayout()
        v_glow_lbl = QVBoxLayout()
        glow_title = QLabel("Flank Edge Lighting Waves")
        glow_title.setFont(QFont("Segoe UI", 9, QFont.Weight.DemiBold))
        self._glow_sub = QLabel("Animated light drops along the side edges of the notch")
        self._glow_sub.setProperty("class", "subtext")
        v_glow_lbl.addWidget(glow_title)
        v_glow_lbl.addWidget(self._glow_sub)

        self._edge_glow_cb = QCheckBox("Enable Edge Lighting Waves")
        self._edge_glow_cb.setChecked(self._s.get("enable_edge_glow", False))
        self._edge_glow_cb.toggled.connect(self._on_edge_glow_toggled)

        row_glow.addLayout(v_glow_lbl, 1)
        row_glow.addWidget(self._edge_glow_cb)
        layout.addLayout(row_glow)

        # Separator line
        sep_eq = QFrame()
        sep_eq.setFrameShape(QFrame.Shape.HLine)
        sep_eq.setStyleSheet("background-color: rgba(255, 255, 255, 0.08);")
        layout.addWidget(sep_eq)

        # Header 3: MUSIC EQUALIZER & VISUALIZER
        lbl_eq = QLabel("MUSIC EQUALIZER & VISUALIZER")
        lbl_eq.setProperty("class", "section-header")
        layout.addWidget(lbl_eq)

        # Row 11: Equalizer Theme
        row_eq_style = QHBoxLayout()
        v_eq_style_lbl = QVBoxLayout()
        eq_s_title = QLabel("Equalizer Color Theme")
        eq_s_title.setFont(QFont("Segoe UI", 9, QFont.Weight.DemiBold))
        eq_s_sub = QLabel("Select visualizer colors or adapt dynamically to album art")
        eq_s_sub.setProperty("class", "subtext")
        v_eq_style_lbl.addWidget(eq_s_title)
        v_eq_style_lbl.addWidget(eq_s_sub)

        self._eq_style_combo = QComboBox()
        for key, name in EQUALIZER_STYLE_NAMES.items():
            self._eq_style_combo.addItem(name, key)
        cur_eq_style = self._s.get("eq_style", "neon_purple")
        idx_eq_style = self._eq_style_combo.findData(cur_eq_style)
        if idx_eq_style >= 0:
            self._eq_style_combo.setCurrentIndex(idx_eq_style)
        self._eq_style_combo.currentIndexChanged.connect(self._on_eq_style_changed)

        row_eq_style.addLayout(v_eq_style_lbl, 1)
        row_eq_style.addWidget(self._eq_style_combo)
        layout.addLayout(row_eq_style)

        # Row 12: Equalizer Mode
        row_eq_mode = QHBoxLayout()
        v_eq_mode_lbl = QVBoxLayout()
        eq_m_title = QLabel("Equalizer Display Format")
        eq_m_title.setFont(QFont("Segoe UI", 9, QFont.Weight.DemiBold))
        eq_m_sub = QLabel("Choose visualizer badge geometry and animation mode")
        eq_m_sub.setProperty("class", "subtext")
        v_eq_mode_lbl.addWidget(eq_m_title)
        v_eq_mode_lbl.addWidget(eq_m_sub)

        self._eq_mode_combo = QComboBox()
        for key, name in EQUALIZER_MODE_NAMES.items():
            self._eq_mode_combo.addItem(name, key)
        cur_eq_mode = self._s.get("eq_mode", "pill")
        idx_eq_mode = self._eq_mode_combo.findData(cur_eq_mode)
        if idx_eq_mode >= 0:
            self._eq_mode_combo.setCurrentIndex(idx_eq_mode)
        self._eq_mode_combo.currentIndexChanged.connect(self._on_eq_mode_changed)

        row_eq_mode.addLayout(v_eq_mode_lbl, 1)
        row_eq_mode.addWidget(self._eq_mode_combo)
        layout.addLayout(row_eq_mode)

        # Row 10: Edge Lighting Glow Waves
        row_glow = QHBoxLayout()
        v_glow_lbl = QVBoxLayout()
        glow_title = QLabel("Flank Edge Lighting Waves")
        glow_title.setFont(QFont("Segoe UI", 9, QFont.Weight.DemiBold))
        self._glow_sub = QLabel("Animated light drops along the side edges of the notch")
        self._glow_sub.setProperty("class", "subtext")
        v_glow_lbl.addWidget(glow_title)
        v_glow_lbl.addWidget(self._glow_sub)

        self._edge_glow_cb = QCheckBox("Enable Edge Lighting Waves")
        self._edge_glow_cb.setChecked(self._s.get("enable_edge_glow", False))
        self._edge_glow_cb.toggled.connect(self._on_edge_glow_toggled)

        row_glow.addLayout(v_glow_lbl, 1)
        row_glow.addWidget(self._edge_glow_cb)
        layout.addLayout(row_glow)

        # Separator line
        sep_eq = QFrame()
        sep_eq.setFrameShape(QFrame.Shape.HLine)
        sep_eq.setStyleSheet("background-color: rgba(255, 255, 255, 0.08);")
        layout.addWidget(sep_eq)

        # Header 3: MUSIC EQUALIZER & VISUALIZER
        lbl_eq = QLabel("MUSIC EQUALIZER & VISUALIZER")
        lbl_eq.setProperty("class", "section-header")
        layout.addWidget(lbl_eq)

        # Row 11: Equalizer Theme
        row_eq_style = QHBoxLayout()
        v_eq_style_lbl = QVBoxLayout()
        eq_s_title = QLabel("Equalizer Color Theme")
        eq_s_title.setFont(QFont("Segoe UI", 9, QFont.Weight.DemiBold))
        eq_s_sub = QLabel("Select visualizer colors or adapt dynamically to album art")
        eq_s_sub.setProperty("class", "subtext")
        v_eq_style_lbl.addWidget(eq_s_title)
        v_eq_style_lbl.addWidget(eq_s_sub)

        self._eq_style_combo = QComboBox()
        for key, name in EQUALIZER_STYLE_NAMES.items():
            self._eq_style_combo.addItem(name, key)
        cur_eq_style = self._s.get("eq_style", "neon_purple")
        idx_eq_style = self._eq_style_combo.findData(cur_eq_style)
        if idx_eq_style >= 0:
            self._eq_style_combo.setCurrentIndex(idx_eq_style)
        self._eq_style_combo.currentIndexChanged.connect(self._on_eq_style_changed)

        row_eq_style.addLayout(v_eq_style_lbl, 1)
        row_eq_style.addWidget(self._eq_style_combo)
        layout.addLayout(row_eq_style)

        # Row 12: Equalizer Mode
        row_eq_mode = QHBoxLayout()
        v_eq_mode_lbl = QVBoxLayout()
        eq_m_title = QLabel("Equalizer Display Format")
        eq_m_title.setFont(QFont("Segoe UI", 9, QFont.Weight.DemiBold))
        eq_m_sub = QLabel("Choose visualizer badge geometry and animation mode")
        eq_m_sub.setProperty("class", "subtext")
        v_eq_mode_lbl.addWidget(eq_m_title)
        v_eq_mode_lbl.addWidget(eq_m_sub)

        self._eq_mode_combo = QComboBox()
        for key, name in EQUALIZER_MODE_NAMES.items():
            self._eq_mode_combo.addItem(name, key)
        cur_eq_mode = self._s.get("eq_mode", "pill")
        idx_eq_mode = self._eq_mode_combo.findData(cur_eq_mode)
        if idx_eq_mode >= 0:
            self._eq_mode_combo.setCurrentIndex(idx_eq_mode)
        self._eq_mode_combo.currentIndexChanged.connect(self._on_eq_mode_changed)

        row_eq_mode.addLayout(v_eq_mode_lbl, 1)
        row_eq_mode.addWidget(self._eq_mode_combo)
        layout.addLayout(row_eq_mode)

        layout.addStretch()
        return w

    def _on_eq_style_changed(self, index: int):
        val = self._eq_style_combo.currentData()
        self._s.set("eq_style", val, save_now=True)
        self.settings_changed.emit(self._s)

    def _on_eq_mode_changed(self, index: int):
        val = self._eq_mode_combo.currentData()
        self._s.set("eq_mode", val, save_now=True)
        self.settings_changed.emit(self._s)

    def _choose_wallpaper(self):
        try:
            from tools.wallpaper import pick_and_set_wallpaper
            path = pick_and_set_wallpaper(self)
            if path:
                fname = os.path.basename(path)
                self._wp_sub.setText(f"Wallpaper updated: {fname}")
        except Exception as e:
            print(f"Error choosing wallpaper: {e}")

    def _update_eye_swatch(self, color: QColor):
        r, g, b, a = color.red(), color.green(), color.blue(), color.alpha()
        self._eye_swatch.setStyleSheet(f"""
            QPushButton {{
                background-color: rgba({r}, {g}, {b}, {a / 255.0:.2f});
                border: 2px solid rgba(255, 255, 255, 0.45);
                border-radius: 6px;
            }}
            QPushButton:hover {{
                border: 2px solid #00f0ff;
            }}
        """)
        self._eye_sub.setText(f"Custom eye glow and transparency (rgba({r}, {g}, {b}, {a}))")

    def _open_eye_color_picker(self):
        from PySide6.QtWidgets import QColorDialog
        dlg = QColorDialog(self)
        dlg.setWindowTitle("Select Pet Eye RGBA Color")
        dlg.setOption(QColorDialog.ColorDialogOption.ShowAlphaChannel, True)
        dlg.setCurrentColor(self._current_eye_color)
        if dlg.exec():
            selected = dlg.selectedColor()
            if selected.isValid():
                self._current_eye_color = selected
                self._update_eye_swatch(selected)
                r, g, b, a = selected.red(), selected.green(), selected.blue(), selected.alpha()
                self._s.set("island_eye_color", f"rgba({r},{g},{b},{a})", save_now=True)
                self.settings_changed.emit(self._s)
                if hasattr(self, "_save_status_lbl"):
                    self._save_status_lbl.setText("Eye color saved successfully")
                    QTimer.singleShot(3000, lambda: self._save_status_lbl.setText(""))

    def _on_theme_changed(self, idx: int):
        new_th = self._island_theme_combo.currentData()
        if new_th:
            self._s.set("island_style", new_th, save_now=True)
            self.settings_changed.emit(self._s)

    def _on_opacity_slider_changed(self, val: int):
        self._op_sub.setText(f"Adjust theme transparency ({val}%)")
        self._s.set("background_opacity", val, save_now=True)
        self.settings_changed.emit(self._s)

    def _on_dock_toggled(self, checked: bool):
        self._s.set("enable_island", checked, save_now=True)
        self.settings_changed.emit(self._s)

    def _on_dock_mode_changed(self, idx: int):
        new_dm = self._dock_mode_combo.currentData()
        if new_dm:
            self._s.set("dock_mode", new_dm, save_now=True)
            self.settings_changed.emit(self._s)

    def _on_preview_toggled(self, checked: bool):
        self._s.set("show_app_previews", checked, save_now=True)
        self.settings_changed.emit(self._s)

    def _on_icon_only_toggled(self, checked: bool):
        self._s.set("icon_only", checked, save_now=True)
        self.settings_changed.emit(self._s)

    def _on_notch_style_changed(self, idx: int):
        new_ns = self._notch_style_combo.currentData()
        if new_ns:
            self._s.set("notch_style", new_ns, save_now=True)
            self.settings_changed.emit(self._s)

    def _on_edge_glow_toggled(self, checked: bool):
        self._s.set("enable_edge_glow", checked, save_now=True)
        self.settings_changed.emit(self._s)

    # ── Modules Page ──────────────────────────────────────────────────────────
    def _build_modules_page(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(14)

        lbl = QLabel("NOTCH & DOCK MODULES")
        lbl.setProperty("class", "section-header")
        layout.addWidget(lbl)

        # Ambient lighting style
        row_amb = QHBoxLayout()
        v_amb_lbl = QVBoxLayout()
        amb_lbl = QLabel("Ambient Lighting Aura")
        amb_lbl.setFont(QFont("Segoe UI", 9, QFont.Weight.DemiBold))
        amb_sub = QLabel("Select fluid light mesh effect")
        amb_sub.setProperty("class", "subtext")
        v_amb_lbl.addWidget(amb_lbl)
        v_amb_lbl.addWidget(amb_sub)

        self._island_ambient_combo = QComboBox()
        for key, name in ISLAND_AMBIENT_NAMES.items():
            self._island_ambient_combo.addItem(name, key)
        cur_amb_idx = self._island_ambient_combo.findData(self._s.get("island_ambient_style", "adaptive_album"))
        if cur_amb_idx >= 0:
            self._island_ambient_combo.setCurrentIndex(cur_amb_idx)
        self._island_ambient_combo.currentIndexChanged.connect(self._on_ambient_style_changed)

        row_amb.addLayout(v_amb_lbl, 1)
        row_amb.addWidget(self._island_ambient_combo)
        layout.addLayout(row_amb)

        # Island Position
        row_pos = QHBoxLayout()
        v_pos_lbl = QVBoxLayout()
        pos_lbl = QLabel("Default Island Anchor")
        pos_lbl.setFont(QFont("Segoe UI", 9, QFont.Weight.DemiBold))
        pos_sub = QLabel("Positioning target for dynamic notch")
        pos_sub.setProperty("class", "subtext")
        v_pos_lbl.addWidget(pos_lbl)
        v_pos_lbl.addWidget(pos_sub)

        self._island_pos_combo = QComboBox()
        for key, name in ISLAND_POSITION_NAMES.items():
            self._island_pos_combo.addItem(name, key)
        cur_pos_idx = self._island_pos_combo.findData(self._s.get("island_position", "top_notch"))
        if cur_pos_idx >= 0:
            self._island_pos_combo.setCurrentIndex(cur_pos_idx)
        self._island_pos_combo.currentIndexChanged.connect(self._on_position_changed)

        row_pos.addLayout(v_pos_lbl, 1)
        row_pos.addWidget(self._island_pos_combo)
        layout.addLayout(row_pos)

        # Weather Location
        row_loc = QHBoxLayout()
        v_loc_lbl = QVBoxLayout()
        loc_lbl = QLabel("Weather Location City")
        loc_lbl.setFont(QFont("Segoe UI", 9, QFont.Weight.DemiBold))
        loc_sub = QLabel("City used for live forecast updates")
        loc_sub.setProperty("class", "subtext")
        v_loc_lbl.addWidget(loc_lbl)
        v_loc_lbl.addWidget(loc_sub)

        self._weather_loc_edit = QLineEdit(self._s.get("weather_location", "Kochi, Kerala, India"))
        self._weather_loc_edit.setPlaceholderText("e.g. Kochi, Kerala, India")

        row_loc.addLayout(v_loc_lbl, 1)
        row_loc.addWidget(self._weather_loc_edit)
        layout.addLayout(row_loc)

        layout.addStretch()
        return w

    def _on_ambient_style_changed(self, idx: int):
        new_amb = self._island_ambient_combo.currentData()
        if new_amb:
            self._s.set("island_ambient_style", new_amb, save_now=True)
            self.settings_changed.emit(self._s)

    def _on_position_changed(self, idx: int):
        new_pos = self._island_pos_combo.currentData()
        if new_pos:
            self._s.set("island_position", new_pos, save_now=True)
            self.settings_changed.emit(self._s)

    # ── About Page ────────────────────────────────────────────────────────────
    def _build_about_page(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(24, 24, 24, 20)
        layout.setSpacing(10)

        title = QLabel("Desktop Pet & Bloom Origin Notch")
        title.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        version = QLabel("Version 2.5 • Bloom Glass Engine")
        version.setProperty("class", "subtext")

        desc = QLabel(
            "High-performance desktop companion with dynamic island notch, "
            "Apple and OriginOS fluid spring physics, Control Center quick toggles, "
            "Pomodoro focus timer, mini calendar, and seamless Spotify and media synchronization."
        )
        desc.setWordWrap(True)
        desc.setStyleSheet("color: #a8b0c0; line-height: 1.5; font-size: 12px; margin-top: 10px;")

        layout.addWidget(title)
        layout.addWidget(version)
        layout.addWidget(desc)
        layout.addStretch()
        return w

    # ── Master Collect and Save ──────────────────────────────────────────────
    def _collect_and_save(self):
        self._s.selected_pet = self._pet_combo.currentData()
        self._s.pet_size = self._size_slider.value()
        self._s.card_style = self._card_combo.currentData()
        self._s.enable_island = self._dock_cb.isChecked()
        self._s.island_style = self._island_theme_combo.currentData()
        self._s.background_opacity = self._opacity_slider.value()
        self._s.dock_mode = self._dock_mode_combo.currentData()
        self._s.show_app_previews = self._preview_cb.isChecked()
        self._s.icon_only = self._icon_cb.isChecked()
        self._s.notch_style = self._notch_style_combo.currentData()
        self._s.island_ambient_style = self._island_ambient_combo.currentData()
        self._s.island_position = self._island_pos_combo.currentData()
        self._s.weather_location = self._weather_loc_edit.text().strip() or "Kochi, Kerala, India"
        self._s.animation_fps = self._fps_spin.value()
        self._s.walk_speed = self._speed_slider.value()
        self._s.follow_cursor = self._follow_cb.isChecked()
        self._s.sounds_enabled = self._sound_cb.isChecked()
        self._s.start_with_windows = self._startup_cb.isChecked()
        self._s.always_on_top = self._ontop_cb.isChecked()
        if hasattr(self, "_edge_glow_cb"):
            self._s.set("enable_edge_glow", self._edge_glow_cb.isChecked())
        if hasattr(self, "_eq_style_combo"):
            self._s.set("eq_style", self._eq_style_combo.currentData())
        if hasattr(self, "_eq_mode_combo"):
            self._s.set("eq_mode", self._eq_mode_combo.currentData())
        if hasattr(self, "_edge_glow_cb"):
            self._s.set("enable_edge_glow", self._edge_glow_cb.isChecked())
        if hasattr(self, "_eq_style_combo"):
            self._s.set("eq_style", self._eq_style_combo.currentData())
        if hasattr(self, "_eq_mode_combo"):
            self._s.set("eq_mode", self._eq_mode_combo.currentData())
        if hasattr(self, "_current_eye_color") and self._current_eye_color.isValid():
            r, g, b, a = self._current_eye_color.red(), self._current_eye_color.green(), self._current_eye_color.blue(), self._current_eye_color.alpha()
            self._s.set("island_eye_color", f"rgba({r},{g},{b},{a})")
        self._s.save()
        self._sync_to_active_pets()
        self.settings_changed.emit(self._s)

    def _save_settings_action(self):
        self._collect_and_save()
        if hasattr(self, "_save_status_lbl"):
            self._save_status_lbl.setText("Settings saved successfully")
            QTimer.singleShot(3500, lambda: self._save_status_lbl.setText(""))

    def _save_and_close(self):
        self._collect_and_save()
        self.accept()

    def _on_close_clicked(self):
        self._collect_and_save()
        self.close()

    def closeEvent(self, event):
        self._collect_and_save()
        event.accept()
        super().closeEvent(event)

    def reject(self):
        self._collect_and_save()
        super().reject()

    def accept(self):
        self._collect_and_save()
        super().accept()
