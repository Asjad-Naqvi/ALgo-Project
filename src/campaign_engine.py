
from src.inventory import optimal_load, greedy_load
from src.routing import plan_routes
from src.cable import plan_cable

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

    case: CaseData returned by the master data loader
    day: 1 through 7
    origin: current truck location
    """
    if not 1 <= day <= 7:
        raise ValueError("Campaign day must be 1 through 7")

    # Read closure waves from the original case.
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

    # Identify roads closed on this day.
    closed_roads = {
        row["road_no"]
        for row in wave_rows
        if row["wave_no"] in blocked_wave_numbers
    }

    # Module B: Apply daily road-time adjustments.
    roads = []

    for original in case.tables.get("roads", ()):
        road = dict(original)

        road["minutes"] = adjust_road_minutes(
            day, road["minutes"]
        )

        roads.append(road)

    # Module F: Roads available for cable planning.
    open_roads = [
        road for road in roads
        if road["road_no"] not in closed_roads
    ]

    # Module A: Apply daily crate-value adjustments.
    crates = []

    for original in case.tables.get("crates", ()):
        crate = dict(original)

        crate["value"] = adjust_crate_value(
            day,
            crate["cat"],
            crate["value"],
        )

        crates.append(crate)

    # Module B: Apply daily location penalties.
    locations = []

    for original in case.tables.get("locations", ()):
        location = dict(original)

        location["penalty"] = adjust_location_penalty(
            day,
            location["penalty"],
        )

        locations.append(location)

    # Module C: Filter unavailable rescue windows.
    windows = [
        dict(window)
        for window in case.tables.get("windows", ())
        if is_window_available(
            day, window["window_id"]
        )
    ]

    # Module D: Add special emergency alarms.
    incidents = add_emergency_alarm(
        day,
        case.tables.get("incidents", ()),
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
    Execute rescue scheduling and emergency dispatch.

    Module C:
        Greedy maximum-count scheduling
        Weighted interval scheduling

    Module D:
        Heap or linear-scan emergency queue
    """

    count_selection = greedy_max_windows(
        day_inputs["windows"]
    )

    value_selection = weighted_interval_scheduling(
        day_inputs["windows"]
    )

    alarm_dispatch = dispatch_alarms(
        day_inputs["incidents"],
        algorithm=queue_algorithm,
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
    Execute the complete seven-day campaign.

    Primary algorithms:
        A: Optimal 0/1 Knapsack
        B: Dijkstra
        C: Greedy and Weighted Interval Scheduling
        D: Binary Max-Heap
        F: Kruskal MST

    Baseline algorithms:
        A: Greedy Knapsack
        B: Bellman-Ford
        C: Same scheduling objectives
        D: Linear Scan Queue
        F: Prim MST

    The truck starts at HQ (location 0).

    The truck moves only when the day's target
    is reachable.

    Cable planning always uses the component
    connected to HQ (location 0).

    Day 7 is evacuation-only: no cargo loading.
    """

    if mode not in ("primary", "baseline"):
        raise ValueError(
            "Invalid campaign mode. "
            "Choose 'primary' or 'baseline'."
        )

    baseline = mode == "baseline"

    current_location = 0
    results = []

    for day in range(1, 8):

        # -----------------------------------------
        # STEP 1: Prepare daily campaign inputs
        # -----------------------------------------

        inputs = prepare_day(
            case,
            day,
            origin=current_location,
        )

        # -----------------------------------------
        # STEP 2: Module B - Route Planning
        # -----------------------------------------

        route = plan_routes(
            inputs["locations"],
            inputs["roads"],
            current_location,
            inputs["target"],
            inputs["closed_road_nos"],
            baseline=baseline,
        )

        reachable = route.cheapest_path is not None

        # -----------------------------------------
        # STEP 3: Module F - Cable Planning
        # -----------------------------------------

        # Determine the component connected to HQ.
        # HQ is location 0, even when the truck
        # is somewhere else.

        hq_route = plan_routes(
            inputs["locations"],
            inputs["roads"],
            0,
            0,
            inputs["closed_road_nos"],
            baseline=baseline,
        )

        # Select a minimum-cost cable network
        # within the HQ-connected component.

        cable_plan = plan_cable(
            inputs["open_roads"],
            hq_route.reachable_ids,
            source=0,
            baseline=baseline,
        )

        # -----------------------------------------
        # STEP 4: Module A - Truck Loading
        # -----------------------------------------

        selected_crates = []
        load_weight = 0
        load_value = 0

        # Loading is allowed only when:
        # 1. The destination is reachable.
        # 2. The day permits cargo loading.

        if reachable and inputs["loading_allowed"]:

            load_algorithm = (
                greedy_load
                if baseline
                else optimal_load
            )

            load = load_algorithm(
                inputs["crates"],
                inputs["capacity"],
            )

            selected_crates = list(
                load.crate_ids
            )

            load_weight = load.total_weight
            load_value = load.total_value

        # -----------------------------------------
        # STEP 5: Modules C and D
        # Rescue Scheduling + Emergency Queue
        # -----------------------------------------

        local_result = evaluate_local_day(
            inputs,
            queue_algorithm=(
                "scan" if baseline else "heap"
            ),
        )

        # -----------------------------------------
        # STEP 6: Update Truck Location
        # -----------------------------------------

        # If the target cannot be reached,
        # the truck remains at its current location.

        if reachable:
            current_location = inputs["target"]

        # -----------------------------------------
        # STEP 7: Record Complete Daily Results
        # -----------------------------------------

        results.append({

            # Campaign information
            "case_id": case.case_id,
            "day": day,
            "mode": mode,

            "origin": inputs["origin"],
            "target": inputs["target"],
            "end_location": current_location,

            "status": (
                "completed"
                if reachable
                else "unreachable"
            ),

            # Road closures
            "closed_road_nos": inputs[
                "closed_road_nos"
            ],

            # Module B: Routing results
            "cheapest_path": (
                list(route.cheapest_path)
                if reachable
                else None
            ),

            "route_cost": route.cheapest_cost,

            "reachable_ids": sorted(
                route.reachable_ids
            ),

            "fewest_roads_path": (
                list(route.fewest_roads_path)
                if route.fewest_roads_path is not None
                else None
            ),

            # Module F: Cable planning results
            "hq_reachable_ids": sorted(
                hq_route.reachable_ids
            ),

            "cable_road_ids": list(
                cable_plan.road_ids
            ),

            "cable_cost": cable_plan.total_cost,

            # Module A: Inventory results
            "loading_allowed": inputs[
                "loading_allowed"
            ],

            "selected_crates": selected_crates,
            "load_weight": load_weight,
            "load_value": load_value,

            # Module C: Rescue scheduling results
            "window_count": local_result[
                "window_count"
            ],

            "window_value": local_result[
                "window_value"
            ],

            "count_window_ids": local_result[
                "count_window_ids"
            ],

            "value_window_ids": local_result[
                "value_window_ids"
            ],

            # Module D: Emergency dispatch results
            "alarm_dispatch": local_result[
                "alarm_dispatch"
            ],
        })

    return results
