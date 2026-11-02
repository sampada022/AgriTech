import { Table2, BarChart3 } from 'lucide-react'
import { useEffect, useRef, useState, type ReactNode } from 'react'

function useWidth() {
  const ref = useRef<HTMLDivElement>(null); const [w, setW] = useState(480)
  useEffect(() => {
    const el = ref.current; if (!el) return
    const ro = new ResizeObserver(([e]) => setW(Math.max(240, Math.floor(e.contentRect.width)))); ro.observe(el); setW(Math.max(240, el.clientWidth)); return () => ro.disconnect()
  }, [])
  return [ref, w] as const
}

/** A chart with the table view the accessibility pass asks for. */
export function ChartCard({ title, sub, head, rows, children, legend }: { title: string; sub?: string; head: string[]; rows: (string | number)[][]; children: ReactNode; legend?: ReactNode }) {
  const [table, setTable] = useState(false)
  return (
    <section className="rounded-card border border-line bg-surface p-5">
      <header className="mb-4 flex items-start justify-between gap-4">
        <div><h2 className="font-display !text-lg !font-semibold !leading-tight !tracking-tight">{title}</h2>{sub && <p className="mt-1 text-sm text-muted">{sub}</p>}</div>
        <button onClick={() => setTable(!table)} aria-pressed={table} aria-label={table ? 'Show chart' : 'Show table'} className="grid h-9 w-9 shrink-0 place-items-center rounded-ctl border border-line hover:border-ink">
          {table ? <BarChart3 size={16} strokeWidth={1.5} /> : <Table2 size={16} strokeWidth={1.5} />}</button>
      </header>
      {legend && !table && <div className="mb-3 flex flex-wrap gap-x-5 gap-y-1 text-sm">{legend}</div>}
      {table ? (
        <div className="max-h-72 overflow-auto"><table className="w-full text-left text-sm"><thead><tr className="border-b border-ink">{head.map((h) => <th key={h} className="label mono py-2 pr-4 font-normal text-muted">{h}</th>)}</tr></thead>
          <tbody>{rows.map((r, i) => <tr key={i} className="border-b border-line">{r.map((c, j) => <td key={j} className="mono py-2 pr-4">{c}</td>)}</tr>)}</tbody></table></div>
      ) : children}
    </section>
  )
}
export const LegendItem = ({ swatch, children }: { swatch: ReactNode; children: ReactNode }) => <span className="inline-flex items-center gap-2 text-muted">{swatch}{children}</span>

interface Tip { x: number; y: number; text: string }
function TipBox({ tip }: { tip: Tip | null }) {
  if (!tip) return null
  return <div role="status" className="label mono pointer-events-none absolute z-10 max-w-[240px] -translate-x-1/2 -translate-y-full rounded-ctl border border-line bg-bg px-3 py-2 text-ink" style={{ left: tip.x, top: tip.y - 10, textTransform: 'none', letterSpacing: '.02em' }}>{tip.text}</div>
}

