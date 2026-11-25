import unittest

from src.master_data import CaseData
from src.campaign_engine import (
    prepare_day,
    evaluate_local_day,
    run_campaign
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

class TestFullCampaign(unittest.TestCase):

    def setUp(self):
        self.case = CaseData(
            case_id="1-00",
            metadata={
                "target_0": 1,
                "target_1": 2,
                "target_2": 2,
                "capacity": 50,
            },
            tables={
                "locations": [
                    {"loc_id": 0, "penalty": 0},
                    {"loc_id": 1, "penalty": 0},
                    {"loc_id": 2, "penalty": 0},
                ],
                "roads": [
                    {
                        "road_no": 0,
                        "u": 0, "v": 1, "minutes": 2, "cable": 2
                    },
                    {
                        "road_no": 1,
                        "u": 1, "v": 2, "minutes": 2, "cable": 3
                    },
                    {
                        "road_no": 2,
                        "u": 0, "v": 2, "minutes": 8, "cable": 8
                    },
                ],
                "waves": [
                    {"wave_no": 1, "road_no": 1},
                    {"wave_no": 2, "road_no": 2},
                ],
                "crates": [
                    {
                        "crate_id": 1, "cat": 0,
                        "weight": 10, "value": 60
                    },
                    {
                        "crate_id": 2, "cat": 0,
                        "weight": 20, "value": 100
                    },
                    {
                        "crate_id": 3, "cat": 0,
                        "weight": 30, "value": 120
                    },
                ],
                "windows": [],
                "incidents": [],
            },
        )

    def test_primary_vs_baseline(self):
        primary = run_campaign(self.case, "primary")
        baseline = run_campaign(self.case, "baseline")

        self.assertEqual(len(primary), 7)
        self.assertEqual(len(baseline), 7)

        # Classic knapsack counterexample.
        self.assertEqual(primary[0]["load_value"], 220)
        self.assertEqual(baseline[0]["load_value"], 160)

        # Both routing algorithms find optimal costs.
        for p, b in zip(primary, baseline):
            self.assertEqual(p["route_cost"], b["route_cost"])
            self.assertEqual(p["status"], b["status"])
            self.assertEqual(p["cable_cost"], b["cable_cost"])
        self.assertEqual(primary[0]["cable_road_ids"], [0, 1])
        self.assertEqual(primary[0]["cable_cost"], 5)

    def test_each_day_starts_at_hq(self):
        results = run_campaign(self.case)

        # Day 5 finishes at location 2.
        self.assertEqual(results[4]["end_location"], 2)

        # All closure waves activate on Day 6.
        # Location 2 becomes disconnected.
        self.assertEqual(results[5]["status"], "unreachable")
        self.assertEqual(results[5]["origin"], 0)
        self.assertEqual(results[5]["end_location"], 0)
        self.assertEqual(results[5]["cable_road_ids"], [0])
        self.assertEqual(results[5]["reachable_ids"], [0, 1])
        self.assertEqual(results[5]["selected_crates"], [])

        self.assertTrue(all(day["origin"] == 0 for day in results))
        self.assertEqual(results[6]["cheapest_path"], [0, 1])

    def test_day7_no_loading_on_reachable_route(self):
        case = CaseData(
            case_id=self.case.case_id,
            metadata={
                "target_0": 0,
                "target_1": 1,
                "target_2": 1,
                "capacity": 50,
            },
            tables=self.case.tables,
        )

        results = run_campaign(case)

        day7 = results[6]

        self.assertEqual(day7["status"], "completed")
        self.assertEqual(day7["cheapest_path"], [0])
        self.assertFalse(day7["loading_allowed"])
        self.assertEqual(day7["selected_crates"], [])
        self.assertEqual(day7["load_value"], 0)

    def test_invalid_campaign_mode(self):
        with self.assertRaises(ValueError):
            run_campaign(self.case, "unknown")
