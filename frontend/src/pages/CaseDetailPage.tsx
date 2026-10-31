import {
  ArrowLeftIcon,
  CheckIcon,
  DownloadIcon,
  EyeIcon,
  EyeOffIcon,
  ExternalLinkIcon,
  LockIcon,
  ScissorsIcon,
  XIcon,
} from 'lucide-react'
import { useCallback, useEffect, useState, type FormEvent } from 'react'
import { Link, useParams } from 'react-router'
import CaseGraph from '@/components/CaseGraph'
import PageHeader from '@/components/PageHeader'
import RiskBadge from '@/components/RiskBadge'
import { Alert as Callout, AlertDescription, AlertTitle } from '@/components/ui/alert'
import {
  AlertDialog,
  AlertDialogClose,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogPopup,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardDescription, CardHeader, CardPanel, CardTitle } from '@/components/ui/card'
import { Label } from '@/components/ui/label'
import { Radio, RadioGroup } from '@/components/ui/radio-group'
import { Select, SelectItem, SelectPopup, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Skeleton } from '@/components/ui/skeleton'
import { Spinner } from '@/components/ui/spinner'
import { Tabs, TabsList, TabsPanel, TabsTab } from '@/components/ui/tabs'
import { Textarea } from '@/components/ui/textarea'
import { toastManager } from '@/components/ui/toast'
import {
  addNote,
  can,
  decideRecommendation,
  downloadCaseReport,
  getCase,
  overrideRisk,
  PII_FIELDS,
  recordDecision,
  revealPii,
  splitCase,
  type CaseAlert,
  type CaseDecision,
  type CaseWorkspace,
  type PiiField,
  type Recommendation,
  type RiskBand,
} from '@/lib/api'
import { ROLE_LABELS, type Role, useRole, useUser } from '@/lib/role'
import { StatusBadge } from '@/pages/CasesPage'

// Investigation workspace (level2.md §4): timeline, alerts and why they were grouped, the case network,
// entities, indicators, evidence, risk, notes and history, plus the analyst actions.

const DECISIONS: { value: CaseDecision; label: string; hint: string }[] = [
  { value: 'requires_investigation', label: 'Needs further investigation', hint: 'Keep the case open and investigate.' },
  { value: 'request_info', label: 'Request additional information', hint: 'Wait for the customer, branch or another team.' },
  {
    value: 'recommend_hold',
    label: 'Recommend a temporary hold',
    hint: 'A different Supervisor must approve. No account is changed.',
  },
  {
    value: 'recommend_verification',
    label: 'Recommend enhanced verification',
    hint: 'A different Supervisor must approve. No account is changed.',
  },
  { value: 'escalate', label: 'Escalate to a specialist or supervisor', hint: 'Hands the case over; it stays open for them.' },
  { value: 'false_positive', label: 'False positive', hint: 'Close the case; the original alerts and evidence are kept.' },
  { value: 'conclude', label: 'Record investigation conclusion', hint: 'Closes the case with your conclusion as the record.' },
]
const FINAL = new Set(['closed', 'concluded'])
const CONFIRM = new Set<CaseDecision>(['escalate', 'false_positive', 'conclude'])
const RISKS: { value: RiskBand; label: string }[] = [
  { value: 'High', label: 'High' },
  { value: 'Medium', label: 'Medium' },
  { value: 'Low', label: 'Low' },
]

const when = (iso: string | null) =>
  iso ? new Date(iso).toLocaleString('en-IN', { dateStyle: 'medium', timeStyle: 'short' }) : '-'
const humanize = (s: string) => s.replaceAll('_', ' ')
const errorText = (e: unknown) => (e instanceof Error ? e.message : '')

