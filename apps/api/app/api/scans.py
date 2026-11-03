"""Scan status, hotspots, layers, routes, the sensitivity slider and exports."""

from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Depends, Response
from fastapi.responses import FileResponse
from sqlmodel import Session

from app import ingest
from app.db import get_session
from app.errors import ApiError, not_found
from app.models import SCAN_CANCELLED, SCAN_DONE, SCAN_FAILED, FieldRecord, Scan
from app.schemas import (
    HotspotCollection,
    HotspotFeature,
    LayerOut,
    ManualHotspotCreate,
    RouteCreate,
    RouteOut,
    ScanOut,
    ScanWithHotspots,
    ThresholdUpdate,
)
from app.services.exports import csv_export, dataset_zip, geojson_export
from app.services.routes import (
    create_route,
    latest_route,
    refresh_kpis,
    route_payload,
    scan_hotspots,
)
from app.services.scans import add_manual_hotspot, apply_threshold
from app.services.serialize import bounds_payload, hotspot_feature, scan_payload
from app.storage import public_url

router = APIRouter(tags=["scans"])


def load_scan(session: Session, scan_id: str) -> tuple[Scan, FieldRecord]:
    scan = session.get(Scan, scan_id)
    if scan is None:
        raise not_found("Scan", scan_id)
    field = session.get(FieldRecord, scan.field_id)
    if field is None:
        raise not_found("Field", scan.field_id)
    return scan, field


def _require_done(scan: Scan) -> None:
    if scan.status != SCAN_DONE:
        raise ApiError(
            409,
            "scan_not_ready",
            "This scan has not finished yet.",
            "Wait for the analysis to complete, then try again.",
        )


def _collection(session: Session, scan: Scan) -> dict:
    return {
        "type": "FeatureCollection",
        "scan_id": scan.id,
        "model_version": scan.version_used,
        "features": [hotspot_feature(h) for h in scan_hotspots(session, scan.id)],
    }


@router.get(
    "/scans/{scan_id}",
    response_model=ScanOut,
    summary="Status, stage, progress, timings and KPI summary",
    description="Polled every 800 ms while the processing screen is open.",
)
def get_scan(scan_id: str, session: Session = Depends(get_session)) -> dict:
    scan, field = load_scan(session, scan_id)
    return scan_payload(scan, field)


@router.post("/scans/{scan_id}/cancel", response_model=ScanOut, summary="Cancel a running scan")
def cancel_scan(scan_id: str, session: Session = Depends(get_session)) -> dict:
    scan, field = load_scan(session, scan_id)
    if scan.status not in (SCAN_DONE, SCAN_FAILED, SCAN_CANCELLED):
        scan.cancel_requested = True
        session.add(scan)
        session.commit()
    return scan_payload(scan, field)


@router.get(
    "/scans/{scan_id}/report",
    summary="Download the farmer-facing PDF report for this scan",
    description="Builds it the first time it's asked for, then serves the cached file. Works for "
    "every field, including Studio-only demo ones with no farmer attached.",
)
def get_scan_report(scan_id: str, session: Session = Depends(get_session)) -> FileResponse:
    scan, field = load_scan(session, scan_id)
    _require_done(scan)
    path = ingest.ensure_report_any(session, scan)
    if path is None:
        raise ApiError(409, "report_unavailable", "The report could not be generated.", "Try again.")
    return FileResponse(path, media_type="application/pdf", filename=f"{field.name}-report.pdf")


@router.get(
    "/scans/{scan_id}/hotspots",
    response_model=HotspotCollection,
    summary="Hotspot FeatureCollection, sorted by rank",
)
def get_hotspots(scan_id: str, session: Session = Depends(get_session)) -> dict:
    scan, _ = load_scan(session, scan_id)
    return _collection(session, scan)


