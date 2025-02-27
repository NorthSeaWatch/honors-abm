class Model:
    def __init__(self):
        self.ships = []
    
    def add_ship(self, ship):
        "Add a ship to the model"
        self.ships.append(ship)
        
    def run(self):
        for ship in self.ships:
            ship.move()
            print(f"Ship {ship.imo_id} moved to {ship.position}")
            scrubber_water = ship.discharge_scrubber_water()
            print(f"Ship {ship.imo_id} discharged {scrubber_water} liters of scrubber water.")