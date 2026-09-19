# Design acceptance criteria

## Page flow

The report is one continuous page in this order:

1. Workbook-driven masthead.
2. `Drone view` heading.
3. Overall GA decision card.
4. Four to eight readiness-gate tiles.
5. Primary release path and management actions.
6. `Execution view` with milestones, decisions/support, and audience/client adoption.
7. `Details view: GA readiness records` table.
8. ReportKit identity footer.

Do not add tabs, accordions, modal details, or a separate dashboard route.

## Executive decision card

- Lead with one unambiguous overall verdict.
- Show the count of confirmed GA blockers next to the verdict.
- List each confirmed blocker by name with one evidence sentence.
- Keep on-track substream language in the summary, never as a competing headline.
- Show the countdown separately from the verdict.

## Gate tiles

- Three columns at desktop width and one column on narrow screens.
- Every tile shows gate name, status label, value, and a one-sentence explanation.
- Status colors are consistent: green for ready/on track, amber for missing confirmation or evidence, red for at risk/blocked.

## Details table

- Group rows by workstream.
- Required columns are Item, Status, Owner, Target, GA impact, Current evidence, and Next action.
- Owners must never disappear because a screen is narrow; horizontal scrolling is acceptable.
- `Unassigned` is shown explicitly and contributes to a workbook check.

## Execution view

- Three adjacent panels at desktop width and one continuous stack on narrow screens.
- Milestones show status, owner, progress, target or completion date, and current evidence.
- Decisions and support requests show the request, status, owner, due date, and next action.
- Audience and client adoption shows status, stage/progress, owner, evidence, and next action.
- The section is summary-level; every decision and adoption record still appears in the detailed owner table below.

## Visual character

- Compact Microsoft-style product UI, not a slide deck.
- Light and dark color schemes supported.
- Quiet surfaces, thin borders, small-radius cards, restrained shadows, and limited decorative chrome.
- System font stack; no remote fonts, images, scripts, or services.

## Accessibility and static output

- Semantic headings preserve the page hierarchy.
- Tables use header cells and an accessible label.
- Status cannot be conveyed by color alone; every status has text.
- Focus and contrast meet the ReportKit baseline.
- Print output uses a light canvas and removes decorative shadows.
- Output remains usable with JavaScript disabled because generated reports contain no scripts.
