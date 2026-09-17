# ReportKit Test Strategy

## Purpose

ReportKit turns operational facts into durable reports. Testing must protect more than code execution: generated reports must be factually faithful, deterministic, accessible, portable, and understandable by their intended audience. Publication safety is a target requiring additional security gates, not a guarantee of the current experimental release.

This strategy defines three release levels:

- **P0 — Hack Week marketing preview:** honest, visually credible local examples and baseline checks;
  implementation evidence does not imply that every release gate is closed.
- **P1 — Technical preview:** all five templates generated from canonical data with strong contract and site validation.
- **P2 — v1:** publication-grade validation, safe publishing, compatibility, accessibility, and security hardening.

## Testing principles

1. **Facts are immutable across templates.** A template may select, group, label, and order canonical data, but it must not invent or silently change facts.
2. **Unknown is not healthy.** Missing, stale, partial, invalid, or unknown data must never become a positive state.
3. **Identical inputs produce identical bytes.** Determinism includes HTML, JSON, filenames, ordering, and navigation.
4. **Validation fails before publication.** An error preserves the previous valid destination.
5. **Static-first is tested with JavaScript disabled.** Merely omitting JavaScript from one sample page is insufficient.
6. **Public examples are treated as public.** Synthetic-data and secret-scanning checks are release gates.
7. **Visual correctness is behavior.** Responsive layout, print output, focus, and missing-data states are product requirements.

## Current automated baseline

The standard-library suite includes P0 security regressions and declarative-template/guided-flow
tests. Run the suite for the current test count. Coverage and the broader target gates below
must not be confused with production certification.

```powershell
python -B -m unittest discover -s tests -v
```

- The 401-item public sample and expected status counts.
- Deterministic built-in output, including the five-template canonical sample set.
- HTML escaping and script-free generated output.
- Generated-site links, counts, structure, classification, and freshness.
- Case-insensitive duplicate-attribute rejection on every HTML element, including
  rehashed CSP/image bypass fixtures. The browser gate demonstrates first-value parsing
  with traffic intercepted, then confirms validation rejects the fixture before opening it.
- Sensitive canonical field rejection.
- Parseable and minimally aligned machine contracts.
- Complete local HTML resource and fragment resolution across prototypes, companion pages, generated examples, and the showcase.
- Absence of package and local-environment artifacts.
- Preservation of the previous output after a failed build.
- Screenshot contract dimensions and required P0 desktop/mobile coverage.
- Public-sample and launch-asset safety checks.
- Marketing claims aligned with current implementation status.
- A clean-copy, offline, dependency-free smoke test using the README command sequence.
- Text-contract checks for exactly three onboarding choices, pause behavior, manual project
  inspection, whole-folder skill installation, and verified clickable completion artifact links.

This is the P0 automated baseline. It is not sufficient for publication-grade claims.

## P0 — Required before Hack Week marketing

### P0.1 Clean-checkout smoke test

From a clean copy with Python 3.10 or later:

1. Validate the canonical sample.
2. Build all five built-ins with their matching sample configurations.
3. Validate the generated site.
4. Run the complete test suite.
5. Open the result offline.

Acceptance:

- No core package installation.
- README commands work as written.
- No absolute developer paths in output.
- Validation and rendering complete with network access blocked.

The automated suite covers the first four technical conditions. Final browser opening remains a manual release check.

### P0.2 Public-sample safety

Scan committed sample JSON, HTML, screenshots, manifests, and validation reports for secrets, credentials, internal identifiers, internal URLs, real customer or incident names, and unexpected classification values.

Acceptance:

- Launch assets use approved synthetic data.
- Report pages display `Public sample`.
- Secret scanning reports no findings.

The standard-library check scans text assets and uncompressed PNG metadata. A dedicated release secret scanner remains recommended before external publication.

### P0.3 Screenshot contract

Required hero images:

- `executive-health-hero.png`
- `action-risk-hero.png`
- `portfolio-team-hero.png`
- `operational-health-hero.png`
- `compliance-readiness-hero.png`

Acceptance:

- 1440 × 1000.
- Title, classification, period, and freshness visible.
- No preview chrome.
- No clipping or overlap.
- Primary audience decision above the fold.
- Consistent ReportKit identity.

Dimensions, source metadata, fixed capture settings, and overflow detection are automated. Visual credibility and clipping review use the approved scorecard.

### P0.4 Responsive screenshots

Capture every template at 390 × 844. Verify no horizontal overflow, readable content, logical ordering, visible classification and freshness, reachable navigation, and no viewport-dependent loss of facts.

Capture dimensions and horizontal overflow are automated. Human visual review remains required.

### P0.5 Prototype links

Scan every prototype, companion page, generated example, and showcase page for:

