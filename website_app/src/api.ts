export interface GeoJsonGeometry { type: string; coordinates: unknown }

// Types mirror apps/api/app/schemas.py exactly -- that file is the contract.
export type Tier = 'red' | 'amber' | 'grey_blue'
export type HotspotClass = 'likely_biotic' | 'uncertain' | 'likely_abiotic'
export type HotspotStatus = 'detected' | 'assigned' | 'inspected' | 'confirmed' | 'cleared'
export type RouteMode = 'shortest' | 'worst_first'
export type Label = 'pest' | 'disease' | 'nutrient' | 'water' | 'weeds_other' | 'false_alarm'
export type Confidence = 'high' | 'medium' | 'low'
export type DataSource = 'synthetic' | 'stand_in' | 'real'

export const LABEL_NAMES: Record<Label, string> = {
  pest: 'Pest damage', disease: 'Disease', nutrient: 'Nutrient deficiency',
  water: 'Water stress', weeds_other: 'Weeds or other', false_alarm: 'False alarm (healthy)',
}
export const TIER_NAMES: Record<Tier, string> = { red: 'Red', amber: 'Amber', grey_blue: 'Grey' }

export interface Bounds { sw_lat: number; sw_lon: number; ne_lat: number; ne_lon: number; leaflet: [number, number][] }
export interface ScanSummary {
  id: string; status: string; progress: number
  hotspot_count: number | null; tier_counts: Record<string, number> | null
  created_at: string | null; finished_at: string | null
}
export interface FieldOut {
  id: string; name: string; crop: string; data_source: DataSource; data_source_badge: string
  bounds: Bounds; thumbnail_url: string | null; image_width: number; image_height: number
  gsd_cm: number; altitude_m: number | null; created_at: string | null; latest_scan: ScanSummary | null
}
export interface LayerInfo { url: string; bytes: number; format: string }
export interface ScanGrid {
  tile_px: number; ny: number; nx: number; tiles_total: number; tiles_excluded: number; tiles_nodata: number
  tiles_flagged: number; working_width: number; working_height: number; gsd_cm: number; data_fraction: number
  default_start: { lat: number; lon: number } | null
}
export interface ScanOut {
  id: string; field_id: string; status: 'queued' | 'running' | 'done' | 'failed' | 'cancelled'
  stage: string | null; stages: string[]; progress: number; elapsed_s: number | null
  stage_timings: Record<string, number>; params: Record<string, unknown>
  quality: Record<string, unknown> | null; canopy_pct: number | null; mask_preview_url: string | null
  layers: Record<string, LayerInfo>; bounds: Bounds; grid: ScanGrid | null
  kpis: Kpis | null; model_version_used: number | null
  data_source: DataSource; data_source_badge: string
  error: { code: string; message: string; hint: string | null } | null
  created_at: string | null; started_at: string | null; finished_at: string | null
}
export interface Kpis {
  hotspot_count: number; tier_counts: Record<Tier, number>
  field_area_m2: number; area_flagged_m2: number; area_flagged_pct: number
  spray_area_m2: number; spray_area_pct: number
  walk_saved_pct: number | null; route_distance_m: number | null; baseline_distance_m: number | null
  walk_saved_vs_w_pattern_pct: number | null; w_pattern_distance_m: number | null
  route_stops: number; eta_min: number | null
  tiles_total: number | null; tiles_excluded: number | null
  assumptions: Record<string, unknown>
}
export interface Centroid { lat: number; lon: number }
export interface HotspotProperties {
  scan_id: string; rank: number; previous_rank: number | null; area_m2: number; centroid: Centroid
  tile_count: number; tier: Tier; previous_tier: Tier | null; biotic_score: number
  class: HotspotClass; confidence: Confidence; confidence_score: number; mean_anomaly: number
  cues: Record<string, number>; contributions: Record<string, number>
  abiotic_hint: 'striping' | 'large_smooth_zone' | null; abiotic_hint_text: string | null
  status: HotspotStatus; label: Label | null; manual: boolean; note: string | null; crop_url: string | null
}
export interface HotspotFeature { type: 'Feature'; id: string; geometry: GeoJsonGeometry; properties: HotspotProperties }
export interface HotspotCollection { type: 'FeatureCollection'; scan_id: string; model_version: number | null; features: HotspotFeature[] }
export interface RouteStop {
  order: number; hotspot_id: string; lat: number; lon: number; tier: Tier; biotic_score: number
  area_m2: number; status: HotspotStatus; leg_distance_m: number; cumulative_distance_m: number
}
export interface RouteOut {
  id: string; scan_id: string; mode: RouteMode; include_abiotic: boolean
  start: { lat: number; lon: number }; stops: RouteStop[]; stop_count: number
  distance_m: number; eta_min: number; baseline_m: number; saved_pct: number
  w_pattern_m: number; saved_vs_w_pattern_pct: number
  polyline: GeoJsonGeometry; assumptions: Record<string, unknown>
}
export interface CandidateOut { name: string; type: string; probability: number }
export interface DiagnosisResult {
  plant_visible: boolean; image_quality: string; observed_symptoms: string[]
  candidates: CandidateOut[]; confirm_by: string[]; actions_ipm: string[]; needs_expert: boolean; language: string
}
export interface LabelOption { label: Label; name: string }
export interface DiagnosisBlock {
  source: 'live' | 'cache' | 'canned' | 'fallback'; result: DiagnosisResult | null
  suggested_label: Label | null; message: string | null; photo_warning: string | null
  advisory: string; label_options: LabelOption[]
}
export interface ObservationOut {
  id: string; hotspot_id: string; photo_url: string | null; lat: number | null; lon: number | null
  taken_at: string | null; language: string; label: Label | null; note: string | null
  confirmed_at: string | null; diagnosis: DiagnosisBlock | null
}
export interface HotspotDetail { feature: HotspotFeature; observations: ObservationOut[]; guidance: Record<string, unknown> | null }
export interface ModelChange {
  version: number; previous_version: number; changed: boolean; label_count: number
  agreement: number | null; weight_changes: Record<string, { before: number; after: number }>; note: string
}
export interface HotspotChange { hotspot_id: string; before: { tier: Tier; rank: number; biotic_score: number }; after: { tier: Tier; rank: number; biotic_score: number } }
export interface FalsePositive { count: number; suggest_raise_threshold: boolean; hint: string | null }
export interface ConfirmOut {
  observation_id: string; hotspot_id: string; label: Label; model: ModelChange
  changes: HotspotChange[]; route: RouteOut; kpis: Kpis; false_positive: FalsePositive; guidance: Record<string, unknown>
}
export interface CueMeta { name: string; direction: 'biotic' | 'abiotic'; rationale: string; prior_weight: number; centre: number; range: number }
export interface ModelOut {
  version: number; weights: Record<string, number>; bias: number
  prior_weights: Record<string, number>; prior_bias: number; is_prior: boolean
  label_count: number; agreement: number | null; agreement_note: string; recalibration_note: string
  false_positive: FalsePositive; cues: CueMeta[]
}
export interface ModelVersionOut { version: number; parent_version: number | null; weights: Record<string, number>; bias: number; label_count: number; agreement: number | null; created_at: string | null }
export interface DemoSettings { force_cached_ai: boolean; sim_speed_mps: number }
export interface DemoLoadOut { scenario: string; field_id: string; scan_id: string; load_seconds: number; synthetic: boolean }
export interface HealthOut { status: string; demo_mode: boolean; database: boolean; llm: Record<string, unknown>; basemap: Record<string, unknown>; analysis: Record<string, unknown> }

