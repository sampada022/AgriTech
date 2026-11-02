import { animate } from 'framer-motion'
import { useRef, useState } from 'react'
import Eyebrow from '../components/Eyebrow'
import { Reveal } from '../components/Reveal'
import TextureTile from '../components/TextureTile'
import { useReduced } from '../hooks/useMedia'

const tiles = [
  { kind: 'pest' as const, label: 'Pest damage', contrast: 0.84, entropy: 4.8, note: 'Ragged, patchy, uneven' },
  { kind: 'drought' as const, label: 'Drought stress', contrast: 0.12, entropy: 2.1, note: 'Smooth, even fade' },
]

export default function WhyDronesGetItWrong() {
  const [amount, setAmount] = useState(0), ctl = useRef<ReturnType<typeof animate> | null>(null), reduced = useReduced()
  const go = (to: number) => { ctl.current?.stop(); if (reduced) return setAmount(to); ctl.current = animate(amount, to, { duration: .9, ease: [.22, 1, .36, 1], onUpdate: setAmount }) }
  const on = amount > .5
  return (
    <section id="why" aria-labelledby="why-h" className="section">
      <div className="wrap grid gap-16 lg:grid-cols-12">
        <Reveal className="lg:col-span-5">
          <Eyebrow>03 / WHY DRONES GET IT WRONG</Eyebrow>
          <h2 id="why-h">Same colour, different cause.</h2>
          <p className="mt-8">From the air, a pest-chewed canopy and a thirsty one both look yellow and thin. Chewing insects leave ragged, patchy damage. Drought fades leaves evenly.</p>
          <p className="mt-4">AeroScout measures that difference with GLCM, a way of scoring how rough or smooth a patch of pixels is. It needs only an ordinary RGB camera, no expensive multispectral sensor.</p>
          <div className="mt-10 rounded-card border border-line bg-surface p-5">
            <div className="flex items-center justify-between gap-4">
              <label htmlFor="tex" className="label mono">Show texture (GLCM)</label>
              <button role="switch" aria-checked={on} aria-label="Show texture (GLCM)" onClick={() => go(on ? 0 : 1)}
                className="relative h-7 w-12 rounded-full border border-line" style={{ background: on ? 'var(--hot)' : 'var(--bg)' }}>
                <span className="absolute left-0.5 top-0.5 h-5 w-5 rounded-full" style={{ background: on ? 'var(--on-hot)' : 'var(--muted)', transform: `translateX(${on ? 20 : 0}px)`, transition: 'transform .4s cubic-bezier(.22,1,.36,1), background-color .3s' }} />
              </button>
            </div>
            <input id="tex" type="range" min={0} max={1} step={0.01} value={amount} onChange={(e) => { ctl.current?.stop(); setAmount(+e.target.value) }} className="mt-5 w-full accent-[var(--hot)]" aria-label="Blend from RGB view to texture view" />
            <div className="label mono mt-1 flex justify-between text-muted"><span>RGB</span><span>Texture</span></div>
          </div>
        </Reveal>
        <Reveal className="lg:col-span-7" delay={.1}>
          <div className="grid gap-6 sm:grid-cols-2">
            {tiles.map((t) => (
              <figure key={t.kind}>
                <div role="img" aria-label={`${t.label} canopy tile. In RGB it looks yellow and thin; in texture view it shows ${t.kind === 'pest' ? 'jagged, high-contrast, high-entropy patterns' : 'a smooth, even fade'}.`}>
                  <TextureTile kind={t.kind} amount={amount} />
                </div>
                <figcaption className="mt-4">
                  <p className="font-display text-xl font-semibold">{t.label}</p>
                  <p className="mono mt-3 grid grid-cols-2 gap-2 border-t border-line pt-3 text-sm">
                    <span className="label text-muted">Contrast<br /><span className={`text-base ${t.kind === 'pest' && amount > .5 ? 'text-hot' : ''}`}>{(t.contrast * amount).toFixed(2)}</span></span>
                    <span className="label text-muted">Entropy<br /><span className={`text-base ${t.kind === 'pest' && amount > .5 ? 'text-hot' : ''}`}>{(t.entropy * amount).toFixed(1)}</span></span>
                  </p>
                  <p className="label mono mt-2 text-muted">{amount > .5 ? t.note : 'Looks the same in RGB'}</p>
                </figcaption>
              </figure>
            ))}
          </div>
          <p className="label mono mt-6 text-muted">SAMPLE DATA · ILLUSTRATIVE TILES</p>
        </Reveal>
      </div>
    </section>
  )
}
