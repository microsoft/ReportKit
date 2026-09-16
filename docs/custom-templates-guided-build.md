# Custom Templates and Guided Build Experience

## Product decision

This document combines the intended experience with the implemented foundation listed below.
It is not evidence that every workflow step is automated. The menu-first entry point is
`SKILL.md`, with agent display metadata in `agents/openai.yaml`.

The target design has two first-class extension experiences:

1. Configure a built-in template through safe branding, terminology, section, formatting, and design tokens.
2. Bring Your Own Template through a validated declarative pack composed from approved ReportKit components.

Trusted custom renderer code remains a maintainer/contributor extension path, not an ordinary imported template.

The visible user flow is:

> **Choose a template → Add your data → Build and review → Return files or export manually**

Mapping, customization, preview, and validation happen within those four phases. Users do not need to learn the canonical schema, capability contract, renderer architecture, or publisher boundary before starting.

Publication automation is roadmap work; do not present a file return as publication.

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

Level 1's target design allows names, approved local logos, design tokens, terminology, optional
sections, allowed order, freshness thresholds, formatting, status labels, footer, and print identity.
Current sample configurations demonstrate the executable subset. Logo rendering and complete
terminology substitution are not implemented. Configuration may not change canonical facts,
security checks, mandatory metadata, source logic, arbitrary HTML/CSS/JavaScript, or publication behavior.

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

### Configuration schema limits

Custom packs use a restricted JSON Schema subset, not universal JSON Schema conformance.
Unknown keywords and malformed nested keyword shapes are rejected. Supported constraints include
`allOf`, `maxItems`, `maxProperties`, and exclusive numeric bounds.

References must resolve locally to schema nodes. Remote, recursive, and annotation-target
references are rejected; depth, schema size, and reference expansion are bounded. Current schema
limits include depth 20 and 500 schema nodes.

Patterns match the full string. The bounded matcher supports flat literals, character classes,
and repetitions, with a work budget; patterns are limited to 128 characters and repetition bounds
to 1024. Leading `^` and trailing `$` anchors are supported; arbitrary groups, alternation,
lookaround/word-boundary assertions, and backreferences are unsupported. The existing
fixed semantic-version expression is a safe preset, not permission to use arbitrary grouped regex.
Unsupported schemas fail validation rather than silently weakening pack constraints.

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

The registry validates sources, variants, and selections. The renderer implements a bounded
single-page composition; accepting a variant or `linkTo` field does not implement distinct variant
layouts or linked destinations. Those behaviors, custom multi-page/repeated-group rendering,
logo rendering, and complete terminology substitution remain roadmap work.

## Discovery, validation, and locking

Built-ins come from the trusted repository registry. Imported packs are project-local by default:

```text
my-report/
  reportkit.project.json
  reportkit.lock.json
  templates/
    contoso-release-review/
```

Proposed add/install flow (roadmap, not an executable command or coordinator):

1. Select a local folder or ZIP.
2. Inspect entries before extraction.
3. Reject traversal, links, executable/active content, nested archives, unsupported assets, and limits.
4. Validate capability, layout, theme, configuration, examples, and cases.
5. Build and validate the example.
6. Display identity, version, compatibility, pages, required data, trust kind, and restrictions.
7. Ask for confirmation.
8. Copy into the project and record source plus SHA-256 digest.
9. Lock ID, version, kind, path, and digest in `reportkit.lock.json`.

Current commands validate local folders/ZIPs and build a folder with a matching lock; copying a
pack and preparing the lock are explicit manual operations. There is no automatic installer,
quarantine manager, or network installation. ID collisions must never overwrite silently.

Trust labels:

- Built in
- Project template — declarative
- Trusted extension — reviewed code
- Invalid or incompatible

## Guided four-phase experience

### 1. Choose a template

When no concrete task, file, or project is supplied, show exactly these three numbered choices:

1. Start a new report
2. Inspect an existing ReportKit project and continue manually
3. Validate a custom template

Stop after the menu and wait. Do not scan the workspace. Manual inspection is not automated
resume; validation is not template installation. For a new report ask which decision the audience
needs to make, recommend a template, and allow browsing all choices.

