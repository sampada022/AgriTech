"""Request and response shapes. These generate /docs, the contract the frontend builds against."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

Tier = Literal["red", "amber", "grey_blue"]
HotspotClass = Literal["likely_biotic", "uncertain", "likely_abiotic"]
HotspotStatus = Literal["detected", "assigned", "inspected", "confirmed", "cleared"]
RouteMode = Literal["shortest", "worst_first"]
Label = Literal["pest", "disease", "nutrient", "water", "weeds_other", "false_alarm"]
Language = Literal["en", "kn"]


class ErrorDetail(BaseModel):
    code: str
    message: str
    hint: str | None = None


class ErrorResponse(BaseModel):
    error: ErrorDetail


class LatLon(BaseModel):
    lat: float = Field(ge=-90, le=90)
    lon: float = Field(ge=-180, le=180)


class BoundsOut(BaseModel):
    sw_lat: float
    sw_lon: float
    ne_lat: float
    ne_lon: float
    leaflet: list[list[float]] = Field(description="[[south, west], [north, east]] for Leaflet.")


class ScanSummary(BaseModel):
    id: str
    status: str
    progress: int
    hotspot_count: int | None = None
    tier_counts: dict[str, int] | None = None
    created_at: str | None = None
    finished_at: str | None = None


class FieldOut(BaseModel):
    id: str
    name: str
    crop: str
    data_source: Literal["synthetic", "stand_in", "real"]
    data_source_badge: str = Field(description="Show this on every field: the honesty badge.")
    bounds: BoundsOut
    thumbnail_url: str | None
    image_width: int
    image_height: int
    gsd_cm: float
    altitude_m: float | None
    created_at: str | None
    latest_scan: ScanSummary | None


class ScanCreate(BaseModel):
    tile_px: int | None = Field(default=None, ge=16, le=128, description="Default 48.")
    threshold: float | None = Field(default=None, ge=0.5, le=10, description="Default 2.0.")
    eps: float | None = Field(
        default=None, ge=1.0, le=5.0, description="Multiple of the tile size. Default 1.6."
    )
    min_canopy: float | None = Field(
        default=None,
        ge=0.1,
        le=0.9,
        description="Share of a tile that must be green canopy for it to be scored. Default 0.6, "
        "for a closed canopy. Try 0.3 for seedling to early whorl stage, when the canopy is open.",
    )


class ScanCreated(BaseModel):
    id: str
    field_id: str
    status: str


class LayerInfo(BaseModel):
    url: str
    bytes: int
    format: str


class LayerOut(LayerInfo):
    layer: Literal["rgb", "vari", "heat"]
    bounds: BoundsOut


class ScanOut(BaseModel):
    id: str
    field_id: str
    status: Literal["queued", "running", "done", "failed", "cancelled"]
    stage: str | None
    stages: list[str] = Field(description="The eight named stages, in order.")
    progress: int = Field(description="0 to 100.")
    elapsed_s: float | None
    stage_timings: dict[str, float]
    params: dict[str, Any]
    quality: dict[str, Any] | None = Field(description="score, warnings, blur_variance and so on.")
    canopy_pct: float | None
    mask_preview_url: str | None
    layers: dict[str, LayerInfo]
    bounds: BoundsOut
    grid: dict[str, Any] | None
    kpis: dict[str, Any] | None
    model_version_used: int | None
    data_source: str
    data_source_badge: str
    error: ErrorDetail | None
    created_at: str | None
    started_at: str | None
    finished_at: str | None


class ThresholdUpdate(BaseModel):
    threshold: float = Field(ge=0.5, le=10, description="tau, from the sensitivity slider.")


class HotspotPatch(BaseModel):
    status: HotspotStatus | None = None
    note: str | None = Field(default=None, max_length=2000)


class ManualHotspotCreate(BaseModel):
    lat: float = Field(ge=-90, le=90)
    lon: float = Field(ge=-180, le=180)
    radius_m: float = Field(default=2.0, gt=0, le=50)
    note: str | None = Field(default=None, max_length=2000)


class Centroid(BaseModel):
    lat: float
    lon: float


class HotspotProperties(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    scan_id: str
    rank: int
    previous_rank: int | None
    area_m2: float
    centroid: Centroid
    tile_count: int
    tier: Tier
    previous_tier: Tier | None
    biotic_score: float
    hotspot_class: HotspotClass = Field(alias="class")
    confidence: Literal["high", "medium", "low"]
    confidence_score: float
    mean_anomaly: float
    cues: dict[str, float]
    contributions: dict[str, float] = Field(
        description="Signed push from each cue. Build the why-flagged bars from this."
    )
    abiotic_hint: Literal["striping", "large_smooth_zone"] | None
    abiotic_hint_text: str | None
    status: HotspotStatus
    label: Label | None
    manual: bool
    note: str | None
    crop_url: str | None


class HotspotFeature(BaseModel):
    type: Literal["Feature"] = "Feature"
    id: str
    geometry: dict[str, Any] = Field(description="GeoJSON Polygon, in [lon, lat].")
    properties: HotspotProperties


class HotspotCollection(BaseModel):
    type: Literal["FeatureCollection"] = "FeatureCollection"
    scan_id: str
    model_version: int | None
    features: list[HotspotFeature] = Field(description="Sorted by rank.")


class RouteCreate(BaseModel):
    start: LatLon | None = Field(default=None, description="Default: south-west field corner.")
    mode: RouteMode = "shortest"
    include_abiotic: bool = False
    walking_speed_mps: float = Field(default=1.2, gt=0.1, le=5)
    minutes_per_stop: float = Field(default=3.0, ge=0, le=60)


class RouteStop(BaseModel):
    order: int
    hotspot_id: str
    lat: float
    lon: float
    tier: Tier
    biotic_score: float
    area_m2: float
    status: HotspotStatus
    leg_distance_m: float
    cumulative_distance_m: float


class RouteOut(BaseModel):
    id: str
    scan_id: str
    mode: RouteMode
    include_abiotic: bool
    start: LatLon
    stops: list[RouteStop]
    stop_count: int
    distance_m: float
    eta_min: float
    baseline_m: float = Field(description="Length of a full serpentine sweep.")
    saved_pct: float
    w_pattern_m: float = Field(description="Length of a W-pattern scouting walk.")
    saved_vs_w_pattern_pct: float = Field(description="Can be negative. Show next to saved_pct.")
    polyline: dict[str, Any] = Field(description="GeoJSON LineString, in [lon, lat].")
    assumptions: dict[str, Any] = Field(description="Feeds the tooltips on assumption-based numbers.")


class ScanWithHotspots(BaseModel):
    scan: ScanOut
    hotspots: HotspotCollection
    route: RouteOut | None


class ConfirmRequest(BaseModel):
    label: Label
    note: str | None = Field(default=None, max_length=2000)


class CandidateOut(BaseModel):
    name: str
    type: str
    probability: float


class DiagnosisResult(BaseModel):
    plant_visible: bool
    image_quality: str
    observed_symptoms: list[str]
    candidates: list[CandidateOut]
    confirm_by: list[str]
    actions_ipm: list[str]
    needs_expert: bool
    language: str


class LabelOption(BaseModel):
    label: Label
    name: str


class DiagnosisBlock(BaseModel):
    source: Literal["live", "cache", "canned", "fallback"] = Field(
        description="canned is a demo stand-in and fallback means result is null. Tell the user."
    )
    result: DiagnosisResult | None
    suggested_label: Label | None
    message: str | None = Field(description="Set when result is null: show it with label_options.")
    photo_warning: str | None
    advisory: str
    label_options: list[LabelOption]


class ObservationOut(BaseModel):
    id: str
    hotspot_id: str
    photo_url: str | None
    lat: float | None
    lon: float | None
    taken_at: str | None
    language: str
    label: Label | None
    note: str | None
    confirmed_at: str | None
    diagnosis: DiagnosisBlock | None


class HotspotDetail(BaseModel):
    feature: HotspotFeature
    observations: list[ObservationOut]
    guidance: dict[str, Any] | None = Field(description="IPM-first guidance once labelled.")


class ChangeState(BaseModel):
    tier: Tier
    rank: int
    biotic_score: float


class HotspotChange(BaseModel):
    hotspot_id: str
    before: ChangeState
    after: ChangeState


class FalsePositive(BaseModel):
    count: int
    suggest_raise_threshold: bool
    hint: str | None


class ModelChange(BaseModel):
    version: int
    previous_version: int
    changed: bool
    label_count: int
    agreement: float | None
    weight_changes: dict[str, dict[str, float]]
    note: str


class ConfirmOut(BaseModel):
    observation_id: str
    hotspot_id: str
    label: Label
    model: ModelChange
    changes: list[HotspotChange] = Field(description="Hotspots that moved. Animate these.")
    route: RouteOut
    kpis: dict[str, Any]
    false_positive: FalsePositive
    guidance: dict[str, Any]


class ModelOut(BaseModel):
    version: int
    weights: dict[str, float]
    bias: float
    prior_weights: dict[str, float]
    prior_bias: float
    is_prior: bool
    label_count: int
    agreement: float | None
    agreement_note: str
    recalibration_note: str
    false_positive: FalsePositive
    cues: list[dict[str, Any]]


class ModelVersionOut(BaseModel):
    version: int
    parent_version: int | None
    weights: dict[str, float]
    bias: float
    label_count: int
    agreement: float | None
    created_at: str | None


class ModelHistory(BaseModel):
    versions: list[ModelVersionOut]


class FlightPlanCreate(BaseModel):
    name: str = Field(default="AeroScout survey", max_length=120)
    polygon: list[LatLon] = Field(min_length=3, max_length=200)
    altitude_m: float = Field(default=35.0, gt=5)
    front_overlap: float = Field(default=0.75, ge=0, le=0.95)
    side_overlap: float = Field(default=0.65, ge=0, le=0.95)
    camera: dict[str, float] | None = None


class FlightPlanOut(BaseModel):
    id: str
    altitude_m: float
    front_overlap: float
    side_overlap: float
    waypoints: list[dict[str, float]]
    summary: dict[str, Any]
    kml: str
    waypoint_file: str
    kml_url: str
    waypoint_file_url: str


class DemoSettingsPatch(BaseModel):
    force_cached_ai: bool | None = None
    sim_speed_mps: float | None = Field(default=None, gt=0, le=20)


class DemoSettingsOut(BaseModel):
    force_cached_ai: bool
    sim_speed_mps: float


class DemoLoadOut(BaseModel):
    scenario: str
    field_id: str
    scan_id: str
    load_seconds: float
    synthetic: bool


class HealthOut(BaseModel):
    status: str
    demo_mode: bool
    database: bool
    llm: dict[str, Any]
    basemap: dict[str, Any]
    analysis: dict[str, Any]
