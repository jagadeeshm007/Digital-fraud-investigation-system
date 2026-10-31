# Intent Capture & Framing — Questions

## Sources

- [desc] Initial description: "lets build requiments ,plan , scope, intent , units ,bolts, claude md, memory md etc .. all required files and desigines and eveyting into code base and git init thre porject"
- [scope] Workflow-selected scope: `mvp`.

## Q1. [Product owner] What business problem are we solving?

Context: the options below restate what you described earlier in our conversation, so you can confirm or correct them.

A. Fraud is caught system by system. Suspicious activity across onboarding, lending, insurance and core banking is checked in silos, so coordinated fraud is missed. Investigators spend most of their time gathering evidence instead of deciding (the hackathon's "Digital Fraud Investigation System" challenge)
B. Only transaction-level fraud detection based on amounts and thresholds
C. Only the time investigators spend writing case notes
D. Not yet defined
X. Other (please specify)

[Answer]: A

## Q2. [Product owner] Who are the primary users, and who is the customer?

A. Users: fraud analysts (first-line triage), fraud investigators (second-line review) and a supervisor who checks decisions. Customer: a financial institution running digital lending, insurance and core banking (e.g. a bank using Azentio's products)
B. Only fraud analysts
C. The bank's own end customers
D. Not yet defined
X. Other (please specify)

[Answer]: A

## Q3. [Product owner] What pain are those users experiencing today?

A. Most alerts are false positives. Evidence sits in separate screens. Links between customers, devices, applications and accounts are invisible to single-system rules. Decisions are hard to explain to auditors later.
B. Only too many false positives
C. Only slow evidence gathering
D. Not identified
X. Other (please specify)

[Answer]: A

## Q4. [Product owner] What does success look like for this first version? (select all that apply)

A. The full Level 1 journey works end to end on the organiser's sample data and hidden tests: ingest and validate data, detect, assess risk, show the alert dashboard, run the case queue
B. All four required scenarios (suspicious transfers, shared devices, repeated login failures, legitimate lookalikes) plus at least one extra (loan applications or duplicate claims) are detected on planted synthetic data, with no legitimate lookalike flagged
C. Every alert shows the factors behind its risk level and its supporting records, and every case decision is kept in history without changing the original alert
D. Total AI model spend for the hackathon stays under $10
E. Not yet defined
X. Other (please specify)

[Answer]: A, B, C, D, X. Other: We will mostly use free AI APIs, so the design must handle rate limits and optimise usage. Success means a working application that demonstrates data ingestion, fraud detection, risk assessment, an alert dashboard and a basic investigation queue, alongside AI logs and observability. PII protection and security masking are priorities, and the application should visibly show that data is kept safe.

## Q5. [Product owner] What triggered this initiative now?

A. The Azentio hackathon challenge on 2026-10-31: Level 1 is built in about 3 hours and judged on observable behaviour, with later levels unlocking progressively. It also tells a forward-deployed-engineer story of fitting into Azentio's financial-crime products.
B. A regulatory deadline
C. Internal technical debt
D. Not identified
X. Other (please specify)

[Answer]: A

## Q6. [Product owner] Who are the key stakeholders, and what does each care about? (select all that apply)

A. Hackathon organiser and judges: observable app behaviour, hidden tests, the evaluation rubric
B. Fraud analysts, investigators and supervisors (end users): fast, explainable alerts and a clear case queue
C. Azentio (the product company the challenge is for): a solution that plugs into their existing products rather than replacing them
D. You and your team (builders): a working demo and pitch within the time limits
E. Not identified
X. Other (please specify)

[Answer]: A, B, C

## Q7. [Product owner] Who decides scope and priority, and who influences those decisions?

A. You (Jagadeesh Mandala) decide scope and priority. The organiser's rubric, level briefs and briefing answers influence them.
B. The team decides jointly
C. The organiser decides
D. Not yet defined
X. Other (please specify)

[Answer]: B

## Q8. [Product owner] Are there communication requirements or a reporting cadence?

A. Milestone-based: a working demo at each level unlock, a backup demo video, submission on HackCulture before 18:00, and a 5-minute finalist demo if selected
B. None
C. Written status updates only
D. Not yet defined
X. Other (please specify)

[Answer]: A

## Q9. [Product owner] What should this first version NOT do? (select all that apply)

The workflow plan is already chosen; this is only about what the product leaves out for now.

A. The heavier platform pieces we deferred: separate services with mTLS / zero-trust networking, the MCP server, Grafana and OpenTelemetry dashboards, Langfuse, multi-agent fan-out, CI security scans
B. The AI investigation agent and draft suspicious-transaction report (planned for Level 2 onward)
C. Real integration with Azentio or core-banking systems, real customer data, production credentials, real payments
D. None
X. Other (please specify)

[Answer]: X. Other: Leave out the heavy platform pieces such as mTLS / zero-trust networking and Langfuse. Keep the product simple and deployment-ready.

## Q10. [Product owner] What form should "AI logs and observability" take in this first version?

Context: your success answer (Q4) asks for AI logs and observability, while your boundary answer (Q9) leaves out heavy pieces such as Langfuse. This settles which one wins.

A. Lightweight and built into the app: every AI call and agent step is logged (model, tokens, latency, cost, rate-limit retries, masked prompt), shown on an in-app page, plus structured application logs. No separate observability services.
B. Bring back Langfuse and Grafana dashboards despite the extra setup
C. Plain application log files only, no in-app view
D. Not yet defined
X. Other (please specify)

[Answer]: A

## Q11. [Product owner] What role does AI play in this first version?

Context: your boundary answer (Q9) did not leave out the AI investigation agent, and your success answer (Q4) mentions AI logs, so AI seems to be in.

A. Detection and risk scoring stay rule-based and statistical, so they are explainable and testable. AI (free-tier models first) adds a plain-language explanation or case summary on top of each alert or case, always working on masked data.
B. AI also decides risk scores and fraud categories
C. No AI in this first version
D. Not yet defined
X. Other (please specify)

[Answer]: X. Other: AI should be a core part of the system and take part in making decisions, as the challenge asks for an AI-powered Digital Fraud Investigation System (changed at the summary confirmation; first answer was A).

## Consolidated Summary Confirmation

- Problem: fraud is checked system by system across onboarding, lending, insurance and core banking, so coordinated fraud is missed and investigators spend most of their time gathering evidence (Q1).
- Users: first-line fraud analysts, second-line investigators and a supervisor; the customer is a financial institution running lending, insurance and core banking (Q2).
- Pain: mostly false-positive alerts, evidence in separate screens, cross-system links invisible to single rules, decisions hard to explain to auditors (Q3).
- Success: the Level 1 journey works end to end on organiser data and hidden tests; four required scenarios plus one extra are detected with no lookalike flagged; every alert explains its risk and keeps its evidence and decision history; AI spend stays under $10 using mostly free APIs with rate-limit handling; the app also shows AI logs and observability and visibly protects PII through masking (Q4).
- Trigger: the Azentio hackathon on 2026-10-31, judged on observable behaviour, with levels unlocking progressively (Q5).
- Stakeholders: organiser and judges; fraud analysts, investigators and supervisors; Azentio (Q6).
- Decisions: the team decides scope and priority jointly (Q7).
- Communication: milestone-based, with a demo at each level unlock, a backup video, HackCulture submission before 18:00 and a finalist demo if selected (Q8).
- Out of this first version: heavy platform pieces such as mTLS / zero-trust networking and Langfuse; keep it simple and deployment-ready (Q9).
- Observability: lightweight and in-app, logging every AI call and agent step, with no separate observability services (Q10).
- AI role: AI is a core part of the system and takes part in decisions (Q11).
- How decisions are shared: hybrid. Rules, statistics and the link graph give the evidence and a base score; an AI agent reviews masked evidence, sets the fraud category, adjusts the risk within a bound and recommends a decision that cites records; people make the final case decision; the rule-based result stands if AI is unavailable. The team will provide paid AI models with a spending limit (Q12).
- MCP server: users can work with the application directly from Claude or other frontier models; reads are free, every write needs the user's explicit consent first, the web app's role checks and masking apply, and data reaches the model masked (feedback, Q13).
- Influencers: the organiser and judges shape priorities through the rubric, level briefs, briefing answers and hidden tests (Q14); Azentio shapes design choices by wanting a fit with its existing products (Q15).

Does this all look correct before I generate the artifact?

- Looks correct
- Request changes

[Answer]: Looks correct

## Requested Changes Feedback

What should change?

[Answer]: AI should be a core part of the system and take part in making decisions, as the official challenge describes an AI-powered Digital Fraud Investigation System (the person pasted the challenge text with this request).

## Q12. [Product owner] How should AI share decisions with the rules and with people?

Context: you want AI to be core and take part in decisions (your change to Q11). The challenge also says each risk level must be explained by its contributing factors, judges score observable behaviour rather than standalone AI output, and you plan to run mostly on free, rate-limited AI APIs. This settles how those fit together.

A. Hybrid. Rules, statistics and the link graph produce the evidence signals and a base score. An AI agent then reviews each flagged alert's linked evidence (masked), assigns the fraud category, adjusts the risk within a bounded range, and recommends a decision, with reasoning that cites the supporting records. People make the final case decision. If the AI is unavailable or rate-limited, the rule-based result still stands.
B. AI alone decides the risk score, category and decision for every event
C. AI decides and acts on its own, including closing false positives without a person
D. Not yet defined
X. Other (please specify)

[Answer]: A. Hybrid. The person also said the team will provide paid AI models with a spending limit, so free-tier rate limits are not a concern.

## Requested Changes Feedback

What should change?

[Answer]: Also add an MCP server so users can interact with the application directly through Claude or other frontier models.

## Q13. [Product owner] What may Claude or another frontier model do through the MCP server?

Context: you asked for an MCP server so users can work with the application directly from Claude or other frontier models. Some actions only read (list alerts, open a case), others change things (record a case decision, upload data, change a rule threshold).

A. Read freely; every write action needs the user's explicit consent before it runs (the model proposes, the user confirms), and the same role checks and masking as the web app apply; data reaches the model masked
B. Read-only: no write actions through MCP
C. Read and write freely, with no extra consent step
D. Not yet defined
X. Other (please specify)

[Answer]: A

## Assumption Confirmation

The stakeholder map carries these unconfirmed items:

- [assumption] Whether the hackathon organiser and judges influence scope and priority decisions (for example through the rubric or level briefs) was not confirmed; only the team was confirmed as the decision-maker.
- [assumption] Whether Azentio influences scope and priority decisions was not confirmed.

A. Accept assumptions
B. Convert to follow-up questions

[Answer]: B. Convert to follow-up questions

## Q14. [Product owner] Do the hackathon organiser and judges influence scope and priority decisions?

Context: the team decides scope and priority (Q7); this asks whether the organiser and judges shape those decisions.

A. Yes: the evaluation rubric, level briefs, briefing answers and hidden tests shape what the team prioritises
B. No: they only judge the result
C. Not identified
X. Other (please specify)

[Answer]: A

## Q15. [Product owner] Does Azentio influence scope and priority decisions?

Context: Azentio is a stakeholder that wants a solution plugging into its existing products (Q6).

A. Yes: fitting Azentio's existing products (integrating, not replacing) shapes design choices
B. No: Azentio is only the challenge sponsor
C. Not identified
X. Other (please specify)

[Answer]: A
