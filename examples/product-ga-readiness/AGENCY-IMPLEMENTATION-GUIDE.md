# Agency implementation guide

## Outcome

Implement `microsoft/product-ga-readiness` as a reusable ReportKit template that reproduces the supplied single-flow management page for any product using the paired Excel contract.

The template must not contain product-specific technologies, partners, people, or fixed-date assumptions. Those values belong in the workbook.

## Operating boundary

- Excel owns report identity, facts, status labels, owners, dates, GA impact, evidence, and next actions.
- The adapter owns deterministic mapping and rejects missing required setup values.
- The canonical model owns normalized statuses and stable IDs.
- The ReportKit template owns layout, typography, responsive behavior, print behavior, and accessibility.
- Validators own schema, safety, lock, manifest, and generated-site checks.

## Required ReportKit implementation

The supplied declarative pack composes four generic components:

| Component | Source | Responsibility |
|---|---|---|
| `readiness-masthead` | Report metadata | Workbook-driven title, subtitle, data-as-of, generated-at, classification, and freshness. |
| `readiness-drone-view` | Report, metrics, groups, items | Overall verdict, confirmed blockers, countdown, gate tiles, primary release path, and top management actions. |
| `readiness-progress-view` | Milestones and categorized items | Key milestones, decisions/support requests, and audience/client adoption progress in one flowing execution section. |
| `readiness-detail-table` | Items grouped by groups | Continuous detail table with item, status, owner, target, GA impact, current evidence, and next action. |

These are trusted renderer components. Do not put executable HTML, CSS, or JavaScript in the imported template pack.

## Build flow

From the ReportKit repository root:

```powershell
python examples\product-ga-readiness\scripts\excel-to-reportkit.py `
  --input examples\product-ga-readiness\Product-GA-Readiness-Input.xlsx `
  --out-dir examples\product-ga-readiness

python scripts\validate-template `
  examples\product-ga-readiness\templates\microsoft-product-ga-readiness

python scripts\build-template `
  --template examples\product-ga-readiness\templates\microsoft-product-ga-readiness `
  --data examples\product-ga-readiness\canonical-report.json `
  --config examples\product-ga-readiness\product-ga-readiness.config.json `
  --lock examples\product-ga-readiness\reportkit.lock.json `
  --output examples\product-ga-readiness\generated-site `
  --overwrite
```

Use `--overwrite` only for a previously generated ReportKit-owned output directory.

## Daily operating model

The source owner refreshes the workbook once per business day. A scheduled build may then run the adapter, validate, build into staging, validate the entire staged site, and replace the published static files only after validation passes.

No network access, current-time injection, hidden status inference, or publication side effect belongs in the adapter or renderer.

## Definition of done

- A different product can be rendered by changing Excel values only.
- No project-specific text exists in template or renderer code.
- The executive verdict never conflicts with confirmed blocker rows.
- Owners remain visible in the details table; missing owners render as `Unassigned`.
- Milestones, decisions/support, and adoption records remain separately authorable in Excel and visible before the detailed table.
- The page is one continuous scroll with no tabs or hidden drill-down.
- Desktop, mobile, print, schema, safety, lock, manifest, and full-site validation pass.
