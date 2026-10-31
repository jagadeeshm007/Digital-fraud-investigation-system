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

export type RiskBand = 'High' | 'Medium' | 'Low'

export interface AlertFactor {
  factor: string
  points: number
  evidence_id?: string
}

export interface Alert {
  alert_id: string
  rule_id: string
  fraud_category: string
  entity_type: string
  entity_id: string
  customer_id: string | null
  product: string | null
  detected_at: string
  base_score: number
  ai_adjustment: number
  final_score: number
  risk_band: RiskBand
  factors: AlertFactor[]
  ai_recommendation: string | null
  ai_status: string
  status: string
  cleared_reason: string | null
}

export interface Paged<T> {
  items: T[]
  page: number
  page_size: number
  total: number
}

export function getAlerts(params: Record<string, string | number | undefined>): Promise<Paged<Alert>> {
  const qs = new URLSearchParams()
  for (const [k, v] of Object.entries(params)) if (v !== undefined && v !== '') qs.set(k, String(v))
  return apiFetch<Paged<Alert>>(`/alerts?${qs}`)
}

export function getAlert(alertId: string): Promise<Alert> {
  return apiFetch<Alert>(`/alerts/${encodeURIComponent(alertId)}`)
}

export function runDetection(): Promise<{
  new_alerts: number
  new_cases: number
  cleared_count: number
  total_hits: number
}> {
  return apiFetch('/detection/run', { method: 'POST' })
}

// Entity graph from app/api/graph.py (React Flow-ready nodes and edges, PII masked server-side).
export type GraphNodeType =
  | 'customer'
  | 'account'
  | 'transaction'
  | 'device'
  | 'login_event'
  | 'ip_address'
  | 'beneficiary_change'
  | 'loan_application'
  | 'insurance_claim'
  | 'alert'

export interface GraphNode {
  id: string
  type: GraphNodeType
  data: { label: string; [key: string]: unknown }
}

export interface GraphEdge {
  id: string
  source: string
  target: string
  label: string
}

export interface EntityGraphData {
  nodes: GraphNode[]
  edges: GraphEdge[]
}

export function getGraph(kind: 'alert' | 'entity', id: string, depth = 2): Promise<EntityGraphData> {
  return apiFetch<EntityGraphData>(`/graph/${kind}/${encodeURIComponent(id)}?depth=${depth}`)
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
