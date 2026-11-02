import { useRef, type ReactNode } from 'react'
import gsap from 'gsap'
import { useReduced } from '../hooks/useMedia'

/** Pulls its child gently toward the cursor when within 40px of its bounds. */
export default function Magnetic({ children }: { children: ReactNode }) {
  const ref = useRef<HTMLDivElement>(null)
  const reduced = useReduced()
  const onMove = (e: React.MouseEvent) => {
    if (reduced) return
    const r = ref.current!.getBoundingClientRect()
    const cx = r.left + r.width / 2, cy = r.top + r.height / 2
    gsap.to(ref.current, { x: (e.clientX - cx) * .25, y: (e.clientY - cy) * .25, duration: .4, ease: 'power3.out' })
  }
  const reset = () => gsap.to(ref.current, { x: 0, y: 0, duration: .6, ease: 'power3.out' })
  // 40px halo: padding extends the hover zone around the button
  return <div className="inline-block p-10 -m-10" onMouseMove={onMove} onMouseLeave={reset}><div ref={ref} className="no-tr inline-block">{children}</div></div>
}
