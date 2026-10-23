"""
Surplus Food Rescue Matcher
DSA Case Study - matches food donations to the nearest suitable NGO
before the food expires, most urgent donation first.

Custom classes : IndexedMinHeap, FoodRescueSystem
heapq          : used ONLY inside dijkstra()
"""

import heapq
from collections import deque

INF = float("inf")
PICKUP_BUFFER = 15  # minutes needed for packing and pickup


# ----------------------------------------------------------------------
# 1. PRIMARY DATA STRUCTURE: handwritten indexed binary min-heap
# ----------------------------------------------------------------------
class IndexedMinHeap:
    """Binary min-heap of (expiry_time, donation_id) + a position dictionary."""

    # O(1): create an empty heap list and empty position dictionary
    def __init__(self):
        self.heap = []   # list of (priority, id) tuples
        self.pos = {}    # id -> index of that id inside self.heap

    # O(1): number of entries in the heap
    def __len__(self):
        return len(self.heap)

    # O(1): True when the heap has no entries
    def is_empty(self):
        return len(self.heap) == 0

    # O(1): dictionary membership test, no heap scan needed
    def contains(self, id):
        return id in self.pos

    # O(1): swap two heap slots and fix the position of BOTH ids
    def _swap(self, i, j):
        self.heap[i], self.heap[j] = self.heap[j], self.heap[i]
        self.pos[self.heap[i][1]] = i
        self.pos[self.heap[j][1]] = j

    # O(log n): move an entry up while it is smaller than its parent
    def _sift_up(self, i):
        while i > 0:
            parent = (i - 1) // 2
            # tuple comparison: smaller expiry first, then smaller id
            if self.heap[i] < self.heap[parent]:
                self._swap(i, parent)
                i = parent
            else:
                break

    # O(log n): move an entry down while a child is smaller than it
    def _sift_down(self, i):
        n = len(self.heap)
        while True:
            smallest = i
            left, right = 2 * i + 1, 2 * i + 2
            if left < n and self.heap[left] < self.heap[smallest]:
                smallest = left
            if right < n and self.heap[right] < self.heap[smallest]:
                smallest = right
            if smallest == i:
                break
            self._swap(i, smallest)
            i = smallest

    # O(log n): add a new entry at the end and sift it up
    def push(self, id, priority):
        if self.contains(id):          # avoid duplicate ids in the heap
            self.update_priority(id, priority)
            return
        self.heap.append((priority, id))
        self.pos[id] = len(self.heap) - 1
        self._sift_up(len(self.heap) - 1)

    # O(log n): remove and return the root (most urgent) entry, or None
    def pop_min(self):
        if self.is_empty():
            return None
        return self.remove(self.heap[0][1])

    # O(log n): remove any id using its stored index, or None if absent
    def remove(self, id):
        if not self.contains(id):      # safe on empty heap / unknown id
            return None
        i = self.pos[id]
        last = len(self.heap) - 1
        if i != last:
            self._swap(i, last)        # move target to the end
        entry = self.heap.pop()        # O(1) removal from list end
        del self.pos[id]
        if i < len(self.heap):         # repair the slot that was filled
            self._sift_up(i)
            self._sift_down(i)
        return entry

    # O(log n): change an id's priority, then sift in the needed direction
    def update_priority(self, id, new_priority):
        if not self.contains(id):
            return False
        i = self.pos[id]
        old_priority = self.heap[i][0]
        self.heap[i] = (new_priority, id)
        if new_priority < old_priority:
            self._sift_up(i)
        else:
            self._sift_down(i)
        return True


# ----------------------------------------------------------------------
# 2. DIJKSTRA (the only place heapq is used)
# ----------------------------------------------------------------------
def dijkstra(graph, source):
    """Shortest travel time from source to every location (INF if unreachable)."""
    dist = {node: INF for node in graph}
    if source not in graph:
        return dist
    dist[source] = 0
    pq = [(0, source)]
    while pq:
        d, node = heapq.heappop(pq)
        if d > dist[node]:             # stale queue entry, skip it
            continue
        for neighbour, minutes in graph[node]:
            new_d = d + minutes
            if new_d < dist[neighbour]:
                dist[neighbour] = new_d
                heapq.heappush(pq, (new_d, neighbour))
    return dist


