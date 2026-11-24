# Modules C/D/E — Synthetic Pilot Benchmarks

Run from the repository root after committing the pre-experiment predictions:

```bash
python3 -m unittest tests.test_benchmark_sameer -v
python3 -m benchmarks.benchmark_sameer --smoke
python3 -m benchmarks.benchmark_sameer
```

Outputs: `results/results_sameer_smoke.csv` and `results/results_sameer_synthetic.csv`.
These are **synthetic development measurements**, not the final scored master-CSV results. Do not merge the smoke CSV into official results.

The complete run uses 55 algorithm-size combinations. For each completed combination, input generation and pairwise correctness verification are excluded from timing; one warm-up is discarded, followed by five measurements using `time.perf_counter`. `time_s` is their median and `time_iqr_s` is the inclusive quartile IQR (for five samples, the fourth minus second sorted time). A separate `tracemalloc` pass measures peak traced Python allocations beyond the prebuilt input. All operations are counted in a separate, non-timed pass.

Five geometric sizes are used per experiment. The independent scheduling exhaustive reference is implemented only for 18 or fewer windows, so n=32,64,128,256 are **predeclared DNF with no timeout claimed**. Real runs have a 300-second process-level limit per algorithm/size combination; the worker is stopped if that limit is exceeded. Any error is retained in its own CSV row.

`ops` units vary by experiment and are recorded in each row's `note`: window field reads, enumerated subsets, priority comparisons, character comparisons, DP cell updates, or instrumented symbol/heap actions. Hirschberg's `ops` is blank (not instrumented), rather than an invented count. These units should not be directly compared across unrelated experiments.

Input families: reproducible seeded interval windows; sustained-backlog alarms (~1.5 arrivals/tick); worst-case repeated-character matching with the pattern length varied across 4,8,12,20,40; seeded equal-length edit reports; skewed 38-symbol radio logs. This benchmark uses Python's elapsed time and tracemalloc allocations, not full process RSS or on-disk codebook serialization.

Record hardware, Python version, master-data version/hash, sampling scheme and official experiment results separately when running the master release. Do not treat these pilot rows as master-data evidence.
