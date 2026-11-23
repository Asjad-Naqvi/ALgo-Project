import unittest
import random
from collections import Counter
from heapq import heapify, heappop, heappush
from src.huffman_coding import (
    MinHeap,
    build_huffman_codes,
    huffman_encode,
    huffman_decode,
    fixed_length_encode,
    RADIO_ALPHABET
)

class TestHuffmanCoding(unittest.TestCase):

    def test_min_heap_order(self):
        heap = MinHeap()

        heap.push((5, 0, "A"))
        heap.push((2, 1, "B"))
        heap.push((8, 2, "C"))
        heap.push((1, 3, "D"))

        result = [heap.pop()[2] for _ in range(4)]

        self.assertEqual(result, ["D", "B", "A", "C"])

    def test_equal_frequencies(self):
        heap = MinHeap()

        heap.push((3, 2, "B"))
        heap.push((3, 1, "A"))

        self.assertEqual(heap.pop()[2], "A")
        self.assertEqual(heap.pop()[2], "B")

    def test_empty_heap(self):
        heap = MinHeap()

        with self.assertRaises(IndexError):
            heap.pop()
    def test_huffman_round_trip(self):
        text = "MAYDAY_MAYDAY-2026"

        encoded, codes = huffman_encode(text)
        decoded = huffman_decode(encoded, codes)

        self.assertEqual(decoded, text)

    def test_huffman_prefix_free(self):
        codes = build_huffman_codes("AAAAABBBCCD")

        for char1, code1 in codes.items():
            for char2, code2 in codes.items():
                if char1 != char2:
                    self.assertFalse(
                        code2.startswith(code1)
                    )

    def test_huffman_single_character(self):
        encoded, codes = huffman_encode("AAAAA")

        self.assertEqual(codes, {"A": "0"})
        self.assertEqual(encoded, "00000")
        self.assertEqual(
            huffman_decode(encoded, codes),
            "AAAAA"
        )

    def test_huffman_empty(self):
        encoded, codes = huffman_encode("")

        self.assertEqual(encoded, "")
        self.assertEqual(codes, {})
        self.assertEqual(huffman_decode("", {}), "")

    def test_huffman_optimal_known_example(self):
        text = (
            "A" * 5 +
            "B" * 9 +
            "C" * 12 +
            "D" * 13 +
            "E" * 16 +
            "F" * 45
        )

        encoded, codes = huffman_encode(text)

        # Known optimal Huffman cost: 224 bits.
        self.assertEqual(len(encoded), 224)
        self.assertEqual(huffman_decode(encoded, codes), text)

    def test_huffman_deterministic(self):
        text = "ABCDABCD"

        codes1 = build_huffman_codes(text)
        codes2 = build_huffman_codes(text)

        self.assertEqual(codes1, codes2)

    def test_huffman_invalid_data(self):
        with self.assertRaises(ValueError):
            huffman_decode("11", {"A": "0", "B": "10"})

        with self.assertRaises(ValueError):
            huffman_decode("1", {"A": "0", "B": "10"})

        with self.assertRaises(ValueError):
            huffman_decode("0", {"A": "0", "B": "01"})
    def test_fixed_length_encoding(self):
        text = RADIO_ALPHABET

        encoded, codes = fixed_length_encode(text)

        self.assertEqual(len(encoded), 38 * 6)
        self.assertEqual(huffman_decode(encoded, codes), text)

        for code in codes.values():
            self.assertEqual(len(code), 6)

    def test_fixed_length_invalid_input(self):
        with self.assertRaises(ValueError):
            fixed_length_encode("hello world")

        with self.assertRaises(TypeError):
            fixed_length_encode(123)

    def test_min_heap_randomized(self):
        rng = random.Random(2521)
        heap = MinHeap()

        items = [
            (rng.randint(1, 30), i, str(i))
            for i in range(100)
        ]

        for item in items:
            heap.push(item)

        actual = [heap.pop() for _ in range(len(items))]
        expected = sorted(items, key=lambda x: x[:2])

        self.assertEqual(actual, expected)

    def test_huffman_randomized_optimality(self):
        rng = random.Random(2521)

        for case_no in range(100):
            text = "".join(
                rng.choices(
                    RADIO_ALPHABET,
                    k=rng.randint(0, 250)
                )
            )

            encoded, codes = huffman_encode(text)
            fixed_bits, _ = fixed_length_encode(text)

            expected_bits = reference_optimal_bit_count(text)

            with self.subTest(case=case_no):
                self.assertEqual(
                    huffman_decode(encoded, codes),
                    text
                )

                self.assertEqual(
                    len(encoded),
                    expected_bits
                )

                self.assertLessEqual(
                    len(encoded),
                    len(fixed_bits)
                )

                for char1, code1 in codes.items():
                    for char2, code2 in codes.items():
                        if char1 != char2:
                            self.assertFalse(
                                code2.startswith(code1)
                            )

    def test_huffman_compression_advantage(self):
        text = "A" * 1000 + "B" * 100 + "C" * 10

        huffman_bits, codes = huffman_encode(text)
        fixed_bits, _ = fixed_length_encode(text)

        self.assertLess(len(huffman_bits), len(fixed_bits))
        self.assertEqual(
            huffman_decode(huffman_bits, codes),
            text
        )

if __name__ == "__main__":
    unittest.main()

def reference_optimal_bit_count(text):
    if not text:
        return 0

    frequencies = list(Counter(text).values())

    if len(frequencies) == 1:
        return len(text)

    heapify(frequencies)
    total_cost = 0

    while len(frequencies) > 1:
        a = heappop(frequencies)
        b = heappop(frequencies)

        combined = a + b
        total_cost += combined

        heappush(frequencies, combined)

    return total_cost