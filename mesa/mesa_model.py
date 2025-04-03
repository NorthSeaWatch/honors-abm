from mesa import Agent, Model
import math
from mesa.time import RandomActivation
from mesa.space import MultiGrid
#leave this import for now for future data collection and visualization
from mesa.datacollection import DataCollector
from mesa.visualization.modules import CanvasGrid
from mesa.visualization.ModularVisualization import ModularServer
import csv
from shapely.geometry import Polygon, Point
# Import Port and Ship from their modules
from port import Port
from ship import Ship, Terrain, ScrubberTrail

#To run this mesa model it is suggested to pip install mesa version 0.9.0

class ShipPortModel(Model):
    """"
    Simulation class that runs the model logic.
    """
    def __init__(self, width, height, num_ships, ship_wait_time=20, prob_allow_scrubbers=0.5):
        self.num_ships = num_ships
        # torus False means ships cannot travel to the other side of the grid
        self.grid = MultiGrid(width, height, torus=False)
        self.schedule = RandomActivation(self)
        self.running = True
        # initial numbers for docked and undocked
        self.docked_ships_count = 0
        self.undocked_ships_count = 0
        
        self.next_trail_id = 10000
        
        # Extra environment settings
        self.ship_wait_time = ship_wait_time
        self.prob_allow_scrubbers = prob_allow_scrubbers
        
        # initialize scrubber penalty accumulators
        self.scrubber_penalty_sum = 0
        self.scrubber_penalty_count = 0


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
        
        # gradual ship spawning
        self.next_ship_id = num_ports
        self.remaining_ships = num_ships
        
        self.spawn_duration = 5
        
        # Initialize the datacollector.
        self.datacollector = DataCollector(
            model_reporters = {
                "NumScrubberShips": lambda m: sum(1 for a in m.schedule.agents if isinstance(a, Ship) and getattr(a, 'is_scrubber', False)),
                "NumScrubberTrails": lambda m: sum(1 for a in m.schedule.agents if type(a) is ScrubberTrail),
                "TotalScrubberWater": lambda m: sum(a.water_units for a in m.schedule.agents if type(a) is ScrubberTrail),
                "NumShips": lambda m: sum(1 for a in m.schedule.agents if isinstance(a, Ship)),
                "TotalDockedShips": lambda m: sum(len(a.docked_ships) for a in m.schedule.agents if isinstance(a, Port)),
                "AvgPortPopularity": lambda m: (sum(len(a.docked_ships) for a in m.schedule.agents if isinstance(a, Port)) 
                                                / max(1, sum(1 for a in m.schedule.agents if isinstance(a, Port)))),
                "NumPortsBan": lambda m: sum(1 for a in m.schedule.agents if isinstance(a, Port) and not a.allow_scrubber),
                "TotalPortRevenue": lambda m: sum(a.revenue for a in m.schedule.agents if isinstance(a, Port)),
                "AvgPortRevenue": lambda m: (sum(a.revenue for a in m.schedule.agents if isinstance(a, Port)) 
                                             / max(1, sum(1 for a in m.schedule.agents if isinstance(a, Port))))
            }
        )
        
    def get_average_penalty(self):
        if self.scrubber_penalty_count > 0:
            return self.scrubber_penalty_sum / self.scrubber_penalty_count
        return 0    
    
    def spawn_ship(self, ship_id):
        """Spawns a new Ship agent at a water cell along the bottom of the grid"""
        # create the new ship
        new_ship = Ship(ship_id, self)
        # Select a water cell from the bottom row.
        bottom_y = 0
        x_range = min(38, self.grid.width)
        possible_positions = []
        for x in range(x_range):
            pos = (x, bottom_y)
            cell_contents = self.grid.get_cell_list_contents(pos)
            if any(isinstance(agent, Terrain) and agent.terrain_type == 'water' for agent in cell_contents):
                possible_positions.append(pos)
        if possible_positions:
            start_pos = self.random.choice(possible_positions)
        else:
            # fallback: choose any water cell in grid.
            water_cells = []
            for x in range(self.grid.width):
                for y in range(self.grid.height):
                    cell_contents = self.grid.get_cell_list_contents((x, y))
                    if any(isinstance(agent, Terrain) and agent.terrain_type == 'water' for agent in cell_contents):
                        water_cells.append((x, y))
            start_pos = self.random.choice(water_cells) if water_cells else (0, bottom_y)
        self.grid.place_agent(new_ship, start_pos)
        self.schedule.add(new_ship)
        
        # determine ship route based on ship type and port popularity
        ports = [agent for agent in self.schedule.agents if isinstance(agent, Port)]
        if ports:
            def base_popularity(port):
            # Use port capacity so that larger ports are slightly more attractive,
            # but all ports start near 1.
                return port.port_capacity / 10.0  # adjust divisor as needed
                
            # ship type specific factors
            # higher number means they prefer busier ports
            # might need tuning to match empirical data
            ship_type_factors = {
                "cargo": 1.0,
                "tanker": 1.0,
                "fishing": 0.9,
                "other": 0.9,
                "tug": 0.8,
                "passenger": 1.0,
                "hsc": 1.0,
                "dredging": 0.8,
                "search": 0.8 
            }
            factor = ship_type_factors.get(new_ship.ship_type, 1.0)
            # weighted list of routes to choose from
            agent_weights = [base_popularity(port) * factor for port in ports]
            
            # algorithm for weighted sampling without replacement
            def weighted_random_sampling(agents, weights, k):
                selected = []
                agents_copy = agents[:]
                weights_copy = weights[:]
                for _ in range(k):
                    total = sum(weights_copy)
                    if total == 0:
                        break
                    r = self.random.random() * total
                    upto = 0
                    for idx, w in enumerate(weights_copy):
                        upto += w
                        if upto >= r:
                            selected.append(agents_copy.pop(idx))
                            weights_copy.pop(idx)
                            break
                return selected
            
            # Choose how many ports to visit; having a larger k (within reasonable bounds) may allow more ports to be involved.
            new_ship.route = weighted_random_sampling(ports, agent_weights, k=3)
        return new_ship
            

    def step(self):
        """
        Step method: gradually spawn ships during initial time steps
        """
         # Gradually spawn ships over spawn_duration steps.
        current_step = self.schedule.steps  # scheduler steps so far
        if current_step < self.spawn_duration and self.remaining_ships > 0:
            # Calculate how many ships to spawn this step.
            spawn_rate = math.ceil(self.remaining_ships / (self.spawn_duration - current_step))
            for _ in range(spawn_rate):
                if self.remaining_ships <= 0:
                    break
                self.spawn_ship(self.next_ship_id)
                self.next_ship_id += 1
                self.remaining_ships -= 1
                
        self.schedule.step()
        self.datacollector.collect(self)

    def lat_lon_to_grid(self, lat, lon):
        """
        Convert lat/lon to grid coordinates
        """
        x = int(((lon - self.min_lon) / (self.max_lon - self.min_lon)) * (self.grid.width - 1))
        y = int(((lat - self.min_lat) / (self.max_lat - self.min_lat)) * (self.grid.height - 1))
        return (x, y)

