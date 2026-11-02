/** SVG hotspot marker: solid dot + slowly pulsing ring. Tooltip text via data-tip (read by Cursor). */
export default function HotspotMarker({ x, y, r = 9, tip, pulse = true, label }: { x: number; y: number; r?: number; tip?: string; pulse?: boolean; label?: string }) {
  return (
    <g data-hotspot data-tip={tip} transform={`translate(${x} ${y})`} style={{ cursor: 'pointer' }}>
      {pulse && <circle className="pulse-ring" r={r * 1.6} fill="none" stroke="var(--hot)" strokeWidth={1.5} />}
      <circle r={r * 2.4} fill="transparent" />
      <circle r={r} fill="var(--hot)" stroke="var(--bg)" strokeWidth={1.5} />
      <circle r={r * 0.35} fill="var(--on-hot)" />
      {label && <text x={r + 6} y={-r - 2} className="mono" fontSize={11} fill="var(--text)" stroke="var(--map-bg)" strokeWidth={3} paintOrder="stroke" style={{ fontFamily: 'var(--font-mono)', letterSpacing: '.08em' }}>{label}</text>}
    </g>
  )
}
