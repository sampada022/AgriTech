import os
import cv2
import numpy as np
from app.engine.scoring import compute_hotspot_features, score_hotspot
from app.route.planner import plan_field_route
from app.diagnosis.client import diagnose_leaf_image
from app.engine.pipeline import run_aerial_scan_pipeline

def test_hotspot_scoring_and_explainability():
    mock_cluster = {
        "area_m2": 15.0,
        "solidity": 0.65,
        "mean_anomaly": 2.5,
        "member_tile_indices": [
            {"features": {"contrast": 2.2, "entropy": 1.6, "edge_density": 0.25, "anisotropy": 0.08}}
        ]
    }

    cues = compute_hotspot_features(
        cluster=mock_cluster,
        field_tiles=[],
        all_canopy_contrast_mean=1.0,
        all_canopy_entropy_mean=1.0,
        all_canopy_edge_mean=0.1
    )

    assert cues["contrast_ratio"] > 1.5
    assert cues["irregularity"] > 0.2

    weights = {"contrast_ratio": 1.0, "entropy_ratio": 0.7, "edge_ratio": 0.6, "anisotropy": -0.8}
    score, b_class, tier, conf, contribs = score_hotspot(cues, weights, bias=-0.2)

    assert score > 0.60
    assert b_class in ["likely_biotic", "uncertain"]
    assert "contrast_ratio" in contribs
    assert contribs["contrast_ratio"] > 0

def test_route_planner_2opt():
    start = {"lat": 12.5205, "lon": 76.8955, "label": "Start", "hotspot_id": None}
    hotspots = [
        {"id": "h_01", "rank": 1, "tier": "red", "area_m2": 15.0, "centroid": [76.8980, 12.5230]},
        {"id": "h_02", "rank": 2, "tier": "red", "area_m2": 12.0, "centroid": [76.8990, 12.5240]},
        {"id": "h_03", "rank": 3, "tier": "amber", "area_m2": 8.0, "centroid": [76.8965, 12.5220]}
    ]

    route = plan_field_route(start, hotspots, mode="worst_first", field_area_m2=11000.0)
    assert len(route["ordered_hotspot_ids"]) == 3
    assert route["distance_m"] > 50.0
    assert route["saved_pct"] > 50.0
    assert len(route["waypoints"]) == 4

def test_diagnosis_hash_cache():
    dummy_photo = b"unique_leaf_image_bytes_42"
    diag1 = diagnose_leaf_image(dummy_photo)
    assert diag1.plant_visible is True
    assert len(diag1.candidates) > 0
    assert len(diag1.actions_ipm) > 0

    # Second call hits hash cache
    diag2 = diagnose_leaf_image(dummy_photo)
    assert diag2.candidates[0].name == diag1.candidates[0].name

def test_full_aerial_pipeline():
    image_path = "demo/scenarios/mixed/field.jpg"
    assert os.path.exists(image_path), "Field image must exist from Phase 2"

    weights = {"contrast_ratio": 1.0, "entropy_ratio": 0.7, "edge_ratio": 0.6, "irregularity": 0.5, "sharpness": 0.5, "log_area": -0.6, "anisotropy": -0.8}
    bias = -0.2

    result = run_aerial_scan_pipeline(image_path, weights, bias)
    assert "features" in result
    assert len(result["features"]) > 0
    assert "timings" in result
    assert result["heatmap_rgba"].shape[2] == 4

