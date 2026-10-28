import math
import random
from pathlib import Path
from typing import Optional, List

from PySide6.QtCore import Qt, QTimer, QPoint, QRect, QRectF
from PySide6.QtGui import (
    QPainter, QColor, QFont, QFontMetrics, QPainterPath, QPen, QPixmap, QImage,
    QLinearGradient
)
from PySide6.QtWidgets import (
    QWidget, QPushButton, QHBoxLayout, QVBoxLayout,
    QGraphicsDropShadowEffect
)

from media_service import MediaService, MediaInfo

ALBUM_ART_PATH = Path(__file__).parent / "assets" / "sprites" / "album_art.png"


CARD_THEMES = {
    "glass": {
        "name": "Frosted Glass 🪟",
        "bg_top": QColor(18, 24, 38, 235),
        "bg_bottom": QColor(10, 14, 24, 248),
        "border": QColor(200, 230, 255, 140),
        "border_width": 1.2,
        "badge_color": QColor(100, 210, 255),
        "title_color": QColor(255, 255, 255),
        "artist_color": QColor(176, 208, 230),
        "art_bg": QColor(15, 22, 34),
        "art_border": QColor(200, 230, 255, 75),
        "ctrl_btn_bg": "rgba(255, 255, 255, 0.10)",
        "ctrl_btn_hover": "rgba(100, 210, 255, 0.3)",
        "ctrl_btn_border": "rgba(200, 230, 255, 0.35)",
        "ctrl_btn_color": "#ffffff",
        "play_grad_0": "#64d2ff",
        "play_grad_1": "#007aff",
        "play_btn_color": "#ffffff",
        "resume_bg": "rgba(100, 210, 255, 0.2)",
        "resume_border": "#64d2ff",
        "resume_color": "#64d2ff",
        "eq_color_0": QColor(100, 210, 255),
        "eq_color_1": QColor(0, 122, 255),
    },
    "crystal_transparent": {
        "name": "Crystal Clear 🫧",
        "bg_top": QColor(10, 15, 25, 65),
        "bg_bottom": QColor(20, 30, 50, 95),
        "border": QColor(255, 255, 255, 120),
        "border_width": 1.0,
        "badge_color": QColor(168, 230, 207),
        "title_color": QColor(255, 255, 255),
        "artist_color": QColor(212, 232, 248),
        "art_bg": QColor(15, 25, 35, 110),
        "art_border": QColor(255, 255, 255, 90),
        "ctrl_btn_bg": "rgba(255, 255, 255, 0.15)",
        "ctrl_btn_hover": "rgba(255, 255, 255, 0.35)",
        "ctrl_btn_border": "rgba(255, 255, 255, 0.45)",
        "ctrl_btn_color": "#ffffff",
        "play_grad_0": "#ffffff",
        "play_grad_1": "#a8e6cf",
        "play_btn_color": "#0a1a10",
        "resume_bg": "rgba(255, 255, 255, 0.25)",
        "resume_border": "rgba(255, 255, 255, 0.75)",
        "resume_color": "#ffffff",
        "eq_color_0": QColor(255, 255, 255, 230),
        "eq_color_1": QColor(100, 220, 255, 230),
    },
    "ghost_transparent": {
        "name": "Ghost Sheer (Ultra Invisible) 👻",
        "bg_top": QColor(0, 0, 0, 35),
        "bg_bottom": QColor(0, 0, 0, 65),
        "border": QColor(255, 255, 255, 75),
        "border_width": 0.9,
        "badge_color": QColor(255, 255, 255),
        "title_color": QColor(255, 255, 255),
        "artist_color": QColor(224, 224, 224),
        "art_bg": QColor(0, 0, 0, 100),
        "art_border": QColor(255, 255, 255, 65),
        "ctrl_btn_bg": "rgba(255, 255, 255, 0.12)",
        "ctrl_btn_hover": "rgba(255, 255, 255, 0.28)",
        "ctrl_btn_border": "rgba(255, 255, 255, 0.35)",
        "ctrl_btn_color": "#ffffff",
        "play_grad_0": "rgba(255, 255, 255, 0.9)",
        "play_grad_1": "rgba(210, 210, 210, 0.9)",
        "play_btn_color": "#000000",
        "resume_bg": "rgba(255, 255, 255, 0.18)",
        "resume_border": "rgba(255, 255, 255, 0.6)",
        "resume_color": "#ffffff",
        "eq_color_0": QColor(255, 255, 255, 210),
        "eq_color_1": QColor(190, 190, 190, 210),
    },
    "hologram_transparent": {
        "name": "Holo Wireframe 🌌",
        "bg_top": QColor(0, 20, 40, 70),
        "bg_bottom": QColor(0, 10, 30, 95),
        "border": QColor(0, 243, 255, 160),
        "border_width": 1.1,
        "badge_color": QColor(0, 243, 255),
        "title_color": QColor(255, 255, 255),
        "artist_color": QColor(112, 228, 255),
        "art_bg": QColor(0, 30, 50, 110),
        "art_border": QColor(0, 243, 255, 120),
        "ctrl_btn_bg": "rgba(0, 243, 255, 0.15)",
        "ctrl_btn_hover": "rgba(0, 243, 255, 0.38)",
        "ctrl_btn_border": "rgba(0, 243, 255, 0.55)",
        "ctrl_btn_color": "#00f3ff",
        "play_grad_0": "#00f3ff",
        "play_grad_1": "#0077ff",
        "play_btn_color": "#001a2e",
        "resume_bg": "rgba(0, 243, 255, 0.25)",
        "resume_border": "#00f3ff",
        "resume_color": "#00f3ff",
        "eq_color_0": QColor(0, 243, 255),
        "eq_color_1": QColor(0, 119, 255),
    },
    "professional": {
        "name": "Executive Slate 💼",
        "bg_top": QColor(24, 28, 36, 250),
        "bg_bottom": QColor(36, 42, 54, 252),
        "border": QColor(170, 185, 205, 175),
        "border_width": 1.0,
        "badge_color": QColor(140, 160, 184),
        "title_color": QColor(242, 245, 248),
        "artist_color": QColor(156, 174, 194),
        "art_bg": QColor(22, 26, 34),
        "art_border": QColor(170, 185, 205, 80),
        "ctrl_btn_bg": "rgba(255, 255, 255, 0.06)",
        "ctrl_btn_hover": "rgba(255, 255, 255, 0.16)",
        "ctrl_btn_border": "rgba(170, 185, 205, 0.3)",
        "ctrl_btn_color": "#e1e7ec",
        "play_grad_0": "#e1e7ec",
        "play_grad_1": "#9fb0c4",
        "play_btn_color": "#12161f",
        "resume_bg": "rgba(225, 231, 236, 0.15)",
        "resume_border": "#a0b2c6",
        "resume_color": "#e1e7ec",
        "eq_color_0": QColor(180, 195, 215),
        "eq_color_1": QColor(110, 125, 145),
    },
    "cyberpunk": {
        "name": "Cyberpunk Neon ⚡",
        "bg_top": QColor(14, 2, 28, 250),
        "bg_bottom": QColor(28, 0, 52, 252),
        "border": QColor(0, 243, 255, 210),
        "border_width": 1.4,
        "badge_color": QColor(255, 0, 127),
        "title_color": QColor(255, 255, 255),
        "artist_color": QColor(0, 243, 255),
        "art_bg": QColor(18, 2, 36),
        "art_border": QColor(255, 0, 127, 110),
        "ctrl_btn_bg": "rgba(255, 0, 127, 0.16)",
        "ctrl_btn_hover": "rgba(0, 243, 255, 0.35)",
        "ctrl_btn_border": "rgba(0, 243, 255, 0.5)",
        "ctrl_btn_color": "#00f3ff",
        "play_grad_0": "#ff007f",
        "play_grad_1": "#7928ca",
        "play_btn_color": "#ffffff",
        "resume_bg": "rgba(0, 243, 255, 0.2)",
        "resume_border": "#00f3ff",
        "resume_color": "#00f3ff",
        "eq_color_0": QColor(255, 0, 127),
        "eq_color_1": QColor(0, 243, 255),
    },
    "aurora": {
        "name": "Sunset Aurora 🌅",
        "bg_top": QColor(38, 8, 64, 250),
        "bg_bottom": QColor(68, 14, 72, 252),
        "border": QColor(255, 183, 3, 200),
        "border_width": 1.2,
        "badge_color": QColor(255, 183, 3),
        "title_color": QColor(255, 255, 255),
        "artist_color": QColor(251, 133, 0),
        "art_bg": QColor(36, 6, 56),
        "art_border": QColor(255, 183, 3, 90),
        "ctrl_btn_bg": "rgba(255, 183, 3, 0.12)",
        "ctrl_btn_hover": "rgba(255, 183, 3, 0.3)",
        "ctrl_btn_border": "rgba(255, 183, 3, 0.35)",
        "ctrl_btn_color": "#ffd166",
        "play_grad_0": "#ffb703",
        "play_grad_1": "#fb8500",
        "play_btn_color": "#240638",
        "resume_bg": "rgba(255, 183, 3, 0.2)",
        "resume_border": "#ffb703",
        "resume_color": "#ffd166",
        "eq_color_0": QColor(255, 183, 3),
        "eq_color_1": QColor(251, 133, 0),
    },
    "emerald": {
        "name": "Emerald Mint 🍃",
        "bg_top": QColor(10, 24, 18, 245),
        "bg_bottom": QColor(16, 42, 30, 250),
        "border": QColor(56, 239, 125, 180),
        "border_width": 1.2,
        "badge_color": QColor(56, 239, 125),
        "title_color": QColor(255, 255, 255),
        "artist_color": QColor(142, 221, 178),
        "art_bg": QColor(11, 31, 21),
        "art_border": QColor(56, 239, 125, 80),
        "ctrl_btn_bg": "rgba(255, 255, 255, 0.08)",
        "ctrl_btn_hover": "rgba(56, 239, 125, 0.25)",
        "ctrl_btn_border": "rgba(56, 239, 125, 0.25)",
        "ctrl_btn_color": "#d4f8e8",
        "play_grad_0": "#38ef7d",
        "play_grad_1": "#11998e",
        "play_btn_color": "#051a10",
        "resume_bg": "rgba(56, 239, 125, 0.18)",
        "resume_border": "#38ef7d",
        "resume_color": "#4ef590",
        "eq_color_0": QColor(56, 239, 125),
        "eq_color_1": QColor(17, 153, 142),
    },
}


