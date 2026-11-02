import { Camera, Check } from 'lucide-react'
import Leaf from './Leaf'

export default function Phone({ className = '' }: { className?: string }) {
  return (
    <div className={`mx-auto w-[250px] rounded-[32px] border-2 border-ink bg-surface p-3 ${className}`} role="img" aria-label="Phone showing a leaf photo with a result card: Fall armyworm confirmed, 94 percent confidence, photo linked to aerial tile B-04. Sample data.">
      <div className="relative overflow-hidden rounded-[22px] border border-line">
        <div className="aspect-[3/4]"><Leaf className="h-full w-full" /></div>
        <span className="absolute left-1/2 top-2 h-1.5 w-14 -translate-x-1/2 rounded-full bg-ink/70" />
        <span className="label mono absolute bottom-2 left-2 rounded-ctl bg-bg/85 px-2 py-1" style={{ fontSize: 10 }}><Camera aria-hidden size={12} strokeWidth={1.5} className="mr-1 inline" />LEAF PHOTO</span>
      </div>
      <div className="mt-3 rounded-[12px] border border-line p-3">
        <p className="label mono flex items-center gap-1 text-canopy" style={{ fontSize: 10 }}><Check aria-hidden size={12} strokeWidth={1.5} />CONFIRMED · SAMPLE</p>
        <p className="font-display text-lg font-semibold leading-tight">Fall armyworm</p>
        <p className="mono text-xs text-muted">94% · linked to tile B-04</p>
      </div>
    </div>
  )
}
