import { ButtonLink } from '../components/Button'
import HotspotMarker from '../components/HotspotMarker'
import Magnetic from '../components/Magnetic'
import { Reveal } from '../components/Reveal'

export default function FinalCTA() {
  return (
    <section aria-labelledby="cta-h" className="px-0 py-0">
      <div className="relative overflow-hidden bg-band py-24 text-band-fg lg:py-40 dark:border-y dark:border-canopy" style={{ borderTop: 'var(--band-border, 0)' }}>
        <svg aria-hidden viewBox="0 0 1200 600" preserveAspectRatio="xMidYMid slice" className="absolute inset-0 h-full w-full opacity-30">
          {Array.from({ length: 25 }).map((_, i) => <line key={'v' + i} x1={i * 50} x2={i * 50} y1={0} y2={600} stroke="currentColor" strokeWidth={1} opacity={.4} />)}
          {Array.from({ length: 13 }).map((_, i) => <line key={'h' + i} y1={i * 50} y2={i * 50} x1={0} x2={1200} stroke="currentColor" strokeWidth={1} opacity={.4} />)}
          <g style={{ color: 'var(--hot)' }}>{[[300, 200], [820, 150], [640, 450]].map(([x, y], i) => <HotspotMarker key={i} x={x} y={y} r={6} />)}</g>
        </svg>
        <div className="wrap relative">
          <Reveal>
            <h2 id="cta-h" className="max-w-4xl !text-[clamp(2.25rem,6vw,5.5rem)]">Your field already knows where the pests are. Now you will too.</h2>
            <div className="mt-14"><Magnetic><ButtonLink href="#contact" className="!px-10 !py-5 !text-lg">Request a field scan</ButtonLink></Magnetic></div>
          </Reveal>
        </div>
      </div>
    </section>
  )
}
