import { motion } from 'framer-motion'
import gsap from 'gsap'
import { useEffect, useMemo, useRef, useState } from 'react'
import { EASE } from '../lib'
import Globe, { type Cam } from './Globe'

const MANDYA = { lat: 12.5223, lon: 76.897 }
const pageReady = () => Promise.all([
  document.fonts?.ready ?? Promise.resolve(),
  document.readyState === 'complete' ? Promise.resolve() : new Promise<void>((r) => addEventListener('load', () => r(), { once: true })),
])

/** Dot-matrix globe spins, lands on Mandya, a marker pings, then an iris closes on it to reveal the site. */
export default function Preloader({ onReveal, onDone }: { onReveal: () => void; onDone: () => void }) {
  const root = useRef<HTMLDivElement>(null), globe = useRef<HTMLDivElement>(null), count = useRef<HTMLSpanElement>(null), orbit = useRef<SVGCircleElement>(null)
  const cam = useMemo<Cam>(() => ({ lon: -150, lat: 24, k: 0.92 }), [])
  const [landed, setLanded] = useState(false)
  const [size, setSize] = useState(() => Math.round(Math.min(innerWidth * 0.86, innerHeight * 0.72, 600)))
  const [hot, setHot] = useState('#C2391B')

  useEffect(() => {
    setHot(getComputedStyle(root.current!).getPropertyValue('--hot').trim() || '#FF6B42')
    document.documentElement.style.overflow = 'hidden'; scrollTo(0, 0)
    let dead = false; const prog = { v: 0 }
    const paint = () => {
      if (count.current) count.current.textContent = String(Math.round(prog.v)).padStart(3, '0')
      const a = -Math.PI / 2 + (prog.v / 100) * Math.PI * 2
      orbit.current?.setAttribute('cx', String(90 + 82 * Math.cos(a))); orbit.current?.setAttribute('cy', String(24 + 18 * Math.sin(a)))
    }
    const spin = gsap.timeline()
    spin.to(cam, { lon: MANDYA.lon, lat: MANDYA.lat, k: 1, duration: 2.5, ease: 'power3.out' })
      .add(() => setLanded(true), '>-0.35')
    const run = async () => {
      await gsap.to(prog, { v: 90, duration: 2.4, ease: 'power2.out', onUpdate: paint }).then()
      await pageReady(); if (dead) return
      await gsap.to(prog, { v: 100, duration: 0.45, ease: 'power1.inOut', onUpdate: paint }).then(); if (dead) return
      const tl = gsap.timeline({ delay: 0.75, onComplete: () => { document.documentElement.style.overflow = ''; onDone() } })
      tl.to(globe.current, { scale: 1.5, duration: 0.8, ease: 'power2.in' })
        .add(() => onReveal(), '>-0.25')
        .to(root.current, { clipPath: 'circle(0% at 50% 50%)', duration: 0.95, ease: 'power3.inOut' }, '<0.05')
    }
    run()
    return () => { dead = true; spin.kill(); gsap.killTweensOf(prog); document.documentElement.style.overflow = '' }
  }, [cam, onDone, onReveal])

  useEffect(() => { const on = () => setSize(Math.round(Math.min(innerWidth * 0.86, innerHeight * 0.72, 600))); addEventListener('resize', on); return () => removeEventListener('resize', on) }, [])

  return (
    <div ref={root} role="status" aria-live="polite" aria-busy="true" aria-label="Loading AeroScout" className="stage-dark no-tr fixed inset-0 z-[300] overflow-hidden" style={{ clipPath: 'circle(150% at 50% 50%)' }}>
      <div className="absolute inset-x-0 top-0 flex items-start justify-between p-6 sm:p-10">
        <motion.div initial={{ opacity: 0, y: -10 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.7, ease: EASE }} className="flex items-baseline gap-2">
          <span className="font-display text-2xl font-bold tracking-tight">AeroScout</span><span className="label mono text-muted">by 9Eleven</span></motion.div>
        <motion.p initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ duration: 0.7, delay: 0.2 }} className="label mono hidden text-muted sm:block">Loading field survey</motion.p>
      </div>

      <div className="absolute inset-0 grid place-items-center">
        <div ref={globe} className="no-tr relative" style={{ width: size, height: size }}>
          <Globe cam={cam} size={size} color={hot} />
          {/* marker sits at the centre of the globe, which is where the camera lands */}
          {landed && (
            <div className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2">
              <motion.span initial={{ scale: 0, opacity: 0 }} animate={{ scale: 1, opacity: 1 }} transition={{ duration: 0.6, ease: EASE }} className="relative block h-7 w-7 rounded-full border-[6px] border-hot bg-bg">
                <span aria-hidden className="pulse-ring absolute -inset-3 rounded-full border border-hot" />
              </motion.span>
            </div>
          )}
          {landed && (
            <div className="absolute left-1/2 top-1/2 hidden w-[min(300px,34vw)] sm:block" style={{ marginLeft: 22 }}>
              <motion.div initial={{ scaleX: 0 }} animate={{ scaleX: 1 }} transition={{ duration: 0.6, ease: EASE, delay: 0.1 }} className="h-px origin-left bg-text" style={{ background: 'var(--text)', opacity: 0.6, width: 80 }} />
              <motion.div initial={{ opacity: 0, x: -10 }} animate={{ opacity: 1, x: 0 }} transition={{ duration: 0.7, ease: EASE, delay: 0.45 }} className="absolute left-[80px] top-1/2 -translate-y-1/2 border-y border-l border-ink/60 py-3 pl-5 pr-2" style={{ borderColor: 'color-mix(in srgb, var(--text) 55%, transparent)' }}>
                <p className="font-display text-2xl font-semibold leading-none">Mandya</p>
                <p className="mt-2 text-sm text-muted">Karnataka, India</p>
                <p className="label mono mt-2 whitespace-nowrap text-muted" style={{ fontSize: 10 }}>12.5223° N · 76.8970° E</p>
              </motion.div>
            </div>
          )}
        </div>
      </div>

      <div className="absolute inset-x-0 bottom-0 flex items-end justify-between gap-6 p-6 sm:p-10">
        <motion.p initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.8, ease: EASE, delay: 0.3 }} className="hidden max-w-[220px] font-display text-xl font-semibold leading-tight sm:block">
          Find the three sick patches.<span className="block text-sm font-normal text-muted" style={{ fontFamily: 'var(--font-body)' }}>Skip the fifty healthy acres.</span></motion.p>
        <div className="mx-auto flex flex-col items-center sm:absolute sm:inset-x-0 sm:bottom-10 sm:mx-0">
          <svg width="180" height="48" viewBox="0 0 180 48" aria-hidden>
            <ellipse cx="90" cy="24" rx="82" ry="18" fill="none" stroke="var(--text)" strokeOpacity=".55" strokeDasharray="3 4" />
            <circle ref={orbit} cx="90" cy="6" r="4.5" fill="var(--hot)" />
          </svg>
          <p className="label mono mt-2 text-muted"><span ref={count}>000</span>%</p>
        </div>
        <p className="label mono ml-auto hidden text-muted sm:block">Sample data</p>
      </div>
    </div>
  )
}
