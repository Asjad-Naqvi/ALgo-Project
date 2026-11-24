"""Reproducible synthetic pilot benchmarks for LIFELINE modules C/D/E.

Run from repository root:
    python3 -m benchmarks.benchmark_sameer --smoke
    python3 -m benchmarks.benchmark_sameer

The output is deliberately separate from the official master-CSV results.
"""

import argparse
import csv
import multiprocessing as mp
import random
import signal
import statistics
import time
import tracemalloc
from pathlib import Path

from src import emergency_queue, huffman_coding, radio_logs, rescue_scheduling
from tests.reference_scheduling import exhaustive_scheduling

SEED = 2521
LIMIT_SECONDS = 300
C_SIZES = (16, 32, 64, 128, 256)
D_SIZES = (64, 128, 256, 512, 1024)
E_SIZES = (256, 512, 1024, 2048, 4096)
EDIT_SIZES = (16, 32, 64, 128, 256)
C_EXACT_LIMIT = 18  # Matches the independent reference's supported limit.
FIELDS = (
    'module', 'experiment', 'algorithm', 'instance', 'size', 'size2',
    'time_s', 'time_iqr_s', 'ops', 'mem_bytes', 'status', 'note'
)


class CountedWindow(dict):
    def __init__(self, row, counter):
        super().__init__(row)
        self.counter = counter

    def __getitem__(self, key):
        self.counter[0] += 1
        return super().__getitem__(key)


def make_input(experiment, size):
    rng = random.Random(f'LIFELINE|2521|{experiment}|{size}')
    if experiment == 'scheduling':
        return [{
            'window_id': i + 1,
            'start': (start := rng.randrange(size * 2)),
            'finish': start + rng.randint(1, 20),
            'value': rng.randint(1, 100),
        } for i in range(size)]
    if experiment == 'alarms':
        # ~1.5 arriving alarms per tick => sustained backlog.
        return [{
            'alarm_id': i + 1, 'tick': (2 * i) // 3,
            'priority': rng.randint(1, 10),
        } for i in range(size)]
    if experiment == 'matching':
        lengths = {256: 4, 512: 8, 1024: 12, 2048: 20, 4096: 40}
        m = lengths[size]
        return ('A' * size, 'A' * (m - 1) + 'B')
    if experiment == 'edit':
        alphabet = 'ABC012'
        return (
            ''.join(rng.choices(alphabet, k=size)),
            ''.join(rng.choices(alphabet, k=size)),
        )
    if experiment == 'compression':
        alphabet = huffman_coding.RADIO_ALPHABET
        return ''.join(rng.choices(
            alphabet, weights=([65] + [1] * (len(alphabet) - 1)), k=size
        ))
    raise ValueError(f'Unknown experiment: {experiment}')


def tasks(smoke=False):
    cases = (
        ('C', 'scheduling', C_SIZES, ('greedy', 'weighted', 'exhaustive')),
        ('D', 'alarms', D_SIZES, ('heap', 'scan')),
        ('E', 'matching', E_SIZES, ('naive', 'kmp')),
        ('E', 'edit', EDIT_SIZES, ('full_dp', 'hirschberg')),
        ('E', 'compression', E_SIZES, ('huffman', 'fixed6')),
    )
    for module, experiment, sizes, algorithms in cases:
        for size in (sizes[:1] if smoke else sizes):
            for algorithm in algorithms:
                yield (module, experiment, algorithm, size)


def execute(experiment, algorithm, data):
    if experiment == 'scheduling':
        return {
            'greedy': rescue_scheduling.greedy_max_windows,
            'weighted': rescue_scheduling.weighted_interval_scheduling,
            'exhaustive': exhaustive_scheduling,
        }[algorithm](data)
    if experiment == 'alarms':
        return emergency_queue.dispatch_alarms(data, algorithm)
    if experiment == 'matching':
        return {
            'naive': radio_logs.naive_search,
            'kmp': radio_logs.kmp_search,
        }[algorithm](*data)
    if experiment == 'edit':
        return {
            'full_dp': radio_logs.edit_distance_with_script,
            'hirschberg': radio_logs.hirschberg_edit_script,
        }[algorithm](*data)
    if experiment == 'compression':
        return {
            'huffman': huffman_coding.huffman_encode,
            'fixed6': huffman_coding.fixed_length_encode,
        }[algorithm](data)
    raise ValueError(experiment)


