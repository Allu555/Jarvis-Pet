import ctypes
import ctypes.wintypes
import time
from PySide6.QtCore import Qt, QTimer, QPoint, QRectF
from PySide6.QtGui import QPainter, QColor, QFont, QPainterPath, QPen, QLinearGradient
from PySide6.QtWidgets import QWidget, QLabel, QVBoxLayout

GWL_EXSTYLE      = -20
WS_EX_TOOLWINDOW = 0x00000080
WS_EX_NOACTIVATE = 0x08000000

_user32 = ctypes.windll.user32


class SpeechBubble(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool |
            Qt.WindowType.SubWindow
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)

        self._text = ""
        self._hide_timer = QTimer(self)
        self._hide_timer.setSingleShot(True)
        self._hide_timer.timeout.connect(self._start_hide_anim)

        # OriginOS Pop-in Spring Physics State
        self._anim_scale = 0.0
        self._anim_scale_vel = 0.0
        self._anim_target_scale = 0.0
        self._anim_alpha = 0.0
        self._is_closing = False
        self._last_anim_time = time.monotonic()

        self._anim_timer = QTimer(self)
        self._anim_timer.setTimerType(Qt.TimerType.PreciseTimer)
        self._anim_timer.setInterval(16)  # 60 FPS spring physics
        self._anim_timer.timeout.connect(self._step_spring_anim)

        # Label inside
        self._label = QLabel(self)
        self._label.setStyleSheet("""
            color: #ffffff;
            font-weight: 700;
            font-size: 12px;
            font-family: 'Segoe UI', sans-serif;
        """)
        self._label.setWordWrap(True)
        self._label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 14)
        layout.addWidget(self._label)

    def _step_spring_anim(self):
        now = time.monotonic()
        dt = min(0.04, max(0.001, now - self._last_anim_time))
        self._last_anim_time = now

        diff = self._anim_target_scale - self._anim_scale
        if self._is_closing:
            tension = 340.0
            damping = 26.0
        else:
            tension = 280.0
            damping = 19.5

        if abs(diff) > 0.005 or abs(self._anim_scale_vel) > 0.01:
            acc = tension * diff - damping * self._anim_scale_vel
            self._anim_scale_vel += acc * dt
            self._anim_scale += self._anim_scale_vel * dt
            if self._is_closing:
                self._anim_alpha = max(0.0, self._anim_alpha - dt * 6.0)
            else:
                self._anim_alpha = min(1.0, self._anim_alpha + dt * 7.0)
            self.update()
        else:
            self._anim_scale = self._anim_target_scale
            self._anim_scale_vel = 0.0
            if self._is_closing:
                self._anim_alpha = 0.0
                self._anim_timer.stop()
                self.hide()
            else:
                self._anim_alpha = 1.0
                self._anim_timer.stop()
            self.update()

    def _start_hide_anim(self):
        self._is_closing = True
        self._anim_target_scale = 0.0
        self._last_anim_time = time.monotonic()
        self._anim_timer.start()

    def show_message(self, text: str, pet_x: int, pet_y: int, pet_size: int, duration: float = 4.0):
        self._text = text
        self._label.setText(text)
        self.adjustSize()

        bubble_w = max(140, min(self.sizeHint().width() + 24, 250))
        self.setFixedWidth(bubble_w)
        self.adjustSize()

        # Position bubble directly centered above pet
        bx = int(pet_x + (pet_size - self.width()) / 2)
        by = int(pet_y - self.height() - 6)

        # If too close to screen top, show below pet instead
        if by < 10:
            by = int(pet_y + pet_size + 6)

        self.move(bx, by)

        # Trigger OriginOS Elastic Spring Pop-in Entrance
        self._is_closing = False
        self._anim_scale = 0.2
        self._anim_scale_vel = 0.0
        self._anim_target_scale = 1.0
        self._anim_alpha = 0.2
        self._last_anim_time = time.monotonic()
        self._anim_timer.start()

        self.show()

        self._hide_timer.stop()
        self._hide_timer.start(int(duration * 1000))

    def update_position(self, pet_x: int, pet_y: int, pet_size: int):
        if not self.isVisible():
            return
        bx = int(pet_x + (pet_size - self.width()) / 2)
        by = int(pet_y - self.height() - 6)
        if by < 10:
            by = int(pet_y + pet_size + 6)
        self.move(bx, by)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        rect = self.rect()
        body_rect = QRectF(2, 2, rect.width() - 4, rect.height() - 8)

        # OriginOS Elastic Scale Transform Centered at Bottom Tail
        painter.save()
        painter.setOpacity(self._anim_alpha)
        scale = max(0.01, self._anim_scale)
        tail_cx = body_rect.center().x()
        tail_cy = rect.height() - 2
        painter.translate(tail_cx, tail_cy)
        painter.scale(scale, scale)
        painter.translate(-tail_cx, -tail_cy)

        path = QPainterPath()
        path.addRoundedRect(body_rect, 10, 10)

        # Cute small triangle tail pointing down to pet
        cx = body_rect.center().x()
        tri_path = QPainterPath()
        tri_path.moveTo(cx - 6, body_rect.bottom())
        tri_path.lineTo(cx, rect.height() - 2)
        tri_path.lineTo(cx + 6, body_rect.bottom())
        path.addPath(tri_path)

        # Modern Pet Green acrylic gradient
        grad = QLinearGradient(0, 0, rect.width(), rect.height())
        grad.setColorAt(0.0, QColor(10, 26, 18, 240))
        grad.setColorAt(1.0, QColor(16, 42, 30, 248))
        painter.fillPath(path, grad)

        # Glowing Pet Green border
        painter.setPen(QPen(QColor(56, 239, 125, 175), 1.2))
        painter.drawPath(path)
        painter.restore()
        painter.end()
