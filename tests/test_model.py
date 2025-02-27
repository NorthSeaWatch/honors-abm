import unittest
from io import StringIO
import sys
from src.model.model import Model
from src.agents.ship import Ship


class TestModel(unittest.TestCase):
    def setUp(self):
        """Set up test data."""
        self.model = Model()

        # Ships to add to the model
        self.ship_with_scrubber = Ship(1, ship_type="cargo", scrubber_usage=True, route=[(1, 1), (2, 2)], position=(0, 0))
        self.ship_without_scrubber = Ship(2, ship_type="cargo", scrubber_usage=False, route=[(1, 1)], position=(0, 0))

        # Adding ships to the model
        self.model.add_ship(self.ship_with_scrubber)
        self.model.add_ship(self.ship_without_scrubber)

    def test_add_ship(self):
        """Test if ships are added to the model correctly."""
        self.assertEqual(len(self.model.ships), 2)
        self.assertIn(self.ship_with_scrubber, self.model.ships)
        self.assertIn(self.ship_without_scrubber, self.model.ships)

    def test_run(self):
        """Test if the model runs correctly, moving ships and discharging water."""
        # Capture printed output
        captured_output = StringIO()
        sys.stdout = captured_output
        
        self.model.run()
        
        # Check if ship movements and scrubber water discharges are printed
        self.assertIn("Ship 1 moved to (1, 1)", captured_output.getvalue())
        self.assertIn("Ship 2 moved to (1, 1)", captured_output.getvalue())
        self.assertIn("Ship 1 discharged 10 liters of scrubber water", captured_output.getvalue())
        self.assertIn("Ship 2 discharged 0 liters of scrubber water", captured_output.getvalue())

        # Reset stdout
        sys.stdout = sys.__stdout__

    def test_ship_movement(self):
        """Test if ships move correctly within the model."""
        self.model.run()
        self.assertEqual(self.ship_with_scrubber.position, (1, 1))
        self.assertEqual(self.ship_without_scrubber.position, (1, 1))

    def test_ship_discharge(self):
        """Test if the ships discharge the correct amount of water after moving."""
        self.model.run()
        self.assertEqual(self.ship_with_scrubber.discharge_scrubber_water(), 10)
        self.assertEqual(self.ship_without_scrubber.discharge_scrubber_water(), 0)
        
if __name__ == "__main__":
    unittest.main()