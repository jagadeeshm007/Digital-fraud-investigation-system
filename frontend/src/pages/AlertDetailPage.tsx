import { ArrowLeftIcon, SparklesIcon } from 'lucide-react'
import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router'
import EntityGraph from '@/components/EntityGraph'
import PageHeader from '@/components/PageHeader'
import RiskBadge from '@/components/RiskBadge'
import { Alert as Callout, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardDescription, CardHeader, CardPanel, CardTitle } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import { getAlert, type Alert } from '@/lib/api'

export default function AlertDetailPage() {
  const { alertId = '' } = useParams()
  const [alert, setAlert] = useState<Alert | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    setAlert(null)
    setError(null)
    getAlert(alertId)
      .then(setAlert)
      .catch((e) => setError(e instanceof Error ? e.message : 'Could not load the alert'))
  }, [alertId])

  const back = (
    <Button variant="outline" render={<Link to="/alerts" />}>
      <ArrowLeftIcon />
      All alerts
    </Button>
  )

  if (error) {
    return (
      <section>
        <PageHeader title="Alert" action={back} />
        <Callout variant="error">
          <AlertDescription>{error}</AlertDescription>
        </Callout>
      </section>
    )
  }
  if (!alert) {
    return (
      <section className="space-y-4">
        <Skeleton className="h-10 w-80" />
        <Skeleton className="h-40 w-full" />
        <Skeleton className="h-[420px] w-full" />
      </section>
    )
  }

  // The graph starts from the flagged entity; a transaction alert is better explored from its customer.
  const graphRoot = alert.entity_type === 'transaction' && alert.customer_id ? alert.customer_id : alert.entity_id
  const factors = [...(alert.factors ?? [])].sort((a, b) => b.points - a.points)

  return (
    <section className="space-y-5">
      <PageHeader title={alert.fraud_category} description={`Alert ${alert.alert_id}`} action={back} />

      <div className="flex flex-wrap items-center gap-2 text-sm">
        <RiskBadge band={alert.risk_band} score={alert.final_score} />
        <Badge variant="outline" className="capitalize">
          {alert.status}
        </Badge>
        <span className="text-muted-foreground">
          {alert.entity_type} <span className="font-mono">{alert.entity_id}</span>
          {alert.customer_id && (
            <>
              {' '}
              · customer <span className="font-mono">{alert.customer_id}</span>
            </>
          )}
          {alert.product && <> · {alert.product}</>} · rule <span className="font-mono">{alert.rule_id}</span>
        </span>
      </div>

      <div aria-live="polite">
        {alert.ai_status === 'completed' && alert.ai_recommendation ? (
          <Callout variant="info">
            <SparklesIcon />
            <AlertTitle>AI review</AlertTitle>
            <AlertDescription>
              <p>{alert.ai_recommendation}</p>
              <p className="tabular-nums">
                Base {alert.base_score} · AI {alert.ai_adjustment >= 0 ? '+' : ''}
                {alert.ai_adjustment} · Final {alert.final_score}
              </p>
            </AlertDescription>
          </Callout>
        ) : (
          <Callout>
            <SparklesIcon />
            <AlertTitle>{alert.ai_status === 'unavailable' ? 'AI review unavailable' : 'AI review pending'}</AlertTitle>
            <AlertDescription>Rule-based score shown: {alert.base_score}.</AlertDescription>
          </Callout>
        )}
      </div>

      {alert.cleared_reason && (
        <Callout variant="success">
          <AlertTitle>Cleared as a legitimate lookalike</AlertTitle>
          <AlertDescription>{alert.cleared_reason}</AlertDescription>
        </Callout>
      )}

      <Card>
        <CardHeader>
          <CardTitle>Why it was flagged</CardTitle>
          <CardDescription>Each factor adds to the rule-based score.</CardDescription>
        </CardHeader>
        <CardPanel>
          <ol className="space-y-2">
            {factors.map((f, i) => (
              <li key={i} className="flex gap-3 rounded-lg border px-3 py-2">
                <span
                  className={`w-10 shrink-0 text-right font-mono font-semibold ${
                    f.points > 0 ? 'text-destructive-foreground' : 'text-muted-foreground'
                  }`}
                >
                  {f.points > 0 ? `+${f.points}` : f.points}
                </span>
                <span className="min-w-0">
                  <span className="block">{f.factor}</span>
                  {f.evidence_id && (
                    <span className="font-mono text-muted-foreground text-xs">evidence {f.evidence_id}</span>
                  )}
                </span>
              </li>
            ))}
          </ol>
        </CardPanel>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Related entities</CardTitle>
          <CardDescription>
            Customers, accounts, devices, loan applications and claims linked through shared identifiers.
          </CardDescription>
        </CardHeader>
        <CardPanel>
          <EntityGraph entityId={graphRoot} />
        </CardPanel>
      </Card>
    </section>
  )
}
