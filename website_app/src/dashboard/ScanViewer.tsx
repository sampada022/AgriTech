import { useState } from 'react'
import type { HotspotFeature, ScanOut } from '../api'

const LAYERS = [['rgb', 'Photo'], ['heat', 'Hotspots'], ['vari', 'VARI']] as const
type Layer = (typeof LAYERS)[number][0]

function pct(h: HotspotFeature, b: ScanOut['bounds']): [number, number] {
  const { lat, lon } = h.properties.centroid
  return [(lon - b.sw_lon) / (b.ne_lon - b.sw_lon), (b.ne_lat - lat) / (b.ne_lat - b.sw_lat)]
}

export default function ScanViewer({ scan, hotspots, selected, onSelect, initial = 'heat' }: {
  scan: ScanOut; hotspots: HotspotFeature[]; selected?: string | null; onSelect?: (id: string) => void; initial?: Layer
}) {
  const [layer, setLayer] = useState<Layer>(initial)
  const present = LAYERS.filter(([k]) => scan.layers[k])
  const url = scan.layers[layer]?.url
  return (
    <div>
      <div role="tablist" aria-label="Map layer" className="no-print mb-3 flex flex-wrap gap-1">
        {present.map(([k, l]) => <button key={k} role="tab" aria-selected={layer === k} onClick={() => setLayer(k)} className={`label mono rounded-ctl border px-3 py-2 ${layer === k ? 'border-ink bg-ink text-bg' : 'border-line hover:border-ink'}`}>{l}</button>)}
      </div>
      <div className="relative overflow-hidden rounded-card border border-line bg-mapbg" style={{ aspectRatio: `${scan.grid?.working_width ?? 1} / ${scan.grid?.working_height ?? 1}` }}>
        {url && <img key={layer + scan.id} src={url} alt={`${LAYERS.find((l) => l[0] === layer)![1]} layer of ${scan.id}`} className="absolute inset-0 h-full w-full object-fill" />}
        {(layer === 'rgb' || layer === 'heat') && hotspots.map((h) => {
          const [x, y] = pct(h, scan.bounds)
          return (
            <button key={h.id} data-hotspot data-tip={`Hotspot ${h.id} · ${h.properties.area_m2} m² · ${h.properties.tier} · ${h.properties.status}`} aria-label={`Hotspot ${h.id}, ${h.properties.tier} tier`} onClick={() => onSelect?.(h.id)}
              className="absolute grid h-8 w-8 -translate-x-1/2 -translate-y-1/2 place-items-center rounded-full" style={{ left: `${x * 100}%`, top: `${y * 100}%` }}>
              <span aria-hidden className="pulse-ring absolute inset-0 rounded-full border-2 border-hot" />
              <span className={`label mono grid h-6 w-6 place-items-center rounded-full bg-hot text-on-hot ${selected === h.id ? 'ring-2 ring-ink' : ''}`}>{h.properties.rank}</span>
            </button>
          )
        })}
        {layer === 'vari' && <p className="label mono absolute bottom-3 left-3 rounded-ctl bg-bg/80 px-2 py-1">Greenness lost vs field median · green → amber → red</p>}
        {layer === 'heat' && <p className="label mono absolute bottom-3 left-3 rounded-ctl bg-bg/80 px-2 py-1">Anomaly score · low → high</p>}
      </div>
    </div>
  )
}
