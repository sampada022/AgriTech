import { motion } from 'framer-motion'
import gsap from 'gsap'
import { ScrollTrigger } from 'gsap/ScrollTrigger'
import { useEffect, useRef, useState } from 'react'
import { ButtonLink, TextLink } from '../components/Button'
import Eyebrow from '../components/Eyebrow'
import FieldMap from '../components/FieldMap'
import Leaf from '../components/Leaf'
import { VB_H, VB_W, hotspots } from '../data/field'
import { useDesktop, useReduced } from '../hooks/useMedia'
import { useIntro } from '../hooks/intro'
import { EASE } from '../lib'

gsap.registerPlugin(ScrollTrigger)
const LINES = ['Find the three', 'sick patches.', 'Skip the fifty', 'healthy acres.']
const target = hotspots[1]

export default function Hero() {
  const desktop = useDesktop(), reduced = useReduced(), ready = useIntro()
  const sec = useRef<HTMLElement>(null), zoomG = useRef<SVGGElement>(null), fadeG = useRef<SVGGElement>(null)
  const leaf = useRef<HTMLDivElement>(null), card = useRef<HTMLDivElement>(null), hint = useRef<HTMLDivElement>(null)
  const tlRef = useRef<gsap.core.Timeline | null>(null)
  const [scan, setScan] = useState(reduced ? 1 : 0), [route, setRoute] = useState(reduced ? 1 : 0), [alt, setAlt] = useState(35)
  const [zoomed, setZoomed] = useState(false)

  // Intro: scan sweep, then walking route draws itself.
  useEffect(() => {
    if (reduced) { setScan(1); setRoute(1); return }
    if (!ready) return
    const p = { scan: 0, route: 0 }
    const tl = gsap.timeline({ delay: .5 })
    tl.to(p, { scan: 1, duration: 4.2, ease: 'none', onUpdate: () => setScan(Math.round(p.scan * 200) / 200) })
      .to(p, { route: 1, duration: 1.8, ease: 'power2.inOut', onUpdate: () => setRoute(Math.round(p.route * 200) / 200) }, '+=.2')
    return () => { tl.kill() }
  }, [reduced, ready])

  // Descent: zoom to one hotspot, ALT 35.0 -> 0.3 M, grid dissolves to leaf, card slides in.
  useEffect(() => {
    if (reduced) return
    const ctx = gsap.context(() => {
      const s = 4.2, p = { alt: 35 }
      gsap.set(leaf.current, { opacity: 0 }); gsap.set(card.current, { opacity: 0, y: 24 })
      const tl = gsap.timeline({ paused: true, defaults: { ease: 'power2.inOut' } })
      tl.to(zoomG.current, { scale: s, x: VB_W / 2 - s * target.cx, y: VB_H / 2 - s * target.cy, svgOrigin: '0 0', duration: .55 }, 0)
        .to(p, { alt: .3, duration: .85, ease: 'none', onUpdate: () => setAlt(Math.round(p.alt * 10) / 10) }, 0)
        .to(hint.current, { opacity: 0, duration: .1 }, 0)
        .to(fadeG.current, { opacity: 0, duration: .25 }, .5)
        .to(leaf.current, { opacity: 1, duration: .25 }, .5)
        .to(card.current, { opacity: 1, y: 0, duration: .15, ease: 'power3.out' }, .85)
        .to({}, { duration: .0 }, 1)
      tlRef.current = tl
      if (desktop) ScrollTrigger.create({ trigger: sec.current, start: 'top top', end: '+=150%', pin: true, scrub: .6, animation: tl, anticipatePin: 1 })
    }, sec)
    return () => { ctx.revert(); tlRef.current = null; setAlt(35) }
  }, [desktop, reduced])

  const tapZoom = () => {
    if (desktop || reduced || !tlRef.current) return
    const next = !zoomed; setZoomed(next)
    if (next) tlRef.current.timeScale(1).tweenTo(1, { duration: 2.4, ease: 'power2.inOut' }); else tlRef.current.tweenTo(0, { duration: 1.4, ease: 'power2.inOut' })
  }

  return (
    <section ref={sec} id="top" aria-labelledby="hero-h" className="relative">
      <div className="wrap grid min-h-screen items-center gap-12 pb-24 pt-28 lg:grid-cols-12 lg:gap-16 lg:pb-16">
        <div className="lg:col-span-5">
          <motion.div initial={{ opacity: 0, y: 16 }} animate={ready ? { opacity: 1, y: 0 } : { opacity: 0, y: 16 }} transition={{ duration: .7, ease: EASE }}>
            <Eyebrow>01 / UAV PEST HOTSPOT DETECTION</Eyebrow>
          </motion.div>
          <h1 id="hero-h" className="!text-[clamp(2.75rem,5vw,5rem)]">
            {LINES.map((l, i) => (
              <span key={l} className="block overflow-hidden pb-[0.08em]">
                <motion.span className="block" initial={{ y: '110%' }} animate={{ y: ready ? 0 : '110%' }} transition={{ duration: .9, ease: EASE, delay: .15 + i * .08 }}>{l}</motion.span>
              </span>
            ))}
          </h1>
          <motion.p className="mt-8 text-lg" initial={{ opacity: 0, y: 24 }} animate={ready ? { opacity: 1, y: 0 } : { opacity: 0, y: 24 }} transition={{ duration: .8, ease: EASE, delay: .6 }}>
            AeroScout flies your field at 35 m, tells pest damage apart from drought, and walks you straight to the spots that need you.
          </motion.p>
          <motion.div className="mt-10 flex flex-wrap items-center gap-x-8 gap-y-5" initial={{ opacity: 0, y: 24 }} animate={ready ? { opacity: 1, y: 0 } : { opacity: 0, y: 24 }} transition={{ duration: .8, ease: EASE, delay: .7 }}>
            <ButtonLink href="#/dashboard">See a field scan</ButtonLink>
            <TextLink href="#why" arrow>How it tells pests from drought</TextLink>
          </motion.div>
        </div>

        <motion.div className="lg:col-span-7" initial={{ opacity: 0, y: 24 }} animate={ready ? { opacity: 1, y: 0 } : { opacity: 0, y: 24 }} transition={{ duration: .9, ease: EASE, delay: .3 }}>
          <div className="relative" onClick={tapZoom}>
            <FieldMap
              scan={scan} route={route} mode="class" dismiss={scan >= 1 ? 1 : Math.min(1, Math.max(0, (scan - .5) * 2))} showScanLine liveCoords
              groupRef={zoomG} fadeRef={fadeG} className="w-full"
              label="Top-down map of a crop field being scanned by a drone. Most plots are healthy green, two amber patches are dismissed as drought, and three red hotspots are linked by a walking route from the farmhouse."
              hud={{ alt: `${alt.toFixed(1)} M`, vari: '0.21', entropy: '4.8', hotspots: '03' }}
            />
            <div ref={leaf} className="no-tr pointer-events-none absolute inset-0 z-[5] overflow-hidden rounded-card opacity-0"><Leaf className="h-full w-full" /></div>
            <div ref={card} className="no-tr absolute inset-x-5 bottom-14 z-20 max-w-sm rounded-card border border-line bg-surface p-4 opacity-0 sm:left-auto sm:right-5">
              <p className="label mono text-canopy">SPECIES CONFIRMED · SAMPLE</p>
              <p className="font-display mt-1 text-xl font-semibold">Fall armyworm</p>
              <p className="mono mt-1 text-sm text-muted">94% confidence · model updated</p>
            </div>
            <p className="sr-only">Animation: a drone scan classifies the field. Healthy plots stay green, two drought patches are dismissed, three pest hotspots turn red and a walking route links them. On scroll the view descends from 35 metres to 0.3 metres to a damaged leaf, where the species is confirmed as fall armyworm with 94 percent confidence. Values are sample data.</p>
          </div>
          <p className="label mono mt-4 text-muted lg:hidden">{reduced ? '' : 'Tap the map to zoom into a hotspot'}</p>
        </motion.div>
      </div>
      <div ref={hint} className="no-tr pointer-events-none absolute inset-x-0 bottom-6 hidden flex-col items-center gap-3 lg:flex" aria-hidden>
        <span className="label mono text-muted">SCROLL TO DESCEND</span>
        <span className="relative block h-10 w-px overflow-hidden bg-line"><span className="scroll-line absolute inset-0 bg-hot" /></span>
      </div>
    </section>
  )
}
