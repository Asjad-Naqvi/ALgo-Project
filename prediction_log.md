# Experiment predictions

## A, B and F development pilot

Recorded 2026-11-25 at 18:56 PKT before timing. The official course release is absent, so this round uses seed 1 synthetic inputs. Inventory uses capacity twice the number of crates. Routes and cable use connected graphs with a spanning tree plus random roads, shuffled before benchmarking.

Predictions for the largest input of each series use median runtime ratios:

- A, 256 crates. Greedy will be faster. Predict knapsack takes 20× as long, with a tolerance of 15×, because the DP visits a capacity range for every crate.
- B, 512 locations. Dijkstra will be faster. Predict Bellman–Ford takes 3× as long, with a tolerance of 2×, because relaxation makes repeated passes over the graph.
- F, 512 locations. Kruskal will be faster. Predict Prim takes 1.5× as long, with a tolerance of 0.5×, because its heap can hold multiple candidate edges per location.

### Observed results

| Module | Predicted slower-to-faster ratio | Observed ratio |
|---|---:|---:|
| A | 20× ± 15× | 17.59× |
| B | 3× ± 2× | 1.37× |
| F | 1.5× ± 0.5× | 1.19× |

All three winners and tolerance bands held. The gaps for B and F were smaller than their point predictions. The measured calls include shared input validation and graph preparation, which may narrow their end-to-end timing gaps. Bellman–Ford also exits when it completes a pass without a change. The pilot did not time individual phases.

Run `python -m benchmarks.benchmark_ali` to regenerate the [30 pilot rows](results/results_ali_development.csv). The run used Python 3.14.0 on Windows 11 build 26300 (Intel64 family 6 model 142). Each combination used one warm-up, five timed calls, median and IQR, and a separate peak-allocation pass with tracemalloc. Data generation was outside the timed region. Official measurements and operation counts are pending.

### Fault injection

The three checks in `tests.test_ali_invariants` passed. A temporary mock stripped destination penalties before routing. The route test failed with `AssertionError: 2 != 6`, catching the missing penalty. Removing the mock restored the correct behavior and all three checks passed again.
