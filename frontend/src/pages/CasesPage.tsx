import { RefreshCwIcon } from 'lucide-react'
import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router'
import PageHeader from '@/components/PageHeader'
import RiskBadge from '@/components/RiskBadge'
import { Alert as Callout, AlertDescription } from '@/components/ui/alert'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardPanel } from '@/components/ui/card'
import { Empty, EmptyDescription, EmptyHeader, EmptyTitle } from '@/components/ui/empty'
import { Select, SelectItem, SelectPopup, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Skeleton } from '@/components/ui/skeleton'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { getCases, type Case, type Paged } from '@/lib/api'
import { useRole } from '@/lib/role'

const PAGE_SIZE = 20
const ALL = 'all'
const STATUSES = [
  { value: ALL, label: 'All statuses' },
  { value: 'new', label: 'New' },
  { value: 'under_investigation', label: 'Under investigation' },
  { value: 'info_requested', label: 'Info requested' },
  { value: 'escalated', label: 'Escalated' },
  { value: 'closed', label: 'Closed' },
  { value: 'concluded', label: 'Concluded' },
]
const REVIEW = [
  { value: ALL, label: 'All cases' },
  { value: 'true', label: 'Needs review only' },
  { value: 'false', label: 'Hide needs review' },
]
const RISKS = [
  { value: ALL, label: 'All risk levels' },
  { value: 'High', label: 'High' },
  { value: 'Medium', label: 'Medium' },
  { value: 'Low', label: 'Low' },
]

export function StatusBadge({ status }: { status: string }) {
  const variant =
    status === 'escalated'
      ? 'error'
      : status === 'closed' || status === 'concluded'
        ? 'success'
        : status === 'new'
          ? 'info'
          : 'warning'
  return (
    <Badge variant={variant} className="capitalize">
      {status.replaceAll('_', ' ')}
    </Badge>
  )
}

export default function CasesPage() {
  const role = useRole()
  const [page, setPage] = useState(1)
  const [status, setStatus] = useState(ALL)
  const [risk, setRisk] = useState(ALL)
  const [review, setReview] = useState(ALL)
  const [data, setData] = useState<Paged<Case> | null>(null)
  const [error, setError] = useState<string | null>(null)

  const load = useCallback(async () => {
    setError(null)
    try {
      setData(
        await getCases({
          page,
          page_size: PAGE_SIZE,
          status: status === ALL ? undefined : status,
          risk_level: risk === ALL ? undefined : risk,
          needs_review: review === ALL ? undefined : review,
        }),
      )
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not load cases')
    }
  }, [page, status, risk, review])

  useEffect(() => {
    void load()
  }, [load, role])

  const pages = data ? Math.max(1, Math.ceil(data.total / PAGE_SIZE)) : 1

  return (
    <section className="space-y-5">
      <PageHeader
        title="Cases"
        description="Investigations, highest priority first. Alerts that share an identifier are grouped into one case."
        action={
          <Button variant="outline" onClick={() => void load()}>
            <RefreshCwIcon />
            Refresh
          </Button>
        }
      />

      {error && (
        <Callout variant="error">
          <AlertDescription>{error}</AlertDescription>
        </Callout>
      )}

      <Card>
        <CardPanel className="space-y-4">
          <div className="flex flex-wrap gap-2">
            <Filter label="Status" items={STATUSES} value={status} onChange={(v) => (setStatus(v), setPage(1))} />
            <Filter label="Risk level" items={RISKS} value={risk} onChange={(v) => (setRisk(v), setPage(1))} />
            <Filter label="Needs review" items={REVIEW} value={review} onChange={(v) => (setReview(v), setPage(1))} />
          </div>

          {!data && !error ? (
            <div className="space-y-2">
              {Array.from({ length: 5 }, (_, i) => (
                <Skeleton key={i} className="h-9 w-full" />
              ))}
            </div>
          ) : data && data.items.length === 0 ? (
            <Empty>
              <EmptyHeader>
                <EmptyTitle>No cases</EmptyTitle>
                <EmptyDescription>Run detection from the Alerts screen to open cases.</EmptyDescription>
              </EmptyHeader>
            </Empty>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Priority</TableHead>
                  <TableHead>Risk</TableHead>
                  <TableHead>Category</TableHead>
                  <TableHead>Alerts</TableHead>
                  <TableHead>Customer</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Updated</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {data?.items.map((c) => (
                  <TableRow key={c.case_id}>
                    <TableCell>
                      <span className="flex items-center gap-2">
                        <span className="w-7 font-medium tabular-nums">{c.priority_score}</span>
                        {c.needs_review && <Badge variant="warning">Needs review</Badge>}
                      </span>
                    </TableCell>
                    <TableCell>
                      <RiskBadge band={c.risk_level} score={undefined} />
                    </TableCell>
                    <TableCell>
                      <Link to={`/cases/${c.case_id}`} className="font-medium underline-offset-4 hover:underline">
                        {c.fraud_category}
                      </Link>
                    </TableCell>
                    <TableCell className="tabular-nums">{c.alert_count ?? 1}</TableCell>
                    <TableCell className="font-mono text-xs">{c.customer_id ?? '-'}</TableCell>
                    <TableCell>
                      <StatusBadge status={c.status} />
                    </TableCell>
                    <TableCell className="tabular-nums">
                      {new Date(c.updated_at).toLocaleString('en-IN', { dateStyle: 'medium', timeStyle: 'short' })}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}

          {data && data.total > PAGE_SIZE && (
            <div className="flex items-center justify-between text-muted-foreground text-sm">
              <span>
                Page {page} of {pages} · {data.total} cases
              </span>
              <div className="flex gap-2">
                <Button variant="outline" size="sm" disabled={page <= 1} onClick={() => setPage((p) => p - 1)}>
                  Previous
                </Button>
                <Button variant="outline" size="sm" disabled={page >= pages} onClick={() => setPage((p) => p + 1)}>
                  Next
                </Button>
              </div>
            </div>
          )}
        </CardPanel>
      </Card>
    </section>
  )
}

function Filter({
  label,
  items,
  value,
  onChange,
}: {
  label: string
  items: { value: string; label: string }[]
  value: string
  onChange: (value: string) => void
}) {
  return (
    <Select items={items} value={value} onValueChange={(v) => onChange(v ?? ALL)}>
      <SelectTrigger aria-label={label} className="w-52">
        <SelectValue />
      </SelectTrigger>
      <SelectPopup>
        {items.map((item) => (
          <SelectItem key={item.value} value={item.value}>
            {item.label}
          </SelectItem>
        ))}
      </SelectPopup>
    </Select>
  )
}
