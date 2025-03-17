import numpy as np
import matplotlib.pyplot as plt
from mesa_model import ShipPortModel

def run_simulation(prob, steps=1000, num_ships=200, ship_wait_time=100):
    """
    Run the ShipPortModel for a specified number of steps and return the final aggregated metrics.
    """
    model = ShipPortModel(width=100, height=100, num_ships=num_ships, 
                          ship_wait_time=ship_wait_time, prob_allow_scrubbers=prob)
    for _ in range(steps):
        model.step()
    data = model.datacollector.get_model_vars_dataframe()
    final_vals = data.iloc[-1]
    return final_vals

def experiment(prob_values, steps=1000):
    # Metrics to compare. (Adjust if you add more reporters.)
    metrics = ["AvgPortPopularity", "NumPortsBan", "NumScrubberShips", "NumShips", "TotalScrubberWater"]
    results = {metric: [] for metric in metrics}
    
    for prob in prob_values:
        final_vals = run_simulation(prob, steps=steps)
        for metric in metrics:
            results[metric].append(final_vals[metric])
        print(f"Probability {prob:.2f}: " + ", ".join(f"{metric}={final_vals[metric]:.2f}" for metric in metrics))
    
    return results

if __name__ == "__main__":
    # Test over a range of probability values from 0 to 1.
    prob_values = np.linspace(0, 1, 6)
    results = experiment(prob_values, steps=1000)
    
    # Create plots for each metric against the probability
    plt.figure(figsize=(12, 8))
    for metric, values in results.items():
        plt.plot(prob_values, values, marker='o', linewidth=2, label=metric)
    plt.xlabel("Probability Port Allows Scrubbers")
    plt.ylabel("Final Value")
    plt.title("Final Metrics vs. Probability Port Allows Scrubbers")
    plt.legend()
    plt.tight_layout()
    plt.show()