# ReportKit Security Test Plan

## Security objective

ReportKit must safely transform untrusted operational data and configuration into a validated static site without executing source content, leaking sensitive information, loading unexpected external resources, escaping the intended output directory, or replacing a previously valid report with an invalid one.

> ReportKit treats source data as data, generates inert static output, validates the complete artifact, and publishes only after validation succeeds.

ReportKit is skill-first. The security boundary includes the Python helpers and the agent instructions in `SKILL.md`.

## Trust boundaries

| Input or component | Trust level | Required treatment |
|---|---|---|
| Source JSON, CSV, exports, and text | Untrusted | Parse as data; never interpret as HTML, code, commands, or agent instructions |
| Canonical report model | Untrusted until validated | Apply structural, semantic, sensitivity, size, and reference validation |
| Rendering configuration | Untrusted until validated | Strict properties and token allowlists; no arbitrary CSS or HTML |
| Template capability contract | Repository-controlled but validated | Validate compatibility and required capabilities |
| Template implementation | Trusted code | Review, test, own, and render deterministically |
| Generated site | Untrusted until post-render validation | Crawl and validate every file and page |
| Manifest and validation report | Generated security records | Validate shape, reconcile with site, and reject stale or forged status |
| Publication destination | Explicitly authorized, potentially hostile | Contain paths, reject redirection, stage safely, and replace atomically |
| Source/report hyperlinks | Untrusted destinations | Enforce schemes and paths; never fetch while building |
| Instructions embedded in data | Prompt injection | Render as inert data and never expand agent authority |

## Primary threats

- Stored markup, attribute, or script injection.
- CSS injection through configuration.
- Unsafe, credential-bearing, local-file, protocol-relative, or active URLs.
- External tracking and runtime dependencies.
- Secrets, personal data, internal identifiers, or local paths in public output.
- Path traversal through links, IDs, manifests, filenames, and destinations.
- Symbolic-link, junction, or reparse-point redirection.
- Forged or stale manifests and validation reports.
- Partial generation or loss of the last valid report.
- Resource exhaustion and renderer crashes.
- Prompt injection against the ReportKit skill.
- CI workflow and development-tool supply-chain compromise.
- Security claims that exceed implemented controls.

## Current P0 security baseline

The current vertical slice implements:

- Structural and semantic canonical validation with duplicate/reference checks.
- Rejection of prohibited sensitive field names and selected sensitive value patterns.
- Additional public-sample identifier checks.
- Strict configuration properties, template identity, hexadecimal color, boolean output, and bounded/ordered freshness thresholds.
- Context-safe HTML text and attribute escaping for the Executive Health renderer.
- Validated CSS color tokens instead of arbitrary CSS interpolation.
- A restrictive generated-page Content Security Policy.
- Whole-site HTML crawling.
- Rejection of scripts, frames, embedded objects, forms, base elements, meta refresh, and inline event handlers.
- Self-contained URL enforcement and no external resources.
- Repeated URL decoding, resolved path containment, reserved-name rejection, and manifest-path validation.
- Complete file-inventory reconciliation.
- Manifest identity checks against rendered output.
- Validation-report count/status reconciliation.
- Fail-closed invalid model/configuration and post-render validation behavior.
- Offline clean-copy workflow coverage.
- Explicit prompt-injection rules in `SKILL.md`.
- Adversarial regression fixtures in `tests/security/`.

The following remain P0 blockers before any claim of publication-safe or publication-grade output:

- Full evaluation of the checked-in JSON Schemas against positive and negative fixture corpora.
- Complete nested-property enforcement across every canonical type.
- Comprehensive context tests for every future renderer field and URL-bearing canonical property.
- Sensitive-data scanning with a dedicated secret scanner plus human public-data review.
- Renderer-exception, disk-full, interrupted-write, stale-temporary, and stale-backup simulations.
- Browser-confirmed zero-request navigation of the generated site.
- Publication controls; no publisher currently exists.

## P0 security gates

### P0.1 Canonical schema enforcement

Apply `schema/reportkit-v1.schema.json`, reject missing or unknown properties, invalid and duplicate IDs, invalid states, malformed owners, boolean metrics, invalid dates/trends, unresolved references, and absent capability-required fields. Every failure must be structured and must occur before rendering.

### P0.2 Configuration validation

Reject CSS-breaking values, style termination, quotes, braces, semicolons, URL functions, invalid or reversed freshness thresholds, HTML-bearing unsupported properties, unknown properties, and external resource configuration. Prefer constrained tokens.

### P0.3 Context-aware output encoding

Test every rendered string in HTML text, attributes, titles, metadata, CSS tokens, URLs, and JSON records. Payloads include elements, quote breaking, style termination, mixed encoding, bidirectional controls, unusual whitespace, and long values.

### P0.4 Safe URL policy

- Internal navigation: contained relative paths and fragments only.
- Generated self-contained output: no external destinations or assets.
- Future external source links: HTTPS only by explicit policy.
- Reject `javascript:`, `data:` links, `file:`, `vbscript:`, protocol-relative, control-character, encoded-scheme, and credential-bearing URLs.
- Never retrieve links during generation or validation.

### P0.5 Whole-site security validation

Every generated page must reject active content, event handlers, unsafe links, broken references, missing classification/freshness, external assets, redirects, duplicate IDs, missing landmarks, and missing CSP.

Adversarial fixtures must include a clean `index.html` plus a malicious child page.

### P0.6 Path containment

