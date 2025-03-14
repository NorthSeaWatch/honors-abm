from mesa import Agent, Model
from mesa.time import RandomActivation
from mesa.space import MultiGrid
#leave this import for now for future data collection and visualization
from mesa.datacollection import DataCollector
from mesa.visualization.modules import CanvasGrid
from mesa.visualization.ModularVisualization import ModularServer
import csv
from shapely.geometry import Polygon, Point

#To run this mesa model it is suggested to pip install mesa version 0.9.0

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
    

    def port_size(self, capacity):
        """
        Transformation of port capacity from categorical into int.
        M-medium, L-large
        """
        if capacity == 'M':
            self.port_capacity = 5
        elif capacity == 'L':
            self.port_capacity = 10
        return self.port_capacity
    
    def dock_ship(self, ship):
        """
        Attempt to dock a ship at this port.
        Returns True if docking was successful, False otherwise.
        """
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


class Ship(Agent):
    """"
    A ship agent in the North Sea simulation - dynamic.
    """
    def __init__(self, unique_id, model):
        super().__init__(unique_id, model)
        #ship is not docked in the first step
        self.docked = False
        #steps that ship was docked
        self.docking_steps = 0
    

    def step(self):
        """
        Ship movement method. 
        """
        if not self.docked:
            # movement is random in any direction in neighborhood cells
            possible_steps = self.model.grid.get_neighborhood(
                self.pos, moore=True, include_center=True
            )
            
            #checking for possible cells to step into (only water is allowed)
            valid_steps = []
            for pos in possible_steps:
                cell_contents = self.model.grid.get_cell_list_contents(pos)
                if any(isinstance(agent, Terrain) and agent.terrain_type == 'water' for agent in cell_contents):
                    valid_steps.append(pos)
            
            # choosing a random water cells if there is one in the valid_steps
            if valid_steps:
                new_position = self.random.choice(valid_steps)
                self.model.grid.move_agent(self, new_position)
            
            # checking if the ship is next to the port (moore=True allows ships to check 8 cells around them, 
            # when False is used it only checks the 4 cells around it)
            neighbors = self.model.grid.get_neighbors(self.pos, moore=True, include_center=False)
            for neighbor in neighbors:
                if isinstance(neighbor, Port):
                    # docking to the port if it is next to it
                    if neighbor.dock_ship(self):
                        self.docked = True
                        #changing docking counter to 0
                        self.docking_steps = 0
                        print(f'Ship {self.unique_id} docked at {neighbor.name}')
                        break
        else:
            # if the ship is docked we start the counter
            self.docking_steps += 1      
            # ship is unlocked after certain amount of steps (10 in this case) 
            if self.docking_steps >= 10:
                for agent in self.model.schedule.agents:
                    if isinstance(agent, Port) and self in agent.docked_ships:
                        agent.undock_ship(self)
                        print(f'Ship {self.unique_id} undocked from {agent.name}')
                        break

class Terrain(Agent):
    """"
    A terrain agent in the North Sea simulation - static.
    """
    def __init__(self, unique_id, model, terrain_type):
        super().__init__(unique_id, model)
        self.terrain_type = terrain_type


