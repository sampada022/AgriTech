import { useEffect, useRef } from 'react'
import { useTheme } from '../hooks/useTheme'

const N = 140
const hash = (x: number, y: number, s: number) => { const v = Math.sin(x * 127.1 + y * 311.7 + s * 74.7) * 43758.5453; return v - Math.floor(v) }
function vnoise(x: number, y: number, s: number) {
  const xi = Math.floor(x), yi = Math.floor(y), xf = x - xi, yf = y - yi
  const u = xf * xf * (3 - 2 * xf), v = yf * yf * (3 - 2 * yf)
  const a = hash(xi, yi, s), b = hash(xi + 1, yi, s), c = hash(xi, yi + 1, s), d = hash(xi + 1, yi + 1, s)
  return a + (b - a) * u + (c - a) * v + (a - b - c + d) * u * v
}
const css = (n: string) => getComputedStyle(document.documentElement).getPropertyValue(n).trim()
function rgbOf(hex: string): [number, number, number] { const h = hex.replace('#', ''); return [0, 2, 4].map((i) => parseInt(h.slice(i, i + 2), 16)) as [number, number, number] }
const lerp = (a: number[], b: number[], t: number) => a.map((v, i) => v + (b[i] - v) * t)

/** Two stacked canvases: RGB look and GLCM texture look. `amount` crossfades them (opacity only). */
export default function TextureTile({ kind, amount }: { kind: 'pest' | 'drought'; amount: number }) {
  const rgbRef = useRef<HTMLCanvasElement>(null), texRef = useRef<HTMLCanvasElement>(null)
  const { theme } = useTheme()
  useEffect(() => {
    const ok = rgbOf(css('--tile-ok') || '#6E9A6F'), st = rgbOf(css('--stress') || '#8A5D00'), hot = rgbOf(css('--hot') || '#C2391B'), ink = rgbOf(css('--text') || '#1B1F17'), bg = rgbOf(css('--map-bg') || '#E9E4D2')
    const draw = (cv: HTMLCanvasElement, f: (x: number, y: number) => number[]) => {
      const ctx = cv.getContext('2d')!; const img = ctx.createImageData(N, N)
      for (let y = 0; y < N; y++) for (let x = 0; x < N; x++) { const c = f(x, y), i = (y * N + x) * 4; img.data[i] = c[0]; img.data[i + 1] = c[1]; img.data[i + 2] = c[2]; img.data[i + 3] = 255 }
      ctx.putImageData(img, 0, 0)
    }
    const seed = kind === 'pest' ? 3 : 3 // identical base so RGB tiles look alike
    // RGB: same yellowing, thinning canopy for both; pest differs only subtly.
    draw(rgbRef.current!, (x, y) => {
      const n = vnoise(x / 18, y / 18, seed) * .6 + vnoise(x / 5, y / 5, seed + 1) * .4
      const thin = vnoise(x / 30, y / 30, seed + 2)
      let c = lerp(ok, st, .35 + thin * .3 + (n - .5) * .25)
      if (kind === 'pest' && vnoise(x / 7, y / 7, 9) > .8) c = lerp(c, st, .18)
      return c
    })
    // Texture: local contrast map. Pest = jagged, high-frequency; drought = smooth fade.
    draw(texRef.current!, (x, y) => {
      let t: number
      if (kind === 'pest') {
        const a = vnoise(x / 4, y / 4, 11), b = vnoise(x / 9, y / 9, 12), e = vnoise(x / 2.2, y / 2.2, 13)
        t = Math.abs(a - .5) * 1.6 + Math.abs(b - .5) * 1.2 + Math.abs(e - .5) * .8
        t = Math.min(1, Math.max(0, (t - .25) * 2.2)); t = t > .55 ? Math.min(1, t * 1.25) : t * .55
      } else {
        t = .18 + vnoise(x / 70, y / 70, 5) * .22 + (x / N) * .08
      }
      return t > .62 ? lerp(bg, hot, Math.min(1, (t - .62) * 3.2)).map((v, i) => v * .55 + (lerp(bg, ink, t)[i]) * .45) : lerp(bg, ink, t * .8)
    })
  }, [kind, theme])
  return (
    <div className="relative aspect-square overflow-hidden rounded-card border border-line">
      <canvas ref={rgbRef} width={N} height={N} className="absolute inset-0 h-full w-full [image-rendering:auto]" aria-hidden />
      <canvas ref={texRef} width={N} height={N} className="absolute inset-0 h-full w-full" aria-hidden style={{ opacity: amount, transition: 'none' }} />
      {['left-2 top-2 border-l border-t', 'right-2 top-2 border-r border-t', 'left-2 bottom-2 border-l border-b', 'right-2 bottom-2 border-r border-b'].map((c) => <span key={c} aria-hidden className={`corner ${c}`} style={{ borderColor: 'var(--surface)' }} />)}
    </div>
  )
}
