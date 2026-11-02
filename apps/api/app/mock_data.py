from typing import Dict, Any

# Initial Model Priors w0
INITIAL_WEIGHTS = {
    "contrast_ratio": 1.0,
    "entropy_ratio": 0.7,
    "edge_ratio": 0.6,
    "irregularity": 0.5,
    "sharpness": 0.5,
    "log_area": -0.6,
    "anisotropy": -0.8
}

INITIAL_BIAS = -0.20

MOCK_FIELDS = [
    {
        "id": "f_mandya_01",
        "name": "Mandya Plot 4 (Sugarcane)",
        "crop": "Sugarcane",
        "data_source": "synthetic",
        "bounds": {
            "sw": [12.5200, 76.8950],
            "ne": [12.5280, 76.9050]
        },
        "image_url": "/demo/scenarios/mixed/field.jpg",
        "gsd_cm": 3.0,
        "created_at": "2026-11-02T10:00:00Z"
    }
]

MOCK_SCANS = {
    "s_01": {
        "id": "s_01",
        "field_id": "f_mandya_01",
        "status": "completed",
        "stage": "route",
        "progress": 100,
        "timings": {
            "quality": 0.45,
            "normalise": 0.32,
            "canopy_mask": 1.10,
            "indices": 0.85,
            "tiles": 3.40,
            "anomaly": 0.90,
            "cluster": 0.65,
            "scoring": 0.40,
            "route": 0.15
        },
        "quality_score": 0.94,
        "canopy_pct": 82.5,
        "kpi_summary": {
            "hotspot_count": 5,
            "area_flagged_pct": 4.8,
            "spray_area_pct": 7.6,
            "walk_saved_pct": 68.5,
            "route_distance_m": 420.0,
            "baseline_distance_m": 1330.0
        },
        "layers": {
            "rgb": "/api/scans/s_01/layers/rgb",
            "vari": "/api/scans/s_01/layers/vari",
            "heat": "/api/scans/s_01/layers/heat"
        },
        "model_version": "v1"
    }
}

