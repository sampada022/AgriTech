from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from typing import List
import uuid
import datetime
from app.schemas import FieldRead, FieldCreate, Bounds
from app.mock_data import MOCK_FIELDS
from app.errors import AeroScoutError

router = APIRouter(prefix="/fields", tags=["Fields"])

@router.get("", response_model=List[FieldRead])
def list_fields():
    return MOCK_FIELDS

@router.get("/{field_id}", response_model=FieldRead)
def get_field(field_id: str):
    field = next((f for f in MOCK_FIELDS if f["id"] == field_id), None)
    if not field:
        raise AeroScoutError(
            code="FIELD_NOT_FOUND",
            message=f"Field with ID '{field_id}' does not exist.",
            hint="Check the field ID or create a new field first.",
            status_code=404
        )
    return field

@router.post("", response_model=FieldRead, status_code=201)
def create_field(
    name: str = Form(...),
    crop: str = Form(...),
    sw_lat: float = Form(...),
    sw_lon: float = Form(...),
    ne_lat: float = Form(...),
    ne_lon: float = Form(...),
    data_source: str = Form("synthetic")
):
    new_field = {
        "id": f"f_{uuid.uuid4().hex[:8]}",
        "name": name,
        "crop": crop,
        "data_source": data_source if data_source in ["synthetic", "real"] else "synthetic",
        "bounds": {
            "sw": [sw_lat, sw_lon],
            "ne": [ne_lat, ne_lon]
        },
        "image_url": "/demo/scenarios/mixed/field.jpg",
        "gsd_cm": 3.0,
        "created_at": datetime.datetime.utcnow().isoformat() + "Z"
    }
    MOCK_FIELDS.append(new_field)
    return new_field

