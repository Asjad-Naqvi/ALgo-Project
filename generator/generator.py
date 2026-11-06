#!/usr/bin/env python3
"""LIFELINE case generator (Iteration 1).

Usage:  python generate.py --seed S --out cases.xlsx [--only K [K ...]]
All randomness is derived from the group seed S and the case number k.
"""
import argparse, bisect, heapq, itertools, math, random
from collections import deque
from fractions import Fraction
from openpyxl import Workbook

ALPH = [chr(c) for c in range(65, 91)] + [str(d) for d in range(10)] + ["_", "-"]

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

RNG = {  # (tier S, tier M, tier L/X)
 "crates": ((8, 20), (40, 200), (500, 1500)),
 "V": ((6, 12), (30, 150), (500, 2000)),
 "log": ((200, 500), (2000, 10000), (20000, 100000)),
 "report": ((10, 30), (30, 150), (200, 1000)),
 "windows": ((8, 20), (50, 300), (1000, 3000)),
 "alarms": ((10, 40), (200, 1000), (2000, 5000)),
 "sites": ((5, 9), (10, 16), (200, 500)),
 "stages": ((4, 8), (15, 60), (100, 300)),
 "drum": ((5, 14), (40, 200), (500, 2000)),
 "sensor": ((6, 14), (20, 40), (100, 400)),
 "switches": ((6, 15), (20, 50), (20, 50)),
 "rations": ((8, 20), (24, 40), (50, 100)),
}


def rr(s, k, name):
    return random.Random(f"LIFELINE|{s}|{k}|{name}")


def tier_of(k):
    return "S" if k < 20 else "M" if k < 40 else "L" if k < 46 else "X"


def tidx(t):
    return {"S": 0, "M": 1, "L": 2, "X": 2}[t]


# ---------------------------------------------------------------- exact helpers
def knap_opt(items, cap):
    best = [0] * (cap + 1)
    for w, v in items:
        for c in range(cap, w - 1, -1):
            nv = best[c - w] + v
            if nv > best[c]:
                best[c] = nv
    return best[cap]


def greedy_cargo(items, cap):  # items (crate_id, w, v)
    order = sorted(items, key=lambda t: (-Fraction(t[2], t[1]), t[0]))
    tot = 0
    for _, w, v in order:
        if w <= cap:
            cap -= w
            tot += v
    return tot


def win_opt(ws):
    ws = sorted(ws, key=lambda w: (w[1], w[0]))
    cnt, last = 0, -1
    for s, f, v in ws:
        if s >= last:
            cnt += 1
            last = f
    fin = [w[1] for w in ws]
    dp = [0] * (len(ws) + 1)
    for i, (s, f, v) in enumerate(ws, 1):
        j = bisect.bisect_right(fin, s, 0, i - 1)
        dp[i] = max(dp[i - 1], dp[j] + v)
    return cnt, dp[-1]


def drum_opt(prices):
    L = len(prices)
    best = [0] * (L + 1)
    for j in range(1, L + 1):
        best[j] = max(best[j - i] + prices[i - 1] for i in range(1, j + 1))
    return best[L]


