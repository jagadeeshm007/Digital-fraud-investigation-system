import { Badge } from '@/components/ui/badge'
import type { RiskBand } from '@/lib/api'

const VARIANT = { High: 'error', Medium: 'warning', Low: 'success' } as const

export default function RiskBadge({ band, score }: { band: RiskBand; score: number }) {
  return (
    <Badge variant={VARIANT[band] ?? 'outline'} className="tabular-nums">
      {band.charAt(0)} {score}
    </Badge>
  )
}
