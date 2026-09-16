# ReportKit

> From operational data to a durable report—without building another dashboard.

ReportKit is an open-source, static-first reporting skill that helps an AI agent transform structured operational data into polished, validated, audience-specific HTML report sites.

It is designed for teams whose reporting is trapped in recurring email, presentations, spreadsheets, screenshots, or source-specific dashboards. ReportKit converts a point-in-time data snapshot into a portable report that can be reviewed, archived, compared, and published almost anywhere.

ReportKit is **a skill and reporting contract**, not a hosted service and not a package that users must deploy. The repository contains the skill instructions, canonical data contract, reusable report templates, validation rules, examples, and supporting generation scripts.

> **Experimental status:** ReportKit is an open-source Hack Week project. Executive Health is the
> current generated vertical slice; the other four reports shown below are approved static
> prototypes awaiting connection to the deterministic engine.

![Executive Health report showing portfolio status, freshness, metrics, trend, and confirmed signals](docs/assets/screenshots/executive-health-hero.png)

| Five report designs | Static-first | Deterministic validation |
|---|---|---|
| Executive Health is generated today; four clearly labeled prototypes illustrate the remaining audience designs. | Core content and navigation work without a backend or required JavaScript. | Explicit inputs produce stable output that is validated before publication. |

## One generated report, five report designs

| Leadership | Operations |
|---|---|
| [![Executive Health](docs/assets/screenshots/executive-health-hero.png)](examples/operational-snapshot/generated/executive-health/index.html) | [![Action and Risk](docs/assets/screenshots/action-risk-hero.png)](templates/action-risk/action-risk.html) |
| **Are we healthy?** | **What must happen next?** |

| Management | Reliability | Assurance |
|---|---|---|
| [![Portfolio and Team](docs/assets/screenshots/portfolio-team-hero.png)](templates/portfolio-team/portfolio-team.html) | [![Operational Health](docs/assets/screenshots/operational-health-hero.png)](templates/operational-health/operational-health.html) | [![Compliance Readiness](docs/assets/screenshots/compliance-readiness-hero.png)](templates/compliance-readiness/compliance-readiness.html) |
| **Where is risk concentrated?** | **What regressed?** | **Can we proceed?** |

[Watch the 36-second silent walkthrough](docs/assets/reportkit-walkthrough.mp4) ·
[View the architecture diagram](docs/assets/reportkit-architecture.svg) ·
[Open the local showcase](showcase/index.html)

GitHub displays checked-in `.html` links as source until static hosting is configured. Clone or
download the repository and open the local showcase to review the rendered pages.

## 60-second quick start

```powershell
python scripts\validate `
  examples\operational-snapshot\canonical-report.json `
  --kind model `
  --template executive-health

python scripts\build `
  --template executive-health `
  --data examples\operational-snapshot\canonical-report.json `
  --config examples\operational-snapshot\executive-health.config.json `
  --output report-site

python scripts\validate report-site --kind site
```

Open `report-site\index.html`. No server or package installation is required.

### Bring your own declarative template

```powershell
python scripts\validate-template `
  examples\custom-template-project\templates\contoso-release-review

python scripts\build-template `
  --template examples\custom-template-project\templates\contoso-release-review `
  --data examples\custom-template-project\templates\contoso-release-review\examples\canonical-report.json `
  --config examples\custom-template-project\templates\contoso-release-review\examples\configuration.json `
  --lock examples\custom-template-project\reportkit.lock.json `
  --output custom-report-site
