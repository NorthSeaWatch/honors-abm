from mesa import Agent, Model
from mesa.time import RandomActivation
from mesa.space import MultiGrid
#leave this import for now for future data collection and visualization
from mesa.datacollection import DataCollector
from mesa.visualization.modules import CanvasGrid
from mesa.visualization.ModularVisualization import ModularServer
import csv


class Port(Agent):
    """
    A port agent in the North Sea simulation -static.
    
    """
    #variable to store all port data
    raw_port_data = []
    # loading port information from filtered_port.csv
    with open('filtered_ports_with_x_y.csv', 'r') as port_data:
        open_port = csv.DictReader(port_data)
        for row in open_port:
            raw_port_data.append({
                "id": int(row["INDEX_NO"]),
                "name": row["PORT_NAME"],
                "lat": float(row["LATITUDE"]),
                "lon": float(row["LONGITUDE"]),
                "capacity": row["HARBORSIZE"],
                'X': row['X'],
                'Y': row['Y']
            })
    
    #using information from parent class Agent (unique_id and model)
    def __init__(self, unique_id, model, port_data, policy=None):
        super().__init__(unique_id, model)
        #storing port information in the port's instance of the class
        self.port_data = port_data
        self.name = port_data["name"]
        self.lat = port_data["lat"]
        self.lon = port_data["lon"]
        self.port_capacity = self.port_size(port_data["capacity"])
        self.current_capacity = 0
        self.docked_ships = []
        # Set the scrubber policy based on the provided parameter or model's default
        if policy is not None:
            self.scrubber_policy = policy
        else:
            # If there's a default policy in the model, use that
            if model.port_policy and len(model.port_policy) > 0:
                self.scrubber_policy = model.random.choice(model.port_policy)
            else:
                self.scrubber_policy = "allow"  # Default fallback
                
        self.allow_scrubber = self.scrubber_policy != "ban"

        self.revenue = 0
        
        # base fees for differnet ship types (needs empirical backing)
        self.base_fees = {
            "cargo": 100,
            "tanker": 120,
            "fishing": 50,
            "other": 40,
            "tug": 30,
            "passenger": 80,
            "hsc": 60,
            "dredging": 35,
            "search": 20
        }

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
    
    def calculate_docking_fee(self, ship):
        """
        Calculate the docking fee based on ship type and current occupancy.
        The fee is adjustede dynamically: the more full the port, the higher the fee 
        """
        base_fee = self.base_fees.get(ship.ship_type, 40)
        if self.scrubber_policy == "tax" and ship.is_scrubber:
            base_fee *= 1.5 # increase fee for scrubbers
        elif self.scrubber_policy == "subsidy" and not ship.is_scrubber:
            base_fee *= 0.8 # discount for non-scrubbers
            
        occupancy_ratio = self.current_capacity / self.port_capacity if self.port_capacity > 0 else 0
        multiplier = 1 + occupancy_ratio
        return base_fee * multiplier

    def dock_ship(self, ship):
        """
        Attempt to dock a ship at this port.
        Returns True if docking was successful, False otherwise.
        """
        if ship.is_scrubber and self.scrubber_policy == "ban":
            return False
        
        if self.current_capacity < self.port_capacity:
            fee = self.calculate_docking_fee(ship)
            self.revenue += fee
            self.current_capacity += 1
            self.docked_ships.append(ship)
            print(f"Port {self.name}: Ship {ship.unique_id} docked, fee charged: {fee:.2f}, total revenue: {self.revenue:.2f}")
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