export default function CaseDetailPage() {
  const { caseId = '' } = useParams()
  const role = useRole()
  const user = useUser()
  const [item, setItem] = useState<CaseWorkspace | null>(null)
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
      toastManager.add({ type: 'success', title: 'Action recorded', description: humanize(decision) })
      setReason('')
      load()
    } catch (e) {
      toastManager.add({ type: 'error', title: 'Action not saved', description: errorText(e) })
    } finally {
      setSaving(false)
      setConfirmOpen(false)
    }
  }

  const submit = (e: FormEvent) => {
    e.preventDefault()
    if (CONFIRM.has(decision)) setConfirmOpen(true)
    else void save()
  }

  const actions = (
    <div className="flex gap-2">
      <Button
        variant="outline"
        onClick={() =>
          downloadCaseReport(caseId).catch((e) =>
            toastManager.add({ type: 'error', title: 'Report not downloaded', description: errorText(e) }),
          )
        }
      >
        <DownloadIcon />
        Download report
      </Button>
      <Button variant="outline" render={<Link to="/cases" />}>
        <ArrowLeftIcon />
        All cases
      </Button>
    </div>
  )

  if (error) {
    return (
      <section>
        <PageHeader title="Case" action={actions} />
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
  const reasons = item.risk.priority_parts.review_reasons ?? []
  const chosen = DECISIONS.find((d) => d.value === decision) ?? DECISIONS[0]

  return (
    <section className="space-y-5">
      <PageHeader
        title={item.fraud_category}
        description={`Case ${item.case_id} · ${item.alerts.length} alert${item.alerts.length === 1 ? '' : 's'}`}
        action={actions}
      />

      <div className="flex flex-wrap items-center gap-2 text-sm">
        <RiskBadge band={item.risk_level} score={undefined} />
        {item.risk_original && <span className="text-muted-foreground text-xs">was {item.risk_original}</span>}
        <Badge variant="outline" className="tabular-nums">
          Priority {item.priority_score}
        </Badge>
        {item.needs_review && <Badge variant="warning">Needs review</Badge>}
        <StatusBadge status={item.status} />
        {item.customer_id && (
          <span className="text-muted-foreground">
            customer <span className="font-mono">{item.customer_id}</span>
          </span>
        )}
        {item.split_from && (
          <Button size="sm" variant="ghost" render={<Link to={`/cases/${item.split_from}`} />}>
            Split from case {item.split_from.slice(0, 8)}
            <ExternalLinkIcon />
          </Button>
        )}
      </div>

      {item.needs_review && (
        <Callout variant="warning">
          <AlertTitle>Needs review before it is prioritised</AlertTitle>
          <AlertDescription>
            Weak evidence ({reasons.join(', ')}), so its priority is capped. Check it before acting on it.
          </AlertDescription>
        </Callout>
      )}
      {item.conclusion && (
        <Callout variant="info">
          <AlertTitle>Investigation conclusion</AlertTitle>
          <AlertDescription>{item.conclusion}</AlertDescription>
        </Callout>
      )}

      {item.customer && <CustomerCard caseId={item.case_id} masked={item.customer} role={role} />}

      <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_minmax(0,1fr)]">
        <Card>
          <CardHeader>
            <CardTitle>Analyst actions</CardTitle>
            <CardDescription>
              {locked
                ? `This case is ${humanize(item.status)}; no further actions.`
                : allowed
                  ? `Acting as ${user}. Every action goes into the case history and the audit trail.`
                  : `The ${ROLE_LABELS[role]} role can view cases but not act on them.`}
            </CardDescription>
          </CardHeader>
          <CardPanel>
            <form onSubmit={submit} className="space-y-4">
              <fieldset disabled={locked || !allowed} className="space-y-4 disabled:opacity-60">
                <legend className="sr-only">Action</legend>
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
                  <Label htmlFor="reason">{decision === 'conclude' ? 'Conclusion' : 'Reason'}</Label>
                  <Textarea
                    id="reason"
                    required
                    value={reason}
                    onChange={(e) => setReason((e.target as HTMLTextAreaElement).value)}
                    placeholder={
                      decision === 'conclude' ? 'What did the investigation find?' : 'What did you check, and why?'
                    }
                  />
                </div>
                <Button type="submit" disabled={saving || !reason.trim()}>
                  {saving && <Spinner />}
                  Save
                </Button>
              </fieldset>
            </form>
          </CardPanel>
        </Card>

        <Recommendations items={item.recommendations} role={role} user={user} onChange={load} />
      </div>

      <Tabs defaultValue="timeline">
        <TabsList className="flex-wrap">
          <TabsTab value="timeline">Timeline</TabsTab>
          <TabsTab value="alerts">Alerts ({item.alerts.length})</TabsTab>
          <TabsTab value="network">Network</TabsTab>
          <TabsTab value="entities">Entities</TabsTab>
          <TabsTab value="indicators">Indicators ({item.indicators.length})</TabsTab>
          <TabsTab value="evidence">Evidence ({item.evidence.length})</TabsTab>
          <TabsTab value="risk">Risk</TabsTab>
          <TabsTab value="notes">Notes ({item.notes.length})</TabsTab>
          <TabsTab value="history">History</TabsTab>
        </TabsList>

        <TabsPanel value="timeline" className="pt-4">
          <ol className="space-y-3 border-l pl-4">
            {item.timeline.map((t, i) => (
              <li key={`${t.id}-${i}`} className="text-sm">
                <div className="text-muted-foreground text-xs tabular-nums">
                  {when(t.at)} · {t.kind === 'alert' ? 'Detection' : humanize(t.type)}
                </div>
                <div className={t.kind === 'alert' ? 'font-medium' : ''}>{t.summary}</div>
                <div className="font-mono text-muted-foreground text-xs">{t.id}</div>
              </li>
            ))}
          </ol>
        </TabsPanel>

        <TabsPanel value="alerts" className="pt-4">
          <AlertsList item={item} canSplit={allowed && !locked && item.alerts.length > 1} onChange={load} />
        </TabsPanel>

        <TabsPanel value="network" className="pt-4">
          <CaseGraph caseId={item.case_id} primaryAlertId={item.alert_id} alerts={item.alerts} evidence={item.evidence} />
        </TabsPanel>

        <TabsPanel value="entities" className="pt-4">
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {item.entities.map((group) => (
              <Card key={group.type}>
                <CardHeader>
                  <CardTitle className="text-sm capitalize">
                    {group.type} ({group.values.length})
                  </CardTitle>
                </CardHeader>
                <CardPanel>
                  <ul className="space-y-1 text-xs">
                    {group.values.map((v) => (
                      <li key={v.value} className="flex items-center justify-between gap-2">
                        <span className="break-all font-mono">{v.value}</span>
                        {v.alert_ids.length > 1 && <Badge variant="warning">{v.alert_ids.length} alerts</Badge>}
                      </li>
                    ))}
                  </ul>
                </CardPanel>
              </Card>
            ))}
          </div>
        </TabsPanel>

        <TabsPanel value="indicators" className="pt-4">
          <ul className="divide-y rounded-lg border">
            {item.indicators.map((f, i) => (
              <li key={i} className="flex items-start gap-3 px-3 py-2 text-sm">
                <span className="w-10 shrink-0 text-right tabular-nums">+{f.points}</span>
                <span className="flex-1">
                  {f.factor}
                  <span className="block text-muted-foreground text-xs">
                    {f.rule_id}
                    {f.evidence_id && (
                      <>
                        {' '}
                        · evidence <span className="font-mono">{f.evidence_id}</span>
                      </>
                    )}
                  </span>
                </span>
              </li>
            ))}
          </ul>
        </TabsPanel>

        <TabsPanel value="evidence" className="pt-4">
          <div className="grid gap-3 lg:grid-cols-2">
            {item.evidence.map((e) => (
              <div key={e.id} className="rounded-lg border p-3 text-xs">
                <div className="mb-1 font-medium text-sm capitalize">
                  {humanize(e.type)} <span className="font-mono normal-case">{e.id}</span>
                </div>
                <RecordFields record={e.record} />
              </div>
            ))}
          </div>
        </TabsPanel>

        <TabsPanel value="risk" className="pt-4">
          <RiskPanel item={item} canOverride={allowed && !locked} onChange={load} />
        </TabsPanel>

        <TabsPanel value="notes" className="pt-4">
          <Notes item={item} canWrite={can.note(role)} onChange={load} />
        </TabsPanel>

        <TabsPanel value="history" className="pt-4">
          {item.history.length === 0 ? (
            <p className="text-muted-foreground text-sm">No actions yet.</p>
          ) : (
            <ol className="space-y-3 border-l pl-4">
              {item.history.map((h) => (
                <li key={h.history_id} className="text-sm">
                  <div className="text-muted-foreground text-xs tabular-nums">
                    {when(h.changed_at)} · {h.user_id ?? h.changed_by} ({h.changed_by})
                  </div>
                  <div>
                    <span className="capitalize">{humanize(h.decision ?? 'update')}</span>
                    {h.from_status !== h.to_status && (
                      <>
                        : {h.from_status && humanize(h.from_status)} → {humanize(h.to_status)}
                      </>
                    )}
                  </div>
                  {h.reason && <div className="text-muted-foreground">“{h.reason}”</div>}
                </li>
              ))}
            </ol>
          )}
        </TabsPanel>
      </Tabs>

      <AlertDialog open={confirmOpen} onOpenChange={setConfirmOpen}>
        <AlertDialogPopup>
          <AlertDialogHeader>
            <AlertDialogTitle>{chosen.label}?</AlertDialogTitle>
            <AlertDialogDescription>{chosen.hint}</AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogClose render={<Button variant="ghost" />}>Cancel</AlertDialogClose>
            <Button
              variant={decision === 'escalate' ? 'destructive' : 'default'}
              onClick={() => void save()}
              disabled={saving}
            >
              {saving && <Spinner />}
              Confirm
            </Button>
          </AlertDialogFooter>
        </AlertDialogPopup>
      </AlertDialog>
    </section>
  )
}

