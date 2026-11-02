import Eyebrow from '../components/Eyebrow'
import { Item, Reveal, Stagger } from '../components/Reveal'
import { team } from '../data/copy'

export default function Team() {
  return (
    <section id="team" aria-labelledby="team-h" className="section">
      <div className="wrap grid gap-16 lg:grid-cols-12">
        <Reveal className="lg:col-span-5">
          <Eyebrow>11 / TEAM 9ELEVEN</Eyebrow>
          <h2 id="team-h">Three students from Mandya.</h2>
          <p className="mt-8">P.E.S College of Engineering, Mandya. We built AeroScout in a weekend because walking a whole field to find a few sick plants seemed like the wrong way round.</p>
          <p className="label mono mt-8 text-muted">Built for LEAP Agritech Hackathon 2026 · GMIT, Mandya · 2–3 November 2026</p>
          <p className="mono mt-4 text-sm">Contact: <span className="text-muted">[team email — to be added]</span></p>
        </Reveal>
        <Stagger as="ul" className="grid gap-px overflow-hidden rounded-card border border-line bg-line lg:col-span-7">
          {team.map((m) => (
            <Item as="li" key={m.name} className="flex items-center gap-6 bg-surface p-6 sm:p-8">
              <span aria-hidden className="grid h-16 w-16 shrink-0 place-items-center rounded-full border border-ink font-display text-xl font-bold">{m.mono}</span>
              <div><p className="font-display text-2xl font-semibold tracking-tight">{m.name}</p><p className="label mono mt-1 text-muted">{m.role}</p><p className="mt-1 text-[15px] text-muted">P.E.S College of Engineering, Mandya</p></div>
            </Item>
          ))}
        </Stagger>
      </div>
    </section>
  )
}
