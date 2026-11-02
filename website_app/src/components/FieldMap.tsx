import { useEffect, useId, useRef, useState, type Ref } from 'react'
import { COLS, OX, OY, ROWS, CELL, VB_H, VB_W, abioticPatches, coordsAt, farmhouse, hotspots, routePath, tiles, type Tile } from '../data/field'
import HotspotMarker from './HotspotMarker'

export type MapMode = 'rgb' | 'index' | 'class'
export interface Hud { alt: string; vari: string; entropy: string; hotspots: string }
interface Props {
  scan?: number; mode?: MapMode; dismiss?: number; route?: number; outline?: boolean; tileGrid?: boolean
  hud?: Hud | null; liveCoords?: boolean; showScanLine?: boolean; className?: string; label: string
  groupRef?: Ref<SVGGElement>; fadeRef?: Ref<SVGGElement>; onHotspot?: (id: string) => void
}
const mix = (a: string, b: string, pct: number) => `color-mix(in srgb, var(--${a}) ${Math.round((1 - pct) * 100)}%, var(--${b}))`
const ramp = (v: number) => (v < .5 ? mix('canopy', 'stress', v * 2) : mix('stress', 'hot', (v - .5) * 2))

export function fillFor(t: Tile, mode: MapMode, scanned: boolean, dismiss: number) {
  if (!scanned) return 'var(--tile-raw)'
  if (mode === 'rgb') return t.cls === 'ok' ? mix('tile-ok', 'stress', t.rgb * .12) : mix('tile-ok', 'stress', .38 + t.rgb * .1)
  if (mode === 'index') return ramp(t.vari)
  if (t.cls === 'ok') return 'var(--tile-ok)'
  if (t.cls === 'abiotic') return mix('stress', 'tile-ok', dismiss)
  return 'var(--hot)'
}

function CoordReadout({ target }: { target: React.RefObject<HTMLDivElement | null> }) {
  const [c, setC] = useState(coordsAt(.5, .5))
  useEffect(() => {
    const el = target.current; if (!el) return; let raf = 0
    const mv = (e: MouseEvent) => {
      cancelAnimationFrame(raf)
      raf = requestAnimationFrame(() => { const r = el.getBoundingClientRect(); setC(coordsAt((e.clientX - r.left) / r.width, (e.clientY - r.top) / r.height)) })
    }
    el.addEventListener('mousemove', mv); return () => { el.removeEventListener('mousemove', mv); cancelAnimationFrame(raf) }
  }, [target])
  return <span>{c}</span>
}