# ----------------------------------------------------------------------
# 3. THE SYSTEM
# ----------------------------------------------------------------------
class FoodRescueSystem:
    def __init__(self):
        self.graph = {}                  # adjacency list: place -> [(place, minutes)]
        self.heap = IndexedMinHeap()     # pending donations by urgency
        self.donations = {}              # donation_id -> donation dict
        self.ngos = {}                   # ngo_id -> ngo dict
        self.events = deque(maxlen=5)    # last five important events
        self.matched = []                # matched records
        self.expired = []                # expired records
        self.current_time = 0            # simulated clock in minutes
        self._build_map()
        self._load_ngos()

    # ---------- fixed data ----------
    def _build_map(self):
        places = ["Hotel_Sun", "Hostel_A", "WeddingHall", "Cafe_Blue",
                  "Market", "NGO_Hope", "NGO_Care", "NGO_Seva", "Island"]
        for p in places:
            self.graph[p] = []           # Island keeps an empty list (isolated)
        roads = [
            ("Hotel_Sun", "Market", 10), ("Hotel_Sun", "NGO_Hope", 20),
            ("Hostel_A", "Market", 15), ("Hostel_A", "NGO_Care", 10),
            ("WeddingHall", "Market", 25), ("WeddingHall", "NGO_Seva", 30),
            ("Cafe_Blue", "NGO_Care", 35), ("Cafe_Blue", "Hostel_A", 5),
            ("Market", "NGO_Seva", 20), ("NGO_Hope", "NGO_Care", 40),
        ]
        for a, b, minutes in roads:      # undirected: store both directions
            self.graph[a].append((b, minutes))
            self.graph[b].append((a, minutes))

    def _load_ngos(self):
        self.ngos = {
            1: {"name": "NGO_Hope", "location": "NGO_Hope", "capacity": 50},
            2: {"name": "NGO_Care", "location": "NGO_Care", "capacity": 30},
            3: {"name": "NGO_Seva", "location": "NGO_Seva", "capacity": 100},
        }

    # ---------- helpers ----------
    def log(self, message):
        text = f"[t={self.current_time}] {message}"
        self.events.append(text)
        print("   EVENT:", text)

    def _valid(self, location, meals, expiry_time):
        if location not in self.graph:
            return "unknown location"
        if meals <= 0:
            return "meals must be positive"
        if expiry_time <= self.current_time:
            return "expiry time must be in the future"
        return None

    # ---------- donation operations ----------
    def add_donation(self, did, location, meals, expiry_time):
        if did in self.donations:
            print(f"   Rejected: donation {did} already exists")
            return
        error = self._valid(location, meals, expiry_time)
        if error:
            print(f"   Rejected donation {did}: {error}")
            return
        self.donations[did] = {"id": did, "location": location, "meals": meals,
                               "expiry_time": expiry_time, "status": "PENDING"}
        self.heap.push(did, expiry_time)
        print(f"   Added D{did}: {meals} meals at {location}, expires t={expiry_time}")

    def update_donation(self, did, location=None, meals=None, expiry_time=None):
        d = self.donations.get(did)
        if d is None:
            print(f"   Update rejected: donation {did} does not exist")
            return
        if d["status"] != "PENDING":
            print(f"   Update rejected: D{did} is already {d['status']}")
            return
        new_loc = d["location"] if location is None else location
        new_meals = d["meals"] if meals is None else meals
        new_exp = d["expiry_time"] if expiry_time is None else expiry_time
        error = self._valid(new_loc, new_meals, new_exp)
        if error:
            print(f"   Update rejected for D{did}: {error}")
            return
        if new_exp != d["expiry_time"]:
            self.heap.update_priority(did, new_exp)   # keep heap order correct
        d["location"], d["meals"], d["expiry_time"] = new_loc, new_meals, new_exp
        self.log(f"D{did} updated -> {new_meals} meals at {new_loc}, expires t={new_exp}")

    def cancel_donation(self, did):
        d = self.donations.get(did)
        if d is None:
            print(f"   Cancel rejected: donation {did} does not exist")
            return
        if d["status"] != "PENDING":
            print(f"   Cancel rejected: D{did} is already {d['status']}")
            return
        self.heap.remove(did)
        d["status"] = "CANCELLED"
        self.log(f"D{did} cancelled")

    def advance_clock(self, minutes):
        if minutes <= 0:
            print("   Clock not changed: minutes must be positive")
            return
        self.current_time += minutes
        print(f"   Clock advanced by {minutes} min -> now t={self.current_time}")

    def _expire(self, d, reason):
        d["status"] = "EXPIRED"
        self.expired.append({"donation_id": d["id"], "reason": reason})
        self.log(f"D{d['id']} EXPIRED ({reason})")

    # ---------- core matching ----------
    def run_matching(self):
        count = len(self.heap)           # process at most this many (no infinite loop)
        if count == 0:
            print("   No pending donations - heap is empty, nothing to process.")
            return
        print(f"   Processing {count} donation(s) in expiry order at t={self.current_time}")
        still_pending = []               # re-inserted AFTER the loop

        for _ in range(count):
            entry = self.heap.pop_min()
            if entry is None:
                break
            expiry, did = entry
            d = self.donations[did]
            print(f"\n   -> D{did} ({d['meals']} meals, {d['location']}, expires t={expiry})")

            if self.current_time >= expiry:
                self._expire(d, "expiry time already passed")
                continue

            dist = dijkstra(self.graph, d["location"])
            best_id, best_time = None, INF
            deadline_possible = False   # can ANY reachable NGO make the deadline?

            # NGO ids were inserted as 1, 2, 3, so the smaller id is checked first
            # and wins a travel-time tie (strict < below). One O(G) scan.
            for ngo_id in self.ngos:
                ngo = self.ngos[ngo_id]
                travel = dist[ngo["location"]]
                if travel == INF:
                    continue
                if self.current_time + travel + PICKUP_BUFFER <= expiry:
                    deadline_possible = True
                    if ngo["capacity"] >= d["meals"] and travel < best_time:
                        best_id, best_time = ngo_id, travel
                print(f"      {ngo['name']}: travel {travel} min, capacity {ngo['capacity']}")

            if best_id is not None:
                ngo = self.ngos[best_id]
                ngo["capacity"] -= d["meals"]
                d["status"] = "MATCHED"
                self.matched.append({"donation_id": did, "ngo_id": best_id,
                                     "travel_time": best_time})
                self.log(f"D{did} MATCHED to {ngo['name']} (travel {best_time} min)")
            elif deadline_possible:
                still_pending.append(did)
                self.log(f"D{did} left PENDING (no NGO has {d['meals']} meals capacity)")
            elif all(dist[n["location"]] == INF for n in self.ngos.values()):
                self._expire(d, f"no NGO reachable from {d['location']}")
            else:
                self._expire(d, f"no NGO reachable before expiry with {PICKUP_BUFFER}-min buffer")

        # Re-insert pending ones now so they are not popped again in this same run.
        for did in still_pending:
            self.heap.push(did, self.donations[did]["expiry_time"])

    # ---------- display ----------
    def show_ngos(self):
        print("   NGO capacities left:",
              ", ".join(f"{n['name']}={n['capacity']}" for n in self.ngos.values()))

    def show_status(self):
        print("   Donation statuses:")
        for did in sorted(self.donations):
            d = self.donations[did]
            print(f"      D{did}: {d['status']:<9} {d['meals']:>3} meals  "
                  f"{d['location']:<11} expires t={d['expiry_time']}")

    def show_report(self):
        print("   Matched records:")
        for r in self.matched:
            print(f"      D{r['donation_id']} -> {self.ngos[r['ngo_id']]['name']} "
                  f"(NGO {r['ngo_id']}), travel {r['travel_time']} min")
        print("   Expired records:")
        for r in self.expired:
            print(f"      D{r['donation_id']}: {r['reason']}")
        print("   Last 5 events:")
        for e in self.events:
            print("      " + e)


