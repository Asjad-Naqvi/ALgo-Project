from src.inventory import optimal_load, greedy_load
from src.routing import plan_routes

from src.campaign_rules import (
    get_blocked_waves,
    get_destination_index,
    is_loading_allowed,
    adjust_crate_value,
    adjust_road_minutes,
    adjust_location_penalty,
    is_window_available,
    add_emergency_alarm,
)

from src.rescue_scheduling import (
    greedy_max_windows,
    weighted_interval_scheduling,
)

from src.emergency_queue import dispatch_alarms


def prepare_day(case, day, origin=0):
    """
    Prepare independent inputs for one campaign day.

    case: CaseData returned by load_master()
    day: 1 through 7
    origin: starting location for this day
    """
    if not 1 <= day <= 7:
        raise ValueError("Campaign day must be 1 through 7")

    # The dataset uses one-based wave numbers.
    wave_rows = case.tables.get("waves", ())
    wave_numbers = sorted({
        row["wave_no"] for row in wave_rows
    })

    blocked_indices = get_blocked_waves(
        day, len(wave_numbers)
    )

    blocked_wave_numbers = [
        wave_numbers[i] for i in blocked_indices
    ]

    # Find original road IDs closed on this day.
    closed_roads = {
        row["road_no"]
        for row in wave_rows
        if row["wave_no"] in blocked_wave_numbers
    }

    # Adjust road travel times without changing base data.
    roads = []

    for original in case.tables.get("roads", ()):
        road = dict(original)
        road["minutes"] = adjust_road_minutes(
            day, road["minutes"]
        )
        roads.append(road)

    open_roads = [
        road for road in roads
        if road["road_no"] not in closed_roads
    ]

    crates = []

    for original in case.tables.get("crates", ()):
        crate = dict(original)
        crate["value"] = adjust_crate_value(
            day, crate["cat"], crate["value"]
        )
        crates.append(crate)

    locations = []

    for original in case.tables.get("locations", ()):
        location = dict(original)
        location["penalty"] = adjust_location_penalty(
            day, location["penalty"]
        )
        locations.append(location)

    windows = [
        dict(window)
        for window in case.tables.get("windows", ())
        if is_window_available(day, window["window_id"])
    ]

    incidents = add_emergency_alarm(
        day, case.tables.get("incidents", ())
    )

    target_index = get_destination_index(day)

    return {
        "case_id": case.case_id,
        "day": day,
        "origin": origin,
        "target_index": target_index,
        "target": case.metadata[f"target_{target_index}"],
        "capacity": case.metadata["capacity"],
        "blocked_wave_numbers": blocked_wave_numbers,
        "closed_road_nos": sorted(closed_roads),
        "roads": roads,
        "open_roads": open_roads,
        "crates": crates,
        "locations": locations,
        "windows": windows,
        "incidents": incidents,
        "loading_allowed": is_loading_allowed(day),
        "evacuation_only": day == 7,
    }


def evaluate_local_day(day_inputs, queue_algorithm="heap"):
    """
    Execute our scheduling and emergency queue modules
    using prepared campaign inputs.
    """
    count_selection = greedy_max_windows(
        day_inputs["windows"]
    )

    value_selection = weighted_interval_scheduling(
        day_inputs["windows"]
    )

    alarm_dispatch = dispatch_alarms(
        day_inputs["incidents"],
        algorithm=queue_algorithm
    )

    return {
        "window_count": len(count_selection),
        "count_window_ids": [
            window["window_id"]
            for window in count_selection
        ],
        "window_value": sum(
            window["value"]
            for window in value_selection
        ),
        "value_window_ids": [
            window["window_id"]
            for window in value_selection
        ],
        "alarm_dispatch": alarm_dispatch,
    }

def run_campaign(case, mode="primary"):
    """
    Execute all seven campaign days.

    Primary: Dijkstra, optimal knapsack, heap queue.
    Baseline: Bellman-Ford, greedy load, scan queue.
    """

    if mode not in ("primary", "baseline"):
        raise ValueError("Invalid campaign mode")

    baseline = mode == "baseline"
    current_location = 0
    results = []

    for day in range(1, 8):
        inputs = prepare_day(
            case, day, origin=current_location
        )

        # Calculate route using the day's road conditions.
        route = plan_routes(
            inputs["locations"],
            inputs["roads"],
            current_location,
            inputs["target"],
            inputs["closed_road_nos"],
            baseline=baseline,
        )

        reachable = route.cheapest_path is not None

        # Default: no crates loaded.
        selected_crates = []
        load_weight = 0
        load_value = 0

        # Loading requires a reachable destination.
        # Day 7 never permits loading.
        if reachable and inputs["loading_allowed"]:
            load_algorithm = (
                greedy_load if baseline else optimal_load
            )

            load = load_algorithm(
                inputs["crates"],
                inputs["capacity"],
            )

            selected_crates = list(load.crate_ids)
            load_weight = load.total_weight
            load_value = load.total_value

        # Run rescue scheduling and emergency dispatch.
        local_result = evaluate_local_day(
            inputs,
            queue_algorithm="scan" if baseline else "heap",
        )

        # Move only if the destination is reachable.
        if reachable:
            current_location = inputs["target"]

        results.append({
            "case_id": case.case_id,
            "day": day,
            "mode": mode,
            "origin": inputs["origin"],
            "target": inputs["target"],
            "end_location": current_location,
            "status": (
                "completed" if reachable else "unreachable"
            ),
            "closed_road_nos": inputs["closed_road_nos"],
            "cheapest_path": (
                list(route.cheapest_path)
                if reachable else None
            ),
            "route_cost": route.cheapest_cost,
            "fewest_roads_path": (
                list(route.fewest_roads_path)
                if route.fewest_roads_path is not None
                else None
            ),
            "loading_allowed": inputs["loading_allowed"],
            "selected_crates": selected_crates,
            "load_weight": load_weight,
            "load_value": load_value,
            "window_count": local_result["window_count"],
            "window_value": local_result["window_value"],
            "count_window_ids": local_result["count_window_ids"],
            "value_window_ids": local_result["value_window_ids"],
            "alarm_dispatch": local_result["alarm_dispatch"],
        })

    return results