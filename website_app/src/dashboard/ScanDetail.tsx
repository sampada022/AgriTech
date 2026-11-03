import { Check, Copy, Download, FileJson, Printer } from 'lucide-react'
import { useCallback, useEffect, useRef, useState } from 'react'
import { scansApi, type HotspotFeature, type RouteOut, type ScanOut } from '../api'
import { Empty, fmtDate, PageTitle, Panel, Stat, StatGrid } from './ui'
import HotspotCard from './HotspotCard'
import ScanViewer from './ScanViewer'
import { useStore } from './store'

export default function ScanDetail({ id }: { id: string }) {
  const { refresh } = useStore()
  const [scan, setScan] = useState<ScanOut | null>(null)
  const [hotspots, setHotspots] = useState<HotspotFeature[]>([])
  const [route, setRoute] = useState<RouteOut | null>(null)
  const [err, setErr] = useState(''), [sel, setSel] = useState<string | null>(null), [copied, setCopied] = useState(false)
  const timer = useRef<ReturnType<typeof setTimeout>>(undefined)

  const load = useCallback(() => {
    scansApi.get(id).then(async (s) => {
      setScan(s)
      if (s.status === 'queued' || s.status === 'running') {
        timer.current = setTimeout(load, 800)
      } else if (s.status === 'done') {
        const [hs, r] = await Promise.all([scansApi.hotspots(id), scansApi.getRoute(id).catch(() => null)])
        setHotspots(hs.features); setRoute(r)
      }
    }).catch((e) => setErr(e.message))
  }, [id])
  useEffect(() => { setScan(null); setHotspots([]); setRoute(null); setErr(''); load(); return () => clearTimeout(timer.current) }, [load])

  if (err) return <Empty title="Scan not found" body={err}><a href="#/dashboard/scans" className="link-u font-medium">Back to fields</a></Empty>
  if (!scan) return <p className="text-muted">Loading…</p>

  const upd = (f: HotspotFeature) => { setHotspots((hs) => hs.map((h) => (h.id === f.id ? f : h))); refresh() }
  const share = () => { navigator.clipboard?.writeText(location.href); setCopied(true); setTimeout(() => setCopied(false), 1800) }
  const btn = 'label mono inline-flex items-center gap-2 rounded-ctl border border-line px-3 py-2 hover:border-ink'

  if (scan.status === 'queued' || scan.status === 'running') {
    return (
      <>
        <PageTitle sub={`${scan.data_source_badge} · field ${scan.field_id}`}>Analysing…</PageTitle>
        <Panel title={scan.stage ? `Stage: ${scan.stage}` : 'Starting…'}>
          <div className="h-2 overflow-hidden rounded-ctl bg-line" role="progressbar" aria-valuenow={scan.progress} aria-valuemin={0} aria-valuemax={100}>
            <div className="h-full bg-hot" style={{ width: `${scan.progress}%`, transition: 'width .6s cubic-bezier(.22,1,.36,1)' }} />
          </div>
          <p className="label mono mt-2 text-muted">{scan.progress}%</p>
        </Panel>
      </>
    )
  }
  if (scan.status === 'failed') {
    return <Empty title="Analysis failed" body={scan.error?.message ?? 'Unknown error.'}><a href="#/dashboard/scans" className="link-u font-medium">Back to fields</a></Empty>
  }

  const open = hotspots.filter((h) => h.properties.status !== 'confirmed' && h.properties.status !== 'cleared').length
  const kpis = scan.kpis

  return (
    <>
      <p className="no-print label mono mb-3"><a href="#/dashboard/scans" className="link-u text-muted">Fields</a> <span className="text-muted">/</span> {scan.id}</p>
      <PageTitle sub={`${fmtDate(scan.created_at ?? '')} · ${scan.data_source_badge} · field ${scan.field_id}`}
        action={<div className="no-print flex flex-wrap gap-2">
          <a className={btn} href={scansApi.exportUrl(scan.id, 'csv')}><Download size={14} strokeWidth={1.5} />CSV</a>
          <a className={btn} href={scansApi.exportUrl(scan.id, 'geojson')}><FileJson size={14} strokeWidth={1.5} />GeoJSON</a>
          <button className={btn} onClick={() => window.print()}><Printer size={14} strokeWidth={1.5} />Print report</button>
          <button className={btn} onClick={share}>{copied ? <Check size={14} strokeWidth={1.5} /> : <Copy size={14} strokeWidth={1.5} />}{copied ? 'Copied' : 'Copy link'}</button></div>}>
        {scan.id}
      </PageTitle>

      <div className="grid gap-6 lg:grid-cols-12">
        <div className="lg:col-span-7"><ScanViewer scan={scan} hotspots={hotspots} selected={sel} onSelect={setSel} /></div>
        <div className="flex flex-col gap-6 lg:col-span-5">
          <StatGrid cols="grid-cols-3 sm:grid-cols-3 xl:grid-cols-3">
            <Stat label="Hotspots" value={hotspots.length} accent />
            <Stat label="Still to visit" value={open} />
            <Stat label="Walk" value={route ? Math.round(route.distance_m) : 0} unit="m" />
            <Stat label="Field area" value={kpis ? Math.round(kpis.field_area_m2) : 0} unit="m²" />
            <Stat label="Area flagged" value={kpis ? `${kpis.area_flagged_pct}` : 0} unit="%" />
            <Stat label="Walk saved" value={kpis?.walk_saved_pct ?? 0} unit="%" />
          </StatGrid>
          <Panel title="Walking route" sub="2-opt route to the red and amber hotspots.">
            {!route || route.stops.length === 0 ? <p className="text-muted">No hotspots above the sensitivity threshold, so no route.</p> : (
              <ol className="mono text-sm"><li className="flex justify-between border-b border-line py-2"><span>Start (south-west corner)</span><span className="text-muted">0 m</span></li>
                {route.stops.map((s) => <li key={s.hotspot_id} className="flex justify-between border-b border-line py-2"><span>Stop {s.order} · hotspot {s.hotspot_id}</span><span>+{Math.round(s.leg_distance_m)} m</span></li>)}
                <li className="flex justify-between pt-2 font-medium"><span>Total</span><span>{Math.round(route.distance_m)} m</span></li></ol>)}
          </Panel>
        </div>
      </div>

      <h2 className="mt-12 mb-4 !text-2xl">Hotspots</h2>
      {hotspots.length === 0 ? <Empty title="No hotspots found" body="This field looks healthy to the model." /> : (
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {[...hotspots].sort((a, b) => a.properties.rank - b.properties.rank).map((h) => (
            <HotspotCard key={h.id} h={h} routeStop={route?.stops.find((s) => s.hotspot_id === h.id)?.order} onUpdate={upd} selected={sel === h.id} onSelect={() => setSel(h.id)} />
          ))}
        </div>)}
      <p className="label mono mt-10 max-w-3xl text-muted" style={{ textTransform: 'none' }}>Classical computer vision (VARI/GLI + GLCM texture), not a trained pest classifier. Area assumes {scan.grid?.gsd_cm ?? '—'} cm per pixel.</p>
    </>
  )
}
