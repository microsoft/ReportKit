# ReportKit v1 Product Design

**Status:** Hack Week v1 product contract  
**Scope:** Design and specification only  
**Tagline:** From operational data to a durable report - without building another dashboard.

## 1. Executive Summary

ReportKit is a static-first reporting toolkit that transforms operational data into validated,
audience-specific, publish-ready report sites using reusable templates.

Teams frequently have valuable data in JSON, CSV, APIs, scripts, dashboards, email, and
PowerPoint. Turning that data into a professional report usually requires building and maintaining
a custom application. Reports then become trapped in email threads, inaccessible dashboards, or
one-off presentations.

ReportKit separates the reporting process into four independent concerns:

1. An **adapter** translates source data into a canonical report model.
2. A **template** communicates those facts for a particular audience and reporting purpose.
3. A **generator** creates a portable static report site.
4. A **publisher** copies the validated site to its destination.

S360, Build Health, security reviews, release readiness, and similar systems are sample data
sources. They are not concepts built into ReportKit.

## 2. Mission

> ReportKit is a static-first reporting toolkit that transforms operational data into validated,
> audience-specific, publish-ready report sites using reusable templates.

The key product boundary is:

> The source determines the facts.  
> The template determines how those facts are communicated.  
> The destination determines where the generated report lives.

Any feature that violates this separation belongs in another layer or outside v1.

## 3. Product Principles

### 3.1 Static-first

Static output is a deliberate product capability, not a fallback:

- No backend is required.
- Reports can be hosted almost anywhere.
- A generated report is an archivable point-in-time snapshot.
- Distribution and hosting are inexpensive.
- Reports work in restrictive environments such as SharePoint document libraries.
- Core content remains available when JavaScript is blocked.

JavaScript may be supported later as progressive enhancement, but v1 templates must remain useful
without it.

### 3.2 Source independence

Templates must not understand S360, Azure DevOps, GitHub, Kusto, or another source system. They
understand canonical reporting concepts such as metrics, groups, ownership, deadlines, status,
trends, evidence, and next actions.

### 3.3 Audience-specific communication

The same canonical dataset can produce different reports for different decisions:

- Leadership asks: Are we healthy, and what needs attention?
- Operators ask: What must be fixed, by whom, and when?
- Managers ask: Which teams are carrying the risk?

### 3.4 Deterministic generation

The v1 reproducibility invariant is:

```text
canonical model
+ template version
+ configuration
+ ReportKit version
= identical output
```

`generatedAt` is input data. Rendering must never call the current clock and silently change the
artifact.

Given identical inputs, ReportKit must generate the same:

- Page structure
- Ordering
- File names
- Navigation
- Content
- Manifest
- Validation results

### 3.5 Fail-closed publication

Publication occurs only after the complete report site passes blocking validation. A failed build
or partial generation must not replace the previously published report.

### 3.6 Preserve reporting semantics

ReportKit must not flatten distinct operational concepts:

- Accountable owner versus action owner
- Due date versus ETA
- Status versus next action
- Raw records versus deduplicated items
- Items versus grouped decisions
- `generatedAt` versus `dataAsOf`
- Source navigation versus report navigation

## 4. Target Users

### Report author

A person who has operational data and needs to create a durable report without building a custom
web application.

### Data adapter author

A person who understands a source system and maps its fields into the canonical model.

### Template author

A person who designs how canonical report facts are communicated for a particular audience.

### Automation owner

A person or pipeline that generates, validates, publishes, archives, or indexes reports.

### Report reader

A leader, manager, operator, reviewer, or stakeholder who consumes the generated static site.

## 5. v1 Reporting Templates

Templates are based on reporting jobs, not Microsoft-specific scenarios.

### 5.1 Executive Health

**Audience:** Leadership and program owners

**Questions answered:**

- Are we healthy?
- What changed?
- What needs attention?
- What are the largest risks?
- Is the information fresh?

**Core content:**

