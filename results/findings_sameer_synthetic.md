# Synthetic Pilot Benchmark Findings — Modules C, D, E

**Roll:** 23I-2521  
**Dataset:** reproducible synthetic pilot, seed 2521  
**Source:** `results/results_sameer_synthetic.csv`  
**Status:** final-score dataset **not** represented by this file

## 1. Methods and audit

The uploaded CSV has **55 unique algorithm-size rows**: **51 OK** and **4 DNF**. All 51 executed benchmark combinations completed successfully. The four scheduling-exhaustive combinations at n = 32, 64, 128 and 256 were **predeclared skips**, since the independent exact reference supports only n ≤ 18; **no actual 300-second timeout occurred**.

The runner used five geometrically increasing input sizes per family, one discarded warm-up, five timed samples, and the sample median. It reports the inclusive-quartile IQR (fourth minus second sorted measurement). Input generation and correctness checks were excluded from timing. Peak allocations were measured separately using `tracemalloc`; they do **not** represent total process RSS or input storage. Operation units differ by experiment and are not directly comparable across modules.

## 2. Module C — Rescue scheduling

| Input size | Greedy count (ms) | Weighted value (ms) | Weighted/greedy time |
|---:|---:|---:|---:|
| 16 | 0.019 | 0.027 | 1.45× |
| 32 | 0.043 | 0.065 | 1.52× |
| 64 | 0.097 | 0.137 | 1.41× |
| 128 | 0.226 | 0.307 | 1.36× |
| 256 | 0.504 | 0.712 | 1.41× |

At n = 256, greedy took **0.504 ms** versus **0.712 ms** for weighted scheduling (1.41× longer). For n = 16, exhaustive scheduling required **140.431 ms** and enumerated **65,536 subsets**, about **5,177×** the weighted algorithm’s 0.0271 ms. The counts of window field reads rose from 240 to 7,752 for greedy and 326 to 10,013 for weighted as n increased from 16 to 256. This is consistent with efficient sorting/DP growth and the impracticality of exhaustive subset enumeration. Greedy and weighted solve **different optimization objectives**, so their runtime comparison is not an interchangeability claim.

## 3. Module D — Emergency queue

| Input size | Max-heap (ms) | Linear scan (ms) | Heap speed advantage |
|---:|---:|---:|---:|
| 64 | 0.137 | 0.125 | 0.92× |
| 128 | 0.338 | 0.435 | 1.29× |
| 256 | 0.771 | 1.569 | 2.04× |
| 512 | 1.808 | 5.853 | 3.24× |
| 1,024 | 4.083 | 24.352 | 5.96× |

With **1,024 alarms**, heap dispatch took **4.083 ms**, versus **24.352 ms** for scan: **5.96× faster**. Priority comparisons were **16,800** (heap) and **174,933** (scan), a **10.41×** difference. At n = 64, scan was marginally faster (0.126 versus 0.137 ms) due to overheads, but heap increasingly outperformed scan as backlog grew. Over a 16× size increase (64→1,024), heap time grew about **29.86×** and scan about **194.11×**. This supports the original O(n log n) versus backlog-sensitive O(n²) queue prediction for the chosen sustained-backlog arrival pattern.

## 4. Module E — Radio logs

### 4.1 Naive search versus KMP

| Input size | Naive (ms) | KMP (ms) | KMP speed advantage |
|---:|---:|---:|---:|
| 256 | 0.050 | 0.029 | 1.73× |
| 512 | 0.178 | 0.058 | 3.06× |
| 1,024 | 0.518 | 0.116 | 4.48× |
| 2,048 | 1.643 | 0.233 | 7.06× |
| 4,096 | 6.216 | 0.465 | 13.37× |

The pattern length increased with text length (m = 4, 8, 12, 20, 40). At n = 4,096 and m = 40, naive search took **6.216 ms**, whereas KMP took **0.465 ms**, making KMP **13.37× faster**. The independently counted character comparisons were **162,280** (naive) against **8,268** (KMP), a **19.63×** reduction. As text length grew 16×, naive time grew ~124.94× versus ~16.15× for KMP. The repeated-character, almost-matching pattern is deliberately adversarial to naive search.

### 4.2 Full-matrix DP versus Hirschberg

| Input size | Full DP (ms) | Hirschberg (ms) | Hirschberg/DP time |
|---:|---:|---:|---:|
| 16 | 0.041 | 0.125 | 3.06× |
| 32 | 0.164 | 0.391 | 2.39× |
| 64 | 0.559 | 1.351 | 2.42× |
| 128 | 2.252 | 4.991 | 2.22× |
| 256 | 8.526 | 18.265 | 2.14× |

| Report length (each) | Full DP peak (bytes) | Hirschberg peak (bytes) | Hirschberg memory reduction |
|---:|---:|---:|---:|
| 16 | 2,632 | 2,952 | -12.2% |
| 32 | 9,224 | 4,208 | +54.4% |
| 64 | 34,728 | 7,288 | +79.0% |
| 128 | 138,088 | 12,264 | +91.1% |
| 256 | 559,824 | 41,416 | +92.6% |

