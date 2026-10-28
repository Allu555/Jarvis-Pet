import math
import random
import time
from enum import Enum, auto
from typing import Optional
from dataclasses import dataclass, field

from PySide6.QtWidgets import QApplication


class PetState(Enum):
    IDLE       = auto()
    WALK_LEFT  = auto()
    WALK_RIGHT = auto()
    SIT        = auto()
    SLEEP      = auto()
    WAKING     = auto()
    BLINKING   = auto()
    HAPPY      = auto()
    IDEA       = auto()
    WORK       = auto()
    CRY        = auto()
    SAD        = auto()
    SHRUG      = auto()
    ROARING    = auto()
    JUMPING    = auto()
    DRAG       = auto()
    FALL       = auto()
    LAND       = auto()
    MUSIC      = auto()


# Backward compatibility alias
LionState = PetState


# How long (seconds) the pet stays in each state before reconsidering
STATE_DURATION = {
    PetState.IDLE:       (1.5,  4.5),
    PetState.WALK_LEFT:  (2.0,  5.0),
    PetState.WALK_RIGHT: (2.0,  5.0),
    PetState.SIT:        (3.0,  6.0),
    PetState.SLEEP:      (8.0, 20.0),
    PetState.WAKING:     (1.5,  1.5),
    PetState.BLINKING:   (0.5,  0.5),
    PetState.HAPPY:      (2.5,  3.5),
    PetState.IDEA:       (2.5,  3.5),
    PetState.WORK:       (3.0,  4.5),
    PetState.CRY:        (2.5,  3.5),
    PetState.SAD:        (2.5,  3.5),
    PetState.SHRUG:      (2.0,  3.0),
    PetState.ROARING:    (2.5,  4.0),
    PetState.JUMPING:    (1.5,  2.5),
    PetState.DRAG:       (9999.0, 9999.0),
    PetState.FALL:       (9999.0, 9999.0),
    PetState.LAND:       (0.4,  0.4),
    PetState.MUSIC:      (3.5,  6.0),
}

# Probability weights for autonomous transitions from IDLE
IDLE_TRANSITIONS = {
    PetState.WALK_LEFT:  20,
    PetState.WALK_RIGHT: 20,
    PetState.SIT:        12,
    PetState.BLINKING:   10,
    PetState.IDEA:       10,
    PetState.WORK:       10,
    PetState.SHRUG:       8,
    PetState.HAPPY:       5,
    PetState.JUMPING:     5,
    PetState.IDLE:        5,
}

PIXELS_PER_SECOND = 110  # walking speed (pixels / sec)
PET_SIZE = 80
INACTIVITY_SLEEP = 25.0  # seconds of no user interaction before pet naps
GRAVITY = 1500.0         # gravity acceleration for realistic cute fall


