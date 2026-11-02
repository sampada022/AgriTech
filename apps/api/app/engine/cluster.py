import numpy as np
from typing import List, Dict, Tuple
from sklearn.cluster import DBSCAN
from shapely.geometry import box, Polygon, MultiPolygon
from shapely.ops import unary_union
from app.engine.geo import xy_to_latlon

def cluster_flagged_tiles(
    tiles: List[Dict],
    gsd_cm: float = 3.0,
    tile_size_px: int = 48,
    eps_multiplier: float = 1.6,
    min_samples: int = 3,
    min_area_m2: float = 2.0,
    lat0: float = 12.5240,
    lon0: float = 76.9000,
    img_width_px: int = 2048,
    img_height_px: int = 1536
) -> List[Dict]:
    """
    Groups flagged tiles into spatial polygons using DBSCAN in metres:
    1. Filter flagged tiles.
    2. Convert tile centers to metres from field origin.
    3. DBSCAN clustering with eps = eps_multiplier * tile_size_m.
    4. Shapely polygon union of member tiles.
    5. Drop clusters smaller than min_area_m2.
    6. Convert coordinates back to WGS84 GeoJSON polygons.
    """
    flagged = [t for t in tiles if t.get("flagged", False)]
    if not flagged:
        return []

    tile_m = (tile_size_px * gsd_cm) / 100.0
    half_w = img_width_px / 2.0
    half_h = img_height_px / 2.0

    # Metric coordinates relative to center
    metric_coords = []
    for t in flagged:
        mx = (t["cx_px"] - half_w) * (gsd_cm / 100.0)
        # Invert y so top is North
        my = (half_h - t["cy_px"]) * (gsd_cm / 100.0)
        metric_coords.append([mx, my])

    coords_arr = np.array(metric_coords)
    eps = eps_multiplier * tile_m

    db = DBSCAN(eps=eps, min_samples=min_samples).fit(coords_arr)
    labels = db.labels_

    unique_labels = set(labels)
    clusters = []

    for label in unique_labels:
        if label == -1:
            continue  # Noise points dropped

        member_indices = np.where(labels == label)[0]
        member_boxes = []

        member_scores = []
        for idx in member_indices:
            t = flagged[idx]
            member_scores.append(t["anomaly_score"])
            # Tile bounding box in metres
            x1 = (t["x_px"] - half_w) * (gsd_cm / 100.0)
            x2 = (t["x_px"] + tile_size_px - half_w) * (gsd_cm / 100.0)
            y1 = (half_h - (t["y_px"] + tile_size_px)) * (gsd_cm / 100.0)
            y2 = (half_h - t["y_px"]) * (gsd_cm / 100.0)
            member_boxes.append(box(x1, y1, x2, y2))

        # Union member tile rectangles
        union_geom = unary_union(member_boxes)
        if union_geom.is_empty:
            continue

        # Keep largest polygon if MultiPolygon
        if isinstance(union_geom, MultiPolygon):
            union_geom = max(union_geom.geoms, key=lambda p: p.area)

        area_m2 = float(union_geom.area)
        if area_m2 < min_area_m2:
            continue

        # Convert polygon exterior to WGS84 [lon, lat] for GeoJSON
        ext_coords = list(union_geom.exterior.coords)
        geojson_coords = []
        for mx, my in ext_coords:
            lat, lon = xy_to_latlon(mx, my, lat0, lon0)
            geojson_coords.append([round(lon, 6), round(lat, 6)])

        # Centroid
        c_lat, c_lon = xy_to_latlon(union_geom.centroid.x, union_geom.centroid.y, lat0, lon0)

        # Polygon features
        convex_hull_area = union_geom.convex_hull.area or 1e-6
        solidity = min(1.0, area_m2 / convex_hull_area)
        mean_anomaly = float(np.mean(member_scores))

        clusters.append({
            "geometry": {
                "type": "Polygon",
                "coordinates": [geojson_coords]
            },
            "centroid": [round(c_lon, 6), round(c_lat, 6)],
            "area_m2": round(area_m2, 2),
            "solidity": round(solidity, 3),
            "mean_anomaly": round(mean_anomaly, 2),
            "tile_count": len(member_indices),
            "member_tile_indices": [flagged[idx] for idx in member_indices]
        })

    # Sort clusters by severity (mean anomaly * area)
    clusters.sort(key=lambda c: -(c["mean_anomaly"] * np.log1p(c["area_m2"])))
    return clusters

