class Port:
    """
    A port agent in the North Sea simulation.
    Attributes:
        port_id (int): Unique identifier for the port.
        port_name (str): Name of the port (e.g "Rotterdam").
        max_capacity (int): Maximum quantity of ships that a port can have.
        current_capacity (int): Current number of ships present at the port.
        pos_x (float): X-coordinate position of the port (0-1 range).
        pos_y (float): Y-coordinate position of the port (0-1 range).
    """
    def __init__(self, port_id, port_name, max_capacity, current_capacity, pos_x=0, pos_y=0):
        self._port_id = port_id
        self._port_name = port_name
        self._max_capacity = max_capacity
        self.current_capacity = current_capacity
        self.pos_x = pos_x
        self.pos_y = pos_y
        self.docked_ships = []
        
    @property
    def port_id(self):
        return self._port_id
        
    @property
    def port_name(self):
        return self._port_name
        
    @port_name.setter
    def port_name(self, new_port_name):
        self._port_name = new_port_name
        
    @property
    def max_capacity(self):
        return self._max_capacity
        
    @max_capacity.setter
    def max_capacity(self, new_max_capacity):
        self._max_capacity = new_max_capacity
        
    def max_capacity_filter(self):
        """
        This function converts ports categorical (str) description into numerical (int).
        For experiment purposes M(Medium size ports) are set to 30,
        L(large size ports) to 60.
        """
        if self.max_capacity == 'M':
            return 30
        elif self.max_capacity == 'L':
            return 60
        return self.max_capacity
    
    def has_capacity(self):
        """Check if the port has available capacity for new ships"""
        return self.current_capacity < self.max_capacity_filter()
    
    def dock_ship(self, ship):
        """
        Attempt to dock a ship at this port.
        Returns True if docking was successful, False otherwise.
        """
        if self.has_capacity():
            self.current_capacity += 1
            self.docked_ships.append(ship)
            return True
        return False
    
    def undock_ship(self, ship):
        """
        Remove a ship from the port when it leaves.
        """
        if ship in self.docked_ships:
            self.docked_ships.remove(ship)
            self.current_capacity -= 1
            return True
        return False
    
    def calculate_distance(self, ship):
        """Calculate distance between port and a ship"""
        return ((self.pos_x - ship.pos_x)**2 + (self.pos_y - ship.pos_y)**2)**0.5
    
    def update_capacity(self):
        """Update current capacity based on number of docked ships"""
        self.current_capacity = len(self.docked_ships)
    
    def __repr__(self):
        return f'Port (id: {self.port_id}, name: {self.port_name}, position: ({self.pos_x:.2f}, {self.pos_y:.2f}), max capacity: {self.max_capacity_filter()}, current_capacity: {self.current_capacity})'
    