@dataclass
class MovementController:
    walk_speed: float = PIXELS_PER_SECOND
    inactivity_sleep: float = INACTIVITY_SLEEP
    follow_cursor: bool = True

    _state: PetState = field(default=PetState.IDLE, init=False)
    _x: float = field(default=0.0, init=False)
    _y: float = field(default=0.0, init=False)
    _vy: float = field(default=0.0, init=False)
    _state_until: float = field(default=0.0, init=False)
    _last_user_action: float = field(default_factory=time.monotonic, init=False)
    _screen_width: int = field(default=1920, init=False)
    _screen_height: int = field(default=1080, init=False)
    _last_cursor_pos: tuple[int, int] = field(default=(0, 0), init=False)
    _is_dragging: bool = field(default=False, init=False)

    def __post_init__(self):
        self._screen_width, self._screen_height = self._get_screen_dimensions()
        self._x = float(random.randint(100, max(100, self._screen_width - 200)))
        self._y = float(self._screen_height - PET_SIZE - 40)
        self._schedule_next(PetState.IDLE)

    # ── public API ────────────────────────────────────────────────────────────

    @property
    def x(self) -> int:
        return int(self._x)

    @property
    def y(self) -> int:
        return int(self._y)

    @property
    def state(self) -> PetState:
        return self._state

    def set_position(self, x: float, y: float, pet_size: int = PET_SIZE):
        self._x = max(0.0, min(float(x), float(self._screen_width - pet_size)))
        self._y = max(0.0, min(float(y), float(self._screen_height - pet_size)))

    def start_drag(self, x: float, y: float):
        self._is_dragging = True
        self._x = x
        self._y = y
        self._vy = 0.0
        self._last_user_action = time.monotonic()
        self._transition(PetState.DRAG)

    def drag_to(self, x: float, y: float, pet_size: int = PET_SIZE):
        self._x = max(0.0, min(x, float(self._screen_width - pet_size)))
        self._y = max(0.0, min(y, float(self._screen_height - pet_size)))
        self._last_user_action = time.monotonic()

    def end_drag(self, pet_size: int = PET_SIZE):
        self._is_dragging = False
        self._last_user_action = time.monotonic()
        floor_y = float(self._screen_height - pet_size - 40)
        # If released high up above floor, initiate physics fall!
        if self._y < floor_y - 20:
            self._vy = 120.0  # Initial downward velocity
            self._transition(PetState.FALL)
        else:
            self._transition(PetState.LAND)
            self._state_until = time.monotonic() + 0.35

    def trigger_happy(self):
        self._last_user_action = time.monotonic()
        self._transition(PetState.HAPPY)

    def trigger_idea(self):
        self._last_user_action = time.monotonic()
        self._transition(PetState.IDEA)

    def trigger_work(self):
        self._last_user_action = time.monotonic()
        self._transition(PetState.WORK)

    def trigger_cry(self):
        self._last_user_action = time.monotonic()
        self._transition(PetState.CRY)

    def trigger_sad(self):
        self._last_user_action = time.monotonic()
        self._transition(PetState.SAD)

    def trigger_shrug(self):
        self._last_user_action = time.monotonic()
        self._transition(PetState.SHRUG)

    def trigger_jump(self):
        self._last_user_action = time.monotonic()
        self._transition(PetState.JUMPING)

    def trigger_sit(self):
        self._last_user_action = time.monotonic()
        self._transition(PetState.SIT)

    def trigger_sleep(self):
        self._last_user_action = time.monotonic()
        self._transition(PetState.SLEEP)

    def trigger_roar(self):
        self._last_user_action = time.monotonic()
        self._transition(PetState.ROARING)

    def trigger_music(self):
        self._last_user_action = time.monotonic()
        self._transition(PetState.MUSIC)

    def trigger_action(self, action_name: str):
        self._last_user_action = time.monotonic()
        mapping = {
            "idle": PetState.IDLE,
            "walk_left": PetState.WALK_LEFT,
            "walk_right": PetState.WALK_RIGHT,
            "sit": PetState.SIT,
            "sleep": PetState.SLEEP,
            "wake": PetState.WAKING,
            "blink": PetState.BLINKING,
            "happy": PetState.HAPPY,
            "idea": PetState.IDEA,
            "work": PetState.WORK,
            "cry": PetState.CRY,
            "sad": PetState.SAD,
            "shrug": PetState.SHRUG,
            "jump": PetState.JUMPING,
            "roar": PetState.ROARING,
            "drag": PetState.DRAG,
            "fall": PetState.FALL,
            "land": PetState.LAND,
            "music": PetState.MUSIC,
        }
        if action_name in mapping:
            self._transition(mapping[action_name])

    def pause(self):
        self._transition(PetState.IDLE)
        self._state_until = time.monotonic() + 9999.0

    def resume(self):
        self._state_until = time.monotonic()

    def update(self, delta: float, cursor_x: Optional[int] = None, cursor_y: Optional[int] = None, pet_size: int = PET_SIZE):
        now = time.monotonic()
        self._screen_width, self._screen_height = self._get_screen_dimensions()
        floor_y = float(self._screen_height - pet_size - 40)

        # 1. DRAGGING STATE
        if self._is_dragging or self._state == PetState.DRAG:
            return

        # 2. FALLING STATE (Simulated gravity physics)
        if self._state == PetState.FALL:
            self._vy += GRAVITY * delta
            self._y += self._vy * delta

            # Reached floor / bottom
            if self._y >= floor_y:
                self._y = floor_y
                self._vy = 0.0
                self._transition(PetState.LAND)
                self._state_until = now + 0.35
            return

        # 3. LANDING STATE
        if self._state == PetState.LAND:
            if now >= self._state_until:
                self._transition(PetState.IDLE)
            return

        # 3b. EXPLICIT ACTION EMOTES / SKILLS
        ACTION_STATES = (
            PetState.ROARING, PetState.JUMPING, PetState.WORK, PetState.HAPPY,
            PetState.IDEA, PetState.SHRUG, PetState.CRY, PetState.SAD,
            PetState.SIT, PetState.MUSIC, PetState.SLEEP, PetState.WAKING, PetState.BLINKING
        )
        if self._state in ACTION_STATES:
            if now < self._state_until:
                return
            else:
                self._advance_state()
                return

        # 4. CURSOR FOLLOWING MODE
        if self.follow_cursor and cursor_x is not None and cursor_y is not None:
            target_x = float(cursor_x - pet_size // 2)
            target_y = float(cursor_y - pet_size // 2)

            dx = target_x - self._x
            dy = target_y - self._y
            dist = math.hypot(dx, dy)

            # Detect mouse movement
            if math.hypot(cursor_x - self._last_cursor_pos[0], cursor_y - self._last_cursor_pos[1]) > 5:
                self._last_user_action = now
                self._last_cursor_pos = (cursor_x, cursor_y)
                if self._state == PetState.SLEEP:
                    self._transition(PetState.WAKING)

            arrival_threshold = max(20.0, pet_size * 0.35)

            if dist > arrival_threshold and self._state != PetState.SLEEP:
                speed = self.walk_speed * 1.3
                step = min(dist, speed * delta)
                self._x += (dx / dist) * step
                self._y += (dy / dist) * step

                if dx < -4 and self._state != PetState.WALK_LEFT:
                    self._transition(PetState.WALK_LEFT)
                elif dx > 4 and self._state != PetState.WALK_RIGHT:
                    self._transition(PetState.WALK_RIGHT)
            else:
                if self._state in (PetState.WALK_LEFT, PetState.WALK_RIGHT):
                    self._transition(PetState.IDLE)

        else:
            # Autonomous roam mode
            if self._state == PetState.WALK_LEFT:
                self._x -= self.walk_speed * delta
            elif self._state == PetState.WALK_RIGHT:
                self._x += self.walk_speed * delta

            if self._x <= 0 and self._state == PetState.WALK_LEFT:
                self._transition(PetState.WALK_RIGHT)
            elif self._x >= self._screen_width - pet_size and self._state == PetState.WALK_RIGHT:
                self._transition(PetState.WALK_LEFT)

        # Check inactivity -> sleep
        if (self._state not in (PetState.SLEEP, PetState.WAKING) and
                now - self._last_user_action > self.inactivity_sleep):
            if self._state != PetState.SLEEP:
                self._transition(PetState.SLEEP)

        # Autonomous state transitions
        if now >= self._state_until:
            self._advance_state()

        # Boundaries clamp
        self._x = max(0.0, min(self._x, float(self._screen_width - pet_size)))
        self._y = max(0.0, min(self._y, float(self._screen_height - pet_size)))

    # ── state machine ─────────────────────────────────────────────────────────

    def _advance_state(self):
        s = self._state
        if s in (PetState.DRAG, PetState.FALL):
            return
        if s == PetState.SLEEP:
            self._transition(PetState.WAKING)
            self._last_user_action = time.monotonic()
        elif s in (PetState.WAKING, PetState.LAND):
            self._transition(PetState.IDLE)
        elif s in (PetState.HAPPY, PetState.ROARING, PetState.JUMPING,
                   PetState.BLINKING, PetState.IDEA, PetState.WORK,
                   PetState.CRY, PetState.SHRUG):
            self._transition(PetState.IDLE)
        elif s in (PetState.SIT, PetState.SAD):
            self._transition(PetState.IDLE)
        else:
            if self.follow_cursor:
                playful_choices = [
                    PetState.IDLE, PetState.IDEA, PetState.WORK,
                    PetState.BLINKING, PetState.SHRUG, PetState.HAPPY
                ]
                next_s = random.choice(playful_choices)
            else:
                choices = list(IDLE_TRANSITIONS.keys())
                weights = list(IDLE_TRANSITIONS.values())
                if s in (PetState.WALK_LEFT, PetState.WALK_RIGHT):
                    next_s = random.choices(
                        [PetState.IDLE, PetState.SIT, PetState.IDEA,
                         PetState.WORK, PetState.WALK_LEFT, PetState.WALK_RIGHT],
                        weights=[25, 15, 10, 10, 20, 20]
                    )[0]
                else:
                    next_s = random.choices(choices, weights=weights)[0]
            self._transition(next_s)

    def _transition(self, new_state: PetState):
        self._state = new_state
        self._schedule_next(new_state)

    def _schedule_next(self, state: PetState):
        lo, hi = STATE_DURATION.get(state, (2.0, 4.0))
        self._state_until = time.monotonic() + random.uniform(lo, hi)

    # ── helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def _get_screen_dimensions() -> tuple[int, int]:
        app = QApplication.instance()
        if app:
            screen = app.primaryScreen()
            if screen:
                geom = screen.geometry()
                return geom.width(), geom.height()
        return 1920, 1080


# Map PetState → animation name string
STATE_TO_ANIM = {
    PetState.IDLE:       "idle",
    PetState.WALK_LEFT:  "walk_left",
    PetState.WALK_RIGHT: "walk_right",
    PetState.SIT:        "sit",
    PetState.SLEEP:      "sleep",
    PetState.WAKING:     "wake",
    PetState.BLINKING:   "blink",
    PetState.HAPPY:      "happy",
    PetState.IDEA:       "idea",
    PetState.WORK:       "work",
    PetState.CRY:        "cry",
    PetState.SAD:        "sad",
    PetState.SHRUG:      "shrug",
    PetState.ROARING:    "roar",
    PetState.JUMPING:    "jump",
    PetState.DRAG:       "drag",
    PetState.FALL:       "fall",
    PetState.LAND:       "land",
    PetState.MUSIC:      "music",
}
