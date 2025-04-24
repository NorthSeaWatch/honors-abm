"""
This experiment file runs the ShipPortModel for a number of steps (NUM_STEPS)
and repeats this experiment NUM_RUNS times.
In this version, a custom port policy mapping is provided to ban scrubbers on the
major ports: Amsterdam, Rotterdam, Hamburg, Antwerp, and London.
It extracts time series from the DataCollector:
  - Total Scrubber Water (with mean and 95% confidence interval)
  - Total Port Revenue and Total Docked Ships (overall across ports)
  - PortRevenues and PortDocking: dict reporters returning per-port data
For each metric, the average time series and a 95% confidence interval are computed.
For per‑port measures, a “relative” time series is normalized by each port’s overall mean.
The resulting plots are saved as individual image files.
Note: Ensure your ShipPortModel’s DataCollector is configured to record "PortRevenues" and "PortDocking".
"""

import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
from mesa_model import ShipPortModel

# Experiment settings
NUM_RUNS = 20
NUM_STEPS = 1000

# Model parameters (adjust as needed)
WIDTH = 100
HEIGHT = 100
NUM_SHIPS = 300
SHIP_WAIT_TIME = 100
DEFAULT_PORT_POLICY = "tax"         # default for ports not in the custom mapping
SELECTED_PORT = "None"
SELECTED_POLICY = "None"

# Disable custom per-port policies since we enforce a uniform tax.
CUSTOM_PORT_POLICIES = "None"
# Containers for overall metrics (across runs)
all_total_discharge = []  # For TotalScrubberWater
all_revenue = []          # For TotalPortRevenue (overall)
all_docked = []           # For TotalDockedShips

# New container for per-run per-port revenue.
desired_ports = ["amsterdam", "rotterdam", "london", "antwerpen", "hamburg"]
all_port_revenues = {port: [] for port in desired_ports}
# New container for per-run per-port docking frequency.
all_port_docking = {port: [] for port in desired_ports}

for run in range(NUM_RUNS):
    print(f"Running experiment {run+1}/{NUM_RUNS}...")
    # Note the updated instantiation with custom_port_policies.
    model = ShipPortModel(WIDTH, HEIGHT, NUM_SHIPS, ship_wait_time=SHIP_WAIT_TIME,
                          port_policy=DEFAULT_PORT_POLICY,
                          selected_port=SELECTED_PORT,
                          selected_policy=SELECTED_POLICY,
                          custom_port_policies=CUSTOM_PORT_POLICIES)
    for step in range(NUM_STEPS):
        model.step()
    df = model.datacollector.get_model_vars_dataframe()
    all_total_discharge.append(df["TotalScrubberWater"])
    all_revenue.append(df["TotalPortRevenue"])
    all_docked.append(df["TotalDockedShips"])
    
    # Extract per-port revenue time series.
    port_rev_series = df["PortRevenues"]
    port_rev_df = port_rev_series.apply(pd.Series).fillna(0)
    for port in desired_ports:
        key = port.lower()
        if key in port_rev_df.columns:
            series = port_rev_df[key]
        else:
            series = pd.Series(0, index=port_rev_df.index)
        all_port_revenues[port].append(series)
    
    # Extract per-port docking frequency time series.
    port_dock_series = df["PortDocking"]
    port_dock_df = port_dock_series.apply(pd.Series).fillna(0)
    for port in desired_ports:
        key = port.lower()
        if key in port_dock_df.columns:
            series = port_dock_df[key]
        else:
            series = pd.Series(0, index=port_dock_df.index)
        all_port_docking[port].append(series)

# Helper function: calculates mean and 95% confidence interval from a DataFrame (each column = one run)
def calc_mean_ci(df):
    mean_series = df.mean(axis=1)
    std_series = df.std(axis=1)
    n = df.shape[1]
    stderr = std_series / np.sqrt(n)
    ci = 1.96 * stderr  # 95% CI
    return mean_series, ci

# Process overall metrics.
discharge_df = pd.concat(all_total_discharge, axis=1)
discharge_df.columns = range(NUM_RUNS)
avg_discharge, ci_discharge = calc_mean_ci(discharge_df)

