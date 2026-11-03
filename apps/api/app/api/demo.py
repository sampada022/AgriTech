"""Demo controls (F17). Every route returns 404 unless DEMO_MODE=1."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlmodel import Session

from app.config import get_settings
from app.db import get_session
from app.diagnosis.service import rate_limiter
from app.errors import ApiError
from app.schemas import DemoLoadOut, DemoSettingsOut, DemoSettingsPatch
from app.services.demo import load_scenario, reset_all
from app.services.demo_settings import demo_settings


def _demo_only() -> None:
    if not get_settings().demo_mode:
        raise ApiError(
            404,
            "demo_mode_off",
            "Demo controls are turned off.",
            "Start the server with DEMO_MODE=1.",
        )


router = APIRouter(prefix="/demo", tags=["demo"], dependencies=[Depends(_demo_only)])


@router.post(
    "/load/{scenario}",
    response_model=DemoLoadOut,
    summary="Load Healthy, Pest outbreak or Mixed stress",
    description="scenario is one of healthy, pest, mixed. Ids are stable: f_mixed and s_mixed.",
)
def post_load(scenario: str, session: Session = Depends(get_session)) -> dict:
    return load_scenario(session, scenario)


@router.post("/reset", summary="Delete everything and return to the priors")
def post_reset(session: Session = Depends(get_session)) -> dict:
    reset_all(session)
    rate_limiter.reset()
    return {"status": "reset"}


@router.get("/settings", response_model=DemoSettingsOut, summary="Read the demo settings")
def get_demo_settings() -> dict:
    return demo_settings.as_dict()


@router.patch(
    "/settings",
    response_model=DemoSettingsOut,
    summary="Force cached AI or set the simulated GPS speed",
)
def patch_demo_settings(body: DemoSettingsPatch) -> dict:
    if body.force_cached_ai is not None:
        demo_settings.force_cached_ai = body.force_cached_ai
    if body.sim_speed_mps is not None:
        demo_settings.sim_speed_mps = body.sim_speed_mps
    return demo_settings.as_dict()
