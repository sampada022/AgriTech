import { AlertTriangle, Check, Upload } from 'lucide-react'
import { useCallback, useEffect, useRef, useState } from 'react'
import { fieldsApi, scansApi, type FieldOut, type HotspotFeature, type ScanOut } from '../api'
import { Button, TextLink } from '../components/Button'
import LeafUpload from '../components/LeafUpload'
import { ButtonLink } from '../components/Button'
import { useAuth } from '../hooks/auth'
import Eyebrow from '../components/Eyebrow'
import { Reveal } from '../components/Reveal'

const LAYERS = [['rgb', 'Photo'], ['heat', 'Hotspots'], ['vari', 'VARI']] as const
type Layer = (typeof LAYERS)[number][0]
const TIER_COLOR = { red: 'text-hot', amber: 'text-ink', grey_blue: 'text-muted' } as const

// No GPS on a plain upload, so the field is placed at a fixed demo location, sized from cm-per-pixel.
const CENTRE_LAT = 12.5231, CENTRE_LON = 76.8951, M_PER_DEG_LON = 111_320, M_PER_DEG_LAT = 110_574
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
function pct(h: HotspotFeature, b: ScanOut['bounds']): [number, number] {
  const { lat, lon } = h.properties.centroid
  return [(lon - b.sw_lon) / (b.ne_lon - b.sw_lon), (b.ne_lat - lat) / (b.ne_lat - b.sw_lat)]
}

