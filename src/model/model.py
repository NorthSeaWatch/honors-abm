import random
import math
import uuid
import matplotlib.pyplot as plt
import matplotlib.image as mpimg
from matplotlib.offsetbox import OffsetImage, AnnotationBbox
from agents.ship import Ship
from agents.port import Port
import os
import csv

#load port data
port_data_path = os.path.abspath('data/filtered_port.csv')

#load port image
port_path = os.path.abspath('static/port_image.png')
port_img = mpimg.imread(port_path)

class Model:
    """
    Initializes the simulation model.

        Attributes:
        - self.iterations (int): Stores the total number of simulation steps.
        - self.ships (list): A list that will store all ship objects.
        - self.ports (list): A list that will store port locations.
        - self.num_scrubbers (float): The proportion of ships with scrubbers.
        - self.trails (list): A list to store the movement history (trails) of ships.
        - self.current_step (int): Tracks the current step of the simulation.
    """

    def __init__(self, iterations, number_of_ships, ship_speed=0.01, num_scrubbers=0.3):
        self.iterations = iterations
        self.ships = []
        self.ports = []
        self.num_scrubbers = num_scrubbers
        self.trails = []
        self.current_step = 0
        self.add_ports()
        self.add_ships(number_of_ships, ship_speed)
        self.setup_plot()
    
    def add_ports(self):
        """Add ports to the model with their coordinates"""
    
        ports_data = []
        with open(port_data_path, 'r') as csv_file_port:
            reader_port = csv.DictReader(csv_file_port)
            
            # First collect all lat/lon values to find min/max for normalization
            all_lats = []
            all_lons = []
            
            # First pass to collect all coordinates
            raw_port_data = []
            for row in reader_port:
                lat = float(row["LATITUDE"])
                lon = float(row["LONGITUDE"])
                all_lats.append(lat)
                all_lons.append(lon)
                raw_port_data.append({
                    "id": int(row["INDEX_NO"]),
                    "name": row["PORT_NAME"],
                    "lat": lat,
                    "lon": lon,
                    "capacity": row["HARBORSIZE"]
                })
            
            # Calculate min/max for normalization
            min_lat, max_lat = min(all_lats), max(all_lats)
            min_lon, max_lon = min(all_lons), max(all_lons)
            
            # Calculate the center points
            center_lat = (min_lat + max_lat) / 2
            center_lon = (min_lon + max_lon) / 2
            
            # Determine the range 
            # The larger these factors, the more spread out the ports will be
            spread_factor = 1
            lat_range = (max_lat - min_lat) * spread_factor
            lon_range = (max_lon - min_lon) * spread_factor
            
            # Second pass to normalize and create ports
            for port_data in raw_port_data:
                # Center and scale coordinates
                normalized_x = 0.5 + ((port_data["lon"] - center_lon) / lon_range)
                normalized_y = 0.5 + ((port_data["lat"] - center_lat) / lat_range)
                
                # Ensure coordinates remain within 0-1 range
                normalized_x = max(0.05, min(0.95, normalized_x))
                normalized_y = max(0.05, min(0.95, normalized_y))
                
                port = Port(
                    port_id=port_data["id"],
                    port_name=port_data["name"],
                    max_capacity=port_data["capacity"],
                    current_capacity=0,
                    pos_x=normalized_x,
                    pos_y=normalized_y
                )
                self.ports.append(port)
    
    def add_ships(self, number_of_ships, ship_speed):
        """Add ships to the model"""
        for _ in range(number_of_ships):
            pos_x = random.random()
            pos_y = random.random()
            angle = random.uniform(0, 2 * math.pi)
            imo_id = uuid.uuid4()
            
            # Determine if ship has a destination port
            # 95% of ships have a destination
            assigned_port = None
            if random.random() < 0.95:
                assigned_port = random.choice(self.ports)
            
            # Create ship
            if random.random() < self.num_scrubbers:
                self.ships.append(Ship(
                    imo_id, pos_x, pos_y, angle, 0.02, 
                    scrubber_usage=True, 
                    destination_port=assigned_port
                ))
            else:
                self.ships.append(Ship(
                    imo_id, pos_x, pos_y, angle, 
                    ship_type="passenger", 
                    speed=ship_speed, 
                    scrubber_usage=False,
                    destination_port=assigned_port
                ))
    
    def run(self, iterations=None):
        if iterations is None:
            iterations = self.iterations
        for i in range(iterations):
            self.step()
            self.draw()
    
    def step(self):
        self.current_step += 1
        
        for ship in self.ships:
            # If ship is already at a port
            if hasattr(ship, 'current_port') and ship.current_port:
                # Check if ship should leave the port
                # 10% chance to leave port
                if random.random() < 0.1:
                    port = ship.current_port
                    port.undock_ship(ship)
                    ship.current_port = None
                    ship.at_port = False
                    
                    # Assign a new destination
                     # 95% chance to get new destination
                    if random.random() < 0.95:
                        # Pick a different port than the one just left
                        possible_ports = [p for p in self.ports if p != port]
                        ship.destination_port = random.choice(possible_ports) if possible_ports else None
                    else:
                        ship.destination_port = None
                    ship.step()
                continue
            
            # If ship has a destination port, check if it's reached it
            if ship.destination_port:
                distance = ship.destination_port.calculate_distance(ship)
                
                # If ship is at port location
                if distance < 0.1:
                    # Try to dock the ship
                    if ship.destination_port.dock_ship(ship):
                        ship.at_port = True
                        ship.current_port = ship.destination_port
                        continue
                
                # Ship isn't at port yet, adjust heading towards the port
                target_angle = math.atan2(
                    ship.destination_port.pos_y - ship.pos_y, 
                    ship.destination_port.pos_x - ship.pos_x
                )
                # Gradually adjust ship angle toward target
                angle_diff = (target_angle - ship.angle + math.pi) % (2 * math.pi) - math.pi
                ship.angle += 0.1 * angle_diff
            
            # Record trail if it's a scrubber ship
            if ship.scrubber_usage:
                self.trails.append((ship.pos_x, ship.pos_y, self.current_step))
            
            # Move the ship
            ship.step()
        
        # Update port capacities
        for port in self.ports:
            port.update_capacity()
            
        # Remove trails older than 50 steps
        self.trails = [(x, y, t) for x, y, t in self.trails if self.current_step - t <= 50]
    
    def draw(self):
        self.ax1.axis([0, 1, 0, 1])

        # Draw ports
        for port in self.ports:
            imagebox = OffsetImage(port_img, zoom=0.007) 
            ab = AnnotationBbox(imagebox, (port.pos_x, port.pos_y), frameon=False)
            self.ax1.add_artist(ab)
                
            # Add port name and capacity text
            self.ax1.text(port.pos_x, port.pos_y - 0.02,
                        f"{port.port_name} ({port.current_capacity}/{port.max_capacity_filter()})",
                        fontsize=7, ha='center', va='top')
            
        # Plot the trails for scrubber ships
        if self.trails:
            trail_x, trail_y, timestamps = zip(*self.trails)
            alphas = [(50 - (self.current_step - t)) / 50 * 0.1 for t in timestamps]
            self.ax1.scatter(trail_x, trail_y, c='red', alpha=alphas, s=1)
        
        # Collect updated x and y positions for all ships
        for ship in self.ships:
            if not hasattr(ship, 'at_port') or not ship.at_port:
                self.ax1.scatter(ship.pos_x, ship.pos_y, c=ship.color)
                # Draw a line indicating direction
                line_length = 0.02
                end_x = ship.pos_x + math.cos(ship.angle) * line_length
                end_y = ship.pos_y + math.sin(ship.angle) * line_length
                self.ax1.plot([ship.pos_x, end_x], [ship.pos_y, end_y], color=ship.color)
        
        plt.draw()
        plt.pause(0.01)
        self.ax1.cla()
        
    def setup_plot(self):
        self.fig, self.ax1 = plt.subplots(1, figsize = (7,7))
        self.ax1.set_aspect('equal')
        self.ax1.axes.get_xaxis().set_visible(False)
        self.ax1.axes.get_yaxis().set_visible(False)
