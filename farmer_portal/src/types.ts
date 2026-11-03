import type { Geometry } from 'geojson'

export type Tier = 'red' | 'amber' | 'grey_blue'
export type Confidence = 'high' | 'medium' | 'low'
export type Verdict = 'PEST' | 'NOT_PEST' | 'OTHER' | null

export interface Hotspot {
  id: string
  tier: Tier
  biotic_score: number
  hotspot_class: 'likely_biotic' | 'uncertain' | 'likely_abiotic'
  confidence: Confidence
  area_m2: number
  cues: Record<string, number>
  contributions: Record<string, number>
  abiotic_hint: 'striping' | 'large_smooth_zone' | null
  status: string
  label: string | null
  note: string | null
  rank: number
  centroid: [number, number]
  geometry: Geometry
}

// The backend stores a six-way label (pest/disease/nutrient/water/weeds_other/false_alarm); the
// farmer's three ground-check buttons are a coarser view over it.
export function verdictOf(h: Hotspot): Verdict {
  if (h.label === null) return null
  if (h.label === 'pest' || h.label === 'disease') return 'PEST'
  if (h.label === 'false_alarm') return 'NOT_PEST'
  return 'OTHER'
}

export interface SurveySummary {
  valid_crop_area_sqm: number
  suspicious_area_sqm: number
  suspicious_area_percent: number
  hotspots_detected: number
  status: 'anomalies_detected' | 'no_significant_anomaly'
}

export interface SurveyDetail {
  id: string
  farm: { id: string; name: string; crop: string }
  status: string
  created_at: string
  data_source: string
  summary: SurveySummary
  image: { width_px: number; height_px: number; gsd_m: number; bounds_wgs84: [number, number, number, number] }
  kpis: Record<string, unknown> | null
  quality: Record<string, unknown> | null
  layers: string[]
  hotspots: Hotspot[]
  report_id: string | null
}

export interface FarmerMe {
  id: string
  name: string
  village: string
  language: 'kn' | 'en'
  farms: {
    id: string
    name: string
    crop: string
    surveys: { id: string; status: string; created_at: string; summary: SurveySummary | null; data_source: string }[]
  }[]
}

export interface SmsMessage {
  pk: number
  to_mobile: string
  body: string
  kind: string
  at: string
}

export interface SimFarm {
  farm_id: string
  farm_name: string
  farmer_id: string
  farmer: string | null
  village: string | null
  language: 'kn' | 'en' | null
  access_mode: 'DIGITAL' | 'ASSISTED' | 'BOTH' | null
  input: { source: string; simulated_stress: boolean }
  survey_id: string | null
  status: 'not_started' | 'queued' | 'running' | 'done' | 'failed' | 'cancelled'
  stage: string
  progress: number
  error: { code: string; message: string; hint: string | null } | null
  result: {
    hotspots: number | null
    suspicious_percent: number | null
    valid_crop_area_sqm: number | null
    report_id: string | null
    notified: boolean
    sms: string | null
  } | null
}

export interface SimStatus {
  farms: SimFarm[]
  started: boolean
  finished: boolean
  ready: boolean
  missing: string[]
}
