import random
import math

class Ship:
    def __init__(self, imo_id, pos_x, pos_y, angle, speed=0.5, ship_type="tanker", scrubber_usage=False, destination_port=None):
        self.imo_id = imo_id
        self.pos_x = pos_x
        self.pos_y = pos_y
        self.angle = angle
        self.speed = speed
        self.ship_type = ship_type
        self.scrubber_usage = scrubber_usage
        self.color = 'green' if scrubber_usage else 'orange'
        self.destination_port = destination_port
        self.at_port = False
        self.current_port = None
        
    def step(self):
        """Move the ship one step"""
        # Only move if not at port
        if not self.at_port:
            
            # Calculate new position
            self.pos_x += math.cos(self.angle) * self.speed
            self.pos_y += math.sin(self.angle) * self.speed
            
            # if the ship leaves the grid it comes back on the other side
            self.pos_x = self.pos_x % 1.0
            self.pos_y = self.pos_y % 1.0
    
    def dock(self, port):
        """Dock at a port"""
        self.at_port = True
        self.current_port = port
        
    def undock(self):
        """Leave the current port"""
        if self.current_port:
            self.current_port.undock_ship(self)
            self.current_port = None
        self.at_port = False
    
    def __repr__(self):
        status = "docked at " + self.current_port.port_name if self.current_port else \
                ("en route to " + self.destination_port.port_name if self.destination_port else "sailing")
        return f"Ship(id: {self.imo_id}, status: {status}, scrubber: {self.scrubber_usage})"