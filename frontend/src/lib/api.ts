import { getRole, getUser } from './role'

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

/** fetch wrapper: injects the active role and user as X-Role / X-User and turns `{ error, detail }` bodies into ApiError. */
export async function apiFetch<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers)
  headers.set('X-Role', getRole())
  headers.set('X-User', getUser())
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
  | 'phone'
  | 'policy'

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

// Case network (GET /api/graph/case/{id}): alerts and the identifiers in their evidence.
// Every edge names the matching identifier and the records it was read from; none come from the AI.
export interface CaseGraphEdge extends GraphEdge {
  match: { type: string; value: string }
  evidence: string[]
  shared: boolean
  origin: 'identifier'
}

export interface CaseGraphData {
  case_id: string
  nodes: GraphNode[]
  edges: CaseGraphEdge[]
}

export function getCaseGraph(caseId: string): Promise<CaseGraphData> {
  return apiFetch<CaseGraphData>(`/graph/case/${encodeURIComponent(caseId)}`)
}

export interface EntityLinks {
  entity_id: string
  link_count: number
  links: {
    shared_type: string
    shared_value: string
    linked_entities: { id: string; entity_type: string; customer_id: string | null }[]
  }[]
}

export function getLinks(entityId: string): Promise<EntityLinks> {
  return apiFetch<EntityLinks>(`/links/${encodeURIComponent(entityId)}`)
}

// Cases (app/api/detection.py, app/api/cases.py). A case is an investigation over many alerts.
export type CaseDecision =
  | 'requires_investigation'
  | 'false_positive'
  | 'escalate'
  | 'request_info'
  | 'recommend_hold'
  | 'recommend_verification'
  | 'conclude'

export interface Case {
  case_id: string
  alert_id: string
  customer_id: string | null
  fraud_category: string
  risk_level: RiskBand
  risk_original: RiskBand | null
  risk_reason: string | null
  risk_changed_by: string | null
  status: string
  priority_score: number
  needs_review: boolean
  conclusion: string | null
  split_from: string | null
  alert_count?: number
  created_at: string
  updated_at: string
}

export interface CaseHistory {
  history_id: string
  changed_at: string
  changed_by: string
  user_id: string | null
  from_status: string | null
  to_status: string
  decision: string | null
  reason: string | null
}

export interface CaseLink {
  with_alert: string
  with_rule: string
  type: string
  value: string
}

export interface CaseAlert extends Alert {
  link_reason: string
  links: CaseLink[]
  linked_at: string
}

export interface EvidenceRecord {
  id: string
  type: string
  record: Record<string, unknown>
  alert_ids: string[]
}

export interface TimelineItem {
  at: string | null
  kind: 'evidence' | 'alert'
  type: string
  id: string
  summary: string
  alert_ids: string[]
}

export interface CaseNote {
  note_id: string
  author_user: string
  author_role: string
  body: string
  created_at: string
}

export interface Recommendation {
  recommendation_id: string
  case_id: string
  kind: 'hold' | 'verification'
  reason: string
  status: 'pending' | 'approved' | 'rejected'
  maker_user: string
  maker_role: string
  created_at: string
  decided_by: string | null
  decided_at: string | null
  decision_reason: string | null
  effect: string
}

export interface PriorityParts {
  severity?: number
  exposure?: number
  related_events?: number
  confidence?: number
  exposure_inr?: string
  alert_count?: number
  evidence_count?: number
  factor_count?: number
  review_reasons?: string[]
}

export interface CaseWorkspace extends Case {
  customer: Record<PiiField, string> | null
  alerts: CaseAlert[]
  evidence: EvidenceRecord[]
  timeline: TimelineItem[]
  entities: { type: string; values: { value: string; alert_ids: string[] }[] }[]
  indicators: (AlertFactor & { rule_id: string; alert_id: string })[]
  risk: {
    risk_level: RiskBand
    risk_original: RiskBand | null
    risk_reason: string | null
    risk_changed_by: string | null
    priority_score: number
    needs_review: boolean
    priority_parts: PriorityParts
  }
  notes: CaseNote[]
  recommendations: Recommendation[]
  history: CaseHistory[]
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

export function getCase(caseId: string): Promise<CaseWorkspace> {
  return apiFetch(`/cases/${encodeURIComponent(caseId)}`)
}

function send<T>(path: string, method: string, body: unknown): Promise<T> {
  return apiFetch<T>(path, { method, headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) })
}

export function splitCase(caseId: string, alertId: string, reason: string): Promise<{ new_case: Case }> {
  return send(`/cases/${encodeURIComponent(caseId)}/split`, 'POST', { alert_id: alertId, reason })
}

export function addNote(caseId: string, body: string): Promise<CaseNote> {
  return send(`/cases/${encodeURIComponent(caseId)}/notes`, 'POST', { body })
}

export function overrideRisk(caseId: string, riskLevel: RiskBand, reason: string): Promise<Case> {
  return send(`/cases/${encodeURIComponent(caseId)}/risk`, 'PATCH', { risk_level: riskLevel, reason })
}

export function decideRecommendation(id: string, approve: boolean, reason: string): Promise<Recommendation> {
  return send(`/recommendations/${encodeURIComponent(id)}/decision`, 'POST', { approve, reason })
}

export function openCaseFromAlert(alertId: string, reason: string): Promise<Case> {
  return send(`/alerts/${encodeURIComponent(alertId)}/case`, 'POST', { reason })
}

/** Fetches the structured JSON report and saves it as a file (the request carries the role headers). */
export async function downloadCaseReport(caseId: string): Promise<void> {
  const report = await apiFetch<unknown>(`/cases/${encodeURIComponent(caseId)}/report`)
  const url = URL.createObjectURL(new Blob([JSON.stringify(report, null, 2)], { type: 'application/json' }))
  const a = document.createElement('a')
  a.href = url
  a.download = `case-${caseId.slice(0, 8)}-report.json`
  a.click()
  URL.revokeObjectURL(url)
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
  return send<Case>(`/cases/${encodeURIComponent(caseId)}/decision`, 'PATCH', { decision, reason })
}

export interface DetectionSummary {
  total_alerts: number
  open_alerts: number
  cleared_alerts: number
  risk_distribution: Record<RiskBand, number>
  fraud_categories: Record<string, number>
  case_statuses: Record<string, number>
  open_cases: number
  needs_review_cases?: number
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
  note: (role: string) => role !== 'analyst',
  approve: (role: string) => role === 'supervisor',
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
