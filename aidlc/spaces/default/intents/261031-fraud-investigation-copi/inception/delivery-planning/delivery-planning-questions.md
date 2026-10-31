# Delivery Planning — Questions

Inputs: `inception/units-generation/unit-of-work.md`, `inception/units-generation/unit-of-work-dependency.md`, `inception/contract-design/contract-summary.md`, `inception/practices-discovery/team-practices.md`.

The person asked not to be asked and to proceed on the information given ("continue assume mini req to finish the task and lets start"). The delivery lead chose these answers from the approved upstream artifacts.

## Q1. Bolt granularity — one Bolt per Unit, or bundle?

A. One Bolt per Unit (5 Bolts total). Each Unit is already sized for one focused build session; bundling would mix too many concerns in one merge.

[Answer]: A (delivery lead's choice)

## Q2. Sequencing heuristic?

A. Risk-first + dependency order. Bolt 1 (platform) de-risks the shared foundation; Bolt 2 (detection) de-risks the core product value and the most complex logic; Bolt 3 (AI) de-risks the AI spend and citation guards; Bolts 4 and 5 can be picked up independently once Bolt 3 is merged.

[Answer]: A (delivery lead's choice)

## Q3. Team size and mob strategy?

A. Solo or pair construction. No separate mobs — each Bolt is assigned to the team as a whole. Given the hackathon context, the team builds one Bolt at a time in the dependency order.

[Answer]: A (delivery lead's choice)

## Q4. Parallel construction (B4 and B5)?

A. Offered as parallel, but the team chooses at construction time based on how many people are available. Both Bolts depend on Bolt 3 and have no edge between them.

[Answer]: A (delivery lead's choice)
