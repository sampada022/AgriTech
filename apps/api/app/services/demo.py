"""Demo scenarios, precomputed so a click loads in under a second (F3, F17, TRD 8.4).

    python -m app.services.demo        # builds all three bundles under demo_assets/

Every scenario is synthetic and says so. Ids are stable, so QR codes and rehearsal notes survive
a reload. Loading a scenario again replaces it with a fresh copy.
"""

from __future__ import annotations

import json
import shutil
import time

from sqlmodel import Session, select

from app.config import get_settings
from app.engine.pipeline import AnalysisParams, analyze
from app.engine.render import crop_jpeg, mask_preview, thumbnail_jpeg, write_bytes
from app.engine.scoring import ScoringModel
from app.engine.simulator import SCENARIOS, SimConfig, save, simulate
from app.errors import ApiError
from app.models import FieldRecord, Hotspot, ModelVersion, Observation, Route, Scan, utcnow
from app.services.demo_settings import demo_settings
from app.services.model import ensure_prior, rescore_all, active_model, MUTATION_LOCK
from app.services.routes import create_route, refresh_kpis
from app.services.scans import (
    clear_engine_cache,
    grid_summary,
    hotspot_row,
    write_engine_cache,
    write_layers,
)
from app.storage import field_image_path, public_dir, remove_scan_files, scan_private_dir, wipe_all

# Seeds picked by looking at the output. See scripts/pick_demo_seed.py for how mixed was chosen.
SCENARIO_CONFIG = {
    "healthy": {"seed": 11, "name": "Demo · Healthy field", "crop": "Maize"},
    "pest": {"seed": 7, "name": "Demo · Pest outbreak", "crop": "Maize"},
    "mixed": {"seed": 18, "name": "Demo · Mixed stress", "crop": "Maize"},
}


def _bundle_dir(scenario: str):
    return get_settings().demo_assets_dir / scenario


def build_bundle(scenario: str) -> dict:
    """Run the real pipeline with the prior model and store everything needed to load it fast."""
    config = SCENARIO_CONFIG[scenario]
    field_id, scan_id = f"f_{scenario}", f"s_{scenario}"
    out = _bundle_dir(scenario)
    shutil.rmtree(out, ignore_errors=True)
    (out / "public").mkdir(parents=True)

    sim = simulate(SimConfig(scenario, "medium", config["seed"]))
    save(sim, out / "source")
    params = AnalysisParams()
    result = analyze(sim.image, sim.bounds, params, ScoringModel.prior())

    layers = write_layers(out / "public", scan_id, result)
    write_engine_cache(out / "private", result)
    write_bytes(out / "public" / "mask.webp", mask_preview(result.canopy.mask))
    write_bytes(out / "public" / "thumb.jpg", thumbnail_jpeg(result.working_rgb))

    hotspots = []
    for rank, item in enumerate(result.hotspots, start=1):
        hotspot_id = f"h_{scenario}_{rank:02d}"
        relative = f"crops/{hotspot_id}.jpg"
        write_bytes(
            out / "public" / relative,
            crop_jpeg(result.working_rgb, item.draft.polygon, result.frame),
        )
        row = hotspot_row(
            hotspot_id, scan_id, result.frame, item, rank, f"{scan_id}/{relative}"
        )
        hotspots.append(row.model_dump())

    timings = dict(result.timings)
    bundle = {
        "scenario": scenario,
        "synthetic": True,
        "field": {
            "id": field_id,
            "name": config["name"],
            "crop": config["crop"],
            "data_source": "synthetic",
            **sim.bounds.as_dict(),
            "thumbnail_path": f"{scan_id}/thumb.jpg",
            "image_path": str(field_image_path(field_id).name),
            "image_width": sim.image.shape[1],
            "image_height": sim.image.shape[0],
            "gsd_cm": sim.config.gsd_m * 100,
        },
        "scan": {
            "id": scan_id,
            "field_id": field_id,
            "params": params.as_dict(),
            "quality": result.quality.as_dict(),
            "quality_score": result.quality.score,
            "canopy_pct": round(result.canopy.canopy_pct, 1),
            "layers": layers,
            "mask_path": f"{scan_id}/mask.webp",
            "stage_timings": timings,
            "grid": grid_summary(result),
        },
        "hotspots": hotspots,
    }
    (out / "bundle.json").write_text(json.dumps(bundle, indent=1), encoding="utf-8")
    return bundle


