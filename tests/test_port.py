import unittest
from src.destination.port import Port

class TestPort(unittest.TestCase):
    def setUp(self):
        """
        Set up test data
        """
        self.port_1 = Port(port_id=123, port_name = 'Amsterdam', max_capacity='M', current_capacity=0)
        self.port_2 = Port(port_id=321, port_name = 'Rotterdam', max_capacity='L', current_capacity=0)

    
    def test_max_capacity(self):
        """
        Test if the values of port capacities are correct for Medium and Large
        """
        self.assertEqual(self.port_1.max_capacity_filter(), 30)
        self.assertEqual(self.port_2.max_capacity_filter(), 60)


    def test_repr(self):
        """
        Test the string representation of the port.
        """
        self.assertEqual(repr(self.port_1), 'Port (id: 123,name: Amsterdam,max capacity: 30, current_capacity: 0)')

if __name__ == '__main__':
    unittest.main()