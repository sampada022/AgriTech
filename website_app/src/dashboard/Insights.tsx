import { useEffect, useState } from 'react'
import { modelApi, type ModelVersionOut } from '../api'
import { BarList, ChartCard } from './charts'
import { useStore } from './store'
import { Empty, PageTitle, Panel } from './ui'

export default function Insights() {
  const { model } = useStore()
  const [history, setHistory] = useState<ModelVersionOut[]>([])
  useEffect(() => { modelApi.history().then((h) => setHistory(h.versions)).catch(() => {}) }, [model?.version])

  if (!model) return (<><PageTitle sub="How the model separates pests from drought.">Insights</PageTitle><Empty title="Nothing to analyse yet" body="Insights appear once the model is loaded." /></>)
  const cues = [...model.cues].sort((a, b) => Math.abs(model.weights[b.name]) - Math.abs(model.weights[a.name]))

  return (
    <>
      <PageTitle sub="How the model separates pests from drought, and what it has learnt from confirmed labels.">Insights</PageTitle>
      <div className="grid gap-6 lg:grid-cols-12">
        <Panel className="lg:col-span-7" title="Cue weights" sub="Seven cues feed one logistic model. A biotic cue pushes the score up; an abiotic cue pushes it down.">
          <ul className="flex flex-col divide-y divide-line">
            {cues.map((c) => {
              const w = model.weights[c.name], prior = model.prior_weights[c.name]
              return (
                <li key={c.name} className="py-3">
                  <div className="flex items-center justify-between gap-3">
                    <span className="mono text-sm">{c.name}</span>
                    <span className={`label mono ${c.direction === 'biotic' ? 'text-hot' : 'text-muted'}`}>{c.direction}</span>
                  </div>
                  <div className="mt-1 flex items-center gap-3">
                    <span className="h-2 flex-1 rounded-ctl bg-line"><span className="block h-full rounded-ctl" style={{ width: `${Math.min(100, Math.abs(w) / 2 * 100)}%`, background: c.direction === 'biotic' ? 'var(--hot)' : 'var(--muted)', marginLeft: w < 0 ? 'auto' : 0 }} /></span>
                    <span className="mono w-16 text-right text-sm">{w.toFixed(2)}</span>
                  </div>
                  <p className="mt-1 text-xs text-muted">{c.rationale} {Math.abs(w - prior) > 0.01 && <span className="text-ink">Moved from prior {prior.toFixed(2)}.</span>}</p>
                </li>
              )
            })}
          </ul>
        </Panel>

        <Panel className="lg:col-span-5" title="Recalibration" sub={model.recalibration_note}>
          <p className="font-display text-5xl font-bold [font-variant-numeric:tabular-nums]">v{model.version}</p>
          <p className="mt-1 text-muted">{model.label_count} confirmed label{model.label_count === 1 ? '' : 's'}. {model.agreement != null ? `${Math.round(model.agreement * 100)}% training-set agreement.` : 'No labels yet, so the model is still the prior.'}</p>
          {model.false_positive.count > 0 && <p className="mt-3 rounded-ctl border border-line bg-bg p-3 text-sm">{model.false_positive.count} false alarm{model.false_positive.count === 1 ? '' : 's'} confirmed. {model.false_positive.hint}</p>}
        </Panel>

        <div className="lg:col-span-12"><ChartCard title="Version history" sub="Each confirmed label nudges the weights toward the ground truth, regularised toward the prior."
          head={['Version', 'Labels', 'Agreement', 'Created']} rows={history.map((v) => [`v${v.version}`, v.label_count, v.agreement != null ? `${Math.round(v.agreement * 100)}%` : '—', v.created_at ? new Date(v.created_at).toLocaleString() : '—'])}>
          {history.length <= 1 ? <p className="text-muted">Only the prior exists so far. Confirm a hotspot's ground truth to create v2.</p> : (
            <BarList data={history.map((v) => ({ name: `v${v.version}`, count: Math.round((v.agreement ?? 0) * 100) }))} />
          )}
        </ChartCard></div>
      </div>
    </>
  )
}
