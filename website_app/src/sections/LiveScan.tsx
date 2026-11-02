import { AlertTriangle, Check, Upload } from 'lucide-react'
import { useCallback, useEffect, useRef, useState } from 'react'
import { api, type Hotspot, type Sample, type Scan, type ScanRow } from '../api'
import { Button, TextLink } from '../components/Button'
import LeafUpload from '../components/LeafUpload'
import { ButtonLink } from '../components/Button'
import { useAuth } from '../hooks/auth'
import Eyebrow from '../components/Eyebrow'
import { Reveal } from '../components/Reveal'

const LAYERS = [['image', 'Photo'], ['overlay', 'Hotspots'], ['vari', 'VARI'], ['texture', 'Texture']] as const
type Layer = (typeof LAYERS)[number][0]
const sev = { High: 'text-hot', Medium: 'text-ink', Low: 'text-muted' }

export default function LiveScan() {
  const { user } = useAuth()
  const [online, setOnline] = useState<boolean | null>(null)
  const [samples, setSamples] = useState<Sample[]>([]), [species, setSpecies] = useState<string[]>([]), [history, setHistory] = useState<ScanRow[]>([])
  const [scan, setScan] = useState<Scan | null>(null), [layer, setLayer] = useState<Layer>('overlay'), [sel, setSel] = useState<string | null>(null)
  const [busy, setBusy] = useState(false), [err, setErr] = useState(''), [file, setFile] = useState<File | null>(null), [pick, setPick] = useState(''), [name, setName] = useState(''), [gsd, setGsd] = useState('1.0'), [drag, setDrag] = useState(false)
  const input = useRef<HTMLInputElement>(null)

  const refresh = useCallback(async () => {
    try {
      const [s, h, sp] = await Promise.all([api.samples(), api.scans(), api.species()])
      setSamples(s); setHistory(h); setSpecies(sp); setOnline(true); setPick((p) => p || s[0]?.name || '')
      return h
    } catch { setOnline(false); return [] }
  }, [])
  useEffect(() => { if (!user) return; refresh().then((h) => { if (h[0]) api.scan(h[0].id).then(setScan).catch(() => {}) }) }, [refresh, user])

  const run = async () => {
    setBusy(true); setErr('')
    try {
      const s = await api.create({ file: file ?? undefined, sample: file ? undefined : pick, name, gsd: parseFloat(gsd) || 1 })
      setScan(s); setLayer('overlay'); setSel(null); setFile(null); setName(''); refresh()
    } catch (e) { setErr((e as Error).message) } finally { setBusy(false) }
  }
  const updated = (s: Scan) => { setScan(s); refresh() }
  const selected = scan?.hotspots.find((h) => h.id === sel)

  return (
    <section id="try" aria-labelledby="try-h" className="section">
      <div className="wrap">
        <Reveal className="max-w-3xl">
          <Eyebrow>09 / TRY IT ON A FIELD</Eyebrow>
          <h2 id="try-h">Upload a field photo. Get the places to walk to.</h2>
          <p className="mt-6">This runs the real analysis on your computer: it cuts the photo into tiles, scores greenness (VARI) and texture (GLCM), groups suspect tiles (DBSCAN) and plans the walk. Results are saved and listed on the <TextLink href="#/data" className="font-medium">data console</TextLink>.</p>
        </Reveal>

        {!user && (
          <div className="mt-12 flex flex-col items-start gap-5 rounded-card border border-line bg-surface p-8 sm:flex-row sm:items-center sm:justify-between">
            <div><p className="font-display text-2xl font-semibold">Sign in to analyse a field.</p><p className="mt-2 text-muted">Your scans, hotspots and leaf photos are saved to your account.</p></div>
            <ButtonLink href="#/dashboard">Sign in to continue</ButtonLink>
          </div>
        )}
        {user && online === false && (
          <div role="alert" className="mt-12 flex gap-4 rounded-card border border-hot p-6"><AlertTriangle aria-hidden strokeWidth={1.5} className="shrink-0 text-hot" />
            <div><p className="font-medium">The analysis server is not running.</p><p className="mono mt-2 text-sm">uv run uvicorn backend.app.main:app --port 8000</p></div></div>
        )}

        {user && <div className="mt-12 grid gap-10 lg:grid-cols-12">
          <div className="lg:col-span-4">
            <div className="rounded-card border border-line bg-surface p-6">
              <h3 className="label mono !text-xs !font-normal text-muted">1 · Choose a photo</h3>
              <div onDragOver={(e) => { e.preventDefault(); setDrag(true) }} onDragLeave={() => setDrag(false)} onDrop={(e) => { e.preventDefault(); setDrag(false); const f = e.dataTransfer.files[0]; if (f) setFile(f) }}
                className={`mt-4 rounded-ctl border border-dashed p-5 text-center ${drag ? 'border-hot' : 'border-line'}`}>
                <input ref={input} type="file" accept="image/jpeg,image/png" hidden onChange={(e) => setFile(e.target.files?.[0] ?? null)} />
                <Upload aria-hidden className="mx-auto text-muted" strokeWidth={1.5} />
                <p className="mt-2 text-sm">{file ? <span className="mono">{file.name}</span> : 'Drop a drone photo here'}</p>
                <button onClick={() => input.current?.click()} className="link-u mt-1 text-sm font-medium">or browse (.jpg, .png, up to 30 MB)</button>
              </div>
              {!file && samples.length > 0 && (
                <label className="mt-4 block text-sm">…or use a sample field
                  <select value={pick} onChange={(e) => setPick(e.target.value)} className="mt-1 w-full rounded-ctl border border-line bg-bg px-3 py-2">
                    {samples.map((s) => <option key={s.name} value={s.name}>{s.name}</option>)}
                  </select></label>
              )}
              <label className="mt-4 block text-sm">Name <span className="text-muted">(optional)</span>
                <input value={name} onChange={(e) => setName(e.target.value)} placeholder="e.g. Plot 7, north" className="mt-1 w-full rounded-ctl border border-line bg-bg px-3 py-2" /></label>
              <label className="mt-4 block text-sm">Ground size of one pixel, in cm
                <input value={gsd} onChange={(e) => setGsd(e.target.value)} inputMode="decimal" className="mono mt-1 w-full rounded-ctl border border-line bg-bg px-3 py-2" />
                <span className="mt-1 block text-xs text-muted">Sets area and walking distance. Typical at 35 m: about 1 cm. Unsure? Leave 1.0.</span></label>
              <Button onClick={run} disabled={busy || online === false || (!file && !pick)} className="mt-6 w-full">{busy ? 'Analysing…' : 'Analyse field'}</Button>
              {err && <p role="alert" className="mt-3 text-sm text-hot">{err}</p>}
            </div>
            {history.length > 0 && (
              <div className="mt-6"><h3 className="label mono !text-xs !font-normal text-muted">Recent scans</h3>
                <ul className="mt-3 divide-y divide-line border-y border-line">
                  {history.slice(0, 5).map((h) => (
                    <li key={h.id}><button onClick={() => api.scan(h.id).then((s) => { setScan(s); setSel(null) })} className={`flex w-full items-center justify-between py-3 text-left text-sm ${scan?.id === h.id ? 'text-hot' : ''}`}>
                      <span className="truncate">{h.name}</span><span className="label mono text-muted">{h.hotspots} hotspot{h.hotspots === 1 ? '' : 's'}</span></button></li>
                  ))}</ul></div>
            )}
          </div>

          <div className="lg:col-span-8">
            {!scan ? (
              <div className="grid min-h-[320px] place-items-center rounded-card border border-dashed border-line p-8 text-center text-muted"><p>No scan yet. Pick a sample and press Analyse field.</p></div>
            ) : (
              <div>
                <div className="mb-3 flex flex-wrap items-center justify-between gap-3">
                  <div role="tablist" aria-label="Map layer" className="flex gap-1">
                    {LAYERS.map(([k, l]) => <button key={k} role="tab" aria-selected={layer === k} onClick={() => setLayer(k)} className={`label mono rounded-ctl border px-3 py-2 ${layer === k ? 'border-ink bg-ink text-bg' : 'border-line'}`}>{l}</button>)}
                  </div>
                  <p className="label mono text-muted">{scan.name} · {scan.id}</p>
                </div>
                <div className="relative overflow-hidden rounded-card border border-line bg-mapbg" style={{ aspectRatio: `${scan.image.width} / ${scan.image.height}` }}>
                  <img key={layer + scan.id} src={scan.files[layer]} alt={`${LAYERS.find((l) => l[0] === layer)![1]} layer of the field photo`} className="absolute inset-0 h-full w-full object-fill" />
                  {layer === 'overlay' && scan.hotspots.map((h) => (
                    <button key={h.id} data-hotspot data-tip={`Hotspot ${h.id} · ${h.area_m2} m² · ${h.severity} · ${h.status}`} aria-label={`Select hotspot ${h.id}`} onClick={() => setSel(h.id)}
                      className="absolute grid h-8 w-8 -translate-x-1/2 -translate-y-1/2 place-items-center rounded-full" style={{ left: `${h.pct[0] * 100}%`, top: `${h.pct[1] * 100}%` }}>
                      <span aria-hidden className="pulse-ring absolute inset-0 rounded-full border-2 border-hot" />
                      <span className={`label mono grid h-6 w-6 place-items-center rounded-full bg-hot text-on-hot ${sel === h.id ? 'ring-2 ring-ink' : ''}`}>{h.id}</span>
                    </button>
                  ))}
                  {layer === 'vari' && <p className="label mono absolute bottom-3 left-3 rounded-ctl bg-bg/80 px-2 py-1">Greenness lost vs field median · green → amber → red</p>}
                  {layer === 'texture' && <p className="label mono absolute bottom-3 left-3 rounded-ctl bg-bg/80 px-2 py-1">GLCM roughness vs healthy · smooth → ragged</p>}
                </div>

                <dl className="mt-6 grid grid-cols-2 gap-px overflow-hidden rounded-card border border-line bg-line sm:grid-cols-4">
                  {[['Hotspots', String(scan.hotspots.length), true], ['Pest-like tiles', String(scan.field.biotic_tiles)], ['Drought-like tiles', String(scan.field.abiotic_tiles)], ['Walk', scan.hotspots.length ? `${scan.route.distance_m} m` : '—']].map(([k, v, hot]) => (
                    <div key={k as string} className="bg-surface p-4"><dt className="label mono text-muted">{k}</dt><dd className={`bignum !text-4xl ${hot ? 'text-hot' : ''}`}>{v}</dd></div>
                  ))}
                </dl>

                {scan.hotspots.length === 0 ? (
                  <p className="mt-6 flex items-center gap-3 rounded-card border border-line p-5"><Check aria-hidden className="text-canopy" strokeWidth={1.5} />No pest-like hotspots found in this photo. {scan.field.abiotic_tiles > 0 ? `${scan.field.abiotic_tiles} tiles look stressed but smooth, which points to drought or nutrients rather than insects.` : ''}</p>
                ) : (
                  <ol className="mt-6 grid gap-3 md:grid-cols-2">
                    {[...scan.hotspots].sort((a, b) => (a.route_stop ?? 99) - (b.route_stop ?? 99)).map((h) => (
                      <li key={h.id} className={`rounded-card border p-5 ${sel === h.id ? 'border-ink' : 'border-line'} bg-surface`}>
                        <button onClick={() => setSel(h.id)} className="flex w-full items-center justify-between text-left">
                          <span className="font-display text-xl font-semibold">Stop {h.route_stop} · Hotspot {h.id}</span><span className="mono text-sm">{h.area_m2} m²</span></button>
                        <p className="mt-2 flex flex-wrap items-center gap-x-4 gap-y-1"><span className={`label mono ${sev[h.severity]}`}>Severity: {h.severity}</span>
                          <span className={`label mono ${h.status.startsWith('Confirmed') ? 'text-canopy' : 'text-muted'}`}>{h.status}</span></p>
                        <p className="mono mt-2 text-sm text-muted">VARI {h.vari} · contrast {h.glcm_contrast} · entropy {h.glcm_entropy}</p>
                        {(sel === h.id || h.photos.length > 0) && <LeafUpload scan={scan} h={h} species={species} onDone={updated} />}
                      </li>
                    ))}
                  </ol>
                )}
                {selected && !selected.photos.length && <p className="label mono mt-3 text-muted">Walk to hotspot {selected.id}, photograph a leaf, and add it above.</p>}
                <p className="mt-6"><TextLink href={`#/dashboard/scans/${scan.id}`} arrow className="font-medium">Open this scan in the dashboard</TextLink></p>
                <p className="label mono mt-6 max-w-3xl text-muted" style={{ textTransform: 'none' }}>{scan.method} Area and distance assume {scan.gsd_cm} cm per pixel. Species is chosen by the scout; there is no species classifier in this build.</p>
              </div>
            )}
          </div>
        </div>}
      </div>
    </section>
  )
}