```

Declarative packs compose approved ReportKit components without executable HTML, CSS, JavaScript,
or renderer code. Their immutable SHA-256 identity is recorded in project state, the lock file, and
the generated manifest. Text-file line endings are normalized before digesting so the same pack
retains its identity across Windows and Linux checkouts.

## Why ReportKit?

Teams often already have the facts they need. The difficulty is turning those facts into a report that is:

- Appropriate for a particular audience
- Clear about freshness and reporting period
- Consistent about status, ownership, dates, and units
- Safe to publish
- Useful without a backend
- Easy to archive as a point-in-time record
- Portable across SharePoint, file shares, artifacts, storage, and static hosting

A dashboard is not always the right answer. Dashboards require hosting, permissions, runtime dependencies, maintenance, and continued access to the source system. Email reports are easy to send but difficult to navigate, reuse, compare, and retain.

ReportKit produces a durable middle ground: a validated static report site.

## Product boundary

ReportKit follows one architectural rule:

> **The source determines the facts.**  
> **The template determines how those facts are communicated.**  
> **The destination determines where the generated report lives.**

This means:

- Adapters transform source data into canonical ReportKit data.
- Templates communicate canonical facts for a specific audience.
- Publishers copy validated output to a destination.
- Adapters do not contain presentation logic.
- Templates do not understand source-specific schemas.
- Publishers do not transform report facts.

## Static-first is a feature

Every ReportKit template is designed to produce useful output without JavaScript.

Static output provides:

- No backend or database dependency
- Inexpensive and flexible hosting
- Point-in-time archival
- Easy file-based distribution
- Compatibility with restrictive hosting environments
- Predictable security boundaries
- Simple link and content validation
- Long-term readability after the source system changes

Optional progressive enhancement may be added later, but core report content and navigation must remain available without it.

## Who is ReportKit for?

ReportKit is useful for:

- Engineering and operations teams
- Program and portfolio managers
- Release and readiness reviewers
- Security and compliance teams
- Leadership reporting
- Incident and reliability reviews
- Teams publishing reports to SharePoint or file-based portals
- AI agents that need a governed way to create operational reports

ReportKit is source-neutral. Azure DevOps, GitHub, CSV, JSON, service-health systems, security platforms, spreadsheets, and internal APIs can all be inputs when an adapter maps them into the canonical model.

## The five templates

ReportKit v1 defines five reporting templates. Templates are selected by the decision the reader needs to make, not by the source system that supplied the data.

| Template | Primary audience | Primary decision | Typical content |
|---|---|---|---|
| **Executive Health** | Executives and senior leaders | Are we healthy, and where does leadership need to intervene? | Overall status, KPIs, trends, highlights, decisions, concentration, and outlook |
| **Action & Risk Tracker** | Operators and delivery teams | What needs to be fixed, by whom, and by when? | Prioritized actions, accountable owner, action owner, due date, ETA, blockers, aging, and next action |
| **Portfolio / Team Rollup** | Managers and organization leaders | Which teams carry the most risk, and where should management intervene? | Organization summary, comparable team metrics, risk concentration, team cards, and linked team-detail pages |
| **Operational Health** | Service owners and release managers | What is degraded, what threatens reliability or delivery, and what must recover next? | Availability, builds, deployments, incidents, regressions, blockers, service health, and recovery milestones |
| **Compliance / Readiness** | Assurance leaders and approvers | Can the review or release proceed, and which requirements or exceptions remain? | Controls, evidence, gates, exceptions, readiness status, owners, remediation, and expiry dates |

### Choosing a template

Use the reader’s question as the selector:

- “Do leaders need to intervene?” → **Executive Health**
- “What exactly must we do next?” → **Action & Risk Tracker**
- “Which teams are carrying the risk?” → **Portfolio / Team Rollup**
- “What is broken or degrading operationally?” → **Operational Health**
- “Are the requirements satisfied so we can proceed?” → **Compliance / Readiness**

The same canonical snapshot can be rendered through multiple templates. The facts remain the same while the decision surface changes.

## How it works

```mermaid
flowchart TD
    A[Source data] --> B[Adapter]
    B --> C[Canonical model]
    C --> D[Model validation]
    D --> E[Audience template]
    E --> F[Static report site]
    F --> G[Site validation]
    G --> H[File-copy publisher]
