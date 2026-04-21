from typing import Dict, Any
from .base import PlaceableBase

class Radar(PlaceableBase):
    def __init__(self, obj_id: str, type_name: str, x_km: float, y_km: float, properties: Dict[str, Any]):
        super().__init__(obj_id, type_name, x_km, y_km, properties)
        self.data["range_km"] = properties.get("range_km", 150)

    def step(self, tick: int, world_state: Dict[str, Any]):
        pass