def _apply_edits(source, edits):
    chars = list(source)
    for item in edits:
        position = item['index']
        if item['operation'] == 'insert':
            chars.insert(position, item['character'])
        elif item['operation'] == 'delete':
            chars.pop(position)
        elif item['operation'] == 'replace':
            chars[position] = item['character']
        else:
            raise AssertionError('Unexpected edit operation')
    return ''.join(chars)


def check_correctness(experiment, size):
    """Verify paired algorithms before measuring either one."""
    data = make_input(experiment, size)
    if experiment == 'scheduling':
        greedy = execute(experiment, 'greedy', data)
        weighted = execute(experiment, 'weighted', data)
        for chosen in (greedy, weighted):
            ordered = sorted(chosen, key=lambda w: w['start'])
            assert all(a['finish'] <= b['start'] for a, b in zip(ordered, ordered[1:]))
        if size <= C_EXACT_LIMIT:
            count, value = exhaustive_scheduling(data)
            assert len(greedy) == count
            assert sum(w['value'] for w in weighted) == value
    elif experiment == 'alarms':
        assert execute(experiment, 'heap', data) == execute(experiment, 'scan', data)
    elif experiment == 'matching':
        assert execute(experiment, 'naive', data) == execute(experiment, 'kmp', data)
    elif experiment == 'edit':
        a, b = data
        results = [execute(experiment, algorithm, data)
                   for algorithm in ('full_dp', 'hirschberg')]
        assert results[0][0] == results[1][0]
        for distance, edits in results:
            assert len(edits) == distance and _apply_edits(a, edits) == b
    elif experiment == 'compression':
        bits, codebook = execute(experiment, 'huffman', data)
        fixed, _ = execute(experiment, 'fixed6', data)
        assert huffman_coding.huffman_decode(bits, codebook) == data
        assert len(bits) <= len(fixed)


def matching_checks(text, pattern, use_kmp):
    """Count character comparisons in a separately instrumented search."""
    if not use_kmp:
        comparisons = 0
        matches = []
        for i in range(len(text) - len(pattern) + 1):
            for j in range(len(pattern)):
                comparisons += 1
                if text[i + j] != pattern[j]:
                    break
            else:
                matches.append(i)
        assert matches == radio_logs.naive_search(text, pattern)
        return comparisons

    comparisons = 0
    m = len(pattern)
    lps = [0] * m
    j, i = 0, 1
    while i < m:
        comparisons += 1
        if pattern[i] == pattern[j]:
            j += 1
            lps[i] = j
            i += 1
        elif j:
            j = lps[j - 1]
        else:
            i += 1
    positions = []
    i = j = 0
    while i < len(text):
        comparisons += 1
        if text[i] == pattern[j]:
            i += 1
            j += 1
        if j == m:
            positions.append(i - m)
            j = lps[j - 1]
        elif i < len(text):
            comparisons += 1
            if text[i] != pattern[j]:
                if j:
                    j = lps[j - 1]
                else:
                    i += 1
    assert positions == radio_logs.kmp_search(text, pattern)
    return comparisons


def count_ops(experiment, algorithm, data):
    """Return (count, unit). Counting occurs outside timing and memory runs."""
    if experiment == 'scheduling':
        if algorithm == 'exhaustive':
            return 1 << len(data), 'enumerated_subsets'
        counter = [0]
        wrapped = [CountedWindow(row, counter) for row in data]
        execute(experiment, algorithm, wrapped)
        return counter[0], 'window_field_reads'
    if experiment == 'alarms':
        cls = (emergency_queue.MaxHeap if algorithm == 'heap'
               else emergency_queue.LinearScanQueue)
        original = cls.higher_priority
        counter = [0]
        def counted(self, a, b):
            counter[0] += 1
            return original(self, a, b)
        cls.higher_priority = counted
        try:
            execute(experiment, algorithm, data)
        finally:
            cls.higher_priority = original
        return counter[0], 'priority_comparisons'
    if experiment == 'matching':
        return matching_checks(*data, use_kmp=(algorithm == 'kmp')), 'character_comparisons'
    if experiment == 'edit':
        if algorithm == 'full_dp':
            return len(data[0]) * len(data[1]), 'dp_cell_updates'
        return '', 'not_instrumented'
    if experiment == 'compression':
        if algorithm == 'fixed6':
            return len(data) + len(huffman_coding.RADIO_ALPHABET), 'symbol_encodes_plus_codebook_entries'
        sigma = len(set(data))
        return 2 * len(data) + 4 * sigma - 2, 'symbol_visits_plus_heap_push_pop'  # nonempty cases
    raise ValueError(experiment)


