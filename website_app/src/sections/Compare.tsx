import { Check, Minus, X } from 'lucide-react'
import Eyebrow from '../components/Eyebrow'
import { Reveal } from '../components/Reveal'
import { compareCols, compareRows, type Rating } from '../data/copy'

const R: Record<Rating, { Icon: typeof Check; text: string; cls: string }> = {
  yes: { Icon: Check, text: 'Yes', cls: 'text-canopy' },
  partial: { Icon: Minus, text: 'Partly', cls: 'text-stress' },
  no: { Icon: X, text: 'No', cls: 'text-muted' },
}
export default function Compare() {
  return (
    <section aria-labelledby="cmp-h" className="section">
      <div className="wrap">
        <Reveal className="max-w-3xl"><Eyebrow>04 / WHAT FARMERS USE TODAY</Eyebrow><h2 id="cmp-h">Each tool answers one question. None answers all four.</h2></Reveal>
        <Reveal className="mt-16 overflow-x-auto">
          <table className="w-full min-w-[760px] border-collapse text-left">
            <caption className="sr-only">Comparison of scouting methods against four needs</caption>
            <thead>
              <tr className="border-b border-ink">
                <th scope="col" className="label py-4 pr-4 font-normal text-muted">Method</th>
                {compareCols.map((c) => <th key={c} scope="col" className="label py-4 pr-4 align-bottom font-normal text-muted">{c}</th>)}
              </tr>
            </thead>
            <tbody>
              {compareRows.map((r) => (
                <tr key={r.name} className={`border-b border-line ${r.hero ? 'bg-surface' : ''}`}>
                  <th scope="row" className={`py-5 pr-4 pl-0 font-display text-xl font-semibold ${r.hero ? 'border-l-2 border-hot pl-4' : ''}`}>{r.name}</th>
                  {r.ratings.map((k, i) => { const { Icon, text, cls } = R[k]; return (
                    <td key={i} className="py-5 pr-4"><span className={`inline-flex items-center gap-2 ${cls}`}><Icon aria-hidden size={18} strokeWidth={1.5} /><span className="label mono text-ink">{text}</span></span></td>
                  ) })}
                </tr>
              ))}
            </tbody>
          </table>
        </Reveal>
        <Reveal className="mt-16 max-w-4xl"><p className="font-display max-w-none text-[clamp(1.5rem,2.8vw,2.5rem)] font-semibold leading-tight tracking-tight">
          No one connects what the drone sees from the sky with what the farmer can confirm on the ground. <span className="underline decoration-hot decoration-2 underline-offset-8">That’s the gap.</span></p></Reveal>
        <p className="label mono mt-6 text-muted">Ratings are the team’s own assessment, not measured benchmarks.</p>
      </div>
    </section>
  )
}
