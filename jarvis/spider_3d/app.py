"""
spider_3d/app.py – JARVIS 3D Autonomous Vision Recon Drone

Pure Native PySide6 (QWidget + QPainter):
- 100% Guaranteed Visible on any Windows PC (zero Chromium overhead / zero WebEngine crashes)
- Real-time 8-frame leg stepping animation cycles (Normal, Fast/Sprint, Slow/Stalk, Reverse)
- Glowing Holographic Blue LIDAR Scanning Cone & Rotating Radar Ring
- Smooth 60 FPS Desktop Locomotion & Autonomous Edge/Taskbar Patrol
- Instant Task Intercept: rushes to target button/window, fires laser, clicks, celebrates
- Seamless File-based IPC via %TEMP%/jarvis_spider_cmd.json
- Draggable anywhere, topmost, transparent background
"""

import os
import sys

# Permanently disabled per user request
sys.exit(0)
import json
import math
import random
import time
import logging
from pathlib import Path

# Redirect logging to spider_drone.log when headless
_LOG_FILE = Path(__file__).parent / "spider_drone.log"
try:
    if sys.stdout is None or not hasattr(sys.stdout, "write"):
        sys.stdout = open(_LOG_FILE, "a", encoding="utf-8", buffering=1)
    if sys.stderr is None or not hasattr(sys.stderr, "write"):
        sys.stderr = open(_LOG_FILE, "a", encoding="utf-8", buffering=1)
except Exception:
    pass

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("jarvis.spider_3d")

from PySide6.QtWidgets import QApplication, QWidget
from PySide6.QtCore import Qt, QPoint, QPointF, QRect, QRectF, QTimer, Signal, QObject
from PySide6.QtGui import (
    QPainter, QColor, QFont, QPen, QBrush, QPixmap, QImage,
    QRadialGradient, QLinearGradient, QPolygonF, QTransform
)

JARVIS_ROOT = Path(__file__).resolve().parent.parent
if str(JARVIS_ROOT) not in sys.path:
    sys.path.insert(0, str(JARVIS_ROOT))

# ── IPC Paths ────────────────────────────────────────────────────────────────
_TEMP = Path(os.environ.get("TEMP", os.environ.get("TMP", "/tmp")))
IPC_CMD_FILE    = _TEMP / "jarvis_spider_cmd.json"
IPC_STATUS_FILE = _TEMP / "jarvis_spider_status.json"


def _write_status(status: str):
    try:
        IPC_STATUS_FILE.write_text(json.dumps({"status": status, "pid": os.getpid()}), encoding="utf-8")
    except Exception:
        pass


# ── Audio effects via winsound ────────────────────────────────────────────────
def _beep(freq: int = 880, dur: int = 80):
    try:
        import winsound
        winsound.Beep(freq, dur)
    except Exception:
        pass


# ── Drone Widget ─────────────────────────────────────────────────────────────

