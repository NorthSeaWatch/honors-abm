import unittest
import math
from src.agents.ship import Ship

class TestShip(unittest.TestCase):
    def setUp(self):
        """Set up test data."""
        self.ship_with_scrubber = Ship(
            imo_id=1,
            pos_x=0.5,
            pos_y=0.5,
            angle=0,
            speed=0.01,
            ship_type="cargo",
            scrubber_usage=True
        )
        self.ship_without_scrubber = Ship(
            imo_id=2,
            pos_x=0.5,
            pos_y=0.5,
            angle=math.pi/2,
            speed=0.01,
            ship_type="passenger",
            scrubber_usage=False
        )

    def test_initialization(self):
        """Test if ship initializes correctly."""
        self.assertEqual(self.ship_with_scrubber.pos_x, 0.5)
        self.assertEqual(self.ship_with_scrubber.pos_y, 0.5)
        self.assertEqual(self.ship_with_scrubber.color, "red")
        self.assertEqual(self.ship_without_scrubber.color, "blue")

    def test_step(self):
        """Test if the ship moves correctly."""
        initial_pos = (self.ship_with_scrubber.pos_x, self.ship_with_scrubber.pos_y)
        self.ship_with_scrubber.step()
        final_pos = (self.ship_with_scrubber.pos_x, self.ship_with_scrubber.pos_y)
        
        # Position should change after step
        self.assertNotEqual(initial_pos, final_pos)

    def test_boundary_behavior(self):
        """Test if ship turns around at boundaries."""
        # Move ship to boundary
        self.ship_with_scrubber.pos_x = 1.1
        initial_angle = self.ship_with_scrubber.angle
        self.ship_with_scrubber.step()
        
        # Angle should change by approximately pi (180 degrees)
        angle_diff = abs(initial_angle - self.ship_with_scrubber.angle)
        self.assertAlmostEqual(angle_diff, math.pi, places=1)

    def test_discharge_scrubber_water(self):
        """Test scrubber water discharge."""
        self.assertEqual(self.ship_with_scrubber.discharge_scrubber_water(), 10)
        self.assertEqual(self.ship_without_scrubber.discharge_scrubber_water(), 0)

    def test_distance(self):
        """Test distance calculation between ships."""
        ship1 = Ship(1, 0, 0, 0, 0.01)
        ship2 = Ship(2, 3, 4, 0, 0.01)
        self.assertEqual(ship1.distance(ship2), 5.0)