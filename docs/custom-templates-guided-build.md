# Custom Templates and Guided Build Experience

## Product decision

ReportKit supports two first-class extension experiences:

1. Configure a built-in template through safe branding, terminology, section, formatting, and design tokens.
2. Bring Your Own Template through a validated declarative pack composed from approved ReportKit components.

Trusted custom renderer code remains a maintainer/contributor extension path, not an ordinary imported template.

The visible user flow is:

> **Choose a template → Add your data → Build and review → Publish to a destination**

Mapping, customization, preview, and validation happen within those four phases. Users do not need to learn the canonical schema, capability contract, renderer architecture, or publisher boundary before starting.

Use **publish to your destination** consistently.

- The source determines the facts.
- The template determines how facts are communicated.
- Validators determine whether the artifact is safe and internally consistent.
- The destination determines where the validated report lives.

## Goals and non-goals

Goals:

- Organization-specific visual identity and terminology.
- One canonical model across built-in and custom templates.
- Safe, deterministic, static-first template addition.
- A guided first-report conversation.
- Responsive, accessible, printable output without a backend.
- Preserved adapter/template/validator/publisher boundaries.

The MVP is not a drag-and-drop editor, query language, executable-plugin marketplace, hosted authoring service, source connector, self-publishing template, validation bypass, or generated-report JavaScript requirement.

## Customization levels

| Level | Experience | Trust |
|---|---|---|
| 1 | Configure a built-in template | Schema-validated safe configuration |
| 2 | Declarative custom template pack | Untrusted until every file, contract, example, and digest validates |
| 3 | Custom renderer extension | Trusted reviewed code with the full security suite |

Level 1 may change names, approved local logos, design tokens, terminology, optional sections, allowed order, freshness thresholds, formatting, status labels, footer, and print identity. It may not change canonical facts, security checks, mandatory metadata, source logic, arbitrary HTML/CSS/JavaScript, or publication behavior.

Level 2 selects and arranges registered components. It contains no executable renderer code.

Level 3 must live in a trusted reviewed location, declare compatibility, remain deterministic/network-free, use ReportKit safety utilities, and never install automatically from an arbitrary URL.

## Declarative pack

```text
my-template/
  template.json
  layout.json
  theme.json
  config.schema.json
  README.md
  LICENSE
  examples/
    minimum.json
    canonical-report.json
    configuration.json
  tests/
    cases.json
  assets/
    logo.png
```

The current validator requires all files except `preview.png` and `assets/`. PNG and WebP are the only permitted asset formats. HTML, CSS, JavaScript, SVG, executables, scripts, symlinks, nested archives, remote assets, traversal paths, and oversized files are rejected.

Custom IDs are lowercase namespaced identifiers such as `contoso/release-review`. `reportkit/*` is reserved. Versions are immutable exact semantic versions. The same ID/version with changed bytes has a changed digest and requires explicit revalidation and relocking.

### Capability

`template.json` declares identity, audience, primary decision, supported schema versions, required sections and fields, optional sections, page types, features, and minimum ReportKit version.

### Layout

`layout.json` composes registered components. It contains no free-form HTML, expressions, or query language. Initial selections are named engine strategies:

- `leadership-attention`
- `all-open`
- `overdue`
- `blocked`
- `due-in-seven-days`

New strategies require engine changes and tests.

### Theme

`theme.json` contains six-digit color tokens, the system font choice, and bounded plain-text terminology. Mandatory identity, classification, freshness, times, validation identity, navigation, manifest, and validation report remain core-owned and cannot be removed or falsified.

### Initial component registry

- Report masthead
- Overall status
- Freshness panel
- Metric grid
- Trend visualization
- Signal list
- Action/decision table
- Group card grid
- Empty state
- Stale-data warning
- Partial-coverage warning
- Validation-warning banner
- Report footer

Each component has explicit sources, variants, selections, deterministic ordering, empty behavior, responsive/print behavior, accessibility structure, and encoding rules.

## Discovery, validation, and locking

Built-ins come from the trusted repository registry. Imported packs are project-local by default:

```text
my-report/
  reportkit.project.json
  reportkit.lock.json
  templates/
    contoso-release-review/
```

The add flow:

1. Select a local folder or ZIP.
2. Inspect entries before extraction.
3. Reject traversal, links, executable/active content, nested archives, unsupported assets, and limits.
4. Validate capability, layout, theme, configuration, examples, and cases.
5. Build and validate the example.
6. Display identity, version, compatibility, pages, required data, trust kind, and restrictions.
7. Ask for confirmation.
8. Copy into the project and record source plus SHA-256 digest.
9. Lock ID, version, kind, path, and digest in `reportkit.lock.json`.

