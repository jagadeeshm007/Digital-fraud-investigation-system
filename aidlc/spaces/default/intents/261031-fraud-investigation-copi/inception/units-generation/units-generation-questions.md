# Units Generation — Questions and Plan

Inputs: `inception/domain-design/components.md`, `inception/domain-design/decisions.md`, `inception/requirements-analysis/requirements.md`, `inception/user-stories/stories.md`.

The person asked not to be asked and to proceed on the information given ("don't ask, assume with what you have", then "go"). The architect chose these answers from the approved upstream artifacts. The person approves the result at this stage's gate.

## Q1. [Architect] Unit boundary strategy?

A. By capability slice, grouping the 13 components into 5 units: platform foundation, detection and cases, AI review, web console, MCP gateway
X. Other (please specify)

[Answer]: A (architect's choice)

## Q2. [Architect] Granularity?

A. Coarse: 5 units, so each fits one focused build session inside the 3-hour milestone
X. Other (please specify)

[Answer]: A (architect's choice)

## Q3. [Architect] Dependency ordering?

A. Strict dependencies where code is shared; units with no edge between them may be built in parallel
X. Other (please specify)

[Answer]: A (architect's choice)

## Q4. [Architect] Integration between units?

A. In-process calls between backend units; an HTTP JSON API between the web console and the backend; an MCP protocol between AI assistants and the MCP gateway; one AlertRaised in-process event for AI review
X. Other (please specify)

[Answer]: A (architect's choice)

## Q5. [Release engineer] Deployment model?

A. One deployable container (a modular monolith) running the backend units and serving the built web console, deployed from one Dockerfile (team practices)
X. Other (please specify)

[Answer]: A (architect's choice)

## Plan

- **Units:** 5.
  - `u1-platform` (service)
  - `u2-detection-cases` (service)
  - `u3-ai-review` (service)
  - `u4-web-console` (ui)
  - `u5-mcp-gateway` (service)
- **Shape:** an acyclic graph. Plan approval is folded into this stage's gate, at the person's request.
