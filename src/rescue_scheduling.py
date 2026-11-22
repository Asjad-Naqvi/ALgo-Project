def merge_sort(windows):
    if len(windows) <= 1:
        return windows[:]

    mid = len(windows) // 2

    left = merge_sort(windows[:mid])
    right = merge_sort(windows[mid:])

    merged = []
    i = j = 0

    while i < len(left) and j < len(right):
        key_left = (left[i]["finish"], left[i]["window_id"])
        key_right = (right[j]["finish"], right[j]["window_id"])

        if key_left <= key_right:
            merged.append(left[i])
            i += 1
        else:
            merged.append(right[j])
            j += 1

    merged.extend(left[i:])
    merged.extend(right[j:])

    return merged


def greedy_max_windows(windows):
    for window in windows:
        if window["start"] >= window["finish"]:
            raise ValueError("Invalid rescue window")

    sorted_windows = merge_sort(windows)

    selected = []
    last_finish = -1

    for window in sorted_windows:
        if window["start"] >= last_finish:
            selected.append(window)
            last_finish = window["finish"]

    return selected

def weighted_interval_scheduling(windows):
    if not windows:
        return []

    for w in windows:
        if w["start"] >= w["finish"] or w["value"] <= 0:
            raise ValueError("Invalid rescue window")

    sorted_windows = merge_sort(windows)
    n = len(sorted_windows)

    # Find the last compatible window for each window
    p = [0] * (n + 1)

    for i in range(1, n + 1):
        start = sorted_windows[i - 1]["start"]

        low, high = 0, i - 1

        while low < high:
            mid = (low + high) // 2

            if sorted_windows[mid]["finish"] <= start:
                low = mid + 1
            else:
                high = mid

        p[i] = low

    # Dynamic Programming
    dp = [0] * (n + 1)

    for i in range(1, n + 1):
        value = sorted_windows[i - 1]["value"]

        include = value + dp[p[i]]
        exclude = dp[i - 1]

        dp[i] = max(include, exclude)

    # Reconstruct selected windows
    selected = []
    i = n

    while i > 0:
        value = sorted_windows[i - 1]["value"]

        if value + dp[p[i]] > dp[i - 1]:
            selected.append(sorted_windows[i - 1])
            i = p[i]
        else:
            i -= 1

    selected.reverse()
    return selected