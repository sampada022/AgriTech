import { Download, Search } from 'lucide-react'
import { useState } from 'react'
import NewScanForm from './NewScanForm'
import { useStore } from './store'
import { Empty, fmtDate, PageTitle, Panel, TierChip } from './ui'

export default function Scans() {
  const { fields } = useStore(); const [q, setQ] = useState('')
  const rows = fields.filter((f) => (f.name + f.id).toLowerCase().includes(q.toLowerCase()))
  return (
    <>
      <PageTitle sub="Every field you have analysed.">Fields</PageTitle>
      <div className="grid gap-6 lg:grid-cols-12">
        <Panel className="lg:col-span-4 lg:self-start" title="Analyse a field"><NewScanForm onCreated={(id) => { location.hash = `#/dashboard/scans/${id}` }} /></Panel>
        <div className="lg:col-span-8">
          <label className="relative mb-4 block"><span className="sr-only">Search fields</span><Search aria-hidden size={16} strokeWidth={1.5} className="absolute left-3 top-1/2 -translate-y-1/2 text-muted" />
            <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search by name or ID" className="w-full rounded-ctl border border-line bg-surface py-2.5 pl-9 pr-3" /></label>
          {rows.length === 0 ? <Empty title={fields.length ? 'No field matches that search' : 'No fields yet'} body={fields.length ? undefined : 'Analyse your first photo on the left.'} /> : (
            <ul className="grid gap-4 sm:grid-cols-2">
              {rows.map((f) => {
                const scanId = f.latest_scan?.id, tiers = f.latest_scan?.tier_counts ?? {}
                const href = scanId ? `#/dashboard/scans/${scanId}` : undefined
                return (
                  <li key={f.id} className="overflow-hidden rounded-card border border-line bg-surface">
                    {href && f.thumbnail_url ? <a href={href} className="block"><img src={f.thumbnail_url} alt={`${f.name} thumbnail`} loading="lazy" className="aspect-[16/10] w-full object-cover" /></a>
                      : <div className="aspect-[16/10] w-full bg-mapbg" />}
                    <div className="p-4">
                      <a href={href ?? '#'} className="link-u font-display text-lg font-semibold">{f.name}</a>
                      <p className="label mono mt-1 text-muted">{f.id} · {f.created_at ? fmtDate(f.created_at) : '—'} · {f.data_source_badge}</p>
                      <p className="mono mt-3 text-sm">{f.latest_scan ? `${f.latest_scan.status} · ${f.latest_scan.hotspot_count ?? 0} hotspot${f.latest_scan.hotspot_count === 1 ? '' : 's'}` : 'No scan yet'}</p>
                      <div className="mt-2 flex flex-wrap items-center justify-between gap-2">
                        <div className="flex flex-wrap gap-2">{(['red', 'amber', 'grey_blue'] as const).filter((k) => (tiers[k] ?? 0) > 0).map((k) => <span key={k} className="inline-flex items-center gap-1"><TierChip s={k} /><span className="mono text-sm">×{tiers[k]}</span></span>)}</div>
                        {scanId && f.latest_scan?.status === 'done' && (
                          <a href={`/api/scans/${scanId}/report`} target="_blank" rel="noreferrer"
                            className="label mono inline-flex items-center gap-1.5 rounded-ctl border border-line px-2.5 py-1.5 text-xs hover:bg-bg">
                            <Download size={13} strokeWidth={1.5} />PDF report
                          </a>
                        )}
                      </div>
                    </div></li>) })}
            </ul>)}
        </div>
      </div>
    </>
  )
}
