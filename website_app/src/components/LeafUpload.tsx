import { Camera, Loader2 } from 'lucide-react'
import { useRef, useState } from 'react'
import { hotspotsApi, LABEL_NAMES, type HotspotFeature, type Label, type ObservationOut } from '../api'

export default function LeafUpload({ h, onConfirmed }: { h: HotspotFeature; onConfirmed: (f: HotspotFeature) => void }) {
  const [obs, setObs] = useState<ObservationOut | null>(null)
  const [busy, setBusy] = useState(false), [err, setErr] = useState('')
  const input = useRef<HTMLInputElement>(null)

  const send = async (f: File) => {
    setBusy(true); setErr('')
    try { setObs(await hotspotsApi.addObservation(h.id, f, 'en')) }
    catch (e) { setErr((e as Error).message) } finally { setBusy(false); if (input.current) input.current.value = '' }
  }
  const confirm = async (label: Label) => {
    if (!obs) return
    setBusy(true); setErr('')
    try {
      await hotspotsApi.confirm(obs.id, label)
      const updated = await hotspotsApi.get(h.id)
      onConfirmed(updated.feature)
      setObs(null)
    } catch (e) { setErr((e as Error).message) } finally { setBusy(false) }
  }

  if (obs) {
    const diag = obs.diagnosis
    return (
      <div className="mt-3 border-t border-line pt-3">
        {obs.photo_url && <img src={obs.photo_url} alt={`Leaf photo from hotspot ${h.id}`} className="h-24 w-24 rounded-ctl border border-line object-cover" />}
        {diag?.result ? (
          <div className="mt-2">
            <p className="label mono text-muted">Diagnosis · {diag.source === 'canned' ? 'demo reply' : diag.source}</p>
            <ul className="mt-1 flex flex-col gap-1">{diag.result.candidates.slice(0, 3).map((c) => (
              <li key={c.name} className="flex items-center justify-between text-sm"><span>{c.name}</span><span className="mono text-muted">{Math.round(c.probability * 100)}%</span></li>
            ))}</ul>
          </div>
        ) : diag?.message && <p className="mt-2 text-sm text-muted">{diag.message}</p>}
        <p className="label mono mt-3 text-muted">Confirm what you found</p>
        <div className="mt-2 flex flex-wrap gap-2">
          {(diag?.label_options ?? []).map((o) => (
            <button key={o.label} disabled={busy} onClick={() => confirm(o.label)}
              className={`label mono inline-flex items-center gap-2 rounded-ctl border px-3 py-2 hover:border-ink ${diag?.suggested_label === o.label ? 'border-ink bg-ink text-bg' : 'border-line'}`}>{o.name}</button>
          ))}
        </div>
        {err && <p role="alert" className="mt-2 text-sm text-hot">{err}</p>}
      </div>
    )
  }

  return (
    <div className="mt-3 border-t border-line pt-3">
      <p className="label mono mb-2 text-muted">Leaf photo · AI-assisted diagnosis</p>
      <input ref={input} type="file" accept="image/jpeg,image/png,image/webp" capture="environment" hidden onChange={(e) => e.target.files?.[0] && send(e.target.files[0])} />
      <button onClick={() => input.current?.click()} disabled={busy} className="label mono inline-flex items-center gap-2 rounded-ctl border border-ink px-3 py-2 hover:bg-ink hover:text-bg">
        {busy ? <Loader2 size={14} className="animate-spin" strokeWidth={1.5} /> : <Camera size={14} strokeWidth={1.5} />}Add leaf photo
      </button>
      {h.properties.label && <p className="label mono mt-2 text-canopy">Already confirmed: {LABEL_NAMES[h.properties.label]}</p>}
      {err && <p role="alert" className="mt-2 text-sm text-hot">{err}</p>}
    </div>
  )
}
