import { api, type DataOverview } from '../api'
import { useEffect, useState } from 'react'
import { ChartCard, LegendItem, Scatter, StackedBars } from './charts'
import { useStore } from './store'
import { Empty, PageTitle, Panel, SeverityChip } from './ui'

export default function Insights() {
  const { stats } = useStore(); const [data, setData] = useState<DataOverview | null>(null)
  useEffect(() => { api.data().then(setData).catch(() => {}) }, [stats?.totals.photos])
  if (!stats || stats.points.length === 0) return (<><PageTitle sub="How the model separates pests from drought.">Insights</PageTitle><Empty title="Nothing to analyse yet" body="Insights appear once a field has at least one hotspot." /></>)
  const conf = stats.points.filter((p) => p.confirmed).length
  return (
    <>
      <PageTitle sub="How the model separates pests from drought, and what it has learnt from leaf photos.">Insights</PageTitle>
      <div className="grid gap-6 lg:grid-cols-12">
        <div className="lg:col-span-7"><ChartCard title="Every hotspot: greenness lost vs texture" sub="Pest damage sits high on texture contrast. Drought fades sit low and are dismissed before this chart."
          head={['Field', 'Hotspot', 'VARI drop', 'Contrast', 'Label']} rows={stats.points.map((p) => [p.scan_name, p.hotspot, p.vari_drop, p.glcm_contrast, p.label ?? 'awaiting photo'])}
          legend={<><LegendItem swatch={<i className="block h-3 w-3 rounded-full bg-hot" />}>Confirmed by leaf photo ({conf})</LegendItem><LegendItem swatch={<i className="block h-3 w-3 rounded-full border-2 border-hot" />}>Awaiting photo ({stats.points.length - conf})</LegendItem></>}>
          <Scatter pts={stats.points} /></ChartCard></div>
        <Panel className="lg:col-span-5" title="Severity" sub="Across all fields">
          <ul className="flex flex-col divide-y divide-line">{(['High', 'Medium', 'Low'] as const).map((k) => <li key={k} className="flex items-center justify-between py-3"><SeverityChip s={k} /><span className="font-display text-3xl font-bold [font-variant-numeric:tabular-nums]">{stats.severity[k]}</span></li>)}</ul>
          <p className="mt-3 text-sm text-muted">Severity blends how much greenness is lost with how large the cluster is. It ranks work; it is not a yield loss estimate.</p>
        </Panel>
        <div className="lg:col-span-7"><ChartCard title="Pest-like vs drought-like tiles" head={['Field', 'Pest-like', 'Drought-like']} rows={stats.per_scan.map((s) => [s.name, s.biotic_tiles, s.abiotic_tiles])}
          legend={<><LegendItem swatch={<i className="block h-3 w-3 rounded-[3px] bg-hot" />}>Pest-like</LegendItem><LegendItem swatch={<i className="block h-3 w-3 rounded-[3px]" style={{ background: 'var(--stress)' }} />}>Drought-like</LegendItem></>}>
          <StackedBars data={stats.per_scan.slice(0, 10).map((s) => ({ id: s.id, name: s.name, biotic: s.biotic_tiles, abiotic: s.abiotic_tiles }))} /></ChartCard></div>
        <Panel className="lg:col-span-5" title="Learning from the field" sub={data?.note}>
          <p className="font-display text-5xl font-bold [font-variant-numeric:tabular-nums]">{data?.counts.labelled_examples ?? 0}</p>
          <p className="mt-1 text-muted">labelled examples saved (leaf photos with a named species). Each stores that hotspot’s greenness and texture numbers so a later retraining run can use them.</p>
          <a href="#/dashboard/data" className="link-u mt-4 text-sm font-medium">See the examples</a>
        </Panel>
      </div>
    </>
  )
}