export default function LiveScan() {
  const { user } = useAuth()
  const [online, setOnline] = useState<boolean | null>(null)
  const [history, setHistory] = useState<FieldOut[]>([])
  const [scan, setScan] = useState<ScanOut | null>(null), [hotspots, setHotspots] = useState<HotspotFeature[]>([])
  const [layer, setLayer] = useState<Layer>('heat'), [sel, setSel] = useState<string | null>(null)
  const [busy, setBusy] = useState(false), [err, setErr] = useState(''), [file, setFile] = useState<File | null>(null), [name, setName] = useState(''), [gsd, setGsd] = useState('3.0'), [drag, setDrag] = useState(false)
  const input = useRef<HTMLInputElement>(null)
  const poll = useRef<ReturnType<typeof setTimeout>>(undefined)

  const refresh = useCallback(async () => {
    try { const h = await fieldsApi.list(); setHistory(h); setOnline(true); return h } catch { setOnline(false); return [] }
  }, [])
  useEffect(() => { if (!user) return; refresh().then((h) => { if (h[0]?.latest_scan) open(h[0].latest_scan.id) }) }, [refresh, user])
  useEffect(() => () => clearTimeout(poll.current), [])

  const open = (scanId: string) => {
    setSel(null)
    const tick = () => scansApi.get(scanId).then(async (s) => {
      setScan(s)
      if (s.status === 'queued' || s.status === 'running') poll.current = setTimeout(tick, 800)
      else if (s.status === 'done') setHotspots((await scansApi.hotspots(scanId)).features)
    })
    tick()
  }
  const run = async () => {
    if (!file) return
    setBusy(true); setErr('')
    try {
      const { width, height } = await imageSize(file)
      const gsdCm = parseFloat(gsd) || 3
      const bounds = boundsFromCentre((width * gsdCm) / 100, (height * gsdCm) / 100)
      const field = await fieldsApi.create({ image: file, name: name || file.name, data_source: 'stand_in', ...bounds })
      const started = await fieldsApi.startScan(field.id)
      setLayer('heat'); setFile(null); setName(''); setHotspots([]); open(started.id); refresh()
    } catch (e) { setErr((e as Error).message) } finally { setBusy(false) }
  }
  const selected = hotspots.find((h) => h.id === sel)

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
            <div><p className="font-display text-2xl font-semibold">Sign in to analyse a field.</p><p className="mt-2 text-muted">Your scans and hotspots are saved to your account.</p></div>
            <ButtonLink href="#/dashboard">Sign in to continue</ButtonLink>
          </div>
        )}
        {user && online === false && (
          <div role="alert" className="mt-12 flex gap-4 rounded-card border border-hot p-6"><AlertTriangle aria-hidden strokeWidth={1.5} className="shrink-0 text-hot" />
            <div><p className="font-medium">The analysis server is not running.</p><p className="mono mt-2 text-sm">cd apps/api && uvicorn app.main:app --port 8000</p></div></div>
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
                <button onClick={() => input.current?.click()} className="link-u mt-1 text-sm font-medium">or browse (.jpg, .png, up to 50 MB)</button>
              </div>
              <label className="mt-4 block text-sm">Name <span className="text-muted">(optional)</span>
                <input value={name} onChange={(e) => setName(e.target.value)} placeholder="e.g. Plot 7, north" className="mt-1 w-full rounded-ctl border border-line bg-bg px-3 py-2" /></label>
              <label className="mt-4 block text-sm">Ground size of one pixel, in cm
                <input value={gsd} onChange={(e) => setGsd(e.target.value)} inputMode="decimal" className="mono mt-1 w-full rounded-ctl border border-line bg-bg px-3 py-2" />
                <span className="mt-1 block text-xs text-muted">Sets area and walking distance. Typical at 35 m: about 3 cm. Unsure? Leave 3.0.</span></label>
              <Button onClick={run} disabled={busy || online === false || !file} className="mt-6 w-full">{busy ? 'Starting…' : 'Analyse field'}</Button>
              {err && <p role="alert" className="mt-3 text-sm text-hot">{err}</p>}
            </div>
            {history.length > 0 && (
              <div className="mt-6"><h3 className="label mono !text-xs !font-normal text-muted">Recent fields</h3>
                <ul className="mt-3 divide-y divide-line border-y border-line">
                  {history.slice(0, 5).map((f) => (
                    <li key={f.id}><button disabled={!f.latest_scan} onClick={() => f.latest_scan && open(f.latest_scan.id)} className={`flex w-full items-center justify-between py-3 text-left text-sm ${scan?.field_id === f.id ? 'text-hot' : ''}`}>
                      <span className="truncate">{f.name}</span><span className="label mono text-muted">{f.latest_scan?.hotspot_count ?? 0} hotspot{f.latest_scan?.hotspot_count === 1 ? '' : 's'}</span></button></li>
                  ))}</ul></div>
            )}
          </div>

          <div className="lg:col-span-8">
            {!scan ? (
              <div className="grid min-h-[320px] place-items-center rounded-card border border-dashed border-line p-8 text-center text-muted"><p>No scan yet. Upload a photo and press Analyse field.</p></div>
            ) : scan.status === 'queued' || scan.status === 'running' ? (
              <div className="grid min-h-[320px] place-items-center rounded-card border border-dashed border-line p-8 text-center text-muted">
                <div><p>{scan.stage ? `Stage: ${scan.stage}` : 'Starting…'}</p><div className="mt-3 h-2 w-48 overflow-hidden rounded-ctl bg-line"><div className="h-full bg-hot" style={{ width: `${scan.progress}%` }} /></div></div>
              </div>
            ) : scan.status === 'failed' ? (
              <div role="alert" className="rounded-card border border-hot p-6">{scan.error?.message ?? 'Analysis failed.'}</div>
            ) : (
              <div>
                <div className="mb-3 flex flex-wrap items-center justify-between gap-3">
                  <div role="tablist" aria-label="Map layer" className="flex gap-1">
                    {LAYERS.filter(([k]) => scan.layers[k]).map(([k, l]) => <button key={k} role="tab" aria-selected={layer === k} onClick={() => setLayer(k)} className={`label mono rounded-ctl border px-3 py-2 ${layer === k ? 'border-ink bg-ink text-bg' : 'border-line'}`}>{l}</button>)}
                  </div>
                  <p className="label mono text-muted">{scan.id}</p>
                </div>
                <div className="relative overflow-hidden rounded-card border border-line bg-mapbg" style={{ aspectRatio: `${scan.grid?.working_width ?? 1} / ${scan.grid?.working_height ?? 1}` }}>
                  {scan.layers[layer] && <img key={layer + scan.id} src={scan.layers[layer].url} alt={`${LAYERS.find((l) => l[0] === layer)![1]} layer of the field photo`} className="absolute inset-0 h-full w-full object-fill" />}
                  {(layer === 'rgb' || layer === 'heat') && hotspots.map((h) => {
                    const [x, y] = pct(h, scan.bounds)
                    return (
                      <button key={h.id} data-hotspot data-tip={`Hotspot ${h.id} · ${h.properties.area_m2} m² · ${h.properties.tier} · ${h.properties.status}`} aria-label={`Select hotspot ${h.id}`} onClick={() => setSel(h.id)}
                        className="absolute grid h-8 w-8 -translate-x-1/2 -translate-y-1/2 place-items-center rounded-full" style={{ left: `${x * 100}%`, top: `${y * 100}%` }}>
                        <span aria-hidden className="pulse-ring absolute inset-0 rounded-full border-2 border-hot" />
                        <span className={`label mono grid h-6 w-6 place-items-center rounded-full bg-hot text-on-hot ${sel === h.id ? 'ring-2 ring-ink' : ''}`}>{h.properties.rank}</span>
                      </button>) })}
                  {layer === 'vari' && <p className="label mono absolute bottom-3 left-3 rounded-ctl bg-bg/80 px-2 py-1">Greenness lost vs field median · green → amber → red</p>}
                </div>

                <dl className="mt-6 grid grid-cols-2 gap-px overflow-hidden rounded-card border border-line bg-line sm:grid-cols-4">
                  {[['Hotspots', String(hotspots.length), true], ['Red tier', String(scan.kpis?.tier_counts.red ?? 0)], ['Amber tier', String(scan.kpis?.tier_counts.amber ?? 0)], ['Walk', hotspots.length ? `${Math.round(scan.kpis?.route_distance_m ?? 0)} m` : '—']].map(([k, v, hot]) => (
                    <div key={k as string} className="bg-surface p-4"><dt className="label mono text-muted">{k}</dt><dd className={`bignum !text-4xl ${hot ? 'text-hot' : ''}`}>{v}</dd></div>
                  ))}
                </dl>

                {hotspots.length === 0 ? (
                  <p className="mt-6 flex items-center gap-3 rounded-card border border-line p-5"><Check aria-hidden className="text-canopy" strokeWidth={1.5} />No hotspots found in this photo. This field looks healthy to the model.</p>
                ) : (
                  <ol className="mt-6 grid gap-3 md:grid-cols-2">
                    {[...hotspots].sort((a, b) => a.properties.rank - b.properties.rank).map((h) => (
                      <li key={h.id} className={`rounded-card border p-5 ${sel === h.id ? 'border-ink' : 'border-line'} bg-surface`}>
                        <button onClick={() => setSel(h.id)} className="flex w-full items-center justify-between text-left">
                          <span className="font-display text-xl font-semibold">Stop {h.properties.rank} · Hotspot {h.id}</span><span className="mono text-sm">{h.properties.area_m2} m²</span></button>
                        <p className="mt-2 flex flex-wrap items-center gap-x-4 gap-y-1"><span className={`label mono ${TIER_COLOR[h.properties.tier]}`}>Tier: {h.properties.tier}</span>
                          <span className={`label mono ${h.properties.label ? 'text-canopy' : 'text-muted'}`}>{h.properties.status}</span></p>
                        <p className="mono mt-2 text-sm text-muted">Biotic score {h.properties.biotic_score} · confidence {h.properties.confidence}</p>
                        {(sel === h.id || h.properties.label) && <LeafUpload h={h} onConfirmed={(f) => setHotspots((hs) => hs.map((x) => (x.id === f.id ? f : x)))} />}
                      </li>
                    ))}
                  </ol>
                )}
                {selected && !selected.properties.label && <p className="label mono mt-3 text-muted">Walk to hotspot {selected.id}, photograph a leaf, and add it above.</p>}
                <p className="mt-6"><TextLink href={`#/dashboard/scans/${scan.id}`} arrow className="font-medium">Open this scan in the dashboard</TextLink></p>
                <p className="label mono mt-6 max-w-3xl text-muted" style={{ textTransform: 'none' }}>Classical computer vision, not a trained pest classifier. Area assumes {scan.grid?.gsd_cm ?? '—'} cm per pixel.</p>
              </div>
            )}
          </div>
        </div>}
      </div>
    </section>
  )
}
