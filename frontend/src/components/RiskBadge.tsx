import { Badge } from '@/components/ui/badge'
import type { RiskBand } from '@/lib/api'

const VARIANT = { High: 'error', Medium: 'warning', Low: 'success' } as const

/** Risk band with its letter and score ("H 92"); the band word alone when there is no score (cases). */
export default function RiskBadge({ band, score }: { band: RiskBand; score: number | undefined }) {
  return (
    <Badge variant={VARIANT[band] ?? 'outline'} className="tabular-nums">
      {score === undefined ? band : `${band.charAt(0)} ${score}`}
    </Badge>
  )
}
