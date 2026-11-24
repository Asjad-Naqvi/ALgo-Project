
# Fault-Injection Verification

Roll Number: 23I-2521

## Fault 1 — Emergency Queue

Mutation: Reverse alarm-ID tie-breaking from ascending to descending.

Expected behavior: Smaller alarm ID wins when priority and arrival tick are equal.

Detection: Randomized dispatch verification detected 20 failing subcases.

Restoration: Correct comparator restored. Full suite subsequently passed.

## Fault 2 — Rescue Scheduling

Mutation:
`window["start"] >= last_finish`
changed to:
`window["start"] > last_finish`

Detection:
`test_touching_windows` failed.

Observed:
Expected 2 compatible windows, obtained 1.

Restoration:
Compatibility condition restored.

## Fault 3 — KMP String Matching

Mutation:
After a complete match, replace the LPS fallback with `j = 0`.

Detection:
`test_kmp_overlapping` failed.

Observed:
Expected [0, 1, 2], obtained [0].

Restoration:
LPS fallback restored. Targeted test passed.

## Final Verification

Command:
`python3 -m unittest discover -s tests -v`

Result:
94 tests executed; all passed.

No intentional mutations remain in the final implementation.
