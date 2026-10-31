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

// Upload templates served by GET /api/demo/{name} (app/demo_data/*.csv); the logins file is named login_events.
const TEMPLATE_NAMES: Record<SourceType, string> = {
  customers_accounts: 'customers_accounts',
  transactions: 'transactions',
  devices_logins: 'login_events',
  loan_applications: 'loan_applications',
  insurance_claims: 'insurance_claims',
}

/** CSV with the expected columns and a few synthetic example rows (readable, since none of it is real PII). */
export function templateUrl(source: SourceType): string {
  return `/api/demo/${TEMPLATE_NAMES[source]}?masked=false`
}

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

export interface EvidenceRecord {
  id: string
  type: string
  record: Record<string, string | number | boolean | null>
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
  // only present on single-alert fetch (not list)
  case_id?: string | null
  evidence?: EvidenceRecord[]
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

// Cases (app/api/detection.py)
export type CaseDecision = 'requires_investigation' | 'false_positive' | 'escalate'

export interface Case {
  case_id: string
  alert_id: string
  customer_id: string | null
  fraud_category: string
  risk_level: RiskBand
  status: string
  created_at: string
  updated_at: string
}

export interface CaseHistory {
  history_id: string
  changed_at: string
  changed_by: string
  from_status: string | null
  to_status: string
  decision: string | null
  reason: string | null
}

export function getCases(params: Record<string, string | number | undefined>): Promise<Paged<Case>> {
  const qs = new URLSearchParams()
  for (const [k, v] of Object.entries(params)) if (v !== undefined && v !== '') qs.set(k, String(v))
  return apiFetch<Paged<Case>>(`/cases?${qs}`)
}

// Customer PII on a case, always masked by the server; a supervisor can reveal one field at a time.
export const PII_FIELDS = [
  { key: 'name', label: 'Name' },
  { key: 'phone', label: 'Phone' },
  { key: 'email', label: 'Email' },
  { key: 'address', label: 'Address' },
  { key: 'identity_number', label: 'Identity number' },
] as const
export type PiiField = (typeof PII_FIELDS)[number]['key']

export function getCase(
  caseId: string,
): Promise<Case & { customer: Record<PiiField, string> | null; history: CaseHistory[] }> {
  return apiFetch(`/cases/${encodeURIComponent(caseId)}`)
}

/** Supervisor only; the server audits every attempt, allowed or denied. */
export function revealPii(caseId: string, field: PiiField): Promise<{ plaintext_value: string }> {
  return apiFetch(`/masking/reveal`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ case_id: caseId, field }),
  })
}

export function recordDecision(caseId: string, decision: CaseDecision, reason: string): Promise<Case> {
  return apiFetch<Case>(`/cases/${encodeURIComponent(caseId)}/decision`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ decision, reason }),
  })
}

export interface DetectionSummary {
  total_alerts: number
  open_alerts: number
  cleared_alerts: number
  risk_distribution: Record<RiskBand, number>
  fraud_categories: Record<string, number>
  case_statuses: Record<string, number>
  open_cases: number
}

export function getSummary(): Promise<DetectionSummary> {
  return apiFetch<DetectionSummary>('/detection/summary')
}

// AI review (app/api/ai_review.py)
export interface AiReviewResult {
  alert_id: string
  base_score: number
  ai_adjustment: number
  final_score: number
  risk_band: RiskBand
  recommended_decision: string | null
  reasoning: string | null
  cited_evidence: string[] | null
  ai_available: boolean
  model_used?: string | null
  ai_status: string
}

export function reviewAlert(alertId: string): Promise<AiReviewResult> {
  return apiFetch<AiReviewResult>(`/ai/review/${encodeURIComponent(alertId)}`, { method: 'POST' })
}

export function reviewPending(limit = 20): Promise<{ reviewed: number; completed: number; unavailable: number }> {
  return apiFetch(`/ai/review/run?limit=${limit}`, { method: 'POST' })
}

export const can = {
  runDetection: (role: string) => role !== 'analyst',
  decide: (role: string) => role !== 'analyst',
  reveal: (role: string) => role === 'supervisor',
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

/** Bundled synthetic data for all five sources (app/sample_data.py), one batch per source. */
export function loadSampleData(): Promise<{ batches: IngestionBatch[] }> {
  return apiFetch('/ingest/sample', { method: 'POST' })
}

export async function getRejected(batchId: string): Promise<RejectedRecord[]> {
  const body = await apiFetch<{ batch_id: string; records: RejectedRecord[] }>(
    `/ingest/${encodeURIComponent(batchId)}/rejected`,
  )
  return body.records
}
