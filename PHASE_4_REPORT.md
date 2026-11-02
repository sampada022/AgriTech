# AeroScout — Phase 4 Completion & Gate G3 Report

**Date & Time**: Nov 2, 2026  
**Status**: **PASSED & COMPLETE (Gate G3 Achieved)**

---

## 1. What Was Built in Phase 4

Phase 4 integrated the complete real-time scoring, explainability, route planning, and leaf diagnosis into the end-to-end user loop:

### A. Explainable Multi-Cue Hotspot Scoring (`apps/api/app/engine/scoring.py`)
- Computes the 7 explainability cues:
  1. `contrast_ratio`: Inside hotspot vs field canopy baseline (thinning/holes raise contrast).
  2. `entropy_ratio`: Inside vs baseline (irregular ragged pest lesions).
  3. `edge_ratio`: Inside vs baseline (jagged canopy edges).
  4. `irregularity`: $1.0 - \text{solidity}$ (pest spread is ragged, drought is smooth).
  5. `sharpness`: Boundary gradient contrast (pests have sharp margins).
  6. `log_area`: $\ln(\text{m}^2)$ (large zones point toward abiotic water/fertilizer).
  7. `anisotropy`: Directional striping (high anisotropy indicates planter/sprayer tractor lines).
- Normalized logistic model:
  $$B = \frac{1}{1 + e^{-(w \cdot f_{\text{norm}} + b)}}$$
- Returns signed horizontal `contributions` per cue ($w_i \cdot f_i$) driving the explainability breakdown on the dashboard.
- Assigns severity tiers (`red` = likely biotic act, `amber` = inspect/uncertain, `grey` = likely abiotic).
- Computes `confidence` as the geometric mean of image quality, cue agreement ratio, and tile count support.

### B. 2-Opt Ground Scout Route Planner (`apps/api/app/route/planner.py`)
- Calculates pairwise distance with $1.2\times$ crop row detour factor.
- Solves tour using greedy nearest neighbor followed by **2-opt iterative edge swap optimization**.
- Modes:
  - `worst_first`: Prioritizes `red` tier, then `amber`, then `grey`.
  - `shortest`: Minimizes overall walking distance.
- Computes realistic ETA ($\frac{\text{distance}}{1.2 \text{ m/s}} + 3 \text{ min per stop}$).
- Calculates walk savings against a serpentine sweep baseline ($\text{field area} / 4\text{m}$).
- Calculates potential spot treatment area with 2m buffer.

### C. Leaf Photo Diagnosis & Cache (`apps/api/app/diagnosis/client.py`)
- Fast SHA-256 hash lookup on incoming leaf imagery.
- Returns structured JSON validated by Pydantic:
  - `plant_visible`, `image_quality`, `observed_symptoms`
  - Top 3 candidate causes with probabilities
  - Ground check verification advice (`confirm_by`)
  - IPM-first actions (`actions_ipm`)
  - Extension office disclaimer and expert assistance flags
- Guaranteed offline fallback with `DEMO_FORCE_CACHED_AI=1`.

### D. End-to-End Scan Pipeline Connection (`apps/api/app/engine/pipeline.py`)
- Connected `POST /api/fields/{id}/scans` to the real 11-stage pipeline:
  1. Quality gate
  2. Gray-world normalisation
  3. Canopy and shadow masking
  4. VARI/GLI vegetation rasters
  5. Sliced 48px grid tiling
  6. GLCM texture extraction
  7. Robust z-score anomaly detection
  8. DBSCAN metric clustering
  9. Feature extraction
  10. Scoring and explainability
  11. Heatmap rendering and KPI summaries

---

## 2. Gate G3 Acceptance Checks

| Gate G3 Acceptance Check | Result | Evidence / Measurement |
|:---|:---:|:---|
| **Hotspot Scoring Monotonicity** | **PASS** | High contrast/entropy pushes $B$ toward biotic; large area/anisotropy pulls toward abiotic. |
| **Why-Flagged Contributions** | **PASS** | Signed numerical cue contributions generated for every hotspot polygon. |
| **2-Opt Route Planner** | **PASS** | Generates verified ordered path reducing walk distance by $>60\%$ vs serpentine baseline. |
| **Diagnosis Response & Cache** | **PASS** | Instant cached response on repeated image hash with full IPM recommendation payload. |
| **End-to-End Scan Execution** | **PASS** | `run_aerial_scan_pipeline` processes field image and generates GeoJSON and RGBA heatmap. |
| **Automated Test Suite** | **PASS** | **15 passed in 7.33s** (`test_engine_phase4.py` + full suite). |
| **Next.js Production Build** | **PASS** | Web client compiles with zero errors. |

---

## 3. How to Run Phase 4

Run the Phase 4 test suite:
```powershell
C:\tools\python311\Scripts\pytest.exe apps/api/tests/test_engine_phase4.py -v
```

Or trigger a real scan through the API:
```powershell
curl -X POST http://localhost:8000/api/fields/f_mandya_01/scans
```

---

## 4. Next Step: Phase 5 (Confirm Flow, Recalibration, & Mobile Feedback Loop)
When approved:
1. Live NumPy gradient descent recalibration minimizing logistic loss + $\lambda \|w - w_0\|^2$.
2. Write `ModelVersion` rows (`v1` → `v2`) tracking training agreement and weight shifts.
3. Automatically re-score unlabelled hotspots and update map tiers live upon confirmation.
4. Full closed-loop demonstration on real phone over HTTPS tunnel.
5. Gate G4: Contract freeze.

