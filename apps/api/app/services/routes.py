"""Stored routes and the KPI strip (TRD 6.5, F11, F12)."""

from __future__ import annotations

import math
from datetime import timezone

from shapely.geometry import box
from shapely.ops import unary_union
from sqlmodel import Session, select

from app.diagnosis.guidance import BIOTIC_LABELS
from app.engine.routing import (
    DETOUR_FACTOR,
    MINUTES_PER_STOP,
    MODE_SHORTEST,
    SCOUTING_SWATH_M,
    SPRAY_BUFFER_M,
    WALK_SPEED_MPS,
    Stop,
    plan_route,
    serpentine_baseline_m,
    w_pattern_m,
)
from app.errors import ApiError
from app.models import RESOLVED_STATUSES, STATUS_CLEARED, FieldRecord, Hotspot, Route, Scan, new_id
from app.services.geometry import frame_of, geojson_to_polygon


def _aware(value):
    """SQLite drops the timezone on round-trip; a row just created in this session still has it."""
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


def latest_route(session: Session, scan_id: str) -> Route | None:
    rows = session.exec(select(Route).where(Route.scan_id == scan_id)).all()
    return max(rows, key=lambda r: _aware(r.created_at)) if rows else None


def scan_hotspots(session: Session, scan_id: str) -> list[Hotspot]:
    rows = session.exec(select(Hotspot).where(Hotspot.scan_id == scan_id)).all()
    return sorted(rows, key=lambda h: h.rank)


def create_route(
    session: Session,
    scan: Scan,
    field: FieldRecord,
    mode: str = MODE_SHORTEST,
    start: tuple[float, float] | None = None,
    include_abiotic: bool = False,
    walking_speed_mps: float = WALK_SPEED_MPS,
    minutes_per_stop: float = MINUTES_PER_STOP,
) -> Route:
    """Plan and store a route. Default start is the field tile nearest the south-west corner."""
    frame = frame_of(field, scan)
    if start is None:
        default = (scan.grid or {}).get("default_start")
        start = (default["lat"], default["lon"]) if default else (field.sw_lat, field.sw_lon)
    start_xy = frame.latlon_to_xy(*start)
    if abs(start_xy[0]) > 50_000 or abs(start_xy[1]) > 50_000:
        raise ApiError(
            422,
            "start_too_far",
            "The start point is more than 50 km from this field.",
            "Check the coordinates, or leave the start empty to use the field corner.",
        )

    stops = []
    tiers = ("red", "amber", "grey_blue") if include_abiotic else ("red", "amber")
    for hotspot in scan_hotspots(session, scan.id):
        if hotspot.status in RESOLVED_STATUSES or hotspot.tier not in tiers:
            continue
        x, y = frame.latlon_to_xy(hotspot.centroid_lat, hotspot.centroid_lon)
        stops.append(Stop(hotspot.id, x, y, hotspot.tier))

    # Empty orthomosaic margins are not walkable field, so both baselines use the real field size.
    scale = math.sqrt((scan.grid or {}).get("data_fraction", 1.0))
    width, height = frame.width_m * scale, frame.height_m * scale
    plan = plan_route(
        start_xy,
        stops,
        mode,
        serpentine_baseline_m(width, height),
        w_pattern_m(width, height),
        walking_speed_mps,
        minutes_per_stop,
    )
    route = Route(
        id=new_id("r"),
        scan_id=scan.id,
        mode=mode,
        start_lat=start[0],
        start_lon=start[1],
        ordered_hotspot_ids=plan.ordered_ids,
        leg_distances_m=plan.leg_distances_m,
        distance_m=plan.distance_m,
        eta_min=plan.eta_min,
        baseline_m=plan.baseline_m,
        saved_pct=plan.saved_pct,
        w_pattern_m=plan.w_pattern_m,
        saved_vs_w_pct=plan.saved_vs_w_pct,
        include_abiotic=include_abiotic,
        walking_speed_mps=walking_speed_mps,
        minutes_per_stop=minutes_per_stop,
    )
    session.add(route)
    session.flush()
    return route


def replan_from_previous(
    session: Session, scan: Scan, field: FieldRecord, start: tuple[float, float] | None = None
) -> Route:
    """New route with the previous route's settings, from a new position if one is given."""
    previous = latest_route(session, scan.id)
    if previous is None:
        return create_route(session, scan, field, start=start)
    return create_route(
        session,
        scan,
        field,
        mode=previous.mode,
        start=start or (previous.start_lat, previous.start_lon),
        include_abiotic=previous.include_abiotic,
        walking_speed_mps=previous.walking_speed_mps,
        minutes_per_stop=previous.minutes_per_stop,
    )


