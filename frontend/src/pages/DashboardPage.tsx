import { ArrowRightIcon } from 'lucide-react'
import { useEffect, useState } from 'react'
import { Link } from 'react-router'
import BarList from '@/components/BarList'
import PageHeader from '@/components/PageHeader'
import RiskBadge from '@/components/RiskBadge'
import { Alert as Callout, AlertDescription } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import { Card, CardHeader, CardPanel, CardTitle } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { getAlerts, getSummary, type Alert, type DetectionSummary } from '@/lib/api'
import { useRole } from '@/lib/role'

const BAND_TONE: Record<string, string> = { High: 'bg-destructive', Medium: 'bg-warning', Low: 'bg-success' }

export default function DashboardPage() {
  const role = useRole()
  const [summary, setSummary] = useState<DetectionSummary | null>(null)
  const [top, setTop] = useState<Alert[]>([])
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    setError(null)
    Promise.all([getSummary(), getAlerts({ status: 'open', page_size: 200 })])
      .then(([s, a]) => {
        setSummary(s)
        setTop([...a.items].sort((x, y) => y.final_score - x.final_score).slice(0, 5))
      })
      .catch((e) => setError(e instanceof Error ? e.message : 'Could not load the dashboard'))
  }, [role])

  if (error) {
    return (
      <section>
        <PageHeader title="Dashboard" />
        <Callout variant="error">
          <AlertDescription>{error}</AlertDescription>
        </Callout>
      </section>
    )
  }

  return (
    <section className="space-y-5">
      <PageHeader title="Dashboard" description="Where fraud risk stands across all loaded systems." />

      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <Stat label="Flagged (open alerts)" value={summary?.open_alerts} />
        <Stat label="High risk" value={summary?.risk_distribution.High} tone="text-destructive-foreground" />
        <Stat label="Open cases" value={summary?.open_cases} />
        <Stat label="Lookalikes cleared" value={summary?.cleared_alerts} tone="text-success-foreground" />
      </div>

      <div className="grid gap-3 lg:grid-cols-3">
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Risk distribution</CardTitle>
          </CardHeader>
          <CardPanel>
            {summary ? (
              <BarList data={summary.risk_distribution} tone={(k) => BAND_TONE[k] ?? 'bg-primary'} />
            ) : (
              <Skeleton className="h-20" />
            )}
          </CardPanel>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Fraud categories</CardTitle>
          </CardHeader>
          <CardPanel>{summary ? <BarList data={summary.fraud_categories} /> : <Skeleton className="h-20" />}</CardPanel>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Cases by status</CardTitle>
          </CardHeader>
          <CardPanel>
            {summary ? (
              <BarList data={summary.case_statuses} tone={() => 'bg-ink'} empty="No cases yet" />
            ) : (
              <Skeleton className="h-20" />
            )}
          </CardPanel>
        </Card>
      </div>

      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle className="text-base">Highest-risk alerts</CardTitle>
          <Button size="sm" variant="ghost" render={<Link to="/alerts" />}>
            All alerts
            <ArrowRightIcon />
          </Button>
        </CardHeader>
        <CardPanel>
          {top.length === 0 ? (
            <p className="text-muted-foreground text-sm">No open alerts.</p>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Risk</TableHead>
                  <TableHead>Type</TableHead>
                  <TableHead>Entity</TableHead>
                  <TableHead>Customer</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {top.map((a) => (
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

function Stat({ label, value, tone = '' }: { label: string; value: number | undefined; tone?: string }) {
  return (
    <Card>
      <CardPanel className="py-4">
        <div className="text-muted-foreground text-xs">{label}</div>
        {value === undefined ? (
          <Skeleton className="mt-1 h-8 w-16" />
        ) : (
          <div className={`font-heading font-semibold text-3xl tabular-nums ${tone}`}>
            {value.toLocaleString('en-IN')}
          </div>
        )}
      </CardPanel>
    </Card>
  )
}
