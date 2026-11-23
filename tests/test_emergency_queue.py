import unittest
import random
from src.emergency_queue import MaxHeap
from src.emergency_queue import (
    MaxHeap,
    LinearScanQueue,
    dispatch_alarms
)


class TestEmergencyQueue(unittest.TestCase):

    def test_priority_order(self):
        heap = MaxHeap()

        heap.push({"alarm_id": 1, "tick": 0, "priority": 3})
        heap.push({"alarm_id": 2, "tick": 0, "priority": 9})
        heap.push({"alarm_id": 3, "tick": 0, "priority": 5})

        self.assertEqual(
            [heap.pop()["alarm_id"] for _ in range(3)],
            [2, 3, 1]
        )

    def test_arrival_tie(self):
        heap = MaxHeap()

        heap.push({"alarm_id": 1, "tick": 5, "priority": 8})
        heap.push({"alarm_id": 2, "tick": 2, "priority": 8})

        self.assertEqual(heap.pop()["alarm_id"], 2)

    def test_alarm_id_tie(self):
        heap = MaxHeap()

        heap.push({"alarm_id": 7, "tick": 0, "priority": 9})
        heap.push({"alarm_id": 3, "tick": 0, "priority": 9})

        self.assertEqual(heap.pop()["alarm_id"], 3)

    def test_empty_heap(self):
        heap = MaxHeap()
        self.assertIsNone(heap.pop())
    def test_heap_vs_linear_scan(self):
        incidents = [
            {"alarm_id": 1, "tick": 0, "priority": 3},
            {"alarm_id": 2, "tick": 0, "priority": 9},
            {"alarm_id": 3, "tick": 1, "priority": 8}
        ]

        heap_result = dispatch_alarms(incidents, "heap")
        scan_result = dispatch_alarms(incidents, "scan")

        self.assertEqual(heap_result, scan_result)
        self.assertEqual(
            [a["alarm_id"] for a in heap_result],
            [2, 3, 1]
        )

    def test_alarm_arrival_time(self):
        incidents = [
            {"alarm_id": 1, "tick": 3, "priority": 5}
        ]

        result = dispatch_alarms(incidents)

        self.assertEqual(result[0]["release_tick"], 3)

    def test_dispatch_priority_ties(self):
        incidents = [
            {"alarm_id": 7, "tick": 0, "priority": 9},
            {"alarm_id": 3, "tick": 0, "priority": 9}
        ]

        result = dispatch_alarms(incidents)

        self.assertEqual(
            [a["alarm_id"] for a in result],
            [3, 7]
        )

    def test_empty_dispatch(self):
        self.assertEqual(dispatch_alarms([]), [])

    def test_invalid_incidents(self):
        with self.assertRaises(ValueError):
            dispatch_alarms([
                {"alarm_id": 1, "tick": 0, "priority": 11}
            ])

        with self.assertRaises(ValueError):
            dispatch_alarms([
                {"alarm_id": 1, "tick": 2, "priority": 5},
                {"alarm_id": 2, "tick": 1, "priority": 8}
            ])

    def test_randomized_dispatch(self):
        rng = random.Random(2521)

        for case_no in range(60):
            incidents = []
            tick = 0

            for alarm_id in range(1, rng.randint(5, 35)):
                tick += rng.randint(0, 3)

                incidents.append({
                    "alarm_id": alarm_id,
                    "tick": tick,
                    "priority": rng.randint(1, 10)
                })

            expected = reference_dispatch(incidents)

            with self.subTest(case=case_no):
                self.assertEqual(
                    dispatch_alarms(incidents, "heap"),
                    expected
                )

                self.assertEqual(
                    dispatch_alarms(incidents, "scan"),
                    expected
                )

    def test_no_early_dispatch(self):
        incidents = [
            {"alarm_id": 1, "tick": 5, "priority": 10},
            {"alarm_id": 2, "tick": 8, "priority": 9}
        ]

        result = dispatch_alarms(incidents)

        for alarm in result:
            self.assertGreaterEqual(
                alarm["release_tick"],
                alarm["arrival_tick"]
            )

        self.assertEqual(
            [a["release_tick"] for a in result],
            [5, 8]
        )

    def test_duplicate_alarm_ids(self):
        incidents = [
            {"alarm_id": 1, "tick": 0, "priority": 5},
            {"alarm_id": 1, "tick": 1, "priority": 8}
        ]

        with self.assertRaises(ValueError):
            dispatch_alarms(incidents)

if __name__ == "__main__":
    unittest.main()

def reference_dispatch(incidents):
    pending = []
    released = []
    index = 0
    tick = 0

    while index < len(incidents) or pending:
        while (
            index < len(incidents)
            and incidents[index]["tick"] <= tick
        ):
            pending.append(incidents[index])
            index += 1

        if pending:
            best = min(
                pending,
                key=lambda a: (
                    -a["priority"],
                    a["tick"],
                    a["alarm_id"]
                )
            )

            pending.remove(best)

            released.append({
                "release_tick": tick,
                "alarm_id": best["alarm_id"],
                "arrival_tick": best["tick"],
                "priority": best["priority"]
            })

        tick += 1

    return released