function RecordFields({ record }: { record: Record<string, unknown> }) {
  return (
    <dl className="grid grid-cols-[max-content_minmax(0,1fr)] gap-x-3 gap-y-0.5">
      {Object.entries(record).map(([k, v]) =>
        v === null || v === '' ? null : (
          <div key={k} className="contents">
            <dt className="text-muted-foreground">{humanize(k)}</dt>
            <dd className="break-all font-mono">{String(v)}</dd>
          </div>
        ),
      )}
    </dl>
  )
}

/** The case's alerts, each with the matching identifiers that grouped it, and a split action. */
function AlertsList({ item, canSplit, onChange }: { item: CaseWorkspace; canSplit: boolean; onChange: () => void }) {
  const [target, setTarget] = useState<CaseAlert | null>(null)
  const [reason, setReason] = useState('')
  const [busy, setBusy] = useState(false)

  const split = async () => {
    if (!target) return
    setBusy(true)
    try {
      const { new_case } = await splitCase(item.case_id, target.alert_id, reason.trim())
      toastManager.add({
        type: 'success',
        title: 'Alert split into a new case',
        description: `Case ${new_case.case_id.slice(0, 8)}; both cases keep their evidence.`,
      })
      setTarget(null)
      setReason('')
      onChange()
    } catch (e) {
      toastManager.add({ type: 'error', title: 'Split failed', description: errorText(e) })
    } finally {
      setBusy(false)
    }
  }

  return (
    <>
      <ul className="space-y-3">
        {item.alerts.map((a) => (
          <li key={a.alert_id} className="rounded-lg border p-3">
            <div className="flex flex-wrap items-center gap-2">
              <RiskBadge band={a.risk_band} score={a.final_score} />
              <span className="font-medium">{a.rule_id}</span>
              <span className="text-muted-foreground text-sm">{a.fraud_category}</span>
              {a.product && <Badge variant="outline">{a.product}</Badge>}
              {a.alert_id === item.alert_id && <Badge variant="info">Primary</Badge>}
              <span className="ml-auto flex gap-1">
                <Button size="xs" variant="ghost" render={<Link to={`/alerts/${a.alert_id}`} />}>
                  Open alert
                  <ExternalLinkIcon />
                </Button>
                {canSplit && (
                  <Button size="xs" variant="outline" onClick={() => setTarget(a)}>
                    <ScissorsIcon />
                    Split out
                  </Button>
                )}
              </span>
            </div>
            <p className="mt-2 text-sm">
              <span className="text-muted-foreground">Why grouped: </span>
              {a.link_reason}
            </p>
            {a.links.length > 0 && (
              <ul className="mt-2 flex flex-wrap gap-1.5" aria-label="Matching identifiers">
                {a.links.map((l, i) => (
                  <li key={i}>
                    <Badge variant="outline" className="font-normal">
                      {l.type} <span className="font-mono">{l.value}</span> ↔ {l.with_rule}
                    </Badge>
                  </li>
                ))}
              </ul>
            )}
            <ul className="mt-2 space-y-0.5 text-muted-foreground text-xs">
              {a.factors.map((f, i) => (
                <li key={i}>
                  +{f.points} {f.factor}
                </li>
              ))}
            </ul>
            {a.ai_recommendation && (
              <p className="mt-2 text-xs">
                <span className="text-muted-foreground">
                  AI review ({a.ai_adjustment >= 0 ? '+' : ''}
                  {a.ai_adjustment}, comment only, never a link):{' '}
                </span>
                {a.ai_recommendation}
              </p>
            )}
          </li>
        ))}
      </ul>

      <AlertDialog open={target !== null} onOpenChange={(open) => !open && setTarget(null)}>
        <AlertDialogPopup>
          <AlertDialogHeader>
            <AlertDialogTitle>Split {target?.rule_id} into its own case?</AlertDialogTitle>
            <AlertDialogDescription>
              The alert moves to a new case. Nothing is deleted, and the split is audited.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <div className="space-y-1.5 px-6">
            <Label htmlFor="split-reason">Why does it not belong here?</Label>
            <Textarea
              id="split-reason"
              value={reason}
              onChange={(e) => setReason((e.target as HTMLTextAreaElement).value)}
            />
          </div>
          <AlertDialogFooter>
            <AlertDialogClose render={<Button variant="ghost" />}>Cancel</AlertDialogClose>
            <Button onClick={() => void split()} disabled={busy || !reason.trim()}>
              {busy && <Spinner />}
              Split
            </Button>
          </AlertDialogFooter>
        </AlertDialogPopup>
      </AlertDialog>
    </>
  )
}

