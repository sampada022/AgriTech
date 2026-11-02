# AeroScout — Unified Web Dashboard & End-to-End Demo Guide

**Status**: LIVE & FULLY INTEGRATED  
**Backend API**: `http://127.0.0.1:8000`  
**Frontend Application**: `http://localhost:5174`  
**Demo Credentials**:
- **Email**: `demo@aeroscout.app`
- **Password**: `aeroscout-demo`
- *(Or simply click the one-tap **"Fill demo account"** button on the Login page)*

---

## 1. What Was Completed & Plugged In

1. **Clean Integration of the Complete Frontend System**:
   - Replaced legacy boilerplate with the complete UI suite from your package.
   - Built with full GSAP animations, Lenis smooth scrolling, interactive Field Maps, Leaf Inspection upload modals, and complete Hotspot triage tables.
2. **Unified Backend Functionality Intact**:
   - The FastAPI backend now serves **all** endpoints:
     - Authentication & Demo Sessions (`/api/aeroscout/auth/*`)
     - Aerial Ingest & CV Hotspot Pipeline (`/api/aeroscout/scans/*`)
     - Interactive Layers & Heatmaps (`/api/aeroscout/scans/{id}/files/{kind}`)
     - Ground Truth Leaf Photo Uploads & Multimodal AI (`/api/aeroscout/scans/{id}/hotspots/{id}/photo`)
     - Model State Updates & CSV Data Exports (`/api/aeroscout/scans/{id}/export.csv`)
     - Vernacular Farmer & Assisted Portals (`/api/farmer/*`, `/api/assisted/*`)
   - All 21 core engine regression and contract tests pass with 100% green status.
3. **Seeded Realistic Data**:
   - Initialized database (`data/agriscout.db`) with real UAV rice imagery and seeded demo runs (`FARM-001`, `FARM-002`, `FARM-003`).

---

## 2. End-to-End Demo Workflow (2-Minute Judging Walkthrough)

Follow these exact steps to demonstrate the entire pipeline live:

### Step 1: Open the Application & Login
1. Open your browser and navigate to: **[http://localhost:5174](http://localhost:5174)**.
2. Explore the landing page showcasing:
   - *Problem*: Why conventional aerial classification fails from 35m altitude.
   - *Triage Solution*: Classical CV + explainable anomaly scoring.
3. Click **"Dashboard"** in the top navigation (or navigate to `http://localhost:5174/#/login`).
4. Click **"Fill demo account"** (fills `demo@aeroscout.app` / `aeroscout-demo`) and click **Sign in**.

---

### Step 2: Overview & Anomaly Hotspots
1. You are now inside the **AeroScout Studio Dashboard** (`/#/dashboard`).
2. Under the **Overview** tab:
   - View high-level metrics: Total Fields Monitored, Critical Hotspot Tiers, and Saved Scouting Walk %.
   - Review recent aerial surveys.

---

### Step 3: Deep-Dive into a Field Survey (`Fields` Tab)
1. Click **Fields** in the sidebar navigation.
2. Select any active survey (e.g. *Kikkeri Paddy Plot A* or *Mandya Demo Field*).
3. The interactive **Field Viewer** opens:
   - **Layer Switcher**: Toggle between **RGB Field**, **VARI Vegetation Index**, **Texture Anomaly**, and **Fused Heatmap**.
   - **Flagged Hotspots**: Hover and click on any hotspot marker (Red Tier / Amber Tier).
   - **Explainability Evidence**: View the exact signed contribution cues (GLCM Contrast, Surface Entropy, Boundary Sharpness, and Area $m^2$).
   - **Optimized Walking Route**: View the 2-opt TSP walking path connecting prioritized hotspots to minimize walking effort.

---

### Step 4: Ground Truth Leaf Inspection & AI Diagnosis
1. While inspecting a Hotspot on the map, click **"Inspect Hotspot"** or **"Add Ground Observation"**.
2. Upload or inspect a ground leaf photo showing crop defoliation.
3. Select observed candidate: **Fall Armyworm** (or mark as Abiotic/False Alarm).
4. Click **"Save Observation / Confirm Ground Truth"**.

---

### Step 5: Live Model Recalibration & Triage Re-Ranking
1. Notice the hotspot status immediately transitions from `new` $\rightarrow$ `visited` / `treated`.
2. The regularized logistic scoring model recalibrates live (`v1` $\rightarrow$ `v2`), updating feature weights and re-ranking remaining field anomalies.

---

### Step 6: Export Reports & Data
1. Click **"Export CSV"** to download the complete spreadsheet of ranked hotspots and spatial coordinates.
2. Review the **Data** tab to see raw cue feature vectors and dataset provenance badges.

---

## 3. Server Management Reference

If you need to restart the servers at any time:
- **Backend API**:
  ```powershell
  $env:PYTHONPATH='c:\AgriTech\apps\api'
  cd c:\AgriTech\apps\api
  C:\tools\python311\Scripts\uvicorn.exe app.main:app --host 127.0.0.1 --port 8000
  ```
- **Web Frontend**:
  ```powershell
  cd c:\AgriTech\website_app\dist
  C:\tools\node_full\node-v20.15.0-win-x64\npx.cmd -y serve -s -l 5174
  ```

