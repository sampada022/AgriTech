import { Upload } from 'lucide-react'
import { useRef, useState } from 'react'
import { demoApi, fieldsApi } from '../api'
import { Button } from '../components/Button'
import { useStore } from './store'

// No real GPS on a plain photo upload, so the field is centred here (same convention the farmer
// portal and the engine's own simulator use) and sized from the cm-per-pixel you enter.
const CENTRE_LAT = 12.5231, CENTRE_LON = 76.8951
const M_PER_DEG_LON = 111_320, M_PER_DEG_LAT = 110_574

function boundsFromCentre(widthM: number, heightM: number) {
  const halfLat = heightM / 2 / M_PER_DEG_LAT
  const halfLon = widthM / 2 / (M_PER_DEG_LON * Math.cos((CENTRE_LAT * Math.PI) / 180))
  return { sw_lat: CENTRE_LAT - halfLat, sw_lon: CENTRE_LON - halfLon, ne_lat: CENTRE_LAT + halfLat, ne_lon: CENTRE_LON + halfLon }
}
function imageSize(file: File): Promise<{ width: number; height: number }> {
  return new Promise((resolve, reject) => {
    const img = new Image()
    img.onload = () => resolve({ width: img.naturalWidth, height: img.naturalHeight })
    img.onerror = reject
    img.src = URL.createObjectURL(file)
  })
}

export default function NewScanForm({ onCreated }: { onCreated: (scanId: string) => void }) {
  const { online, refresh } = useStore()
  const [file, setFile] = useState<File | null>(null)
  const [name, setName] = useState(''), [crop, setCrop] = useState(''), [gsd, setGsd] = useState('3.0')
  const [busy, setBusy] = useState(false), [err, setErr] = useState(''), [drag, setDrag] = useState(false)
  const input = useRef<HTMLInputElement>(null)

  const run = async () => {
    if (!file) return
    setBusy(true); setErr('')
    try {
      const { width, height } = await imageSize(file)
      const gsdCm = parseFloat(gsd) || 3
      const bounds = boundsFromCentre((width * gsdCm) / 100, (height * gsdCm) / 100)
      const field = await fieldsApi.create({ image: file, name: name || file.name, crop, data_source: 'stand_in', ...bounds })
      const scan = await fieldsApi.startScan(field.id)
      setFile(null); setName(''); await refresh(); onCreated(scan.id)
    } catch (e) { setErr((e as Error).message) } finally { setBusy(false) }
  }
  const demo = async (scenario: 'healthy' | 'pest' | 'mixed') => {
    setBusy(true); setErr('')
    try { const d = await demoApi.load(scenario); await refresh(); onCreated(d.scan_id) }
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
        <button onClick={() => input.current?.click()} className="link-u mt-1 text-sm font-medium">or browse (.jpg, .png, up to 50 MB)</button>
      </div>
      <label className="mt-4 block text-sm">Name <span className="text-muted">(optional)</span><input value={name} onChange={(e) => setName(e.target.value)} placeholder="e.g. Plot 7, north" className={field} /></label>
      <div className="mt-4 grid grid-cols-2 gap-3">
        <label className="block text-sm">Crop<input value={crop} onChange={(e) => setCrop(e.target.value)} placeholder="e.g. Paddy" className={field} /></label>
        <label className="block text-sm">cm per pixel<input value={gsd} onChange={(e) => setGsd(e.target.value)} inputMode="decimal" className={`mono ${field}`} /></label>
      </div>
      <p className="mt-1 text-xs text-muted">No GPS on a plain photo, so the field is placed at a fixed demo location, sized from cm-per-pixel. About 3 at 35 m altitude.</p>
      <Button onClick={run} disabled={busy || online === false || !file} className="mt-5 w-full">{busy ? 'Analysing…' : 'Analyse field'}</Button>

      <div className="mt-6 border-t border-line pt-4">
        <p className="label mono mb-2 text-muted">…or load a demo scenario</p>
        <div className="flex flex-wrap gap-2">
          {(['healthy', 'pest', 'mixed'] as const).map((s) => (
            <button key={s} disabled={busy || online === false} onClick={() => demo(s)} className="label mono rounded-ctl border border-line px-3 py-2 capitalize hover:border-ink">{s}</button>
          ))}
        </div>
      </div>
      {err && <p role="alert" className="mt-3 text-sm text-hot">{err}</p>}
    </div>
  )
}
