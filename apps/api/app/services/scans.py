"""Running analyses and persisting what they produce.

One worker thread gives "analyses queued one at a time" (TRD 8.4). The API returns the scan id at
once and the UI polls for progress.
"""

from __future__ import annotations

import json
import logging
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import cv2
import numpy as np
from shapely.geometry import Point
from sqlmodel import Session, select

from app.db import new_session
from app.engine.geo import FieldFrame
from app.engine.hotspots import cluster_hotspots, describe_members
from app.engine.pipeline import (
    STAGE_PROGRESS,
    AnalysisParams,
    AnalysisResult,
    Cancelled,
    ScoredHotspot,
    analyze,
    score_drafts,
)
from app.engine.render import (
    crop_jpeg,
    heat_overlay,
    mask_preview,
    rgb_overlay,
    vari_overlay,
    write_bytes,
)
from app.engine.tiles import TileGrid
from app.errors import ApiError
from app.models import (
    SCAN_CANCELLED,
    SCAN_DONE,
    SCAN_FAILED,
    SCAN_QUEUED,
    SCAN_RUNNING,
    STATUS_ASSIGNED,
    STATUS_DETECTED,
    FieldRecord,
    Hotspot,
    Observation,
    Scan,
    new_id,
    utcnow,
)
from app.services.geometry import bounds_of, frame_of, geojson_to_polygon, polygon_to_geojson
from app.services.imaging import load_rgb
from app.services.model import (
    MUTATION_LOCK,
    active_model,
    apply_score,
    rerank_scan,
)
from app.services.routes import create_route, refresh_kpis, replan_from_previous
from app.storage import field_image_path, public_dir, scan_private_dir

log = logging.getLogger("aeroscout.analysis")

_worker = ThreadPoolExecutor(max_workers=1, thread_name_prefix="analysis")


def params_from_request(
    tile_px: int | None,
    threshold: float | None,
    eps: float | None,
    min_canopy: float | None = None,
) -> AnalysisParams:
    defaults = AnalysisParams()
    return AnalysisParams(
        tile_px=tile_px or defaults.tile_px,
        threshold=defaults.threshold if threshold is None else threshold,
        eps=defaults.eps if eps is None else eps,
        min_canopy=defaults.min_canopy if min_canopy is None else min_canopy,
    )


def params_from_row(scan: Scan) -> AnalysisParams:
    defaults = AnalysisParams()
    stored = scan.params or {}
    return AnalysisParams(
        tile_px=stored.get("tile_px", defaults.tile_px),
        threshold=stored.get("threshold", defaults.threshold),
        eps=stored.get("eps", defaults.eps),
        min_samples=stored.get("min_samples", defaults.min_samples),
        min_canopy=stored.get("min_canopy", defaults.min_canopy),
    )


def create_scan(session: Session, field: FieldRecord, params: AnalysisParams) -> Scan:
    scan = Scan(id=new_id("s"), field_id=field.id, params=params.as_dict())
    session.add(scan)
    session.commit()
    _worker.submit(_run_scan_safely, scan.id)
    return scan


def _update(scan_id: str, **values) -> None:
    with new_session() as session:
        scan = session.get(Scan, scan_id)
        if scan is None:
            return
        for key, value in values.items():
            setattr(scan, key, value)
        session.add(scan)
        session.commit()


def _cancel_requested(scan_id: str) -> bool:
    with new_session() as session:
        scan = session.get(Scan, scan_id)
        return scan is None or scan.cancel_requested


def _run_scan_safely(scan_id: str) -> None:
    try:
        run_scan(scan_id)
    except Cancelled:
        log.info("scan_cancelled scan=%s", scan_id)
        _update(scan_id, status=SCAN_CANCELLED, finished_at=utcnow())
    except Exception as exc:  # noqa: BLE001  (a worker failure must reach the polling UI)
        log.exception("scan_failed scan=%s", scan_id)
        message = "The analysis could not finish on this image."
        hint = "Check the image and bounds, or load a demo scenario."
        if isinstance(exc, ValueError):
            message = str(exc)
        _update(
            scan_id,
            status=SCAN_FAILED,
            finished_at=utcnow(),
            error={"code": "analysis_failed", "message": message, "hint": hint},
        )


