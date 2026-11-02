import { useEffect, useRef, useState } from 'react'
import { useInView } from 'framer-motion'
import { useReduced } from '../hooks/useMedia'

/** Counts from 0 to `value` once when it enters the viewport. */
export default function StatCounter({ value, suffix = '', display, className = '' }: { value: number; suffix?: string; display: string; className?: string }) {
  const ref = useRef<HTMLSpanElement>(null)
  const inView = useInView(ref, { once: true, amount: 0.4 })
  const reduced = useReduced()
  const [n, setN] = useState(0)
  useEffect(() => {
    if (!inView || reduced) return
    const t0 = performance.now(), dur = 1600; let raf = 0
    const tick = (t: number) => {
      const p = Math.min(1, (t - t0) / dur); setN(Math.round(value * (1 - Math.pow(1 - p, 4))))
      if (p < 1) raf = requestAnimationFrame(tick)
    }
    raf = requestAnimationFrame(tick); return () => cancelAnimationFrame(raf)
  }, [inView, reduced, value])
  return <span ref={ref} className={`bignum ${className}`} aria-label={display}><span aria-hidden>{reduced ? display : `${n}${suffix}`}</span></span>
}
