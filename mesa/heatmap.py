"""
This experiment file runs the ShipPortModel for a number of steps and saves 
heatmaps of the spatial discharge shift at three points in time: after 100 steps,
after 500 steps, and at the final timestep.
Each heatmap is computed by summing the 'water_units' from any ScrubberTrail agents
present in each grid cell. A scale factor is applied to intensify the trails.
A background image of the North Sea is attempted to be loaded to superimpose behind the heatmap.
If the file "northsea_map.png" is not found, the heatmap is plotted on a plain background.
"""

import matplotlib.pyplot as plt
import numpy as np
import os
from mesa_model import ShipPortModel
from ship import ScrubberTrail  # ensure ScrubberTrail is imported
import matplotlib.image as mpimg

# Experiment & Model Settings
NUM_STEPS = 100
WIDTH = 100
HEIGHT = 100
NUM_SHIPS = 300
SHIP_WAIT_TIME = 100
DEFAULT_PORT_POLICY = "allow"
SELECTED_PORT = "None"
SELECTED_POLICY = "None"
CUSTOM_PORT_POLICIES = "amsterdam:ban, rotterdam:ban, hamburg:ban, antwerpen:ban, london:ban"
SCALING_FACTOR = 50  # Increase strength of trails

# Instantiate the model.
model = ShipPortModel(WIDTH, HEIGHT, NUM_SHIPS, ship_wait_time=SHIP_WAIT_TIME,
                      port_policy=DEFAULT_PORT_POLICY,
                      selected_port=SELECTED_PORT,
                      selected_policy=SELECTED_POLICY,
                      custom_port_policies=CUSTOM_PORT_POLICIES)

# Helper function to compute a spatial discharge heatmap.
def get_spatial_discharge(model, scale=1):
    # Create an array of zeros matching the grid dimensions.
    heatmap = np.zeros((model.grid.width, model.grid.height))
    for x in range(model.grid.width):
        for y in range(model.grid.height):
            cell_agents = model.grid.get_cell_list_contents((x, y))
            # Sum water_units for any ScrubberTrail agents and apply the scaling factor.
            total_discharge = sum(getattr(agent, "water_units", 0)
                                  for agent in cell_agents if isinstance(agent, ScrubberTrail))
            heatmap[x, y] = total_discharge * scale
    return heatmap

# Specify time steps at which to record the heatmap.
record_steps = [10, 50, NUM_STEPS]
heatmaps = {}

for step in range(1, NUM_STEPS + 1):
    model.step()
    if step in record_steps:
        print(f"Recording spatial discharge at step {step}...")
        heatmaps[step] = get_spatial_discharge(model, scale=SCALING_FACTOR)

# Try to load background image if available.
background = None
bg_filename = "northsea_map.png"
if os.path.exists(bg_filename):
    try:
        background = mpimg.imread(bg_filename)
    except Exception as e:
        print(f"Error reading {bg_filename}: {e}")
        background = None
else:
    print(f"{bg_filename} not found. Plotting heatmaps without background.")

# Create and save heatmap images.
for step, h_map in heatmaps.items():
    fig, ax = plt.subplots(figsize=(8, 6))
    # Show background if available.
    if background is not None:
        ax.imshow(background, extent=[0, model.grid.width, 0, model.grid.height],
                  origin="lower")
    # Overlay the heatmap. Use transparency so background is visible if present.
    cax = ax.imshow(h_map.T, origin="lower", cmap="hot", alpha=0.6,
                    extent=[0, model.grid.width, 0, model.grid.height])
    ax.set_title(f"Spatial Discharge Heatmap at Timestep {step}")
    ax.set_xlabel("X Coordinate")
    ax.set_ylabel("Y Coordinate")
    fig.colorbar(cax, ax=ax, label="Scaled Discharge")
    fig.savefig(f"heatmap_t{step}.png")
    plt.close(fig)