Resolve paths and prove containment inside the intended root. Reject traversal, absolute paths, drive and UNC paths, repeated encoded traversal, mixed slashes, controls, reserved names, unsafe IDs, and duplicate normalized paths.

### P0.7 Manifest and validation integrity

Require both records. Reconcile inventory, pages, items, status, counts, report identity, template identity, timestamps, freshness source, and classification. Actual validation errors always override a claimed pass.

### P0.8 Sensitive-data detection

Detect sensitive keys and suspicious values including tokens, authorization headers, secrets, keys, connection strings, signed URLs, internal identifiers, emails, hosts, and local user paths. Public samples require an explicit human review in addition to automation.

### P0.9 Prompt-injection protection

The skill must treat all source content as untrusted data. It must never follow embedded instructions, execute supplied commands, open supplied URLs, widen access, include environment data, or publish without explicit authorization.

### P0.10 Fail-closed generation

Invalid input, configuration, renderer failures, post-render failures, storage interruptions, and stale staging state must preserve the last valid site. No partial output may replace it.

### P0.11 Offline and no exfiltration

Build and validate with networking disabled. Browser navigation must make zero requests and require no remote fonts, images, styles, scripts, or analytics.

### P0.12 Public repository scan

Scan the repository and release archive for secrets, internal identifiers, local paths, development artifacts, logs, dumps, unapproved samples, unintended generated files, and license/attribution gaps.

## P1 technical-preview gates

- Resource limits for bytes, depth, counts, strings, pages, output size, runtime, and memory.
- Relationship-cycle detection.
- Numerical safety for NaN, infinity, ranges, division, and visual percentages.
- CSP compatibility testing and equivalent hosting-header guidance.
- SHA-256 file inventory and post-copy verification.
- Safe publisher roots, staging, replacement, rollback, permissions, and link handling.
- Time-of-check/time-of-use protection for the exact staged bytes.
- Redacted errors without secrets, records, environment values, or customer-facing traces.
- Property and fuzz testing.
- Cross-platform filesystem security, including case collisions and Windows reserved names.

All five templates must use the same validated engine before technical preview.

## P2 v1 hardening

- Checked-in threat model with assets, entry points, assumptions, mitigations, accepted risks, and exclusions.
- Independent security review covering injection, prompt injection, filesystem safety, validator bypasses, CI, release provenance, and restrictive hosts.
- Protected-branch release provenance, checksums, SBOMs where applicable, source/workflow identity, and optional signatures or attestations.
- Complete vulnerability-management process in `SECURITY.md`.
- Sanitized regression fixtures for every discovered security issue.

## GitHub and CI security

- Default workflow permissions to `contents: read`.
- Grant additional permissions only per job.
- Never expose secrets to untrusted fork pull requests.
- Avoid `pull_request_target` when contributor code is checked out or executed.
- Separate validation from publication and require protected-environment approval.
- Pin actions to immutable commit SHAs.
- Review action publishers, permissions, dependencies, and licenses.
- Keep browser and accessibility tools development-only.
- Protect the default branch and require passing security checks.
- Require review for `SKILL.md`, schemas, validator, renderer, publisher, and workflow changes.
- Add CODEOWNERS for security-sensitive paths.
- Enable secret scanning, push protection, dependency alerts, and static analysis where available.

## Automated security suite

```text
tests/security/
  test_schema_bypass.py
  test_html_encoding.py
  test_attribute_encoding.py
  test_css_tokens.py
  test_safe_urls.py
  test_external_assets.py
  test_sensitive_fields.py
  test_sensitive_values.py
  test_path_containment.py
  test_manifest_integrity.py
  test_child_page_validation.py
  test_prompt_injection_fixture.py
  test_resource_limits.py
  test_fail_closed.py
  test_publisher_safety.py
```

The current consolidated P0 regression module is `tests/security/test_security_p0.py`. Split it as the security corpus grows.

## Recommended security CI

| Job | Hack Week | Technical preview | v1 |
|---|---:|---:|---:|
| Schema and semantic negative fixtures | Required | Required | Required |
| HTML, CSS, attribute, and URL injection | Required | Required | Required |
| Whole-site and external-resource scan | Required | Required | Required |
| Public-sample and secret scan | Required | Required | Required |
| Offline/no-network build | Required | Required | Required |
| Repository/archive hygiene | Required | Required | Required |
| Static analysis | Recommended | Required | Required |
| Fuzz and resource limits | Optional | Required | Required |
| Cross-platform paths | Optional | Required | Required |
| Publisher interruption/symlink tests | Not applicable | Required when implemented | Required |
| Checksums, SBOM, and attestation | Optional | Recommended | Required |

## Immediate priorities

1. Apply the real canonical and configuration schemas.
2. Expand context-aware injection fixtures across every rendered field.
3. Extend safe URL policy to future canonical links.
4. Add renderer/storage interruption simulations.
5. Add a dedicated secret scanner and human public-data sign-off.
6. Add resource limits and cycle detection.
7. Add hashes to the manifest.
8. Implement and test a fail-closed publisher.
9. Add cross-platform security CI.
10. Conduct an independent security review before v1.

## Security release decision

- **Hack Week:** remain an experimental preview until every P0 blocker above is closed and manually reviewed.
- **Technical preview:** requires P1 controls, all five validated renderers, and required security CI.
- **v1:** requires independent review, safe publisher testing, provenance, vulnerability management, and a retained regression corpus.
