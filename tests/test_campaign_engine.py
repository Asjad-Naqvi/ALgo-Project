import unittest

from src.master_data import CaseData
from src.campaign_engine import (
    prepare_day,
    evaluate_local_day,
)


class TestCampaignEngine(unittest.TestCase):

    def setUp(self):
        self.case = CaseData(
            case_id="1-00",
            metadata={
                "target_0": 2,
                "target_1": 3,
                "target_2": 4,
                "capacity": 9,
            },
            tables={
                "waves": [
                    {"wave_no": 1, "road_no": 7},
                    {"wave_no": 2, "road_no": 9},
                    {"wave_no": 3, "road_no": 11},
                    {"wave_no": 4, "road_no": 13},
                ],
                "roads": [
                    {"road_no": 7, "minutes": 3},
                    {"road_no": 9, "minutes": 4},
                    {"road_no": 11, "minutes": 5},
                    {"road_no": 13, "minutes": 6},
                ],
                "crates": [
                    {"crate_id": 1, "cat": 3, "value": 10},
                    {"crate_id": 2, "cat": 0, "value": 20},
                    {"crate_id": 3, "cat": 2, "value": 30},
                ],
                "locations": [
                    {"loc_id": 0, "penalty": 0},
                    {"loc_id": 1, "penalty": 2},
                ],
                "windows": [
                    {
                        "window_id": 1,
                        "start": 0, "finish": 2, "value": 5
                    },
                    {
                        "window_id": 2,
                        "start": 2, "finish": 4, "value": 7
                    },
                    {
                        "window_id": 3,
                        "start": 1, "finish": 3, "value": 10
                    },
                    {
                        "window_id": 4,
                        "start": 4, "finish": 6, "value": 4
                    },
                ],
                "incidents": [
                    {"alarm_id": 1, "tick": 0, "priority": 4},
                    {"alarm_id": 2, "tick": 2, "priority": 8},
                ],
            },
        )

    def test_destinations(self):
        expected = [2, 3, 4, 2, 3, 4, 2]

        for day in range(1, 8):
            with self.subTest(day=day):
                inputs = prepare_day(self.case, day)
                self.assertEqual(
                    inputs["target"],
                    expected[day - 1]
                )

    def test_wave_closures(self):
        expected = [
            [],
            [1],
            [2],
            [3],
            [4],
            [1, 2, 3, 4],
            [1, 2, 3, 4],
        ]

        for day in range(1, 8):
            with self.subTest(day=day):
                inputs = prepare_day(self.case, day)
                self.assertEqual(
                    inputs["blocked_wave_numbers"],
                    expected[day - 1]
                )

        day2 = prepare_day(self.case, 2)
        self.assertEqual(day2["closed_road_nos"], [7])

        day6 = prepare_day(self.case, 6)
        self.assertEqual(
            day6["closed_road_nos"],
            [7, 9, 11, 13]
        )
        self.assertEqual(day6["open_roads"], [])

    def test_daily_adjustments(self):
        day2 = prepare_day(self.case, 2)
        day3 = prepare_day(self.case, 3)
        day4 = prepare_day(self.case, 4)
        day5 = prepare_day(self.case, 5)

        self.assertEqual(day2["roads"][0]["minutes"], 5)
        self.assertEqual(day2["crates"][0]["value"], 20)
        self.assertEqual(day3["crates"][1]["value"], 40)
        self.assertEqual(day4["locations"][1]["penalty"], 4)
        self.assertEqual(day5["crates"][2]["value"], 90)

    def test_loading_and_evacuation(self):
        for day in range(1, 7):
            self.assertTrue(
                prepare_day(self.case, day)["loading_allowed"]
            )

        day7 = prepare_day(self.case, 7)
        self.assertFalse(day7["loading_allowed"])
        self.assertTrue(day7["evacuation_only"])

    def test_windows_and_emergency_alarms(self):
        day1 = prepare_day(self.case, 1)
        day2 = prepare_day(self.case, 2)
        day5 = prepare_day(self.case, 5)

        self.assertEqual(
            [w["window_id"] for w in day1["windows"]],
            [1, 2, 3]
        )

        self.assertEqual(
            [w["window_id"] for w in day2["windows"]],
            [1, 2, 4]
        )

        self.assertEqual(len(day2["incidents"]), 3)
        self.assertEqual(day2["incidents"][1]["priority"], 9)
        self.assertEqual(day5["incidents"][1]["priority"], 10)

        # Original master-data records remain unchanged.
        self.assertEqual(
            len(self.case.tables["incidents"]), 2
        )
        self.assertEqual(
            self.case.tables["crates"][0]["value"], 10
        )

    def test_local_algorithm_integration(self):
        inputs = prepare_day(self.case, 1)

        heap_result = evaluate_local_day(inputs, "heap")
        scan_result = evaluate_local_day(inputs, "scan")

        self.assertEqual(heap_result, scan_result)
        self.assertEqual(heap_result["window_count"], 2)
        self.assertEqual(heap_result["window_value"], 12)
        self.assertEqual(
            heap_result["count_window_ids"], [1, 2]
        )
        self.assertEqual(
            [a["alarm_id"] for a in
             heap_result["alarm_dispatch"]],
            [1, 2]
        )


if __name__ == "__main__":
    unittest.main()