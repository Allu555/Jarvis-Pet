import json
import os
from pathlib import Path
from typing import Any, Dict, Optional

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QSlider,
    QCheckBox, QPushButton, QGroupBox, QFormLayout, QSpinBox,
    QComboBox, QLineEdit
)
from PySide6.QtCore import Qt, Signal


CONFIG_DIR = Path(os.environ.get("APPDATA", Path.home())) / "PixelPet"
CONFIG_FILE = CONFIG_DIR / "settings.json"
LEGACY_CONFIG = Path(os.environ.get("APPDATA", Path.home())) / "PixelLion" / "settings.json"

DEFAULTS: Dict[str, Any] = {
    "selected_pet":     "tanjiro",
    "card_style":       "glass",
    "enable_island":    True,
    "island_style":     "apple_dynamic",
    "island_ambient_style": "adaptive_album",
    "island_position":  "top_notch",
    "weather_location": "Kochi, Kerala, India",
    "animation_fps":    12,
    "walk_speed":       90,
    "pet_size":         80,
    "follow_cursor":    True,
    "sounds_enabled":   False,
    "start_with_windows": True,
    "always_on_top":    True,
}

PET_DISPLAY_NAMES = {
    "drip_cat": "Streetwear Drip Cat 🕶️🪙",
    "gamer_cat": "Gamer Kawaii Cat 🎧🌸",
    "cyber_cat": "Cyberpunk Neon Cat ⚡🕶️",
    "explorer_cat": "Explorer Cozy Cat 🎒📖",
    "batman_cat": "Batman Cat 🦇🐱",
    "nezuko": "Nezuko Kamado 🌸",
    "zenitsu": "Zenitsu Agatsuma ⚡",
    "inosuke": "Inosuke Hashibira 🐗",
    "akaza": "Akaza (Upper Moon 3) ❄️",
    "tanjiro": "Tanjiro Kamado ⚔️",
    "goth_girl": "Gothic Butterfly 🦋",
    "alien": "Alien Pet 👽",
    "anime_girl": "Anime Girl 🌸",
    "batman": "Batman 🦇",
    "jcb": "JCB Digger 🚜",
    "dragon": "Mythical Dragon 🐉",
    "goku": "Kid Goku 🥋",
    "venom": "Venom 🕷️",
    "spiderman": "Spider-Man 🕷️🕸️",
    "ghost_spider": "Ghost-Spider 🕷️🌸",
    "drip_boy": "Allu 🕶️👟",
}

CARD_STYLE_NAMES = {
    "glass": "Frosted Glass (Glassmorphism) 🪟",
    "crystal_transparent": "Crystal Clear (Transparent) 🫧",
    "ghost_transparent": "Ghost Sheer (Ultra Invisible) 👻",
    "hologram_transparent": "Holo Wireframe (Cyan Glow) 🌌",
    "professional": "Executive Slate (Professional) 💼",
    "cyberpunk": "Cyberpunk Neon (Futuristic) ⚡",
    "aurora": "Sunset Aurora (Velvet Glow) 🌅",
    "emerald": "Emerald Mint (Classic Pet) 🍃",
}

ISLAND_THEME_NAMES = {
    "apple_dynamic": "Apple Dynamic Glass (iOS Pro) 🍎",
    "originos_dark": "OriginOS Obsidian Glass (Deep Space) 🖤",
    "cyber_glow": "Cyberpunk Titanium (Neon Glow) ⚡",
    "frosted_crystal": "Frosted Crystal (Ultra Clear) 🫧",
}

ISLAND_AMBIENT_NAMES = {
    "adaptive_album": "🎨 Adaptive Album Art Aura (Dynamic Sampling)",
    "aurora_borealis": "🌌 Aurora Borealis (Emerald & Cosmic Violet)",
    "neon_cyber_pulse": "⚡ Cyberpunk Neon (Cyan & Laser Magenta)",
    "sunset_chroma": "🌅 Synthwave Sunset (Solar Gold & Rose)",
    "lava_fire_glow": "🔥 Inferno Magma (Bass Reactive Fire)",
    "rainbow_flow": "🌈 RGB Chroma Spectrum (360° Flowing Prism)",
    "minimal_frost": "✨ Apple Minimal Frost (Diamond White Halo)",
}

