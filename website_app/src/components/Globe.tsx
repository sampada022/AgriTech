import { useEffect, useRef } from 'react'
import { LAND_B64, LAND_H, LAND_W } from '../data/land'

export interface Cam { lon: number; lat: number; k: number }  // centre longitude/latitude (deg) and zoom
const N = 12000
const rad = Math.PI / 180

let pts: { lat: number; lon: number; land: boolean }[] | null = null
function points() {
  if (pts) return pts
  const bits = Uint8Array.from(atob(LAND_B64), (c) => c.charCodeAt(0))
  const golden = Math.PI * (3 - Math.sqrt(5))
  pts = Array.from({ length: N }, (_, i) => {
    const lat = Math.asin(1 - (2 * (i + 0.5)) / N) / rad, lon = ((i * golden) / rad) % 360 - 180
    const col = Math.min(LAND_W - 1, Math.floor(((lon + 180) / 360) * LAND_W)), row = Math.min(LAND_H - 1, Math.floor(((90 - lat) / 180) * LAND_H))
    const idx = row * LAND_W + col
    return { lat, lon, land: !!(bits[idx >> 3] & (1 << (idx & 7))) }
  })
  return pts
}

/** Dot-matrix orthographic globe. Land is drawn bright, ocean as a faint dot grid. `cam` is mutated by GSAP; the canvas just reads it. */
export default function Globe({ cam, size, color }: { cam: Cam; size: number; color: string }) {
  const cv = useRef<HTMLCanvasElement>(null)
  useEffect(() => {
    const c = cv.current!, ctx = c.getContext('2d')!, dpr = Math.min(2, devicePixelRatio || 1)
    c.width = c.height = size * dpr; ctx.scale(dpr, dpr)
    const P = points(); let raf = 0
    const draw = () => {
      ctx.clearRect(0, 0, size, size)
      const R = size * 0.4 * cam.k, cx = size / 2, cy = size / 2
      const p0 = cam.lat * rad, sp0 = Math.sin(p0), cp0 = Math.cos(p0)
      ctx.fillStyle = color
      for (const p of P) {
        const phi = p.lat * rad, dl = (p.lon - cam.lon) * rad
        const cosc = sp0 * Math.sin(phi) + cp0 * Math.cos(phi) * Math.cos(dl)
        if (cosc <= 0.02) continue
        const x = cx + R * Math.cos(phi) * Math.sin(dl), y = cy - R * (cp0 * Math.sin(phi) - sp0 * Math.cos(phi) * Math.cos(dl))
        ctx.globalAlpha = p.land ? 0.25 + 0.75 * Math.pow(cosc, 0.6) : 0.05 + 0.1 * cosc
        const s = p.land ? 1.6 : 1.0
        ctx.fillRect(x - s / 2, y - s / 2, s, s)
      }
      ctx.globalAlpha = 0.55; ctx.strokeStyle = color; ctx.lineWidth = 1.5; ctx.beginPath(); ctx.arc(cx, cy, R, 0, Math.PI * 2); ctx.stroke()
      ctx.globalAlpha = 0.18; ctx.lineWidth = 6; ctx.beginPath(); ctx.arc(cx, cy, R + 5, 0, Math.PI * 2); ctx.stroke()
      raf = requestAnimationFrame(draw)
    }
    raf = requestAnimationFrame(draw); return () => cancelAnimationFrame(raf)
  }, [cam, size, color])
  return <canvas ref={cv} aria-hidden style={{ width: size, height: size }} />
}