def run_scan(scan_id: str) -> None:
    with new_session() as session:
        scan = session.get(Scan, scan_id)
        if scan is None:
            return
        field = session.get(FieldRecord, scan.field_id)
        if scan.cancel_requested:
            raise Cancelled()
        scan.status = SCAN_RUNNING
        scan.started_at = utcnow()
        session.add(scan)
        session.commit()
        params = params_from_row(scan)
        model = active_model(session)
        bounds = bounds_of(field)
        field_id = field.id

    rgb = load_rgb(field_image_path(field_id))

    def on_stage(stage: str, timings: dict[str, float]) -> None:
        _update(scan_id, stage=stage, progress=STAGE_PROGRESS[stage], stage_timings=timings)

    def on_mask(mask: np.ndarray) -> None:
        relative = f"{scan_id}/mask.webp"
        write_bytes(public_dir() / relative, mask_preview(mask))
        _update(scan_id, mask_path=relative)

    result = analyze(
        rgb,
        bounds,
        params,
        model,
        on_stage=on_stage,
        should_cancel=lambda: _cancel_requested(scan_id),
        on_mask=on_mask,
    )
    on_stage("route", result.timings)

    finish_started = utcnow()
    hotspot_ids = [new_id("h") for _ in result.hotspots]
    layers = write_layers(public_dir() / scan_id, scan_id, result)
    write_engine_cache(scan_private_dir(scan_id), result)

    with new_session() as session, MUTATION_LOCK:
        scan = session.get(Scan, scan_id)
        field = session.get(FieldRecord, scan.field_id)
        for rank, (item, hotspot_id) in enumerate(zip(result.hotspots, hotspot_ids), start=1):
            relative = f"{scan_id}/crops/{hotspot_id}.jpg"
            write_bytes(
                public_dir() / relative,
                crop_jpeg(result.working_rgb, item.draft.polygon, result.frame),
            )
            session.add(hotspot_row(hotspot_id, scan_id, result.frame, item, rank, relative))
        scan.quality = result.quality.as_dict()
        scan.quality_score = result.quality.score
        scan.canopy_pct = round(result.canopy.canopy_pct, 1)
        scan.layers = layers
        scan.grid = grid_summary(result)
        scan.version_used = model.version
        session.add(scan)
        session.flush()
        create_route(session, scan, field)
        refresh_kpis(session, scan, field)
        timings = dict(result.timings)
        timings["route"] = round((utcnow() - finish_started).total_seconds(), 3)
        scan.stage_timings = timings
        scan.status = SCAN_DONE
        scan.progress = 100
        scan.finished_at = utcnow()
        session.add(scan)
        session.commit()
    log.info(
        "scan_done scan=%s hotspots=%d timings=%s",
        scan_id, len(hotspot_ids), json.dumps(timings),
    )


def grid_summary(result: AnalysisResult) -> dict:
    grid = result.grid
    frame = result.frame
    has_data = grid.nodata_frac < 0.5
    tiles_with_data = int(has_data.sum())
    return {
        "tile_px": grid.tile_px,
        "ny": grid.ny,
        "nx": grid.nx,
        "tiles_total": tiles_with_data,
        "tiles_excluded": tiles_with_data - int(grid.valid.sum()),
        "tiles_nodata": int(grid.ny * grid.nx) - tiles_with_data,
        "tiles_flagged": int(result.flagged.sum()),
        "working_width": frame.image_width,
        "working_height": frame.image_height,
        "gsd_cm": round(frame.gsd_m * 100, 2),
        "data_fraction": round(result.canopy.data_fraction, 4),
        "default_start": _default_start(grid, frame),
    }


def _default_start(grid: TileGrid, frame: FieldFrame) -> dict | None:
    """Where a walk starts by default: the field tile nearest the south-west corner.

    An orthomosaic's bounding-box corner can sit in the empty margin, off the field entirely.
    """
    rows, cols = np.nonzero(grid.nodata_frac < 0.5)
    if rows.size == 0:
        return None
    nearest = int(np.argmin((grid.ny - 1 - rows) ** 2 + cols**2))
    t = grid.tile_px
    x, y = frame.px_to_xy((cols[nearest] + 0.5) * t, (rows[nearest] + 0.5) * t)
    lat, lon = frame.xy_to_latlon(x, y)
    return {"lat": round(lat, 7), "lon": round(lon, 7)}


def write_layers(out_dir: Path, scan_id: str, result: AnalysisResult) -> dict:
    """Map layers under the byte budget. Layer toggles flip visibility and never re-fetch."""
    encoded = {
        "rgb": rgb_overlay(result.working_rgb, result.canopy.nodata),
        "vari": vari_overlay(result.indices.vari, result.grid),
        "heat": heat_overlay(result.anomaly, result.grid),
    }
    layers = {}
    for name, data in encoded.items():
        relative = f"layers/{name}.webp"
        write_bytes(out_dir / relative, data)
        layers[name] = {"path": f"{scan_id}/{relative}", "bytes": len(data), "format": "webp"}
    return layers


