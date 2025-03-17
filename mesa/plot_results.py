import matplotlib.pyplot as plt
from mesa_model import ShipPortModel

# Create the model.
model = ShipPortModel(width=100, height=100, num_ships=200, ship_wait_time= 100,
            prob_allow_scrubbers= 0.1)
steps = 1000

for _ in range(steps):
    model.step()

# Get DataCollector model variables as a Pandas DataFrame.
data = model.datacollector.get_model_vars_dataframe()

# Create dashboard subplots
fig, axs = plt.subplots(2, 3, figsize=(18, 10))

# Plot 1: Number of Scrubber Ships
axs[0, 0].plot(data.index, data["NumScrubberShips"], label="Scrubber Ships")
axs[0, 0].set_xlabel("Steps")
axs[0, 0].set_ylabel("Num Scrubber Ships")
axs[0, 0].set_title("Scrubber Ships Over Time")
axs[0, 0].legend()

# Plot 2: Total Scrubber Water
axs[0, 1].plot(data.index, data["TotalScrubberWater"], label="Scrubber Water", color='blue')
axs[0, 1].set_xlabel("Steps")
axs[0, 1].set_ylabel("Total Scrubber Water")
axs[0, 1].set_title("Scrubber Water Over Time")
axs[0, 1].legend()

# Plot 3: Number of Scrubber Trails
axs[0, 2].plot(data.index, data["NumScrubberTrails"], label="Scrubber Trails", color='orange')
axs[0, 2].set_xlabel("Steps")
axs[0, 2].set_ylabel("Num Scrubber Trails")
axs[0, 2].set_title("Scrubber Trails Over Time")
axs[0, 2].legend()

# Plot 4: Number of Ships in Simulation
axs[1, 0].plot(data.index, data["NumShips"], label="Ships", color='green')
axs[1, 0].set_xlabel("Steps")
axs[1, 0].set_ylabel("Number of Ships")
axs[1, 0].set_title("Ships in Simulation Over Time")
axs[1, 0].legend()

# Plot 5: Average Port Popularity (avg docked ships per port)
axs[1, 1].plot(data.index, data["AvgPortPopularity"], label="Avg Port Popularity", color='purple')
axs[1, 1].set_xlabel("Steps")
axs[1, 1].set_ylabel("Avg Docked Ships per Port")
axs[1, 1].set_title("Average Port Popularity")
axs[1, 1].legend()

# Plot 6: Number of Ports that Ban Scrubbers
axs[1, 2].plot(data.index, data["NumPortsBan"], label="Ports with Ban", color='red')
axs[1, 2].set_xlabel("Steps")
axs[1, 2].set_ylabel("Num Ports with Ban")
axs[1, 2].set_title("Ports Banning Scrubber Ships")
axs[1, 2].legend()

plt.tight_layout()
plt.savefig("results_10.png")
# plt.show()