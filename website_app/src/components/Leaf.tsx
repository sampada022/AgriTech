/** Code-drawn close-up of a maize leaf with ragged chewing damage. Illustrative, not a photo. */
export default function Leaf({ className = '' }: { className?: string }) {
  return (
    <svg viewBox="0 0 600 460" role="img" aria-label="Illustration of a leaf close-up with ragged, chewed holes along the edge and mid-vein" className={className} preserveAspectRatio="xMidYMid slice">
      <rect width="600" height="460" fill="var(--tile-raw)" />
      <path d="M -20 380 C 120 230 330 150 640 120 L 640 330 C 400 330 180 400 -20 470 Z" fill="var(--tile-ok)" stroke="var(--tile-ok-edge)" strokeWidth="2" />
      <path d="M -20 425 C 160 320 360 230 640 225" fill="none" stroke="var(--tile-ok-edge)" strokeWidth="5" opacity=".8" />
      {Array.from({ length: 14 }).map((_, i) => (
        <path key={i} d={`M -20 ${390 + i * 4} C 160 ${290 + i * 6} 360 ${200 + i * 8} 640 ${170 + i * 11}`} fill="none" stroke="var(--tile-ok-edge)" strokeWidth="1" opacity=".35" />
      ))}
      {/* chewed holes: ragged polygons showing the backdrop */}
      <path d="M 250 255 l 22 -14 l 16 10 l 20 -8 l 10 18 l -14 16 l -22 4 l -16 -12 l -20 6 z" fill="var(--tile-raw)" stroke="var(--hot)" strokeWidth="1.5" />
      <path d="M 405 175 l 18 -8 l 12 12 l 22 -4 l 4 20 l -16 12 l -20 -2 l -10 -14 z" fill="var(--tile-raw)" stroke="var(--hot)" strokeWidth="1.5" />
      <path d="M 120 335 l 16 -12 l 20 6 l 8 16 l -12 14 l -22 -2 z" fill="var(--tile-raw)" stroke="var(--hot)" strokeWidth="1.5" />
      <path d="M 520 140 l 10 -10 l 18 6 l 6 14 l -16 8 z" fill="var(--tile-raw)" stroke="var(--hot)" strokeWidth="1.5" />
    </svg>
  )
}
