import math
from typing import List, Dict, Tuple
from app.engine.geo import haversine_distance_m

DETOUR_FACTOR = 1.2
WALKING_SPEED_MPS = 1.2  # 1.2 m/s (~4.3 km/h)
MINUTES_PER_STOP = 3.0

def euclidean_metric_dist(p1: Dict, p2: Dict) -> float:
    return haversine_distance_m(p1["lat"], p1["lon"], p2["lat"], p2["lon"]) * DETOUR_FACTOR

def solve_2opt(nodes: List[Dict]) -> Tuple[List[Dict], float]:
    """
    Solves TSP route order:
    1. Nearest neighbour greedy tour from node 0.
    2. 2-opt pairwise edge swap optimization until no improvement.
    """
    n = len(nodes)
    if n <= 2:
        dist = sum(euclidean_metric_dist(nodes[i], nodes[i+1]) for i in range(n-1))
        return nodes, dist

    # 1. Nearest Neighbour
    unvisited = list(range(1, n))
    tour = [0]
    curr = 0

    while unvisited:
        next_node = min(unvisited, key=lambda idx: euclidean_metric_dist(nodes[curr], nodes[idx]))
        tour.append(next_node)
        unvisited.remove(next_node)
        curr = next_node

    # 2. 2-Opt refinement
    def calculate_total_dist(path):
        return sum(euclidean_metric_dist(nodes[path[i]], nodes[path[i+1]]) for i in range(len(path)-1))

    improved = True
    best_dist = calculate_total_dist(tour)

    while improved:
        improved = False
        for i in range(1, n - 1):
            for j in range(i + 1, n):
                new_tour = tour[:i] + tour[i:j+1][::-1] + tour[j+1:]
                new_dist = calculate_total_dist(new_tour)
                if new_dist < best_dist - 0.1:
                    tour = new_tour
                    best_dist = new_dist
                    improved = True
                    break
            if improved:
                break

    ordered_nodes = [nodes[idx] for idx in tour]
    return ordered_nodes, best_dist

def plan_field_route(
    start_point: Dict[str, float],
    hotspots: List[Dict],
    mode: str = "worst_first",
    include_abiotic: bool = False,
    field_area_m2: float = 11000.0
) -> Dict:
    """
    Plans ground scout walking path:
    - Baseline: Serpentine sweep with 4m swath: length ~ (field_area / 4m) + headland turns.
    - Route modes:
      - shortest: Global 2-opt across all target stops.
      - worst_first: Sort by tier severity, then NN within tier.
    - Computes walking distance, ETA, and saved walk %.
    """
    # Filter stops
    targets = [
        h for h in hotspots
        if include_abiotic or h["tier"] in ["red", "amber"]
    ]

    nodes = [start_point] + [
        {
            "lat": h["centroid"][1],
            "lon": h["centroid"][0],
            "hotspot_id": h["id"],
            "tier": h["tier"],
            "rank": h["rank"],
            "label": f"Stop {i+1}"
        }
        for i, h in enumerate(targets)
    ]

    if mode == "worst_first":
        # Group by tier
        reds = [n for n in nodes[1:] if n["tier"] == "red"]
        ambers = [n for n in nodes[1:] if n["tier"] == "amber"]
        greys = [n for n in nodes[1:] if n["tier"] == "grey"]

        ordered_nodes = [nodes[0]]
        for group in [reds, ambers, greys]:
            if group:
                sub_ordered, _ = solve_2opt([ordered_nodes[-1]] + group)
                ordered_nodes.extend(sub_ordered[1:])

        dist_m = sum(euclidean_metric_dist(ordered_nodes[i], ordered_nodes[i+1]) for i in range(len(ordered_nodes)-1))
    else:
        ordered_nodes, dist_m = solve_2opt(nodes)

    # Label stops in visitation order
    for idx in range(1, len(ordered_nodes)):
        ordered_nodes[idx]["label"] = f"Stop {idx}"

    num_stops = len(ordered_nodes) - 1
    eta_min = round((dist_m / WALKING_SPEED_MPS / 60.0) + (num_stops * MINUTES_PER_STOP), 1)

    # Baseline sweep length
    baseline_m = round((field_area_m2 / 4.0) * 1.15, 1)
    saved_pct = round(max(0.0, 1.0 - (dist_m / max(100.0, baseline_m))) * 100.0, 1)

    # Potential spot spray area with 2m buffer
    total_buffered_area = sum(h["area_m2"] * 1.4 for h in targets)
    spray_area_pct = round(min(100.0, (total_buffered_area / max(100.0, field_area_m2)) * 100.0), 1)

    return {
        "ordered_hotspot_ids": [n["hotspot_id"] for n in ordered_nodes if n.get("hotspot_id")],
        "distance_m": round(dist_m, 1),
        "eta_min": eta_min,
        "saved_pct": saved_pct,
        "baseline_m": baseline_m,
        "spray_area_pct": spray_area_pct,
        "waypoints": ordered_nodes
    }

