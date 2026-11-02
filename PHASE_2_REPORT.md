# AeroScout — Phase 2 Completion & Gate G1 Report

**Date & Time**: Nov 2, 2026  
**Status**: **PASSED & COMPLETE (Gate G1 Achieved)**

---

## 1. What Was Built in Phase 2

Phase 2 established the core computer vision ingestion pipeline and the synthetic field simulator:

### A. Local Metric Geometry & Coordinates (`apps/api/app/engine/geo.py`)
- Tested conversion functions for Mandya, Karnataka baseline (~12.52 N, 76.90 E):
  - `latlon_to_xy(lat, lon, lat0, lon0)`: converts WGS84 coordinates to local metric offsets (Easting $x$, Northing $y$).
  - `xy_to_latlon(x, y, lat0, lon0)`: inverse projection back to WGS84 GPS.
  - `compute_field_dimensions_m(sw, ne)`: calculates physical field width and height in metres.
  - `haversine_distance_m()`: computes great-circle metric distances.

### B. Preprocessing & Quality Gate (`apps/api/app/engine/preprocess.py`)
- **Quality Check** (`check_image_quality`):
  - Computes blur via variance of the Laplacian.
  - Computes exposure clipping percentage (<= 2 and >= 253 values).
  - Emits normalized quality score (0.0 to 1.0) and warning text.
- **Normalization** (`gray_world_normalise`):
  - Pure gray-world white balance without contrast enhancement or CLAHE to ensure GLCM texture statistics remain uncorrupted.
- **Canopy & Shadow Masking** (`compute_canopy_mask`):
  - Computes Excess Green index ($ExG = 2g - r - b$) on chromatic coordinates.
  - Excludes deep shadows using HSV Value channel threshold.
  - Cleans mask using elliptical morphological opening.

### C. Vegetation Indices (`apps/api/app/engine/indices.py`)
- Implemented visible-light proxies:
  - $\text{VARI} = \frac{G - R}{G + R - B + \epsilon}$ clipped to $[-1.0, 1.0]$.
  - $\text{GLI} = \frac{2G - R - B}{2G + R + B + \epsilon}$ clipped to $[-1.0, 1.0]$.
  - Combined robust standardized **Greenness** = mean of z-scored VARI and GLI.
  - `render_vari_colormap()`: renders VARI false-color heatmaps using standard colormaps.
  - *Honesty Rule*: Documented VARI as a visible-light greenness proxy, distinct from NIR satellite NDVI.

### D. Synthetic Field Simulator (`apps/api/app/sim/generate.py`)
- Generates synthetic 2048x1536 drone fields @ 3cm/px GSD (~1.1 ha near Mandya, Karnataka):
  - Sinusoidal crop rows with multi-octave noise.
  - 4 to 8 ragged pest patches with speckled chlorosis.
  - Smooth drought zones with soft-fading yellowing.
  - Nutrient deficiency stripes along row directions.
  - Distractors: bare soil field road and tree shadows.
  - Exports field image, ground truth class masks, bounds JSON, and patch metadata.
- Precomputed scenario saved to `demo/scenarios/mixed/`.

---

## 2. Gate G1 Acceptance Checks

| Gate G1 Acceptance Check | Result | Evidence / Measurement |
|:---|:---:|:---|
| **Flat-Earth Metric Coordinate Conversions** | **PASS** | Round-trip conversion error $< 10^{-5}$ degrees. Verified in `test_engine_phase2.py`. |
| **Synthetic Simulator Execution** | **PASS** | `app.sim.generate` produces `field.jpg`, `ground_truth_mask.png`, `bounds.json`, `patches.json`. |
| **Canopy & Shadow Mask Extraction** | **PASS** | Robust detection of crop canopy ($ExG > 0.05$) with shadow exclusion. |
| **VARI & GLI Raster Calculation** | **PASS** | Values properly clipped to $[-1.0, 1.0]$ and colormapped without distortion. |
| **GLCM Runtime Benchmark** | **PASS** | **0.149s for 500 tiles** (extrapolates to **~1.5s for 5,000 tiles**), well within the 20s budget! |
| **Automated Pytest Suite** | **PASS** | **10 passed in 1.63s** across API and Engine modules. |

---

## 3. How to Run Phase 2

1. **Run Synthetic Generator**:
   ```powershell
   C:\tools\python311\python.exe -m app.sim.generate --scenario mixed --seed 42 --difficulty medium --outdir demo/scenarios/mixed
   ```
2. **Run GLCM Texture Benchmark**:
   ```powershell
   C:\tools\python311\python.exe apps/api/app/engine/benchmark_glcm.py
   ```
3. **Execute Full Test Suite**:
   ```powershell
   C:\tools\python311\Scripts\pytest.exe apps/api/tests -v
   ```

---

## 4. Next Step: Phase 3 (Tiles, Anomaly, DBSCAN, & Polygons)
When approved:
1. Sliced non-overlapping 48px tile grid with $<60\%$ canopy exclusion.
2. Parallel tile texture feature extraction (GLCM contrast, homogeneity, energy, entropy, anisotropy, Canny edges).
3. Robust z-score anomaly scoring ($A = \max(0, -z_{\text{greenness}}) + 0.6 \cdot \max(0, z_{\text{contrast}})$).
4. DBSCAN spatial clustering in metres ($\epsilon = 1.6 \cdot \text{tile\_m}$, min samples = 3) with Shapely polygon union.
5. Gate G2: Real engine hotspots displayed on the map.

