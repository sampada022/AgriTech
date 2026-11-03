from __future__ import annotations

import secrets
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import JSON, Column
from sqlmodel import Field, SQLModel


def now() -> datetime:
    """Timezone-aware UTC. SQLite drops the timezone on round-trip, so anything comparing a
    freshly created value against one read back from the database must upconvert the naive
    side first (see services/serialize.py's _aware() for the established pattern)."""
    return datetime.now(timezone.utc)


# Preet's engine/services code calls this name; same clock as now().
utcnow = now


def new_id(prefix: str) -> str:
    return f"{prefix}_{secrets.token_hex(4)}"


def _json_column() -> Any:
    return Field(default=None, sa_column=Column(JSON))


# ---------------------------------------------------------------- farmer identity & access
# (kept from the OTP / assisted-operator / PDF-report design, unchanged by the engine swap)


class Farmer(SQLModel, table=True):
    id: str = Field(primary_key=True)  # e.g. MDY-001
    name: str
    village: str
    language: str = "kn"
    mobile: str
    access_mode: str = "BOTH"  # DIGITAL | ASSISTED | BOTH
    sms_consent: bool = True
    collection_point: str = ""


class Operator(SQLModel, table=True):
    id: str = Field(primary_key=True)
    name: str
    centre: str
    pin_salt: str
    pin_hash: str


class Farm(SQLModel, table=True):
    id: str = Field(primary_key=True)
    farmer_id: str = Field(foreign_key="farmer.id", index=True)
    name: str
    crop: str = "Paddy"


class Report(SQLModel, table=True):
    id: str = Field(primary_key=True)
    scan_id: str = Field(foreign_key="scan.id", index=True)
    farmer_id: str = Field(foreign_key="farmer.id", index=True)
    version: int = 1
    path: str
    generated_at: datetime = Field(default_factory=now)


class SessionToken(SQLModel, table=True):
    token_hash: str = Field(primary_key=True)
    subject_type: str  # FARMER | OPERATOR
    subject_id: str
    expires_at: datetime


class LoginChallenge(SQLModel, table=True):
    id: str = Field(primary_key=True)
    farmer_id: str
    otp_hash: str
    expires_at: datetime
    attempts: int = 0
    status: str = "PENDING"  # PENDING | VERIFIED | EXPIRED | LOCKED


class AccessRequest(SQLModel, table=True):
    id: str = Field(primary_key=True)
    farmer_id: str = Field(index=True)
    report_id: str
    operator_id: str
    otp_hash: str
    expires_at: datetime
    attempts: int = 0
    verified_at: Optional[datetime] = None
    status: str = "PENDING"  # PENDING | VERIFIED | EXPIRED | LOCKED | REVOKED
    access_token_hash: Optional[str] = None
    access_expires_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=now)


class AccessLog(SQLModel, table=True):
    pk: Optional[int] = Field(default=None, primary_key=True)
    farmer_id: str
    report_id: str
    actor_type: str  # FARMER | OPERATOR
    actor_id: str
    access_type: str  # VIEW | DOWNLOAD
    authorization_id: str = ""  # AccessRequest id, or SELF
    at: datetime = Field(default_factory=now)


class SmsMessage(SQLModel, table=True):
    """Outbox. In production a real gateway delivers these; in demo they are shown on a phone simulator."""

    pk: Optional[int] = Field(default=None, primary_key=True)
    to_mobile: str = Field(index=True)
    sender: str = "AGRISCT"
    body: str
    kind: str = "INFO"  # OTP | NOTIFY | INFO
    at: datetime = Field(default_factory=now)


# AeroUser (the website's email+password login) stays in aero_models.py.

# ---------------------------------------------------------------- engine (the one real pipeline)
# Ported from the Preet backend: pure-function engine, tested, documented. A FieldRecord here is
# reused across a farm's repeated surveys (FieldRecord.id == Farm.id once the farm's first scan runs).

SCAN_QUEUED = "queued"
SCAN_RUNNING = "running"
SCAN_DONE = "done"
SCAN_FAILED = "failed"
SCAN_CANCELLED = "cancelled"

STATUS_DETECTED = "detected"
STATUS_ASSIGNED = "assigned"
STATUS_INSPECTED = "inspected"
STATUS_CONFIRMED = "confirmed"
STATUS_CLEARED = "cleared"
HOTSPOT_STATUSES = (
    STATUS_DETECTED,
    STATUS_ASSIGNED,
    STATUS_INSPECTED,
    STATUS_CONFIRMED,
    STATUS_CLEARED,
)
RESOLVED_STATUSES = (STATUS_CONFIRMED, STATUS_CLEARED)


