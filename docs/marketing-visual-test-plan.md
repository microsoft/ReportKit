# ReportKit Marketing and Visual Test Plan

> From operational data to a durable report—without building another dashboard.

## Objective

Create a credible open-source launch package proving that one canonical operational snapshot can
support five audience-specific static reports. This plan defines evidence to capture, not a claim
of production readiness or deployed hosting.

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

**Required proof:** One canonical source. Five generated reports.

Capture only after all five built-in samples have been built and validated from
`examples/operational-snapshot/canonical-report.json` with their `<template>.config.json` files.
Use `examples/operational-snapshot/generated/<template>/index.html`, not archived prototype HTML.
The 401-record count measures source records; it is not a service, control, or compliance count.
Do not invent service-health, control-pass, exception, or release-approval facts absent from the model.

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
viewport. Final generated-example images contain no browser chrome, prototype label, internal service identifiers,
confidential data, hover-only facts, clipped content, or animation-dependent state.

## Interaction contracts

### Action & Risk

Queue tiles are navigation:

- All attention (attention statuses or an explicit nonblank blocker)
- Overdue
- Blocked
- Due in seven days

Each static filtered state has a stable URL, selected-state announcement, record count matching
the displayed rows, freshness/period/classification, keyboard focus, and a route to All attention.
Relative dates use the UTC date of explicit `generatedAt`, never the viewer's clock. Overdue means
strictly earlier; due in seven days includes today through today + 7. Healthy, passed, complete,
and not-applicable records are excluded from date queues unless they have an explicit blocker.
Canonical health status is not an open/closed lifecycle. Overdue, blocked, and due-soon views can
overlap and must not be summed as mutually exclusive buckets.
Attention statuses are warning, critical, blocked, failed, in-progress, pending-review, and
not-started. The public sample uses warning/critical; archived Action interaction prototypes
select only those two statuses and are not the authoritative built-in behavior.

Capture these files under `examples/operational-snapshot/generated/action-risk/`:

| View | Generated file |
|---|---|
| All attention | `index.html` |
| Overdue | `overdue.html` |
| Blocked | `blocked.html` |
| Due in seven days | `due-next-seven-days.html` |
| All canonical records | `all-records.html` |

### Portfolio / Team

Each team card is a real keyboard-focusable link with a descriptive accessible name. Team detail
pages preserve report metadata, distinguish accountable ownership from action ownership, reconcile
their totals, use stable team IDs, and provide navigation back to the overview.

The generated overview is `portfolio-team/index.html`, with `all-records.html` for the complete
record set and `group-<full SHA-256 of group ID>.html` for every canonical group. Discover child
paths from the generated overview or manifest; never substitute canonical `groups[].page` hints.
Membership unions `groups[].itemIds`, `items[].groupIds`, and descendants, deduplicated per group.
Validate each group's record set; do not sum overlapping groups as disjoint portfolio totals.
Operational Health and Compliance / Readiness currently each emit one complete `index.html`.

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

After explicitly approving replacement of the checked-in ReportKit-owned public sample outputs,
generate and validate all five examples, then regenerate local showcase HTML and archived
prototype labels:

```powershell
python -B scripts\build-examples --overwrite
python -B scripts\create_prototype_companions.py
python -B scripts\prepare_marketing_pages.py
```

The marketing generator refuses missing or unvalidated public examples. It does not build reports
or capture screenshots. Recapture screenshots separately using the current capture contract after
sample generation. Existing image filenames stay stable; a stale prototype image is not proof of
generated behavior.

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
- Claim five implemented renderers only with five validated built-in generated examples.
- Keep archived prototypes distinct: Action & Risk interaction pages are canonical-populated;
  the other archived design values are illustrative, not canonical-generated.
- GitHub HTML links expose source; the local showcase is a browser preview. Pages is not deployed.
- Publisher, generic CSV adapter, and executable guided init/resume remain unimplemented.
- Manual agent-assisted mapping is not an executable generic mapper.
- Treat S360 and Azure DevOps only as potential adapters or examples.
- Do not claim publication-grade validation before all quality gates exist.

## Release gates

**Experimental marketing evidence:** five generated-example heroes, working links, public synthetic
data, mobile review, README gallery, and accurate implementation status. Historical prototype
captures remain design evidence only.

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
- How to run the Executive Health quick start and select any of the other four built-ins
