# Unit Dependencies

Inputs: `inception/domain-design/components.md` (component dependencies), `inception/domain-design/decisions.md`, `inception/requirements-analysis/requirements.md`, `inception/user-stories/stories.md`, `unit-of-work.md`.

## Dependency DAG

- **u2-detection-cases depends on u1-platform:** detection reads ActivityStore, and cases audit through AccessAudit.
- **u3-ai-review depends on u1-platform and u2-detection-cases:** AI review masks evidence through Masking and consumes AlertRaised from Alerts.
- **u4-web-console depends on u1-platform, u2-detection-cases and u3-ai-review:** its end-to-end tests call their API.
- **u5-mcp-gateway depends on u1-platform, u2-detection-cases and u3-ai-review:** it calls Dashboard, Alerts, Cases, AiReview, Masking and AccessAudit.

```yaml
units:
  - name: u1-platform
    kind: service
    depends_on: []
  - name: u2-detection-cases
    kind: service
    depends_on: [u1-platform]
  - name: u3-ai-review
    kind: service
    depends_on: [u1-platform, u2-detection-cases]
  - name: u4-web-console
    kind: ui
    depends_on: [u1-platform, u2-detection-cases, u3-ai-review]
  - name: u5-mcp-gateway
    kind: service
    depends_on: [u1-platform, u2-detection-cases, u3-ai-review]
```

## Integration Points

| From | To | Mechanism |
|---|---|---|
| u2-detection-cases | u1-platform | In-process calls (ActivityStore reads, AccessAudit) |
| u3-ai-review | u2-detection-cases | In-process AlertRaised event and evidence reads |
| u3-ai-review | u1-platform | In-process Masking |
| u4-web-console | backend units | HTTP JSON API |
| u5-mcp-gateway | backend units | In-process calls; exposed to AI assistants over MCP |

## Parallel Development Opportunities

- u4-web-console and u5-mcp-gateway have no edge between them, so they can be built at the same time once u3-ai-review exists.

## Assumptions & Open Questions

None.
