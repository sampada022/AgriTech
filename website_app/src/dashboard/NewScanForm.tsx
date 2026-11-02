import { Upload } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import { api, type Sample, type Scan } from '../api'
import { Button } from '../components/Button'
import { useStore } from './store'

export default function NewScanForm({ onCreated }: { onCreated: (s: Scan) => void }) {
  const { online, refresh } = useStore()
  const [samples, setSamples] = useState<Sample[]>([]), [pick, setPick] = useState(''), [file, setFile] = useState<File | null>(null)
  const [name, setName] = useState(''), [gsd, setGsd] = useState('1.0'), [start, setStart] = useState('bottom-left'), [busy, setBusy] = useState(false), [err, setErr] = useState(''), [drag, setDrag] = useState(false)
  const input = useRef<HTMLInputElement>(null)
  useEffect(() => { api.samples().then((s) => { setSamples(s); setPick((p) => p || s[0]?.name || '') }).catch(() => {}) }, [])
  const run = async () => {
    setBusy(true); setErr('')
    try { const s = await api.create({ file: file ?? undefined, sample: file ? undefined : pick, name, gsd: parseFloat(gsd) || 1, start }); setFile(null); setName(''); await refresh(); onCreated(s) }
    catch (e) { setErr((e as Error).message) } finally { setBusy(false) }
  }
  const field = 'mt-1 w-full rounded-ctl border border-line bg-bg px-3 py-2'
  return (
    <div>
      <div onDragOver={(e) => { e.preventDefault(); setDrag(true) }} onDragLeave={() => setDrag(false)} onDrop={(e) => { e.preventDefault(); setDrag(false); const f = e.dataTransfer.files[0]; if (f) setFile(f) }}
        className={`rounded-ctl border border-dashed p-5 text-center ${drag ? 'border-hot' : 'border-line'}`}>
        <input ref={input} type="file" accept="image/jpeg,image/png" hidden onChange={(e) => setFile(e.target.files?.[0] ?? null)} />
        <Upload aria-hidden className="mx-auto text-muted" strokeWidth={1.5} />
        <p className="mt-2 text-sm">{file ? <span className="mono">{file.name}</span> : 'Drop a drone photo here'}</p>
        <button onClick={() => input.current?.click()} className="link-u mt-1 text-sm font-medium">or browse (.jpg, .png, up to 30 MB)</button>
      </div>
      {!file && samples.length > 0 && <label className="mt-4 block text-sm">…or a sample field<select value={pick} onChange={(e) => setPick(e.target.value)} className={field}>{samples.map((s) => <option key={s.name}>{s.name}</option>)}</select></label>}
      <label className="mt-4 block text-sm">Name <span className="text-muted">(optional)</span><input value={name} onChange={(e) => setName(e.target.value)} placeholder="e.g. Plot 7, north" className={field} /></label>
      <div className="mt-4 grid grid-cols-2 gap-3">
        <label className="block text-sm">cm per pixel<input value={gsd} onChange={(e) => setGsd(e.target.value)} inputMode="decimal" className={`mono ${field}`} /></label>
        <label className="block text-sm">Walk starts at<select value={start} onChange={(e) => setStart(e.target.value)} className={field}>
          {[['bottom-left', 'Bottom left'], ['bottom-right', 'Bottom right'], ['top-left', 'Top left'], ['top-right', 'Top right']].map(([v, l]) => <option key={v} value={v}>{l}</option>)}</select></label>
      </div>
      <p className="mt-1 text-xs text-muted">cm per pixel sets area and walking distance. About 1 at 35 m. Unsure? Leave 1.0.</p>
      <Button onClick={run} disabled={busy || online === false || (!file && !pick)} className="mt-5 w-full">{busy ? 'Analysing…' : 'Analyse field'}</Button>
      {err && <p role="alert" className="mt-3 text-sm text-hot">{err}</p>}
    </div>
  )
}