class ShipPortModel(Model):
    """"
    Simulation class that runs the model logic.
    """
    def __init__(self, width, height, num_ships):
        # torus False means ships cannot travel to the other side of the grid
        self.grid = MultiGrid(width, height, torus=False)
        self.schedule = RandomActivation(self)
        self.running = True
        # initial numbers for docked and undocked
        self.docked_ships_count = 0
        self.undocked_ships_count = 0

        #!DO NOT TRY TO CHANGE THIS WITHOUT ANDREY'S CONSENT CAUSE HE LOST HIS ABILITY TO SEE TRYING TO SET IT UP!
        land_regions = [
            # UK and islands
            [(0, 0), (0,2), (26, 2), (26,0)], [(0,3), (0,5), (20,5), (20,3), (0,3)],
            [(0,5),(0,24),(26,24),(32,14), (26,6),(0,6)], [(0,25),(20,25),(10,25),(0,25)],
            [(0,26),(20,26),(10,26),(0,26)],[(0,27),(18,27),(10,27),(0,27)],
            [(0, 28),(0,34), (18,34),(18,28),(0,28)],[(0, 34),(0,41), (10,41),(10,34),(0,34)],
            [(11, 34),(11,38), (12,38),(12,34)],[(11, 39),(11,39), (11,39),(11,39)],
            [(0, 42),(0,48), (10,41)], [(0, 52),(4,52), (4,52)], [(0, 56),(0,60), (6,60)],
            [(0, 61),(0,68), (10,68), (5, 61)], [(8, 64),(8,65), (8,65)], [(9, 66),(9,65), (9,65)], 
            [(0, 71),(0,76), (7, 76), (2, 71)], [(0, 80),(0,82), (2,82), (0, 80)], 
            [(10, 89),(13, 95),(15,95),(10, 89)], [(10, 90),(10, 90), (10,90)],
            
            #France and NL
            [(41, 0),(41,1), (46, 1),(47,0)], [(55, 0),(55, 5),(100,5), (100, 0)], 
             [(57, 5),(57, 10),(100, 10), (100, 5)], [(56, 6),(56, 6), (56, 6)], 
             [(59, 11),(59, 12),(100, 12), (100, 11)], [(51, 5),(51, 6),(54, 3)],
             [(53, 10),(53, 13),(56, 10)], [(56, 11),(58, 11),(58, 11)],
             [(63, 13),(71, 21),(71, 13)], [(72, 13),(72, 21),(79, 21), (82,13)], 
             [(80, 19),(100, 19),(100, 12), (80,13)], [(72, 22),(79, 22),(79, 22)],
             [(55, 15),(58, 15),(59, 15)], [(55, 16),(59, 23),(61, 17), (59,16)], 
             [(59, 21),(60, 22), (60, 22)], [(66, 16),(68, 22,),(74, 22), (74,0)], 
             [(75, 23),(78, 25),(78, 23)], [(86, 20),(86, 23),(100, 23), (100, 20)],
             [(84, 23),(86, 23),(86, 23)], [(85, 24),(85, 27),(92, 23)], 
             [(87, 30),(100, 30),(100, 27), (90, 27)], [(95, 27),(100, 27),(100, 24), (95,24)], 

             #Denmark
             [(87, 31),(89, 40),(100, 40), (100, 31)],[(89, 41),(87, 50),(97, 60), (100, 60), (100, 0)],
             
             #Norway and Sweden
             [(60, 99),(100, 99),(100, 96), (60,96)], [(61, 95),(100, 95),(100, 95)],[(61, 91),(61, 95),(100, 95), (100,91)],
             [(61, 84),(61, 90),(94, 90), (94, 84)], [(64, 81),(64, 84),(89, 84), (89, 81)],
             [(70, 65),(64, 80),(94, 84), (80, 65)],[(95, 83), (95, 84), (95, 85)], [(96, 86), (95, 86), (97, 86)], 
             [(96, 90), (95, 90), (95, 90)]
            ]
        
        # using polygon to set the land regions 
        self.land_polygons = [Polygon(region) for region in land_regions]
        # adding land and water terrains 
        for x in range(width):
            for y in range(height):
                #check if the point is within the polygon
                point = Point(x, y)
                #coverts method is used to color areas inside of the polygon
                is_land = any(polygon.covers(point) for polygon in self.land_polygons)
                terrain_type = 'land' if is_land else "water"
                terrain = Terrain(f'terrain_{x}_{y}', self, terrain_type)
                self.grid.place_agent(terrain, (x, y))
                self.schedule.add(terrain)
        
        # calculation for min/max lan and lon to scale ports to the map 
        min_lat = min(port["lat"] for port in Port.raw_port_data)
        max_lat = max(port["lat"] for port in Port.raw_port_data)
        min_lon = min(port["lon"] for port in Port.raw_port_data)
        max_lon = max(port["lon"] for port in Port.raw_port_data)
        #storing for conversion
        self.min_lat = min_lat
        self.max_lat = max_lat
        self.min_lon = min_lon
        self.max_lon = max_lon
        
        # ports at scaled geo locations
        for i, port_data in enumerate(Port.raw_port_data):
            port = Port(i, self, port_data)
            # convert lat and lon onto grid
            x, y = self.lat_lon_to_grid(port_data["lat"], port_data["lon"])
            # bound arrangement 
            x = max(0, min(width - 1, x))
            y = max(0, min(height - 1, y))
            self.grid.place_agent(port, (x, y))
            self.schedule.add(port) 
        num_ports = len(Port.raw_port_data)
        
        # randomly placing ships
        for i in range(num_ports, num_ships):
            ship = Ship(i, self)
            # checking for water cells to place ships
            water_cells = []
            for x in range(width):
                for y in range(height):
                    cell_contents = self.grid.get_cell_list_contents((x, y))
                    if any(isinstance(agent, Terrain) and agent.terrain_type == 'water' for agent in cell_contents):
                        water_cells.append((x, y))
            if water_cells:
                x, y = self.random.choice(water_cells)
                self.grid.place_agent(ship, (x, y))
                self.schedule.add(ship)
    
    def step(self):
        """
        Step method
        """
        self.schedule.step()
    
    def lat_lon_to_grid(self, lat, lon):
        """
        Convert lat/lon to grid coordinates
        """
        x = int(((lon - self.min_lon) / (self.max_lon - self.min_lon)) * (self.grid.width - 1))
        y = int(((lat - self.min_lat) / (self.max_lat - self.min_lat)) * (self.grid.height - 1))
        return (x, y)

def agent_portrayal(agent):
    if isinstance(agent, Port):
        if agent.port_capacity == 5:
            grid_port_size = 2
        else:
            grid_port_size = 3
        return {
            "Shape": "rect", 
            "Color": "black", 
            "Filled": "true", 
            "Layer":1,
            "w": grid_port_size, 
            "h": grid_port_size,
            "port_name": agent.name,
            "text_color": "white",
            "max_capacity": agent.port_capacity,
            "current_capacity": agent.current_capacity 
        }
    elif isinstance(agent, Ship):
        color = "blue" if agent.docked else "red"
        return {
            "Shape": "circle", 
            "Color": color, 
            "Filled": "true", 
            "Layer": 1,
            "r": 1
        }
    elif isinstance(agent, Terrain):
        if agent.terrain_type == 'water':
            return {
                "Shape": "rect", 
                "Color": "lightblue", 
                "Filled": "true", 
                "Layer": 0, 
                "w": 1, 
                "h": 1
            }
        else:
            return {
                "Shape": "rect", 
                "Color": "silver", 
                "Filled": "true", 
                "Layer": 0, 
                "w": 1, 
                "h": 1
            }

# grid set up
grid = CanvasGrid(agent_portrayal, 100, 100, 500, 500)

server = ModularServer(
    ShipPortModel, 
    [grid], 
    'North Sea Watch',
    {'width': 100, 'height': 100, 'num_ships': 120}
)

server.launch()