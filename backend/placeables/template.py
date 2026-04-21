import math
from typing import Dict, Any
from .base import PlaceableBase

class Template(PlaceableBase):
    """
    Template implementation of a placeable object (e.g., a Radar).
    The Simulation Controller will look for a class named 'Template' in the script.
    """
    def __init__(self, obj_id: str, type_name: str, x_km: float, y_km: float, properties: Dict[str, Any]):
        super().__init__(obj_id, type_name, x_km, y_km, properties)
        # Initialize custom properties
        self.detection_range = self.properties.get("detection_range_km", 50.0)
        self.is_active = self.properties.get("is_active", True)
        self.data["status"] = "operational" if self.is_active else "offline"
        self.data["detected_tracks"] = []

    def step(self, tick: int, world_state: Dict[str, Any]):
        """
        Example radar logic: detect objects within range.
        """
        if not self.is_active:
            self.data["status"] = "offline"
            self.data["detected_tracks"] = []
            return

        self.data["status"] = "active"
        detected = []
        
        # Access world state to find other objects
        # In a real scenario, world_state might contain 'tracks', 'assets', etc.
        # For now, let's assume world_state['placeables'] exists.
        others = world_state.get("placeables", {})
        
        for other_id, other_obj in others.items():
            if other_id == self.id:
                continue
            
            # Simple distance calculation
            dx = other_obj.get("x_km", 0) - self.x_km
            dy = other_obj.get("y_km", 0) - self.y_km
            dist = math.sqrt(dx*dx + dy*dy)
            
            if dist <= self.detection_range:
                detected.append({
                    "id": other_id,
                    "type": other_obj.get("type"),
                    "distance_km": round(dist, 2)
                })
        
        self.data["detected_tracks"] = detected
        
        # Example of cross-object influence:
        # If this was a jamming battery, it could modify others' data.
        # (Be careful with race conditions and update order in simulation_controller)
