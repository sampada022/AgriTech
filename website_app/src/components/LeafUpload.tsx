import { Camera, Loader2 } from 'lucide-react'
import { useRef, useState } from 'react'
import { api, type Hotspot, type Scan } from '../api'

export default function LeafUpload({ scan, h, species, onDone }: { scan: Scan; h: Hotspot; species: string[]; onDone: (s: Scan) => void }) {
  const [sp, setSp] = useState('Fall armyworm'), [busy, setBusy] = useState(false), [err, setErr] = useState('')
  const input = useRef<HTMLInputElement>(null)
  const send = async (f: File) => {
    setBusy(true); setErr('')
    try { onDone(await api.photo(scan.id, h.id, f, sp, '')) } catch (e) { setErr((e as Error).message) } finally { setBusy(false); if (input.current) input.current.value = '' }
  }
  return (
    <div className="mt-3 border-t border-line pt-3">
      <p className="label mono mb-2 text-muted">Leaf photo · scout names the pest</p>
      <div className="flex flex-wrap items-center gap-2">
        <select aria-label={`Species for hotspot ${h.id}`} value={sp} onChange={(e) => setSp(e.target.value)} className="rounded-ctl border border-line bg-bg px-2 py-2 text-sm">
          {species.map((s) => <option key={s}>{s}</option>)}
        </select>
        <input ref={input} type="file" accept="image/jpeg,image/png" capture="environment" hidden onChange={(e) => e.target.files?.[0] && send(e.target.files[0])} />
        <button onClick={() => input.current?.click()} disabled={busy} className="label mono inline-flex items-center gap-2 rounded-ctl border border-ink px-3 py-2 hover:bg-ink hover:text-bg">
          {busy ? <Loader2 size={14} className="animate-spin" strokeWidth={1.5} /> : <Camera size={14} strokeWidth={1.5} />}Add leaf photo
        </button>
      </div>
      {err && <p role="alert" className="mt-2 text-sm text-hot">{err}</p>}
      {h.photos.length > 0 && <ul className="mt-3 flex flex-wrap gap-2">{h.photos.map((p) => <li key={p.id}><a href={p.url} target="_blank" rel="noreferrer" title={p.species}><img src={p.url} alt={`Leaf photo from hotspot ${h.id}: ${p.species}`} className="h-12 w-12 rounded-ctl border border-line object-cover" /></a></li>)}</ul>}
    </div>
  )
}
