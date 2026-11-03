import { AlertTriangle, Check, Circle, Eye, Footprints, X, type LucideIcon } from 'lucide-react'
import type { ReactNode } from 'react'
import type { HotspotStatus, Tier } from '../api'

export const fmtDate = (iso: string) => new Date(iso).toLocaleString(undefined, { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' })
export const ago = (iso: string) => {
  const s = Math.max(0, (Date.now() - new Date(iso).getTime()) / 1000)
  if (s < 60) return 'just now'; if (s < 3600) return `${Math.floor(s / 60)} min ago`; if (s < 86400) return `${Math.floor(s / 3600)} h ago`
  return `${Math.floor(s / 86400)} d ago`
}

export function Panel({ title, sub, action, children, className = '' }: { title?: string; sub?: string; action?: ReactNode; children: ReactNode; className?: string }) {
  return (
    <section className={`rounded-card border border-line bg-surface p-5 ${className}`}>
      {(title || action) && (
        <header className="mb-4 flex items-start justify-between gap-4">
          <div>{title && <h2 className="font-display !text-lg !font-semibold !leading-tight !tracking-tight">{title}</h2>}{sub && <p className="mt-1 text-sm text-muted">{sub}</p>}</div>
          {action}
        </header>
      )}
      {children}
    </section>
  )
}

export function Stat({ label, value, hint, accent, unit }: { label: string; value: string | number; hint?: string; accent?: boolean; unit?: string }) {
  return (
    <div className="bg-surface p-4 sm:p-5">
      <dt className="label mono text-muted">{label}</dt>
      <dd className={`mt-2 font-display text-4xl font-bold leading-none tracking-tight [font-variant-numeric:tabular-nums] ${accent ? 'text-hot' : ''}`}>{value}{unit && <span className="ml-1 text-base font-semibold text-muted">{unit}</span>}</dd>
      {hint && <p className="mt-2 text-xs text-muted">{hint}</p>}
    </div>
  )
}
export const StatGrid = ({ children, cols = 'sm:grid-cols-3 xl:grid-cols-4' }: { children: ReactNode; cols?: string }) => <dl className={`grid grid-cols-2 gap-px overflow-hidden rounded-card border border-line bg-line ${cols}`}>{children}</dl>

const TIER: Record<Tier, { label: string; cls: string; Icon?: LucideIcon }> = {
  red: { label: 'Red', cls: 'border-hot text-hot', Icon: AlertTriangle },
  amber: { label: 'Amber', cls: 'border-ink text-ink' },
  grey_blue: { label: 'Grey', cls: 'border-line text-muted' },
}
export function TierChip({ s }: { s: Tier }) {
  const { label, cls, Icon } = TIER[s]
  return <span className={`label mono inline-flex items-center gap-1 rounded-ctl border px-2 py-1 ${cls}`}>{Icon && <Icon aria-hidden size={12} strokeWidth={1.5} />}{label}</span>
}
export const STATUS_META: Record<HotspotStatus, { label: string; cls: string; Icon: LucideIcon }> = {
  detected: { label: 'Detected', cls: 'border-line text-muted', Icon: Circle },
  assigned: { label: 'Assigned', cls: 'border-ink text-ink', Icon: Footprints },
  inspected: { label: 'Inspected', cls: 'border-ink text-ink', Icon: Eye },
  confirmed: { label: 'Confirmed', cls: 'border-canopy text-canopy', Icon: Check },
  cleared: { label: 'Cleared', cls: 'border-line text-muted', Icon: X },
}
export function StatusChip({ s }: { s: HotspotStatus }) {
  const { label, cls, Icon } = STATUS_META[s]
  return <span className={`label mono inline-flex items-center gap-1 rounded-ctl border px-2 py-1 ${cls}`}><Icon aria-hidden size={12} strokeWidth={1.5} />{label}</span>
}

export function Empty({ title, body, children }: { title: string; body?: string; children?: ReactNode }) {
  return <div className="grid place-items-center rounded-card border border-dashed border-line p-10 text-center"><div><p className="font-display text-xl font-semibold">{title}</p>{body && <p className="mx-auto mt-2 max-w-sm text-muted">{body}</p>}{children && <div className="mt-5">{children}</div>}</div></div>
}
export const PageTitle = ({ children, sub, action }: { children: ReactNode; sub?: string; action?: ReactNode }) => (
  <div className="mb-8 flex flex-wrap items-end justify-between gap-4"><div><h1 className="!text-[clamp(1.75rem,3vw,2.5rem)]">{children}</h1>{sub && <p className="mt-2 text-muted">{sub}</p>}</div>{action}</div>
)
