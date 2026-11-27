"""Export reproducible tier-stratified master-data sampling."""

import csv
import io
import zipfile
from pathlib import Path

ARCHIVE = Path.home() / "Downloads" / "archive.zip"
OUTPUT = Path("results/master_sampling_manifest.csv")

TIERS = ("S", "M", "L", "X")
FIELDS = (
    "case_id",
    "tier",
    "master_index",
    "tier_index",
    "group_no",
    "orig_case_id",
)


def main():
    with zipfile.ZipFile(ARCHIVE) as archive:
        with archive.open("cases.csv") as stream:
            reader = csv.DictReader(
                io.TextIOWrapper(stream, encoding="utf-8-sig")
            )
            master = list(reader)

    selected = []

    for tier in TIERS:
        tier_rows = [
            (index, row)
            for index, row in enumerate(master)
            if row["tier"] == tier
        ]

        for tier_index in range(1, len(tier_rows), 7):
            master_index, row = tier_rows[tier_index]

            selected.append({
                "case_id": row["case_id"],
                "tier": tier,
                "master_index": master_index,
                "tier_index": tier_index,
                "group_no": row["group_no"],
                "orig_case_id": row["orig_case_id"],
            })

        print(
            f"Tier {tier}: {len(tier_rows)} available, "
            f"{len(tier_rows[1::7])} selected"
        )

    assert len(master) == 3622
    assert len(selected) == 518
    assert len({r["case_id"] for r in selected}) == 518

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)

    with OUTPUT.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(selected)

    print(f"\nPASS: {len(selected)} sampled cases exported")
    print(f"Output: {OUTPUT}")


if __name__ == "__main__":
    main()
