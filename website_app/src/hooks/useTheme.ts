import { useCallback, useEffect, useState } from 'react'
export type Theme = 'light' | 'dark'
const read = (): Theme => (document.documentElement.dataset.theme === 'dark' ? 'dark' : 'light')
export function useTheme() {
  const [theme, setTheme] = useState<Theme>(read)
  useEffect(() => {
    const mo = new MutationObserver(() => setTheme(read()))
    mo.observe(document.documentElement, { attributes: true, attributeFilter: ['data-theme'] })
    return () => mo.disconnect()
  }, [])
  const toggle = useCallback(() => {
    const next: Theme = read() === 'dark' ? 'light' : 'dark'
    document.documentElement.dataset.theme = next
    try { localStorage.setItem('aeroscout-theme', next) } catch { /* ignore */ }
  }, [])
  return { theme, toggle }
}