No network installation is supported in the Hack Week MVP. ID collisions never overwrite silently.

Trust labels:

- Built in
- Project template — declarative
- Trusted extension — reviewed code
- Invalid or incompatible

## Guided four-phase experience

### 1. Choose a template

Open with a guided choice: create a report, resume a project, or add a custom template. For a new report ask which decision the audience needs to make, recommend a template, and allow browsing all choices.

Cards show preview, audience, primary decision, required sections, page type, trust label, and implementation status.

### 2. Add your data

MVP inputs are canonical JSON, source JSON, CSV, and the public example. Add sources individually and record classification, freshness semantics, stable identity, mapping, and contributed sections.

Inspect counts, fields, IDs, states, dates, owners, missing concepts, and sensitive fields without displaying secret values. Map required semantics explicitly and never silently guess distinctions such as accountable versus action ownership or due date versus ETA.

### 3. Build and review

1. Customize safe tokens, terminology, sections, thresholds, and local branding.
2. Run schema, capability, semantic, sensitivity, provenance, count, and configuration validation.
3. Generate a staging preview for desktop, mobile, print, page list, manifest, and validation summary.
4. Crawl and validate the entire generated site.

Only a validated artifact advances.

### 4. Publish to a destination

MVP destinations are a local folder, ZIP, and a file share or synchronized folder. Direct authenticated service integrations remain outside Hack Week.

Show report/template identity and digest, dates, classification, counts, validation result, exact destination, and replacement behavior. Require explicit confirmation immediately before replacement.

Publication approval is single-use and bound to artifact hash, validation result, destination, and classification.

The future publisher stages, validates exact bytes, copies only declared files, replaces atomically, preserves the prior destination, validates after copying, and reports the final path and manifest.

## Project state and invalidation

`reportkit.project.json` stores non-secret workflow state. `reportkit.lock.json` stores resolved template identity and digest. Neither stores credentials, headers, private keys, environment values, or unapproved absolute paths.

- Source/canonical changes invalidate mapping, validation, preview, and publication approval.
- Template/config changes invalidate validation, preview, and publication approval.
- Destination changes invalidate publication approval.
- ReportKit/skill changes trigger revalidation and may require regeneration.

## Error and recovery

Errors identify the missing concept or exact pack/contract path and offer repair, alternate template, or cancel. Invalid packs remain quarantined and are never partially installed. Validation errors keep publication unavailable. Warnings explain impact and remain in final records. Publication failure must state that the prior destination was preserved and offer a safe retry without broad-directory deletion.

## Implemented Hack Week foundation

- Four-phase conversational workflow in `SKILL.md`.
- Built-in and declarative trust distinctions.
- Dependency-free local folder and ZIP preflight validator.
- Fixed file/count/byte/type constraints.
- Capability, layout, theme, examples, cases, compatibility, and configuration validation.
- Approved component registry and named selections.
- Stable SHA-256 pack digest.
- Deterministic single-page declarative renderer.
- Manifest template kind, source, version, and digest.
- Project state and lock examples.
- Working `contoso/release-review` example pack.

Current limits:

- The declarative renderer supports one non-repeating `index.html` page.
- Multi-page and repeated-group rendering is specified but deferred.
- Pack addition remains an explicit local copy workflow rather than an installer.
- No remote gallery, marketplace, hosted editor, authenticated source, or publisher is implemented.

## Commands

```powershell
python scripts\validate-template `
  examples\custom-template-project\templates\contoso-release-review

python scripts\build-template `
  --template examples\custom-template-project\templates\contoso-release-review `
  --data examples\custom-template-project\templates\contoso-release-review\examples\canonical-report.json `
  --config examples\custom-template-project\templates\contoso-release-review\examples\configuration.json `
  --lock examples\custom-template-project\reportkit.lock.json `
  --output examples\custom-template-project\generated\release-review
```

## Acceptance

A first-time user succeeds when they can choose a reporting decision, select a built-in or project template, add and map local data, customize safe options, preview, understand validation, explicitly select a destination, and resume the project.

A template author succeeds when they can compose registered components, declare required canonical data, validate examples locally, add the pack to one project, and generate deterministic output carrying the immutable template identity and digest.

Marketing shorthand:

> **Choose the decision. Bring the facts. Publish a durable report.**
>
> Built-in templates when you want speed. Your own template when you need control.