- Overall status
- KPI cards
- Trends
- Highlights and wins
- Top risks
- Data freshness
- Optional forward outlook

### 5.2 Action & Risk Tracker

**Audience:** Operators, engineers, and remediation owners

**Questions answered:**

- What requires action?
- Who is accountable?
- Who is performing the action?
- When is it due?
- What is blocking it?
- What happens next?

**Core content:**

- Prioritized action queue
- Severity or priority
- Accountable owner
- Action owner
- Due date
- ETA and ETA health
- Current status
- Blocker
- Next action
- Source/evidence links
- Aging

### 5.3 Portfolio / Team Rollup

**Audience:** Managers and organization leaders

**Questions answered:**

- Which teams or projects carry the most risk?
- How does the portfolio roll up?
- Where should management intervene?

**Core content:**

- Organization summary
- Team/project/service rollups
- Dedicated child pages
- Comparable team metrics
- Team-level action queues
- Ownership and risk concentration

### 5.4 Operational Health

**Audience:** Service owners and on-call teams

**Questions answered:**

- Are builds, deployments, incidents, and services healthy?
- What regressed?
- What is blocking delivery or reliability?

**Core content:**

- Health state
- Builds and deployments
- Incidents and availability
- Reliability signals
- Regressions
- Release blockers
- Known versus unknown root causes
- Recommended operational action

### 5.5 Compliance / Readiness

**Audience:** Reviewers, compliance owners, and release managers

**Questions answered:**

- Which requirements pass or fail?
- What evidence exists?
- What exceptions remain?
- Who owns remediation?
- Are we ready to proceed?

**Core content:**

- Requirements
- Pass/fail/not-applicable status
- Exceptions
- Evidence links
- Accountable and action owners
- Remediation status
- Due dates and ETA
- Readiness decision

## 6. Architecture

```text
Source Data
JSON / CSV / API / script
        |
        v
+----------------------+
|       Adapter        |
| Source -> Canonical  |
+----------+-----------+
           |
           v
+----------------------+
|   Canonical Model    |
|  schemaVersion 1.0   |
+----------+-----------+
           |
      +----+----+
      |         |
      v         v
  Validator  Template
      |         |
      +----+----+
           |
           v
     Site Generator
           |
           v
      report-site\
           |
           v
       Publisher
     file copy only
```

### Layer responsibilities

| Layer | Knows | Must not know |
|---|---|---|
| Adapter | Source format and canonical schema | HTML, template layout, destination |
| Canonical model | Reporting facts and semantics | Source APIs, presentation, destination |
| Validator | Schema, template contract, output rules | Source retrieval behavior |
| Template | Audience and presentation | Source-specific schemas, publishing |
| Generator | Template rendering and deterministic file production | Source retrieval, destination APIs |
| Publisher | Destination and atomic copy behavior | Source semantics, report transformation |

## 7. Canonical Report Model

Every canonical document starts with an explicit schema version:

