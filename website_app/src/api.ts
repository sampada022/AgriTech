export type HState = 'new' | 'visited' | 'treated' | 'dismissed'
export interface Hotspot {
  id: string; severity: 'High' | 'Medium' | 'Low'; status: string; area_m2: number; area_pct: number; n_tiles: number
  vari: number; vari_drop: number; glcm_contrast: number; glcm_entropy: number; texture_ratio: number; score: number
  pct: [number, number]; route_stop?: number; bbox: number[]
  state: HState; state_note: string; state_updated: string | null
  photos: { id: string; species: string; note: string; url: string; created_at: string }[]
}
export interface Scan {
  id: string; name: string; source: string; original_name: string; status: string; created_at: string; gsd_cm: number
  image: { width: number; height: number; original_width: number; original_height: number; gsd_cm_assumed: number }
  grid: { tiles: number; crop_tiles: number; tile_px: number; stride_px: number }
  field: { vari_median: number; glcm_contrast_healthy_median: number; glcm_entropy_healthy_median: number; stressed_tiles: number; biotic_tiles: number; abiotic_tiles: number }
  hotspots: Hotspot[]
  route: { order: string[]; distance_m: number; points: [number, number][] }
  files: Record<'image' | 'overlay' | 'vari' | 'texture', string>
  method: string
}
export interface ScanRow {
  id: string; name: string; source: string; original_name: string; status: string; created_at: string; hotspots: number; photos: number; route_m: number | null
  gsd_cm: number; error: string | null; severity: Record<'High' | 'Medium' | 'Low', number>; open: number; area_m2: number
  field: Scan['field']; files: Scan['files']
}
export interface Stats {
  totals: { scans: number; hotspots: number; area_m2: number; route_m: number; photos: number; confirmed: number; awaiting_photo: number; open: number }
  by_day: { date: string; scans: number; hotspots: number }[]
  species: { name: string; count: number }[]
  severity: Record<'High' | 'Medium' | 'Low', number>
  states: Record<HState, number>
  queue: { scan_id: string; scan_name: string; hotspot: string; severity: 'High' | 'Medium' | 'Low'; area_m2: number; state: HState; status: string; route_stop?: number; score: number }[]
  points: { scan_id: string; scan_name: string; hotspot: string; vari_drop: number; glcm_contrast: number; severity: string; confirmed: boolean; label: string | null }[]
  per_scan: { id: string; name: string; biotic_tiles: number; abiotic_tiles: number; hotspots: number }[]
  activity: { t: string; kind: 'scan' | 'photo' | 'state'; scan_id: string; text: string }[]
  latest_scan_id: string | null
}
export interface Sample { name: string; url: string; kb: number }
export interface DataOverview {
  paths: Record<string, string>; counts: Record<string, number>; note: string
  labelled_examples: { photo_id: string; scan_id: string; hotspot: string; label: string; created_at: string; features: Record<string, number> }[]
}

export interface User { id: string; name: string; email: string }
async function j<T>(r: Response): Promise<T> {
  if (r.status === 401 && !r.url.includes('/auth/')) window.dispatchEvent(new Event('aero:unauth'))
  if (!r.ok) { let m = r.statusText; try { const b = await r.json(); m = typeof b.detail === 'string' ? b.detail : JSON.stringify(b.detail) } catch { /* keep */ } throw new Error(m) }
  return r.json()
}
const B = '/api/aeroscout'
const post = (path: string, body: unknown) => fetch(`${B}/auth/${path}`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) })
export const authApi = {
  me: () => fetch(`${B}/auth/me`).then((r) => (r.ok ? (r.json() as Promise<User>) : null)).catch(() => null),
  login: (email: string, password: string) => post('login', { email, password }).then(j<User>),
  register: (name: string, email: string, password: string) => post('register', { name, email, password }).then(j<User>),
  logout: () => post('logout', {}).then(() => undefined),
}
export const api = {
  samples: () => fetch(`${B}/samples`).then(j<Sample[]>),
  species: () => fetch(`${B}/species`).then(j<string[]>),
  scans: () => fetch(`${B}/scans`).then(j<ScanRow[]>),
  scan: (id: string) => fetch(`${B}/scans/${id}`).then(j<Scan>),
  data: () => fetch(`${B}/data`).then(j<DataOverview>),
  remove: (id: string) => fetch(`${B}/scans/${id}`, { method: 'DELETE' }).then(j<{ ok: boolean }>),
  stats: () => fetch(`${B}/stats`).then(j<Stats>),
  rename: (id: string, name: string) => fetch(`${B}/scans/${id}`, { method: 'PATCH', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ name }) }).then(j<Scan>),
  setState: (id: string, hs: string, state: HState, note = '') => fetch(`${B}/scans/${id}/hotspots/${hs}/state`, { method: 'PATCH', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ state, note }) }).then(j<Scan>),
  create: (f: { file?: File; sample?: string; name: string; gsd: number; start?: string }) => {
    const fd = new FormData(); if (f.file) fd.append('file', f.file); if (f.sample) fd.append('sample', f.sample)
    fd.append('name', f.name); fd.append('gsd_cm', String(f.gsd)); if (f.start) fd.append('start', f.start)
    return fetch(`${B}/scans`, { method: 'POST', body: fd }).then(j<Scan>)
  },
  photo: (scan: string, hs: string, file: File, species: string, note: string) => {
    const fd = new FormData(); fd.append('file', file); fd.append('species', species); fd.append('note', note)
    return fetch(`${B}/scans/${scan}/hotspots/${hs}/photo`, { method: 'POST', body: fd }).then(j<Scan>)
  },
}
