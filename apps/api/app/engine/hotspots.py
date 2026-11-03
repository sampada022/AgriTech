"""Steps 7 to 9 of the pipeline (TRD 6.2): anomaly score, DBSCAN clustering, hotspot features."""

from __future__ import annotations

import math
from dataclasses import dataclass

import cv2
import numpy as np
import shapely
from scipy import ndimage as ndi
from shapely.geometry import Polygon
from shapely.ops import unary_union
from sklearn.cluster import DBSCAN

from app.engine.geo import FieldFrame
from app.engine.tiles import TileGrid

CONTRAST_WEIGHT = 0.6
RING_TILES = 3
MIN_RING_TILES = 4
EDGE_RATIO_FLOOR = 0.02
SHARPNESS_DEPTH_FLOOR = 0.5  # greenness units, so shallow noise cannot read as a sharp edge


@dataclass
class HotspotDraft:
    polygon: Polygon  # metres in the field frame
    rows: np.ndarray
    cols: np.ndarray
    area_m2: float
    centroid_xy: tuple[float, float]
    cues: dict[str, float]
    mean_anomaly: float

    @property
    def tile_count(self) -> int:
        return int(self.rows.size)


def robust_z(x: np.ndarray, valid: np.ndarray) -> np.ndarray:
    """(x - median) / (1.4826 * MAD) against the whole field."""
    if not valid.any():
        return np.zeros_like(x, dtype=np.float64)
    values = x[valid]
    median = float(np.median(values))
    mad = float(np.median(np.abs(values - median)))
    return (x - median) / max(1.4826 * mad, 1e-6)


def anomaly_scores(grid: TileGrid) -> np.ndarray:
    """A = max(0, -z of greenness) + 0.6 * max(0, z of contrast). Excluded tiles score zero."""
    z_green = robust_z(grid.green_mean, grid.valid)
    z_contrast = robust_z(grid.contrast, grid.valid)
    score = np.maximum(0, -z_green) + CONTRAST_WEIGHT * np.maximum(0, z_contrast)
    return np.where(grid.valid, score, 0.0)


def _tile_boxes(rows: np.ndarray, cols: np.ndarray, grid: TileGrid, frame: FieldFrame):
    t = grid.tile_px
    x0 = cols * t * frame.gsd_x - frame.width_m / 2
    x1 = (cols + 1) * t * frame.gsd_x - frame.width_m / 2
    y1 = frame.height_m / 2 - rows * t * frame.gsd_y
    y0 = frame.height_m / 2 - (rows + 1) * t * frame.gsd_y
    return shapely.box(x0, y0, x1, y1)


def _tile_polygon(rows, cols, grid: TileGrid, frame: FieldFrame) -> Polygon:
    """Union of member tiles as one Polygon, with small holes filled.

    Tiles touching only at a corner union to a MultiPolygon, and the contract promises a Polygon,
    so a 1 mm buffer welds them. A larger eps can link tiles with a real gap, so a morphological
    closing runs if needed, and the largest part wins if pieces still remain.
    """
    t_m = grid.tile_px * frame.gsd_m
    shape = unary_union(_tile_boxes(rows, cols, grid, frame)).buffer(1e-3, join_style="mitre")
    if shape.geom_type == "MultiPolygon":
        shape = shape.buffer(t_m, join_style="mitre").buffer(-t_m, join_style="mitre")
    if shape.geom_type == "MultiPolygon":
        shape = max(shape.geoms, key=lambda g: g.area)
    max_hole = 4 * t_m * t_m
    keep = [ring for ring in shape.interiors if Polygon(ring).area > max_hole]
    return Polygon(shape.exterior, keep)


def _shape_elongation(rows: np.ndarray, cols: np.ndarray) -> float:
    """0 for a round blob, approaching 1 for a long thin band. Direction-independent."""
    if rows.size < 3:
        return 0.0
    coords = np.stack((cols.astype(np.float64), rows.astype(np.float64)))
    eigen = np.linalg.eigvalsh(np.cov(coords))
    # A single tile's own extent contributes 1/12 tile^2 of variance on each axis.
    major, minor = eigen[1] + 1 / 12, eigen[0] + 1 / 12
    return float(1 - math.sqrt(minor / major))


def _boundary_sharpness(
    polygon: Polygon, frame: FieldFrame, gradient: np.ndarray, depth: float, downsample: int
) -> float:
    """Boundary gradient divided by anomaly depth, which is about 1 / (edge width in metres).

    Raw gradient mostly tracks how deep an anomaly is, and a deep soft drought zone has a big
    gradient too. Dividing by depth measures edge steepness alone. On the simulator this lifts
    pest-vs-abiotic AUC from 0.59 to 0.87. Clipped to 0..1, so edges under 1 m read as 1.0.

    The polygon follows the tile grid, not the true edge, which can sit up to half a tile away.
    `gradient` is therefore already max-filtered over that distance.
    """
    ring = polygon.exterior
    n = max(8, int(ring.length / 0.5))
    distances = np.linspace(0, ring.length, n, endpoint=False)
    points = shapely.get_coordinates(shapely.line_interpolate_point(ring, distances))
    px = (points[:, 0] + frame.width_m / 2) / frame.gsd_x / downsample
    py = (frame.height_m / 2 - points[:, 1]) / frame.gsd_y / downsample
    h, w = gradient.shape
    ix = np.clip(px.astype(int), 0, w - 1)
    iy = np.clip(py.astype(int), 0, h - 1)
    return float(np.clip(gradient[iy, ix].mean() / max(depth, SHARPNESS_DEPTH_FLOOR), 0, 1))