```json
{
  "schemaVersion": "1.0",
  "report": {
    "id": "service-health-2026-09-15",
    "title": "Service Health",
    "subtitle": "Weekly operational review",
    "generatedAt": "2026-09-15T10:00:00Z",
    "dataAsOf": "2026-09-15T09:55:00Z",
    "status": "yellow",
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

### 7.1 Report metadata

| Field | Required | Purpose |
|---|---:|---|
| `schemaVersion` | Yes | Canonical model compatibility |
| `report.id` | Yes | Stable report/snapshot identity |
| `report.title` | Yes | Primary report title |
| `report.subtitle` | No | Audience or reporting-period context |
| `report.generatedAt` | Yes | Deterministic build input |
| `report.dataAsOf` | Yes | Freshness of the underlying facts |
| `report.status` | Template-dependent | Overall health/readiness state |
| `report.classification` | Yes | Information handling label |

### 7.2 Metrics

Metrics represent summary values and must declare their semantics.

Suggested fields:

```json
{
  "id": "missed-sla",
  "label": "Missed SLA",
  "value": 24,
  "unit": "decisions",
  "status": "critical",
  "description": "Priority decisions requiring immediate attention",
  "target": 10,
  "link": {
    "page": "missed-sla.html"
  }
}
```

Metrics must identify whether they count raw records, items, advisories, grouped decisions, teams,
or another unit.

### 7.3 Groups

Groups represent organizational or analytical rollups such as:

- Organization
- Team
- Project
- Service
- Component
- Program
- Requirement category

Groups may contain metrics, child groups, item references, and dedicated-page metadata.

### 7.4 Items

The canonical item model should preserve operational semantics:

```json
{
  "id": "item-123",
  "title": "Example action",
  "summary": "Why this item matters",
  "status": "in-progress",
  "priority": "high",
  "severity": "important",
  "accountableOwner": {
    "displayName": "Owner Name",
    "alias": "owner"
  },
  "actionOwner": {
    "displayName": "Engineer Name",
    "alias": "engineer"
  },
  "dueDate": "2026-09-30",
  "eta": "2026-09-25",
  "etaHealth": "healthy",
  "statusText": "Implementation is in progress.",
  "nextAction": "Complete validation and request review.",
  "blocker": null,
  "ageDays": 21,
  "groupIds": ["team-a"],
  "links": [],
  "evidence": []
}
```

### 7.5 Trends

Trends contain ordered, explicitly dated observations. The generator must not infer missing
observations or silently interpolate data.

### 7.6 Highlights

Highlights communicate wins, risks, changes, or decisions. They must remain grounded in canonical
facts supplied by the adapter.

### 7.7 Links

Links distinguish:

- Internal report navigation
- Source-system navigation
- Evidence
- Documentation
- Remediation or workflow destinations

### 7.8 Provenance

Provenance records where and how the canonical facts were produced without embedding secrets.

Suggested fields:

```json
{
  "adapter": {
    "id": "s360-sample",
    "version": "1.0"
  },
  "sources": [
    {
      "type": "api",
      "name": "Sample operational source",
      "retrievedAt": "2026-09-15T09:55:00Z"
    }
  ],
  "recordCounts": {
    "raw": 401,
    "canonicalItems": 113,
    "groupedDecisions": 100
  }
}
```

## 8. Schema Versioning

- `schemaVersion` is required at the document root.
- v1 uses schema version `1.0`.
- Adapters declare the schema versions they produce.
- Templates declare the schema versions they accept.
- Validators reject unsupported major versions.
- Backward-compatible additions may increment the minor version.
- Breaking semantic or structural changes increment the major version.
- Old canonical snapshots remain renderable with compatible ReportKit/template versions.

## 9. Template Capability Contract

Each template publishes a machine-readable capability contract.

Example:

```json
{
  "id": "executive-health",
  "version": "1.0",
  "supportedSchemaVersions": ["1.0"],
  "requiredSections": [
    "report",
    "metrics"
  ],
  "requiredFields": [
    "report.title",
    "report.generatedAt",
    "report.dataAsOf"
  ],
  "optionalSections": [
    "trends",
    "highlights",
    "groups",
    "items"
  ],
  "supportedPageTypes": [
    "overview",
    "detail"
  ],
  "features": {
    "multiPage": true,
    "scriptFree": true,
    "responsive": true,
    "printable": true
  }
}
```

The validator uses this contract to produce actionable messages before rendering.

## 10. Adapter Contract

Adapters perform one responsibility:

```text
source data -> canonical model
```

Adapters:

- Know the source schema.
- Preserve canonical reporting semantics.
- Normalize identifiers, dates, statuses, owners, and links.
- Preserve or accept an explicitly supplied `generatedAt`; derive `dataAsOf` from the source where
  appropriate; and supply provenance. Adapters must not silently generate `generatedAt` from the
  current clock.
- Produce schema-valid canonical JSON.
- Must not generate HTML.
- Must not contain template layout decisions.
- Must not publish output.
- Must not embed credentials or secrets.

### v1 adapters

1. JSON canonical passthrough
2. CSV field-mapping adapter
3. S360 sample adapter
4. Azure DevOps Build Health sample adapter

The sample adapters prove extensibility; they do not define the product.

## 11. Configuration

Configuration controls terminology, branding, template options, grouping, ordering, and safe
presentation behavior without changing source facts.

Example:

```json
{
  "template": "action-risk",
  "theme": {
    "name": "contoso",
    "logo": "assets/logo.svg",
    "primaryColor": "#0f6cbd"
  },
  "terminology": {
    "item": "Action",
    "group": "Team",
    "accountableOwner": "Accountable Owner",
    "actionOwner": "Action Owner"
  },
  "navigation": {
    "openInternalLinksInNewTab": true
  },
  "privacy": {
    "allowedClassifications": ["Public", "Internal"],
    "prohibitedFields": ["credentials", "accessToken", "secret"]
  }
}
```

Configuration is part of the deterministic generation input.

## 12. Validation

Validation occurs at two stages:

1. **Model validation** before rendering
2. **Site validation** after rendering and before publication

### 12.1 Severity levels

| Severity | Meaning | Publication |
|---|---|---|
| `error` | Invalid, unsafe, incomplete, or internally inconsistent | Blocked |
| `warning` | Report can be generated but may need attention | Allowed |
| `info` | Informational condition or optional recommendation | Allowed |

### 12.2 Model validation

Model validation checks:

- Supported schema version
- Template capability requirements
- Required metadata
- Required sections and fields
- Valid identifiers
- Valid timestamps and date formats
- Known status and classification values
- Owner semantics
- Due date and ETA semantics
- Metric units
- Group and item references
- Duplicate identifiers
- Provenance
- Prohibited sensitive fields

### 12.3 Site validation

Site validation checks:

- Expected files exist
- Internal links resolve
- Page and tile counts agree with destination pages
- Navigation retains required hosting parameters
- Core content exists without JavaScript
- HTML is escaped
- Required freshness and classification labels are visible
- No prohibited external assets exist in self-contained mode
- Layout remains within supported widths
- Required accessibility labels and document structure exist
- The manifest matches generated files and counts

### 12.4 Validation report

`validation-report.json` is always generated and includes:

```json
{
  "status": "passed-with-warnings",
  "errors": [],
  "warnings": [],
  "info": [],
  "summary": {
    "errorCount": 0,
    "warningCount": 1,
    "infoCount": 2
  }
}
```

## 13. Site Generator

The site generator:

- Accepts canonical data, configuration, and a versioned template.
- Does not retrieve source data.
- Does not call the current clock during rendering.
- Produces deterministic files and ordering.
- Produces script-free core content.
- Supports multi-page reports.
- Escapes all untrusted data.
- Generates the manifest and validation report.
- Does not publish files.

## 14. Output Contract

Every build produces a complete report folder:

```text
report-site\
|-- index.html
|-- pages\
|   |-- ...
|-- assets\
|   |-- report.css
|   `-- ...
|-- report-manifest.json
`-- validation-report.json
```

Templates may choose to inline CSS/assets for restrictive destinations, but the logical output
contract remains the same.

## 15. Report Manifest

The manifest is the machine-readable identity of the generated report.

```json
{
  "reportKitVersion": "0.1.0",
  "schemaVersion": "1.0",
  "template": {
    "id": "executive-health",
    "version": "1.0"
  },
  "reportId": "service-health-2026-09-15",
  "generatedAt": "2026-09-15T10:00:00Z",
  "dataAsOf": "2026-09-15T09:55:00Z",
  "classification": "Internal",
  "pageCount": 6,
  "itemCount": 401,
  "validation": {
    "errors": 0,
    "warnings": 1,
    "info": 2
  }
}
```

Future tools can use manifests to build:

- Report catalogs
- Freshness monitors
- Archives
- Snapshot comparisons
- Search indexes
- Report inventories

No HTML scraping is required.

## 16. Publisher Contract

v1 publishers perform validated file-copy publication only.

Publisher responsibilities:

- Accept a completely generated and validated report folder.
- Confirm that no blocking errors exist.
- Copy the complete artifact to the destination.
- Avoid modifying report content.
- Avoid partial publication.
- Preserve the previously published report if publication fails.
- Report the final destination and publication result.

### v1 destination examples

- SharePoint/OneDrive synchronized folder
- File share
- Azure DevOps pipeline artifact staging folder
- GitHub Pages working directory
- Static storage working directory
- Email attachment package

Direct SharePoint API integration and hosted publication services are outside v1.

## 17. CLI Experience

The intended first-run flow is:

```powershell
reportkit init my-report
Set-Location my-report

