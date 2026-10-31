import { ArrowLeftIcon, SparklesIcon } from 'lucide-react'
import { useEffect, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router'
import EntityGraph from '@/components/EntityGraph'
import PageHeader from '@/components/PageHeader'
import RiskBadge from '@/components/RiskBadge'
import { Alert as Callout, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardDescription, CardHeader, CardPanel, CardTitle } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import { toastManager } from '@/components/ui/toast'
import { can, getAlert, openCaseFromAlert, type Alert, type EvidenceRecord } from '@/lib/api'
import { useRole } from '@/lib/role'

const TYPE_LABELS: Record<string, string> = {
  transaction: 'Transaction',
  login_event: 'Login Event',
  beneficiary_change: 'Beneficiary Change',
  loan_application: 'Loan Application',
  insurance_claim: 'Insurance Claim',
  customer: 'Customer',
  account: 'Account',
}

const PRIORITY_FIELDS = ['timestamp', 'applied_at', 'changed_at', 'claim_date', 'incident_date', 'amount_inr', 'channel', 'status', 'outcome', 'event_type']

function label(key: string) {
  return key.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())
}

function EvidenceCard({ ev }: { ev: EvidenceRecord }) {
  const allKeys = Object.keys(ev.record)
  const priority = PRIORITY_FIELDS.filter((k) => allKeys.includes(k))
  const rest = allKeys.filter((k) => !PRIORITY_FIELDS.includes(k))
  const ordered = [...priority, ...rest]

  return (
    <div className="rounded-lg border text-sm">
      <div className="flex items-center gap-2 border-b px-3 py-2 bg-muted/40">
        <Badge variant="outline" className="capitalize text-xs">
          {TYPE_LABELS[ev.type] ?? ev.type}
        </Badge>
        <span className="font-mono text-muted-foreground text-xs truncate">{ev.id}</span>
      </div>
      <dl className="grid grid-cols-[auto_1fr] gap-x-4 gap-y-1 px-3 py-2">
        {ordered.map((k) => {
          const v = ev.record[k]
          if (v === null || v === undefined) return null
          return (
            <>
              <dt key={`dt-${k}`} className="text-muted-foreground whitespace-nowrap">{label(k)}</dt>
              <dd key={`dd-${k}`} className="font-mono break-all">{String(v)}</dd>
            </>
          )
        })}
      </dl>
    </div>
  )
}

export default function AlertDetailPage() {
  const { alertId = '' } = useParams()
  const [alert, setAlert] = useState<(Alert & { case_id?: string | null }) | null>(null)
  const [error, setError] = useState<string | null>(null)
  const role = useRole()
  const navigate = useNavigate()

  // Detection leaves Low alerts without a case; an investigator can still open one with a reason.
  const openCase = async () => {
    const reason = window.prompt('Why open a case for this alert?')?.trim()
    if (!reason) return
    try {
      const c = await openCaseFromAlert(alertId, reason)
      void navigate(`/cases/${c.case_id}`)
    } catch (e) {
      toastManager.add({ type: 'error', title: 'Case not opened', description: e instanceof Error ? e.message : '' })
    }
  }

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
        {alert.case_id ? (
          <Button size="sm" variant="outline" render={<Link to={`/cases/${alert.case_id}`} />}>
            Open its investigation
          </Button>
        ) : (
          alert.status === 'open' &&
          can.decide(role) && (
            <Button size="sm" variant="outline" onClick={() => void openCase()}>
              Open a case
            </Button>
          )
        )}
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

      {alert.evidence && alert.evidence.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Ingested records</CardTitle>
            <CardDescription>
              Complete data for the flagged entity and all cited evidence — {alert.evidence.length} record{alert.evidence.length !== 1 ? 's' : ''}.
            </CardDescription>
          </CardHeader>
          <CardPanel className="space-y-3">
            {alert.evidence.map((ev) => (
              <EvidenceCard key={ev.id} ev={ev} />
            ))}
          </CardPanel>
        </Card>
      )}

      <Card>
        <CardHeader>
          <CardTitle>Related entities</CardTitle>
          <CardDescription>
            Customers, accounts, devices, loan applications and claims linked through shared identifiers.
          </CardDescription>
        </CardHeader>
        <CardPanel>
          <EntityGraph alertId={alert.alert_id} />
        </CardPanel>
      </Card>
    </section>
  )
}
