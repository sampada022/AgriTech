"""Conversions between engine metres and the GeoJSON the API speaks."""

from __future__ import annotations

from shapely.geometry import Polygon
from shapely.geometry.polygon import orient

from app.engine.geo import Bounds, FieldFrame
from app.models import FieldRecord, Scan

COORD_DECIMALS = 7


def bounds_of(field: FieldRecord) -> Bounds:
    return Bounds(field.sw_lat, field.sw_lon, field.ne_lat, field.ne_lon)


def frame_of(field: FieldRecord, scan: Scan | None = None) -> FieldFrame:
    """Frame at working resolution when the scan has one, otherwise at native resolution."""
    grid = (scan.grid or {}) if scan is not None else {}
    return FieldFrame(
        bounds_of(field),
        int(grid.get("working_width") or field.image_width),
        int(grid.get("working_height") or field.image_height),
    )


def polygon_to_geojson(frame: FieldFrame, polygon: Polygon) -> dict:
    """GeoJSON Polygon with [lon, lat] coordinates and a counter-clockwise exterior."""

    def ring(coords) -> list[list[float]]:
        out = []
        for x, y in coords:
            lat, lon = frame.xy_to_latlon(x, y)
            out.append([round(lon, COORD_DECIMALS), round(lat, COORD_DECIMALS)])
        return out

    oriented = orient(polygon, 1.0)
    return {
        "type": "Polygon",
        "coordinates": [ring(oriented.exterior.coords)]
        + [ring(hole.coords) for hole in oriented.interiors],
    }


def geojson_to_polygon(frame: FieldFrame, geometry: dict) -> Polygon:
    rings = [
        [frame.latlon_to_xy(lat, lon) for lon, lat in ring] for ring in geometry["coordinates"]
    ]
    return Polygon(rings[0], rings[1:])
