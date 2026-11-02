import { Code, Link2 } from 'lucide-react'
import { useState } from 'react'
import { Button, TextLink } from '../components/Button'

const cols = [
  { h: 'Product', l: [['Problem', '#problem'], ['How it works', '#how'], ['Dashboard', '#dashboard'], ['Try it on a field', '#try'], ['Open the dashboard', '#/dashboard']] },
  { h: 'Technology', l: [['Why texture', '#why'], ['Under the hood', '#technology'], ['Impact', '#impact']] },
  { h: 'Team', l: [['Team 9Eleven', '#team'], ['Data console', '#/data'], ['API docs', '/docs']] },
]
export default function Footer() {
  const [done, setDone] = useState(false)
  return (
    <footer id="contact" className="border-t border-line pb-10 pt-24">
      <div className="wrap">
        <div className="grid gap-16 lg:grid-cols-12">
          <nav aria-label="Footer" className="grid grid-cols-2 gap-10 sm:grid-cols-3 lg:col-span-7">
            {cols.map((c) => (
              <div key={c.h}><h3 className="label mono !text-xs !font-normal text-muted">{c.h}</h3>
                <ul className="mt-4 flex flex-col gap-3">{c.l.map(([t, h]) => <li key={t}><TextLink href={h}>{t}</TextLink></li>)}</ul></div>
            ))}
          </nav>
          <div className="lg:col-span-5">
            <form onSubmit={(e) => { e.preventDefault(); setDone(true) }} className="flex flex-col gap-3 sm:flex-row">
              <label htmlFor="em" className="sr-only">Email address</label>
              <input id="em" type="email" required placeholder="you@example.com" className="min-w-0 flex-1 rounded-ctl border border-line bg-surface px-4 py-3 text-ink placeholder:text-muted" />
              <Button type="submit" variant="secondary">Get pilot updates</Button>
            </form>
            <p className="label mono mt-3 text-muted" role="status">{done ? 'Thanks. Demo form: nothing is stored yet.' : 'Occasional notes on the field pilot. No spam.'}</p>
            <div className="mt-8 flex gap-3">
              <a href="https://github.com/Hrudhay-H/LeapHack_backup" aria-label="GitHub repository" className="grid h-10 w-10 place-items-center rounded-ctl border border-line hover:border-ink"><Code size={18} strokeWidth={1.5} /></a>
              <a href="https://www.linkedin.com/" aria-label="LinkedIn (team page link to be added)" className="grid h-10 w-10 place-items-center rounded-ctl border border-line hover:border-ink"><Link2 size={18} strokeWidth={1.5} /></a>
            </div>
          </div>
        </div>
        <svg viewBox="0 0 1000 150" aria-hidden className="mt-24 block w-full"><text x="0" y="140" textLength="1000" lengthAdjust="spacingAndGlyphs" fontSize="170" fontWeight="700" fill="var(--text)" style={{ fontFamily: 'var(--font-display)' }}>AEROSCOUT</text></svg>
        <p className="label mono mt-8 text-muted">© 2026 Team 9Eleven · PESCE Mandya</p>
      </div>
    </footer>
  )
}
