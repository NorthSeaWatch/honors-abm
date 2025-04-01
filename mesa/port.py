from mesa import Agent, Model
from mesa.time import RandomActivation
from mesa.space import MultiGrid
#leave this import for now for future data collection and visualization
from mesa.datacollection import DataCollector
from mesa.visualization.modules import CanvasGrid
from mesa.visualization.ModularVisualization import ModularServer
import csv
from shapely.geometry import Polygon, Point

class Port(Agent):
    """
    A port agent in the North Sea simulation -static.
    
    """
    #variable to store all port data
    raw_port_data = []
    # loading port information from filtered_port.csv
    with open('filtered_port.csv', 'r') as port_data:
        open_port = csv.DictReader(port_data)
        for row in open_port:
            raw_port_data.append({
                "id": int(row["INDEX_NO"]),
                "name": row["PORT_NAME"],
                "lat": float(row["LATITUDE"]),
                "lon": float(row["LONGITUDE"]),
                "capacity": row["HARBORSIZE"]
            })
    
    #using information from parent class Agent (unique_id and model)
    def __init__(self, unique_id, model, port_data):
        super().__init__(unique_id, model)
        #storing port information in the port's instance of the class
        self.port_data = port_data
        self.name = port_data["name"]
        self.lat = port_data["lat"]
        self.lon = port_data["lon"]
        self.port_capacity = self.port_size(port_data["capacity"])
        self.current_capacity = 0
        self.docked_ships = []
        self.allow_scrubber = (self.model.random.random() < self.model.prob_allow_scrubbers)
    

    def port_size(self, capacity):
        """
        Transformation of port capacity from categorical into int.
        M-medium, L-large
        """
        if capacity == 'M':
            base_capacity = 5
        elif capacity == 'L':
            base_capacity = 10
        else:
            base_capacity = 3
        # Scale base capacity by the ratio of total ships to number of ports
        num_ports = len(Port.raw_port_data)
        # Assume self.model.num_ships is available from model parameters
        scaling_factor = self.model.num_ships / num_ports
        scaled_capacity = int(base_capacity * scaling_factor)
        return scaled_capacity
    
    def dock_ship(self, ship):
        """
        Attempt to dock a ship at this port.
        Returns True if docking was successful, False otherwise.
        """
        if ship.is_scrubber and not self.allow_scrubber:
            return False
        if self.current_capacity < self.port_capacity:
            self.current_capacity += 1
            self.docked_ships.append(ship)
            return True
        return False
    
    def undock_ship(self, ship):
        """
        Remove a ship from the port(list) when it leaves.
        Returns True if undocking was successful, False otherwise.
        """
        if ship in self.docked_ships:
            self.docked_ships.remove(ship)
            self.current_capacity -= 1
            return True
        return False
    
    def update_capacity(self):
        """
        Update current capacity based on number of docked ships
        """
        self.current_capacity = len(self.docked_ships)
