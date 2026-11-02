import { Pause, Play } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import { Reveal } from '../components/Reveal'
import { useReduced } from '../hooks/useMedia'

/** Section 7: the architecture video replaces the old layered diagram. The video carries its own "07 / UNDER THE HOOD" title. */
export default function Technology() {
  const reduced = useReduced()
  const vid = useRef<HTMLVideoElement>(null)
  const [playing, setPlaying] = useState(false)

  useEffect(() => {
    const v = vid.current; if (!v || reduced) return
    const io = new IntersectionObserver(([e]) => { if (e.isIntersecting) v.play().catch(() => {}); else v.pause() }, { threshold: 0.35 })
    io.observe(v); return () => io.disconnect()
  }, [reduced])
  const toggle = () => { const v = vid.current; if (!v) return; v.paused ? v.play().catch(() => {}) : v.pause() }

  return (
    <section id="technology" aria-labelledby="tech-h" className="section">
      <div className="wrap">
        <h2 id="tech-h" className="sr-only">07 / Under the hood: sky to leaf, in three layers</h2>
        <Reveal>
          <div className="relative overflow-hidden rounded-card border border-line bg-mapbg" style={{ aspectRatio: '16 / 9' }}>
            <video ref={vid} src="/the_vid.mp4" muted loop playsInline preload="metadata" controls={reduced}
              aria-label="Animated architecture: a drone scans the field at 35 metres, the analysis engine processes tiles, and the dashboard shows hotspots. Three layers: acquisition, processing and interaction."
              onPlay={() => setPlaying(true)} onPause={() => setPlaying(false)} className="h-full w-full object-cover" />
            {!reduced && (
              <button onClick={toggle} aria-label={playing ? 'Pause video' : 'Play video'}
                className="absolute bottom-4 right-4 z-10 grid h-10 w-10 place-items-center rounded-full border border-white/60 bg-black/50 text-white hover:bg-black/70">
                {playing ? <Pause size={16} strokeWidth={1.5} /> : <Play size={16} strokeWidth={1.5} />}
              </button>
            )}
          </div>
        </Reveal>
      </div>
    </section>
  )
}
