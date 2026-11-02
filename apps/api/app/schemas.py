from typing import List, Dict, Optional, Literal, Any
from pydantic import BaseModel, Field

# ----------------- Common / Error -----------------
class ErrorDetail(BaseModel):
    code: str
    message: str
    hint: str

class ErrorResponse(BaseModel):
    error: ErrorDetail

# ----------------- Field -----------------
class Bounds(BaseModel):
    sw: List[float] = Field(..., description="[lat, lon] of south-west corner")
    ne: List[float] = Field(..., description="[lat, lon] of north-east corner")

class FieldCreate(BaseModel):
    name: str
    crop: str
    bounds: Bounds
    data_source: Literal["synthetic", "real"] = "synthetic"

class FieldRead(BaseModel):
    id: str
    name: str
    crop: str
    data_source: Literal["synthetic", "real"]
    bounds: Bounds
    image_url: str
    gsd_cm: float
    created_at: str

# ----------------- Scan -----------------
class ScanCreate(BaseModel):
    tile_px: int = 48
    threshold: float = 2.0
    eps: float = 1.6

class KPISummary(BaseModel):
    hotspot_count: int
    area_flagged_pct: float
    spray_area_pct: float
    walk_saved_pct: float
    route_distance_m: float
    baseline_distance_m: float

class ScanRead(BaseModel):
    model_config = {"protected_namespaces": ()}
    id: str
    field_id: str
    status: Literal["queued", "processing", "completed", "failed"]
    stage: str
    progress: int
    timings: Dict[str, float]
    quality_score: float
    canopy_pct: float
    kpi_summary: KPISummary
    layers: Dict[str, str]
    model_version: str

# ----------------- Hotspots (GeoJSON) -----------------
class HotspotCues(BaseModel):
    contrast_ratio: float
    entropy_ratio: float
    edge_ratio: float
    irregularity: float
    sharpness: float
    log_area: float
    anisotropy: float

class HotspotProperties(BaseModel):
    model_config = {"populate_by_name": True}
    scan_id: str
    rank: int
    area_m2: float
    tier: Literal["red", "amber", "grey"]
    biotic_score: float
    biotic_class: Literal["likely_biotic", "uncertain", "likely_abiotic"] = Field(..., alias="class")
    confidence: Literal["high", "medium", "low"]
    cues: HotspotCues
    contributions: Dict[str, float]
    status: Literal["detected", "assigned", "inspected", "confirmed", "cleared"]
    manual: bool = False
    crop_url: str

class GeoJSONPolygon(BaseModel):
    type: Literal["Polygon"] = "Polygon"
    coordinates: List[List[List[float]]]

class HotspotFeature(BaseModel):
    type: Literal["Feature"] = "Feature"
    id: str
    geometry: GeoJSONPolygon
    properties: HotspotProperties

class HotspotFeatureCollection(BaseModel):
    type: Literal["FeatureCollection"] = "FeatureCollection"
    features: List[HotspotFeature]

class HotspotPatch(BaseModel):
    status: Optional[Literal["detected", "assigned", "inspected", "confirmed", "cleared"]] = None
    note: Optional[str] = None

# ----------------- Route -----------------
class RouteWaypoint(BaseModel):
    lat: float
    lon: float
    label: str
    hotspot_id: Optional[str] = None
    tier: Optional[str] = None
    rank: Optional[int] = None

class RouteRequest(BaseModel):
    start: Optional[List[float]] = None
    mode: Literal["shortest", "worst_first"] = "worst_first"
    include_abiotic: bool = False

class RouteRead(BaseModel):
    id: str
    scan_id: str
    mode: Literal["shortest", "worst_first"]
    ordered_hotspot_ids: List[str]
    distance_m: float
    eta_min: float
    saved_pct: float
    baseline_m: float
    spray_area_pct: float
    waypoints: List[RouteWaypoint]

# ----------------- Leaf Diagnosis & Observations -----------------
class CandidateDiagnosis(BaseModel):
    name: str
    type: Literal["pest", "disease", "nutrient", "water", "other"]
    probability: float

class DiagnosisResult(BaseModel):
    plant_visible: bool
    image_quality: Literal["good", "blurry", "poor_lighting"]
    observed_symptoms: List[str]
    candidates: List[CandidateDiagnosis]
    confirm_by: List[str]
    actions_ipm: List[str]
    needs_expert: bool
    disclaimer: str

class ObservationRead(BaseModel):
    id: str
    hotspot_id: str
    photo_url: str
    lat: float
    lon: float
    taken_at: str
    language: str
    diagnosis: DiagnosisResult
    label: Optional[Literal["pest", "disease", "nutrient", "water", "weeds", "false_alarm"]] = None
    note: Optional[str] = None

class ConfirmLabelRequest(BaseModel):
    label: Literal["pest", "disease", "nutrient", "water", "weeds", "false_alarm"]
    note: Optional[str] = None

class ManualHotspotCreate(BaseModel):
    lat: float
    lon: float
    note: Optional[str] = "Observed during ground scouting"

# ----------------- Model Calibration -----------------
class ModelVersionHistory(BaseModel):
    model_config = {"protected_namespaces": ()}
    version: str
    n_labels: int
    training_agreement_pct: Optional[float]
    created_at: str

class ModelStatusRead(BaseModel):
    model_config = {"protected_namespaces": ()}
    active_version: str
    n_labels: int
    training_agreement_pct: Optional[float]
    weights: Dict[str, float]
    bias: float
    history: List[ModelVersionHistory]

