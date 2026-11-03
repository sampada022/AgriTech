"""Local flat-earth geometry (TRD 5): areas, distances and DBSCAN all run in metres."""

from __future__ import annotations

import math
from dataclasses import dataclass

M_PER_DEG_LON_AT_EQUATOR = 111_320.0
M_PER_DEG_LAT = 110_574.0


@dataclass(frozen=True)
class Bounds:
    """South-west and north-east corners, in degrees."""

    sw_lat: float
    sw_lon: float
    ne_lat: float
    ne_lon: float

    def as_dict(self) -> dict[str, float]:
        return {
            "sw_lat": self.sw_lat,
            "sw_lon": self.sw_lon,
            "ne_lat": self.ne_lat,
            "ne_lon": self.ne_lon,
        }

    def as_leaflet(self) -> list[list[float]]:
        """[[south, west], [north, east]], the shape Leaflet's ImageOverlay takes."""
        return [[self.sw_lat, self.sw_lon], [self.ne_lat, self.ne_lon]]


class FieldFrame:
    """Maps lat/lon and image pixels to metres around the field centre.

    Pixel x grows east and pixel y grows south. Metre x grows east and metre y grows north.
    """

    def __init__(self, bounds: Bounds, image_width: int, image_height: int):
        self.bounds = bounds
        self.image_width = image_width
        self.image_height = image_height
        self.lat0 = (bounds.sw_lat + bounds.ne_lat) / 2
        self.lon0 = (bounds.sw_lon + bounds.ne_lon) / 2
        self._m_per_lon = M_PER_DEG_LON_AT_EQUATOR * math.cos(math.radians(self.lat0))
        self.width_m = (bounds.ne_lon - bounds.sw_lon) * self._m_per_lon
        self.height_m = (bounds.ne_lat - bounds.sw_lat) * M_PER_DEG_LAT
        self.gsd_x = self.width_m / image_width
        self.gsd_y = self.height_m / image_height

    @property
    def area_m2(self) -> float:
        return self.width_m * self.height_m

    @property
    def gsd_m(self) -> float:
        return (self.gsd_x + self.gsd_y) / 2

    def latlon_to_xy(self, lat: float, lon: float) -> tuple[float, float]:
        return (lon - self.lon0) * self._m_per_lon, (lat - self.lat0) * M_PER_DEG_LAT

    def xy_to_latlon(self, x: float, y: float) -> tuple[float, float]:
        return self.lat0 + y / M_PER_DEG_LAT, self.lon0 + x / self._m_per_lon

    def px_to_xy(self, px: float, py: float) -> tuple[float, float]:
        return px * self.gsd_x - self.width_m / 2, self.height_m / 2 - py * self.gsd_y

    def xy_to_px(self, x: float, y: float) -> tuple[float, float]:
        return (x + self.width_m / 2) / self.gsd_x, (self.height_m / 2 - y) / self.gsd_y


def bounds_from_centre(lat: float, lon: float, width_m: float, height_m: float) -> Bounds:
    """Bounds for a rectangle of the given size in metres, used by the simulator."""
    half_lat = height_m / 2 / M_PER_DEG_LAT
    half_lon = width_m / 2 / (M_PER_DEG_LON_AT_EQUATOR * math.cos(math.radians(lat)))
    return Bounds(lat - half_lat, lon - half_lon, lat + half_lat, lon + half_lon)


def gsd_for_flight(
    sensor_width_mm: float, altitude_m: float, focal_length_mm: float, image_width_px: int
) -> float:
    """GSD in metres per pixel (TRD 6.1)."""
    return (sensor_width_mm / 1000) * altitude_m / ((focal_length_mm / 1000) * image_width_px)