def write_engine_cache(out_dir: Path, result: AnalysisResult) -> None:
    """What the sensitivity slider and manual hotspots need to skip the heavy stages."""
    out_dir.mkdir(parents=True, exist_ok=True)
    np.savez(
        out_dir / "cache.npz",
        anomaly=result.anomaly.astype(np.float32),
        gradient=result.gradient,
        **result.grid.to_arrays(),
    )
    cv2.imwrite(
        str(out_dir / "working.jpg"),
        cv2.cvtColor(result.working_rgb, cv2.COLOR_RGB2BGR),
        [cv2.IMWRITE_JPEG_QUALITY, 92],
    )


def hotspot_row(
    hotspot_id: str,
    scan_id: str,
    frame: FieldFrame,
    item: ScoredHotspot,
    rank: int,
    crop_path: str | None,
    manual: bool = False,
    note: str | None = None,
) -> Hotspot:
    draft, score = item.draft, item.score
    lat, lon = frame.xy_to_latlon(*draft.centroid_xy)
    return Hotspot(
        id=hotspot_id,
        scan_id=scan_id,
        polygon=polygon_to_geojson(frame, draft.polygon),
        centroid_lat=round(lat, 7),
        centroid_lon=round(lon, 7),
        area_m2=draft.area_m2,
        tile_count=draft.tile_count,
        cues=draft.cues,
        mean_anomaly=draft.mean_anomaly,
        biotic_score=score.biotic_score,
        hotspot_class=score.hotspot_class,
        tier=score.tier,
        confidence_score=score.confidence_score,
        confidence=score.confidence,
        contributions=score.contributions,
        abiotic_hint=score.abiotic_hint,
        status=STATUS_DETECTED,
        manual=manual,
        crop_path=crop_path,
        rank=rank,
        note=note,
    )


@dataclass
class EngineCache:
    grid: TileGrid
    anomaly: np.ndarray
    gradient: np.ndarray
    rgb: np.ndarray


@lru_cache(maxsize=2)
def load_engine_cache(scan_id: str) -> EngineCache:
    """Kept in memory because the slider fires repeatedly on the same scan."""
    directory = scan_private_dir(scan_id)
    with np.load(directory / "cache.npz") as data:
        grid = TileGrid.from_arrays(data)
        anomaly = data["anomaly"]
        gradient = data["gradient"]
    rgb = cv2.cvtColor(cv2.imread(str(directory / "working.jpg")), cv2.COLOR_BGR2RGB)
    return EngineCache(grid, anomaly, gradient, rgb)


def clear_engine_cache() -> None:
    load_engine_cache.cache_clear()


def _require_cache(scan: Scan) -> EngineCache:
    if scan.status != SCAN_DONE:
        raise ApiError(
            409,
            "scan_not_ready",
            "This scan has not finished yet.",
            "Wait for the analysis to complete, then try again.",
        )
    try:
        return load_engine_cache(scan.id)
    except FileNotFoundError as exc:
        raise ApiError(
            409,
            "scan_cache_missing",
            "The cached analysis for this scan is gone.",
            "Start a new scan of this field.",
        ) from exc


