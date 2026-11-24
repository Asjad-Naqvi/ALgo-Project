
# Pre-Experiment Predictions — Modules C, D and E

Roll Number: 23I-2521
Group Seed: 1

## Experimental Protocol

These predictions are recorded before performance measurements.

Each benchmark will use:
- Five geometrically increasing input sizes.
- One discarded warm-up run.
- Five measured runs.
- Median execution time and interquartile range (IQR).
- Identical inputs for competing algorithms.
- A five-minute timeout, recorded as DNF.
- Algorithm-specific operation counts and memory measurements where feasible.

Input loading will be excluded from algorithm timings.

## Module C — Rescue Scheduling

Input sizes: 16, 32, 64, 128, 256 windows.

### Prediction C1: Greedy Maximum-Count Scheduling
Expected complexity: O(n log n).
The sorting stage should dominate runtime.
Doubling input size should increase runtime by approximately 2–2.5 times for sufficiently large inputs.

### Prediction C2: Weighted Interval Scheduling
Expected complexity: O(n log n).
Weighted scheduling should have greater constant overhead than greedy scheduling due to binary searches, DP and traceback.

### Prediction C3: Exhaustive Reference
Expected complexity: O(2^n) times feasibility-check overhead.
It should become impractical much sooner than the dynamic-programming algorithm.
Timeouts will be recorded rather than silently omitted.

## Module D — Emergency Queue

Input sizes: 64, 128, 256, 512, 1024 alarms.

### Prediction D1: Binary Max-Heap
Expected queue complexity: O(n log n).
Doubling the alarm count should increase queue-processing time by approximately 2–2.5 times at larger sizes.

### Prediction D2: Linear Scan
Expected worst-case complexity: O(n^2) when the pending backlog grows proportionally with n.
Under sustained backlog, doubling the alarm count should approach a 4-times increase in comparison work.

### Prediction D3: Correctness
Heap and scan should produce identical alarm dispatches and release ticks.

## Module E — Radio Logs

### Prediction E1: Naive Search versus KMP
Text sizes: 256, 512, 1024, 2048, 4096 characters.

Expected complexities:
- Naive: O(nm) worst case.
- KMP: O(n + m).

Repeated-character inputs with long, nearly matching patterns should expose more redundant comparisons in Naive Search.

KMP should scale better when both text and pattern lengths increase.

### Prediction E2: Full-Matrix Edit Distance
Report lengths: 16, 32, 64, 128, 256 characters.

Expected time: O(nm).
Expected auxiliary space: O(nm).

When both report lengths double, the number of DP cells should increase approximately fourfold.

### Prediction E3: Hirschberg
Expected time: O(nm).
Expected auxiliary space: O(n + m), including output reconstruction.

Hirschberg should use less auxiliary memory than full-matrix DP for large reports, although recursion and repeated row calculations may increase runtime.

### Prediction E4: Huffman Coding
Message sizes: 256, 512, 1024, 2048, 4096 characters.

Expected encoding complexity: O(N + sigma log sigma), where sigma is the number of distinct symbols.

Huffman payload lengths should be no greater than the 6-bit fixed-length baseline for the supported 38-character alphabet.

Huffman should achieve its largest payload reduction on skewed character distributions.

Codebook storage costs will be reported separately.

## Interpretation Rules

Predictions are hypotheses, not measured results.

Actual timing ratios, operation counts, memory usage, prediction errors, and unexpected behavior will be documented after experiments.

All failures, DNF outcomes, and deviations will be retained in the results.
