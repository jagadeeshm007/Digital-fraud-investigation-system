# Contract Summary

Inputs: `inception/units-generation/unit-of-work.md` (5 units, build order), `inception/units-generation/unit-of-work-dependency.md` (DAG), `inception/domain-design/components.md` (13 components, interaction styles), `inception/requirements-analysis/requirements.md` (FR1–FR12).

All five units run inside one Python process (FastAPI monolith) and one built Vite+ static bundle. Backend units communicate by direct in-process Python calls; the web console communicates over HTTP/JSON; AI assistants communicate over the MCP protocol. There is one asynchronous coupling: the `AlertRaised` in-process event.

---

## Contract C1 — U1 Platform services consumed by U2, U3, U5

**Boundary:** in-process Python module calls  
**Provider:** u1-platform  
**Consumers:** u2-detection-cases, u3-ai-review, u5-mcp-gateway  
**Owner:** u1-platform (provider owns the interface)

### ActivityStore — read API

| Call | Arguments | Returns | Failure behaviour |
|---|---|---|---|
| `get_customer_history(customer_id)` | `customer_id: str` | `CustomerHistory` (amounts, payees, devices, dates) | raises `NotFound` if customer unknown |
| `get_transactions(filters)` | `AccountFilter | DateFilter | DeviceFilter` | `list[Transaction]` | empty list when no matches |
| `get_entity(entity_type, entity_id)` | `EntityType`, `str` | typed entity or `None` | `None` if not found; never raises |
| `list_customers_by_device(device_id)` | `device_id: str` | `list[Customer]` | empty list |
| `get_linked_entities(entity_id)` | `entity_id: str` | `list[EntityLink]` | empty list |

**Data shapes:** all money as `Decimal` (INR fixed-point); identifiers as opaque `str`; timestamps as `datetime` with timezone. No floats cross this boundary.

### AccessAudit — permission and audit API

| Call | Arguments | Returns | Failure behaviour |
|---|---|---|---|
| `check_permission(role, action)` | `Role`, `Action` | `None` | raises `PermissionDenied` — callers must not catch this |
| `audit(role, channel, action, target, result)` | all `str` | `AuditEntry` | raises `StorageError`; callers surface to user |

**Rule:** callers must call `check_permission` before acting and `audit` after. `check_permission` raises on denial; the caller does not catch it — the FastAPI exception handler returns 403.

### Masking — PII masking API

| Call | Arguments | Returns | Failure behaviour |
|---|---|---|---|
| `mask(value, field_type)` | `str`, `FieldType` | `str` (stable token) | returns `"[masked]"` on error; never raises |
| `mask_entity(entity)` | typed entity | copy with PII fields replaced | returns entity with all PII fields replaced; never raises |
| `reveal(case_id, field, role)` | `str`, `str`, `Role` | `str` (plaintext) | raises `PermissionDenied` if role is not Supervisor; raises `NotFound` if case unknown |

**Rule:** every in-process call that will later reach an AI model, MCP response, or UI response passes the result through `mask_entity` first. U3 and U5 must never forward an unmasked entity.

### Ingestion — ingest API (consumed by U4 via HTTP only)

Ingestion is not called in-process by U2, U3, or U5. Its contract is covered under C3 (HTTP API).

---

## Contract C2 — U2 → U1 (detection reads and access checks)

**Boundary:** in-process Python module calls  
**Provider:** u1-platform (ActivityStore, AccessAudit)  
**Consumer:** u2-detection-cases  
**Owner:** u1-platform

This is a subset of C1. The specific calls U2 makes:

- `ActivityStore.get_transactions(filters)` — for every detection rule that checks transfer amounts, sequences, or device sharing.
- `ActivityStore.get_customer_history(customer_id)` — for the suspicious-transfer rule (normal history for mitigation in RiskScoring) and for identity checks.
- `ActivityStore.list_customers_by_device(device_id)` — for the shared-device rule.
- `AccessAudit.check_permission(role, action=CHANGE_RULE_SETTING)` — before any rule-setting change.
- `AccessAudit.audit(...)` — after each detection run and after each rule-setting change.

**Failure contract:** detection rules that raise `StorageError` on an ActivityStore read abort the current detection run and surface the error to the caller of `Alerts.run_detection()`; partial results are not written.

---

## Contract C3 — Backend HTTP/JSON API consumed by U4 (WebConsole)

**Boundary:** HTTP/JSON over localhost (same container)  
**Provider:** u1-platform, u2-detection-cases, u3-ai-review (FastAPI routes)  
**Consumer:** u4-web-console (Vite+ React app)  
**Owner:** backend units (providers own the schema)

### Authentication

Every request carries `X-Role: analyst | investigator | supervisor`. The server resolves the role and refuses anything not permitted for that role with HTTP 403. There are no passwords or tokens in the demo — the role switcher in the UI sets the header.

### Encoding rules

- Money: `string` in the JSON (`"1234.56"`) — never `number`, because JSON `number` loses precision on large INR values.
- Identifiers: `string` (opaque).
- Timestamps: ISO-8601 with timezone (`"2026-10-31T09:15:00+05:30"`).
- PII fields (name, phone, email, address, identityNumber, accountNumber): always masked tokens in responses (`"***-a1b2c3"`). Supervisor reveal is a separate endpoint; it never appears in list or detail responses.

### Endpoints (summary)

