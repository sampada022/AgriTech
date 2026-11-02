import { motion, useMotionValueEvent, useScroll, useSpring } from 'framer-motion'
import { useRef } from 'react'

/** Altitude-gauge style progress bar with a tiny mono percentage on desktop. */
export default function ScrollProgress() {
  const { scrollYProgress } = useScroll()
  const x = useSpring(scrollYProgress, { stiffness: 200, damping: 40, restDelta: .001 })
  const txt = useRef<HTMLSpanElement>(null)
  useMotionValueEvent(scrollYProgress, 'change', (v) => { if (txt.current) txt.current.textContent = String(Math.round(v * 100)).padStart(3, '0') + '%' })
  return (
    <div aria-hidden className="pointer-events-none fixed inset-x-0 top-0 z-[60] h-[3px]">
      <motion.div className="no-tr h-full origin-left bg-hot" style={{ scaleX: x }} />
      <div className="absolute inset-0 -z-10 opacity-60" style={{ backgroundImage: 'repeating-linear-gradient(to right, var(--border) 0 1px, transparent 1px 48px)' }} />
      <span ref={txt} className="label mono absolute right-6 top-2 hidden text-muted lg:block" style={{ fontSize: 10 }}>000%</span>
    </div>
  )
}
