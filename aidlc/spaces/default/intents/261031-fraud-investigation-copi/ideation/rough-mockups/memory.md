<!-- INVARIANT: examples are single-line HTML comments so a fresh template parses to total=0 (MEMORY_EMPTY). Do NOT un-comment or split across lines. t100 guards this. -->
> This file is kept up to date automatically while the stage runs. Add observations at the review step, not by editing here directly.

## Interpretations
<!-- example: 2026-05-29T10:14:32Z — chose REST over GraphQL; the consuming team only needs CRUD, revisit if subscriptions land -->
- 2026-10-31T06:40:00Z — Brand palette and fonts taken from the printed Azentio homepage PDF the person supplied (Poppins/Noto Sans; navy #16303D, mint #55FFBE, greens #2ED88E and #39AB7F), because the live site failed certificate verification.

## Deviations
<!-- example: 2026-05-29T10:14:32Z — skipped the optional caching layer the stage prose suggested; the dataset is small enough that it adds risk -->
- 2026-10-31T06:40:00Z — Did not bypass TLS verification to fetch azentio.com; waited for the person's printed copy instead.

## Tradeoffs
<!-- example: 2026-05-29T10:14:32Z — picked TDD over BDD this run; the team is unit-first and the domain is well-understood -->
- 2026-10-31T06:40:00Z — Mint accent kept to outlines and focus rings only, since it fails text contrast on white.

## Open questions
<!-- example: 2026-05-29T10:14:32Z — confirm the retention window with compliance before the next stage hardens the schema -->
