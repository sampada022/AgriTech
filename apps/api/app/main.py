from __future__ import annotations

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .db import init_db
from .aero_auth import auth_router, ensure_demo_user
from .aero_routes import aero_router
from .routes import admin_router, assisted_router, dev_router, farmer_router, verdict_router


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    ensure_demo_user()
    yield


LOCAL_ORIGINS = [
    "http://localhost:5173", "http://127.0.0.1:5173", 
    "http://localhost:5174", "http://127.0.0.1:5174", 
    "http://localhost:5175", "http://127.0.0.1:5175",
    "http://localhost:3000", "http://127.0.0.1:3000"
]


def cors_origins() -> list[str]:
    """Origins allowed to call the API from a browser.

    AGRISCOUT_CORS_ORIGINS is a comma-separated list (for example the Vercel site's URL). The local dev origins are
    always allowed. "*" allows any origin: acceptable only because auth is a bearer token sent in a header, never a cookie.
    """
    raw = os.environ.get("AGRISCOUT_CORS_ORIGINS", "").strip()
    if raw == "*":
        return ["*"]
    return [o.strip().rstrip("/") for o in raw.split(",") if o.strip()] + LOCAL_ORIGINS


app = FastAPI(title="AeroScout API", version="1.0.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins(),
    # Optional regex, e.g. https://agriscout-.*\.vercel\.app to also allow Vercel preview deployments.
    allow_origin_regex=os.environ.get("AGRISCOUT_CORS_REGEX") or None,
    allow_methods=["*"],
    allow_headers=["*"],
)
for r in (auth_router, aero_router, farmer_router, verdict_router, assisted_router, admin_router, dev_router):
    app.include_router(r)


@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "service": "AeroScout Core API",
        "llm": {"mode": "cached_fallback", "configured": False},
        "basemap": {"reachability": "online", "fallback": "dark_canvas"}
    }

# Mount SPA static files from website_app/dist so frontend & backend run on one port seamlessly
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pathlib import Path

DIST_DIR = Path(__file__).resolve().parents[3] / "website_app" / "dist"
if DIST_DIR.exists():
    app.mount("/assets", StaticFiles(directory=DIST_DIR / "assets"), name="assets")

    @app.get("/{full_path:path}")
    def serve_spa(full_path: str):
        file_path = DIST_DIR / full_path
        if file_path.is_file():
            return FileResponse(file_path)
        return FileResponse(DIST_DIR / "index.html")
else:
    @app.get("/")
    def read_root():
        return {"message": "AeroScout API operational."}
