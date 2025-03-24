# North Sea Ship Simulation

This project is an Agent-Based Model (ABM) simulation built with Mesa that models ship movement and port interactions in the North Sea. The simulation is designed to study scrubber water discharge from ships—particularly large cargo vessels with scrubber systems—and how ships interact with ports of varying capacity and popularity.

## Overview

The simulation includes several agents with specific roles:

- **Port Agents:**  
  Represents ports (docks) in the simulation. Port data is loaded from a CSV file (`filtered_port.csv`) and includes attributes such as the port’s name, geographic coordinates, and categorical capacity (`M`, `L`, etc.).  
  - **Capacity Scaling:**  
    Each port’s base capacity is adjusted by scaling with the ratio of the total number of ships in the simulation to the number of ports. This allows the model to better reflect different load conditions as the number of ships changes.
  - **Docking Logic:**  
    Ports determine whether to allow docking based on current capacity and if the port allows scrubber-equipped ships.

- **Ship Agents:**  
  Represents dynamic ship entities that navigate the grid.  
  - **Type Assignment:**  
    Each ship is randomly assigned a type (such as cargo, tanker, fishing, etc.) based on empirical proportions.  
  - **Scrubber Usage:**  
    Depending on the ship type, the probability that a ship has a scrubber is set (e.g., 18% for cargo ships, 13% for tankers, 5% for others by default). Ships with scrubbers are visually marked (colored red if they have scrubbers) to highlight potential environmental impact.
  - **Movement and Routing:**  
    Ships are given routes based on port popularity and ship-type specific factors using a weighted random sampling algorithm without replacement. The algorithm combines a base popularity metric (e.g., Rotterdam being most popular) with a factor that adjusts the weight based on the ship's type.  
    - Simple step-by-step movement is computed using differences in grid coordinates (using a sign function) and validated to ensure movement only occurs over water.
    - When ships are near a target port, an attempt is made to dock; if a port is full or not permitting a ship (especially scrubber-equipped ones where appropriate), the ship continues its motion.

- **ScrubberTrail Agents:**  
  These agents model the trail left behind by scrubber-equipped ships as they move.  
  - They carry a fixed number of water units and fade (are removed) after a set lifespan, which helps track cumulative scrubber water discharge over time.

- **Terrain Agents:**  
  Represents the underlying grid representing water and land.  
  - A `Terrain` agent is placed on every grid cell, with the type determined from a series of polygons defining land regions versus water.
    
## Key Model Components

- **Port Capacity Scaling:**  
  The `port_size` method in the Port class converts a categorical capacity into a base integer (e.g., `M` becomes 5, `L` becomes 10), which is then scaled by the ratio of the total number of ships to the number of ports. This ensures that as more ships are added, each port's effective capacity increases proportionally.

- **Ship Route Selection:**  
  The route for each ship is chosen by weighting ports according to both empirical port popularity and ship-type specific factors. A custom weighted random sampling algorithm is used:
  - The algorithm creates a copy of the list of ports and weights.
  - Iterates to randomly select a port based on the calculated weights.
  - This sampling is done without replacement to achieve diversity in the ship's route (typically, each ship will have a route containing three ports).

- **Agent Visualizations:**  
  The agent portrayal function defines how each agent is rendered:
  - **Ports:** Colored brown or black (depending on scrubber policy) with size based on capacity.
  - **Ships:** Colored based on their type (e.g., blue for cargo, navy for tanker, yellow for fishing, etc.). Ships with scrubbers override the color to red.
  - **Scrubber Trails:** Displayed as orange circles.
  - **Terrain:** Land is rendered in silver and water in light blue.

## Running the Simulation

The model is integrated with Mesa’s visualization modules. To run the simulation, open Visual Studio Code (on your Mac) and run the following command from the terminal:

```
python mesa_model.py
```

This command starts the **ModularServer** with a CanvasGrid visualization, allowing you to observe ship movements, docking events, and environmental effects in real-time.


## Data Logging and Export (abm_export.py)

This script is designed to collect and export simulation data from the Mesa model into a relational database using a bulk insert strategy. Here’s a breakdown of what each part does:

- **Database Connection and Table Creation:**  
  The script uses the Google Cloud SQL Connector and SQLAlchemy to connect to a PostgreSQL database. The `create_tables()` function verifies (or creates if needed) four tables:
  - `experiments` – stores metadata for each experiment run (with parameters and run date).
  - `abm_ships` – holds per-step information for each Ship agent (such as ID, ship type, scrubber status, route as JSON, position, docking details, etc.).
  - `abm_ports` – records per-step state for each Port agent (including its ID, name, geographic coordinates, capacity, and current status).
  - `abm_cells` – logs grid cell activity (only for cells with a Ship or a ScrubberTrail) including their coordinates and occupancy status.

- **Data Collection (Function: collect_simulation_state):**  
  This function is called every simulation step. It iterates over the model’s agents to gather:
  - **Ship Data:** For every Ship, the function collects its unique ID, type, scrubber flag, assigned route (as a list of port IDs), grid coordinates, and docking/wait information.
  - **Port Data:** For every Port, it records the port’s unique ID, name, location (latitude and longitude), capacity details, and whether the port allows scrubber ships.
  - **Cell Data:** To reduce overhead, cell-level logging (i.e. checking if a cell contains a Ship or a ScrubberTrail) happens **only every 10 steps**. Only cells with activity are recorded.

  Each call to this function returns lists of new data entries for ships, ports, and active grid cells.

- **Experiment Run and Bulk Insert (Function: run_experiment):**  
  In the `run_experiment` function:
  - An experiment record is first inserted into the database to generate an `experiment_id` that links all future data.
  - The Mesa model is then initialized and run for a specified number of steps.
  - At each step, the data from `collect_simulation_state` is accumulated in memory (i.e. appended to lists for ships, ports, and cells).
  - After the simulation completes, the accumulated data is converted into Pandas DataFrames and inserted into the database using a **bulk insert**. This minimizes database transactions and improves performance.

- **Performance Considerations:**  
  By logging only cells with activity and sampling cell data only every 10 steps, the script reduces the amount of data written to the database—helping the overall experiment run faster.

This module provides a robust mechanism for capturing the evolution of ship, port, and cell states over time, enabling later analysis and visualization (for instance, on a Mapbox instance).