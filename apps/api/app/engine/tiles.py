"""Steps 5 and 6 of the pipeline (TRD 6.2): tile grid and per-tile features.

GLCMs are built for every tile at once with one np.bincount per offset, rather than one
skimage.graycomatrix call per tile. test_tiles.py checks the output against scikit-image. This
replaces the joblib parallelism in TRD 6.3, because a single core already beats the 20 s budget.
"""

from __future__ import annotations

from dataclasses import dataclass, fields

import cv2
import numpy as np

GLCM_DISTANCES = (1, 3)
GLCM_ANGLES_DEG = (0, 45, 90, 135)


def _glcm_offset(distance: int, angle_deg: int) -> tuple[int, int]:
    """(row, column) offset, rounded as scikit-image does, so 45 degrees at 3 px is (2, 2)."""
    angle = np.deg2rad(angle_deg)
    return round(float(np.sin(angle)) * distance), round(float(np.cos(angle)) * distance)


@dataclass
class TileGrid:
    tile_px: int
    ny: int
    nx: int
    canopy_frac: np.ndarray
    nodata_frac: np.ndarray
    valid: np.ndarray
    green_mean: np.ndarray
    green_std: np.ndarray
    hue_shift: np.ndarray
    contrast: np.ndarray
    homogeneity: np.ndarray
    energy: np.ndarray
    entropy: np.ndarray
    anisotropy: np.ndarray
    edge_density: np.ndarray

    def to_arrays(self) -> dict[str, np.ndarray]:
        return {f.name: np.asarray(getattr(self, f.name)) for f in fields(self)}

    @classmethod
    def from_arrays(cls, data) -> "TileGrid":
        values = {f.name: data[f.name] for f in fields(cls)}
        for key in ("tile_px", "ny", "nx"):
            values[key] = int(values[key])
        return cls(**values)


def _block_sum(a: np.ndarray, t: int, ny: int, nx: int) -> np.ndarray:
    return a[: ny * t, : nx * t].reshape(ny, t, nx, t).sum(axis=(1, 3))