def manh(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def tour_len(pts, t):
    return sum(manh(pts[t[i]], pts[t[(i + 1) % len(t)]]) for i in range(len(t)))


def tour_brute(pts):
    n = len(pts)
    best = None
    for p in itertools.permutations(range(1, n)):
        t = (0,) + p
        L = tour_len(pts, t)
        if best is None or L < best[0]:
            best = (L, list(t))
    return best


def nn_tour(pts, high=False):
    n = len(pts)
    seen = [False] * n
    seen[0] = True
    t = [0]
    while len(t) < n:
        c = t[-1]
        best = None
        for j in range(n):
            if not seen[j]:
                d = manh(pts[c], pts[j])
                if best is None or d < best[0] or (high and d == best[0]):
                    best = (d, j)
        seen[best[1]] = True
        t.append(best[1])
    return t


def two_opt(pts, t):
    n = len(t)
    D = [[manh(a, b) for b in pts] for a in pts]
    t = t[:]
    for _ in range(60):
        imp = False
        for i in range(1, n - 1):
            for j in range(i + 1, n):
                a, b, c, d = t[i - 1], t[i], t[j], t[(j + 1) % n]
                if D[a][c] + D[b][d] < D[a][b] + D[c][d]:
                    t[i:j + 1] = t[i:j + 1][::-1]
                    imp = True
        if not imp:
            break
    return t


def min_cover(n, edges):
    best = n
    em = [(1 << u) | (1 << v) for u, v in edges]
    for mask in range(1 << n):
        pc = bin(mask).count("1")
        if pc < best and all(mask & e for e in em):
            best = pc
    return best


def edit_dist(a, b):
    prev = list(range(len(b) + 1))
    for i in range(1, len(a) + 1):
        cur = [i] + [0] * len(b)
        ai = a[i - 1]
        for j in range(1, len(b) + 1):
            cur[j] = min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ai != b[j - 1]))
        prev = cur
    return prev[-1]


def count_occ(t, p):
    c, i = 0, t.find(p)
    while i != -1:
        c += 1
        i = t.find(p, i + 1)
    return c


def hop_vs_cost(V, adj, pen):
    """returns (dist, hops, hopcost): cheapest cost, fewest roads, cheapest cost among fewest-road routes."""
    INF = float("inf")
    dist = [INF] * V
    dist[0] = 0
    pq = [(0, 0)]
    while pq:
        d, u = heapq.heappop(pq)
        if d > dist[u]:
            continue
        for v, m in adj[u]:
            nd = d + m + pen[v]
            if nd < dist[v]:
                dist[v] = nd
                heapq.heappush(pq, (nd, v))
    hops = [-1] * V
    hops[0] = 0
    order = [0]
    hc = [INF] * V
    hc[0] = 0
    dq = deque([0])
    while dq:
        u = dq.popleft()
        for v, m in adj[u]:
            if hops[v] == -1:
                hops[v] = hops[u] + 1
                order.append(v)
                dq.append(v)
            if hops[v] == hops[u] + 1:
                hc[v] = min(hc[v], hc[u] + m + pen[v])
    return dist, hops, hc


# ---------------------------------------------------------------- crates
def pick_cats(rng, n, scn):
    req = {1: ([0, 1], 0.55), 2: ([2, 3], 0.45), 4: ([4], 0.10), 6: ([2, 1], 0.55)}
    cats = []
    if scn in req:
        grp, frac = req[scn]
        need = min(n, math.ceil(frac * n) + (1 if n < 40 else 0))
        cats = [rng.choice(grp) for _ in range(need)]
    cats += [rng.randrange(5) for _ in range(n - len(cats))]
    rng.shuffle(cats)
    return cats


