
"""Export seven-day results from the verified Master CSV release."""

import argparse
import csv
import json
from pathlib import Path

from src.master_release import load_master_release
from src.campaign_engine import prepare_day, run_campaign


CASE_IDS = ["1-01", "1-08", "1-15", "1-40", "1-49"]

FIELDS = [
    "case_id", "tier", "mode", "day",
    "origin", "target", "end_location", "status",
    "route_cost", "cheapest_path", "fewest_roads_path",
    "load_weight", "load_value", "selected_crates",
    "window_count", "window_value",
    "count_window_ids", "value_window_ids",
    "alarm_count", "last_alarm_release_tick",
    "closed_road_nos",
]


def export_campaign(archive, output, case_ids):
    cases = load_master_release(archive, case_ids)

    output.parent.mkdir(parents=True, exist_ok=True)
    rows = []

    for case_id in case_ids:
        case = cases[case_id]

        primary = run_campaign(case, "primary")
        baseline = run_campaign(case, "baseline")

        if len(primary) != 7 or len(baseline) != 7:
            raise AssertionError("Campaign must have seven days")

        # Both exact routing algorithms must agree.
        for p, b in zip(primary, baseline):
            if (p["status"], p["route_cost"], p["end_location"]) != (
                b["status"], b["route_cost"], b["end_location"]
            ):
                raise AssertionError(
                    f"Routing disagreement: {case_id}, day {p['day']}"
                )

            if p["alarm_dispatch"] != b["alarm_dispatch"]:
                raise AssertionError(
                    f"Alarm disagreement: {case_id}, day {p['day']}"
                )

        for mode, daily_results in (
            ("primary", primary),
            ("baseline", baseline),
        ):
            for result in daily_results:
                day = result["day"]

                inputs = prepare_day(
                    case, day, origin=result["origin"]
                )

                alarms = result["alarm_dispatch"]

                if len(alarms) != len(inputs["incidents"]):
                    raise AssertionError(
                        f"Undispatched alarms: {case_id}, day {day}"
                    )

                if result["load_weight"] > inputs["capacity"]:
                    raise AssertionError("Truck capacity exceeded")

                if day == 7 or result["status"] == "unreachable":
                    if result["selected_crates"] or result["load_value"]:
                        raise AssertionError("Invalid cargo loading")

                rows.append({
                    "case_id": case_id,
                    "tier": case.metadata["tier"],
                    "mode": mode,
                    "day": day,
                    "origin": result["origin"],
                    "target": result["target"],
                    "end_location": result["end_location"],
                    "status": result["status"],
                    "route_cost": result["route_cost"],
                    "cheapest_path": json.dumps(
                        result["cheapest_path"]
                    ),
                    "fewest_roads_path": json.dumps(
                        result["fewest_roads_path"]
                    ),
                    "load_weight": result["load_weight"],
                    "load_value": result["load_value"],
                    "selected_crates": json.dumps(
                        result["selected_crates"]
                    ),
                    "window_count": result["window_count"],
                    "window_value": result["window_value"],
                    "count_window_ids": json.dumps(
                        result["count_window_ids"]
                    ),
                    "value_window_ids": json.dumps(
                        result["value_window_ids"]
                    ),
                    "alarm_count": len(alarms),
                    "last_alarm_release_tick": (
                        alarms[-1]["release_tick"] if alarms else ""
                    ),
                    "closed_road_nos": json.dumps(
                        result["closed_road_nos"]
                    ),
                })

            print(f"{case_id} / {mode}: 7 days verified")

    with output.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)

    print(f"\nPASS: {len(rows)} campaign records exported")
    print(f"Output: {output}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--archive",
        type=Path,
        default=Path.home() / "Downloads" / "archive.zip",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("results/results_sameer_master_campaign.csv"),
    )
    parser.add_argument(
        "--cases", nargs="+", default=CASE_IDS
    )

    args = parser.parse_args()
    export_campaign(args.archive, args.out, args.cases)