reportkit map --data my-data.csv

reportkit build `
  --template executive-health `
  --data report.json

reportkit validate report-site

reportkit publish report-site `
  --target \\sharepoint-sync\Reports\
```

### Proposed commands

| Command | Purpose |
|---|---|
| `reportkit init` | Scaffold a report project |
| `reportkit map` | Help map JSON/CSV source fields into the canonical model |
| `reportkit build` | Generate a report site |
| `reportkit validate` | Validate canonical data or generated output |
| `reportkit publish` | Copy a validated site to a configured destination |

Exact flags and runtime technology remain implementation-design decisions, not product-scope
changes.

## 18. Skill and Documentation Experience

The README and assistant skill are first-class parts of the product.

The guided experience is:

1. Choose a template.
2. Bring existing data.
3. Map data to the canonical model.
4. Configure terminology and branding.
5. Generate the report site.
6. Validate the model and site.
7. Publish the validated artifact.
8. Optionally schedule the same commands externally.

Suggested README structure:

```text
# ReportKit

From operational data to a durable report -
without building another dashboard.

## 1. Choose a template
## 2. Bring your data
## 3. Map to the canonical model
## 4. Generate
## 5. Validate
## 6. Publish
```

The skill helps users select a template, understand validation failures, map source fields, and
generate configuration. It must preserve layer boundaries and must not hide validation failures.

