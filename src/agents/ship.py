class Ship:
    """
    A ship agent in the North Sea simulation.

    Attributes:
        ship_id (int): Unique identifier for the ship.
        ship_type (str): Type of the ship (e.g., "cargo", "passenger").
        scrubber_usage (bool): Whether the ship uses a scrubber.
        route (list): List of coordinates representing the ship's route.
        position (tuple): The current position of the ship on the grid.
        scrubber_discharge_rate (int): The rate of discharge for ships with scrubbers.
    """
    def __init__(self, imo_id, ship_type="cargo", scrubber_usage=False, route=None, position=(0,0)):
        self.imo_id = imo_id
        self.ship_type = ship_type
        self.scrubber_usage = scrubber_usage
        self.route = route if route else []
        self.position = position
        
    def move(self):
        """
        Move the ship to next port or along its route.
        """
        if self.route:
            self.position = self.route.pop(0)
        else:
            print(f"Ship {self.unique_id} has completed its route.")
            
    def discharge_scrubber_water(self):
        """
        Simulate the scrubber water discharge for ships that use scrubbers.
        Returns the amount of water discharged, 0 for ships without scrubbers.
        """
        return 10 if self.scrubber_usage else 0
        
    def __repr__(self):
        return f"Ship(id={self.imo_id}, type={self.ship_type}, position={self.position}, scrubber_usage={self.scrubber_usage})"