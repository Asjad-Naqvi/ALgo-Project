import unittest

from src.cable import plan_cable
from src.inventory import exhaustive_load, greedy_load, optimal_load
from src.routing import plan_routes


class TestAliInvariants(unittest.TestCase):
    def setUp(self):
        self.locations = [{"loc_id": i, "penalty": p} for i, p in enumerate((0, 4, 0, 0))]
        self.roads = [
            {"road_no": i, "u": u, "v": v, "minutes": minutes, "cable": cable}
            for i, (u, v, minutes, cable) in enumerate(
                ((0, 1, 1, 3), (1, 2, 1, 4), (0, 2, 7, 8), (2, 3, 1, 1))
            )
        ]

    def test_destination_penalties_and_closures(self):
        for baseline in (False, True):
            result = plan_routes(self.locations, self.roads, 0, 2, [3], baseline=baseline)
            self.assertEqual(result.cheapest_path, (0, 1, 2))
            self.assertEqual(result.cheapest_cost, 6)
            self.assertEqual(result.fewest_roads_path, (0, 2))
            self.assertEqual(result.reachable_ids, {0, 1, 2})

    def test_cable_spans_open_hq_component(self):
        open_roads = self.roads[:3]
        for baseline in (False, True):
            result = plan_cable(open_roads, {0, 1, 2}, baseline=baseline)
            self.assertEqual(result.road_ids, (0, 1))
            self.assertEqual(result.total_cost, 7)
            self.assertEqual(plan_cable([], {0}, baseline=baseline).road_ids, ())
            with self.assertRaises(ValueError):
                plan_cable(open_roads, {0, 1, 2, 3}, baseline=baseline)

    def test_load_respects_capacity_and_matches_reference(self):
        crates = [{"crate_id": i, "weight": w, "value": v}
                  for i, w, v in ((1, 10, 60), (2, 20, 100), (3, 30, 120))]
        exact = optimal_load(crates, 50)
        greedy = greedy_load(crates, 50)
        self.assertEqual(exact, exhaustive_load(crates, 50))
        self.assertEqual(exact.total_value, 220)
        self.assertEqual(greedy.total_value, 160)
        for result in (exact, greedy):
            self.assertEqual(result.total_weight, sum(crates[i - 1]["weight"] for i in result.crate_ids))
            self.assertLessEqual(result.total_weight, 50)
