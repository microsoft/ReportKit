# ReportKit Marketing and Visual Test Plan

> From operational data to a durable report—without building another dashboard.

## Objective

Create a credible open-source launch package proving that one canonical operational snapshot can
support five audience-specific, publish-ready static reports.

The launch sells outcomes:

- A durable report instead of another recurring email
- Five decision surfaces from one shared set of facts
- Static HTML without a backend
- Deterministic, validated output
- Portable file-based publication
- A skill-first workflow rather than another package to deploy

## Launch message

**Headline:** Turn operational data into decision-ready static reports.

**Supporting line:** ReportKit uses one canonical model and five reusable templates to create
validated HTML reports for leaders, operators, managers, service owners, and reviewers.

**Proof:** One model. Five report designs. One generated today.

## Required screenshots

All screenshots use Chromium, light mode, 100% zoom, device scale factor 1, classification
`Public sample`, and the same 15 September 2026 synthetic snapshot.

| File | Template | Decision |
|---|---|---|
| `executive-health-hero.png` | Executive Health | Do leaders need to intervene? |
| `action-risk-hero.png` | Action & Risk | What must happen next? |
| `portfolio-team-hero.png` | Portfolio / Team | Which teams carry the risk? |
| `operational-health-hero.png` | Operational Health | What regressed or threatens reliability? |
| `compliance-readiness-hero.png` | Compliance / Readiness | Can the review or release proceed? |

Desktop heroes use 1440 x 1000. Mobile proofs use 390 x 844. Full-page captures use a 1440-pixel
viewport. Final images contain no browser chrome, preview label, internal service identifiers,
confidential data, hover-only facts, clipped content, or animation-dependent state.

## Interaction contracts

### Action & Risk

Queue tiles are navigation:

- All open
- Overdue
- Blocked
- Due in seven days

Each static filtered state has a stable URL, selected-state announcement, record count matching
the displayed rows, freshness/period/classification, keyboard focus, and a route to All open.
Relative dates use the explicit report date, never the viewer's clock.

### Portfolio / Team

Each team card is a real keyboard-focusable link with a descriptive accessible name. Team detail
pages preserve report metadata, distinguish accountable ownership from action ownership, reconcile
their totals, use stable team IDs, and provide navigation back to the overview.

## Visual capture workflow

The optional development-only Playwright workflow:

- Opens only checked-in public sample pages
- Sets fixed viewport, scale factor, and light color scheme
- Disables animations and transitions
- Waits for fonts and layout
- Writes stable PNG names
- Fails for missing pages or states
- Never uploads or publishes

Playwright is not a generated-report dependency and is not part of the ReportKit skill runtime.

## Acceptance gates

Every accepted screenshot must satisfy:

- Visible report title, template identity, classification, period, `dataAsOf`, `generatedAt`, and freshness
- Explicit metric units
- No invented factual prose
- No sensitive or placeholder content
- No horizontal overflow, clipping, overlap, or unreadable columns
- Primary decision surface above the fold
- One clear `h1`, keyboard reachability, visible focus, non-color status cues, and readable contrast
- Useful core content and navigation with JavaScript disabled
- Stable filenames, ordering, relative-date behavior, and link targets

Score each hero from 1 to 5 for immediate comprehension, decision clarity, credibility,
information hierarchy, product consistency, static usability, and public safety. No launch hero
may score below 4.

## README visual order

1. Product name and outcome
2. Executive Health hero
3. Five templates, static-first, deterministic validation
4. Five-template gallery
5. Sixty-second quick start
6. Architectural boundary
7. Current implementation status
8. Documentation links

## Positioning guardrails

- Describe ReportKit as an experimental open-source Hack Week project until support is established.
- Do not imply a hosted Microsoft service.
- Do not imply all five renderers are implemented.
- Distinguish approved prototypes from generated output.
- Treat S360 and Azure DevOps only as potential adapters or examples.
- Do not claim publication-grade validation before all quality gates exist.

## Release gates

**Marketing preview:** five prototype heroes, working links, public synthetic data, mobile review,
README gallery, and accurate implementation status.

**Technical preview:** five generated templates, script-free interaction states, visual regression
workflow, manifests, validation reports, sensitive-field checks, and matching documentation.

**v1:** stable contracts, all renderers, publication-quality validation, fail-closed publisher,
accessibility/restrictive-host testing, and compatibility policy.

## Definition of done

A new reader can inspect the README for thirty seconds and explain:

- What ReportKit creates
- Why static-first matters
- Why five templates exist
- How one fact set supports different audiences
- Which parts work today
- How to run the Executive Health example
