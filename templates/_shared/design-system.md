# ReportKit Design System

## Shared primitives

- ReportKit identity and template version
- Classification badge
- Report title, subtitle, and period
- Overall status and status rationale
- Freshness, `dataAsOf`, and `generatedAt`
- Metric card with explicit unit and optional delta
- Status, priority, ETA, and readiness badges
- Standard card and section heading
- Responsive data table
- Group/team summary card
- Static navigation and detail-page links
- Provenance footer
- Print stylesheet

## Required states

Every applicable component must define:

- Populated
- Empty
- Partial data
- Stale
- Warning
- Blocking error
- Unknown/not assessed

Templates may alter density and page composition but not redefine shared semantics.

