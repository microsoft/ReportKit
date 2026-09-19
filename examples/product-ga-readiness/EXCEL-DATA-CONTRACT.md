# Excel data contract

Only rows inside the named Excel tables are read. Sheet names, table names, column names, and stable IDs are contractual.

## Report Setup

Sheet: `Report Setup`  
Table: `ReportSettingsTable`

| Key | Required | Use |
|---|---:|---|
| Report ID | Yes | Stable canonical report ID. |
| Report Title | Yes | Page title and document title. |
| Subtitle | Yes | Scope statement below the title. |
| Product Name | Yes | Product identity for governance and authoring. |
| Primary GA Target | Yes | Product that owns the GA decision. |
| GA Target Label | Yes | Human-readable target label. |
| GA Target Date | Yes | Countdown and target-date calculations. |
| Data As Of | Yes | Freshness basis for source facts. |
| Generated At | Yes | Explicit UTC build timestamp; never replace silently. |
| Classification | Yes | Visible report classification. |
| Overall Status | Yes | Friendly status mapped to canonical ReportKit status. |
| Overall Status Label | Yes | Short executive verdict, such as `GA is AT RISK`. |
| Overall Status Summary | Yes | Plain-language reason for the verdict. |
| Decision Question | Yes | Management framing question. |
| Refresh Cadence | Yes | Expected operating cadence; this template uses daily. |
| Report Period Start / End | Yes | Decision window. |
| Template ID / Version | Yes | Exact ReportKit template identity. |
| Primary Color | No | Six-digit hex configuration value. |

## Readiness Gates

Sheet: `Readiness Gates`  
Table: `ReadinessGatesTable`

| Column | Rule |
|---|---|
| Gate ID | Stable and unique. |
| Gate Name | Short management-facing title. |
| Status | One allowed friendly status. |
| Status Label | Short tile label such as `ON TRACK`, `AT RISK`, or `UPDATE`. |
| Value / Unit | Current state shown prominently. Leave Unit blank for text values. |
| Summary | One sentence explaining the current state. |
| Owner | Named accountable team or person. |
| Target Date | Target for closing the gate. |
| Blocks GA | `Yes` only for a confirmed blocker to the primary GA decision. |
| Display Order | Integer used to order tiles. |

Use four to eight gates. Do not create a gate for every work item.

## Milestones

Sheet: `Milestones`  
Table: `MilestonesTable`

| Column | Rule |
|---|---|
| Milestone ID | Stable and unique across the workbook. |
| Milestone / Workstream / Milestone Type | Management-facing delivery point and its context. |
| Status | Current management signal. |
| Progress % | Supporting completion estimate from 0% through 100%; it does not replace Status. |
| Owner | Person or team responsible for delivery. |
| Target Date / Completed Date | Planned and actual completion dates. |
| Dependency / GA Impact | What the milestone relies on and whether it affects the primary GA decision. |
| Current Evidence / Next Action | Verifiable current state and concrete next step. |

## Decisions & Support

Sheet: `Decisions & Support`  
Table: `DecisionsSupportTable`

Use one row for each decision, commitment, escalation, support request, or action. `Owner` drives the request; `Needed From` identifies the person or organization that must respond. Use `Scope or Related Record` to link a request to an authoritative blocker without double-counting it.

## Audience Adoption

Sheet: `Audience Adoption`  
Table: `AudienceAdoptionTable`

Track target audiences, partners, and clients with `Adoption Stage`, `Progress %`, owner, evidence, and next action. A delayed partner is not automatically a blocker for the primary GA target; set `Blocks GA=Yes` only when the current GA decision truly depends on it.

## Readiness Details

Sheet: `Readiness Details`  
Table: `ReadinessDetailsTable`

| Column | Rule |
|---|---|
| Record ID | Stable and unique across the workbook. |
| Workstream ID | Stable grouping ID; `primary-release-path` identifies the path rendered in the Drone view. |
| Workstream | Display label for the grouped table. |
| Item | Product, platform, service, launch deliverable, or other authoritative readiness record. |
| Status | Friendly status mapped by the adapter. |
| Priority | Critical, High, Medium, Low, or Unknown. |
| Owner | Person or team doing the next action. Use `Unassigned` explicitly. |
| Accountable Owner | Person or team accountable for the outcome. |
| Target Date | Planned completion or decision date. |
| Blocks GA | `Yes` only for a confirmed blocker. |
| GA Impact | Exact decision impact, such as `Confirmed GA blocker`, `Primary GA target`, or `Launch readiness gap`. |
| Current State or Evidence | What is known now and how it was verified. |
| Next Action | Concrete action that advances or closes the record. |
| Evidence State | Not Required, Missing, Partial, Submitted, Verified, Rejected, or Unknown. |
| Release Scope | Current GA, partner adoption, follow-on release, or other explicit scope. |
| Source Reference | Human-readable source or meeting reference. |
| Display Order | Integer within the workstream. |

## Friendly status mapping

| Excel | Canonical |
|---|---|
| Complete | complete |
| Ready / On Track | healthy |
| In Progress | in-progress |
| At Risk | critical |
| Blocked | blocked |
| Update Required | warning |
| Pending Review | pending-review |
| Not Started | not-started |
| Unknown | unknown |
| N/A | not-applicable |

The adapter must fail on missing setup keys, invalid IDs, duplicate IDs, empty owners, invalid dates, or unsupported status values before invoking ReportKit.