Cards show preview, audience, primary decision, required sections, page type, trust label, and implementation status.

### 2. Add your data

Current conversational inputs are canonical JSON, source JSON, CSV, and the synthetic public
example. Source JSON/CSV mapping is manual and agent-assisted, not a generic adapter or executable
mapping engine. Add sources individually and record classification, freshness semantics, stable
identity, mapping, and contributed sections.

Inspect counts, fields, IDs, states, dates, owners, missing concepts, and sensitive fields without displaying secret values. Map required semantics explicitly and never silently guess distinctions such as accountable versus action ownership or due date versus ETA.

### 3. Build and review

1. Use implemented configuration options; do not promise deferred logo/terminology/variant behavior.
2. Run schema, capability, semantic, sensitivity, provenance, count, and configuration validation.
3. Build local files and inspect available pages, manifest, and validation summary; browser,
   mobile, and print review are manual checks, not an automated guided preview coordinator.
4. Crawl and validate the entire generated site.

Only a validated artifact advances.

### 4. Return files or export manually

Current delivery returns a validated local folder. A ZIP or copy to a file share/synchronized
folder is a separately authorized manual operation. No publisher or Pages deployment is implemented.
Direct authenticated service integrations remain outside Hack Week.

Show report/template identity and digest, dates, classification, counts, validation result, exact destination, and replacement behavior. Require explicit confirmation immediately before replacement.

The proposed publisher must bind single-use publication approval to artifact hash, validation
result, destination, and classification; no current coordinator manages these approval states.

The future publisher stages, validates exact bytes, copies only declared files, replaces atomically, preserves the prior destination, validates after copying, and reports the final path and manifest.

## Project state and invalidation

`reportkit.project.json` stores non-secret workflow state. `reportkit.lock.json` stores resolved template identity and digest. Neither stores credentials, headers, private keys, environment values, or unapproved absolute paths.

These are example contracts, not executable init/resume automation. During manual inspection,
read only the user-supplied state file. Do not automatically traverse project references.
Only open a specific reference explicitly requested by the user after confirming it is a safe
scoped relative path within the approved project root. Reject absolute paths, traversal (`..`),
symlinks, junctions, and reparse points in the file or its ancestor directories. Never treat stored
commands, destinations, URLs, or old approval flags as authorization. Ask for the next manual step.

- Source/canonical changes invalidate mapping, validation, preview, and publication approval.
- Template/config changes invalidate validation, preview, and publication approval.
- Destination changes invalidate publication approval.
- ReportKit/skill changes trigger revalidation and may require regeneration.

## Error and recovery

Errors identify the missing concept or exact pack/contract path and offer repair, alternate
template, or cancel. Current validation rejects invalid packs without installing them. Warnings
explain impact and remain in final records. A future installer must not partially install packs;
a future publisher must preserve prior destinations and offer safe recovery without broad deletion.

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
- Source JSON/CSV mapping is manual and agent-assisted; no generic CSV adapter or executable
  mapping engine is implemented.
- Project state examples are not an executable guided init/resume coordinator.
- No Pages deployment is configured or performed.

## Commands

Run from the installed skill root (the complete repository containing `SKILL.md`), not the report
project. See [Copilot skill installation](../README.md#1-make-the-skill-available).

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

## Target acceptance (not a completion claim)

A first-time user succeeds when they can choose a reporting decision, select a built-in or project template, add and map local data, customize safe options, preview, understand validation, explicitly select a destination, and resume the project.

A template author succeeds when they can compose registered components, declare required canonical data, validate examples locally, add the pack to one project, and generate deterministic output carrying the immutable template identity and digest.

## Current completion response

Verify files exist and return clickable `index.html`, `report-manifest.json`, and
`validation-report.json` links to their actual existing output paths. Add a clickable ZIP link only
if explicitly requested and actually created. Explain local-file opening or a user-approved,
verified loopback local server if the client blocks file links. GitHub HTML source is not a live
report and Pages is not deployed. Never commit private machine paths or internal data to public docs.

Marketing shorthand:

> **Choose the decision. Bring the facts. Publish a durable report.**
>
> Built-in templates when you want speed. Your own template when you need control.
