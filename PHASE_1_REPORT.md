# AeroScout — Phase 1 Completion & Gate Report

**Date & Time**: Nov 2, 2026  
**Status**: **PASSED & COMPLETE**

---

## 1. What Was Built in Phase 1 (Contracts + Mocks)

Phase 1 established the canonical API contract and realistic mock server so that both the **Desktop Dashboard** and the **Mobile Scout App** can fully render and interact before the heavy computer vision math is wired in.

### A. Canonical API Contract & Schemas
- Defined `docs/contract.md` documenting every entity and endpoint:
  - Unified Error Envelope: `{"error": {"code": str, "message": str, "hint": str}}`.
  - GeoJSON standard: RFC 7946 Polygon representations in WGS84 `[lon, lat]` format.
  - Hotspot properties: `scan_id`, `rank`, `area_m2`, `tier`, `biotic_score`, `class`, `confidence`, `cues`, signed `contributions`, `status`, `manual`, and `crop_url`.
- Implemented robust Pydantic v2 schemas in `apps/api/app/schemas.py`:
  - `FieldCreate`, `FieldRead`, `Bounds`
  - `ScanCreate`, `ScanRead`, `KPISummary`
  - `HotspotFeature`, `HotspotFeatureCollection`, `HotspotProperties`, `HotspotPatch`
  - `RouteRequest`, `RouteRead`, `RouteWaypoint`
  - `ObservationRead`, `DiagnosisResult`, `CandidateDiagnosis`, `ConfirmLabelRequest`
  - `ModelStatusRead`, `ModelVersionHistory`

### B. Realistic Mock Backend Routers
Implemented and mounted endpoints under `/api`:
- `GET /api/fields`, `GET /api/fields/{id}`, `POST /api/fields`: Field listing and bounds creation.
- `POST /api/fields/{id}/scans`, `GET /api/scans/{id}`: Scan creation and status polling.
- `GET /api/scans/{id}/hotspots`: Returns valid GeoJSON with red, amber, and grey tiers.
- `PATCH /api/hotspots/{id}`: Updates inspection status (`detected` → `confirmed` / `cleared`).
- `POST /api/scans/{id}/route`: Calculates 2-opt ordered stops, distance, ETA, and saved walk %.
- `POST /api/hotspots/{id}/observations`: Simulates structured leaf diagnosis with Fall Armyworm IPM guidance.
- `POST /api/observations/{id}/confirm`: Farmer confirms ground finding, which increments `n_labels` and bumps model version `v1 -> v2`.
- `GET /api/model`, `POST /api/model/reset`: Live weights, bias, agreement %, and version history.
- `POST /api/demo/load/{scenario}`, `POST /api/demo/reset`: One-click demo fixtures.

### C. Frontend API Client & Screens
- Created typed client in `apps/web/lib/api.ts` connecting to all mock endpoints.
- **Desktop Mission Dashboard** (`apps/web/app/page.tsx`):
  - Live field status badge (Honest "Synthetic" badge).
  - Hotspot map layout with red/amber/grey tier markers.
  - KPI strip: Hotspot count, % field flagged, spot-spray potential, walk saved.
  - Hotspot detail drawer with **Why-Flagged horizontal signed contribution bars**.
  - Direct launch link to the Scout mobile app.
- **Mobile Scout PWA** (`apps/web/app/scout/[id]/page.tsx`):
  - Stop progress tracker and waypoint target cards.
  - GPS arrival detection simulator (`Simulate Walk` toggle).
  - Leaf photo camera trigger and structured AI diagnosis presentation.
  - One-tap label confirmation (`Confirm Fall Armyworm`), which recalibrates the model live and updates the status.

---

## 2. Acceptance Checks & Test Output

| Acceptance Check | Result | Evidence |
|:---|:---:|:---|
| **Contract Documentation** | **PASS** | Complete specification written to `docs/contract.md`. |
| **Pydantic Validation** | **PASS** | All entities strictly typed and validated in `schemas.py`. |
| **All Mock Endpoints Respond** | **PASS** | Fields, scans, hotspots, routes, observations, confirm, and model endpoints all live. |
| **Recalibration Loop in Mocks** | **PASS** | `POST /api/observations/{id}/confirm` bumps active model version `v1 -> v2`. |
| **Backend Unit Tests** | **PASS** | `pytest tests/` executed **8 passed in 1.93s** with zero failures. |
| **Web Production Build** | **PASS** | `next build` compiled `/` and `/scout/[id]` cleanly with dynamic server rendering. |

### Pytest Log:
```
apps/api/tests/test_api.py::test_health_endpoint PASSED
apps/api/tests/test_api.py::test_root_endpoint PASSED
apps/api/tests/test_contract_mocks.py::test_fields_contract PASSED
apps/api/tests/test_contract_mocks.py::test_scan_and_hotspots_contract PASSED
apps/api/tests/test_contract_mocks.py::test_route_contract PASSED
apps/api/tests/test_contract_mocks.py::test_observation_and_confirm_loop PASSED
apps/api/tests/test_health.py::test_backend_sanity PASSED
apps/api/tests/test_health.py::test_config_defaults PASSED

======================== 8 passed in 1.93s ========================
```

---

## 3. How to Run Phase 1

1. **Start Backend**:
   ```powershell
   cd apps/api
   C:\tools\python311\Scripts\uvicorn.exe app.main:app --host 0.0.0.0 --port 8000 --reload
   ```
2. **Start Frontend**:
   ```powershell
   cd apps/web
   C:\tools\node_full\node-v20.15.0-win-x64\npm.cmd run dev
   ```
3. Open `http://localhost:3000` to see the Desktop Dashboard with live mock data.
4. Open `http://localhost:3000/scout/s_01` to test the mobile Scout app workflow.

---

## 4. Next Step: Phase 2 (Simulator + Preprocessing + Indices)
When approved:
1. Build `app.sim.generate` producing synthetic field images, bounds, and ground truth masks.
2. Implement `app.engine.geo` for flat-earth metric conversions.
3. Implement `preprocess.py` (gray-world normalisation, Otsu canopy mask, shadow exclusion).
4. Implement `indices.py` (VARI & GLI vegetation layers).
5. Gate G1: Simulator image overlays correctly on the Leaflet map; GLCM baseline benchmark measured.

