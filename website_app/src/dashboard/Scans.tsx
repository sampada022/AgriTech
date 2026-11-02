import { Search, Trash2 } from 'lucide-react'
import { useState } from 'react'
import { api } from '../api'
import NewScanForm from './NewScanForm'
import { useStore } from './store'
import { Empty, fmtDate, PageTitle, Panel, SeverityChip } from './ui'

export default function Scans() {
  const { scans, refresh } = useStore(); const [q, setQ] = useState('')
  const rows = scans.filter((s) => (s.name + s.id + s.original_name).toLowerCase().includes(q.toLowerCase()))
  const del = async (id: string, name: string) => { if (confirm(`Delete “${name}” and all its photos?`)) { await api.remove(id); refresh() } }
  return (
    <>
      <PageTitle sub="Every field photo you have analysed.">Fields</PageTitle>
      <div className="grid gap-6 lg:grid-cols-12">
        <Panel className="lg:col-span-4 lg:self-start" title="Analyse a new field"><NewScanForm onCreated={(s) => { location.hash = `#/dashboard/scans/${s.id}` }} /></Panel>
        <div className="lg:col-span-8">
          <label className="relative mb-4 block"><span className="sr-only">Search fields</span><Search aria-hidden size={16} strokeWidth={1.5} className="absolute left-3 top-1/2 -translate-y-1/2 text-muted" />
            <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search by name or ID" className="w-full rounded-ctl border border-line bg-surface py-2.5 pl-9 pr-3" /></label>
          {rows.length === 0 ? <Empty title={scans.length ? 'No field matches that search' : 'No fields yet'} body={scans.length ? undefined : 'Analyse your first photo on the left.'} /> : (
            <ul className="grid gap-4 sm:grid-cols-2">
              {rows.map((s) => (
                <li key={s.id} className="overflow-hidden rounded-card border border-line bg-surface">
                  <a href={`#/dashboard/scans/${s.id}`} className="block"><img src={s.files.overlay} alt={`${s.name} with hotspots marked`} loading="lazy" className="aspect-[16/10] w-full object-cover" /></a>
                  <div className="p-4">
                    <div className="flex items-start justify-between gap-2"><a href={`#/dashboard/scans/${s.id}`} className="link-u font-display text-lg font-semibold">{s.name}</a>
                      <button aria-label={`Delete ${s.name}`} onClick={() => del(s.id, s.name)} className="grid h-8 w-8 shrink-0 place-items-center rounded-ctl border border-line hover:border-hot hover:text-hot"><Trash2 size={14} strokeWidth={1.5} /></button></div>
                    <p className="label mono mt-1 text-muted">{s.id} · {fmtDate(s.created_at)}</p>
                    <p className="mono mt-3 text-sm">{s.hotspots} hotspot{s.hotspots === 1 ? '' : 's'} · {s.open} open · {s.photos} photo{s.photos === 1 ? '' : 's'}</p>
                    <div className="mt-2 flex flex-wrap gap-2">{(['High', 'Medium', 'Low'] as const).filter((k) => s.severity[k] > 0).map((k) => <span key={k} className="inline-flex items-center gap-1"><SeverityChip s={k} /><span className="mono text-sm">×{s.severity[k]}</span></span>)}</div>
                  </div></li>))}
            </ul>)}
        </div>
      </div>
    </>
  )
}
