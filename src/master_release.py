"""Selective reader for the course's LIFELINE master_release_v1 ZIP.

Unlike the Phase 1 workbook CSV reader, the release adds group_no and
orig_case_id. This reader verifies the bundled CSV checksums, preserves both
extra fields, and materializes only requested case IDs into CaseData objects.

Examples:
    from pathlib import Path
    from src.master_release import load_master_release
    cases = load_master_release(Path('archive.zip'), ['1-01', '1-40', '1-49'])
"""

import csv
import hashlib
import io
import re
from collections import defaultdict
from pathlib import Path
from types import MappingProxyType
from zipfile import ZipFile, BadZipFile

from src.master_data import CaseData, DatasetError
from validator.dataset_schema import HEAD, TEXT

_EXTRA = ("group_no", "orig_case_id")


def _checksums(archive):
    try:
        lines = archive.read("CHECKSUMS.txt").decode("utf-8").splitlines()
    except (KeyError, UnicodeError) as error:
        raise DatasetError("Missing or invalid CHECKSUMS.txt") from error

    expected = {}
    for line in lines:
        fields = line.split()
        if not fields:
            continue
        if len(fields) != 2 or not re.fullmatch(r"[0-9a-fA-F]{64}", fields[0]):
            raise DatasetError("Invalid SHA-256 manifest entry")
        digest, name = fields
        if name in expected:
            raise DatasetError(f"Duplicate SHA-256 manifest entry: {name}")
        expected[name] = digest.lower()

    csv_names = {name + ".csv" for name in HEAD}
    if set(expected) != csv_names:
        raise DatasetError("Manifest does not cover the expected 20 CSV tables")
    return expected


def _verify(archive, hashes):
    for name, expected in hashes.items():
        actual = hashlib.sha256()
        try:
            with archive.open(name) as binary:
                for block in iter(lambda: binary.read(1024 * 1024), b""):
                    actual.update(block)
        except KeyError as error:
            raise DatasetError(f"Missing release CSV: {name}") from error
        if actual.hexdigest() != expected:
            raise DatasetError(f"SHA-256 mismatch for {name}")


def load_master_release(path, case_ids):
    """Load a selected set of released case IDs after checking all 20 SHA-256s.

    Returns Mapping[str, CaseData]. Unknown IDs raise DatasetError.
    Request a modest set of case IDs; all-case materialization is deliberately
    unsupported because the master release contains millions of table rows.
    """
    case_ids = tuple(case_ids)
    if not case_ids or len(case_ids) != len(set(case_ids)):
        raise ValueError("Provide distinct, nonempty case IDs")
    if any(not isinstance(case_id, str) for case_id in case_ids):
        raise ValueError("Case IDs must be strings")
    requested = set(case_ids)
    meta = {}
    data = {case_id: defaultdict(list) for case_id in case_ids}
    try:
        with ZipFile(Path(path)) as archive:
            _verify(archive, _checksums(archive))
            # Scope the filter by passing an explicit local set rather than
            # writing attributes to _rows (safe for repeated calls).
            for row in _iter_selected(archive, "cases", requested):
                case_id = row["case_id"]
                if case_id in meta:
                    raise DatasetError(f"Duplicate released case: {case_id}")
                if case_id != f"{row['group_no']}-{row['case_no']:02d}":
                    raise DatasetError(f"Invalid released case ID: {case_id}")
                meta[case_id] = row
            missing = requested - set(meta)
            if missing:
                raise DatasetError(f"Requested case IDs not found: {sorted(missing)}")
            for name in HEAD:
                if name == "cases":
                    continue
                for row in _iter_selected(archive, name, requested):
                    if row["group_no"] != meta[row["case_id"]]["group_no"]:
                        raise DatasetError(f"Invalid group_no in {name} for {row['case_id']}")
                    data[row["case_id"]][name].append(row)
    except (OSError, ValueError, BadZipFile) as error:
        if isinstance(error, DatasetError):
            raise
        raise DatasetError(f"Cannot open master release: {error}") from error

    return MappingProxyType({
        case_id: CaseData(case_id, meta[case_id], MappingProxyType({
            name: tuple(data[case_id].get(name, ()))
            for name in HEAD if name != "cases"
        })) for case_id in case_ids
    })


def _iter_selected(archive, name, selected_ids):
    try:
        with archive.open(name + ".csv") as binary:
            with io.TextIOWrapper(binary, encoding="utf-8-sig", newline="") as text:
                reader = csv.reader(text, strict=True)
                header = next(reader, None)
                if header != list(HEAD[name]) + list(_EXTRA):
                    raise DatasetError(f"Unexpected release header for {name}")
                for values in reader:
                    if len(values) != len(header):
                        raise DatasetError(f"Wrong field count in {name} line {reader.line_num}")
                    if values[0] not in selected_ids:
                        continue
                    parsed = {}
                    for column, value in zip(header, values):
                        if column in TEXT or column == "orig_case_id":
                            parsed[column] = value
                        elif re.fullmatch(r"-?[0-9]+", value):
                            parsed[column] = int(value)
                        else:
                            raise DatasetError(f"Invalid integer {column} in {name}")
                    yield MappingProxyType(parsed)
    except (OSError, UnicodeError, csv.Error, KeyError) as error:
        raise DatasetError(f"Could not parse {name}: {error}") from error


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser(description="Verify release ZIP and load selected cases")
    p.add_argument("archive", type=Path)
    p.add_argument("--cases", nargs="+", default=["1-01", "1-08", "1-15", "1-40", "1-49"])
    args = p.parse_args()
    result = load_master_release(args.archive, args.cases)
    for cid, case in result.items():
        print(f"{cid}: tier={case.metadata['tier']}, "
              f"crates={len(case.tables['crates'])}, "
              f"windows={len(case.tables['windows'])}, "
              f"alarms={len(case.tables['incidents'])}")
    print("PASS: all 20 CSV checksums verified, selected cases loaded")
