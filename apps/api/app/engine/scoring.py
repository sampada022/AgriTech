import math
import numpy as np
from typing import Dict, Tuple, List

# Typical cue ranges for normalization to roughly [-3.0, 3.0]
CUE_RANGES = {
    "contrast_ratio": 1.5,
    "entropy_ratio": 1.0,
    "edge_ratio": 1.2,
    "irregularity": 0.4,
    "sharpness": 0.5,
    "log_area": 3.0,
    "anisotropy": 0.4
}

def sigmoid(z: float) -> float:
    return 1.0 / (1.0 + math.exp(-z))

def compute_hotspot_features(
    cluster: Dict,
    field_tiles: List[Dict],
    all_canopy_contrast_mean: float,
    all_canopy_entropy_mean: float,
    all_canopy_edge_mean: float
) -> Dict[str, float]:
    """
    Computes the 7 explainability cues for a clustered hotspot:
    1. contrast_ratio (inside vs baseline)
    2. entropy_ratio (inside vs baseline)
    3. edge_ratio (inside vs baseline)
    4. irregularity (1.0 - solidity)
    5. sharpness (mean boundary gradient/contrast)
    6. log_area (log of m^2)
    7. anisotropy (mean directional striping inside)
    """
    member_tiles = cluster.get("member_tile_indices", [])
    
    if member_tiles:
        c_inside = np.mean([t["features"]["contrast"] for t in member_tiles])
        e_inside = np.mean([t["features"]["entropy"] for t in member_tiles])
        edges_inside = np.mean([t["features"]["edge_density"] for t in member_tiles])
        aniso_inside = np.mean([t["features"]["anisotropy"] for t in member_tiles])
    else:
        c_inside, e_inside, edges_inside, aniso_inside = 1.0, 1.0, 0.1, 0.1

    # Ratios vs field baseline
    contrast_ratio = float(c_inside / max(0.1, all_canopy_contrast_mean))
    entropy_ratio = float(e_inside / max(0.1, all_canopy_entropy_mean))
    edge_ratio = float(edges_inside / max(0.01, all_canopy_edge_mean))

    area_m2 = cluster["area_m2"]
    irregularity = float(max(0.0, 1.0 - cluster.get("solidity", 0.8)))
    sharpness = float(min(1.0, cluster.get("mean_anomaly", 2.0) / 4.0))
    log_area = float(math.log(max(1.0, area_m2)))
    anisotropy = float(aniso_inside)

    return {
        "contrast_ratio": round(contrast_ratio, 2),
        "entropy_ratio": round(entropy_ratio, 2),
        "edge_ratio": round(edge_ratio, 2),
        "irregularity": round(irregularity, 2),
        "sharpness": round(sharpness, 2),
        "log_area": round(log_area, 2),
        "anisotropy": round(anisotropy, 2)
    }

def score_hotspot(
    cues: Dict[str, float],
    weights: Dict[str, float],
    bias: float,
    image_quality: float = 0.95,
    tile_count: int = 4
) -> Tuple[float, str, str, str, Dict[str, float]]:
    """
    Computes:
    - Biotic likelihood score B = sigmoid(sum(w_i * f_norm_i) + bias)
    - Signed contributions per cue (w_i * f_norm_i)
    - Classification: B >= 0.65 -> likely_biotic, B <= 0.35 -> likely_abiotic, else uncertain
    - Tier: red (likely biotic), amber (uncertain/mild), grey (likely abiotic)
    - Confidence: geometric mean of image quality, cue agreement, and tile support
    """
    contributions = {}
    z = bias

    agreed_cues = 0
    total_cues = len(cues)

    for cue_name, raw_val in cues.items():
        w = weights.get(cue_name, 0.0)
        norm_range = CUE_RANGES.get(cue_name, 1.0)
        norm_val = np.clip(raw_val / norm_range, -3.0, 3.0)
        contrib = float(w * norm_val)
        contributions[cue_name] = round(contrib, 2)
        z += contrib

    biotic_score = round(sigmoid(z), 2)

    # Class determination
    if biotic_score >= 0.65:
        biotic_class = "likely_biotic"
        tier = "red"
    elif biotic_score <= 0.35:
        biotic_class = "likely_abiotic"
        tier = "grey"
    else:
        biotic_class = "uncertain"
        tier = "amber"

    # Cue agreement calculation
    for cue_name, contrib in contributions.items():
        if (biotic_class == "likely_biotic" and contrib > 0) or \
           (biotic_class == "likely_abiotic" and contrib < 0) or \
           (biotic_class == "uncertain"):
            agreed_cues += 1

    agreement_ratio = agreed_cues / float(total_cues)
    size_support = min(1.0, tile_count / 6.0)

    # Confidence: geometric mean of image_quality, agreement_ratio, and size_support
    conf_score = (image_quality * agreement_ratio * size_support) ** (1.0 / 3.0)
    if conf_score >= 0.65:
        confidence = "high"
    elif conf_score >= 0.40:
        confidence = "medium"
    else:
        confidence = "low"

    return biotic_score, biotic_class, tier, confidence, contributions

