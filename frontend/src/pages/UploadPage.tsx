import { CircleAlertIcon, DatabaseIcon, FileUpIcon } from 'lucide-react'
import { useState, type FormEvent } from 'react'
import PageHeader from '@/components/PageHeader'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import { Card, CardDescription, CardHeader, CardPanel, CardTitle } from '@/components/ui/card'
import { Empty, EmptyDescription, EmptyHeader, EmptyTitle } from '@/components/ui/empty'
import { Field, FieldDescription, FieldLabel } from '@/components/ui/field'
import { Input } from '@/components/ui/input'
import { Select, SelectItem, SelectPopup, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Spinner } from '@/components/ui/spinner'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { Tabs, TabsList, TabsPanel, TabsTab } from '@/components/ui/tabs'
import { toastManager } from '@/components/ui/toast'
import {
  ApiError,
  getRejected,
  ingestFile,
  loadSampleData,
  SOURCE_TYPES,
  type IngestionBatch,
  type RejectedRecord,
  type SourceType,
} from '@/lib/api'
import { ROLE_LABELS, useRole } from '@/lib/role'

const MAX_UPLOAD_MB = 50
const ACCEPTED = ['.csv', '.xlsx', '.json']
const SOURCE_ITEMS = SOURCE_TYPES.map((s) => ({ value: s.value, label: s.label }))

