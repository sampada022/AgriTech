"""GET /health: liveness, plus the dependency status on the demo-controls panel."""

from __future__ import annotations

import threading
import time
import urllib.error
import urllib.request

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlmodel import Session, select

from app.config import get_settings
from app.db import get_session
from app.models import SCAN_QUEUED, SCAN_RUNNING, Scan
from app.schemas import HealthOut

router = APIRouter(tags=["health"])

LLM_HOST = "https://api.anthropic.com/"
_PROBE_TIMEOUT_S = 2.0


def _reachable(url: str) -> bool:
    """Any HTTP answer counts, even a 4xx: the point is that the host can be reached."""
    request = urllib.request.Request(url, method="HEAD", headers={"User-Agent": "AeroScout/0.1"})
    try:
        with urllib.request.urlopen(request, timeout=_PROBE_TIMEOUT_S):  # noqa: S310
            return True
    except urllib.error.HTTPError:
        return True
    except (urllib.error.URLError, TimeoutError, OSError):
        return False


class _Probe:
    """Refreshes in the background, so /health stays fast even when the venue network is not."""

    def __init__(self) -> None:
        self.state: dict[str, bool | None] = {"llm": None, "basemap": None}
        self.checked_at = 0.0
        self._running = False
        self._lock = threading.Lock()

    def maybe_refresh(self, max_age: float, basemap_url: str) -> None:
        with self._lock:
            if self._running or time.monotonic() - self.checked_at < max_age:
                return
            self._running = True
        threading.Thread(target=self._refresh, args=(basemap_url,), daemon=True).start()

    def _refresh(self, basemap_url: str) -> None:
        try:
            self.state = {"llm": _reachable(LLM_HOST), "basemap": _reachable(basemap_url)}
            self.checked_at = time.monotonic()
        finally:
            self._running = False


_probe = _Probe()


@router.get("/health", response_model=HealthOut, summary="Liveness and dependency status")
def health(session: Session = Depends(get_session)) -> dict:
    settings = get_settings()
    _probe.maybe_refresh(settings.health_cache_s, settings.basemap_url)
    try:
        session.exec(text("SELECT 1"))
        database = True
    except Exception:  # noqa: BLE001  (health must report a broken database, not crash on it)
        database = False
    active = session.exec(select(Scan).where(Scan.status.in_((SCAN_QUEUED, SCAN_RUNNING)))).all()
    return {
        "status": "ok" if database else "degraded",
        "demo_mode": settings.demo_mode,
        "database": database,
        "llm": {
            "provider": settings.diagnosis_provider,
            "model": settings.diagnosis_model,
            "api_key_set": bool(settings.anthropic_api_key),
            "reachable": _probe.state["llm"],
        },
        "basemap": {"url": settings.basemap_url, "reachable": _probe.state["basemap"]},
        "analysis": {"active_scans": len(active)},
    }
