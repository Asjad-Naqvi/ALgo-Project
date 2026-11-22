"""Read the course master CSVs without an Excel dependency."""

import csv
import hashlib
import re
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Mapping, Tuple, Union

from validator.dataset_schema import HEAD, TEXT

Cell = Union[str, int]
Row = Mapping[str, Cell]


class DatasetError(ValueError):
    """The release could not be verified or parsed."""


@dataclass(frozen=True)
class CaseData:
    case_id: str
    metadata: Row
    tables: Mapping[str, Tuple[Row, ...]]


def verify_sha256(path: Path, expected: str) -> str:
    """Verify the exact file named by the course checksum."""
    expected = expected.strip().lower()
    if not re.fullmatch(r"[0-9a-f]{64}", expected):
        raise DatasetError("Expected a 64-digit SHA-256 digest")
    digest = hashlib.sha256()
    try:
        with path.open("rb") as stream:
            for block in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(block)
    except OSError as error:
        raise DatasetError(f"{path}: {error}") from error
    if digest.hexdigest() != expected:
        raise DatasetError(f"{path}: SHA-256 mismatch")
    return expected


def _read_table(path: Path, columns):
    try:
        with path.open(encoding="utf-8-sig", newline="") as stream:
            reader = csv.reader(stream, strict=True)
            if next(reader, None) != columns:
                raise DatasetError(f"{path}: unexpected header")
            for values in reader:
                location = f"{path}:{reader.line_num}"
                if len(values) != len(columns):
                    raise DatasetError(f"{location}: expected {len(columns)} columns")
                row = {}
                for column, value in zip(columns, values):
                    if column in TEXT:
                        row[column] = value
                    elif re.fullmatch(r"-?[0-9]+", value):
                        row[column] = int(value)
                    else:
                        raise DatasetError(f"{location}: {column} must be an integer")
                yield location, MappingProxyType(row)
    except (OSError, UnicodeError, csv.Error) as error:
        raise DatasetError(f"{path}: {error}") from error


def load_master(directory: Path) -> Mapping[str, CaseData]:
    """Return immutable cases keyed by case ID in master cases.csv order."""
    metadata = {}
    for location, row in _read_table(directory / "cases.csv", HEAD["cases"]):
        case_id = row["case_id"]
        if case_id != f"{row['group_seed']}-{row['case_no']:02d}":
            raise DatasetError(f"{location}: case_id does not match seed and case number")
        if case_id in metadata:
            raise DatasetError(f"{location}: duplicate case_id {case_id}")
        metadata[case_id] = row
    if not metadata:
        raise DatasetError(f"{directory / 'cases.csv'}: no cases")

    tables = {case_id: defaultdict(list) for case_id in metadata}
    for name, columns in HEAD.items():
        if name == "cases":
            continue
        for location, row in _read_table(directory / f"{name}.csv", columns):
            case_id = row["case_id"]
            if case_id not in tables:
                raise DatasetError(f"{location}: unknown case_id {case_id}")
            tables[case_id][name].append(row)

    return MappingProxyType({
        case_id: CaseData(case_id, row, MappingProxyType({
            name: tuple(tables[case_id].get(name, ()))
            for name in HEAD if name != "cases"
        }))
        for case_id, row in metadata.items()
    })
