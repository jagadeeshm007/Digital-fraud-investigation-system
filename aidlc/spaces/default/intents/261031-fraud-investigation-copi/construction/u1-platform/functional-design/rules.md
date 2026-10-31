# Business Rules — u1-platform

Unit: u1-platform. Components: ActivityStore, AccessAudit, Masking, Ingestion.

---

## Money rules

- `BR-MON-1` All monetary amounts are stored as `Decimal(14,2)` — fixed-point INR, never floating-point.
- `BR-MON-2` Amounts are serialised as JSON strings (`"1234.56"`) over the HTTP API. Deserialisation rejects any value that is not parseable as a decimal.
- `BR-MON-3` Negative amounts are rejected at ingestion with reason `"Amount must be non-negative"`.

## Identifier rules

- `BR-ID-1` All identifiers are stored as opaque strings exactly as received. Leading zeros, hyphens, and spaces are preserved.
- `BR-ID-2` Identifiers are not normalised, trimmed, or case-folded during ingestion. Comparison is always case-sensitive and byte-exact.

## Timestamp rules

- `BR-TS-1` Timestamps are stored with time-zone information. A naive timestamp without a zone is rejected at ingestion with reason `"Timestamp must include a timezone"`.
- `BR-TS-2` Timestamps are serialised as ISO 8601 with offset (`"2026-10-31T09:15:00+05:30"`) in API responses.

## Ingestion rules

- `BR-ING-1` Files larger than 50 MB are rejected before parsing with reason `"File too large (limit 50 MB)"`.
- `BR-ING-2` A file that cannot be parsed as CSV, Excel, or JSON returns `"Could not read this file as CSV, Excel or JSON"` and nothing is stored.
- `BR-ING-3` Column mapping is applied before validation. If a required source column is absent from the file, all records in the file are rejected with reason `"Required column <name> is missing"`.
- `BR-ING-4` A record is rejected if any mandatory field (per `SourceMapping.mandatory_fields`) is absent or empty after mapping. The rejection names the first failing field.
- `BR-ING-5` A record that fails a type or format check is rejected. Rejection names the field and the expected format (e.g. `"amount: expected decimal, got 'abc'"`).
- `BR-ING-6` An allowed-values check failure (e.g. `channel` not in the allowed enum) is a rejection, not a warning.
- `BR-ING-7` The first record with a given primary key is accepted. Subsequent records with the same key are rejected with reason `"Duplicate key <id>"`.
- `BR-ING-8` A record that references an unknown identifier (e.g. a transaction whose `sender_account_id` is not in the loaded accounts) produces a warning, not a rejection. The record is still stored.
- `BR-ING-9` Every rejected record is stored in `RejectedRecord` with its full `raw_values`. Nothing is silently dropped.
- `BR-ING-10` An empty file (zero data rows after the header) is accepted as a batch with `accepted_count = 0`, `rejected_count = 0`. It is not an error.
- `BR-ING-11` CSV files are parsed with `quoting=QUOTE_ALL` semantics: commas and quotes inside quoted fields are handled correctly. A byte-order mark at the start is stripped.

## Permission rules

- `BR-PERM-1` The server resolves the active role from the `X-Role` header. An absent or unrecognised role is treated as `analyst`.
- `BR-PERM-2` Role-to-action matrix:

  | Action | Analyst | Investigator | Supervisor |
  |---|---|---|---|
  | Upload file | ✓ | ✓ | ✓ |
  | Run detection | ✗ | ✓ | ✓ |
  | View alerts | ✓ | ✓ | ✓ |
  | View cases | ✓ | ✓ | ✓ |
  | Record case decision (all) | ✗ | ✓ | ✓ |
  | Escalate case | ✗ | ✓ | ✓ |
  | Change rule setting | ✗ | ✗ | ✓ |
  | Reveal PII field | ✗ | ✗ | ✓ |
  | View audit trail | ✓ | ✓ | ✓ |
  | View AI log | ✓ | ✓ | ✓ |

- `BR-PERM-3` `check_permission` raises `PermissionDenied` synchronously. Callers must not catch it. The FastAPI exception handler maps it to HTTP 403.
- `BR-PERM-4` Every permitted action is followed by an `audit` call with `result = allowed`. A denied action is audited with `result = denied` by the exception handler before returning 403.
- `BR-PERM-5` Audit entries never contain unmasked PII. The `target` field holds only IDs, never names or account numbers.

## PII masking rules

- `BR-MASK-1` PII fields are: `name`, `phone`, `email`, `address`, `identity_number`, `ip_address`, `location`, `beneficiary_name`, `account_id` (when shown in a display context).
- `BR-MASK-2` Masking is applied to every entity before it leaves the server — on API responses, AI call payloads, and MCP responses. Raw entities never reach the transport layer unmasked.
- `BR-MASK-3` The mask token is a stable, deterministic HMAC-SHA256 prefix (`***-<6-char-hex>`) keyed on a session secret. The same input value always produces the same token within a process lifetime, so related records can be correlated without exposing plaintext.
- `BR-MASK-4` A Supervisor may reveal one PII field for a case through the app (`POST /api/masking/reveal`). This action is:
  - Not available through MCP or AI calls — ever.
  - Audited as `reveal_pii` with the field name in `target`.
  - Recorded as a `RevealEvent`.
  - Rate-limited to one reveal per field per case per supervisor session.
- `BR-MASK-5` If masking fails for any reason, the field is replaced with the literal `"[masked]"`. The failure is logged but does not abort the request.

## File-size and security rules

- `BR-SEC-1` File uploads are limited to 50 MB (enforced before parsing).
- `BR-SEC-2` XML parsing is not supported. Any file disguised as XML, or containing XML entity expansions, is rejected as an unrecognised format.
- `BR-SEC-3` Secrets (database URL, HMAC key, OpenRouter key) are read exclusively from environment variables. Accessing them from any other path raises a startup error.
- `BR-SEC-4` SQL queries use parameterised statements. String interpolation into queries is forbidden.

## Sources

- [desc] Digital Fraud Investigation System — hackathon MVP
- [scope] mvp
- `inception/requirements-analysis/requirements.md` (FR1, FR2, FR8, FR9, FR10)
- `inception/domain-design/components.md`
- `inception/contract-design/contract-summary.md` (C1 Masking, C1 AccessAudit, C3)

## Assumptions & Open Questions

None.
