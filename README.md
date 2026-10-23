# Surplus Food Rescue Matcher

A Data Structures case study in Python 3. Restaurants, hostels and wedding halls often have leftover cooked food that goes to waste, while nearby NGOs need it. This program matches each food donation to the **nearest suitable NGO before the food expires**, handling the **most urgent donations first**.

Donations can also be **updated** or **cancelled** while they are still pending.

## Features

- Processes donations in order of expiry time (most urgent first)
- Finds shortest travel times with Dijkstra's algorithm
- Matches each donation to the nearest NGO that has enough capacity and can arrive in time
- Supports updating and cancelling pending donations
- Tracks NGO capacity after every match
- Keeps the last 5 events and records of matched and expired donations
- Uses a simulated clock (no real time)

## Data Structures Used

| Structure | Where it is used | Why |
|---|---|---|
| **IndexedMinHeap** (hand-written) | Pending donations by expiry time | Gets the most urgent donation in O(log n) |
| **Position dictionary** | Inside the heap, maps donation id to heap index | Allows O(log n) removal and priority update, and O(1) `contains` |
| **Adjacency list** (dict of lists) | Road map | The road network is sparse |
| **Dijkstra with `heapq`** | Shortest travel time from donor to every place | Roads have different travel times |
| **Dictionaries** | Donations and NGOs | O(1) average lookup by id |
| **`deque(maxlen=5)`** | Event history | Automatically keeps only the last 5 events |
| **Plain lists** | Matched and expired records | Only appended to and printed in order |

> `heapq` is used **only** inside `dijkstra()`. The primary heap is written by hand.

## Matching Rules

`PICKUP_BUFFER = 15` minutes.

An NGO is suitable for a donation only if **both** are true:

1. `capacity_left >= meals` (the whole donation goes to one NGO)
2. `current_time + travel_time + PICKUP_BUFFER <= expiry_time`

Among suitable NGOs, the one with the **smallest travel time** is chosen. On a tie, the **smaller NGO id** wins.

| Situation | Result |
|---|---|
| A suitable NGO exists | `MATCHED` |
| An NGO can make the deadline, but none has enough capacity | stays `PENDING` and is retried later |
| No NGO is reachable, or none can be reached in time | `EXPIRED` (reason recorded) |
| Current time has reached or passed the expiry time | `EXPIRED` |

Each matching run processes at most as many donations as were in the heap when it started, and pending donations are pushed back only after the loop, so there is no infinite loop.

## Map

Places: `Hotel_Sun`, `Hostel_A`, `WeddingHall`, `Cafe_Blue`, `Market`, `NGO_Hope`, `NGO_Care`, `NGO_Seva`, and `Island` (isolated, used to test unreachable cases).

Roads (undirected, travel time in minutes):

| Road | Minutes |
|---|---:|
| Hotel_Sun - Market | 10 |
| Hotel_Sun - NGO_Hope | 20 |
| Hostel_A - Market | 15 |
| Hostel_A - NGO_Care | 10 |
| WeddingHall - Market | 25 |
| WeddingHall - NGO_Seva | 30 |
| Cafe_Blue - NGO_Care | 35 |
| Cafe_Blue - Hostel_A | 5 |
| Market - NGO_Seva | 20 |
| NGO_Hope - NGO_Care | 40 |

NGOs:

| ID | Name | Capacity (meals) |
|---|---|---:|
| 1 | NGO_Hope | 50 |
| 2 | NGO_Care | 30 |
| 3 | NGO_Seva | 100 |

## How to Run

Requires Python 3. No external libraries.

```bash
python food_rescue_matcher.py
```

The program runs a fixed demonstration automatically. There are no menus and no input is needed.

## What the Demo Covers

- A donation matched to a suitable NGO
- NGO capacity too small for a donation
- A donation that fails because of the 15-minute pickup buffer
- An unreachable donor at `Island`
- Updating a pending donation (expiry time and meal count)
- Cancelling a pending donation
- Equal expiry times, to verify the donation-id tie-break
- Advancing the clock and matching again
- Empty heap and unknown id handled without errors
- Rejected updates and cancels for donations that are already matched, expired or cancelled

## Time Complexity

n = donations in the heap, V = places, E = roads, k = donations processed in one run, G = NGOs.

| Operation | Complexity |
|---|---|
| Heap push | O(log n) |
| Heap pop_min | O(log n) |
| Heap remove by id | O(log n) |
| Heap update_priority | O(log n) |
| Heap contains | O(1) |
| Dictionary lookup | O(1) average |
| Dijkstra (adjacency list + `heapq`) | O((V + E) log V) |
| One matching run | O(k((V + E) log V + G + log k)) |

## Project Structure

```
food_rescue_matcher.py   # complete program (single file)
README.md
```

Inside `food_rescue_matcher.py`:

- `IndexedMinHeap`: hand-written binary min-heap with a position dictionary
- `dijkstra()`: shortest travel times from a source to every place
- `FoodRescueSystem`: map, NGOs, donations, matching, update, cancel, clock and reports
- `main()`: deterministic demonstration

## Team

| Member | Contribution |
|---|---|
| Nikhil S | Project skeleton, `FoodRescueSystem.__init__`, `_build_map`, `_load_ngos`, README |
| Moshlekha | `IndexedMinHeap` |
| Rakeshkumar | `dijkstra()` and `run_matching()` |
| Sarvesh | Update, cancel and clock methods, display methods, `main()` demo |

*Replace the member labels with your names and GitHub usernames.*

## Possible Improvements

- Real map data instead of a hardcoded map
- Splitting one donation across several NGOs
- Caching distances, since the map is fixed
- A real input source for donations
