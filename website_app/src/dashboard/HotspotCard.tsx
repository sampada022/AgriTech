import { hotspotsApi, LABEL_NAMES, type HotspotFeature, type HotspotStatus } from '../api'
import LeafUpload from '../components/LeafUpload'
import { useState } from 'react'
import { useStore } from './store'
import { STATUS_META, TierChip, StatusChip } from './ui'

const QUICK: HotspotStatus[] = ['detected', 'assigned', 'inspected']

export default function HotspotCard({ h, routeStop, onUpdate, selected, onSelect, big }: {
  h: HotspotFeature; routeStop?: number; onUpdate: (f: HotspotFeature) => void; selected?: boolean; onSelect?: () => void; big?: boolean
}) {
  const { refresh } = useStore(); const [busy, setBusy] = useState(false), [err, setErr] = useState('')
  const p = h.properties
  const set = async (st: HotspotStatus) => {
    setBusy(true); setErr('')
    try { onUpdate(await hotspotsApi.patch(h.id, { status: st })); refresh() } catch (e) { setErr((e as Error).message) } finally { setBusy(false) }
  }
  const done = p.status === 'confirmed' || p.status === 'cleared'
  const statusLine = p.label ? `Confirmed: ${LABEL_NAMES[p.label]}` : p.abiotic_hint_text ?? 'Awaiting ground check'
  return (
    <article className={`rounded-card border p-5 ${selected ? 'border-ink' : 'border-line'} ${done ? 'opacity-70' : ''} bg-surface`} aria-label={`Hotspot ${h.id}`}>
      <header className="flex flex-wrap items-center justify-between gap-3">
        <button onClick={onSelect} className="text-left"><span className="label mono text-muted">Stop {routeStop ?? '–'}</span>
          <h3 className="font-display !text-xl !font-semibold">Hotspot {h.id}</h3></button>
        <div className="flex flex-wrap items-center gap-2"><TierChip s={p.tier} /><StatusChip s={p.status} /></div>
      </header>
      <p className={`mt-2 label mono ${p.label ? 'text-canopy' : 'text-muted'}`}>{statusLine}</p>
      <dl className="mono mt-3 grid grid-cols-3 gap-2 text-sm">
        <div><dt className="label text-muted">Area</dt><dd>{p.area_m2} m²</dd></div>
        <div><dt className="label text-muted">Biotic score</dt><dd>{p.biotic_score}</dd></div>
        <div><dt className="label text-muted">Confidence</dt><dd>{p.confidence}</dd></div>
      </dl>
      <div className={`mt-4 flex flex-wrap gap-2 ${big ? 'sm:gap-3' : ''}`} role="group" aria-label={`Set status of hotspot ${h.id}`}>
        {QUICK.map((st) => { const { label, Icon } = STATUS_META[st]; const on = p.status === st
          return <button key={st} disabled={busy || on} aria-pressed={on} onClick={() => set(st)}
            className={`label mono inline-flex items-center gap-2 rounded-ctl border ${big ? 'px-4 py-3' : 'px-3 py-2'} ${on ? 'border-ink bg-ink text-bg' : 'border-line hover:border-ink'}`}><Icon aria-hidden size={14} strokeWidth={1.5} />{label}</button> })}
      </div>
      {err && <p role="alert" className="mt-2 text-sm text-hot">{err}</p>}
      <LeafUpload h={h} onConfirmed={(f) => { onUpdate(f); refresh() }} />
    </article>
  )
}
