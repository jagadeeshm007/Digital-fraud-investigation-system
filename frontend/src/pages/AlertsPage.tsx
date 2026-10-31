import { PlayIcon, RefreshCwIcon } from 'lucide-react'
import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router'
import PageHeader from '@/components/PageHeader'
import RiskBadge from '@/components/RiskBadge'
import { Alert as Callout, AlertDescription } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import { Card, CardPanel } from '@/components/ui/card'
import { Empty, EmptyDescription, EmptyHeader, EmptyTitle } from '@/components/ui/empty'
import { Input } from '@/components/ui/input'
import { Select, SelectItem, SelectPopup, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Skeleton } from '@/components/ui/skeleton'
import { Spinner } from '@/components/ui/spinner'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { toastManager } from '@/components/ui/toast'
import { getAlerts, runDetection, type Alert, type Paged } from '@/lib/api'
import { useRole } from '@/lib/role'

const PAGE_SIZE = 20
const ALL = 'all'
const BANDS = [
  { value: ALL, label: 'All risk levels' },
  { value: 'High', label: 'High' },
  { value: 'Medium', label: 'Medium' },
  { value: 'Low', label: 'Low' },
]
const STATUSES = [
  { value: 'open', label: 'Open' },
  { value: 'cleared', label: 'Cleared lookalikes' },
  { value: ALL, label: 'All statuses' },
]

export default function AlertsPage() {
  const role = useRole()
  const canRun = role !== 'analyst'
  const [page, setPage] = useState(1)
  const [band, setBand] = useState(ALL)
  const [status, setStatus] = useState('open')
  const [customer, setCustomer] = useState('')
  const [txn, setTxn] = useState('')
  const [dateFrom, setDateFrom] = useState('')
  const [dateTo, setDateTo] = useState('')
  const [data, setData] = useState<Paged<Alert> | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [running, setRunning] = useState(false)

  const load = useCallback(async () => {
    setError(null)
    try {
      setData(
        await getAlerts({
          page,
          page_size: PAGE_SIZE,
          risk_band: band === ALL ? undefined : band,
          status: status === ALL ? undefined : status,
          customer_id: customer.trim() || undefined,
          transaction_id: txn.trim() || undefined,
          date_from: dateFrom || undefined,
          date_to: dateTo || undefined,
        }),
      )
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not load alerts')
    }
  }, [page, band, status, customer, txn, dateFrom, dateTo])

  useEffect(() => {
    void load()
  }, [load, role])

  const run = async () => {
    setRunning(true)
    try {
      const r = await runDetection()
      toastManager.add({
        type: 'success',
        title: 'Detection finished',
        description: `${r.new_alerts} new alerts, ${r.new_cases} new cases, ${r.cleared_count} lookalikes cleared`,
      })
      setPage(1)
      await load()
    } catch (err) {
      toastManager.add({
        type: 'error',
        title: 'Detection failed',
        description: err instanceof Error ? err.message : '',
      })
    } finally {
      setRunning(false)
    }
  }

  const pages = data ? Math.max(1, Math.ceil(data.total / PAGE_SIZE)) : 1

  return (
    <section className="space-y-5">
      <PageHeader
        title="Alerts"
        description="Suspicious activity scored by the detection rules, highest risk first within each run."
        action={
          <div className="flex gap-2">
            <Button variant="outline" onClick={() => void load()}>
              <RefreshCwIcon />
              Refresh
            </Button>
            {canRun && (
              <Button onClick={() => void run()} disabled={running}>
                {running ? <Spinner /> : <PlayIcon />}
                Run detection
              </Button>
            )}
          </div>
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
            <Input
              aria-label="Customer ID"
              placeholder="Customer ID"
              className="w-44"
              value={customer}
              onChange={(e) => {
                setCustomer((e.target as HTMLInputElement).value)
                setPage(1)
              }}
            />
            <FilterSelect label="Risk level" items={BANDS} value={band} onChange={(v) => (setBand(v), setPage(1))} />
            <FilterSelect label="Status" items={STATUSES} value={status} onChange={(v) => (setStatus(v), setPage(1))} />
            <Input
              aria-label="Transaction ID"
              placeholder="Transaction ID"
              className="w-44"
              value={txn}
              onChange={(e) => {
                setTxn((e.target as HTMLInputElement).value)
                setPage(1)
              }}
            />
            <Input
              type="date"
              aria-label="Detected from"
              title="Detected from"
              className="w-40"
              value={dateFrom}
              onChange={(e) => {
                setDateFrom((e.target as HTMLInputElement).value)
                setPage(1)
              }}
            />
            <Input
              type="date"
              aria-label="Detected to"
              title="Detected to"
              className="w-40"
              value={dateTo}
              onChange={(e) => {
                setDateTo((e.target as HTMLInputElement).value)
                setPage(1)
              }}
            />
          </div>

          {!data && !error ? (
            <div className="space-y-2">
              {Array.from({ length: 6 }, (_, i) => (
                <Skeleton key={i} className="h-9 w-full" />
              ))}
            </div>
          ) : data && data.items.length === 0 ? (
            <Empty>
              <EmptyHeader>
                <EmptyTitle>No alerts</EmptyTitle>
                <EmptyDescription>
                  {canRun ? 'Upload data, then run detection.' : 'An Investigator or Supervisor can run detection.'}
                </EmptyDescription>
              </EmptyHeader>
            </Empty>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Risk</TableHead>
                  <TableHead>Type</TableHead>
                  <TableHead>Entity</TableHead>
                  <TableHead>Customer</TableHead>
                  <TableHead>Product</TableHead>
                  <TableHead>Detected</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {data?.items.map((a) => (
                  <TableRow key={a.alert_id}>
                    <TableCell>
                      <RiskBadge band={a.risk_band} score={a.final_score} />
                    </TableCell>
                    <TableCell>
                      <Link to={`/alerts/${a.alert_id}`} className="font-medium underline-offset-4 hover:underline">
                        {a.fraud_category}
                      </Link>
                    </TableCell>
                    <TableCell className="font-mono text-xs">
                      {a.entity_type} {a.entity_id}
                    </TableCell>
                    <TableCell className="font-mono text-xs">{a.customer_id ?? '-'}</TableCell>
                    <TableCell className="capitalize">{a.product ?? '-'}</TableCell>
                    <TableCell className="tabular-nums">
                      {new Date(a.detected_at).toLocaleString('en-IN', { dateStyle: 'medium', timeStyle: 'short' })}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}

          {data && data.total > PAGE_SIZE && (
            <div className="flex items-center justify-between text-muted-foreground text-sm">
              <span>
                Page {page} of {pages} · {data.total} alerts
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

function FilterSelect({
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
      <SelectTrigger aria-label={label} className="w-48">
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
