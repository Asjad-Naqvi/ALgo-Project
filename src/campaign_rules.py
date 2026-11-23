def get_blocked_waves(day, num_waves):
    if not 1 <= day <= 7:
        raise ValueError("Invalid campaign day")

    if not 2 <= num_waves <= 5:
        raise ValueError("Invalid number of waves")

    if day == 1:
        return []

    if 2 <= day <= 5:
        return [(day - 2) % num_waves]

    return list(range(num_waves))

if __name__ == "__main__":
    print(get_blocked_waves(2, 3))
    print(get_blocked_waves(4, 3))
    print(get_blocked_waves(5, 3))
    print(get_blocked_waves(6, 3))

def get_destination_index(day):
    if not 1 <= day <= 7:
        raise ValueError("Invalid campaign day")

    return (day - 1) % 3


def is_loading_allowed(day):
    if not 1 <= day <= 7:
        raise ValueError("Invalid campaign day")

    return day != 7

def adjust_crate_value(day, category, value):
    if not 1 <= day <= 7:
        raise ValueError("Invalid campaign day")

    if day == 2 and category == 3:
        return value * 2  # Tools

    if day == 3 and category == 0:
        return value * 2  # Food

    if day == 5 and category == 2:
        return value * 3  # Medicine

    return value


def adjust_road_minutes(day, minutes):
    if not 1 <= day <= 7:
        raise ValueError("Invalid campaign day")

    if day == 2:
        return (3 * minutes + 1) // 2

    return minutes

def adjust_location_penalty(day, penalty):
    if not 1 <= day <= 7:
        raise ValueError("Invalid campaign day")

    if day == 4 and penalty >= 2:
        return penalty * 2

    return penalty


def is_window_available(day, window_id):
    if not 1 <= day <= 7:
        raise ValueError("Invalid campaign day")

    if window_id < 1:
        raise ValueError("Invalid window ID")

    return (window_id + day) % 5 != 0

def add_emergency_alarm(day, incidents):
    if not 1 <= day <= 7:
        raise ValueError("Invalid campaign day")

    updated = [dict(alarm) for alarm in incidents]

    if day in (2, 5):
        new_id = max(
            (alarm["alarm_id"] for alarm in updated),
            default=0
        ) + 1

        updated.append({
            "alarm_id": new_id,
            "tick": 0,
            "priority": 9 if day == 2 else 10
        })

    # Dispatch requires incidents in arrival order.
    updated.sort(
        key=lambda alarm: (alarm["tick"], alarm["alarm_id"])
    )

    return updated