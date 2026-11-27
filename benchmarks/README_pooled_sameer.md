# Sampled Master Release Benchmark (Modules C/D/E)

This **supplements** `benchmark_sameer_master.py` (two single-case prefixes). It consumes the committed 518-case manifest but deliberately loads only the **first five** selected cases in each tier, for 20 total. This is a stratified, pooled sensitivity experiment, **not a run over all 518 cases**, and **not an experiment on unaltered full cases**.

Input pool: round robin by case in tier order S/M/L/X; source windows retain start, finish and value but receive collision-free IDs; incidents retain tick and priority but are sorted by tick and receive collision-free IDs; report/log text keeps each character but interleaves the cases; radio patterns are original patterns selected from case IDs recorded in provenance. Prefixes of the pooled streams yield five geometric sizes. This changes cross-case context intentionally and must be discussed as a limit.

## Commands (from repository root)

**Before any timing run**, first install files and commit `results/predictions_sameer_pooled.md`, as required for pre-experiment prediction evidence. Check the other filenames are staged too.

```bash
python3 -m unittest discover -s tests -v
python3 -m benchmarks.benchmark_sameer_pooled --smoke
python3 -m benchmarks.benchmark_sameer_pooled | tee results/benchmark_sameer_pooled_run.log
```

The smoke run writes `results/results_sameer_master_pooled_smoke.csv`. The full run writes `results/results_sameer_master_pooled.csv`; both write `results/sameer_pooled_provenance.json` (archive and sampling-manifest hashes, exact source IDs, pooling policy and lengths). The same 55 task layout applies, with four expected predeclared exhaustive-reference DNF entries above n=18.

Per algorithm-size pair: one untimed warm-up, five timed calls, median and IQR, separate `tracemalloc` peak, separately instrumented operations, timed execution excluding loading/pooling. One isolated child process per task, 300-second time limit. Codebook serialization excluded from Huffman savings. Exact formulas for operation counts are in `benchmarks/benchmark_sameer.py`.