def build_gradient_raster(
    greenness: np.ndarray, mask: np.ndarray, tile_px: int, gsd_m: float, downsample: int = 4
) -> np.ndarray:
    """Greenness gradient per metre, smoothed and spread for boundary sharpness.

    Non-canopy pixels are filled with the canopy median, so a soil edge does not read as a sharp
    pest boundary. The 0.75 m blur is wider than the row spacing, so rows do not read as edges.
    """
    median = float(np.median(greenness[mask])) if mask.any() else 0.0
    filled = np.where(mask, greenness, median).astype(np.float32)
    small = cv2.resize(
        filled, None, fx=1 / downsample, fy=1 / downsample, interpolation=cv2.INTER_AREA
    )
    metres_per_px = gsd_m * downsample
    smooth = cv2.GaussianBlur(small, (0, 0), max(1.0, 0.75 / metres_per_px))
    gx = cv2.Sobel(smooth, cv2.CV_32F, 1, 0, ksize=3)
    gy = cv2.Sobel(smooth, cv2.CV_32F, 0, 1, ksize=3)
    # A 3 x 3 Sobel has a gain of 8 per pixel step.
    per_metre = cv2.magnitude(gx, gy) / (8 * metres_per_px)
    reach = max(3, int(tile_px / 2 / downsample) * 2 + 1)
    return cv2.dilate(per_metre, np.ones((reach, reach), np.uint8))


def describe_members(
    rows: np.ndarray,
    cols: np.ndarray,
    polygon: Polygon,
    grid: TileGrid,
    frame: FieldFrame,
    anomaly: np.ndarray,
    flagged: np.ndarray,
    gradient: np.ndarray,
    downsample: int = 4,
) -> HotspotDraft:
    """Hotspot feature vector: the seven cues plus mean anomaly (TRD 6.2 step 9, 6.4)."""
    members = np.zeros((grid.ny, grid.nx), dtype=bool)
    members[rows, cols] = True

    ring = ndi.binary_dilation(members, iterations=RING_TILES) & ~members & grid.valid & ~flagged
    if ring.sum() < MIN_RING_TILES:
        # Nothing clean nearby, so compare against the whole field instead.
        ring = grid.valid & ~flagged

    def ratio(values: np.ndarray, floor: float = 1e-9) -> float:
        inside = float(values[members].mean()) if members.any() else 0.0
        outside = float(values[ring].mean()) if ring.any() else inside
        return (inside + floor) / (outside + floor)

    depth = 0.0
    if members.any() and ring.any():
        depth = abs(float(grid.green_mean[members].mean() - grid.green_mean[ring].mean()))
    area = float(polygon.area)
    hull = float(polygon.convex_hull.area)
    solidity = area / hull if hull > 0 else 1.0
    tile_excess = float(
        grid.anisotropy[members].mean()
        - (grid.anisotropy[grid.valid].mean() if grid.valid.any() else 0.0)
    )
    cues = {
        "contrast_ratio": ratio(grid.contrast),
        "entropy_ratio": ratio(grid.entropy),
        # Smooth canopy can have almost no Canny edges, so the ratio needs a floor to stay stable.
        "edge_ratio": ratio(grid.edge_density, floor=EDGE_RATIO_FLOOR),
        "irregularity": 1.0 - solidity,
        "sharpness": _boundary_sharpness(polygon, frame, gradient, depth, downsample),
        "log_area": math.log(max(area, 1e-3)),
        # Row crops are directional in every tile, so raw tile GLCM anisotropy says little on its
        # own. The cue also uses shape elongation, which spots stripes at any row angle.
        "anisotropy": max(_shape_elongation(rows, cols), tile_excess),
    }
    centroid = polygon.centroid
    return HotspotDraft(
        polygon=polygon,
        rows=rows,
        cols=cols,
        area_m2=area,
        centroid_xy=(float(centroid.x), float(centroid.y)),
        cues=cues,
        mean_anomaly=float(anomaly[members].mean()) if members.any() else 0.0,
    )


def cluster_hotspots(
    grid: TileGrid,
    frame: FieldFrame,
    anomaly: np.ndarray,
    threshold: float,
    eps: float,
    min_samples: int,
    min_cluster_m2: float,
    gradient: np.ndarray,
    downsample: int = 4,
) -> tuple[list[HotspotDraft], np.ndarray]:
    """DBSCAN on flagged-tile centres in metres, with eps given as a multiple of tile size."""
    flagged = grid.valid & (anomaly >= threshold)
    rows, cols = np.nonzero(flagged)
    if rows.size == 0:
        return [], flagged

    t = grid.tile_px
    points = np.column_stack(((cols + 0.5) * t * frame.gsd_x, (rows + 0.5) * t * frame.gsd_y))
    eps_m = eps * t * frame.gsd_m
    labels = DBSCAN(eps=eps_m, min_samples=min_samples).fit_predict(points)

    drafts: list[HotspotDraft] = []
    for label in np.unique(labels):
        if label < 0:
            continue
        chosen = labels == label
        r, c = rows[chosen], cols[chosen]
        polygon = _tile_polygon(r, c, grid, frame)
        if polygon.area < min_cluster_m2:
            continue
        drafts.append(
            describe_members(
                r, c, polygon, grid, frame, anomaly, flagged, gradient, downsample
            )
        )
    return drafts, flagged