```

The layers have intentionally narrow responsibilities:

| Layer | Knows about | Must not do |
|---|---|---|
| Source adapter | Source schema and canonical schema | Render HTML or publish files |
| Canonical model | Reporting facts and semantics | Encode source-specific presentation |
| Validator | Schemas, references, safety, and consistency | Silently repair or invent facts |
| Template | Audience and report composition | Query source systems or change facts |
| Site generator | Deterministic rendering and file creation | Read the current clock or network |
| Publisher | Validated files and destination | Transform report data or publish partial output |

## Using ReportKit as an agent skill

ReportKit is intended to be used by an agent that can read the repository’s `SKILL.md` and work with local files.

### 1. Make the skill available

Clone or download this repository and make `SKILL.md` available through the skill mechanism supported by your agent environment.

```bash
git clone https://github.com/microsoft/ReportKit.git
cd ReportKit
```

There is no requirement to publish or install ReportKit as a language package. Supporting scripts may use standard development runtimes, but the product surface is the skill, contracts, templates, and generated static output.

## Repository status at a glance

ReportKit is an early open-source Hack Week project. The repository currently provides one working end-to-end vertical slice and four additional approved visual prototypes.

| Capability | Current state |
|---|---|
| Skill-guided workflow | Available in `SKILL.md` |
| Canonical schema 1.0 | Available |
| Configuration, capability, manifest, and validation schemas | Available |
| Executive Health deterministic generation | Implemented |
| Executive Health model and generated-site validation | Implemented baseline |
| Action & Risk visual prototype | Complete; generator connection pending |
| Portfolio / Team visual prototype and linked team pages | Complete; generator connection pending |
| Operational Health visual prototype | Complete; generator connection pending |
| Compliance / Readiness visual prototype | Complete; generator connection pending |
| Synthetic 401-record sample | Available |
| Safe file-copy publisher | Not implemented yet |
| Published language package | Intentionally not part of the product |

The prototype pages demonstrate the approved design direction. They are not generated customer reports and must not be mistaken for completed renderer support.

## Prerequisites

The current helper scripts require Python 3.10 or later and use only the Python standard library. There is no package installation step, no virtual environment requirement, and no dependency download.

Confirm your runtime:

```bash
python3 --version
```

On Windows, `python` may be the appropriate executable instead of `python3`.

## Quick start

Clone the repository and enter it:

```bash
git clone https://github.com/microsoft/ReportKit.git
cd ReportKit
```

Validate the included canonical model:

```bash
python3 scripts/validate \
  examples/operational-snapshot/canonical-report.json \
  --kind model \
  --template executive-health
```

Build the Executive Health sample:

```bash
python3 scripts/build \
  --template executive-health \
  --data examples/operational-snapshot/canonical-report.json \
  --config examples/operational-snapshot/executive-health.config.json \
  --output report-site
```

Validate the generated site:

```bash
python3 scripts/validate report-site --kind site
```

Open `report-site/index.html` in a browser. No server is required.

PowerShell equivalent:

```powershell
python scripts\validate `
  examples\operational-snapshot\canonical-report.json `
  --kind model `
  --template executive-health

python scripts\build `
  --template executive-health `
  --data examples\operational-snapshot\canonical-report.json `
  --config examples\operational-snapshot\executive-health.config.json `
  --output report-site

python scripts\validate report-site --kind site
```

Run the tests:

```bash
python3 -B -m unittest discover -s tests -v
```

### 2. Give the agent your data

Provide one of the following:

- Canonical ReportKit JSON
- Source JSON that needs mapping
- CSV data and a field-mapping description
- Exported API or query results
- A script that produces a stable snapshot

Do not provide credentials, live access tokens, private keys, certificates, or secrets as report data.

### 3. Describe the audience and decision

Example prompt:

```text
Use the ReportKit skill.

Turn operations-snapshot.json into an Action & Risk report for service owners.
Keep accountable owner separate from action owner.
The report period ends on 2026-09-15.
Use 2026-09-15T18:00:00Z as generatedAt.
Validate everything and return a static report folder.
Do not publish it.
```

Another example:

```text
Use the ReportKit Portfolio / Team template for this canonical model.
Generate one overview page and one static page for each team.
Show freshness, classification, coverage, and management actions.
Fail if team totals do not reconcile with the portfolio totals.
```

### 4. Review the result

A successful run returns a complete static report directory, its manifest, and its validation report. Publication is a separate, explicit operation.

## Canonical data model

ReportKit templates consume a generic, schema-versioned model rather than source-specific data.

