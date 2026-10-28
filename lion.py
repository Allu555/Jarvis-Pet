import ctypes
import ctypes.wintypes
import random
import time
from typing import Optional, List

from PySide6.QtCore import Qt, QTimer, QPoint
from PySide6.QtGui import QPainter, QPixmap, QImage, QAction, QCursor
from PySide6.QtWidgets import QWidget, QApplication, QMenu

from animation import AnimationController, PET_TYPES
from movement import MovementController, STATE_TO_ANIM, PetState
from settings import Settings, SettingsDialog
from speech_bubble import SpeechBubble
from media_card import MediaNotificationCard
from origin_island import OriginIsland
from activity import ActivityMonitor
from pet_manager import PetManager
import startup

# ── Win32 constants ───────────────────────────────────────────────────────────
GWL_EXSTYLE      = -20
WS_EX_TOOLWINDOW = 0x00000080
WS_EX_NOACTIVATE = 0x08000000
WM_NCHITTEST     = 0x0084
HTTRANSPARENT    = -1
HTCLIENT         = 1

_user32 = ctypes.windll.user32

_user32.GetWindowLongW.argtypes  = [ctypes.wintypes.HWND, ctypes.c_int]
_user32.GetWindowLongW.restype   = ctypes.c_long
_user32.SetWindowLongW.argtypes  = [ctypes.wintypes.HWND, ctypes.c_int, ctypes.c_long]
_user32.SetWindowLongW.restype   = ctypes.c_long
_user32.GetWindowRect.argtypes   = [ctypes.wintypes.HWND, ctypes.POINTER(ctypes.wintypes.RECT)]
_user32.GetWindowRect.restype    = ctypes.wintypes.BOOL
HWND_TOPMOST     = -1
SWP_NOSIZE       = 0x0001
SWP_NOMOVE       = 0x0002
SWP_NOACTIVATE   = 0x0010
SWP_SHOWWINDOW   = 0x0040

_user32.SetWindowPos.argtypes = [
    ctypes.wintypes.HWND, ctypes.wintypes.HWND,
    ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int,
    ctypes.c_uint
]
_user32.SetWindowPos.restype = ctypes.wintypes.BOOL


def _hwnd(widget: QWidget) -> int:
    return int(widget.winId())


def _apply_extended_styles(hwnd: int):
    style = _user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
    _user32.SetWindowLongW(hwnd, GWL_EXSTYLE, style | WS_EX_TOOLWINDOW | WS_EX_NOACTIVATE)
    _user32.SetWindowPos(hwnd, HWND_TOPMOST, 0, 0, 0, 0, SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE | SWP_SHOWWINDOW)


