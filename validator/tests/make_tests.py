#!/usr/bin/env python3
"""Builds two valid single-case workbooks and broken copies of each (one defect per copy).
Usage: python make_tests.py SEED   (run from validator/tests)"""
import os, sys, copy
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "generator"))
import generate as G
from openpyxl import load_workbook

seed = int(sys.argv[1]) if len(sys.argv) > 1 else 1
HERE = os.path.dirname(os.path.abspath(__file__))
A, B = 9, 25   # A: tier S, study 4.  B: tier M, study 2.


def make(k, name):
    p = os.path.join(HERE, name)
    G.write(G.build(seed, [k]), p)
    return p


def edit(src, dst, fn):
    wb = load_workbook(src)
    fn(wb)
    wb.save(dst)


def cell(wb, sheet, row, col, val):
    wb[sheet].cell(row=row, column=col).value = val


def hdr(wb, sheet, col):
    return [c.value for c in wb[sheet][1]].index(col) + 1


def mut(sheet, col, row, f):
    def fn(wb):
        c = hdr(wb, sheet, col)
        old = wb[sheet].cell(row=row, column=c).value
        cell(wb, sheet, row, c, f(old))
    return fn


def drop_rows(sheet, pred_col, pred):
    def fn(wb):
        ws = wb[sheet]
        c = hdr(wb, sheet, pred_col)
        for r in range(ws.max_row, 1, -1):
            if pred(ws.cell(row=r, column=c).value):
                ws.delete_rows(r)
    return fn


def rename_header(wb):
    wb["crates"].cell(row=1, column=4).value = "kilos"


def planted_flip(wb):
    ws = wb["safety_planted"]
    for r in range(2, ws.max_row + 1):
        ws.cell(row=r, column=3).value = 1 - ws.cell(row=r, column=3).value


def no_hospital(wb):
    ws = wb["locations"]
    for r in range(2, ws.max_row + 1):
        if ws.cell(row=r, column=3).value == "H":
            ws.cell(row=r, column=3).value = "J"


def target_hq(wb):
    cell(wb, "cases", 2, 7, 0)


def dup_serial(wb):
    ws = wb["crates"]
    ws.cell(row=3, column=7).value = ws.cell(row=2, column=7).value


def repeat_road(wb):
    ws = wb["roads"]
    ws.cell(row=3, column=3).value = ws.cell(row=2, column=3).value
    ws.cell(row=3, column=4).value = ws.cell(row=2, column=4).value


def disconnect(wb):
    ws = wb["roads"]
    # re-point every road touching the last location away from it by deleting them
    V = wb["locations"].max_row - 2
    for r in range(ws.max_row, 1, -1):
        if V in (ws.cell(row=r, column=3).value, ws.cell(row=r, column=4).value):
            ws.delete_rows(r)


def overlap_waves(wb):
    ws = wb["waves"]
    ws.cell(row=3, column=3).value = ws.cell(row=2, column=3).value


def float_cell(wb):
    wb["windows"].cell(row=2, column=5).value = 12.5


def formula_cell(wb):
    wb["windows"].cell(row=2, column=5).value = "=1+1"


def swap_tick(wb):
    ws = wb["incidents"]
    a, b = ws.cell(row=2, column=3).value, ws.cell(row=ws.max_row, column=3).value
    ws.cell(row=2, column=3).value, ws.cell(row=ws.max_row, column=3).value = b + 5, a


def low_priority(wb):
    ws = wb["incidents"]
    for r in range(2, ws.max_row + 1):
        ws.cell(row=r, column=4).value = 1


def kill_touching(wb):
    ws = wb["windows"]
    for r in range(2, ws.max_row + 1):
        s, f = ws.cell(row=r, column=3).value, ws.cell(row=r, column=4).value
        if f < 1439:
            ws.cell(row=r, column=4).value = f + 0  # no-op; real change below
    fins = {ws.cell(row=r, column=4).value for r in range(2, ws.max_row + 1)}
    for r in range(2, ws.max_row + 1):
        s = ws.cell(row=r, column=3).value
        while s in fins and s > 0:
            s -= 1
        ws.cell(row=r, column=3).value = s if s < ws.cell(row=r, column=4).value - 4 else ws.cell(row=r, column=3).value


def thin_cats(wb):
    ws = wb["crates"]
    for r in range(2, ws.max_row + 1):
        ws.cell(row=r, column=3).value = 0


