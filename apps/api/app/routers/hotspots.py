from fastapi import APIRouter
from app.schemas import HotspotFeature, HotspotPatch, ManualHotspotCreate
from app.mock_data import MOCK_HOTSPOTS
from app.errors import AeroScoutError

router = APIRouter(tags=["Hotspots"])

@router.post("/scans/{scan_id}/hotspots", response_model=HotspotFeature)
def add_manual_hotspot(scan_id: str, manual: ManualHotspotCreate):
    """
    P1 Feature: Allows ground scout to tap on the map to add an unflagged
    stress spot found while walking the field.
    """
    spots = MOCK_HOTSPOTS.setdefault(scan_id, [])
    next_idx = len(spots) + 1
    new_id = f"h_manual_{next_idx:02d}"

    # Standard 1.5m radius circular polygon footprint around lat/lon
    dlat = 0.000015
    dlon = 0.000015
    poly_coords = [[
        [manual.lon - dlon, manual.lat - dlat],
        [manual.lon + dlon, manual.lat - dlat],
        [manual.lon + dlon, manual.lat + dlat],
        [manual.lon - dlon, manual.lat + dlat],
        [manual.lon - dlon, manual.lat - dlat],
    ]]

    feature = {
        "type": "Feature",
        "id": new_id,
        "geometry": {
            "type": "Polygon",
            "coordinates": poly_coords
        },
        "properties": {
            "rank": next_idx,
            "tier": 2,
            "area_m2": 6.8,
            "biotic_score": 0.50,
            "class": "scout_added",
            "confidence": 0.85,
            "status": "unvisited",
            "cues": {
                "contrast_ratio": 1.2,
                "entropy_ratio": 1.1,
                "edge_ratio": 1.15,
                "irregularity": 1.3,
                "sharpness": 1.1,
                "log_area": 1.9,
                "anisotropy": 1.05
            },
            "contributions": {
                "contrast_ratio": 0.1,
                "entropy_ratio": 0.05,
                "edge_ratio": 0.08,
                "irregularity": 0.12,
                "sharpness": 0.06,
                "log_area": 0.05,
                "anisotropy": 0.04
            },
            "suggested_action": "Sample manual ground spot for disease verification."
        }
    }
    spots.append(feature)
    return feature

@router.patch("/hotspots/{hotspot_id}", response_model=HotspotFeature)
def update_hotspot(hotspot_id: str, patch: HotspotPatch):
    # Find hotspot across scans
    for scan_id, spots in MOCK_HOTSPOTS.items():
        for spot in spots:
            if spot["id"] == hotspot_id:
                if patch.status:
                    spot["properties"]["status"] = patch.status
                return spot

    raise AeroScoutError(
        code="HOTSPOT_NOT_FOUND",
        message=f"Hotspot with ID '{hotspot_id}' does not exist.",
        hint="Refresh the scan hotspot list.",
        status_code=404
    )