class LionWindow(QWidget):
    FRAME_MS = 16   # ~60 fps: butter-smooth high refresh rate movement and physics

    def __init__(self, settings: Settings, is_secondary: bool = False):
        super().__init__(None)
        self._settings = settings
        self.is_secondary = is_secondary
        self._paused = False
        self._last_frame_time = time.monotonic()
        self._pet_size = settings.pet_size

        self._anim = AnimationController(
            fps=settings.animation_fps,
            pet_type=settings.get("selected_pet", "alien")
        )
        self._move = MovementController(
            walk_speed=settings.walk_speed,
            inactivity_sleep=25.0,
            follow_cursor=settings.get("follow_cursor", True),
        )

        self._activity = ActivityMonitor()
        self._bubble = SpeechBubble()
        self._media_card = MediaNotificationCard(
            card_style=settings.get("card_style", "glass")
        )
        self._island = OriginIsland(settings=self._settings) if not self.is_secondary else None

        self._current_pixmap, _ = self._anim.tick(self._pet_size)
        self._click_timestamps: List[float] = []
        self._is_mouse_down = False
        self._is_dragging = False
        self._drag_start_pos = QPoint(0, 0)
        self._drag_offset = QPoint(0, 0)

        self._last_music_state = False
        self._last_auto_talk = time.monotonic()

        self._build_window()
        self._setup_timer()

        # Register in central multi-pet manager
        PetManager.instance().register_pet(self)

        if self._island and self._settings.get("enable_island", True):
            self._island.show()

        # Initial welcome speech for primary pet
        if not self.is_secondary:
            QTimer.singleShot(1500, self._show_welcome)

    # ── Properties & Helpers ──────────────────────────────────────────────────

    @property
    def pet_type(self) -> str:
        return self._anim.pet_type

    @property
    def pet_size(self) -> int:
        return self._pet_size

    def set_pos(self, x: int, y: int):
        self._move.set_position(x, y, self._pet_size)
        self.move(self._move.x, self._move.y)
        self._bubble.update_position(self._move.x, self._move.y, self._pet_size)
        self._media_card.update_position(self._move.x, self._move.y, self._pet_size)

    # ── Window setup ──────────────────────────────────────────────────────────

    def _build_window(self):
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground)
        self.setWindowTitle("PixelPet")

        self.setGeometry(self._move.x, self._move.y, self._pet_size, self._pet_size)
        self.show()
        self.raise_()

        _apply_extended_styles(_hwnd(self))

    def _show_welcome(self):
        self._bubble.show_message(
            "Hi there! ✨ I'm your desktop pet!\nRight-click to spawn more pets, or 5-click to toggle follow!",
            self._move.x, self._move.y, self._pet_size, duration=5.0
        )

    # ── Timer / game loop ─────────────────────────────────────────────────────

    def _setup_timer(self):
        self._timer = QTimer(self)
        self._timer.setTimerType(Qt.TimerType.PreciseTimer)
        self._timer.timeout.connect(self._tick)
        self._timer.start(self.FRAME_MS)

    def _tick(self):
        now = time.monotonic()
        delta = now - self._last_frame_time
        self._last_frame_time = now

        if self._paused:
            return

        cursor_pos = QCursor.pos()
        self._move.update(
            delta,
            cursor_x=cursor_pos.x(),
            cursor_y=cursor_pos.y(),
            pet_size=self._pet_size,
        )

        # Update island follower anchor if primary pet
        if self._island and self._island.isVisible():
            self._island.set_pet_anchor(self._move.x, self._move.y, self._pet_size)

        # 1. Real-time typing detection -> Working mode
        is_typing = self._activity.is_user_typing()
        if is_typing:
            if self._move.state not in (PetState.DRAG, PetState.FALL):
                if self._move.state != PetState.WORK:
                    self._move.trigger_work()
                    self._anim.set_state("work")

        # 2. Music detection & automatic dancing
        is_music, category = self._activity.update()
        if is_music and not self._last_music_state:
            self._last_music_state = True
            if self._move.state not in (PetState.DRAG, PetState.FALL) and not is_typing:
                self._move.trigger_music()
                self._anim.set_state("music")
                song = self._activity._detect_song() or "Playing Music"
                self._media_card.show_card(song, self._move.x, self._move.y, self._pet_size, duration=8.0)
        elif not is_music and self._last_music_state:
            self._last_music_state = False

        # 3. Periodic companion chat (every 50-70s)
        if now - self._last_auto_talk > random.uniform(50.0, 70.0):
            self._last_auto_talk = now
            if self._move.state not in (PetState.DRAG, PetState.FALL, PetState.SLEEP):
                msg = self._activity.get_context_message()
                self._bubble.show_message(msg, self._move.x, self._move.y, self._pet_size, duration=4.0)

        anim_name = STATE_TO_ANIM.get(self._move.state, "idle")
        self._anim.set_state(anim_name)

        # Advance animation and get pre-scaled frame
        raw, frame_changed = self._anim.tick(self._pet_size)
        self._current_pixmap = raw

        new_x, new_y = self._move.x, self._move.y
        if self.x() != new_x or self.y() != new_y:
            self.move(new_x, new_y)
            self._bubble.update_position(new_x, new_y, self._pet_size)
            self._media_card.update_position(new_x, new_y, self._pet_size)

        self.update()

    # ── Painting ──────────────────────────────────────────────────────────────

    def paintEvent(self, event):
        if self._current_pixmap is None or self._current_pixmap.isNull():
            self._current_pixmap, _ = self._anim.tick(self._pet_size)
        if self._current_pixmap is None or self._current_pixmap.isNull():
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
        painter.drawPixmap(0, 0, self._current_pixmap)
        painter.end()

    # ── Click-through via WM_NCHITTEST ────────────────────────────────────────

    def nativeEvent(self, event_type: bytes, message) -> tuple:
        if event_type == b"windows_generic_MSG":
            msg = ctypes.cast(
                int(message),
                ctypes.POINTER(ctypes.wintypes.MSG)
            ).contents
            if msg.message == WM_NCHITTEST:
                lp = msg.lParam
                sx = ctypes.c_int16(lp & 0xFFFF).value
                sy = ctypes.c_int16((lp >> 16) & 0xFFFF).value
                rect = ctypes.wintypes.RECT()
                _user32.GetWindowRect(_hwnd(self), ctypes.byref(rect))
                lx = sx - rect.left
                ly = sy - rect.top
                if self._is_opaque(lx, ly):
                    return True, HTCLIENT
                return True, HTTRANSPARENT
        return super().nativeEvent(event_type, message)

    def _is_opaque(self, lx: int, ly: int) -> bool:
        size = self._pet_size
        if lx < 0 or ly < 0 or lx >= size or ly >= size:
            return False
        img = self._anim.current_frame_image(size)
        if img is None or img.isNull():
            return False
        alpha = (img.pixel(lx, ly) >> 24) & 0xFF
        return alpha > 30

    # ── Mouse events ──────────────────────────────────────────────────────────

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._is_mouse_down = True
            self._is_dragging = False
            self._drag_start_pos = event.globalPosition().toPoint()
            self._drag_offset = event.position().toPoint()
        elif event.button() == Qt.MouseButton.MiddleButton:
            self._move.trigger_work()
            self._anim.set_state("work")
            self._bubble.show_message("Working on my hologram tablet! 💻", self._move.x, self._move.y, self._pet_size)
        elif event.button() == Qt.MouseButton.RightButton:
            self._show_context_menu(event.globalPosition().toPoint())

    def mouseMoveEvent(self, event):
        if self._is_mouse_down:
            delta = (event.globalPosition().toPoint() - self._drag_start_pos).manhattanLength()
            if delta > 4:
                target_pos = event.globalPosition().toPoint() - self._drag_offset
                if not self._is_dragging:
                    self._is_dragging = True
                    self._move.start_drag(target_pos.x(), target_pos.y())
                    self._anim.set_state("drag")
                else:
                    self._move.drag_to(target_pos.x(), target_pos.y(), self._pet_size)
                self.move(self._move.x, self._move.y)
                self._bubble.update_position(self._move.x, self._move.y, self._pet_size)
                self._media_card.update_position(self._move.x, self._move.y, self._pet_size)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            now = time.monotonic()
            if self._is_dragging:
                self._is_dragging = False
                self._move.end_drag(self._pet_size)
                anim_name = STATE_TO_ANIM.get(self._move.state, "idle")
                self._anim.set_state(anim_name)
            elif self._is_mouse_down:
                # ── 5-Click detection for follow toggle ──
                self._click_timestamps.append(now)
                self._click_timestamps = [t for t in self._click_timestamps if now - t <= 2.2]

                if len(self._click_timestamps) >= 5:
                    self._click_timestamps.clear()
                    self._move.follow_cursor = not self._move.follow_cursor
                    self._settings.follow_cursor = self._move.follow_cursor
                    self._settings.save()

                    if self._move.follow_cursor:
                        self._anim.set_state("happy")
                        self._bubble.show_message(
                            "🎯 Cursor Following: ON!\nI'm following you everywhere!",
                            self._move.x, self._move.y, self._pet_size, duration=3.5
                        )
                    else:
                        self._anim.set_state("shrug")
                        self._bubble.show_message(
                            "🐾 Cursor Following: OFF!\nRoaming around freely!",
                            self._move.x, self._move.y, self._pet_size, duration=3.5
                        )
                else:
                    # Single click reaction
                    self._last_auto_talk = now
                    song = self._activity._detect_song()
                    if song:
                        self._media_card.show_card(song, self._move.x, self._move.y, self._pet_size, duration=8.0)
                        self._move.trigger_music()
                        self._anim.set_state("music")
                    else:
                        msg = self._activity.get_context_message()
                        self._bubble.show_message(msg, self._move.x, self._move.y, self._pet_size, duration=3.5)

                        choice = random.choice(["happy", "idea", "shrug", "blink"])
                        if choice == "happy":
                            self._move.trigger_happy()
                            self._anim.set_state("happy")
                        elif choice == "idea":
                            self._move.trigger_idea()
                            self._anim.set_state("idea")
                        elif choice == "shrug":
                            self._move.trigger_shrug()
                            self._anim.set_state("shrug")
                        else:
                            self._move.trigger_action("blink")
                            self._anim.set_state("blink")

            self._is_mouse_down = False

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            song = self._activity._detect_song()
            if song:
                self._move.trigger_music()
                self._anim.set_state("music")
                self._media_card.show_card(song, self._move.x, self._move.y, self._pet_size, duration=8.0)
            else:
                action = random.choice(["idea", "work", "jump"])
                if action == "idea":
                    self._move.trigger_idea()
                    self._anim.set_state("idea")
                    self._bubble.show_message("Eureka! I just had a bright idea! 💡", self._move.x, self._move.y, self._pet_size)
                elif action == "work":
                    self._move.trigger_work()
                    self._anim.set_state("work")
                    self._bubble.show_message("Typing notes into my holo-pad! 💻", self._move.x, self._move.y, self._pet_size)
                else:
                    self._move.trigger_jump()
                    self._anim.set_state("jump")

    # ── Context menu ──────────────────────────────────────────────────────────

    def _show_context_menu(self, pos: QPoint):
        menu = QMenu()
        menu.setWindowFlags(menu.windowFlags() | Qt.WindowType.WindowStaysOnTopHint)

        # ── 1. Spawn Another Pet Submenu ──
        spawn_menu = menu.addMenu("Spawn Another Pet ➕")
        pet_options = [
            ("Streetwear Drip Cat 🕶️🪙", "drip_cat"),
            ("Gamer Kawaii Cat 🎧🌸", "gamer_cat"),
            ("Cyberpunk Neon Cat ⚡🕶️", "cyber_cat"),
            ("Explorer Cozy Cat 🎒📖", "explorer_cat"),
            ("Batman Cat 🦇🐱", "batman_cat"),
            ("Nezuko Kamado 🌸", "nezuko"),
            ("Zenitsu Agatsuma ⚡", "zenitsu"),
            ("Inosuke Hashibira 🐗", "inosuke"),
            ("Akaza (Upper Moon 3) ❄️", "akaza"),
            ("Tanjiro Kamado ⚔️", "tanjiro"),
            ("Kid Goku 🥋", "goku"),
            ("Venom 🕷️", "venom"),
            ("Spider-Man 🕷️🕸️", "spiderman"),
            ("Ghost-Spider 🕷️🌸", "ghost_spider"),
            ("Allu 🕶️👟", "drip_boy"),
            ("Mythical Dragon 🐉", "dragon"),
            ("Batman 🦇", "batman"),
            ("Gothic Butterfly 🦋", "goth_girl"),
            ("Anime Girl 🌸", "anime_girl"),
            ("Alien Pet 👽", "alien"),
            ("JCB Digger 🚜", "jcb"),
        ]
        for label, pkey in pet_options:
            act = QAction(label, self)
            act.triggered.connect(lambda checked=False, pk=pkey: self._spawn_new_pet(pk))
            spawn_menu.addAction(act)

        spawn_menu.addSeparator()
        rnd_act = QAction("🎲 Spawn Random Pet", self)
        rnd_act.triggered.connect(self._spawn_random_pet)
        spawn_menu.addAction(rnd_act)

        menu.addSeparator()

        # ── 2. Switch Current Pet Submenu ──
        pets_menu = menu.addMenu("Switch This Pet 🐾")
        current_pet = self._anim.pet_type
        for label, pet_key in pet_options:
            pet_act = QAction(label, self)
            pet_act.setCheckable(True)
            pet_act.setChecked(current_pet == pet_key)
            pet_act.triggered.connect(lambda checked=False, pk=pet_key: self._select_pet(pk))
            pets_menu.addAction(pet_act)

        # ── 3. OriginOS Dynamic Island Submenu (if primary pet) ──
        if self._island:
            island_menu = menu.addMenu("OriginOS Dynamic Island 🏝️")

            island_toggle_act = QAction("Enable Dynamic Island ✨", self)
            island_toggle_act.setCheckable(True)
            island_toggle_act.setChecked(self._settings.get("enable_island", True))
            island_toggle_act.toggled.connect(self._toggle_island)
            island_menu.addAction(island_toggle_act)

            island_menu.addSeparator()

            island_themes_menu = island_menu.addMenu("Island Theme 🎨")
            theme_options = [
                ("OriginOS Obsidian Glass 🖤", "originos_dark"),
                ("Apple Dynamic Glass 🍎", "apple_dynamic"),
                ("Cyber Glow Neon ⚡", "cyber_glow"),
                ("Frosted Crystal Clear 🫧", "frosted_crystal"),
            ]
            cur_island_theme = self._settings.get("island_style", "originos_dark")
            for label, t_key in theme_options:
                t_act = QAction(label, self)
                t_act.setCheckable(True)
                t_act.setChecked(cur_island_theme == t_key)
                t_act.triggered.connect(lambda checked=False, tk=t_key: self._select_island_theme(tk))
                island_themes_menu.addAction(t_act)

            island_ambient_menu = island_menu.addMenu("Ambient Light Effect 🌟")
            ambient_options = [
                ("🎨 Adaptive Album Art Aura", "adaptive_album"),
                ("🌌 Aurora Borealis Flow", "aurora_borealis"),
                ("⚡ Cyberpunk Neon Strobe", "neon_cyber_pulse"),
                ("🌅 Synthwave Sunset Glow", "sunset_chroma"),
                ("🔥 Inferno Magma Pulse", "lava_fire_glow"),
                ("🌈 RGB Chroma Spectrum (360°)", "rainbow_flow"),
                ("✨ Apple Minimalist Frost", "minimal_frost"),
            ]
            cur_ambient_style = self._settings.get("island_ambient_style", "adaptive_album")
            for label, a_key in ambient_options:
                a_act = QAction(label, self)
                a_act.setCheckable(True)
                a_act.setChecked(cur_ambient_style == a_key)
                a_act.triggered.connect(lambda checked=False, ak=a_key: self._select_island_ambient_style(ak))
                island_ambient_menu.addAction(a_act)

            island_pos_menu = island_menu.addMenu("Island Position 📍")
            pos_options = [
                ("Top Screen Center (Notch) 🖥️", "top_notch"),
                ("Companion Follow Pet 🐾", "follow_pet"),
                ("Free Floating (Draggable) 📌", "floating"),
            ]
            cur_island_pos = self._settings.get("island_position", "top_notch")
            for label, p_key in pos_options:
                p_act = QAction(label, self)
                p_act.setCheckable(True)
                p_act.setChecked(cur_island_pos == p_key)
                p_act.triggered.connect(lambda checked=False, pk=p_key: self._select_island_position(pk))
                island_pos_menu.addAction(p_act)

        # ── 4. Media notification & Companion Talk ──
        media_action = QAction("Media Player Controls 🎛️", self)
        media_action.triggered.connect(self._show_now_playing)
        menu.addAction(media_action)

        talk_action = QAction("Talk / Tips 💬", self)
        talk_action.triggered.connect(self._talk_action_triggered)
        menu.addAction(talk_action)

        # ── 5. Pet Custom Actions Submenu ──
        actions_menu = menu.addMenu("Pet Actions 🎮")
        actions = [
            ("Music Dance 🎵", "music"),
            ("Water Dragon / Signature Skill ⚡🌊", "roar"),
            ("Snack / Train / Work 🍙💻", "work"),
            ("Lightbulb Idea 💡", "idea"),
            ("Happy Cheer ✨", "happy"),
            ("Shrug / Greet 👋", "shrug"),
            ("Acrobatic Leap / Jump ⚡", "jump"),
            ("Rest & Sleep 💤", "sleep"),
            ("Cry / Sad 😢", "cry"),
            ("Sit Down 🐾", "sit"),
            ("Walk Left ⬅️", "walk_left"),
            ("Walk Right ➡️", "walk_right"),
        ]
        for label, anim in actions:
            act = QAction(label, self)
            act.triggered.connect(lambda checked=False, a=anim: self._play_custom_action(a))
            actions_menu.addAction(act)

        menu.addSeparator()

        # Follow cursor toggle
        follow_action = QAction("Follow Cursor 🎯 (or 5-Click)", self)
        follow_action.setCheckable(True)
        follow_action.setChecked(self._move.follow_cursor)
        follow_action.toggled.connect(self._toggle_follow_cursor)
        menu.addAction(follow_action)

        pause_action = QAction("Pause ⏸️", self)
        pause_action.setCheckable(True)
        pause_action.setChecked(self._paused)
        pause_action.toggled.connect(self._toggle_pause)
        menu.addAction(pause_action)

        menu.addSeparator()

        settings_action = QAction("Settings… ⚙️", self)
        settings_action.triggered.connect(self._open_settings)
        menu.addAction(settings_action)

        menu.addSeparator()

        # Dismiss / Close options
        dismiss_this_act = QAction("Dismiss This Pet ❌", self)
        dismiss_this_act.triggered.connect(self.close)
        menu.addAction(dismiss_this_act)

        if len(PetManager.instance().pets) > 1:
            dismiss_others_act = QAction("Dismiss All Other Pets 🧹", self)
            dismiss_others_act.triggered.connect(lambda: PetManager.instance().dismiss_all_except(self))
            menu.addAction(dismiss_others_act)

        exit_action = QAction("Exit All Pets 🛑", self)
        exit_action.triggered.connect(QApplication.quit)
        menu.addAction(exit_action)

        menu.exec(pos)

    def _spawn_new_pet(self, pet_type: str):
        PetManager.instance().spawn_pet(pet_type, near_x=self._move.x, near_y=self._move.y)
        self._bubble.show_message(f"Spawned a new friend: {pet_type}! 🐾✨", self._move.x, self._move.y, self._pet_size, duration=3.0)

    def _spawn_random_pet(self):
        PetManager.instance().spawn_random_pet(near_x=self._move.x, near_y=self._move.y)
        self._bubble.show_message("Spawned a random pet companion! 🎲✨", self._move.x, self._move.y, self._pet_size, duration=3.0)

    def _toggle_island(self, enable: bool):
        if not self._island:
            return
        self._settings.enable_island = enable
        self._settings.save()
        if enable:
            self._island.show()
            self._bubble.show_message("OriginOS Dynamic Island Enabled! 🏝️✨", self._move.x, self._move.y, self._pet_size, duration=3.0)
        else:
            self._island.hide()
            self._bubble.show_message("Dynamic Island Hidden 🏝️", self._move.x, self._move.y, self._pet_size, duration=2.5)

    def _select_island_theme(self, theme_key: str):
        if not self._island:
            return
        self._settings.island_style = theme_key
        self._settings.save()
        self._island.set_island_style(theme_key)
        self._bubble.show_message(f"Dynamic Island Theme: {theme_key} 🎨", self._move.x, self._move.y, self._pet_size, duration=2.5)

    def _select_island_ambient_style(self, ambient_key: str):
        if not self._island:
            return
        self._settings.island_ambient_style = ambient_key
        self._settings.save()
        self._island.set_ambient_style(ambient_key)
        self._bubble.show_message(f"Ambient Light: {ambient_key} 🌟", self._move.x, self._move.y, self._pet_size, duration=2.5)

    def _select_island_position(self, pos_key: str):
        if not self._island:
            return
        self._settings.island_position = pos_key
        self._settings.save()
        self._island.set_island_position(pos_key)
        self._bubble.show_message(f"Dynamic Island Position: {pos_key} 📍", self._move.x, self._move.y, self._pet_size, duration=2.5)

    def _show_now_playing(self):
        song = self._activity._detect_song() or "Playing Audio / Media"
        self._media_card.show_card(song, self._move.x, self._move.y, self._pet_size, duration=8.0)
        self._move.trigger_music()
        self._anim.set_state("music")
        if self._island and self._island.isVisible():
            self._island.expand_to_state(1)

    def _talk_action_triggered(self):
        msg = self._activity.get_context_message()
        self._bubble.show_message(msg, self._move.x, self._move.y, self._pet_size, duration=4.0)
        self._anim.set_state("happy")

    def _play_custom_action(self, action_name: str):
        self._move.trigger_action(action_name)
        self._anim.set_state(action_name)
        pet = self._anim.pet_type
        if action_name == "music":
            song = self._activity._detect_song() or "Grooving to the music!"
            self._media_card.show_card(song, self._move.x, self._move.y, self._pet_size, duration=8.0)
        elif action_name == "idea":
            self._bubble.show_message("I've got a great idea! 💡", self._move.x, self._move.y, self._pet_size, duration=3.5)
        elif action_name == "happy":
            self._bubble.show_message("Yay! Feeling wonderful! ✨💖", self._move.x, self._move.y, self._pet_size, duration=3.0)
        elif action_name == "shrug":
            self._bubble.show_message("Hey there! How's your day going? 👋", self._move.x, self._move.y, self._pet_size, duration=3.0)
        elif action_name == "cry":
            self._bubble.show_message("Uwahh... feeling a bit emotional... 😢", self._move.x, self._move.y, self._pet_size, duration=3.0)
        elif action_name == "sit":
            self._bubble.show_message("Taking a cozy little seat right here! 🐾", self._move.x, self._move.y, self._pet_size, duration=3.0)
        elif action_name == "walk_left":
            self._bubble.show_message("Strolling to the left! ⬅️", self._move.x, self._move.y, self._pet_size, duration=2.5)
        elif action_name == "walk_right":
            self._bubble.show_message("Strolling to the right! ➡️", self._move.x, self._move.y, self._pet_size, duration=2.5)
        elif action_name == "roar":
            if pet == "batman_cat":
                self._bubble.show_message("HISS! Feline Shadows Unleashed! 🦇🐱⚡\nProtecting Gotham in the night!", self._move.x, self._move.y, self._pet_size, duration=4.0)
            elif pet == "drip_cat":
                self._bubble.show_message("GOLD DRIP MEOW! 🕶️🪙✨\nToo stylish for this desktop!", self._move.x, self._move.y, self._pet_size, duration=4.0)
            elif pet == "gamer_cat":
                self._bubble.show_message("VICTORY ROYALE NYAA~! 🎧🌸🎮\nChat is going wild in the stream!", self._move.x, self._move.y, self._pet_size, duration=4.0)
            elif pet == "cyber_cat":
                self._bubble.show_message("NEON OVERDRIVE! ⚡🕶️💾\nCyberpunk firewalls bypassed!", self._move.x, self._move.y, self._pet_size, duration=4.0)
            elif pet == "explorer_cat":
                self._bubble.show_message("EXPEDITION DISCOVERY! 🎒📖🗺️\nNew secrets found in the ancient lore!", self._move.x, self._move.y, self._pet_size, duration=4.0)
            elif pet == "nezuko":
                self._bubble.show_message("Exploding Blood Demon Art: Pyrokinesis! 🌸🔥\nPink lotus flames burst forth!", self._move.x, self._move.y, self._pet_size, duration=4.5)
            elif pet == "zenitsu":
                self._bubble.show_message("Thunder Breathing First Form: THUNDERCLAP AND FLASH! ⚡⚡\nSixfold godspeed strike!", self._move.x, self._move.y, self._pet_size, duration=4.5)
            elif pet == "inosuke":
                self._bubble.show_message("Beast Breathing Fifth Fang: CRAZY CUTTING! 🐗⚔️\nPIG ASSAULT! PIG ASSAULT!", self._move.x, self._move.y, self._pet_size, duration=4.5)
            elif pet == "akaza":
                self._bubble.show_message("Destructive Death: COMPASS NEEDLE! ❄️🥋\nAir Type Annihilation Shockwaves!", self._move.x, self._move.y, self._pet_size, duration=4.5)
            elif pet == "tanjiro":
                self._bubble.show_message("Water Breathing 10th Form: Constant Flux! 🌊🐉⚔️\n(Water Dragon Unleashed!)", self._move.x, self._move.y, self._pet_size, duration=4.5)
            elif pet == "goth_girl":
                self._bubble.show_message("Dark Butterfly Swarm Magic! 🦋✨🔮\nIlluminating the twilight sky...", self._move.x, self._move.y, self._pet_size, duration=4.0)
            elif pet == "dragon":
                self._bubble.show_message("ROAAAR! 🔥🐉\nInferno Dragon Fire Breath!", self._move.x, self._move.y, self._pet_size, duration=4.0)
            elif pet == "batman":
                self._bubble.show_message("I AM THE NIGHT! 🦇", self._move.x, self._move.y, self._pet_size, duration=3.0)
            elif pet == "goku":
                self._bubble.show_message("KAMEHAMEHA! 💥🥋\nFull Power Ki Blast!", self._move.x, self._move.y, self._pet_size, duration=4.0)
            elif pet == "venom":
                self._bubble.show_message("WE ARE VENOM! 🕷️⚡\nScreeching Symbiote Roar!", self._move.x, self._move.y, self._pet_size, duration=4.0)
            elif pet == "spiderman":
                self._bubble.show_message("THWIP! Web-Shooter Barrage! 🕸️⚡\nYour friendly neighborhood Spider-Man is on duty!", self._move.x, self._move.y, self._pet_size, duration=4.5)
            elif pet == "ghost_spider":
                self._bubble.show_message("WEB BURST! 🕸️🌸✨\nGhost-Spider web-line swing barrage!", self._move.x, self._move.y, self._pet_size, duration=4.5)
            else:
                self._bubble.show_message("ROAAAR! 🦁⚡", self._move.x, self._move.y, self._pet_size, duration=3.0)
        elif action_name == "work":
            if pet == "batman_cat":
                self._bubble.show_message("Studying Batcomputer security footage! 💻🦇", self._move.x, self._move.y, self._pet_size, duration=3.5)
            elif pet == "drip_cat":
                self._bubble.show_message("Coding like a boss on laptop! 💻🕶️☕\nGood Code = Good Day!", self._move.x, self._move.y, self._pet_size, duration=3.5)
            elif pet == "gamer_cat":
                self._bubble.show_message("Streaming on pink laptop with sweet boba tea! 💻🎧🧋🌸", self._move.x, self._move.y, self._pet_size, duration=3.5)
            elif pet == "cyber_cat":
                self._bubble.show_message("Hacking cyberspace with neon energy boost! 💻⚡🔋", self._move.x, self._move.y, self._pet_size, duration=3.5)
            elif pet == "explorer_cat":
                self._bubble.show_message("Studying ancient lore books with warm tea! 📖🎒☕\nStay Pawsitive!", self._move.x, self._move.y, self._pet_size, duration=3.5)
            elif pet == "nezuko":
                self._bubble.show_message("Mmh mmh! 🌸 Tiny Nezuko happy dance!", self._move.x, self._move.y, self._pet_size, duration=3.5)
            elif pet == "zenitsu":
                self._bubble.show_message("Training lightning quick reflexes! ⚡🌾", self._move.x, self._move.y, self._pet_size, duration=3.5)
            elif pet == "inosuke":
                self._bubble.show_message("Sharpening dual jagged Nichirin katanas! 🐗⚔️", self._move.x, self._move.y, self._pet_size, duration=3.5)
            elif pet == "akaza":
                self._bubble.show_message("Demon martial arts stance training! 🥋❄️", self._move.x, self._move.y, self._pet_size, duration=3.5)
            elif pet == "tanjiro":
                self._bubble.show_message("Delicious onigiri rice ball snack! 🍙✨\nRegaining stamina for demon slaying!", self._move.x, self._move.y, self._pet_size, duration=3.5)
            elif pet == "goth_girl":
                self._bubble.show_message("Studying my ancient gothic grimoire... 📖✨", self._move.x, self._move.y, self._pet_size, duration=3.5)
            elif pet == "dragon":
                self._bubble.show_message("Guarding my hoard of gold & crystal eggs! 🪙💎", self._move.x, self._move.y, self._pet_size, duration=3.5)
            elif pet == "jcb":
                self._bubble.show_message("Digging & scooping gravel! ⛏️🚜", self._move.x, self._move.y, self._pet_size, duration=3.5)
            elif pet == "goku":
                self._bubble.show_message("Devouring a feast after training! 🍜🍗", self._move.x, self._move.y, self._pet_size, duration=3.5)
            elif pet == "venom":
                self._bubble.show_message("Symbiote flexing muscles! 💪🖤", self._move.x, self._move.y, self._pet_size, duration=3.5)
            elif pet == "spiderman":
                self._bubble.show_message("Hacking into Stark Web-Tech mainframe! 💻🕷️⚡", self._move.x, self._move.y, self._pet_size, duration=3.5)
            elif pet == "ghost_spider":
                self._bubble.show_message("Coordinating missions with Spider-Bot! 🕷️🤖✨", self._move.x, self._move.y, self._pet_size, duration=3.5)
            else:
                self._bubble.show_message("Working on my holo-pad! 💻", self._move.x, self._move.y, self._pet_size, duration=3.5)
        elif action_name == "jump":
            if pet == "batman_cat":
                self._bubble.show_message("Stealthy gargoyle prowl! 🦇🐱✨", self._move.x, self._move.y, self._pet_size, duration=2.5)
            elif pet in ["drip_cat", "gamer_cat", "cyber_cat", "explorer_cat"]:
                self._bubble.show_message("Acrobatic feline leap! 🐾✨", self._move.x, self._move.y, self._pet_size, duration=2.5)
            elif pet == "inosuke":
                self._bubble.show_message("Beast acrobatic flip! 🐗💨", self._move.x, self._move.y, self._pet_size, duration=2.5)
            elif pet == "zenitsu":
                self._bubble.show_message("Lightning dash leap! ⚡🌾", self._move.x, self._move.y, self._pet_size, duration=2.5)
            elif pet == "tanjiro":
                self._bubble.show_message("Total Concentration Breathing Leap! ⚡🗡️", self._move.x, self._move.y, self._pet_size, duration=2.5)
            elif pet == "goth_girl":
                self._bubble.show_message("Gliding gracefully with my gothic parasol! ☂️🦋", self._move.x, self._move.y, self._pet_size, duration=2.5)
            elif pet == "dragon":
                self._bubble.show_message("Soaring into flight! 🦅⚡", self._move.x, self._move.y, self._pet_size, duration=2.5)
            elif pet == "goku":
                self._bubble.show_message("Flying on Flying Nimbus! ☁️✨", self._move.x, self._move.y, self._pet_size, duration=2.5)
            elif pet == "spiderman":
                self._bubble.show_message("Acrobatic web-swing leap through the skyline! 🕸️🏙️✨", self._move.x, self._move.y, self._pet_size, duration=3.0)
            elif pet == "ghost_spider":
                self._bubble.show_message("Gliding on web-wings through the sky! 🕸️🌸✨", self._move.x, self._move.y, self._pet_size, duration=3.0)
            else:
                self._bubble.show_message("Leaping high! 🦘✨", self._move.x, self._move.y, self._pet_size, duration=2.5)
        elif action_name == "sleep":
            if pet == "drip_cat":
                self._bubble.show_message("Curled up cat nap on black plush cushion... 💤🕶️🐟", self._move.x, self._move.y, self._pet_size, duration=3.0)
            elif pet == "gamer_cat":
                self._bubble.show_message("Cozy nap on pink cushion dreaming of fish snacks... 💤🎧🌸", self._move.x, self._move.y, self._pet_size, duration=3.0)
            elif pet == "cyber_cat":
                self._bubble.show_message("Recharging in sleep mode on neon bed... 💤⚡🕶️", self._move.x, self._move.y, self._pet_size, duration=3.0)
            elif pet == "explorer_cat":
                self._bubble.show_message("Resting peacefully on cozy green campsite cushion... 💤🎒📖", self._move.x, self._move.y, self._pet_size, duration=3.0)
            elif pet == "nezuko":
                self._bubble.show_message("Curling up peacefully inside the wooden travel box... 💤📦🌸", self._move.x, self._move.y, self._pet_size, duration=3.5)
            elif pet == "tanjiro":
                self._bubble.show_message("Resting peacefully by Nezuko's wooden box... 💤📦", self._move.x, self._move.y, self._pet_size, duration=3.0)
            elif pet == "batman_cat":
                self._bubble.show_message("Sleeping in the shadow of Wayne Manor... 💤🦇", self._move.x, self._move.y, self._pet_size, duration=2.5)
            elif pet == "goth_girl":
                self._bubble.show_message("Resting peacefully in the dark sanctuary... 💤🖤", self._move.x, self._move.y, self._pet_size, duration=2.5)
            elif pet == "dragon":
                self._bubble.show_message("Resting in the dragon's lair... 💤", self._move.x, self._move.y, self._pet_size, duration=2.5)
            elif pet == "spiderman":
                self._bubble.show_message("Hanging upside down in a cozy web cocoon... 💤🕸️", self._move.x, self._move.y, self._pet_size, duration=3.0)
            elif pet == "ghost_spider":
                self._bubble.show_message("Hanging upside down in a cozy pink web hammock... 💤🕸️🌸", self._move.x, self._move.y, self._pet_size, duration=3.0)
            else:
                self._bubble.show_message("Taking a peaceful nap... 💤", self._move.x, self._move.y, self._pet_size, duration=2.5)

    def _select_pet(self, pet_key: str):
        if self._anim.pet_type == pet_key:
            return
        self._anim.set_pet(pet_key)
        self._settings.selected_pet = pet_key
        self._settings.save()
        
        pet_names = {
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
        }
        pet_name = pet_names.get(pet_key, "Pet")
        if pet_key == "drip_cat":
            self._bubble.show_message("Meow with drip! 🕶️✨\nCheck the gold chain, homie! 🪙", self._move.x, self._move.y, self._pet_size, duration=4.0)
        elif pet_key == "gamer_cat":
            self._bubble.show_message("Nyaa~! 🎧🌸\nGamer Cat ready for the livestream! 🎮✨", self._move.x, self._move.y, self._pet_size, duration=4.0)
        elif pet_key == "cyber_cat":
            self._bubble.show_message("Neon systems online! ⚡🕶️\nCyber Cat hacking into the mainframe! 💻✨", self._move.x, self._move.y, self._pet_size, duration=4.0)
        elif pet_key == "explorer_cat":
            self._bubble.show_message("Adventure awaits! 🎒🗺️\nCozy Explorer Cat ready for journey & books! 📖✨", self._move.x, self._move.y, self._pet_size, duration=4.0)
        elif pet_key == "batman_cat":
            self._bubble.show_message("Meow! I am the Cat Knight of Gotham! 🦇🐱\nProtecting your desktop from the shadows!", self._move.x, self._move.y, self._pet_size, duration=4.5)
        elif pet_key == "nezuko":
            self._bubble.show_message("Mmh mmh! 🌸✨\nNezuko is here to keep you company and brighten your day!", self._move.x, self._move.y, self._pet_size, duration=4.5)
        elif pet_key == "zenitsu":
            self._bubble.show_message("AAAAHHH! Thunderclap and Flash! ⚡💥\nZenitsu reporting for duty!", self._move.x, self._move.y, self._pet_size, duration=4.5)
        elif pet_key == "inosuke":
            self._bubble.show_message("PIG ASSAULT! 🐗💨\nLord Inosuke has arrived! Watch my legendary acrobatics!", self._move.x, self._move.y, self._pet_size, duration=4.5)
        elif pet_key == "akaza":
            self._bubble.show_message("Destructive Death: Compass Needle! ❄️🥋\nLet us hone our martial prowess together!", self._move.x, self._move.y, self._pet_size, duration=4.5)
        elif pet_key == "tanjiro":
            self._bubble.show_message("Kamado Tanjiro desu! ⚔️🔥\nI will protect you with Water & Sun Breathing!", self._move.x, self._move.y, self._pet_size, duration=4.5)
        elif pet_key == "goth_girl":
            self._bubble.show_message("Hello... I'm your Gothic Butterfly pet 🦋🖤\nLet me flutter alongside you in the shadows...", self._move.x, self._move.y, self._pet_size, duration=4.5)
        elif pet_key == "batman":
            self._bubble.show_message("I am vengeance. I am the night.\nI am Batman! 🦇", self._move.x, self._move.y, self._pet_size, duration=4.0)
        elif pet_key == "jcb":
            self._bubble.show_message("Vroom Vroom! 🚜💨\nJCB Digger ready for heavy work! ⛏️", self._move.x, self._move.y, self._pet_size, duration=4.0)
        elif pet_key == "dragon":
            self._bubble.show_message("I awaken! 🐉⚡\nThe Winged Dragon takes flight!", self._move.x, self._move.y, self._pet_size, duration=4.0)
        elif pet_key == "goku":
            self._bubble.show_message("Hey, it's me, Goku! 🥋✨\nLet's train and find the Dragon Balls! 🐉", self._move.x, self._move.y, self._pet_size, duration=4.0)
        elif pet_key == "venom":
            self._bubble.show_message("WE ARE VENOM! 🕷️🖤\nTime to hunt some snacks!", self._move.x, self._move.y, self._pet_size, duration=4.0)
        elif pet_key == "spiderman":
            self._bubble.show_message("THWIP! 🕸️ Your friendly neighborhood Spider-Man is here!\nReady to swing across your desktop! 🕷️🏙️", self._move.x, self._move.y, self._pet_size, duration=4.5)
        elif pet_key == "ghost_spider":
            self._bubble.show_message("Hey there! I'm Ghost-Spider! 🕷️🌸\nReady to rock and swing into action!", self._move.x, self._move.y, self._pet_size, duration=4.5)
        elif pet_key == "drip_boy":
            self._bubble.show_message("Yo! Allu in the house! 🕶️👟✨\nReady to chill, code & skate on your desktop!", self._move.x, self._move.y, self._pet_size, duration=4.5)
        else:
            self._bubble.show_message(f"Switched to {pet_name}!\nHello there! ✨", self._move.x, self._move.y, self._pet_size, duration=3.5)
        self._anim.set_state("happy")

    def _toggle_follow_cursor(self, checked: bool):
        self._move.follow_cursor = checked
        self._settings.follow_cursor = checked
        self._settings.save()
        if checked:
            self._bubble.show_message("🎯 Cursor Following: ON!", self._move.x, self._move.y, self._pet_size, duration=3.0)
        else:
            self._bubble.show_message("🐾 Cursor Following: OFF!", self._move.x, self._move.y, self._pet_size, duration=3.0)

    def _toggle_pause(self, checked: bool):
        self._paused = checked
        if checked:
            self._move.pause()
            self._bubble.show_message("Paused ⏸️", self._move.x, self._move.y, self._pet_size, duration=2.0)
        else:
            self._move.resume()
            self._bubble.show_message("Resumed ▶️", self._move.x, self._move.y, self._pet_size, duration=2.0)

    def _open_settings(self):
        dlg = SettingsDialog(self._settings, parent=None)
        dlg.settings_changed.connect(self._apply_settings)
        dlg.exec()

    def _apply_settings(self, s: Settings):
        self._anim.set_pet(s.selected_pet)
        self._anim.set_fps(s.animation_fps)
        self._move.walk_speed = s.walk_speed
        self._move.follow_cursor = s.follow_cursor
        self._media_card.set_card_style(s.card_style)
        self._pet_size = s.pet_size
        self.resize(s.pet_size, s.pet_size)
        
        # OriginOS Dynamic Island settings
        if self._island:
            if s.get("enable_island", True):
                self._island.set_island_style(s.get("island_style", "originos_dark"))
                self._island.set_ambient_style(s.get("island_ambient_style", "adaptive_album"))
                self._island.set_island_position(s.get("island_position", "top_notch"))
                if hasattr(s, "weather_location") and s.weather_location:
                    self._island.set_weather_location(s.weather_location)
                self._island.show()
            else:
                self._island.hide()

        startup.sync_startup(s.start_with_windows)

    # ── Cleanup ───────────────────────────────────────────────────────────────

    def closeEvent(self, event):
        PetManager.instance().unregister_pet(self)
        self._timer.stop()
        self._bubble.close()
        self._media_card.close()
        if self._island:
            self._island.close()
        event.accept()

        if len(PetManager.instance().pets) == 0:
            QApplication.quit()


# Alias for clean naming
PetWindow = LionWindow
