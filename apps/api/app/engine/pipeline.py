"""The analysis pipeline as a pure function, free of any database or web concerns (TRD 6.2).

The API, the demo precompute and the benchmark all call analyze(), so they cannot drift apart.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass, field

import numpy as np

from app.engine.geo import Bounds, FieldFrame
from app.engine.hotspots import (
    HotspotDraft,
    anomaly_scores,
    build_gradient_raster,
    cluster_hotspots,
)
from app.engine.preprocess import (
    CanopyResult,
    IndexLayers,
    QualityReport,
    canopy_mask,
    compute_indices,
    gray_world,
    nodata_mask,
    quality_check,
    resample_to_working,
)
from app.engine.scoring import Score, ScoringModel, TIER_ORDER, score_hotspot
from app.engine.tiles import TileGrid, compute_tiles

# The eight named stages on the processing screen, in order.
STAGES = (
    "quality_check",
    "canopy_mask",
    "indices",
    "texture",
    "anomalies",
    "clustering",
    "scoring",
    "route",
)
STAGE_PROGRESS = dict(zip(STAGES, (5, 15, 22, 55, 62, 72, 85, 92)))

# Below this share of scorable tiles, say so instead of quietly drawing the field grey. Real early
# wheat scored only 37% of its tiles at the 60% canopy cutoff, and 57% at a 30% cutoff.
LOW_SCORED_SHARE = 0.5


class Cancelled(Exception):
    """Raised between stages when the caller asks to stop."""


@dataclass(frozen=True)
class AnalysisParams:
    tile_px: int = 48
    threshold: float = 2.0
    eps: float = 1.6  # a multiple of tile size
    min_samples: int = 3
    min_cluster_m2: float = 2.0
    min_canopy: float = 0.6
    glcm_levels: int = 16

    def as_dict(self) -> dict:
        return {
            "tile_px": self.tile_px,
            "threshold": self.threshold,
            "eps": self.eps,
            "min_samples": self.min_samples,
            "min_canopy": self.min_canopy,
        }


@dataclass
class ScoredHotspot:
    draft: HotspotDraft
    score: Score


@dataclass
class AnalysisResult:
    params: AnalysisParams
    frame: FieldFrame
    working_rgb: np.ndarray
    quality: QualityReport
    canopy: CanopyResult
    indices: IndexLayers
    grid: TileGrid
    anomaly: np.ndarray
    gradient: np.ndarray
    flagged: np.ndarray
    hotspots: list[ScoredHotspot]
    timings: dict[str, float] = field(default_factory=dict)


def rank_key(item: ScoredHotspot) -> tuple:
    """Tier first, then evidence, then size. The order is stable for equal scores."""
    return (
        TIER_ORDER.get(item.score.tier, 99),
        -round(item.score.biotic_score, 6),
        -item.draft.area_m2,
    )


def score_drafts(
    drafts: list[HotspotDraft], model: ScoringModel, quality_score: float
) -> list[ScoredHotspot]:
    scored = [
        ScoredHotspot(
            draft=d,
            score=score_hotspot(model, d.cues, d.mean_anomaly, d.tile_count, quality_score),
        )
        for d in drafts
    ]
    return sorted(scored, key=rank_key)


def analyze(
    rgb: np.ndarray,
    bounds: Bounds,
    params: AnalysisParams,
    model: ScoringModel,
    on_stage: Callable[[str, dict[str, float]], None] | None = None,
    should_cancel: Callable[[], bool] | None = None,
    on_mask: Callable[[np.ndarray], None] | None = None,
) -> AnalysisResult:
    """Run stages 1 to 7. The route stage needs persisted hotspot ids, so the caller runs it."""
    timings: dict[str, float] = {}
    started = {"t": time.perf_counter()}

    def enter(stage: str) -> None:
        if should_cancel is not None and should_cancel():
            raise Cancelled()
        if on_stage is not None:
            on_stage(stage, dict(timings))
        started["t"] = time.perf_counter()

    def leave(stage: str) -> None:
        timings[stage] = round(time.perf_counter() - started["t"], 3)

    enter("quality_check")
    native = FieldFrame(bounds, rgb.shape[1], rgb.shape[0])
    working, _ = resample_to_working(rgb, native.gsd_m)
    frame = FieldFrame(bounds, working.shape[1], working.shape[0])
    nodata = nodata_mask(working)
    quality = quality_check(working, nodata)
    leave("quality_check")

    enter("canopy_mask")
    norm = gray_world(working, nodata=nodata)
    canopy = canopy_mask(norm, frame.gsd_m, nodata)
    if on_mask is not None:
        on_mask(canopy.mask)
    leave("canopy_mask")

    enter("indices")
    indices = compute_indices(norm, canopy.mask)
    leave("indices")

    enter("texture")
    grid = compute_tiles(
        norm,
        canopy.mask,
        indices.greenness,
        params.tile_px,
        params.min_canopy,
        params.glcm_levels,
        nodata,
    )
    data_tiles = int((grid.nodata_frac < 0.5).sum())
    scored_share = int(grid.valid.sum()) / data_tiles if data_tiles else 0.0
    if scored_share < LOW_SCORED_SHARE:
        quality.warnings.append(
            f"Only {scored_share:.0%} of this field has enough green canopy to score, so the rest "
            "is drawn grey and not analysed. This is expected for young or ripening crops. For "
            "young crops, try a lower canopy cutoff."
        )
    leave("texture")

    enter("anomalies")
    anomaly = anomaly_scores(grid)
    gradient = build_gradient_raster(
        indices.greenness, canopy.mask, params.tile_px, frame.gsd_m
    )
    leave("anomalies")

    enter("clustering")
    drafts, flagged = cluster_hotspots(
        grid,
        frame,
        anomaly,
        params.threshold,
        params.eps,
        params.min_samples,
        params.min_cluster_m2,
        gradient,
    )
    leave("clustering")

    enter("scoring")
    hotspots = score_drafts(drafts, model, quality.score)
    leave("scoring")

    return AnalysisResult(
        params=params,
        frame=frame,
        working_rgb=working,
        quality=quality,
        canopy=canopy,
        indices=indices,
        grid=grid,
        anomaly=anomaly,
        gradient=gradient,
        flagged=flagged,
        hotspots=hotspots,
        timings=timings,
    )