def build_all() -> None:
    for scenario in SCENARIOS:
        started = time.perf_counter()
        bundle = build_bundle(scenario)
        tiers: dict[str, int] = {}
        for hotspot in bundle["hotspots"]:
            tiers[hotspot["tier"]] = tiers.get(hotspot["tier"], 0) + 1
        print(
            f"{scenario:<8} hotspots={len(bundle['hotspots']):<3} tiers={tiers} "
            f"built in {time.perf_counter() - started:.1f}s"
        )


def _remove_scenario(session: Session, field_id: str, scan_id: str) -> None:
    """Delete a demo field and everything under it, including scans started by hand on it."""
    scan_rows = session.exec(select(Scan).where(Scan.field_id == field_id)).all()
    scan_ids = {scan.id for scan in scan_rows} | {scan_id}
    hotspots = [h for h in session.exec(select(Hotspot)).all() if h.scan_id in scan_ids]
    hotspot_ids = {h.id for h in hotspots}
    for observation in session.exec(select(Observation)).all():
        if observation.hotspot_id in hotspot_ids:
            (public_dir() / observation.photo_path).unlink(missing_ok=True)
            session.delete(observation)
    for hotspot in hotspots:
        session.delete(hotspot)
    for route in session.exec(select(Route)).all():
        if route.scan_id in scan_ids:
            session.delete(route)
    for scan in scan_rows:
        session.delete(scan)
    field = session.get(FieldRecord, field_id)
    if field is not None:
        session.delete(field)
    session.flush()
    for identifier in scan_ids:
        remove_scan_files(identifier)


def load_scenario(session: Session, scenario: str) -> dict:
    """Copy a prebuilt bundle into place and insert its rows, then apply the current model."""
    if scenario not in SCENARIO_CONFIG:
        raise ApiError(
            404,
            "scenario_not_found",
            f"There is no demo scenario called {scenario}.",
            f"Choose one of: {', '.join(SCENARIOS)}.",
        )
    started = time.perf_counter()
    directory = _bundle_dir(scenario)
    if not (directory / "bundle.json").exists():
        build_bundle(scenario)  # slow path, so the demo still works if assets were never built
    bundle = json.loads((directory / "bundle.json").read_text(encoding="utf-8"))

    with MUTATION_LOCK:
        field_id, scan_id = bundle["field"]["id"], bundle["scan"]["id"]
        _remove_scenario(session, field_id, scan_id)
        clear_engine_cache()

        shutil.copytree(directory / "public", public_dir() / scan_id, dirs_exist_ok=True)
        shutil.copytree(directory / "private", scan_private_dir(scan_id), dirs_exist_ok=True)
        image_target = field_image_path(field_id)
        image_target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(directory / "source" / "field.jpg", image_target)

        field_row = FieldRecord(**bundle["field"])
        scan = Scan(
            **bundle["scan"],
            status="done",
            stage="route",
            progress=100,
            started_at=utcnow(),
            finished_at=utcnow(),
        )
        session.add(field_row)
        session.add(scan)
        session.flush()
        for row in bundle["hotspots"]:
            session.add(Hotspot(**row))
        session.flush()

        # The bundle was built with the priors, so bring it up to the current model.
        rescore_all(session, active_model(session))
        create_route(session, scan, field_row)
        refresh_kpis(session, scan, field_row)
        session.commit()

    return {
        "scenario": scenario,
        "field_id": field_id,
        "scan_id": scan_id,
        "load_seconds": round(time.perf_counter() - started, 3),
        "synthetic": True,
    }


def reset_all(session: Session) -> None:
    """Delete everything, including photos and cached AI replies, and return to the priors."""
    with MUTATION_LOCK:
        for table in (Observation, Hotspot, Route, Scan, FieldRecord, ModelVersion):
            for row in session.exec(select(table)).all():
                session.delete(row)
        session.commit()
        clear_engine_cache()
        wipe_all()
        demo_settings.reset()
        ensure_prior(session)


if __name__ == "__main__":
    build_all()
