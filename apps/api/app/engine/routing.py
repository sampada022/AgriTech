"""Route planner and savings arithmetic (TRD 6.5). No external solver."""

from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np

from app.engine.scoring import TIER_ORDER

DETOUR_FACTOR = 1.2
WALK_SPEED_MPS = 1.2
MINUTES_PER_STOP = 3.0
SCOUTING_SWATH_M = 4.0
SPRAY_BUFFER_M = 2.0

# Far beyond the 40 stops the TRD plans for. A very low threshold can get here, and the
# nearest-neighbour order is still usable while 2-opt would stall the request.
MAX_TWO_OPT_STOPS = 80

MODE_SHORTEST = "shortest"
MODE_WORST_FIRST = "worst_first"
ROUTE_MODES = (MODE_SHORTEST, MODE_WORST_FIRST)


@dataclass
class Stop:
    hotspot_id: str
    x: float
    y: float
    tier: str


@dataclass
class RoutePlan:
    mode: str
    ordered_ids: list[str] = field(default_factory=list)
    distance_m: float = 0.0
    eta_min: float = 0.0
    baseline_m: float = 0.0
    saved_pct: float = 0.0
    w_pattern_m: float = 0.0
    saved_vs_w_pct: float = 0.0
    leg_distances_m: list[float] = field(default_factory=list)


def serpentine_baseline_m(width_m: float, height_m: float, swath_m: float = SCOUTING_SWATH_M) -> float:
    """Full sweep: passes along the long side, joined by headland turns one swath long."""
    long_side, short_side = max(width_m, height_m), min(width_m, height_m)
    passes = max(1, math.ceil(short_side / swath_m))
    return passes * long_side + (passes - 1) * swath_m


def w_pattern_m(width_m: float, height_m: float, detour_factor: float = DETOUR_FACTOR) -> float:
    """W-pattern scouting walk: four legs across the field, spaced evenly along the long side.

    This is what scouts actually do, so a route should also be compared with it, not only with a
    full sweep nobody walks. It samples rather than covers, so a shorter walk that sees less is not
    the same as a saving. The legs cross rows just as a route does, so they get the same detour.
    """
    long_side, short_side = max(width_m, height_m), min(width_m, height_m)
    return 4 * math.hypot(long_side / 4, short_side) * detour_factor


def _distance(a: tuple[float, float], b: tuple[float, float]) -> float:
    return math.hypot(a[0] - b[0], a[1] - b[1])


def _nearest_neighbour(
    start: tuple[float, float], points: list[tuple[float, float]], indices: list[int]
) -> list[int]:
    remaining = list(indices)
    order: list[int] = []
    current = start
    while remaining:
        best = min(remaining, key=lambda i: _distance(current, points[i]))
        order.append(best)
        remaining.remove(best)
        current = points[best]
    return order


def _path_length(start, points, order) -> float:
    total, current = 0.0, start
    for i in order:
        total += _distance(current, points[i])
        current = points[i]
    return total


def _two_opt(start, points, order: list[int]) -> list[int]:
    """Reverse segments until nothing improves. The start is fixed and the end is free."""
    best = list(order)
    if len(best) > MAX_TWO_OPT_STOPS:
        return best
    best_length = _path_length(start, points, best)
    improved = True
    while improved:
        improved = False
        for i in range(len(best) - 1):
            for j in range(i + 1, len(best)):
                candidate = best[:i] + best[i : j + 1][::-1] + best[j + 1 :]
                length = _path_length(start, points, candidate)
                if length < best_length - 1e-9:
                    best, best_length = candidate, length
                    improved = True
    return best


def plan_route(
    start_xy: tuple[float, float],
    stops: list[Stop],
    mode: str,
    baseline_m: float,
    w_walk_m: float = 0.0,
    walking_speed_mps: float = WALK_SPEED_MPS,
    minutes_per_stop: float = MINUTES_PER_STOP,
    detour_factor: float = DETOUR_FACTOR,
) -> RoutePlan:
    if mode not in ROUTE_MODES:
        raise ValueError(f"Unknown route mode: {mode}")
    points = [(s.x, s.y) for s in stops]

    if mode == MODE_SHORTEST:
        order = _two_opt(start_xy, points, _nearest_neighbour(start_xy, points, list(range(len(stops)))))
    else:
        # Sort by tier, then nearest neighbour inside each tier, carrying on from the last stop.
        order = []
        current = start_xy
        for tier in sorted({s.tier for s in stops}, key=lambda t: TIER_ORDER.get(t, 99)):
            group = [i for i, s in enumerate(stops) if s.tier == tier]
            chunk = _nearest_neighbour(current, points, group)
            order.extend(chunk)
            current = points[chunk[-1]]

    legs: list[float] = []
    current = start_xy
    for i in order:
        legs.append(_distance(current, points[i]) * detour_factor)
        current = points[i]
    distance = float(np.sum(legs)) if legs else 0.0
    eta = distance / walking_speed_mps / 60 + minutes_per_stop * len(order)
    saved = (1 - distance / baseline_m) * 100 if baseline_m > 0 else 0.0
    return RoutePlan(
        mode=mode,
        ordered_ids=[stops[i].hotspot_id for i in order],
        distance_m=distance,
        eta_min=eta,
        baseline_m=baseline_m,
        saved_pct=saved,
        w_pattern_m=w_walk_m,
        saved_vs_w_pct=(1 - distance / w_walk_m) * 100 if w_walk_m > 0 else 0.0,
        leg_distances_m=legs,
    )
