# Validation

ReportKit validates both canonical input and generated output.

## Severity

| Severity | Meaning | Publication |
|---|---|---|
| Error | Invalid, unsafe, incomplete, or inconsistent | Blocked |
| Warning | Usable report requiring attention | Allowed |
| Info | Recommendation or optional condition | Allowed |

## Model validation

Checks include:

- Supported schema and template versions
- Required report metadata
- Valid timestamps and dates
- Unique IDs and resolved references
- Explicit metric units
- Ownership, due-date, ETA, status, and next-action semantics
- Provenance
- Prohibited sensitive fields

## Site validation

Checks include:

- Expected files and valid internal links
- Counts matching linked destination pages
- Escaped untrusted data
- Visible freshness and classification
- Script-free core content
- Accessibility structure
- Manifest consistency
- No prohibited external assets in self-contained mode

Validation produces `validation-report.json`. Any error prevents publication.