revenue_df = pd.concat(all_revenue, axis=1)
revenue_df.columns = range(NUM_RUNS)
avg_revenue, ci_revenue = calc_mean_ci(revenue_df)

docked_df = pd.concat(all_docked, axis=1)
docked_df.columns = range(NUM_RUNS)
avg_docked, ci_docked = calc_mean_ci(docked_df)

# Overall relative revenue
overall_avg_revenue = avg_revenue.mean() if not avg_revenue.empty else 0
relative_revenue = avg_revenue / overall_avg_revenue
ci_relative = ci_revenue / overall_avg_revenue if overall_avg_revenue != 0 else ci_revenue

# Process per-port revenue and compute relative revenue for each desired port.
relative_port_revenues = {}
ci_relative_port = {}
for port in desired_ports:
    port_runs = pd.concat(all_port_revenues[port], axis=1)
    port_runs.columns = range(NUM_RUNS)
    avg_series, ci_series = calc_mean_ci(port_runs)
    overall_port_avg = avg_series.mean() if not avg_series.empty else 0
    rel_series = avg_series / overall_port_avg if overall_port_avg != 0 else avg_series
    rel_ci = ci_series / overall_port_avg if overall_port_avg != 0 else ci_series
    relative_port_revenues[port] = rel_series
    ci_relative_port[port] = rel_ci

# Process per-port docking frequency similarly.
relative_port_docking = {}
ci_relative_docking = {}
for port in desired_ports:
    dock_runs = pd.concat(all_port_docking[port], axis=1)
    dock_runs.columns = range(NUM_RUNS)
    avg_series, ci_series = calc_mean_ci(dock_runs)
    overall_dock_avg = avg_series.mean() if not avg_series.empty else 0
    rel_series = avg_series / overall_dock_avg if overall_dock_avg != 0 else avg_series
    rel_ci = ci_series / overall_dock_avg if overall_dock_avg != 0 else ci_series
    relative_port_docking[port] = rel_series
    ci_relative_docking[port] = rel_ci

# ---- Save individual plots (do not display figures) ----

# 1. Total Scrubber Water over time.
fig, ax = plt.subplots(figsize=(8,6))
ax.plot(avg_discharge.index, avg_discharge.values, color="brown", label="Avg Scrubber Water")
ax.fill_between(avg_discharge.index, (avg_discharge - ci_discharge).values,
                (avg_discharge + ci_discharge).values, color="brown", alpha=0.2)
ax.set_xlabel("Timestep")
ax.set_ylabel("Scrubber Water")
ax.set_title("Total Scrubber Water over Time")
ax.legend()
fig.savefig("uniform_total_scrubber_water_major.png")
plt.close(fig)

# 5. Relative Revenue per port over time.
fig, ax = plt.subplots(figsize=(8,6))
for port in desired_ports:
    rel_series = relative_port_revenues[port]
    rel_ci_series = ci_relative_port[port]
    ax.plot(rel_series.index, rel_series.values, label=port.capitalize())
    ax.fill_between(rel_series.index, (rel_series - rel_ci_series).values,
                    (rel_series + rel_ci_series).values, alpha=0.2)
ax.set_xlabel("Timestep")
ax.set_ylabel("Relative Revenue")
ax.set_title("Relative Revenue per Port over Time")
ax.legend(loc="upper right")
fig.savefig("uniform_relative_revenue_per_port_major.png")
plt.close(fig)

# 6. Relative Docking Frequency per port over time.
fig, ax = plt.subplots(figsize=(8,6))
for port in desired_ports:
    rel_series = relative_port_docking[port]
    rel_ci_series = ci_relative_docking[port]
    ax.plot(rel_series.index, rel_series.values, label=port.capitalize())
    ax.fill_between(rel_series.index, (rel_series - rel_ci_series).values,
                    (rel_series + rel_ci_series).values, alpha=0.2)
ax.set_xlabel("Timestep")
ax.set_ylabel("Relative Docking Frequency")
ax.set_title("Relative Docking Frequency per Port over Time")
ax.legend(loc="upper right")
fig.savefig("uniform_relative_docking_frequency_per_port_major.png")
plt.close(fig)