# AeroScout API & Data Contract (Canonical)

All paths live under `/api`.
Realtime communication is done via polling every 800 ms.
All errors follow a unified error envelope.

---

## 1. Unified Error Contract

```json
{
  "error": {
    "code": "STRING_IDENTIFIER",
    "message": "Human readable description of the failure.",
    "hint": "Actionable next step for the user or UI."
  }
}
```

---

## 2. Core Entities & Schemas

### Bounds & Coordinates
Coordinates use WGS84 standard: `[longitude, latitude]` in GeoJSON, and `{"sw": [lat, lon], "ne": [lat, lon]}` in bounding box payloads.

### Field
```json
{
  "id": "f_mandya_01",
  "name": "Mandya Plot 4",
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
```

### Scan & Processing State
```json
{
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
    "hotspot_count": 8,
    "area_flagged_pct": 5.4,
    "spray_area_pct": 8.2,
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
```

### Hotspot GeoJSON Feature (`GET /api/scans/{id}/hotspots`)
Returns RFC 7946 `FeatureCollection`:
```json
{
  "type": "FeatureCollection",
  "features": [
    {
      "type": "Feature",
      "id": "h_01",
      "geometry": {
        "type": "Polygon",
        "coordinates": [
          [
            [76.8961, 12.5231],
            [76.8964, 12.5231],
            [76.8964, 12.5234],
            [76.8961, 12.5234],
            [76.8961, 12.5231]
          ]
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
          "contrast_ratio": 2.3,
          "entropy_ratio": 1.7,
          "edge_ratio": 1.9,
          "irregularity": 0.38,
          "sharpness": 0.75,
          "log_area": 2.9,
          "anisotropy": 0.08
        },
        "contributions": {
          "contrast_ratio": 1.15,
          "entropy_ratio": 0.62,
          "edge_ratio": 0.54,
          "irregularity": 0.35,
          "sharpness": 0.40,
          "log_area": -0.25,
          "anisotropy": -0.06
        },
        "status": "detected",
        "manual": false,
        "crop_url": "/demo/scenarios/mixed/crops/h_01.jpg"
      }
    }
  ]
}
```

### Route Plan (`POST /api/scans/{id}/route`)
```json
{
  "id": "r_01",
  "scan_id": "s_01",
  "mode": "worst_first",
  "ordered_hotspot_ids": ["h_01", "h_02", "h_04", "h_06"],
  "distance_m": 420.5,
  "eta_min": 17.8,
  "saved_pct": 68.5,
  "baseline_m": 1335.0,
  "spray_area_pct": 8.2,
  "waypoints": [
    {"lat": 12.5205, "lon": 76.8955, "label": "Start", "hotspot_id": null},
    {"lat": 12.5232, "lon": 76.8962, "label": "Stop 1", "hotspot_id": "h_01", "tier": "red", "rank": 1},
    {"lat": 12.5245, "lon": 76.8970, "label": "Stop 2", "hotspot_id": "h_02", "tier": "red", "rank": 2}
  ]
}
```

### Leaf Diagnosis Observation (`POST /api/hotspots/{id}/observations`)
```json
{
  "id": "obs_101",
  "hotspot_id": "h_01",
  "photo_url": "/demo/leaf_photos/leaf_01.jpg",
  "lat": 12.5232,
  "lon": 76.8962,
  "taken_at": "2026-11-02T10:15:00Z",
  "language": "en",
  "diagnosis": {
    "plant_visible": true,
    "image_quality": "good",
    "observed_symptoms": ["chewed leaf margins", "frass on upper surface"],
    "candidates": [
      {"name": "Spodoptera frugiperda (Fall Armyworm)", "type": "pest", "probability": 0.74},
      {"name": "Stem Borer Damage", "type": "pest", "probability": 0.16},
      {"name": "Nitrogen Deficiency", "type": "nutrient", "probability": 0.10}
    ],
    "confirm_by": ["Check leaf underside for caterpillar larvae or egg clusters"],
    "actions_ipm": [
      "Handpick and destroy egg masses and early-stage larvae",
      "Apply neem seed kernel extract (NSKE 5%) if infestation persists"
    ],
    "needs_expert": false,
    "disclaimer": "Advisory only. Follow local pesticide labels and consult extension officer."
  },
  "label": null,
  "note": null
}
```

### Observation Confirmation (`POST /api/observations/{id}/confirm`)
Body: `{"label": "pest"}`
Triggers logistic model recalibration and bumps model version `v1 -> v2`.

### Model History (`GET /api/model`)
```json
{
  "active_version": "v2",
  "n_labels": 1,
  "training_agreement_pct": 100.0,
  "weights": {
    "contrast_ratio": 1.25,
    "entropy_ratio": 0.85,
    "edge_ratio": 0.65,
    "irregularity": 0.52,
    "sharpness": 0.51,
    "log_area": -0.58,
    "anisotropy": -0.82
  },
  "bias": -0.15,
  "history": [
    {
      "version": "v1",
      "n_labels": 0,
      "training_agreement_pct": null,
      "created_at": "2026-11-02T09:00:00Z"
    },
    {
      "version": "v2",
      "n_labels": 1,
      "training_agreement_pct": 100.0,
      "created_at": "2026-11-02T10:16:30Z"
    }
  ]
}
```

