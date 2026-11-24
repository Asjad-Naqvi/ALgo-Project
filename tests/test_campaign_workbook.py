import unittest
from pathlib import Path
from openpyxl import load_workbook

from src.master_data import CaseData
from src.campaign_engine import (
    prepare_day,
    run_campaign,
)


def load_workbook_case(case_id):
    path = Path(__file__).resolve().parents[1] / "cases.xlsx"

    workbook = load_workbook(
        path, read_only=True, data_only=True
    )

    try:
        cases_sheet = workbook["cases"]
        headers = next(
            cases_sheet.iter_rows(max_row=1, values_only=True)
        )

        metadata = None

        for values in cases_sheet.iter_rows(
            min_row=2, values_only=True
        ):
            if values[0] == case_id:
                metadata = dict(zip(headers, values))
                break

        if metadata is None:
            raise ValueError(f"Case not found: {case_id}")

        tables = {}

        for name in (
            "crates", "locations", "roads",
            "waves", "windows", "incidents"
        ):
            sheet = workbook[name]

            columns = next(
                sheet.iter_rows(max_row=1, values_only=True)
            )

            tables[name] = []

            for values in sheet.iter_rows(
                min_row=2, values_only=True
            ):
                if values[0] == case_id:
                    tables[name].append(
                        dict(zip(columns, values))
                    )

        return CaseData(case_id, metadata, tables)

    finally:
        workbook.close()


class TestCampaignWorkbook(unittest.TestCase):

    def test_real_case_campaigns(self):
        case_ids = ["1-00", "1-01", "1-02"]

        for case_id in case_ids:
            with self.subTest(case_id=case_id):
                case = load_workbook_case(case_id)

                primary = run_campaign(case, "primary")
                baseline = run_campaign(case, "baseline")

                self.assertEqual(len(primary), 7)
                self.assertEqual(len(baseline), 7)

                for p, b in zip(primary, baseline):
                    day = p["day"]
                    inputs = prepare_day(case, day)

                    # Both routing methods must agree.
                    self.assertEqual(
                        p["route_cost"], b["route_cost"]
                    )
                    self.assertEqual(
                        p["status"], b["status"]
                    )
                    self.assertEqual(
                        p["end_location"], b["end_location"]
                    )

                    # Both queue implementations must agree.
                    self.assertEqual(
                        p["alarm_dispatch"],
                        b["alarm_dispatch"]
                    )

                    # Every alarm must be dispatched.
                    self.assertEqual(
                        len(p["alarm_dispatch"]),
                        len(inputs["incidents"])
                    )

                    # Capacity must never be exceeded.
                    self.assertLessEqual(
                        p["load_weight"],
                        inputs["capacity"]
                    )

                    # No loading on unreachable trips.
                    if p["status"] == "unreachable":
                        self.assertEqual(
                            p["selected_crates"], []
                        )
                        self.assertEqual(
                            p["load_value"], 0
                        )

                    # Day 7 is evacuation-only.
                    if day == 7:
                        self.assertEqual(
                            p["selected_crates"], []
                        )
                        self.assertEqual(
                            p["load_value"], 0
                        )

                    # One alarm can be handled per tick.
                    release_ticks = [
                        alarm["release_tick"]
                        for alarm in p["alarm_dispatch"]
                    ]

                    self.assertEqual(
                        len(release_ticks),
                        len(set(release_ticks))
                    )


if __name__ == "__main__":
    unittest.main()