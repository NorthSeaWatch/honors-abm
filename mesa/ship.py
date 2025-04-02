from mesa import Agent, Model
from mesa.time import RandomActivation
from mesa.space import MultiGrid
#leave this import for now for future data collection and visualization
from mesa.datacollection import DataCollector
from mesa.visualization.modules import CanvasGrid
from mesa.visualization.ModularVisualization import ModularServer
import csv
from shapely.geometry import Polygon, Point
from port import Port

class ScrubberTrail(Agent):
    """
    Agent representing a discharge trail from a scrubber ship.
    Carries 10 units of scrubber water and fades after a few steps.
    """
    def __init__(self, unique_id, model, lifespan=60):
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
            base_prob = 0.18
        elif self.ship_type == 'tanker':
            base_prob = 0.13
        else:
            base_prob = 0.05
            
        # adjust probability based on model's average scrubber penalty
        avg_penalty = self.model.get_average_penalty()
        adjusted_prob = base_prob / (1 + avg_penalty)
        self.is_scrubber = (self.model.random.random() < adjusted_prob)
        
        # initialize ship penalty
        self.penalty = 0
    
        # Count the steps the ship is waiting to dock.
        self.wait_time = 0
        
    def sign(self, x):
        if x > 0:
            return 1
        elif x < 0:
            return -1
        else:
            return 0
        
    def is_valid_move(self, pos):
        cell_contents = self.model.grid.get_cell_list_contents(pos)
        # valid if cell contains water and does NOT contain any Port instance.
        is_water = any(isinstance(agent, Terrain) and agent.terrain_type == "water" for agent in cell_contents)
        has_port = any(isinstance(agent, Port) for agent in cell_contents)
        return is_water and not has_port
    
    def move_along_route(self, target_pos, current_pos):
        # Calculate the ideal step direction.
        dx = self.sign(target_pos[0] - current_pos[0])
        dy = self.sign(target_pos[1] - current_pos[1])
        ideal_pos = (current_pos[0] + dx, current_pos[1] + dy)
        if self.is_valid_move(ideal_pos):
            self.model.grid.move_agent(self, ideal_pos)
            return
        
        # If the ideal move is blocked, look among neighbors.
        neighbors = self.model.grid.get_neighborhood(current_pos, moore=True, include_center=False)
        valid_neighbors = [pos for pos in neighbors if self.is_valid_move(pos)]
        if valid_neighbors:
            # Choose the neighbor that minimizes the Euclidean distance to the target.
            def distance(pos):
                return ((pos[0] - target_pos[0])**2 + (pos[1] - target_pos[1])**2)**0.5
            best_move = min(valid_neighbors, key=distance)
            self.model.grid.move_agent(self, best_move)
        else:
            # Fallback: If no valid neighbor was found, the ship stays in place.
            pass
                
    def step(self):
        """
        Ship movement method. 
        """
        # If already removed from the schedule, stop processing.
        if self not in self.model.schedule.agents:
            return
        
         # If not already marked as exiting, check if the route is complete.
        if not hasattr(self, "exiting"):
            self.exiting = False
        if not self.exiting:
            # Check if route is defined and whether the ship has reached its destination.
            if self.route and self.current_target_index >= len(self.route):
                self.exiting = True
            # Also trigger exiting if waiting time is up
            if self.wait_time >= self.model.ship_wait_time:
                self.exiting = True
                print(f"Ship {self.unique_id} initiating exit due to timeout waiting to dock.")
                
            # pick a target cell at the bottom of the english channel to exit form
            if self.exiting and not hasattr(self, "exit_target"):
                bottom_y = 0
                x_range = min(38, self.model.grid.width) # width of the english channel (roughly)
                possible_exits = []
                for x in range(x_range):
                    pos = (x, bottom_y)
                    cell_contents = self.model.grid.get_cell_list_contents(pos)
                    if any(isinstance(agent, Terrain) and agent.terrain_type == 'water' for agent in cell_contents):
                        possible_exits.append(pos)
                if possible_exits:
                    self.exit_target = self.random.choice(possible_exits)
                else:
                    self.exit_target = (0, bottom_y)
                    
        # if exiting, move toward exit_target
        if self.exiting:
            old_pos = self.pos
            target_pos = self.exit_target
            self.move_along_route(target_pos, old_pos)
            # leave a scrubber trail if the ship is a scrubber
            if self.is_scrubber and self.pos != old_pos:
                new_trail = ScrubberTrail(self.model.next_trail_id, self.model)
                self.model.next_trail_id += 1
                self.model.grid.place_agent(new_trail, old_pos)
                self.model.schedule.add(new_trail)
            # when reached the exit cell, remove ship form simulation
            if self.pos == target_pos:
                print(f"Ship {self.unique_id} has exited the simulation at {self.pos}.")    
                self.model.grid.remove_agent(self)
                self.model.schedule.remove(self)
                # Spawn a replacement ship so the total remains constant.
                self.model.spawn_ship(self.model.next_ship_id)
                self.model.next_ship_id += 1
                return   
                           
        else:
            old_pos = self.pos  # save current position before moving
            if self.route and self.current_target_index < len(self.route):
                target_port = self.route[self.current_target_index]
                target_pos = target_port.pos # port's grid position
                current_pos = self.pos
                
                self.move_along_route(target_pos, current_pos)
            
                # If the ship is in or next to the target port's cell, attempt docking.
                if self.pos == target_pos or target_pos in self.model.grid.get_neighborhood(self.pos, moore=True, include_center=True):
                    success = target_port.dock_ship(self)
                    if success:
                        self.docked = True
                        self.docking_steps = 0
                        self.wait_time = 0  # reset when docked
                        print(f'Ship {self.unique_id} docked at {target_port.name}')
                    else:
                        # distinguish between rejection due to capacity vs. scrubber restrictions.
                        if self.is_scrubber and not target_port.allow_scrubber:
                            self.penalty += 1
                            self.model.scrubber_penalty_sum += 1
                            self.model.scrubber_penalty_count += 1
                            print(f"Ship {self.unique_id} penalized. Port {target_port.name} does not allow scrubbers. Searching for another port.")
                            # Skip this port in favor of an alternate.
                            self.current_target_index += 1
                        else:
                            # Unable to dock due to lack of capacity: wait (do not change position).
                            print(f"Ship {self.unique_id} waiting at {self.pos} for port {target_port.name} capacity.")
            
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
            if not self.docked:
                self.wait_time += 1
        
           
        # If the ship is docked, increment the docking counter.
        if self.docked:
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
                    