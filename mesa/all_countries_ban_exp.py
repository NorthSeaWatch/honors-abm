"""
This experiment runs the ShipPortModel with all ports in all countries set to a 'ban' policy.
It saves all collected time series and per-country data to a Parquet file, and generates:
- Relative revenue per country (legend lower right)
- Relative docking frequency per country (legend lower right)
- Total scrubber water over time
"""

import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
from mesa_model import ShipPortModel
import csv
import os
from tqdm import tqdm

# Experiment settings
NUM_RUNS = 20
NUM_STEPS = 1000
WIDTH = 100
HEIGHT = 100
NUM_SHIPS = 300
SHIP_WAIT_TIME = 100
DEFAULT_PORT_POLICY = "allow"
SELECTED_PORT = "None"
SELECTED_POLICY = "None"

# --- Identify all ports and build port-to-country mapping ---
port_csv = os.path.join(os.path.dirname(__file__), "filtered_ports_with_x_y.csv")
port_to_country = {}
country_set = set()
with open(port_csv, "r") as f:
    reader = csv.DictReader(f)
    for row in reader:
        country = row["COUNTRY"].strip().upper()
        name = row["PORT_NAME"].strip().lower()
        port_to_country[name] = country
        country_set.add(country)
country_list = sorted(country_set)
ban_ports = list(port_to_country.keys())
custom_port_policies = ", ".join(f"{p}:ban" for p in ban_ports)

# Containers for overall metrics (across runs)
all_total_discharge = []
all_revenue = []
all_docked = []
all_num_ships = []
all_num_ports_ban = []
all_num_ports_tax = []
all_num_ports_subsidy = []
all_num_ports_allow = []

# Per-country containers
all_country_revenues = {country: [] for country in country_list}
all_country_docking = {country: [] for country in country_list}

for run in tqdm(range(NUM_RUNS), desc="Experiment Runs"):
    model = ShipPortModel(WIDTH, HEIGHT, NUM_SHIPS, ship_wait_time=SHIP_WAIT_TIME,
                          port_policy=DEFAULT_PORT_POLICY,
                          selected_port=SELECTED_PORT,
                          selected_policy=SELECTED_POLICY,
                          custom_port_policies=custom_port_policies)
    for step in range(NUM_STEPS):
        model.step()
    df = model.datacollector.get_model_vars_dataframe()
    all_total_discharge.append(df["TotalScrubberWater"])
    all_revenue.append(df["TotalPortRevenue"])
    all_docked.append(df["TotalDockedShips"])
    all_num_ships.append(df["NumShips"])
    all_num_ports_ban.append(df["NumPortsBan"])
    all_num_ports_tax.append(df["NumPortsTax"])
    all_num_ports_subsidy.append(df["NumPortsSubsidy"])
    all_num_ports_allow.append(df["NumPortsAllow"])
    # Per-country revenue and docking
    port_rev_series = df["PortRevenues"]
    port_rev_df = port_rev_series.apply(pd.Series).fillna(0)
    country_rev_df = pd.DataFrame(0, index=port_rev_df.index, columns=country_list)
    for port in port_rev_df.columns:
        country = port_to_country.get(port, None)
        if country:
            country_rev_df[country] += port_rev_df[port]
    for country in country_list:
        all_country_revenues[country].append(country_rev_df[country])
    # Per-country docking
    port_dock_series = df["PortDocking"]
    port_dock_df = port_dock_series.apply(pd.Series).fillna(0)
    country_dock_df = pd.DataFrame(0, index=port_dock_df.index, columns=country_list)
    for port in port_dock_df.columns:
        country = port_to_country.get(port, None)
        if country:
            country_dock_df[country] += port_dock_df[port]
    for country in country_list:
        all_country_docking[country].append(country_dock_df[country])

# Helper: mean and 95% CI
calc_mean_ci = lambda df: (df.mean(axis=1), 1.96 * df.std(axis=1) / np.sqrt(df.shape[1]))

discharge_df = pd.concat(all_total_discharge, axis=1)
discharge_df.columns = range(NUM_RUNS)
avg_discharge, ci_discharge = calc_mean_ci(discharge_df)

revenue_df = pd.concat(all_revenue, axis=1)
revenue_df.columns = range(NUM_RUNS)
avg_revenue, ci_revenue = calc_mean_ci(revenue_df)

docked_df = pd.concat(all_docked, axis=1)
docked_df.columns = range(NUM_RUNS)
avg_docked, ci_docked = calc_mean_ci(docked_df)

num_ships_df = pd.concat(all_num_ships, axis=1)
num_ships_df.columns = range(NUM_RUNS)
avg_num_ships, ci_num_ships = calc_mean_ci(num_ships_df)

num_ports_ban_df = pd.concat(all_num_ports_ban, axis=1)
num_ports_ban_df.columns = range(NUM_RUNS)
avg_ports_ban, ci_ports_ban = calc_mean_ci(num_ports_ban_df)
num_ports_tax_df = pd.concat(all_num_ports_tax, axis=1)
num_ports_tax_df.columns = range(NUM_RUNS)
avg_ports_tax, ci_ports_tax = calc_mean_ci(num_ports_tax_df)
num_ports_subsidy_df = pd.concat(all_num_ports_subsidy, axis=1)
num_ports_subsidy_df.columns = range(NUM_RUNS)
avg_ports_subsidy, ci_ports_subsidy = calc_mean_ci(num_ports_subsidy_df)
num_ports_allow_df = pd.concat(all_num_ports_allow, axis=1)
num_ports_allow_df.columns = range(NUM_RUNS)
avg_ports_allow, ci_ports_allow = calc_mean_ci(num_ports_allow_df)

