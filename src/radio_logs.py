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