class FieldRecord(SQLModel, table=True):
    __tablename__ = "field"

    id: str = Field(primary_key=True)
    name: str
    crop: str = ""
    data_source: str = "real"  # real | stand_in | synthetic
    sw_lat: float
    sw_lon: float
    ne_lat: float
    ne_lon: float
    image_path: str
    thumbnail_path: str
    image_width: int
    image_height: int
    gsd_cm: float
    altitude_m: float | None = None
    created_at: datetime = Field(default_factory=now)


class Scan(SQLModel, table=True):
    id: str = Field(primary_key=True)
    field_id: str = Field(index=True)
    status: str = SCAN_QUEUED
    stage: str | None = None
    progress: int = 0
    params: dict | None = _json_column()
    quality: dict | None = _json_column()
    quality_score: float | None = None
    canopy_pct: float | None = None
    kpis: dict | None = _json_column()
    layers: dict | None = _json_column()
    mask_path: str | None = None
    stage_timings: dict | None = _json_column()
    grid: dict | None = _json_column()
    version_used: int | None = None
    error: dict | None = _json_column()
    cancel_requested: bool = False
    created_at: datetime = Field(default_factory=now)
    started_at: datetime | None = None
    finished_at: datetime | None = None


class Hotspot(SQLModel, table=True):
    id: str = Field(primary_key=True)
    scan_id: str = Field(index=True)
    polygon: dict | None = _json_column()  # GeoJSON Polygon geometry
    centroid_lat: float
    centroid_lon: float
    area_m2: float
    tile_count: int = 0
    cues: dict | None = _json_column()
    mean_anomaly: float = 0.0
    biotic_score: float = 0.5
    hotspot_class: str = "uncertain"
    tier: str = "amber"
    confidence_score: float = 0.0
    confidence: str = "low"
    contributions: dict | None = _json_column()
    abiotic_hint: str | None = None
    status: str = STATUS_DETECTED
    manual: bool = False
    crop_path: str | None = None
    rank: int = 0
    previous_rank: int | None = None
    previous_tier: str | None = None
    label: str | None = None
    note: str | None = None


class Observation(SQLModel, table=True):
    id: str = Field(primary_key=True)
    hotspot_id: str = Field(index=True)
    photo_path: str | None = None  # blank for a verdict recorded with no photo (farmer/operator quick verdict)
    image_hash: str = ""
    lat: float | None = None
    lon: float | None = None
    taken_at: datetime = Field(default_factory=now)
    language: str = "en"
    ai_response: dict | None = _json_column()
    ai_source: str = "fallback"  # live | cache | canned | fallback
    label: str | None = None
    note: str | None = None
    confirmed_at: datetime | None = None
    # False once a model reset has retired this label from training. The label itself is kept,
    # so it still appears in the drawer and in dataset exports.
    in_training: bool = True


class ModelVersion(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    version: int = Field(index=True)
    weights: dict | None = _json_column()
    bias: float = 0.0
    label_count: int = 0
    agreement: float | None = None
    parent_version: int | None = None
    created_at: datetime = Field(default_factory=now)


class Route(SQLModel, table=True):
    id: str = Field(primary_key=True)
    scan_id: str = Field(index=True)
    mode: str
    start_lat: float
    start_lon: float
    ordered_hotspot_ids: list | None = _json_column()
    leg_distances_m: list | None = _json_column()
    distance_m: float = 0.0
    eta_min: float = 0.0
    baseline_m: float = 0.0
    saved_pct: float = 0.0
    w_pattern_m: float = 0.0
    saved_vs_w_pct: float = 0.0
    include_abiotic: bool = False
    walking_speed_mps: float = 1.2
    minutes_per_stop: float = 3.0
    created_at: datetime = Field(default_factory=now)


class FlightPlan(SQLModel, table=True):
    id: str = Field(primary_key=True)
    polygon: dict | None = _json_column()
    altitude_m: float
    front_overlap: float
    side_overlap: float
    waypoints: list | None = _json_column()
    summary: dict | None = _json_column()
    kml: str = ""
    waypoint_file: str = ""
    created_at: datetime = Field(default_factory=now)
