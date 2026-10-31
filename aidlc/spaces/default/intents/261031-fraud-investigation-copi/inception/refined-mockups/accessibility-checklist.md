# Accessibility Checklist (WCAG 2.1 AA basics)

Inputs: `inception/requirements-analysis/requirements.md` (NFR10), `ideation/rough-mockups/wireframes.md`, `ideation/rough-mockups/user-flow.md`, `inception/user-stories/stories.md` (AC5.2.4), `inception/practices-discovery/team-practices.md`.

## Per Screen

| Screen | Heading | Landmark | Keyboard entry | Checks |
|---|---|---|---|---|
| Shell | — | header, nav, main | Skip-to-content link | Visible focus ring (mint, 2 px) |
| Data Upload | h1, h2 report | main, form | Source select | Labels on all inputs; results announced |
| Dashboard | h1, h2 panels | main | First stat tile | Every chart has a table alternative |
| Alerts | h1 | main, form "Alert filters" | First filter | Sortable `th`; risk shown with letter and number |
| Alert Detail | h1, h2 sections | main | Open case button | Graph has a text list; AI panel announced |
| Case Queue | h1 | main | Status filter | Table semantics |
| Case Detail | h1, h2 sections | main, form | First decision radio | fieldset/legend; dialog focus trap; errors in text |
| AI Activity | h1 | main | First row toggle | `aria-expanded` on toggles |
| Data Safety | h1, h2 | main | First section | Definition list for examples |
| Audit Trail | h1 | main | Action filter | Table semantics |

## Global

- [ ] Every function works by keyboard alone, with no keyboard traps.
- [ ] Text contrast is at least 4.5:1. Mint #55FFBE is never used for text. Red, green and amber band colours are checked with their text colour at build time.
- [ ] Risk and status are never shown by colour alone.
- [ ] Every input has a visible label. Errors name the field and the fix.
- [ ] `prefers-reduced-motion` turns off non-essential motion, including graph animation.
- [ ] The page `lang` is "en".
- [ ] Layouts hold at 200 percent zoom on desktop. The tablet layout (768–1279 px) collapses the side navigation to icons, and wide tables scroll with the first column pinned.
- [ ] An automated axe check is part of the frontend tests (team practices: Vitest in CI).
