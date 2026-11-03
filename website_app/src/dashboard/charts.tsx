import { Table2, BarChart3 } from 'lucide-react'
import { useRef, useState, type ReactNode } from 'react'

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

interface Tip { x: number; y: number; text: string }
function TipBox({ tip }: { tip: Tip | null }) {
  if (!tip) return null
  return <div role="status" className="label mono pointer-events-none absolute z-10 max-w-[240px] -translate-x-1/2 -translate-y-full rounded-ctl border border-line bg-bg px-3 py-2 text-ink" style={{ left: tip.x, top: tip.y - 10, textTransform: 'none', letterSpacing: '.02em' }}>{tip.text}</div>
}

/** Horizontal bars for a ranked list (one hue; the label carries identity). */
export function BarList({ data, color = 'var(--canopy)' }: { data: { name: string; count: number }[]; color?: string }) {
  const max = Math.max(1, ...data.map((d) => d.count)); const [tip, setTip] = useState<Tip | null>(null); const ref = useRef<HTMLUListElement>(null)
  return (
    <ul ref={ref} className="relative flex flex-col gap-3" onMouseLeave={() => setTip(null)}>
      {data.map((d) => (
        <li key={d.name} className="grid grid-cols-[minmax(90px,150px)_1fr_auto] items-center gap-3 text-sm"
          onMouseMove={(e) => { const r = ref.current!.getBoundingClientRect(); setTip({ x: e.clientX - r.left, y: e.clientY - r.top, text: `${d.name}: ${d.count}` }) }}>
          <span className="truncate">{d.name}</span>
          <span className="h-3 rounded-r-[4px] bg-bg"><span className="block h-full rounded-r-[4px]" style={{ width: `${(d.count / max) * 100}%`, background: color, minWidth: 4 }} /></span>
          <span className="mono w-6 text-right">{d.count}</span>
        </li>
      ))}
      <TipBox tip={tip} />
    </ul>
  )
}
