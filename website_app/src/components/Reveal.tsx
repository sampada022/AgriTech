import { motion, type Variants } from 'framer-motion'
import type { ElementType, ReactNode } from 'react'
import { EASE } from '../lib'
import { useReduced } from '../hooks/useMedia'

const item = (reduced: boolean): Variants => ({
  hidden: { opacity: 0, y: reduced ? 0 : 24 },
  show: { opacity: 1, y: 0, transition: { duration: 0.8, ease: EASE } },
})
const container: Variants = { hidden: {}, show: { transition: { staggerChildren: 0.08 } } }
const vp = { once: true, amount: 0.2 } as const

/** Container that staggers its <Item> children when 20% visible, once. */
export function Stagger({ children, className, as = 'div' }: { children: ReactNode; className?: string; as?: ElementType }) {
  const Tag = motion.create(as)
  return <Tag className={className} variants={container} initial="hidden" whileInView="show" viewport={vp}>{children}</Tag>
}
export function Item({ children, className, as = 'div' }: { children: ReactNode; className?: string; as?: ElementType }) {
  const reduced = useReduced(); const Tag = motion.create(as)
  return <Tag className={className} variants={item(reduced)}>{children}</Tag>
}
/** Single element reveal. */
export function Reveal({ children, className, delay = 0 }: { children: ReactNode; className?: string; delay?: number }) {
  const reduced = useReduced()
  return (
    <motion.div className={className} initial={{ opacity: 0, y: reduced ? 0 : 24 }} whileInView={{ opacity: 1, y: 0 }}
      viewport={vp} transition={{ duration: 0.8, ease: EASE, delay }}>{children}</motion.div>
  )
}