## 19. Security, Privacy, and Data Handling

ReportKit must:

- Escape all untrusted content.
- Never include credentials, tokens, or secrets in output.
- Support prohibited-field validation.
- Display report classification.
- Record provenance without authentication material.
- Avoid external network calls during static rendering.
- Support self-contained output.
- Treat raw source data and generated reports according to configured sensitivity.
- Avoid silent publication after partial or stale data retrieval.

Adapters and publishers own source/destination authentication. Credentials never enter the
canonical model.

## 20. Accessibility and Portability

v1 output must:

- Use semantic HTML.
- Support keyboard navigation.
- Provide visible focus states.
- Use readable color contrast.
- Avoid conveying meaning through color alone.
- Support responsive widths.
- Remain useful when JavaScript is unavailable.
- Provide meaningful link labels.
- Display freshness and classification visibly.
- Support browser printing.

## 21. Repository Structure

Proposed logical structure:

```text
reportkit\
|-- README.md
|-- schemas\
|   `-- report-model-1.0.schema.json
|-- templates\
|   |-- executive-health\
|   |-- action-risk\
|   |-- portfolio-team\
|   |-- operational-health\
|   `-- compliance-readiness\
|-- adapters\
|   |-- json\
|   |-- csv\
|   `-- samples\
|       |-- s360\
|       `-- ado-build-health\
|-- src\
|   |-- cli\
|   |-- validation\
|   |-- generation\
|   `-- publishing\
|-- examples\
|-- tests\
`-- skills\
    `-- reportkit\
