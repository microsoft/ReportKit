# Contributing to ReportKit

ReportKit contributions must preserve its architectural and reproducibility invariants.

## Before contributing

1. Read [`docs/product-contract.md`](docs/product-contract.md).
2. Do not add source-specific logic to templates.
3. Do not add presentation or publication behavior to adapters.
4. Do not read the current clock during rendering.
5. Do not introduce required JavaScript for core report content.

## Template changes

Template contributions must:

- Include or update the template capability contract.
- Reuse the shared design system.
- Define deterministic ordering.
- Support responsive and print output.
- Include empty, partial, stale, warning, and error states.
- Keep classification and freshness visible.
- Preserve accountable owner/action owner, due date/ETA, and status/next-action distinctions.

## Validation expectations

Changes must eventually include focused tests for:

- Schema validation
- Deterministic output
- HTML escaping
- Broken links
- Count integrity
- Manifest integrity
- Script-free core content
- Publication failure safety

## Pull requests

See [CI and screenshot baselines](docs/ci.md) for reproducible captures and baseline updates.

Keep changes focused and document any product-contract impact. Product-scope changes require an
explicit design decision before implementation.
