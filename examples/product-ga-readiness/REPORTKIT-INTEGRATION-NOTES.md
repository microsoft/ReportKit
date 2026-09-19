# ReportKit integration notes

The ReportKit declarative registry includes the generic trusted-engine extension required for the
Drone view, execution view, and seven-column readiness table. These notes document that extension.

## Schema changes

In `schema/reportkit-v1.schema.json`:

- Add optional `statusLabel` to metrics so an Excel-authored label such as `ON TRACK` or `UPDATE` survives normalization.
- Add optional `impact` to items so the details table does not misuse `blocker` for non-blocking impacts.
- Extend optional milestone fields with status text, progress percentage, type, owner, dependency, impact, next action, and display order.

In `schema/template-layout-v1.schema.json`:

- Register `readiness-masthead`.
- Register `readiness-drone-view`.
- Register `readiness-progress-view`.
- Register `readiness-detail-table` with source `items`.

## Renderer changes

In `scripts/template_pack.py`:

- Add the four component registry entries.
- Render the readiness components using only escaped canonical data.
- Derive confirmed blocker cards only from open items whose impact or blocker text explicitly identifies a confirmed blocker.
- Derive management actions from confirmed blockers first, then unassigned high-priority records.
- Render all gate metrics except `days-to-target`; use that metric for the countdown.
- Render the group with type `primary-release-path` as the release path.
- Render report milestones and items categorized under `decisions-support` and `audience-adoption` in the execution view.
- Render every group and item in the details table exactly once.
- Preserve ReportKit metadata, classification, freshness, template identity, digest, CSP, and item count.

## Regression coverage

- Valid pack and canonical example pass.
- Missing title and missing action owner fail required-field validation.
- Two confirmed blocker items produce a red overall badge with count two.
- An on-track primary path cannot replace or soften an at-risk overall verdict.
- Metrics beyond four are rendered; this template expects up to eight gates.
- Every canonical item appears once in the details table.
- HTML escaping, exact CSP, script-free output, mobile reflow, print mode, and deterministic output pass.
- Workbook title, target, classification, and owner changes appear after an adapter/build cycle without template edits.

## Validation result

The supplied pack and generated site validate with zero errors and zero warnings. The adapter emits a one-point daily blocker observation so the canonical model remains ready for future trend use, although this first template version does not display a trend chart.