def too_dense(wb):
    # add many extra roads so the average degree leaves the study's band
    ws = wb["roads"]
    have = {(ws.cell(row=r, column=3).value, ws.cell(row=r, column=4).value) for r in range(2, ws.max_row + 1)}
    V = wb["locations"].max_row - 1
    no = ws.max_row - 1
    cid = ws.cell(row=2, column=1).value
    for u in range(V):
        for v in range(u + 1, V):
            if (u, v) not in have:
                ws.append([cid, no, u, v, 5, 5])
                no += 1


def pattern_zero(wb):
    for r in range(2, wb["radio_patterns"].max_row + 1):
        wb["radio_patterns"].cell(row=r, column=4).value = 0


def short_bound(wb):
    cell(wb, "cases", 2, 10, -1 + 0 * 1)


def tour_len(wb):
    c = hdr(wb, "cases", "tour_length")
    cell(wb, "cases", 2, c, wb["cases"].cell(row=2, column=c).value + 7)


def cover_drop(wb):
    ws = wb["sensor_cover"]
    ws.delete_rows(2)


def ration_sum(wb):
    c = hdr(wb, "cases", "rations_target")
    cell(wb, "cases", 2, c, wb["cases"].cell(row=2, column=c).value + 1)


def claim_wrong(wb):
    ws = wb["claims"]
    ws.cell(row=2, column=2).value += 1


def scenario_wrong(wb):
    c = hdr(wb, "cases", "scenario")
    cell(wb, "cases", 2, c, wb["cases"].cell(row=2, column=c).value % 6 + 1)


def capacity_big(wb):
    c = hdr(wb, "cases", "capacity")
    cell(wb, "cases", 2, c, 10 ** 6)


def log_symbol(wb):
    ws = wb["radio_log"]
    ws.cell(row=2, column=3).value = "a" + ws.cell(row=2, column=3).value[1:]


def rule_dup_switch(wb):
    ws = wb["safety_rules"]
    ws.cell(row=2, column=4).value = ws.cell(row=2, column=3).value


def extra_sheet(wb):
    wb.create_sheet("notes")


def pipeline_range(wb):
    wb["pipeline_dims"].cell(row=2, column=3).value = 1


def drum_prop(wb):
    ws = wb["drum_prices"]
    for r in range(2, ws.max_row + 1):
        ws.cell(row=r, column=3).value = 5 * (r - 1)


CASES = {
    "A": (A, [
        ("header_renamed", rename_header, "V1"),
        ("duplicate_serial", dup_serial, "V2"),
        ("repeated_road_pair", repeat_road, "V3"),
        ("disconnected_network", disconnect, "V4"),
        ("pattern_counts_zero", pattern_zero, "V5"),
        ("wrong_claim", claim_wrong, "V5"),
        ("planted_assignment_flipped", planted_flip, "V6"),
        ("cover_node_removed", cover_drop, "V3"),
        ("wrong_scenario", scenario_wrong, "V1"),
        ("no_hospital", no_hospital, "V3"),
        ("float_in_integer_column", float_cell, "V1"),
        ("extra_sheet", extra_sheet, "V1"),
        ("rare_crates_removed", thin_cats, "V7"),
    ]),
    "B": (B, [
        ("waves_overlap", overlap_waves, "V4"),
        ("tour_length_wrong", tour_len, "V6"),
        ("rations_target_wrong", ration_sum, "V6"),
        ("target_is_hq", target_hq, "V3"),
        ("capacity_out_of_range", capacity_big, "V2"),
        ("all_priorities_one", low_priority, "V2"),
        ("tick_decreases", swap_tick, "V3"),
        ("graph_too_dense_for_study", too_dense, "V7"),
        ("log_symbol_lowercase", log_symbol, "V5"),
        ("rule_repeats_switch", rule_dup_switch, "V3"),
        ("formula_cell", formula_cell, "V1"),
        ("pipeline_dim_out_of_range", pipeline_range, "V2"),
        ("drum_proportional", drum_prop, "V2"),
    ]),
}

if __name__ == "__main__":
    manifest = []
    for tag, (k, muts) in CASES.items():
        base = make(k, f"valid_{tag}_case{k}.xlsx")
        for name, fn, code in muts:
            dst = os.path.join(HERE, f"broken_{tag}_{name}.xlsx")
            edit(base, dst, fn)
            manifest.append((os.path.basename(dst), code))
    with open(os.path.join(HERE, "manifest.txt"), "w") as f:
        for n, c in manifest:
            f.write(f"{n} {c}\n")
    print(len(manifest), "broken copies written")
