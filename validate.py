#!/usr/bin/env python3
"""LIFELINE validator. Usage: python validate.py cases.xlsx [--partial]
Recomputes everything from the raw cells (no field is trusted).
--partial: workbook holds fewer than 50 cases (used for tests); skips the 50-case and cross-case rules.
Prints PASS or the broken rules for every case."""
import bisect, heapq, itertools, re, sys
from collections import deque, defaultdict
from fractions import Fraction
from openpyxl import load_workbook

HEAD = {
 "cases": "case_id group_seed case_no tier scenario capacity target_0 target_1 target_2 edit_bound tour_length sensor_nodes sensor_k safety_vars rations_target",
 "crates": "case_id crate_id cat weight value expiry serial",
 "locations": "case_id loc_id type penalty",
 "roads": "case_id road_no u v minutes cable",
 "waves": "case_id wave_no road_no",
 "radio_log": "case_id part text",
 "radio_patterns": "case_id pattern_no pattern count",
 "radio_reports": "case_id report_a report_b",
 "windows": "case_id window_id start finish value",
 "incidents": "case_id alarm_id tick priority",
 "sites": "case_id site_no x y",
 "tour": "case_id step site_no",
 "pipeline_dims": "case_id idx dim",
 "drum_prices": "case_id length price",
 "sensor_edges": "case_id u v",
 "sensor_cover": "case_id node",
 "safety_rules": "case_id rule_no lit_1 lit_2 lit_3",
 "safety_planted": "case_id switch value",
 "rations": "case_id item value planted",
 "claims": "case_id cargo_opt window_count_opt window_value_opt drum_opt tour_opt cover_min",
}
HEAD = {k: v.split() for k, v in HEAD.items()}
TEXT = {"case_id", "tier", "type", "text", "pattern", "report_a", "report_b"}
ALPH = set("ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-")
R = {"crates": ((8, 20), (40, 200), (500, 1500)), "V": ((6, 12), (30, 150), (500, 2000)),
     "log": ((200, 500), (2000, 10000), (20000, 100000)), "report": ((10, 30), (30, 150), (200, 1000)),
     "windows": ((8, 20), (50, 300), (1000, 3000)), "alarms": ((10, 40), (200, 1000), (2000, 5000)),
     "sites": ((5, 9), (10, 16), (200, 500)), "stages": ((4, 8), (15, 60), (100, 300)),
     "drum": ((5, 14), (40, 200), (500, 2000)), "sensor": ((6, 14), (20, 40), (100, 400)),
     "switches": ((6, 15), (20, 50), (20, 50)), "rations": ((8, 20), (24, 40), (50, 100))}
TI = {"S": 0, "M": 1, "L": 2, "X": 2}


def tier_of(k):
    return "S" if k < 20 else "M" if k < 40 else "L" if k < 46 else "X"


class Case:
    def __init__(self, cid):
        self.cid = cid
        self.err = []
        self.d = defaultdict(list)

    def bad(self, code, msg):
        if len(self.err) < 40:
            self.err.append(f"{code}: {msg}")


# ---------------------------------------------------------------- algorithms (own implementations)
def knap(items, cap):
    b = [0] * (cap + 1)
    for w, v in items:
        for c in range(cap, w - 1, -1):
            if b[c - w] + v > b[c]:
                b[c] = b[c - w] + v
    return b[cap]


def greedy(items, cap):  # (id,w,v)
    tot = 0
    for _, w, v in sorted(items, key=lambda t: (-Fraction(t[2], t[1]), t[0])):
        if w <= cap:
            cap -= w
            tot += v
    return tot


def edit(a, b):
    p = list(range(len(b) + 1))
    for i, x in enumerate(a, 1):
        c = [i]
        for j, y in enumerate(b, 1):
            c.append(min(p[j] + 1, c[j - 1] + 1, p[j - 1] + (x != y)))
        p = c
    return p[-1]


def occ(t, p):
    n, i = 0, t.find(p)
    while i >= 0:
        n += 1
        i = t.find(p, i + 1)
    return n


