import unittest
from src.campaign_rules import get_blocked_waves


class TestCampaignRules(unittest.TestCase):

    def test_normal_day(self):
        self.assertEqual(get_blocked_waves(1, 4), [])

    def test_storm(self):
        self.assertEqual(get_blocked_waves(2, 4), [0])

    def test_wave_wrapping(self):
        self.assertEqual(get_blocked_waves(5, 3), [0])

    def test_all_waves_blocked(self):
        self.assertEqual(get_blocked_waves(6, 4), [0, 1, 2, 3])
        self.assertEqual(get_blocked_waves(7, 4), [0, 1, 2, 3])

    def test_invalid_day(self):
        with self.assertRaises(ValueError):
            get_blocked_waves(8, 4)

    def test_invalid_wave_count(self):
        with self.assertRaises(ValueError):
            get_blocked_waves(2, 0)


if __name__ == "__main__":
    unittest.main()