# ----------------------------------------------------------------------
# 4. DEMONSTRATION
# ----------------------------------------------------------------------
def section(title):
    print("\n" + "=" * 64 + f"\n{title}\n" + "=" * 64)


def main():
    system = FoodRescueSystem()

    section("STEP 1: Load predefined donations (t=0)")
    # D3, D1, D2 share expiry 60 and are added out of order on purpose:
    # the heap must still process them as D1, D2, D3 (id tie-break).
    system.add_donation(3, "Cafe_Blue", 20, 60)
    system.add_donation(1, "Hotel_Sun", 40, 60)
    system.add_donation(2, "Hostel_A", 25, 60)
    system.add_donation(4, "WeddingHall", 120, 200)  # too big for any NGO at first
    system.add_donation(5, "WeddingHall", 10, 40)    # fails only because of buffer
    system.add_donation(6, "Island", 5, 100)         # unreachable donor
    system.add_donation(7, "Market", 15, 150)        # will be cancelled
    system.add_donation(8, "Hotel_Sun", 10, 30)      # expiry will be extended
    system.add_donation(9, "Hostel_A", 90, 70)       # waits, then expires by time
    system.add_donation(10, "Nowhere", 5, 50)        # invalid location -> rejected
    system.show_ngos()

    section("STEP 2: Update and cancel before matching")
    system.update_donation(8, expiry_time=90)         # priority update in heap
    system.cancel_donation(7)                         # O(log n) remove by id
    system.update_donation(5, meals=-3)               # invalid -> rejected

    section("STEP 3: Matching round 1 (t=0)")
    system.run_matching()
    system.show_ngos()
    system.show_status()

    section("STEP 4: Update pending D4 and try to change finished donations")
    system.update_donation(4, meals=70)               # meal-count update
    system.cancel_donation(1)                         # MATCHED -> rejected
    system.update_donation(7, meals=20)               # CANCELLED -> rejected

    section("STEP 5: Advance clock 30 min and run matching round 2")
    system.advance_clock(30)
    system.run_matching()
    system.show_ngos()

    section("STEP 6: Advance clock 50 min and run matching round 3")
    system.advance_clock(50)
    system.run_matching()

    section("STEP 7: Boundary cases - empty heap")
    system.run_matching()
    print("   pop_min() on empty heap returns:", system.heap.pop_min())
    print("   remove(99) of unknown id returns:", system.heap.remove(99))
    print("   contains(4) after matching:", system.heap.contains(4))

    section("FINAL REPORT")
    system.show_ngos()
    system.show_status()
    system.show_report()


if __name__ == "__main__":
    main()