def _timeout_handler(_signum, _frame):
    raise TimeoutError('300-second experiment limit exceeded')


def _worker(connection, task):
    _module, experiment, algorithm, size = task
    signal.signal(signal.SIGALRM, _timeout_handler)
    signal.alarm(LIMIT_SECONDS)
    try:
        data = make_input(experiment, size)  # Input generation excluded from timing.
        execute(experiment, algorithm, data)  # Discard one warm-up.
        measurements = []
        for _ in range(5):
            start = time.perf_counter()
            execute(experiment, algorithm, data)
            measurements.append(time.perf_counter() - start)
        # Tracemalloc changes execution speed; measure peak memory separately.
        tracemalloc.start()
        try:
            execute(experiment, algorithm, data)
            peak_bytes = tracemalloc.get_traced_memory()[1]
        finally:
            tracemalloc.stop()
        ops, unit = count_ops(experiment, algorithm, data)
        measurements.sort()
        payload = dict(
            status='OK', time_s=f'{statistics.median(measurements):.9f}',
            time_iqr_s=f'{(measurements[3] - measurements[1]):.9f}',
            ops=ops, mem_bytes=peak_bytes, note=f'ops_unit={unit}; warmup=1; measured=5; mem=tracemalloc_peak',
        )
    except TimeoutError:
        payload = dict(status='DNF', note='actual 300s experiment timeout')
    except Exception as error:
        payload = dict(status='ERROR', note=f'{type(error).__name__}: {error}')
    finally:
        signal.alarm(0)
    try:
        connection.send(payload)
    finally:
        connection.close()


def run_task(task):
    module, experiment, algorithm, size = task
    row = dict.fromkeys(FIELDS, '')
    row.update(module=module, experiment=experiment, algorithm=algorithm,
               instance=f'synthetic_seed_{SEED}_{experiment}_{size}',
               size=size, size2=(
                   len(make_input(experiment, size)[1]) if experiment == 'matching' else
                   size if experiment == 'edit' else ''
               ))
    if experiment == 'scheduling' and algorithm == 'exhaustive' and size > C_EXACT_LIMIT:
        row.update(status='DNF', note=f'predefined exact cap n>{C_EXACT_LIMIT}; no timeout claimed')
        return row
    ctx = mp.get_context('spawn')
    receiving, sending = ctx.Pipe(duplex=False)
    proc = ctx.Process(target=_worker, args=(sending, task))
    proc.start()
    sending.close()
    proc.join(LIMIT_SECONDS + 10)
    if proc.is_alive():
        proc.terminate()
        proc.join()
        row.update(status='DNF', note='forced process stop after 310s')
    elif receiving.poll():
        row.update(receiving.recv())
    else:
        row.update(status='ERROR', note=f'worker exited without result; exitcode={proc.exitcode}')
    receiving.close()
    return row


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--smoke', action='store_true', help='one size per experiment; diagnostic only')
    args = parser.parse_args()
    destination = Path('results') / ('results_sameer_smoke.csv' if args.smoke else 'results_sameer_synthetic.csv')
    destination.parent.mkdir(parents=True, exist_ok=True)
    cases = list(tasks(args.smoke))
    checked = set()
    with destination.open('w', newline='', encoding='utf-8') as stream:
        writer = csv.DictWriter(stream, fieldnames=FIELDS)
        writer.writeheader()
        for index, task in enumerate(cases, 1):
            _module, experiment, algorithm, size = task
            if (experiment, size) not in checked:
                check_correctness(experiment, size)
                checked.add((experiment, size))
            row = run_task(task)
            row['note'] = 'synthetic pilot; ' + row['note']
            writer.writerow(row)
            stream.flush()
            print(f'{index:02d}/{len(cases)} {experiment:<12} n={size:<5} {algorithm:<12} {row["status"]}', flush=True)
    print(f'Wrote {destination}')


if __name__ == '__main__':
    main()
