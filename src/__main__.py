"""Run Operation LIFELINE from a directory of master CSVs."""

import argparse
import json
from pathlib import Path

from .campaign_engine import run_campaign
from .master_data import load_master


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("csv_directory", type=Path)
    parser.add_argument("case_id")
    parser.add_argument("--mode", choices=("primary", "baseline", "both"), default="primary")
    args = parser.parse_args(argv)

    try:
        cases = load_master(args.csv_directory)
        if args.case_id not in cases:
            raise ValueError(f"unknown case ID {args.case_id}")
        modes = ("primary", "baseline") if args.mode == "both" else (args.mode,)
        results = {mode: run_campaign(cases[args.case_id], mode) for mode in modes}
    except ValueError as error:
        parser.error(str(error))
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
