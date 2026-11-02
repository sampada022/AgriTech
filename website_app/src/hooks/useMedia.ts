import { useEffect, useState } from 'react'
export function useMedia(query: string, initial = false) {
  const [m, setM] = useState(() => (typeof window === 'undefined' ? initial : matchMedia(query).matches))
  useEffect(() => {
    const mq = matchMedia(query); const on = () => setM(mq.matches); on()
    mq.addEventListener('change', on); return () => mq.removeEventListener('change', on)
  }, [query])
  return m
}
export const useReduced = () => useMedia('(prefers-reduced-motion: reduce)')
export const useDesktop = () => useMedia('(min-width: 1024px)')