```json
{
  "schemaVersion": "1.0",
  "report": {
    "id": "service-health-2026-09-15",
    "title": "Service Health",
    "subtitle": "Weekly operational review",
    "status": "warning",
    "statusLabel": "Focused intervention",
    "statusSummary": "Two services require recovery before the next release window.",
    "period": {
      "startDate": "2026-09-09",
      "endDate": "2026-09-15",
      "label": "Week ending 15 Sep 2026"
    },
    "generatedAt": "2026-09-15T18:00:00Z",
    "dataAsOf": "2026-09-15T17:55:00Z",
    "classification": "Internal"
  },
  "metrics": [],
  "groups": [],
  "items": [],
  "trends": [],
  "highlights": [],
  "links": [],
  "provenance": {}
}
```

### Important semantic distinctions

ReportKit preserves distinctions that are frequently lost in one-off reports:

| Concept | Meaning |
|---|---|
| `generatedAt` | When the report artifact was generated; an explicit reproducibility input |
| `dataAsOf` | When the underlying facts were current |
| Report period | The business interval represented by the report |
| `retrievedAt` | When an adapter obtained data from a source |
| Raw record count | Number of records received from the source |
| Canonical item count | Number of normalized ReportKit items |
| Grouped decision count | Number of rollups or decisions presented to the reader |
| Accountable owner | Person or group responsible for the outcome |
| Action owner | Person or group performing the work |
| Due date | Committed completion date |
| ETA | Current expected completion date |
| Status | Current state of an item |
| Next action | Concrete work that should happen next |
| Source link | Link to an authoritative source record |
| Report navigation | Link between generated report pages |

Templates and adapters must not flatten these concepts into generic strings simply because the source system does not model them cleanly.

## Deterministic generation

ReportKit defines reproducibility as:

```text
canonical model
+ template version
+ configuration
+ ReportKit version
= identical output
```

The generator must not silently inject the current date or time. `generatedAt` is supplied through the canonical model or build invocation and becomes part of the reproducibility inputs.

During rendering, ReportKit must not:

- Read the current clock
- Retrieve source data
- Contact a publication target
- Generate random IDs
- Depend on unstable iteration order
- Insert machine-specific absolute paths
- Add nondeterministic metadata to output files

Collections use defined ordering rules and stable tie-breakers. If two inputs are identical, their generated report structure and contents must be identical.

## Template capability contracts

Each template publishes a machine-readable capability contract describing:

- Template ID and version
- Supported canonical schema versions
- Required model sections
- Required fields
- Optional sections
- Supported page types
- Supported states
- Multi-page behavior
- Script-free support
- Responsive and print support
- Self-contained asset policy

Capability contracts allow validation to fail with an understandable message before rendering begins.

For example:

```json
{
  "id": "executive-health",
  "contractVersion": "1.0",
  "version": "1.0",
  "supportedSchemaVersions": ["1.0"],
  "requiredSections": ["report", "metrics"],
  "optionalSections": ["trends", "highlights", "groups", "items"],
  "features": {
    "multiPage": true,
    "scriptFree": true,
    "responsive": true,
    "printable": true
  }
}
```

## Output contract

The v1 product contract defines a complete report-site folder. The current Executive Health vertical slice emits the required entry point and machine-readable records:

```text
report-site/
├── index.html
├── report-manifest.json
└── validation-report.json
```

Multi-page renderers may additionally emit `pages/`, while renderers with local supporting files may emit `assets/`. Those directories are not created when they are unnecessary. The entry point, manifest, and validation report are always present after a successful current build.

### Report manifest

The manifest makes the artifact understandable without scraping HTML.

```json
{
  "reportKitVersion": "0.1.0",
  "schemaVersion": "1.0",
  "template": {
    "id": "executive-health",
    "version": "1.0"
  },
  "reportId": "service-health-2026-09-15",
  "generatedAt": "2026-09-15T18:00:00Z",
  "dataAsOf": "2026-09-15T17:55:00Z",
  "classification": "Internal",
  "pageCount": 1,
  "itemCount": 401,
  "validation": {
    "status": "passed",
    "errors": 0,
    "warnings": 0,
    "info": 0
  }
}
```

The manifest supports archives, report catalogs, freshness monitors, comparisons, automation, and future publishing workflows.

## Validation

Validation runs twice:

