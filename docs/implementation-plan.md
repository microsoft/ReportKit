# ReportKit v1 Implementation Plan

**Status:** Implementation baseline  
**Product contract:** ReportKit is a static-first reporting toolkit that transforms operational
data into validated, audience-specific, publish-ready report sites using reusable templates.

The phases below describe the target implementation, not completed release gates. The README
tracks current availability. File-copy publishing, a generic CSV adapter, executable guided
init/resume, and Pages deployment remain unimplemented; local data mapping is agent-assisted
manual work.

Current renderer scope: all five built-ins, real static Action & Risk filters, Portfolio / Team
detail pages for every canonical group, and a locked single-page declarative custom foundation.
Generated examples use the same public canonical snapshot and per-template configurations.
Operational and compliance views preserve canonical units and cannot invent missing domain facts.

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

Use Python 3.10 or later with the standard library for the deterministic helper scripts.
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
|-- LICENSE.md
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
directories. They remain archived design inputs, not generator output. Generated examples belong
under `examples/operational-snapshot/generated/<template>/`, not `templates/`.

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
Show three choices and wait (when no concrete task is supplied)
-> choose template or inspect a project manually or validate a custom template
-> inspect only explicitly supplied/authorized data
-> map source JSON/CSV fields manually with agent assistance
-> validate canonical data
-> generate static HTML
-> validate generated site
-> return publishable files
```

The skill must not hide errors, silently invent facts, publish incomplete output, or place
credentials in canonical data.

Install the complete repository as a lowercase `reportkit` skill folder, not `SKILL.md` alone;
follow the README's verified Copilot CLI instructions. Manual project inspection never automatically
traverses references: open only user-explicit safe scoped relative references, rejecting absolute,
traversal, symlink/junction/reparse-point paths. Custom installation and init/resume coordination
remain roadmap work.

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
- Operational Health
- Compliance / Readiness

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

`pages/` and `assets/` are optional and depend on the renderer. Current built-ins produce Executive
Health (one page), Action & Risk (five pages), Portfolio / Team (overview, all records, and every
group's detail page), Operational Health (one page), and Compliance / Readiness (one page).
Custom packs currently render one page; repeated groups, custom multi-page navigation, logo
rendering, complete terminology substitution, `linkTo`, and distinct layout variants remain roadmap.

Completion supplies clickable `index.html`, `report-manifest.json`, and `validation-report.json`
links to verified actual existing output paths, plus a ZIP link only when one was created.
Local-file links or a verified user-approved loopback server provide previews; GitHub source is not
live Pages hosting.

## 8. Initial Milestone (historical plan)

The repository foundation is complete when:

1. All five prototypes are preserved in template directories.
2. Each template has a machine-readable capability contract.
3. The canonical schema is valid JSON Schema.
4. `SKILL.md` defines the complete guided workflow.
5. Documentation explains authoring, validation, and publishing boundaries.
6. Build and validation entry points fail explicitly until their implementation phase is complete.

The entry points now build all five built-ins and the single-page custom foundation. Do not
restore placeholder failures. Derive the current regression count with
`python -B -m unittest discover -s tests -v`; no fixed count is a release guarantee.
