import unittest
from src.campaign_rules import (
    get_blocked_waves,
    get_destination_index,
    is_loading_allowed,
    adjust_crate_value,
    adjust_road_minutes,
    adjust_location_penalty,
    is_window_available,
    add_emergency_alarm
)
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

    def test_destinations(self):
        expected = [0, 1, 2, 0, 1, 2, 0]

        for day in range(1, 8):
            self.assertEqual(
                get_destination_index(day),
                expected[day - 1]
            )

    def test_loading(self):
        for day in range(1, 7):
            self.assertTrue(is_loading_allowed(day))

        self.assertFalse(is_loading_allowed(7))

    def test_invalid_destination_day(self):
        with self.assertRaises(ValueError):
            get_destination_index(0)

    def test_crate_value_adjustments(self):
        self.assertEqual(adjust_crate_value(2, 3, 50), 100)
        self.assertEqual(adjust_crate_value(3, 0, 50), 100)
        self.assertEqual(adjust_crate_value(5, 2, 50), 150)

    def test_unchanged_crate_values(self):
        self.assertEqual(adjust_crate_value(1, 3, 50), 50)
        self.assertEqual(adjust_crate_value(4, 2, 50), 50)
        self.assertEqual(adjust_crate_value(7, 0, 50), 50)

    def test_road_time_adjustment(self):
        self.assertEqual(adjust_road_minutes(2, 10), 15)
        self.assertEqual(adjust_road_minutes(2, 11), 17)
        self.assertEqual(adjust_road_minutes(3, 10), 10)

    def test_location_penalties(self):
        self.assertEqual(adjust_location_penalty(4, 2), 4)
        self.assertEqual(adjust_location_penalty(4, 6), 12)
        self.assertEqual(adjust_location_penalty(4, 1), 1)
        self.assertEqual(adjust_location_penalty(3, 6), 6)

    def test_window_availability(self):
        self.assertFalse(is_window_available(1, 4))
        self.assertTrue(is_window_available(1, 5))
        self.assertFalse(is_window_available(3, 2))
        self.assertTrue(is_window_available(3, 3))

    def test_invalid_window_id(self):
        with self.assertRaises(ValueError):
            is_window_available(2, 0)

    def test_emergency_alarm_day2(self):
        incidents = [
            {"alarm_id": 1, "tick": 0, "priority": 5}
        ]

        result = add_emergency_alarm(2, incidents)

        self.assertEqual(len(result), 2)
        self.assertEqual(result[1]["priority"], 9)
        self.assertEqual(result[1]["tick"], 0)
        self.assertEqual(result[1]["alarm_id"], 2)

    def test_emergency_alarm_day5(self):
        result = add_emergency_alarm(5, [])

        self.assertEqual(result[0]["priority"], 10)
        self.assertEqual(result[0]["tick"], 0)

    def test_no_extra_alarm(self):
        self.assertEqual(add_emergency_alarm(3, []), [])

    def test_emergency_alarm_dispatch_integration(self):
        from src.campaign_rules import add_emergency_alarm
        from src.emergency_queue import dispatch_alarms

        original = [
            {"alarm_id": 1, "tick": 0, "priority": 3},
            {"alarm_id": 2, "tick": 2, "priority": 8}
        ]

        for day, expected_priority in [(2, 9), (5, 10)]:
            with self.subTest(day=day):
                updated = add_emergency_alarm(day, original)

                self.assertEqual(
                    [alarm["tick"] for alarm in updated],
                    [0, 0, 2]
                )

                result = dispatch_alarms(updated, "heap")

                self.assertEqual(len(result), 3)
                self.assertEqual(
                    result[0]["priority"],
                    expected_priority
                )
                self.assertEqual(
                    result[0]["release_tick"],
                    0
                )

                self.assertEqual(len(original), 2)

if __name__ == "__main__":
    unittest.main()