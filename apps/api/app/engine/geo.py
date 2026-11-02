import math
from typing import Tuple, List

# Approximate conversion factors near Mandya, Karnataka (~12.52 N, 76.90 E)
# In local metres:
# x = (lon - lon0) * 111320 * cos(lat0)
# y = (lat - lat0) * 110574

METRES_PER_DEG_LAT = 110574.0
METRES_PER_DEG_LON_EQUATOR = 111320.0

def latlon_to_xy(lat: float, lon: float, lat0: float, lon0: float) -> Tuple[float, float]:
    """
    Converts (lat, lon) in WGS84 to local metres (x, y) relative to origin (lat0, lon0).
    x: Easting in metres
    y: Northing in metres
    """
    lat_rad = math.radians(lat0)
    x = (lon - lon0) * METRES_PER_DEG_LON_EQUATOR * math.cos(lat_rad)
    y = (lat - lat0) * METRES_PER_DEG_LAT
    return (x, y)

def xy_to_latlon(x: float, y: float, lat0: float, lon0: float) -> Tuple[float, float]:
    """
    Converts local metres (x, y) back to WGS84 (lat, lon) relative to origin (lat0, lon0).
    """
    lat_rad = math.radians(lat0)
    lat = lat0 + (y / METRES_PER_DEG_LAT)
    lon = lon0 + (x / (METRES_PER_DEG_LON_EQUATOR * math.cos(lat_rad)))
    return (lat, lon)

def compute_field_dimensions_m(sw_lat: float, sw_lon: float, ne_lat: float, ne_lon: float) -> Tuple[float, float]:
    """
    Computes (width_m, height_m) for a field bounded by SW and NE corners.
    """
    origin_lat = (sw_lat + ne_lat) / 2.0
    origin_lon = (sw_lon + ne_lon) / 2.0
    sw_x, sw_y = latlon_to_xy(sw_lat, sw_lon, origin_lat, origin_lon)
    ne_x, ne_y = latlon_to_xy(ne_lat, ne_lon, origin_lat, origin_lon)
    return (abs(ne_x - sw_x), abs(ne_y - sw_y))

def haversine_distance_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Computes great-circle distance between two GPS coordinates in metres.
    """
    R = 6371000.0
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = math.sin(delta_phi / 2.0) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0) ** 2
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return R * c

