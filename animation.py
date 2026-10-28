from pathlib import Path
from typing import Dict, Optional, List
import time

from PySide6.QtGui import QPixmap, QImage
from PySide6.QtCore import Qt

SPRITE_DIR = Path(__file__).parent / "assets" / "sprites"
FRAME_SIZE = 192

PET_TYPES = {
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


class Animation:

    def __init__(self, name: str, fps: float = 12.0, pet_type: str = "alien"):
        self.name = name
        self.fps = fps
        self.pet_type = pet_type
        self.frames: List[QPixmap] = []
        self.images: List[QImage] = []
        self._scaled_frames: Dict[int, List[QPixmap]] = {}
        self._scaled_images: Dict[int, List[QImage]] = {}
        self.current_frame = 0
        self._last_tick = time.monotonic()
        self._load()

    def _load(self):
        # 1. Search in pet subfolder first (e.g. assets/sprites/anime_girl/idle.png)
        path = SPRITE_DIR / self.pet_type / f"{self.name}.png"
        if not path.exists():
            # 2. Fallback to base sprite dir (e.g. assets/sprites/idle.png)
            path = SPRITE_DIR / f"{self.name}.png"
            
        if not path.exists():
            ph = self._placeholder(FRAME_SIZE)
            self.frames = [ph]
            self.images = [ph.toImage()]
            return
            
        sheet = QImage(str(path))
        if sheet.isNull():
            ph = self._placeholder(FRAME_SIZE)
            self.frames = [ph]
            self.images = [ph.toImage()]
            return
            
        frame_h = sheet.height()
        n_frames = max(1, sheet.width() // frame_h)
        for i in range(n_frames):
            crop = sheet.copy(i * frame_h, 0, frame_h, frame_h)
            self.images.append(crop)
            self.frames.append(QPixmap.fromImage(crop))

    def _placeholder(self, size: int = FRAME_SIZE) -> QPixmap:
        pm = QPixmap(size, size)
        pm.fill(Qt.GlobalColor.transparent)
        return pm

    def _ensure_scaled(self, size: int):
        if size in self._scaled_frames:
            return
        scaled_list = []
        scaled_img_list = []
        for img in self.images:
            if img.width() == size and img.height() == size:
                scaled_img = img
            else:
                scaled_img = img.scaled(
                    size, size,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                )
            scaled_img_list.append(scaled_img)
            scaled_list.append(QPixmap.fromImage(scaled_img))
        self._scaled_frames[size] = scaled_list
        self._scaled_images[size] = scaled_img_list

    def get_scaled_frame(self, size: int) -> QPixmap:
        if not self.frames:
            return self._placeholder(size)
        self._ensure_scaled(size)
        return self._scaled_frames[size][self.current_frame]

    def get_scaled_image(self, size: int) -> QImage:
        if not self.images:
            return self._placeholder(size).toImage()
        self._ensure_scaled(size)
        return self._scaled_images[size][self.current_frame]

    # State-specific speed multipliers to give natural, realistic pacing
    # (e.g. Sleep & rest are peaceful and slow, while walk & run are active)
    STATE_FPS_MULTIPLIERS = {
        "sleep": 0.25,      # ~3.0 fps: peaceful, slow rhythmic breathing
        "wake": 0.35,       # ~4.2 fps: waking up gently
        "sit": 0.35,        # ~4.2 fps: calm resting
        "idle": 0.45,       # ~5.4 fps: gentle idle breathing
        "idle_flip": 0.45,
        "idle_left": 0.45,
        "idle_right": 0.45,
        "work": 0.6,        # ~7.2 fps: typing focus
        "idea": 0.6,
        "music": 0.5,       # ~6.0 fps: head bobbing
        "drag": 0.5,        # ~6.0 fps: gentle dangling
        "happy": 0.6,
        "walk_right": 1.0,  # 12.0 fps: active walking
        "walk_left": 1.0,
        "run_right": 1.3,   # ~15.6 fps: sprinting
        "run_left": 1.3,
        "roar": 0.8,
    }

    def _effective_fps(self) -> float:
        mult = self.STATE_FPS_MULTIPLIERS.get(self.name, 1.0)
        return max(1.0, self.fps * mult)

    def tick(self, target_size: Optional[int] = None) -> tuple[QPixmap, bool]:
        now = time.monotonic()
        elapsed = now - self._last_tick
        eff_fps = self._effective_fps()
        frame_duration = 1.0 / eff_fps
        frame_changed = False
        if elapsed >= frame_duration:
            steps = int(elapsed / frame_duration)
            old_frame = self.current_frame
            self.current_frame = (self.current_frame + steps) % len(self.frames)
            self._last_tick = now
            if self.current_frame != old_frame:
                frame_changed = True
        if target_size is not None:
            return self.get_scaled_frame(target_size), frame_changed
        return self.frames[self.current_frame], frame_changed

    def reset(self):
        self.current_frame = 0
        self._last_tick = time.monotonic()

    @property
    def finished(self) -> bool:
        return self.current_frame == len(self.frames) - 1

    def set_fps(self, fps: float):
        self.fps = max(1.0, fps)


class AnimationController:
    
    ONE_SHOT = {
        "wake", "blink", "happy", "roar", "jump",
        "idea", "work", "cry", "sad", "shrug", "land"
    }

    def __init__(self, fps: float = 12.0, pet_type: str = "alien"):
        self._fps = fps
        self._pet_type = pet_type if pet_type in PET_TYPES else "alien"
        self._cache: Dict[str, Animation] = {}
        self._state = "idle"
        self._queued: Optional[str] = None   # next state after one-shot finishes
        self._load_all()

    def _load_all(self):
        names = [
            "idle", "idle_flip",
            "walk_right", "walk_left",
            "sit", "sleep", "wake",
            "blink", "happy", "idea", "work",
            "cry", "sad", "shrug",
            "jump", "roar",
            "drag", "fall", "land", "music",
        ]
        self._cache.clear()
        for n in names:
            self._cache[n] = Animation(n, self._fps, pet_type=self._pet_type)

    def set_pet(self, pet_type: str):
        if pet_type not in PET_TYPES:
            return
        if self._pet_type == pet_type:
            return
        self._pet_type = pet_type
        current_state = self._state
        self._load_all()
        self.set_state(current_state)

    @property
    def pet_type(self) -> str:
        return self._pet_type

    def set_state(self, state: str, queue_after: str = "idle"):
        if state not in self._cache:
            return
        if self._state == state:
            return
        self._state = state
        self._cache[state].reset()
        self._queued = queue_after if state in self.ONE_SHOT else None

    def tick(self, target_size: Optional[int] = None) -> tuple[QPixmap, bool]:
        anim = self._cache.get(self._state)
        if not anim:
            return QPixmap(), False
        pixmap, frame_changed = anim.tick(target_size)
        if self._queued and anim.finished:
            self.set_state(self._queued)
            self._queued = None
            frame_changed = True
        return pixmap, frame_changed

    def current_frame(self, target_size: Optional[int] = None) -> QPixmap:
        anim = self._cache.get(self._state)
        if not anim:
            return QPixmap()
        if target_size is not None:
            return anim.get_scaled_frame(target_size)
        if not anim.frames:
            return QPixmap()
        return anim.frames[anim.current_frame]

    def current_frame_image(self, size: int) -> Optional[QImage]:
        anim = self._cache.get(self._state)
        if not anim:
            return None
        return anim.get_scaled_image(size)

    @property
    def state(self) -> str:
        return self._state

    def set_fps(self, fps: float):
        self._fps = fps
        for a in self._cache.values():
            a.set_fps(fps)
