"""
test_matching.py - unittest suite for the Surplus Food Rescue Matcher.
Run from the same folder as main.py:  python -m unittest -v
(If the main file is not called main.py, change the import below.)
"""
import io
import unittest
from contextlib import redirect_stdout

from main import IndexedMinHeap, dijkstra, FoodRescueSystem, INF   # <- change 'main' if needed


def quiet(func, *args, **kwargs):
    """Run a function and hide its printed output."""
    with redirect_stdout(io.StringIO()):
        return func(*args, **kwargs)


def new_system(*donations):
    """Fresh system; each donation is (id, location, meals, expiry_time)."""
    s = FoodRescueSystem()
    for d in donations:
        quiet(s.add_donation, *d)
    return s


def match(s):
    quiet(s.run_matching)


def heap_valid(h):
    """Position dict matches the list and every parent <= its children."""
    if len(h.heap) != len(h.pos):
        return False
    return all(h.pos.get(did) == i and (i == 0 or h.heap[(i - 1) // 2] <= h.heap[i])
               for i, (_, did) in enumerate(h.heap))


class TestIndexedMinHeap(unittest.TestCase):

    def test_pop_order_with_tie_break(self):
        h = IndexedMinHeap()
        for did, p in [(3, 60), (1, 60), (5, 40), (2, 90)]:
            h.push(did, p)
        self.assertEqual([h.pop_min()[1] for _ in range(4)], [5, 1, 3, 2])

    def test_update_priority_both_directions(self):
        h = IndexedMinHeap()
        for did, p in [(1, 50), (2, 60), (3, 70)]:
            h.push(did, p)
        h.update_priority(3, 10)                      # more urgent -> moves up
        self.assertEqual(h.heap[0], (10, 3))
        h.update_priority(3, 100)                     # less urgent -> moves down
        self.assertEqual([h.pop_min()[1] for _ in range(3)], [1, 2, 3])

    def test_remove_root_middle_last(self):
        h = IndexedMinHeap()
        for did in range(1, 8):
            h.push(did, did * 10)
        for pick in (lambda: h.heap[0][1], lambda: h.heap[3][1], lambda: h.heap[-1][1]):
            target = pick()
            h.remove(target)
            self.assertTrue(heap_valid(h))
            self.assertFalse(h.contains(target))

    def test_empty_heap_and_duplicate_push(self):
        h = IndexedMinHeap()
        self.assertIsNone(h.pop_min())
        self.assertIsNone(h.remove(99))
        self.assertFalse(h.update_priority(99, 5))
        h.push(1, 50)
        h.push(1, 20)                                 # same id -> updated, not duplicated
        self.assertEqual((len(h), h.heap[0]), (1, (20, 1)))


class TestDijkstra(unittest.TestCase):

    def setUp(self):
        self.graph = FoodRescueSystem().graph

    def test_known_shortest_times(self):
        d = dijkstra(self.graph, "Hotel_Sun")
        # Care is 35 via Hostel_A, not 60 via Hope
        self.assertEqual((d["Hotel_Sun"], d["NGO_Hope"], d["NGO_Seva"], d["NGO_Care"]), (0, 20, 30, 35))

    def test_island_and_unknown_source(self):
        from_island = dijkstra(self.graph, "Island")
        self.assertTrue(all(v == INF for k, v in from_island.items() if k != "Island"))
        self.assertEqual(dijkstra(self.graph, "Hotel_Sun")["Island"], INF)
        self.assertTrue(all(v == INF for v in dijkstra(self.graph, "Nowhere").values()))


class TestDonationOperations(unittest.TestCase):

    def test_invalid_donations_rejected(self):
        s = new_system((1, "Hotel_Sun", 10, 60))
        quiet(s.add_donation, 1, "Hostel_A", 99, 80)      # duplicate id
        quiet(s.add_donation, 2, "Nowhere", 5, 50)        # unknown location
        quiet(s.add_donation, 3, "Hotel_Sun", 0, 50)      # zero meals
        quiet(s.add_donation, 4, "Hotel_Sun", -5, 50)     # negative meals
        quiet(s.add_donation, 5, "Hotel_Sun", 5, 0)       # expiry == current time
        self.assertEqual(list(s.donations), [1])
        self.assertEqual(s.donations[1]["meals"], 10)

    def test_update_and_invalid_update(self):
        s = new_system((1, "Hotel_Sun", 10, 60), (2, "Hostel_A", 5, 80))
        quiet(s.update_donation, 2, meals=20, expiry_time=30)
        self.assertEqual((s.donations[2]["meals"], s.heap.heap[0]), (20, (30, 2)))
        quiet(s.update_donation, 1, meals=-3)
        quiet(s.update_donation, 1, location="Nowhere")
        quiet(s.update_donation, 99, meals=5)             # missing id
        self.assertEqual((s.donations[1]["meals"], s.donations[1]["location"]), (10, "Hotel_Sun"))
        self.assertNotIn(99, s.donations)

    def test_cancel_and_edge_cases(self):
        s = new_system((1, "Hotel_Sun", 10, 60))
        quiet(s.advance_clock, -5)                        # negative clock move ignored
        self.assertEqual(s.current_time, 0)
        for did in (1, 1, 99):                            # normal, twice, missing
            quiet(s.cancel_donation, did)
        self.assertEqual(s.donations[1]["status"], "CANCELLED")
        self.assertFalse(s.heap.contains(1))


class TestMatching(unittest.TestCase):

    def test_nearest_ngo_and_capacity_reduced(self):
        s = new_system((1, "Hotel_Sun", 40, 60))
        match(s)
        self.assertEqual((s.donations[1]["status"], s.matched[0]["ngo_id"], s.matched[0]["travel_time"]),
                         ("MATCHED", 1, 20))
        self.assertEqual(s.ngos[1]["capacity"], 10)
        self.assertFalse(s.heap.contains(1))

    def test_fallback_and_same_expiry_order(self):
        s = new_system((3, "Cafe_Blue", 20, 60), (1, "Hotel_Sun", 40, 60), (2, "Hostel_A", 25, 60))
        match(s)
        self.assertEqual([m["donation_id"] for m in s.matched], [1, 2, 3])   # id tie-break
        self.assertEqual([m["ngo_id"] for m in s.matched], [1, 2, 3])        # Hope full -> Care full -> Seva

    def test_unreachable_and_not_enough_time_expire(self):
        s = new_system((6, "Island", 5, 100), (5, "WeddingHall", 10, 40))   # 30 + 15 buffer > 40
        match(s)
        self.assertEqual((s.donations[6]["status"], s.donations[5]["status"]), ("EXPIRED", "EXPIRED"))

    def test_too_big_stays_pending_then_matches_after_update(self):
        s = new_system((4, "WeddingHall", 120, 200))
        match(s)
        self.assertEqual(s.donations[4]["status"], "PENDING")
        self.assertTrue(s.heap.contains(4))
        quiet(s.update_donation, 4, meals=70)
        match(s)
        self.assertEqual((s.donations[4]["status"], s.matched[0]["ngo_id"]), ("MATCHED", 3))

    def test_boundary_time_exact_and_one_minute_short(self):
        on_time = new_system((1, "Hotel_Sun", 5, 35))     # 20 travel + 15 buffer = 35
        late = new_system((1, "Hotel_Sun", 5, 34))
        match(on_time)
        match(late)
        self.assertEqual((on_time.donations[1]["status"], late.donations[1]["status"]),
                         ("MATCHED", "EXPIRED"))

    def test_boundary_meals_equal_to_capacity(self):
        s = new_system((1, "Hotel_Sun", 50, 100), (2, "Hotel_Sun", 1, 100))
        match(s)
        self.assertEqual((s.matched[0]["ngo_id"], s.ngos[1]["capacity"]), (1, 0))
        self.assertEqual(s.matched[1]["ngo_id"], 3)       # full NGO skipped

    def test_empty_system_and_repeat_match(self):
        match(FoodRescueSystem())                         # must not crash
        s = new_system((1, "Hotel_Sun", 40, 60))
        match(s)
        match(s)
        self.assertEqual(len(s.matched), 1)

    def test_pending_expires_and_matched_is_locked(self):
        s = new_system((9, "Hostel_A", 120, 70), (1, "Hotel_Sun", 40, 60))
        match(s)
        quiet(s.cancel_donation, 1)                       # already MATCHED -> rejected
        quiet(s.update_donation, 1, meals=5)
        self.assertEqual((s.donations[1]["status"], s.donations[1]["meals"]), ("MATCHED", 40))
        quiet(s.advance_clock, 80)
        match(s)
        self.assertEqual(s.donations[9]["status"], "EXPIRED")
        self.assertIn("already passed", s.expired[-1]["reason"])


class TestDemoScenario(unittest.TestCase):

    def test_demo_results(self):
        s = new_system((3, "Cafe_Blue", 20, 60), (1, "Hotel_Sun", 40, 60), (2, "Hostel_A", 25, 60),
                       (4, "WeddingHall", 120, 200), (5, "WeddingHall", 10, 40), (6, "Island", 5, 100),
                       (7, "Market", 15, 150), (8, "Hotel_Sun", 10, 30), (9, "Hostel_A", 90, 70),
                       (10, "Nowhere", 5, 50))
        quiet(s.update_donation, 8, expiry_time=90)
        quiet(s.cancel_donation, 7)
        match(s)
        quiet(s.update_donation, 4, meals=70)
        for minutes in (30, 50):
            quiet(s.advance_clock, minutes)
            match(s)
        status = {i: d["status"] for i, d in s.donations.items()}
        self.assertEqual(status, {1: "MATCHED", 2: "MATCHED", 3: "MATCHED", 4: "MATCHED", 5: "EXPIRED",
                                  6: "EXPIRED", 7: "CANCELLED", 8: "MATCHED", 9: "EXPIRED"})
        self.assertEqual([n["capacity"] for n in s.ngos.values()], [0, 5, 10])
        self.assertEqual(sum(d["meals"] for d in s.donations.values() if d["status"] == "MATCHED"), 165)
        self.assertTrue(s.heap.is_empty())


if __name__ == "__main__":
    unittest.main(verbosity=2)
