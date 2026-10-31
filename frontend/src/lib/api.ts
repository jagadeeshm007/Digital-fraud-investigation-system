import { getRole } from './role'

// Contracts from construction/u1-platform/functional-design/functional-spec.md (Flows 1 and 2).
export const SOURCE_TYPES = [
  { value: 'customers_accounts', label: 'Customer & account profiles' },
  { value: 'transactions', label: 'Transactions' },
  { value: 'devices_logins', label: 'Devices & logins' },
  { value: 'loan_applications', label: 'Loan applications' },
  { value: 'insurance_claims', label: 'Insurance claims' },
] as const
export type SourceType = (typeof SOURCE_TYPES)[number]['value']

export interface IngestionBatch {
  batch_id: string
  source_type: SourceType
  accepted_count: number
  rejected_count: number
  warning_count: number
}

export interface RejectedRecord {
  rejected_id: string
  row_number: number
  field: string
  reason: string
  raw_values: Record<string, unknown>
}

export class ApiError extends Error {
  readonly status: number
  readonly code: string

  constructor(status: number, code: string, detail: string) {
    super(detail)
    this.status = status
    this.code = code
  }
}

/** fetch wrapper: injects the active role as X-Role and turns `{ error, detail }` bodies into ApiError. */
export async function apiFetch<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers)
  headers.set('X-Role', getRole())
  const res = await fetch(`/api${path}`, { ...init, headers })
  if (!res.ok) {
    const body = await res.json().catch(() => ({}))
    // FastAPI's HTTPException wraps the spec's { error, detail } inside "detail"; accept both shapes.
    const payload = body.detail && typeof body.detail === 'object' ? body.detail : body
    const detail = typeof payload.detail === 'string' ? payload.detail : res.statusText
    const code = payload.error ?? (res.status === 403 ? 'permission_denied' : `http_${res.status}`)
    throw new ApiError(res.status, code, detail || `Request failed (${res.status})`)
  }
  return res.json() as Promise<T>
}

export function ingestFile(file: File, sourceType: SourceType): Promise<IngestionBatch> {
  const form = new FormData()
  form.append('file', file)
  form.append('source_type', sourceType)
  return apiFetch<IngestionBatch>('/ingest', { method: 'POST', body: form })
}

export interface AuditEntry {
  audit_id: string
  timestamp: string
  role: string
  channel: string
  action: string
  target: string | null
  result: 'allowed' | 'denied'
}

export interface AuditPage {
  items: AuditEntry[]
  page: number
  page_size: number
  total: number
}

export function getAudit(page: number, pageSize: number): Promise<AuditPage> {
  return apiFetch<AuditPage>(`/audit?page=${page}&page_size=${pageSize}`)
}

export async function getRejected(batchId: string): Promise<RejectedRecord[]> {
  const body = await apiFetch<{ batch_id: string; records: RejectedRecord[] }>(
    `/ingest/${encodeURIComponent(batchId)}/rejected`,
  )
  return body.records
}