1. **Before rendering**, against the canonical model and selected template capability contract
2. **After rendering**, against the generated report site

### Severity levels

| Severity | Meaning | Publication behavior |
|---|---|---|
| `error` | Invalid, unsafe, incomplete, or inconsistent | Publication blocked |
| `warning` | Report is usable but requires attention | Publication allowed unless configuration is stricter |
| `info` | Recommendation or optional observation | Publication allowed |

### Current model validation baseline

Model validation includes:

- Supported schema and template versions
- Required report identity, timestamps, classification, and provenance
- Valid timestamps and dates
- Explicit metric units
- Unique IDs
- Resolved group and item references
- Valid status, priority, and severity values
- Due-date, ETA, and next-action-date formats
- Provenance and source counts
- Prohibited sensitive fields
- Raw item-count integrity

The checked-in JSON Schema files define a broader machine-readable contract. The current dependency-free engine performs an explicit subset of those structural and semantic checks in Python. Full schema-driven validation and complete enforcement of every template `requiredFields` path remain implementation work.

### Current generated-site validation baseline

Site validation includes:

- Expected output files
- Valid internal links
- Manifest page-count and optional expected item-count agreement
- Manifest accuracy
- Classification visibility
- Freshness visibility
- Required headings and landmarks
- Basic `main` and `h1` accessibility structure
- Script-free core rendering
- HTML escaping

The full v1 quality target additionally includes keyboard checks, layout-width checks, responsive and print assertions, comprehensive HTML-escaping checks, external-asset policy enforcement, and count reconciliation across tiles, tables, and detail pages. Those stronger checks should be added before treating the validator as publication-grade.

Errors block publication.

## Missing and edge states

Templates must explicitly handle applicable states such as:

- No history available
- No critical decisions
- No open actions
- Empty optional section
- Stale data
- Partial source coverage
- Unknown status
- Missing accountable owner
- Unmapped records
- Expired exception
- Planned maintenance
- Validation warning

Missing or unknown data must not silently become healthy, current, complete, or zero.

## Adapters

Adapters perform one transformation:

```text
source data → schema-versioned canonical model
```

An adapter may:

- Read a source export
- Map source fields
- Normalize source status values
- Preserve stable source identifiers
- Derive `dataAsOf` where the source semantics allow it
- Record provenance and retrieval details
- Accept or preserve an explicitly supplied `generatedAt`

An adapter must not:

- Render HTML
- Select visual styles
- Publish files
- Contain template-specific layout decisions
- Invent facts absent from the source or supplied configuration
- Silently read the current clock for `generatedAt`

Potential adapters include:

- Canonical JSON pass-through
- CSV field mapping
- Generic REST/API snapshot mapping
- Azure DevOps work-item or build export samples
- Service-health export samples
- Compliance-control export samples

Source-specific adapters are examples and integrations. They do not redefine the ReportKit model.

## Theming and terminology

Configuration may control presentation without changing facts:

- Organization or product name
- Approved colors and design tokens
- Status labels
- Section visibility
- Terminology aliases
- Freshness thresholds
- Date and number formatting
- Self-contained asset policy

Configuration must be versionable and deterministic. It must not contain credentials or source queries.

## Publishing

ReportKit v1 treats publishing as safe file copying.

Possible destinations include:

- SharePoint or OneDrive synchronized folders
- File shares
- GitHub Pages working directories
- Azure DevOps artifact staging directories
- Static storage directories
- Archive or email-attachment packages

A publisher must:

- Confirm that validation contains no errors
- Copy the entire report site
- Avoid transforming report data
- Prevent partial destination replacement
- Preserve the previous publication if copying fails
- Report the final destination

Authentication belongs to the destination environment. Credentials never belong in canonical data, generated HTML, manifests, or logs.

## Repository structure

```text
ReportKit/
├── README.md
├── LICENSE.md
├── SECURITY.md
├── CONTRIBUTING.md
├── SKILL.md
├── docs/
│   ├── product-contract.md
│   ├── canonical-model.md
│   ├── template-authoring.md
│   ├── validation.md
│   ├── publishing.md
│   └── implementation-plan.md
├── schema/
│   └── reportkit-v1.schema.json
├── templates/
│   ├── _shared/
│   ├── executive-health/
│   ├── action-risk/
│   ├── portfolio-team/
│   ├── operational-health/
│   └── compliance-readiness/
├── examples/
│   └── operational-snapshot/
└── scripts/
```