def comps(V, adj, src=0, blocked=()):
    seen = [False] * V
    seen[src] = True
    q = deque([src])
    while q:
        u = q.popleft()
        for v in adj[u]:
            if not seen[v]:
                seen[v] = True
                q.append(v)
    return seen


def bfs(V, adj, s):
    d = [-1] * V
    d[s] = 0
    q = deque([s])
    while q:
        u = q.popleft()
        for v in adj[u]:
            if d[v] < 0:
                d[v] = d[u] + 1
                q.append(v)
    return d


def route_info(V, wadj, pen):
    INF = 10 ** 18
    dist = [INF] * V
    dist[0] = 0
    pq = [(0, 0)]
    while pq:
        d, u = heapq.heappop(pq)
        if d > dist[u]:
            continue
        for v, m in wadj[u]:
            if d + m + pen[v] < dist[v]:
                dist[v] = d + m + pen[v]
                heapq.heappush(pq, (dist[v], v))
    hop = [-1] * V
    hop[0] = 0
    hc = [INF] * V
    hc[0] = 0
    q = deque([0])
    while q:
        u = q.popleft()
        for v, m in wadj[u]:
            if hop[v] < 0:
                hop[v] = hop[u] + 1
                q.append(v)
            if hop[v] == hop[u] + 1:
                hc[v] = min(hc[v], hc[u] + m + pen[v])
    return dist, hop, hc


def win_opt(ws):
    ws = sorted(ws, key=lambda w: (w[1], w[0]))
    cnt, last = 0, -1
    for s, f, v in ws:
        if s >= last:
            cnt, last = cnt + 1, f
    fin = [w[1] for w in ws]
    dp = [0]
    for i, (s, f, v) in enumerate(ws):
        j = bisect.bisect_right(fin, s, 0, i)
        dp.append(max(dp[-1], dp[j] + v))
    return cnt, dp[-1]


def mlen(p, t):
    return sum(abs(p[t[i]][0] - p[t[(i + 1) % len(t)]][0]) + abs(p[t[i]][1] - p[t[(i + 1) % len(t)]][1]) for i in range(len(t)))


def nn(p, high):
    n = len(p)
    t, seen = [0], {0}
    while len(t) < n:
        c = t[-1]
        best = None
        for j in range(n):
            if j not in seen:
                d = abs(p[c][0] - p[j][0]) + abs(p[c][1] - p[j][1])
                if best is None or d < best[0] or (high and d == best[0]):
                    best = (d, j)
        seen.add(best[1])
        t.append(best[1])
    return t


def avg_overlap(ws):
    st = sorted(w[0] for w in ws)
    fi = sorted(w[1] for w in ws)
    tot = 0
    for s, f, _ in ws:
        tot += bisect.bisect_left(st, f) - bisect.bisect_right(fi, s) - 1
    return tot / len(ws)


# ---------------------------------------------------------------- reading
def read(path, errs):
    wb = load_workbook(path)
    if wb.sheetnames != list(HEAD):
        errs.append(f"V1: sheets are {wb.sheetnames}, expected the 20 sheets in order")
    data = {}
    for name, hd in HEAD.items():
        if name not in wb.sheetnames:
            continue
        ws = wb[name]
        if ws.merged_cells.ranges:
            errs.append(f"V1: merged cells in {name}")
        rows = list(ws.iter_rows(values_only=False))
        if not rows or [c.value for c in rows[0]] != hd or len(rows[0]) != len(hd):
            errs.append(f"V1: header of {name} wrong")
            continue
        out = []
        for r in rows[1:]:
            vals = [c.value for c in r]
            if all(v is None for v in vals):
                errs.append(f"V1: empty row in {name}")
                continue
            for c, h in zip(r, hd):
                v = c.value
                if c.data_type == "f":
                    errs.append(f"V1: formula in {name}")
                elif h in TEXT:
                    if not isinstance(v, str) or not v.isascii():
                        errs.append(f"V1: {name}.{h} not ASCII text ({v!r})")
                elif type(v) is not int:
                    errs.append(f"V1: {name}.{h} not an integer ({v!r})")
            out.append(tuple(vals))
        # sort order
        keys = [(r[0], r[1]) if isinstance(r[1], (int, str)) else (r[0],) for r in out]
        if keys != sorted(keys):
            errs.append(f"V1: rows of {name} not sorted by case_id and second column")
        data[name] = out
    return data


