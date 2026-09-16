# Template Authoring

Templates communicate canonical facts for a particular audience. They do not understand source
schemas and do not publish output.

## Required files

Each template directory contains:

- `template.json`: capability contract and version
- `README.md`: audience, decision, pages, and data requirements
- `prototype.html`: preserved design reference during the implementation phase

## Shared design system

Templates must reuse shared:

- Masthead and report identity
- Classification and freshness
- Report period and provenance
- Metric cards and semantic units
- Status and priority badges
- Tables and responsive transformations
- Navigation
- Print rules
- Empty, partial, stale, warning, and error states

Template-specific layout and density are permitted. Reimplementing shared primitives is not.

## Static navigation

Multi-page templates generate deterministic file names. Links must resolve locally and remain
usable without JavaScript. Every summary count linking to a detail page must agree with the number
of records represented by that destination.

## Accessibility

Use semantic headings, landmarks, tables, captions, meaningful link labels, visible focus, text
alternatives for charts, and labels in addition to color.

