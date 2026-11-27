"""C/D/E pooled benchmarks from seed-1 sampled, course-release cases.

Usage (repository root):
    python3 -m benchmarks.benchmark_sameer_pooled --smoke
    python3 -m benchmarks.benchmark_sameer_pooled

This intentionally composes a new, labeled benchmark input from original
rows/characters of 20 manifest-selected cases (first five per S/M/L/X tier).
It is neither a full-case benchmark nor a claim about every sampled case.
"""

import argparse
import csv
import hashlib
import json
from collections import deque
from pathlib import Path

from benchmarks.benchmark_sameer_master import (
    tasks, check_correctness, run_task, PATTERN_SIZES, E_SIZES,
)
from benchmarks.benchmark_sameer import FIELDS
from src.master_release import load_master_release

TIERS = ('S', 'M', 'L', 'X')
PER_TIER = 5
DEFAULT_MANIFEST = Path('results/master_sampling_manifest.csv')
DEFAULT_RESULT = Path('results/results_sameer_master_pooled.csv')
DEFAULT_SMOKE = Path('results/results_sameer_master_pooled_smoke.csv')
DEFAULT_PROVENANCE = Path('results/sameer_pooled_provenance.json')


def choose_source_cases(manifest_path, per_tier=PER_TIER):
    """Take the first `per_tier` manifest entries from each tier in master order."""
    selected = {tier: [] for tier in TIERS}
    seen = set()
    with Path(manifest_path).open(encoding='utf-8-sig', newline='') as stream:
        reader = csv.DictReader(stream)
        required = {'case_id', 'tier', 'tier_index', 'master_index'}
        if not required.issubset(reader.fieldnames or ()):
            raise ValueError('Sampling manifest has missing fields')
        for row in reader:
            tier = row['tier']
            case_id = row['case_id']
            tier_index = int(row['tier_index'])
            if tier not in selected or case_id in seen or tier_index < 1 or (tier_index - 1) % 7:
                raise ValueError('Invalid seed-1 sampling manifest row')
            seen.add(case_id)
            if len(selected[tier]) < per_tier:
                selected[tier].append(case_id)
    if any(len(v) != per_tier for v in selected.values()):
        raise ValueError('Insufficient sampled cases in one or more tiers')
    return selected


def round_robin(sequences):
    """Yield from each case in turn, preserving within-case order."""
    active = deque(iter(seq) for seq in sequences if seq)
    while active:
        iterator = active.popleft()
        try:
            item = next(iterator)
        except StopIteration:
            continue
        yield item
        active.append(iterator)


def build_pooled_inputs(cases, selected):
    """Compose official-row inputs with balanced initial contributions.

    Windows/alarms need new unique IDs because source cases reuse local IDs.
    Original window times, values, alarm ticks/priorities are unchanged.
    Text/report characters are unmodified but deliberately interleaved.
    """
    ids = [case_id for tier in TIERS for case_id in selected[tier]]
    windows_by_case = []
    incidents_by_case = []
    texts = []
    reports_a = []
    reports_b = []
    for case_id in ids:
        case = cases[case_id]
        windows_by_case.append([
            dict(start=row['start'], finish=row['finish'], value=row['value'],
                 source_case_id=case_id)
            for row in case.tables['windows']
        ])
        incidents_by_case.append([
            dict(tick=row['tick'], priority=row['priority'],
                 source_case_id=case_id)
            for row in case.tables['incidents']
        ])
        texts.append(''.join(row['text'] for row in sorted(
            case.tables['radio_log'], key=lambda r: r['part'])))
        report_rows = case.tables['radio_reports']
        if len(report_rows) != 1:
            raise ValueError(f'Expected one report pair for {case_id}')
        reports_a.append(report_rows[0]['report_a'])
        reports_b.append(report_rows[0]['report_b'])

    windows = [dict(row, window_id=i) for i, row in enumerate(
        round_robin(windows_by_case), start=1)]
    incidents = list(round_robin(incidents_by_case))
    # Sort by original arrival tick; stable order breaks ties deterministically.
    incidents.sort(key=lambda row: row['tick'])
    for i, row in enumerate(incidents, start=1):
        row['alarm_id'] = i

    # Different native patterns of each specified length are selected from the
    # sample, without generating or modifying pattern characters.
    pattern_sources = {
        4: selected['S'][0],
        8: selected['M'][0],
        12: selected['L'][0],
        20: selected['X'][0],
        40: selected['X'][1],
    }
    patterns = {}
    for length, case_id in pattern_sources.items():
        values = [row['pattern'] for row in cases[case_id].tables['radio_patterns']
                  if len(row['pattern']) == length]
        if len(values) != 1:
            raise ValueError(f'Expected one native length-{length} pattern in {case_id}')
        patterns[length] = values[0]

    pooled = {
        'windows': windows,
        'incidents': incidents,
        'radio_text': ''.join(round_robin(texts)),
        'patterns': patterns,
        'report': (''.join(round_robin(reports_a)),
                   ''.join(round_robin(reports_b))),
    }
    min_lengths = {'windows': 256, 'incidents': 1024, 'radio_text': 4096}
    for name, threshold in min_lengths.items():
        if len(pooled[name]) < threshold:
            raise ValueError(f'Insufficient pooled {name}: {len(pooled[name])}')
    if min(len(x) for x in pooled['report']) < 256:
        raise ValueError('Insufficient pooled edit reports')
    return pooled, pattern_sources