def apply_threshold(session: Session, scan: Scan, field: FieldRecord, threshold: float) -> None:
    """Sensitivity slider (F7): re-cluster from cached tile features, without re-running GLCM.

    Hotspots someone has worked on (labelled, photographed, inspected or added by hand) stay put.
    New clusters overlapping them are dropped, so a label is never orphaned by a slider move.
    """
    with MUTATION_LOCK:
        cache = _require_cache(scan)
        frame = frame_of(field, scan)
        params = params_from_row(scan)
        model = active_model(session)

        existing = session.exec(select(Hotspot).where(Hotspot.scan_id == scan.id)).all()
        observed = {
            o.hotspot_id
            for o in session.exec(select(Observation)).all()
            if o.hotspot_id in {h.id for h in existing}
        }
        kept, disposable = [], []
        for hotspot in existing:
            untouched = (
                hotspot.status in (STATUS_DETECTED, STATUS_ASSIGNED)
                and hotspot.label is None
                and not hotspot.manual
                and hotspot.id not in observed
            )
            (disposable if untouched else kept).append(hotspot)

        for hotspot in disposable:
            if hotspot.crop_path:
                (public_dir() / hotspot.crop_path).unlink(missing_ok=True)
            session.delete(hotspot)
        session.flush()

        kept_polygons = [geojson_to_polygon(frame, h.polygon) for h in kept]
        drafts, flagged = cluster_hotspots(
            cache.grid,
            frame,
            cache.anomaly,
            threshold,
            params.eps,
            params.min_samples,
            params.min_cluster_m2,
            cache.gradient,
        )
        drafts = [
            d
            for d in drafts
            if not any(d.polygon.intersects(existing_poly) for existing_poly in kept_polygons)
        ]
        quality = scan.quality_score if scan.quality_score is not None else 1.0
        for item in score_drafts(drafts, model, quality):
            hotspot_id = new_id("h")
            relative = f"{scan.id}/crops/{hotspot_id}.jpg"
            write_bytes(
                public_dir() / relative, crop_jpeg(cache.rgb, item.draft.polygon, frame)
            )
            session.add(hotspot_row(hotspot_id, scan.id, frame, item, 0, relative))
        session.flush()
        rerank_scan(session, scan.id)
        session.flush()

        scan.params = {**(scan.params or {}), "threshold": threshold}
        scan.grid = {**(scan.grid or {}), "tiles_flagged": int(flagged.sum())}
        session.add(scan)
        session.flush()
        replan_from_previous(session, scan, field)
        refresh_kpis(session, scan, field)
        session.commit()


def add_manual_hotspot(
    session: Session,
    scan: Scan,
    field: FieldRecord,
    lat: float,
    lon: float,
    radius_m: float,
    note: str | None,
) -> Hotspot:
    """Something the drone missed (F21). It gets real cues, so it can join the labelled dataset."""
    with MUTATION_LOCK:
        cache = _require_cache(scan)
        frame = frame_of(field, scan)
        x, y = frame.latlon_to_xy(lat, lon)
        if abs(x) > frame.width_m / 2 or abs(y) > frame.height_m / 2:
            raise ApiError(
                422,
                "outside_field",
                "That point is outside this field.",
                "Tap a spot inside the field boundary.",
            )
        polygon = Point(x, y).buffer(radius_m, 16)
        t = cache.grid.tile_px
        px, py = frame.xy_to_px(x, y)
        reach_x = radius_m / (t * frame.gsd_x)
        reach_y = radius_m / (t * frame.gsd_y)
        col_c, row_c = px / t - 0.5, py / t - 0.5
        rows_all, cols_all = np.mgrid[0 : cache.grid.ny, 0 : cache.grid.nx]
        inside = ((cols_all - col_c) / max(reach_x, 1e-6)) ** 2 + (
            (rows_all - row_c) / max(reach_y, 1e-6)
        ) ** 2 <= 1
        if not inside.any():
            inside[
                int(np.clip(round(row_c), 0, cache.grid.ny - 1)),
                int(np.clip(round(col_c), 0, cache.grid.nx - 1)),
            ] = True
        rows, cols = np.nonzero(inside)
        params = params_from_row(scan)
        flagged = cache.grid.valid & (cache.anomaly >= params.threshold)
        draft = describe_members(
            rows, cols, polygon, cache.grid, frame, cache.anomaly, flagged, cache.gradient
        )
        model = active_model(session)
        quality = scan.quality_score if scan.quality_score is not None else 1.0
        item = score_drafts([draft], model, quality)[0]
        hotspot_id = new_id("h")
        relative = f"{scan.id}/crops/{hotspot_id}.jpg"
        write_bytes(public_dir() / relative, crop_jpeg(cache.rgb, polygon, frame))
        hotspot = hotspot_row(
            hotspot_id, scan.id, frame, item, 0, relative, manual=True, note=note
        )
        apply_score(hotspot, model, quality)
        session.add(hotspot)
        session.flush()
        rerank_scan(session, scan.id)
        session.flush()
        replan_from_previous(session, scan, field)
        refresh_kpis(session, scan, field)
        session.commit()
        return hotspot


def fail_interrupted_scans() -> None:
    """A restart kills the worker, so anything still marked as running will never finish."""
    with new_session() as session:
        stale = session.exec(
            select(Scan).where(Scan.status.in_((SCAN_QUEUED, SCAN_RUNNING)))
        ).all()
        for scan in stale:
            scan.status = SCAN_FAILED
            scan.finished_at = utcnow()
            scan.error = {
                "code": "interrupted",
                "message": "The server restarted during this analysis.",
                "hint": "Start the scan again.",
            }
            session.add(scan)
        session.commit()
