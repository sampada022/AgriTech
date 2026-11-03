"""POST /fields, GET /fields, GET /fields/{id}, POST /fields/{id}/scans."""

from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, UploadFile
from sqlmodel import Session, select

from app.config import get_settings
from app.db import get_session
from app.engine.geo import Bounds, FieldFrame
from app.engine.render import thumbnail_jpeg, write_bytes
from app.errors import ApiError, not_found
from app.models import FieldRecord, new_id
from app.schemas import FieldOut, ScanCreate, ScanCreated
from app.services.imaging import decode_image, encode_jpeg, read_upload
from app.services.scans import create_scan, params_from_request
from app.services.serialize import field_payload
from app.storage import field_image_path, public_dir

router = APIRouter(tags=["fields"])


def _validate_bounds(bounds: Bounds, max_diagonal_m: float) -> None:
    def invalid(message: str) -> ApiError:
        return ApiError(
            422, "invalid_bounds", message, "Drag the rectangle again or check the coordinates."
        )

    if not (-90 <= bounds.sw_lat <= 90 and -90 <= bounds.ne_lat <= 90):
        raise invalid("Latitudes must be between -90 and 90.")
    if not (-180 <= bounds.sw_lon <= 180 and -180 <= bounds.ne_lon <= 180):
        raise invalid("Longitudes must be between -180 and 180.")
    if bounds.ne_lat <= bounds.sw_lat or bounds.ne_lon <= bounds.sw_lon:
        raise invalid("The north-east corner must be north and east of the south-west corner.")
    frame = FieldFrame(bounds, 1, 1)
    if (frame.width_m**2 + frame.height_m**2) ** 0.5 > max_diagonal_m:
        raise invalid(f"This field is larger than {max_diagonal_m / 1000:g} km corner to corner.")


@router.post("/fields", response_model=FieldOut, status_code=201, summary="Create a field")
def create_field(
    image: UploadFile = File(description="JPG, PNG or 8-bit TIFF, up to 50 MB. Decoded to validate."),
    name: str = Form(max_length=120),
    sw_lat: float = Form(),
    sw_lon: float = Form(),
    ne_lat: float = Form(),
    ne_lon: float = Form(),
    crop: str = Form(default="", max_length=60),
    data_source: str = Form(default="real", pattern="^(real|stand_in|synthetic)$"),
    altitude_m: float | None = Form(default=None),
    session: Session = Depends(get_session),
) -> dict:
    settings = get_settings()
    bounds = Bounds(sw_lat, sw_lon, ne_lat, ne_lon)
    _validate_bounds(bounds, settings.max_field_diagonal_m)
    data = read_upload(image, settings.max_field_image_mb)
    decoded = decode_image(data, {"JPEG", "PNG", "TIFF"}, settings.max_field_pixels)

    field_id = new_id("f")
    # Re-encoded so drone EXIF, including GPS, is not kept with the stored image.
    target = field_image_path(field_id)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(encode_jpeg(decoded.rgb, 95, full_chroma=True))
    thumbnail = f"fields/{field_id}.jpg"
    write_bytes(public_dir() / thumbnail, thumbnail_jpeg(decoded.rgb))

    frame = FieldFrame(bounds, decoded.width, decoded.height)
    row = FieldRecord(
        id=field_id,
        name=name,
        crop=crop,
        data_source=data_source,
        sw_lat=sw_lat,
        sw_lon=sw_lon,
        ne_lat=ne_lat,
        ne_lon=ne_lon,
        image_path=target.name,
        thumbnail_path=thumbnail,
        image_width=decoded.width,
        image_height=decoded.height,
        gsd_cm=frame.gsd_m * 100,
        altitude_m=altitude_m,
    )
    session.add(row)
    session.commit()
    return field_payload(session, row)


@router.get("/fields", response_model=list[FieldOut], summary="List fields, newest first")
def list_fields(session: Session = Depends(get_session)) -> list[dict]:
    rows = session.exec(select(FieldRecord)).all()
    rows = sorted(rows, key=lambda f: f.created_at, reverse=True)
    return [field_payload(session, row) for row in rows]


@router.get("/fields/{field_id}", response_model=FieldOut, summary="Read a field")
def get_field(field_id: str, session: Session = Depends(get_session)) -> dict:
    row = session.get(FieldRecord, field_id)
    if row is None:
        raise not_found("Field", field_id)
    return field_payload(session, row)


@router.post(
    "/fields/{field_id}/scans",
    response_model=ScanCreated,
    status_code=202,
    summary="Start analysis",
    description="Returns the scan id at once. Poll GET /scans/{id} every 800 ms.",
)
def start_scan(
    field_id: str,
    body: ScanCreate | None = None,
    session: Session = Depends(get_session),
) -> dict:
    row = session.get(FieldRecord, field_id)
    if row is None:
        raise not_found("Field", field_id)
    body = body or ScanCreate()
    scan = create_scan(
        session, row, params_from_request(body.tile_px, body.threshold, body.eps, body.min_canopy)
    )
    return {"id": scan.id, "field_id": row.id, "status": scan.status}
