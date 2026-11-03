"""GeoJSON, CSV and labelled-dataset exports (F22). The dataset is how real training data starts."""

from __future__ import annotations

import csv
import io
import json
import zipfile

from sqlmodel import Session, select

from app.engine.scoring import CUE_NAMES
from app.models import Hotspot, Observation, Scan
from app.services.routes import scan_hotspots
from app.services.serialize import hotspot_feature, iso
from app.storage import public_dir


def _safe_cell(value):
    """A note beginning with one of these would run as a formula when opened in a spreadsheet."""
    if isinstance(value, str) and value[:1] in ("=", "+", "-", "@"):
        return "'" + value
    return value


def _write_csv(rows: list[list]) -> str:
    buffer = io.StringIO()
    csv.writer(buffer).writerows([[_safe_cell(c) for c in row] for row in rows])
    return buffer.getvalue()


def geojson_export(session: Session, scan: Scan) -> str:
    return json.dumps(
        {
            "type": "FeatureCollection",
            "features": [hotspot_feature(h) for h in scan_hotspots(session, scan.id)],
        },
        ensure_ascii=False,
    )


def csv_export(session: Session, scan: Scan) -> str:
    header = [
        "rank", "hotspot_id", "lat", "lon", "area_m2", "tier", "class", "biotic_score",
        "confidence", "status", "label", "manual", "note",
    ]
    rows = [header]
    for h in scan_hotspots(session, scan.id):
        rows.append(
            [
                h.rank, h.id, h.centroid_lat, h.centroid_lon, round(h.area_m2, 1), h.tier,
                h.hotspot_class, round(h.biotic_score, 3), h.confidence, h.status, h.label or "",
                h.manual, h.note or "",
            ]
        )
    return _write_csv(rows)


def dataset_zip(session: Session, scan: Scan) -> bytes:
    """labels.csv, features.csv and the leaf photos (TRD 6.7)."""
    hotspots = {h.id: h for h in session.exec(select(Hotspot).where(Hotspot.scan_id == scan.id))}
    observations = [
        o
        for o in session.exec(select(Observation)).all()
        if o.hotspot_id in hotspots and o.label is not None
    ]
    label_rows = [
        ["observation_id", "hotspot_id", "label", "lat", "lon", "taken_at", "confirmed_at",
         "language", "note", "photo"]
    ]
    feature_rows = [["hotspot_id", "area_m2", "mean_anomaly", "manual", *CUE_NAMES]]
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        for o in observations:
            photo_name = f"photos/{o.id}.jpg"
            label_rows.append(
                [o.id, o.hotspot_id, o.label, o.lat, o.lon, iso(o.taken_at), iso(o.confirmed_at),
                 o.language, o.note or "", photo_name]
            )
            photo = public_dir() / o.photo_path
            if photo.exists():
                archive.write(photo, photo_name)
        labelled = {o.hotspot_id for o in observations}
        for hotspot_id in sorted(labelled):
            h = hotspots[hotspot_id]
            feature_rows.append(
                [h.id, round(h.area_m2, 2), round(h.mean_anomaly, 3), h.manual,
                 *[round((h.cues or {}).get(c, 0.0), 4) for c in CUE_NAMES]]
            )
        archive.writestr("labels.csv", _write_csv(label_rows))
        archive.writestr("features.csv", _write_csv(feature_rows))
        archive.writestr(
            "README.txt",
            "AeroScout labelled dataset. Labels are farmer-confirmed ground truth.\n"
            f"Scan: {scan.id}. Check the field's data source before training: simulated fields "
            "are not real crop data.\n",
        )
    return buffer.getvalue()
