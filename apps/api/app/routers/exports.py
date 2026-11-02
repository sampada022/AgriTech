import io
import csv
import zipfile
import json
from fastapi import APIRouter, Response, HTTPException
from fastapi.responses import StreamingResponse
from app.mock_data import MOCK_HOTSPOTS, MOCK_SCANS, MOCK_OBSERVATIONS
from app.model.versions import TRAINING_SAMPLES
from app.errors import AeroScoutError

router = APIRouter(prefix="/scans", tags=["Exports (P1)"])

@router.get("/{scan_id}/export/geojson")
def export_geojson(scan_id: str):
    spots = MOCK_HOTSPOTS.get(scan_id, [])
    fc = {
        "type": "FeatureCollection",
        "scan_id": scan_id,
        "features": spots
    }
    content = json.dumps(fc, indent=2)
    return Response(
        content=content,
        media_type="application/geo+json",
        headers={"Content-Disposition": f"attachment; filename=aeroscout_{scan_id}_hotspots.geojson"}
    )

@router.get("/{scan_id}/export/csv")
def export_csv(scan_id: str):
    spots = MOCK_HOTSPOTS.get(scan_id, [])
    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow([
        "id", "rank", "tier", "area_m2", "biotic_score", "class",
        "confidence", "status", "contrast_ratio", "entropy_ratio",
        "edge_ratio", "irregularity", "sharpness", "anisotropy"
    ])

    for s in spots:
        p = s["properties"]
        c = p["cues"]
        writer.writerow([
            s["id"], p["rank"], p["tier"], p["area_m2"], p["biotic_score"],
            p["class"], p["confidence"], p["status"], c["contrast_ratio"],
            c["entropy_ratio"], c["edge_ratio"], c["irregularity"],
            c["sharpness"], c["anisotropy"]
        ])

    return Response(
        content=output.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=aeroscout_{scan_id}_hotspots.csv"}
    )

@router.get("/{scan_id}/export/dataset.zip")
def export_dataset_zip(scan_id: str):
    """
    Exports clean labelled dataset ZIP for downstream species ML training:
    - labels.csv (ground findings)
    - features.csv (extracted CV cue vectors)
    - metadata.json (GSD, scan parameters, bounds)
    """
    zip_buffer = io.BytesIO()

    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        # 1. features.csv
        spots = MOCK_HOTSPOTS.get(scan_id, [])
        feat_io = io.StringIO()
        f_writer = csv.writer(feat_io)
        f_writer.writerow(["hotspot_id", "contrast_ratio", "entropy_ratio", "edge_ratio", "irregularity", "sharpness", "log_area", "anisotropy", "area_m2"])
        for s in spots:
            p = s["properties"]
            c = p["cues"]
            f_writer.writerow([s["id"], c["contrast_ratio"], c["entropy_ratio"], c["edge_ratio"], c["irregularity"], c["sharpness"], c["log_area"], c["anisotropy"], p["area_m2"]])
        zf.writestr("features.csv", feat_io.getvalue())

        # 2. labels.csv
        label_io = io.StringIO()
        l_writer = csv.writer(label_io)
        l_writer.writerow(["hotspot_id", "label_biotic_binary", "label_name", "confirmed_at"])
        for smp in TRAINING_SAMPLES:
            l_writer.writerow([smp.get("hotspot_id", "h_01"), smp.get("label", 1), "pest", "2026-11-02T10:16:30Z"])
        zf.writestr("labels.csv", label_io.getvalue())

        # 3. metadata.json
        meta = {
            "scan_id": scan_id,
            "crop": "Sugarcane",
            "gsd_cm": 3.0,
            "provenance": "AeroScout Dual-Scale Triage",
            "benchmark_dataset_ready": True
        }
        zf.writestr("metadata.json", json.dumps(meta, indent=2))

    zip_buffer.seek(0)
    return StreamingResponse(
        zip_buffer,
        media_type="application/zip",
        headers={"Content-Disposition": f"attachment; filename=aeroscout_{scan_id}_dataset.zip"}
    )