export default function FieldMap({ scan = 1, mode = 'class', dismiss = 1, route = 0, outline = false, tileGrid = false, hud, liveCoords, showScanLine, className = '', label, groupRef, fadeRef, onHotspot }: Props) {
  const wrap = useRef<HTMLDivElement>(null)
  const mid = 'route' + useId().replace(/:/g, '')
  const yScan = scan * (VB_H + 20)
  const classified = mode === 'class'
  return (
    <div ref={wrap} data-cursor="map" className={`relative overflow-hidden rounded-card border border-line bg-mapbg ${className}`} style={{ aspectRatio: `${VB_W} / ${VB_H}` }}>
      {['left-3 top-3 border-l border-t', 'right-3 top-3 border-r border-t', 'left-3 bottom-3 border-l border-b', 'right-3 bottom-3 border-r border-b'].map((c) => <span key={c} aria-hidden className={`corner z-10 ${c}`} />)}
      <svg viewBox={`0 0 ${VB_W} ${VB_H}`} role="img" aria-label={label} className="absolute inset-0 h-full w-full">
        <g ref={groupRef} className="no-tr">
          <g ref={fadeRef}>
            {/* tracks between plots */}
            <rect x={OX - 6} y={OY - 6} width={COLS * CELL + 12} height={ROWS * CELL + 12} rx={4} fill="none" stroke="var(--map-line)" strokeOpacity={.18} strokeDasharray="2 4" />
            {tiles.map((t) => {
              const scanned = t.y + t.h / 2 < yScan
              return <rect key={t.id} x={t.x} y={t.y} width={t.w} height={t.h} rx={2} fill={fillFor(t, mode, scanned, dismiss)}
                stroke="var(--tile-ok-edge)" strokeOpacity={scanned ? .5 : .25} strokeWidth={.6}
                opacity={classified && scanned && t.cls === 'abiotic' ? 1 - dismiss * .25 : 1} style={{ transition: 'fill .9s cubic-bezier(.22,1,.36,1), opacity .9s' }} />
            })}
            {tileGrid && Array.from({ length: 4 }).map((_, i) => (
              <g key={i} stroke="var(--map-line)" strokeOpacity={.45} strokeWidth={.8} strokeDasharray="3 3">
                <line x1={OX + (i + 1) * (COLS / 4) * CELL - (i === 3 ? 0 : 0)} x2={OX + (i + 1) * (COLS / 4) * CELL} y1={OY - 6} y2={OY + ROWS * CELL + 6} />
                {i < 1 && <line x1={OX - 6} x2={OX + COLS * CELL + 6} y1={OY + ROWS * CELL / 2} y2={OY + ROWS * CELL / 2} />}
              </g>
            ))}
            {classified && abioticPatches.map((p, i) => yScan > p.cy && (
              <text key={i} x={p.cx} y={p.cy + 36} textAnchor="middle" fontSize={10} letterSpacing=".08em" fill="var(--stress)" stroke="var(--map-bg)" strokeWidth={4} paintOrder="stroke"
                style={{ fontFamily: 'var(--font-mono)', textDecoration: 'line-through', textTransform: 'uppercase' }}>
                ABIOTIC — dismissed
              </text>
            ))}
            {outline && hotspots.map((h) => {
              const ts = h.tiles.map((id) => tiles.find((t) => t.id === id)!)
              const x0 = Math.min(...ts.map((t) => t.x)) - 5, y0 = Math.min(...ts.map((t) => t.y)) - 5
              const x1 = Math.max(...ts.map((t) => t.x + t.w)) + 5, y1 = Math.max(...ts.map((t) => t.y + t.h)) + 5
              return <rect key={h.id} x={x0} y={y0} width={x1 - x0} height={y1 - y0} rx={6} fill="none" stroke="var(--hot)" strokeWidth={1.5} strokeDasharray="5 3" />
            })}
            <defs>
              <mask id={mid}><path d={routePath} fill="none" stroke="#fff" strokeWidth={8} pathLength={1} strokeDasharray={1} strokeDashoffset={1 - route} strokeLinecap="round" /></mask>
            </defs>
            <path d={routePath} fill="none" stroke="var(--map-line)" strokeWidth={2} strokeDasharray="7 6" strokeLinejoin="round" mask={`url(#${mid})`} />
            {/* farmhouse */}
            <g transform={`translate(${farmhouse.x} ${farmhouse.y})`} data-tip="Farmhouse · route start">
              <circle r={13} fill="var(--surface)" stroke="var(--map-line)" strokeWidth={1.2} />
              <path d="M -6 1 L 0 -5 L 6 1 M -4 0 V 6 H 4 V 0" fill="none" stroke="var(--map-line)" strokeWidth={1.2} strokeLinejoin="round" />
            </g>
            {classified && hotspots.map((h) => yScan > h.cy && (
              <g key={h.id} onClick={() => onHotspot?.(h.id)}>
                <HotspotMarker x={h.cx} y={h.cy} tip={`${h.name} · ${h.area} · ${h.severity} · ${h.status} (sample)`} label={h.id} />
              </g>
            ))}
          </g>
        </g>
        {showScanLine && scan > 0 && scan < 1 && (
          <g aria-hidden pointerEvents="none">
            <rect x={0} y={yScan - 22} width={VB_W} height={22} fill="var(--scan)" opacity={.12} />
            <line x1={0} x2={VB_W} y1={yScan} y2={yScan} stroke="var(--scan)" strokeWidth={1.5} />
          </g>
        )}
      </svg>
      {hud && (
        <div aria-hidden className="pointer-events-none absolute inset-0 z-10 p-3 text-ink sm:p-5 max-sm:[&_.label]:!text-[10px] [&_span]:bg-mapbg/70 [&_span]:px-1">
          <div className="label mono flex justify-between"><span>ALT {hud.alt}</span><span>GLCM ENTROPY {hud.entropy}</span></div>
          <div className="label mono mt-1 flex justify-between"><span>VARI {hud.vari}</span><span className="text-hot">HOTSPOTS {hud.hotspots}</span></div>
          <div className="label mono absolute bottom-3 left-3 sm:bottom-5 sm:left-5">{liveCoords ? <CoordReadout target={wrap} /> : coordsAt(.5, .5)}</div>
          <div className="label mono absolute bottom-3 right-3 text-muted sm:bottom-5 sm:right-5">SAMPLE DATA</div>
        </div>
      )}
    </div>
  )
}
