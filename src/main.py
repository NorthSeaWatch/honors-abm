import matplotlib.pyplot as plt
from model.model import Model

if __name__ == "__main__":
    my_experiment = Model(iterations=500, number_of_ships=20, num_scrubbers=0.3)
    my_experiment.run()