/** Vertical bars over time (one measure, one axis). */
export function DayBars({ data, field, label }: { data: { date: string; [k: string]: number | string }[]; field: string; label: string }) {
  const [ref, w] = useWidth(); const [tip, setTip] = useState<Tip | null>(null)
  const h = 200, m = { l: 32, r: 8, t: 12, b: 28 }, iw = w - m.l - m.r, ih = h - m.t - m.b
  const max = Math.max(1, ...data.map((d) => Number(d[field])))
  const top = Math.max(2, Math.ceil(max / 2) * 2); const ticks = [0, top / 2, top]
  const band = iw / data.length, bw = Math.min(28, Math.max(8, band * 0.55))
  return (
    <div ref={ref} className="relative" onMouseLeave={() => setTip(null)}>
      <svg width={w} height={h} role="img" aria-label={`${label}, last ${data.length} days`}>
        {ticks.map((t) => <g key={t}><line x1={m.l} x2={w - m.r} y1={m.t + ih - (t / top) * ih} y2={m.t + ih - (t / top) * ih} stroke="var(--border)" strokeWidth={1} /><text x={m.l - 8} y={m.t + ih - (t / top) * ih + 4} textAnchor="end" fontSize="11" fill="var(--muted)" style={{ fontFamily: 'var(--font-mono)' }}>{t}</text></g>)}
        {data.map((d, i) => {
          const v = Number(d[field]), x = m.l + band * i + (band - bw) / 2, bh = (v / top) * ih, d0 = new Date(d.date)
          return (
            <g key={d.date} onMouseMove={(e) => { const r = ref.current!.getBoundingClientRect(); setTip({ x: e.clientX - r.left, y: m.t + ih - bh, text: `${d0.toLocaleDateString(undefined, { day: 'numeric', month: 'short' })}: ${v} ${label.toLowerCase()}${'scans' in d ? ` · ${d.scans} scan${d.scans === 1 ? '' : 's'}` : ''}` }) }}>
              <rect x={m.l + band * i} y={m.t} width={band} height={ih} fill="transparent" />
              {v > 0 && <path d={`M ${x} ${m.t + ih} V ${m.t + ih - bh + 4} Q ${x} ${m.t + ih - bh} ${x + 4} ${m.t + ih - bh} H ${x + bw - 4} Q ${x + bw} ${m.t + ih - bh} ${x + bw} ${m.t + ih - bh + 4} V ${m.t + ih} Z`} fill="var(--hot)" />}
              {i % 2 === (data.length - 1) % 2 && <text x={x + bw / 2} y={h - 8} textAnchor="middle" fontSize="11" fill="var(--muted)" style={{ fontFamily: 'var(--font-mono)' }}>{d0.getDate()}/{d0.getMonth() + 1}</text>}
            </g>
          )
        })}
      </svg>
      <TipBox tip={tip} />
    </div>
  )
}

/** Horizontal bars for a ranked list (one hue; the label carries identity). */
export function BarList({ data, color = 'var(--canopy)' }: { data: { name: string; count: number }[]; color?: string }) {
  const max = Math.max(1, ...data.map((d) => d.count)); const [tip, setTip] = useState<Tip | null>(null); const ref = useRef<HTMLUListElement>(null)
  return (
    <ul ref={ref} className="relative flex flex-col gap-3" onMouseLeave={() => setTip(null)}>
      {data.map((d) => (
        <li key={d.name} className="grid grid-cols-[minmax(90px,150px)_1fr_auto] items-center gap-3 text-sm"
          onMouseMove={(e) => { const r = ref.current!.getBoundingClientRect(); setTip({ x: e.clientX - r.left, y: e.clientY - r.top, text: `${d.name}: ${d.count} confirmed photo${d.count === 1 ? '' : 's'}` }) }}>
          <span className="truncate">{d.name}</span>
          <span className="h-3 rounded-r-[4px] bg-bg"><span className="block h-full rounded-r-[4px]" style={{ width: `${(d.count / max) * 100}%`, background: color, minWidth: 4 }} /></span>
          <span className="mono w-6 text-right">{d.count}</span>
        </li>
      ))}
      <TipBox tip={tip} />
    </ul>
  )
}

/** Horizontal stacked bars: pest-like vs drought-like tiles per scan, 2px surface gap between segments. */
export function StackedBars({ data }: { data: { id: string; name: string; biotic: number; abiotic: number }[] }) {
  const max = Math.max(1, ...data.map((d) => d.biotic + d.abiotic)); const [tip, setTip] = useState<Tip | null>(null); const ref = useRef<HTMLUListElement>(null)
  return (
    <ul ref={ref} className="relative flex flex-col gap-3" onMouseLeave={() => setTip(null)}>
      {data.map((d) => (
        <li key={d.id} className="grid grid-cols-[minmax(90px,150px)_1fr_auto] items-center gap-3 text-sm"
          onMouseMove={(e) => { const r = ref.current!.getBoundingClientRect(); setTip({ x: e.clientX - r.left, y: e.clientY - r.top, text: `${d.name}: ${d.biotic} pest-like, ${d.abiotic} drought-like tiles` }) }}>
          <a href={`#/dashboard/scans/${d.id}`} className="link-u truncate">{d.name}</a>
          <span className="flex h-3 gap-[2px]" style={{ width: `${((d.biotic + d.abiotic) / max) * 100}%`, minWidth: 8 }}>
            {d.biotic > 0 && <span className="rounded-l-[4px] bg-hot" style={{ flexGrow: d.biotic }} />}
            {d.abiotic > 0 && <span className="rounded-r-[4px]" style={{ flexGrow: d.abiotic, background: 'var(--stress)' }} />}
          </span>
          <span className="mono w-14 text-right">{d.biotic + d.abiotic}</span>
        </li>
      ))}
      <TipBox tip={tip} />
    </ul>
  )
}

