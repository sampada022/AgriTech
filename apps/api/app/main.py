from __future__ import annotations

import mimetypes
import os
from contextlib import asynccontextmanager
from pathlib import Path

# Windows' mimetypes registry doesn't know .webp (engine map layers) in some environments;
# StaticFiles falls back to text/plain without this, which some browsers refuse to render as an image.
mimetypes.add_type("image/webp", ".webp")

from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .aero_auth import auth_router, ensure_demo_user
from .api import demo, fields, flightplans, health, hotspots, model, scans
from .db import create_tables
from .errors import install_error_handlers
from .routes import admin_router, assisted_router, dev_router, farmer_router, verdict_router
from .services.model import ensure_prior
from .services.scans import fail_interrupted_scans
from .storage import ensure_dirs, public_dir


class RevalidatedFiles(StaticFiles):
    """Browsers keep these but check the ETag first, and an unchanged file is a cheap 304.

    Demo scans have stable ids, so a long max-age could show an old overlay under new hotspots
    after a bundle is rebuilt during rehearsal.
    """

    async def get_response(self, path, scope):  # noqa: ANN001
        response = await super().get_response(path, scope)
        if response.status_code in (200, 304):
            response.headers["Cache-Control"] = "no-cache"
        return response


@asynccontextmanager
async def lifespan(_: FastAPI):
    ensure_dirs()
    create_tables()
    ensure_demo_user()
    from .db import new_session
    with new_session() as session:
        ensure_prior(session)
    fail_interrupted_scans()
    yield


LOCAL_ORIGINS = [
    "http://localhost:5173", "http://127.0.0.1:5173",
    "http://localhost:5174", "http://127.0.0.1:5174",
    "http://localhost:5175", "http://127.0.0.1:5175",
    "http://localhost:3000", "http://127.0.0.1:3000",
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
    allow_origin_regex=os.environ.get("AGRISCOUT_CORS_REGEX") or None,
    allow_methods=["*"],
    allow_headers=["*"],
)
install_error_handlers(app)

# The Studio API: the real engine, one real pipeline. Bare /api/* paths, matching Preet's own
# tests/benchmarks/docs verbatim (the website's Studio client is updated to match, see Stage B).
aeroscout_api = APIRouter(prefix="/api")
for _module in (fields, scans, hotspots, model, flightplans, demo, health):
    aeroscout_api.include_router(_module.router)
app.include_router(aeroscout_api)

# The farmer-facing side: OTP login, assisted operator access, admin console, PDF reports.
# auth_router keeps its own /api/aeroscout/auth/* prefix (the website's login, unrelated to OTP).
for r in (auth_router, farmer_router, verdict_router, assisted_router, admin_router, dev_router):
    app.include_router(r)

# Engine-produced images (map layers, hotspot crops, leaf photos) served from one static root.
app.mount("/files", RevalidatedFiles(directory=public_dir(), check_dir=False), name="files")

# Mount the SPA static files from website_app/dist so frontend & backend run on one port seamlessly.
DIST_DIR = Path(__file__).resolve().parents[3] / "website_app" / "dist"
if DIST_DIR.exists():
    from fastapi.responses import FileResponse

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