function RiskPanel({ item, canOverride, onChange }: { item: CaseWorkspace; canOverride: boolean; onChange: () => void }) {
  const [level, setLevel] = useState<RiskBand>(item.risk_level)
  const [reason, setReason] = useState('')
  const [busy, setBusy] = useState(false)
  const p = item.risk.priority_parts
  const parts: [string, number | undefined, string][] = [
    ['Severity', p.severity, 'highest final score among the alerts'],
    ['Financial exposure', p.exposure, `₹${p.exposure_inr ?? '0'} in the evidence, on a log scale`],
    ['Related events', p.related_events, `${p.alert_count ?? 0} alerts, ${p.evidence_count ?? 0} records`],
    ['Confidence', p.confidence, 'share of factors backed by evidence, and whether the AI agrees'],
  ]

  const save = async (e: FormEvent) => {
    e.preventDefault()
    setBusy(true)
    try {
      await overrideRisk(item.case_id, level, reason.trim())
      toastManager.add({ type: 'success', title: 'Risk classification changed', description: 'The original is kept.' })
      setReason('')
      onChange()
    } catch (err) {
      toastManager.add({ type: 'error', title: 'Not changed', description: errorText(err) })
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="grid gap-4 lg:grid-cols-2">
      <Card>
        <CardHeader>
          <CardTitle>Risk assessment</CardTitle>
          <CardDescription>
            Priority {item.priority_score} / 100{item.needs_review ? ' (capped: needs review)' : ''}
          </CardDescription>
        </CardHeader>
        <CardPanel className="space-y-3">
          {parts.map(([label, value, hint]) => {
            const pct = Math.round((value ?? 0) * 100)
            return (
              <div key={label} className="space-y-1">
                <div className="flex justify-between text-sm">
                  <span>{label}</span>
                  <span className="tabular-nums">{pct}%</span>
                </div>
                <div className="h-2 rounded bg-muted">
                  <div className="h-2 rounded bg-primary" style={{ width: `${pct}%` }} />
                </div>
                <div className="text-muted-foreground text-xs">{hint}</div>
              </div>
            )
          })}
          <dl className="grid grid-cols-[max-content_minmax(0,1fr)] gap-x-4 gap-y-1 pt-2 text-sm">
            <dt className="text-muted-foreground">Current classification</dt>
            <dd>{item.risk_level}</dd>
            <dt className="text-muted-foreground">Original classification</dt>
            <dd>{item.risk_original ?? `${item.risk_level} (unchanged)`}</dd>
            {item.risk_reason && (
              <>
                <dt className="text-muted-foreground">Changed by</dt>
                <dd>{item.risk_changed_by}</dd>
                <dt className="text-muted-foreground">Reason</dt>
                <dd>{item.risk_reason}</dd>
              </>
            )}
          </dl>
        </CardPanel>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Change risk classification</CardTitle>
          <CardDescription>The original classification and your reason are kept in the case and its report.</CardDescription>
        </CardHeader>
        <CardPanel>
          <form onSubmit={save}>
            <fieldset disabled={!canOverride} className="space-y-3 disabled:opacity-60">
              <Select items={RISKS} value={level} onValueChange={(v) => v && setLevel(v as RiskBand)}>
                <SelectTrigger aria-label="New risk level" className="w-48">
                  <SelectValue />
                </SelectTrigger>
                <SelectPopup>
                  {RISKS.map((r) => (
                    <SelectItem key={r.value} value={r.value}>
                      {r.label}
                    </SelectItem>
                  ))}
                </SelectPopup>
              </Select>
              <Textarea
                aria-label="Reason for the change"
                value={reason}
                onChange={(e) => setReason((e.target as HTMLTextAreaElement).value)}
                placeholder="Why is the classification wrong?"
              />
              <Button type="submit" disabled={busy || !reason.trim() || level === item.risk_level}>
                {busy && <Spinner />}
                Change classification
              </Button>
            </fieldset>
          </form>
        </CardPanel>
      </Card>
    </div>
  )
}

function Notes({ item, canWrite, onChange }: { item: CaseWorkspace; canWrite: boolean; onChange: () => void }) {
  const [body, setBody] = useState('')
  const [busy, setBusy] = useState(false)

  const save = async (e: FormEvent) => {
    e.preventDefault()
    setBusy(true)
    try {
      await addNote(item.case_id, body.trim())
      setBody('')
      onChange()
    } catch (err) {
      toastManager.add({ type: 'error', title: 'Note not saved', description: errorText(err) })
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_22rem]">
      <ol className="space-y-3">
        {item.notes.length === 0 && <li className="text-muted-foreground text-sm">No notes yet.</li>}
        {item.notes.map((n) => (
          <li key={n.note_id} className="rounded-lg border p-3 text-sm">
            <div className="text-muted-foreground text-xs">
              {when(n.created_at)} · {n.author_user} ({n.author_role})
            </div>
            <p className="whitespace-pre-wrap">{n.body}</p>
          </li>
        ))}
      </ol>
      <form onSubmit={save} className="space-y-2">
        <Label htmlFor="note">Add a note</Label>
        <Textarea
          id="note"
          disabled={!canWrite}
          value={body}
          onChange={(e) => setBody((e.target as HTMLTextAreaElement).value)}
          placeholder={canWrite ? 'What did you find?' : 'Analysts can read notes but not add them.'}
        />
        <Button type="submit" disabled={!canWrite || busy || !body.trim()}>
          {busy && <Spinner />}
          Add note
        </Button>
      </form>
    </div>
  )
}

/** Hold and verification recommendations; a Supervisor who is not the maker approves or rejects. */
function Recommendations({
  items,
  role,
  user,
  onChange,
}: {
  items: Recommendation[]
  role: Role
  user: string
  onChange: () => void
}) {
  const [reason, setReason] = useState<Record<string, string>>({})
  const [busy, setBusy] = useState<string | null>(null)

  const decide = async (rec: Recommendation, approve: boolean) => {
    setBusy(rec.recommendation_id)
    try {
      await decideRecommendation(rec.recommendation_id, approve, (reason[rec.recommendation_id] ?? '').trim())
      toastManager.add({
        type: 'success',
        title: approve ? 'Recommendation approved' : 'Recommendation rejected',
        description: 'Authorisation recorded. No account or transaction was changed.',
      })
      onChange()
    } catch (e) {
      toastManager.add({ type: 'error', title: 'Not recorded', description: errorText(e) })
    } finally {
      setBusy(null)
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Recommendations</CardTitle>
        <CardDescription>
          Holds and verifications stay recommendations until a different Supervisor approves them. This system never
          changes an account or transaction.
        </CardDescription>
      </CardHeader>
      <CardPanel>
        {items.length === 0 ? (
          <p className="text-muted-foreground text-sm">
            None yet. Use “Recommend a temporary hold” or “Recommend enhanced verification”.
          </p>
        ) : (
          <ul className="space-y-3">
            {items.map((r) => {
              const mine = r.maker_user === user
              const canDecide = can.approve(role) && !mine && r.status === 'pending'
              const text = (reason[r.recommendation_id] ?? '').trim()
              return (
                <li key={r.recommendation_id} className="rounded-lg border p-3 text-sm">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="font-medium">{r.kind === 'hold' ? 'Temporary hold' : 'Enhanced verification'}</span>
                    <Badge variant={r.status === 'approved' ? 'success' : r.status === 'rejected' ? 'error' : 'warning'}>
                      {r.status === 'pending' ? 'recommended' : r.status}
                    </Badge>
                  </div>
                  <div className="text-muted-foreground text-xs">
                    by {r.maker_user} ({r.maker_role}) · {when(r.created_at)}
                  </div>
                  <p className="mt-1">“{r.reason}”</p>
                  {r.decided_by && (
                    <p className="mt-1 text-muted-foreground text-xs">
                      {r.status} by {r.decided_by} · {when(r.decided_at)}: “{r.decision_reason}”
                    </p>
                  )}
                  {r.status === 'pending' &&
                    (canDecide ? (
                      <div className="mt-2 space-y-2">
                        <Textarea
                          aria-label="Reason for approving or rejecting"
                          value={reason[r.recommendation_id] ?? ''}
                          onChange={(e) =>
                            setReason((m) => ({ ...m, [r.recommendation_id]: (e.target as HTMLTextAreaElement).value }))
                          }
                          placeholder="Reason for approving or rejecting"
                        />
                        <div className="flex gap-2">
                          <Button size="sm" disabled={busy !== null || !text} onClick={() => void decide(r, true)}>
                            <CheckIcon />
                            Approve
                          </Button>
                          <Button
                            size="sm"
                            variant="outline"
                            disabled={busy !== null || !text}
                            onClick={() => void decide(r, false)}
                          >
                            <XIcon />
                            Reject
                          </Button>
                        </div>
                      </div>
                    ) : (
                      <p className="mt-2 text-muted-foreground text-xs">
                        {mine
                          ? 'You made this recommendation, so another Supervisor must approve it.'
                          : 'Waiting for a Supervisor to approve or reject.'}
                      </p>
                    ))}
                </li>
              )
            })}
          </ul>
        )}
      </CardPanel>
    </Card>
  )
}

/** Masked customer fields; a supervisor can reveal one at a time, and each reveal is audited server-side. */
function CustomerCard({ caseId, masked, role }: { caseId: string; masked: Record<PiiField, string>; role: Role }) {
  const [revealed, setRevealed] = useState<Partial<Record<PiiField, string>>>({})
  const [busy, setBusy] = useState<PiiField | null>(null)
  const allowed = can.reveal(role)

  // Switching away from Supervisor (or to another case) hides everything again.
  useEffect(() => setRevealed({}), [role, caseId])

  const toggle = async (field: PiiField) => {
    if (revealed[field] !== undefined) {
      setRevealed((r) => ({ ...r, [field]: undefined }))
      return
    }
    setBusy(field)
    try {
      const { plaintext_value } = await revealPii(caseId, field)
      setRevealed((r) => ({ ...r, [field]: plaintext_value }))
      toastManager.add({ type: 'info', title: 'Value revealed', description: 'This reveal was written to the audit trail.' })
    } catch (e) {
      toastManager.add({ type: 'error', title: 'Reveal refused', description: e instanceof Error ? e.message : '' })
    } finally {
      setBusy(null)
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Customer details</CardTitle>
        <CardDescription>
          {allowed
            ? 'Masked by default. Each reveal is recorded in the audit trail.'
            : `Masked. Only a Supervisor can reveal these; the ${ROLE_LABELS[role]} role sees tokens only.`}
        </CardDescription>
      </CardHeader>
      <CardPanel>
        <dl className="grid gap-x-6 gap-y-2 text-sm sm:grid-cols-[max-content_minmax(0,1fr)_max-content]">
          {PII_FIELDS.map(({ key, label }) => {
            const plain = revealed[key]
            return (
              <div key={key} className="contents">
                <dt className="text-muted-foreground">{label}</dt>
                <dd className={plain === undefined ? 'font-mono text-muted-foreground' : 'break-words'}>
                  {plain ?? masked[key]}
                </dd>
                <dd className="max-sm:mb-2">
                  {allowed ? (
                    <Button size="xs" variant="ghost" onClick={() => void toggle(key)} disabled={busy === key}>
                      {busy === key ? <Spinner /> : plain === undefined ? <EyeIcon /> : <EyeOffIcon />}
                      {plain === undefined ? 'Reveal' : 'Hide'}
                    </Button>
                  ) : (
                    <LockIcon className="size-4 text-muted-foreground" aria-label="Locked for your role" />
                  )}
                </dd>
              </div>
            )
          })}
        </dl>
      </CardPanel>
    </Card>
  )
}