def gen_crates(s, k, tier, scn):
    rng = rr(s, k, "crates")
    lo, hi = RNG["crates"][tidx(tier)]
    if k == 47:
        n = rng.randint(12, 14)
        items = [(1, 15)] + [(10, 100)] * 2 + [(rng.randint(10, 12), rng.randint(10, 25)) for _ in range(n - 3)]
        rng.shuffle(items)
        ser = rng.sample(range(10 ** 7, 10 ** 8), n)
        rows = [(i + 1, rng.randrange(5), w, v, rng.randint(0, 999), ser[i]) for i, (w, v) in enumerate(items)]
        return rows, 20
    designated = tier == "S" and k % 3 == 0
    for _ in range(4000):
        n = rng.randint(1500, 3000) if k == 46 else rng.randint(lo, hi)
        cats = pick_cats(rng, n, scn if k < 46 else 0)
        w = [rng.randint(1, 20) for _ in range(n)]
        v = [min(100, max(10, int(w[i] * rng.uniform(1.5, 6) + (20 if cats[i] == 4 else 0) + rng.randint(0, 15)))) for i in range(n)]
        ex = [rng.randint(0, 999) for _ in range(n)]
        if scn == 6 and k < 46:
            for i in rng.sample(range(n), min(n, n // 2 + 1)):
                ex[i] = rng.randint(0, 300)
        ser = rng.sample(range(10 ** 7, 10 ** 8), n)
        if k == 46:  # dock-order trap: value, expiry, serial non-decreasing in crate_id order
            v.sort(); ex.sort(); ser.sort()
        tot = sum(w)
        cap = rng.randint(max(1, math.ceil(tot * 0.15)), max(1, int(tot * 0.6)))
        if designated:
            items = [(i + 1, w[i], v[i]) for i in range(n)]
            if greedy_cargo(items, cap) >= knap_opt([(a, b) for _, a, b in items], cap):
                continue
        break
    rows = [(i + 1, cats[i], w[i], v[i], ex[i], ser[i]) for i in range(n)]
    return rows, cap


# ---------------------------------------------------------------- graph
def build_edges(rng, V, scn, k):
    """returns (sorted edge list, cut index or None)"""
    es = set()
    if k == 48:  # shortest-looks-cheapest trap: long chain with local chords
        for i in range(V - 1):
            es.add((i, i + 1))
        for i in range(V - 2):
            if i == 0 or rng.random() < 0.5:
                es.add((i, i + 2))
        return sorted(es), None
    if scn == 5 and k < 46:
        c = rng.randint(max(1, V // 3), min(V - 3, 2 * V // 3))
        for i in range(V - 1):
            es.add((i, i + 1))
        cands = [i for i in range(V - 2) if i not in (c - 1, c)]
        ne = rng.randint(0, min(len(cands), math.floor(1.2 * V) - (V - 1)))
        for i in rng.sample(cands, ne):
            es.add((i, i + 2))
        return sorted(es), c
    if scn == 1 and k < 46:
        lo_e, hi_e = math.ceil(1.1 * V), math.floor(1.6 * V)
    elif scn == 2 and k < 46:
        lo_e, hi_e = V, math.floor(1.3 * V)
    elif scn == 4 and k < 46:
        lo_e, hi_e = math.ceil(1.75 * V), min(3 * V, V * (V - 1) // 2)
    else:
        lo_e, hi_e = math.ceil(1.2 * V), math.floor(2.2 * V)
    E = rng.randint(lo_e, hi_e)
    for i in range(1, V):
        p = rng.randint(max(0, i - 6), i - 1)
        es.add((p, i))
    if E > 0.5 * V * (V - 1) / 2:
        miss = [(a, b) for a in range(V) for b in range(a + 1, V) if (a, b) not in es]
        for e in rng.sample(miss, E - len(es)):
            es.add(e)
    else:
        while len(es) < E:
            u = rng.randrange(V)
            if rng.random() < 0.7:
                v = u + 1 + int(rng.expovariate(1 / 4))
            else:
                v = rng.randrange(V)
            if v >= V or u == v:
                continue
            es.add((min(u, v), max(u, v)))
    return sorted(es), None


def gen_waves(rng, E, scn, k, cut_road):
    nw = rng.randint(3, 5) if (scn in (1, 3, 5) and k < 46) else rng.randint(2, 5)
    nw = min(nw, E - 1)
    cap = max(1, min(max(1, E // 4), max(3, E // 15)))
    sizes = [rng.randint(1, cap) for _ in range(nw)]
    while sum(sizes) > E - 1:
        i = sizes.index(max(sizes))
        sizes[i] -= 1
    pool = [r for r in range(E) if r != cut_road]
    pick = rng.sample(pool, sum(sizes))
    if cut_road is not None:
        pick[0] = cut_road
    waves, p = [], 0
    for sz in sizes:
        waves.append(sorted(pick[p:p + sz]))
        p += sz
    return waves


def gen_graph(s, k, tier, scn):
    rng = rr(s, k, "graph")
    lo, hi = RNG["V"][tidx(tier)]
    if k == 48:
        lo, hi = 1500, 3000
    need2 = tier == "S" and k in (0, 1, 2, 3, 5, 6, 7, 8)
    for _ in range(3000):
        V = rng.randint(lo, hi)
        edges, c = build_edges(rng, V, scn, k)
        E = len(edges)
        rng.shuffle(edges)
        # types
        types = ["J"] * V
        types[0] = "D"
        ids = list(range(1, V))
        rng.shuffle(ids)
        nS = max(2, math.ceil(0.3 * V))
        nH = max(1, round(0.12 * V))
        for i in ids[:nS]:
            types[i] = "S"
        for i in ids[nS:nS + nH]:
            types[i] = "H"
        pen = [rng.choices([0, 1, 2, 4, 6], [4, 3, 3, 2, 1])[0] for _ in range(V)]
        pen[0] = 0
        if scn == 1 and k < 46:
            need = math.ceil(0.45 * V) + 1
            while sum(1 for p in pen if p >= 2) < need:
                i = rng.randrange(1, V)
                if pen[i] < 2:
                    pen[i] = rng.choice([2, 4, 6])
        roads = [(u, v, rng.randint(1, 60), rng.randint(1, 100)) for u, v in edges]
        if k == 48:
            idx = {(u, v): i for i, (u, v, _, _) in enumerate(roads)}
            for (a, b), m in (((0, 1), 1), ((1, 2), 1), ((0, 2), 60)):
                i = idx[(a, b)]
                roads[i] = (a, b, m, roads[i][3])
            pen[1], pen[2], types[2] = 0, 6, "H"
        forced = []
        if k == 48:
            forced = [2]
        if c is not None:
            far = rng.randrange(c + 1, V)
            if types[far] in "JD":
                types[far] = rng.choice("SH")
            forced = [far]
        adj = [[] for _ in range(V)]
        for u, v, m, _ in roads:
            adj[u].append((v, m))
            adj[v].append((u, m))
        if need2:
            dist, hops, hc = hop_vs_cost(V, adj, pen)
            good = [v for v in range(1, V) if types[v] in "SH" and hc[v] > dist[v]]
            if not good:
                continue
            forced = [rng.choice(good)]
        tc = [v for v in range(1, V) if types[v] in "SH" and v not in forced]
        targets = forced + rng.sample(tc, 3 - len(forced))
        cut_road = None
        if c is not None:
            cut_road = next(i for i, (u, v, _, _) in enumerate(roads) if (u, v) == (c, c + 1))
        waves = gen_waves(rng, E, scn, k, cut_road)
        return dict(V=V, types=types, pen=pen, roads=roads, waves=waves, targets=targets)
    raise RuntimeError("graph generation failed for case %d" % k)


# ---------------------------------------------------------------- radio
def gen_log(rng, n, scn, k):
    if k == 49:
        N = rng.randint(50000, 100000)
        blk = rng.choice(ALPH[:26])
        mm = rng.choice([a for a in ALPH if a != blk])
        noise_al = [a for a in ALPH if a not in (blk, mm)]
        nz = int(N * rng.uniform(0.03, 0.07))
        n1 = rng.randint(nz // 3, 2 * nz // 3)
        seg = lambda m: "".join(rng.choices(noise_al, k=m))
        a = rng.randint(N // 5, N // 2)
        text = blk * a + seg(n1) + blk * (N - nz - a) + seg(nz - n1)
        return text, blk, mm
    for _ in range(300):
        if scn == 6 and k < 46:
            dom = rng.choice(ALPH)
            w = [0.34 if x == dom else 0.66 / 37 for x in ALPH]
        elif scn == 3 and k < 46:
            w = [1] * 38
        else:
            w = [1 / (i + 1) ** 0.8 for i in range(38)]
            rng.shuffle(w)
        arr = rng.choices(ALPH, weights=w, k=n)
        beac = ["".join(rng.choices(ALPH, weights=w, k=rng.randint(6, 25))) for _ in range(rng.randint(2, 5))]
        for _ in range(max(1, n // 80)):
            b = rng.choice(beac)
            p0 = rng.randrange(0, max(1, n - len(b)))
            b = b[:n - p0]
            arr[p0:p0 + len(b)] = list(b)
        text = "".join(arr)
        if scn == 3 and k < 46 and len(set(text)) < 30:
            continue
        if scn == 6 and k < 46 and max(text.count(a) for a in ALPH) < 0.27 * n:
            continue
        return text, None, None
    raise RuntimeError("log failed")


def gen_patterns(rng, text, k, blk, mm):
    if k == 49:
        return [blk * 2, blk * 4, blk * 7 + mm, blk * 11 + mm, blk * 19 + mm, blk * 39 + mm]
    lens = [2, 4, 8, 12, 20, 40]
    pats = []
    for i, L in enumerate(lens):
        absent = i == 5 or (i == 4 and rng.random() < 0.4)
        if not absent:
            p0 = rng.randrange(0, len(text) - L + 1)
            pats.append(text[p0:p0 + L])
        else:
            while True:
                p = "".join(rng.choices(ALPH, k=L))
                if text.find(p) == -1:
                    break
            pats.append(p)
    return pats


def gen_reports(rng, tier):
    lo, hi = RNG["report"][tidx(tier)]
    for _ in range(100):
        a = [rng.choice(ALPH) for _ in range(rng.randint(lo, hi))]
        b = a[:]
        for _ in range(rng.randint(1, max(2, len(a) // 4))):
            op = rng.randrange(3)
            if op == 0 and len(b) < hi:
                b.insert(rng.randint(0, len(b)), rng.choice(ALPH))
            elif op == 1 and len(b) > lo:
                del b[rng.randrange(len(b))]
            else:
                b[rng.randrange(len(b))] = rng.choice(ALPH)
        a, b = "".join(a), "".join(b)
        if lo <= len(b) <= hi:
            return a, b, edit_dist(a, b)
    raise RuntimeError("reports failed")


# ---------------------------------------------------------------- windows / incidents
def gen_windows(s, k, tier, scn):
    rng = rr(s, k, "win")
    lo, hi = RNG["windows"][tidx(tier)]
    for _ in range(1000):
        n = rng.randint(lo, hi)
        ws = []
        for _ in range(n - 3):
            if scn == 3 and k < 46:
                d = rng.randint(120, 480)
                st = rng.randint(200, 1440 - d)
            else:
                d = int(min(480, max(5, rng.triangular(5, 480, 90))))
                st = rng.randint(0, 1440 - d)
            ws.append([st, st + d, rng.randint(1, 100)])
        bases = [w for w in ws if w[1] <= 1430]
        for b in rng.sample(bases, 3):
            d = rng.randint(5, min(480, 1440 - b[1]))
            ws.append([b[1], b[1] + d, rng.randint(1, 100)])
        rng.shuffle(ws)
        if scn == 3 and k < 46 and tier != "L":
            tot = sum(1 for i in range(n) for j in range(n) if i != j and ws[i][0] < ws[j][1] and ws[j][0] < ws[i][1])
            if tot / n < 2.4:
                continue
        return ws
    raise RuntimeError("windows failed")


def gen_incidents(s, k, tier, scn):
    rng = rr(s, k, "inc")
    lo, hi = RNG["alarms"][tidx(tier)]
    ml = tier != "S"
    for _ in range(1000):
        c = rng.randint(lo, hi)
        if ml:
            r = rng.uniform(1.5, 1.75) if (scn == 4 and k < 46) else rng.uniform(1.25, 1.75)
            T1 = int(c // r)
        else:
            T1 = rng.randint(max(3, c // 3), c + 5)
        if scn == 2 and k < 46:
            cen = rng.sample(range(T1), max(2, T1 // 80))
            ticks = [min(T1 - 1, rng.choice(cen) + int(rng.expovariate(1 / 5))) if rng.random() < 0.7 else rng.randrange(T1) for _ in range(c)]
        else:
            ticks = [rng.randrange(T1) for _ in range(c)]
        ticks.sort()
        ticks[0], ticks[-1] = 0, T1 - 1
        wts = [1, 1, 1, 2, 3, 4, 5, 6, 6, 6] if (scn == 2 and k < 46) else [1] * 10
        pr = rng.choices(range(1, 11), wts, k=c)
        if ml:
            for pos, val in zip(rng.sample(range(c), 6), [1, 10, 9, 8, 7, 6]):
                pr[pos] = val
        if scn == 2 and k < 46 and sum(pr) < 6.2 * c:
            continue
        return [(i + 1, ticks[i], pr[i]) for i in range(c)]
    raise RuntimeError("incidents failed")


# ---------------------------------------------------------------- hard modules
def gen_sites(s, k, tier):
    rng = rr(s, k, "sites")
    lo, hi = RNG["sites"][tidx(tier)]
    n = rng.randint(lo, hi)
    pts = set()
    while len(pts) < n:
        pts.add((rng.randint(0, 999), rng.randint(0, 999)))
    pts = sorted(pts)
    rng.shuffle(pts)
    if tier == "S":
        L, t = tour_brute(pts)
        return pts, t, L
    nn = nn_tour(pts)
    t = two_opt(pts, nn)
    L = tour_len(pts, t)
    if tier in 'LX':
        assert L <= min(tour_len(pts, nn), tour_len(pts, nn_tour(pts, True)))
    return pts, t, L


def gen_sensor(s, k, tier):
    rng = rr(s, k, "sensor")
    lo, hi = RNG["sensor"][tidx(tier)]
    n = rng.randint(lo, hi)
    kk = rng.randint(max(2, n // 4), n // 2)
    cov = rng.sample(range(n), kk)
    non = [v for v in range(n) if v not in cov]
    es = set()
    mk = lambda a, b: (min(a, b), max(a, b))
    for i in range(1, kk):
        es.add(mk(cov[i], cov[rng.randrange(i)]))
    for v in non:
        es.add(mk(v, rng.choice(cov)))
    for _ in range(rng.randint(0, n)):
        a, b = rng.choice(cov), rng.randrange(n)
        if a != b:
            es.add(mk(a, b))
    return n, kk, sorted(cov), sorted(es)


def gen_safety(s, k, tier, cls):
    rng = rr(s, k, "safety")
    lo, hi = RNG["switches"][tidx(tier)]
    n = rng.randint(lo, hi)
    if k in cls:
        r = {"low": rng.uniform(2.7, 3.35), "mid": rng.uniform(3.7, 4.6), "high": rng.uniform(5.0, 5.8)}[cls[k]]
    else:
        r = rng.uniform(2.2, 5.8)
    m = min(6 * n, max(2 * n, round(r * n)))
    pl = [None] + [rng.randint(0, 1) for _ in range(n)]
    rules = []
    for _ in range(m):
        vs = rng.sample(range(1, n + 1), 3)
        lit = [v * rng.choice((1, -1)) for v in vs]
        if not any((pl[abs(l)] == 1) == (l > 0) for l in lit):
            j = rng.randrange(3)
            lit[j] = -lit[j]
        rules.append(lit)
    return n, rules, pl[1:]


def gen_rations(s, k, tier):
    rng = rr(s, k, "rations")
    lo, hi = RNG["rations"][tidx(tier)]
    n = rng.randint(lo, hi)
    vals = [rng.randint(1, 1000) for _ in range(n)]
    sel = set(rng.sample(range(n), rng.randint(max(2, n // 4), max(3, n // 2))))
    return vals, sel, sum(vals[i] for i in sel)


def gen_pipe_drum(s, k, tier):
    rng = rr(s, k, "pipe")
    n = rng.randint(*RNG["stages"][tidx(tier)])
    dims = [rng.randint(2, 100) for _ in range(n + 1)]
    L = rng.randint(*RNG["drum"][tidx(tier)])
    a = 450 / L ** 0.8
    pr = [max(1, min(500, int(a * j ** 0.8 * rng.uniform(0.85, 1.15)))) for j in range(1, L + 1)]
    if all(pr[j - 1] * 1 == pr[0] * j for j in range(1, L + 1)):
        pr[-1] += 1
    return dims, pr


# ---------------------------------------------------------------- one case
def safety_classes(s):
    r = random.Random(f"LIFELINE|{s}|safety")
    cl = ["low"] * 7 + ["mid"] * 11 + ["high"] * 8
    r.shuffle(cl)
    return {20 + i: c for i, c in enumerate(cl)}


def gen_case(s, k):
    cid = f"{s}-{k:02d}"
    tier, scn = tier_of(k), k % 6 + 1
    S = {name: [] for name in HEAD}
    crates, cap = gen_crates(s, k, tier, scn)
    for r in crates:
        S["crates"].append((cid,) + r)
    g = gen_graph(s, k, tier, scn)
    for i, (t, p) in enumerate(zip(g["types"], g["pen"])):
        S["locations"].append((cid, i, t, p))
    for i, (u, v, m, c) in enumerate(g["roads"]):
        S["roads"].append((cid, i, u, v, m, c))
    for wi, w in enumerate(g["waves"], 1):
        for r in w:
            S["waves"].append((cid, wi, r))
    rng = rr(s, k, "radio")
    text, blk, mm = gen_log(rng, rng.randint(*RNG["log"][tidx(tier)]) if k != 49 else 0, scn, k)
    for pi in range(0, len(text), 10000):
        S["radio_log"].append((cid, pi // 10000 + 1, text[pi:pi + 10000]))
    pats = gen_patterns(rng, text, k, blk, mm)
    for i, p in enumerate(pats):
        S["radio_patterns"].append((cid, i, p, count_occ(text, p)))
    ra, rb, eb = gen_reports(rng, tier)
    S["radio_reports"].append((cid, ra, rb))
    ws = gen_windows(s, k, tier, scn)
    for i, (a, b, v) in enumerate(ws, 1):
        S["windows"].append((cid, i, a, b, v))
    for a, t, p in gen_incidents(s, k, tier, scn):
        S["incidents"].append((cid, a, t, p))
    pts, t, tl = gen_sites(s, k, tier)
    for i, (x, y) in enumerate(pts):
        S["sites"].append((cid, i, x, y))
    for i, v in enumerate(t):
        S["tour"].append((cid, i, v))
    dims, pr = gen_pipe_drum(s, k, tier)
    for i, d in enumerate(dims):
        S["pipeline_dims"].append((cid, i, d))
    for j, p in enumerate(pr, 1):
        S["drum_prices"].append((cid, j, p))
    sn, sk, cov, ses = gen_sensor(s, k, tier)
    for u, v in ses:
        S["sensor_edges"].append((cid, u, v))
    for c in cov:
        S["sensor_cover"].append((cid, c))
    sv, rules, pl = gen_safety(s, k, tier, safety_classes(s))
    for i, r in enumerate(rules, 1):
        S["safety_rules"].append((cid, i) + tuple(r))
    for i, v in enumerate(pl, 1):
        S["safety_planted"].append((cid, i, v))
    vals, sel, target = gen_rations(s, k, tier)
    for i, v in enumerate(vals):
        S["rations"].append((cid, i, v, 1 if i in sel else 0))
    S["cases"].append((cid, s, k, tier, scn, cap) + tuple(g["targets"]) + (eb, tl, sn, sk, sv, target))
    if tier == "S":
        items = [(r[3], r[4]) for r in crates]
        wc, wv = win_opt([tuple(w) for w in ws])
        S["claims"].append((cid, knap_opt([(r[2], r[3]) for r in crates], cap), wc, wv, drum_opt(pr), tl, min_cover(sn, ses)))
    return S


def build(s, only=None):
    ks = list(range(50)) if only is None else only
    allS = {name: [] for name in HEAD}
    for k in ks:
        S = gen_case(s, k)
        for name in HEAD:
            allS[name].extend(S[name])
    return allS


def write(allS, path):
    wb = Workbook()
    wb.remove(wb.active)
    for name in HEAD:
        ws = wb.create_sheet(name)
        ws.append(HEAD[name])
        for r in allS[name]:
            ws.append(list(r))
    wb.save(path)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, required=True)
    ap.add_argument("--out", default="cases.xlsx")
    ap.add_argument("--only", type=int, nargs="*")
    a = ap.parse_args()
    write(build(a.seed, a.only), a.out)
    print("wrote", a.out)
