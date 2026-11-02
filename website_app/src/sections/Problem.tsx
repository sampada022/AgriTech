import Eyebrow from '../components/Eyebrow'
import { Item, Reveal, Stagger } from '../components/Reveal'
import StatCounter from '../components/StatCounter'
import { stats } from '../data/copy'

export default function Problem() {
  return (
    <section id="problem" aria-labelledby="problem-h" className="section">
      <div className="wrap">
        <Reveal className="max-w-3xl">
          <Eyebrow>02 / THE PROBLEM</Eyebrow>
          <h2 id="problem-h">Pests start small. Scouting on foot starts late.</h2>
        </Reveal>
        <Stagger as="dl" className="mt-16 grid border-y border-line sm:grid-cols-2 lg:mt-24 lg:grid-cols-4">
          {stats.map((s, i) => (
            <Item key={s.label} className={`flex flex-col justify-between gap-6 border-line py-10 sm:px-6 ${i > 0 ? 'lg:border-l' : 'lg:pr-6'} ${i % 2 === 1 ? 'sm:border-l lg:border-l' : ''} ${i > 1 ? 'sm:border-t lg:border-t-0' : ''} ${i === 1 ? 'border-t sm:border-t-0' : i > 0 ? 'border-t sm:border-t-0' : ''}`}>
              <dt className={`flex items-baseline gap-2 whitespace-nowrap ${s.accent ? 'text-hot' : ''}`}>
                {s.text ? <span className="bignum !text-[clamp(2.5rem,4.6vw,4.5rem)]">{s.display}</span>
                  : <><StatCounter value={s.value} suffix={s.suffix} display={s.display.replace(' ' + s.unit, '')} className="!text-[clamp(2.5rem,4.6vw,4.5rem)]" />
                    {s.unit && <span className="font-display text-xl font-semibold text-ink">{s.unit}</span>}</>}
              </dt>
              <dd className="max-w-[24ch] text-muted">{s.label}</dd>
            </Item>
          ))}
        </Stagger>
        <Reveal>
          <p className="label mono mt-6 max-w-3xl normal-case tracking-wide text-muted" style={{ textTransform: 'none' }}>
            Yield-loss figures: team-supplied, source to be confirmed before launch. Background reading:{' '}
            <a className="link-u text-ink" href="https://www.fao.org/plant-health-2020/about/en/" target="_blank" rel="noreferrer">FAO, International Year of Plant Health</a>.
          </p>
        </Reveal>
      </div>
    </section>
  )
}
