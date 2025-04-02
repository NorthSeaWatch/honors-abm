# North Sea Ship Simulation

This project is an Agent-Based Model (ABM) built with Mesa to simulate ship movement and port interactions in the North Sea. It focuses on studying scrubber water discharge from ships (especially large cargo vessels) and how these vessels interact with ports that differ in capacity, popularity, and scrubber policy.

## Overview

The simulation contains several agent types:

- **Port Agents:**  
  - **Data and Capacity Scaling:**  
    Port data is loaded from `filtered_port.csv` and includes the port's name, geographic coordinates, and a categorical capacity (e.g., `M`, `L`). A helper function converts this capacity into a base integer (e.g., `M` becomes 5, `L` becomes 10) which is then scaled by the ratio of total ships to ports.
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

## Key Enhancements

1. **Waiting to Dock:**  
   Ships that cannot dock due to port capacity will remain in place—trying to dock every step until capacity is available.

2. **Scrubber Penalty and Alternate Routing:**  
   When a scrubber ship is rejected by a port (because the port does not allow scrubbers), a penalty counter is increased (both on the ship and cumulatively in the model). This penalty diminishes the probability that future ships will be scrubber-equipped, while the ship then seeks an alternate port.

3. **Exiting and Replacement:**  
   Once a ship completes its route or times out waiting, it exits the simulation through a designated exit zone at the bottom of the grid. Importantly, even when exiting, scrubber trails are recorded. As a ship departs, a replacement ship is spawned to maintain a constant number of ships in the simulation.

4. **Improved Movement:**  
   Ship movement has been enhanced to be less random. If the ideal move toward a target is blocked, the ship examines its valid neighboring cells to select the best move (the one that minimizes the distance to the target) ensuring smoother, more realistic navigation that avoids passing through port cells.

## Running the Simulation

The model uses Mesa’s visualization modules. To run the simulation, open Visual Studio Code on your Mac and execute:

```
python mesa_model.py
```

This starts the **ModularServer** with a CanvasGrid visualization where you can observe ship movements, docking events (including waiting and alternate routing), scrubber trail markings, and ship replacement upon exit.

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