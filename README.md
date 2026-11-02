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

- **Backend**: Python 3.11, FastAPI, SQLModel + SQLite, NumPy, OpenCV, scikit-image, SciPy, scikit-learn, Shapely, Pillow.
- **Frontend**: React 19, Vite, Tailwind CSS v4, Framer Motion, GSAP, Lucide Icons, Leaflet.
- **Zero-Internet Fallback**: Fully self-contained offline mode with SHA-256 leaf diagnosis hash cache and dark-canvas basemaps.

---

## ⚡ Quick Start

### 1. Prerequisites
- Python 3.11+
- Node.js 20+

### 2. Backend Setup
```bash
# Clone the repository
git clone https://github.com/sampada022/AgriTech.git
cd AgriTech

# Install Python dependencies
pip install -r requirements.txt

# Seed realistic demo fields and farmer accounts
python -m app.seed
```

### 3. Run the Unified Server
```bash
cd apps/api
uvicorn app.main:app --host 127.0.0.1 --port 8000
```
Open your browser to: **`http://localhost:8000`**

---

## 🔑 Demo Access Credentials

The demo application includes pre-configured access for judging and testing:
- **Demo Account**: `demo@aeroscout.app`
- **Password**: `aeroscout-demo`
- *(Or simply click the one-tap **"Fill demo account"** button on the Login page)*

---

## 🧪 Running Automated Tests

Run the comprehensive 21-test suite covering geo-conversions, CV anomaly tiling, 2-opt TSP route planning, leaf diagnosis cache, and logistic model recalibration:
```bash
pytest apps/api/tests -v
```
All 21 unit and contract tests run locally with zero external network dependencies.

---

## 📄 License
This project was developed for the AgriTech / LeapHack Hackathon. Licensed under the MIT License.