MOCK_HOTSPOTS = {
    "s_01": [
        {
            "type": "Feature",
            "id": "h_01",
            "geometry": {
                "type": "Polygon",
                "coordinates": [
                    [[76.8970, 12.5230], [76.8974, 12.5230], [76.8974, 12.5234], [76.8970, 12.5234], [76.8970, 12.5230]]
                ]
            },
            "properties": {
                "scan_id": "s_01",
                "rank": 1,
                "area_m2": 18.2,
                "tier": "red",
                "biotic_score": 0.82,
                "class": "likely_biotic",
                "confidence": "high",
                "cues": {
                    "contrast_ratio": 2.3, "entropy_ratio": 1.7, "edge_ratio": 1.9,
                    "irregularity": 0.38, "sharpness": 0.75, "log_area": 2.9, "anisotropy": 0.08
                },
                "contributions": {
                    "contrast_ratio": 1.15, "entropy_ratio": 0.62, "edge_ratio": 0.54,
                    "irregularity": 0.35, "sharpness": 0.40, "log_area": -0.25, "anisotropy": -0.06
                },
                "status": "detected",
                "manual": False,
                "crop_url": "/demo/scenarios/mixed/crops/h_01.jpg"
            }
        },
        {
            "type": "Feature",
            "id": "h_02",
            "geometry": {
                "type": "Polygon",
                "coordinates": [
                    [[76.8985, 12.5242], [76.8988, 12.5242], [76.8988, 12.5245], [76.8985, 12.5245], [76.8985, 12.5242]]
                ]
            },
            "properties": {
                "scan_id": "s_01",
                "rank": 2,
                "area_m2": 12.5,
                "tier": "red",
                "biotic_score": 0.76,
                "class": "likely_biotic",
                "confidence": "high",
                "cues": {
                    "contrast_ratio": 2.0, "entropy_ratio": 1.5, "edge_ratio": 1.7,
                    "irregularity": 0.30, "sharpness": 0.68, "log_area": 2.5, "anisotropy": 0.10
                },
                "contributions": {
                    "contrast_ratio": 0.95, "entropy_ratio": 0.50, "edge_ratio": 0.45,
                    "irregularity": 0.28, "sharpness": 0.32, "log_area": -0.20, "anisotropy": -0.08
                },
                "status": "detected",
                "manual": False,
                "crop_url": "/demo/scenarios/mixed/crops/h_02.jpg"
            }
        },
        {
            "type": "Feature",
            "id": "h_03",
            "geometry": {
                "type": "Polygon",
                "coordinates": [
                    [[76.9010, 12.5255], [76.9016, 12.5255], [76.9016, 12.5261], [76.9010, 12.5261], [76.9010, 12.5255]]
                ]
            },
            "properties": {
                "scan_id": "s_01",
                "rank": 3,
                "area_m2": 45.0,
                "tier": "grey",
                "biotic_score": 0.24,
                "class": "likely_abiotic",
                "confidence": "high",
                "cues": {
                    "contrast_ratio": 0.85, "entropy_ratio": 0.92, "edge_ratio": 0.70,
                    "irregularity": 0.12, "sharpness": 0.25, "log_area": 3.8, "anisotropy": 0.12
                },
                "contributions": {
                    "contrast_ratio": -0.40, "entropy_ratio": -0.20, "edge_ratio": -0.35,
                    "irregularity": -0.15, "sharpness": -0.30, "log_area": -0.65, "anisotropy": -0.10
                },
                "status": "detected",
                "manual": False,
                "crop_url": "/demo/scenarios/mixed/crops/h_03.jpg"
            }
        },
        {
            "type": "Feature",
            "id": "h_04",
            "geometry": {
                "type": "Polygon",
                "coordinates": [
                    [[76.8992, 12.5220], [76.8996, 12.5220], [76.8996, 12.5223], [76.8992, 12.5223], [76.8992, 12.5220]]
                ]
            },
            "properties": {
                "scan_id": "s_01",
                "rank": 4,
                "area_m2": 9.4,
                "tier": "amber",
                "biotic_score": 0.58,
                "class": "uncertain",
                "confidence": "medium",
                "cues": {
                    "contrast_ratio": 1.45, "entropy_ratio": 1.25, "edge_ratio": 1.30,
                    "irregularity": 0.22, "sharpness": 0.45, "log_area": 2.2, "anisotropy": 0.25
                },
                "contributions": {
                    "contrast_ratio": 0.45, "entropy_ratio": 0.30, "edge_ratio": 0.25,
                    "irregularity": 0.18, "sharpness": 0.15, "log_area": -0.15, "anisotropy": -0.22
                },
                "status": "detected",
                "manual": False,
                "crop_url": "/demo/scenarios/mixed/crops/h_04.jpg"
            }
        },
        {
            "type": "Feature",
            "id": "h_05",
            "geometry": {
                "type": "Polygon",
                "coordinates": [
                    [[76.9025, 12.5235], [76.9032, 12.5235], [76.9032, 12.5240], [76.9025, 12.5240], [76.9025, 12.5235]]
                ]
            },
            "properties": {
                "scan_id": "s_01",
                "rank": 5,
                "area_m2": 32.0,
                "tier": "grey",
                "biotic_score": 0.31,
                "class": "likely_abiotic",
                "confidence": "medium",
                "cues": {
                    "contrast_ratio": 0.95, "entropy_ratio": 1.05, "edge_ratio": 0.85,
                    "irregularity": 0.15, "sharpness": 0.30, "log_area": 3.4, "anisotropy": 0.65
                },
                "contributions": {
                    "contrast_ratio": -0.15, "entropy_ratio": 0.05, "edge_ratio": -0.18,
                    "irregularity": -0.10, "sharpness": -0.22, "log_area": -0.55, "anisotropy": -0.58
                },
                "status": "detected",
                "manual": False,
                "crop_url": "/demo/scenarios/mixed/crops/h_05.jpg"
            }
        }
    ]
}

MOCK_OBSERVATIONS: Dict[str, Any] = {}

MOCK_MODEL_STATE = {
    "active_version": "v1",
    "n_labels": 0,
    "training_agreement_pct": None,
    "weights": INITIAL_WEIGHTS.copy(),
    "bias": INITIAL_BIAS,
    "history": [
        {
            "version": "v1",
            "n_labels": 0,
            "training_agreement_pct": None,
            "created_at": "2026-11-02T10:00:00Z"
        }
    ]
}

