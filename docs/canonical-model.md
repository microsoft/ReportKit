# Canonical Model

The canonical model is source-independent, schema-versioned reporting data.

## Root structure

```json
{
  "schemaVersion": "1.0",
  "report": {},
  "metrics": [],
  "groups": [],
  "items": [],
  "trends": [],
  "highlights": [],
  "links": [],
  "provenance": {}
}
```

Only `schemaVersion`, `report`, and `provenance` are universally required. Collection sections are
optional in the canonical schema and become required only when selected by a template capability
contract. When present, a collection is an array.

## Time semantics

- `report.generatedAt`: explicit reproducibility input
- `report.dataAsOf`: when the underlying facts were current
- `provenance.sources[].retrievedAt`: when an adapter obtained source data
- `report.period`: the reporting interval or human-readable reporting window

`report.period.startDate` and `endDate` are calendar dates (`YYYY-MM-DD`), not date-time values.

## Ownership

`accountableOwner` owns the outcome. `actionOwner` performs the work. They must remain separate,
and either may be absent only when the template capability permits it.

## Counts and units

Every metric declares its unit. Raw records, canonical items, grouped decisions, programs, teams,
services, requirements, incidents, builds, and percentages are not interchangeable.

Items may separately declare `lifecycle`, `category`, `confidence`, `rootCauseState`,
`evidenceState`, an `exception`, a `readinessGate`, and `recoveryMilestones`. Reports may declare
`outlookMilestones`, and provenance may declare per-source `coverage`. These fields keep workflow,
health, evidence, exception, readiness, recovery, and source-coverage facts distinct instead of
overloading `status` or flattening them into prose.

`provenance.recordCounts.canonicalItems`, when present, must equal `items.length`. `raw` remains an
independent source count. If `sourceTotal` is supplied, it must reconcile with the individual
`provenance.sources[].recordCount` values and with `raw`.

## References

Groups may reference child groups and items. All references must resolve, and IDs must be unique
within their collection.

The human-readable group field is `groups[].label`.

See [`../schema/reportkit-v1.schema.json`](../schema/reportkit-v1.schema.json).