```

The exact language and package layout are implementation-design decisions.

## 22. Hack Week Demonstration

Do not lead with S360.

Start with:

> Here are 401 operational records.

Render the same canonical dataset three ways:

### Leadership view

Use **Executive Health** to answer:

- Are we healthy?
- What changed?
- What requires leadership attention?

### Operator view

Use **Action & Risk Tracker** to answer:

- What must be fixed?
- Who owns it?
- When is it due?
- What happens next?

### Manager view

Use **Portfolio / Team Rollup** to answer:

- Which teams carry the risk?
- Where should management intervene?

Reveal afterward that the sample data came from an S360/Build Health scenario. This demonstrates
that the data source is incidental and ReportKit is the product.

## 23. Hack Week v1 Scope

### Included

- Canonical model schema version `1.0`
- Five reusable templates
- Template capability contracts
- JSON passthrough adapter
- CSV mapping adapter
- S360 sample adapter
- Azure DevOps Build Health sample adapter
- CLI
- Model validation
- Generated-site validation
- Error/warning/info validation severity
- Deterministic static generation
- Responsive multi-page output
- Report manifest
- Validation report
- File-copy publisher
- SharePoint synchronized-folder example
- README and assistant skill
- Tests for deterministic output, links, counts, escaping, and publication safety

### Excluded

- Hosted ReportKit service
- Authentication platform
- Live report mutations
- Visual report editor
- Arbitrary query engine
- Built-in scheduling service
- Direct SharePoint API integration
- Backend-dependent templates
- Required JavaScript
- Real-time dashboards
- Email delivery platform
- Report catalog or freshness-monitor service

Scheduling may be demonstrated using external systems such as Task Scheduler or CI/CD, but it is
not a ReportKit v1 responsibility.

## 24. v1 Normative Requirements

- **Adapters MUST** output schema-versioned canonical data.
- **Adapters MUST NOT** silently generate `generatedAt` from the current clock.
- **Adapters MUST NOT** generate presentation or publication output.
- **Templates MUST** publish a machine-readable capability contract.
- **Templates MUST NOT** understand source-specific schemas.
- **Templates MUST** provide useful script-free output.
- **Validation MUST** run before rendering and against generated output.
- **Errors MUST** block publication.
- **Warnings and info MUST** be recorded in `validation-report.json`.
- **Generation MUST** be deterministic for identical inputs.
- **Rendering MUST NOT** call the current clock.
- **Publishers MUST NOT** transform report data.
- **Publishers MUST** fail closed and avoid partial replacement.
- **Freshness and classification MUST** appear in HTML and the manifest.
- **Untrusted values MUST** be HTML-escaped.
- **Generated counts and destination-page counts MUST** agree.
- **Accountable owner and action owner MUST** remain separate concepts.
- **Due date and ETA MUST** remain separate concepts.
- **Status and next action MUST** remain separate concepts.

## 25. Acceptance Criteria

ReportKit v1 is successful when:

1. One canonical dataset can generate at least three audience-specific reports.
2. All five templates operate without source-specific rendering logic.
3. The same inputs generate byte-for-byte equivalent deterministic output where platform-safe.
4. Invalid canonical data produces actionable validation errors.
5. Site validation detects broken links, count mismatches, unsafe HTML, and missing metadata.
6. Blocking validation prevents publication.
7. A complete static site can be copied to and opened from a SharePoint-synchronized folder.
8. Core content works without JavaScript.
9. `report-manifest.json` accurately describes the generated artifact.
10. A new user can follow the README/skill from source data to a published report.

## 26. Deferred Design Decisions

These decisions belong to the implementation-design phase and do not change the frozen product
scope:

- Programming language and runtime
- Template engine
- CLI packaging and installation
- JSON Schema implementation
- CSS organization
- Snapshot testing framework
- Canonical mapping-file syntax
- Exact theme token format
- Atomic directory-swap implementation per platform

## 27. Final Product Contract

> ReportKit is a static-first reporting toolkit that transforms operational data into validated,
> audience-specific, publish-ready report sites using reusable templates.

Its architectural invariant is:

> The source determines the facts.  
> The template determines how those facts are communicated.  
> The destination determines where the generated report lives.

Its reproducibility invariant is:

```text
canonical model
+ template version
+ configuration
+ ReportKit version
= identical output
```
