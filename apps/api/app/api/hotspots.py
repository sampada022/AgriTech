"""Hotspot detail and status, leaf-photo observations, and ground-truth confirmation."""

from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, Request, UploadFile
from sqlmodel import Session, select

from app.config import get_settings
from app.db import get_session
from app.diagnosis.guidance import guidance_for
from app.diagnosis.providers import DiagnosisContext
from app.diagnosis.service import outcome_payload, rate_limiter, run_diagnosis
from app.engine.render import write_bytes
from app.errors import ApiError, not_found
from app.models import (
    STATUS_ASSIGNED,
    STATUS_DETECTED,
    STATUS_INSPECTED,
    FieldRecord,
    Hotspot,
    Observation,
    Scan,
    new_id,
)
from app.schemas import (
    ConfirmOut,
    ConfirmRequest,
    HotspotDetail,
    HotspotFeature,
    HotspotPatch,
    ObservationOut,
)
from app.services.imaging import prepare_leaf_photo, read_upload
from app.services.model import MUTATION_LOCK, confirm_observation, rerank_scan
from app.services.routes import refresh_kpis, replan_from_previous
from app.services.serialize import hotspot_feature, observation_payload
from app.storage import public_dir

router = APIRouter(tags=["hotspots"])


def _load_hotspot(session: Session, hotspot_id: str) -> Hotspot:
    hotspot = session.get(Hotspot, hotspot_id)
    if hotspot is None:
        raise not_found("Hotspot", hotspot_id)
    return hotspot


def _observations(session: Session, hotspot_id: str) -> list[Observation]:
    rows = session.exec(select(Observation).where(Observation.hotspot_id == hotspot_id)).all()
    return sorted(rows, key=lambda o: o.taken_at, reverse=True)


@router.get(
    "/hotspots/{hotspot_id}",
    response_model=HotspotDetail,
    summary="Everything the hotspot drawer shows",
)
def get_hotspot(hotspot_id: str, session: Session = Depends(get_session)) -> dict:
    hotspot = _load_hotspot(session, hotspot_id)
    observations = _observations(session, hotspot_id)
    language = observations[0].language if observations else "en"
    return {
        "feature": hotspot_feature(hotspot),
        "observations": [observation_payload(o) for o in observations],
        "guidance": guidance_for(hotspot.label, language) if hotspot.label else None,
    }


@router.patch(
    "/hotspots/{hotspot_id}",
    response_model=HotspotFeature,
    summary="Change status or add a note",
)
def patch_hotspot(
    hotspot_id: str, body: HotspotPatch, session: Session = Depends(get_session)
) -> dict:
    with MUTATION_LOCK:
        hotspot = _load_hotspot(session, hotspot_id)
        if body.note is not None:
            hotspot.note = body.note
        if body.status is not None and body.status != hotspot.status:
            hotspot.status = body.status
            session.add(hotspot)
            session.flush()
            # Resolving a stop changes the ranking and the walk, so both need refreshing.
            scan = session.get(Scan, hotspot.scan_id)
            field = session.get(FieldRecord, scan.field_id)
            rerank_scan(session, scan.id)
            session.flush()
            replan_from_previous(session, scan, field)
            refresh_kpis(session, scan, field)
        session.add(hotspot)
        session.commit()
        return hotspot_feature(hotspot)


def _client_ip(request: Request) -> str:
    if get_settings().trust_proxy_headers:
        forwarded = request.headers.get("cf-connecting-ip")
        if forwarded:
            return forwarded
    return request.client.host if request.client else "unknown"


def _expected_type(hotspot: Hotspot) -> str:
    """Which canned demo reply suits this hotspot. Uses only what the aerial scan concluded."""
    if hotspot.hotspot_class == "likely_biotic":
        return "pest"
    if hotspot.abiotic_hint == "striping":
        return "nutrient"
    if hotspot.abiotic_hint == "large_smooth_zone":
        return "water"
    if hotspot.hotspot_class == "uncertain":
        return "pest"
    return "healthy"


@router.post(
    "/hotspots/{hotspot_id}/observations",
    response_model=ObservationOut,
    status_code=201,
    summary="Upload a leaf photo and run diagnosis",
    description="Always returns a usable reply. Check diagnosis.source: when it is `fallback`, "
    "result is null, so show diagnosis.message with diagnosis.label_options. Rate limited per IP.",
)
def create_observation(
    hotspot_id: str,
    request: Request,
    photo: UploadFile = File(description="JPG, PNG or WebP. Downscale to 1280 px on the phone."),
    lat: float | None = Form(default=None, ge=-90, le=90),
    lon: float | None = Form(default=None, ge=-180, le=180),
    language: str = Form(default="en", pattern="^(en|kn)$"),
    note: str | None = Form(default=None, max_length=2000),
    session: Session = Depends(get_session),
) -> dict:
    settings = get_settings()
    hotspot = _load_hotspot(session, hotspot_id)
    rate_limiter.check(_client_ip(request), settings.diagnosis_rate_limit_per_min)

    data = read_upload(photo, settings.max_photo_mb)
    clean, image_hash, blurry = prepare_leaf_photo(data, settings.max_photo_pixels)

    scan = session.get(Scan, hotspot.scan_id)
    field = session.get(FieldRecord, scan.field_id) if scan else None
    if field is None:
        raise ApiError(409, "field_missing", "This hotspot's field is gone.", "Reload the field.")
    context = DiagnosisContext(
        crop=field.crop,
        language=language,
        aerial_area_m2=hotspot.area_m2,
        aerial_class=hotspot.hotspot_class,
        aerial_score=hotspot.biotic_score,
        expected_type=_expected_type(hotspot),
    )
    # Runs outside any lock: an LLM call takes seconds, and pollers must not wait on it.
    outcome = run_diagnosis(clean, image_hash, context)

    observation_id = new_id("o")
    relative = f"photos/{observation_id}.jpg"
    write_bytes(public_dir() / relative, clean)
    observation = Observation(
        id=observation_id,
        hotspot_id=hotspot.id,
        photo_path=relative,
        image_hash=image_hash,
        lat=lat,
        lon=lon,
        language=language,
        ai_response=outcome_payload(outcome, language, blurry),
        ai_source=outcome.source,
        note=note,
    )
    with MUTATION_LOCK:
        session.add(observation)
        session.refresh(hotspot)
        if hotspot.status in (STATUS_DETECTED, STATUS_ASSIGNED):
            hotspot.status = STATUS_INSPECTED
            session.add(hotspot)
        session.commit()
    return observation_payload(observation)


@router.get(
    "/observations/{observation_id}",
    response_model=ObservationOut,
    summary="Read an observation",
)
def get_observation(observation_id: str, session: Session = Depends(get_session)) -> dict:
    observation = session.get(Observation, observation_id)
    if observation is None:
        raise not_found("Observation", observation_id)
    return observation_payload(observation)


@router.post(
    "/observations/{observation_id}/confirm",
    response_model=ConfirmOut,
    summary="Set the ground-truth label",
    description="Triggers recalibration: refits the model, re-scores unlabelled hotspots and "
    "re-plans the route. False alarm does not train the score. It clears the hotspot and counts "
    "toward the false-positive hint.",
)
def confirm(
    observation_id: str, body: ConfirmRequest, session: Session = Depends(get_session)
) -> dict:
    observation = session.get(Observation, observation_id)
    if observation is None:
        raise not_found("Observation", observation_id)
    return confirm_observation(session, observation, body.label, body.note)