| Group | Method | Path | Description |
|---|---|---|---|
| Ingest | `POST` | `/api/ingest` | Upload file (multipart) or select sample; returns `IngestionBatch` with counts |
| Ingest | `GET` | `/api/ingest/{batch_id}/rejected` | List rejected records |
| Detection | `POST` | `/api/detection/run` | Start a detection run; returns `DetectionRun` |
| Detection | `GET` | `/api/detection/settings` | List rule settings |
| Detection | `PATCH` | `/api/detection/settings/{key}` | Change one rule setting (Supervisor only) |
| Alerts | `GET` | `/api/alerts` | List alerts with optional filters (band, type, date) |
| Alerts | `GET` | `/api/alerts/{alert_id}` | Alert detail with factors, evidence IDs, related entities |
| Cases | `GET` | `/api/cases` | Case queue (open and recent) |
| Cases | `GET` | `/api/cases/{case_id}` | Case detail with decision history |
| Cases | `POST` | `/api/cases/{case_id}/decisions` | Record a decision (body: `{decision, reason}`) |
| AI | `GET` | `/api/ai/reviews/{alert_id}` | AI review result for an alert |
| AI | `GET` | `/api/ai/log` | AI call log |
| Dashboard | `GET` | `/api/dashboard` | All dashboard figures in one call |
| Audit | `GET` | `/api/audit` | Paginated audit trail |
| Masking | `POST` | `/api/masking/reveal` | Supervisor-only: reveal one PII field for a case |
| Links | `GET` | `/api/links/{entity_id}` | Related entities for the entity graph |

### Error shape

```json
{ "error": "<machine_code>", "detail": "<human readable>" }
```

HTTP status: 400 for validation failures, 403 for permission denied, 404 for not found, 422 for malformed request body, 500 for unexpected server errors. The UI never shows 5xx detail to the user — it shows "Something went wrong. Try again."

### Failure contract

- Detection run: if the run fails mid-way, the `DetectionRun` record is written with `status: failed` and `error: "<reason>"`. No partial alerts are written.
- Case decision duplicate: a second submission of the same decision on a case is silently accepted (idempotent) and returns 200 with the original `CaseDecision`.

---

## Contract C4 — AlertRaised in-process event (U2 → U3)

**Boundary:** in-process Python event (synchronous call on a registered handler)  
**Emitter:** u2-detection-cases (Alerts component)  
**Consumer:** u3-ai-review (AiReview component)  
**Owner:** u2-detection-cases (emitter owns the event schema)

### Event schema

```python
@dataclass
class AlertRaised:
    alert_id: str
    detection_type: str          # one of the 7 scenario codes
    base_score: int              # 0–100
    band: Literal["Low", "Medium", "High"]
    evidence_ids: list[str]      # IDs of records that contributed
    subject_ids: list[str]       # IDs of the subjects (customers, accounts)
```

### Dispatch rules

- Raised **once**, synchronously, by `Alerts.create_alert()` after the `Alert` row is written.
- The handler runs in the same process. If the handler raises, the exception is caught, logged, and **does not roll back the alert**. AiReview failure never blocks alert creation.
- `AiReview` reads the full alert evidence via `ActivityStore` after the event arrives — it does not receive the raw records in the event payload.
- All evidence passed to the AI model passes through `Masking.mask_entity()` first.

---

## Contract C5 — U5 MCP Gateway (consumed by AI assistants)

**Boundary:** MCP protocol (JSON-RPC over stdio or HTTP)  
**Provider:** u5-mcp-gateway (McpGateway component)  
**Consumers:** Claude and other frontier models  
**Owner:** u5-mcp-gateway

### MCP tools

| Tool | Kind | Description | Role required |
|---|---|---|---|
| `get_dashboard` | read | Returns dashboard figures (masked) | Analyst+ |
| `list_alerts` | read | Returns alert list with filters | Analyst+ |
| `get_alert` | read | Returns one alert with factors and masked evidence | Analyst+ |
| `get_case` | read | Returns case detail with decision history | Analyst+ |
| `get_ai_log` | read | Returns the AI call log | Analyst+ |
| `record_case_decision` | **write** | Records a case decision | Investigator+ |
| `run_detection` | **write** | Starts a detection run | Investigator+ |

### Consent gate for writes

Before executing any write tool, McpGateway presents the user with the exact action and arguments and waits for explicit approval. A declined or unanswered consent returns a `ConsentDenied` error to the model; nothing is written. The `ConsentRequest` record is written regardless of outcome.

### Response rules

- Every response masks PII using `Masking.mask_entity()` before the payload is serialised.
- Errors are returned as MCP tool errors with a `code` field: `permission_denied`, `not_found`, `consent_required`, `consent_denied`, `internal_error`.
- There is no reveal tool. Supervisor reveals are only possible through the web app.

---

## Contract Ownership Summary

| Contract | Provider | Consumer(s) | Interface |
|---|---|---|---|
| C1 ActivityStore read | u1-platform | u2, u3, u5 | Python module |
| C1 AccessAudit | u1-platform | u2, u3, u5 | Python module |
| C1 Masking | u1-platform | u3, u5 | Python module |
| C2 Detection reads | u1-platform | u2-detection-cases | Python module (subset of C1) |
| C3 HTTP API | Backend units | u4-web-console | HTTP/JSON (FastAPI) |
| C4 AlertRaised | u2-detection-cases | u3-ai-review | In-process event |
| C5 MCP tools | u5-mcp-gateway | AI assistants | MCP protocol |

## Assumptions & Open Questions

None.

## Sources

- [desc] Digital Fraud Investigation System — hackathon MVP
- [scope] mvp
- `inception/units-generation/unit-of-work.md`
- `inception/units-generation/unit-of-work-dependency.md`
- `inception/domain-design/components.md`
- `inception/requirements-analysis/requirements.md`
