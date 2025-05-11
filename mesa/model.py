from mesa import Agent, Model
import math
import numpy as np
from mesa.time import RandomActivation
from mesa.space import MultiGrid
from mesa.datacollection import DataCollector
from mesa.visualization.modules import CanvasGrid, ChartModule, TextElement
from mesa.visualization.ModularVisualization import ModularServer
# Import additional UI modules
from mesa.visualization.UserParam import UserSettableParameter, Slider, Choice
import csv
from shapely.geometry import Polygon, Point
# Import Port and Ship from their modules
from port import Port
from ship import Ship, Terrain, ScrubberTrail

#To run this mesa model it is suggested to pip install mesa version 0.9.0

class LegendElement(TextElement):
    """Display a legend for the simulation."""
    
    def render(self, model):
        return """
        <div style="background-color: rgba(255, 255, 255, 0.8); padding: 10px; border-radius: 5px;">
            <h3>Legend</h3>
            <div><span style="color: black; font-weight: bold;">■</span> Port (Ban Scrubbers)</div>
            <div><span style="color: orange; font-weight: bold;">■</span> Port (Tax Scrubbers)</div>
            <div><span style="color: green; font-weight: bold;">■</span> Port (Subsidy Non-Scrubbers)</div>
            <div><span style="color: brown; font-weight: bold;">■</span> Port (Allow All)</div>
            <br>
            <div><span style="color: red; font-weight: bold;">●</span> Scrubber Ship</div>
            <div><span style="color: blue; font-weight: bold;">●</span> Cargo Ship</div>
            <div><span style="color: navy; font-weight: bold;">●</span> Tanker Ship</div>
            <div><span style="color: yellow; font-weight: bold;">●</span> Fishing Ship</div>
        </div>
        """

class ShipCountElement(TextElement):
    """Display current ship and port statistics."""
    
    def render(self, model):
        ship_count = sum(1 for a in model.schedule.agents if isinstance(a, Ship))
        scrubber_count = sum(1 for a in model.schedule.agents if isinstance(a, Ship) and getattr(a, 'is_scrubber', False))
        docked_count = sum(len(a.docked_ships) for a in model.schedule.agents if isinstance(a, Port))
        
        return f"""
        <div style="background-color: rgba(255, 255, 255, 0.8); padding: 10px; border-radius: 5px;">
            <h3>Current Statistics</h3>
            <div>Ships: {ship_count}</div>
            <div>Scrubber Ships: {scrubber_count}</div>
            <div>Docked Ships: {docked_count}</div>
            <div>Step: {model.schedule.steps}</div>
        </div>
        """

