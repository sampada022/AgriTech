import { Check, Copy, Download, FileJson, Pencil, Printer, Trash2 } from 'lucide-react'
import { useCallback, useEffect, useState } from 'react'
import { api, type Scan } from '../api'
import { Empty, fmtDate, PageTitle, Panel, Stat, StatGrid } from './ui'
import HotspotCard from './HotspotCard'
import ScanViewer from './ScanViewer'
import { useStore } from './store'

function legs(scan: Scan) {
  const { width: W, height: H, original_width: OW } = scan.image, f = (scan.gsd_cm / 100) * (OW / W), p = scan.route.points
  return p.slice(1).map((b, i) => ({ to: scan.route.order[i], m: Math.round(Math.hypot((b[0] - p[i][0]) * W, (b[1] - p[i][1]) * H) * f * 10) / 10 }))
}

export default function ScanDetail({ id }: { id: string }) {
  const { refresh } = useStore(); const [scan, setScan] = useState<Scan | null>(null), [err, setErr] = useState(''), [sel, setSel] = useState<string | null>(null)
  const [editing, setEditing] = useState(false), [name, setName] = useState(''), [copied, setCopied] = useState(false)
  const load = useCallback(() => api.scan(id).then((s) => { setScan(s); setName(s.name) }).catch((e) => setErr(e.message)), [id])
  useEffect(() => { setScan(null); setErr(''); load() }, [load])

  if (err) return <Empty title="Field not found" body={err}><a href="#/dashboard/scans" className="link-u font-medium">Back to fields</a></Empty>
  if (!scan) return <p className="text-muted">Loading…</p>
  const upd = (s: Scan) => { setScan(s); refresh() }
  const save = async () => { if (name.trim()) { upd(await api.rename(scan.id, name)); setEditing(false) } }
  const del = async () => { if (confirm(`Delete “${scan.name}” and all its photos?`)) { await api.remove(scan.id); await refresh(); location.hash = '#/dashboard/scans' } }
  const share = () => { navigator.clipboard?.writeText(location.href); setCopied(true); setTimeout(() => setCopied(false), 1800) }
  const lg = legs(scan), open = scan.hotspots.filter((h) => h.state === 'new' || h.state === 'visited').length
  const btn = 'label mono inline-flex items-center gap-2 rounded-ctl border border-line px-3 py-2 hover:border-ink'

  return (
    <>
      <p className="no-print label mono mb-3"><a href="#/dashboard/scans" className="link-u text-muted">Fields</a> <span className="text-muted">/</span> {scan.id}</p>
      <PageTitle sub={`${fmtDate(scan.created_at)} · ${scan.source === 'sample' ? 'sample ' : ''}${scan.original_name || ''} · ${scan.gsd_cm} cm per pixel`}
        action={<div className="no-print flex flex-wrap gap-2">
          <a className={btn} href={`/api/aeroscout/scans/${scan.id}/export.csv`}><Download size={14} strokeWidth={1.5} />CSV</a>
          <a className={btn} href={`/api/aeroscout/scans/${scan.id}`} target="_blank" rel="noreferrer"><FileJson size={14} strokeWidth={1.5} />JSON</a>
          <button className={btn} onClick={() => window.print()}><Printer size={14} strokeWidth={1.5} />Print report</button>
          <button className={btn} onClick={share}>{copied ? <Check size={14} strokeWidth={1.5} /> : <Copy size={14} strokeWidth={1.5} />}{copied ? 'Copied' : 'Copy link'}</button>
          <button className={`${btn} hover:!border-hot hover:text-hot`} onClick={del} aria-label="Delete field"><Trash2 size={14} strokeWidth={1.5} /></button></div>}>
        {editing ? (
          <span className="flex items-center gap-2"><input autoFocus value={name} onChange={(e) => setName(e.target.value)} onKeyDown={(e) => e.key === 'Enter' && save()} aria-label="Field name" className="rounded-ctl border border-ink bg-bg px-3 py-1 text-[inherit]" style={{ font: 'inherit', width: 'min(60vw, 520px)' }} />
            <button className={btn} onClick={save}>Save</button></span>
        ) : <span className="inline-flex items-center gap-3">{scan.name}<button aria-label="Rename field" onClick={() => setEditing(true)} className="no-print grid h-8 w-8 place-items-center rounded-ctl border border-line text-muted hover:border-ink hover:text-ink"><Pencil size={14} strokeWidth={1.5} /></button></span>}
      </PageTitle>

      <div className="grid gap-6 lg:grid-cols-12">
        <div className="lg:col-span-7"><ScanViewer scan={scan} selected={sel} onSelect={setSel} /></div>
        <div className="flex flex-col gap-6 lg:col-span-5">
          <StatGrid cols="grid-cols-3 sm:grid-cols-3 xl:grid-cols-3">
            <Stat label="Hotspots" value={scan.hotspots.length} accent />
            <Stat label="Still to visit" value={open} />
            <Stat label="Walk" value={scan.hotspots.length ? scan.route.distance_m : 0} unit="m" />
            <Stat label="Pest-like tiles" value={scan.field.biotic_tiles} />
            <Stat label="Drought-like tiles" value={scan.field.abiotic_tiles} />
            <Stat label="Tiles checked" value={scan.grid.crop_tiles} />
          </StatGrid>
          <Panel title="Walking route" sub="Shortest path that visits only the hotspots.">
            {scan.hotspots.length === 0 ? <p className="text-muted">No pest-like hotspots, so no route.</p> : (
              <ol className="mono text-sm"><li className="flex justify-between border-b border-line py-2"><span>Start (field corner)</span><span className="text-muted">0 m</span></li>
                {lg.map((l, i) => <li key={i} className="flex justify-between border-b border-line py-2"><span>Stop {i + 1} · hotspot {l.to}</span><span>+{l.m} m</span></li>)}
                <li className="flex justify-between pt-2 font-medium"><span>Total</span><span>{scan.route.distance_m} m</span></li></ol>)}
          </Panel>
        </div>
      </div>

      <h2 className="mt-12 mb-4 !text-2xl">Hotspots</h2>
      {scan.hotspots.length === 0 ? <Empty title="No pest-like hotspots found" body={scan.field.abiotic_tiles > 0 ? `${scan.field.abiotic_tiles} tiles look stressed but smooth, which points to drought or nutrients rather than insects.` : 'This field looks healthy to the model.'} /> : (
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {[...scan.hotspots].sort((a, b) => (a.route_stop ?? 99) - (b.route_stop ?? 99)).map((h) => <HotspotCard key={h.id} scan={scan} h={h} onUpdate={upd} selected={sel === h.id} onSelect={() => setSel(h.id)} />)}
        </div>)}
      <p className="label mono mt-10 max-w-3xl text-muted" style={{ textTransform: 'none' }}>{scan.method} Area and distance assume {scan.gsd_cm} cm per pixel. Species is chosen by the scout; there is no species classifier in this build.</p>
    </>
  )
}