Do not commit local virtual environments, dependency caches, generated package metadata, editor state, temporary files, credentials, or a nested `.git` directory.

## Current project status

ReportKit is currently a Hack Week implementation project with a working Executive Health vertical slice.

| Area | Status |
|---|---|
| Product contract | Frozen for v1 |
| Five template visual designs | Complete |
| Template capability contracts | Available for all five templates |
| Canonical and supporting schemas | Available as v1 baselines |
| `SKILL.md` workflow | Available |
| Shared design system | Design defined; extraction remains |
| Executive Health deterministic generator | Implemented |
| Declarative single-page template packs | Implemented Hack Week foundation |
| Other four renderers | Not implemented yet |
| Model validator | Implemented baseline; broader schema enforcement remains |
| Generated-site validator | Implemented baseline; publication-grade checks remain |
| Sample 401-record dataset | Included |
| Public Executive Health demo output | Included |
| Automated tests | Thirty-four standard-library tests included |
| File-copy publisher | Planned for v1 |

Do not treat prototype HTML as generator output. Prototypes preserve the approved visual direction while reusable templates and deterministic rendering are implemented.

## Hack Week demonstration

The primary demo uses one synthetic 401-record snapshot to create three reports:

1. **Executive Health** — leadership asks whether intervention is required.
2. **Action & Risk Tracker** — operators see what must happen next and who owns it.
3. **Portfolio / Team Rollup** — managers see which teams carry the greatest risk.

The demo proves the core ReportKit idea:

> Same facts. Different audience. Different decision surface.

Operational Health and Compliance / Readiness demonstrate that the same contracts also support reliability, delivery, assurance, and release-review scenarios.

## Security and data handling

Generated reports may contain operationally sensitive information.

Never commit or publish:

- Access tokens
- Passwords
- Client secrets
- Private keys
- Certificates
- Connection strings
- Authentication headers
- Sensitive personal information
- Unapproved internal operational data

ReportKit should fail closed when configured prohibited fields are discovered.

Public examples must use synthetic or explicitly approved data. Classification and freshness must appear in generated HTML and the manifest.

Report suspected vulnerabilities privately through the repository’s configured security-reporting channel. Do not disclose security vulnerabilities in a public issue.

See [SECURITY.md](SECURITY.md) for the security policy.
See the [ReportKit test strategy](docs/test-strategy.md) for P0, P1, and P2 release gates.
See the [ReportKit security test plan](docs/security-test-plan.md) for trust boundaries, implemented controls, and remaining blockers.
See [Custom Templates and Guided Build](docs/custom-templates-guided-build.md) for declarative packs and the four-phase authoring flow.

## Contributing

Contributions are welcome when they preserve the ReportKit architectural boundary and reproducibility guarantee.

Before contributing:

1. Read `docs/product-contract.md`.
2. Keep source-specific behavior in adapters.
3. Keep audience and composition behavior in templates.
4. Keep destination behavior in publishers.
5. Do not introduce required JavaScript for core content.
6. Do not read the current clock during rendering.
7. Add or update capability contracts when template requirements change.
8. Add focused validation and deterministic-output tests for implementation changes.

Template contributions should define:

- Intended audience
- Primary decision
- Required canonical sections and fields
- Optional sections
- Supported page types
- Deterministic ordering
- Missing and edge states
- Responsive behavior
- Print behavior
- Accessibility expectations
- Example canonical input
- Expected generated output

Product-contract changes require an explicit design decision before implementation.

See [CONTRIBUTING.md](CONTRIBUTING.md) for contribution guidance.

## Development roadmap

### v0.1 — End-to-end vertical slice

- [x] Align the first canonical schema and capability contracts
- [x] Add the synthetic 401-record sample
- [x] Implement a dependency-free model-validation baseline
- [x] Render Executive Health deterministically
- [x] Produce the report manifest and validation report
- [x] Add deterministic, escaping, link, count, and fail-closed tests
- [ ] Enforce the complete JSON Schema and template capability contract
- [ ] Strengthen generated-site validation to the full v1 quality gate