class MediaNotificationCard(QWidget):
    """
    High-Performance Frameless Media Card with 100% Guaranteed Zero Ghosting.
    All backgrounds, texts, artwork, and equalizer bars are composited directly
    to an ARGB32 buffer in a single pass to eliminate Qt Windows DWM alpha artifacts.
    """
    def __init__(self, card_style: str = "glass", parent=None):
        super().__init__(parent)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool |
            Qt.WindowType.SubWindow
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)

        self.setFixedSize(288, 88)

        self._card_style = card_style if card_style in CARD_THEMES else "glass"
        self._media_service = MediaService.get_instance()
        self._is_playing = True
        self._title = "No Track Playing"
        self._artist = "Tap play to listen"
        self._badge = "🎵 MUSIC"
        self._album_pixmap: Optional[QPixmap] = None

        # Equalizer bar animation
        self._eq_phase = 0.0
        self._eq_heights = [3, 7, 10, 5]

        # Timers (started only when card is visible)
        self._eq_timer = QTimer(self)
        self._eq_timer.setTimerType(Qt.TimerType.PreciseTimer)
        self._eq_timer.setInterval(16)
        self._eq_timer.timeout.connect(self._animate_eq)

        self._auto_hide_timer = QTimer(self)
        self._auto_hide_timer.setSingleShot(True)
        self._auto_hide_timer.timeout.connect(self.hide)

        self._refresh_timer = QTimer(self)
        self._refresh_timer.setInterval(500)
        self._refresh_timer.timeout.connect(self._sync_with_media_service)

        self._build_controls()
        self._load_default_art()
        self.set_card_style(self._card_style)
        self._media_service.add_listener(self._on_media_changed)

    def _build_controls(self):
        # Interactive Buttons placed over the canvas
        self._prev_btn = QPushButton("⏮", self)
        self._prev_btn.setFixedSize(22, 22)
        self._prev_btn.move(76, 58)
        self._prev_btn.setToolTip("Previous Track")
        self._prev_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._prev_btn.clicked.connect(self._on_prev)

        self._play_btn = QPushButton("⏸ Pause", self)
        self._play_btn.setFixedHeight(22)
        self._play_btn.setMinimumWidth(68)
        self._play_btn.move(104, 58)
        self._play_btn.setToolTip("Play / Pause")
        self._play_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._play_btn.clicked.connect(self._on_play_pause)

        self._next_btn = QPushButton("⏭", self)
        self._next_btn.setFixedSize(22, 22)
        self._next_btn.move(178, 58)
        self._next_btn.setToolTip("Next Track")
        self._next_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._next_btn.clicked.connect(self._on_next)

        self._close_btn = QPushButton("✕", self)
        self._close_btn.setFixedSize(16, 16)
        self._close_btn.move(262, 8)
        self._close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._close_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                color: #a0b0c0;
                border: none;
                font-size: 10px;
                font-weight: bold;
                border-radius: 8px;
            }
            QPushButton:hover {
                background: rgba(255, 255, 255, 0.2);
                color: #ff5577;
            }
        """)
        self._close_btn.clicked.connect(self.hide)

    def _load_default_art(self):
        if ALBUM_ART_PATH.exists():
            self._album_pixmap = QPixmap(str(ALBUM_ART_PATH))
        else:
            self._album_pixmap = None

    def set_card_style(self, style_name: str):
        if style_name not in CARD_THEMES:
            style_name = "glass"
        self._card_style = style_name
        theme = CARD_THEMES[style_name]

        btn_style = f"""
            QPushButton {{
                background: {theme['ctrl_btn_bg']};
                color: {theme['ctrl_btn_color']};
                border: 1px solid {theme['ctrl_btn_border']};
                border-radius: 10px;
                font-size: 10px;
                font-weight: bold;
                outline: none;
            }}
            QPushButton:hover {{
                background: {theme['ctrl_btn_hover']};
                color: #ffffff;
            }}
            QPushButton:pressed {{
                background: {theme['ctrl_btn_hover']};
            }}
        """
        self._prev_btn.setStyleSheet(btn_style)
        self._next_btn.setStyleSheet(btn_style)

        self._update_play_button_style(self._is_playing)
        self.update()

    def _update_play_button_style(self, is_playing: bool):
        self._is_playing = is_playing
        theme = CARD_THEMES.get(self._card_style, CARD_THEMES["glass"])
        if is_playing:
            self._play_btn.setText("⏸ Pause")
            self._play_btn.setStyleSheet(f"""
                QPushButton {{
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 {theme['play_grad_0']}, stop:1 {theme['play_grad_1']});
                    color: {theme['play_btn_color']};
                    border: none;
                    outline: none;
                    border-radius: 11px;
                    font-size: 9.5px;
                    font-weight: 800;
                    padding: 0 6px;
                }}
                QPushButton:hover {{
                    opacity: 0.9;
                }}
                QPushButton:pressed {{
                    opacity: 0.75;
                }}
            """)
        else:
            self._play_btn.setText("▶ Resume")
            self._play_btn.setStyleSheet(f"""
                QPushButton {{
                    background: {theme['resume_bg']};
                    border: 1px solid {theme['resume_border']};
                    color: {theme['resume_color']};
                    border-radius: 11px;
                    font-size: 9.5px;
                    font-weight: 800;
                    padding: 0 6px;
                    outline: none;
                }}
                QPushButton:hover {{
                    background: {theme['ctrl_btn_hover']};
                    color: #ffffff;
                }}
                QPushButton:pressed {{
                    opacity: 0.8;
                }}
            """)

    def _animate_eq(self):
        if not self._is_playing or not self.isVisible():
            return
        self._eq_phase += 0.08
        for i in range(len(self._eq_heights)):
            val = math.sin(self._eq_phase + i * 1.25) * 4.2 + 6.0
            self._eq_heights[i] = max(2, min(11, int(round(val))))
        self.update()

    def _on_media_changed(self, info: MediaInfo):
        QTimer.singleShot(0, lambda: self._apply_media_info(info))

    def _apply_media_info(self, info: MediaInfo):
        if not info.has_media:
            return
        self._title = info.display_title()
        self._artist = info.display_artist()
        self._badge = f"🎵 {info.app_name.upper()}"
        self._is_playing = info.is_playing

        if info.thumbnail_bytes:
            qimg = QImage.fromData(info.thumbnail_bytes)
            if not qimg.isNull():
                self._album_pixmap = QPixmap.fromImage(qimg)
            else:
                self._load_default_art()
        else:
            self._load_default_art()

        self._update_play_button_style(info.is_playing)
        self.update()

    def _sync_with_media_service(self):
        info = self._media_service.get_current_media()
        if info.has_media:
            self._apply_media_info(info)

    def show_card(
        self,
        track_title: str = "",
        pet_x: int = 0,
        pet_y: int = 0,
        pet_size: int = 128,
        duration: float = 10.0
    ):
        info = self._media_service.get_current_media()
        if info.has_media:
            self._apply_media_info(info)
        elif track_title:
            raw = track_title.strip()
            app_name = "MUSIC"
            if raw.lower().startswith("spotify - "):
                app_name = "SPOTIFY"
                raw = raw[10:].strip()
            elif raw.lower().startswith("brave - "):
                app_name = "BRAVE"
                raw = raw[8:].strip()
            elif raw.lower().startswith("chrome - "):
                app_name = "CHROME"
                raw = raw[9:].strip()

            if " - " in raw:
                parts = raw.split(" - ", 1)
                self._artist = parts[0].strip()
                self._title = parts[1].strip()
            else:
                self._title = raw
                self._artist = "Playing in background"

            self._badge = f"🎵 {app_name}"
            self._load_default_art()
            self._update_play_button_style(True)

        QTimer.singleShot(80, self._sync_with_media_service)

        bx = int(pet_x + (pet_size - self.width()) / 2)
        by = int(pet_y - self.height() - 8)

        if by < 10:
            by = int(pet_y + pet_size + 8)

        self.move(bx, by)
        self.show()
        if self._is_playing:
            self._eq_timer.start()
        self.update()

        self._refresh_timer.start()
        self._auto_hide_timer.stop()
        self._auto_hide_timer.start(int(duration * 1000))

    def update_position(self, pet_x: int, pet_y: int, pet_size: int):
        if not self.isVisible():
            return
        bx = int(pet_x + (pet_size - self.width()) / 2)
        by = int(pet_y - self.height() - 8)
        if by < 10:
            by = int(pet_y + pet_size + 8)
        self.move(bx, by)

    def _on_play_pause(self):
        self._media_service.toggle_play_pause()
        new_state = not self._is_playing
        self._update_play_button_style(new_state)
        if new_state:
            self._eq_timer.start()
        else:
            self._eq_timer.stop()
        self._auto_hide_timer.start(10000)
        self.update()

    def _on_prev(self):
        self._media_service.skip_previous()
        self._auto_hide_timer.start(10000)

    def _on_next(self):
        self._media_service.skip_next()
        self._auto_hide_timer.start(10000)

    def hide(self):
        self._refresh_timer.stop()
        self._eq_timer.stop()
        super().hide()

    def paintEvent(self, event):
        theme = CARD_THEMES.get(self._card_style, CARD_THEMES["glass"])

        # ── Offscreen Buffer (ARGB32) to completely eliminate all ghosting ──
        buffer = QImage(self.width(), self.height(), QImage.Format.Format_ARGB32_Premultiplied)
        buffer.fill(0)

        p = QPainter(buffer)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)

        # 1. Main Card Background
        card_rect = QRectF(2, 2, self.width() - 4, self.height() - 4)
        card_path = QPainterPath()
        card_path.addRoundedRect(card_rect, 14, 14)

        grad = QLinearGradient(0, 0, self.width(), self.height())
        grad.setColorAt(0.0, theme["bg_top"])
        grad.setColorAt(1.0, theme["bg_bottom"])
        p.fillPath(card_path, grad)

        # Card Border
        border_pen = QPen(theme["border"], theme["border_width"])
        p.setPen(border_pen)
        p.drawPath(card_path)

        # 2. Album Artwork
        art_rect = QRectF(10, 10, 56, 56)
        art_path = QPainterPath()
        art_path.addRoundedRect(art_rect, 10, 10)

        p.fillPath(art_path, theme["art_bg"])

        if self._album_pixmap and not self._album_pixmap.isNull():
            p.save()
            p.setClipPath(art_path)
            scaled = self._album_pixmap.scaled(
                56, 56,
                Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                Qt.TransformationMode.SmoothTransformation
            )
            ox = int(10 + (56 - scaled.width()) / 2)
            oy = int(10 + (56 - scaled.height()) / 2)
            p.drawPixmap(ox, oy, scaled)
            p.restore()

        art_pen = QPen(theme["art_border"], 1.0)
        p.setPen(art_pen)
        p.drawPath(art_path)

        # 3. Badge Text ("🎵 SPOTIFY", "🎵 BRAVE", etc.)
        badge_font = QFont("Segoe UI", 8)
        badge_font.setBold(True)
        badge_font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 0.5)
        p.setFont(badge_font)
        p.setPen(theme["badge_color"])

        fm_badge = QFontMetrics(badge_font)
        badge_width = fm_badge.horizontalAdvance(self._badge)
        p.drawText(76, 20, self._badge)

        # 4. Animated Equalizer Sound Bars
        eq_x = 76 + badge_width + 8
        eq_base_y = 20
        bar_w = 2.5
        spacing = 3.0

        for h in self._eq_heights:
            b_rect = QRectF(eq_x, eq_base_y - h, bar_w, h)
            b_path = QPainterPath()
            b_path.addRoundedRect(b_rect, 1.0, 1.0)

            eq_grad = QLinearGradient(eq_x, eq_base_y - h, eq_x, eq_base_y)
            eq_grad.setColorAt(0.0, theme["eq_color_0"])
            eq_grad.setColorAt(1.0, theme["eq_color_1"])
            p.fillPath(b_path, eq_grad)
            eq_x += bar_w + spacing

        # 5. Song Title
        title_font = QFont("Segoe UI", 9)
        title_font.setBold(True)
        p.setFont(title_font)
        p.setPen(theme["title_color"])

        fm_title = QFontMetrics(title_font)
        elided_title = fm_title.elidedText(self._title, Qt.TextElideMode.ElideRight, 175)
        p.drawText(76, 36, elided_title)

        # 6. Artist Name
        artist_font = QFont("Segoe UI", 8)
        artist_font.setBold(False)
        p.setFont(artist_font)
        p.setPen(theme["artist_color"])

        fm_artist = QFontMetrics(artist_font)
        elided_artist = fm_artist.elidedText(self._artist, Qt.TextElideMode.ElideRight, 175)
        p.drawText(76, 50, elided_artist)

        p.end()

        # ── Copy Buffer Directly with Source Composition to guarantee zero ghosting ──
        wp = QPainter(self)
        wp.setCompositionMode(QPainter.CompositionMode.CompositionMode_Source)
        wp.drawImage(0, 0, buffer)
        wp.end()
