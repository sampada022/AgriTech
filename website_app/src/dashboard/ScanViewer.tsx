import { useState } from 'react'
import type { Scan } from '../api'

const LAYERS = [['image', 'Photo'], ['overlay', 'Hotspots'], ['vari', 'VARI'], ['texture', 'Texture']] as const
type Layer = (typeof LAYERS)[number][0]

export default function ScanViewer({ scan, selected, onSelect, initial = 'overlay' }: { scan: Scan; selected?: string | null; onSelect?: (id: string) => void; initial?: Layer }) {
  const [layer, setLayer] = useState<Layer>(initial)
  return (
    <div>
      <div role="tablist" aria-label="Map layer" className="no-print mb-3 flex flex-wrap gap-1">
        {LAYERS.map(([k, l]) => <button key={k} role="tab" aria-selected={layer === k} onClick={() => setLayer(k)} className={`label mono rounded-ctl border px-3 py-2 ${layer === k ? 'border-ink bg-ink text-bg' : 'border-line hover:border-ink'}`}>{l}</button>)}
      </div>
      <div className="relative overflow-hidden rounded-card border border-line bg-mapbg" style={{ aspectRatio: `${scan.image.width} / ${scan.image.height}` }}>
        <img key={layer + scan.id} src={scan.files[layer]} alt={`${LAYERS.find((l) => l[0] === layer)![1]} layer of ${scan.name}`} className="absolute inset-0 h-full w-full object-fill" />
        {layer === 'overlay' && scan.hotspots.map((h) => (
          <button key={h.id} data-hotspot data-tip={`Hotspot ${h.id} · ${h.area_m2} m² · ${h.severity} · ${h.status}`} aria-label={`Hotspot ${h.id}, ${h.severity} severity`} onClick={() => onSelect?.(h.id)}
            className="absolute grid h-8 w-8 -translate-x-1/2 -translate-y-1/2 place-items-center rounded-full" style={{ left: `${h.pct[0] * 100}%`, top: `${h.pct[1] * 100}%` }}>
            <span aria-hidden className="pulse-ring absolute inset-0 rounded-full border-2 border-hot" />
            <span className={`label mono grid h-6 w-6 place-items-center rounded-full bg-hot text-on-hot ${selected === h.id ? 'ring-2 ring-ink' : ''}`}>{h.id}</span>
          </button>
        ))}
        {layer === 'vari' && <p className="label mono absolute bottom-3 left-3 rounded-ctl bg-bg/80 px-2 py-1">Greenness lost vs field median · green → amber → red</p>}
        {layer === 'texture' && <p className="label mono absolute bottom-3 left-3 rounded-ctl bg-bg/80 px-2 py-1">GLCM roughness vs healthy · smooth → ragged</p>}
      </div>
    </div>
  )
}