class SpiderDroneWidget(QWidget):
    W, H = 380, 270

    def __init__(self):
        super().__init__()
        # Native transparent, frameless, topmost desktop tool window
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.resize(self.W, self.H)

        # Screen geometry bounds
        geo = QApplication.primaryScreen().availableGeometry()
        self.screen_w = float(geo.width())
        self.screen_h = float(geo.height())
        self.min_x = 10.0
        self.max_x = max(50.0, self.screen_w - self.W - 10.0)
        self.min_y = 10.0
        self.max_y = max(50.0, self.screen_h - self.H - 10.0)

        # Initial position: Center-right of screen (100% visible in plain sight)
        self.cur_x = float(self.screen_w - self.W - 60.0)
        self.cur_y = float(120.0)
        self.move(int(self.cur_x), int(self.cur_y))
        self.dest_x, self.dest_y = self.cur_x, self.cur_y

        # Locomotion & animation states
        self.walking = False
        self.facing_left = False
        self.task_active = False
        self.pending_desc = ""
        self.patrol_enabled = True
        self.patrol_cooldown = 3.5
        self.is_scanning = False
        self.scan_desc = "SURVEYING SCREEN SECTOR"
        self.is_celebrating = False
        self.autopilot_active = False

        # Gaits: normal, fast, slow, reverse
        self.GAITS = ["normal", "fast", "slow", "reverse"]
        self.gait_idx = 0
        self.current_gait = "normal"
        self.walk_frame_idx = 0
        self.time_counter = 0.0
        self.radar_angle = 0.0

        # Load sprites
        self._load_all_sprites()

        # 60 FPS animation & physics timer
        self._fps_tmr = QTimer(self)
        self._fps_tmr.setInterval(16)
        self._fps_tmr.timeout.connect(self._on_frame)
        self._fps_tmr.start()

        # Step frame timer (for 8-frame leg stepping cycles)
        self._step_tmr = QTimer(self)
        self._step_tmr.setInterval(90)
        self._step_tmr.timeout.connect(self._on_step_tick)
        self._step_tmr.start()

        # IPC poll timer (every 180ms)
        self._ipc_tmr = QTimer(self)
        self._ipc_tmr.setInterval(180)
        self._ipc_tmr.timeout.connect(self._poll_ipc)
        self._ipc_tmr.start()

        # Autonomous Roaming timer (checks every 1s)
        self._patrol_tmr = QTimer(self)
        self._patrol_tmr.setInterval(1000)
        self._patrol_tmr.timeout.connect(self._patrol_tick)
        self._patrol_tmr.start()

        # Drag tracking
        self._drag = False
        self._drag_pos = QPoint()

        # Interactive button definitions (x, y, w, h, label, id)
        self._btn_rects = {}

        _write_status("online")
        logger.info("[JARVIS] 3D Spider Recon Drone ONLINE — Pure Native QWidget")

    def _load_all_sprites(self):
        """Loads root poses and all 32 walk cycle frames as QPixmap."""
        sprites_dir = Path(__file__).parent / "sprites"
        self.sprites = {}

        # Load root poses
        for f in sprites_dir.glob("*.png"):
            pm = QPixmap(str(f))
            if not pm.isNull():
                self.sprites[f.stem] = pm

        # Load walk cycles
        self.walk_cycles = {g: [] for g in self.GAITS}
        walk_dir = sprites_dir / "walk_cycles"
        if walk_dir.exists():
            for g in self.GAITS:
                for i in range(8):
                    f = walk_dir / f"walk_{g}_{i}.png"
                    if f.exists():
                        pm = QPixmap(str(f))
                        if not pm.isNull():
                            self.walk_cycles[g].append(pm)

        logger.info(f"Loaded {len(self.sprites)} poses & {sum(len(v) for v in self.walk_cycles.values())} walk frames.")

    def _on_step_tick(self):
        """Advances leg walking frame index."""
        if self.walking:
            frames = self.walk_cycles.get(self.current_gait, [])
            if frames:
                self.walk_frame_idx = (self.walk_frame_idx + 1) % len(frames)

    def _on_frame(self):
        """60 FPS loop: advances physics, lidar rotation, and triggers repaint."""
        self.time_counter += 0.016
        self.radar_angle = (self.radar_angle + 3.0) % 360.0

        if self.walking:
            dx = self.dest_x - self.cur_x
            dy = self.dest_y - self.cur_y
            dist = math.hypot(dx, dy)

            if dist > 5.5:
                # Crawl speed scaled by active gait
                if self.task_active:
                    spd = max(4.5, min(9.0, dist * 0.055))
                else:
                    if self.current_gait == "fast":
                        spd = 4.2
                    elif self.current_gait == "slow":
                        spd = 1.6
                    elif self.current_gait == "reverse":
                        spd = 2.0
                    else:
                        spd = 2.8

                self.cur_x += (dx / dist) * spd
                self.cur_y += (dy / dist) * spd
                self.move(int(self.cur_x), int(self.cur_y))
            else:
                # Arrived at destination
                self.cur_x, self.cur_y = self.dest_x, self.dest_y
                self.move(int(self.cur_x), int(self.cur_y))
                self.walking = False

                if self.task_active:
                    # Arrived at task element: trigger laser scan
                    self.is_scanning = True
                    self.scan_desc = self.pending_desc or "TARGET LOCKED"
                    _beep(1100, 100)
                    QTimer.singleShot(2400, self._on_task_scan_done)
                else:
                    # Arrived at patrol sector: brief LIDAR survey
                    self.is_scanning = True
                    self.scan_desc = "SURVEYING SCREEN SECTOR"
                    QTimer.singleShot(1800, self._on_patrol_survey_done)

        self.update()

    def _on_task_scan_done(self):
        if not self.walking and self.task_active:
            self.task_active = False
            self.is_scanning = False
            self.patrol_cooldown = random.uniform(5.0, 8.0)

    def _on_patrol_survey_done(self):
        if not self.walking and not self.task_active:
            self.is_scanning = False
            self.patrol_cooldown = random.uniform(4.0, 9.0)

    def _patrol_tick(self):
        """Drives autonomous crawling across desktop sectors."""
        if not self.patrol_enabled or self.task_active or self.walking:
            return

        self.patrol_cooldown -= 1.0
        if self.patrol_cooldown <= 0:
            targets = [
                # Bottom taskbar edge
                (random.uniform(self.min_x, self.max_x), self.max_y - random.uniform(10, 40)),
                # Left screen margin
                (self.min_x + random.uniform(5, 50), random.uniform(self.min_y + 40, self.max_y - 40)),
                # Right screen margin
                (self.max_x - random.uniform(5, 50), random.uniform(self.min_y + 40, self.max_y - 40)),
                # Top screen margin
                (random.uniform(self.min_x, self.max_x), self.min_y + random.uniform(10, 50)),
                # Mid-screen desktop
                (random.uniform(self.min_x + 100, self.max_x - 100), random.uniform(self.min_y + 100, self.max_y - 100)),
            ]
            chosen = random.choice(targets)
            self.dest_x = max(self.min_x, min(self.max_x, chosen[0]))
            self.dest_y = max(self.min_y, min(self.max_y, chosen[1]))

            dist = math.hypot(self.dest_x - self.cur_x, self.dest_y - self.cur_y)
            if dist < 70:
                self.patrol_cooldown = random.uniform(3.0, 6.0)
                return

            self.task_active = False
            self.is_scanning = False
            self.walking = True
            self.facing_left = (self.dest_x < self.cur_x)
            logger.info(f"Patrolling to ({int(self.dest_x)},{int(self.dest_y)})")

    def _poll_ipc(self):
        """Reads JSON commands written by Jarvis."""
        try:
            if not IPC_CMD_FILE.exists():
                return
            raw = IPC_CMD_FILE.read_text(encoding="utf-8").strip()
            if not raw:
                return
            IPC_CMD_FILE.unlink(missing_ok=True)
            cmd = json.loads(raw)
            action = cmd.get("action", "")

            if action == "walk_and_scan":
                tx = int(cmd.get("x", 500))
                ty = int(cmd.get("y", 400))
                desc = cmd.get("desc", "Target Location")
                self.on_walk_scan(tx, ty, desc)
            elif action == "scan_here":
                desc = cmd.get("desc", "Analyzing Screen")
                self.on_scan_here(desc)
            elif action == "celebrate":
                self.on_celebrate()
            elif action == "status":
                self.scan_desc = cmd.get("msg", "READY")
        except Exception as e:
            logger.debug(f"IPC poll error: {e}")

    def on_walk_scan(self, tx: int, ty: int, desc: str):
        """Called when Jarvis commands the spider to walk to a target."""
        self.task_active = True
        self.dest_x = max(self.min_x, min(self.max_x, float(tx - self.W * 0.45)))
        self.dest_y = max(self.min_y, min(self.max_y, float(ty - self.H * 0.76)))
        self.pending_desc = desc
        self.walking = True
        self.facing_left = (self.dest_x < self.cur_x)
        self.is_scanning = False
        _beep(900, 60)
        logger.info(f"Task intercept: walking to ({tx},{ty}) for '{desc}'")

    def on_scan_here(self, desc: str):
        self.is_scanning = True
        self.scan_desc = desc[:35]
        _beep(840, 80)
        QTimer.singleShot(2600, lambda: setattr(self, "is_scanning", False))

    def on_celebrate(self):
        self.task_active = False
        self.is_celebrating = True
        self.is_scanning = False
        _beep(1200, 70)
        _beep(1500, 90)
        QTimer.singleShot(1800, lambda: setattr(self, "is_celebrating", False))
        self.patrol_cooldown = random.uniform(4.0, 7.0)

    # ── Paint Event ──────────────────────────────────────────────────────────

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

        # 1. Rotating LIDAR Radar Ring (at feet of spider)
        cx, cy = self.W * 0.52, self.H * 0.72
        rw, rh = 140.0, 48.0
        p.save()
        p.translate(cx, cy)
        # Radar ellipse
        pen = QPen(QColor(0, 229, 255, 110), 2)
        p.setPen(pen)
        p.setBrush(QColor(0, 229, 255, 18))
        p.drawEllipse(QPointF(0, 0), rw, rh)
        # Radar sweep beam line
        rad = math.radians(self.radar_angle)
        sx = math.cos(rad) * rw
        sy = math.sin(rad) * rh
        p.setPen(QPen(QColor(0, 229, 255, 200), 2))
        p.drawLine(QPointF(0, 0), QPointF(sx, sy))
        p.restore()

        # 2. Holographic Blue Laser Scanning Cone (when scanning)
        if self.is_scanning:
            p.save()
            laser_poly = QPolygonF([
                QPointF(cx + (-25 if self.facing_left else 25), cy - 35),
                QPointF(cx + (-140 if self.facing_left else 140), cy + 50),
                QPointF(cx + (-50 if self.facing_left else 50), cy + 70),
            ])
            grad = QRadialGradient(QPointF(cx, cy - 35), 180)
            grad.setColorAt(0.0, QColor(0, 229, 255, 190))
            grad.setColorAt(0.5, QColor(0, 229, 255, 70))
            grad.setColorAt(1.0, QColor(0, 229, 255, 0))
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QBrush(grad))
            p.drawPolygon(laser_poly)
            p.restore()

        # 3. Spider Sprite Rendering (animated walk cycles or poses)
        current_pm = None
        if self.is_celebrating:
            current_pm = self.sprites.get("jump") or self.sprites.get("idle")
        elif self.is_scanning:
            current_pm = self.sprites.get("scan") or self.sprites.get("idle")
        elif self.walking:
            frames = self.walk_cycles.get(self.current_gait, [])
            if frames:
                current_pm = frames[self.walk_frame_idx % len(frames)]
            else:
                current_pm = self.sprites.get("walk") or self.sprites.get("idle")
        else:
            current_pm = self.sprites.get("idle") or self.sprites.get("front_view")

        if current_pm and not current_pm.isNull():
            # Bobbing calculation
            bob_y = math.sin(self.time_counter * (14.0 if self.walking else 2.5)) * (4.0 if self.walking else 3.0)
            # Flip image if moving left
            if self.facing_left:
                draw_pm = current_pm.transformed(QTransform().scale(-1, 1))
            else:
                draw_pm = current_pm

            # Scale nicely
            target_w = 230
            target_h = int(draw_pm.height() * (target_w / max(1, draw_pm.width())))
            sp_x = int(self.W * 0.5 - target_w * 0.5)
            sp_y = int(self.H * 0.62 - target_h * 0.5 + bob_y)

            p.drawPixmap(sp_x, sp_y, target_w, target_h, draw_pm)

        # 4. Tactical Top-Left HUD
        hud_w, hud_h = 210, 56
        p.setPen(QPen(QColor(0, 229, 255, 140), 1))
        p.setBrush(QColor(6, 12, 24, 215))
        p.drawRoundedRect(10, 10, hud_w, hud_h, 6, 6)
        # Left cyan accent bar
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(0, 229, 255, 240))
        p.drawRoundedRect(10, 10, 4, hud_h, 2, 2)

        # Title
        p.setPen(QColor(0, 229, 255))
        f_title = QFont("Segoe UI", 8, QFont.Weight.Bold)
        f_title.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 1.2)
        p.setFont(f_title)
        # Pulsing status dot
        dot_color = QColor(0, 255, 128) if self.walking else (QColor(255, 145, 0) if self.is_scanning else QColor(0, 229, 255))
        p.setBrush(dot_color)
        p.drawEllipse(22, 17, 7, 7)
        p.drawText(34, 24, "JARVIS 3D TACTICAL SCOUT")

        # Status text
        f_body = QFont("Segoe UI", 7)
        p.setFont(f_body)
        p.setPen(QColor(180, 220, 240))
        if self.is_scanning:
            status_txt = f"LIDAR: {self.scan_desc[:24]}"
        elif self.task_active:
            status_txt = f"INTERCEPT: {self.pending_desc[:22]}"
        elif self.walking:
            status_txt = f"PATROLLING [{self.current_gait.upper()} GAIT]"
        else:
            status_txt = "STATUS: STANDBY // VISION READY"
        p.drawText(22, 38, status_txt)

        # Badge
        badge_txt = "TASK INTERCEPT" if self.task_active else ("SCANNING" if self.is_scanning else ("PATROL ACTIVE" if self.patrol_enabled else "STANDBY"))
        badge_col = QColor(255, 145, 0, 80) if (self.is_scanning or self.task_active) else QColor(0, 229, 255, 50)
        p.setBrush(badge_col)
        p.setPen(Qt.PenStyle.NoPen)
        p.drawRoundedRect(22, 44, 90, 16, 3, 3)
        p.setPen(QColor(255, 200, 100) if (self.is_scanning or self.task_active) else QColor(0, 229, 255))
        f_badge = QFont("Segoe UI", 6, QFont.Weight.Bold)
        p.setFont(f_badge)
        p.drawText(28, 55, badge_txt)

        # 5. Bottom Interactive Controls
        btns = [
            ("⚡ SCAN", "scan", QColor(0, 229, 255)),
            (f"🌐 PATROL: {'ON' if self.patrol_enabled else 'OFF'}", "patrol", QColor(199, 125, 255) if self.patrol_enabled else QColor(140, 140, 160)),
            (f"🕷️ {self.current_gait.upper()}", "gait", QColor(0, 255, 128)),
            (f"🤖 AUTO: {'ON' if self.autopilot_active else 'OFF'}", "auto", QColor(255, 145, 0) if self.autopilot_active else QColor(140, 140, 160)),
            ("✕", "close", QColor(255, 70, 70)),
        ]

        bar_y = self.H - 34
        start_x = 12
        btn_spacing = 6
        f_btn = QFont("Segoe UI", 7, QFont.Weight.Bold)
        p.setFont(f_btn)

        self._btn_rects.clear()
        bx = start_x
        for label, bid, col in btns:
            # Measure text width
            metrics = p.fontMetrics()
            bw = metrics.horizontalAdvance(label) + 16
            rect = QRect(bx, bar_y, bw, 24)
            self._btn_rects[bid] = rect

            # Draw button background
            p.setPen(QPen(col.lighter(120), 1))
            bg_col = QColor(col.red(), col.green(), col.blue(), 45)
            p.setBrush(bg_col)
            p.drawRoundedRect(rect, 12, 12)

            # Draw button text
            p.setPen(col)
            p.drawText(rect, Qt.AlignmentFlag.AlignCenter, label)
            bx += bw + btn_spacing

        p.end()

    # ── Mouse Interaction ────────────────────────────────────────────────────

    def mousePressEvent(self, e):
        pos = e.position().toPoint()

        # Check button clicks
        for bid, rect in self._btn_rects.items():
            if rect.contains(pos):
                self._handle_btn(bid)
                e.accept()
                return

        # Otherwise initiate window drag
        if e.button() == Qt.MouseButton.LeftButton:
            self._drag = True
            self._drag_pos = e.globalPosition().toPoint() - self.frameGeometry().topLeft()
            self.walking = False
            self.task_active = False
            e.accept()

    def mouseMoveEvent(self, e):
        if self._drag and e.buttons() == Qt.MouseButton.LeftButton:
            p = e.globalPosition().toPoint() - self._drag_pos
            self.cur_x = float(max(self.min_x, min(self.max_x, p.x())))
            self.cur_y = float(max(self.min_y, min(self.max_y, p.y())))
            self.move(int(self.cur_x), int(self.cur_y))
            e.accept()

    def mouseReleaseEvent(self, e):
        self._drag = False
        self.dest_x, self.dest_y = self.cur_x, self.cur_y
        self.patrol_cooldown = random.uniform(4.0, 7.0)

    def _handle_btn(self, bid: str):
        if bid == "scan":
            _beep(600, 90)
            self.on_scan_here("SCANNING ACTIVE DESKTOP")
            # Trigger Vision Scout in background thread
            def _s():
                try:
                    from control.spider_scout import SpiderScout
                    SpiderScout.instance().scan_once_and_act("Inspect active window tasks")
                except Exception:
                    pass
            import threading
            threading.Thread(target=_s, daemon=True).start()

        elif bid == "patrol":
            self.patrol_enabled = not self.patrol_enabled
            _beep(880 if self.patrol_enabled else 440, 90)
            if not self.patrol_enabled:
                self.walking = False
                self.dest_x, self.dest_y = self.cur_x, self.cur_y

        elif bid == "gait":
            self.gait_idx = (self.gait_idx + 1) % len(self.GAITS)
            self.current_gait = self.GAITS[self.gait_idx]
            _beep(700 + self.gait_idx * 120, 80)
            logger.info(f"Switched walking gait to: {self.current_gait}")

        elif bid == "auto":
            self.autopilot_active = not self.autopilot_active
            _beep(960 if self.autopilot_active else 400, 100)
            try:
                from control.spider_scout import SpiderScout
                scout = SpiderScout.instance()
                if self.autopilot_active:
                    scout.start_scout("Monitor and automate active desktop tasks")
                else:
                    scout.stop_scout()
            except Exception as e:
                logger.warning(f"Autopilot toggle error: {e}")

        elif bid == "close":
            self.close()

    def closeEvent(self, e):
        _write_status("offline")
        e.accept()


# ── Launch Entrypoint ─────────────────────────────────────────────────────────

def launch():
    try:
        IPC_CMD_FILE.unlink(missing_ok=True)
    except Exception:
        pass

    app = QApplication.instance() or QApplication(sys.argv)
    w = SpiderDroneWidget()
    w.show()
    w.raise_()
    w.activateWindow()

    # Bring topmost on Windows
    try:
        import ctypes
        hwnd = int(w.winId())
        ctypes.windll.user32.SetWindowPos(hwnd, -1, 0, 0, 0, 0, 0x0001 | 0x0002 | 0x0040)
    except Exception:
        pass

    logger.info("[JARVIS] 3D Spider Recon Drone ONLINE — Pure QPainter Visible")
    return app.exec()


if __name__ == "__main__":
    sys.exit(launch())