export default function UploadPage() {
  const role = useRole()
  const [sourceType, setSourceType] = useState<SourceType>('transactions')
  const [file, setFile] = useState<File | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [batch, setBatch] = useState<(IngestionBatch & { file_name: string }) | null>(null)
  const [sample, setSample] = useState<IngestionBatch[] | null>(null)
  const [loadingSample, setLoadingSample] = useState(false)

  const loadSample = async () => {
    setLoadingSample(true)
    setError(null)
    try {
      const { batches } = await loadSampleData()
      setSample(batches)
      const accepted = batches.reduce((n, b) => n + b.accepted_count, 0)
      const rejected = batches.reduce((n, b) => n + b.rejected_count, 0)
      toastManager.add({
        type: 'success',
        title: 'Sample data loaded',
        description: `${accepted.toLocaleString('en-IN')} records accepted across ${batches.length} sources${
          rejected ? `, ${rejected} rejected (already loaded)` : ''
        }`,
      })
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not load sample data')
    } finally {
      setLoadingSample(false)
    }
  }
  const [rejected, setRejected] = useState<RejectedRecord[]>([])

  const fileProblem = (f: File): string | null => {
    if (!ACCEPTED.some((ext) => f.name.toLowerCase().endsWith(ext))) {
      return `Unsupported file type. Use ${ACCEPTED.join(', ')}.`
    }
    if (f.size > MAX_UPLOAD_MB * 1024 * 1024) return `File is larger than ${MAX_UPLOAD_MB} MB.`
    return null
  }

  const submit = async (e: FormEvent) => {
    e.preventDefault()
    if (!file) return
    const problem = fileProblem(file)
    if (problem) {
      setError(problem)
      return
    }
    setBusy(true)
    setError(null)
    setBatch(null)
    setRejected([])
    try {
      const result = await ingestFile(file, sourceType)
      setBatch({ ...result, file_name: file.name })
      if (result.rejected_count > 0) setRejected(await getRejected(result.batch_id))
      toastManager.add({
        type: result.rejected_count > 0 ? 'warning' : 'success',
        title: 'File validated',
        description: `${result.accepted_count} accepted, ${result.rejected_count} rejected`,
      })
    } catch (err) {
      const message =
        err instanceof ApiError && err.status === 403
          ? `The ${ROLE_LABELS[role]} role cannot upload files. ${err.message}`
          : err instanceof Error
            ? err.message
            : 'Upload failed'
      setError(message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <section className="space-y-5">
      <PageHeader
        title="Data Upload"
        description="Load records from lending, insurance and core banking systems."
        action={
          <Button variant="outline" onClick={() => void loadSample()} disabled={loadingSample}>
            {loadingSample ? <Spinner /> : <DatabaseIcon />}
            Load sample data
          </Button>
        }
      />

      <Card>
        <CardPanel>
          <form onSubmit={submit} className="grid items-start gap-4 sm:grid-cols-[14rem_minmax(0,1fr)_auto]">
            <Field>
              <FieldLabel>Source</FieldLabel>
              <Select
                items={SOURCE_ITEMS}
                value={sourceType}
                onValueChange={(value) => value && setSourceType(value as SourceType)}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectPopup>
                  {SOURCE_ITEMS.map((item) => (
                    <SelectItem key={item.value} value={item.value}>
                      {item.label}
                    </SelectItem>
                  ))}
                </SelectPopup>
              </Select>
            </Field>
            <Field>
              <FieldLabel>File</FieldLabel>
              <Input
                className="w-full"
                type="file"
                accept={ACCEPTED.join(',')}
                onChange={(e) => {
                  setFile((e.target as HTMLInputElement).files?.[0] ?? null)
                  setError(null)
                }}
              />
              <FieldDescription>CSV, XLSX or JSON, up to {MAX_UPLOAD_MB} MB</FieldDescription>
            </Field>
            <Button type="submit" disabled={!file || busy} className="sm:mt-6">
              {busy ? <Spinner /> : <FileUpIcon />}
              {busy ? 'Validating…' : 'Validate'}
            </Button>
          </form>
        </CardPanel>
      </Card>

      <div aria-live="polite">
        {error && (
          <Alert variant="error">
            <CircleAlertIcon />
            <AlertTitle>Upload failed</AlertTitle>
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}
      </div>

      {sample && (
        <Card>
          <CardHeader>
            <CardTitle>Sample data</CardTitle>
            <CardDescription>
              Synthetic records with planted fraud scenarios and lookalikes. Run detection from Alerts next.
            </CardDescription>
          </CardHeader>
          <CardPanel>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Source</TableHead>
                  <TableHead className="text-right">Accepted</TableHead>
                  <TableHead className="text-right">Rejected</TableHead>
                  <TableHead className="text-right">Warnings</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {sample.map((b) => (
                  <TableRow key={b.batch_id}>
                    <TableCell>{SOURCE_TYPES.find((s) => s.value === b.source_type)?.label ?? b.source_type}</TableCell>
                    <TableCell className="text-right tabular-nums">
                      {b.accepted_count.toLocaleString('en-IN')}
                    </TableCell>
                    <TableCell className="text-right tabular-nums">{b.rejected_count}</TableCell>
                    <TableCell className="text-right tabular-nums">{b.warning_count}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardPanel>
        </Card>
      )}

      {batch && (
        <Card>
          <CardHeader>
            <CardTitle>Validation report</CardTitle>
            <CardDescription>
              {batch.file_name} · {SOURCE_TYPES.find((s) => s.value === batch.source_type)?.label ?? batch.source_type}{' '}
              · batch <span className="font-mono text-xs">{batch.batch_id}</span>
            </CardDescription>
          </CardHeader>
          <CardPanel>
            <Tabs defaultValue="report">
              <TabsList>
                <TabsTab value="report">Report</TabsTab>
                <TabsTab value="rejected">Rejected records ({batch.rejected_count})</TabsTab>
              </TabsList>
              <TabsPanel value="report" className="pt-4">
                <div className="grid grid-cols-3 gap-3 sm:max-w-xl">
                  <Stat label="Accepted" value={batch.accepted_count} tone="text-success-foreground" />
                  <Stat label="Rejected" value={batch.rejected_count} tone="text-destructive-foreground" />
                  <Stat label="Warnings" value={batch.warning_count} tone="text-warning-foreground" />
                </div>
              </TabsPanel>
              <TabsPanel value="rejected" className="pt-4">
                <RejectedTable records={rejected} />
              </TabsPanel>
            </Tabs>
          </CardPanel>
        </Card>
      )}
    </section>
  )
}

function Stat({ label, value, tone }: { label: string; value: number; tone: string }) {
  return (
    <div className="rounded-lg border px-3 py-2">
      <div className="text-muted-foreground text-xs">{label}</div>
      <div className={`font-heading font-semibold text-2xl tabular-nums ${tone}`}>{value.toLocaleString('en-IN')}</div>
    </div>
  )
}

function RejectedTable({ records }: { records: RejectedRecord[] }) {
  if (records.length === 0) {
    return (
      <Empty>
        <EmptyHeader>
          <EmptyTitle>No rejected records</EmptyTitle>
          <EmptyDescription>Every row in this batch passed validation.</EmptyDescription>
        </EmptyHeader>
      </Empty>
    )
  }
  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>Row</TableHead>
          <TableHead>Field</TableHead>
          <TableHead>Value</TableHead>
          <TableHead>Reason</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {records.map((r) => {
          const value = r.raw_values?.[r.field]
          return (
            <TableRow key={r.rejected_id}>
              <TableCell className="tabular-nums">{r.row_number}</TableCell>
              <TableCell className="font-mono text-xs">{r.field}</TableCell>
              <TableCell className="font-mono text-xs">
                {value === undefined || value === null || value === '' ? '(empty)' : String(value)}
              </TableCell>
              <TableCell className="whitespace-normal">{r.reason}</TableCell>
            </TableRow>
          )
        })}
      </TableBody>
    </Table>
  )
}
