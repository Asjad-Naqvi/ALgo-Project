"""Route planning for the open roads of a campaign day."""

from collections import deque
from dataclasses import dataclass
from heapq import heappop, heappush
from typing import FrozenSet, Optional, Tuple


@dataclass(frozen=True)
class Routes:
    cheapest_path: Optional[Tuple[int, ...]]
    cheapest_cost: Optional[int]
    reachable_ids: FrozenSet[int]
    fewest_roads_path: Optional[Tuple[int, ...]]


def _integer(row, field, minimum=0):
    value = row.get(field)
    if type(value) is not int or value < minimum:
        raise ValueError(f"{field} must be an integer >= {minimum}")
    return value


def _open_graph(locations, roads, source, target, blocked_road_ids):
    penalties = {}
    for location in locations:
        loc_id = _integer(location, "loc_id")
        if loc_id in penalties:
            raise ValueError(f"duplicate location ID {loc_id}")
        penalties[loc_id] = _integer(location, "penalty")
    for endpoint in (source, target):
        if type(endpoint) is not int or endpoint not in penalties:
            raise ValueError(f"unknown route endpoint {endpoint}")

    blocked = set()
    for road_id in blocked_road_ids:
        if type(road_id) is not int or road_id < 0:
            raise ValueError("blocked road IDs must be nonnegative integers")
        blocked.add(road_id)
    graph = {loc_id: [] for loc_id in penalties}
    road_ids = set()
    for road in roads:
        road_id = _integer(road, "road_no")
        u, v = _integer(road, "u"), _integer(road, "v")
        minutes = _integer(road, "minutes", 1)
        if road_id in road_ids:
            raise ValueError(f"duplicate road ID {road_id}")
        if u == v or u not in graph or v not in graph:
            raise ValueError(f"invalid endpoints for road {road_id}")
        road_ids.add(road_id)
        if road_id not in blocked:
            graph[u].append((v, minutes + penalties[v]))
            graph[v].append((u, minutes + penalties[u]))
    if blocked - road_ids:
        raise ValueError(f"unknown blocked road IDs: {sorted(blocked - road_ids)}")
    for neighbors in graph.values():
        neighbors.sort()
    return graph


def _bfs(graph, source):
    parents = {source: None}
    queue = deque([source])
    while queue:
        u = queue.popleft()
        for v, _ in graph[u]:
            if v not in parents:
                parents[v] = u
                queue.append(v)
    return parents


def _dijkstra(graph, source):
    distances = {source: 0}
    queue = [(0, source)]
    while queue:
        distance, u = heappop(queue)
        if distance != distances[u]:
            continue
        for v, cost in graph[u]:
            candidate = distance + cost
            if v not in distances or candidate < distances[v]:
                distances[v] = candidate
                heappush(queue, (candidate, v))
    return distances


def _bellman_ford(graph, source):
    distances = {source: 0}
    for _ in range(len(graph) - 1):
        changed = False
        for u, neighbors in graph.items():
            if u not in distances:
                continue
            for v, cost in neighbors:
                candidate = distances[u] + cost
                if v not in distances or candidate < distances[v]:
                    distances[v] = candidate
                    changed = True
        if not changed:
            break
    return distances


def _path(parents, target):
    path = []
    while target is not None:
        path.append(target)
        target = parents[target]
    return tuple(reversed(path))


def plan_routes(locations, roads, source, target, blocked_road_ids=(), *, baseline=False):
    """Return cheapest and fewest-roads paths as tuples of location IDs.

    Pass the full road table and the closed road IDs. An unreachable target
    has no paths or cost, but the result still contains the reachable set.
    """
    graph = _open_graph(locations, roads, source, target, blocked_road_ids)
    hops = _bfs(graph, source)
    reachable = frozenset(hops)
    if target not in reachable:
        return Routes(None, None, reachable, None)

    shortest = _bellman_ford if baseline else _dijkstra
    distances = shortest(graph, source)
    # Choose the lowest-ID predecessor among equally cheap steps.
    parents = {source: None}
    for u in reachable:
        for v, cost in graph[u]:
            if distances[u] + cost == distances[v] and (v not in parents or u < parents[v]):
                parents[v] = u
    return Routes(_path(parents, target), distances[target], reachable, _path(hops, target))
