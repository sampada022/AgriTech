import { motion, AnimatePresence } from 'framer-motion'
import { Moon, Sun } from 'lucide-react'
import { useTheme } from '../hooks/useTheme'
import { EASE } from '../lib'

export default function ThemeToggle() {
  const { theme, toggle } = useTheme()
  return (
    <button onClick={toggle} aria-label={theme === 'dark' ? 'Switch to light theme' : 'Switch to dark theme'}
      className="relative grid h-10 w-10 place-items-center rounded-ctl border border-line hover:border-ink">
      <AnimatePresence mode="wait" initial={false}>
        <motion.span key={theme} initial={{ rotate: -90, scale: 0.4, opacity: 0 }} animate={{ rotate: 0, scale: 1, opacity: 1 }}
          exit={{ rotate: 90, scale: 0.4, opacity: 0 }} transition={{ duration: 0.3, ease: EASE }} className="grid place-items-center">
          {theme === 'dark' ? <Moon size={18} strokeWidth={1.5} /> : <Sun size={18} strokeWidth={1.5} />}
        </motion.span>
      </AnimatePresence>
    </button>
  )
}
