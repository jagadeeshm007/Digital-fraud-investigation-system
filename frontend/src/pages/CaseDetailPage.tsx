import { ArrowLeftIcon, ExternalLinkIcon } from 'lucide-react'
import { useCallback, useEffect, useState, type FormEvent } from 'react'
import { Link, useParams } from 'react-router'
import PageHeader from '@/components/PageHeader'
import RiskBadge from '@/components/RiskBadge'
import { Alert as Callout, AlertDescription } from '@/components/ui/alert'
import {
  AlertDialog,
  AlertDialogClose,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogPopup,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog'
import { Button } from '@/components/ui/button'
import { Card, CardDescription, CardHeader, CardPanel, CardTitle } from '@/components/ui/card'
import { Label } from '@/components/ui/label'
import { Radio, RadioGroup } from '@/components/ui/radio-group'
import { Skeleton } from '@/components/ui/skeleton'
import { Spinner } from '@/components/ui/spinner'
import { Textarea } from '@/components/ui/textarea'
import { toastManager } from '@/components/ui/toast'
import { can, getCase, recordDecision, type Case, type CaseDecision, type CaseHistory } from '@/lib/api'
import { ROLE_LABELS, useRole } from '@/lib/role'
import { StatusBadge } from '@/pages/CasesPage'

const DECISIONS: { value: CaseDecision; label: string; hint: string }[] = [
  { value: 'requires_investigation', label: 'Requires investigation', hint: 'Keep the case open and investigate.' },
  { value: 'false_positive', label: 'False positive', hint: 'Close the case; the original alert is kept.' },
  { value: 'escalate', label: 'Escalate', hint: 'Hand over for further action. Cannot be undone here.' },
]
const FINAL = new Set(['closed', 'escalated'])

export default function CaseDetailPage() {
  const { caseId = '' } = useParams()
  const role = useRole()
  const [item, setItem] = useState<(Case & { history: CaseHistory[] }) | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [decision, setDecision] = useState<CaseDecision>('requires_investigation')
  const [reason, setReason] = useState('')
  const [saving, setSaving] = useState(false)
  const [confirmOpen, setConfirmOpen] = useState(false)

  const load = useCallback(() => {
    getCase(caseId)
      .then(setItem)
      .catch((e) => setError(e instanceof Error ? e.message : 'Could not load the case'))
  }, [caseId])

  useEffect(load, [load])

  const save = async () => {
    setSaving(true)
    try {
      await recordDecision(caseId, decision, reason.trim())
      toastManager.add({ type: 'success', title: 'Decision recorded', description: decision.replaceAll('_', ' ') })
      setReason('')
      load()
    } catch (e) {
      toastManager.add({ type: 'error', title: 'Decision not saved', description: e instanceof Error ? e.message : '' })
    } finally {
      setSaving(false)
      setConfirmOpen(false)
    }
  }

  const submit = (e: FormEvent) => {
    e.preventDefault()
    if (decision === 'escalate') setConfirmOpen(true)
    else void save()
  }

  const back = (
    <Button variant="outline" render={<Link to="/cases" />}>
      <ArrowLeftIcon />
      All cases
    </Button>
  )

  if (error) {
    return (
      <section>
        <PageHeader title="Case" action={back} />
        <Callout variant="error">
          <AlertDescription>{error}</AlertDescription>
        </Callout>
      </section>
    )
  }
  if (!item) {
    return (
      <section className="space-y-4">
        <Skeleton className="h-10 w-80" />
        <Skeleton className="h-48 w-full" />
      </section>
    )
  }

  const locked = FINAL.has(item.status)
  const allowed = can.decide(role)

  return (
    <section className="space-y-5">
      <PageHeader title={item.fraud_category} description={`Case ${item.case_id}`} action={back} />

      <div className="flex flex-wrap items-center gap-2 text-sm">
        <RiskBadge band={item.risk_level} score={undefined} />
        <StatusBadge status={item.status} />
        {item.customer_id && (
          <span className="text-muted-foreground">
            customer <span className="font-mono">{item.customer_id}</span>
          </span>
        )}
        <Button size="sm" variant="ghost" render={<Link to={`/alerts/${item.alert_id}`} />}>
          Open alert and graph
          <ExternalLinkIcon />
        </Button>
      </div>

      <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_minmax(0,1fr)]">
        <Card>
          <CardHeader>
            <CardTitle>Record a decision</CardTitle>
            <CardDescription>
              {locked
                ? `This case is ${item.status.replaceAll('_', ' ')}; no further decisions.`
                : allowed
                  ? 'Every decision is added to the case history and the audit trail.'
                  : `The ${ROLE_LABELS[role]} role can view cases but not decide them.`}
            </CardDescription>
          </CardHeader>
          <CardPanel>
            <form onSubmit={submit} className="space-y-4">
              <fieldset disabled={locked || !allowed} className="space-y-4 disabled:opacity-60">
                <legend className="sr-only">Decision</legend>
                <RadioGroup value={decision} onValueChange={(v) => setDecision(v as CaseDecision)}>
                  {DECISIONS.map((d) => (
                    <Label key={d.value} className="flex items-start gap-2 font-normal">
                      <Radio value={d.value} aria-label={d.label} />
                      <span>
                        <span className="block font-medium">{d.label}</span>
                        <span className="block text-muted-foreground text-xs">{d.hint}</span>
                      </span>
                    </Label>
                  ))}
                </RadioGroup>
                <div className="space-y-1.5">
                  <Label htmlFor="reason">Reason</Label>
                  <Textarea
                    id="reason"
                    required
                    value={reason}
                    onChange={(e) => setReason((e.target as HTMLTextAreaElement).value)}
                    placeholder="What did you check, and why this decision?"
                  />
                </div>
                <Button type="submit" disabled={saving || !reason.trim()}>
                  {saving && <Spinner />}
                  Save decision
                </Button>
              </fieldset>
            </form>
          </CardPanel>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>History</CardTitle>
            <CardDescription>Opened {new Date(item.created_at).toLocaleString('en-IN')}</CardDescription>
          </CardHeader>
          <CardPanel>
            {item.history.length === 0 ? (
              <p className="text-muted-foreground text-sm">No decisions yet.</p>
            ) : (
              <ol className="space-y-3 border-l pl-4">
                {item.history.map((h) => (
                  <li key={h.history_id} className="text-sm">
                    <div className="text-muted-foreground text-xs tabular-nums">
                      {new Date(h.changed_at).toLocaleString('en-IN', { dateStyle: 'medium', timeStyle: 'short' })} ·{' '}
                      <span className="capitalize">{h.changed_by}</span>
                    </div>
                    <div>
                      <span className="capitalize">{(h.decision ?? 'update').replaceAll('_', ' ')}</span>:{' '}
                      {h.from_status?.replaceAll('_', ' ')} → {h.to_status.replaceAll('_', ' ')}
                    </div>
                    {h.reason && <div className="text-muted-foreground">“{h.reason}”</div>}
                  </li>
                ))}
              </ol>
            )}
          </CardPanel>
        </Card>
      </div>

      <AlertDialog open={confirmOpen} onOpenChange={setConfirmOpen}>
        <AlertDialogPopup>
          <AlertDialogHeader>
            <AlertDialogTitle>Escalate this case?</AlertDialogTitle>
            <AlertDialogDescription>
              Escalated cases are locked for further decisions in this console.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogClose render={<Button variant="ghost" />}>Cancel</AlertDialogClose>
            <Button variant="destructive" onClick={() => void save()} disabled={saving}>
              {saving && <Spinner />}
              Escalate
            </Button>
          </AlertDialogFooter>
        </AlertDialogPopup>
      </AlertDialog>
    </section>
  )
}
