import { useEffect, useState } from 'react'
import { scansApi, type HotspotFeature, type RouteOut } from '../api'
import HotspotCard from './HotspotCard'
import { useStore } from './store'
import { Empty, PageTitle } from './ui'

interface Loaded { hotspots: HotspotFeature[]; route: RouteOut | null }

export default function Tasks() {
  const { fields } = useStore()
  const withHotspots = fields.filter((f) => f.latest_scan?.status === 'done' && (f.latest_scan?.hotspot_count ?? 0) > 0)
  const ids = withHotspots.map((f) => f.latest_scan!.id).join(',')
  const [data, setData] = useState<Record<string, Loaded>>({})
  useEffect(() => {
    if (!ids) { setData({}); return }
    Promise.all(ids.split(',').map((id) =>
      Promise.all([scansApi.hotspots(id), scansApi.getRoute(id).catch(() => null)]).then(([hs, route]) => [id, { hotspots: hs.features, route }] as const)
    )).then((entries) => setData(Object.fromEntries(entries)))
  }, [ids])
  const upd = (scanId: string, f: HotspotFeature) =>
    setData((d) => ({ ...d, [scanId]: { ...d[scanId], hotspots: d[scanId].hotspots.map((h) => (h.id === f.id ? f : h)) } }))

  return (
    <>
      <PageTitle sub="For the scout in the field. Walk the stops in order, add a leaf photo, confirm each one.">Field tasks</PageTitle>
      {fields.length === 0 ? <Empty title="No fields yet" body="Analyse a drone photo and its hotspots show up here as a walking checklist."><a href="#/dashboard/scans" className="link-u font-medium">Analyse a field</a></Empty>
        : withHotspots.length === 0 ? <Empty title="No hotspots to visit" body="Every field looks healthy to the model." /> : (
        <div className="flex flex-col gap-12">
          {withHotspots.map((f) => {
            const scanId = f.latest_scan!.id, d = data[scanId]
            if (!d) return <section key={f.id} aria-label={f.name}><p className="text-muted">Loading…</p></section>
            const done = d.hotspots.filter((h) => h.properties.status === 'confirmed' || h.properties.status === 'cleared').length, total = d.hotspots.length
            return (
              <section key={f.id} aria-label={f.name}>
                <header className="mb-4 flex flex-wrap items-end justify-between gap-3">
                  <div><a href={`#/dashboard/scans/${scanId}`} className="link-u font-display text-2xl font-semibold">{f.name}</a>
                    <p className="label mono mt-1 text-muted">Route {d.route ? Math.round(d.route.distance_m) : 0} m · {d.route?.stops.map((s) => s.hotspot_id).join(' → ') || 'no stops'}</p></div>
                  <div className="w-full max-w-xs"><p className="label mono mb-1 flex justify-between"><span>Done</span><span>{done} / {total}</span></p>
                    <div className="h-2 overflow-hidden rounded-ctl bg-line" role="progressbar" aria-valuenow={done} aria-valuemin={0} aria-valuemax={total}><div className="h-full bg-canopy" style={{ width: `${(done / total) * 100}%`, transition: 'width .6s cubic-bezier(.22,1,.36,1)' }} /></div></div>
                </header>
                <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
                  {[...d.hotspots].sort((a, b) => a.properties.rank - b.properties.rank).map((h) => (
                    <HotspotCard key={h.id} h={h} routeStop={d.route?.stops.find((s) => s.hotspot_id === h.id)?.order} onUpdate={(f) => upd(scanId, f)} big />
                  ))}
                </div>
              </section>) })}
        </div>)}
    </>
  )
}
