import { useLang } from '../lang'
import type { Key } from '../i18n'
import type { Hotspot, Verdict } from '../types'
import { verdictOf } from '../types'
import { Button, Chip, tierColor } from './Ui'

const ABIOTIC_HINT_TEXT: Record<string, string> = {
  striping: 'Strong directional pattern: reads as nutrient, irrigation or planting, not pest.',
  large_smooth_zone: 'Large smooth zone: reads as water stress, not pest.',
}

interface Props {
  hotspots: Hotspot[]
  selected: string | null
  onSelect: (id: string) => void
  onVerdict?: (h: Hotspot, v: Exclude<Verdict, null>) => void
  busy?: string | null
}

export function HotspotList({ hotspots, selected, onSelect, onVerdict, busy }: Props) {
  const { t } = useLang()
  const verdictLabel = (v: Verdict): string =>
    v === 'PEST' ? t('pest') : v === 'NOT_PEST' ? t('notPest') : v === 'OTHER' ? t('other') : t('pending')

  return (
    <ul className="space-y-3">
      {hotspots.map((h) => {
        const verdict = verdictOf(h)
        return (
        <li
          key={h.id}
          onClick={() => onSelect(h.id)}
          className={`cursor-pointer rounded-xl border p-3 transition-colors ${
            selected === h.id ? 'border-brand-600 bg-brand-50' : 'border-gray-200 bg-white hover:border-gray-300'
          }`}
        >
          <div className="flex flex-wrap items-center gap-2">
            <span className="grid h-6 w-6 place-items-center rounded-full bg-gray-900 text-xs font-semibold text-white">{h.rank}</span>
            <span className="text-sm font-semibold">{h.id}</span>
            <Chip color={tierColor(h.tier)}>{t(`T_${h.tier}` as Key)}</Chip>
            <Chip color="#6b7280">{t('confidence')}: {t(`C_${h.confidence}` as Key)}</Chip>
          </div>
          <div className="mt-2 text-sm text-gray-800">{h.abiotic_hint ? ABIOTIC_HINT_TEXT[h.abiotic_hint] : 'Pattern consistent with localised stress. Inspect for pest damage.'}</div>
          <div className="mt-2 text-xs text-gray-600">
            Area: <b>{h.area_m2.toFixed(0)} m²</b>
          </div>

          <div className="mt-3 border-t border-gray-100 pt-2">
            <div className="mb-1 text-xs font-medium text-gray-500">
              {t('groundCheck')}: <span className="text-gray-900">{verdictLabel(verdict)}</span>
            </div>
            {onVerdict && (
              <div className="flex flex-wrap gap-2" onClick={(e) => e.stopPropagation()}>
                {(['PEST', 'NOT_PEST', 'OTHER'] as const).map((v) => (
                  <Button
                    key={v}
                    variant={verdict === v ? 'primary' : 'secondary'}
                    disabled={busy === h.id}
                    onClick={() => onVerdict(h, v)}
                    className="!px-2.5 !py-1 text-xs"
                  >
                    {verdictLabel(v)}
                  </Button>
                ))}
              </div>
            )}
          </div>
        </li>
      )})}
    </ul>
  )
}
