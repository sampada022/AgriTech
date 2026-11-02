import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from 'react'
import { api, type ScanRow, type Stats } from '../api'

interface Store { stats: Stats | null; scans: ScanRow[]; species: string[]; online: boolean | null; loading: boolean; refresh: () => Promise<void> }
const Ctx = createContext<Store | null>(null)
export const useStore = () => { const c = useContext(Ctx); if (!c) throw new Error('no store'); return c }

export function StoreProvider({ children }: { children: ReactNode }) {
  const [stats, setStats] = useState<Stats | null>(null), [scans, setScans] = useState<ScanRow[]>([]), [species, setSpecies] = useState<string[]>([])
  const [online, setOnline] = useState<boolean | null>(null), [loading, setLoading] = useState(true)
  const refresh = useCallback(async () => {
    try {
      const [st, sc, sp] = await Promise.all([api.stats(), api.scans(), api.species()])
      setStats(st); setScans(sc); setSpecies(sp); setOnline(true)
    } catch { setOnline(false) } finally { setLoading(false) }
  }, [])
  useEffect(() => {
    refresh()
    const t = setInterval(() => { if (!document.hidden) refresh() }, 20000)
    const vis = () => { if (!document.hidden) refresh() }
    document.addEventListener('visibilitychange', vis)
    return () => { clearInterval(t); document.removeEventListener('visibilitychange', vis) }
  }, [refresh])
  const v = useMemo(() => ({ stats, scans, species, online, loading, refresh }), [stats, scans, species, online, loading, refresh])
  return <Ctx.Provider value={v}>{children}</Ctx.Provider>
}
