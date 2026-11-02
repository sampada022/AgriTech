import numpy as np
from typing import List, Dict

def compute_robust_z(values: np.ndarray) -> np.ndarray:
    """
    Robust z-score using Median and Median Absolute Deviation (MAD):
    z = (x - median) / (1.4826 * MAD)
    """
    if len(values) == 0:
        return np.array([])
    median = np.median(values)
    mad = np.median(np.abs(values - median))
    scale = 1.4826 * mad
    if scale < 1e-6:
        return np.zeros_like(values)
    return (values - median) / scale

def score_tile_anomalies(tiles: List[Dict], tau: float = 2.0) -> List[Dict]:
    """
    Computes anomaly score A for canopy tiles:
    A = max(0, -z_greenness) + 0.6 * max(0, z_contrast)
    Tiles with A >= tau are flagged.
    """
    canopy_indices = [i for i, t in enumerate(tiles) if t["features"]["valid_canopy"] == 1.0]

    if not canopy_indices:
        for t in tiles:
            t["anomaly_score"] = 0.0
            t["flagged"] = False
        return tiles

    greenness_vals = np.array([tiles[i]["features"]["greenness_mean"] for i in canopy_indices])
    contrast_vals = np.array([tiles[i]["features"]["contrast"] for i in canopy_indices])

    z_green = compute_robust_z(greenness_vals)
    z_contrast = compute_robust_z(contrast_vals)

    # Compute anomaly scores
    anomaly_scores = np.maximum(0.0, -z_green) + 0.6 * np.maximum(0.0, z_contrast)

    for idx, tile_idx in enumerate(canopy_indices):
        score = float(anomaly_scores[idx])
        tiles[tile_idx]["anomaly_score"] = score
        tiles[tile_idx]["flagged"] = bool(score >= tau)

    # Non-canopy tiles are explicitly marked unflagged
    non_canopy = [i for i, t in enumerate(tiles) if t["features"]["valid_canopy"] == 0.0]
    for idx in non_canopy:
        tiles[idx]["anomaly_score"] = 0.0
        tiles[idx]["flagged"] = False

    return tiles

