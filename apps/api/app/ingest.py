"""Start a new farmer survey on the real engine, and the farmer-facing report/notify glue.

A Farm's plot is tracked as one FieldRecord (same id as the Farm), reused across repeated surveys;
each survey is a Scan. The PDF report is built lazily, the first time it's asked for after the scan
finishes, rather than eagerly from a completion hook.
"""
from __future__ import annotations

from pathlib import Path

from sqlmodel import Session, select

from . import reports
from .db import REPORTS
from .engine.geo import bounds_from_centre
from .engine.pipeline import AnalysisParams
from .engine.render import thumbnail_jpeg, write_bytes
from .models import SCAN_DONE, Farm, Farmer, FieldRecord, Hotspot, Report, Scan, now
from .services.imaging import encode_jpeg, load_rgb
from .services.routes import latest_route
from .services.scans import create_scan
from .storage import field_image_path, public_dir

# Mandya-area reference point, used when a sample/upload carries no real GPS bounds.
DEFAULT_LAT = 12.5240
DEFAULT_LON = 76.9000


def ensure_field(session: Session, farm: Farm, image_path: Path, gsd_cm: float, data_source: str = "real") -> FieldRecord:
    """One FieldRecord per farm (same id), reused across repeated surveys; its base image is replaced each time."""
    rgb = load_rgb(image_path)
    height, width = rgb.shape[:2]
    target = field_image_path(farm.id)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(encode_jpeg(rgb, 92, full_chroma=True))

    # Thumbnail lives under the public root (served at /files/...); the original field photo
    # under the private root never is.
    thumb_relative = f"{farm.id}/thumb.jpg"
    write_bytes(public_dir() / thumb_relative, thumbnail_jpeg(rgb))

    width_m = width * gsd_cm / 100
    height_m = height * gsd_cm / 100
    bounds = bounds_from_centre(DEFAULT_LAT, DEFAULT_LON, width_m, height_m)

    field = session.get(FieldRecord, farm.id)
    if field is None:
        field = FieldRecord(
            id=farm.id, name=farm.name, crop=farm.crop, data_source=data_source,
            sw_lat=bounds.sw_lat, sw_lon=bounds.sw_lon, ne_lat=bounds.ne_lat, ne_lon=bounds.ne_lon,
            image_path=str(target), thumbnail_path=thumb_relative, image_width=width, image_height=height,
            gsd_cm=gsd_cm,
        )
    else:
        field.name, field.crop, field.data_source = farm.name, farm.crop, data_source
        field.sw_lat, field.sw_lon = bounds.sw_lat, bounds.sw_lon
        field.ne_lat, field.ne_lon = bounds.ne_lat, bounds.ne_lon
        field.image_path, field.thumbnail_path = str(target), thumb_relative
        field.image_width, field.image_height, field.gsd_cm = width, height, gsd_cm
    session.add(field)
    session.commit()
    session.refresh(field)
    return field


def start_survey(session: Session, farm_id: str, image_path: Path, gsd_cm: float = 3.0, data_source: str = "real") -> Scan:
    """Create/refresh the farm's FieldRecord and queue a new scan. Runs on Preet's own worker thread."""
    farm = session.get(Farm, farm_id)
    if farm is None:
        raise ValueError(f"Unknown farm {farm_id}")
    field = ensure_field(session, farm, image_path, gsd_cm, data_source)
    return create_scan(session, field, AnalysisParams())


def ensure_report(session: Session, scan: Scan) -> Report | None:
    """Build the farmer PDF the first time it's asked for after the scan finishes."""
    if scan.status != SCAN_DONE:
        return None
    existing = session.exec(select(Report).where(Report.scan_id == scan.id)).first()
    if existing is not None and Path(existing.path).exists():
        return existing
    field = session.get(FieldRecord, scan.field_id)
    farm = session.get(Farm, field.id)  # FieldRecord.id == Farm.id
    farmer = session.get(Farmer, farm.farmer_id)
    hotspots = session.exec(select(Hotspot).where(Hotspot.scan_id == scan.id).order_by(Hotspot.rank)).all()
    route = latest_route(session, scan.id)
    report_id = f"RPT-{scan.id}-v1"
    out = REPORTS / f"{report_id}.pdf"
    map_img = reports.build_map(field, scan, hotspots)
    html = reports.build_html(scan, field, farmer, farm, hotspots, route, map_img, now().strftime("%d %b %Y, %H:%M UTC"))
    reports.render_pdf(html, out)
    rep = Report(id=report_id, scan_id=scan.id, farmer_id=farmer.id, version=1, path=str(out))
    session.add(rep)
    session.commit()
    return rep


def notify_survey(session: Session, scan: Scan) -> dict:
    """SMS the farmer that the survey is done (Kannada or English, crop-aware). Mock gateway in the prototype."""
    from . import security as sec
    from .sms import notify_text, provider

    field = session.get(FieldRecord, scan.field_id)
    farm = session.get(Farm, field.id)
    farmer = session.get(Farmer, farm.farmer_id)
    if not farmer.sms_consent:
        return {"sent": False, "reason": "no SMS consent"}
    hotspots = session.exec(select(Hotspot).where(Hotspot.scan_id == scan.id)).all()
    provider.send(
        session, farmer.mobile,
        notify_text(farmer.language, len(hotspots) > 0, farmer.collection_point, farmer.id, farm.crop),
        "NOTIFY",
    )
    return {"sent": True, "to": sec.mask_mobile(farmer.mobile)}
