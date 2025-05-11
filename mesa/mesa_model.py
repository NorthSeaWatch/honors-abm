from mesa import Agent, Model
import math
import numpy as np
from mesa.time import RandomActivation
from mesa.space import MultiGrid
#leave this import for now for future data collection and visualization
from mesa.datacollection import DataCollector
from mesa.visualization.modules import CanvasGrid
from mesa.visualization.ModularVisualization import ModularServer
from mesa.visualization.UserParam import UserSettableParameter, Slider, Choice
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
    def __init__(self, width, height, num_ships, ship_wait_time=20, port_policy="allow", selected_port=None, selected_policy=None, custom_port_policies="None"):
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
        
        # initialize scrubber penalty accumulators
        self.scrubber_penalty_sum = 0
        self.scrubber_penalty_count = 0
        
        self.port_policy = [p.strip() for p in port_policy.split(',') if p.strip()]

        # Store the selected port and policy for UI interaction
        self.selected_port = selected_port
        self.selected_policy = selected_policy
        
        # Process custom port policies mapping (e.g., "amsterdam:ban, rotterdam:ban, hamburg:ban, antwerp:ban, london:ban")
        if custom_port_policies != "None":
            self.custom_port_policies = {}
            for pair in custom_port_policies.split(','):
                if ':' in pair:
                    port_name, policy = pair.split(':', 1)
                    self.custom_port_policies[port_name.strip().lower()] = policy.strip()
        else:
            self.custom_port_policies = {}

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
        
        # Create port agents with potential custom policies.
        for i, port_data in enumerate(Port.raw_port_data):
            # Check if a custom policy exists for this port (using lower-case names)
            port_policy_for_agent = None
            port_name_lc = port_data['name'].lower()
            if self.custom_port_policies and port_name_lc in self.custom_port_policies:
                port_policy_for_agent = self.custom_port_policies[port_name_lc]
            # Otherwise, if UI was used to select a specific port policy, then apply it.
            elif selected_port != "None" and selected_policy != "None":
                if port_data['name'] == selected_port:
                    port_policy_for_agent = selected_policy
            # Create the Port agent with the determined policy.
            port = Port(i, self, port_data, policy=port_policy_for_agent)
            x, y = int(port_data['X']), int(port_data['Y'])
            self.grid.place_agent(port, (x, y))
            self.schedule.add(port)
        
        num_ports = len(Port.raw_port_data)
        self.next_ship_id = num_ports
        self.remaining_ships = num_ships
        self.spawn_duration = 3
        
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
                "NumPortsBan": lambda m: sum(1 for a in m.schedule.agents if isinstance(a, Port) and  a.scrubber_policy == "ban"),
                "NumPortsTax": lambda m: sum(1 for a in m.schedule.agents if isinstance(a, Port) and  a.scrubber_policy == "tax"),
                "NumPortsSubsidy": lambda m: sum(1 for a in m.schedule.agents if isinstance(a, Port) and  a.scrubber_policy == "subsidy"),
                "NumPortsAllow": lambda m: sum(1 for a in m.schedule.agents if isinstance(a, Port) and  a.scrubber_policy == "allow"),
                "TotalPortRevenue": lambda m: sum(a.revenue for a in m.schedule.agents if isinstance(a, Port)),
                "AvgPortRevenue": lambda m: (sum(a.revenue for a in m.schedule.agents if isinstance(a, Port)) 
                                             / max(1, sum(1 for a in m.schedule.agents if isinstance(a, Port)))),
                "PortRevenues": lambda m: {port.name.lower(): port.revenue
                                            for port in m.schedule.agents if isinstance(port, Port)},
                "PortDocking": lambda m: {port.name.lower(): len(port.docked_ships)
                                          for port in m.schedule.agents if isinstance(port, Port)},
                
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
            # base port popularity (based on empirical data)
            def base_popularity(port):
                port_name = port.name.lower()
                if port_name == "rotterdam":
                    return 8
                elif port_name == "antwerp":
                    return 5
                elif port_name in ["amsterdam", "hamburg"]:
                    return 2
                else:
                    return 1
                
            # ship type specific factors
            # higher number means they prefer busier ports
            # might need tuning to match empirical data
            ship_type_factors = {
                "cargo": 1.0,
                "tanker": 1.0,
                "fishing": 0.8,
                "other": 0.8,
                "tug": 0.5,
                "passenger": 1.2,
                "hsc": 1.2,
                "dredging": 0.6,
                "search": 0.7 
            }
            factor = ship_type_factors.get(new_ship.ship_type, 1.0)
            # weighted list of routes to choose from
            agent_weights = []
            for port in ports:
                weight = base_popularity(port)
                # Adjust weights based on port policy and ship type.
                if port.scrubber_policy == 'ban' and new_ship.is_scrubber:
                    weight = 0
                elif port.scrubber_policy == 'tax' and new_ship.is_scrubber:
                    weight *= 0.5  # reduce desirability for scrubber ships
                elif port.scrubber_policy == 'subsidy' and not new_ship.is_scrubber:
                    weight *= 1.5  # increase desirability for non-scrubber ships
                agent_weights.append(weight * factor)
            # algorithm for weighted sampling without replacement
            def weighted_random_sampling(agents, weights, k):
                selected = []
                agents_copy = agents[:]
                weights_copy = weights[:]
                for _ in range(k):
                    total = sum(weights_copy)
                    r = self.random.random() * total
                    upto = 0
                    for idx, w in enumerate(weights_copy):
                        upto += w
                        if upto >= r:
                            selected.append(agents_copy.pop(idx))
                            weights_copy.pop(idx)
                            break
                return selected
            # we need to figure out how many ports ships typically visit (3 has been chosen arbitrarily)
            new_ship.route = weighted_random_sampling(ports, agent_weights, 3)
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
        if agent.scrubber_policy == "ban":
            color = "black"
        elif agent.scrubber_policy == "tax":
            color = "orange"
        elif agent.scrubber_policy == "subsidy":
            color = "green"
        else:
            color = "brown"
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

# Create port name list for dropdown menu
def get_port_names():
    port_names = []
    for port_data in Port.raw_port_data:
        port_names.append(port_data["name"])
    return port_names


if __name__ == "__main__":
    # grid set up
    grid = CanvasGrid(agent_portrayal, 100, 100, 500, 500)
    
    # Get available port names for dropdown
    port_names = []
    with open('filtered_ports_with_x_y.csv', 'r') as port_data:
        open_port = csv.DictReader(port_data)
        for row in open_port:
            port_names.append(row["PORT_NAME"])

    # Define the model parameters that can be set by the user
    model_params = {
        'width': 100,
        'height': 100,
        'num_ships': Slider("Number of Ships", 50, 10, 200, 10),
        'ship_wait_time': Slider("Ship Wait Time", 100, 10, 200, 10),
        'port_policy': UserSettableParameter('choice', 'Default Port Policy', 
                                           value='allow',
                                           choices=['allow', 'ban', 'tax', 'subsidy']),
        'selected_port': UserSettableParameter('choice', 'Select Port to Configure', 
                                             value="None",
                                             choices=["None"] + port_names),
        'selected_policy': UserSettableParameter('choice', 'Policy for Selected Port', 
                                               value="None",
                                               choices=["None", 'allow', 'ban', 'tax', 'subsidy'])
    }

    server = ModularServer(
        ShipPortModel, 
        [grid], 
        'North Sea Watch',
        model_params
    )
    
    server.port = 8521  # example port
    server.launch()