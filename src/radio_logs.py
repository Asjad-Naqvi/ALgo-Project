def naive_search(text, pattern):
    if not pattern:
        raise ValueError("Pattern cannot be empty")

    positions = []
    n = len(text)
    m = len(pattern)

    for i in range(n - m + 1):
        match = True

        for j in range(m):
            if text[i + j] != pattern[j]:
                match = False
                break

        if match:
            positions.append(i)

    return positions

def compute_lps(pattern):
    m = len(pattern)
    lps = [0] * m

    length = 0
    i = 1

    while i < m:
        if pattern[i] == pattern[length]:
            length += 1
            lps[i] = length
            i += 1

        elif length != 0:
            length = lps[length - 1]

        else:
            lps[i] = 0
            i += 1

    return lps

def kmp_search(text, pattern):
    if not pattern:
        raise ValueError("Pattern cannot be empty")

    n = len(text)
    m = len(pattern)

    lps = compute_lps(pattern)

    positions = []
    i = 0
    j = 0

    while i < n:
        if text[i] == pattern[j]:
            i += 1
            j += 1

        if j == m:
            positions.append(i - j)
            j = lps[j - 1]

        elif i < n and text[i] != pattern[j]:
            if j != 0:
                j = lps[j - 1]
            else:
                i += 1

    return positions

def edit_distance_with_script(source, target):
    if not isinstance(source, str) or not isinstance(target, str):
        raise TypeError("Reports must be strings")

    n = len(source)
    m = len(target)

    dp = [[0] * (m + 1) for _ in range(n + 1)]

    for i in range(n, -1, -1):
        dp[i][m] = n - i

    for j in range(m, -1, -1):
        dp[n][j] = m - j

    for i in range(n - 1, -1, -1):
        for j in range(m - 1, -1, -1):
            if source[i] == target[j]:
                dp[i][j] = dp[i + 1][j + 1]
            else:
                dp[i][j] = 1 + min(
                    dp[i + 1][j + 1],
                    dp[i + 1][j],
                    dp[i][j + 1]
                )

    operations = []
    i = j = 0

    while i < n or j < m:
        if (
            i < n and j < m
            and source[i] == target[j]
            and dp[i][j] == dp[i + 1][j + 1]
        ):
            i += 1
            j += 1

        elif (
            i < n and j < m
            and dp[i][j] == 1 + dp[i + 1][j + 1]
        ):
            operations.append({
                "operation": "replace",
                "index": j,
                "character": target[j]
            })
            i += 1
            j += 1

        elif i < n and dp[i][j] == 1 + dp[i + 1][j]:
            operations.append({
                "operation": "delete",
                "index": j
            })
            i += 1

        else:
            operations.append({
                "operation": "insert",
                "index": j,
                "character": target[j]
            })
            j += 1

    return dp[0][0], operations


def _edit_distance_row(a, a_start, a_end,
                       b, b_start, b_end, reverse=False):
    width = b_end - b_start
    previous = list(range(width + 1))

    for i in range(a_end - a_start):
        char_a = (
            a[a_end - 1 - i]
            if reverse else a[a_start + i]
        )

        current = [i + 1] + [0] * width

        for j in range(width):
            char_b = (
                b[b_end - 1 - j]
                if reverse else b[b_start + j]
            )

            current[j + 1] = min(
                previous[j + 1] + 1,
                current[j] + 1,
                previous[j] + (char_a != char_b)
            )

        previous = current

    return previous


def hirschberg_edit_script(source, target):
    if not isinstance(source, str) or not isinstance(target, str):
        raise TypeError("Reports must be strings")

    alignment = []

    def small_alignment(a_start, a_end, b_start, b_end):
        n = a_end - a_start
        m = b_end - b_start

        dp = [[0] * (m + 1) for _ in range(n + 1)]

        for i in range(n + 1):
            dp[i][0] = i

        for j in range(m + 1):
            dp[0][j] = j

        for i in range(1, n + 1):
            for j in range(1, m + 1):
                dp[i][j] = min(
                    dp[i - 1][j] + 1,
                    dp[i][j - 1] + 1,
                    dp[i - 1][j - 1] + (
                        source[a_start + i - 1]
                        != target[b_start + j - 1]
                    )
                )

        pairs = []
        i, j = n, m

        while i > 0 or j > 0:
            if (
                i > 0 and j > 0
                and source[a_start + i - 1]
                    == target[b_start + j - 1]
                and dp[i][j] == dp[i - 1][j - 1]
            ):
                pairs.append((
                    source[a_start + i - 1],
                    target[b_start + j - 1]
                ))
                i -= 1
                j -= 1

            elif (
                i > 0 and j > 0
                and dp[i][j] == dp[i - 1][j - 1] + 1
            ):
                pairs.append((
                    source[a_start + i - 1],
                    target[b_start + j - 1]
                ))
                i -= 1
                j -= 1

            elif i > 0 and dp[i][j] == dp[i - 1][j] + 1:
                pairs.append((source[a_start + i - 1], None))
                i -= 1

            else:
                pairs.append((None, target[b_start + j - 1]))
                j -= 1

        alignment.extend(reversed(pairs))

    def align(a_start, a_end, b_start, b_end):
        n = a_end - a_start
        m = b_end - b_start

        if n == 0:
            alignment.extend(
                (None, target[j])
                for j in range(b_start, b_end)
            )
            return

        if m == 0:
            alignment.extend(
                (source[i], None)
                for i in range(a_start, a_end)
            )
            return

        if n == 1 or m == 1:
            small_alignment(a_start, a_end, b_start, b_end)
            return

        a_mid = a_start + n // 2

        left_costs = _edit_distance_row(
            source, a_start, a_mid,
            target, b_start, b_end
        )

        right_costs = _edit_distance_row(
            source, a_mid, a_end,
            target, b_start, b_end,
            reverse=True
        )

        split = min(
            range(m + 1),
            key=lambda j: left_costs[j] + right_costs[m - j]
        )

        del left_costs, right_costs

        b_mid = b_start + split

        align(a_start, a_mid, b_start, b_mid)
        align(a_mid, a_end, b_mid, b_end)

    align(0, len(source), 0, len(target))

    operations = []
    position = 0

    for old, new in alignment:
        if old is None:
            operations.append({
                "operation": "insert",
                "index": position,
                "character": new
            })
            position += 1

        elif new is None:
            operations.append({
                "operation": "delete",
                "index": position
            })

        elif old != new:
            operations.append({
                "operation": "replace",
                "index": position,
                "character": new
            })
            position += 1

        else:
            position += 1

    return len(operations), operations