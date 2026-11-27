# Pre-Measurement Predictions — Official Sampled/Pooled C/D/E Experiments

Owner: 23I-2521; group seed: 1. **Commit this file before running any pooled timing experiments.**

## Fixed plan

Use `results/master_sampling_manifest.csv` from the verified course `master_release_v1` ZIP. Take the first five manifest-selected cases from each tier S/M/L/X (20 cases total), preserving the 1,8,15,... zero-based tier-order rule. Build prefix inputs through deterministic round-robin pooling of real source rows/characters. Reindex local IDs only to avoid collisions, and sort pooled alarms by arrival tick. Use native radio patterns from selected cases. These are **derived, pooled inputs**, not unaltered full cases or all 518 selected cases.

Sizes are C n=16,32,64,128,256; D n=64,128,256,512,1024; E match/compress n=256,512,1024,2048,4096 (pattern lengths 4,8,12,20,40); E edit n=16,32,64,128,256 per string. Paired algorithms get identical inputs. After one discarded warm-up, take five timings per algorithm/size; report median and IQR, separate `tracemalloc` peak and operation counts, with a 300 s cap. Exclude ZIP verification, case parsing and pooling from timed calls.

## Prediction C

Greedy maximum-count and weighted interval scheduling should scale approximately O(n log n); weighted should be slower due to DP and predecessor searches. They optimize **different** objectives and must not be compared as if one were an approximation to the other. Exhaustive enumeration should complete for n=16; n>18 must remain explicitly *predeclared cap DNF*, not asserted measured timeout.

## Prediction D

Heap queue processing should grow around O(n log n) while a linear-scan pending list should trend toward O(n²) with a sufficiently sustained pooled backlog. The scan might be competitive at n=64. Both should produce identical release ticks/IDs.

## Prediction E

KMP should use fewer comparisons than naive matching, with larger advantages for longer patterns and highly repetitive logs; the mixed pooled texts may weaken the worst-case advantage compared with the synthetic adversarial test. Full edit-distance DP and Hirschberg should both grow around O(nm); Hirschberg should save traced memory for longer reports but may require more time. Huffman should compress pooled skewed radio logs better than fixed six-bit payloads when symbol frequencies are unequal, with slower codebook construction. Any savings exclude serialized codebook overhead, which must be disclosed.

## Limitations to check after measurements

The pooling policy mixes independent cases and affects arrival-time contention, pattern matches, text frequency, and rescue-window conflicts. State those effects clearly. Record observed departures from these predictions, fitted growth and crossover sizes; retain all failures or capped entries without relabeling them as timeouts. Compare these results with previous single-case-prefix and synthetic pilots but do not replace those raw CSVs.
