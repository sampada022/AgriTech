import type Lenis from 'lenis'
export const EASE = [0.22, 1, 0.36, 1] as const
let lenis: Lenis | null = null
export const setLenis = (l: Lenis | null) => { lenis = l }
export function scrollToHash(hash: string) {
  if (hash.startsWith('#/')) { location.hash = hash; return }
  let el: HTMLElement | null = null
  try { el = document.querySelector(hash) } catch { /* not a selector */ }
  if (!el) return
  if (lenis) lenis.scrollTo(el, { offset: 0, duration: 1.2 })
  else el.scrollIntoView({ behavior: 'smooth' })
}
export function scrollToY(y: number) {
  if (lenis) lenis.scrollTo(y, { duration: 1.2 }); else window.scrollTo({ top: y, behavior: 'smooth' })
}
