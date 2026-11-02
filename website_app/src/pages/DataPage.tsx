import { ArrowLeft, Copy, Download, Trash2 } from 'lucide-react'
import { useCallback, useEffect, useState } from 'react'
import { api, type DataOverview, type ScanRow } from '../api'

function Wrapper({ embedded, children }: { embedded: boolean; children: React.ReactNode }) {
  return embedded ? <div>{children}</div> : <main className="wrap pb-16 pt-32">{children}</main>
}
const copy = (t: string) => navigator.clipboard?.writeText(t)

export default function DataPage({ embedded = false }: { embedded?: boolean }) {
  const [data, setData] = useState<DataOverview | null>(null), [scans, setScans] = useState<ScanRow[]>([]), [err, setErr] = useState('')
  const load = useCallback(async () => { try { const [d, s] = await Promise.all([api.data(), api.scans()]); setData(d); setScans(s); setErr('') } catch (e) { setErr((e as Error).message) } }, [])
  useEffect(() => { load() }, [load])
  const del = async (id: string) => { if (confirm(`Delete ${id} and its files?`)) { await api.remove(id); load() } }
  return (
    <Wrapper embedded={embedded}>
      {!embedded && <a href="#top" onClick={() => { location.hash = '' }} className="link-u label mono mb-10"><ArrowLeft size={14} strokeWidth={1.5} />Back to site</a>}
      <p className="label mono mb-4 text-muted">DATA CONSOLE</p>
      <h1 className="!text-[clamp(1.75rem,3vw,2.5rem)]">Where your data lives</h1>
      {err && <p role="alert" className="mt-6 text-hot">Cannot reach the server ({err}). Start it with <span className="mono">uv run uvicorn backend.app.main:app --port 8000</span></p>}
      {data && (<>
        <dl className="mt-12 grid grid-cols-2 gap-px overflow-hidden rounded-card border border-line bg-line md:grid-cols-4">
          {Object.entries(data.counts).map(([k, v]) => <div key={k} className="bg-surface p-5"><dt className="label mono text-muted">{k.replace('_', ' ')}</dt><dd className="bignum !text-5xl">{v}</dd></div>)}
        </dl>

        <h2 className="mt-20 !text-3xl">Folders: where to put images</h2>
        <p className="mt-3 text-muted">Copy any <span className="mono">.jpg</span> or <span className="mono">.png</span> drone photo into <span className="mono">samples</span>, refresh, and it appears in the sample list on the site. Uploads made through the site are kept in <span className="mono">uploads</span>.</p>
        <ul className="mt-6 divide-y divide-line border-y border-line">
          {Object.entries(data.paths).map(([k, v]) => (
            <li key={k} className="flex flex-wrap items-center justify-between gap-3 py-4"><span className="label mono w-36 text-muted">{k.replace('_', ' ')}</span>
              <span className="mono min-w-0 flex-1 break-all text-sm">{v}</span>
              <button aria-label={`Copy ${k} path`} onClick={() => copy(v)} className="grid h-9 w-9 place-items-center rounded-ctl border border-line hover:border-ink"><Copy size={14} strokeWidth={1.5} /></button></li>
          ))}
        </ul>

        <h2 className="mt-20 !text-3xl">Scans</h2>
        {scans.length === 0 ? <p className="mt-4 text-muted">No scans yet. Run one from the “Try it” section.</p> : (
          <div className="mt-6 overflow-x-auto"><table className="w-full min-w-[760px] text-left text-sm">
            <thead><tr className="border-b border-ink">{['ID', 'Name', 'Source', 'When', 'Hotspots', 'Photos', 'Walk', ''].map((h) => <th key={h} className="label mono py-3 pr-4 font-normal text-muted">{h}</th>)}</tr></thead>
            <tbody>{scans.map((s) => (
              <tr key={s.id} className="border-b border-line">
                <td className="mono py-3 pr-4">{s.id}</td><td className="pr-4">{s.name}</td><td className="mono pr-4">{s.source}{s.original_name ? ` · ${s.original_name}` : ''}</td>
                <td className="mono pr-4">{new Date(s.created_at).toLocaleString()}</td><td className="mono pr-4">{s.hotspots}</td><td className="mono pr-4">{s.photos}</td><td className="mono pr-4">{s.route_m ?? '—'} m</td>
                <td className="flex gap-2 py-2"><a href={`/api/aeroscout/scans/${s.id}`} target="_blank" rel="noreferrer" className="label mono inline-flex items-center gap-1 rounded-ctl border border-line px-2 py-1 hover:border-ink"><Download size={12} strokeWidth={1.5} />JSON</a>
                  <a href={`/api/aeroscout/scans/${s.id}/files/overlay`} target="_blank" rel="noreferrer" className="label mono rounded-ctl border border-line px-2 py-1 hover:border-ink">Overlay</a>
                  <button aria-label={`Delete ${s.id}`} onClick={() => del(s.id)} className="grid h-7 w-7 place-items-center rounded-ctl border border-line hover:border-hot hover:text-hot"><Trash2 size={13} strokeWidth={1.5} /></button></td></tr>))}</tbody></table></div>
        )}

        <h2 className="mt-20 !text-3xl">Labelled examples</h2>
        <p className="mt-3 text-muted">{data.note}</p>
        {data.labelled_examples.length > 0 && (
          <div className="mt-6 overflow-x-auto"><table className="w-full min-w-[700px] text-left text-sm"><thead><tr className="border-b border-ink">{['Photo', 'Scan', 'Hotspot', 'Label', 'VARI', 'Contrast', 'Entropy'].map((h) => <th key={h} className="label mono py-3 pr-4 font-normal text-muted">{h}</th>)}</tr></thead>
            <tbody>{data.labelled_examples.map((e) => <tr key={e.photo_id} className="mono border-b border-line"><td className="py-3 pr-4">{e.photo_id}</td><td className="pr-4">{e.scan_id}</td><td className="pr-4">{e.hotspot}</td><td className="pr-4">{e.label}</td><td className="pr-4">{e.features.vari}</td><td className="pr-4">{e.features.glcm_contrast}</td><td>{e.features.glcm_entropy}</td></tr>)}</tbody></table></div>
        )}
        <p className="mt-16 flex flex-wrap gap-6 text-sm"><a className="link-u font-medium" href="/docs" target="_blank" rel="noreferrer">Interactive API docs (/docs)</a><a className="link-u font-medium" href="/api/aeroscout/data" target="_blank" rel="noreferrer">Raw overview JSON</a></p>
      </>)}
    </Wrapper>
  )
}
