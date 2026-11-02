import gsap from 'gsap'
import { ScrollTrigger } from 'gsap/ScrollTrigger'
import { ArrowLeft, ArrowRight, Check } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import { fillFor } from '../components/FieldMap'
import HotspotMarker from '../components/HotspotMarker'
import { COLS, OX, OY, ROWS, CELL, hotspots, tiles } from '../data/field'
import { useDesktop, useReduced } from '../hooks/useMedia'
import { scrollToY } from '../lib'

gsap.registerPlugin(ScrollTrigger)

const STAGES = [
  { name: 'Drone sees', arc: 'THE DRONE SEES', body: 'At 35 m the drone photographs the whole field. Every tile gets a greenness score and a texture score.' },
  { name: 'Model flags', arc: 'THE MODEL FLAGS', body: 'Ragged, patchy damage turns red. Even fades are dismissed as drought. Only the red spots go on the route.' },
  { name: 'Farmer confirms', arc: 'THE FARMER CONFIRMS', body: 'The farmer walks to a hotspot and photographs a leaf. The pest is named and tied to that exact tile.' },
  { name: 'Model retrains', arc: 'THE MODEL RETRAINS', body: 'That leaf photo teaches the aerial model what this pest looks like from 35 m. The next scan starts smarter.' },
]
const CX = 400, CY = 282, R = 166, RING = 206
const pt = (r: number, a: number) => [CX + r * Math.cos(a), CY + r * Math.sin(a)]
const TOP = `M ${CX - 226} ${CY} A 226 226 0 0 1 ${CX + 226} ${CY}`
const BOT = `M ${CX - 238} ${CY} A 238 238 0 0 0 ${CX + 238} ${CY}`
const SC = 0.63, FX = OX + (COLS * CELL) / 2, FY = OY + (ROWS * CELL) / 2

