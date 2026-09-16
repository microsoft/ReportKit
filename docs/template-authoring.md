# Template Authoring

Templates communicate canonical facts for a particular audience. They do not understand source
schemas and do not publish output.

## Built-in files

Each template directory contains:

- `template.json`: capability contract and version
- `README.md`: audience, decision, pages, and data requirements
- `prototype.html`: archived, illustrative design reference, not renderer output

Generated public examples live under `examples/operational-snapshot/generated/<template>/`.
The archived Action & Risk interaction pages are populated from the canonical sample but are
not built-in renderer artifacts. Do not use archived prototype values as implementation evidence.

## Declarative custom packs

Custom packs do not use `prototype.html` or executable renderer files. They require
`template.json`, `layout.json`, `theme.json`, `config.schema.json`, `README.md`, `LICENSE`,
example canonical/configuration files, and declared cases. See
[the complete pack contract](custom-templates-guided-build.md#declarative-pack).
`scripts\validate-template` validates a local folder or ZIP; it does not add or install it.
`scripts\build-template` builds an explicitly selected folder with a matching digest-bound lock.
Run helpers from the complete installed skill root, not the user's report project.

The current custom renderer emits one non-repeating `index.html`. Custom multi-page/repeated-group
rendering, logos, complete terminology substitution, `linkTo` navigation, and distinct layout
variants remain roadmap work; metadata acceptance is not implementation. Built-in Action & Risk
and Portfolio / Team multi-page rendering already works and is separate from this limitation.

## Implemented capabilities versus design intent

`implementationCapabilities` describes actual renderer support. Optional `designCapabilities`
records aspirational behavior and is not a runtime promise. `features` is the legacy runtime alias:
legacy-only contracts remain accepted, but when both runtime objects are present they must match.

Executive Health, Operational Health, and Compliance / Readiness have runtime `multiPage: false`.
Action & Risk and Portfolio / Team have runtime `multiPage: true`. All five built-in designs may
retain `multiPage: true` without claiming that every current renderer generates child pages.
The declarative renderer requires runtime `multiPage: false`, even when its design is multi-page.

For example, the Executive Health capability fragment is:

```json
{
  "features": {
    "multiPage": false, "scriptFree": true, "responsive": true, "printable": true
  },
  "implementationCapabilities": {
    "multiPage": false, "scriptFree": true, "responsive": true, "printable": true
  },
  "designCapabilities": {
    "multiPage": true, "scriptFree": true, "responsive": true, "printable": true
  }
}
```

This is a fragment, not a complete `template.json`; identity, required fields, compatibility, and
other contract fields remain necessary. Declaring a capability never substitutes for implementation
or validation evidence.

## Manifest content identities

The manifest's required `reproducibility` object contains `canonicalModelDigest`,
`configurationDigest`, `renderer` (`id` and `digest`), sorted `sourceIdentifiers`, and
`artifactHashes`. Artifact hashes cover every inventoried output file, including
`validation-report.json`, except `report-manifest.json` itself.

These SHA-256 content identities support reproducibility and tamper detection. They are not
provenance attestations, signatures, Git commit IDs, or proof that a source is trustworthy.
Never add private source identifiers or machine paths to public examples.

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

The current self-contained site policy rejects external `href` and `src` destinations, including
HTTPS anchors. Built-in source/evidence references may display safe HTTP(S) URLs as escaped text,
not clickable external links. Only generated local report navigation is clickable; unsupported
source destination hints must not create output files.

`output.includePrototypeNotice` on generated built-in reports means a review notice:
“Preview report — Generated from canonical data for review.” It does not mean that the generated
artifact is a hand-authored prototype.

## Accessibility

Use semantic headings, landmarks, tables, captions, meaningful link labels, visible focus, text
alternatives for charts, and labels in addition to color.
