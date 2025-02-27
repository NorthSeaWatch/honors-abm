import unittest
from src.agents.ship import Ship

class TestShip(unittest.TestCase):
    def setUp(self):
        """Set up test data."""
        self.ship_with_scrubber = Ship(1, ship_type="cargo", scrubber_usage=True, route=[(1, 1), (2, 2)], position=(0, 0))
        self.ship_without_scrubber = Ship(2, ship_type="cargo", scrubber_usage=False, route=[(1, 1)], position=(0, 0))

    def test_move(self):
        """Test if the ship moves correctly."""
        self.ship_with_scrubber.move()
        self.assertEqual(self.ship_with_scrubber.position, (1, 1))

    def test_discharge_scrubber_water(self):
        """Test if the ship discharges the correct amount of water if it uses a scrubber."""
        self.assertEqual(self.ship_with_scrubber.discharge_scrubber_water(), 10)
        self.assertEqual(self.ship_without_scrubber.discharge_scrubber_water(), 0)

    def test_repr(self):
        """Test the string representation of the ship."""
        self.assertEqual(repr(self.ship_with_scrubber), "Ship(id=1, type=cargo, position=(0, 0), scrubber_usage=True)")

if __name__ == "__main__":
    unittest.main()