class ShipPortModel(Model):
    """
    Simulation class that runs the model logic.
    """
    def __init__(self, width, height, num_ships, ship_wait_time=20, port_policy="allow", 
                 custom_port_policies="None", scrubber_ratio=0.15):
        """
        Initialize the ShipPortModel.
        
        Args:
            width (int): Width of the grid
            height (int): Height of the grid
            num_ships (int): Number of ships in the simulation
            ship_wait_time (int): Maximum time a ship will wait to dock
            port_policy (str): Default policy for ports (comma-separated list)
            selected_port (str): Name of port to apply specific policy to
            selected_policy (str): Policy to apply to selected port
            scrubber_ratio (float): Target ratio of scrubber ships (0-1)
        """
        # Basic model setup
        self.width = width
        self.height = height
        self.num_ships = num_ships
        self.ship_wait_time = ship_wait_time
        self.scrubber_ratio = scrubber_ratio
        
        # Initialize grid and scheduler
        self.grid = MultiGrid(width, height, torus=False)
        self.schedule = RandomActivation(self)
        self.running = True
        
        # Ship and port tracking
        self.docked_ships_count = 0
        self.undocked_ships_count = 0
        self.next_trail_id = 10000
        self.next_ship_id = 0
        
        # Scrubber penalty system
        self.scrubber_penalty_sum = 0
        self.scrubber_penalty_count = 0
        
        # Parse custom port policies mapping (format: "Port1:policy1, Port2:policy2")
        if custom_port_policies != "None":
            self.custom_port_policies = {}
            pairs = custom_port_policies.split(',')
            for pair in pairs:
                if ':' in pair:
                    port_name, policy = pair.split(':', 1)
                    self.custom_port_policies[port_name.strip()] = policy.strip()
        else:
            self.custom_port_policies = {}

        # Create land regions using polygons
        self._setup_terrain()
        
        # Set up ports and initialize ships
        self._setup_ports()
        self.remaining_ships = num_ships
        self.spawn_duration = 5  # Spawn ships over this many steps
        
        # Initialize the data collector for charts and analysis
        self._setup_data_collector()
    
    def _setup_terrain(self):
        """Set up terrain (land and water) on the grid."""
        # Land region polygons
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
        
        # Convert to Shapely polygons for faster point-in-polygon checks
        self.land_polygons = [Polygon(region) for region in land_regions]
        
        # Create terrain grid - optimize by creating a lookup grid first
        terrain_grid = {}
        for x in range(self.width):
            for y in range(self.height):
                point = Point(x, y)
                is_land = any(polygon.covers(point) for polygon in self.land_polygons)
                terrain_grid[(x, y)] = 'land' if is_land else 'water'
        
        # Now place terrain agents using the lookup grid
        for x in range(self.width):
            for y in range(self.height):
                terrain_type = terrain_grid[(x, y)]
                terrain = Terrain(f'terrain_{x}_{y}', self, terrain_type)
                self.grid.place_agent(terrain, (x, y))
                self.schedule.add(terrain)
    
    def _setup_ports(self):
        """Set up port agents based on data."""
        for i, port_data in enumerate(Port.raw_port_data):
            # Determine policy for this port using the custom mapping
            port_policy = None
            if port_data['name'] in self.custom_port_policies:
                port_policy = self.custom_port_policies[port_data['name']]
                
            port = Port(i, self, port_data, policy=port_policy)
            x, y = int(port_data['X']), int(port_data['Y'])
            self.grid.place_agent(port, (x, y))
            self.schedule.add(port)
        
        # Start ship IDs after port IDs
        self.next_ship_id = len(Port.raw_port_data)
    
    def _setup_data_collector(self):
        """Set up data collection for charts and analysis."""
        self.datacollector = DataCollector(
            model_reporters = {
                "NumScrubberShips": lambda m: sum(1 for a in m.schedule.agents if isinstance(a, Ship) and getattr(a, 'is_scrubber', False)),
                "NumNonScrubberShips": lambda m: sum(1 for a in m.schedule.agents if isinstance(a, Ship) and not getattr(a, 'is_scrubber', False)),
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
                "ScrubberRatio": lambda m: sum(1 for a in m.schedule.agents if isinstance(a, Ship) and getattr(a, 'is_scrubber', False)) / 
                                           max(1, sum(1 for a in m.schedule.agents if isinstance(a, Ship)))
            },
            agent_reporters = {
                "x": lambda a: a.pos[0] if hasattr(a, "pos") else None,
                "y": lambda a: a.pos[1] if hasattr(a, "pos") else None,
                "Type": lambda a: type(a).__name__,
                "IsScruber": lambda a: getattr(a, "is_scrubber", False) if isinstance(a, Ship) else None,
                "ShipType": lambda a: getattr(a, "ship_type", None) if isinstance(a, Ship) else None,
                "PortPolicy": lambda a: getattr(a, "scrubber_policy", None) if isinstance(a, Port) else None,
                "PortName": lambda a: getattr(a, "name", None) if isinstance(a, Port) else None
            }
        )
        
    def get_average_penalty(self):
        """Calculate the average scrubber penalty."""
        if self.scrubber_penalty_count > 0:
            return self.scrubber_penalty_sum / self.scrubber_penalty_count
        return 0    
    
    def spawn_ship(self, ship_id):
        """Spawns a new Ship agent at a water cell along the bottom of the grid"""
        # Create the new ship
        new_ship = Ship(ship_id, self)
        
        # Cache water cells instead of searching each time
        if not hasattr(self, "water_cells_cache"):
            # Find all water cells along the bottom edge
            bottom_y = 0
            x_range = min(38, self.grid.width)
            bottom_cells = []
            for x in range(x_range):
                pos = (x, bottom_y)
                cell_contents = self.grid.get_cell_list_contents(pos)
                if any(isinstance(agent, Terrain) and agent.terrain_type == 'water' for agent in cell_contents):
                    bottom_cells.append(pos)
            
            # Find all water cells as fallback
            all_water_cells = []
            if not bottom_cells:
                for x in range(self.grid.width):
                    for y in range(self.grid.height):
                        cell_contents = self.grid.get_cell_list_contents((x, y))
                        if any(isinstance(agent, Terrain) and agent.terrain_type == 'water' for agent in cell_contents):
                            all_water_cells.append((x, y))
            
            self.water_cells_cache = {
                "bottom": bottom_cells,
                "all": all_water_cells
            }
        
        # Select starting position
        if self.water_cells_cache["bottom"]:
            start_pos = self.random.choice(self.water_cells_cache["bottom"])
        elif self.water_cells_cache["all"]:
            start_pos = self.random.choice(self.water_cells_cache["all"])
        else:
            start_pos = (0, 0)  # Fallback position
            
        self.grid.place_agent(new_ship, start_pos)
        self.schedule.add(new_ship)
        
        # Cache port agents to avoid repeated searches
        if not hasattr(self, "port_agents_cache"):
            self.port_agents_cache = [agent for agent in self.schedule.agents if isinstance(agent, Port)]
        
        if self.port_agents_cache:
            # Determine ship route based on port popularity and policies
            route = self._determine_ship_route(new_ship)
            new_ship.route = route
        
        return new_ship
    
    def _determine_ship_route(self, ship):
        """Calculate optimal route for a ship based on its type and port attributes."""
        ports = self.port_agents_cache
        
        # Base port popularity factors
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
        
        # Ship type preferences
        ship_type_factors = {
            "cargo": 1.0, "tanker": 1.0, "fishing": 0.8,
            "other": 0.8, "tug": 0.5, "passenger": 1.2,
            "hsc": 1.2, "dredging": 0.6, "search": 0.7 
        }
        factor = ship_type_factors.get(ship.ship_type, 1.0)
        
        # Calculate weights for each port
        agent_weights = []
        for port in ports:
            weight = base_popularity(port)
            
            # Adjust weights based on port policy and ship characteristics
            if port.scrubber_policy == 'ban' and ship.is_scrubber:
                weight = 0  # Scrubber ships avoid ban ports
            elif port.scrubber_policy == 'tax' and ship.is_scrubber:
                weight *= 0.5  # Scrubber ships less likely to visit tax ports
            elif port.scrubber_policy == 'subsidy' and not ship.is_scrubber:
                weight *= 1.5  # Non-scrubber ships prefer subsidy ports
                
            agent_weights.append(weight * factor)
        
        # Weighted random sampling without replacement
        selected = []
        agents_copy = ports.copy()
        weights_copy = agent_weights.copy()
        
        # Select up to 3 ports for the route
        for _ in range(3):
            total = sum(weights_copy)
            if total <= 0:
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

    def step(self):
        """
        Advance the model by one step.
        """
        # Gradually spawn ships over spawn_duration steps
        current_step = self.schedule.steps
        if current_step < self.spawn_duration and self.remaining_ships > 0:
            # Calculate how many ships to spawn this step
            spawn_rate = math.ceil(self.remaining_ships / (self.spawn_duration - current_step))
            for _ in range(spawn_rate):
                if self.remaining_ships <= 0:
                    break
                self.spawn_ship(self.next_ship_id)
                self.next_ship_id += 1
                self.remaining_ships -= 1
        
        # Run all agent steps
        self.schedule.step()
        
        # Collect data for charts and analysis
        self.datacollector.collect(self)
    
    def export_data(self, filename="simulation_data.csv"):
        """Export collected data to CSV file."""
        model_data = self.datacollector.get_model_vars_dataframe()
        model_data.to_csv(filename)
        return f"Data exported to {filename}"

