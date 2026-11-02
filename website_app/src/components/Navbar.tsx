import { AnimatePresence, motion } from 'framer-motion'
import { Menu, X } from 'lucide-react'
import { useEffect, useState } from 'react'
import { navLinks } from '../data/copy'
import { EASE, scrollToHash } from '../lib'
import { ButtonLink } from './Button'
import ThemeToggle from './ThemeToggle'

export default function Navbar() {
  const [solid, setSolid] = useState(false), [hidden, setHidden] = useState(false), [open, setOpen] = useState(false)
  useEffect(() => {
    let last = scrollY
    const on = () => {
      const y = scrollY; setSolid(y > 80)
      if (Math.abs(y - last) > 6) { setHidden(y > last && y > 200); last = y }
    }
    addEventListener('scroll', on, { passive: true }); return () => removeEventListener('scroll', on)
  }, [])
  useEffect(() => { document.body.style.overflow = open ? 'hidden' : ''; return () => { document.body.style.overflow = '' } }, [open])
  const go = (href: string) => (e: React.MouseEvent) => { e.preventDefault(); setOpen(false); setTimeout(() => scrollToHash(href), open ? 250 : 0) }
  return (
    <>
      <motion.header initial={false} animate={{ y: hidden && !open ? '-100%' : 0 }} transition={{ duration: .5, ease: EASE }}
        className={`no-tr fixed inset-x-0 top-0 z-50 border-b ${solid ? 'border-line bg-bg/75 backdrop-blur-md' : 'border-transparent'}`} style={{ transition: 'background-color .3s, border-color .3s' }}>
        <nav aria-label="Primary" className="wrap flex h-16 items-center justify-between gap-6 lg:h-20">
          <a href="#top" onClick={go('#top')} className="flex items-baseline gap-2">
            <span className="font-display text-2xl font-bold tracking-tight">AeroScout</span>
            <span className="label mono whitespace-nowrap text-muted">by 9Eleven</span>
          </a>
          <ul className="hidden items-center gap-8 lg:flex">
            {navLinks.map((l) => <li key={l.href}><a href={l.href} onClick={go(l.href)} className="link-u text-[15px] font-medium">{l.label}</a></li>)}
          </ul>
          <div className="flex items-center gap-3">
            <ThemeToggle />
            <ButtonLink href="#/dashboard" className="max-sm:!hidden !py-2.5" arrow={false}>See a field scan</ButtonLink>
            <button className="grid h-10 w-10 place-items-center rounded-ctl border border-line lg:hidden" aria-label={open ? 'Close menu' : 'Open menu'} aria-expanded={open} onClick={() => setOpen(!open)}>
              {open ? <X size={20} strokeWidth={1.5} /> : <Menu size={20} strokeWidth={1.5} />}
            </button>
          </div>
        </nav>
      </motion.header>
      <AnimatePresence>
        {open && (
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} transition={{ duration: .25 }} className="fixed inset-0 z-40 bg-bg px-6 pt-28 lg:hidden">
            <ul className="flex flex-col gap-2">
              {navLinks.map((l, i) => (
                <motion.li key={l.href} initial={{ opacity: 0, y: 24 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: .08 * i + .1, duration: .6, ease: EASE }}>
                  <a href={l.href} onClick={go(l.href)} className="font-display block border-b border-line py-4 text-4xl font-bold tracking-tight">{l.label}</a>
                </motion.li>
              ))}
              <motion.li className="pt-8" initial={{ opacity: 0, y: 24 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: .6, duration: .6, ease: EASE }}>
                <ButtonLink href="#/dashboard" onClick={go('#/dashboard')}>See a field scan</ButtonLink>
              </motion.li>
            </ul>
          </motion.div>
        )}
      </AnimatePresence>
    </>
  )
}
