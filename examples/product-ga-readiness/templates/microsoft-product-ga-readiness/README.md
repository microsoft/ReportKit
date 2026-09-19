# Product GA Readiness template

This declarative template renders one continuous management page:

1. Workbook-driven masthead and decision context.
2. Drone view with the overall verdict, confirmed blockers, readiness-gate tiles, primary release path, and management actions.
3. Execution view with milestones, decisions/support requests, and audience/client adoption progress.
4. Detailed records grouped by workstream with status, owner, target, GA impact, evidence, and next action.

The template is intentionally product-agnostic. Product names, dates, titles, labels, facts, owners, and statuses belong in the paired Excel workbook and canonical model.

The template requires four generic ReportKit registry components: `readiness-masthead`, `readiness-drone-view`, `readiness-progress-view`, and `readiness-detail-table`. The agency must add those components to the trusted renderer, schema, and automated tests before using this pack.
