# North Sea Ship Simulation

This project is an Agent-Based Model (ABM) built with Mesa to simulate ship movement and port interactions in the North Sea. It focuses on studying scrubber water discharge from ships (especially large cargo vessels) and how these vessels interact with ports that differ in capacity, popularity, and scrubber policy.

## Project Structure

```
honors-abm/
├── mesa/
│   ├── data/                  # Contains experiment data files
│   ├── graphs/               # Output directory for visualization plots
│   ├── mesa_model.py         # Core simulation model
│   ├── ship.py              # Ship agent implementation
│   ├── port.py              # Port agent implementation
│   ├── plot_comparison.py   # Script for comparing experiment results
│   ├── sweden_denmark_ban_exp.py    # Sweden/Denmark ban experiment
│   ├── all_countries_ban_exp.py     # All countries ban experiment
│   ├── nl_ban.py            # Netherlands ban experiment
│   └── filtered_ports_with_x_y.csv  # Port data with grid coordinates
└── requirements.txt         # Python dependencies
```

## Overview

The simulation contains several agent types:

- **Port Agents:**  
  - **Data and Capacity Scaling:**  
    Port data is loaded from `filtered_ports_with_x_y.csv` and includes the port's name, geographic coordinates, and a categorical capacity (e.g., `M`, `L`). A helper function converts this capacity into a base integer (e.g., `M` becomes 5, `L` becomes 10) which is then scaled by the ratio of total ships to ports.
   - **Docking Logic and Revenue:**  
    - Ports decide whether to allow docking based on current capacity and a randomized policy on scrubber acceptance.
    - Each docking event generates revenue based on a base fee for the ship type and a dynamic pricing multiplier. The multiplier increases with the current occupancy, reflecting higher fees when the port is fuller.
    - Collected revenue is tracked for each port and exported as part of the simulation data.
  
- **Ship Agents:**  
  - **Type Assignment & Scrubber Status:**  
    Each ship is assigned a type (cargo, tanker, fishing, etc.) based on empirical proportions. Depending on the type, a base probability is set for having a scrubber (e.g., approximately 18% for cargo ships, 13% for tankers, 5% for others). This probability is then adjusted downward if previous scrubber penalties have been recorded.
  - **Routing and Movement:**  
    Ships are given a route through a weighted random sampling of ports (typically three per route) based on port popularity and ship-type factors.  
    The movement logic is now smarter:
    - **Smart Routing:**  
      Ships use a helper method to compute an ideal move toward the target. If the ideal cell is blocked or contains a port, the method examines neighboring water cells and selects the one that minimizes the Euclidean distance to the target.
    - **Docking:**  
      When near a target port, a ship attempts to dock. If docking fails due to capacity constraints, the ship waits at its current position and reattempts docking each subsequent step.
    - **Alternate Routing for Scrubbers:**  
      When a scrubber ship is rejected because the target port does not allow scrubbers, a penalty is applied to the vessel. This penalty adjusts the chance for future ships to be scrubber-equipped. The rejected port is then skipped in favor of an alternate route.
  - **Exiting and Replacement:**  
    Once a ship completes its route or its waiting time expires, it navigates toward a designated exit zone (restricted to water cells on the lower part of the grid, e.g. within the first 38 cells on the x-axis). The ship leaves a scrubber trail even while exiting. Upon exit, the ship is removed from the simulation and immediately replaced by a new ship, keeping the total number of ships constant.

- **ScrubberTrail Agents:**  
  Representing the trail of scrubber water discharged by ships, these agents carry a fixed number of water units and fade over a set lifespan. They allow visualization of cumulative environmental impact over time.

- **Terrain Agents:**  
  The underlying grid is populated with Terrain agents (land or water) based on geographic polygon definitions. Ships are only allowed to move over water cells, and movement through ports is prohibited.

## Experiments

The project includes three main experiments to study the effects of different scrubber ban policies:

1. **Sweden/Denmark Ban** (`sweden_denmark_ban_exp.py`):
   - Simulates the impact of banning scrubber water discharge in Swedish and Danish ports
   - Analyzes changes in ship routing, port revenue, and environmental impact

2. **All Countries Ban** (`all_countries_ban_exp.py`):
   - Models a scenario where all North Sea ports ban scrubber water discharge
   - Examines system-wide effects on shipping patterns and environmental outcomes

3. **Netherlands Ban** (`nl_ban.py`):
   - Studies the effects of adding Netherlands to the Sweden/Denmark ban
   - Evaluates regional impacts and potential ripple effects

## Visualization and Analysis

The `plot_comparison.py` script generates comparative visualizations of the experiment results, showing:
- Relative revenue changes for each port
- Relative docking frequency changes
- Total scrubber water discharge patterns

Results are saved in the `graphs/` directory as PNG files.

## Running the Simulation

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Run a specific experiment:
```bash
python mesa/mesa_model.py
```

This starts the **ModularServer** with a CanvasGrid visualization where you can observe:
- Ship movements and routing
- Docking events (including waiting and alternate routing)
- Scrubber trail markings
- Ship replacement upon exit

## Data Organization

- **Input Data:**
  - Port data is stored in `filtered_ports_with_x_y.csv`
  - Experiment parameters are defined in the respective experiment files

- **Output Data:**
  - Experiment results are saved in the `data/` directory as parquet files
  - Visualization plots are generated in the `graphs/` directory