def make_pooled_input(pooled, experiment, size):
    if experiment == 'scheduling':
        return pooled['windows'][:size]
    if experiment == 'alarms':
        return pooled['incidents'][:size]
    if experiment == 'matching':
        m = PATTERN_SIZES[E_SIZES.index(size)]
        return pooled['radio_text'][:size], pooled['patterns'][m]
    if experiment == 'edit':
        return pooled['report'][0][:size], pooled['report'][1][:size]
    if experiment == 'compression':
        return pooled['radio_text'][:size]
    raise ValueError(f'Unknown experiment: {experiment}')


def sha256_file(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--archive', type=Path, default=Path.home() / 'Downloads/archive.zip')
    parser.add_argument('--manifest', type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument('--out', type=Path)
    parser.add_argument('--provenance', type=Path, default=DEFAULT_PROVENANCE)
    parser.add_argument('--smoke', action='store_true')
    args = parser.parse_args()

    selected = choose_source_cases(args.manifest)
    ids = [cid for tier in TIERS for cid in selected[tier]]
    print(f'Verifying 20 release CSV checksums and loading {len(ids)} sampled cases ...', flush=True)
    cases = load_master_release(args.archive, ids)
    pooled, pattern_sources = build_pooled_inputs(cases, selected)

    provenance = {
        'release': 'master_release_v1',
        'archive_sha256': sha256_file(args.archive),
        'manifest_sha256': sha256_file(args.manifest),
        'sampling': 'seed=1; tier_index=1+7k (zero-based); first five selected per tier',
        'selected_by_tier': selected,
        'selection_count': len(ids),
        'pooling': 'round-robin over original case rows/characters; no synthetic source values',
        'transforms': ('windows: unique reindexed window_id; alarms: tick-sort and unique reindexed alarm_id; '
                       'texts and report pairs: character-interleaved; patterns: native sampled-case values'),
        'pattern_source_by_length': pattern_sources,
        'pool_lengths': {
            'windows': len(pooled['windows']),
            'incidents': len(pooled['incidents']),
            'radio_text': len(pooled['radio_text']),
            'report_a': len(pooled['report'][0]),
            'report_b': len(pooled['report'][1]),
        },
        'methodology_note': ('These are pooled prefixes made from 20 sampled cases, '
                             'not whole-case measurements and not a sample of all 518 manifest cases.'),
    }
    args.provenance.parent.mkdir(parents=True, exist_ok=True)
    args.provenance.write_text(json.dumps(provenance, indent=2) + '\n', encoding='utf-8')

    output = args.out or (DEFAULT_SMOKE if args.smoke else DEFAULT_RESULT)
    output.parent.mkdir(parents=True, exist_ok=True)
    planned = list(tasks(args.smoke))
    checked = set()
    with output.open('w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        for index, task in enumerate(planned, start=1):
            _module, experiment, algorithm, size = task
            data = make_pooled_input(pooled, experiment, size)
            if (experiment, size) not in checked:
                check_correctness(experiment, data)
                checked.add((experiment, size))
            row = run_task(task, data)
            row['instance'] = f'master_release_v1:sampled20:round_robin:{experiment}'
            row['note'] = row['note'].replace('official master prefix', 'sampled master pool')
            row['note'] = 'sampled_seed1_20cases; round_robin_pooled_prefix; ' + row['note']
            if experiment == 'matching':
                m = PATTERN_SIZES[E_SIZES.index(size)]
                row['note'] += f'; pattern_case={pattern_sources[m]}'
            writer.writerow(row)
            f.flush()
            print(f'{index:02d}/{len(planned)} {experiment:<12} n={size:<5} '
                  f'{algorithm:<11} {row["status"]}', flush=True)
    print(f'Wrote {output}')
    print(f'Wrote {args.provenance}')


if __name__ == '__main__':
    main()
