import { Coins, Sprout, Users } from 'lucide-react'
import Eyebrow from '../components/Eyebrow'
import { Item, Reveal, Stagger } from '../components/Reveal'
import { impact } from '../data/copy'

const icons = { users: Users, coins: Coins, sprout: Sprout }
export default function Impact() {
  return (
    <section id="impact" aria-labelledby="impact-h" className="section">
      <div className="wrap grid gap-16 lg:grid-cols-12">
        <Reveal className="lg:col-span-7">
          <Eyebrow>10 / WHAT CHANGES</Eyebrow>
          <h2 id="impact-h" className="sr-only">Impact</h2>
          <p className="bignum text-hot !text-[clamp(3.5rem,10vw,9rem)]">Up to 80%<span className="block text-ink">less pesticide</span></p>
          <p className="mt-8">Spray only the confirmed hotspots, not the whole field.</p>
          <p className="label mono mt-4 text-muted">ESTIMATED · not yet measured in a field trial</p>
        </Reveal>
        <Stagger className="flex flex-col divide-y divide-line border-y border-line lg:col-span-5 lg:self-end">
          {impact.map((b) => { const Icon = icons[b.icon]; return (
            <Item key={b.title} className="flex gap-5 py-8">
              <Icon aria-hidden size={28} strokeWidth={1.5} className="mt-1 shrink-0 text-canopy" />
              <div><h3>{b.title}</h3><p className="mt-2 text-muted">{b.body}</p></div>
            </Item>
          ) })}
        </Stagger>
      </div>
    </section>
  )
}
