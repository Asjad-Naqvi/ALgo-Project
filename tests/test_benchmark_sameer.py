import unittest

from benchmarks.benchmark_sameer import (
    C_SIZES, D_SIZES, E_SIZES, EDIT_SIZES, FIELDS,
    check_correctness, make_input, tasks,
)


class TestBenchmarkSameer(unittest.TestCase):
    def test_shapes_and_schema(self):
        self.assertEqual(len(FIELDS), 12)
        self.assertEqual(len(tuple(tasks())), 55)
        self.assertEqual(len(tuple(tasks(smoke=True))), 11)
        for experiment, sizes in (
            ('scheduling', C_SIZES),
            ('alarms', D_SIZES),
            ('matching', E_SIZES),
            ('edit', EDIT_SIZES),
            ('compression', E_SIZES),
        ):
            data = make_input(experiment, sizes[0])
            self.assertEqual(data, make_input(experiment, sizes[0]))
            if experiment in ('scheduling', 'alarms', 'compression'):
                self.assertEqual(len(data), sizes[0])
            elif experiment == 'edit':
                self.assertEqual(len(data[0]), sizes[0])
                self.assertEqual(len(data[1]), sizes[0])
            else:
                self.assertEqual(len(data[0]), sizes[0])

    def test_small_inputs_agree(self):
        for experiment, size in (
            ('scheduling', C_SIZES[0]),
            ('alarms', D_SIZES[0]),
            ('matching', E_SIZES[0]),
            ('edit', EDIT_SIZES[0]),
            ('compression', E_SIZES[0]),
        ):
            with self.subTest(experiment=experiment):
                check_correctness(experiment, size)


if __name__ == '__main__':
    unittest.main()