/** Scatter: x = greenness lost, y = GLCM contrast (log). Filled = confirmed by leaf photo, hollow = not yet. */
export function Scatter({ pts }: { pts: { scan_name: string; hotspot: string; vari_drop: number; glcm_contrast: number; confirmed: boolean; label: string | null }[] }) {
  const [ref, w] = useWidth(); const [tip, setTip] = useState<Tip | null>(null)
  const h = 280, m = { l: 48, r: 12, t: 12, b: 40 }, iw = w - m.l - m.r, ih = h - m.t - m.b
  const xs = pts.map((p) => p.vari_drop), maxX = Math.max(0.5, ...xs) * 1.1
  const ly = (c: number) => Math.log10(Math.max(0.1, c)); const minY = -1, maxY = Math.max(1.5, ...pts.map((p) => ly(p.glcm_contrast))) + 0.15
  const X = (v: number) => m.l + (v / maxX) * iw, Y = (c: number) => m.t + ih - ((ly(c) - minY) / (maxY - minY)) * ih
  const yt = [0.1, 1, 10, 100].filter((t) => ly(t) <= maxY)
  return (
    <div ref={ref} className="relative" onMouseLeave={() => setTip(null)}>
      <svg width={w} height={h} role="img" aria-label="Scatter of hotspots: greenness lost against texture contrast">
        {yt.map((t) => <g key={t}><line x1={m.l} x2={w - m.r} y1={Y(t)} y2={Y(t)} stroke="var(--border)" /><text x={m.l - 8} y={Y(t) + 4} textAnchor="end" fontSize="11" fill="var(--muted)" style={{ fontFamily: 'var(--font-mono)' }}>{t}</text></g>)}
        {[0, 0.25, 0.5, 0.75, 1].filter((t) => t <= maxX).map((t) => <text key={t} x={X(t)} y={h - 20} textAnchor="middle" fontSize="11" fill="var(--muted)" style={{ fontFamily: 'var(--font-mono)' }}>{t}</text>)}
        <text x={m.l + iw / 2} y={h - 4} textAnchor="middle" fontSize="11" fill="var(--muted)" style={{ fontFamily: 'var(--font-mono)' }}>VARI DROP (greenness lost vs field)</text>
        <text transform={`translate(12 ${m.t + ih / 2}) rotate(-90)`} textAnchor="middle" fontSize="11" fill="var(--muted)" style={{ fontFamily: 'var(--font-mono)' }}>GLCM CONTRAST (log)</text>
        {pts.map((p, i) => (
          <g key={i} onMouseMove={(e) => { const r = ref.current!.getBoundingClientRect(); setTip({ x: e.clientX - r.left, y: e.clientY - r.top, text: `${p.scan_name} · hotspot ${p.hotspot}: drop ${p.vari_drop}, contrast ${p.glcm_contrast}${p.label ? ' · ' + p.label : ' · awaiting photo'}` }) }}>
            <circle cx={X(p.vari_drop)} cy={Y(p.glcm_contrast)} r={14} fill="transparent" />
            <circle cx={X(p.vari_drop)} cy={Y(p.glcm_contrast)} r={6} fill={p.confirmed ? 'var(--hot)' : 'var(--surface)'} stroke={p.confirmed ? 'var(--surface)' : 'var(--hot)'} strokeWidth={p.confirmed ? 2 : 2} />
          </g>
        ))}
      </svg>
      <TipBox tip={tip} />
    </div>
  )
}
