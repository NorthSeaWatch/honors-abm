import math
import random
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
    def __init__(self, imo_id, pos_x, pos_y, angle, speed, ship_type="cargo", scrubber_usage=False, route=None):
        self.imo_id = imo_id
        self.ship_type = ship_type
        self.scrubber_usage = scrubber_usage
        self.route = route if route else []
        
        # movement attributes
        self.pos_x, self.pos_y = pos_x, pos_y
        self.angle = angle
        self.speed = speed
        
        self.color = "red" if scrubber_usage else "blue"  # Red for scrubber ships, blue for non-scrubber
        
        
    def distance(self, other):
        # compute the distance between two ships
        # we'll need a smart way to make sure ships don't collide
        x_dist = (self.pos_x - other.pos_x) ** 2
        y_dist = (self.pos_y - other.pos_y) ** 2

        return math.sqrt(x_dist + y_dist)
            
    def step(self):
        """
        Move the ship to next port or along its route.
        CURRENTLY RANDOM
        """
        if random.random() < 0.2:
            self.angle += random.uniform(-math.pi / 2, math.pi / 2)
            
        # calculate movement in x and y
        dx = math.cos(self.angle) * self.speed
        dy = math.sin(self.angle) * self.speed

        # update movement
        self.pos_x += dx
        self.pos_y += dy

        # edge case: turn around if at edge of the world
        if self.pos_x < 0 or self.pos_y < 0 or self.pos_x > 1 or self.pos_y > 1:
            self.angle += math.pi
        
        self.discharge_scrubber_water()
            
        # if self.route:
        #     self.position = self.route.pop(0)
        # else:
        #     print(f"Ship {self.imo_id} has completed its route.")
            
    def discharge_scrubber_water(self):
        """
        Simulate the scrubber water discharge for ships that use scrubbers.
        Returns the amount of water discharged, 0 for ships without scrubbers.
        """
        return 10 if self.scrubber_usage else 0
        
    def __repr__(self):
        return f"Ship(id={self.imo_id}, type={self.ship_type}, position={(self.pos_x, self.pos_y)}, scrubber_usage={self.scrubber_usage})"