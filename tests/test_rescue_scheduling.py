import unittest
import random
from tests.reference_scheduling import exhaustive_scheduling
from src.rescue_scheduling import greedy_max_windows
from src.rescue_scheduling import (
    greedy_max_windows,
    weighted_interval_scheduling
)

class TestRescueScheduling(unittest.TestCase):

    def test_normal_scheduling(self):
        windows = [
            {"window_id": 1, "start": 1, "finish": 4, "value": 30},
            {"window_id": 2, "start": 3, "finish": 5, "value": 50},
            {"window_id": 3, "start": 4, "finish": 7, "value": 40},
            {"window_id": 4, "start": 7, "finish": 9, "value": 60}
        ]

        result = greedy_max_windows(windows)

        ids = [w["window_id"] for w in result]
        self.assertEqual(ids, [1, 3, 4])

    def test_empty_windows(self):
        self.assertEqual(greedy_max_windows([]), [])

    def test_touching_windows(self):
        windows = [
            {"window_id": 1, "start": 0, "finish": 5, "value": 10},
            {"window_id": 2, "start": 5, "finish": 10, "value": 20}
        ]

        result = greedy_max_windows(windows)
        self.assertEqual(len(result), 2)

    def test_finish_time_tie(self):
        windows = [
            {"window_id": 7, "start": 0, "finish": 2, "value": 10},
            {"window_id": 2, "start": 0, "finish": 2, "value": 20},
            {"window_id": 3, "start": 2, "finish": 4, "value": 30}
        ]

        result = greedy_max_windows(windows)
        self.assertEqual(
            [w["window_id"] for w in result],
            [2, 3]
        )

    def test_invalid_window(self):
        windows = [
            {"window_id": 1, "start": 5, "finish": 3, "value": 10}
        ]

        with self.assertRaises(ValueError):
            greedy_max_windows(windows)

    def test_weighted_scheduling(self):
        windows = [
            {"window_id": 1, "start": 1, "finish": 4, "value": 30},
            {"window_id": 2, "start": 3, "finish": 5, "value": 50},
            {"window_id": 3, "start": 4, "finish": 7, "value": 40},
            {"window_id": 4, "start": 7, "finish": 9, "value": 60}
        ]

        result = weighted_interval_scheduling(windows)

        self.assertEqual(
            [w["window_id"] for w in result],
            [1, 3, 4]
        )
        self.assertEqual(
            sum(w["value"] for w in result),
            130
        )

    def test_weighted_high_value(self):
        windows = [
            {"window_id": 1, "start": 0, "finish": 2, "value": 30},
            {"window_id": 2, "start": 2, "finish": 4, "value": 30},
            {"window_id": 3, "start": 0, "finish": 4, "value": 100}
        ]

        result = weighted_interval_scheduling(windows)

        self.assertEqual(
            [w["window_id"] for w in result],
            [3]
        )

    def test_weighted_empty(self):
        self.assertEqual(weighted_interval_scheduling([]), [])

    def test_weighted_touching(self):
        windows = [
            {"window_id": 1, "start": 0, "finish": 5, "value": 20},
            {"window_id": 2, "start": 5, "finish": 10, "value": 30}
        ]

        result = weighted_interval_scheduling(windows)

        self.assertEqual(
            sum(w["value"] for w in result),
            50
        )
    def test_greedy_vs_exhaustive(self):
        windows = [
            {"window_id": 1, "start": 1, "finish": 4, "value": 30},
            {"window_id": 2, "start": 3, "finish": 5, "value": 50},
            {"window_id": 3, "start": 4, "finish": 7, "value": 40},
            {"window_id": 4, "start": 7, "finish": 9, "value": 60}
        ]

        optimal_count, _ = exhaustive_scheduling(windows)
        greedy_result = greedy_max_windows(windows)

        self.assertEqual(len(greedy_result), optimal_count)

    def test_weighted_vs_exhaustive(self):
        windows = [
            {"window_id": 1, "start": 0, "finish": 2, "value": 30},
            {"window_id": 2, "start": 2, "finish": 4, "value": 30},
            {"window_id": 3, "start": 0, "finish": 4, "value": 100}
        ]

        _, optimal_value = exhaustive_scheduling(windows)
        dp_result = weighted_interval_scheduling(windows)

        self.assertEqual(
            sum(w["value"] for w in dp_result),
            optimal_value
        )
    def test_randomized_against_exhaustive(self):
        rng = random.Random(2521)

        for case_no in range(60):
            n = rng.randint(0, 10)
            windows = []

            for window_id in range(1, n + 1):
                start = rng.randint(0, 40)
                finish = start + rng.randint(1, 15)
                value = rng.randint(1, 100)

                windows.append({
                    "window_id": window_id,
                    "start": start,
                    "finish": finish,
                    "value": value
                })

            optimal_count, optimal_value = exhaustive_scheduling(windows)

            greedy_result = greedy_max_windows(windows)
            dp_result = weighted_interval_scheduling(windows)

            with self.subTest(case=case_no):
                self.assertEqual(
                    len(greedy_result),
                    optimal_count
                )

                self.assertEqual(
                    sum(w["value"] for w in dp_result),
                    optimal_value
                )

                for result in (greedy_result, dp_result):
                    ordered = sorted(
                        result,
                        key=lambda w: (w["start"], w["finish"])
                    )

                    ids = [w["window_id"] for w in ordered]
                    self.assertEqual(len(ids), len(set(ids)))

                    for i in range(1, len(ordered)):
                        self.assertLessEqual(
                            ordered[i - 1]["finish"],
                            ordered[i]["start"]
                        )
if __name__ == "__main__":
    unittest.main()