def agent_portrayal(agent):
    if isinstance(agent, Port):
        color = "brown" if agent.allow_scrubber else "black"
        grid_port_size = 2 if agent.port_capacity == 5 else 3
        return {
            "Shape": "rect", 
            "Color": color, 
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
        # Define color mapping for each ship type.
        ship_colors = {
            "cargo": "blue",
            "tanker": "navy",
            "fishing": "yellow",
            "other": "gray",
            "tug": "orange",
            "passenger": "pink",
            "hsc": "purple",
            "dredging": "brown",
            "search": "green"
        }
        # Select color based on ship type.
        color = ship_colors.get(agent.ship_type, "green")
        # Optional override: if the ship is a scrubber then color it red.
        if agent.is_scrubber:
            color = "red"
        return {
            "Shape": "circle", 
            "Color": color, 
            "Filled": "true", 
            "Layer": 1,
            "r": 1
        }
    elif isinstance(agent, ScrubberTrail):
        return {
            "Shape": "circle", 
            "Color": "orange", 
            "Filled": "true", 
            "Layer": 0,
            "r": 0.5
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

if __name__ == "__main__":
    # grid set up
    grid = CanvasGrid(agent_portrayal, 100, 100, 500, 500)

    server = ModularServer(
        ShipPortModel, 
        [grid], 
        'North Sea Watch',
        {
            'width': 100, 
            'height': 100, 
            'num_ships': 300,
            'ship_wait_time': 100,
            'prob_allow_scrubbers': 0.8      # chance a port allows scrubber ships

        }
    )
    server.port = 8521  # example port
    server.launch()