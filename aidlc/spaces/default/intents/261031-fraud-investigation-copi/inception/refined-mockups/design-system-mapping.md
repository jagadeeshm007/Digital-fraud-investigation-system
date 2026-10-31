# Design System Mapping

Inputs: `ideation/rough-mockups/wireframes.md` (Brand Look tokens), `inception/requirements-analysis/requirements.md` (NFR10, NFR11), `inception/user-stories/stories.md`, `inception/practices-discovery/team-practices.md` (Vite+ lint and format), `ideation/rough-mockups/user-flow.md`.

## Tokens to Theme

| Token | Value | coss ui / Tailwind variable |
|---|---|---|
| Ink | #16303D | `--foreground` |
| Ink 2 | #212D3A | `--muted-foreground` (dark theme surface) |
| Mint accent | #55FFBE | `--ring`, active nav underline (never text) |
| Deep green | #39AB7F | `--primary` (white text on it) |
| Green | #2ED88E | `--success`, Low band background with dark text |
| Red | #E51520 | `--destructive`, High band |
| Amber | (chosen to pass 4.5:1 with ink text) | Medium band |
| Background | #FFFFFF | `--background` |
| Heading font | Poppins 600/700 | `--font-heading` |
| Body font | Noto Sans 400/500 | `--font-sans` |

## Screen to Component Map

| Mockup element | coss ui / library component |
|---|---|
| Side navigation | Sidebar |
| Role switcher | Select |
| Masked badge, RiskBadge | Badge |
| Stat tiles | Card |
| Charts | simple bar built with divs, plus a table alternative (no chart library needed) |
| Tables | Table with pagination |
| Filters | Input, Select, date Input |
| Upload | Input type=file, Button |
| Tabs (Report, Rejected, Mapping) | Tabs |
| Rule settings, record details | Sheet (drawer) |
| Escalate confirmation | AlertDialog |
| Decision radios | RadioGroup in a fieldset |
| Toasts | Toast |
| Loading | Skeleton |
| Entity graph | React Flow (`@xyflow/react`) with a d3-force layout |

## Notes

- Light theme first. A dark theme swaps the background to Ink and the text to white, keeping mint for focus rings only.
- No Azentio logo or trademarks are used.
