import os
import json
import pandas as pd
from datetime import datetime
from google.cloud.sql.connector import Connector
from sqlalchemy import create_engine, text
from mesa_model import ShipPortModel, Ship, Port, ScrubberTrail, Terrain


# Set the environment variable to the JSON key file for the service account.
# pulled from the ais-stream-api-reop
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "north-sea-watch-39a510f80808.json"

# DB connection constants
DB_NAME = os.getenv("DB_NAME", "ais_data_collection")
DB_USER = os.getenv("DB_USER", "aoyamaxx")
DB_PASSWORD = os.getenv("DB_PASSWORD", "aoyamaxx")
INSTANCE_CONNECTION_NAME = "north-sea-watch:europe-west4:ais-database"

# Create a connection object using Connector.
connector = Connector()
def getconn():
    conn = connector.connect(
        INSTANCE_CONNECTION_NAME,
        "pg8000",
        user=DB_USER,
        password=DB_PASSWORD,
        db=DB_NAME,
    )
    return conn

engine = create_engine("postgresql+pg8000://", creator=getconn)

def create_tables():
    ddl_statements = [
        """
        CREATE TABLE IF NOT EXISTS experiments (
            experiment_id SERIAL PRIMARY KEY,
            run_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            parameters JSON
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS abm_ships (
            id SERIAL PRIMARY KEY,
            experiment_id INTEGER,
            step INTEGER,
            ship_unique_id INTEGER,
            ship_type VARCHAR(50),
            is_scrubber BOOLEAN,
            route JSON,
            x INTEGER,
            y INTEGER,
            docking_steps INTEGER,
            wait_time INTEGER,
            docked BOOLEAN,
            FOREIGN KEY (experiment_id) REFERENCES experiments(experiment_id)
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS abm_ports (
            id SERIAL PRIMARY KEY,
            experiment_id INTEGER,
            step INTEGER,
            port_id INTEGER,
            name VARCHAR(100),
            lat NUMERIC,
            lon NUMERIC,
            port_capacity INTEGER,
            current_capacity INTEGER,
            allow_scrubber BOOLEAN,
            x INTEGER,
            y INTEGER,
            FOREIGN KEY (experiment_id) REFERENCES experiments(experiment_id)
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS abm_cells (
            id SERIAL PRIMARY KEY,
            experiment_id INTEGER,
            step INTEGER,
            x INTEGER,
            y INTEGER,
            occupied_by_ship BOOLEAN,
            occupied_by_trail BOOLEAN,
            FOREIGN KEY (experiment_id) REFERENCES experiments(experiment_id)
        )
        """
    ]
    with engine.begin() as conn:
        for ddl in ddl_statements:
            conn.execute(text(ddl))
    print("Tables created or verified.")

def log_simulation_state(model, experiment_id, step):
    ship_data = []
    port_data = []
    cell_data = []
    # Log ship/port details from agents in the schedule.
    for agent in model.schedule.agents:
        if isinstance(agent, Ship):
            # route stored as port unique_ids; convert route to JSON string.
            route = [port.unique_id for port in agent.route] if agent.route else []
            ship_data.append({
                "experiment_id": experiment_id,
                "step": step,
                "ship_unique_id": agent.unique_id,
                "ship_type": agent.ship_type,
                "is_scrubber": agent.is_scrubber,
                "route": json.dumps(route),
                "x": agent.pos[0],
                "y": agent.pos[1],
                "docking_steps": agent.docking_steps,
                "wait_time": agent.wait_time,
                "docked": agent.docked
            })
        elif isinstance(agent, Port):
            port_data.append({
                "experiment_id": experiment_id,
                "step": step,
                "port_id": agent.unique_id,
                "name": agent.name,
                "lat": agent.lat,
                "lon": agent.lon,
                "port_capacity": agent.port_capacity,
                "current_capacity": agent.current_capacity,
                "allow_scrubber": agent.allow_scrubber,
                "x": agent.pos[0],
                "y": agent.pos[1]
            })
    # For water cells, iterate through grid cells.
    for (x, y) in model.grid.coord_iter():
        cell_contents = model.grid.get_cell_list_contents((x, y))
        # Mark if a ship or scrubber trail occupies the cell.
        occupied_by_ship = any(isinstance(a, Ship) for a in cell_contents)
        occupied_by_trail = any(isinstance(a, ScrubberTrail) for a in cell_contents)
        cell_data.append({
            "experiment_id": experiment_id,
            "step": step,
            "x": x,
            "y": y,
            "occupied_by_ship": occupied_by_ship,
            "occupied_by_trail": occupied_by_trail,
        })
    # Convert lists to DataFrame and then push to database.
    ships_df = pd.DataFrame(ship_data)
    ports_df = pd.DataFrame(port_data)
    cells_df = pd.DataFrame(cell_data)
    
    with engine.begin() as conn:
        if not ships_df.empty:
            ships_df.to_sql("abm_ships", conn, if_exists="append", index=False)
        if not ports_df.empty:
            ports_df.to_sql("abm_ports", conn, if_exists="append", index=False)
        if not cells_df.empty:
            cells_df.to_sql("abm_cells", conn, if_exists="append", index=False)
    print(f"Step {step} logged.")

def run_experiment(num_steps=50, width=100, height=100, num_ships=120, ship_wait_time=100, prob_allow_scrubbers=0.5):
    # Insert a new experiment record and get the generated experiment_id.
    experiment_params = {
        "width": width,
        "height": height,
        "num_ships": num_ships,
        "ship_wait_time": ship_wait_time,
        "prob_allow_scrubbers": prob_allow_scrubbers
    }
    with engine.begin() as conn:
        result = conn.execute(
            text("INSERT INTO experiments (parameters) VALUES (:params) RETURNING experiment_id"),
            {"params": json.dumps(experiment_params)}
        )
        experiment_id = result.scalar()
    print(f"Experiment {experiment_id} started at {datetime.now()}")
    
    # Initialize the Mesa model.
    model = ShipPortModel(width, height, num_ships, ship_wait_time, prob_allow_scrubbers)
    # Run the model for a given number of steps.
    for step in range(num_steps):
        model.step()
        log_simulation_state(model, experiment_id, step)
    
    print("Experiment complete.")

if __name__ == "__main__":
    create_tables()
    run_experiment(num_steps=350)