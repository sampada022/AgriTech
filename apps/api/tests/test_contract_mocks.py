import pytest
from app.routers.fields import list_fields
from app.routers.scans import get_scan, get_scan_hotspots
from app.routers.route import plan_route
from app.routers.observations import create_observation, confirm_observation
from app.routers.model import get_model
from app.schemas import RouteRequest, ConfirmLabelRequest

def test_fields_contract():
    fields = list_fields()
    assert len(fields) > 0
    f = fields[0]
    assert "bounds" in f
    assert "sw" in f["bounds"]

def test_scan_and_hotspots_contract():
    scan = get_scan("s_01")
    assert scan["kpi_summary"]["hotspot_count"] > 0

    fc = get_scan_hotspots("s_01")
    assert fc["type"] == "FeatureCollection"
    assert len(fc["features"]) > 0
    props = fc["features"][0]["properties"]
    assert "biotic_score" in props
    assert "contributions" in props
    assert "tier" in props

def test_route_contract():
    route = plan_route("s_01", RouteRequest(mode="worst_first"))
    assert route.saved_pct > 0
    assert len(route.waypoints) > 1

def test_observation_and_confirm_loop():
    # Submit observation directly to router logic
    obs = create_observation(
        hotspot_id="h_01",
        lat=12.5232,
        lon=76.8962,
        language="en",
        photo=None
    )
    assert obs["diagnosis"]["plant_visible"] is True

    # Confirm label
    confirmed = confirm_observation(obs["id"], ConfirmLabelRequest(label="pest"))
    assert confirmed["label"] == "pest"

    # Check model update
    status = get_model()
    assert status["active_version"] in ["v1", "v2"]
