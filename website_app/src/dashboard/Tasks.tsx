import { useEffect, useState } from 'react'
import { api, type Scan } from '../api'
import HotspotCard from './HotspotCard'
import { useStore } from './store'
import { Empty, PageTitle } from './ui'

export default function Tasks() {
  const { scans } = useStore(); const [full, setFull] = useState<Record<string, Scan>>({})
  const ids = scans.filter((s) => s.hotspots > 0).map((s) => s.id).join(',')
  useEffect(() => { ids && Promise.all(ids.split(',').map((i) => api.scan(i))).then((l) => setFull(Object.fromEntries(l.map((s) => [s.id, s])))) }, [ids])
  const list = scans.filter((s) => s.hotspots > 0).map((s) => full[s.id]).filter(Boolean)
  const upd = (s: Scan) => setFull((f) => ({ ...f, [s.id]: s }))
  return (
    <>
      <PageTitle sub="For the scout in the field. Walk the stops in order, add a leaf photo, mark each one done.">Field tasks</PageTitle>
      {scans.length === 0 ? <Empty title="No fields yet" body="Analyse a drone photo and its hotspots show up here as a walking checklist."><a href="#/dashboard/scans" className="link-u font-medium">Analyse a field</a></Empty>
        : list.length === 0 ? <Empty title="No hotspots to visit" body="Every field looks healthy to the model." /> : (
        <div className="flex flex-col gap-12">
          {list.map((s) => {
            const done = s.hotspots.filter((h) => h.state === 'treated' || h.state === 'dismissed').length, total = s.hotspots.length
            return (
              <section key={s.id} aria-label={s.name}>
                <header className="mb-4 flex flex-wrap items-end justify-between gap-3">
                  <div><a href={`#/dashboard/scans/${s.id}`} className="link-u font-display text-2xl font-semibold">{s.name}</a><p className="label mono mt-1 text-muted">Route {s.route.distance_m} m · {s.route.order.join(' → ')}</p></div>
                  <div className="w-full max-w-xs"><p className="label mono mb-1 flex justify-between"><span>Done</span><span>{done} / {total}</span></p>
                    <div className="h-2 overflow-hidden rounded-ctl bg-line" role="progressbar" aria-valuenow={done} aria-valuemin={0} aria-valuemax={total}><div className="h-full bg-canopy" style={{ width: `${(done / total) * 100}%`, transition: 'width .6s cubic-bezier(.22,1,.36,1)' }} /></div></div>
                </header>
                <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">{[...s.hotspots].sort((a, b) => (a.route_stop ?? 99) - (b.route_stop ?? 99)).map((h) => <HotspotCard key={h.id} scan={s} h={h} onUpdate={upd} big />)}</div>
              </section>)
          })}
        </div>)}
    </>
  )
}
