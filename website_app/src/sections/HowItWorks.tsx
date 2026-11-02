import gsap from 'gsap'
import { ScrollTrigger } from 'gsap/ScrollTrigger'
import { useEffect, useRef, useState } from 'react'
import Eyebrow from '../components/Eyebrow'
import FieldMap from '../components/FieldMap'
import Phone from '../components/Phone'
import { Reveal } from '../components/Reveal'
import { steps } from '../data/copy'
import { useDesktop, useReduced } from '../hooks/useMedia'

gsap.registerPlugin(ScrollTrigger)

function StepVisual({ step }: { step: number }) {
  const reduced = useReduced()
  const [dismiss, setDismiss] = useState(0), [route, setRoute] = useState(0)
  useEffect(() => {
    setDismiss(0); setRoute(0)
    if (step === 2) { const t = setTimeout(() => setDismiss(1), reduced ? 0 : 700); return () => clearTimeout(t) }
    if (step === 3) {
      if (reduced) { setDismiss(1); setRoute(1); return }
      setDismiss(1); const p = { r: 0 }; const tw = gsap.to(p, { r: 1, duration: 2, ease: 'power2.inOut', delay: .3, onUpdate: () => setRoute(p.r) })
      return () => { tw.kill() }
    }
    if (step >= 4) setDismiss(1)
  }, [step, reduced])
  const mode = step === 1 ? 'index' : 'class'
  return (
    <div className="relative">
      <FieldMap mode={mode} dismiss={step === 3 ? 1 : dismiss} route={route} outline={step >= 2} tileGrid={step === 1} className="w-full"
        label={['', 'Field map cut into tiles, coloured by vegetation index from green to amber to red.', 'Field map where amber drought patches fade out and three red pest clusters are outlined.', 'Field map with a dashed walking route from the farmhouse through the three hotspots.', 'Field map dimmed behind a phone.'][step]}
        hud={{ alt: step === 4 ? '0.3 M' : '35.0 M', vari: '0.21', entropy: step === 1 ? '—' : '4.8', hotspots: step === 1 ? '—' : '03' }} />
      {step === 1 && (
        <div className="mt-4 flex items-center gap-3"><span className="label mono text-muted">VARI</span>
          <span aria-hidden className="h-2 flex-1 rounded-ctl" style={{ background: 'linear-gradient(to right, var(--canopy), var(--stress), var(--hot))' }} />
          <span className="label mono text-muted">low → high stress</span></div>
      )}
      {step === 3 && <p className="label mono absolute right-5 top-14 z-20 rounded-ctl border border-line bg-surface px-3 py-2 text-ink" style={{ opacity: route }}>1.2 km <span className="text-muted">instead of 50 acres</span></p>}
      {step === 4 && <div className="absolute inset-0 z-20 grid place-items-center rounded-card bg-bg/80 p-4"><Phone className="scale-90" /></div>}
    </div>
  )
}

export default function HowItWorks() {
  const desktop = useDesktop(), reduced = useReduced()
  const [active, setActive] = useState(1)
  const list = useRef<HTMLOListElement>(null), fill = useRef<HTMLDivElement>(null)
  useEffect(() => {
    if (!desktop) return
    const ctx = gsap.context(() => {
      list.current!.querySelectorAll<HTMLElement>('[data-step]').forEach((el, i) => {
        ScrollTrigger.create({ trigger: el, start: 'top 55%', end: 'bottom 55%', onToggle: (s) => { if (s.isActive) setActive(i + 1) } })
      })
      if (!reduced) gsap.fromTo(fill.current, { scaleY: 0 }, { scaleY: 1, ease: 'none', scrollTrigger: { trigger: list.current, start: 'top 55%', end: 'bottom 55%', scrub: true } })
      else gsap.set(fill.current, { scaleY: 1 })
    })
    return () => ctx.revert()
  }, [desktop, reduced])
  return (
    <section id="how" aria-labelledby="how-h" className="section">
      <div className="wrap">
        <Reveal className="max-w-3xl"><Eyebrow>05 / HOW IT WORKS</Eyebrow><h2 id="how-h">From the sky to the leaf, in four steps.</h2></Reveal>
        <div className="mt-16 grid gap-12 lg:grid-cols-12 lg:gap-16">
          {desktop && (
            <div className="lg:col-span-6">
              <div className="sticky top-28" aria-live="polite"><StepVisual step={active} />
                <p className="label mono mt-4 text-muted">STEP 0{active} / 04 · {steps[active - 1].readout}</p></div>
            </div>
          )}
          <div className={`relative ${desktop ? 'lg:col-span-6 pl-10' : ''}`}>
            {desktop && <><div aria-hidden className="absolute bottom-0 left-0 top-0 w-px bg-line" /><div ref={fill} aria-hidden className="no-tr absolute bottom-0 left-0 top-0 w-px origin-top bg-hot" style={{ width: 2 }} /></>}
            <ol ref={list} className="flex flex-col gap-16 lg:gap-0">
              {steps.map((s, i) => (
                <li key={s.n} data-step className={`lg:flex lg:min-h-[80vh] lg:flex-col lg:justify-center lg:transition-opacity ${desktop && active !== i + 1 ? 'opacity-40' : ''}`}>
                  <span className={`label mono ${desktop && active === i + 1 ? 'text-hot' : 'text-muted'}`}>STEP {s.n}</span>
                  <h3 className="mt-3 !text-3xl">{s.title}</h3>
                  <p className="mt-4">{s.body}</p>
                  {!desktop && <div className="mt-8"><StepVisual step={i + 1} /><p className="label mono mt-3 text-muted">{s.readout}</p></div>}
                </li>
              ))}
            </ol>
          </div>
        </div>
      </div>
    </section>
  )
}
