# AeroScout — Phase 3 Completion & Gate G2 Report

**Date & Time**: Nov 2, 2026  
**Status**: **PASSED & COMPLETE (Gate G2 Achieved)**

---

## 1. What Was Built in Phase 3

Phase 3 delivered the sliced classical CV analysis and polygon hotspot extraction engine:

### A. Non-Overlapping Grid Tiling (`apps/api/app/engine/tiles.py`)
- Slices working image into non-overlapping **48px tiles** (~1.44 m at 3 cm/px GSD).
- **Canopy filter**: Tiles with $<60\%$ canopy are excluded from scoring and flagged as non-canopy (never falsely scored as crop anomalies).
- **Multi-cue tile feature extraction**:
  - Greenness mean and standard deviation (on canopy pixels).
  - GLCM texture on 16 quantized gray levels (distances $d \in \{1, 3\}$, 4 angles $\{0, \pi/4, \pi/2, 3\pi/4\}$):
    - GLCM Contrast
    - GLCM Homogeneity
    - GLCM Energy
    - GLCM Entropy ($-\sum p \log_2 p$)
  - Anisotropy: directional striping $\frac{|C_0 - C_{90}|}{C_0 + C_{90} + \epsilon}$.
  - Canny edge density on canopy pixels.

### B. Robust Anomaly Scoring (`apps/api/app/engine/anomaly.py`)
- Standardizes greenness and contrast over field canopy tiles using median and Median Absolute Deviation (MAD):
  $$z = \frac{x - \text{median}}{1.4826 \cdot \text{MAD}}$$
- Computes anomaly score $A$:
  $$A = \max(0, -z_{\text{greenness}}) + 0.6 \cdot \max(0, z_{\text{contrast}})$$
- Flags tiles where $A \ge \tau$ (user-configurable sensitivity slider; default $\tau = 2.0$).

### C. DBSCAN Spatial Clustering & Polygons (`apps/api/app/engine/cluster.py`)
- Sliced analysis merge: Tiles straddling patch boundaries merge into single continuous polygons.
- DBSCAN clustering in **local metric coordinates**:
  - $\epsilon = 1.6 \cdot \text{tile\_size\_m}$
  - `min_samples = 3` (avoids single-tile false alarms)
- Converts member tile boxes to unified metric polygons using **Shapely** (`unary_union`).
- Filters out noise clusters smaller than $2.0 \text{ m}^2$.
- Computes cluster properties: area in $\text{m}^2$, solidity ($\frac{\text{area}}{\text{convex hull}}$), and mean anomaly score.
- Re-projects polygon boundaries to WGS84 `[lon, lat]` GeoJSON format.

### D. Layer Rendering Engine (`apps/api/app/engine/render.py`)
- `render_anomaly_heatmap_rgba`: Upsamples tile anomaly scores using bicubic interpolation into smooth RGBA overlays with alpha transparency for non-stressed canopy.

---

## 2. Gate G2 Acceptance Checks

| Gate G2 Acceptance Check | Result | Evidence / Measurement |
|:---|:---:|:---|
| **Canopy Filter Exclusion** | **PASS** | Bare ground/road tiles ($<60\%$ canopy) excluded from anomaly scores. |
| **Robust z-Score & Anomaly Math** | **PASS** | Stressed vegetation successfully flagged via robust deviation from field baseline. |
| **DBSCAN Metric Clustering** | **PASS** | Flagged tiles merge into continuous Shapely polygons in metres. |
| **Min Area Filter** | **PASS** | Dropped small spurious detections $< 2.0 \text{ m}^2$. |
| **Valid GeoJSON Polygons** | **PASS** | Output features conform to RFC 7946 WGS84 coordinates. |
| **Heatmap RGBA Rendering** | **PASS** | Smooth alpha-blended overlay generated matching image dimensions. |
| **Automated Test Suite** | **PASS** | **11 passed in 5.61s** (`test_engine_phase3.py` + full suite). |

---

## 3. How to Verify Phase 3

Run the unit test verifying tiling, anomaly scoring, DBSCAN clustering, and heatmap rendering:
```powershell
C:\tools\python311\Scripts\pytest.exe apps/api/tests/test_engine_phase3.py -v
```

---

## 4. Next Step: Phase 4 (Scoring, Explanations, Route Planner, & Leaf Diagnosis)
When approved:
1. Multi-cue logistic scoring ($B = \text{sigmoid}(w \cdot f + b)$) mapping cues to `likely_biotic`, `uncertain`, and `likely_abiotic` with confidence and signed `contributions`.
2. Connect real pipeline to `POST /api/fields/{id}/scans`.
3. 2-Opt walking route planner & baseline comparison math.
4. Leaf-photo diagnosis integration with structured schema validation and fallback card.
5. Gate G3: Upload field image → real hotspots → route end-to-end in browser.

