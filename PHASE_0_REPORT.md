# AeroScout — Phase 0 Completion & Gate Report

**Date & Time**: Nov 2, 2026  
**Status**: **PASSED & COMPLETE**

---

## 1. What Was Built in Phase 0

Phase 0 established the complete foundational repository baseline, isolated local runtimes, and verified connectivity between the backend API and frontend web client.

### A. Repository Architecture & Layout
The project tree was created strictly matching the hackathon specifications:
- `AGENTS.md`: Master prompt & operating directives.
- `Makefile`: Dev/Demo/Test/Seed/Reset command entry points.
- `.env.example`: Tunables, storage paths, LLM modes, and demo flags.
- `KNOWN_ISSUES.md`: Issue tracking log.
- `apps/api/`: Python 3.11 FastAPI backend structure with subdirectories:
  - `app/routers/` (`health.py`, etc.)
  - `app/engine/`
  - `app/route/`
  - `app/diagnosis/`
  - `app/model/`
  - `app/sim/`
  - `tests/` (`test_health.py`, `test_api.py`)
- `apps/web/`: Next.js 14 App Router client with TypeScript, Tailwind CSS, Lucide icons, Framer Motion, and Leaflet dependencies.
- `data/` and `demo/`: Storage directories for persistent SQLite databases, image uploads, and precomputed scenario caches.

### B. Runtime Environment & Pinned Dependencies
Since the host Windows environment lacked pre-installed Python 3.11 and Node.js in the global PATH, standalone portable runtimes were deployed to `C:\tools\`:
- **Python 3.11.9** (`C:\tools\python311\python.exe`):
  - Configured `python311._pth` with `import site` and local module search paths.
  - Installed `pip 26.2.2`.
  - Installed all pinned backend requirements: `fastapi==0.111.0`, `uvicorn[standard]==0.30.1`, `pydantic==2.7.4`, `sqlmodel==0.0.19`, `numpy==1.26.4`, `opencv-python-headless==4.9.0.80`, `scikit-image==0.23.2`, `scipy==1.13.1`, `scikit-learn==1.5.0`, `shapely==2.0.4`, `pillow==10.3.0`, `joblib==1.4.2`, `httpx==0.27.0`, `pytest==8.2.2`.
- **Node.js LTS v20.15.0 & npm 10.7.0** (`C:\tools\node_full\node-v20.15.0-win-x64\`):
  - Installed all frontend web dependencies (`next`, `react`, `react-dom`, `leaflet`, `react-leaflet`, `zustand`, `@tanstack/react-query`, `framer-motion`, `lucide-react`, `tailwindcss`).

### C. Backend API Core & Health Endpoint
Implemented the core FastAPI application in `apps/api/app/main.py`:
- Configured CORS middleware for all development origins.
- Implemented structured error handling schema (`{"error": {"code": str, "message": str, "hint": str}}`).
- Built the `/api/health` endpoint reporting:
  - Overall status (`ok`).
  - LLM client mode (`cached_fallback` vs `live`).
  - Basemap reachability (`online` vs `offline` fallback).
  - Demo guard status (`active`).

### D. Next.js Web Application Shell
Built the initial UI shell in `apps/web/app/page.tsx`:
- Dark mode theme configured with design tokens matching the project palette (Deep Navy background `#0b111e`, Surface `#121b2d`, Agri Green `#10b981`, Precision Cyan `#06b6d4`, Amber warning `#f59e0b`, Red act `#ef4444`).
- Next.js rewrite proxy configured in `next.config.js` to route all `/api/*` calls directly to `http://127.0.0.1:8000/api/*`.
- Interactive health dashboard displaying live API status, LLM mode, Basemap reachability, and Phase 0 gate status.

---

## 2. Verification & Acceptance Checks

| Gate Acceptance Check | Result | Evidence |
|:---|:---:|:---|
| **Python & Dependencies Clean Load** | **PASS** | `verify_deps.py` runs without error; all scientific packages (`numpy`, `cv2`, `skimage`, `scipy`, `sklearn`, `shapely`) load cleanly. |
| **API Health Endpoint** | **PASS** | `GET /api/health` returns `200 OK` with JSON contract. |
| **Backend Unit Tests** | **PASS** | `pytest tests/` executed **4 passed in 4.28s**. |
| **Next.js Web Build** | **PASS** | `npm run build` compiled static pages with zero TypeScript or styling errors. |
| **`make` Targets Configured** | **PASS** | Top-level `Makefile` wired for `dev`, `demo`, `test`, `seed`, `reset`, `health`. |

---

## 3. How to Run the Project

### Start Development Mode (Both Servers)
Using Makefile:
```bash
make dev
```
Or manually in two terminals:
- **Backend**:
  ```powershell
  cd apps/api
  C:\tools\python311\Scripts\uvicorn.exe app.main:app --host 0.0.0.0 --port 8000 --reload
  ```
- **Frontend**:
  ```powershell
  cd apps/web
  C:\tools\node_full\node-v20.15.0-win-x64\npm.cmd run dev
  ```
- **Access Web**: Open `http://localhost:3000` in your browser.
- **Access API Docs**: Open `http://localhost:8000/docs`.

### Run Backend Tests
```bash
C:\tools\python311\Scripts\pytest.exe apps/api/tests -v
```

---

## 4. Risks & Mitigations Handled

1. **System Environment Runtimes**: Standard Windows store python was inaccessible in sandbox; addressed by provisioning self-contained portable toolchains in `C:\tools\`.
2. **Leaflet SSR Compatibility**: App Router structure set to `'use client'` only, prepped for dynamic Leaflet imports in Phase 1.
3. **Offline Demo Fallback**: Health probe defaults to `demo_mode` safe responses when external OSM servers are unreachable.

---

## 5. Next Step: Phase 1 (Contracts + Mocks)
Now that Phase 0 is complete and all gates are green:
1. Define Pydantic schemas in `apps/api/app/schemas.py`.
2. Document canonical GeoJSON and error formats in `docs/contract.md`.
3. Provide mock responses for `/api/fields`, `/api/scans`, `/api/hotspots`, `/api/route`, `/api/observations`.
4. Test mobile Scout PWA route and tunnel access.