At **n = m = 256**, full DP took **8.526 ms** and peaked at **559,824 traced bytes**; Hirschberg took **18.265 ms** and peaked at **41,416 traced bytes**. Hirschberg thus used **92.6% less measured peak memory** while taking **2.14×** as long. At n = 16 it instead showed slightly higher peak allocations, reflecting fixed overhead at small sizes. The full DP operation counts were n×m cell updates (256→65,536); Hirschberg operation counts were **not instrumented**, so no comparative operation-count claim is made.

### 4.3 Huffman versus 6-bit fixed-length encoding

| Input size | Huffman (ms) | Fixed 6-bit (ms) | Huffman/fixed time |
|---:|---:|---:|---:|
| 256 | 0.173 | 0.030 | 5.78× |
| 512 | 0.200 | 0.048 | 4.20× |
| 1,024 | 0.270 | 0.071 | 3.79× |
| 2,048 | 0.392 | 0.129 | 3.04× |
| 4,096 | 0.655 | 0.249 | 2.64× |

At n = 4,096, Huffman took **0.656 ms** while fixed-length encoding took **0.249 ms** (**2.64× longer** for Huffman). The benchmark used a skewed 38-character alphabet and measured the time of coding; it did **not** include payload-bit counts or serialized codebook overhead in the CSV.

**Independent derived payload calculation (not a CSV measurement):** reconstructing the deterministic seeded message generator and calculating the optimal Huffman merge cost gives the following payload-only estimates. They exclude codebook metadata, framing and bit packing; therefore they are **not net file-compression ratios**.

| Message symbols | Huffman payload (bits) | 6-bit payload (bits) | Payload-only reduction |
|---:|---:|---:|---:|
| 256 | 742 | 1,536 | 51.7% |
| 512 | 1,464 | 3,072 | 52.3% |
| 1,024 | 2,913 | 6,144 | 52.6% |
| 2,048 | 5,807 | 12,288 | 52.7% |
| 4,096 | 12,174 | 24,576 | 50.5% |

This calculation validates the expected payload benefit for a skewed alphabet, but the actual implementation should also output payload and codebook sizes for the official measurements. The `ops` column for compression is an algorithm-specific formula/proxy rather than the same type of runtime instrumented count used for heap and KMP.

## 5. Prediction versus observation

| Committed prediction | Pilot observation | Assessment |
|---|---|---|
| C: sorting + weighted DP scale near O(n log n) | Both scale smoothly; weighted slower by ~1.36–1.52× | Consistent |
| C: exhaustive reference grows exponentially | 65,536 subsets at n=16; larger sizes capped before execution | Supported qualitatively; no measured large-n timeout |
| D: heap scales better than scan with backlog | 5.96× faster and 10.41× fewer comparisons at n=1,024 | Supported |
| E: KMP scales better on adversarial matching | 13.37× faster; 19.63× fewer comparisons at n=4,096 | Supported |
| E: Hirschberg trades runtime for lower space | 2.14× slower and 92.6% less peak memory at n=m=256 | Supported at larger sizes |
| E: Huffman saves payload bits on skewed distributions | Deterministic-input reconstruction estimates ~50–53% payload saving | Supported by derived payload estimate; not recorded directly |

## 6. Limitations and recommended next actions

These results are **synthetic pilot evidence only**, not official coursework benchmark results. They use five repeated samples for each instance, without reported hardware/OS/Python version or cross-machine variance. Very short execution times are sensitive to measurement noise; the reported IQR is helpful but does not establish statistical significance. Tracemalloc undercounts memory in some cases (including 0 for naive search) because it traces Python allocations beyond the prebuilt input, not total memory. Equal heap/scan peaks in the CSV are not evidence of identical asymptotic memory use.

For the final scored experiment, use the course-verified master CSVs and SHA-256, commit the verified release metadata, repeat the prescribed sampling protocol, preserve this pilot in a separate file, and export official records under the shared schema. Record real DNF timeouts separately from predefined caps. For Huffman, record codebook bytes and payload bits explicitly; for Hirschberg, retain the `ops` entry as uninstrumented unless actual operation counting is added. Gather hardware, OS and Python version before the official run.

### Source and reproducibility

- Uploaded results: `results/results_sameer_synthetic.csv` (55 rows).
- Runner: `benchmarks/benchmark_sameer.py`, using `time.perf_counter`, separate `tracemalloc`, and counted operations where supported.
- All numerical timing/speed/memory claims above were computed from that CSV. The distinct Huffman payload table is derived from the deterministic generator and Huffman merge-cost identity, not from the CSV.

---

*Prepared as a report-ready summary of measured pilot results. Do not relabel these measurements as official master-CSV experiments.*
