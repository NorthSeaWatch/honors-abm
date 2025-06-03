"""
This script loads data from three different ban experiments and creates comparison plots
with consistent axes across all experiments.
"""

import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

# Load all datasets
sweden_denmark_data = pd.read_parquet("data/sweden_denmark_ban_exp_data.parquet")
all_countries_data = pd.read_parquet("data/all_countries_ban_exp_data.parquet")
nl_data = pd.read_parquet("data/sweden_denmark_netherlands_ban_exp_data.parquet")

# Print column names to debug
print("Sweden/Denmark data columns:", sweden_denmark_data.columns.tolist())
print("\nAll countries data columns:", all_countries_data.columns.tolist())
print("\nNetherlands data columns:", nl_data.columns.tolist())

# Plot settings
PLOT_START = 200
FIG_SIZE = (24, 6)  # Wider figure to accommodate three subplots

# Function to get y-axis limits for a set of series
def get_y_limits(dataframes, metric_name, ci_prefix=None):
    min_val = float('inf')
    max_val = float('-inf')
    for df in dataframes:
        series = df[metric_name][PLOT_START:]
        ci_name = f"ci_{ci_prefix}" if ci_prefix else f"ci_{metric_name.split('_')[-1]}"
        ci = df[ci_name][PLOT_START:]
        min_val = min(min_val, (series - ci).min())
        max_val = max(max_val, (series + ci).max())
    # Add 5% padding
    range_val = max_val - min_val
    return min_val - 0.05 * range_val, max_val + 0.05 * range_val

# Get consistent y-axis limits for each plot type
scrubber_water_limits = get_y_limits(
    [sweden_denmark_data, all_countries_data, nl_data],
    "avg_discharge",
    ci_prefix="discharge"
)

# Function to plot scrubber water
def plot_scrubber_water(ax, data, y_limits):
    avg_discharge = data["avg_discharge"][PLOT_START:]
    ci_discharge = data["ci_discharge"][PLOT_START:]
    
    ax.plot(avg_discharge.index, avg_discharge.values, color="brown", label="Avg Scrubber Water")
    ax.fill_between(avg_discharge.index, 
                    (avg_discharge - ci_discharge).values,
                    (avg_discharge + ci_discharge).values, 
                    color="brown", alpha=0.2)
    
    ax.set_xlabel("Timestep")
    ax.set_ylabel("Scrubber Water")
    ax.set_ylim(y_limits)
    ax.legend()

# Function to get country-specific metrics
def get_country_metrics(data, metric_prefix):
    metrics = {}
    for col in data.columns:
        if col.startswith(f"{metric_prefix}_"):
            country = col.split("_")[-1]
            if country not in metrics:
                metrics[country] = {
                    "values": data[col][PLOT_START:],
                    "ci": data[f"ci_{metric_prefix}_{country}"][PLOT_START:]
                }
    return metrics

# Get all unique countries across datasets
all_countries = set()
for df in [sweden_denmark_data, all_countries_data, nl_data]:
    for col in df.columns:
        if col.startswith("relative_revenue_"):
            country = col.split("_")[-1]
            all_countries.add(country)
all_countries = sorted(list(all_countries))

# Function to get y-axis limits for relative metrics
def get_relative_limits(dataframes, metric_prefix):
    min_val = float('inf')
    max_val = float('-inf')
    for df in dataframes:
        for country in all_countries:
            if f"{metric_prefix}_{country}" in df.columns:
                series = df[f"{metric_prefix}_{country}"][PLOT_START:]
                ci = df[f"ci_{metric_prefix}_{country}"][PLOT_START:]
                min_val = min(min_val, (series - ci).min())
                max_val = max(max_val, (series + ci).max())
    # Add 5% padding
    range_val = max_val - min_val
    return min_val - 0.05 * range_val, max_val + 0.05 * range_val

# Get consistent y-axis limits for relative metrics
revenue_limits = get_relative_limits(
    [sweden_denmark_data, all_countries_data, nl_data],
    "relative_revenue"
)
docking_limits = get_relative_limits(
    [sweden_denmark_data, all_countries_data, nl_data],
    "relative_docking"
)

# Function to plot relative metrics
def plot_relative_metrics(ax, data, metric_prefix, y_limits, legend_loc="lower right", exclude_ports=False):
    for country in all_countries:
        # Skip port-level data for Sweden/Denmark ban if exclude_ports is True
        if exclude_ports and country.lower() in ['amsterdam', 'antwerpen', 'hamburg', 'london', 'rotterdam']:
            continue
            
        if f"{metric_prefix}_{country}" in data.columns:
            series = data[f"{metric_prefix}_{country}"][PLOT_START:]
            ci = data[f"ci_{metric_prefix}_{country}"][PLOT_START:]
            ax.plot(series.index, series.values, label=country)
            ax.fill_between(series.index,
                          (series - ci).values,
                          (series + ci).values,
                          alpha=0.2)
    
    ax.set_xlabel("Timestep")
    ax.set_ylabel("Relative " + metric_prefix.split("_")[1].title())
    ax.set_ylim(y_limits)
    ax.legend(loc=legend_loc)

# Function to create scenario comparison plot
def create_scenario_plot(data, title, filename, exclude_ports=False):
    fig, axes = plt.subplots(1, 3, figsize=FIG_SIZE)
    
    # Plot relative revenue
    plot_relative_metrics(axes[0], data, "relative_revenue", revenue_limits, exclude_ports=exclude_ports)
    axes[0].set_title("Relative Revenue")
    
    # Plot relative docking
    plot_relative_metrics(axes[1], data, "relative_docking", docking_limits, exclude_ports=exclude_ports)
    axes[1].set_title("Relative Docking Frequency")
    
    # Plot scrubber water
    plot_scrubber_water(axes[2], data, scrubber_water_limits)
    axes[2].set_title("Scrubber Water")
    
    fig.suptitle(title, y=1.05)
    plt.tight_layout()
    fig.savefig(filename)
    plt.close(fig)

# Create plots for each scenario
create_scenario_plot(
    sweden_denmark_data,
    "Sweden/Denmark Ban Scenario",
    "graphs/sweden_denmark_ban_comparison.png",
    exclude_ports=True
)

create_scenario_plot(
    all_countries_data,
    "All Countries Ban Scenario",
    "graphs/all_countries_ban_comparison.png"
)

create_scenario_plot(
    nl_data,
    "Sweden/Denmark/Netherlands Ban Scenario",
    "graphs/nl_ban_comparison.png"
) 