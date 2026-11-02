import cv2
import numpy as np
from typing import List, Tuple, Dict
from skimage.feature import graycomatrix, graycoprops

def extract_tile_features(
    tile_rgb: np.ndarray,
    tile_gray: np.ndarray,
    tile_greenness: np.ndarray,
    tile_canopy_mask: np.ndarray
) -> Dict[str, float]:
    """
    Computes texture and color features for a single 48px tile:
    - Canopy percentage
    - Greenness mean and std
    - GLCM (16 levels) contrast, homogeneity, energy, entropy
    - Anisotropy (directional contrast ratio 0 deg vs 90 deg)
    - Canny edge density
    """
    canopy_pixels = np.sum(tile_canopy_mask > 0)
    total_pixels = tile_canopy_mask.size
    canopy_pct = canopy_pixels / float(total_pixels)

    if canopy_pct < 0.60:
        return {
            "canopy_pct": canopy_pct,
            "greenness_mean": 0.0,
            "greenness_std": 0.0,
            "contrast": 0.0,
            "homogeneity": 0.0,
            "energy": 0.0,
            "entropy": 0.0,
            "anisotropy": 0.0,
            "edge_density": 0.0,
            "valid_canopy": 0.0
        }

    # Greenness stats on canopy pixels
    greenness_vals = tile_greenness[tile_canopy_mask > 0]
    g_mean = float(np.mean(greenness_vals)) if len(greenness_vals) > 0 else 0.0
    g_std = float(np.std(greenness_vals)) if len(greenness_vals) > 0 else 0.0

    # Quantize grayscale to 16 levels for stable fast GLCM
    q_gray = (tile_gray // 16).astype(np.uint8)
    glcm = graycomatrix(
        q_gray,
        distances=[1, 3],
        angles=[0, np.pi/4, np.pi/2, 3*np.pi/4],
        levels=16,
        symmetric=True,
        normed=True
    )

    contrast_matrix = graycoprops(glcm, 'contrast')
    contrast = float(np.mean(contrast_matrix))
    homogeneity = float(np.mean(graycoprops(glcm, 'homogeneity')))
    energy = float(np.mean(graycoprops(glcm, 'energy')))

    # Entropy: -sum(p * log2(p + eps))
    glcm_eps = glcm + 1e-12
    entropy = float(-np.sum(glcm * np.log2(glcm_eps)))

    # Anisotropy: abs(C0 - C90) / (C0 + C90 + eps)
    c0 = float(np.mean(contrast_matrix[:, 0]))
    c90 = float(np.mean(contrast_matrix[:, 2]))
    anisotropy = float(abs(c0 - c90) / (c0 + c90 + 1e-6))

    # Canny edge density on canopy
    edges = cv2.Canny(tile_gray, 50, 150)
    edge_density = float(np.sum((edges > 0) & (tile_canopy_mask > 0))) / float(max(1, canopy_pixels))

    return {
        "canopy_pct": float(canopy_pct),
        "greenness_mean": g_mean,
        "greenness_std": g_std,
        "contrast": contrast,
        "homogeneity": homogeneity,
        "energy": energy,
        "entropy": entropy,
        "anisotropy": anisotropy,
        "edge_density": edge_density,
        "valid_canopy": 1.0
    }

def grid_tiling(
    img_bgr: np.ndarray,
    greenness: np.ndarray,
    canopy_mask: np.ndarray,
    tile_size: int = 48
) -> List[Dict]:
    """
    Divides the working image into non-overlapping tile_size x tile_size grid.
    Returns list of tile records with grid indices, pixel bounds, and feature dicts.
    """
    height, width = img_bgr.shape[:2]
    gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
    tiles = []

    for y in range(0, height - tile_size + 1, tile_size):
        for x in range(0, width - tile_size + 1, tile_size):
            t_bgr = img_bgr[y:y+tile_size, x:x+tile_size]
            t_gray = gray[y:y+tile_size, x:x+tile_size]
            t_greenness = greenness[y:y+tile_size, x:x+tile_size]
            t_mask = canopy_mask[y:y+tile_size, x:x+tile_size]

            feats = extract_tile_features(t_bgr, t_gray, t_greenness, t_mask)
            tiles.append({
                "x_px": x,
                "y_px": y,
                "cx_px": x + (tile_size // 2),
                "cy_px": y + (tile_size // 2),
                "tile_size": tile_size,
                "features": feats
            })

    return tiles