function Stage({ p, onPick }: { p: number; onPick: (i: number) => void }) {
  const idx = Math.min(3, Math.floor(p * 4 + 1e-6)), local = Math.min(1, p * 4 - idx)
  const mode = idx === 0 ? 'rgb' : 'class'
  const scan = idx === 0 ? local : 1
  const dismiss = idx === 1 ? Math.min(1, local * 2) : idx > 1 ? 1 : 0
  const ang = -Math.PI / 2 + p * Math.PI * 2 * 0.999
  const [dx, dy] = pt(RING, ang)
  const circ = 2 * Math.PI * RING
  const confirmed = hotspots[0]
  return (
    <svg viewBox="0 0 800 560" role="img" className="h-full w-full" aria-label={`Learning loop, stage ${idx + 1} of 4: ${STAGES[idx].name}. ${STAGES[idx].body}`}>
      <defs>
        <clipPath id="disc"><circle cx={CX} cy={CY} r={R} /></clipPath>
        <pattern id="pts" width="40" height="40" patternUnits="userSpaceOnUse"><circle cx="2" cy="2" r="1" fill="var(--text)" opacity=".18" /></pattern>
        <path id="arcTop" d={TOP} /><path id="arcBot" d={BOT} />
      </defs>
      <rect width="800" height="560" fill="url(#pts)" />

      <text fill="var(--muted)" fontSize="12" letterSpacing="9" style={{ fontFamily: 'var(--font-mono)' }}>
        <textPath href="#arcTop" startOffset="50%" textAnchor="middle">IT · GETS · SMARTER · EVERY · FIELD</textPath></text>
      {STAGES.map((s, i) => (
        <text key={s.name} fill="var(--text)" fontSize="14" letterSpacing="10" opacity={i === idx ? 1 : 0} style={{ fontFamily: 'var(--font-mono)', transition: 'opacity .5s cubic-bezier(.22,1,.36,1)' }}>
          <textPath href="#arcBot" startOffset="50%" textAnchor="middle" dy="22">{s.arc.split('').join(' ').replace(/ {2,}/g, '  ')}</textPath></text>
      ))}

      <circle cx={CX} cy={CY} r={RING} fill="none" stroke="var(--text)" strokeOpacity=".55" strokeWidth="2" strokeDasharray="1 7" strokeLinecap="round" />
      <circle cx={CX} cy={CY} r={RING} fill="none" stroke="var(--hot)" strokeWidth="2" strokeDasharray={`${circ * p} ${circ}`} transform={`rotate(-90 ${CX} ${CY})`} />
      {[0, 1, 2, 3].map((i) => {
        const [x, y] = pt(RING, -Math.PI / 2 + (i * Math.PI) / 2); const on = i <= idx
        return (
          <g key={i} onClick={() => onPick(i)} style={{ cursor: 'pointer' }} role="button" aria-label={`Go to ${STAGES[i].name}`}>
            <circle cx={x} cy={y} r="14" fill="transparent" />
            <circle cx={x} cy={y} r="6" fill={on ? 'var(--hot)' : 'var(--bg)'} stroke={on ? 'var(--hot)' : 'var(--text)'} strokeWidth="1.5" />
          </g>
        )
      })}
      <circle cx={dx} cy={dy} r="9" fill="var(--hot)" stroke="var(--bg)" strokeWidth="2" />
      <circle cx={dx} cy={dy} r="16" fill="none" stroke="var(--hot)" strokeOpacity=".5" />

      <circle cx={CX} cy={CY} r={R + 5} fill="var(--bg)" stroke="var(--text)" strokeOpacity=".4" />
      <g clipPath="url(#disc)">
        <rect x={CX - R} y={CY - R} width={R * 2} height={R * 2} fill="var(--tile-raw)" />
        <g transform={`translate(${CX} ${CY}) scale(${SC}) translate(${-FX} ${-FY})`}>
          {tiles.map((t) => {
            const scanned = (t.y + t.h / 2 - OY) / (ROWS * CELL) < scan
            return <rect key={t.id} x={t.x} y={t.y} width={t.w} height={t.h} rx={2} fill={fillFor(t, mode, scanned, dismiss)} stroke="var(--tile-ok-edge)" strokeOpacity=".45" strokeWidth="1"
              opacity={idx === 3 && t.cls === 'abiotic' ? 0.55 : 1} style={{ transition: 'fill .8s cubic-bezier(.22,1,.36,1), opacity .8s' }} />
          })}
          {idx >= 1 && hotspots.map((h) => <HotspotMarker key={h.id} x={h.cx} y={h.cy} r={11} tip={`${h.name} · ${h.area} · ${h.severity} · ${h.status} (sample)`} label={h.id} />)}
          {idx === 2 && <circle cx={confirmed.cx} cy={confirmed.cy} r={34} fill="none" stroke="var(--canopy)" strokeWidth="3" />}
          {idx === 3 && hotspots.map((h) => <circle key={h.id} cx={h.cx} cy={h.cy} r={30} fill="none" stroke="var(--canopy)" strokeWidth="2" strokeDasharray="6 5" />)}
        </g>
        {idx === 0 && local < 1 && <line x1={CX - R} x2={CX + R} y1={CY - R + scan * 2 * R} y2={CY - R + scan * 2 * R} stroke="var(--hot)" strokeWidth="2" />}
      </g>
      {idx === 0 && <g transform={`translate(${CX} ${CY - RING})`} aria-hidden><circle r="13" fill="var(--bg)" stroke="var(--text)" /><path d="M -6 -6 L 6 6 M 6 -6 L -6 6" stroke="var(--text)" strokeWidth="1.5" strokeLinecap="round" /><circle r="2.5" fill="var(--text)" /></g>}

      <g style={{ opacity: idx >= 2 ? 1 : 0, transition: 'opacity .6s cubic-bezier(.22,1,.36,1)' }}>
        <rect x={CX + R - 10} y={CY - 70} width="200" height="64" rx="10" fill="var(--surface)" stroke="var(--canopy)" />
        <text x={CX + R + 6} y={CY - 46} fontSize="10" letterSpacing="1.5" fill="var(--canopy)" style={{ fontFamily: 'var(--font-mono)' }}>{idx === 3 ? 'MODEL v2 · +1 EXAMPLE' : 'LEAF CONFIRMED · SAMPLE'}</text>
        <text x={CX + R + 6} y={CY - 22} fontSize="18" fontWeight="600" fill="var(--text)" style={{ fontFamily: 'var(--font-display)' }}>Fall armyworm</text>
      </g>
    </svg>
  )
}

