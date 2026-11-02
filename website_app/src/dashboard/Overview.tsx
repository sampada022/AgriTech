import { Camera, Footprints, ScanLine } from 'lucide-react'
import { useState } from 'react'
import { api } from '../api'
import { Button, ButtonLink } from '../components/Button'
import { BarList, ChartCard, DayBars, LegendItem, StackedBars } from './charts'
import { useStore } from './store'
import { ago, Empty, PageTitle, Panel, SeverityChip, Stat, StatGrid, StateChip } from './ui'

const ICON = { scan: ScanLine, photo: Camera, state: Footprints } as const

export default function Overview() {
  const { stats, scans, refresh, loading, online } = useStore()
  const [busy, setBusy] = useState(false)
  const demo = async () => { setBusy(true); try { const s = await api.create({ sample: 'demo-field-synthetic.jpg', name: 'Demo field', gsd: 1 }); await refresh(); location.hash = `#/dashboard/scans/${s.id}` } catch { setBusy(false) } }

  if (loading) return <p className="text-muted">Loading…</p>
  if (!stats || online === false) return <Empty title="The analysis server is not running" body="Start it, then this page fills in on its own.">
    <p className="mono text-sm">uv run uvicorn backend.app.main:app --port 8000</p></Empty>
  const t = stats.totals
  if (t.scans === 0) return (<><PageTitle sub="Everything about your fields in one place.">Overview</PageTitle>
    <Empty title="No fields analysed yet" body="Upload a drone photo, or run the demo field to see how the dashboard fills in.">
      <div className="flex flex-wrap justify-center gap-3"><Button onClick={demo} disabled={busy}>{busy ? 'Analysing…' : 'Analyse the demo field'}</Button><ButtonLink variant="secondary" href="#/dashboard/scans">Upload a photo</ButtonLink></div></Empty></>)

  const attention = [...scans].filter((s) => s.open > 0).sort((a, b) => b.open - a.open)[0]
  const latest = attention ?? scans.find((s) => s.id === stats.latest_scan_id) ?? scans[0]
  return (
    <>
      <PageTitle sub="What needs attention today, across every field." action={<ButtonLink href="#/dashboard/scans" arrow={false}>Analyse a field</ButtonLink>}>Overview</PageTitle>
      <StatGrid>
        <Stat label="Hotspots to visit" value={t.open} accent hint="New or visited, not yet treated" />
        <Stat label="Fields analysed" value={t.scans} />
        <Stat label="Hotspots found" value={t.hotspots} hint={`${stats.severity.High} high severity`} />
        <Stat label="Awaiting leaf photo" value={t.awaiting_photo} />
        <Stat label="Confirmed by photo" value={t.confirmed} />
        <Stat label="Area flagged" value={t.area_m2} unit="m²" hint="Assumes the cm-per-pixel you entered" />
        <Stat label="Walk planned" value={t.route_m} unit="m" />
        <Stat label="Treated" value={stats.states.treated} hint={`${stats.states.dismissed} dismissed as false alarms`} />
      </StatGrid>

      <div className="mt-8 grid items-start gap-6 lg:grid-cols-12">
        <Panel className="lg:col-span-7" title="Priority queue" sub="Highest severity first. Open a hotspot to act on it."
          action={<a href="#/dashboard/tasks" className="link-u text-sm font-medium">All field tasks</a>}>
          {stats.queue.length === 0 ? <p className="text-muted">Nothing waiting. Every hotspot is treated or dismissed.</p> : (
            <div className="overflow-x-auto"><table className="w-full min-w-[520px] text-left text-sm">
              <thead><tr className="border-b border-ink">{['Field', 'Hotspot', 'Severity', 'Area', 'State', ''].map((h) => <th key={h} className="label mono py-2 pr-3 font-normal text-muted">{h}</th>)}</tr></thead>
              <tbody>{stats.queue.slice(0, 7).map((q) => (
                <tr key={q.scan_id + q.hotspot} className="border-b border-line">
                  <td className="max-w-[160px] truncate py-3 pr-3">{q.scan_name}</td><td className="mono pr-3">{q.hotspot}{q.route_stop ? ` · stop ${q.route_stop}` : ''}</td>
                  <td className="pr-3"><SeverityChip s={q.severity} /></td><td className="mono pr-3">{q.area_m2} m²</td><td className="pr-3"><StateChip s={q.state} /></td>
                  <td><a href={`#/dashboard/scans/${q.scan_id}`} className="link-u text-sm font-medium">Open</a></td></tr>))}</tbody></table></div>
          )}
        </Panel>

        {latest && (
          <Panel className="lg:col-span-5" title={attention ? 'Needs attention' : 'Latest field'} sub={`${latest.name} · ${ago(latest.created_at)}`} action={<a href={`#/dashboard/scans/${latest.id}`} className="link-u text-sm font-medium">Open</a>}>
            <a href={`#/dashboard/scans/${latest.id}`} className="block overflow-hidden rounded-card border border-line">
              <img src={latest.files.overlay} alt={`Latest scan ${latest.name} with hotspots marked`} loading="lazy" className="block w-full" /></a>
            <p className="mono mt-3 text-sm text-muted">{latest.hotspots} hotspot{latest.hotspots === 1 ? '' : 's'} · {latest.open} open · {latest.route_m ?? 0} m walk</p>
          </Panel>
        )}

        <div className="lg:col-span-7"><ChartCard title="Hotspots found, last 14 days" head={['Date', 'Hotspots', 'Scans']} rows={stats.by_day.map((d) => [d.date, d.hotspots, d.scans])}>
          <DayBars data={stats.by_day} field="hotspots" label="Hotspots" /></ChartCard></div>

        <div className="lg:col-span-5"><ChartCard title="Pests confirmed by leaf photo" sub="Species named by the scout" head={['Species', 'Photos']} rows={stats.species.map((s) => [s.name, s.count])}>
          {stats.species.length ? <BarList data={stats.species} /> : <p className="text-muted">No leaf photos yet. Walk to a hotspot and add one.</p>}</ChartCard></div>

        <Panel className="lg:col-span-5" title="Recent activity">
          <ul className="flex flex-col divide-y divide-line">
            {stats.activity.map((a, i) => { const Icon = ICON[a.kind]; return (
              <li key={i} className="flex gap-3 py-3 text-sm"><Icon aria-hidden size={16} strokeWidth={1.5} className="mt-0.5 shrink-0 text-muted" />
                <div className="min-w-0 flex-1"><a href={`#/dashboard/scans/${a.scan_id}`} className="link-u">{a.text}</a></div><span className="label mono shrink-0 text-muted">{ago(a.t)}</span></li>) })}
          </ul>
        </Panel>

        <div className="lg:col-span-7"><ChartCard title="Pest-like vs drought-like tiles" sub="Per field. Same colour on the map can have a different cause."
          head={['Field', 'Pest-like', 'Drought-like']} rows={stats.per_scan.map((s) => [s.name, s.biotic_tiles, s.abiotic_tiles])}
          legend={<><LegendItem swatch={<i className="block h-3 w-3 rounded-[3px] bg-hot" />}>Pest-like (ragged)</LegendItem><LegendItem swatch={<i className="block h-3 w-3 rounded-[3px]" style={{ background: 'var(--stress)' }} />}>Drought-like (even fade)</LegendItem></>}>
          <StackedBars data={stats.per_scan.slice(0, 8).map((s) => ({ id: s.id, name: s.name, biotic: s.biotic_tiles, abiotic: s.abiotic_tiles }))} /></ChartCard></div>
      </div>
    </>
  )
}
