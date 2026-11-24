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