import unittest
from pathlib import Path
from openpyxl import load_workbook

from src.radio_logs import (
    naive_search,
    kmp_search,
    edit_distance_with_script,
)

from src.huffman_coding import (
    huffman_encode,
    huffman_decode,
    fixed_length_encode,
)


def load_radio_case(case_id):
    path = Path(__file__).resolve().parents[1] / "cases.xlsx"

    workbook = load_workbook(
        path, read_only=True, data_only=True
    )

    try:
        case_headers = next(
            workbook["cases"].iter_rows(
                max_row=1, values_only=True
            )
        )

        metadata = None

        for row in workbook["cases"].iter_rows(
            min_row=2, values_only=True
        ):
            if row[0] == case_id:
                metadata = dict(zip(case_headers, row))
                break

        if metadata is None:
            raise ValueError(f"Unknown case: {case_id}")

        parts = []

        for cid, part, text in workbook["radio_log"].iter_rows(
            min_row=2, values_only=True
        ):
            if cid == case_id:
                parts.append((part, text))

        parts.sort(key=lambda item: item[0])
        radio_text = "".join(text for _, text in parts)

        patterns = []

        for cid, number, pattern, count in (
            workbook["radio_patterns"].iter_rows(
                min_row=2, values_only=True
            )
        ):
            if cid == case_id:
                patterns.append((number, pattern, count))

        patterns.sort(key=lambda item: item[0])

        reports = None

        for cid, report_a, report_b in (
            workbook["radio_reports"].iter_rows(
                min_row=2, values_only=True
            )
        ):
            if cid == case_id:
                reports = (report_a, report_b)
                break

        return metadata, radio_text, patterns, reports

    finally:
        workbook.close()


class TestRadioWorkbook(unittest.TestCase):

    def test_pattern_counts(self):
        for case_id in ("1-00", "1-40", "1-49"):
            _, text, patterns, _ = load_radio_case(case_id)

            self.assertEqual(len(patterns), 6)

            for number, pattern, expected_count in patterns:
                with self.subTest(
                    case=case_id, pattern=number
                ):
                    naive = naive_search(text, pattern)
                    kmp = kmp_search(text, pattern)

                    self.assertEqual(kmp, naive)
                    self.assertEqual(
                        len(kmp), expected_count
                    )

    def test_huffman_trap_round_trip(self):
        _, text, _, _ = load_radio_case("1-49")

        encoded, codes = huffman_encode(text)
        fixed_bits, _ = fixed_length_encode(text)

        self.assertEqual(
            huffman_decode(encoded, codes), text
        )

        self.assertLessEqual(
            len(encoded), len(fixed_bits)
        )

    def test_edit_distance_workbook_claims(self):
        for case_id in ("1-40", "1-49"):
            metadata, _, _, reports = load_radio_case(
                case_id
            )

            self.assertIsNotNone(reports)
            source, target = reports

            distance, operations = edit_distance_with_script(
                source, target
            )

            characters = list(source)

            for operation in operations:
                index = operation["index"]
                action = operation["operation"]

                if action == "replace":
                    characters[index] = operation["character"]
                elif action == "insert":
                    characters.insert(
                        index, operation["character"]
                    )
                elif action == "delete":
                    characters.pop(index)

            with self.subTest(case=case_id):
                self.assertEqual(
                    distance, metadata["edit_bound"]
                )
                self.assertEqual(
                    len(operations), distance
                )
                self.assertEqual(
                    "".join(characters), target
                )


if __name__ == "__main__":
    unittest.main()