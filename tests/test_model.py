import unittest
from src.model.model import Model
from src.agents.ship import Ship

class TestModel(unittest.TestCase):
    def setUp(self):
        """Set up test data."""
        self.model = Model(iterations=100, number_of_ships=2, ship_speed=0.01, num_scrubbers=0.5)

    def test_initialization(self):
        """Test if model initializes correctly."""
        self.assertEqual(self.model.iterations, 100)
        self.assertEqual(len(self.model.ships), 2)  # 2 ships per iteration due to implementation
        self.assertEqual(self.model.current_step, 0)
        self.assertEqual(len(self.model.trails), 0)

    def test_step(self):
        """Test if step updates correctly."""
        initial_positions = [(ship.pos_x, ship.pos_y) for ship in self.model.ships]
        self.model.step()
        final_positions = [(ship.pos_x, ship.pos_y) for ship in self.model.ships]
        
        # Check step counter increased
        self.assertEqual(self.model.current_step, 1)
        
        # Check positions changed
        self.assertNotEqual(initial_positions, final_positions)

    def test_trail_creation(self):
        """Test if trails are created for scrubber ships."""
        # Run one step
        self.model.step()
        
        # Count scrubber ships
        scrubber_ships = sum(1 for ship in self.model.ships if ship.scrubber_usage)
        
        # Check if trails were created for scrubber ships
        self.assertEqual(len(self.model.trails), scrubber_ships)

    def test_trail_cleanup(self):
        """Test if old trails are removed."""
        # Run for 60 steps to ensure we exceed the 50-step trail limit
        for _ in range(60):
            self.model.step()
            
        # Check that no trail is older than 50 steps
        for _, _, timestamp in self.model.trails:
            self.assertTrue(self.model.current_step - timestamp <= 50)
