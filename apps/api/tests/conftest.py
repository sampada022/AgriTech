"""Tests run against a throwaway data folder, with no API key and no network."""

from __future__ import annotations

import io
import os
import shutil
import tempfile
import time

_ROOT = tempfile.mkdtemp(prefix="aeroscout-tests-")
os.environ["DATA_DIR"] = os.path.join(_ROOT, "data")
os.environ["DEMO_ASSETS_DIR"] = os.path.join(_ROOT, "demo_assets")
os.environ["DEMO_MODE"] = "1"
os.environ["DEMO_AUTOLOAD"] = ""
os.environ["DIAGNOSIS_PROVIDER"] = "none"
os.environ["ANTHROPIC_API_KEY"] = ""
os.environ["CORS_ORIGINS"] = "http://localhost:3000"
os.environ["BENCHMARK_RESULTS"] = os.path.join(_ROOT, "bench.json")
os.environ["REAL_PIXEL_RESULTS"] = os.path.join(_ROOT, "real.json")

import numpy as np  # noqa: E402
import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from PIL import Image  # noqa: E402

from app.diagnosis.service import demo_replies_dir  # noqa: E402
from app.engine.geo import bounds_from_centre  # noqa: E402
from app.engine.simulator import SimConfig, simulate  # noqa: E402
from app.main import app  # noqa: E402

SMALL = {"width": 1536, "height": 1152}


@pytest.fixture(scope="session")
def client():
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture(autouse=True)
def clean_state(client):
    assert client.post("/api/demo/reset").status_code == 200
    # A demo reset keeps these on purpose, so tests have to clear them to stay independent.
    shutil.rmtree(demo_replies_dir(), ignore_errors=True)
    yield


@pytest.fixture(scope="session")
def small_sim():
    """A field small enough to analyse quickly, with a known pest patch in it."""
    return simulate(SimConfig("mixed", "easy", 3, n_pest=4, n_drought=1, n_nutrient=1, **SMALL))


def jpeg_bytes(rgb: np.ndarray, quality: int = 95, **save_kwargs) -> bytes:
    buffer = io.BytesIO()
    Image.fromarray(rgb).save(buffer, "JPEG", quality=quality, **save_kwargs)
    return buffer.getvalue()


def leaf_photo(seed: int = 1, size: tuple[int, int] = (600, 800)) -> bytes:
    rng = np.random.default_rng(seed)
    pixels = rng.random((*size, 3)) * 80 + np.array([40, 110, 30])
    return jpeg_bytes(pixels.astype(np.uint8), 85)


def upload_field(client, rgb, bounds=None, name="Test field", data_source="synthetic", **form):
    h, w = rgb.shape[:2]
    bounds = bounds or bounds_from_centre(12.5231, 76.8951, w * 0.03, h * 0.03)
    return client.post(
        "/api/fields",
        files={"image": ("field.jpg", jpeg_bytes(rgb), "image/jpeg")},
        data={
            "name": name,
            "crop": "Maize",
            "data_source": data_source,
            **bounds.as_dict(),
            **form,
        },
    )


def wait_for_scan(client, scan_id: str, timeout_s: float = 60) -> dict:
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        scan = client.get(f"/api/scans/{scan_id}").json()
        if scan["status"] in ("done", "failed", "cancelled"):
            return scan
        time.sleep(0.05)
    raise AssertionError(f"Scan {scan_id} did not finish in {timeout_s} s")


@pytest.fixture
def scanned_field(client, small_sim):
    field = upload_field(client, small_sim.image, small_sim.bounds).json()
    started = client.post(f"/api/fields/{field['id']}/scans", json={})
    assert started.status_code == 202
    scan = wait_for_scan(client, started.json()["id"])
    assert scan["status"] == "done", scan["error"]
    return field, scan
