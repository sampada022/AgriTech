"""Biotic-likelihood model and recalibration (TRD 6.4 and 6.7).

B = logistic(w . f + b), where f is the seven cues normalised and clipped to -3..3.

The weights below are the TRD's priors from domain reasoning, not fitted values. The centres, the
ranges and the prior bias were read off the synthetic benchmark, so they are tuned on simulated
fields only. The TRD divides cues by a typical range; centring them as well means a cue at its
typical value contributes nothing, so a why-flagged bar's sign actually carries meaning.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

CUE_NAMES = (
    "contrast_ratio",
    "entropy_ratio",
    "edge_ratio",
    "irregularity",
    "sharpness",
    "log_area",
    "anisotropy",
)

CUE_SPEC = {
    "contrast_ratio": {
        "centre": 1.3,
        "range": 0.8,
        "prior": 1.0,
        "direction": "biotic",
        "rationale": "Thinning and holes mix healthy and damaged leaves, raising local contrast.",
    },
    "entropy_ratio": {
        "centre": 1.12,
        "range": 0.12,
        "prior": 0.7,
        "direction": "biotic",
        "rationale": "Irregular damage is less ordered.",
    },
    "edge_ratio": {
        "centre": 1.5,
        "range": 1.5,
        "prior": 0.6,
        "direction": "biotic",
        "rationale": "Jagged, broken canopy has more edges.",
    },
    "irregularity": {
        # Wide range on purpose. On tile-scale polygons this cue runs opposite to its prior:
        # small patches look compact and large abiotic zones look ragged. See KNOWN_ISSUES.md.
        "centre": 0.2,
        "range": 0.5,
        "prior": 0.5,
        "direction": "biotic",
        "rationale": "Pest spread is ragged; drought zones are blobby.",
    },
    "sharpness": {
        "centre": 0.5,
        "range": 0.25,
        "prior": 0.5,
        "direction": "biotic",
        "rationale": "Pest patches have sharp edges; water stress fades gradually.",
    },
    "log_area": {
        "centre": 3.5,
        "range": 1.5,
        "prior": -0.6,
        "direction": "abiotic",
        "rationale": "Early pest patches are small; large smooth zones are usually water or nutrient.",
    },
    "anisotropy": {
        "centre": 0.4,
        "range": 0.3,
        "prior": -0.8,
        "direction": "abiotic",
        "rationale": "Strong directional striping suggests irrigation, spraying or planting artefacts.",
    },
}

PRIOR_WEIGHTS = np.array([CUE_SPEC[n]["prior"] for n in CUE_NAMES], dtype=np.float64)
# Not given by the TRD. Chosen on the synthetic benchmark: at -0.5 every normal pest patch stays red
# while false ambers on a healthy field fall from 1.8 to 0.6 per field. Anything lower starts
# pushing faint real pests into the unrouted tier, against "we favour recall" (TRD 8.3).
PRIOR_BIAS = -0.5

_CENTRES = np.array([CUE_SPEC[n]["centre"] for n in CUE_NAMES], dtype=np.float64)
_RANGES = np.array([CUE_SPEC[n]["range"] for n in CUE_NAMES], dtype=np.float64)

BIOTIC_AT = 0.65
ABIOTIC_AT = 0.35
STRONG_ANOMALY = 3.0
SIZE_SUPPORT_TILES = 6
CONFIDENCE_HIGH = 0.7
CONFIDENCE_MEDIUM = 0.4

STRIPING_ANISOTROPY = 0.6
LARGE_ZONE_LOG_AREA = 4.6  # about 100 m^2

# Refit settings. One confirmed label should visibly move the model without flipping everything.
# The TRD regularises only the weights, but an unconstrained bias turns one "pest" label into
# "everything looks more like pest". With these settings, and the bias held close to its prior,
# false promotions fell from 40 to 10 across 19 simulated fields, against lambda 0.02 on both, while
# the same 10 of 11 uncertain pest patches were lifted.
REFIT_LAMBDA = 0.1
REFIT_BIAS_LAMBDA = 0.5
REFIT_LEARNING_RATE = 0.2
REFIT_STEPS = 400

CLASS_BIOTIC = "likely_biotic"
CLASS_UNCERTAIN = "uncertain"
CLASS_ABIOTIC = "likely_abiotic"
TIER_RED = "red"
TIER_AMBER = "amber"
TIER_GREY = "grey_blue"
TIER_ORDER = {TIER_RED: 0, TIER_AMBER: 1, TIER_GREY: 2}


@dataclass
class ScoringModel:
    weights: np.ndarray
    bias: float
    version: int = 1

    @classmethod
    def prior(cls) -> "ScoringModel":
        return cls(PRIOR_WEIGHTS.copy(), PRIOR_BIAS, 1)


@dataclass
class Score:
    biotic_score: float
    hotspot_class: str
    tier: str
    confidence_score: float
    confidence: str
    contributions: dict[str, float]
    abiotic_hint: str | None


def normalise(cues: dict[str, float]) -> np.ndarray:
    values = np.array([cues[n] for n in CUE_NAMES], dtype=np.float64)
    return np.clip((values - _CENTRES) / _RANGES, -3.0, 3.0)


def sigmoid(x):
    return 1.0 / (1.0 + np.exp(-np.clip(x, -30, 30)))


def classify(b: float) -> str:
    if b >= BIOTIC_AT:
        return CLASS_BIOTIC
    if b <= ABIOTIC_AT:
        return CLASS_ABIOTIC
    return CLASS_UNCERTAIN


def tier_for(hotspot_class: str, mean_anomaly: float) -> str:
    """Red needs both likely-biotic evidence and a strong anomaly. Abiotic is informational."""
    if hotspot_class == CLASS_ABIOTIC:
        return TIER_GREY
    if hotspot_class == CLASS_BIOTIC and mean_anomaly >= STRONG_ANOMALY:
        return TIER_RED
    return TIER_AMBER


def abiotic_hint(cues: dict[str, float], hotspot_class: str) -> str | None:
    if hotspot_class == CLASS_BIOTIC:
        return None
    if cues["anisotropy"] >= STRIPING_ANISOTROPY:
        return "striping"
    if cues["log_area"] >= LARGE_ZONE_LOG_AREA:
        return "large_smooth_zone"
    return None


def _agreement_share(contributions: np.ndarray, hotspot_class: str) -> float:
    toward_biotic = float((contributions > 0).mean())
    if hotspot_class == CLASS_BIOTIC:
        return toward_biotic
    if hotspot_class == CLASS_ABIOTIC:
        return 1.0 - toward_biotic
    # "Uncertain" has no direction of its own, so use how lopsided the cues are.
    return max(toward_biotic, 1.0 - toward_biotic)


def confidence_of(quality: float, agreement: float, tile_count: int) -> float:
    """Geometric mean of image quality, cue agreement and size support."""
    size_support = min(tile_count, SIZE_SUPPORT_TILES) / SIZE_SUPPORT_TILES
    return float((max(quality, 0) * max(agreement, 0) * max(size_support, 0)) ** (1 / 3))


def confidence_level(value: float) -> str:
    if value >= CONFIDENCE_HIGH:
        return "high"
    if value >= CONFIDENCE_MEDIUM:
        return "medium"
    return "low"


def score_hotspot(
    model: ScoringModel,
    cues: dict[str, float],
    mean_anomaly: float,
    tile_count: int,
    quality: float,
) -> Score:
    f = normalise(cues)
    contributions = model.weights * f
    b = float(sigmoid(contributions.sum() + model.bias))
    hotspot_class = classify(b)
    agreement = _agreement_share(contributions, hotspot_class)
    conf = confidence_of(quality, agreement, tile_count)
    if hotspot_class == CLASS_UNCERTAIN:
        # "Uncertain, high confidence" contradicts itself, so uncertain tops out at medium.
        conf = min(conf, CONFIDENCE_HIGH - 0.01)
    return Score(
        biotic_score=b,
        hotspot_class=hotspot_class,
        tier=tier_for(hotspot_class, mean_anomaly),
        confidence_score=conf,
        confidence=confidence_level(conf),
        contributions={n: float(c) for n, c in zip(CUE_NAMES, contributions)},
        abiotic_hint=abiotic_hint(cues, hotspot_class),
    )


def refit(
    features: np.ndarray,
    labels: np.ndarray,
    prior_weights: np.ndarray = PRIOR_WEIGHTS,
    prior_bias: float = PRIOR_BIAS,
    lam: float = REFIT_LAMBDA,
    learning_rate: float = REFIT_LEARNING_RATE,
    steps: int = REFIT_STEPS,
    bias_lam: float = REFIT_BIAS_LAMBDA,
) -> tuple[np.ndarray, float]:
    """Mean logistic loss plus squared distance from the priors, by gradient descent.

    `features` holds normalised cue vectors, one row per labelled hotspot. With few labels this is
    a prior-regularised nudge to seven weights, not learning, and the UI should say so.
    """
    weights, bias = prior_weights.astype(np.float64).copy(), float(prior_bias)
    if len(labels) == 0:
        return weights, bias
    for _ in range(steps):
        error = sigmoid(features @ weights + bias) - labels
        weights -= learning_rate * (
            features.T @ error / len(labels) + 2 * lam * (weights - prior_weights)
        )
        bias -= learning_rate * (error.mean() + 2 * bias_lam * (bias - prior_bias))
    return weights, bias


def agreement(model: ScoringModel, features: np.ndarray, labels: np.ndarray) -> float | None:
    """Share of labelled hotspots whose predicted class matches their label.

    Training-set agreement, not accuracy. "Uncertain" counts as not matching.
    """
    if len(labels) == 0:
        return None
    predicted = sigmoid(features @ model.weights + model.bias)
    hits = np.where(labels == 1, predicted >= BIOTIC_AT, predicted <= ABIOTIC_AT)
    return float(hits.mean())


def cue_metadata() -> list[dict]:
    return [
        {
            "name": n,
            "direction": CUE_SPEC[n]["direction"],
            "rationale": CUE_SPEC[n]["rationale"],
            "prior_weight": CUE_SPEC[n]["prior"],
            "centre": CUE_SPEC[n]["centre"],
            "range": CUE_SPEC[n]["range"],
        }
        for n in CUE_NAMES
    ]
