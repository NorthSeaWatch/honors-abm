from mesa import Agent, Model
from mesa.time import RandomActivation
from mesa.space import MultiGrid
#leave this import for now for future data collection and visualization
from mesa.datacollection import DataCollector
from mesa.visualization.modules import CanvasGrid
from mesa.visualization.ModularVisualization import ModularServer
import csv
from shapely.geometry import Polygon, Point

class ScrubberTrail(Agent):
    """
    Agent representing a discharge trail from a scrubber ship.
    Carries 10 units of scrubber water and fades after a few steps.
    """
    def __init__(self, unique_id, model, lifespan=35):
        super().__init__(unique_id, model)
        self.water_units = 10
        self.lifespan = lifespan
    
    def step(self):
        self.lifespan -= 1
        if self.lifespan <= 0:
            self.model.grid.remove_agent(self)
            self.model.schedule.remove(self)
            
                
class Terrain(Agent):
    """"
    A terrain agent in the North Sea simulation - static.
    """
    def __init__(self, unique_id, model, terrain_type):
        super().__init__(unique_id, model)
        self.terrain_type = terrain_type

class Ship(Agent):
    """"
    A ship agent in the North Sea simulation - dynamic.
    """
    def __init__(self, unique_id, model):
        super().__init__(unique_id, model)
        # assign ship type based on empirical proportions
        self.ship_type = self.model.random.choices(
            population=['cargo', 'tanker', 'fishing', 'other', 'tug', 'passenger', 'hsc', 'dredging', 'search'],
            weights=[0.532, 0.213, 0.106, 0.032, 0.032, 0.053, 0.011, 0.011, 0.011],
            k=1
        )[0]
        #ship is not docked in the first step
        self.docked = False
        #steps that ship was docked
        self.docking_steps = 0  
        
        self.route = []
        self.current_target_index = 0
        
        # update scrubber probability based on ship type
        if self.ship_type == 'cargo':
            scrubber_prob = 0.18
        elif self.ship_type == 'tanker':
            scrubber_prob = 0.13
        else:
            scrubber_prob = 0.05
        self.is_scrubber = (self.model.random.random() < scrubber_prob)
        
        # Count the steps the ship is waiting to dock.
        self.wait_time = 0
        
    def sign(self, x):
        if x > 0:
            return 1
        elif x < 0:
            return -1
        else:
            return 0
    

    def step(self):
        """
        Ship movement method. 
        """
        # If already removed from the schedule, stop processing.
        if self not in self.model.schedule.agents:
            return
        if not self.docked:
            old_pos = self.pos  # save current position before moving
            if self.route and self.current_target_index < len(self.route):
                target_port = self.route[self.current_target_index]
                target_pos = target_port.pos # port's grid position
                current_pos = self.pos
                
                # Calculate a one-step move in the direction of the target port using a simple sign function.
                dx = self.sign(target_pos[0] - current_pos[0])
                dy = self.sign(target_pos[1] - current_pos[1])
                new_position = (current_pos[0] + dx, current_pos[1] + dy)
                
                # First check if the chosen cell is water
                cell_contents = self.model.grid.get_cell_list_contents(new_position)
                if any(isinstance(agent, Terrain) and agent.terrain_type == 'water' for agent in cell_contents):
                    self.model.grid.move_agent(self, new_position)
                else:
                    # Fallback: choose a random water cell from the neighborhood if the ideal move isn't valid.
                    possible_steps = self.model.grid.get_neighborhood(self.pos, moore=True, include_center=True)
                    valid_steps = []
                    for pos in possible_steps:
                        cell_contents = self.model.grid.get_cell_list_contents(pos)
                        if any(isinstance(agent, Terrain) and agent.terrain_type == 'water' for agent in cell_contents):
                            valid_steps.append(pos)
                    if valid_steps:
                        new_position = self.random.choice(valid_steps)
                        self.model.grid.move_agent(self, new_position)
                
                # If the ship is in or next to the target port's cell, attempt docking.
                if self.pos == target_pos or target_pos in self.model.grid.get_neighborhood(self.pos, moore=True, include_center=True):
                    if target_port.dock_ship(self):
                        self.docked = True
                        self.docking_steps = 0
                        self.wait_time = 0  # reset when docked
                        print(f'Ship {self.unique_id} docked at {target_port.name}')
                    # if docking fails (for example due to capacity), keep moving toward the target.
            else:
                # default random movement (water cells only) if no valid route is set
                possible_steps = self.model.grid.get_neighborhood(self.pos, moore=True, include_center=True)
                valid_steps = []
                for pos in possible_steps:
                    cell_contents = self.model.grid.get_cell_list_contents(pos)
                    if any(isinstance(agent, Terrain) and agent.terrain_type == 'water' for agent in cell_contents):
                        valid_steps.append(pos)
                if valid_steps:
                    new_position = self.random.choice(valid_steps)
                    self.model.grid.move_agent(self, new_position)
                    
            # If the ship moved and is a scrubber ship, leave a trail
            if self.is_scrubber and self.pos != old_pos:
                new_trail = ScrubberTrail(self.model.next_trail_id, self.model)
                self.model.next_trail_id += 1
                self.model.grid.place_agent(new_trail, old_pos)
                self.model.schedule.add(new_trail)
            
            # Increase wait time when not docked.
            self.wait_time += 1
            if self.wait_time >= self.model.ship_wait_time:
                print(f"Ship {self.unique_id} removed due to timeout waiting to dock.")
                self.model.grid.remove_agent(self)
                self.model.schedule.remove(self)
                return
        else:
            # If the ship is docked, increment the docking counter.
            self.docking_steps += 1      
            # After 10 steps, undock and, if a route is defined, move to the next target port.
            if self.docking_steps >= 10:
                for agent in self.model.schedule.agents:
                    if isinstance(agent, Port) and self in agent.docked_ships:
                        agent.undock_ship(self)
                        print(f'Ship {self.unique_id} undocked from {agent.name}')
                        self.docked = False
                        # Advance to the next target port in the route.
                        self.current_target_index += 1
                        break
                    