# Master dataset and module handoff

Group seed is **1**. Official release version, filename and SHA-256 are pending receipt of the course release. Record them here after verifying the exact file or files named by the course checksum. Use the verified archive's extracted CSVs, if the course publishes an archive. The local Iteration 1 workbook can supply development fixtures.

From the repository root, use the loader with Python.

```python
from pathlib import Path
from src.master_data import load_master, verify_sha256

verify_sha256(Path(course_file), course_sha256)
cases = load_master(Path(csv_directory))
case = cases[case_id]
```

Repeat the checksum check for each file covered by a per-file manifest. The loader reads one CSV per workbook sheet, with the existing headers and UTF-8 encoding. It preserves the order in `cases.csv` for sampling and keeps sheet rows in input order. With seed 1, take zero-based positions 1, 8, 15 and so on after filtering to the required tier.

## Shared inputs and outcomes

- `CaseData.case_id` is the string ID in the master file. `metadata` exposes the case row, including tier, capacity and targets. `tables` maps each remaining sheet name to a tuple of read-only rows keyed by column name. Text fields are strings and numeric fields are integers. Missing rows for a case are exposed as empty tuples, including the optional Tier S claims.
- A consumes crates and capacity and returns crate IDs, total weight and total value. B consumes locations, roads, source, target and blocked road IDs and returns the cheapest path and cost, reachable IDs, and the fewest-roads path. F consumes the open roads and HQ component and returns selected road IDs and total cable cost.
- C consumes available windows and returns chosen window IDs, count and value for the requested objective. D consumes incidents and returns alarm IDs with release ticks. Use descending priority, ascending arrival tick and ascending alarm ID. E consumes the radio tables. G/H/I use their source tables as defined in the proposal.
- The campaign builds day-specific inputs from immutable base rows. HQ is location 0. The workbook validator uses one-based wave numbers, so index the sorted wave groups when applying the campaign's zero-based wave indices. Use the original road IDs for closures.
- The loader raises `DatasetError` for unreadable or structurally invalid CSVs. Modules validate their own domain constraints and raise `ValueError` on invalid inputs. A valid but unreachable route or absent solution uses `None` for the unavailable result. Valid empty selections and queues return empty collections. The CLI should show these outcomes explicitly.

These interfaces are ready for Sameer's campaign adapter and Saad's benchmark runner. Confirm them as the module signatures are added.

## Truck loading

```python
from src.inventory import optimal_load

load = optimal_load(case.tables["crates"], case.metadata["capacity"])
print(load.crate_ids, load.total_weight, load.total_value)
```

Use the same inputs with `greedy_load` for an exact-ratio greedy baseline or `exhaustive_load` for a small-case exact comparison. For the campaign, pass crate rows with that day's adjusted values.

## Route planning

```python
from src.routing import plan_routes

routes = plan_routes(
    case.tables["locations"], case.tables["roads"],
    source=0, target=case.metadata["target_0"], blocked_road_ids=(),
)
```

Pass the full road table, with any daily travel-time changes, the day's location penalties, and the day's blocked road IDs. Set `baseline=True` to use Bellman–Ford for the cheapest route. The fewest-roads path uses ascending-neighbour BFS in either mode. Path ties for cheapest cost use the lowest-ID optimal predecessor at each step. When the destination is unreachable, both paths and the cost are `None` and the reachable set is still returned.
