from fastapi import APIRouter, Form, UploadFile, File
import uuid
import datetime
from app.schemas import ObservationRead, DiagnosisResult, CandidateDiagnosis, ConfirmLabelRequest
from app.mock_data import MOCK_OBSERVATIONS, MOCK_HOTSPOTS
from app.diagnosis.client import diagnose_leaf_image
from app.model.versions import record_feedback_and_recalibrate
from app.errors import AeroScoutError

router = APIRouter(tags=["Observations & Recalibration"])

@router.post("/hotspots/{hotspot_id}/observations", response_model=ObservationRead, status_code=201)
def create_observation(
    hotspot_id: str,
    lat: float = Form(...),
    lon: float = Form(...),
    language: str = Form("en"),
    photo: UploadFile = File(None)
):
    obs_id = f"obs_{uuid.uuid4().hex[:6]}"

    if photo and hasattr(photo, "file"):
        content = photo.file.read()
    else:
        content = b"sample_mock_leaf_bytes_faw"

    # Execute structured diagnosis client (hash lookup & IPM recommendations)
    diagnosis = diagnose_leaf_image(
        image_bytes=content,
        crop="Sugarcane",
        language=language
    )

    obs = {
        "id": obs_id,
        "hotspot_id": hotspot_id,
        "photo_url": "/demo/leaf_photos/leaf_01.jpg",
        "lat": lat,
        "lon": lon,
        "taken_at": datetime.datetime.utcnow().isoformat() + "Z",
        "language": language,
        "diagnosis": diagnosis.model_dump(),
        "label": None,
        "note": None
    }

    MOCK_OBSERVATIONS[obs_id] = obs
    return obs

@router.post("/observations/{observation_id}/confirm", response_model=ObservationRead)
def confirm_observation(observation_id: str, payload: ConfirmLabelRequest):
    obs = MOCK_OBSERVATIONS.get(observation_id)
    if not obs:
        raise AeroScoutError(
            code="OBSERVATION_NOT_FOUND",
            message=f"Observation '{observation_id}' not found.",
            hint="Take a leaf photo first.",
            status_code=404
        )

    obs["label"] = payload.label
    obs["note"] = payload.note

    # Trigger Live NumPy Logistic Model Recalibration & Re-ranking of remaining spots
    recal_result = record_feedback_and_recalibrate(
        hotspot_id=obs["hotspot_id"],
        label_str=payload.label,
        note=payload.note or ""
    )

    return obs
