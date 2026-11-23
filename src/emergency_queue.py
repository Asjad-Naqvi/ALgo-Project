class MaxHeap:
    def __init__(self):
        self.heap = []

    def higher_priority(self, a, b):
        if a["priority"] != b["priority"]:
            return a["priority"] > b["priority"]

        if a["tick"] != b["tick"]:
            return a["tick"] < b["tick"]

        return a["alarm_id"] < b["alarm_id"]

    def push(self, alarm):
        self.heap.append(alarm)
        i = len(self.heap) - 1

        while i > 0:
            parent = (i - 1) // 2

            if not self.higher_priority(
                self.heap[i], self.heap[parent]
            ):
                break

            self.heap[i], self.heap[parent] = (
                self.heap[parent], self.heap[i]
            )
            i = parent

    def pop(self):
        if not self.heap:
            return None

        result = self.heap[0]
        last = self.heap.pop()

        if not self.heap:
            return result

        self.heap[0] = last
        i = 0
        n = len(self.heap)

        while True:
            left = 2 * i + 1
            right = 2 * i + 2
            best = i

            if left < n and self.higher_priority(
                self.heap[left], self.heap[best]
            ):
                best = left

            if right < n and self.higher_priority(
                self.heap[right], self.heap[best]
            ):
                best = right

            if best == i:
                break

            self.heap[i], self.heap[best] = (
                self.heap[best], self.heap[i]
            )
            i = best

        return result

class LinearScanQueue:
    def __init__(self):
        self.alarms = []

    def higher_priority(self, a, b):
        if a["priority"] != b["priority"]:
            return a["priority"] > b["priority"]

        if a["tick"] != b["tick"]:
            return a["tick"] < b["tick"]

        return a["alarm_id"] < b["alarm_id"]

    def push(self, alarm):
        self.alarms.append(alarm)

    def pop(self):
        if not self.alarms:
            return None

        best = 0

        for i in range(1, len(self.alarms)):
            if self.higher_priority(
                self.alarms[i], self.alarms[best]
            ):
                best = i

        return self.alarms.pop(best)

def dispatch_alarms(incidents, algorithm="heap"):
    if algorithm == "heap":
        queue = MaxHeap()
    elif algorithm == "scan":
        queue = LinearScanQueue()
    else:
        raise ValueError("Unknown queue algorithm")

    seen_ids = set()
    previous_tick = -1

    for alarm in incidents:
        if not 1 <= alarm["priority"] <= 10:
            raise ValueError("Invalid alarm priority")

        if alarm["tick"] < previous_tick or alarm["tick"] < 0:
            raise ValueError("Incidents must be ordered by tick")

        if alarm["alarm_id"] in seen_ids:
            raise ValueError("Duplicate alarm ID")

        seen_ids.add(alarm["alarm_id"])
        previous_tick = alarm["tick"]

    released = []
    current_tick = 0
    index = 0
    pending_count = 0

    while index < len(incidents) or pending_count > 0:

        # Add every alarm that has arrived.
        while (
            index < len(incidents)
            and incidents[index]["tick"] <= current_tick
        ):
            queue.push(incidents[index])
            pending_count += 1
            index += 1

        # Answer at most one alarm per tick.
        if pending_count > 0:
            alarm = queue.pop()
            pending_count -= 1

            released.append({
                "release_tick": current_tick,
                "alarm_id": alarm["alarm_id"],
                "arrival_tick": alarm["tick"],
                "priority": alarm["priority"]
            })

        current_tick += 1

    return released