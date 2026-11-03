import { ArrowLeft, Download } from 'lucide-react'
import { useCallback, useEffect, useState } from 'react'
import { fieldsApi, type FieldOut } from '../api'

function Wrapper({ embedded, children }: { embedded: boolean; children: React.ReactNode }) {
  return embedded ? <div>{children}</div> : <main className="wrap pb-16 pt-32">{children}</main>
}

export default function DataPage({ embedded = false }: { embedded?: boolean }) {
  const [fields, setFields] = useState<FieldOut[]>([]), [err, setErr] = useState('')
  const load = useCallback(async () => { try { setFields(await fieldsApi.list()); setErr('') } catch (e) { setErr((e as Error).message) } }, [])
  useEffect(() => { load() }, [load])
  return (
    <Wrapper embedded={embedded}>
      {!embedded && <a href="#top" onClick={() => { location.hash = '' }} className="link-u label mono mb-10"><ArrowLeft size={14} strokeWidth={1.5} />Back to site</a>}
      <p className="label mono mb-4 text-muted">DATA CONSOLE</p>
      <h1 className="!text-[clamp(1.75rem,3vw,2.5rem)]">Where your data lives</h1>
      <p className="mt-3 max-w-2xl text-muted">One SQLite file and a folder of files on disk, served only through the API below — nothing here reads the filesystem directly from the browser.</p>
      {err && <p role="alert" className="mt-6 text-hot">Cannot reach the server ({err}). Start it with <span className="mono">cd apps/api && uvicorn app.main:app --port 8000</span></p>}

      <dl className="mt-12 grid grid-cols-2 gap-px overflow-hidden rounded-card border border-line bg-line md:grid-cols-4">
        <div className="bg-surface p-5"><dt className="label mono text-muted">fields</dt><dd className="bignum !text-5xl">{fields.length}</dd></div>
        <div className="bg-surface p-5"><dt className="label mono text-muted">scanned</dt><dd className="bignum !text-5xl">{fields.filter((f) => f.latest_scan?.status === 'done').length}</dd></div>
        <div className="bg-surface p-5"><dt className="label mono text-muted">hotspots</dt><dd className="bignum !text-5xl">{fields.reduce((n, f) => n + (f.latest_scan?.hotspot_count ?? 0), 0)}</dd></div>
        <div className="bg-surface p-5"><dt className="label mono text-muted">running</dt><dd className="bignum !text-5xl">{fields.filter((f) => f.latest_scan?.status === 'running' || f.latest_scan?.status === 'queued').length}</dd></div>
      </dl>

      <h2 className="mt-20 !text-3xl">Fields</h2>
      {fields.length === 0 ? <p className="mt-4 text-muted">No fields yet. Analyse one from the dashboard, or load a demo scenario.</p> : (
        <div className="mt-6 overflow-x-auto"><table className="w-full min-w-[760px] text-left text-sm">
          <thead><tr className="border-b border-ink">{['ID', 'Name', 'Source', 'When', 'Scan status', 'Hotspots', ''].map((h) => <th key={h} className="label mono py-3 pr-4 font-normal text-muted">{h}</th>)}</tr></thead>
          <tbody>{fields.map((f) => (
            <tr key={f.id} className="border-b border-line">
              <td className="mono py-3 pr-4">{f.id}</td><td className="pr-4">{f.name}</td><td className="mono pr-4">{f.data_source_badge}</td>
              <td className="mono pr-4">{f.created_at ? new Date(f.created_at).toLocaleString() : '—'}</td>
              <td className="mono pr-4">{f.latest_scan?.status ?? '—'}</td><td className="mono pr-4">{f.latest_scan?.hotspot_count ?? '—'}</td>
              <td className="py-2">{f.latest_scan && <a href={`/api/scans/${f.latest_scan.id}`} target="_blank" rel="noreferrer" className="label mono inline-flex items-center gap-1 rounded-ctl border border-line px-2 py-1 hover:border-ink"><Download size={12} strokeWidth={1.5} />JSON</a>}</td>
            </tr>))}</tbody></table></div>
      )}
      <p className="mt-16 flex flex-wrap gap-6 text-sm"><a className="link-u font-medium" href="/docs" target="_blank" rel="noreferrer">Interactive API docs (/docs)</a><a className="link-u font-medium" href="/api/fields" target="_blank" rel="noreferrer">Raw fields JSON</a></p>
    </Wrapper>
  )
}