def route_assumptions(route: Route | None = None) -> dict:
    speed = route.walking_speed_mps if route else WALK_SPEED_MPS
    minutes = route.minutes_per_stop if route else MINUTES_PER_STOP
    return {
        "walking_speed_mps": speed,
        "minutes_per_stop": minutes,
        "detour_factor": DETOUR_FACTOR,
        "scouting_swath_m": SCOUTING_SWATH_M,
        "spray_buffer_m": SPRAY_BUFFER_M,
        "notes": {
            "route_distance": f"Straight-line distance between stops times {DETOUR_FACTOR}, to "
            "allow for crop rows and field bunds.",
            "eta": f"Distance at {speed} m/s, plus {minutes:g} minutes at each stop.",
            "walk_saved": f"Compared with a full serpentine sweep on a {SCOUTING_SWATH_M:g} m "
            "scouting swath, including headland turns. Scouts rarely walk a full sweep, so show "
            "this next to the W-pattern figure.",
            "walk_saved_vs_w_pattern": "Compared with a W-pattern scouting walk, four legs across "
            "the field. This can be negative. A W-pattern is a sample that only sees what lies on "
            "its line, so a shorter walk is not the same as better coverage.",
            "spray_area": f"Hotspot area plus a {SPRAY_BUFFER_M:g} m buffer. This is the potential "
            "spot-treatment area if ground checks confirm, not a pesticide saving.",
        },
    }


def route_payload(session: Session, route: Route) -> dict:
    by_id = {h.id: h for h in scan_hotspots(session, route.scan_id)}
    stops = []
    coordinates = [[route.start_lon, route.start_lat]]
    cumulative = 0.0
    ordered = route.ordered_hotspot_ids or []
    legs = route.leg_distances_m or []
    for index, hotspot_id in enumerate(ordered):
        hotspot = by_id.get(hotspot_id)
        if hotspot is None:
            continue
        leg = legs[index] if index < len(legs) else 0.0
        cumulative += leg
        coordinates.append([hotspot.centroid_lon, hotspot.centroid_lat])
        stops.append(
            {
                "order": len(stops) + 1,
                "hotspot_id": hotspot.id,
                "lat": hotspot.centroid_lat,
                "lon": hotspot.centroid_lon,
                "tier": hotspot.tier,
                "biotic_score": round(hotspot.biotic_score, 3),
                "area_m2": round(hotspot.area_m2, 1),
                "status": hotspot.status,
                "leg_distance_m": round(leg, 1),
                "cumulative_distance_m": round(cumulative, 1),
            }
        )
    return {
        "id": route.id,
        "scan_id": route.scan_id,
        "mode": route.mode,
        "include_abiotic": route.include_abiotic,
        "start": {"lat": route.start_lat, "lon": route.start_lon},
        "stops": stops,
        "stop_count": len(stops),
        "distance_m": round(route.distance_m, 1),
        "eta_min": round(route.eta_min, 1),
        "baseline_m": round(route.baseline_m, 1),
        "saved_pct": round(route.saved_pct, 1),
        "w_pattern_m": round(route.w_pattern_m, 1),
        "saved_vs_w_pattern_pct": round(route.saved_vs_w_pct, 1),
        "polyline": {"type": "LineString", "coordinates": coordinates},
        "assumptions": route_assumptions(route),
    }


def refresh_kpis(session: Session, scan: Scan, field: FieldRecord) -> dict:
    """Recompute the KPI strip. Runs after anything that changes hotspots or the route."""
    frame = frame_of(field, scan)
    hotspots = scan_hotspots(session, scan.id)
    active = [h for h in hotspots if h.status != STATUS_CLEARED]
    polygons = {h.id: geojson_to_polygon(frame, h.polygon) for h in active}

    flagged = unary_union(list(polygons.values())) if polygons else None
    flagged_area = float(flagged.area) if flagged is not None else 0.0

    # Spray area covers what may still need treating. Confirmed abiotic hotspots drop out.
    treatable = [
        polygons[h.id]
        for h in active
        if h.label in BIOTIC_LABELS or (h.label is None and h.tier in ("red", "amber"))
    ]
    spray_area = 0.0
    if treatable:
        field_rect = box(
            -frame.width_m / 2, -frame.height_m / 2, frame.width_m / 2, frame.height_m / 2
        )
        spray_area = float(
            unary_union([p.buffer(SPRAY_BUFFER_M) for p in treatable]).intersection(field_rect).area
        )

    route = latest_route(session, scan.id)
    grid = scan.grid or {}
    field_area = frame.area_m2 * grid.get("data_fraction", 1.0)
    tiers = {"red": 0, "amber": 0, "grey_blue": 0}
    for hotspot in active:
        tiers[hotspot.tier] = tiers.get(hotspot.tier, 0) + 1
    kpis = {
        "hotspot_count": len(active),
        "tier_counts": tiers,
        "field_area_m2": round(field_area, 1),
        "area_flagged_m2": round(flagged_area, 1),
        "area_flagged_pct": round(flagged_area / field_area * 100, 2) if field_area else 0.0,
        "spray_area_m2": round(spray_area, 1),
        "spray_area_pct": round(spray_area / field_area * 100, 2) if field_area else 0.0,
        "walk_saved_pct": round(route.saved_pct, 1) if route else None,
        "route_distance_m": round(route.distance_m, 1) if route else None,
        "baseline_distance_m": round(route.baseline_m, 1) if route else None,
        "walk_saved_vs_w_pattern_pct": round(route.saved_vs_w_pct, 1) if route else None,
        "w_pattern_distance_m": round(route.w_pattern_m, 1) if route else None,
        "route_stops": len(route.ordered_hotspot_ids or []) if route else 0,
        "eta_min": round(route.eta_min, 1) if route else None,
        "tiles_total": grid.get("tiles_total"),
        "tiles_excluded": grid.get("tiles_excluded"),
        "assumptions": route_assumptions(route),
    }
    scan.kpis = kpis
    session.add(scan)
    return kpis
