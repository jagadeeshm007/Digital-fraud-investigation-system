# Feasibility & Constraints — Questions

Input: `aidlc/spaces/default/intents/261031-fraud-investigation-copi/ideation/intent-capture/intent-statement.md`

## Q1. [Architect] What existing systems must this integrate with?

Context: the intent says Azentio wants a solution that plugs into its existing products, and the organiser provides schemas, sample data and possibly sandbox APIs.

A. For this version, data arrives by upload or selection of CSV, Excel and JSON files in the organiser's formats. Integration points are adapters named after Azentio's products (alerts source, core banking source, digital channel events, case write-back) that read local data now and can be swapped for real APIs by configuration. Organiser sandbox APIs are used if they are provided.
B. Live integration with real Azentio or core-banking APIs is required now
C. No integration at all; a standalone app
D. Not yet defined
X. Other (please specify)

[Answer]: A

## Q2. [Compliance] Are there regulatory or compliance requirements?

A. Challenge rules apply: synthetic or properly anonymised data only, no real customer PII, no production credentials, no real payments. The prototype is not certified for regulatory compliance, but it follows Indian banking practice (RBI, FIU-IND) where it can. PII is masked before any AI call or MCP response.
B. It must meet a named standard now (for example PCI DSS or India's DPDP Act)
C. None
D. Not identified
X. Other (please specify)

[Answer]: A

## Q3. [Developer] What tech stack and skills does the team bring?

Context: this records the stack you chose earlier in our conversation, so later stages can rely on it.

A. Python and FastAPI for the backend, Postgres on Supabase, a Vite+ / React / TypeScript / coss ui frontend with React Flow for the link graph, LangGraph for the AI agent, and paid model APIs. The team is strong in Python, LangGraph, RAG, guardrails and data masking.
B. A different stack (please specify)
C. Stack still open
D. Not yet defined
X. Other (please specify)

[Answer]: A

## Q4. [Product owner] What is the AI spending limit?

Context: you first set a $10 total cap on AI spend, then said the team will provide paid models with a limit. This records the actual number.

A. $10 total for the hackathon, enforced as a credit limit on the API key
B. $25 total
C. $50 total
D. Not yet defined
X. Other (please specify)

[Answer]: A

## Q5. [Product owner] What is the timeline?

A. Hackathon day 2026-10-31: the build window runs 11:00 to 18:00. Level 1 takes about 3 hours, later levels unlock after each one is cleared, and submission closes at 18:00.
B. A longer timeline beyond the hackathon day
C. Level 1 only, no later levels
D. Not yet defined
X. Other (please specify)

[Answer]: A

## Q6. [Product owner] Are there organisational blockers?

A. The organiser checks rules on pre-written code at check-in, which may limit what can be in the repository before the build clock starts
B. None
C. Competing priorities or team availability limits
D. Not identified
X. Other (please specify)

[Answer]: A

## Q7. [Operations] Where will it run?

Context: the stage normally asks about AWS accounts; this project may not use AWS.

A. No AWS. One application container started with `docker compose up` on a laptop, with Postgres hosted on Supabase. Optionally a free hosting service for a shareable demo link.
B. AWS (please specify which services and accounts)
C. Another cloud provider (please specify)
D. Not yet defined
X. Other (please specify)

[Answer]: X. Other. Exact words: "need to deply it and need to provied deployed url for jury". Corrected: The application must be deployed, and a deployed URL must be provided to the jury.

## Q8. [Operations] Where should the deployed URL for the jury be hosted?

Context: you need a deployed URL for the jury (Q7). Postgres is already on Supabase, so this is about where the one application container runs.

A. A managed container host with a free or low-cost tier (for example Render, Railway or Fly.io), deployed from the same Dockerfile used locally, with HTTPS on a public URL
B. A virtual machine you control (for example a cloud VM) running `docker compose up` behind HTTPS
C. Split hosting: the frontend on a static host (for example Vercel) and the backend on a container host
D. Not yet defined
X. Other (please specify)

[Answer]: A

## Consolidated Summary Confirmation

- Integration: data arrives by upload or selection of CSV, Excel and JSON in the organiser's formats; adapters named after Azentio's products (alerts, core banking, channel events, case write-back) read local data now and swap to real APIs by configuration; organiser sandbox APIs are used if provided (Q1).
- Compliance: challenge rules apply (synthetic or anonymised data only, no real PII, credentials or payments); not certified, but follows RBI / FIU-IND practice where it can; PII masked before any AI call or MCP response (Q2).
- Stack and skills: Python / FastAPI, Supabase Postgres, Vite+ / React / TypeScript / coss ui with React Flow, LangGraph agent, paid model APIs; team strong in Python, LangGraph, RAG, guardrails and masking (Q3).
- AI budget: $10 total, enforced as a credit limit on the API key (Q4).
- Timeline: hackathon day 2026-10-31, build window 11:00 to 18:00, Level 1 in about 3 hours, later levels unlock in turn, submission closes 18:00 (Q5).
- Blocker: the organiser's rules on pre-written code at check-in may limit what is in the repository before the clock starts (Q6).
- Deployment: the application must be deployed with a public URL for the jury (Q7), on a managed container host's free or low-cost tier (for example Render, Railway or Fly.io) from the same Dockerfile used locally, with HTTPS (Q8).

Does this all look correct?

- Looks correct
- Request changes

[Answer]: Looks correct
