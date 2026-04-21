from typing import Dict, Any
from .base import PlaceableBase

class SAM(PlaceableBase):
    def __init__(self, obj_id: str, type_name: str, x_km: float, y_km: float, properties: Dict[str, Any]):
        super().__init__(obj_id, type_name, x_km, y_km, properties)
        self.data["missile_count"] = properties.get("missile_count", 8)

    def step(self, tick: int, world_state: Dict[str, Any]):
        pass
