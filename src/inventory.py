"""Truck-loading algorithms for Module A."""

from dataclasses import dataclass
from functools import cmp_to_key
from typing import Iterable, Mapping, Tuple


@dataclass(frozen=True)
class Load:
    crate_ids: Tuple[int, ...]
    total_weight: int
    total_value: int


@dataclass(frozen=True)
class _Crate:
    crate_id: int
    weight: int
    value: int


def _prepare(rows: Iterable[Mapping[str, int]], capacity: int):
    if type(capacity) is not int or capacity < 0:
        raise ValueError("capacity must be a nonnegative integer")
    crates = []
    seen = set()
    for row in rows:
        try:
            crate = _Crate(row["crate_id"], row["weight"], row["value"])
        except (KeyError, TypeError) as error:
            raise ValueError("each crate needs crate_id, weight and value") from error
        if (
            type(crate.crate_id) is not int or crate.crate_id < 1
            or type(crate.weight) is not int or crate.weight < 1
            or type(crate.value) is not int or crate.value < 0
        ):
            raise ValueError("crate IDs and weights must be positive integers and values nonnegative integers")
        if crate.crate_id in seen:
            raise ValueError(f"duplicate crate ID {crate.crate_id}")
        seen.add(crate.crate_id)
        if crate.weight <= capacity and crate.value > 0:
            crates.append(crate)
    return sorted(crates, key=lambda crate: crate.crate_id)


def _load(selected):
    return Load(
        tuple(sorted(crate.crate_id for crate in selected)),
        sum(crate.weight for crate in selected),
        sum(crate.value for crate in selected),
    )


def optimal_load(rows: Iterable[Mapping[str, int]], capacity: int) -> Load:
    """Solve 0/1 knapsack in O(n log n + nW) time with traceback.

    On equal value prefer omitting the largest ID at which the loads differ.
    """
    crates = _prepare(rows, capacity)
    capacity = min(capacity, sum(crate.weight for crate in crates))
    values = [0] * (capacity + 1)
    decisions = []
    for crate in crates:
        taken = bytearray(capacity + 1)
        for remaining in range(capacity, crate.weight - 1, -1):
            candidate = crate.value + values[remaining - crate.weight]
            if candidate > values[remaining]:
                values[remaining] = candidate
                taken[remaining] = 1
        decisions.append(taken)

    selected = []
    remaining = capacity
    for crate, taken in zip(reversed(crates), reversed(decisions)):
        if taken[remaining]:
            selected.append(crate)
            remaining -= crate.weight
    return _load(selected)


def _compare_ratio(left, right):
    difference = right.value * left.weight - left.value * right.weight
    if difference:
        return -1 if difference < 0 else 1
    return left.crate_id - right.crate_id


def greedy_load(rows: Iterable[Mapping[str, int]], capacity: int) -> Load:
    """Try crates in descending exact value-to-weight ratio order."""
    crates = _prepare(rows, capacity)
    selected = []
    for crate in sorted(crates, key=cmp_to_key(_compare_ratio)):
        if crate.weight <= capacity:
            selected.append(crate)
            capacity -= crate.weight
    return _load(selected)


def exhaustive_load(rows: Iterable[Mapping[str, int]], capacity: int) -> Load:
    """Enumerate feasible subsets as an exact reference for small cases."""
    crates = list(reversed(_prepare(rows, capacity)))
    selected = []
    best = []
    best_value = 0

    def visit(index, remaining, value):
        nonlocal best, best_value
        if index == len(crates):
            if value > best_value:
                best = selected.copy()
                best_value = value
            return
        crate = crates[index]
        visit(index + 1, remaining, value)
        if crate.weight <= remaining:
            selected.append(crate)
            visit(index + 1, remaining - crate.weight, value + crate.value)
            selected.pop()

    visit(0, capacity, 0)
    return _load(best)
