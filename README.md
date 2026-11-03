# AeroScout AI (AgriTech)

> **Precision UAV-Based Pest & Stress Hotspot Triage and Ground Scout Feedback Loop**  
> Built for early crop stress detection, autonomous drone survey flight planning, and closed-loop ground scouting feedback.

---

## 🌟 Overview

Conventional aerial classification often promises too much from 35-meter drone flights. **AeroScout** is built on an honest triage principle:
> *"Tells you where to look first, and learns from what you find."*

Instead of deep-learning black boxes prone to hallucination, AeroScout uses **classical computer vision + robust anomaly z-scoring** to flag stress hotspots, plans an **optimal 2-opt TSP walking route** for scouts, provides **structured ground-level multimodal leaf diagnosis**, and **recalibrates its scoring model live** ($v_1 \rightarrow v_2$) the moment the farmer confirms field observations.

---

## 🚀 Key Capabilities

1. **Aerial Triage Engine (Zero-Hallucination Classical CV)**:
   - Automated image normalization & Otsu canopy thresholding.
   - VARI (Visible Atmospherically Resistant Index) & GLI rasters.
   - 48px grid tiling with local GLCM texture contrast, entropy, and boundary irregularity.
   - DBSCAN metric clustering in true ground coordinates (meters).
2. **Transparent Explainability**:
   - Every flagged anomaly provides **7 signed contribution cues** (Contrast, Entropy, Sharpness, Edge Ratio, Area) explaining *why* it was prioritized.
3. **Optimized Scout Pathing (2-opt TSP)**:
   - Solves the Traveling Salesperson Problem over prioritized hotspots.
   - Reduces scouting walking distance by **>70%** compared to full-field sweeps.
4. **Unified Farmer & Agronomist Web Studio**:
   - Multi-layer map viewer: RGB Mosaic, VARI vegetation raster, texture anomaly heatmap, and fused stress zones.
   - Integrated ground leaf inspection modal with IPM (Integrated Pest Management) biological recommendations.
   - Real-time model weight recalibration upon farmer verification.
5. **Autopilot Drone Flight Planning**:
   - Generates boustrophedon (lawnmower) flight paths based on camera FOV and altitude.
   - One-click exports to **DJI Pilot KML** and **QGroundControl Waypoints (`.wpl`)**.
6. **Data Interoperability & Research Exports**:
   - Instant downloads for **GeoJSON FeatureCollections**, **Summary CSVs**, and standardized **ML Training Dataset ZIPs** (`features.csv`, `labels.csv`, `metadata.json`).

---

## 🛠️ Architecture & Tech Stack

- **Backend**: Python 3.11, FastAPI, SQLModel + SQLite, NumPy, OpenCV, scikit-image, SciPy, scikit-learn, Shapely, Pillow, Playwright (PDF rendering).
- **Frontend**: React 19, Vite, Tailwind CSS v4, Framer Motion, GSAP, Lucide Icons, Leaflet. Two separate apps share the one backend: `website_app` (agronomist/Studio dashboard) and `farmer_portal` (farmer-facing dashboard).
- **Leaf diagnosis**: Gemini (`google-genai`) by default, with an Anthropic provider also available. Falls back to a cached/canned reply when no API key is set or the live call fails, so the demo never shows a blank screen.

---

## ⚡ Quick Start

### 1. Prerequisites
- Python **3.11** specifically — `numpy==1.26.4` has no prebuilt wheel for 3.13, so a newer interpreter will fail to install. On Windows, use the `py -3.11` launcher if you have multiple Python versions.
- Node.js 20+

### 2. Clone and set up the Python environment
```bash
git clone https://github.com/sampada022/AgriTech.git
cd AgriTech

py -3.11 -m venv .venv
.venv\Scripts\activate          # macOS/Linux: source .venv/bin/activate

pip install -r apps/api/requirements.txt
playwright install chromium     # one-time, needed for PDF report rendering
```

### 3. Add your Gemini API key
Create `apps/api/.env` (this file is gitignored — each developer needs their own):
```
GEMINI_API_KEY=your_key_here
```
Get a free-tier key from [Google AI Studio](https://aistudio.google.com/apikey). Without a key set, leaf diagnosis still works but only returns cached/canned replies instead of live analysis.

### 4. Seed demo fields and farmer accounts
```bash
cd apps/api
python -m app.seed
cd ../..
```

### 5. Run the backend
```bash
cd apps/api
uvicorn app.main:app --host 127.0.0.1 --port 8000
```
If `website_app` has already been built (`npm run build`, see below), the Studio dashboard is served directly at **`http://localhost:8000`**. Otherwise this just serves the API.

### 6. Run the frontends (separate terminals)
```bash
cd website_app
npm install
npm run dev
```
Studio dashboard at **`http://localhost:5174`** — proxies `/api` and `/files` to the backend on port 8000.

```bash
cd farmer_portal
npm install
npm run dev
```
Farmer dashboard at **`http://localhost:5173`** — same proxy setup.

---

## 🔑 Demo Access Credentials

The Studio dashboard includes pre-configured access for judging and testing:
- **Demo Account**: `demo@aeroscout.app`
- **Password**: `aeroscout-demo`
- *(Or simply click the one-tap **"Fill demo account"** button on the Login page)*

The seeded farmer accounts (from `python -m app.seed`) log into `farmer_portal` via OTP, PIN `1234`.

---

## 🧪 Running Automated Tests

Run the backend test suite — geo-conversions, CV anomaly tiling, 2-opt TSP route planning, leaf diagnosis providers and cache, logistic model recalibration, and the farmer/OTP/assisted API surface:
```bash
pytest apps/api/tests -v
```
176 tests, all running locally with no external network dependencies (the live Gemini/Anthropic providers are exercised against local stub servers, not the real API).

---

## 📄 License
This project was developed for the AgriTech / LeapHack Hackathon. Licensed under the MIT License.

