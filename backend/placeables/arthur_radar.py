import math
from typing import Dict, Any
from .base import PlaceableBase

class Template(PlaceableBase):
    """
    ARTHUR (Artillery Hunting Radar) 
    ARTHUR is a counter-battery radar system developed for detecting and tracking 
    artillery projectiles to determine the position of hostiles and own forces' fall-of-shot.
    """
    def __init__(self, obj_id: str, type_name: str, x_km: float, y_km: float, properties: Dict[str, Any]):
        super().__init__(obj_id, type_name, x_km, y_km, properties)
        
        # Specs based on arthur_radar.txt
        # Mod C: 60 km
        # Mod D: 100 km
        self.mod = self.properties.get("variant", "Mod D")
        if self.mod == "Mod C":
            self.detection_range = 60.0
        else: # Default to Mod D
            self.detection_range = 100.0
        
        # Allow property override
        self.detection_range = self.properties.get("range_km", self.detection_range)
        
        self.is_active = self.properties.get("is_active", True)
        self.data["status"] = "operational" if self.is_active else "offline"
        self.data["mod"] = self.mod
        self.data["range_km"] = self.detection_range
        self.data["detected_hostile_firings"] = []
        self.data["counter_battery_solutions"] = []

    def step(self, tick: int, world_state: Dict[str, Any]):
        """
        Arthur Radar logic: 
        1. Detect incoming projectiles (hostile tracks).
        2. Calculate firing position (counter-battery).
        3. Identify own fall-of-shot (friendly tracks/assets).
        """
        if not self.is_active:
            self.data["status"] = "offline"
            return

        self.data["status"] = "active"
        
        # In this simulation, 'tracks' are hostile and 'assets' are friendly
        # Arthur detects tracks (artillery/rocket projectiles)
        tracks = world_state.get("tracks", [])
        detected_firings = []
        solutions = []
        
        for track in tracks:
            # Simple assumption: ARTHUR detects hostile tracks that might be projectiles
            # Real Arthur specialized in trajectory calculation.
            tx = getattr(track, 'x_km', 0)
            ty = getattr(track, 'y_km', 0)
            dx = tx - self.x_km
            dy = ty - self.y_km
            dist = math.sqrt(dx*dx + dy*dy)
            
            if dist <= self.detection_range:
                # Arthur logic: It doesn't just see a dot, it identifies the firing source
                # Here we model this by identifying the track and proposing a source position
                # For simulation purposes, we assume source is at some point along the reverse trajectory
                # but for simplicity now we just log the detection.
                tid = getattr(track, 'track_id', 'unknown')
                conf = getattr(track, 'confidence', 0)
                detected_firings.append({
                    "track_id": tid,
                    "dist_km": round(dist, 1),
                    "bearing_deg": round(math.degrees(math.atan2(dx, dy)) % 360, 1)
                })
                
                # Propose a counter-battery solution if it's high confidence
                if conf > 0.8:
                    solutions.append({
                        "target_track_id": tid,
                        "origin_estimate_x": round(tx + (dx/dist) * 10, 1), # Simplified back-calculation
                        "origin_estimate_y": round(ty + (dy/dist) * 10, 1)
                    })
        
        self.data["detected_hostile_firings"] = detected_firings
        self.data["counter_battery_solutions"] = solutions
        self.data["detected_count"] = len(detected_firings)
