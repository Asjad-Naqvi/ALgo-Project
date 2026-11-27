# C/D/E Master Release Benchmarks — Official data-derived inputs

Run from the project root **after** committing `results/predictions_sameer.md`:

```sh
python3 -m unittest discover -s tests -v
python3 -m benchmarks.benchmark_sameer_master --smoke
python3 -m benchmarks.benchmark_sameer_master | tee results/benchmark_sameer_master_run.log
```

Default archive is `~/Downloads/archive.zip`; override with `--archive /path/to/archive.zip`.
The script verifies all 20 CSV SHA-256 checksums before reading any experiment input.
It reads two official cases (case `1-40`, tier L; case `1-49`, trap X) from the
release into memory *before* starting timed trials. It does not generate synthetic
test input, but to obtain five geometric sizes it deliberately takes **prefixes**
of the case tables/text. Prefix measurements are not the same as measuring the
unaltered full case, and the report must explicitly say so.

Families and provenance:

| Family | Case | Official source | Size values |
|---|---|---|---|
| C scheduling | 1-40 | first n `windows` rows | 16,32,64,128,256 |
| D alarms | 1-40 | first n `incidents` rows | 64,128,256,512,1024 |
| E matching | 1-49 | first n radio characters; original pattern at lengths 4,8,12,20,40 | 256,512,1024,2048,4096 |
| E edit | 1-40 | first n chars of both original radio reports | 16,32,64,128,256 |
| E compression | 1-49 | first n radio characters | 256,512,1024,2048,4096 |

Pairwise correctness checks occur before measurements. Each algorithm-size
combination runs in a fresh child process with one discarded warmup, five timed
calls, a median and the IQR between the second and fourth sorted measurements.
`tracemalloc` runs separately to record peak newly allocated Python memory,
not OS RSS. `ops` is a separately instrumented operation count (with unit in
`note`), not a universal cross-module metric. Time excludes data loading and
preprocessing. Parent supervises the child with a 300s timeout.

The independent exhaustive C reference supports n<=18. The rows for 32,64,128,
256 are **predeclared DNF (unsupported cap)** rather than actual timeout runs.
There are 55 rows (51 OK, 4 DNF if nothing else fails).

Compression rows additionally record Huffman bit length, six-bit baseline bit
length and payload savings percentages, excluding codebook cost. The source
patterns are taken verbatim from the official 1-49 release; 1-49 is adversarial.
The matched text is intentionally truncated by size and is not the whole log.

The resulting CSV has the team's canonical schema. It is a master-derived
benchmark, distinct from the synthetic pilot and seven-day campaign outcomes.
For the full project report also record hardware/Python version, ZIP checksums,
master-order sampling rules and any other modules measured by teammates.
