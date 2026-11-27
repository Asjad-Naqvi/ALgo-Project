"""Portable fixtures for release ZIP parsing; no 83 MB course file needed."""
import csv
import hashlib
import io
import tempfile
import unittest
from pathlib import Path
from zipfile import ZipFile

from src.master_data import DatasetError
from src.master_release import load_master_release
from validator.dataset_schema import HEAD, TEXT


class TestMasterRelease(unittest.TestCase):
    def make_release(self, destination, corrupted=False):
        raw_files = {}
        for table, old_header in HEAD.items():
            columns = list(old_header) + ["group_no", "orig_case_id"]
            stream = io.StringIO(newline="")
            writer = csv.writer(stream)
            writer.writerow(columns)
            if table == "cases":
                record = {field: 0 for field in columns}
                record.update({
                    "case_id": "16-07", "group_seed": 8, "case_no": 7,
                    "tier": "S", "scenario": 1, "capacity": 20,
                    "group_no": 16, "orig_case_id": "8-07",
                })
                for field in columns:
                    if field in TEXT and field not in record:
                        record[field] = ""
                writer.writerow([record.get(k, "") for k in columns])
            if table == "windows":
                writer.writerow(["16-07", 1, 0, 10, 5, 16, "8-07"])
            raw_files[table + ".csv"] = stream.getvalue().encode("utf-8")
        checksums = "".join(
            f"{hashlib.sha256(data).hexdigest()}  {name}\n"
            for name, data in raw_files.items()
        )
        if corrupted:
            raw_files["windows.csv"] += b"corrupted"
        with ZipFile(destination, "w") as z:
            z.writestr("CHECKSUMS.txt", checksums)
            for name, data in raw_files.items():
                z.writestr(name, data)

    def test_accepts_group_number_distinct_from_group_seed(self):
        with tempfile.TemporaryDirectory() as directory:
            archive = Path(directory) / "sample.zip"
            self.make_release(archive)
            cases = load_master_release(archive, ["16-07"])
            self.assertEqual(list(cases), ["16-07"])
            self.assertEqual(cases["16-07"].metadata["group_no"], 16)
            self.assertEqual(cases["16-07"].metadata["group_seed"], 8)
            self.assertEqual(cases["16-07"].tables["windows"][0]["value"], 5)
            self.assertEqual(cases["16-07"].metadata["orig_case_id"], "8-07")

    def test_checksum_mismatch_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            archive = Path(directory) / "bad.zip"
            self.make_release(archive, corrupted=True)
            with self.assertRaisesRegex(DatasetError, "SHA-256 mismatch"):
                load_master_release(archive, ["16-07"])


if __name__ == "__main__":
    unittest.main()