# Visualization functions
def agent_portrayal(agent):
    """Define visual appearance of each agent type."""
    if isinstance(agent, Port):
        # Set port color based on policy
        policy_colors = {
            "ban": "black",
            "tax": "orange",
            "subsidy": "green",
            "allow": "brown"
        }
        color = policy_colors.get(agent.scrubber_policy, "brown")
        
        # Adjust port size based on capacity
        grid_port_size = 2 if agent.port_capacity <= 5 else 3
        
        # Create tooltip text
        tooltip = f"{agent.name} - Policy: {agent.scrubber_policy}<br>Ships: {len(agent.docked_ships)}/{agent.port_capacity}"
        
        return {
            "Shape": "rect", 
            "Color": color, 
            "Filled": "true", 
            "Layer": 1,
            "w": grid_port_size, 
            "h": grid_port_size,
            "port_name": agent.name,
            "text_color": "white",
            "max_capacity": agent.port_capacity,
            "current_capacity": agent.current_capacity,
            "tooltip": tooltip
        }
    elif isinstance(agent, Ship):
        # Ship color based on type
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
        color = ship_colors.get(agent.ship_type, "green")
        
        # Highlight scrubber ships in red
        if agent.is_scrubber:
            color = "red"
            
        # Create tooltip with ship info
        tooltip = f"Ship {agent.unique_id} - Type: {agent.ship_type}"
        tooltip += " (Scrubber)" if agent.is_scrubber else ""
        
        return {
            "Shape": "circle", 
            "Color": color, 
            "Filled": "true", 
            "Layer": 1,
            "r": 1,
            "tooltip": tooltip
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

# Get port names for dropdown
def get_port_names():
    """Get list of available port names from data file."""
    port_names = []
    try:
        with open('filtered_ports_with_x_y.csv', 'r') as port_data:
            open_port = csv.DictReader(port_data)
            for row in open_port:
                port_names.append(row["PORT_NAME"])
    except Exception as e:
        print(f"Error loading port names: {e}")
        port_names = ["Error loading ports"]
    return port_names

if __name__ == "__main__":
    # Set up visualization grid
    grid = CanvasGrid(agent_portrayal, 100, 100, 600, 600)
    
    # Add charts for monitoring key metrics
    ship_chart = ChartModule([
        {"Label": "NumScrubberShips", "Color": "red"},
        {"Label": "NumNonScrubberShips", "Color": "blue"},
    ], data_collector_name='datacollector')
    
    port_chart = ChartModule([
        {"Label": "TotalDockedShips", "Color": "green"},
        {"Label": "AvgPortPopularity", "Color": "orange"},
    ], data_collector_name='datacollector')
    
    revenue_chart = ChartModule([
        {"Label": "TotalPortRevenue", "Color": "purple"},
    ], data_collector_name='datacollector')
    
    trails_chart = ChartModule([
        {"Label": "NumScrubberTrails", "Color": "orange"},
        {"Label": "TotalScrubberWater", "Color": "brown"},
    ], data_collector_name='datacollector')
    
    # Add legend and stats elements
    legend = LegendElement()
    stats = ShipCountElement()
    
    # Get port names for dropdown
    port_names = get_port_names()
    
    # Define model parameters
    model_params = {
        'width': 100,
        'height': 100,
        'num_ships': Slider(
            "Number of Ships", 
            50, 
            10, 
            200, 
            10,
            "Total number of ships in the simulation"
        ),
        'ship_wait_time': Slider(
            "Ship Wait Time", 
            100, 
            10, 
            200, 
            10,
            "Maximum time a ship will wait to dock before leaving"
        ),
        'scrubber_ratio': Slider(
            "Target Scrubber Ratio", 
            0.15, 
            0.0, 
            0.5, 
            0.05,
            "Target proportion of ships with scrubbers"
        ),
        'port_policy': Choice(
            "Default Port Policy", 
            'allow',
            ['allow', 'ban', 'tax', 'subsidy'],
            "Default policy for all ports (unless individually configured)"
        ),
        'custom_port_policies': UserSettableParameter(
        'text', 
        "Custom Port Policies", 
        "None", 
        "Enter port-policy mappings in format PortName:policy, e.g., 'Rotterdam:ban, Antwerp:tax'"
        )
    }

    # Create and launch server
    server = ModularServer(
        ShipPortModel, 
        [grid, legend, stats, ship_chart, port_chart, revenue_chart, trails_chart], 
        'North Sea Watch: Ship & Port Simulation',
        model_params
    )
    server.port = 8521
    server.launch()