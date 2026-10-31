# Intent Statement: Digital Fraud Investigation System

## Problem Statement

Financial institutions check for fraud one system at a time. Suspicious activity in onboarding, lending, insurance and core banking is reviewed in silos, so coordinated fraud that only shows when those activities are connected goes unnoticed. [Q1]

Investigators spend most of their time gathering evidence instead of deciding on cases. [Q1]

The users feel four pains today: [Q3]

- most alerts turn out to be false positives [Q3]
- evidence sits in separate screens [Q3]
- links between customers, devices, applications and accounts are invisible to rules that look at one system [Q3]
- decisions are hard to explain to auditors later [Q3]

## Target Customer

| Who | Role | How they benefit | Source |
|-----|------|------------------|--------|
| Fraud analysts | First-line triage of alerts | Fewer false positives, alerts that explain themselves | [Q2] [Q3] |
| Fraud investigators | Second-line review of cases | Linked evidence in one place instead of separate screens | [Q2] [Q3] |
| Supervisor | Checks decisions | Decisions that can be explained to auditors | [Q2] [Q3] |
| Financial institution (customer) | Runs digital lending, insurance and core banking, for example a bank using Azentio's products | Coordinated fraud across products becomes visible | [Q2] |

## Success Metrics

This first version succeeds when: [Q4]

- The full Level 1 journey works end to end on the organiser's sample data and hidden tests: ingest and validate data, detect, assess risk, show the alert dashboard, and run the case queue. [Q4]
- All four required scenarios are detected on planted synthetic data: suspicious transfers, shared devices, repeated login failures and legitimate lookalikes. At least one extra scenario (suspicious loan applications or duplicate insurance claims) is detected too, and no legitimate lookalike is flagged. [Q4]
- Every alert shows the factors behind its risk level and its supporting records. Every case decision is kept in history without changing the original alert. [Q4]
- AI model spend stays low. The team provides paid AI models with a spending limit, so free-tier rate limits are not a constraint. [Q4] [Q12]
- The application shows AI logs and observability alongside the fraud journey. Every AI call and agent step is logged and shown in the app. [Q4] [Q10]
- PII protection and security masking are visible priorities: the application visibly shows that data is kept safe. [Q4]

## Initiative Trigger

The Azentio hackathon on 2026-10-31. Level 1 is built in about 3 hours and judged on observable behaviour, with later levels unlocking progressively. It also carries a forward-deployed-engineer story of fitting into Azentio's financial-crime products. [Q5]

## How AI Takes Part

- AI is a core part of the system and takes part in decisions, as the challenge asks for an AI-powered fraud investigation system. [Q11]
- Decisions are hybrid. Rules, statistics and the link graph produce the evidence signals and a base score. An AI agent reviews each flagged alert's masked evidence, assigns the fraud category, adjusts the risk within a bounded range, and recommends a decision with reasoning that cites the supporting records. [Q12]
- People make the final case decision. If the AI is unavailable, the rule-based result still stands. [Q12]
- Users can also work with the application directly from Claude or other frontier models through an MCP server. Reads are free; every write action needs the user's explicit consent before it runs. The web app's role checks and masking apply, and data reaches the model masked. [Q13]

## Initial Scope Signal

- Workflow-selected scope: `mvp`. [scope]
- User-confirmed product boundary: this first version leaves out the heavy platform pieces such as mTLS / zero-trust networking and Langfuse, and stays simple and deployment-ready. [Q9]
- Observability stays lightweight and inside the app, with no separate observability services. [Q10]

## Assumptions & Open Questions

None.