@router.post(
    "/scans/{scan_id}/hotspots",
    response_model=HotspotFeature,
    status_code=201,
    summary="Add a hotspot manually",
)
def create_manual_hotspot(
    scan_id: str, body: ManualHotspotCreate, session: Session = Depends(get_session)
) -> dict:
    scan, field = load_scan(session, scan_id)
    hotspot = add_manual_hotspot(session, scan, field, body.lat, body.lon, body.radius_m, body.note)
    return hotspot_feature(hotspot)


@router.post(
    "/scans/{scan_id}/threshold",
    response_model=ScanWithHotspots,
    summary="Move the sensitivity slider",
    description="Re-clusters from cached tile features, without re-running analysis. Debounce it. "
    "Hotspot ids change, except for hotspots someone has already worked on.",
)
def set_threshold(
    scan_id: str, body: ThresholdUpdate, session: Session = Depends(get_session)
) -> dict:
    scan, field = load_scan(session, scan_id)
    apply_threshold(session, scan, field, body.threshold)
    route = latest_route(session, scan.id)
    return {
        "scan": scan_payload(scan, field),
        "hotspots": _collection(session, scan),
        "route": route_payload(session, route) if route else None,
    }


@router.get(
    "/scans/{scan_id}/layers/{layer}",
    response_model=LayerOut,
    summary="Overlay image URL plus bounds",
)
def get_layer(
    scan_id: str,
    layer: Literal["rgb", "vari", "heat"],
    session: Session = Depends(get_session),
) -> dict:
    scan, field = load_scan(session, scan_id)
    _require_done(scan)
    info = (scan.layers or {}).get(layer)
    if info is None:
        raise not_found("Layer", layer)
    return {
        "layer": layer,
        "url": public_url(info["path"]),
        "bytes": info["bytes"],
        "format": info["format"],
        "bounds": bounds_payload(field),
    }


@router.post("/scans/{scan_id}/route", response_model=RouteOut, summary="Plan a route")
def plan_route(
    scan_id: str, body: RouteCreate | None = None, session: Session = Depends(get_session)
) -> dict:
    scan, field = load_scan(session, scan_id)
    _require_done(scan)
    body = body or RouteCreate()
    route = create_route(
        session,
        scan,
        field,
        mode=body.mode,
        start=(body.start.lat, body.start.lon) if body.start else None,
        include_abiotic=body.include_abiotic,
        walking_speed_mps=body.walking_speed_mps,
        minutes_per_stop=body.minutes_per_stop,
    )
    refresh_kpis(session, scan, field)
    session.commit()
    return route_payload(session, route)


@router.get(
    "/scans/{scan_id}/route",
    response_model=RouteOut,
    summary="Latest route",
    description="What the scout app reads after scanning the QR code.",
)
def get_route(scan_id: str, session: Session = Depends(get_session)) -> dict:
    scan, _ = load_scan(session, scan_id)
    _require_done(scan)
    route = latest_route(session, scan.id)
    if route is None:
        raise not_found("Route for scan", scan_id)
    return route_payload(session, route)


@router.get(
    "/scans/{scan_id}/export/{kind}",
    summary="Export GeoJSON, CSV or the labelled dataset",
    response_class=Response,
)
def export_scan(
    scan_id: str,
    kind: Literal["geojson", "csv", "dataset.zip"],
    session: Session = Depends(get_session),
) -> Response:
    scan, _ = load_scan(session, scan_id)
    _require_done(scan)
    if kind == "geojson":
        content, media, name = (
            geojson_export(session, scan), "application/geo+json", f"{scan.id}.geojson"
        )
    elif kind == "csv":
        content, media, name = csv_export(session, scan), "text/csv", f"{scan.id}.csv"
    else:
        content, media, name = (
            dataset_zip(session, scan), "application/zip", f"{scan.id}_dataset.zip"
        )
    return Response(
        content=content,
        media_type=media,
        headers={"Content-Disposition": f'attachment; filename="{name}"'},
    )
