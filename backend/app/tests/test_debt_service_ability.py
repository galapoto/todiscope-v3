import unittest

class TestDebtServiceAbility(unittest.TestCase):
    def test_basic_functionality(self):
        # Test with realistic data
        # Example: debt service coverage ratio calculation
        cash_flow = 100000
        debt_service = 50000
        expected_ratio = cash_flow / debt_service
        self.assertEqual(calculate_debt_service_coverage_ratio(cash_flow, debt_service), expected_ratio)

    def test_edge_case_minimal_values(self):
        # Test with minimal values
        cash_flow = 1
        debt_service = 1
        expected_ratio = cash_flow / debt_service
        self.assertEqual(calculate_debt_service_coverage_ratio(cash_flow, debt_service), expected_ratio)

    def test_edge_case_extreme_values(self):
        # Test with extreme values
        cash_flow = 1e12
        debt_service = 1e6
        expected_ratio = cash_flow / debt_service
        self.assertEqual(calculate_debt_service_coverage_ratio(cash_flow, debt_service), expected_ratio)

    def test_missing_data(self):
        # Test handling of missing data
        with self.assertRaises(ValueError):
            calculate_debt_service_coverage_ratio(None, 50000)

if __name__ == '__main__':
    unittest.main()
