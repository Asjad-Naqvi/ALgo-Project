"""Data pooling tests; deliberately do not run timed benchmarks."""

import csv
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from benchmarks.benchmark_sameer_pooled import (
    TIERS, build_pooled_inputs, choose_source_cases, make_pooled_input,
)


class TestPooledBenchmark(unittest.TestCase):
    def test_manifest_stratified_selection(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / 'manifest.csv'
            with path.open('w', encoding='utf-8', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=(
                    'case_id', 'tier', 'master_index', 'tier_index'
                ))
                writer.writeheader()
                for tier in TIERS:
                    for i in range(6):
                        writer.writerow(dict(case_id=f'{tier}-{i}', tier=tier,
                                             master_index=i, tier_index=1 + 7 * i))
            selected = choose_source_cases(path, per_tier=5)
            self.assertEqual(len([v for ids in selected.values() for v in ids]), 20)
            self.assertEqual(selected['S'][0], 'S-0')
            self.assertEqual(selected['X'][-1], 'X-4')

    def test_unique_ids_and_original_values(self):
        selected = {tier: [f'{tier}-{i}' for i in range(5)] for tier in TIERS}
        cases = {}
        for j, case_id in enumerate(cid for tier in TIERS for cid in selected[tier]):
            text = 'ABCDE_' * 900
            cases[case_id] = SimpleNamespace(tables={
                'windows': [dict(start=j, finish=j + 2, value=10 + j)],
                'incidents': [dict(tick=19 - j, priority=1 + (j % 10))],
                'radio_log': [dict(part=1, text=text)],
                'radio_reports': [dict(report_a='ABC' * 20,
                                       report_b='ADC' * 20)],
                'radio_patterns': [dict(pattern='A' * p) for p in (4, 8, 12, 20, 40)],
            })
        # Small fixture insufficient for longest windows/alarm prefixes: this
        # must be rejected, rather than silently fabricating extra records.
        with self.assertRaisesRegex(ValueError, 'Insufficient pooled windows'):
            build_pooled_inputs(cases, selected)
        # Extend the same 20 fixtures to validate the complete pooled shape.
        for case in cases.values():
            case.tables['windows'] *= 15
            case.tables['incidents'] *= 55
        pooled, sources = build_pooled_inputs(cases, selected)
        self.assertEqual(len(set(x['window_id'] for x in pooled['windows'])),
                         len(pooled['windows']))
        self.assertEqual(len(set(x['alarm_id'] for x in pooled['incidents'])),
                         len(pooled['incidents']))
        self.assertEqual([x['tick'] for x in pooled['incidents']],
                         sorted(x['tick'] for x in pooled['incidents']))
        self.assertEqual(len(make_pooled_input(pooled, 'matching', 4096)[0]), 4096)
        self.assertEqual(len(make_pooled_input(pooled, 'edit', 256)[0]), 256)
        self.assertEqual(len(sources), 5)


if __name__ == '__main__':
    unittest.main()
