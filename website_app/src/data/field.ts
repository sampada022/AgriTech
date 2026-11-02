export const COLS = 12, ROWS = 8, CELL = 44, OX = 36, OY = 28
export const VB_W = 600, VB_H = 460
export type Cls = 'ok' | 'abiotic' | 'pest'
export interface Tile { id: string; c: number; r: number; x: number; y: number; w: number; h: number; cls: Cls; vari: number; rgb: number }
export interface Hotspot {
  id: string; name: string; tiles: string[]; cx: number; cy: number
  area: string; severity: 'High' | 'Medium' | 'Low'; status: string; confirmed: boolean
}

const h = (n: number) => { const s = Math.sin(n * 127.1 + 311.7) * 43758.5453; return s - Math.floor(s) }
const key = (c: number, r: number) => `${c},${r}`

const PEST_SETS: Record<string, [number, number][]> = {
  A: [[3, 1], [3, 2], [4, 2]],
  B: [[8, 3], [8, 4], [9, 3]],
  C: [[6, 5], [6, 6]],
}
const ABIOTIC_SETS: [number, number][][] = [
  [[10, 1], [10, 2], [11, 1]],
  [[1, 4], [1, 5], [2, 5]],
]
const pestKeys = new Map<string, string>()
Object.entries(PEST_SETS).forEach(([k, v]) => v.forEach(([c, r]) => pestKeys.set(key(c, r), k)))
const abioticKeys = new Set(ABIOTIC_SETS.flat().map(([c, r]) => key(c, r)))

export const tiles: Tile[] = []
for (let r = 0; r < ROWS; r++) for (let c = 0; c < COLS; c++) {
  const i = r * COLS + c, k = key(c, r)
  const jx = (h(i) - .5) * 4, jy = (h(i + 99) - .5) * 4
  const w = CELL - 4 - h(i + 7) * 3, hh = CELL - 4 - h(i + 13) * 3
  const cls: Cls = pestKeys.has(k) ? 'pest' : abioticKeys.has(k) ? 'abiotic' : 'ok'
  const vari = cls === 'pest' ? .62 + h(i + 5) * .33 : cls === 'abiotic' ? .45 + h(i + 5) * .15 : .06 + h(i + 5) * .2
  tiles.push({ id: k, c, r, x: OX + c * CELL + 2 + jx, y: OY + r * CELL + 2 + jy, w, h: hh, cls, vari, rgb: h(i + 21) })
}

const center = (ids: string[]) => {
  const ts = ids.map((id) => tiles.find((t) => t.id === id)!)
  return { cx: ts.reduce((a, t) => a + t.x + t.w / 2, 0) / ts.length, cy: ts.reduce((a, t) => a + t.y + t.h / 2, 0) / ts.length }
}
const ids = (k: string) => PEST_SETS[k].map(([c, r]) => key(c, r))

// All areas are SAMPLE DATA for the demo.
export const hotspots: Hotspot[] = [
  { id: 'A', name: 'Hotspot A', tiles: ids('A'), ...center(ids('A')), area: '0.31 ha', severity: 'Medium', status: 'Confirmed: Fall armyworm', confirmed: true },
  { id: 'B', name: 'Hotspot B', tiles: ids('B'), ...center(ids('B')), area: '0.42 ha', severity: 'High', status: 'Awaiting photo', confirmed: false },
  { id: 'C', name: 'Hotspot C', tiles: ids('C'), ...center(ids('C')), area: '0.19 ha', severity: 'Low', status: 'Awaiting photo', confirmed: false },
]
export const abioticPatches = ABIOTIC_SETS.map((set) => {
  const i = set.map(([c, r]) => key(c, r)); return { tiles: i, ...center(i) }
})
export const farmhouse = { x: 40, y: 418 }
export const route: [number, number][] = [[farmhouse.x, farmhouse.y], [hotspots[2].cx, hotspots[2].cy], [hotspots[1].cx, hotspots[1].cy], [hotspots[0].cx, hotspots[0].cy]]
export const routePath = 'M ' + route.map(([x, y]) => `${x.toFixed(1)} ${y.toFixed(1)}`).join(' L ')

// Map coordinates near Mandya (sample framing)
const LAT0 = 12.5223, LON0 = 76.8970
export const coordsAt = (nx: number, ny: number) => {
  const lat = LAT0 + (0.5 - ny) * 0.0036, lon = LON0 + (nx - 0.5) * 0.0048
  return `${lat.toFixed(4)}° N, ${lon.toFixed(4)}° E`
}
