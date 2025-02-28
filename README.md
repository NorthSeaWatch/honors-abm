# North Sea Ship Simulation

This project is an Agent-Based Model (ABM) simulation of ships in the North Sea, focusing on scrubber water discharge from ships using scrubbers. The model tracks the movement of ships across various ports and logs discharge data.

## Project Overview

The goal is to simulate the movement of ships, particularly large cargo vessels that use scrubbers, and track their environmental impact in terms of scrubber water discharge. The simulation will include features like:
- Agent-based behavior: Ships act as individual agents with their own characteristics (e.g., scrubber usage, route, position).
- Environmental monitoring: Tracking scrubber water discharge and other relevant data.
- Visualization: Future work will include visualizing ship movements and data output.
- Data Collection: Simulate and store data related to ship routes, discharge, and interactions.

## File Structure

The project is organized into the following structure:

```
honors-abm/
├── .gitignore             # Files and directories to ignore in version control
├── README.md              # Project overview and documentation
├── requirements.txt       # Project dependencies
├── src/                   # Code related to the simulation
│   ├── agents/            # Ship and agent logic
│   │   └── ship.py        # Ship class
│   ├── model/             # NorthSeaModel, scheduling logic
│   │   └── model.py       # Main model class
│   ├── visualization/     # (For future visualization code)
│   └── utils/             # Helper functions, constants, etc.
├── data/                  # Input data or outputs (e.g., maps)
├── notebooks/             # Jupyter notebooks for analysis, testing, etc.
└── tests/                 # Unit tests for agents, models, etc.
    └── test_agents.py     # Tests for ship agent behavior
```

To run the unit tests:
```
 python -m unittest discover tests/
```