import random
import math
import uuid
import matplotlib.pyplot as plt
from ..agents.ship import Ship

class Model:
    def __init__(self, iterations, number_of_ships, ship_speed=0.01, num_scrubbers=0.3):
        self.iterations = iterations
        self.ships = []
        self.num_scrubbers = num_scrubbers
        self.trails = []  # Store trails of scrubber ships
        self.current_step=0
        self.add_ships(number_of_ships, ship_speed)
        
        self.setup_plot()

        
    def add_ships(self, number_of_ships, ship_speed):
        "Add a ship to the model"
        for _ in range (number_of_ships):
            pos_x = random.random()
            pos_y = random.random()
            angle = random.uniform(0, 2 * math.pi)
            imo_id = uuid.uuid4() 
            
            # ship distribution will be altered once we have descriptives of north sea traffic
            if random.random() < self.num_scrubbers:
                self.ships.append(Ship(imo_id, pos_x, pos_y, angle, 0.02, scrubber_usage=True))
                return 
            self.ships.append(Ship(imo_id, pos_x, pos_y, angle, ship_type="passenger", speed=ship_speed, scrubber_usage=False))
            
        
    def run(self, iterations=None):
        if iterations is None:
            iterations = self.iterations
            
        for i in range(iterations):
            self.step()
            self.draw()
            
    def step(self):
        self.current_step += 1
        for ship in self.ships:
            if ship.scrubber_usage:
                self.trails.append((ship.pos_x, ship.pos_y, self.current_step))
            ship.step()
            
        # Remove trails older than 50 steps
        self.trails = [(x, y, t) for x, y, t in self.trails if self.current_step - t <= 50]
            
    def draw(self):
        self.ax1.axis([0, 1, 0, 1])
        
        # Plot the trails for scrubber ships
        if self.trails:
            trail_x, trail_y, timestamps = zip(*self.trails)
            alphas = [(50 - (self.current_step - t)) / 50 * 0.1 for t in timestamps]
            self.ax1.scatter(trail_x, trail_y, c='red', alpha=alphas, s=1)

        # collect updated x and y positions for all creatures
        pos_x = [ship.pos_x for ship in self.ships]
        pos_y = [ship.pos_y for ship in self.ships]

        colors = [ship.color for ship in self.ships]

        # redraw grid
        self.ax1.scatter(pos_x, pos_y, c=colors)

        plt.draw()
        plt.pause(0.01)
        self.ax1.cla()


    def setup_plot(self):
        self.fig, self.ax1 = plt.subplots(1)
        self.ax1.set_aspect('equal')
        self.ax1.axes.get_xaxis().set_visible(False)
        self.ax1.axes.get_yaxis().set_visible(False)
