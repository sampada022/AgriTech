import { useState } from 'react'
import { demoApi } from '../api'
import { Button, ButtonLink } from '../components/Button'
import { useStore } from './store'
import { Empty, PageTitle, Panel, Stat, StatGrid, TierChip } from './ui'

export default function Overview() {
  const { fields, totals, model, refresh, loading, online } = useStore()
  const [busy, setBusy] = useState(false)
  const demo = async () => { setBusy(true); try { const d = await demoApi.load('mixed'); await refresh(); location.hash = `#/dashboard/scans/${d.scan_id}` } catch { setBusy(false) } }

  if (loading) return <p className="text-muted">Loading…</p>
  if (online === false) return <Empty title="The analysis server is not running" body="Start it, then this page fills in on its own.">
    <p className="mono text-sm">cd apps/api && uvicorn app.main:app --port 8000</p></Empty>
  if (totals.fields === 0) return (<><PageTitle sub="Everything about your fields in one place.">Overview</PageTitle>
    <Empty title="No fields analysed yet" body="Upload a drone photo, or load the mixed-stress demo scenario to see how the dashboard fills in.">
      <div className="flex flex-wrap justify-center gap-3"><Button onClick={demo} disabled={busy}>{busy ? 'Loading…' : 'Load the demo scenario'}</Button><ButtonLink variant="secondary" href="#/dashboard/scans">Upload a photo</ButtonLink></div></Empty></>)

  const sorted = [...fields].sort((a, b) => {
    const open = (f: typeof a) => (f.scan?.kpis ? f.scan.kpis.tier_counts.red + f.scan.kpis.tier_counts.amber : -1)
    return open(b) - open(a)
  })
  const attention = sorted.find((f) => f.scan?.kpis && f.scan.kpis.tier_counts.red + f.scan.kpis.tier_counts.amber > 0)
  const latest = attention ?? sorted[0]
  const latestImg = latest?.scan?.layers.heat?.url ?? latest?.scan?.layers.rgb?.url

  return (
    <>
      <PageTitle sub="What needs attention today, across every field." action={<ButtonLink href="#/dashboard/scans" arrow={false}>Analyse a field</ButtonLink>}>Overview</PageTitle>
      <StatGrid>
        <Stat label="Hotspots to visit" value={totals.open} accent hint="Red or amber, not yet cleared" />
        <Stat label="Fields analysed" value={totals.fields} />
        <Stat label="Hotspots found" value={totals.hotspots} />
        <Stat label="Still running" value={totals.running} hint={totals.failed ? `${totals.failed} failed` : undefined} />
        <Stat label="Area flagged" value={Math.round(totals.area_flagged_m2)} unit="m²" />
        <Stat label="Walk planned" value={Math.round(totals.route_m)} unit="m" />
        <Stat label="Model version" value={model?.version ?? 1} hint={model?.is_prior ? 'Still the priors' : `${model?.label_count ?? 0} labels`} />
        <Stat label="Training agreement" value={model?.agreement != null ? `${Math.round(model.agreement * 100)}%` : '—'} />
      </StatGrid>

      <div className="mt-8 grid items-start gap-6 lg:grid-cols-12">
        <Panel className="lg:col-span-7" title="Priority queue" sub="Highest tier first. Open a field to act on its hotspots."
          action={<a href="#/dashboard/tasks" className="link-u text-sm font-medium">All field tasks</a>}>
          {sorted.every((f) => !f.scan?.kpis || f.scan.kpis.hotspot_count === 0) ? <p className="text-muted">Nothing waiting. Every field looks healthy or is still being scanned.</p> : (
            <div className="overflow-x-auto"><table className="w-full min-w-[520px] text-left text-sm">
              <thead><tr className="border-b border-ink">{['Field', 'Tiers', 'Area flagged', 'Status', ''].map((h) => <th key={h} className="label mono py-2 pr-3 font-normal text-muted">{h}</th>)}</tr></thead>
              <tbody>{sorted.filter((f) => f.scan?.kpis && f.scan.kpis.hotspot_count > 0).slice(0, 7).map((f) => (
                <tr key={f.id} className="border-b border-line">
                  <td className="max-w-[160px] truncate py-3 pr-3">{f.name}</td>
                  <td className="pr-3">{(['red', 'amber', 'grey_blue'] as const).filter((t) => (f.scan!.kpis!.tier_counts[t] ?? 0) > 0).map((t) => <span key={t} className="mr-1 inline-flex items-center gap-1"><TierChip s={t} /><span className="mono text-xs">×{f.scan!.kpis!.tier_counts[t]}</span></span>)}</td>
                  <td className="mono pr-3">{Math.round(f.scan!.kpis!.area_flagged_m2)} m²</td>
                  <td className="mono pr-3 capitalize">{f.scan?.status}</td>
                  <td><a href={`#/dashboard/scans/${f.latest_scan!.id}`} className="link-u text-sm font-medium">Open</a></td></tr>))}</tbody></table></div>
          )}
        </Panel>

        {latest && (
          <Panel className="lg:col-span-5" title={attention ? 'Needs attention' : 'Latest field'} sub={latest.name} action={latest.latest_scan && <a href={`#/dashboard/scans/${latest.latest_scan.id}`} className="link-u text-sm font-medium">Open</a>}>
            {latestImg ? (
              <a href={latest.latest_scan ? `#/dashboard/scans/${latest.latest_scan.id}` : '#'} className="block overflow-hidden rounded-card border border-line">
                <img src={latestImg} alt={`Latest scan of ${latest.name}`} loading="lazy" className="block w-full" /></a>
            ) : <p className="text-muted">No layers yet.</p>}
            <p className="mono mt-3 text-sm text-muted">{latest.scan?.kpis?.hotspot_count ?? 0} hotspot{latest.scan?.kpis?.hotspot_count === 1 ? '' : 's'} · {Math.round(latest.scan?.kpis?.route_distance_m ?? 0)} m walk</p>
          </Panel>
        )}

        <Panel className="lg:col-span-5" title="Hotspots by tier" sub="Across every field">
          <ul className="flex flex-col divide-y divide-line">{(['red', 'amber', 'grey_blue'] as const).map((k) => <li key={k} className="flex items-center justify-between py-3"><TierChip s={k} /><span className="font-display text-3xl font-bold [font-variant-numeric:tabular-nums]">{totals.tiers[k]}</span></li>)}</ul>
          <p className="mt-3 text-sm text-muted">Red needs both biotic evidence and a strong anomaly. Grey is informational — usually water or nutrient stress, not pest.</p>
        </Panel>

        <Panel className="lg:col-span-7" title="Model recalibration" sub={model?.recalibration_note}>
          {model ? (
            <>
              <p className="font-display text-4xl font-bold [font-variant-numeric:tabular-nums]">v{model.version}</p>
              <p className="mt-1 text-sm text-muted">{model.label_count} confirmed label{model.label_count === 1 ? '' : 's'} · {model.agreement != null ? `${Math.round(model.agreement * 100)}% training agreement` : 'no labels yet'}</p>
              {model.false_positive.hint && <p className="mt-3 rounded-ctl border border-line bg-bg p-3 text-sm">{model.false_positive.hint}</p>}
            </>
          ) : <p className="text-muted">Loading…</p>}
        </Panel>
      </div>
    </>
  )
}
