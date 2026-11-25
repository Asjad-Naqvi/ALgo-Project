# Experiment predictions

## A, B and F development pilot

Recorded 2026-11-25 at 18:56 PKT before timing. The official course release is absent, so this round uses seed 1 synthetic inputs. Inventory uses capacity twice the number of crates. Routes and cable use connected graphs with a spanning tree plus random roads, shuffled before benchmarking.

Predictions for the largest input of each series use median runtime ratios:

- A, 256 crates. Greedy will be faster. Predict knapsack takes 20× as long, with a tolerance of 15×, because the DP visits a capacity range for every crate.
- B, 512 locations. Dijkstra will be faster. Predict Bellman–Ford takes 3× as long, with a tolerance of 2×, because relaxation makes repeated passes over the graph.
- F, 512 locations. Kruskal will be faster. Predict Prim takes 1.5× as long, with a tolerance of 0.5×, because its heap can hold multiple candidate edges per location.
