"""Minimum-cost cable planning for the open-road component of HQ."""

from collections import defaultdict
from dataclasses import dataclass
from heapq import heapify, heappop, heappush
from typing import Tuple

from .routing import _integer


@dataclass(frozen=True)
class CablePlan:
    road_ids: Tuple[int, ...]
    total_cost: int


def _kruskal(edges, locations):
    parent = {node: node for node in locations}
    size = dict.fromkeys(locations, 1)

    def find(node):
        while node != parent[node]:
            parent[node] = parent[parent[node]]
            node = parent[node]
        return node

    for cost, road_id, u, v in sorted(edges):
        left, right = find(u), find(v)
        if left == right:
            continue
        if size[left] < size[right]:
            left, right = right, left
        parent[right] = left
        size[left] += size[right]
        yield cost, road_id


def _prim(edges, source):
    graph = defaultdict(list)
    for cost, road_id, u, v in edges:
        graph[u].append((cost, road_id, v))
        graph[v].append((cost, road_id, u))
    visited = {source}
    queue = graph[source].copy()
    heapify(queue)
    while queue:
        cost, road_id, node = heappop(queue)
        if node in visited:
            continue
        visited.add(node)
        yield cost, road_id
        for edge in graph[node]:
            if edge[2] not in visited:
                heappush(queue, edge)


def plan_cable(open_roads, reachable_ids, source=0, *, baseline=False):
    """Span the supplied HQ component using Kruskal or the Prim baseline."""
    locations = set(reachable_ids)
    if source not in locations:
        raise ValueError("reachable locations must include HQ")

    edges = []
    seen = set()
    for row in open_roads:
        road_id = _integer(row, "road_no")
        u, v = _integer(row, "u"), _integer(row, "v")
        cost = _integer(row, "cable", 1)
        if road_id in seen or u == v:
            raise ValueError(f"invalid or duplicate cable road {road_id}")
        seen.add(road_id)
        if u in locations and v in locations:
            edges.append((cost, road_id, u, v))

    chosen = list(_prim(edges, source) if baseline else _kruskal(edges, locations))
    if len(chosen) != len(locations) - 1:
        raise ValueError("open roads do not connect all supplied locations")
    return CablePlan(tuple(sorted(road_id for _, road_id in chosen)),
                     sum(cost for cost, _ in chosen))
