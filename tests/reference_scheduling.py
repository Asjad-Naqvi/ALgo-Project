def exhaustive_scheduling(windows):
    n = len(windows)

    if n > 18:
        raise ValueError("Too many windows for exhaustive search")

    best_count = 0
    best_value = 0

    for mask in range(1 << n):
        selected = []

        for i in range(n):
            if mask & (1 << i):
                selected.append(windows[i])

        selected.sort(key=lambda w: (
            w["start"], w["finish"], w["window_id"]
        ))

        valid = True

        for i in range(1, len(selected)):
            if selected[i]["start"] < selected[i - 1]["finish"]:
                valid = False
                break

        if valid:
            count = len(selected)
            value = sum(w["value"] for w in selected)

            best_count = max(best_count, count)
            best_value = max(best_value, value)

    return best_count, best_value