export default function LearningLoop() {
  const desktop = useDesktop(), reduced = useReduced()
  const pinned = desktop && !reduced
  const sec = useRef<HTMLElement>(null), st = useRef<ScrollTrigger | null>(null)
  const [p, setP] = useState(0)
  useEffect(() => {
    if (!pinned) return
    const ctx = gsap.context(() => {
      st.current = ScrollTrigger.create({ trigger: sec.current, start: 'top top', end: '+=320%', pin: true, anticipatePin: 1, scrub: true,
        onUpdate: (s) => setP(Math.round(s.progress * 400) / 400) })
    }, sec)
    return () => { ctx.revert(); st.current = null }
  }, [pinned])

  const idx = Math.min(3, Math.floor(p * 4 + 1e-6))
  const pick = (i: number) => {
    const target = (i + 0.02) / 4
    if (pinned && st.current) scrollToY(st.current.start + target * (st.current.end - st.current.start))
    else setP(Math.min(0.999, (i + 0.5) / 4))
  }
  const prev = STAGES[(idx + 3) % 4], next = STAGES[(idx + 1) % 4]

  return (
    <section ref={sec} aria-labelledby="loop-h" className={pinned ? 'relative h-screen overflow-hidden' : 'section'}>
      <div className={`wrap flex flex-col ${pinned ? 'h-full pb-6 pt-24' : ''}`}>
        <div className="flex flex-wrap items-end justify-between gap-6">
          <div>
            <p className="label mb-4 flex items-center gap-3 text-muted"><span aria-hidden className="inline-block h-px w-8 bg-hot" />06 / IT GETS SMARTER EVERY FIELD</p>
            <h2 id="loop-h" className="!text-[clamp(1.75rem,3.2vw,2.75rem)]">Every leaf photo teaches the drone.</h2>
          </div>
          <p className="max-w-md text-[15px] text-muted">This is called active learning: each photo a farmer confirms shows the model what that pest looks like from 35 m up.</p>
        </div>

        <div className="stage-dark relative mt-6 min-h-[460px] flex-1 overflow-hidden rounded-card border border-line">
          {['left-3 top-3 border-l border-t', 'right-3 top-3 border-r border-t', 'left-3 bottom-3 border-l border-b', 'right-3 bottom-3 border-r border-b'].map((c) => <span key={c} aria-hidden className={`corner z-10 ${c}`} />)}
          <div role="tablist" aria-label="Learning loop stages" className="absolute inset-x-0 top-4 z-10 flex justify-center gap-1 px-4 sm:gap-6">
            {STAGES.map((s, i) => (
              <button key={s.name} role="tab" aria-selected={i === idx} onClick={() => pick(i)}
                className={`label mono border-b px-1 pb-1 text-[10px] sm:text-xs ${i === idx ? 'border-hot text-ink' : 'border-transparent text-muted hover:text-ink'}`}>{s.name}</button>
            ))}
          </div>

          <div className="absolute inset-0 px-2 pb-2 pt-9 sm:px-10"><Stage p={p} onPick={pick} /></div>

          <button onClick={() => pick((idx + 3) % 4)} aria-label={`Previous stage: ${prev.name}`} className="absolute left-4 top-[48%] z-10 hidden items-center gap-3 text-muted hover:text-ink md:flex">
            <ArrowLeft aria-hidden size={18} strokeWidth={1.5} /><span aria-hidden className="h-px w-16 bg-current" /><span className="label mono text-[10px]">{prev.name}</span></button>
          <button onClick={() => pick((idx + 1) % 4)} aria-label={`Next stage: ${next.name}`} className="absolute right-4 top-[48%] z-10 hidden items-center gap-3 text-muted hover:text-ink md:flex">
            <span className="label mono text-[10px]">{next.name}</span><span aria-hidden className="h-px w-16 bg-current" /><ArrowRight aria-hidden size={18} strokeWidth={1.5} /></button>

          <div className="absolute inset-x-0 bottom-0 z-10 flex items-end justify-between gap-4 p-5 sm:px-10">
            <div className="max-w-xs sm:max-w-sm" aria-live="polite">
              <p className="label mono flex items-center gap-2 text-hot">{idx === 2 && <Check aria-hidden size={14} strokeWidth={1.5} />}STAGE 0{idx + 1} / 04 · {STAGES[idx].name}</p>
              <p className="mt-2 text-[15px] leading-snug">{STAGES[idx].body}</p>
            </div>
            {pinned && (
              <div aria-hidden className="flex flex-col items-center gap-2 text-muted">
                <span className="relative block h-7 w-4 rounded-full border border-current"><span className="absolute left-1/2 top-1.5 h-1.5 w-px -translate-x-1/2 bg-hot" /></span>
                <span className="label mono text-[10px]">Scroll</span>
              </div>
            )}
          </div>
        </div>
      </div>
    </section>
  )
}
