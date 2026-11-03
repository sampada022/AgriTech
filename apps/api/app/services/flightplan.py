"""Flight-plan generator (F26): a lawnmower pattern exported as KML and a QGC waypoint file."""

from __future__ import annotations

import math
from xml.sax.saxutils import escape

from shapely.geometry import LineString, Polygon

from app.engine.geo import Bounds, FieldFrame
from app.errors import ApiError

# A typical 12 MP consumer drone: 1.2 cm per pixel at 35 m, so about 50 m across (TRD 6.1).
DEFAULT_CAMERA = {
    "sensor_width_mm": 6.3,
    "focal_length_mm": 4.5,
    "image_width_px": 4000,
    "image_height_px": 3000,
}
CRUISE_SPEED_MPS = 5.0
TURN_OVERHEAD_S = 4.0
MAX_ALTITUDE_M = 120.0  # the common open-airspace ceiling; verify the local rules before flying
MAX_LINES = 400


def plan_flight(
    polygon_latlon: list[tuple[float, float]],
    altitude_m: float,
    front_overlap: float,
    side_overlap: float,
    camera: dict | None = None,
) -> dict:
    """Waypoints in visiting order, plus a summary of what the flight will cost."""
    if altitude_m > MAX_ALTITUDE_M:
        raise ApiError(
            422,
            "altitude_too_high",
            f"Altitude must stay under {MAX_ALTITUDE_M:.0f} m.",
            "Lower the altitude, and check the drone rules for your location.",
        )
    cam = {**DEFAULT_CAMERA, **(camera or {})}
    lats = [p[0] for p in polygon_latlon]
    lons = [p[1] for p in polygon_latlon]
    frame = FieldFrame(Bounds(min(lats), min(lons), max(lats), max(lons)), 1, 1)
    polygon = Polygon([frame.latlon_to_xy(lat, lon) for lat, lon in polygon_latlon])
    if not polygon.is_valid or polygon.area <= 0:
        raise ApiError(
            422,
            "invalid_polygon",
            "This field outline crosses itself or has no area.",
            "Draw the outline again without crossing lines.",
        )

    gsd_m = (cam["sensor_width_mm"] / 1000) * altitude_m / (
        (cam["focal_length_mm"] / 1000) * cam["image_width_px"]
    )
    footprint_w = gsd_m * cam["image_width_px"]
    footprint_h = gsd_m * cam["image_height_px"]
    line_spacing = footprint_w * (1 - side_overlap)
    photo_spacing = footprint_h * (1 - front_overlap)

    minx, miny, maxx, maxy = polygon.bounds
    along_x = (maxx - minx) >= (maxy - miny)
    across_min, across_max = (miny, maxy) if along_x else (minx, maxx)
    n_lines = max(1, math.ceil((across_max - across_min) / line_spacing))
    if n_lines > MAX_LINES:
        raise ApiError(
            422,
            "too_many_lines",
            "This outline would need too many flight lines at this altitude and overlap.",
            "Fly higher, reduce the overlap, or plan a smaller area.",
        )

    legs: list[tuple[tuple[float, float], tuple[float, float]]] = []
    for i in range(n_lines):
        offset = across_min + (i + 0.5) * (across_max - across_min) / n_lines
        line = (
            LineString([(minx - 1, offset), (maxx + 1, offset)])
            if along_x
            else LineString([(offset, miny - 1), (offset, maxy + 1)])
        )
        clipped = polygon.intersection(line)
        if clipped.is_empty:
            continue
        pieces = list(clipped.geoms) if hasattr(clipped, "geoms") else [clipped]
        for piece in pieces:
            if piece.geom_type != "LineString" or piece.length < 0.01:
                continue
            a, b = piece.coords[0], piece.coords[-1]
            if (a[0], a[1]) > (b[0], b[1]):
                a, b = b, a
            legs.append((a, b) if len(legs) % 2 == 0 else (b, a))

    waypoints_xy = [point for leg in legs for point in leg]
    survey_m = sum(math.dist(a, b) for a, b in legs)
    transit_m = sum(math.dist(legs[i][1], legs[i + 1][0]) for i in range(len(legs) - 1))
    photos = sum(max(1, math.ceil(math.dist(a, b) / photo_spacing) + 1) for a, b in legs)
    flight_s = (survey_m + transit_m) / CRUISE_SPEED_MPS + TURN_OVERHEAD_S * len(legs)

    waypoints = []
    for x, y in waypoints_xy:
        lat, lon = frame.xy_to_latlon(x, y)
        waypoints.append({"lat": round(lat, 7), "lon": round(lon, 7), "alt_m": altitude_m})

    summary = {
        "gsd_cm": round(gsd_m * 100, 2),
        "footprint_width_m": round(footprint_w, 1),
        "footprint_height_m": round(footprint_h, 1),
        "line_spacing_m": round(line_spacing, 1),
        "photo_spacing_m": round(photo_spacing, 1),
        "flight_lines": len(legs),
        "estimated_photos": photos,
        "estimated_flight_min": round(flight_s / 60, 1),
        "area_m2": round(polygon.area, 1),
        "camera": cam,
        "assumptions": f"Cruise at {CRUISE_SPEED_MPS:g} m/s with {TURN_OVERHEAD_S:g} s per turn. "
        "Camera values are for a typical 12 MP consumer drone; change them to match yours.",
        "safety": "Get permission, keep line of sight and verify local drone rules before flying.",
    }
    return {
        "waypoints": waypoints,
        "summary": summary,
        "photo_spacing_m": photo_spacing,
    }


def to_kml(name: str, waypoints: list[dict]) -> str:
    coordinates = " ".join(f"{w['lon']},{w['lat']},{w['alt_m']}" for w in waypoints)
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<kml xmlns="http://www.opengis.net/kml/2.2"><Document>'
        f"<name>{escape(name)}</name>"
        f"<Placemark><name>{escape(name)} survey</name><LineString>"
        "<altitudeMode>relativeToGround</altitudeMode>"
        f"<coordinates>{coordinates}</coordinates>"
        "</LineString></Placemark></Document></kml>\n"
    )


def to_qgc_waypoints(waypoints: list[dict], photo_spacing_m: float) -> str:
    """QGC WPL 110, which Mission Planner and QGroundControl both read."""
    if not waypoints:
        return "QGC WPL 110\n"
    first = waypoints[0]
    altitude = first["alt_m"]

    def row(index, current, frame, command, p1, lat, lon, alt):
        fields = [index, current, frame, command, p1, 0, 0, 0, lat, lon, alt, 1]
        return "\t".join(str(f) for f in fields)

    lines = ["QGC WPL 110"]
    lines.append(row(0, 1, 0, 16, 0, first["lat"], first["lon"], 0))  # home
    lines.append(row(1, 0, 3, 22, 0, first["lat"], first["lon"], altitude))  # takeoff
    lines.append(row(2, 0, 3, 206, round(photo_spacing_m, 2), 0, 0, 0))  # trigger camera by distance
    index = 3
    for waypoint in waypoints:
        lines.append(row(index, 0, 3, 16, 0, waypoint["lat"], waypoint["lon"], waypoint["alt_m"]))
        index += 1
    lines.append(row(index, 0, 3, 206, 0, 0, 0, 0))  # stop triggering
    lines.append(row(index + 1, 0, 3, 20, 0, 0, 0, 0))  # return to launch
    return "\n".join(lines) + "\n"