### v0.2 — Five-template generation

- Extract shared design primitives
- Render all five templates
- Generate Portfolio / Team child pages
- Support optional-section removal
- Add template-specific semantic validation
- Add deterministic snapshot tests

### v0.3 — Adapters and safe publishing

- Add JSON pass-through adapter
- Add CSV mapping adapter
- Add public source-specific sample adapters
- Implement fail-closed file-copy publishing
- Add SharePoint/OneDrive synchronized-folder example
- Add CI validation examples

### v1.0 — Stable skill contract

- Stabilize canonical schema 1.x
- Stabilize capability-contract format
- Document compatibility and versioning policy
- Complete accessibility and restrictive-host testing
- Publish validated examples and migration guidance

## MVP boundaries

ReportKit v1 includes:

- Five templates
- Canonical schema and semantic validation
- Skill-guided source mapping
- Deterministic static generation
- Responsive and print-ready HTML
- Multi-page report output
- Manifest and validation report
- Sample adapters
- Theming and terminology configuration
- Safe file-copy publication example

ReportKit v1 does not include:

- A hosted reporting service
- An authentication platform
- A visual report editor
- Live mutation of source data
- An arbitrary query engine
- A scheduling service
- Full SharePoint API integration
- A required JavaScript application runtime

## Frequently asked questions

### Is ReportKit a dashboard framework?

No. It creates durable static reports from point-in-time snapshots. It can present dashboard-like summaries, but it does not require a live backend or continuously query source systems.

### Is ReportKit a Python or JavaScript package?

No. ReportKit is primarily a skill, contract, template set, and validation workflow. The current implementation includes dependency-free Python helper scripts, but the repository intentionally does not contain package metadata and does not require publication to a package registry.

### Which templates can the current generator build?

Executive Health is currently connected end to end. The other four templates are approved, navigable static prototypes with capability contracts, but their deterministic renderers are not implemented yet. The build helper fails explicitly if one of those template IDs is requested.

### Are the prototype pages generated output?

No. Files under `templates/*/prototype.html` and their companion pages preserve the approved design and interaction model. Generated output is written to the build destination and includes a manifest and validation report.

### Does ReportKit install dependencies?

No. The current scripts use the Python standard library. Contributors may use additional local development tools, but generated reports must not depend on them.

### Can ReportKit use CSV data?

Yes. A CSV adapter or agent-guided mapping must convert the source into the canonical model before rendering.

### Can one dataset generate several reports?

Yes. This is a core use case. A single canonical snapshot can be communicated differently for executives, operators, managers, service owners, and reviewers.

### Does ReportKit require JavaScript in generated pages?

No. Core content, navigation, tables, responsive layouts, and print rendering must work without JavaScript.

### Can generated reports be hosted on SharePoint?

Yes, when the SharePoint environment can host the generated static files. The v1 publishing example uses a locally synchronized SharePoint or OneDrive folder rather than direct SharePoint API integration.

### Does ReportKit fetch source data while rendering?

No. Adapters obtain or receive source snapshots before rendering. The generator is network-free.

### Where does `generatedAt` come from?

It is explicitly supplied through canonical data or the build invocation. The generator must never silently substitute the current time.

### What happens when data is incomplete?

The report displays an explicit partial, unknown, stale, or validation state. Blocking errors prevent publication. Missing data is never silently converted into a healthy result.

### Can a template add explanatory prose?

Templates may provide labels and structural guidance, but factual statements, status summaries, interventions, outlook, confidence, highlights, and next actions must come from canonical data or deterministic configuration.

### Why include a manifest?

The manifest makes the report machine-readable for catalogs, archives, comparisons, validation, freshness monitoring, and future automation without scraping HTML.

## License

ReportKit is licensed under the [MIT License](LICENSE.md).

## Project principle

When evaluating any new feature, return to the architectural test:

> The source determines the facts.  
> The template determines how those facts are communicated.  
> The destination determines where the generated report lives.

If a feature violates those boundaries, it belongs in another layer—or outside ReportKit v1.