# Per-country relative revenue and docking
relative_country_revenues = {}
ci_relative_country = {}
for country in country_list:
    country_runs = pd.concat(all_country_revenues[country], axis=1)
    country_runs.columns = range(NUM_RUNS)
    avg_series, ci_series = calc_mean_ci(country_runs)
    overall_country_avg = avg_series.mean() if not avg_series.empty else 0
    rel_series = avg_series / overall_country_avg if overall_country_avg != 0 else avg_series
    rel_ci = ci_series / overall_country_avg if overall_country_avg != 0 else ci_series
    relative_country_revenues[country] = rel_series
    ci_relative_country[country] = rel_ci

relative_country_docking = {}
ci_relative_country_docking = {}
for country in country_list:
    dock_runs = pd.concat(all_country_docking[country], axis=1)
    dock_runs.columns = range(NUM_RUNS)
    avg_series, ci_series = calc_mean_ci(dock_runs)
    overall_dock_avg = avg_series.mean() if not avg_series.empty else 0
    rel_series = avg_series / overall_dock_avg if overall_dock_avg != 0 else avg_series
    rel_ci = ci_series / overall_dock_avg if overall_dock_avg != 0 else ci_series
    relative_country_docking[country] = rel_series
    ci_relative_country_docking[country] = rel_ci

# ---- Save all data to Parquet ----
all_data = {
    "avg_discharge": avg_discharge,
    "ci_discharge": ci_discharge,
    "avg_revenue": avg_revenue,
    "ci_revenue": ci_revenue,
    "avg_docked": avg_docked,
    "ci_docked": ci_docked,
    "avg_num_ships": avg_num_ships,
    "ci_num_ships": ci_num_ships,
    "avg_ports_ban": avg_ports_ban,
    "ci_ports_ban": ci_ports_ban,
    "avg_ports_tax": avg_ports_tax,
    "ci_ports_tax": ci_ports_tax,
    "avg_ports_subsidy": avg_ports_subsidy,
    "ci_ports_subsidy": ci_ports_subsidy,
    "avg_ports_allow": avg_ports_allow,
    "ci_ports_allow": ci_ports_allow,
}
for country in country_list:
    all_data[f"relative_revenue_{country}"] = relative_country_revenues[country]
    all_data[f"ci_relative_revenue_{country}"] = ci_relative_country[country]
    all_data[f"relative_docking_{country}"] = relative_country_docking[country]
    all_data[f"ci_relative_docking_{country}"] = ci_relative_country_docking[country]
all_df = pd.DataFrame(all_data)
all_df.to_parquet("data/all_countries_ban_exp_data.parquet")

# ---- Plots ----
PLOT_START = 200

def plot_relative_country(df, ci_df, ylabel, title, fname, country_list, legend_loc="lower right"):
    fig, ax = plt.subplots(figsize=(8,6))
    for country in country_list:
        rel_series = df[f"relative_revenue_{country}"][PLOT_START:]
        rel_ci_series = ci_df[f"ci_relative_revenue_{country}"][PLOT_START:]
        ax.plot(rel_series.index, rel_series.values, label=country)
        ax.fill_between(rel_series.index, (rel_series - rel_ci_series).values,
                        (rel_series + rel_ci_series).values, alpha=0.2)
    ax.set_xlabel("Timestep")
    ax.set_ylabel(ylabel)
    ax.set_title(title)
    ax.legend(loc=legend_loc)
    fig.savefig(fname)
    plt.close(fig)

def plot_relative_country_docking(df, ci_df, ylabel, title, fname, country_list, legend_loc="lower right"):
    fig, ax = plt.subplots(figsize=(8,6))
    for country in country_list:
        rel_series = df[f"relative_docking_{country}"][PLOT_START:]
        rel_ci_series = ci_df[f"ci_relative_docking_{country}"][PLOT_START:]
        ax.plot(rel_series.index, rel_series.values, label=country)
        ax.fill_between(rel_series.index, (rel_series - rel_ci_series).values,
                        (rel_series + rel_ci_series).values, alpha=0.2)
    ax.set_xlabel("Timestep")
    ax.set_ylabel(ylabel)
    ax.set_title(title)
    ax.legend(loc=legend_loc)
    fig.savefig(fname)
    plt.close(fig)

plot_relative_country(
    all_df, all_df,
    ylabel="Relative Revenue",
    title="Relative Revenue per Country over Time",
    fname="graphs/all_countries_ban_relative_revenue_per_country.png",
    country_list=country_list,
    legend_loc="lower right"
)

plot_relative_country_docking(
    all_df, all_df,
    ylabel="Relative Docking Frequency",
    title="Relative Docking Frequency per Country over Time",
    fname="graphs/all_countries_ban_relative_docking_frequency_per_country.png",
    country_list=country_list,
    legend_loc="lower right"
)

avg_discharge = all_df["avg_discharge"][PLOT_START:]
ci_discharge = all_df["ci_discharge"][PLOT_START:]

fig, ax = plt.subplots(figsize=(8,6))
ax.plot(avg_discharge.index, avg_discharge.values, color="brown", label="Avg Scrubber Water")
ax.fill_between(avg_discharge.index, (avg_discharge - ci_discharge).values,
                (avg_discharge + ci_discharge).values, color="brown", alpha=0.2)
ax.set_xlabel("Timestep")
ax.set_ylabel("Scrubber Water")
ax.set_title("Total Scrubber Water over Time")
ax.legend()
fig.savefig("graphs/all_countries_ban_total_scrubber_water.png")
plt.close(fig)