# ---------------------------------------------------------------- per case checks
def check_case(c, cs, partial):
    d = c.d
    bad = c.bad
    row = d["cases"][0]
    _, seed, k, tier, scn, cap, t0, t1, t2, ebound, tlen, snodes, sk, sv, rtarget = row
    tg = [t0, t1, t2]
    ti = TI.get(tier, 0)
    if c.cid != f"{seed}-{k:02d}":
        bad("V1", "case_id format")
    if tier != tier_of(k):
        bad("V1", "wrong tier for case_no")
    if scn != k % 6 + 1:
        bad("V1", "wrong scenario for case_no")
    # ---- crates
    cr = sorted(d["crates"])
    n = len(cr)
    lo, hi = R["crates"][ti]
    if k == 46: lo, hi = 1500, 3000
    if k == 47: lo, hi = 12, 60
    if not lo <= n <= hi: bad("V2", f"crate count {n}")
    if [r[1] for r in cr] != list(range(1, n + 1)): bad("V3", "crate_id not 1..n")
    for r in cr:
        if r[2] not in range(5) or not 1 <= r[3] <= 20 or not 10 <= r[4] <= 100 or not 0 <= r[5] <= 999:
            bad("V2", f"crate {r[1]} field out of range"); break
    ser = [r[6] for r in cr]
    if len(set(ser)) != n or any(not 10 ** 7 <= x <= 10 ** 8 - 1 for x in ser): bad("V2", "serials not distinct 8-digit")
    tw = sum(r[3] for r in cr)
    if not (cap >= 1 and 10 * cap >= tw and 10 * cap <= 7 * tw): bad("V2", "capacity outside 10%..70% of crate weight")
    # ---- locations & roads
    lc = sorted(d["locations"])
    V = len(lc)
    lo, hi = R["V"][ti]
    if k == 48: lo, hi = 1500, 3000
    if not lo <= V <= hi: bad("V2", f"location count {V}")
    if [r[1] for r in lc] != list(range(V)): bad("V3", "loc_id not 0..V-1")
    typ = [r[2] for r in lc]
    pen = [r[3] for r in lc]
    if any(t not in ("D", "S", "H", "J") for t in typ): bad("V2", "bad location type")
    if any(p not in (0, 1, 2, 4, 6) for p in pen): bad("V2", "penalty not in {0,1,2,4,6}")
    if V and (typ[0] != "D" or pen[0] != 0): bad("V3", "location 0 is not the HQ (D, penalty 0)")
    if "S" not in typ or "H" not in typ: bad("V3", "needs at least one S and one H")
    rd = sorted(d["roads"])
    E = len(rd)
    if [r[1] for r in rd] != list(range(E)): bad("V3", "road_no not 0..E-1")
    if not V - 1 <= E <= 3 * V: bad("V2", f"E={E} outside V-1..3V")
    pairs = set()
    adj = [[] for _ in range(V)]
    wadj = [[] for _ in range(V)]
    for r in rd:
        _, no, u, v, m, cb = r
        if not (0 <= u < v < V): bad("V3", f"road {no}: need 0<=u<v<V"); continue
        if (u, v) in pairs: bad("V3", f"road {no}: repeated pair")
        pairs.add((u, v))
        if not 1 <= m <= 60 or not 1 <= cb <= 100: bad("V2", f"road {no} minutes/cable range")
        adj[u].append(v); adj[v].append(u)
        wadj[u].append((v, m)); wadj[v].append((u, m))
    if V and not all(comps(V, adj)): bad("V4", "network not connected before closures")
    if len(set(tg)) != 3 or any(not (0 < t < V and typ[t] in "SH") for t in tg if isinstance(t, int)):
        bad("V3", "targets must be 3 distinct shelters/hospitals other than HQ")
    # ---- waves
    wv = defaultdict(list)
    for r in d["waves"]:
        wv[r[1]].append(r[2])
    nw = len(wv)
    if sorted(wv) != list(range(1, nw + 1)) or not 2 <= nw <= 5: bad("V2", "waves must be numbered 1..nw with nw in 2..5")
    allw = [x for w in wv.values() for x in w]
    if any(not 0 <= x < E for x in allw): bad("V3", "wave references a missing road")
    if len(allw) != len(set(allw)): bad("V4", "waves not disjoint")
    if any(not 1 <= len(w) <= max(1, E // 4) for w in wv.values()): bad("V4", "wave size outside 1..max(1,E/4)")
    # ---- radio
    parts = sorted(d["radio_log"])
    if [p[1] for p in parts] != list(range(1, len(parts) + 1)): bad("V5", "log parts not consecutive from 1")
    if any(len(p[2]) > 10000 or not p[2] for p in parts): bad("V5", "log part empty or over 10,000 symbols")
    log = "".join(p[2] for p in sorted(parts, key=lambda p: p[1]))
    if set(log) - ALPH: bad("V5", "log symbol outside the 38-symbol alphabet")
    lo, hi = R["log"][ti]
    if k == 49: lo, hi = 50000, 100000
    if not lo <= len(log) <= hi: bad("V2", f"log length {len(log)}")
    pt = sorted(d["radio_patterns"])
    if [p[1] for p in pt] != list(range(6)) or [len(p[2]) for p in pt] != [2, 4, 8, 12, 20, 40]:
        bad("V5", "patterns must be numbered 0..5 with lengths 2,4,8,12,20,40")
    cnts = []
    for p in pt:
        t = occ(log, p[2])
        cnts.append(t)
        if t != p[3]: bad("V5", f"pattern {p[1]} count {p[3]} but true count {t}")
    if sum(1 for x in cnts if x > 0) < 2 or all(x > 0 for x in cnts): bad("V5", "need >=2 occurring patterns and >=1 absent")
    ra, rb = d["radio_reports"][0][1:]
    lo, hi = R["report"][ti]
    if not (lo <= len(ra) <= hi and lo <= len(rb) <= hi): bad("V2", "report length")
    if (set(ra) | set(rb)) - ALPH: bad("V5", "report symbol outside alphabet")
    true_ed = edit(ra, rb)
    if not true_ed <= ebound <= len(ra) + len(rb): bad("V5", f"edit_bound {ebound} but true edit distance {true_ed}")
    # ---- windows
    ws = sorted(d["windows"])
    lo, hi = R["windows"][ti]
    if not lo <= len(ws) <= hi: bad("V2", "window count")
    if [w[1] for w in ws] != list(range(1, len(ws) + 1)): bad("V3", "window_id not 1..n")
    W = [(w[2], w[3], w[4]) for w in ws]
    if any(not (0 <= s < f <= 1440 and 5 <= f - s <= 480 and 1 <= v <= 100) for s, f, v in W): bad("V2", "window start/finish/duration/value range")
    if len(W) >= 8:
        fs = defaultdict(int)
        for s, f, v in W: fs[f] += 1
        touch = sum(fs[s] for s, f, v in W)
        if touch < 2: bad("V2", "fewer than two touching pairs")
    # ---- incidents
    inc = sorted(d["incidents"])
    lo, hi = R["alarms"][ti]
    if not lo <= len(inc) <= hi: bad("V2", "alarm count")
    if [a[1] for a in inc] != list(range(1, len(inc) + 1)): bad("V3", "alarm_id not 1..n")
    ticks = [a[2] for a in inc]; prs = [a[3] for a in inc]
    if not ticks or ticks[0] != 0 or any(ticks[i] > ticks[i + 1] for i in range(len(ticks) - 1)): bad("V3", "ticks must start at 0 and never decrease")
    if any(not 1 <= p <= 10 for p in prs): bad("V2", "priority range")
    rate = len(inc) / (ticks[-1] + 1) if ticks else 0
    if tier in "ML":
        if not 1.2 <= rate <= 1.8: bad("V2", f"alarms per tick {rate:.3f}")
        if len(set(prs)) < 6 or 1 not in prs: bad("V2", "need >=6 distinct priorities including 1")
    # ---- sites / tour
    st = sorted(d["sites"])
    ns = len(st)
    lo, hi = R["sites"][ti]
    if not lo <= ns <= hi: bad("V2", "site count")
    if [s[1] for s in st] != list(range(ns)): bad("V3", "site_no not 0..n-1")
    P = [(s[2], s[3]) for s in st]
    if any(not (0 <= x <= 999 and 0 <= y <= 999) for x, y in P) or len(set(P)) != ns: bad("V2", "site coordinates")
    tr = [t[2] for t in sorted(d["tour"])]
    if [t[1] for t in sorted(d["tour"])] != list(range(len(tr))): bad("V3", "tour steps not 0..n-1")
    if sorted(tr) != list(range(ns)) or tr[0] != 0: bad("V6", "tour is not a permutation starting at site 0")
    elif mlen(P, tr) != tlen: bad("V6", f"tour_length {tlen} but tour closes at {mlen(P, tr)}")
    elif tier in "LX" and tlen > min(mlen(P, nn(P, False)), mlen(P, nn(P, True))): bad("V6", "planted tour longer than nearest-neighbour tour")
    # ---- pipeline / drum
    dm = sorted(d["pipeline_dims"])
    lo, hi = R["stages"][ti]
    if not lo <= len(dm) - 1 <= hi: bad("V2", "pipeline stage count")
    if [x[1] for x in dm] != list(range(len(dm))): bad("V3", "pipeline idx not 0..n")
    if any(not 2 <= x[2] <= 100 for x in dm): bad("V2", "dimension range")
    dr = sorted(d["drum_prices"])
    lo, hi = R["drum"][ti]
    if not lo <= len(dr) <= hi: bad("V2", "drum length")
    if [x[1] for x in dr] != list(range(1, len(dr) + 1)): bad("V3", "drum lengths not 1..L")
    pr = [x[2] for x in dr]
    if any(not 1 <= p <= 500 for p in pr): bad("V2", "drum price range")
    if pr and all(pr[j - 1] == pr[0] * j for j in range(1, len(pr) + 1)): bad("V2", "drum prices all proportional to length")
    # ---- sensors
    lo, hi = R["sensor"][ti]
    if not lo <= snodes <= hi: bad("V2", "sensor node count")
    se = sorted((e[1], e[2]) for e in d["sensor_edges"])
    if any(not (0 <= u < v < snodes) for u, v in se) or len(set(se)) != len(se): bad("V3", "sensor edges invalid (u<v, in range, no repeats)")
    if len(se) < snodes - 1: bad("V2", "fewer than n-1 sensor edges")
    cov = [x[1] for x in d["sensor_cover"]]
    if len(cov) != sk or len(set(cov)) != sk or any(not 0 <= x < snodes for x in cov): bad("V3", "cover nodes invalid or not sensor_k distinct nodes")
    elif not (2 <= sk and 2 * sk <= snodes): bad("V2", "sensor_k outside 2..n/2")
    elif any(u not in cov and v not in cov for u, v in se): bad("V6", "planted cover misses an edge")
    # ---- safety
    lo, hi = R["switches"][ti]
    if not lo <= sv <= hi: bad("V2", "safety_vars range")
    rules = [tuple(r[2:5]) for r in sorted(d["safety_rules"])]
    if [r[1] for r in sorted(d["safety_rules"])] != list(range(1, len(rules) + 1)): bad("V3", "rule_no not 1..m")
    if any(0 in r or len({abs(x) for x in r}) != 3 or any(abs(x) > sv for x in r) for r in rules): bad("V3", "rule needs 3 non-zero literals on 3 different switches")
    ratio = len(rules) / sv if sv else 0
    if not 2.0 <= ratio <= 6.0: bad("V2", f"rules per switch {ratio:.2f}")
    pl = {x[1]: x[2] for x in d["safety_planted"]}
    if sorted(pl) != list(range(1, sv + 1)) or any(v not in (0, 1) for v in pl.values()): bad("V3", "safety_planted must give 0/1 for switches 1..n")
    elif any(not any((pl[abs(l)] == 1) == (l > 0) for l in r) for r in rules): bad("V6", "planted assignment violates a safety rule")
    # ---- rations
    rt = sorted(d["rations"])
    lo, hi = R["rations"][ti]
    if not lo <= len(rt) <= hi: bad("V2", "ration count")
    if [x[1] for x in rt] != list(range(len(rt))): bad("V3", "ration item not 0..n-1")
    if any(not 1 <= x[2] <= 1000 or x[3] not in (0, 1) for x in rt): bad("V2", "ration value/planted range")
    if rtarget <= 0 or sum(x[2] for x in rt if x[3] == 1) != rtarget: bad("V6", "planted rations do not sum to rations_target")
    # ---- claims
    cl = d["claims"]
    if tier == "S":
        if len(cl) != 1: bad("V5", "tier S needs exactly one claims row")
        else:
            _, c_cargo, c_wc, c_wv, c_dr, c_tour, c_cov = cl[0]
            if c_cargo != knap([(r[3], r[4]) for r in cr], cap): bad("V5", "cargo_opt wrong")
            wc, wvv = win_opt(W)
            if c_wc != wc: bad("V5", "window_count_opt wrong")
            if c_wv != wvv: bad("V5", "window_value_opt wrong")
            L = len(pr); b = [0] * (L + 1)
            for j in range(1, L + 1): b[j] = max(b[j - i] + pr[i - 1] for i in range(1, j + 1))
            if c_dr != b[L]: bad("V5", "drum_opt wrong")
            if c_tour != min(mlen(P, (0,) + p) for p in itertools.permutations(range(1, ns))): bad("V5", "tour_opt wrong")
            em = [(1 << u) | (1 << v) for u, v in se]
            cm = min(bin(m).count("1") for m in range(1 << snodes) if all(m & e for e in em))
            if c_cov != cm: bad("V5", "cover_min wrong")
    elif cl:
        bad("V5", "claims only exist for tier S")
    # ---- signature rules (cases 0..45)
    sig(c, k, scn, locals())
    if k >= 46:
        trap(c, k, locals())
    return dict(cr=cr, cap=cap, adj=adj, wadj=wadj, pen=pen, typ=typ, tg=tg, tier=tier, ratio=ratio, W=W, log=log, V=V)


def sig(c, k, scn, L):
    if k >= 46:
        return
    bad = c.bad
    V, E, typ, pen, cr, n, inc, prs, rate, W = (L[x] for x in "V E typ pen cr n inc prs rate W".split())
    adj, wv, tg, log = L["adj"], L["wv"], L["tg"], L["log"]
    ad = 2 * E / V if V else 0
    cat = lambda *cs: sum(1 for r in cr if r[2] in cs)
    if scn == 1:
        if not 2.2 <= ad <= 3.2: bad("V7", f"S1 avg degree {ad:.2f}")
        if 10 * sum(1 for p in pen if p >= 2) < 4 * V: bad("V7", "S1 under 40% locations with penalty>=2")
        if len(wv) < 3: bad("V7", "S1 needs >=3 waves")
        if 100 * cat(0, 1) < 55 * n: bad("V7", "S1 food+water under 55%")
    if scn == 2:
        if not 2.0 <= ad <= 2.6: bad("V7", f"S2 avg degree {ad:.2f}")
        if 100 * cat(2, 3) < 45 * n: bad("V7", "S2 medicine+tool under 45%")
        if sum(prs) < 6 * len(prs): bad("V7", "S2 mean alarm priority under 6.0")
    if scn == 3:
        if 4 * typ.count("S") < V: bad("V7", "S3 shelters under 25%")
        if len(wv) < 3: bad("V7", "S3 needs >=3 waves")
        if avg_overlap(W) < 2: bad("V7", "S3 mean window overlap under 2")
        if len(set(log)) < 30: bad("V7", "S3 log uses fewer than 30 symbols")
    if scn == 4:
        if ad < 3.5: bad("V7", f"S4 avg degree {ad:.2f}")
        if L["tier"] in "ML" and rate < 1.5: bad("V7", "S4 under 1.5 alarms per tick")
        if 10 * cat(4) < n: bad("V7", "S4 rare crates under 10%")
    if scn == 5:
        if ad > 2.4: bad("V7", f"S5 avg degree {ad:.2f}")
        if max(len(a) for a in adj) > 4: bad("V7", "S5 a location has more than 4 roads")
        dd = bfs(V, adj, 0)
        if max(dd) < V // 4: bad("V7", "S5 farthest location too close to HQ")
        if len(wv) < 3: bad("V7", "S5 needs >=3 waves")
        closed = {x for w in wv.values() for x in w}
        a2 = [[] for _ in range(V)]
        for r in sorted(L["d"]["roads"]):
            if r[1] not in closed:
                a2[r[2]].append(r[3]); a2[r[3]].append(r[2])
        seen = comps(V, a2)
        if all(seen[t] for t in tg if 0 <= t < V): bad("V7", "S5 all targets still reachable after all waves")
    if scn == 6:
        if 100 * cat(2, 1) < 55 * n: bad("V7", "S6 medicine+water under 55%")
        if 2 * sum(1 for r in cr if r[5] <= 300) < n: bad("V7", "S6 under half of crates expire by hour 300")
        if 4 * max(log.count(a) for a in set(log)) < len(log): bad("V7", "S6 no symbol reaches 25% of the log")


def mono(seq):
    return all(a <= b for a, b in zip(seq, seq[1:])) or all(a >= b for a, b in zip(seq, seq[1:]))


def trap(c, k, L):
    bad = c.bad
    cr, cap, log = L["cr"], L["cap"], L["log"]
    if k == 46:
        f = [[r[4] for r in cr], [r[3] for r in cr], [r[5] for r in cr], [r[6] for r in cr], [Fraction(r[4], r[3]) for r in cr]]
        if sum(mono(x) for x in f) < 3: bad("V8", "46: fewer than three monotone fields")
    if k == 47:
        items = [(r[1], r[3], r[4]) for r in cr]
        opt = knap([(w, v) for _, w, v in items], cap)
        if 100 * greedy(items, cap) > 60 * opt: bad("V8", "47: value-per-kg greedy reaches more than 60% of optimum")
    if k == 48:
        V, adj, wadj, pen, tg = L["V"], L["adj"], L["wadj"], L["pen"], L["tg"]
        d1 = bfs(V, adj, 0)
        a = d1.index(max(d1))
        if max(bfs(V, adj, a)) < 500: bad("V8", "48: longest distance under 500 roads")
        dist, hop, hc = route_info(V, wadj, pen)
        if not any(2 * hc[t] >= 3 * dist[t] for t in tg): bad("V8", "48: no target where fewest-roads routes cost >= 1.5x cheapest")
    if k == 49:
        N = len(log)
        if not any(sum(1 for i in range(N) if log[i] == log[i % p]) * 10 >= 9 * N for p in range(1, 9)): bad("V8", "49: under 90% repetition of one block of <=8 symbols")
        near = 0
        for r in sorted(L["d"]["radio_patterns"]):
            p = r[2]; m = len(p)
            if m < 2: continue
            hits = occ(log, p[:-1])
            if 2 * hits >= N - m + 1: near += 1
        if near < 4: bad("V8", f"49: only {near} near-miss patterns")


# ---------------------------------------------------------------- driver
def validate(path, partial=False):
    gerr = []
    data = read(path, gerr)
    cases = {}
    for name, rows in data.items():
        for r in rows:
            cases.setdefault(r[0], Case(r[0])).d[name].append(r)
    for r in data.get("cases", []):
        pass
    infos = {}
    ids = [r[0] for r in data.get("cases", [])]
    if not partial:
        want = None
        if len(ids) != 50 or len(set(ids)) != 50: gerr.append(f"V1: expected 50 distinct case_ids, found {len(ids)}")
    for cid, c in sorted(cases.items()):
        if len(c.d["cases"]) != 1:
            c.bad("V1", "case must have exactly one row in cases"); continue
        if any(not c.d[n] for n in ("crates", "locations", "roads", "radio_log", "radio_patterns", "radio_reports", "windows", "incidents", "sites", "tour", "pipeline_dims", "drum_prices", "sensor_edges", "sensor_cover", "safety_rules", "safety_planted", "rations")):
            c.bad("V1", "a sheet has no rows for this case"); continue
        try:
            infos[cid] = check_case_wrap(c, partial)
        except Exception as e:  # malformed data must be rejected, not crash
            c.bad("V1", f"data could not be processed ({type(e).__name__}: {e})")
    # global rules
    glob = list(gerr)
    if not partial and not glob:
        S = [(i, cid) for cid, i in infos.items() if i["tier"] == "S"]
        g1 = sum(1 for i, _ in S if greedy([(r[1], r[3], r[4]) for r in i["cr"]], i["cap"]) < knap([(r[3], r[4]) for r in i["cr"]], i["cap"]))
        if g1 < 5: glob.append(f"V7: only {g1} tier-S cases where value-per-kg greedy is not optimal (need 5)")
        g2 = 0
        for i, _ in S:
            dist, hop, hc = route_info(i["V"], i["wadj"], i["pen"])
            if any(hc[t] > dist[t] for t in i["tg"]): g2 += 1
        if g2 < 5: glob.append(f"V7: only {g2} tier-S cases where fewest-roads is not cheapest (need 5)")
        ml = [i["ratio"] for cid, i in infos.items() if i["tier"] in "ML"]
        if len(ml) != 26 or any(not 2.5 <= x <= 6.0 for x in ml): glob.append("V7: rules per switch outside 2.5..6.0 on tiers M/L")
        elif sum(x < 3.5 for x in ml) < 5 or sum(3.5 <= x <= 4.8 for x in ml) < 8 or sum(x > 4.8 for x in ml) < 5:
            glob.append("V7: rules per switch bands (<3.5, 3.5..4.8, >4.8) need 5, 8, 5 cases")
        glob += dup_modules(cases)
    return cases, glob


def check_case_wrap(c, partial):
    d = c.d
    # make the check functions see waves dict & rows
    info = check_case_inner(c, partial)
    return info


def check_case_inner(c, partial):
    # thin shim so sig()/trap() can read d, wv, rate, inc, prs, n, E via locals()
    import types
    src = check_case
    return src(c, None, partial)


def dup_modules(cases):
    mods = {"crates": 1, "locations": 1, "roads": 1, "radio_log": 1, "windows": 1, "incidents": 1, "sites": 1, "pipeline_dims": 1, "drum_prices": 1, "sensor_edges": 1, "safety_rules": 1, "rations": 1}
    out = []
    for m in mods:
        seen = {}
        for cid, c in cases.items():
            rows = tuple(r[1:] for r in sorted(c.d[m]))
            if len(rows) < 8:
                continue
            if rows in seen:
                out.append(f"V7: cases {seen[rows]} and {cid} are equal in module {m}")
            seen[rows] = cid
    return out


def main():
    path = sys.argv[1]
    partial = "--partial" in sys.argv
    cases, glob = validate(path, partial)
    ok = True
    for cid, c in sorted(cases.items()):
        if c.err:
            ok = False
            print(f"{cid} FAIL")
            for e in c.err:
                print("    " + e)
        else:
            print(f"{cid} PASS")
    if glob:
        ok = False
        print("GLOBAL FAIL")
        for e in glob:
            print("    " + e)
    else:
        print("GLOBAL PASS")
    print("RESULT: PASS" if ok else "RESULT: FAIL")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
