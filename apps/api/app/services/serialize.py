"""Database rows to API dictionaries. The Hotspot shape here is the contract in TRD 7.2."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlmodel import Session, select

from app.engine.pipeline import STAGES
from app.models import FieldRecord, Hotspot, Observation, Scan, utcnow
from app.services.geometry import bounds_of
from app.storage import public_url

SOURCE_BADGES = {
    "synthetic": "Synthetic data",
    "stand_in": "Real pixels, stand-in field",
    "real": "Real flight",
}

HINT_TEXT = {
    "striping": "Strong directional pattern: this reads as a nutrient, irrigation or planting "
    "pattern.",
    "large_smooth_zone": "Large smooth zone: this reads as water stress.",
}


def iso(value: datetime | None) -> str | None:
    """SQLite drops the timezone. Everything is stored in UTC, so say so explicitly."""
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.isoformat().replace("+00:00", "Z")


def _aware(value: datetime) -> datetime:
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


def bounds_payload(field: FieldRecord) -> dict:
    bounds = bounds_of(field)
    return {**bounds.as_dict(), "leaflet": bounds.as_leaflet()}


def scan_payload(scan: Scan, field: FieldRecord) -> dict:
    elapsed = None
    if scan.started_at is not None:
        end = _aware(scan.finished_at) if scan.finished_at else utcnow()
        elapsed = round((end - _aware(scan.started_at)).total_seconds(), 2)
    layers = {
        name: {**info, "url": public_url(info["path"])}
        for name, info in (scan.layers or {}).items()
    }
    for info in layers.values():
        info.pop("path", None)
    return {
        "id": scan.id,
        "field_id": scan.field_id,
        "status": scan.status,
        "stage": scan.stage,
        "stages": list(STAGES),
        "progress": scan.progress,
        "elapsed_s": elapsed,
        "stage_timings": scan.stage_timings or {},
        "params": scan.params or {},
        "quality": scan.quality,
        "canopy_pct": scan.canopy_pct,
        "mask_preview_url": public_url(scan.mask_path),
        "layers": layers,
        "bounds": bounds_payload(field),
        "grid": scan.grid,
        "kpis": scan.kpis,
        "model_version_used": scan.version_used,
        "data_source": field.data_source,
        "data_source_badge": SOURCE_BADGES.get(field.data_source, field.data_source),
        "error": scan.error,
        "created_at": iso(scan.created_at),
        "started_at": iso(scan.started_at),
        "finished_at": iso(scan.finished_at),
    }


def scan_summary(scan: Scan) -> dict:
    kpis = scan.kpis or {}
    return {
        "id": scan.id,
        "status": scan.status,
        "progress": scan.progress,
        "hotspot_count": kpis.get("hotspot_count"),
        "tier_counts": kpis.get("tier_counts"),
        "created_at": iso(scan.created_at),
        "finished_at": iso(scan.finished_at),
    }


def latest_scan(session: Session, field_id: str) -> Scan | None:
    rows = session.exec(select(Scan).where(Scan.field_id == field_id)).all()
    return max(rows, key=lambda s: _aware(s.created_at)) if rows else None


def field_payload(session: Session, field: FieldRecord) -> dict:
    latest = latest_scan(session, field.id)
    return {
        "id": field.id,
        "name": field.name,
        "crop": field.crop,
        "data_source": field.data_source,
        "data_source_badge": SOURCE_BADGES.get(field.data_source, field.data_source),
        "bounds": bounds_payload(field),
        "thumbnail_url": public_url(field.thumbnail_path),
        "image_width": field.image_width,
        "image_height": field.image_height,
        "gsd_cm": round(field.gsd_cm, 2),
        "altitude_m": field.altitude_m,
        "created_at": iso(field.created_at),
        "latest_scan": scan_summary(latest) if latest else None,
    }


def hotspot_feature(hotspot: Hotspot) -> dict:
    """GeoJSON Feature, the object every screen consumes."""
    cues = hotspot.cues or {}
    contributions = hotspot.contributions or {}
    return {
        "type": "Feature",
        "id": hotspot.id,
        "geometry": hotspot.polygon,
        "properties": {
            "scan_id": hotspot.scan_id,
            "rank": hotspot.rank,
            "previous_rank": hotspot.previous_rank,
            "area_m2": round(hotspot.area_m2, 1),
            "centroid": {"lat": hotspot.centroid_lat, "lon": hotspot.centroid_lon},
            "tile_count": hotspot.tile_count,
            "tier": hotspot.tier,
            "previous_tier": hotspot.previous_tier,
            "biotic_score": round(hotspot.biotic_score, 3),
            "class": hotspot.hotspot_class,
            "confidence": hotspot.confidence,
            "confidence_score": round(hotspot.confidence_score, 3),
            "mean_anomaly": round(hotspot.mean_anomaly, 2),
            "cues": {k: round(v, 3) for k, v in cues.items()},
            "contributions": {k: round(v, 3) for k, v in contributions.items()},
            "abiotic_hint": hotspot.abiotic_hint,
            "abiotic_hint_text": HINT_TEXT.get(hotspot.abiotic_hint or ""),
            "status": hotspot.status,
            "label": hotspot.label,
            "manual": hotspot.manual,
            "note": hotspot.note,
            "crop_url": public_url(hotspot.crop_path),
        },
    }


def observation_payload(observation: Observation) -> dict:
    block = observation.ai_response or {}
    return {
        "id": observation.id,
        "hotspot_id": observation.hotspot_id,
        "photo_url": public_url(observation.photo_path),
        "lat": observation.lat,
        "lon": observation.lon,
        "taken_at": iso(observation.taken_at),
        "language": observation.language,
        "label": observation.label,
        "note": observation.note,
        "confirmed_at": iso(observation.confirmed_at),
        "diagnosis": block or None,
    }
