import random
import unittest

from src.radio_logs import (
    naive_search,
    compute_lps,
    kmp_search,
    edit_distance_with_script,
    hirschberg_edit_script
)

class TestRadioLogs(unittest.TestCase):

    def test_normal_search(self):
        self.assertEqual(
            naive_search("ABCABC", "ABC"),
            [0, 3]
        )

    def test_overlapping_matches(self):
        self.assertEqual(
            naive_search("ABABABA", "ABA"),
            [0, 2, 4]
        )

    def test_pattern_not_found(self):
        self.assertEqual(
            naive_search("ABCDEFG", "XYZ"),
            []
        )

    def test_pattern_longer_than_text(self):
        self.assertEqual(
            naive_search("ABC", "ABCDE"),
            []
        )

    def test_empty_pattern(self):
        with self.assertRaises(ValueError):
            naive_search("ABC", "")


    def test_lps_array(self):
        self.assertEqual(
            compute_lps("ABABCABAB"),
            [0, 0, 1, 2, 0, 1, 2, 3, 4]
        )

    def test_kmp_normal(self):
        self.assertEqual(
            kmp_search("ABCABCABC", "ABC"),
            [0, 3, 6]
        )

    def test_kmp_overlapping(self):
        self.assertEqual(
            kmp_search("AAAAA", "AAA"),
            [0, 1, 2]
        )

    def test_kmp_edge_cases(self):
        self.assertEqual(kmp_search("", "ABC"), [])
        self.assertEqual(kmp_search("ABC", "ABCDE"), [])
        self.assertEqual(kmp_search("ABC", "XYZ"), [])

        with self.assertRaises(ValueError):
            kmp_search("ABC", "")

    def test_kmp_randomized(self):
        rng = random.Random(2521)
        alphabet = "ABC_01"

        for case_no in range(100):
            text = "".join(
                rng.choices(alphabet, k=rng.randint(0, 100))
            )
            pattern = "".join(
                rng.choices(alphabet, k=rng.randint(1, 15))
            )

            with self.subTest(case=case_no):
                self.assertEqual(
                    kmp_search(text, pattern),
                    naive_search(text, pattern)
                )
    def test_edit_distance_normal(self):
        distance, operations = edit_distance_with_script(
            "KITTEN", "SITTING"
        )

        self.assertEqual(distance, 3)
        self.assertEqual(len(operations), 3)

    def test_edit_distance_identical(self):
        distance, operations = edit_distance_with_script(
            "ABC", "ABC"
        )

        self.assertEqual(distance, 0)
        self.assertEqual(operations, [])

    def test_edit_distance_empty(self):
        self.assertEqual(
            edit_distance_with_script("", "ABC")[0], 3
        )
        self.assertEqual(
            edit_distance_with_script("ABC", "")[0], 3
        )

    def test_edit_distance_replacement(self):
        distance, _ = edit_distance_with_script(
            "ABC", "AXC"
        )

        self.assertEqual(distance, 1)

    def test_edit_script_reconstruction(self):
        cases = [
            ("ABC", "AXC"),
            ("ABC", "AC"),
            ("AC", "ABC"),
            ("KITTEN", "SITTING"),
            ("", "ABC"),
            ("ABC", "")
        ]

        for source, target in cases:
            distance, operations = edit_distance_with_script(
                source, target
            )

            characters = list(source)

            for operation in operations:
                index = operation["index"]
                action = operation["operation"]

                if action == "replace":
                    characters[index] = operation["character"]
                elif action == "delete":
                    characters.pop(index)
                elif action == "insert":
                    characters.insert(
                        index, operation["character"]
                    )

            with self.subTest(source=source, target=target):
                self.assertEqual("".join(characters), target)
                self.assertEqual(len(operations), distance)
    def test_edit_distance_randomized(self):
        rng = random.Random(2521)
        alphabet = "ABC012"

        for case_no in range(100):
            source = "".join(
                rng.choices(alphabet, k=rng.randint(0, 15))
            )
            target = "".join(
                rng.choices(alphabet, k=rng.randint(0, 15))
            )

            expected = reference_edit_distance(source, target)
            distance, operations = edit_distance_with_script(
                source, target
            )

            characters = list(source)

            for op in operations:
                index = op["index"]

                if op["operation"] == "replace":
                    characters[index] = op["character"]
                elif op["operation"] == "insert":
                    characters.insert(index, op["character"])
                elif op["operation"] == "delete":
                    characters.pop(index)

            with self.subTest(case=case_no):
                self.assertEqual(distance, expected)
                self.assertEqual(len(operations), distance)
                self.assertEqual("".join(characters), target)


    def test_hirschberg_known_example(self):
        distance, operations = hirschberg_edit_script(
            "KITTEN", "SITTING"
        )

        self.assertEqual(distance, 3)
        self.assertEqual(len(operations), 3)

        self.assertEqual(
            apply_edit_script("KITTEN", operations),
            "SITTING"
        )

    def test_hirschberg_empty_inputs(self):
        cases = [
            ("", "", 0),
            ("", "ABC", 3),
            ("ABC", "", 3),
        ]

        for source, target, expected in cases:
            with self.subTest(source=source, target=target):
                distance, operations = hirschberg_edit_script(
                    source, target
                )

                self.assertEqual(distance, expected)
                self.assertEqual(
                    apply_edit_script(source, operations),
                    target
                )

        with self.assertRaises(TypeError):
            hirschberg_edit_script(123, "ABC")

    def test_hirschberg_reconstruction(self):
        cases = [
            ("ABC", "AXC"),
            ("ABC", "AC"),
            ("AC", "ABC"),
            ("ABAB", "BABA"),
            ("AAAAAA", "BAAABA"),
        ]

        for source, target in cases:
            distance, operations = hirschberg_edit_script(
                source, target
            )

            with self.subTest(source=source, target=target):
                self.assertEqual(
                    apply_edit_script(source, operations),
                    target
                )
                self.assertEqual(len(operations), distance)

    def test_hirschberg_randomized(self):
        rng = random.Random(2521)
        alphabet = "ABC012"

        for case_no in range(100):
            source = "".join(
                rng.choices(alphabet, k=rng.randint(0, 30))
            )
            target = "".join(
                rng.choices(alphabet, k=rng.randint(0, 30))
            )

            full_distance, _ = edit_distance_with_script(
                source, target
            )

            distance, operations = hirschberg_edit_script(
                source, target
            )

            with self.subTest(case=case_no):
                self.assertEqual(distance, full_distance)
                self.assertEqual(len(operations), distance)
                self.assertEqual(
                    apply_edit_script(source, operations),
                    target
                )

    def test_hirschberg_asymmetric_input(self):
        source = "A" * 3000
        target = "B"

        distance, operations = hirschberg_edit_script(
            source, target
        )

        self.assertEqual(distance, 3000)
        self.assertEqual(
            apply_edit_script(source, operations),
            target
        )
if __name__ == "__main__":
    unittest.main()

def reference_edit_distance(a, b):
    n, m = len(a), len(b)
    dp = [[0] * (m + 1) for _ in range(n + 1)]

    for i in range(n + 1):
        dp[i][0] = i

    for j in range(m + 1):
        dp[0][j] = j

    for i in range(1, n + 1):
        for j in range(1, m + 1):
            cost = 0 if a[i - 1] == b[j - 1] else 1

            dp[i][j] = min(
                dp[i - 1][j] + 1,
                dp[i][j - 1] + 1,
                dp[i - 1][j - 1] + cost
            )

    return dp[n][m]


def apply_edit_script(source, operations):
    characters = list(source)

    for op in operations:
        index = op["index"]

        if op["operation"] == "replace":
            characters[index] = op["character"]

        elif op["operation"] == "insert":
            characters.insert(index, op["character"])

        elif op["operation"] == "delete":
            characters.pop(index)

    return "".join(characters)