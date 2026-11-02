from unittest.mock import patch
from app.mock_data import MOCK_HOTSPOTS, MOCK_SCANS
from app.routers.exports import export_geojson, export_csv, export_dataset_zip
from app.routers.flightplan import get_flightplan_kml, get_flightplan_qgroundcontrol, FlightPlanRequest
from app.routers.hotspots import add_manual_hotspot
from app.schemas import ManualHotspotCreate

def test_exports_geojson_and_csv():
    # Ensure scan exists
    scan_id = "s_01"
    res_geo = export_geojson(scan_id)
    assert res_geo.status_code == 200
    assert "FeatureCollection" in res_geo.body.decode()

    res_csv = export_csv(scan_id)
    assert res_csv.status_code == 200
    assert "contrast_ratio" in res_csv.body.decode()

def test_exports_dataset_zip():
    scan_id = "s_01"
    res_zip = export_dataset_zip(scan_id)
    assert res_zip.status_code == 200
    assert res_zip.media_type == "application/zip"

def test_flightplan_generators():
    req = FlightPlanRequest(altitude_m=35.0, overlap_side_pct=70.0)
    kml_res = get_flightplan_kml(req)
    assert kml_res.status_code == 200
    assert "<kml" in kml_res.body.decode()
    assert "Survey Track" in kml_res.body.decode()

    qgc_res = get_flightplan_qgroundcontrol(req)
    assert qgc_res.status_code == 200
    assert "QGC WPL 110" in qgc_res.body.decode()

def test_manual_hotspot_addition():
    scan_id = "s_01"
    initial_count = len(MOCK_HOTSPOTS.get(scan_id, []))
    manual = ManualHotspotCreate(lat=11.0175, lon=76.8210, note="Suspicious yellowing")
    spot = add_manual_hotspot(scan_id, manual)
    assert spot["id"].startswith("h_manual_")
    assert spot["properties"]["class"] == "scout_added"
    assert len(MOCK_HOTSPOTS[scan_id]) == initial_count + 1

