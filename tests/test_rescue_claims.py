import unittest
from pathlib import Path
from collections import defaultdict
from openpyxl import load_workbook

from src.rescue_scheduling import (
    greedy_max_windows,
    weighted_interval_scheduling
)


class TestRescueClaims(unittest.TestCase):

    def test_tier_s_claims(self):
        dataset = Path(__file__).resolve().parents[1] / "cases.xlsx"

        self.assertTrue(dataset.exists(), "cases.xlsx not found")

        workbook = load_workbook(
            dataset, read_only=True, data_only=True
        )

        try:
            claims = {}

            for row in workbook["claims"].iter_rows(
                min_row=2, values_only=True
            ):
                case_id = row[0]
                claims[case_id] = {
                    "count": row[2],
                    "value": row[3]
                }

            self.assertEqual(len(claims), 20)

            windows_by_case = defaultdict(list)

            for row in workbook["windows"].iter_rows(
                min_row=2, values_only=True
            ):
                case_id, window_id, start, finish, value = row

                if case_id in claims:
                    windows_by_case[case_id].append({
                        "window_id": window_id,
                        "start": start,
                        "finish": finish,
                        "value": value
                    })
        finally:
            workbook.close()

        for case_id, expected in claims.items():
            windows = windows_by_case[case_id]

            with self.subTest(case_id=case_id):
                greedy = greedy_max_windows(windows)
                weighted = weighted_interval_scheduling(windows)

                self.assertEqual(
                    len(greedy),
                    expected["count"]
                )

                self.assertEqual(
                    sum(w["value"] for w in weighted),
                    expected["value"]
                )


if __name__ == "__main__":
    unittest.main()