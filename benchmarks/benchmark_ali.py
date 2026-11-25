"""Run seed-1 development benchmarks with python -m benchmarks.benchmark_ali."""

import argparse
import csv
import json
import platform
import random
import statistics
import subprocess
import sys
import time
import tracemalloc
from pathlib import Path

from src.cable import plan_cable
from src.inventory import greedy_load, optimal_load
from src.routing import plan_routes

SERIES = (
    ("A", "inventory", ("knapsack", "ratio_greedy"), (16, 32, 64, 128, 256)),
    ("B", "routing", ("dijkstra", "bellman_ford"), (32, 64, 128, 256, 512)),
    ("F", "cable", ("kruskal", "prim"), (32, 64, 128, 256, 512)),
)
FIELDS = ("module", "experiment", "algorithm", "instance", "size", "size2",
          "time_s", "time_iqr_s", "ops", "mem_bytes", "status", "note")


def make_input(size):
    rng = random.Random(f"LIFELINE|1|{size}")
    crates = [{"crate_id": i + 1, "weight": rng.randint(1, 20),
               "value": rng.randint(10, 100)} for i in range(size)]
    locations = [{"loc_id": i, "penalty": rng.choice((0, 1, 2, 4, 6))}
                 for i in range(size)]
    pairs = {(rng.randrange(v), v) for v in range(1, size)}
    while len(pairs) < 2 * size:
        pairs.add(tuple(sorted(rng.sample(range(size), 2))))
    roads = [{"road_no": i, "u": u, "v": v, "minutes": rng.randint(1, 60),
              "cable": rng.randint(1, 100)} for i, (u, v) in enumerate(sorted(pairs))]
    rng.shuffle(locations)
    rng.shuffle(roads)
    return crates, locations, roads


def measure(module, algorithm, size):
    crates, locations, roads = make_input(size)
    if module == "A":
        solver = optimal_load if algorithm == "knapsack" else greedy_load
        run = lambda: solver(crates, 2 * size)
    elif module == "B":
        run = lambda: plan_routes(locations, roads, 0, size - 1,
                                  baseline=algorithm == "bellman_ford")
    else:
        run = lambda: plan_cable(roads, range(size), baseline=algorithm == "prim")
    run()
    samples = []
    for _ in range(5):
        start = time.perf_counter()
        result = run()
        samples.append(time.perf_counter() - start)
        del result
    tracemalloc.start()
    run()
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    q1, _, q3 = statistics.quantiles(samples, method="inclusive")
    return dict(time_s=statistics.median(samples), time_iqr_s=q3 - q1, mem_bytes=peak)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("results/results_ali_development.csv"))
    parser.add_argument("--measure", nargs=3, metavar=("MODULE", "ALGORITHM", "SIZE"))
    args = parser.parse_args()
    if args.measure:
        module, algorithm, size = args.measure
        print(json.dumps(measure(module, algorithm, int(size))))
        return

    print(f"Python {platform.python_version()} on {platform.platform()} ({platform.processor()})")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=FIELDS)
        writer.writeheader()
        for module, experiment, algorithms, sizes in SERIES:
            for size in sizes:
                for algorithm in algorithms:
                    row = dict(module=module, experiment=experiment, algorithm=algorithm,
                               instance=f"synthetic-seed1-{size}", size=size,
                               size2=2 * size, status="OK",
                               note="Development pilot. Operation counts unavailable.")
                    try:
                        completed = subprocess.run(
                            [sys.executable, "-m", "benchmarks.benchmark_ali",
                             "--measure", module, algorithm, str(size)],
                            capture_output=True, text=True, check=False, timeout=300,
                        )
                        if completed.returncode:
                            row.update(status="FAIL", note=completed.stderr.strip())
                        else:
                            row.update(json.loads(completed.stdout))
                    except subprocess.TimeoutExpired:
                        row.update(status="DNF", note="Worker exceeded 300 seconds.")
                    writer.writerow(row)


if __name__ == "__main__":
    main()
