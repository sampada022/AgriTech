import gsap from 'gsap'
import { ScrollTrigger } from 'gsap/ScrollTrigger'
import { Check, Clock, MapPin, Route as RouteIcon } from 'lucide-react'
import { useEffect, useRef } from 'react'
import Eyebrow from '../components/Eyebrow'
import FieldMap from '../components/FieldMap'
import { Reveal } from '../components/Reveal'
import { hotspots } from '../data/field'
import { useDesktop, useReduced } from '../hooks/useMedia'

gsap.registerPlugin(ScrollTrigger)
const sevCls = { High: 'text-hot', Medium: 'text-ink', Low: 'text-muted' }

export default function Dashboard() {
  const mock = useRef<HTMLDivElement>(null), shadow = useRef<HTMLDivElement>(null), reduced = useReduced(), desktop = useDesktop()
  useEffect(() => {
    if (reduced) return
    const ctx = gsap.context(() => {
      const st = { trigger: mock.current, start: 'top 95%', end: 'top 35%', scrub: .6 }
      gsap.fromTo(mock.current, { rotateX: desktop ? 14 : 6, rotateZ: desktop ? -4 : -2, y: 40 }, { rotateX: 0, rotateZ: 0, y: 0, ease: 'none', scrollTrigger: st })
      gsap.fromTo(shadow.current, { opacity: 1 }, { opacity: .35, ease: 'none', scrollTrigger: st })
    })
    return () => ctx.revert()
  }, [reduced, desktop])
  return (
    <section id="dashboard" aria-labelledby="dash-h" className="section overflow-x-clip">
      <div className="wrap">
        <Reveal className="max-w-3xl"><Eyebrow>08 / THE DASHBOARD</Eyebrow><h2 id="dash-h">One screen. Three places to go.</h2>
          <p className="mt-6">The scout sees the map, the hotspots in order of severity, and the walking route. Everything shown here is sample data.</p></Reveal>
        <div className="mt-16 [perspective:1600px]">
          <div ref={mock} className="no-tr relative [transform-style:preserve-3d]">
            <div ref={shadow} aria-hidden className="no-tr absolute inset-0 rounded-card shadow-float" />
            <div className="relative overflow-hidden rounded-card border border-line bg-surface">
              <div className="flex items-center justify-between border-b border-line px-5 py-3">
                <span className="flex items-center gap-3"><span className="flex gap-1.5" aria-hidden>{[0, 1, 2].map((i) => <i key={i} className="block h-2.5 w-2.5 rounded-full border border-line" />)}</span><span className="label mono">AeroScout · Field 07 · Mandya</span></span>
                <span className="label mono text-muted">SAMPLE DATA</span>
              </div>
              <div className="grid gap-6 p-5 lg:grid-cols-12">
                <div className="lg:col-span-7"><FieldMap route={1} mode="class" label="Dashboard field map with three red hotspots and a dashed walking route." hud={{ alt: '35.0 M', vari: '0.21', entropy: '4.8', hotspots: '03' }} /></div>
                <div className="flex flex-col gap-4 lg:col-span-5">
                  <h3 className="label mono text-muted">Hotspots</h3>
                  <ul className="flex flex-col gap-3">
                    {hotspots.map((h) => (
                      <li key={h.id} className="rounded-ctl border border-line p-4">
                        <div className="flex items-center justify-between"><span className="flex items-center gap-2 font-display text-lg font-semibold"><MapPin aria-hidden size={16} strokeWidth={1.5} className="text-hot" />{h.name}</span><span className="mono text-sm">{h.area}</span></div>
                        <div className="mt-2 flex flex-wrap items-center gap-2">
                          <span className={`label mono ${sevCls[h.severity]}`}>Severity: {h.severity}</span>
                          <span className={`label mono inline-flex items-center gap-1 rounded-ctl border px-2 py-1 ${h.confirmed ? 'border-canopy text-canopy' : 'border-line text-muted'}`}>
                            {h.confirmed ? <Check aria-hidden size={12} strokeWidth={1.5} /> : <Clock aria-hidden size={12} strokeWidth={1.5} />}{h.status}</span>
                        </div>
                      </li>
                    ))}
                  </ul>
                  <div className="mt-auto flex items-center gap-3 rounded-ctl bg-bg p-4"><RouteIcon aria-hidden size={20} strokeWidth={1.5} /><div><p className="label mono text-muted">Route</p><p className="mono">1.2 km · 3 stops · ~25 min walk</p></div></div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  )
}
