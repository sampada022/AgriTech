"""Model page: current weights, version history, reset and the validation benchmark."""

from __future__ import annotations

import json

from fastapi import APIRouter, Depends
from sqlmodel import Session, select

from app.config import get_settings
from app.db import get_session
from app.engine.scoring import cue_metadata
from app.errors import ApiError
from app.models import ModelVersion
from app.schemas import ModelHistory, ModelOut
from app.services.model import model_payload, reset_model
from app.services.serialize import iso

router = APIRouter(tags=["model"])

REAL_PIXEL_DISCLAIMER = (
    "These runs show that cleaning and canopy masking work on real orthomosaics. The images have "
    "no pest ground truth, so they say nothing about pest accuracy. Any hotspots found on them are "
    "unverified."
)


def _model_response(session: Session) -> dict:
    return {**model_payload(session), "cues": cue_metadata()}


@router.get("/model", response_model=ModelOut, summary="Current weights and label count")
def get_model(session: Session = Depends(get_session)) -> dict:
    return _model_response(session)


@router.get("/model/history", response_model=ModelHistory, summary="Version history, newest first")
def get_history(session: Session = Depends(get_session)) -> dict:
    rows = sorted(session.exec(select(ModelVersion)).all(), key=lambda r: -r.version)
    return {
        "versions": [
            {
                "version": r.version,
                "parent_version": r.parent_version,
                "weights": r.weights,
                "bias": r.bias,
                "label_count": r.label_count,
                "agreement": r.agreement,
                "created_at": iso(r.created_at),
            }
            for r in rows
        ]
    }


@router.post(
    "/model/reset",
    response_model=ModelOut,
    summary="Back to priors",
    description="For rehearsals. Existing labels stay on record but stop training the model.",
)
def post_reset(session: Session = Depends(get_session)) -> dict:
    reset_model(session)
    return _model_response(session)


@router.get(
    "/model/validation",
    summary="Synthetic benchmark and real-pixel checks for the validation page",
    description="Always show both `disclaimer` fields, first. Produced by `make benchmark`.",
)
def get_validation() -> dict:
    settings = get_settings()
    path = settings.benchmark_results
    if not path.exists():
        raise ApiError(
            404,
            "benchmark_missing",
            "No benchmark results yet.",
            "Run `make benchmark` on the server.",
        )
    body = json.loads(path.read_text(encoding="utf-8"))
    real = settings.real_pixel_results
    body["real_pixels"] = {
        "disclaimer": REAL_PIXEL_DISCLAIMER,
        "checks": json.loads(real.read_text(encoding="utf-8")) if real.exists() else {},
    }
    return body
