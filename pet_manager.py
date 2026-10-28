import random
from typing import List, Optional, TYPE_CHECKING
from PySide6.QtCore import QObject

if TYPE_CHECKING:
    from lion import LionWindow


class PetManager(QObject):
    """Central manager for tracking and spawning multiple pets on desktop."""

    _instance: Optional["PetManager"] = None

    @classmethod
    def instance(cls) -> "PetManager":
        if cls._instance is None:
            cls._instance = PetManager()
        return cls._instance

    def __init__(self):
        super().__init__()
        self.pets: List["LionWindow"] = []

    def register_pet(self, pet: "LionWindow"):
        if pet not in self.pets:
            self.pets.append(pet)

    def unregister_pet(self, pet: "LionWindow"):
        if pet in self.pets:
            self.pets.remove(pet)

    def spawn_pet(self, pet_type: str, near_x: Optional[int] = None, near_y: Optional[int] = None) -> "LionWindow":
        """Spawns a new pet instance on desktop."""
        from lion import LionWindow
        from settings import Settings

        new_settings = Settings()
        new_settings.selected_pet = pet_type
        # Only the primary pet manages the island
        new_settings.set("enable_island", False)

        new_pet = LionWindow(new_settings, is_secondary=True)

        if near_x is not None and near_y is not None:
            ox = random.choice([-140, 140])
            new_pet.set_pos(max(50, near_x + ox), near_y)

        new_pet.show()
        return new_pet

    def spawn_random_pet(self, near_x: Optional[int] = None, near_y: Optional[int] = None) -> "LionWindow":
        from animation import PET_TYPES
        choice = random.choice(list(PET_TYPES.keys()))
        return self.spawn_pet(choice, near_x=near_x, near_y=near_y)

    def dismiss_all_except(self, keep_pet: "LionWindow"):
        """Dismisses all pets except the specified one."""
        to_close = [p for p in self.pets if p != keep_pet]
        for p in to_close:
            p.close()