ISLAND_POSITION_NAMES = {
    "top_notch": "Top Screen Center (Apple Notch) 📱",
    "follow_pet": "Floating Companion (Follow Pet) 🐾",
    "floating": "Free Draggable (Anywhere) 📍",
}


class Settings:
    """Load/save settings; attribute access for individual values."""

    def __init__(self):
        self._data: Dict[str, Any] = dict(DEFAULTS)
        self.load()

    def load(self):
        target = CONFIG_FILE if CONFIG_FILE.exists() else LEGACY_CONFIG
        if target.exists():
            try:
                with open(target, "r", encoding="utf-8") as f:
                    loaded = json.load(f)
                for k, v in loaded.items():
                    if k in DEFAULTS:
                        self._data[k] = v
            except (json.JSONDecodeError, OSError):
                pass

    def save(self):
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(self._data, f, indent=2)

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
        self.setWindowTitle("Pixel Pet – Settings")
        self.setMinimumWidth(380)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowType.WindowContextHelpButtonHint)
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        # ── Character group ──────────────────────────────────────────────────
        char_group = QGroupBox("Pet Character 🐾")
        char_form = QFormLayout(char_group)

        self._pet_combo = QComboBox()
        for key, name in PET_DISPLAY_NAMES.items():
            self._pet_combo.addItem(name, key)

        cur_idx = self._pet_combo.findData(self._s.selected_pet)
        if cur_idx >= 0:
            self._pet_combo.setCurrentIndex(cur_idx)
        char_form.addRow("Active Pet:", self._pet_combo)
        layout.addWidget(char_group)

        # ── Media Player Card Style group ───────────────────────────────────
        card_group = QGroupBox("Media Player Card Style 🎛️")
        card_form = QFormLayout(card_group)

        self._card_combo = QComboBox()
        for key, name in CARD_STYLE_NAMES.items():
            self._card_combo.addItem(name, key)

        cur_card_idx = self._card_combo.findData(self._s.card_style)
        if cur_card_idx >= 0:
            self._card_combo.setCurrentIndex(cur_card_idx)
        card_form.addRow("Card Theme:", self._card_combo)
        layout.addWidget(card_group)

        # ── OriginOS Dynamic Island group ───────────────────────────────────
        island_group = QGroupBox("OriginOS / Apple Dynamic Island 🏝️")
        island_form = QFormLayout(island_group)

        self._island_enable_cb = QCheckBox("Enable Dynamic Island")
        self._island_enable_cb.setChecked(self._s.get("enable_island", True))
        island_form.addRow("", self._island_enable_cb)

        self._island_theme_combo = QComboBox()
        for key, name in ISLAND_THEME_NAMES.items():
            self._island_theme_combo.addItem(name, key)
        cur_ith_idx = self._island_theme_combo.findData(self._s.get("island_style", "originos_dark"))
        if cur_ith_idx >= 0:
            self._island_theme_combo.setCurrentIndex(cur_ith_idx)
        island_form.addRow("Island Theme:", self._island_theme_combo)

        self._island_ambient_combo = QComboBox()
        for key, name in ISLAND_AMBIENT_NAMES.items():
            self._island_ambient_combo.addItem(name, key)
        cur_amb_idx = self._island_ambient_combo.findData(self._s.get("island_ambient_style", "adaptive_album"))
        if cur_amb_idx >= 0:
            self._island_ambient_combo.setCurrentIndex(cur_amb_idx)
        island_form.addRow("Ambient Lighting 🌟:", self._island_ambient_combo)

        self._island_pos_combo = QComboBox()
        for key, name in ISLAND_POSITION_NAMES.items():
            self._island_pos_combo.addItem(name, key)
        cur_pos_idx = self._island_pos_combo.findData(self._s.get("island_position", "top_notch"))
        if cur_pos_idx >= 0:
            self._island_pos_combo.setCurrentIndex(cur_pos_idx)
        island_form.addRow("Island Position:", self._island_pos_combo)

        self._weather_loc_edit = QLineEdit(self._s.get("weather_location", "Kochi, Kerala, India"))
        self._weather_loc_edit.setPlaceholderText("e.g. Kochi, Kerala, India")
        island_form.addRow("Weather City 📍:", self._weather_loc_edit)

        layout.addWidget(island_group)

        # ── Animation group ──────────────────────────────────────────────────
        anim_group = QGroupBox("Animation")
        anim_form = QFormLayout(anim_group)

        self._fps_spin = QSpinBox()
        self._fps_spin.setRange(4, 30)
        self._fps_spin.setValue(self._s.animation_fps)
        self._fps_spin.setSuffix(" fps")
        anim_form.addRow("Animation Speed:", self._fps_spin)

        layout.addWidget(anim_group)

        # ── Movement group ───────────────────────────────────────────────────
        move_group = QGroupBox("Movement")
        move_form = QFormLayout(move_group)

        self._speed_slider = QSlider(Qt.Orientation.Horizontal)
        self._speed_slider.setRange(20, 200)
        self._speed_slider.setValue(self._s.walk_speed)
        self._speed_label = QLabel(f"{self._s.walk_speed} px/s")
        self._speed_slider.valueChanged.connect(
            lambda v: self._speed_label.setText(f"{v} px/s")
        )
        spd_row = QHBoxLayout()
        spd_row.addWidget(self._speed_slider)
        spd_row.addWidget(self._speed_label)
        move_form.addRow("Walking Speed:", spd_row)

        self._size_spin = QSpinBox()
        self._size_spin.setRange(48, 256)
        self._size_spin.setSingleStep(16)
        self._size_spin.setValue(self._s.pet_size)
        self._size_spin.setSuffix(" px")
        move_form.addRow("Pet Size:", self._size_spin)

        self._follow_cb = QCheckBox("Follow mouse cursor")
        self._follow_cb.setChecked(self._s.follow_cursor)
        move_form.addRow("", self._follow_cb)

        layout.addWidget(move_group)

        # ── Sound group ──────────────────────────────────────────────────────
        sound_group = QGroupBox("Sound")
        sound_layout = QVBoxLayout(sound_group)
        self._sound_cb = QCheckBox("Enable sounds")
        self._sound_cb.setChecked(self._s.sounds_enabled)
        sound_layout.addWidget(self._sound_cb)
        layout.addWidget(sound_group)

        # ── System group ─────────────────────────────────────────────────────
        sys_group = QGroupBox("System")
        sys_layout = QVBoxLayout(sys_group)
        self._startup_cb = QCheckBox("Start with Windows")
        self._startup_cb.setChecked(self._s.start_with_windows)
        self._ontop_cb = QCheckBox("Always on top")
        self._ontop_cb.setChecked(self._s.always_on_top)
        sys_layout.addWidget(self._startup_cb)
        sys_layout.addWidget(self._ontop_cb)
        layout.addWidget(sys_group)

        # ── Buttons ──────────────────────────────────────────────────────────
        btn_row = QHBoxLayout()
        ok_btn = QPushButton("OK")
        ok_btn.setDefault(True)
        ok_btn.clicked.connect(self._save_and_close)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        btn_row.addStretch()
        btn_row.addWidget(cancel_btn)
        btn_row.addWidget(ok_btn)
        layout.addLayout(btn_row)

    def _save_and_close(self):
        self._s.selected_pet = self._pet_combo.currentData()
        self._s.card_style = self._card_combo.currentData()
        self._s.enable_island = self._island_enable_cb.isChecked()
        self._s.island_style = self._island_theme_combo.currentData()
        self._s.island_ambient_style = self._island_ambient_combo.currentData()
        self._s.island_position = self._island_pos_combo.currentData()
        self._s.weather_location = self._weather_loc_edit.text().strip() or "Kochi, Kerala, India"
        self._s.animation_fps = self._fps_spin.value()
        self._s.walk_speed = self._speed_slider.value()
        self._s.pet_size = self._size_spin.value()
        self._s.follow_cursor = self._follow_cb.isChecked()
        self._s.sounds_enabled = self._sound_cb.isChecked()
        self._s.start_with_windows = self._startup_cb.isChecked()
        self._s.always_on_top = self._ontop_cb.isChecked()
        self._s.save()
        self.settings_changed.emit(self._s)
        self.accept()
