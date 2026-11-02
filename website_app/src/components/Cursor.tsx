import { useEffect, useRef } from 'react'
import { coordsAt } from '../data/field'

/** Desktop-only survey crosshair + lagging ring. Ring shows coords over maps, "Inspect" over hotspots; also renders data-tip tooltips. */
export default function Cursor() {
  const cross = useRef<HTMLDivElement>(null), ring = useRef<HTMLDivElement>(null), ringText = useRef<HTMLSpanElement>(null), tip = useRef<HTMLDivElement>(null)
  useEffect(() => {
    if (!matchMedia('(hover: hover) and (pointer: fine)').matches) return
    document.documentElement.classList.add('has-cursor')
    let mx = -100, my = -100, rx = -100, ry = -100, raf = 0, visible = false
    const move = (e: MouseEvent) => {
      mx = e.clientX; my = e.clientY
      if (!visible) { visible = true; rx = mx; ry = my; cross.current!.style.opacity = '1'; ring.current!.style.opacity = '1' }
      const t = e.target as Element | null
      const hot = t?.closest('[data-hotspot]'), map = t?.closest('[data-cursor="map"]'), tipEl = t?.closest('[data-tip]') as HTMLElement | null
      const txt = ringText.current!, ringEl = ring.current!
      if (hot) { txt.textContent = 'Inspect'; ringEl.dataset.big = '1' }
      else if (map) {
        const r = map.getBoundingClientRect(); txt.textContent = coordsAt((mx - r.left) / r.width, (my - r.top) / r.height); ringEl.dataset.big = '1'
      } else { txt.textContent = ''; ringEl.dataset.big = t?.closest('a,button,[role="switch"],input[type="range"]') ? 'link' : '0' }
      const tp = tip.current!
      if (tipEl?.dataset.tip) { tp.textContent = tipEl.dataset.tip; tp.style.opacity = '1'; tp.style.transform = `translate(${mx + 18}px, ${my + 18}px)` }
      else tp.style.opacity = '0'
    }
    const leave = () => { visible = false; cross.current!.style.opacity = '0'; ring.current!.style.opacity = '0'; tip.current!.style.opacity = '0' }
    const loop = () => {
      rx += (mx - rx) * .18; ry += (my - ry) * .18
      cross.current!.style.transform = `translate(${mx}px, ${my}px)`
      ring.current!.style.transform = `translate(${rx}px, ${ry}px)`
      raf = requestAnimationFrame(loop)
    }
    raf = requestAnimationFrame(loop)
    addEventListener('mousemove', move); document.documentElement.addEventListener('mouseleave', leave)
    return () => { cancelAnimationFrame(raf); removeEventListener('mousemove', move); document.documentElement.removeEventListener('mouseleave', leave); document.documentElement.classList.remove('has-cursor') }
  }, [])
  return (
    <div aria-hidden className="pointer-events-none fixed inset-0 z-[100] hidden [@media(hover:hover)_and_(pointer:fine)]:block">
      <div ref={cross} className="no-tr absolute left-0 top-0 opacity-0" style={{ width: 0, height: 0 }}>
        {/* two 1px lines, each split by a 6px gap */}
        <span className="absolute bg-ink" style={{ left: -11, top: 0, width: 8, height: 1 }} />
        <span className="absolute bg-ink" style={{ left: 3, top: 0, width: 8, height: 1 }} />
        <span className="absolute bg-ink" style={{ left: 0, top: -11, width: 1, height: 8 }} />
        <span className="absolute bg-ink" style={{ left: 0, top: 3, width: 1, height: 8 }} />
      </div>
      <div ref={ring} className="absolute left-0 top-0 opacity-0 no-tr group/ring" style={{ width: 0, height: 0 }}>
        <div className="cursor-ring absolute grid place-items-center rounded-full border border-ink/60 bg-bg/70 text-ink" style={{ width: 32, height: 32, left: -16, top: -16, transition: 'width .3s, height .3s, left .3s, top .3s, background-color .3s, border-color .3s' }}>
          <span ref={ringText} className="label mono whitespace-nowrap" style={{ fontSize: 10 }} />
        </div>
      </div>
      <div ref={tip} className="label mono absolute left-0 top-0 max-w-[260px] rounded-ctl border border-line bg-surface px-3 py-2 text-ink opacity-0" style={{ transition: 'opacity .2s' }} />
      <style>{`
        .cursor-ring { backdrop-filter: none }
        [data-big="1"] > .cursor-ring { width: 150px !important; height: 32px !important; left: -75px !important; border-radius: 16px; border-color: var(--hot) }
        [data-big="link"] > .cursor-ring { width: 48px !important; height: 48px !important; left: -24px !important; top: -24px !important }
      `}</style>
    </div>
  )
}
