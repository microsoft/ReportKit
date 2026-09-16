# ReportKit v1 Implementation Plan

**Status:** Implementation baseline  
**Workspace:** `C:\hackweek-2026\ReportKit`  
**Product contract:** ReportKit is a static-first reporting toolkit that transforms operational
data into validated, audience-specific, publish-ready report sites using reusable templates.

## 1. Invariants

The implementation must preserve these boundaries:

- The source determines the facts.
- The template determines how those facts are communicated.
- The destination determines where the generated report lives.

Reproducibility is defined as:

```text
canonical model
+ template version
+ configuration
+ ReportKit version
= identical output
```

Rendering must not read the current clock, retrieve source data, or contact a publication target.
`generatedAt` is explicit canonical input.

## 2. Runtime Decision

Use Python 3.11 or later with the standard library for the initial deterministic helper scripts.
ReportKit remains a skill/agent product and is not published as a Python package. The repository
does not require installed dependencies for its v1 engine milestone.

Reasons:

- Cross-platform execution on Windows, macOS, and Linux
- Strong JSON, filesystem, HTML escaping, hashing, and testing support
- Straightforward distribution as a CLI
- No Node.js toolchain required for static generation

## 3. Repository Foundation

```text
ReportKit/
|-- README.md
|-- LICENSE
|-- SECURITY.md
|-- CONTRIBUTING.md
|-- SKILL.md
|-- docs/
|-- schema/
|-- templates/
|-- examples/
`-- scripts/
```

The original HTML designs remain preserved as `prototype.html` in their corresponding template
directories. They are design inputs, not yet generator output.

## 4. Implementation Phases

### Phase 1: Freeze the shared design system

Extract and normalize:

- Report identity and masthead
- Classification and freshness
- Report period and provenance
- Overall status treatment
- Metric cards and units
- Status, priority, ETA, and readiness badges
- Tables and responsive table transformations
- Group and team cards
- Navigation and static drill-down links
- Print rules
- Empty, partial, stale, warning, and error states

Deliverables:

- Shared design tokens
- Shared component contract
- Template-specific density/layout modifiers
- Accessibility and print acceptance checklist

### Phase 2: Finalize canonical schema 1.0

The schema must cover:

- Report identity, period, generated time, data freshness, status, and classification
- Metrics with explicit units
- Accountable and action ownership
- Groups and hierarchy
- Items, due date, ETA, blocker, status, next action, and age
- Trends with explicitly dated observations
- Highlights grounded in canonical facts
- Internal, source, evidence, and documentation links
- Provenance and record counts

Gates:

- Unsupported major schema versions fail.
- Duplicate IDs and unresolved references fail semantic validation.
- Missing metric units fail.
- Invalid timestamps fail.
- Prohibited secret-bearing fields fail.

### Phase 3: Implement the ReportKit skill

The skill workflow is:

```text
Inspect source data
-> choose template
-> map fields
-> validate canonical data
-> generate static HTML
-> validate generated site
-> return publishable files
```

The skill must not hide errors, silently invent facts, publish incomplete output, or place
credentials in canonical data.

### Phase 4: Build one deterministic generator

One generator renders all five templates through:

- Shared rendering primitives
- Template capability contracts
- Template-specific page composition
- Stable ordering with explicit tie-breakers
- Stable file names
- HTML escaping
- Multi-page static navigation
- Manifest and validation-report generation

The generator must be clock-free and network-free.

### Phase 5: Implement validation

Model validation runs before rendering. Site validation runs after rendering.

Blocking checks include:

- Schema and capability compatibility
- Missing required data
- Duplicate IDs and invalid references
- Unsafe or unescaped output
- Broken internal links
- Count-to-destination mismatches
- Missing freshness, classification, or report identity
- Manifest/file mismatch
- Prohibited external assets in self-contained mode

### Phase 6: Create the public demonstration

Use one non-sensitive, synthetic 401-record operational snapshot to render:

- Executive Health
- Action & Risk
- Portfolio / Team Rollup

The demo must show that the facts remain constant while the audience and decision surface change.

### Phase 7: Publication readiness

Before publishing the GitHub repository:

- Add screenshots and generated sample output
- Verify quick-start commands on a clean environment
- Run deterministic snapshot tests
- Run broken-link and count-integrity tests
- Run secret and sensitive-data checks
- Review licensing and organizational open-source requirements

Publishing itself requires an explicit repository destination and organizational approval.

## 5. Template Acceptance Matrix

| Template | Audience | Primary decision | Required specialized output |
|---|---|---|---|
| Executive Health | Leadership | Are we healthy and where must we intervene? | Status, KPIs, trends, decisions, outlook |
| Action & Risk | Operators | What must be done, by whom, and when? | Prioritized queue, owners, due/ETA, blockers, next action |
| Portfolio / Team | Managers | Which groups carry risk? | Comparable rollups and generated group detail pages |
| Operational Health | Service owners | What regressed and what affects reliability or delivery? | Service matrix, incidents, delivery signals, recovery path |
| Compliance / Readiness | Reviewers | Can we proceed and what exceptions remain? | Gates, controls, evidence, exceptions, readiness decision |

## 6. Deterministic Ordering

Every collection must define stable ordering. Recommended defaults:

- Metrics: explicit `order`, then ID
- Groups: explicit `order`, then display name, then ID
- Items: priority, blocker state, due date, then stable ID
- Trends: observation timestamp, then series ID
- Highlights: explicit `order`, then ID
- Pages: template-defined page type, then stable group/item ID

## 7. Generated Output

```text
report-site/
|-- index.html
|-- pages/
|-- assets/
|-- report-manifest.json
`-- validation-report.json
```

A build is successful only when this complete folder passes site validation. Publication must use
a complete validated artifact and preserve the previous destination if copying fails.

## 8. Initial Milestone

The repository foundation is complete when:

1. All five prototypes are preserved in template directories.
2. Each template has a machine-readable capability contract.
3. The canonical schema is valid JSON Schema.
4. `SKILL.md` defines the complete guided workflow.
5. Documentation explains authoring, validation, and publishing boundaries.
6. Build and validation entry points fail explicitly until their implementation phase is complete.
