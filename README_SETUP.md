# Native reader for LIFELINE master_release_v1

This adapter reads the original full release ZIP **without extracting all 358 MB** or changing any official CSV columns. It verifies the SHA-256 of all 20 CSVs against the release's bundled `CHECKSUMS.txt` and only materializes the chosen cases as `src.master_data.CaseData`, which the existing campaign coordinator understands.

Place `src/master_release.py` and `tests/test_master_release.py` in the existing repository (extract this ZIP from the project root).

Then run:

```bash
python3 -m unittest discover -s tests -v
python3 -m src.master_release ~/Downloads/archive.zip --cases 1-01 1-08 1-15 1-40 1-49
```

Expected case tiers: S, S, S, L, X. Their exact IDs are illustrative development samples; defer to the coursework's sampling rule for final scored runs.

In your own Python code:

```python
from pathlib import Path
from src.master_release import load_master_release
from src.campaign_engine import run_campaign

cases = load_master_release(Path.home() / 'Downloads' / 'archive.zip', ['1-01'])
result = run_campaign(cases['1-01'], mode='primary')
print([(day['day'], day['status'], day['route_cost']) for day in result])
```

The full master release declares itself `master_release_v1`, dated 2026-11-12, with 3,622 cases across 75 groups. All 20 embedded SHA-256 hashes were verified in our inspection. Retain an independently sourced course-release link if required to establish provenance: an internal checksum manifest only checks integrity against the archive's own claims.

Important: some cases have `group_seed != group_no`. This reader validates global `case_id` using `group_no`, preserves `orig_case_id`, and does not use the old `group_seed` case-ID rule. It also supports the older campaign rules' mapping from sorted closure wave labels to wave indices.

Do not commit or re-upload the large course ZIP into Git. Keep it in `~/Downloads` or another ignored local folder.