export interface User { id: string; name: string; email: string }

export class ApiError extends Error {
  status: number
  hint: string | null
  constructor(status: number, message: string, hint: string | null = null) {
    super(message)
    this.status = status
    this.hint = hint
  }
}

async function j<T>(r: Response): Promise<T> {
  if (r.status === 401 && !r.url.includes('/auth/')) dispatchEvent(new Event('aero:unauth'))
  if (!r.ok) {
    let message = r.statusText
    let hint: string | null = null
    try {
      const body = await r.json()
      message = body?.error?.message ?? (typeof body.detail === 'string' ? body.detail : JSON.stringify(body.detail ?? body))
      hint = body?.error?.hint ?? null
    } catch { /* non-JSON error body */ }
    throw new ApiError(r.status, message, hint)
  }
  return r.json() as Promise<T>
}

const AUTH_BASE = '/api/aeroscout/auth'
const post = (path: string, body: unknown) =>
  fetch(`${AUTH_BASE}/${path}`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) })

export const authApi = {
  me: () => fetch(`${AUTH_BASE}/me`).then((r) => (r.ok ? (r.json() as Promise<User>) : null)).catch(() => null),
  login: (email: string, password: string) => post('login', { email, password }).then(j<User>),
  register: (name: string, email: string, password: string) => post('register', { name, email, password }).then(j<User>),
  logout: () => post('logout', {}).then(() => undefined),
}

function form(data: Record<string, string | number | boolean | File | undefined>): FormData {
  const fd = new FormData()
  for (const [k, v] of Object.entries(data)) if (v !== undefined) fd.append(k, v instanceof File ? v : String(v))
  return fd
}

export const fieldsApi = {
  list: () => fetch('/api/fields').then(j<FieldOut[]>),
  get: (id: string) => fetch(`/api/fields/${id}`).then(j<FieldOut>),
  create: (data: {
    image: File; name: string; sw_lat: number; sw_lon: number; ne_lat: number; ne_lon: number
    crop?: string; data_source?: DataSource; altitude_m?: number
  }) => fetch('/api/fields', { method: 'POST', body: form(data) }).then(j<FieldOut>),
  startScan: (fieldId: string, body: { tile_px?: number; threshold?: number; eps?: number; min_canopy?: number } = {}) =>
    fetch(`/api/fields/${fieldId}/scans`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) })
      .then(j<{ id: string; field_id: string; status: string }>),
}

