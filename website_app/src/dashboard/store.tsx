import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from 'react'
import { fieldsApi, scansApi, modelApi, type FieldOut, type ScanOut, type ModelOut, type Tier } from '../api'

export interface FieldRow extends FieldOut { scan: ScanOut | null }

export interface Totals {
  fields: number; hotspots: number; open: number; tiers: Record<Tier, number>
  area_flagged_m2: number; route_m: number; running: number; failed: number
}

interface Store {
  fields: FieldRow[]; model: ModelOut | null; totals: Totals
  online: boolean | null; loading: boolean; refresh: () => Promise<void>
}
const Ctx = createContext<Store | null>(null)
export const useStore = () => { const c = useContext(Ctx); if (!c) throw new Error('no store'); return c }

function totalsOf(rows: FieldRow[]): Totals {
  const t: Totals = { fields: rows.length, hotspots: 0, open: 0, tiers: { red: 0, amber: 0, grey_blue: 0 }, area_flagged_m2: 0, route_m: 0, running: 0, failed: 0 }
  for (const row of rows) {
    const kpis = row.scan?.kpis
    if (row.scan?.status === 'running' || row.scan?.status === 'queued') t.running += 1
    if (row.scan?.status === 'failed') t.failed += 1
    if (!kpis) continue
    t.hotspots += kpis.hotspot_count
    t.open += (kpis.tier_counts.red ?? 0) + (kpis.tier_counts.amber ?? 0)
    for (const tier of ['red', 'amber', 'grey_blue'] as const) t.tiers[tier] += kpis.tier_counts[tier] ?? 0
    t.area_flagged_m2 += kpis.area_flagged_m2
    t.route_m += kpis.route_distance_m ?? 0
  }
  return t
}

export function StoreProvider({ children }: { children: ReactNode }) {
  const [fields, setFields] = useState<FieldRow[]>([])
  const [model, setModel] = useState<ModelOut | null>(null)
  const [online, setOnline] = useState<boolean | null>(null)
  const [loading, setLoading] = useState(true)
  const refresh = useCallback(async () => {
    try {
      const list = await fieldsApi.list()
      const scans = await Promise.all(
        list.map((f) => (f.latest_scan ? scansApi.get(f.latest_scan.id).catch(() => null) : Promise.resolve(null)))
      )
      setFields(list.map((f, i) => ({ ...f, scan: scans[i] })))
      modelApi.get().then(setModel).catch(() => {})
      setOnline(true)
    } catch { setOnline(false) } finally { setLoading(false) }
  }, [])
  useEffect(() => {
    refresh()
    const t = setInterval(() => { if (!document.hidden) refresh() }, 20000)
    const vis = () => { if (!document.hidden) refresh() }
    document.addEventListener('visibilitychange', vis)
    return () => { clearInterval(t); document.removeEventListener('visibilitychange', vis) }
  }, [refresh])
  const totals = useMemo(() => totalsOf(fields), [fields])
  const v = useMemo(() => ({ fields, model, totals, online, loading, refresh }), [fields, model, totals, online, loading, refresh])
  return <Ctx.Provider value={v}>{children}</Ctx.Provider>
}
