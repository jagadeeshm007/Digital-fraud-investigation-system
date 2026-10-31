import { RefreshCwIcon } from 'lucide-react'
import { useCallback, useEffect, useState } from 'react'
import PageHeader from '@/components/PageHeader'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardPanel } from '@/components/ui/card'
import { Empty, EmptyDescription, EmptyHeader, EmptyTitle } from '@/components/ui/empty'
import { Select, SelectItem, SelectPopup, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Skeleton } from '@/components/ui/skeleton'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { getAudit, type AuditPage as AuditPageData } from '@/lib/api'
import { useRole } from '@/lib/role'

const PAGE_SIZE = 20
const ALL = 'all'

export default function AuditPage() {
  const role = useRole()
  const [page, setPage] = useState(1)
  const [data, setData] = useState<AuditPageData | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [action, setAction] = useState(ALL)

  const load = useCallback(async () => {
    setError(null)
    try {
      setData(await getAudit(page, PAGE_SIZE))
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not load the audit trail')
    }
  }, [page])

  useEffect(() => {
    void load()
  }, [load, role])

  const actions = [ALL, ...new Set((data?.items ?? []).map((e) => e.action))]
  const actionItems = actions.map((a) => ({ value: a, label: a === ALL ? 'All actions' : a }))
  const rows = (data?.items ?? []).filter((e) => action === ALL || e.action === action)
  const pages = data ? Math.max(1, Math.ceil(data.total / PAGE_SIZE)) : 1

  return (
    <section className="space-y-5">
      <PageHeader
        title="Audit Trail"
        description="Every action, who did it, through which channel, and whether it was allowed."
        action={
          <Button variant="outline" onClick={() => void load()}>
            <RefreshCwIcon />
            Refresh
          </Button>
        }
      />

      {error && (
        <Alert variant="error">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      <Card>
        <CardPanel className="space-y-4">
          <Select items={actionItems} value={action} onValueChange={(v) => setAction(v ?? ALL)}>
            <SelectTrigger aria-label="Filter by action" className="w-56">
              <SelectValue />
            </SelectTrigger>
            <SelectPopup>
              {actionItems.map((item) => (
                <SelectItem key={item.value} value={item.value}>
                  {item.label}
                </SelectItem>
              ))}
            </SelectPopup>
          </Select>

          {!data && !error ? (
            <div className="space-y-2">
              {Array.from({ length: 5 }, (_, i) => (
                <Skeleton key={i} className="h-8 w-full" />
              ))}
            </div>
          ) : rows.length === 0 ? (
            <Empty>
              <EmptyHeader>
                <EmptyTitle>No audit entries yet</EmptyTitle>
                <EmptyDescription>Uploads, reveals and permission denials appear here.</EmptyDescription>
              </EmptyHeader>
            </Empty>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Time</TableHead>
                  <TableHead>Role</TableHead>
                  <TableHead>Channel</TableHead>
                  <TableHead>Action</TableHead>
                  <TableHead>Target</TableHead>
                  <TableHead>Result</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {rows.map((e) => (
                  <TableRow key={e.audit_id}>
                    <TableCell className="tabular-nums">
                      {new Date(e.timestamp).toLocaleString('en-IN', { dateStyle: 'medium', timeStyle: 'medium' })}
                    </TableCell>
                    <TableCell className="capitalize">{e.role}</TableCell>
                    <TableCell className="uppercase">{e.channel}</TableCell>
                    <TableCell className="font-mono text-xs">{e.action}</TableCell>
                    <TableCell className="max-w-48 truncate font-mono text-xs" title={e.target ?? undefined}>
                      {e.target ?? '-'}
                    </TableCell>
                    <TableCell>
                      <Badge variant={e.result === 'allowed' ? 'success' : 'error'}>{e.result}</Badge>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}

          {data && data.total > PAGE_SIZE && (
            <div className="flex items-center justify-between text-muted-foreground text-sm">
              <span>
                Page {page} of {pages} · {data.total} entries
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