- Relative links and fragments.
- Stylesheet and image references.
- Back navigation.
- Portfolio team-card links.
- Action & Risk queue-state links.

All local HTML references and fragments are an automated P0 gate.

### P0.6 Marketing truth

README, screenshots, showcase, and demo materials must state:

- All five built-ins generate reports from canonical JSON.
- The gallery links to generated examples, not archived prototype pages.
- Archived Action & Risk interaction pages are canonical-populated prototypes; other archive
  values are illustrative, not canonical-generated.
- ReportKit is not a hosted Microsoft service.
- ReportKit is not a published language package.
- Validation remains a baseline until all quality gates are enforced.
- Publisher, generic CSV adapter, executable guided init/resume, and Pages deployment are not
  implemented; source mapping is manual and agent-assisted.

README and showcase status language are automated. Final screenshot and narration review remains manual.

Onboarding must distinguish **Start a new report**, **Inspect an existing ReportKit project and
continue manually**, and **Validate a custom template**, then stop for a selection. Tests must
reject extra numbered choices and resume/install promises. Project references are untrusted:
no automatic traversal, and only user-explicit safe scoped relative references may be opened;
absolute, traversal, symlink/junction/reparse-point paths must be rejected.

Installation examples must use the complete repository under a lowercase `reportkit` directory,
retain scripts/schema/docs/agents, avoid overwriting existing folders, and run commands from the
installed skill root. Completion must link actual existing `index.html`, `report-manifest.json`,
and `validation-report.json`; an optional ZIP must exist before it is linked. File links/local
servers are not GitHub Pages deployment. These are instruction-contract checks, not end-to-end
proof that an external agent obeys the instructions.

### P0.7 Five-second comprehension

Show each hero to at least three people unfamiliar with ReportKit for five seconds. Ask:

1. Who is the report for?
2. What decision does it support?
3. What needs attention?

Pass when at least two of three participants answer the first two questions correctly for every template. This is a manual marketing test.

## P1 — Required before technical preview

All P1 gates must pass before ReportKit is described as a technical preview.

### Contract and input validation

- Apply all five JSON Schemas to positive and negative fixtures.
- Require runtime validation and schemas to reject the same fixtures.
- Enforce every capability `requiredFields` expression without renderer exceptions.
- Validate configuration before rendering.
- Reject CSS injection, invalid colors, invalid thresholds, unknown properties, and unsafe terminology values.
- Test comprehensive HTML, attribute, CSS, URL, and bidirectional-control payloads.
- Enforce safe URL schemes.

### Time and determinism

- Test timestamp ordering, equivalent offsets, timezone requirements, leap days, period order, and freshness boundaries.
- Prove the generator never reads the system clock.
- Produce byte-identical output for all five templates.
- Shuffle input arrays when templates define their own order.
- Verify deterministic tie-breakers and expected changes when reproducibility inputs change.

### Fact fidelity and reconciliation

- Trace every displayed fact to canonical data or deterministic configuration.
- Detect template-authored factual prose with marker fixtures.
- Reconcile source, canonical, displayed, grouped, portfolio, exception, and requirement counts.
- Define percentage denominators and rounding.
- Prevent partial coverage from appearing fully healthy.

### Template semantics

**Action & Risk**

- Explicit report-date boundaries for overdue and due-in-seven-days.
- All attention selects declared attention statuses or an explicit nonblank blocker; health
  status is not an open/closed lifecycle.
- Date queues use the UTC date of `generatedAt`, exclude terminal/healthy statuses unless blocked,
  and include both today and today + 7 in the upcoming window.
- Missing due dates do not become overdue.
- Overlapping views remain valid and are not presented as additive buckets.
- Every selected tile reconciles with rows and has a static route back.

**Portfolio / Team**

- Real links, stable path-safe IDs, deterministic collision handling, detail reconciliation, back navigation, empty and partial states, and separate accountable/action ownership.

**Operational Health**

- Critical incidents remain visible even when service status is healthy.
- Unknown telemetry is not healthy.
- Maintenance, incidents, builds, deployments, degradation, and recovery remain distinct.
- Recovery milestones are canonical facts.

**Compliance / Readiness**

- Missing or expired evidence is not a pass.
- Exceptions remain distinct from satisfied requirements.
- Expired exceptions follow explicit policy.
- Requirement, exception, evidence, scope, and not-applicable denominators remain distinct.

### Missing-data matrix

Every renderer needs fixtures for absent trend history, no open attention, empty optional sections, stale data, partial coverage, unknown status, missing ownership, missing dates, warnings, and empty required sections. Optional sections disappear cleanly; required missing data blocks generation.

### Whole-site validation

Crawl every generated page and validate:

- Links, fragments, assets, duplicate IDs, titles, one meaningful `h1`, and landmarks.
- Classification and freshness.
- Script-free and self-contained policies.
- Safe URL schemes.
- Manifest inventory, page counts, item counts, schema compliance, and publishable validation status.
- Rejection of traversal, absolute paths, encoded traversal, and paths outside the site root.
- Broken-child adversarial fixtures even when `index.html` is valid.

### Accessibility, visual, offline, and platforms

- Automated keyboard, focus, accessible-name, heading, landmark, table, contrast, reduced-motion, and serious-violation checks.
- Approved desktop, mobile, full-page, interaction, and missing-state visual baselines.
- Network-disabled rendering and navigation.
- Windows, Linux, and macOS smoke tests, including spaces, Unicode paths, read-only inputs, and existing-output replacement.

## P2 — Required before v1

### Publisher fail-closed behavior

- Block publication on validation errors.
- Apply explicit warning policy.
- Preserve previous destinations after interruption.
- Switch destinations only after complete validation and copy.
- Support safe cross-volume staging and recovery.
- Prevent source/destination path escape and symlink or reparse-point redirection.
- Never modify report data.

### Manifest integrity

- Declare every generated file and publish no undeclared file.
- Record and verify content hashes.
- Record ReportKit, schema, template, and configuration identity.
- Reconcile freshness, classification, page count, and item count with HTML and canonical data.

### Compatibility, fuzzing, and scale

- Fixtures for every supported schema/template version pair.
- Deterministic migration behavior and early unsupported-version failures.
- Property and fuzz cases for size, Unicode, IDs, cycles, values, and dates.
- Defined performance limits for 401, 5,000, and 25,000 items.
- Actionable failure when supported limits are exceeded.

### Browsers, print, and restrictive hosts

- Chromium, Firefox, and WebKit at supported sizes.
- Print/PDF page breaks, table headings, identity, freshness, classification, grayscale meaning, and no clipping.
- GitHub Pages, static servers, synchronized SharePoint/OneDrive folders, artifact download, and supported local-file browsing.
- Document supported CSP, MIME, path, and filename behavior.

## Suggested suite organization

```text
tests/
  unit/
    test_schema_validation.py
    test_semantics.py
    test_configuration.py
    test_ordering.py
  integration/
    test_build_all_templates.py
    test_determinism.py
    test_fail_closed.py
    test_manifest.py
  contracts/
    valid/
    invalid/
    missing-states/
  site/
    test_links.py
    test_counts.py
    test_offline.py
    test_accessibility.py
  visual/
    screenshot-contract.json
    baselines/
  security/
    test_escaping.py
    test_safe_urls.py
    test_sensitive_data.py
    test_path_safety.py
```

The Python standard-library suite remains the required core. Browser, accessibility, schema, and visual tooling must remain development-only.

## Recommended CI jobs

| Job | Pull requests | Main | Release |
|---|---:|---:|---:|
| Core unit and integration | Yes | Yes | Yes |
| Schema fixture validation | Yes | Yes | Yes |
| Determinism and golden hashes | Yes | Yes | Yes |
| Link, manifest, and offline checks | Yes | Yes | Yes |
| Secret and public-sample scan | Yes | Yes | Yes |
| Accessibility smoke | Yes | Yes | Yes |
| Desktop visual regression | Yes | Yes | Yes |
| Mobile and cross-browser visual suite | Optional | Yes | Yes |
| Clean Windows/Linux/macOS smoke | Optional | Yes | Yes |
| Performance and scale | No | Scheduled | Yes |
| Publisher destination tests | No | Yes | Yes |

## Highest-priority next ten tests

1. Validate canonical input with the actual JSON Schema.
2. Validate configuration and reject CSS injection.
3. Enforce template `requiredFields` without renderer crashes.
4. Crawl and validate every generated HTML page and link.
5. Test Action & Risk tile counts and static destinations.
6. Test Portfolio team-card links and count reconciliation.
7. Add one missing-data fixture for every template.
8. Add deterministic desktop and mobile screenshot comparison for all five templates.
9. Add whole-model HTML, attribute, CSS, and URL injection fixtures.
10. Add a clean-checkout offline smoke test matching the README.

Items 4 and 10 now have P0 baseline coverage. Their P1 forms remain broader because they must validate generated child pages, manifests, accessibility, and all five renderers.

## Release decision

- **Hack Week:** requires the complete P0 set, accurate status language, approved synthetic assets, and no navigation surprises.
- **Technical preview:** requires all five deterministic renderers and the complete P1 contract, site, accessibility, and visual gates.
- **v1:** requires fail-closed publication, content integrity, compatibility, security hardening, cross-browser/print behavior, restrictive-host validation, and documented operational limits.
