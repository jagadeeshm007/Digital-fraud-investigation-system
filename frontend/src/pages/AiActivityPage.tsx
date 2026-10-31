import { SparklesIcon } from 'lucide-react'
import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router'
import PageHeader from '@/components/PageHeader'
import RiskBadge from '@/components/RiskBadge'
import { Alert as Callout, AlertDescription } from '@/components/ui/alert'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardDescription, CardHeader, CardPanel, CardTitle } from '@/components/ui/card'
import { Empty, EmptyDescription, EmptyHeader, EmptyTitle } from '@/components/ui/empty'
import { Skeleton } from '@/components/ui/skeleton'
import { Spinner } from '@/components/ui/spinner'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { toastManager } from '@/components/ui/toast'
import { getAlerts, reviewAlert, reviewPending, type Alert } from '@/lib/api'
import { useRole } from '@/lib/role'

const STATUS_VARIANT = { completed: 'success', unavailable: 'warning', pending: 'outline' } as const

export default function AiActivityPage() {
  const role = useRole()
  const [alerts, setAlerts] = useState<Alert[] | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [running, setRunning] = useState(false)
  const [reviewing, setReviewing] = useState<string | null>(null)

  const load = useCallback(async () => {
    setError(null)
    try {
      setAlerts((await getAlerts({ status: 'open', page_size: 200 })).items)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Could not load AI activity')
    }
  }, [])

  useEffect(() => {
    void load()
  }, [load, role])

  const runAll = async () => {
    setRunning(true)
    try {
      const r = await reviewPending()
      toastManager.add({
        type: r.unavailable ? 'warning' : 'success',
        title: 'AI review finished',
        description: `${r.reviewed} reviewed, ${r.completed} completed, ${r.unavailable} unavailable`,
      })
      await load()
    } catch (e) {
      toastManager.add({ type: 'error', title: 'AI review failed', description: e instanceof Error ? e.message : '' })
    } finally {
      setRunning(false)
    }
  }

  const reviewOne = async (alertId: string) => {
    setReviewing(alertId)
    try {
      const r = await reviewAlert(alertId)
      toastManager.add({
        type: r.ai_available ? 'success' : 'warning',
        title: r.ai_available ? 'AI review completed' : 'AI review unavailable',
        description: `Base ${r.base_score} · AI ${r.ai_adjustment >= 0 ? '+' : ''}${r.ai_adjustment} · Final ${r.final_score}`,
      })
      await load()
    } catch (e) {
      toastManager.add({ type: 'error', title: 'AI review failed', description: e instanceof Error ? e.message : '' })
    } finally {
      setReviewing(null)
    }
  }

  const counts = { completed: 0, unavailable: 0, pending: 0 } as Record<string, number>
  for (const a of alerts ?? []) counts[a.ai_status] = (counts[a.ai_status] ?? 0) + 1

  return (
    <section className="space-y-5">
      <PageHeader
        title="AI Activity"
        description="AI reviews masked evidence and may adjust a rule score by at most ±10."
        action={
          <Button onClick={() => void runAll()} disabled={running || !counts.pending}>
            {running ? <Spinner /> : <SparklesIcon />}
            Review {counts.pending || ''} pending
          </Button>
        }
      />

      {error && (
        <Callout variant="error">
          <AlertDescription>{error}</AlertDescription>
        </Callout>
      )}

      <div className="grid grid-cols-3 gap-3 sm:max-w-xl">
        {(['completed', 'pending', 'unavailable'] as const).map((k) => (
          <Card key={k}>
            <CardPanel className="py-3">
              <div className="text-muted-foreground text-xs capitalize">{k}</div>
              <div className="font-heading font-semibold text-2xl tabular-nums">{alerts ? counts[k] : '–'}</div>
            </CardPanel>
          </Card>
        ))}
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Reviews on open alerts</CardTitle>
          <CardDescription>The rule-based score stands whenever AI is unavailable.</CardDescription>
        </CardHeader>
        <CardPanel>
          {!alerts && !error ? (
            <Skeleton className="h-40 w-full" />
          ) : alerts && alerts.length === 0 ? (
            <Empty>
              <EmptyHeader>
                <EmptyTitle>No open alerts</EmptyTitle>
                <EmptyDescription>Run detection first.</EmptyDescription>
              </EmptyHeader>
            </Empty>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Alert</TableHead>
                  <TableHead>AI status</TableHead>
                  <TableHead className="text-right">Base</TableHead>
                  <TableHead className="text-right">AI</TableHead>
                  <TableHead>Final</TableHead>
                  <TableHead>Recommendation</TableHead>
                  <TableHead />
                </TableRow>
              </TableHeader>
              <TableBody>
                {alerts?.map((a) => (
                  <TableRow key={a.alert_id}>
                    <TableCell>
                      <Link to={`/alerts/${a.alert_id}`} className="font-medium underline-offset-4 hover:underline">
                        {a.fraud_category}
                      </Link>
                      <div className="font-mono text-muted-foreground text-xs">{a.entity_id}</div>
                    </TableCell>
                    <TableCell>
                      <Badge
                        variant={STATUS_VARIANT[a.ai_status as keyof typeof STATUS_VARIANT] ?? 'outline'}
                        className="capitalize"
                      >
                        {a.ai_status}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-right tabular-nums">{a.base_score}</TableCell>
                    <TableCell className="text-right tabular-nums">
                      {a.ai_adjustment > 0 ? `+${a.ai_adjustment}` : a.ai_adjustment}
                    </TableCell>
                    <TableCell>
                      <RiskBadge band={a.risk_band} score={a.final_score} />
                    </TableCell>
                    <TableCell className="max-w-72 whitespace-normal text-muted-foreground text-xs">
                      {a.ai_recommendation ?? '-'}
                    </TableCell>
                    <TableCell>
                      <Button
                        size="sm"
                        variant="outline"
                        disabled={reviewing !== null}
                        onClick={() => void reviewOne(a.alert_id)}
                      >
                        {reviewing === a.alert_id && <Spinner />}
                        {a.ai_status === 'pending' ? 'Review' : 'Re-review'}
                      </Button>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardPanel>
      </Card>
    </section>
  )
}
