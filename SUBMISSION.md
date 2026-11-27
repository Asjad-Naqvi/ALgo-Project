# LIFELINE submission checks

## Reproduce from a clean checkout

Run these commands from the repository root with Python 3.8 or newer. Place the course's `master_release_v1` CSVs in `archive/`, with `cases.csv` directly in that directory. Verify them against the course's `CHECKSUMS.txt` first. See [release details](data/MASTER_DATA.md).

```bash
python -m pip install openpyxl
python -m unittest discover -s tests
python -m src archive 1-01 --mode both
```

Seed 1 sample IDs for a smoke check across tiers are `1-01`, `1-08`, `1-21`, `1-41` and `1-47`. Each run should show seven days in each mode, HQ as the starting point, and no truck load on Day 7. Compare equal route and cable costs across modes for each day.

## Package the checked commit

Use the roll numbers and Section B listed in `members.txt`. The proposal lists Section A, so confirm the labels against course records before submission.

```bash
git archive --format=zip --prefix=23I-2648-B_23I-2521-B_23I-6050-B/ --output=23I-2648-B_23I-2521-B_23I-6050-B.zip HEAD
python -m zipfile -t 23I-2648-B_23I-2521-B_23I-6050-B.zip
```

Run this from a directory where the output filename is free, or choose an output path in a separate folder. The archive contains files tracked in the chosen commit. Keep the course CSV release available locally for reproduction and record its version and checksum in the submission.

Before uploading, verify that the ZIP includes the final report, proposal-change notes, consolidated official experiment results and plots, and final campaign evidence. At the current checkpoint, the A/B/F timing results on `main` are synthetic pilots. The final report and official A/B/F timing results were unavailable. Sameer's newer official C/D/E evidence is on the team's separate branch.

GitHub currently lists the repository as public. The brief requires a private repository named using the roll-number pattern and course staff collaborator access. Confirm the course staff accounts and repository settings before submitting the link.
