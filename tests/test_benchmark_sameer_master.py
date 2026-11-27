import unittest
from benchmarks.benchmark_sameer_master import (
    FIELDS, tasks, make_official_input, instance_label,
)


class TestMasterBenchmark(unittest.TestCase):
    def test_task_plan(self):
        self.assertEqual(len(list(tasks())), 55)
        self.assertEqual(len(list(tasks(smoke=True))), 11)
        self.assertIn('note', FIELDS)
        self.assertIn('master_release_v1', instance_label('matching'))

    def test_official_prefixes(self):
        dummy = {
            'windows': [dict(window_id=i, start=i, finish=i+1, value=2)
                        for i in range(300)],
            'incidents': [dict(alarm_id=i, tick=i//2, priority=8)
                          for i in range(1100)],
            'radio_text': 'A' * 5000,
            'patterns': {4:'AAAA', 8:'A'*8, 12:'A'*12,
                         20:'A'*20, 40:'A'*40},
            'report': ('B'*300, 'C'*310),
        }
        self.assertEqual(len(make_official_input(dummy, 'scheduling', 256)), 256)
        self.assertEqual(len(make_official_input(dummy, 'alarms', 1024)), 1024)
        self.assertEqual(tuple(map(len, make_official_input(dummy, 'matching', 4096))), (4096, 40))
        self.assertEqual(tuple(map(len, make_official_input(dummy, 'edit', 256))), (256, 256))
        self.assertEqual(len(make_official_input(dummy, 'compression', 4096)), 4096)
