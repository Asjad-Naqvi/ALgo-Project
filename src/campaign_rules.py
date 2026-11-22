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