export const scansApi = {
  get: (id: string) => fetch(`/api/scans/${id}`).then(j<ScanOut>),
  cancel: (id: string) => fetch(`/api/scans/${id}/cancel`, { method: 'POST' }).then(j<ScanOut>),
  hotspots: (id: string) => fetch(`/api/scans/${id}/hotspots`).then(j<HotspotCollection>),
  addManualHotspot: (id: string, lat: number, lon: number, radius_m = 2, note?: string) =>
    fetch(`/api/scans/${id}/hotspots`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ lat, lon, radius_m, note }) })
      .then(j<HotspotFeature>),
  setThreshold: (id: string, threshold: number) =>
    fetch(`/api/scans/${id}/threshold`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ threshold }) })
      .then(j<{ scan: ScanOut; hotspots: HotspotCollection; route: RouteOut | null }>),
  planRoute: (id: string, body: { mode?: RouteMode; start?: { lat: number; lon: number }; include_abiotic?: boolean } = {}) =>
    fetch(`/api/scans/${id}/route`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) }).then(j<RouteOut>),
  getRoute: (id: string) => fetch(`/api/scans/${id}/route`).then(j<RouteOut>),
  exportUrl: (id: string, kind: 'geojson' | 'csv' | 'dataset.zip') => `/api/scans/${id}/export/${kind}`,
}

export const hotspotsApi = {
  get: (id: string) => fetch(`/api/hotspots/${id}`).then(j<HotspotDetail>),
  patch: (id: string, body: { status?: HotspotStatus; note?: string }) =>
    fetch(`/api/hotspots/${id}`, { method: 'PATCH', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) }).then(j<HotspotFeature>),
  addObservation: (hotspotId: string, photo: File, language: 'en' | 'kn' = 'en', note?: string, lat?: number, lon?: number) =>
    fetch(`/api/hotspots/${hotspotId}/observations`, { method: 'POST', body: form({ photo, language, note, lat, lon }) }).then(j<ObservationOut>),
  getObservation: (id: string) => fetch(`/api/observations/${id}`).then(j<ObservationOut>),
  confirm: (observationId: string, label: Label, note?: string) =>
    fetch(`/api/observations/${observationId}/confirm`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ label, note }) })
      .then(j<ConfirmOut>),
}

export const modelApi = {
  get: () => fetch('/api/model').then(j<ModelOut>),
  history: () => fetch('/api/model/history').then(j<{ versions: ModelVersionOut[] }>),
  reset: () => fetch('/api/model/reset', { method: 'POST' }).then(j<ModelOut>),
  validation: () => fetch('/api/model/validation').then(j<Record<string, unknown>>),
}

export const demoApi = {
  load: (scenario: 'healthy' | 'pest' | 'mixed') => fetch(`/api/demo/load/${scenario}`, { method: 'POST' }).then(j<DemoLoadOut>),
  reset: () => fetch('/api/demo/reset', { method: 'POST' }).then(j<{ status: string }>),
  settings: () => fetch('/api/demo/settings').then(j<DemoSettings>),
  patchSettings: (body: Partial<DemoSettings>) =>
    fetch('/api/demo/settings', { method: 'PATCH', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) }).then(j<DemoSettings>),
}

export const healthApi = { get: () => fetch('/api/health').then(j<HealthOut>) }

export interface SmsMessage { pk: number; to_mobile: string; sender: string; body: string; kind: 'OTP' | 'NOTIFY' | 'INFO'; at: string }
export interface DemoRunOut {
  farmer_id: string; farmer_name: string; village: string; mobile: string; masked_mobile: string
  survey_id: string; report_id: string | null; sent: boolean
}

// The farmer-facing demo on the marketing site: a real SMS and a real PDF, no dashboard, no login --
// that is the actual shape of the shipped product (the farmer never sees a web app).
export const farmerDemoApi = {
  run: () => fetch('/api/dev/demo/run', { method: 'POST' }).then(j<DemoRunOut>),
  sms: (mobile: string) => fetch(`/api/dev/sms?mobile=${encodeURIComponent(mobile)}`).then(j<SmsMessage[]>),
  reportUrl: (reportId: string) => `/api/dev/demo/report/${reportId}`,
}

export function openBlobUrl(b: Blob, filename?: string) {
  const url = URL.createObjectURL(b)
  if (filename) {
    const a = document.createElement('a')
    a.href = url
    a.download = filename
    a.click()
  } else window.open(url, '_blank')
  setTimeout(() => URL.revokeObjectURL(url), 60_000)
}
