from fastapi import APIRouter, BackgroundTasks, HTTPException
from typing import Dict, Any
import os
import cv2

from app.schemas import ScanRead, ScanCreate, HotspotFeatureCollection
from app.mock_data import MOCK_SCANS, MOCK_HOTSPOTS, MOCK_MODEL_STATE
from app.engine.pipeline import run_aerial_scan_pipeline
from app.errors import AeroScoutError

router = APIRouter(tags=["Scans"])

def process_scan_task(scan_id: str, image_path: str):
    try:
        scan = MOCK_SCANS[scan_id]
        scan["status"] = "processing"
        scan["stage"] = "analyzing"
        scan["progress"] = 20

        result = run_aerial_scan_pipeline(
            image_path=image_path,
            weights=MOCK_MODEL_STATE["weights"],
            bias=MOCK_MODEL_STATE["bias"]
        )

        # Store generated GeoJSON features
        MOCK_HOTSPOTS[scan_id] = result["features"]

        # Save generated heatmap
        heat_path = f"demo/scenarios/mixed/heat_{scan_id}.png"
        cv2.imwrite(heat_path, result["heatmap_rgba"])

        scan["status"] = "completed"
        scan["stage"] = "route"
        scan["progress"] = 100
        scan["timings"] = result["timings"]
        scan["quality_score"] = result["quality_score"]
        scan["canopy_pct"] = result["canopy_pct"]
        scan["kpi_summary"] = result["kpi_summary"]
        scan["layers"]["heat"] = f"/{heat_path}"

    except Exception as e:
        if scan_id in MOCK_SCANS:
            MOCK_SCANS[scan_id]["status"] = "failed"
            MOCK_SCANS[scan_id]["stage"] = str(e)

@router.post("/fields/{field_id}/scans", response_model=ScanRead, status_code=202)
def start_scan(field_id: str, payload: ScanCreate = ScanCreate(), bg: BackgroundTasks = BackgroundTasks()):
    scan_id = "s_01"
    image_path = "demo/scenarios/mixed/field.jpg"

    if not os.path.exists(image_path):
        from app.sim.generate import generate_synthetic_field
        img, mask, bounds, patches = generate_synthetic_field()
        os.makedirs("demo/scenarios/mixed", exist_ok=True)
        cv2.imwrite(image_path, img)

    # Trigger scan pipeline immediately or synchronously for demo reliability
    process_scan_task(scan_id, image_path)
    return MOCK_SCANS[scan_id]

@router.get("/scans/{scan_id}", response_model=ScanRead)
def get_scan(scan_id: str):
    scan = MOCK_SCANS.get(scan_id)
    if not scan:
        raise AeroScoutError(
            code="SCAN_NOT_FOUND",
            message=f"Scan '{scan_id}' not found.",
            hint="Trigger a scan first.",
            status_code=404
        )
    return scan

@router.get("/scans/{scan_id}/hotspots", response_model=HotspotFeatureCollection)
def get_scan_hotspots(scan_id: str):
    features = MOCK_HOTSPOTS.get(scan_id, [])
    return {"type": "FeatureCollection", "features": features}
