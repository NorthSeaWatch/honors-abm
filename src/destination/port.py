class Port:
    """
    A port agent in the North Sea simulation.

    Attributes:
        port_id (int): Unique identifier for the port.
        port_name (str): Name of the port (e.g "Rotterdam").
        max_capacity (int): Maximum quantity of ships that a port can have.
        current_capacity (int): Current number of ships present at the port.
    
    Methods:
        @property (getter): is used for data security.
        @port_name.setter (setter): potential changes that might occur with port names.

    """

    def __init__(self, port_id, port_name, max_capacity, current_capacity):
        self._port_id = port_id
        self._port_name = port_name
        self._max_capacity = max_capacity
        self.current_capacity = current_capacity
    
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
        For experiment purposes M(Medium size ports) are set to 20, 
        L(large size ports) to 60.

        """
        if self.max_capacity == 'M':
            self.max_capacity = 30
        elif self.max_capacity == 'L':
            self.max_capacity = 60
    
    # will need to modify this function to work with either Ship.move or find another logic
    # to calculate how current capacity is calculated
    def capacity_calculation(self):
        pass

    def __repr__(self):
        return f'Port (id: {self.port_id},name: {self.port_id},max capacity: {self.max_capacity}, current_capacity: {self.current_capacity})'
