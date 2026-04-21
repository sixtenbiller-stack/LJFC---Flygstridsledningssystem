from typing import Any, Dict

class PlaceableBase:
    """
    Base class for all placeable objects in the simulation.
    Every .py script in backend/placeables should define a class named 'Template' 
    inheriting from this base class or following its interface.
    """
    def __init__(self, obj_id: str, type_name: str, x_km: float, y_km: float, properties: Dict[str, Any]):
        self.id = obj_id
        self.type = type_name
        self.x_km = x_km
        self.y_km = y_km
        self.properties = properties
        self.data: Dict[str, Any] = {} # Dynamic state data

    def step(self, tick: int, world_state: Dict[str, Any]):
        """
        Executed every tick of the simulation.
        :param tick: Current simulation tick count.
        :param world_state: A dictionary containing the current state of all other objects.
        """
        pass

    def to_dict(self) -> Dict[str, Any]:
        """Returns a serializable dictionary of the object's current state."""
        return {
            "id": self.id,
            "type": self.type,
            "x_km": self.x_km,
            "y_km": self.y_km,
            "properties": self.properties,
            "data": self.data
        }
