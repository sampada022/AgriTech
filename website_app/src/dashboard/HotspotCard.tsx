import type { HState, Hotspot, Scan } from '../api'
import { api } from '../api'
import LeafUpload from '../components/LeafUpload'
import { useState } from 'react'
import { useStore } from './store'
import { SeverityChip, STATE_META, StateChip } from './ui'

const ORDER: HState[] = ['new', 'visited', 'treated', 'dismissed']

export default function HotspotCard({ scan, h, onUpdate, selected, onSelect, big }: { scan: Scan; h: Hotspot; onUpdate: (s: Scan) => void; selected?: boolean; onSelect?: () => void; big?: boolean }) {
  const { species, refresh } = useStore(); const [busy, setBusy] = useState(false), [err, setErr] = useState('')
  const set = async (st: HState) => {
    setBusy(true); setErr('')
    try { onUpdate(await api.setState(scan.id, h.id, st)); refresh() } catch (e) { setErr((e as Error).message) } finally { setBusy(false) }
  }
  const done = h.state === 'treated' || h.state === 'dismissed'
  return (
    <article className={`rounded-card border p-5 ${selected ? 'border-ink' : 'border-line'} ${done ? 'opacity-70' : ''} bg-surface`} aria-label={`Hotspot ${h.id}`}>
      <header className="flex flex-wrap items-center justify-between gap-3">
        <button onClick={onSelect} className="text-left"><span className="label mono text-muted">Stop {h.route_stop ?? '–'}</span>
          <h3 className="font-display !text-xl !font-semibold">Hotspot {h.id}</h3></button>
        <div className="flex flex-wrap items-center gap-2"><SeverityChip s={h.severity} /><StateChip s={h.state} /></div>
      </header>
      <p className={`mt-2 label mono ${h.status.startsWith('Confirmed') ? 'text-canopy' : 'text-muted'}`}>{h.status}</p>
      <dl className="mono mt-3 grid grid-cols-3 gap-2 text-sm">
        <div><dt className="label text-muted">Area</dt><dd>{h.area_m2} m²</dd></div>
        <div><dt className="label text-muted">VARI drop</dt><dd>{h.vari_drop}</dd></div>
        <div><dt className="label text-muted">Contrast</dt><dd>{h.glcm_contrast}</dd></div>
      </dl>
      <div className={`mt-4 flex flex-wrap gap-2 ${big ? 'sm:gap-3' : ''}`} role="group" aria-label={`Set state of hotspot ${h.id}`}>
        {ORDER.map((st) => { const { label, Icon } = STATE_META[st]; const on = h.state === st
          return <button key={st} disabled={busy || on} aria-pressed={on} onClick={() => set(st)}
            className={`label mono inline-flex items-center gap-2 rounded-ctl border ${big ? 'px-4 py-3' : 'px-3 py-2'} ${on ? 'border-ink bg-ink text-bg' : 'border-line hover:border-ink'}`}><Icon aria-hidden size={14} strokeWidth={1.5} />{label}</button> })}
      </div>
      {err && <p role="alert" className="mt-2 text-sm text-hot">{err}</p>}
      <LeafUpload scan={scan} h={h} species={species} onDone={(s) => { onUpdate(s); refresh() }} />
    </article>
  )
}