def glcm_features(
    gray: np.ndarray, mask: np.ndarray, tile_px: int, levels: int = 16
) -> dict[str, np.ndarray]:
    """Symmetric, normalised GLCM statistics per tile, averaged over distances and angles.

    Pairs crossing a tile border or touching a non-canopy pixel are skipped.
    Anisotropy is abs(C0 - C90) / (C0 + C90), with C the contrast mean across distances.
    """
    t = tile_px
    ny, nx = gray.shape[0] // t, gray.shape[1] // t
    h, w = ny * t, nx * t
    n_tiles = ny * nx
    quant = (gray[:h, :w].astype(np.int32) * levels) // 256
    canopy = mask[:h, :w]
    rows, cols = np.ogrid[:h, :w]
    tile_id = (rows // t) * nx + (cols // t)

    i, j = np.ogrid[:levels, :levels]
    diff2 = ((i - j) ** 2).astype(np.float64)
    homog_weight = 1.0 / (1.0 + diff2)

    totals = {k: np.zeros(n_tiles) for k in ("contrast", "homogeneity", "energy", "entropy")}
    contrast_axis = {0: np.zeros(n_tiles), 90: np.zeros(n_tiles)}
    n_offsets = 0

    for d in GLCM_DISTANCES:
        for angle_deg in GLCM_ANGLES_DEG:
            dy, dx = _glcm_offset(d, angle_deg)
            ay = slice(max(0, -dy), h - max(0, dy))
            ax = slice(max(0, -dx), w - max(0, dx))
            by = slice(max(0, dy), h - max(0, -dy))
            bx = slice(max(0, dx), w - max(0, -dx))
            keep = (tile_id[ay, ax] == tile_id[by, bx]) & canopy[ay, ax] & canopy[by, bx]
            index = (
                tile_id[ay, ax][keep] * levels * levels
                + quant[ay, ax][keep] * levels
                + quant[by, bx][keep]
            )
            counts = np.bincount(index, minlength=n_tiles * levels * levels).astype(np.float64)
            p = counts.reshape(n_tiles, levels, levels)
            p = p + p.transpose(0, 2, 1)
            totals_per_tile = p.sum(axis=(1, 2), keepdims=True)
            p = np.divide(p, totals_per_tile, out=np.zeros_like(p), where=totals_per_tile > 0)

            contrast = (p * diff2).sum(axis=(1, 2))
            totals["contrast"] += contrast
            totals["homogeneity"] += (p * homog_weight).sum(axis=(1, 2))
            totals["energy"] += np.sqrt((p * p).sum(axis=(1, 2)))
            log_p = np.log2(p, out=np.zeros_like(p), where=p > 0)
            totals["entropy"] += -(p * log_p).sum(axis=(1, 2))
            if angle_deg in contrast_axis:
                contrast_axis[angle_deg] += contrast
            n_offsets += 1

    out = {k: (v / n_offsets).reshape(ny, nx) for k, v in totals.items()}
    c0 = contrast_axis[0] / len(GLCM_DISTANCES)
    c90 = contrast_axis[90] / len(GLCM_DISTANCES)
    denom = c0 + c90
    out["anisotropy"] = np.divide(
        np.abs(c0 - c90), denom, out=np.zeros_like(denom), where=denom > 0
    ).reshape(ny, nx)
    return out


def compute_tiles(
    norm: np.ndarray,
    mask: np.ndarray,
    greenness: np.ndarray,
    tile_px: int = 48,
    min_canopy: float = 0.6,
    levels: int = 16,
    nodata: np.ndarray | None = None,
) -> TileGrid:
    t = tile_px
    ny, nx = norm.shape[0] // t, norm.shape[1] // t
    if ny == 0 or nx == 0:
        raise ValueError(f"This image is smaller than one {t} px tile.")
    nodata_frac = (
        _block_sum(nodata.astype(np.float32), t, ny, nx) / (t * t)
        if nodata is not None
        else np.zeros((ny, nx), dtype=np.float32)
    )
    rgb8 = (norm * 255).astype(np.uint8)
    gray = cv2.cvtColor(rgb8, cv2.COLOR_RGB2GRAY)
    hsv = cv2.cvtColor(rgb8, cv2.COLOR_RGB2HSV)

    weight = mask.astype(np.float32)
    canopy_count = _block_sum(weight, t, ny, nx)
    canopy_frac = canopy_count / (t * t)
    valid = canopy_frac >= min_canopy
    safe = np.maximum(canopy_count, 1.0)

    green_mean = _block_sum(greenness * weight, t, ny, nx) / safe
    green_sq = _block_sum(greenness * greenness * weight, t, ny, nx) / safe
    green_std = np.sqrt(np.maximum(green_sq - green_mean**2, 0))

    # OpenCV hue runs 0..179. Yellow sits below green, so a positive shift means yellower.
    hue_mean = _block_sum(hsv[..., 0].astype(np.float32) * weight, t, ny, nx) / safe
    median_hue = float(np.median(hue_mean[valid])) if valid.any() else 0.0
    hue_shift = (median_hue - hue_mean) * 2.0  # degrees

    edges = (cv2.Canny(gray, 60, 150) > 0).astype(np.float32)
    edge_density = _block_sum(edges * weight, t, ny, nx) / safe

    glcm = glcm_features(gray, mask, t, levels)
    return TileGrid(
        tile_px=t,
        ny=ny,
        nx=nx,
        canopy_frac=canopy_frac,
        nodata_frac=nodata_frac,
        valid=valid,
        green_mean=green_mean,
        green_std=green_std,
        hue_shift=hue_shift,
        contrast=glcm["contrast"],
        homogeneity=glcm["homogeneity"],
        energy=glcm["energy"],
        entropy=glcm["entropy"],
        anisotropy=glcm["anisotropy"],
        edge_density=edge_density,
    )
