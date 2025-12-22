import unittest

class TestCapitalAdequacy(unittest.TestCase):
    def test_basic_functionality(self):
        # Test with realistic data
        # Example: debt-to-equity ratio calculation
        equity = 100000
        debt = 50000
        expected_ratio = debt / equity
        self.assertEqual(calculate_debt_to_equity_ratio(debt, equity), expected_ratio)

    def test_edge_case_minimal_values(self):
        # Test with minimal values
        equity = 1
        debt = 0
        expected_ratio = debt / equity
        self.assertEqual(calculate_debt_to_equity_ratio(debt, equity), expected_ratio)

    def test_edge_case_extreme_values(self):
        # Test with extreme values
        equity = 1e12
        debt = 1e12
        expected_ratio = debt / equity
        self.assertEqual(calculate_debt_to_equity_ratio(debt, equity), expected_ratio)

    def test_missing_data(self):
        # Test handling of missing data
        with self.assertRaises(ValueError):
            calculate_debt_to_equity_ratio(None, 100000)

if __name__ == '__main__':
    unittest.main()
